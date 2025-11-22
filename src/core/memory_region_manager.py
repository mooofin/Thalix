"""
Memory Region Manager - Caches and manages memory region information.

This module provides efficient access to memory region information with
caching and filtering capabilities.
"""

import bisect
from typing import List, Optional
import logging

from .memory_manager import MemoryManager, MemoryRegion, MemoryState

logger = logging.getLogger(__name__)


class MemoryRegionManager:
    """
    Manages cached memory region information for efficient access.
    
    Maintains a sorted list of memory regions and provides filtered views
    (readable, writable) and efficient lookup by address.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize MemoryRegionManager.
        
        Args:
            memory_manager: MemoryManager instance for the target process.
        """
        self.memory_manager = memory_manager
        self._regions: List[MemoryRegion] = []
        self._region_addresses: List[int] = []  # For binary search
        self._cached = False
        logger.info("MemoryRegionManager initialized")
    
    def refresh_regions(self):
        """
        Refresh the memory region cache.
        
        Enumerates all memory regions and updates the internal cache.
        This should be called when memory layout may have changed.
        """
        logger.info("Refreshing memory regions...")
        self._regions.clear()
        self._region_addresses.clear()
        
        for region in self.memory_manager.enumerate_memory_regions():
            self._regions.append(region)
            self._region_addresses.append(region.base_address)
        
        self._cached = True
        logger.info(f"Cached {len(self._regions)} memory regions")
    
    def _ensure_cached(self):
        """Ensure regions are cached, refresh if not."""
        if not self._cached:
            self.refresh_regions()
    
    def get_all_regions(self) -> List[MemoryRegion]:
        """
        Get all memory regions.
        
        Returns:
            List of all MemoryRegion objects.
        """
        self._ensure_cached()
        return self._regions.copy()
    
    def get_readable_regions(self) -> List[MemoryRegion]:
        """
        Get all readable memory regions.
        
        Filters out PAGE_NOACCESS and PAGE_GUARD regions, and regions
        that are not committed.
        
        Returns:
            List of readable MemoryRegion objects.
        """
        self._ensure_cached()
        readable = [r for r in self._regions if r.is_readable]
        logger.debug(f"Found {len(readable)} readable regions")
        return readable
    
    def get_writable_regions(self) -> List[MemoryRegion]:
        """
        Get all writable memory regions.
        
        Filters out regions without write permission.
        
        Returns:
            List of writable MemoryRegion objects.
        """
        self._ensure_cached()
        writable = [r for r in self._regions if r.is_writable]
        logger.debug(f"Found {len(writable)} writable regions")
        return writable
    
    def get_executable_regions(self) -> List[MemoryRegion]:
        """
        Get all executable memory regions.
        
        Returns:
            List of executable MemoryRegion objects.
        """
        self._ensure_cached()
        executable = [r for r in self._regions if r.is_executable]
        logger.debug(f"Found {len(executable)} executable regions")
        return executable
    
    def get_region_at_address(self, address: int) -> Optional[MemoryRegion]:
        """
        Get the memory region containing the specified address.
        
        Uses binary search for efficient lookup.
        
        Args:
            address: Memory address to look up.
        
        Returns:
            MemoryRegion containing the address, or None if not found.
        """
        self._ensure_cached()
        
        if not self._regions:
            return None
        
        # Binary search to find the region
        # Find the rightmost region with base_address <= address
        idx = bisect.bisect_right(self._region_addresses, address)
        
        if idx == 0:
            # Address is before the first region
            return None
        
        # Check the region before the insertion point
        region = self._regions[idx - 1]
        
        # Verify address is within this region
        if region.base_address <= address < region.base_address + region.size:
            return region
        
        return None
    
    def get_module_region(self, module_name: str) -> Optional[MemoryRegion]:
        """
        Get the memory region for a specific module.
        
        Note: This is a simplified implementation. For full module support,
        we would need to track module information alongside regions.
        
        Args:
            module_name: Name of the module to find.
        
        Returns:
            MemoryRegion for the module, or None if not found.
        """
        # This is a placeholder implementation
        # Full implementation would require integrating module information
        # from ProcessManager.get_process_modules()
        logger.warning("get_module_region is not fully implemented yet")
        return None
    
    def get_regions_in_range(self, start_address: int, end_address: int) -> List[MemoryRegion]:
        """
        Get all memory regions that overlap with the specified address range.
        
        Args:
            start_address: Start of the address range.
            end_address: End of the address range (exclusive).
        
        Returns:
            List of MemoryRegion objects that overlap with the range.
        """
        self._ensure_cached()
        
        if start_address >= end_address:
            return []
        
        # Find the first region that might overlap
        idx = bisect.bisect_right(self._region_addresses, start_address)
        if idx > 0:
            idx -= 1
        
        regions = []
        while idx < len(self._regions):
            region = self._regions[idx]
            region_end = region.base_address + region.size
            
            # Check if region overlaps with our range
            if region.base_address < end_address and region_end > start_address:
                regions.append(region)
            
            # Stop if we've passed the end of our range
            if region.base_address >= end_address:
                break
            
            idx += 1
        
        logger.debug(
            f"Found {len(regions)} regions in range "
            f"0x{start_address:X}-0x{end_address:X}"
        )
        return regions
    
    def get_committed_regions(self) -> List[MemoryRegion]:
        """
        Get all committed memory regions.
        
        Returns:
            List of committed MemoryRegion objects.
        """
        self._ensure_cached()
        committed = [r for r in self._regions if r.state == MemoryState.COMMIT]
        logger.debug(f"Found {len(committed)} committed regions")
        return committed
    
    def get_statistics(self) -> dict:
        """
        Get statistics about memory regions.
        
        Returns:
            Dictionary with region statistics.
        """
        self._ensure_cached()
        
        total_size = sum(r.size for r in self._regions)
        committed_size = sum(r.size for r in self._regions if r.state == MemoryState.COMMIT)
        readable_count = len(self.get_readable_regions())
        writable_count = len(self.get_writable_regions())
        executable_count = len(self.get_executable_regions())
        
        return {
            'total_regions': len(self._regions),
            'total_size': total_size,
            'committed_size': committed_size,
            'readable_regions': readable_count,
            'writable_regions': writable_count,
            'executable_regions': executable_count
        }
