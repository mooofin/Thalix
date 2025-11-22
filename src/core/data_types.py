"""
Data type system for memory scanning and value handling.

This module provides:
- DataType enumeration for all supported data types
- Value parsing and validation functions
- Value formatting functions (hex, decimal, float)
- Struct pack/unpack helpers for reading and writing typed values
"""

import struct
from enum import Enum
from typing import Any, Union, Tuple


class DataType(Enum):
    """Enumeration of supported data types for memory operations.
    
    Each enum value is a tuple of (size_in_bytes, struct_format_char).
    """
    INT8 = (1, 'b')
    UINT8 = (1, 'B')
    INT16 = (2, 'h')
    UINT16 = (2, 'H')
    INT32 = (4, 'i')
    UINT32 = (4, 'I')
    INT64 = (8, 'q')
    UINT64 = (8, 'Q')
    FLOAT = (4, 'f')
    DOUBLE = (8, 'd')
    
    @property
    def size(self) -> int:
        """Get the size in bytes for this data type."""
        return self.value[0]
    
    @property
    def format_char(self) -> str:
        """Get the struct format character for this data type."""
        return self.value[1]
    
    @property
    def is_signed(self) -> bool:
        """Check if this is a signed integer type."""
        return self in (DataType.INT8, DataType.INT16, DataType.INT32, DataType.INT64)
    
    @property
    def is_unsigned(self) -> bool:
        """Check if this is an unsigned integer type."""
        return self in (DataType.UINT8, DataType.UINT16, DataType.UINT32, DataType.UINT64)
    
    @property
    def is_integer(self) -> bool:
        """Check if this is any integer type (signed or unsigned)."""
        return self.is_signed or self.is_unsigned
    
    @property
    def is_float(self) -> bool:
        """Check if this is a floating point type."""
        return self in (DataType.FLOAT, DataType.DOUBLE)
    
    def get_range(self) -> Tuple[Union[int, float], Union[int, float]]:
        """Get the valid range for this data type.
        
        Returns:
            Tuple of (min_value, max_value)
        """
        if self == DataType.INT8:
            return (-128, 127)
        elif self == DataType.UINT8:
            return (0, 255)
        elif self == DataType.INT16:
            return (-32768, 32767)
        elif self == DataType.UINT16:
            return (0, 65535)
        elif self == DataType.INT32:
            return (-2147483648, 2147483647)
        elif self == DataType.UINT32:
            return (0, 4294967295)
        elif self == DataType.INT64:
            return (-9223372036854775808, 9223372036854775807)
        elif self == DataType.UINT64:
            return (0, 18446744073709551615)
        elif self == DataType.FLOAT:
            return (-3.4028235e+38, 3.4028235e+38)
        elif self == DataType.DOUBLE:
            return (-1.7976931348623157e+308, 1.7976931348623157e+308)
        else:
            raise ValueError(f"Unknown data type: {self}")


class ValueParser:
    """Utility class for parsing and validating values for different data types."""
    
    @staticmethod
    def parse_value(value_str: str, data_type: DataType) -> Any:
        """Parse a string value into the appropriate Python type.
        
        Args:
            value_str: String representation of the value
            data_type: Target data type
            
        Returns:
            Parsed value in appropriate Python type
            
        Raises:
            ValueError: If the value cannot be parsed or is out of range
        """
        value_str = value_str.strip()
        
        # Handle hex notation (0x prefix)
        is_hex = value_str.lower().startswith('0x')
        
        try:
            if data_type.is_integer:
                # Parse integer (hex or decimal)
                if is_hex:
                    value = int(value_str, 16)
                else:
                    value = int(value_str, 10)
                
                # Validate range
                min_val, max_val = data_type.get_range()
                if value < min_val or value > max_val:
                    raise ValueError(
                        f"Value {value} is out of range for {data_type.name} "
                        f"(valid range: {min_val} to {max_val})"
                    )
                
                return value
            
            elif data_type.is_float:
                # Parse floating point
                if is_hex:
                    raise ValueError("Hexadecimal notation not supported for floating point values")
                
                value = float(value_str)
                
                # Validate range (approximate)
                min_val, max_val = data_type.get_range()
                if value < min_val or value > max_val:
                    raise ValueError(
                        f"Value {value} is out of range for {data_type.name}"
                    )
                
                return value
            
            else:
                raise ValueError(f"Unknown data type: {data_type}")
                
        except ValueError as e:
            if "invalid literal" in str(e) or "could not convert" in str(e):
                raise ValueError(f"Invalid value '{value_str}' for {data_type.name}")
            raise
    
    @staticmethod
    def validate_value(value: Any, data_type: DataType) -> bool:
        """Validate that a value is appropriate for the given data type.
        
        Args:
            value: Value to validate
            data_type: Target data type
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if data_type.is_integer:
                if not isinstance(value, int):
                    return False
                min_val, max_val = data_type.get_range()
                return min_val <= value <= max_val
            
            elif data_type.is_float:
                if not isinstance(value, (int, float)):
                    return False
                value = float(value)
                min_val, max_val = data_type.get_range()
                return min_val <= value <= max_val
            
            return False
        except (ValueError, TypeError):
            return False


class ValueFormatter:
    """Utility class for formatting values for display."""
    
    @staticmethod
    def format_hex(value: Any, data_type: DataType) -> str:
        """Format a value as hexadecimal.
        
        Args:
            value: Value to format
            data_type: Data type of the value
            
        Returns:
            Hexadecimal string representation
        """
        if data_type.is_integer:
            # Format with appropriate width (2 chars per byte)
            width = data_type.size * 2
            if data_type.is_unsigned:
                return f"0x{value:0{width}X}"
            else:
                # For signed integers, convert to unsigned representation
                if value < 0:
                    # Two's complement representation
                    max_unsigned = (1 << (data_type.size * 8))
                    value = max_unsigned + value
                return f"0x{value:0{width}X}"
        
        elif data_type.is_float:
            # For floats, show hex representation of bytes
            bytes_data = struct.pack(f'<{data_type.format_char}', value)
            hex_str = ''.join(f'{b:02X}' for b in bytes_data)
            return f"0x{hex_str}"
        
        return str(value)
    
    @staticmethod
    def format_decimal(value: Any, data_type: DataType) -> str:
        """Format a value as decimal.
        
        Args:
            value: Value to format
            data_type: Data type of the value
            
        Returns:
            Decimal string representation
        """
        if data_type.is_integer:
            return str(value)
        elif data_type.is_float:
            # Use appropriate precision
            if data_type == DataType.FLOAT:
                return f"{value:.7g}"  # ~7 significant digits for float
            else:  # DOUBLE
                return f"{value:.15g}"  # ~15 significant digits for double
        return str(value)
    
    @staticmethod
    def format_float(value: Any, data_type: DataType) -> str:
        """Format a value as floating point (alias for format_decimal for floats).
        
        Args:
            value: Value to format
            data_type: Data type of the value
            
        Returns:
            Float string representation
        """
        if data_type.is_float:
            return ValueFormatter.format_decimal(value, data_type)
        elif data_type.is_integer:
            # Convert integer to float representation
            return f"{float(value):.2f}"
        return str(value)


class ValuePacker:
    """Utility class for packing and unpacking values to/from bytes."""
    
    @staticmethod
    def pack(value: Any, data_type: DataType) -> bytes:
        """Pack a value into bytes according to its data type.
        
        Args:
            value: Value to pack
            data_type: Data type of the value
            
        Returns:
            Bytes representation of the value (little-endian)
            
        Raises:
            struct.error: If the value cannot be packed
        """
        format_str = f'<{data_type.format_char}'
        return struct.pack(format_str, value)
    
    @staticmethod
    def unpack(data: bytes, data_type: DataType) -> Any:
        """Unpack bytes into a value according to the data type.
        
        Args:
            data: Bytes to unpack
            data_type: Data type to unpack as
            
        Returns:
            Unpacked value
            
        Raises:
            struct.error: If the data cannot be unpacked
            ValueError: If data length doesn't match data type size
        """
        if len(data) < data_type.size:
            raise ValueError(
                f"Insufficient data: expected {data_type.size} bytes, got {len(data)}"
            )
        
        format_str = f'<{data_type.format_char}'
        return struct.unpack(format_str, data[:data_type.size])[0]
    
    @staticmethod
    def unpack_multiple(data: bytes, data_type: DataType) -> list:
        """Unpack multiple values from bytes.
        
        Args:
            data: Bytes to unpack
            data_type: Data type to unpack as
            
        Returns:
            List of unpacked values
            
        Raises:
            struct.error: If the data cannot be unpacked
        """
        value_size = data_type.size
        value_count = len(data) // value_size
        
        if value_count == 0:
            return []
        
        format_str = f'<{value_count}{data_type.format_char}'
        return list(struct.unpack(format_str, data[:value_count * value_size]))



class ComparisonType(Enum):
    """Types of comparisons supported for memory scanning."""
    EXACT = "exact"
    INCREASED = "increased"
    DECREASED = "decreased"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


class ValueComparator:
    """Utility class for comparing values during memory scanning operations."""
    
    # Default epsilon for floating point comparisons
    DEFAULT_FLOAT_EPSILON = 1e-6
    DEFAULT_DOUBLE_EPSILON = 1e-12
    
    def __init__(self, float_epsilon: float = None, double_epsilon: float = None):
        """Initialize the value comparator.
        
        Args:
            float_epsilon: Epsilon for float comparisons (default: 1e-6)
            double_epsilon: Epsilon for double comparisons (default: 1e-12)
        """
        self.float_epsilon = float_epsilon or self.DEFAULT_FLOAT_EPSILON
        self.double_epsilon = double_epsilon or self.DEFAULT_DOUBLE_EPSILON
    
    def compare_exact(self, value1: Any, value2: Any, data_type: DataType, 
                     use_epsilon: bool = False) -> bool:
        """Compare two values for exact equality.
        
        For integer types, uses bitwise equality.
        For float types, can use either bitwise equality or epsilon-based comparison.
        
        Args:
            value1: First value
            value2: Second value
            data_type: Data type of the values
            use_epsilon: If True, use epsilon-based comparison for floats
            
        Returns:
            True if values are equal, False otherwise
        """
        if data_type.is_integer:
            # Bitwise equality for integers
            return value1 == value2
        
        elif data_type.is_float:
            if use_epsilon:
                # Epsilon-based comparison for floats
                epsilon = self.float_epsilon if data_type == DataType.FLOAT else self.double_epsilon
                return abs(value1 - value2) < epsilon
            else:
                # Bitwise equality (exact bit pattern match)
                return value1 == value2
        
        return False
    
    def compare_exact_bytes(self, bytes1: bytes, bytes2: bytes) -> bool:
        """Compare two byte sequences for exact bitwise equality.
        
        This is useful for comparing raw memory without unpacking.
        
        Args:
            bytes1: First byte sequence
            bytes2: Second byte sequence
            
        Returns:
            True if byte sequences are identical, False otherwise
        """
        return bytes1 == bytes2
    
    def compare_increased(self, old_value: Any, new_value: Any, data_type: DataType) -> bool:
        """Check if new_value is greater than old_value.
        
        Args:
            old_value: Previous value
            new_value: Current value
            data_type: Data type of the values
            
        Returns:
            True if new_value > old_value, False otherwise
        """
        if data_type.is_integer or data_type.is_float:
            return new_value > old_value
        return False
    
    def compare_decreased(self, old_value: Any, new_value: Any, data_type: DataType) -> bool:
        """Check if new_value is less than old_value.
        
        Args:
            old_value: Previous value
            new_value: Current value
            data_type: Data type of the values
            
        Returns:
            True if new_value < old_value, False otherwise
        """
        if data_type.is_integer or data_type.is_float:
            return new_value < old_value
        return False
    
    def compare_changed(self, old_value: Any, new_value: Any, data_type: DataType) -> bool:
        """Check if the value has changed (bitwise comparison).
        
        Args:
            old_value: Previous value
            new_value: Current value
            data_type: Data type of the values
            
        Returns:
            True if values are different, False otherwise
        """
        # Use bitwise comparison (no epsilon for floats)
        return old_value != new_value
    
    def compare_changed_bytes(self, old_bytes: bytes, new_bytes: bytes) -> bool:
        """Check if byte sequences have changed (bitwise comparison).
        
        Args:
            old_bytes: Previous byte sequence
            new_bytes: Current byte sequence
            
        Returns:
            True if byte sequences are different, False otherwise
        """
        return old_bytes != new_bytes
    
    def compare_unchanged(self, old_value: Any, new_value: Any, data_type: DataType) -> bool:
        """Check if the value has not changed (bitwise comparison).
        
        Args:
            old_value: Previous value
            new_value: Current value
            data_type: Data type of the values
            
        Returns:
            True if values are the same, False otherwise
        """
        # Use bitwise comparison (no epsilon for floats)
        return old_value == new_value
    
    def compare_unchanged_bytes(self, old_bytes: bytes, new_bytes: bytes) -> bool:
        """Check if byte sequences have not changed (bitwise comparison).
        
        Args:
            old_bytes: Previous byte sequence
            new_bytes: Current byte sequence
            
        Returns:
            True if byte sequences are identical, False otherwise
        """
        return old_bytes == new_bytes
    
    def compare(self, old_value: Any, new_value: Any, data_type: DataType,
                comparison_type: ComparisonType, use_epsilon: bool = False) -> bool:
        """Generic comparison method that dispatches to specific comparison functions.
        
        Args:
            old_value: Previous value (or target value for EXACT)
            new_value: Current value
            data_type: Data type of the values
            comparison_type: Type of comparison to perform
            use_epsilon: If True, use epsilon-based comparison for floats in EXACT mode
            
        Returns:
            True if comparison succeeds, False otherwise
        """
        if comparison_type == ComparisonType.EXACT:
            return self.compare_exact(old_value, new_value, data_type, use_epsilon)
        elif comparison_type == ComparisonType.INCREASED:
            return self.compare_increased(old_value, new_value, data_type)
        elif comparison_type == ComparisonType.DECREASED:
            return self.compare_decreased(old_value, new_value, data_type)
        elif comparison_type == ComparisonType.CHANGED:
            return self.compare_changed(old_value, new_value, data_type)
        elif comparison_type == ComparisonType.UNCHANGED:
            return self.compare_unchanged(old_value, new_value, data_type)
        else:
            raise ValueError(f"Unknown comparison type: {comparison_type}")
