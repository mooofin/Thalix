"""
Custom exceptions for the Memory Editor.

This module defines all custom exception classes used throughout the application
for error handling and reporting.
"""


class MemoryEditorException(Exception):
    """
    Base exception class for all Memory Editor exceptions.
    
    All custom exceptions in the Memory Editor should inherit from this class
    to allow for centralized exception handling.
    """
    pass


class ProcessAccessException(MemoryEditorException):
    """
    Exception raised when process access fails.
    
    This exception is raised when OpenProcess or similar operations fail,
    typically due to insufficient privileges or invalid process ID.
    
    Attributes:
        pid: The process ID that failed to be accessed.
        error_code: The Windows error code from GetLastError().
    """
    
    def __init__(self, pid: int, error_code: int, message: str = None):
        """
        Initialize ProcessAccessException.
        
        Args:
            pid: Process ID that failed to be accessed.
            error_code: Windows error code from GetLastError().
            message: Optional custom error message.
        """
        self.pid = pid
        self.error_code = error_code
        
        if message is None:
            message = f"Failed to access process {pid}: Error code {error_code}"
        
        super().__init__(message)


class MemoryReadException(MemoryEditorException):
    """
    Exception raised when memory read operation fails.
    
    This exception is raised when ReadProcessMemory fails to read the requested
    memory region.
    
    Attributes:
        address: The memory address that failed to be read.
        size: The number of bytes that were requested to be read.
        error_code: The Windows error code from GetLastError().
    """
    
    def __init__(self, address: int, size: int, error_code: int, message: str = None):
        """
        Initialize MemoryReadException.
        
        Args:
            address: Memory address that failed to be read.
            size: Number of bytes requested.
            error_code: Windows error code from GetLastError().
            message: Optional custom error message.
        """
        self.address = address
        self.size = size
        self.error_code = error_code
        
        if message is None:
            message = (
                f"Failed to read {size} bytes from address 0x{address:X}: "
                f"Error code {error_code}"
            )
        
        super().__init__(message)


class MemoryWriteException(MemoryEditorException):
    """
    Exception raised when memory write operation fails.
    
    This exception is raised when WriteProcessMemory fails to write to the
    requested memory region.
    
    Attributes:
        address: The memory address that failed to be written.
        data: The bytes that were attempted to be written.
        error_code: The Windows error code from GetLastError().
    """
    
    def __init__(self, address: int, data: bytes, error_code: int, message: str = None):
        """
        Initialize MemoryWriteException.
        
        Args:
            address: Memory address that failed to be written.
            data: Bytes that were attempted to be written.
            error_code: Windows error code from GetLastError().
            message: Optional custom error message.
        """
        self.address = address
        self.data = data
        self.error_code = error_code
        
        if message is None:
            message = (
                f"Failed to write {len(data)} bytes to address 0x{address:X}: "
                f"Error code {error_code}"
            )
        
        super().__init__(message)


class ArchitectureMismatchException(MemoryEditorException):
    """
    Exception raised when tool and process architectures don't match.
    
    This exception is raised when attempting to access a process with a
    different architecture (e.g., 32-bit tool accessing 64-bit process).
    
    Attributes:
        tool_arch: The architecture of the Memory Editor tool ("32-bit" or "64-bit").
        process_arch: The architecture of the target process ("32-bit" or "64-bit").
    """
    
    def __init__(self, tool_arch: str, process_arch: str, message: str = None):
        """
        Initialize ArchitectureMismatchException.
        
        Args:
            tool_arch: Architecture of the tool ("32-bit" or "64-bit").
            process_arch: Architecture of the process ("32-bit" or "64-bit").
            message: Optional custom error message.
        """
        self.tool_arch = tool_arch
        self.process_arch = process_arch
        
        if message is None:
            message = (
                f"Architecture mismatch: Tool is {tool_arch} but process is {process_arch}. "
                f"Memory operations may be unreliable. Please use the {process_arch} build."
            )
        
        super().__init__(message)
