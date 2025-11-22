"""
Value Freezer - Continuously write values to memory addresses.

This module provides functionality to "freeze" memory values by continuously
writing them at regular intervals, preventing the target process from changing them.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
import logging
import uuid

from .memory_manager import MemoryManager
from .data_types import DataType, ValuePacker

logger = logging.getLogger(__name__)


@dataclass
class FreezeEntry:
    """
    Represents a frozen memory address.
    
    Attributes:
        id: Unique identifier for this freeze entry
        address: Memory address to freeze
        value: Value to continuously write
        data_type: Data type of the value
        interval_ms: Write interval in milliseconds
        enabled: Whether this freeze is currently active
        original_value: Original value before freezing started
        last_write_time: Timestamp of last successful write
        failure_count: Number of consecutive write failures
    """
    id: str
    address: int
    value: Any
    data_type: DataType
    interval_ms: int = 100
    enabled: bool = True
    original_value: Optional[Any] = None
    last_write_time: Optional[float] = None
    failure_count: int = 0
    
    def __post_init__(self):
        """Validate freeze entry fields."""
        if self.address < 0:
            raise ValueError(f"Invalid address: {self.address}")
        if self.interval_ms <= 0:
            raise ValueError(f"Invalid interval: {self.interval_ms}")


class FreezerManager:
    """
    Manages frozen memory values.
    
    Runs a background worker thread that continuously writes frozen values
    to their respective addresses at configured intervals.
    """
    
    def __init__(self, memory_manager: MemoryManager, 
                 max_consecutive_failures: int = 5):
        """
        Initialize FreezerManager.
        
        Args:
            memory_manager: MemoryManager instance for writing memory.
            max_consecutive_failures: Maximum consecutive failures before pausing freeze.
        """
        self.memory_manager = memory_manager
        self.max_consecutive_failures = max_consecutive_failures
        
        # Freeze entries: id -> FreezeEntry
        self._freezes: Dict[str, FreezeEntry] = {}
        self._lock = threading.Lock()
        
        # Worker thread
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_running = False
        self._stop_event = threading.Event()
        
        # Callbacks
        self._failure_callback: Optional[Callable[[str, FreezeEntry], None]] = None
        
        logger.info("FreezerManager initialized")
    
    def start(self):
        """Start the freezer worker thread."""
        if self._worker_running:
            logger.warning("Freezer worker already running")
            return
        
        self._worker_running = True
        self._stop_event.clear()
        
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )
        self._worker_thread.start()
        
        logger.info("Freezer worker started")
    
    def stop(self):
        """Stop the freezer worker thread."""
        if not self._worker_running:
            return
        
        self._worker_running = False
        self._stop_event.set()
        
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None
        
        logger.info("Freezer worker stopped")
    
    def add_freeze(self, address: int, value: Any, data_type: DataType,
                  interval_ms: int = 100, original_value: Optional[Any] = None) -> str:
        """
        Add a new freeze entry.
        
        Args:
            address: Memory address to freeze.
            value: Value to continuously write.
            data_type: Data type of the value.
            interval_ms: Write interval in milliseconds.
            original_value: Original value before freezing (for restoration).
        
        Returns:
            Unique ID of the created freeze entry.
        
        Raises:
            ValueError: If address, value, or interval is invalid.
        """
        if address < 0:
            raise ValueError(f"Invalid address: {address}")
        if interval_ms <= 0:
            raise ValueError(f"Invalid interval: {interval_ms}")
        
        # Validate value can be packed
        try:
            ValuePacker.pack(value, data_type)
        except Exception as e:
            raise ValueError(f"Invalid value for {data_type.name}: {e}")
        
        # Generate unique ID
        freeze_id = str(uuid.uuid4())
        
        # Create freeze entry
        freeze = FreezeEntry(
            id=freeze_id,
            address=address,
            value=value,
            data_type=data_type,
            interval_ms=interval_ms,
            enabled=True,
            original_value=original_value
        )
        
        # Add to freezes
        with self._lock:
            self._freezes[freeze_id] = freeze
        
        logger.info(
            f"Added freeze: ID={freeze_id}, Address=0x{address:X}, "
            f"Value={value}, Interval={interval_ms}ms"
        )
        
        # Start worker if not running
        if not self._worker_running:
            self.start()
        
        return freeze_id
    
    def remove_freeze(self, freeze_id: str) -> bool:
        """
        Remove a freeze entry.
        
        Args:
            freeze_id: ID of the freeze to remove.
        
        Returns:
            True if freeze was removed, False if not found.
        """
        with self._lock:
            if freeze_id in self._freezes:
                freeze = self._freezes[freeze_id]
                del self._freezes[freeze_id]
                logger.info(
                    f"Removed freeze: ID={freeze_id}, Address=0x{freeze.address:X}"
                )
                return True
            else:
                logger.warning(f"Attempted to remove non-existent freeze: {freeze_id}")
                return False
    
    def enable_freeze(self, freeze_id: str) -> bool:
        """
        Enable a freeze entry.
        
        Args:
            freeze_id: ID of the freeze to enable.
        
        Returns:
            True if freeze was enabled, False if not found.
        """
        with self._lock:
            freeze = self._freezes.get(freeze_id)
            if freeze:
                freeze.enabled = True
                freeze.failure_count = 0  # Reset failure count
                logger.info(f"Enabled freeze: ID={freeze_id}")
                return True
            else:
                logger.warning(f"Attempted to enable non-existent freeze: {freeze_id}")
                return False
    
    def disable_freeze(self, freeze_id: str, restore_original: bool = False) -> bool:
        """
        Disable a freeze entry.
        
        Args:
            freeze_id: ID of the freeze to disable.
            restore_original: Whether to restore the original value.
        
        Returns:
            True if freeze was disabled, False if not found.
        """
        with self._lock:
            freeze = self._freezes.get(freeze_id)
        
        if not freeze:
            logger.warning(f"Attempted to disable non-existent freeze: {freeze_id}")
            return False
        
        # Restore original value if requested
        if restore_original and freeze.original_value is not None:
            try:
                original_bytes = ValuePacker.pack(freeze.original_value, freeze.data_type)
                success = self.memory_manager.write_memory(freeze.address, original_bytes)
                if success:
                    logger.info(
                        f"Restored original value at 0x{freeze.address:X}"
                    )
                else:
                    logger.warning(
                        f"Failed to restore original value at 0x{freeze.address:X}"
                    )
            except Exception as e:
                logger.error(
                    f"Error restoring original value at 0x{freeze.address:X}: {e}"
                )
        
        # Disable freeze
        with self._lock:
            freeze.enabled = False
        
        logger.info(f"Disabled freeze: ID={freeze_id}")
        return True
    
    def get_freeze(self, freeze_id: str) -> Optional[FreezeEntry]:
        """
        Get a freeze entry by ID.
        
        Args:
            freeze_id: ID of the freeze to retrieve.
        
        Returns:
            FreezeEntry if found, None otherwise.
        """
        with self._lock:
            return self._freezes.get(freeze_id)
    
    def get_all_freezes(self) -> Dict[str, FreezeEntry]:
        """
        Get all freeze entries.
        
        Returns:
            Dictionary mapping freeze IDs to FreezeEntry objects.
        """
        with self._lock:
            return self._freezes.copy()
    
    def get_freeze_status(self, freeze_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for a freeze entry.
        
        Args:
            freeze_id: ID of the freeze.
        
        Returns:
            Dictionary with status information, or None if not found.
        """
        with self._lock:
            freeze = self._freezes.get(freeze_id)
        
        if not freeze:
            return None
        
        return {
            'id': freeze.id,
            'address': freeze.address,
            'value': freeze.value,
            'data_type': freeze.data_type.name,
            'interval_ms': freeze.interval_ms,
            'enabled': freeze.enabled,
            'last_write_time': freeze.last_write_time,
            'failure_count': freeze.failure_count,
            'is_paused': freeze.failure_count >= self.max_consecutive_failures
        }
    
    def set_failure_callback(self, callback: Callable[[str, FreezeEntry], None]):
        """
        Set a callback to be called when a freeze fails repeatedly.
        
        Args:
            callback: Function to call with (freeze_id, freeze_entry) when max failures reached.
        """
        self._failure_callback = callback
    
    def _worker_loop(self):
        """Main worker loop that writes frozen values."""
        logger.debug("Freezer worker loop started")
        
        # Track last write time for each freeze
        last_write_times: Dict[str, float] = {}
        
        while not self._stop_event.is_set():
            current_time = time.perf_counter()
            
            # Get all enabled freezes
            with self._lock:
                freezes = [f for f in self._freezes.values() if f.enabled]
            
            # Process each freeze
            for freeze in freezes:
                # Check if it's time to write
                last_write = last_write_times.get(freeze.id, 0)
                interval_sec = freeze.interval_ms / 1000.0
                
                if current_time - last_write >= interval_sec:
                    # Check if freeze is paused due to failures
                    if freeze.failure_count >= self.max_consecutive_failures:
                        continue
                    
                    # Write the value
                    try:
                        value_bytes = ValuePacker.pack(freeze.value, freeze.data_type)
                        success = self.memory_manager.write_memory(
                            freeze.address,
                            value_bytes
                        )
                        
                        if success:
                            # Update freeze entry
                            with self._lock:
                                freeze.last_write_time = current_time
                                freeze.failure_count = 0
                            
                            last_write_times[freeze.id] = current_time
                            
                            logger.debug(
                                f"Wrote frozen value to 0x{freeze.address:X}"
                            )
                        else:
                            # Write failed
                            with self._lock:
                                freeze.failure_count += 1
                            
                            logger.warning(
                                f"Failed to write frozen value to 0x{freeze.address:X} "
                                f"(failure {freeze.failure_count}/{self.max_consecutive_failures})"
                            )
                            
                            # Check if max failures reached
                            if freeze.failure_count >= self.max_consecutive_failures:
                                logger.error(
                                    f"Freeze paused due to repeated failures: "
                                    f"ID={freeze.id}, Address=0x{freeze.address:X}"
                                )
                                
                                # Call failure callback if set
                                if self._failure_callback:
                                    try:
                                        self._failure_callback(freeze.id, freeze)
                                    except Exception as e:
                                        logger.error(
                                            f"Error in failure callback: {e}"
                                        )
                    
                    except Exception as e:
                        logger.error(
                            f"Error writing frozen value to 0x{freeze.address:X}: {e}"
                        )
                        with self._lock:
                            freeze.failure_count += 1
            
            # Sleep for a short time to avoid busy-waiting
            # Use the minimum interval among all freezes, or 10ms default
            if freezes:
                min_interval = min(f.interval_ms for f in freezes) / 1000.0
                sleep_time = min(min_interval / 2, 0.01)  # Half of min interval, max 10ms
            else:
                sleep_time = 0.1  # 100ms when no freezes
            
            self._stop_event.wait(sleep_time)
        
        logger.debug("Freezer worker loop stopped")
    
    def clear(self):
        """Clear all freeze entries."""
        with self._lock:
            self._freezes.clear()
        
        logger.info("All freezes cleared")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()
