"""
AOB (Array of Bytes) Scanner - Pattern matching in process memory.

This module provides functionality to search for byte patterns with wildcard
support in process memory. Patterns are specified in hexadecimal notation with
optional wildcards (e.g., "8B ?? 89").
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

from .memory_manager import MemoryManager, MemoryRegion
from .memory_region_manager import MemoryRegionManager

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """
    Represents a parsed AOB pattern.
    
    Attributes:
        bytes: Array of byte values (wildcards are represented as 0x00)
        mask: Boolean array indicating which bytes are wildcards (False = wildcard)
        original: Original pattern string
    """
    bytes: bytes
    mask: List[bool]
    original: str
    
    def __len__(self) -> int:
        """Get the length of the pattern in bytes."""
        return len(self.bytes)
    
    def get_first_non_wildcard_index(self) -> Optional[int]:
        """
        Get the index of the first non-wildcard byte.
        
        Returns:
            Index of first non-wildcard byte, or None if all are wildcards.
        """
        try:
            return self.mask.index(True)
        except ValueError:
            return None
    
    def get_first_non_wildcard_byte(self) -> Optional[int]:
        """
        Get the first non-wildcard byte value.
        
        Returns:
            First non-wildcard byte value, or None if all are wildcards.
        """
        idx = self.get_first_non_wildcard_index()
        if idx is not None:
            return self.bytes[idx]
        return None


class AOBScanner:
    """
    Scanner for finding byte patterns with wildcard support in process memory.
    
    Supports patterns in hexadecimal notation with ?? for wildcards.
    Example: "8B ?? 89 45 ??" matches 8B [any] 89 45 [any]
    """
    
    # Pattern for validating hex bytes and wildcards
    HEX_PATTERN = re.compile(r'^[0-9A-Fa-f?]{2}$')
    
    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize AOBScanner.
        
        Args:
            memory_manager: MemoryManager instance for reading process memory.
        """
        self.memory_manager = memory_manager
        logger.info("AOBScanner initialized")
    
    def parse_pattern(self, pattern_str: str) -> Pattern:
        """
        Parse a hex pattern string into bytes and mask arrays.
        
        Converts a pattern like "8B ?? 89" into:
        - bytes: [0x8B, 0x00, 0x89]
        - mask: [True, False, True]
        
        Args:
            pattern_str: Pattern string in hex notation with optional wildcards.
                        Bytes can be separated by spaces, commas, or nothing.
                        Wildcards are represented as "??" or "**".
        
        Returns:
            Pattern object with parsed bytes and mask.
        
        Raises:
            ValueError: If pattern syntax is invalid.
        
        Examples:
            >>> scanner.parse_pattern("8B ?? 89")
            Pattern(bytes=b'\\x8b\\x00\\x89', mask=[True, False, True], ...)
            
            >>> scanner.parse_pattern("8B??89")
            Pattern(bytes=b'\\x8b\\x00\\x89', mask=[True, False, True], ...)
            
            >>> scanner.parse_pattern("8B, ??, 89")
            Pattern(bytes=b'\\x8b\\x00\\x89', mask=[True, False, True], ...)
        """
        if not pattern_str:
            raise ValueError("Pattern string cannot be empty")
        
        # Remove common separators and normalize
        pattern_str = pattern_str.strip()
        # Replace commas with spaces
        pattern_str = pattern_str.replace(',', ' ')
        # Replace multiple spaces with single space
        pattern_str = ' '.join(pattern_str.split())
        
        # Split into tokens
        # If no spaces, split every 2 characters
        if ' ' not in pattern_str:
            # Split into 2-character chunks
            if len(pattern_str) % 2 != 0:
                raise ValueError(
                    f"Pattern string must have even number of characters when not space-separated: '{pattern_str}'"
                )
            tokens = [pattern_str[i:i+2] for i in range(0, len(pattern_str), 2)]
        else:
            tokens = pattern_str.split()
        
        if not tokens:
            raise ValueError("Pattern string contains no valid bytes")
        
        bytes_list = []
        mask_list = []
        
        for i, token in enumerate(tokens):
            token = token.strip()
            
            if not token:
                continue
            
            # Validate token format
            if not self.HEX_PATTERN.match(token):
                raise ValueError(
                    f"Invalid byte at position {i}: '{token}'. "
                    f"Expected 2-character hex byte (00-FF) or wildcard (??)"
                )
            
            # Check if it's a wildcard
            if token.lower() in ('??', '**'):
                bytes_list.append(0x00)  # Placeholder value
                mask_list.append(False)  # False = wildcard
            else:
                # Parse hex byte
                try:
                    byte_value = int(token, 16)
                    bytes_list.append(byte_value)
                    mask_list.append(True)  # True = match this byte
                except ValueError:
                    raise ValueError(
                        f"Invalid hex byte at position {i}: '{token}'"
                    )
        
        if not bytes_list:
            raise ValueError("Pattern contains no valid bytes")
        
        # Check if pattern is all wildcards
        if not any(mask_list):
            raise ValueError("Pattern cannot consist entirely of wildcards")
        
        pattern_bytes = bytes(bytes_list)
        
        logger.debug(
            f"Parsed pattern '{pattern_str}': "
            f"{len(pattern_bytes)} bytes, "
            f"{sum(mask_list)} non-wildcard"
        )
        
        return Pattern(
            bytes=pattern_bytes,
            mask=mask_list,
            original=pattern_str
        )
    
    def _match_pattern_at_offset(self, data: bytes, offset: int, pattern: Pattern) -> bool:
        """
        Check if pattern matches at a specific offset in data.
        
        Args:
            data: Byte data to search in.
            offset: Offset in data to check.
            pattern: Pattern to match.
        
        Returns:
            True if pattern matches at offset, False otherwise.
        """
        # Check if we have enough data
        if offset + len(pattern) > len(data):
            return False
        
        # Compare each byte according to mask
        for i in range(len(pattern)):
            if pattern.mask[i]:  # Not a wildcard
                if data[offset + i] != pattern.bytes[i]:
                    return False
        
        return True
    
    def _scan_buffer(self, data: bytes, base_address: int, pattern: Pattern) -> List[int]:
        """
        Scan a buffer for pattern matches.
        
        Uses optimized search: find first non-wildcard byte, then verify full pattern.
        
        Args:
            data: Buffer to scan.
            base_address: Base address of the buffer in process memory.
            pattern: Pattern to search for.
        
        Returns:
            List of addresses where pattern was found.
        """
        results = []
        
        # Get first non-wildcard byte for optimization
        first_idx = pattern.get_first_non_wildcard_index()
        if first_idx is None:
            # All wildcards (shouldn't happen due to validation)
            return results
        
        first_byte = pattern.bytes[first_idx]
        pattern_len = len(pattern)
        
        # Search for first byte, then verify full pattern
        offset = 0
        while offset <= len(data) - pattern_len:
            # Find next occurrence of first non-wildcard byte
            try:
                # Search for first byte starting from current offset
                search_start = offset + first_idx
                idx = data.index(first_byte, search_start)
                # Calculate the actual pattern start position
                pattern_start = idx - first_idx
                
                # Verify full pattern
                if pattern_start >= 0 and self._match_pattern_at_offset(data, pattern_start, pattern):
                    address = base_address + pattern_start
                    results.append(address)
                    offset = pattern_start + 1
                else:
                    offset = pattern_start + 1 if pattern_start >= 0 else idx + 1
            except ValueError:
                # No more occurrences of first byte
                break
        
        return results
    
    def scan_pattern(self, pattern: Pattern, regions: List[MemoryRegion],
                    buffer_size: int = 256 * 1024) -> List[int]:
        """
        Search for pattern in specified memory regions.
        
        Maintains an overlap buffer between reads to detect patterns spanning
        buffer boundaries.
        
        Args:
            pattern: Parsed pattern to search for.
            regions: List of memory regions to scan.
            buffer_size: Size of read buffer in bytes (default: 256KB).
        
        Returns:
            List of addresses where pattern was found.
        
        Raises:
            ValueError: If pattern or regions are invalid.
        """
        if not pattern:
            raise ValueError("Pattern cannot be None")
        
        if not regions:
            logger.warning("No regions provided for scanning")
            return []
        
        pattern_len = len(pattern)
        overlap_size = pattern_len - 1
        
        all_results = []
        
        for region in regions:
            if not region.is_readable:
                continue
            
            region_results = []
            address = region.base_address
            region_end = region.base_address + region.size
            overlap_buffer = b""
            
            while address < region_end:
                # Calculate read size
                remaining = region_end - address
                read_size = min(buffer_size, remaining)
                
                if read_size <= 0:
                    break
                
                # Read memory
                data, success = self.memory_manager.read_memory(address, read_size)
                
                if not data:
                    # Skip to next buffer
                    address += buffer_size
                    overlap_buffer = b""
                    continue
                
                # Combine with overlap buffer from previous read
                if overlap_buffer:
                    search_data = overlap_buffer + data
                    search_base = address - len(overlap_buffer)
                else:
                    search_data = data
                    search_base = address
                
                # Scan the buffer
                buffer_results = self._scan_buffer(search_data, search_base, pattern)
                region_results.extend(buffer_results)
                
                # Save overlap for next iteration
                if len(data) >= overlap_size:
                    overlap_buffer = data[-overlap_size:]
                else:
                    overlap_buffer = data
                
                # Move to next buffer
                address += len(data)
            
            all_results.extend(region_results)
            
            if region_results:
                logger.debug(
                    f"Found {len(region_results)} matches in region "
                    f"0x{region.base_address:X}-0x{region_end:X}"
                )
        
        logger.info(
            f"Pattern scan complete: {len(all_results)} matches found "
            f"across {len(regions)} regions"
        )
        
        return all_results
    
    def scan_pattern_in_module(self, pattern: Pattern, module_base: int,
                              module_size: int) -> List[int]:
        """
        Search for pattern within a specific module's address range.
        
        This is a convenience method that restricts the search to a single
        module's memory range.
        
        Args:
            pattern: Parsed pattern to search for.
            module_base: Base address of the module.
            module_size: Size of the module in bytes.
        
        Returns:
            List of addresses where pattern was found.
        
        Raises:
            ValueError: If pattern or module info is invalid.
        """
        if not pattern:
            raise ValueError("Pattern cannot be None")
        
        if module_base < 0:
            raise ValueError(f"Invalid module base address: 0x{module_base:X}")
        
        if module_size <= 0:
            raise ValueError(f"Invalid module size: {module_size}")
        
        logger.info(
            f"Scanning pattern in module range "
            f"0x{module_base:X}-0x{module_base + module_size:X}"
        )
        
        # Query the memory region at module base
        region = self.memory_manager.query_memory_region(module_base)
        
        if not region:
            logger.warning(f"Could not query memory region at 0x{module_base:X}")
            return []
        
        # Create a synthetic region for the module range
        # We'll scan from module_base to module_base + module_size
        module_end = module_base + module_size
        
        # Collect all regions that overlap with the module range
        regions_to_scan = []
        current_address = module_base
        
        while current_address < module_end:
            region = self.memory_manager.query_memory_region(current_address)
            
            if not region:
                # Move forward by a page
                current_address += 0x1000
                continue
            
            # Check if region overlaps with module range
            region_end = region.base_address + region.size
            
            if region.base_address < module_end and region_end > module_base:
                # Region overlaps with module range
                # Adjust region boundaries to module range
                adjusted_base = max(region.base_address, module_base)
                adjusted_end = min(region_end, module_end)
                adjusted_size = adjusted_end - adjusted_base
                
                if adjusted_size > 0 and region.is_readable:
                    # Create adjusted region
                    from dataclasses import replace
                    adjusted_region = replace(
                        region,
                        base_address=adjusted_base,
                        size=adjusted_size
                    )
                    regions_to_scan.append(adjusted_region)
            
            # Move to next region
            current_address = region_end
        
        if not regions_to_scan:
            logger.warning(
                f"No readable regions found in module range "
                f"0x{module_base:X}-0x{module_end:X}"
            )
            return []
        
        # Scan the collected regions
        return self.scan_pattern(pattern, regions_to_scan)
