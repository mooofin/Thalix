"""
Assembly Engine and Code Patcher - Assemble and patch machine code.

This module provides functionality to assemble x86/x64 assembly code
and patch it into process memory with undo support.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from collections import deque
import time
import logging

try:
    import keystone
    KEYSTONE_AVAILABLE = True
except ImportError:
    KEYSTONE_AVAILABLE = False
    keystone = None

from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class PatchEntry:
    """
    Represents a code patch operation.
    
    Attributes:
        timestamp: When the patch was applied
        address: Memory address that was patched
        original_bytes: Original bytes before patching
        new_bytes: New bytes that were written
        assembly_text: Assembly code that was assembled
        description: Description of the patch
    """
    timestamp: float
    address: int
    original_bytes: bytes
    new_bytes: bytes
    assembly_text: str = ""
    description: str = ""
    
    def get_timestamp_str(self) -> str:
        """Get formatted timestamp string."""
        from datetime import datetime
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class AssemblyEngine:
    """
    Engine for assembling x86/x64 assembly code.
    
    Uses the Keystone assembler framework to convert assembly text
    into machine code bytes.
    """
    
    def __init__(self, is_64bit: bool = True):
        """
        Initialize AssemblyEngine.
        
        Args:
            is_64bit: Whether target process is 64-bit (True) or 32-bit (False).
        
        Raises:
            ImportError: If Keystone is not available.
        """
        if not KEYSTONE_AVAILABLE:
            raise ImportError(
                "Keystone library is not available. "
                "Install it with: pip install keystone-engine"
            )
        
        self.is_64bit = is_64bit
        
        # Initialize Keystone
        mode = keystone.KS_MODE_64 if is_64bit else keystone.KS_MODE_32
        self.ks = keystone.Ks(keystone.KS_ARCH_X86, mode)
        
        logger.info(
            f"AssemblyEngine initialized "
            f"({'64-bit' if is_64bit else '32-bit'} mode)"
        )
    
    def assemble(self, assembly_text: str, address: int = 0) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Assemble assembly code into machine code bytes.
        
        Args:
            assembly_text: Assembly code to assemble (can be multi-line).
            address: Virtual address for position-dependent instructions.
        
        Returns:
            Tuple of (assembled_bytes, error_message).
            If successful, returns (bytes, None).
            If failed, returns (None, error_message).
        """
        try:
            # Assemble the code
            encoding, count = self.ks.asm(assembly_text, address)
            
            if encoding is None:
                error_msg = self.get_last_error()
                logger.warning(f"Assembly failed: {error_msg}")
                return (None, error_msg)
            
            # Convert to bytes
            assembled_bytes = bytes(encoding)
            
            logger.debug(
                f"Assembled {len(assembly_text)} chars into "
                f"{len(assembled_bytes)} bytes ({count} instructions)"
            )
            
            return (assembled_bytes, None)
            
        except keystone.KsError as e:
            error_msg = f"Keystone error: {e}"
            logger.error(error_msg)
            return (None, error_msg)
    
    def get_last_error(self) -> str:
        """
        Get the last error message from the assembler.
        
        Returns:
            Error message string.
        """
        if hasattr(self.ks, 'errno') and self.ks.errno != keystone.KS_ERR_OK:
            return keystone.ks_strerror(self.ks.errno)
        return "Unknown error"
    
    def validate_syntax(self, assembly_text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate assembly syntax without producing output.
        
        Args:
            assembly_text: Assembly code to validate.
        
        Returns:
            Tuple of (is_valid, error_message).
        """
        assembled_bytes, error_msg = self.assemble(assembly_text, address=0)
        
        if assembled_bytes is not None:
            return (True, None)
        else:
            return (False, error_msg)


class CodePatcher:
    """
    Manages code patching operations with undo support.
    
    Provides safe code modification with automatic backup and restoration.
    """
    
    def __init__(self, memory_manager: MemoryManager, 
                 assembly_engine: AssemblyEngine,
                 max_undo_entries: int = 100):
        """
        Initialize CodePatcher.
        
        Args:
            memory_manager: MemoryManager for reading/writing memory.
            assembly_engine: AssemblyEngine for assembling code.
            max_undo_entries: Maximum number of undo entries to keep.
        """
        self.memory_manager = memory_manager
        self.assembly_engine = assembly_engine
        self.max_undo_entries = max_undo_entries
        
        # Patch history
        self._patch_history: deque[PatchEntry] = deque(maxlen=max_undo_entries)
        
        logger.info("CodePatcher initialized")
    
    def patch_code(self, address: int, assembly_text: str,
                  description: str = "") -> Tuple[bool, Optional[str]]:
        """
        Assemble and patch code at the specified address.
        
        Reads original bytes, assembles the new code, validates the size,
        and writes to memory. Creates an undo entry on success.
        
        Args:
            address: Memory address to patch.
            assembly_text: Assembly code to assemble and write.
            description: Description of the patch.
        
        Returns:
            Tuple of (success, error_message).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
        # Assemble the code
        new_bytes, error_msg = self.assembly_engine.assemble(assembly_text, address)
        
        if new_bytes is None:
            return (False, f"Assembly failed: {error_msg}")
        
        # Read original bytes
        original_bytes, success = self.memory_manager.read_memory(
            address,
            len(new_bytes)
        )
        
        if not success or len(original_bytes) < len(new_bytes):
            return (False, f"Failed to read original bytes at 0x{address:X}")
        
        # Write new bytes
        success = self.memory_manager.write_memory(address, new_bytes)
        
        if not success:
            return (False, f"Failed to write patched bytes to 0x{address:X}")
        
        # Create patch entry
        patch_entry = PatchEntry(
            timestamp=time.time(),
            address=address,
            original_bytes=original_bytes,
            new_bytes=new_bytes,
            assembly_text=assembly_text,
            description=description
        )
        self._patch_history.append(patch_entry)
        
        logger.info(
            f"Patched code at 0x{address:X}: "
            f"{len(new_bytes)} bytes, {description}"
        )
        
        return (True, None)
    
    def patch_bytes(self, address: int, new_bytes: bytes,
                   description: str = "") -> Tuple[bool, Optional[str]]:
        """
        Patch raw bytes at the specified address.
        
        Args:
            address: Memory address to patch.
            new_bytes: Bytes to write.
            description: Description of the patch.
        
        Returns:
            Tuple of (success, error_message).
        """
        # Read original bytes
        original_bytes, success = self.memory_manager.read_memory(
            address,
            len(new_bytes)
        )
        
        if not success or len(original_bytes) < len(new_bytes):
            return (False, f"Failed to read original bytes at 0x{address:X}")
        
        # Write new bytes
        success = self.memory_manager.write_memory(address, new_bytes)
        
        if not success:
            return (False, f"Failed to write bytes to 0x{address:X}")
        
        # Create patch entry
        patch_entry = PatchEntry(
            timestamp=time.time(),
            address=address,
            original_bytes=original_bytes,
            new_bytes=new_bytes,
            assembly_text="",
            description=description
        )
        self._patch_history.append(patch_entry)
        
        logger.info(
            f"Patched bytes at 0x{address:X}: "
            f"{len(new_bytes)} bytes, {description}"
        )
        
        return (True, None)
    
    def restore_patch(self, patch_entry: PatchEntry) -> bool:
        """
        Restore original bytes from a patch entry.
        
        Args:
            patch_entry: PatchEntry to restore from.
        
        Returns:
            True if restore succeeded, False otherwise.
        """
        success = self.memory_manager.write_memory(
            patch_entry.address,
            patch_entry.original_bytes
        )
        
        if success:
            logger.info(
                f"Restored original bytes at 0x{patch_entry.address:X}"
            )
        else:
            logger.warning(
                f"Failed to restore original bytes at 0x{patch_entry.address:X}"
            )
        
        return success
    
    def get_patch_history(self) -> List[PatchEntry]:
        """
        Get the patch history.
        
        Returns:
            List of PatchEntry objects, most recent first.
        """
        return list(reversed(self._patch_history))
    
    def create_trampoline(self, source_address: int, target_address: int,
                         description: str = "") -> Tuple[bool, Optional[str]]:
        """
        Create a jump trampoline from source to target address.
        
        Calculates the relative offset and creates a JMP instruction.
        
        Args:
            source_address: Address to place the jump.
            target_address: Address to jump to.
            description: Description of the trampoline.
        
        Returns:
            Tuple of (success, error_message).
        """
        # Calculate relative offset
        # JMP instruction is 5 bytes: E9 [4-byte offset]
        jmp_size = 5
        offset = target_address - (source_address + jmp_size)
        
        # Check if offset fits in 32-bit signed integer
        if offset < -2147483648 or offset > 2147483647:
            return (False, f"Jump offset too large: {offset}")
        
        # Create JMP instruction
        # E9 = relative JMP, followed by 4-byte signed offset (little-endian)
        import struct
        jmp_bytes = b'\xE9' + struct.pack('<i', offset)
        
        # Patch the jump
        success, error_msg = self.patch_bytes(
            source_address,
            jmp_bytes,
            description=f"Trampoline to 0x{target_address:X}" + 
                       (f" ({description})" if description else "")
        )
        
        if success:
            logger.info(
                f"Created trampoline: 0x{source_address:X} -> 0x{target_address:X}"
            )
        
        return (success, error_msg)
    
    def nop_bytes(self, address: int, count: int,
                 description: str = "") -> Tuple[bool, Optional[str]]:
        """
        Fill bytes with NOP instructions (0x90).
        
        Args:
            address: Starting address.
            count: Number of bytes to NOP.
            description: Description of the operation.
        
        Returns:
            Tuple of (success, error_message).
        """
        nop_bytes = b'\x90' * count
        
        return self.patch_bytes(
            address,
            nop_bytes,
            description=f"NOP {count} bytes" + 
                       (f" ({description})" if description else "")
        )
    
    def clear_history(self):
        """Clear the patch history."""
        self._patch_history.clear()
        logger.info("Patch history cleared")
