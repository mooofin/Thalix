#!/usr/bin/env python3
"""
Elden Ring Stutter Fix GUI Launcher
A cute and modern GUI application for managing CPU affinity
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from elden_ring_gui import main
    if __name__ == "__main__":
        print("Starting Elden Ring Stutter Fix GUI...")
        main()
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    input("Press Enter to exit...")
except Exception as e:
    print(f"Error starting application: {e}")
    input("Press Enter to exit...")
