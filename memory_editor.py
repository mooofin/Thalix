"""
Windows Memory Editor - Main entry point.

A tool for scanning and modifying process memory on Windows.
"""

import sys
import logging
from pathlib import Path
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/memory_editor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    logger.info("Starting Windows Memory Editor")
    
    try:
        from src.gui import MainWindow
        
        app = MainWindow()
        app.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
