"""
Process Manager - Windows API abstraction for process enumeration and attachment.

This module provides a clean interface for interacting with Windows processes,
including enumeration, module inspection, and process handle management.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import List, Optional
import logging

# Windows API constants
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = -1

# Process access rights
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Error codes
ERROR_NO_MORE_FILES = 18
ERROR_ACCESS_DENIED = 5
ERROR_INVALID_HANDLE = 6

logger = logging.getLogger(__name__)


# Windows API structures
class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', ctypes.c_char * 260)
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('th32ModuleID', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('GlblcntUsage', wintypes.DWORD),
        ('ProccntUsage', wintypes.DWORD),
        ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
        ('modBaseSize', wintypes.DWORD),
        ('hModule', wintypes.HMODULE),
        ('szModule', ctypes.c_char * 256),
        ('szExePath', ctypes.c_char * 260)
    ]


@dataclass
class ProcessInfo:
    """Information about a Windows process."""
    pid: int
    name: str
    exe_path: str
    main_module_base: int
    main_module_size: int


@dataclass
class ModuleInfo:
    """Information about a process module."""
    name: str
    base_address: int
    size: int
    path: str


@dataclass
class ArchitectureInfo:
    """Architecture information for process and tool."""
    tool_is_64bit: bool
    process_is_64bit: bool
    is_match: bool
    
    def get_mismatch_message(self) -> str:
        """Get user-friendly message about architecture mismatch."""
        if self.is_match:
            return "Architecture matches"
        
        tool_arch = "64-bit" if self.tool_is_64bit else "32-bit"
        process_arch = "64-bit" if self.process_is_64bit else "32-bit"
        return (f"Architecture mismatch: Tool is {tool_arch} but process is {process_arch}. "
                f"Memory operations may be unreliable. Please use the {process_arch} build.")


class ProcessHandle:
    """Wrapper for Windows process handle with automatic cleanup."""
    
    def __init__(self, handle: int, pid: int):
        self.handle = handle
        self.pid = pid
        self._closed = False
    
    def is_valid(self) -> bool:
        """Check if the handle is valid."""
        return self.handle != 0 and self.handle != INVALID_HANDLE_VALUE and not self._closed
    
    def close(self):
        """Close the process handle."""
        if self.is_valid():
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self._closed = True
            logger.debug(f"Closed process handle for PID {self.pid}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def __del__(self):
        self.close()


class ProcessManager:
    """
    Manages Windows process enumeration and attachment.
    
    Provides methods to enumerate running processes, retrieve module information,
    and open process handles with appropriate access rights.
    """
    
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        logger.info("ProcessManager initialized")
    
    def enumerate_processes(self) -> List[ProcessInfo]:
        """
        Enumerate all running processes.
        
        Returns:
            List of ProcessInfo objects containing process details.
        
        Raises:
            OSError: If snapshot creation fails.
        """
        processes = []
        
        # Create snapshot of all processes
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == INVALID_HANDLE_VALUE:
            error_code = ctypes.get_last_error()
            logger.error(f"CreateToolhelp32Snapshot failed with error {error_code}")
            raise OSError(f"Failed to create process snapshot: Error {error_code}")
        
        try:
            pe32 = PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
            
            # Get first process
            if not self.kernel32.Process32First(snapshot, ctypes.byref(pe32)):
                error_code = ctypes.get_last_error()
                if error_code != ERROR_NO_MORE_FILES:
                    logger.error(f"Process32First failed with error {error_code}")
                return processes
            
            # Iterate through all processes
            while True:
                pid = pe32.th32ProcessID
                name = pe32.szExeFile.decode('utf-8', errors='ignore')
                
                # Try to get main module information
                main_module_base = 0
                main_module_size = 0
                exe_path = ""
                
                try:
                    modules = self.get_process_modules(pid)
                    if modules:
                        # First module is typically the main executable
                        main_module = modules[0]
                        main_module_base = main_module.base_address
                        main_module_size = main_module.size
                        exe_path = main_module.path
                except Exception as e:
                    logger.debug(f"Could not get modules for PID {pid}: {e}")
                    exe_path = name
                
                processes.append(ProcessInfo(
                    pid=pid,
                    name=name,
                    exe_path=exe_path,
                    main_module_base=main_module_base,
                    main_module_size=main_module_size
                ))
                
                # Get next process
                if not self.kernel32.Process32Next(snapshot, ctypes.byref(pe32)):
                    break
            
            logger.info(f"Enumerated {len(processes)} processes")
            return processes
            
        finally:
            self.kernel32.CloseHandle(snapshot)
    
    def get_process_modules(self, pid: int) -> List[ModuleInfo]:
        """
        Get all modules loaded in a process.
        
        Args:
            pid: Process ID.
        
        Returns:
            List of ModuleInfo objects.
        
        Raises:
            OSError: If snapshot creation fails.
        """
        modules = []
        
        # Create snapshot of process modules
        snapshot = self.kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid
        )
        if snapshot == INVALID_HANDLE_VALUE:
            error_code = ctypes.get_last_error()
            logger.debug(f"CreateToolhelp32Snapshot for modules failed: Error {error_code}")
            raise OSError(f"Failed to create module snapshot for PID {pid}: Error {error_code}")
        
        try:
            me32 = MODULEENTRY32()
            me32.dwSize = ctypes.sizeof(MODULEENTRY32)
            
            # Get first module
            if not self.kernel32.Module32First(snapshot, ctypes.byref(me32)):
                error_code = ctypes.get_last_error()
                if error_code != ERROR_NO_MORE_FILES:
                    logger.debug(f"Module32First failed with error {error_code}")
                return modules
            
            # Iterate through all modules
            while True:
                name = me32.szModule.decode('utf-8', errors='ignore')
                path = me32.szExePath.decode('utf-8', errors='ignore')
                base_address = ctypes.cast(me32.modBaseAddr, ctypes.c_void_p).value
                size = me32.modBaseSize
                
                modules.append(ModuleInfo(
                    name=name,
                    base_address=base_address,
                    size=size,
                    path=path
                ))
                
                # Get next module
                if not self.kernel32.Module32Next(snapshot, ctypes.byref(me32)):
                    break
            
            logger.debug(f"Found {len(modules)} modules for PID {pid}")
            return modules
            
        finally:
            self.kernel32.CloseHandle(snapshot)
    
    def open_process(self, pid: int) -> ProcessHandle:
        """
        Open a process with required access rights.
        
        Opens the process with PROCESS_VM_READ, PROCESS_VM_WRITE,
        PROCESS_VM_OPERATION, and PROCESS_QUERY_INFORMATION rights.
        
        Args:
            pid: Process ID to open.
        
        Returns:
            ProcessHandle object for the opened process.
        
        Raises:
            OSError: If OpenProcess fails with detailed error information.
        """
        access_rights = (
            PROCESS_VM_READ |
            PROCESS_VM_WRITE |
            PROCESS_VM_OPERATION |
            PROCESS_QUERY_INFORMATION
        )
        
        handle = self.kernel32.OpenProcess(access_rights, False, pid)
        
        if not handle or handle == INVALID_HANDLE_VALUE:
            error_code = ctypes.get_last_error()
            error_msg = self._get_open_process_error_message(error_code, pid)
            logger.error(f"OpenProcess failed for PID {pid}: {error_msg}")
            raise OSError(error_msg)
        
        logger.info(f"Successfully opened process PID {pid}")
        return ProcessHandle(handle, pid)
    
    def close_process(self, process_handle: ProcessHandle):
        """
        Close a process handle.
        
        Args:
            process_handle: ProcessHandle to close.
        """
        process_handle.close()
    
    def check_architecture_match(self, process_handle: ProcessHandle) -> ArchitectureInfo:
        """
        Check if tool architecture matches process architecture.
        
        Uses IsWow64Process to determine if there's an architecture mismatch
        between the tool and the target process.
        
        Args:
            process_handle: Handle to the process to check.
        
        Returns:
            ArchitectureInfo with match status and details.
        """
        import sys
        import platform
        
        # Determine tool architecture
        tool_is_64bit = sys.maxsize > 2**32
        
        # Check if process is running under WOW64 (32-bit on 64-bit Windows)
        is_wow64 = wintypes.BOOL()
        result = self.kernel32.IsWow64Process(
            process_handle.handle,
            ctypes.byref(is_wow64)
        )
        
        if not result:
            error_code = ctypes.get_last_error()
            logger.warning(f"IsWow64Process failed with error {error_code}")
            # Assume match if we can't determine
            return ArchitectureInfo(
                tool_is_64bit=tool_is_64bit,
                process_is_64bit=tool_is_64bit,
                is_match=True
            )
        
        # If process is WOW64, it's 32-bit running on 64-bit Windows
        # If not WOW64 and we're on 64-bit Windows, process is 64-bit
        # If not WOW64 and we're on 32-bit Windows, process is 32-bit
        machine = platform.machine().lower()
        system_is_64bit = machine in ('amd64', 'x86_64')
        
        if is_wow64.value:
            process_is_64bit = False
        else:
            process_is_64bit = system_is_64bit
        
        is_match = tool_is_64bit == process_is_64bit
        
        arch_info = ArchitectureInfo(
            tool_is_64bit=tool_is_64bit,
            process_is_64bit=process_is_64bit,
            is_match=is_match
        )
        
        if not is_match:
            logger.warning(f"Architecture mismatch for PID {process_handle.pid}: {arch_info.get_mismatch_message()}")
        
        return arch_info
    
    def _get_open_process_error_message(self, error_code: int, pid: int) -> str:
        """
        Get user-friendly error message for OpenProcess failures.
        
        Args:
            error_code: Windows error code from GetLastError().
            pid: Process ID that failed to open.
        
        Returns:
            Actionable error message.
        """
        if error_code == ERROR_ACCESS_DENIED:
            return (
                f"Access denied when opening process {pid}. "
                f"The process may require administrator privileges. "
                f"Try running this application as administrator."
            )
        elif error_code == ERROR_INVALID_HANDLE:
            return (
                f"Invalid handle for process {pid}. "
                f"The process may have terminated."
            )
        else:
            # Get system error message
            message_buffer = ctypes.create_unicode_buffer(256)
            self.kernel32.FormatMessageW(
                0x00001000,  # FORMAT_MESSAGE_FROM_SYSTEM
                None,
                error_code,
                0,
                message_buffer,
                256,
                None
            )
            system_msg = message_buffer.value.strip()
            return f"Failed to open process {pid}: {system_msg} (Error {error_code})"
