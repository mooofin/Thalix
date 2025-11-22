# Windows Memory Editor - Project Structure

## Overview

This document describes the project structure for the Windows Memory Editor application.

## Directory Structure

```
.
├── src/                    # Source code
│   ├── core/              # Core Windows API abstractions and business logic
│   ├── gui/               # GUI components
│   └── utils/             # Utility functions and helpers
├── tests/                 # Test suite
├── logs/                  # Application logs (auto-generated)
├── memory_editor.py       # Main entry point
└── requirements.txt       # Python dependencies
```

## Module Descriptions

### src/core/
Contains Windows API abstraction layer and core business logic:
- Process management (enumeration, attachment)
- Memory operations (read, write, query)
- Memory scanning engine
- Value freezing system
- Pointer scanner
- Disassembly/assembly engines
- AOB (Array of Bytes) scanner

### src/gui/
Contains all GUI components:
- Main window
- Process list widget
- Memory region viewer
- Scanner interface
- Address table
- Pointer scanner window
- Memory viewer/hex editor
- Code patcher interface

### src/utils/
Contains utility functions:
- Logging configuration
- Error handling
- Data type conversions
- Helper functions

### tests/
Contains test suite:
- Unit tests
- Integration tests
- Test harness application

### logs/
Auto-generated directory for application logs:
- Rotating log files (max 10MB per file)
- Up to 5 backup files retained
- Daily log files with timestamp

## Dependencies

The project requires the following Python packages (see requirements.txt):

- **capstone** (>=5.0.0): Disassembly engine for x86/x64 instructions
- **keystone-engine** (>=0.9.2): Assembly engine for x86/x64 instructions
- **numpy** (>=1.24.0): Efficient array operations for scan results
- **pywin32** (>=306): Windows API access (alternative: ctypes)
- **customtkinter** (>=5.2.0): Modern GUI framework
- **psutil** (>=5.9.0): Process utilities
- **Pillow** (>=9.0.0): Image processing

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python memory_editor.py
```

## Logging

The application uses Python's logging module with:
- File rotation (10MB max per file, 5 backups)
- Console output for real-time monitoring
- Structured log format: `[timestamp] [level] [component] message`
- Log files stored in `logs/` directory

## Development Workflow

1. **Task 1**: ✅ Project structure and core infrastructure (COMPLETED)
2. **Task 2**: Implement Windows API abstraction layer
3. **Task 3**: Implement error handling infrastructure
4. **Task 4**: Implement data type system
5. **Task 5**: Implement memory scanning engine
6. ... (see tasks.md for complete list)

## Notes

- The project follows a layered architecture with clear separation of concerns
- All Windows API interactions are isolated in the core module
- GUI components are decoupled from business logic
- Comprehensive logging for debugging and diagnostics
- Thread-safe operations for concurrent scanning and freezing
