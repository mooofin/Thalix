"""
Core module - Windows API abstractions and business logic.

This module provides the core functionality for the Windows Memory Editor,
including process management, memory operations, and region management.
"""

from .process_manager import (
    ProcessManager,
    ProcessHandle,
    ProcessInfo,
    ModuleInfo,
    ArchitectureInfo
)

from .memory_manager import (
    MemoryManager,
    MemoryRegion,
    MemoryState,
    MemoryType
)

from .memory_region_manager import (
    MemoryRegionManager
)

from .exceptions import (
    MemoryEditorException,
    ProcessAccessException,
    MemoryReadException,
    MemoryWriteException,
    ArchitectureMismatchException
)

from .data_types import (
    DataType,
    ValueParser,
    ValueFormatter,
    ValuePacker,
    ComparisonType,
    ValueComparator
)

from .scan_engine import (
    ScanEngine,
    ScanResults,
    ScanProgress,
    ScanType
)

from .aob_scanner import (
    AOBScanner,
    Pattern
)

from .address_table import (
    AddressTableManager,
    AddressEntry,
    UndoEntry
)

from .freezer import (
    FreezerManager,
    FreezeEntry
)

from .pointer_scanner import (
    PointerScanner,
    PointerChain,
    PointerScanConfig
)

from .disassembly import (
    DisassemblyEngine,
    Instruction
)

from .assembly import (
    AssemblyEngine,
    CodePatcher,
    PatchEntry
)

__all__ = [
    # Process management
    'ProcessManager',
    'ProcessHandle',
    'ProcessInfo',
    'ModuleInfo',
    'ArchitectureInfo',
    
    # Memory management
    'MemoryManager',
    'MemoryRegion',
    'MemoryState',
    'MemoryType',
    
    # Region management
    'MemoryRegionManager',
    
    # Data types and value handling
    'DataType',
    'ValueParser',
    'ValueFormatter',
    'ValuePacker',
    'ComparisonType',
    'ValueComparator',
    
    # Scanning
    'ScanEngine',
    'ScanResults',
    'ScanProgress',
    'ScanType',
    
    # AOB Scanning
    'AOBScanner',
    'Pattern',
    
    # Address Table
    'AddressTableManager',
    'AddressEntry',
    'UndoEntry',
    
    # Freezer
    'FreezerManager',
    'FreezeEntry',
    
    # Pointer Scanner
    'PointerScanner',
    'PointerChain',
    'PointerScanConfig',
    
    # Disassembly
    'DisassemblyEngine',
    'Instruction',
    
    # Assembly and Patching
    'AssemblyEngine',
    'CodePatcher',
    'PatchEntry',
    
    # Exceptions
    'MemoryEditorException',
    'ProcessAccessException',
    'MemoryReadException',
    'MemoryWriteException',
    'ArchitectureMismatchException',
]
