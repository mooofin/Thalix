"""
Memory Editor Module - Lite Cheat Engine functionality
For educational and single-player use only!
"""

import ctypes
from ctypes import wintypes
import struct
import json
import os

# Windows API constants
PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

# Memory protection constants
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000

class MemoryEditor:
    """Handles process memory reading and writing"""
    
    def __init__(self, pid=None):
        self.pid = pid
        self.process_handle = None
        
        # Windows API functions
        self.kernel32 = ctypes.windll.kernel32
        self.OpenProcess = self.kernel32.OpenProcess
        self.ReadProcessMemory = self.kernel32.ReadProcessMemory
        self.WriteProcessMemory = self.kernel32.WriteProcessMemory
        self.VirtualProtectEx = self.kernel32.VirtualProtectEx
        self.CloseHandle = self.kernel32.CloseHandle
        
    def open_process(self, pid):
        """Open process for memory access"""
        self.pid = pid
        self.process_handle = self.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        return self.process_handle is not None and self.process_handle != 0
        
    def close_process(self):
        """Close process handle"""
        if self.process_handle:
            self.CloseHandle(self.process_handle)
            self.process_handle = None
            
    def read_memory(self, address, size):
        """Read memory from process"""
        if not self.process_handle:
            return None
            
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        
        success = self.ReadProcessMemory(
            self.process_handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        
        if success and bytes_read.value == size:
            return buffer.raw
        return None
        
    def write_memory(self, address, data):
        """Write memory to process"""
        if not self.process_handle:
            return False
            
        bytes_written = ctypes.c_size_t(0)
        buffer = ctypes.create_string_buffer(data)
        
        success = self.WriteProcessMemory(
            self.process_handle,
            ctypes.c_void_p(address),
            buffer,
            len(data),
            ctypes.byref(bytes_written)
        )
        
        return success and bytes_written.value == len(data)
        
    def read_int(self, address):
        """Read 4-byte integer"""
        data = self.read_memory(address, 4)
        if data:
            return struct.unpack('<i', data)[0]
        return None
        
    def write_int(self, address, value):
        """Write 4-byte integer"""
        data = struct.pack('<i', value)
        return self.write_memory(address, data)
        
    def read_float(self, address):
        """Read 4-byte float"""
        data = self.read_memory(address, 4)
        if data:
            return struct.unpack('<f', data)[0]
        return None
        
    def write_float(self, address, value):
        """Write 4-byte float"""
        data = struct.pack('<f', value)
        return self.write_memory(address, data)
        
    def read_long(self, address):
        """Read 8-byte long"""
        data = self.read_memory(address, 8)
        if data:
            return struct.unpack('<q', data)[0]
        return None
        
    def write_long(self, address, value):
        """Write 8-byte long"""
        data = struct.pack('<q', value)
        return self.write_memory(address, data)
        
    def read_double(self, address):
        """Read 8-byte double"""
        data = self.read_memory(address, 8)
        if data:
            return struct.unpack('<d', data)[0]
        return None
        
    def write_double(self, address, value):
        """Write 8-byte double"""
        data = struct.pack('<d', value)
        return self.write_memory(address, data)
        
    def read_bytes(self, address, length):
        """Read arbitrary bytes"""
        return self.read_memory(address, length)
        
    def write_bytes(self, address, data):
        """Write arbitrary bytes"""
        return self.write_memory(address, data)
        
    def scan_memory(self, value, value_type='int', start_address=0x10000, end_address=0x7FFFFFFF):
        """
        Scan memory for a specific value
        value_type: 'int', 'float', 'long', 'double', 'bytes'
        Returns list of addresses
        """
        results = []
        current_address = start_address
        
        # Determine scan parameters based on type
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
            return results
            
        # Scan in chunks for performance
        chunk_size = 4096
        
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
            except:
                current_address += chunk_size
                continue
                
        return results
        
    def read_pointer_chain(self, base_address, offsets):
        """
        Read a pointer chain (for multi-level pointers)
        Example: [[Game.exe+123456]+10]+20
        """
        current_address = base_address
        
        for offset in offsets[:-1]:
            # Read pointer at current address
            pointer = self.read_long(current_address + offset)
            if pointer is None:
                return None
            current_address = pointer
            
        # Apply final offset
        return current_address + offsets[-1]


class CheatTable:
    """Handle cheat table files (.ct format simplified)"""
    
    def __init__(self):
        self.entries = []
        
    def add_entry(self, name, address, value_type, description="", offsets=None):
        """Add a cheat entry"""
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
        return entry
        
    def remove_entry(self, index):
        """Remove an entry"""
        if 0 <= index < len(self.entries):
            self.entries.pop(index)
            
    def save_to_file(self, filename):
        """Save cheat table to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.entries, f, indent=2)
            
    def load_from_file(self, filename):
        """Load cheat table from JSON file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                self.entries = json.load(f)
                return True
        return False
        
    def get_entry(self, index):
        """Get entry by index"""
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None


class MemoryFreezer:
    """Keeps memory values frozen at specified values"""
    
    def __init__(self, memory_editor):
        self.memory_editor = memory_editor
        self.frozen_addresses = {}  # address: (value, type)
        self.running = False
        
    def add_frozen_address(self, address, value, value_type):
        """Add an address to freeze"""
        self.frozen_addresses[address] = (value, value_type)
        
    def remove_frozen_address(self, address):
        """Remove frozen address"""
        if address in self.frozen_addresses:
            del self.frozen_addresses[address]
            
    def freeze_loop(self):
        """Keep writing frozen values (run in thread)"""
        while self.running:
            for address, (value, value_type) in self.frozen_addresses.items():
                try:
                    if value_type == 'int':
                        self.memory_editor.write_int(address, value)
                    elif value_type == 'float':
                        self.memory_editor.write_float(address, value)
                    elif value_type == 'long':
                        self.memory_editor.write_long(address, value)
                    elif value_type == 'double':
                        self.memory_editor.write_double(address, value)
                except:
                    pass
            import time
            time.sleep(0.05)  # Update 20 times per second
            
    def start(self):
        """Start freezing"""
        if not self.running:
            self.running = True
            import threading
            threading.Thread(target=self.freeze_loop, daemon=True).start()
            
    def stop(self):
        """Stop freezing"""
        self.running = False
