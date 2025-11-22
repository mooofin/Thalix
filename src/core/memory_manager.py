"""
Memory Manager - Windows API abstraction for memory operations.

This module provides a clean interface for reading, writing, and querying
process memory using Windows API functions.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional, Iterator
from enum import IntEnum
import logging

from .process_manager import ProcessHandle

# Windows API constants
ERROR_PARTIAL_COPY = 299

# Memory states
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_FREE = 0x10000

# Memory types
MEM_IMAGE = 0x1000000
MEM_MAPPED = 0x40000
MEM_PRIVATE = 0x20000

# Memory protection flags
PAGE_NOACCESS = 0x01
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100
PAGE_NOCACHE = 0x200
PAGE_WRITECOMBINE = 0x400

logger = logging.getLogger(__name__)


class MemoryState(IntEnum):
    """Memory region state."""
    COMMIT = MEM_COMMIT
    RESERVE = MEM_RESERVE
    FREE = MEM_FREE


class MemoryType(IntEnum):
    """Memory region type."""
    IMAGE = MEM_IMAGE
    MAPPED = MEM_MAPPED
    PRIVATE = MEM_PRIVATE


# Windows API structures
class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    """Structure returned by VirtualQueryEx."""
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wintypes.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wintypes.DWORD),
        ('Protect', wintypes.DWORD),
        ('Type', wintypes.DWORD)
    ]


@dataclass
class MemoryRegion:
    """Information about a memory region."""
    base_address: int
    size: int
    state: MemoryState
    protect: int
    type: int
    
    @property
    def is_readable(self) -> bool:
        """Check if region is readable."""
        if self.state != MemoryState.COMMIT:
            return False
        if self.protect & PAGE_NOACCESS:
            return False
        if self.protect & PAGE_GUARD:
            return False
        # Check for any read permission
        readable_flags = (
            PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
            PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        )
        return bool(self.protect & readable_flags)
    
    @property
    def is_writable(self) -> bool:
        """Check if region is writable."""
        if self.state != MemoryState.COMMIT:
            return False
        if self.protect & PAGE_NOACCESS:
            return False
        if self.protect & PAGE_GUARD:
            return False
        # Check for write permission
        writable_flags = (
            PAGE_READWRITE | PAGE_WRITECOPY |
            PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        )
        return bool(self.protect & writable_flags)
    
    @property
    def is_executable(self) -> bool:
        """Check if region is executable."""
        if self.state != MemoryState.COMMIT:
            return False
        # Check for execute permission
        executable_flags = (
            PAGE_EXECUTE | PAGE_EXECUTE_READ |
            PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        )
        return bool(self.protect & executable_flags)
    
    @property
    def is_guarded(self) -> bool:
        """Check if region has guard page protection."""
        return bool(self.protect & PAGE_GUARD)
    
    def get_protection_string(self) -> str:
        """Get human-readable protection string."""
        if self.state != MemoryState.COMMIT:
            return "---"
        
        parts = []
        if self.is_readable:
            parts.append("R")
        if self.is_writable:
            parts.append("W")
        if self.is_executable:
            parts.append("X")
        if self.is_guarded:
            parts.append("G")
        
        return "".join(parts) if parts else "---"


class MemoryManager:
    """
    Manages memory read/write operations for a process.
    
    Provides methods to read and write process memory, query memory regions,
    and enumerate the entire memory layout.
    """
    
    def __init__(self, process_handle: ProcessHandle):
        """
        Initialize MemoryManager.
        
        Args:
            process_handle: Handle to the target process.
        """
        self.process_handle = process_handle
        self.kernel32 = ctypes.windll.kernel32
        logger.info(f"MemoryManager initialized for PID {process_handle.pid}")
    
    def read_memory(self, address: int, size: int) -> tuple[bytes, bool]:
        """
        Read memory from the process.
        
        Args:
            address: Memory address to read from.
            size: Number of bytes to read.
        
        Returns:
            Tuple of (data, success). If partial read occurs, returns partial
            data with success=False. If complete failure, returns empty bytes
            with success=False.
        
        Raises:
            ValueError: If address or size is invalid.
        """
        if address < 0:
            raise ValueError(f"Invalid address: {address}")
        if size <= 0:
            raise ValueError(f"Invalid size: {size}")
        
        if not self.process_handle.is_valid():
            logger.error("Attempt to read with invalid process handle")
            return (b"", False)
        
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        
        # Convert numpy integers to Python int
        address = int(address)
        
        result = self.kernel32.ReadProcessMemory(
            self.process_handle.handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        
        if result:
            # Successful read
            logger.debug(f"Read {bytes_read.value} bytes from 0x{address:X}")
            return (buffer.raw[:bytes_read.value], True)
        else:
            error_code = ctypes.get_last_error()
            
            if error_code == ERROR_PARTIAL_COPY and bytes_read.value > 0:
                # Partial read - return what we got
                logger.debug(
                    f"Partial read: {bytes_read.value}/{size} bytes from 0x{address:X}"
                )
                return (buffer.raw[:bytes_read.value], False)
            else:
                # Complete failure
                logger.debug(
                    f"Read failed at 0x{address:X}: Error {error_code}"
                )
                return (b"", False)
    
    def write_memory(self, address: int, data: bytes) -> bool:
        """
        Write memory to the process.
        
        Args:
            address: Memory address to write to.
            data: Bytes to write.
        
        Returns:
            True if write succeeded, False otherwise.
        
        Raises:
            ValueError: If address is invalid or data is empty.
        """
        if address < 0:
            raise ValueError(f"Invalid address: {address}")
        if not data:
            raise ValueError("Data cannot be empty")
        
        if not self.process_handle.is_valid():
            logger.error("Attempt to write with invalid process handle")
            return False
        
        size = len(data)
        bytes_written = ctypes.c_size_t(0)
        
        # Convert numpy integers to Python int
        address = int(address)
        
        result = self.kernel32.WriteProcessMemory(
            self.process_handle.handle,
            ctypes.c_void_p(address),
            data,
            size,
            ctypes.byref(bytes_written)
        )
        
        if result and bytes_written.value == size:
            logger.debug(f"Wrote {bytes_written.value} bytes to 0x{address:X}")
            return True
        else:
            error_code = ctypes.get_last_error()
            logger.warning(
                f"Write failed at 0x{address:X}: "
                f"Wrote {bytes_written.value}/{size} bytes, Error {error_code}"
            )
            return False
    
    def query_memory_region(self, address: int) -> Optional[MemoryRegion]:
        """
        Query information about a memory region.
        
        Args:
            address: Address within the region to query.
        
        Returns:
            MemoryRegion object or None if query fails.
        """
        if not self.process_handle.is_valid():
            logger.error("Attempt to query with invalid process handle")
            return None
        
        mbi = MEMORY_BASIC_INFORMATION()
        
        # Convert numpy integers to Python int
        address = int(address)
        
        result = self.kernel32.VirtualQueryEx(
            self.process_handle.handle,
            ctypes.c_void_p(address),
            ctypes.byref(mbi),
            ctypes.sizeof(mbi)
        )
        
        if result == 0:
            error_code = ctypes.get_last_error()
            logger.debug(f"VirtualQueryEx failed at 0x{address:X}: Error {error_code}")
            return None
        
        return MemoryRegion(
            base_address=mbi.BaseAddress,
            size=mbi.RegionSize,
            state=MemoryState(mbi.State),
            protect=mbi.Protect,
            type=mbi.Type
        )
    
    def enumerate_memory_regions(self) -> Iterator[MemoryRegion]:
        """
        Enumerate all memory regions in the process.
        
        Iterates from address 0 to the maximum address space, yielding
        MemoryRegion objects for each region.
        
        Yields:
            MemoryRegion objects for each region in the process.
        """
        if not self.process_handle.is_valid():
            logger.error("Attempt to enumerate with invalid process handle")
            return
        
        import sys
        
        # Determine maximum address based on architecture
        if sys.maxsize > 2**32:
            # 64-bit
            max_address = 0x7FFFFFFFFFFF  # Typical user-mode limit on 64-bit Windows
        else:
            # 32-bit
            max_address = 0x7FFFFFFF  # Typical user-mode limit on 32-bit Windows
        
        address = 0
        region_count = 0
        
        while address < max_address:
            mbi = MEMORY_BASIC_INFORMATION()
            result = self.kernel32.VirtualQueryEx(
                self.process_handle.handle,
                ctypes.c_void_p(address),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi)
            )
            
            if result == 0:
                # End of address space or error
                break
            
            # Convert BaseAddress from c_void_p to int
            base_addr = mbi.BaseAddress if isinstance(mbi.BaseAddress, int) else ctypes.cast(mbi.BaseAddress, ctypes.c_void_p).value
            if base_addr is None:
                base_addr = address
            
            region = MemoryRegion(
                base_address=base_addr,
                size=mbi.RegionSize,
                state=MemoryState(mbi.State),
                protect=mbi.Protect,
                type=mbi.Type
            )
            
            yield region
            region_count += 1
            
            # Move to next region
            address = base_addr + mbi.RegionSize
            
            # Safety check to prevent infinite loop
            if mbi.RegionSize == 0:
                address += 0x1000  # Move forward by page size
        
        logger.info(f"Enumerated {region_count} memory regions")
