"""
Address Table Management - Track and manage memory addresses of interest.

This module provides functionality to maintain a table of memory addresses,
read/write their values, and support undo operations.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from collections import deque
from datetime import datetime
import logging
import uuid

from .memory_manager import MemoryManager
from .data_types import DataType, ValueParser, ValuePacker, ValueFormatter

logger = logging.getLogger(__name__)


@dataclass
class AddressEntry:
    """
    Represents a tracked memory address in the address table.
    
    Attributes:
        id: Unique identifier for this entry
        address: Memory address to track
        data_type: Data type of the value at this address
        description: User-provided description
        module_name: Optional module name for relative addressing
        last_value: Last read value from this address
        last_read_time: Timestamp of last successful read
        is_frozen: Whether this address is currently frozen
    """
    id: str
    address: int
    data_type: DataType
    description: str = ""
    module_name: Optional[str] = None
    last_value: Optional[Any] = None
    last_read_time: Optional[float] = None
    is_frozen: bool = False
    
    def __post_init__(self):
        """Validate address entry fields."""
        if self.address < 0:
            raise ValueError(f"Invalid address: {self.address}")


@dataclass
class UndoEntry:
    """
    Represents an undo operation for a memory write.
    
    Attributes:
        timestamp: When the write occurred
        address: Memory address that was written
        original_bytes: Original bytes before the write
        new_bytes: New bytes that were written
        description: Description of the operation
    """
    timestamp: float
    address: int
    original_bytes: bytes
    new_bytes: bytes
    description: str = ""
    
    def get_timestamp_str(self) -> str:
        """Get formatted timestamp string."""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class AddressTableManager:
    """
    Manages a table of tracked memory addresses.
    
    Provides functionality to add/remove addresses, read/write values,
    and maintain undo history.
    """
    
    def __init__(self, memory_manager: MemoryManager, max_undo_entries: int = 100):
        """
        Initialize AddressTableManager.
        
        Args:
            memory_manager: MemoryManager instance for reading/writing memory.
            max_undo_entries: Maximum number of undo entries to keep.
        """
        self.memory_manager = memory_manager
        self.max_undo_entries = max_undo_entries
        
        # Address table: id -> AddressEntry
        self._addresses: Dict[str, AddressEntry] = {}
        self._lock = threading.Lock()
        
        # Undo history
        self._undo_history: deque[UndoEntry] = deque(maxlen=max_undo_entries)
        
        # Auto-refresh
        self._auto_refresh_enabled = False
        self._auto_refresh_interval = 1.0  # seconds
        self._auto_refresh_thread: Optional[threading.Thread] = None
        self._auto_refresh_stop_event = threading.Event()
        
        logger.info("AddressTableManager initialized")
    
    def add_address(self, address: int, data_type: DataType, 
                   description: str = "", module_name: Optional[str] = None) -> str:
        """
        Add a new address to the table.
        
        Args:
            address: Memory address to track.
            data_type: Data type of the value at this address.
            description: User-provided description.
            module_name: Optional module name for relative addressing.
        
        Returns:
            Unique ID of the created entry.
        
        Raises:
            ValueError: If address or data type is invalid.
        """
        if address < 0:
            raise ValueError(f"Invalid address: {address}")
        
        # Generate unique ID
        entry_id = str(uuid.uuid4())
        
        # Create entry
        entry = AddressEntry(
            id=entry_id,
            address=address,
            data_type=data_type,
            description=description,
            module_name=module_name
        )
        
        # Add to table
        with self._lock:
            self._addresses[entry_id] = entry
        
        logger.info(
            f"Added address entry: ID={entry_id}, "
            f"Address=0x{address:X}, Type={data_type.name}"
        )
        
        return entry_id
    
    def remove_address(self, entry_id: str) -> bool:
        """
        Remove an address from the table.
        
        Args:
            entry_id: ID of the entry to remove.
        
        Returns:
            True if entry was removed, False if not found.
        """
        with self._lock:
            if entry_id in self._addresses:
                entry = self._addresses[entry_id]
                del self._addresses[entry_id]
                logger.info(
                    f"Removed address entry: ID={entry_id}, "
                    f"Address=0x{entry.address:X}"
                )
                return True
            else:
                logger.warning(f"Attempted to remove non-existent entry: {entry_id}")
                return False
    
    def get_address(self, entry_id: str) -> Optional[AddressEntry]:
        """
        Get an address entry by ID.
        
        Args:
            entry_id: ID of the entry to retrieve.
        
        Returns:
            AddressEntry if found, None otherwise.
        """
        with self._lock:
            return self._addresses.get(entry_id)
    
    def get_all_addresses(self) -> List[AddressEntry]:
        """
        Get all address entries.
        
        Returns:
            List of all AddressEntry objects.
        """
        with self._lock:
            return list(self._addresses.values())
    
    def read_value(self, entry_id: str) -> Optional[Any]:
        """
        Read the current value from memory for an address entry.
        
        Updates the entry's last_value and last_read_time on success.
        
        Args:
            entry_id: ID of the entry to read.
        
        Returns:
            The read value, or None if read failed or entry not found.
        """
        with self._lock:
            entry = self._addresses.get(entry_id)
        
        if not entry:
            logger.warning(f"Attempted to read non-existent entry: {entry_id}")
            return None
        
        # Read memory
        data, success = self.memory_manager.read_memory(
            entry.address,
            entry.data_type.size
        )
        
        if not success or len(data) < entry.data_type.size:
            logger.debug(
                f"Failed to read value at 0x{entry.address:X} "
                f"for entry {entry_id}"
            )
            return None
        
        # Unpack value
        try:
            value = ValuePacker.unpack(data, entry.data_type)
            
            # Update entry
            with self._lock:
                entry.last_value = value
                entry.last_read_time = time.time()
            
            logger.debug(
                f"Read value from 0x{entry.address:X}: "
                f"{ValueFormatter.format_decimal(value, entry.data_type)}"
            )
            
            return value
            
        except Exception as e:
            logger.error(
                f"Failed to unpack value at 0x{entry.address:X}: {e}"
            )
            return None
    
    def read_all_values(self) -> Dict[str, Any]:
        """
        Read values for all non-frozen address entries.
        
        Returns:
            Dictionary mapping entry IDs to their read values.
        """
        results = {}
        
        # Get all entries
        with self._lock:
            entries = list(self._addresses.values())
        
        # Read each entry
        for entry in entries:
            if not entry.is_frozen:
                value = self.read_value(entry.id)
                if value is not None:
                    results[entry.id] = value
        
        logger.debug(f"Read {len(results)} values from address table")
        return results
    
    def write_value(self, entry_id: str, value: Any, 
                   create_undo: bool = True) -> bool:
        """
        Write a value to memory for an address entry.
        
        Args:
            entry_id: ID of the entry to write.
            value: Value to write (will be packed according to data type).
            create_undo: Whether to create an undo entry.
        
        Returns:
            True if write succeeded, False otherwise.
        
        Raises:
            ValueError: If value is invalid for the data type.
        """
        with self._lock:
            entry = self._addresses.get(entry_id)
        
        if not entry:
            logger.warning(f"Attempted to write to non-existent entry: {entry_id}")
            return False
        
        # Pack value to bytes
        try:
            new_bytes = ValuePacker.pack(value, entry.data_type)
        except Exception as e:
            logger.error(
                f"Failed to pack value for entry {entry_id}: {e}"
            )
            raise ValueError(f"Invalid value for {entry.data_type.name}: {e}")
        
        # Read original bytes if creating undo entry
        original_bytes = None
        if create_undo:
            data, success = self.memory_manager.read_memory(
                entry.address,
                entry.data_type.size
            )
            if success and len(data) == entry.data_type.size:
                original_bytes = data
        
        # Write to memory
        success = self.memory_manager.write_memory(entry.address, new_bytes)
        
        if not success:
            logger.warning(
                f"Failed to write value to 0x{entry.address:X} "
                f"for entry {entry_id}"
            )
            return False
        
        # Create undo entry
        if create_undo and original_bytes:
            undo_entry = UndoEntry(
                timestamp=time.time(),
                address=entry.address,
                original_bytes=original_bytes,
                new_bytes=new_bytes,
                description=f"{entry.description} (0x{entry.address:X})"
            )
            self._undo_history.append(undo_entry)
            logger.debug(f"Created undo entry for 0x{entry.address:X}")
        
        logger.info(
            f"Wrote value to 0x{entry.address:X}: "
            f"{ValueFormatter.format_decimal(value, entry.data_type)}"
        )
        
        # Update last value
        with self._lock:
            entry.last_value = value
        
        return True
    
    def get_undo_history(self) -> List[UndoEntry]:
        """
        Get the undo history.
        
        Returns:
            List of UndoEntry objects, most recent first.
        """
        return list(reversed(self._undo_history))
    
    def restore_original(self, undo_entry: UndoEntry) -> bool:
        """
        Restore original bytes from an undo entry.
        
        Args:
            undo_entry: UndoEntry to restore from.
        
        Returns:
            True if restore succeeded, False otherwise.
        """
        success = self.memory_manager.write_memory(
            undo_entry.address,
            undo_entry.original_bytes
        )
        
        if success:
            logger.info(
                f"Restored original bytes at 0x{undo_entry.address:X}"
            )
        else:
            logger.warning(
                f"Failed to restore original bytes at 0x{undo_entry.address:X}"
            )
        
        return success
    
    def set_auto_refresh(self, enabled: bool, interval: float = 1.0):
        """
        Enable or disable auto-refresh of address values.
        
        Args:
            enabled: Whether to enable auto-refresh.
            interval: Refresh interval in seconds.
        """
        if enabled and not self._auto_refresh_enabled:
            # Start auto-refresh
            self._auto_refresh_enabled = True
            self._auto_refresh_interval = interval
            self._auto_refresh_stop_event.clear()
            
            self._auto_refresh_thread = threading.Thread(
                target=self._auto_refresh_worker,
                daemon=True
            )
            self._auto_refresh_thread.start()
            
            logger.info(f"Auto-refresh enabled with interval {interval}s")
            
        elif not enabled and self._auto_refresh_enabled:
            # Stop auto-refresh
            self._auto_refresh_enabled = False
            self._auto_refresh_stop_event.set()
            
            if self._auto_refresh_thread:
                self._auto_refresh_thread.join(timeout=2.0)
                self._auto_refresh_thread = None
            
            logger.info("Auto-refresh disabled")
    
    def _auto_refresh_worker(self):
        """Worker thread for auto-refreshing address values."""
        logger.debug("Auto-refresh worker started")
        
        while not self._auto_refresh_stop_event.is_set():
            # Read all values
            self.read_all_values()
            
            # Wait for interval or stop event
            self._auto_refresh_stop_event.wait(self._auto_refresh_interval)
        
        logger.debug("Auto-refresh worker stopped")
    
    def format_value(self, entry_id: str, format_type: str = "decimal") -> Optional[str]:
        """
        Format the value of an address entry for display.
        
        Args:
            entry_id: ID of the entry.
            format_type: Format type: "decimal", "hex", or "float".
        
        Returns:
            Formatted value string, or None if entry not found or no value.
        """
        with self._lock:
            entry = self._addresses.get(entry_id)
        
        if not entry or entry.last_value is None:
            return None
        
        if format_type == "hex":
            return ValueFormatter.format_hex(entry.last_value, entry.data_type)
        elif format_type == "float":
            return ValueFormatter.format_float(entry.last_value, entry.data_type)
        else:  # decimal
            return ValueFormatter.format_decimal(entry.last_value, entry.data_type)
    
    def clear(self):
        """Clear all address entries and undo history."""
        with self._lock:
            self._addresses.clear()
            self._undo_history.clear()
        
        logger.info("Address table cleared")
    
    def __del__(self):
        """Cleanup on deletion."""
        # Stop auto-refresh if running
        if self._auto_refresh_enabled:
            self.set_auto_refresh(False)
