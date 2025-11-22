"""
Disassembly Engine - Disassemble machine code using Capstone.

This module provides functionality to disassemble x86/x64 machine code
into human-readable assembly instructions.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

try:
    import capstone
    CAPSTONE_AVAILABLE = True
except ImportError:
    CAPSTONE_AVAILABLE = False
    capstone = None

from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class Instruction:
    """
    Represents a disassembled instruction.
    
    Attributes:
        address: Memory address of the instruction
        bytes: Raw bytes of the instruction
        mnemonic: Instruction mnemonic (e.g., "mov", "jmp")
        operands: Operand string (e.g., "eax, [ebp+8]")
        size: Size of the instruction in bytes
    """
    address: int
    bytes: bytes
    mnemonic: str
    operands: str
    size: int
    
    def to_string(self) -> str:
        """
        Format instruction as a string.
        
        Returns:
            String like "0x401000: 8B 45 08    mov eax, [ebp+8]"
        """
        bytes_hex = ' '.join(f'{b:02X}' for b in self.bytes)
        bytes_hex = bytes_hex.ljust(24)  # Pad to fixed width
        
        if self.operands:
            asm = f"{self.mnemonic} {self.operands}"
        else:
            asm = self.mnemonic
        
        return f"0x{self.address:08X}: {bytes_hex} {asm}"


class DisassemblyEngine:
    """
    Engine for disassembling x86/x64 machine code.
    
    Uses the Capstone disassembly framework to convert machine code
    into assembly instructions.
    """
    
    def __init__(self, memory_manager: MemoryManager, is_64bit: bool = True):
        """
        Initialize DisassemblyEngine.
        
        Args:
            memory_manager: MemoryManager for reading code from memory.
            is_64bit: Whether target process is 64-bit (True) or 32-bit (False).
        
        Raises:
            ImportError: If Capstone is not available.
        """
        if not CAPSTONE_AVAILABLE:
            raise ImportError(
                "Capstone library is not available. "
                "Install it with: pip install capstone"
            )
        
        self.memory_manager = memory_manager
        self.is_64bit = is_64bit
        
        # Initialize Capstone
        mode = capstone.CS_MODE_64 if is_64bit else capstone.CS_MODE_32
        self.cs = capstone.Cs(capstone.CS_ARCH_X86, mode)
        
        # Enable detail mode for operand information
        self.cs.detail = True
        
        logger.info(
            f"DisassemblyEngine initialized "
            f"({'64-bit' if is_64bit else '32-bit'} mode)"
        )
    
    def disassemble(self, address: int, count: int = 10, 
                   max_bytes: int = 256) -> List[Instruction]:
        """
        Disassemble instructions starting at the given address.
        
        Args:
            address: Starting address to disassemble from.
            count: Number of instructions to disassemble.
            max_bytes: Maximum bytes to read from memory.
        
        Returns:
            List of Instruction objects.
        """
        # Read memory
        data, success = self.memory_manager.read_memory(address, max_bytes)
        
        if not data:
            logger.warning(f"Failed to read memory at 0x{address:X}")
            return []
        
        # Disassemble
        instructions = []
        
        try:
            for i, cs_insn in enumerate(self.cs.disasm(data, address)):
                if i >= count:
                    break
                
                instruction = Instruction(
                    address=cs_insn.address,
                    bytes=cs_insn.bytes,
                    mnemonic=cs_insn.mnemonic,
                    operands=cs_insn.op_str,
                    size=cs_insn.size
                )
                instructions.append(instruction)
            
            logger.debug(
                f"Disassembled {len(instructions)} instructions at 0x{address:X}"
            )
            
        except capstone.CsError as e:
            logger.error(f"Capstone error during disassembly: {e}")
        
        return instructions
    
    def disassemble_bytes(self, data: bytes, address: int = 0) -> List[Instruction]:
        """
        Disassemble raw bytes.
        
        Args:
            data: Raw bytes to disassemble.
            address: Virtual address for the bytes (for display).
        
        Returns:
            List of Instruction objects.
        """
        instructions = []
        
        try:
            for cs_insn in self.cs.disasm(data, address):
                instruction = Instruction(
                    address=cs_insn.address,
                    bytes=cs_insn.bytes,
                    mnemonic=cs_insn.mnemonic,
                    operands=cs_insn.op_str,
                    size=cs_insn.size
                )
                instructions.append(instruction)
            
            logger.debug(
                f"Disassembled {len(instructions)} instructions from {len(data)} bytes"
            )
            
        except capstone.CsError as e:
            logger.error(f"Capstone error during disassembly: {e}")
        
        return instructions
    
    def disassemble_backward(self, address: int, count: int = 10,
                           lookback_bytes: int = 64) -> List[Instruction]:
        """
        Disassemble instructions before the given address.
        
        This is more complex than forward disassembly because we don't know
        where instructions start. We read a lookback buffer and try multiple
        starting offsets to find a valid disassembly sequence.
        
        Args:
            address: Target address to disassemble before.
            count: Number of instructions to disassemble before target.
            lookback_bytes: Number of bytes to read before target address.
        
        Returns:
            List of Instruction objects ending at or near the target address.
        """
        # Read lookback buffer
        start_address = max(0, address - lookback_bytes)
        read_size = address - start_address + 16  # Extra bytes for context
        
        data, success = self.memory_manager.read_memory(start_address, read_size)
        
        if not data:
            logger.warning(
                f"Failed to read memory for backward disassembly at 0x{address:X}"
            )
            return []
        
        # Try disassembly from multiple candidate start offsets
        best_sequence = []
        best_score = -1
        
        # Try starting from different offsets
        for start_offset in range(0, min(len(data), lookback_bytes), 1):
            try:
                sequence = []
                current_addr = start_address + start_offset
                
                # Disassemble from this offset
                for cs_insn in self.cs.disasm(data[start_offset:], current_addr):
                    instruction = Instruction(
                        address=cs_insn.address,
                        bytes=cs_insn.bytes,
                        mnemonic=cs_insn.mnemonic,
                        operands=cs_insn.op_str,
                        size=cs_insn.size
                    )
                    sequence.append(instruction)
                    
                    # Stop if we've gone past the target
                    if cs_insn.address >= address:
                        break
                
                # Score this sequence based on how close it gets to target
                if sequence:
                    last_addr = sequence[-1].address
                    last_end = last_addr + sequence[-1].size
                    
                    # Perfect score if we end exactly at target
                    if last_end == address:
                        score = 1000
                    # Good score if we end near target
                    elif abs(last_end - address) <= 15:
                        score = 100 - abs(last_end - address)
                    else:
                        score = 0
                    
                    # Prefer longer sequences
                    score += len(sequence)
                    
                    if score > best_score:
                        best_score = score
                        best_sequence = sequence
                
            except capstone.CsError:
                # This start offset didn't work, try next
                continue
        
        # Return the last N instructions from best sequence
        if best_sequence:
            result = best_sequence[-count:] if len(best_sequence) > count else best_sequence
            logger.debug(
                f"Backward disassembly at 0x{address:X}: "
                f"Found {len(result)} instructions"
            )
            return result
        else:
            logger.warning(
                f"Failed to find valid backward disassembly at 0x{address:X}"
            )
            return []
    
    def get_instruction_at(self, address: int) -> Optional[Instruction]:
        """
        Get the instruction at a specific address.
        
        Args:
            address: Address of the instruction.
        
        Returns:
            Instruction object, or None if disassembly fails.
        """
        instructions = self.disassemble(address, count=1, max_bytes=15)
        return instructions[0] if instructions else None
    
    def format_instructions(self, instructions: List[Instruction]) -> str:
        """
        Format a list of instructions as a multi-line string.
        
        Args:
            instructions: List of Instruction objects.
        
        Returns:
            Formatted string with one instruction per line.
        """
        return '\n'.join(insn.to_string() for insn in instructions)
