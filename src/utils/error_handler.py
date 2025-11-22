"""
Error Handler - Utility for translating Windows error codes and providing actionable guidance.

This module provides centralized error handling functionality, including translation
of Windows error codes to user-friendly messages and actionable guidance for common errors.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Common Windows error codes
ERROR_SUCCESS = 0
ERROR_ACCESS_DENIED = 5
ERROR_INVALID_HANDLE = 6
ERROR_NOT_ENOUGH_MEMORY = 8
ERROR_INVALID_PARAMETER = 87
ERROR_PARTIAL_COPY = 299
ERROR_NOACCESS = 998


@dataclass
class ErrorInfo:
    """
    Information about an error with actionable guidance.
    
    Attributes:
        error_code: The Windows error code.
        message: User-friendly error message.
        suggested_action: Actionable guidance for resolving the error.
        requires_elevation: Whether the error can be resolved by running as administrator.
    """
    error_code: int
    message: str
    suggested_action: str
    requires_elevation: bool


class ErrorHandler:
    """
    Utility class for handling Windows API errors.
    
    Provides methods to translate error codes to user-friendly messages
    and generate actionable guidance for common error scenarios.
    """
    
    # Error message mappings for common errors
    ERROR_MESSAGES = {
        ERROR_ACCESS_DENIED: "Access denied",
        ERROR_INVALID_HANDLE: "Invalid handle",
        ERROR_NOT_ENOUGH_MEMORY: "Not enough memory",
        ERROR_INVALID_PARAMETER: "Invalid parameter",
        ERROR_PARTIAL_COPY: "Partial copy",
        ERROR_NOACCESS: "Invalid access to memory location",
    }
    
    @staticmethod
    def get_win32_error_message(error_code: int) -> str:
        """
        Translate a Windows error code to a human-readable message.
        
        Uses FormatMessageW to retrieve the system error message for the given
        error code. Falls back to a generic message if the system message cannot
        be retrieved.
        
        Args:
            error_code: Windows error code from GetLastError().
        
        Returns:
            Human-readable error message.
        """
        if error_code == ERROR_SUCCESS:
            return "Success"
        
        # Check if we have a predefined message
        if error_code in ErrorHandler.ERROR_MESSAGES:
            predefined_msg = ErrorHandler.ERROR_MESSAGES[error_code]
        else:
            predefined_msg = None
        
        # Try to get system error message
        try:
            message_buffer = ctypes.create_unicode_buffer(512)
            result = ctypes.windll.kernel32.FormatMessageW(
                0x00001000,  # FORMAT_MESSAGE_FROM_SYSTEM
                None,
                error_code,
                0,  # Default language
                message_buffer,
                512,
                None
            )
            
            if result > 0:
                system_msg = message_buffer.value.strip()
                if system_msg:
                    return system_msg
        except Exception as e:
            logger.debug(f"Failed to get system error message for code {error_code}: {e}")
        
        # Fall back to predefined message or generic message
        if predefined_msg:
            return f"{predefined_msg} (Error {error_code})"
        else:
            return f"Unknown error (Error {error_code})"
    
    @staticmethod
    def handle_process_open_error(error_code: int, pid: int) -> ErrorInfo:
        """
        Handle errors from OpenProcess and provide actionable guidance.
        
        Analyzes the error code and provides specific guidance for resolving
        process access issues.
        
        Args:
            error_code: Windows error code from GetLastError().
            pid: Process ID that failed to open.
        
        Returns:
            ErrorInfo with detailed error information and suggested actions.
        """
        base_message = ErrorHandler.get_win32_error_message(error_code)
        
        if error_code == ERROR_ACCESS_DENIED:
            message = f"Access denied when opening process {pid}"
            suggested_action = (
                "The process may require administrator privileges. "
                "Try running this application as administrator. "
                "Some system processes and protected processes cannot be accessed even with admin rights."
            )
            requires_elevation = True
        
        elif error_code == ERROR_INVALID_HANDLE:
            message = f"Invalid handle for process {pid}"
            suggested_action = (
                "The process may have terminated or the process ID is invalid. "
                "Refresh the process list and try again."
            )
            requires_elevation = False
        
        elif error_code == ERROR_INVALID_PARAMETER:
            message = f"Invalid parameter when opening process {pid}"
            suggested_action = (
                "The process ID may be invalid or zero. "
                "Ensure you are selecting a valid running process."
            )
            requires_elevation = False
        
        else:
            message = f"Failed to open process {pid}: {base_message}"
            suggested_action = (
                "An unexpected error occurred. "
                "The process may have terminated, or there may be system restrictions. "
                "Check the logs for more details."
            )
            requires_elevation = False
        
        logger.error(f"Process open error: {message} (Error {error_code})")
        
        return ErrorInfo(
            error_code=error_code,
            message=message,
            suggested_action=suggested_action,
            requires_elevation=requires_elevation
        )
    
    @staticmethod
    def handle_memory_read_error(
        error_code: int,
        address: int,
        size: int,
        region_protect: Optional[int] = None
    ) -> ErrorInfo:
        """
        Handle errors from ReadProcessMemory and provide actionable guidance.
        
        Analyzes the error code and memory region protection to provide specific
        guidance for resolving memory read issues.
        
        Args:
            error_code: Windows error code from GetLastError().
            address: Memory address that failed to be read.
            size: Number of bytes requested.
            region_protect: Optional memory protection flags for the region.
        
        Returns:
            ErrorInfo with detailed error information and suggested actions.
        """
        base_message = ErrorHandler.get_win32_error_message(error_code)
        
        if error_code == ERROR_PARTIAL_COPY:
            message = f"Partial read at address 0x{address:X}"
            suggested_action = (
                "Only part of the requested memory could be read. "
                "The memory region may have changed protection or been freed. "
                "Try reading a smaller chunk or refresh the memory regions."
            )
            requires_elevation = False
        
        elif error_code == ERROR_NOACCESS:
            message = f"Cannot access memory at address 0x{address:X}"
            
            if region_protect is not None:
                from ..core.memory_manager import PAGE_NOACCESS, PAGE_GUARD
                
                if region_protect & PAGE_NOACCESS:
                    suggested_action = (
                        "The memory region has PAGE_NOACCESS protection and cannot be read. "
                        "This is a protected or unmapped region."
                    )
                elif region_protect & PAGE_GUARD:
                    suggested_action = (
                        "The memory region has PAGE_GUARD protection. "
                        "Reading this region may trigger an exception in the target process."
                    )
                else:
                    suggested_action = (
                        "The memory address is not accessible. "
                        "The region may have been freed or protection changed."
                    )
            else:
                suggested_action = (
                    "The memory address is not accessible. "
                    "The region may be unmapped, freed, or have restrictive protection. "
                    "Refresh the memory regions to see current state."
                )
            requires_elevation = False
        
        elif error_code == ERROR_INVALID_HANDLE:
            message = "Invalid process handle"
            suggested_action = (
                "The process handle is invalid. "
                "The process may have terminated. "
                "Reattach to the process."
            )
            requires_elevation = False
        
        else:
            message = f"Failed to read {size} bytes from address 0x{address:X}: {base_message}"
            suggested_action = (
                "An unexpected error occurred during memory read. "
                "The process may have terminated or the memory region may be inaccessible. "
                "Check the logs for more details."
            )
            requires_elevation = False
        
        logger.warning(f"Memory read error: {message} (Error {error_code})")
        
        return ErrorInfo(
            error_code=error_code,
            message=message,
            suggested_action=suggested_action,
            requires_elevation=requires_elevation
        )
    
    @staticmethod
    def handle_memory_write_error(
        error_code: int,
        address: int,
        size: int,
        region_protect: Optional[int] = None
    ) -> ErrorInfo:
        """
        Handle errors from WriteProcessMemory and provide actionable guidance.
        
        Analyzes the error code and memory region protection to provide specific
        guidance for resolving memory write issues.
        
        Args:
            error_code: Windows error code from GetLastError().
            address: Memory address that failed to be written.
            size: Number of bytes attempted to write.
            region_protect: Optional memory protection flags for the region.
        
        Returns:
            ErrorInfo with detailed error information and suggested actions.
        """
        base_message = ErrorHandler.get_win32_error_message(error_code)
        
        if error_code == ERROR_PARTIAL_COPY:
            message = f"Partial write at address 0x{address:X}"
            suggested_action = (
                "Only part of the requested memory could be written. "
                "The memory region may have changed protection or been freed. "
                "Try writing a smaller chunk or refresh the memory regions."
            )
            requires_elevation = False
        
        elif error_code == ERROR_NOACCESS:
            message = f"Cannot write to memory at address 0x{address:X}"
            
            if region_protect is not None:
                from ..core.memory_manager import (
                    PAGE_NOACCESS, PAGE_GUARD, PAGE_READONLY,
                    PAGE_EXECUTE, PAGE_EXECUTE_READ
                )
                
                if region_protect & PAGE_NOACCESS:
                    suggested_action = (
                        "The memory region has PAGE_NOACCESS protection and cannot be written. "
                        "This is a protected or unmapped region."
                    )
                elif region_protect & PAGE_GUARD:
                    suggested_action = (
                        "The memory region has PAGE_GUARD protection. "
                        "Writing to this region may trigger an exception in the target process."
                    )
                elif region_protect in (PAGE_READONLY, PAGE_EXECUTE, PAGE_EXECUTE_READ):
                    suggested_action = (
                        "The memory region is read-only or execute-only. "
                        "You cannot write to this region without changing its protection. "
                        "Use VirtualProtectEx to change protection (advanced operation)."
                    )
                else:
                    suggested_action = (
                        "The memory address is not writable. "
                        "The region may have been freed or protection changed."
                    )
            else:
                suggested_action = (
                    "The memory address is not writable. "
                    "The region may be read-only, unmapped, or have restrictive protection. "
                    "Refresh the memory regions to see current state."
                )
            requires_elevation = False
        
        elif error_code == ERROR_INVALID_HANDLE:
            message = "Invalid process handle"
            suggested_action = (
                "The process handle is invalid. "
                "The process may have terminated. "
                "Reattach to the process."
            )
            requires_elevation = False
        
        elif error_code == ERROR_ACCESS_DENIED:
            message = f"Access denied when writing to address 0x{address:X}"
            suggested_action = (
                "Write access was denied. "
                "The memory region may be protected by the operating system or anti-cheat software. "
                "Some regions cannot be written even with administrator privileges."
            )
            requires_elevation = True
        
        else:
            message = f"Failed to write {size} bytes to address 0x{address:X}: {base_message}"
            suggested_action = (
                "An unexpected error occurred during memory write. "
                "The process may have terminated or the memory region may be protected. "
                "Check the logs for more details."
            )
            requires_elevation = False
        
        logger.warning(f"Memory write error: {message} (Error {error_code})")
        
        return ErrorInfo(
            error_code=error_code,
            message=message,
            suggested_action=suggested_action,
            requires_elevation=requires_elevation
        )
