#!/usr/bin/env python3
"""
Thalix - CPU Affinity Manager
"""

import sys
import os

# Add src to path FIRST
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import thalix_gui
    if __name__ == "__main__":
        thalix_gui.main()
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
except Exception as e:
    print(f"Error starting application: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
