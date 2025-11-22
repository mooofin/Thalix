"""
Memory Scanning Engine - High-performance memory scanning with multithreading.

This module provides the core scanning functionality for finding values in
process memory, including exact value scans and incremental rescans.
"""

import numpy as np
import threading
import queue
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Callable, Any
from enum import Enum

from .memory_manager import MemoryManager, MemoryRegion
from .memory_region_manager import MemoryRegionManager
from .data_types import DataType, ValueComparator, ComparisonType, ValuePacker

logger = logging.getLogger(__name__)


class ScanType(Enum):
    """Types of memory scans."""
    EXACT_VALUE = "exact_value"
    INCREASED = "increased"
    DECREASED = "decreased"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


@dataclass
class ScanResults:
    """
    Results from a memory scan operation.
    
    Stores found addresses and metadata about the scan.
    For incremental scans, also stores the previous values.
    """
    addresses: np.ndarray  # Array of addresses (uint64)
    data_type: DataType
    scan_type: ScanType
    timestamp: datetime
    region_count: int
    bytes_scanned: int
    previous_values: Optional[dict[int, bytes]] = None  # For incremental scans
    
    def __len__(self) -> int:
        """Get the number of results."""
        return len(self.addresses)
    
    def get_address_list(self) -> List[int]:
        """Get addresses as a Python list."""
        return self.addresses.tolist()
    
    def get_statistics(self) -> dict:
        """Get statistics about the scan results."""
        return {
            'result_count': len(self.addresses),
            'data_type': self.data_type.name,
            'scan_type': self.scan_type.value,
            'timestamp': self.timestamp.isoformat(),
            'region_count': self.region_count,
            'bytes_scanned': self.bytes_scanned,
            'memory_usage_mb': self.addresses.nbytes / (1024 * 1024)
        }


@dataclass
class ScanProgress:
    """Progress information for a scan operation."""
    regions_scanned: int
    total_regions: int
    bytes_scanned: int
    results_found: int
    
    @property
    def percentage(self) -> float:
        """Get completion percentage (0-100)."""
        if self.total_regions == 0:
            return 0.0
        return (self.regions_scanned / self.total_regions) * 100.0


class ScanEngine:
    """
    High-performance memory scanning engine.
    
    Provides methods for scanning process memory with various search types
    and data types. Uses multithreading and buffered reads for performance.
    """
    
    # Default buffer size for memory reads (256KB)
    DEFAULT_BUFFER_SIZE = 256 * 1024
    
    def __init__(self, 
                 memory_manager: MemoryManager,
                 region_manager: MemoryRegionManager,
                 buffer_size: int = DEFAULT_BUFFER_SIZE):
        """
        Initialize ScanEngine.
        
        Args:
            memory_manager: MemoryManager instance for reading memory.
            region_manager: MemoryRegionManager for accessing region information.
            buffer_size: Size of buffer for memory reads (default: 256KB).
        """
        self.memory_manager = memory_manager
        self.region_manager = region_manager
        self.buffer_size = buffer_size
        
        # Progress tracking
        self._progress_queue: queue.Queue = queue.Queue()
        self._progress_callback: Optional[Callable[[ScanProgress], None]] = None
        
        # Cancellation mechanism
        self._cancel_event = threading.Event()
        
        # Value comparator for type-specific comparisons
        self.comparator = ValueComparator()
        
        logger.info(
            f"ScanEngine initialized with buffer size {buffer_size} bytes"
        )
    
    def set_progress_callback(self, callback: Callable[[ScanProgress], None]):
        """
        Set a callback function for progress updates.
        
        The callback will be called periodically with ScanProgress objects.
        
        Args:
            callback: Function that takes a ScanProgress parameter.
        """
        self._progress_callback = callback
    
    def cancel_scan(self):
        """
        Cancel the currently running scan.
        
        This sets a cancellation flag that worker threads check periodically.
        The scan will stop as soon as possible, but may not be immediate.
        """
        logger.info("Scan cancellation requested")
        self._cancel_event.set()
    
    def _reset_cancellation(self):
        """Reset the cancellation flag for a new scan."""
        self._cancel_event.clear()
    
    def _is_cancelled(self) -> bool:
        """Check if scan has been cancelled."""
        return self._cancel_event.is_set()
    
    def _report_progress(self, progress: ScanProgress):
        """
        Report progress to the callback if set.
        
        Args:
            progress: ScanProgress object with current status.
        """
        # Put progress in queue for thread-safe access
        try:
            self._progress_queue.put_nowait(progress)
        except queue.Full:
            pass  # Skip if queue is full
        
        # Call callback if set
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _read_region_buffered(self, region: MemoryRegion) -> List[tuple[int, bytes]]:
        """
        Read a memory region in buffered chunks.
        
        Reads the region in chunks of buffer_size, handling partial reads
        and respecting region boundaries.
        
        Args:
            region: MemoryRegion to read.
        
        Returns:
            List of (address, data) tuples for successfully read chunks.
        """
        chunks = []
        address = region.base_address
        region_end = region.base_address + region.size
        
        while address < region_end:
            # Check for cancellation
            if self._is_cancelled():
                logger.debug("Region read cancelled")
                break
            
            # Calculate chunk size (don't exceed region boundary)
            chunk_size = min(self.buffer_size, region_end - address)
            
            # Read memory
            data, success = self.memory_manager.read_memory(address, chunk_size)
            
            if data:
                # Store the chunk (even if partial read)
                chunks.append((address, data))
                
                # Move to next chunk
                # Use actual bytes read, not requested size
                address += len(data)
                
                if not success:
                    # Partial read - log and continue
                    logger.debug(
                        f"Partial read at 0x{address:X}: "
                        f"got {len(data)}/{chunk_size} bytes"
                    )
            else:
                # Complete failure - skip to next buffer-sized chunk
                logger.debug(f"Read failed at 0x{address:X}, skipping")
                address += self.buffer_size
        
        return chunks
    
    def _read_addresses_buffered(self, 
                                 addresses: np.ndarray,
                                 data_type: DataType) -> dict[int, bytes]:
        """
        Read memory at specific addresses in an efficient manner.
        
        For incremental scans, reads only the addresses from previous results.
        Groups nearby addresses to minimize read operations.
        
        Args:
            addresses: Array of addresses to read.
            data_type: Data type to read (determines read size).
        
        Returns:
            Dictionary mapping address to bytes data.
        """
        results = {}
        value_size = data_type.size
        
        # Sort addresses for efficient reading
        sorted_addresses = np.sort(addresses)
        
        for address in sorted_addresses:
            # Check for cancellation
            if self._is_cancelled():
                break
            
            # Read the value at this address
            data, success = self.memory_manager.read_memory(
                int(address), 
                value_size
            )
            
            if data and len(data) == value_size:
                results[int(address)] = data
        
        return results
    
    def scan_exact_value(self,
                        value: Any,
                        data_type: DataType,
                        regions: Optional[List[MemoryRegion]] = None,
                        use_epsilon: bool = False) -> ScanResults:
        """
        Scan memory for exact value matches.
        
        Args:
            value: Value to search for.
            data_type: Data type of the value.
            regions: Optional list of regions to scan.
            use_epsilon: If True, use epsilon-based comparison for floats.
        
        Returns:
            ScanResults object containing found addresses.
        """
        logger.info(f"Starting exact value scan for {value} ({data_type.name})")
        
        self._reset_cancellation()
        
        if regions is None:
            # Get only writable regions (like Cheat Engine does by default)
            # This filters to PAGE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY
            regions = self.region_manager.get_writable_regions()
            # Also ensure they're readable and committed
            regions = [r for r in regions if r.is_readable and r.state.value == 0x1000]  # MEM_COMMIT
        
        if not regions:
            logger.warning("No regions to scan")
            return ScanResults(
                addresses=np.array([], dtype=np.uint64),
                data_type=data_type,
                scan_type=ScanType.EXACT_VALUE,
                timestamp=datetime.now(),
                region_count=0,
                bytes_scanned=0
            )
        
        try:
            target_bytes = ValuePacker.pack(value, data_type)
        except Exception as e:
            raise ValueError(f"Failed to pack value: {e}")
        
        logger.info(f"Scanning {len(regions)} regions for value {value}...")
        
        value_size = data_type.size
        
        def scan_chunk(chunk_address: int, chunk_data: bytes) -> List[int]:
            found = []
            for offset in range(0, len(chunk_data) - value_size + 1):
                candidate_bytes = chunk_data[offset:offset + value_size]
                if candidate_bytes == target_bytes:
                    found.append(chunk_address + offset)
            return found
        
        coordinator = ScanCoordinator(
            memory_manager=self.memory_manager,
            buffer_size=self.buffer_size,
            thread_count=None
        )
        
        found_addresses = coordinator.scan_regions(
            regions=regions,
            scan_func=scan_chunk,
            cancel_event=self._cancel_event,
            progress_callback=self._progress_callback
        )
        
        total_bytes = sum(r.size for r in regions)
        addresses_array = np.array(found_addresses, dtype=np.uint64)
        
        logger.info(f"Exact value scan complete: {len(addresses_array)} matches found")
        
        return ScanResults(
            addresses=addresses_array,
            data_type=data_type,
            scan_type=ScanType.EXACT_VALUE,
            timestamp=datetime.now(),
            region_count=len(regions),
            bytes_scanned=total_bytes
        )
    
    def scan_increased(self, previous_results: ScanResults) -> ScanResults:
        """Scan for values that have increased."""
        return self._scan_incremental(previous_results, ComparisonType.INCREASED)
    
    def scan_decreased(self, previous_results: ScanResults) -> ScanResults:
        """Scan for values that have decreased."""
        return self._scan_incremental(previous_results, ComparisonType.DECREASED)
    
    def scan_changed(self, previous_results: ScanResults) -> ScanResults:
        """Scan for values that have changed."""
        return self._scan_incremental(previous_results, ComparisonType.CHANGED)
    
    def scan_unchanged(self, previous_results: ScanResults) -> ScanResults:
        """Scan for values that have not changed."""
        return self._scan_incremental(previous_results, ComparisonType.UNCHANGED)
    
    def _scan_incremental(self, previous_results: ScanResults, 
                         comparison_type: ComparisonType) -> ScanResults:
        """Perform incremental scan on previous results."""
        logger.info(f"Starting {comparison_type.value} scan on {len(previous_results.addresses)} addresses")
        
        self._reset_cancellation()
        
        if len(previous_results.addresses) == 0:
            logger.warning("No previous addresses to scan")
            return ScanResults(
                addresses=np.array([], dtype=np.uint64),
                data_type=previous_results.data_type,
                scan_type=ScanType.INCREMENTAL,
                timestamp=datetime.now(),
                region_count=0,
                bytes_scanned=0
            )
        
        # Read all addresses
        address_data = self._read_addresses_buffered(
            previous_results.addresses,
            previous_results.data_type
        )
        
        # Compare values
        filtered_addresses = []
        for addr in previous_results.addresses:
            if self._is_cancelled():
                break
            
            addr_int = int(addr)
            if addr_int not in address_data:
                continue
            
            new_bytes = address_data[addr_int]
            
            try:
                new_value = ValuePacker.unpack(new_bytes, previous_results.data_type)
                
                # Get old value if available
                old_value = None
                if hasattr(previous_results, 'previous_values') and previous_results.previous_values:
                    idx = np.where(previous_results.addresses == addr)[0]
                    if len(idx) > 0:
                        old_value = previous_results.previous_values.get(addr_int)
                
                if old_value is None:
                    # First incremental scan - just store the value
                    if comparison_type in [ComparisonType.CHANGED, ComparisonType.UNCHANGED]:
                        continue  # Can't compare without old value
                    filtered_addresses.append(addr_int)
                else:
                    # Compare based on type
                    match = False
                    if comparison_type == ComparisonType.INCREASED:
                        match = new_value > old_value
                    elif comparison_type == ComparisonType.DECREASED:
                        match = new_value < old_value
                    elif comparison_type == ComparisonType.CHANGED:
                        match = new_value != old_value
                    elif comparison_type == ComparisonType.UNCHANGED:
                        match = new_value == old_value
                    
                    if match:
                        filtered_addresses.append(addr_int)
            except:
                pass
        
        addresses_array = np.array(filtered_addresses, dtype=np.uint64)
        
        logger.info(f"{comparison_type.value} scan complete: {len(addresses_array)} matches")
        
        return ScanResults(
            addresses=addresses_array,
            data_type=previous_results.data_type,
            scan_type=ScanType.INCREMENTAL,
            timestamp=datetime.now(),
            region_count=0,
            bytes_scanned=len(address_data) * previous_results.data_type.size
        )


class ScanWorker(threading.Thread):
    """
    Worker thread for scanning memory regions.
    
    Processes assigned regions and reports results back to the coordinator.
    """
    
    def __init__(self,
                 worker_id: int,
                 region_queue: queue.Queue,
                 result_queue: queue.Queue,
                 memory_manager: MemoryManager,
                 buffer_size: int,
                 cancel_event: threading.Event,
                 scan_func: Callable):
        """
        Initialize ScanWorker.
        
        Args:
            worker_id: Unique identifier for this worker.
            region_queue: Queue to get regions to scan.
            result_queue: Queue to put scan results.
            memory_manager: MemoryManager for reading memory.
            buffer_size: Size of buffer for reads.
            cancel_event: Event to check for cancellation.
            scan_func: Function to call for scanning each chunk.
        """
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.region_queue = region_queue
        self.result_queue = result_queue
        self.memory_manager = memory_manager
        self.buffer_size = buffer_size
        self.cancel_event = cancel_event
        self.scan_func = scan_func
        
    def run(self):
        """Process regions from the queue until empty or cancelled."""
        logger.debug(f"Worker {self.worker_id} started")
        
        while not self.cancel_event.is_set():
            try:
                # Get a region to scan (with timeout to check cancellation)
                region = self.region_queue.get(timeout=0.1)
            except queue.Empty:
                # No more regions
                break
            
            try:
                # Scan this region
                results = self._scan_region(region)
                
                # Put results in result queue
                self.result_queue.put((region, results))
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
            finally:
                self.region_queue.task_done()
        
        logger.debug(f"Worker {self.worker_id} finished")
    
    def _scan_region(self, region: MemoryRegion) -> List[int]:
        """
        Scan a single region.
        
        Args:
            region: MemoryRegion to scan.
        
        Returns:
            List of addresses where matches were found.
        """
        found_addresses = []
        address = region.base_address
        region_end = region.base_address + region.size
        
        while address < region_end and not self.cancel_event.is_set():
            # Calculate chunk size
            chunk_size = min(self.buffer_size, region_end - address)
            
            # Read memory
            data, success = self.memory_manager.read_memory(address, chunk_size)
            
            if data:
                # Scan this chunk
                chunk_results = self.scan_func(address, data)
                found_addresses.extend(chunk_results)
                
                # Move to next chunk
                address += len(data)
            else:
                # Skip failed read
                address += self.buffer_size
        
        return found_addresses


class ScanCoordinator:
    """
    Coordinates multithreaded scanning operations.
    
    Distributes regions across worker threads and aggregates results.
    """
    
    def __init__(self,
                 memory_manager: MemoryManager,
                 buffer_size: int,
                 thread_count: Optional[int] = None):
        """
        Initialize ScanCoordinator.
        
        Args:
            memory_manager: MemoryManager for reading memory.
            buffer_size: Size of buffer for reads.
            thread_count: Number of worker threads (default: CPU count).
        """
        self.memory_manager = memory_manager
        self.buffer_size = buffer_size
        
        # Determine thread count
        if thread_count is None or thread_count <= 0:
            self.thread_count = os.cpu_count() or 4
        else:
            self.thread_count = thread_count
        
        logger.info(f"ScanCoordinator using {self.thread_count} threads")
    
    def scan_regions(self,
                    regions: List[MemoryRegion],
                    scan_func: Callable,
                    cancel_event: threading.Event,
                    progress_callback: Optional[Callable] = None) -> List[int]:
        """
        Scan multiple regions using worker threads.
        
        Args:
            regions: List of MemoryRegion objects to scan.
            scan_func: Function to call for scanning each chunk.
                      Should take (address, data) and return list of addresses.
            cancel_event: Event to check for cancellation.
            progress_callback: Optional callback for progress updates.
        
        Returns:
            List of all found addresses.
        """
        if not regions:
            return []
        
        # Create queues
        region_queue = queue.Queue()
        result_queue = queue.Queue()
        
        # Fill region queue
        for region in regions:
            region_queue.put(region)
        
        # Create and start workers
        workers = []
        for i in range(self.thread_count):
            worker = ScanWorker(
                worker_id=i,
                region_queue=region_queue,
                result_queue=result_queue,
                memory_manager=self.memory_manager,
                buffer_size=self.buffer_size,
                cancel_event=cancel_event,
                scan_func=scan_func
            )
            worker.start()
            workers.append(worker)
        
        # Aggregate results
        aggregator = ResultAggregator(
            result_queue=result_queue,
            total_regions=len(regions),
            progress_callback=progress_callback
        )
        
        # Wait for all workers to finish
        for worker in workers:
            worker.join()
        
        # Get final results
        all_addresses = aggregator.get_results()
        
        logger.info(f"Scan complete: {len(all_addresses)} addresses found")
        return all_addresses


class ResultAggregator:
    """
    Aggregates results from worker threads in a thread-safe manner.
    
    Collects results and tracks progress.
    """
    
    def __init__(self,
                 result_queue: queue.Queue,
                 total_regions: int,
                 progress_callback: Optional[Callable] = None):
        """
        Initialize ResultAggregator.
        
        Args:
            result_queue: Queue to receive results from workers.
            total_regions: Total number of regions being scanned.
            progress_callback: Optional callback for progress updates.
        """
        self.result_queue = result_queue
        self.total_regions = total_regions
        self.progress_callback = progress_callback
        
        self.all_addresses = []
        self.regions_completed = 0
        self.bytes_scanned = 0
        
        # Start aggregation thread
        self._aggregation_thread = threading.Thread(
            target=self._aggregate_results,
            daemon=True
        )
        self._aggregation_thread.start()
    
    def _aggregate_results(self):
        """Aggregate results from the queue."""
        while self.regions_completed < self.total_regions:
            try:
                # Get result with timeout
                region, addresses = self.result_queue.get(timeout=0.5)
                
                # Add to results
                self.all_addresses.extend(addresses)
                self.regions_completed += 1
                self.bytes_scanned += region.size
                
                # Report progress
                if self.progress_callback:
                    from .scan_engine import ScanProgress
                    progress = ScanProgress(
                        regions_scanned=self.regions_completed,
                        total_regions=self.total_regions,
                        bytes_scanned=self.bytes_scanned,
                        results_found=len(self.all_addresses)
                    )
                    try:
                        self.progress_callback(progress)
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")
                
                self.result_queue.task_done()
                
            except queue.Empty:
                # Timeout - continue waiting
                continue
    
    def get_results(self) -> List[int]:
        """
        Get all aggregated results.
        
        Waits for aggregation to complete.
        
        Returns:
            List of all found addresses.
        """
        # Wait for aggregation thread to finish
        self._aggregation_thread.join(timeout=5.0)
        return self.all_addresses
    
    def scan_exact_value(self,
                        value: Any,
                        data_type: DataType,
                        regions: Optional[List[MemoryRegion]] = None,
                        use_epsilon: bool = False) -> ScanResults:
        """
        Scan memory for exact value matches.
        
        Searches all readable committed regions for addresses containing
        the specified value.
        
        Args:
            value: Value to search for.
            data_type: Data type of the value.
            regions: Optional list of regions to scan. If None, scans all
                    readable committed regions.
            use_epsilon: If True, use epsilon-based comparison for floats.
        
        Returns:
            ScanResults object containing found addresses.
        
        Raises:
            ValueError: If value is invalid for the data type.
        """
        logger.info(
            f"Starting exact value scan for {value} ({data_type.name})"
        )
        
        # Reset cancellation flag
        self._reset_cancellation()
        
        # Get regions to scan if not provided
        if regions is None:
            regions = self.region_manager.get_readable_regions()
            # Filter to only committed regions
            regions = [r for r in regions if r.is_readable]
        
        if not regions:
            logger.warning("No regions to scan")
            return ScanResults(
                addresses=np.array([], dtype=np.uint64),
                data_type=data_type,
                scan_type=ScanType.EXACT_VALUE,
                timestamp=datetime.now(),
                region_count=0,
                bytes_scanned=0
            )
        
        # Calculate total memory to scan
        total_bytes = sum(r.size for r in regions)
        total_mb = total_bytes / (1024 * 1024)
        logger.info(f"Scanning {len(regions)} writable regions ({total_mb:.2f} MB) for value {value}...")
        
        # Pack the target value into bytes for comparison
        try:
            target_bytes = ValuePacker.pack(value, data_type)
        except Exception as e:
            raise ValueError(f"Failed to pack value: {e}")
        
        # Create scan function for exact value matching
        value_size = data_type.size
        
        def scan_chunk(chunk_address: int, chunk_data: bytes) -> List[int]:
            """Scan a chunk of memory for exact value matches."""
            found = []
            
            # Search for the target bytes in this chunk
            # Slide through the chunk with value_size steps
            for offset in range(0, len(chunk_data) - value_size + 1):
                candidate_bytes = chunk_data[offset:offset + value_size]
                
                if use_epsilon and data_type.is_float:
                    # Unpack and compare with epsilon
                    try:
                        candidate_value = ValuePacker.unpack(candidate_bytes, data_type)
                        if self.comparator.compare_exact(
                            value, candidate_value, data_type, use_epsilon=True
                        ):
                            found.append(chunk_address + offset)
                    except:
                        pass  # Skip invalid values
                else:
                    # Bitwise comparison
                    if candidate_bytes == target_bytes:
                        found.append(chunk_address + offset)
            
            return found
        
        # Create coordinator and scan
        coordinator = ScanCoordinator(
            memory_manager=self.memory_manager,
            buffer_size=self.buffer_size,
            thread_count=None  # Use default (CPU count)
        )
        
        # Scan regions
        found_addresses = coordinator.scan_regions(
            regions=regions,
            scan_func=scan_chunk,
            cancel_event=self._cancel_event,
            progress_callback=self._progress_callback
        )
        
        # Calculate total bytes scanned
        total_bytes = sum(r.size for r in regions)
        
        # Convert to numpy array
        addresses_array = np.array(found_addresses, dtype=np.uint64)
        
        logger.info(
            f"Exact value scan complete: {len(addresses_array)} matches found"
        )
        
        return ScanResults(
            addresses=addresses_array,
            data_type=data_type,
            scan_type=ScanType.EXACT_VALUE,
            timestamp=datetime.now(),
            region_count=len(regions),
            bytes_scanned=total_bytes
        )
    
    def scan_increased(self, previous_results: ScanResults) -> ScanResults:
        """
        Scan for values that have increased since the previous scan.
        
        Reads memory at addresses from previous results and compares
        with current values.
        
        Args:
            previous_results: Results from a previous scan.
        
        Returns:
            ScanResults with addresses where values increased.
        """
        logger.info(
            f"Starting increased scan on {len(previous_results)} addresses"
        )
        
        # Reset cancellation flag
        self._reset_cancellation()
        
        return self._incremental_scan(
            previous_results,
            ScanType.INCREASED,
            ComparisonType.INCREASED
        )
    
    def scan_decreased(self, previous_results: ScanResults) -> ScanResults:
        """
        Scan for values that have decreased since the previous scan.
        
        Args:
            previous_results: Results from a previous scan.
        
        Returns:
            ScanResults with addresses where values decreased.
        """
        logger.info(
            f"Starting decreased scan on {len(previous_results)} addresses"
        )
        
        # Reset cancellation flag
        self._reset_cancellation()
        
        return self._incremental_scan(
            previous_results,
            ScanType.DECREASED,
            ComparisonType.DECREASED
        )
    
    def scan_changed(self, previous_results: ScanResults) -> ScanResults:
        """
        Scan for values that have changed since the previous scan.
        
        Args:
            previous_results: Results from a previous scan.
        
        Returns:
            ScanResults with addresses where values changed.
        """
        logger.info(
            f"Starting changed scan on {len(previous_results)} addresses"
        )
        
        # Reset cancellation flag
        self._reset_cancellation()
        
        return self._incremental_scan(
            previous_results,
            ScanType.CHANGED,
            ComparisonType.CHANGED
        )
    
    def scan_unchanged(self, previous_results: ScanResults) -> ScanResults:
        """
        Scan for values that have not changed since the previous scan.
        
        Args:
            previous_results: Results from a previous scan.
        
        Returns:
            ScanResults with addresses where values are unchanged.
        """
        logger.info(
            f"Starting unchanged scan on {len(previous_results)} addresses"
        )
        
        # Reset cancellation flag
        self._reset_cancellation()
        
        return self._incremental_scan(
            previous_results,
            ScanType.UNCHANGED,
            ComparisonType.UNCHANGED
        )
    
    def _incremental_scan(self,
                         previous_results: ScanResults,
                         scan_type: ScanType,
                         comparison_type: ComparisonType) -> ScanResults:
        """
        Perform an incremental scan comparing current values to previous.
        
        Args:
            previous_results: Results from a previous scan.
            scan_type: Type of scan being performed.
            comparison_type: Type of comparison to perform.
        
        Returns:
            ScanResults with addresses matching the comparison criteria.
        """
        if len(previous_results) == 0:
            logger.warning("No previous results to scan")
            return ScanResults(
                addresses=np.array([], dtype=np.uint64),
                data_type=previous_results.data_type,
                scan_type=scan_type,
                timestamp=datetime.now(),
                region_count=0,
                bytes_scanned=0
            )
        
        data_type = previous_results.data_type
        value_size = data_type.size
        
        # Read current values at all previous addresses
        logger.info(f"Reading {len(previous_results)} addresses...")
        current_values = self._read_addresses_buffered(
            previous_results.addresses,
            data_type
        )
        
        # If we don't have previous values stored, we need to read them now
        # This happens on the first incremental scan after an exact value scan
        if previous_results.previous_values is None:
            logger.info("No previous values stored, reading them now...")
            previous_values = current_values.copy()
        else:
            previous_values = previous_results.previous_values
        
        # Compare values
        matching_addresses = []
        new_previous_values = {}
        
        for address in previous_results.addresses:
            address_int = int(address)
            
            # Check for cancellation
            if self._is_cancelled():
                break
            
            # Skip if we couldn't read current value
            if address_int not in current_values:
                continue
            
            current_bytes = current_values[address_int]
            
            # For first incremental scan, we can't compare
            if previous_results.previous_values is None:
                # Store current value for next scan
                new_previous_values[address_int] = current_bytes
                # Include all addresses in results for first incremental scan
                matching_addresses.append(address_int)
                continue
            
            # Skip if we don't have previous value
            if address_int not in previous_values:
                continue
            
            previous_bytes = previous_values[address_int]
            
            # Perform comparison based on type
            matches = False
            
            if comparison_type == ComparisonType.CHANGED:
                # Bitwise comparison for changed
                matches = self.comparator.compare_changed_bytes(
                    previous_bytes, current_bytes
                )
            elif comparison_type == ComparisonType.UNCHANGED:
                # Bitwise comparison for unchanged
                matches = self.comparator.compare_unchanged_bytes(
                    previous_bytes, current_bytes
                )
            else:
                # Unpack values for numeric comparison
                try:
                    old_value = ValuePacker.unpack(previous_bytes, data_type)
                    new_value = ValuePacker.unpack(current_bytes, data_type)
                    
                    matches = self.comparator.compare(
                        old_value, new_value, data_type, comparison_type
                    )
                except Exception as e:
                    logger.debug(f"Failed to unpack values at 0x{address_int:X}: {e}")
                    continue
            
            if matches:
                matching_addresses.append(address_int)
                # Store current value as previous for next scan
                new_previous_values[address_int] = current_bytes
        
        # Convert to numpy array
        addresses_array = np.array(matching_addresses, dtype=np.uint64)
        
        # Calculate bytes scanned
        bytes_scanned = len(previous_results) * value_size
        
        logger.info(
            f"{scan_type.value} scan complete: "
            f"{len(addresses_array)}/{len(previous_results)} matches"
        )
        
        return ScanResults(
            addresses=addresses_array,
            data_type=data_type,
            scan_type=scan_type,
            timestamp=datetime.now(),
            region_count=0,  # Not applicable for incremental scans
            bytes_scanned=bytes_scanned,
            previous_values=new_previous_values
        )
