"""
Memory Editor Module - Lite Cheat Engine functionality
For educational and single-player use only!
"""

import ctypes
from ctypes import wintypes
import struct
import json
import os
import logging
from typing import Optional, List, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Windows API constants
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_CREATE_THREAD = 0x0002

# Memory protection constants
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000

# Configuration constants
MEMORY_PAGE_SIZE = 4096  # Windows memory page size
DEFAULT_SCAN_START = 0x10000  # Skip null page
DEFAULT_SCAN_END = 0x7FFFFFFF  # 2GB limit for 32-bit compat
FREEZE_UPDATE_HZ = 20  # 20 updates per second
FREEZE_UPDATE_INTERVAL = 1.0 / FREEZE_UPDATE_HZ  # 0.05 seconds

# Critical system processes that should never be modified
CRITICAL_PROCESSES = {'system', 'csrss.exe', 'smss.exe', 'wininit.exe', 
                      'services.exe', 'lsass.exe', 'winlogon.exe'}

class MemoryEditor:
    """Handles process memory reading and writing with security safeguards"""
    
    def __init__(self, pid: Optional[int] = None):
        self.pid = pid
        self.process_handle = None
        
        # Windows API functions
        self.kernel32 = ctypes.windll.kernel32
        self.OpenProcess = self.kernel32.OpenProcess
        self.ReadProcessMemory = self.kernel32.ReadProcessMemory
        self.WriteProcessMemory = self.kernel32.WriteProcessMemory
        self.VirtualProtectEx = self.kernel32.VirtualProtectEx
        self.CloseHandle = self.kernel32.CloseHandle
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.close_process()
        return False
    
    def __del__(self):
        """Destructor - ensure handle is closed"""
        try:
            self.close_process()
        except Exception:
            pass
    
    def _is_system_critical_process(self, pid: int) -> bool:
        """Check if process is critical system process that should not be modified"""
        try:
            import psutil
            if pid < 10:  # Very low PIDs are typically system processes
                return True
            
            proc = psutil.Process(pid)
            process_name = proc.name().lower()
            
            return process_name in CRITICAL_PROCESSES
        except Exception as e:
            logger.warning(f"Could not verify process safety for PID {pid}: {e}")
            # Be cautious - if we can't verify, treat as critical
            return True
        
    def open_process(self, pid: int) -> bool:
        """Open process for memory access with security validation"""
        # Validate process safety
        if self._is_system_critical_process(pid):
            logger.error(f"Refusing to open critical system process PID {pid}")
            raise PermissionError("Cannot open critical system process")
        
        self.pid = pid
        # Use least privilege - only request needed permissions
        access_flags = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
        self.process_handle = self.OpenProcess(access_flags, False, pid)
        
        success = self.process_handle is not None and self.process_handle != 0
        if success:
            logger.info(f"Successfully opened process PID {pid}")
        else:
            logger.error(f"Failed to open process PID {pid}")
        
        return success
        
    def close_process(self):
        """Close process handle"""
        if self.process_handle:
            try:
                self.CloseHandle(self.process_handle)
                logger.debug(f"Closed process handle for PID {self.pid}")
            except Exception as e:
                logger.error(f"Error closing process handle: {e}")
            finally:
                self.process_handle = None
            
    def read_memory(self, address: int, size: int) -> Optional[bytes]:
        """Read memory from process with validation"""
        if not self.process_handle:
            logger.warning("Attempted to read memory without open process handle")
            return None
        
        if address < 0x1000:
            logger.warning(f"Attempted to read from invalid low address: {hex(address)}")
            return None
            
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        
        try:
            success = self.ReadProcessMemory(
                self.process_handle,
                ctypes.c_void_p(address),
                buffer,
                size,
                ctypes.byref(bytes_read)
            )
            
            if success and bytes_read.value == size:
                return buffer.raw
        except (OSError, ctypes.WinError) as e:
            logger.debug(f"Memory read failed at {hex(address)}: {e}")
        
        return None
        
    def write_memory(self, address: int, data: bytes) -> bool:
        """Write memory to process with validation"""
        if not self.process_handle:
            logger.warning("Attempted to write memory without open process handle")
            return False
        
        if address < 0x1000:
            logger.warning(f"Attempted to write to invalid low address: {hex(address)}")
            return False
            
        bytes_written = ctypes.c_size_t(0)
        buffer = ctypes.create_string_buffer(data)
        
        try:
            success = self.WriteProcessMemory(
                self.process_handle,
                ctypes.c_void_p(address),
                buffer,
                len(data),
                ctypes.byref(bytes_written)
            )
            
            return success and bytes_written.value == len(data)
        except (OSError, ctypes.WinError) as e:
            logger.error(f"Memory write failed at {hex(address)}: {e}")
            return False
        
    def read_int(self, address: int) -> Optional[int]:
        """Read 4-byte integer with validation"""
        if not isinstance(address, int) or address < 0:
            raise TypeError(f"Address must be non-negative integer, got {type(address)}")
        
        data = self.read_memory(address, 4)
        if data:
            return struct.unpack('<i', data)[0]
        return None
        
    def write_int(self, address: int, value: int) -> bool:
        """Write 4-byte integer with validation"""
        if not isinstance(value, int):
            raise TypeError(f"Value must be int, got {type(value)}")
        
        if not (-(2**31) <= value < 2**31):
            raise ValueError(f"Value {value} out of range for signed 32-bit int")
        
        if address < 0x1000:
            raise ValueError(f"Invalid address {hex(address)} - too low")
        
        data = struct.pack('<i', value)
        return self.write_memory(address, data)
        
    def read_float(self, address: int) -> Optional[float]:
        """Read 4-byte float"""
        data = self.read_memory(address, 4)
        if data:
            return struct.unpack('<f', data)[0]
        return None
        
    def write_float(self, address: int, value: float) -> bool:
        """Write 4-byte float with validation"""
        if not isinstance(value, (int, float)):
            raise TypeError(f"Value must be numeric, got {type(value)}")
        
        data = struct.pack('<f', float(value))
        return self.write_memory(address, data)
        
    def read_long(self, address: int) -> Optional[int]:
        """Read 8-byte long"""
        data = self.read_memory(address, 8)
        if data:
            return struct.unpack('<q', data)[0]
        return None
        
    def write_long(self, address: int, value: int) -> bool:
        """Write 8-byte long with validation"""
        if not isinstance(value, int):
            raise TypeError(f"Value must be int, got {type(value)}")
        
        if not (-(2**63) <= value < 2**63):
            raise ValueError(f"Value {value} out of range for signed 64-bit long")
        
        data = struct.pack('<q', value)
        return self.write_memory(address, data)
        
    def read_double(self, address: int) -> Optional[float]:
        """Read 8-byte double"""
        data = self.read_memory(address, 8)
        if data:
            return struct.unpack('<d', data)[0]
        return None
        
    def write_double(self, address: int, value: float) -> bool:
        """Write 8-byte double with validation"""
        if not isinstance(value, (int, float)):
            raise TypeError(f"Value must be numeric, got {type(value)}")
        
        data = struct.pack('<d', float(value))
        return self.write_memory(address, data)
        
    def read_bytes(self, address: int, length: int) -> Optional[bytes]:
        """Read arbitrary bytes"""
        return self.read_memory(address, length)
        
    def write_bytes(self, address: int, data: bytes) -> bool:
        """Write arbitrary bytes"""
        return self.write_memory(address, data)
        
    def scan_memory(self, value, value_type: str = 'int', 
                    start_address: int = DEFAULT_SCAN_START, 
                    end_address: int = DEFAULT_SCAN_END) -> List[int]:
        """
        Scan memory for a specific value
        
        Args:
            value: Value to search for
            value_type: Type of value ('int', 'float', 'long', 'double', 'bytes')
            start_address: Starting address for scan
            end_address: Ending address for scan
            
        Returns:
            List of addresses where value was found
        """
        results = []
        current_address = start_address
        
        # Determine scan parameters based on type
        try:
            if value_type == 'int':
                search_bytes = struct.pack('<i', value)
                step = 4
            elif value_type == 'float':
                search_bytes = struct.pack('<f', value)
                step = 4
            elif value_type == 'long':
                search_bytes = struct.pack('<q', value)
                step = 8
            elif value_type == 'double':
                search_bytes = struct.pack('<d', value)
                step = 8
            elif value_type == 'bytes':
                search_bytes = value
                step = len(value)
            else:
                logger.error(f"Invalid value type: {value_type}")
                return results
        except struct.error as e:
            logger.error(f"Failed to pack value {value} as {value_type}: {e}")
            return results
            
        # Scan in chunks for performance
        chunk_size = MEMORY_PAGE_SIZE
        
        logger.info(f"Scanning memory for {value_type} value from {hex(start_address)} to {hex(end_address)}")
        
        while current_address < end_address:
            try:
                data = self.read_memory(current_address, chunk_size)
                if data:
                    # Search for value in chunk
                    offset = 0
                    while True:
                        offset = data.find(search_bytes, offset)
                        if offset == -1:
                            break
                        results.append(current_address + offset)
                        offset += step
                        
                current_address += chunk_size
            except (OSError, ctypes.WinError) as e:
                logger.debug(f"Memory scan error at {hex(current_address)}: {e}")
                current_address += chunk_size
                continue
        
        logger.info(f"Memory scan complete: found {len(results)} matches")
        return results
        
    def read_pointer_chain(self, base_address: int, offsets: List[int]) -> Optional[int]:
        """
        Read a pointer chain (for multi-level pointers)
        Example: [[Game.exe+123456]+10]+20
        
        Args:
            base_address: Starting address
            offsets: List of offsets to follow
            
        Returns:
            Final address or None if chain is broken
        """
        current_address = base_address
        
        for i, offset in enumerate(offsets[:-1]):
            # Read pointer at current address
            pointer = self.read_long(current_address + offset)
            if pointer is None:
                logger.debug(f"Pointer chain broken at step {i}")
                return None
            current_address = pointer
            
        # Apply final offset
        return current_address + offsets[-1]


class CheatTable:
    """Handle cheat table files with JSON format"""
    
    def __init__(self):
        self.entries = []
        
    def add_entry(self, name: str, address: int, value_type: str, 
                  description: str = "", offsets: Optional[List[int]] = None) -> dict:
        """
        Add a cheat entry
        
        Args:
            name: Entry name
            address: Memory address
            value_type: Type of value ('int', 'float', 'long', 'double')
            description: Optional description
            offsets: Optional list of pointer offsets
            
        Returns:
            The created entry dictionary
        """
        entry = {
            'name': name,
            'address': address,
            'type': value_type,
            'description': description,
            'offsets': offsets or [],
            'frozen': False,
            'frozen_value': None
        }
        self.entries.append(entry)
        logger.info(f"Added cheat entry: {name} at {hex(address)}")
        return entry
        
    def remove_entry(self, index: int) -> bool:
        """
        Remove an entry by index
        
        Returns:
            True if entry was removed, False otherwise
        """
        if 0 <= index < len(self.entries):
            removed = self.entries.pop(index)
            logger.info(f"Removed cheat entry: {removed['name']}")
            return True
        logger.warning(f"Invalid entry index: {index}")
        return False
            
    def save_to_file(self, filename: str) -> bool:
        """
        Save cheat table to JSON file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.entries, f, indent=2)
            logger.info(f"Saved cheat table to {filename}")
            return True
        except IOError as e:
            logger.error(f"Failed to save cheat table: {e}")
            return False
            
    def load_from_file(self, filename: str) -> bool:
        """
        Load cheat table from JSON file
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(filename):
            logger.warning(f"Cheat table file not found: {filename}")
            return False
        
        try:
            with open(filename, 'r') as f:
                self.entries = json.load(f)
            logger.info(f"Loaded {len(self.entries)} entries from {filename}")
            return True
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load cheat table: {e}")
            return False
        
    def get_entry(self, index: int) -> Optional[dict]:
        """Get entry by index"""
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None


class MemoryFreezer:
    """Keeps memory values frozen at specified values with thread safety"""
    
    def __init__(self, memory_editor: MemoryEditor):
        self.memory_editor = memory_editor
        self.frozen_addresses = {}  # address: (value, type)
        self._running = False
        self._lock = __import__('threading').Lock()
        
    @property
    def running(self) -> bool:
        """Thread-safe running state check"""
        with self._lock:
            return self._running
    
    @running.setter
    def running(self, value: bool):
        """Thread-safe running state setter"""
        with self._lock:
            self._running = value
        
    def add_frozen_address(self, address: int, value, value_type: str):
        """Add an address to freeze"""
        with self._lock:
            self.frozen_addresses[address] = (value, value_type)
            logger.info(f"Added frozen address: {hex(address)} = {value} ({value_type})")
        
    def remove_frozen_address(self, address: int):
        """Remove frozen address"""
        with self._lock:
            if address in self.frozen_addresses:
                del self.frozen_addresses[address]
                logger.info(f"Removed frozen address: {hex(address)}")
            
    def freeze_loop(self):
        """Keep writing frozen values (run in thread)"""
        import time
        
        logger.info("Memory freezer started")
        
        while self.running:
            with self._lock:
                addresses_copy = dict(self.frozen_addresses)
            
            for address, (value, value_type) in addresses_copy.items():
                try:
                    if value_type == 'int':
                        self.memory_editor.write_int(address, value)
                    elif value_type == 'float':
                        self.memory_editor.write_float(address, value)
                    elif value_type == 'long':
                        self.memory_editor.write_long(address, value)
                    elif value_type == 'double':
                        self.memory_editor.write_double(address, value)
                except Exception as e:
                    logger.debug(f"Freeze error at {hex(address)}: {e}")
            
            time.sleep(FREEZE_UPDATE_INTERVAL)
        
        logger.info("Memory freezer stopped")
            
    def start(self):
        """Start freezing"""
        if not self.running:
            self.running = True
            import threading
            threading.Thread(target=self.freeze_loop, daemon=True).start()
            logger.info("Starting memory freezer")
            
    def stop(self):
        """Stop freezing"""
        if self.running:
            self.running = False
            logger.info("Stopping memory freezer")
