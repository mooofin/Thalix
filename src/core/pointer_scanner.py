"""
Pointer Scanner - Discover pointer chains leading to target addresses.

This module provides functionality to scan memory for pointer chains,
which are sequences of pointers that ultimately lead to a target address.
"""

import struct
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Set, Callable, Tuple, Dict
import logging

from .memory_manager import MemoryManager, MemoryRegion
from .memory_region_manager import MemoryRegionManager

logger = logging.getLogger(__name__)


@dataclass
class PointerChain:
    """
    Represents a pointer chain leading to a target address.
    
    A pointer chain is a sequence like: [base] -> [base+offset1] -> [base+offset1+offset2] -> target
    
    Attributes:
        base_address: Starting address of the chain
        offsets: List of offsets to follow
        target_address: Final address the chain points to
        module_name: Optional module name for the base address
    """
    base_address: int
    offsets: List[int]
    target_address: int
    module_name: Optional[str] = None
    
    def to_string(self) -> str:
        """
        Format the pointer chain as a human-readable string.
        
        Returns:
            String like "[module+0x1234] -> [+0x10] -> [+0x20] -> 0xABCD"
        """
        parts = []
        
        # Base address
        if self.module_name:
            parts.append(f"[{self.module_name}+0x{self.base_address:X}]")
        else:
            parts.append(f"[0x{self.base_address:X}]")
        
        # Offsets
        for offset in self.offsets:
            if offset >= 0:
                parts.append(f"[+0x{offset:X}]")
            else:
                parts.append(f"[-0x{-offset:X}]")
        
        # Target
        parts.append(f"0x{self.target_address:X}")
        
        return " -> ".join(parts)
    
    def __len__(self) -> int:
        """Get the depth of the pointer chain (number of dereferences)."""
        return len(self.offsets)


@dataclass
class PointerScanConfig:
    """
    Configuration for pointer scanning.
    
    Attributes:
        max_depth: Maximum depth of pointer chains to search
        alignment: Pointer alignment (4 for 32-bit, 8 for 64-bit)
        max_offset: Maximum offset from pointer value to target
        search_regions: List of regions to search (None = all readable)
        base_address_filter: Optional filter for base addresses (e.g., module ranges)
        max_results_per_level: Maximum results to keep per level
    """
    max_depth: int = 5
    alignment: int = 4
    max_offset: int = 0x1000
    search_regions: Optional[List[MemoryRegion]] = None
    base_address_filter: Optional[Callable[[int], bool]] = None
    max_results_per_level: int = 100000


class PointerScanner:
    """
    Scanner for discovering pointer chains in process memory.
    
    Uses a level-by-level approach to find chains of pointers that
    ultimately point to a target address.
    """
    
    def __init__(self, memory_manager: MemoryManager, 
                 region_manager: MemoryRegionManager):
        """
        Initialize PointerScanner.
        
        Args:
            memory_manager: MemoryManager for reading memory.
            region_manager: MemoryRegionManager for accessing region information.
        """
        self.memory_manager = memory_manager
        self.region_manager = region_manager
        
        # Determine pointer size based on architecture
        import sys
        self.pointer_size = 8 if sys.maxsize > 2**32 else 4
        self.pointer_format = '<Q' if self.pointer_size == 8 else '<I'
        
        # Cancellation
        self._cancel_event = threading.Event()
        
        logger.info(f"PointerScanner initialized (pointer size: {self.pointer_size} bytes)")
    
    def scan_pointers(self, target_address: int, config: PointerScanConfig,
                     progress_callback: Optional[Callable[[int, int, int], None]] = None) -> List[PointerChain]:
        """
        Scan for pointer chains leading to the target address.
        
        Args:
            target_address: Address to find pointers to.
            config: Scan configuration.
            progress_callback: Optional callback(depth, address_count, chain_count).
        
        Returns:
            List of discovered PointerChain objects.
        """
        logger.info(
            f"Starting pointer scan for target 0x{target_address:X}, "
            f"max depth {config.max_depth}"
        )
        
        self._cancel_event.clear()
        
        # Get search regions
        if config.search_regions:
            regions = config.search_regions
        else:
            regions = self.region_manager.get_readable_regions()
        
        logger.info(f"Scanning {len(regions)} memory regions")
        
        # Level 0: Find addresses containing target_address ± max_offset
        level_addresses = self._scan_level_0(target_address, config, regions)
        
        if progress_callback:
            progress_callback(0, len(level_addresses), 0)
        
        if not level_addresses:
            logger.info("No pointers found at level 0")
            return []
        
        logger.info(f"Level 0: Found {len(level_addresses)} addresses")
        
        # Build chains level by level
        chains: List[PointerChain] = []
        
        for depth in range(1, config.max_depth + 1):
            if self._cancel_event.is_set():
                logger.info("Pointer scan cancelled")
                break
            
            # Find addresses pointing to previous level
            new_level_addresses = self._scan_level_n(
                level_addresses, config, regions, depth
            )
            
            if progress_callback:
                progress_callback(depth, len(new_level_addresses), len(chains))
            
            if not new_level_addresses:
                logger.info(f"Level {depth}: No more pointers found")
                break
            
            logger.info(f"Level {depth}: Found {len(new_level_addresses)} addresses")
            
            # Build chains from this level
            for base_addr, chain_offsets in new_level_addresses.items():
                chain = PointerChain(
                    base_address=base_addr,
                    offsets=chain_offsets,
                    target_address=target_address
                )
                chains.append(chain)
            
            # Check result limit
            if len(chains) >= config.max_results_per_level:
                logger.warning(
                    f"Reached max results limit ({config.max_results_per_level}), "
                    f"stopping scan"
                )
                break
            
            # Prepare for next level
            level_addresses = {addr: [] for addr in new_level_addresses.keys()}
        
        logger.info(f"Pointer scan complete: Found {len(chains)} chains")
        return chains
    
    def _scan_level_0(self, target_address: int, config: PointerScanConfig,
                     regions: List[MemoryRegion]) -> Dict[int, List[int]]:
        """
        Scan for addresses containing target_address ± max_offset.
        
        Returns:
            Dictionary mapping found addresses to empty offset lists.
        """
        results = {}
        
        for region in regions:
            if self._cancel_event.is_set():
                break
            
            if not region.is_readable:
                continue
            
            # Read region memory
            data, success = self.memory_manager.read_memory(
                region.base_address,
                region.size
            )
            
            if not data:
                continue
            
            # Scan for pointers
            for offset in range(0, len(data) - self.pointer_size + 1, config.alignment):
                # Read pointer value
                ptr_bytes = data[offset:offset + self.pointer_size]
                if len(ptr_bytes) < self.pointer_size:
                    break
                
                ptr_value = struct.unpack(self.pointer_format, ptr_bytes)[0]
                
                # Check if pointer points near target
                diff = ptr_value - target_address
                if abs(diff) <= config.max_offset:
                    addr = region.base_address + offset
                    
                    # Apply base address filter if provided
                    if config.base_address_filter and not config.base_address_filter(addr):
                        continue
                    
                    results[addr] = [diff]
                    
                    # Check result limit
                    if len(results) >= config.max_results_per_level:
                        logger.warning(
                            f"Level 0: Reached max results limit "
                            f"({config.max_results_per_level})"
                        )
                        return results
        
        return results
    
    def _scan_level_n(self, prev_level: Dict[int, List[int]], config: PointerScanConfig,
                     regions: List[MemoryRegion], depth: int) -> Dict[int, List[int]]:
        """
        Scan for addresses pointing to previous level addresses.
        
        Args:
            prev_level: Dictionary of addresses from previous level.
            config: Scan configuration.
            regions: Regions to search.
            depth: Current depth level.
        
        Returns:
            Dictionary mapping found addresses to their offset chains.
        """
        results = {}
        prev_addresses = set(prev_level.keys())
        
        for region in regions:
            if self._cancel_event.is_set():
                break
            
            if not region.is_readable:
                continue
            
            # Read region memory
            data, success = self.memory_manager.read_memory(
                region.base_address,
                region.size
            )
            
            if not data:
                continue
            
            # Scan for pointers
            for offset in range(0, len(data) - self.pointer_size + 1, config.alignment):
                # Read pointer value
                ptr_bytes = data[offset:offset + self.pointer_size]
                if len(ptr_bytes) < self.pointer_size:
                    break
                
                ptr_value = struct.unpack(self.pointer_format, ptr_bytes)[0]
                
                # Check if pointer points to any previous level address
                for prev_addr in prev_addresses:
                    diff = ptr_value - prev_addr
                    if abs(diff) <= config.max_offset:
                        addr = region.base_address + offset
                        
                        # Apply base address filter if provided
                        if config.base_address_filter and not config.base_address_filter(addr):
                            continue
                        
                        # Build offset chain
                        prev_offsets = prev_level[prev_addr]
                        new_offsets = [diff] + prev_offsets
                        
                        results[addr] = new_offsets
                        
                        # Check result limit
                        if len(results) >= config.max_results_per_level:
                            logger.warning(
                                f"Level {depth}: Reached max results limit "
                                f"({config.max_results_per_level})"
                            )
                            return results
        
        return results
    
    def validate_chain(self, chain: PointerChain) -> bool:
        """
        Validate that a pointer chain resolves to its target address.
        
        Args:
            chain: PointerChain to validate.
        
        Returns:
            True if chain is valid, False otherwise.
        """
        try:
            current_address = chain.base_address
            
            # Follow each offset
            for offset in chain.offsets[:-1]:  # All but last offset
                # Read pointer at current address
                data, success = self.memory_manager.read_memory(
                    current_address,
                    self.pointer_size
                )
                
                if not success or len(data) < self.pointer_size:
                    logger.debug(
                        f"Chain validation failed: Cannot read at 0x{current_address:X}"
                    )
                    return False
                
                # Dereference pointer
                ptr_value = struct.unpack(self.pointer_format, data)[0]
                current_address = ptr_value + offset
            
            # Apply final offset
            if chain.offsets:
                final_offset = chain.offsets[-1]
                final_address = current_address + final_offset
            else:
                final_address = current_address
            
            # Check if we reached the target
            is_valid = final_address == chain.target_address
            
            if is_valid:
                logger.debug(f"Chain validated: {chain.to_string()}")
            else:
                logger.debug(
                    f"Chain validation failed: Expected 0x{chain.target_address:X}, "
                    f"got 0x{final_address:X}"
                )
            
            return is_valid
            
        except Exception as e:
            logger.debug(f"Chain validation error: {e}")
            return False
    
    def cancel_scan(self):
        """Cancel the current pointer scan."""
        self._cancel_event.set()
        logger.info("Pointer scan cancellation requested")
