"""
Master test runner for Thalix
Runs all test suites and generates comprehensive report
"""

import sys
import os
import time

# Add tests directory to path
sys.path.insert(0, os.path.dirname(__file__))

import test_memory_editor
import test_gui


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def main():
    """Run all test suites"""
    start_time = time.time()
    
    print_header("THALIX COMPLETE TEST SUITE")
    print("Testing all components: Memory Editor, GUI, Process Management\n")
    
    all_success = True
    
    # Run Memory Editor tests
    print_header("1. MEMORY EDITOR TESTS")
    mem_success = test_memory_editor.run_tests()
    all_success = all_success and mem_success
    
    print("\n")
    time.sleep(0.5)
    
    # Run GUI tests
    print_header("2. GUI & PROCESS MANAGEMENT TESTS")
    gui_success = test_gui.run_tests()
    all_success = all_success and gui_success
    
    # Calculate elapsed time
    elapsed = time.time() - start_time
    
    # Print final summary
    print_header("FINAL TEST RESULTS")
    print(f"Total execution time: {elapsed:.2f} seconds\n")
    
    print("Component Results:")
    print(f"  Memory Editor:      {'✅ PASS' if mem_success else '❌ FAIL'}")
    print(f"  GUI & Process Mgmt: {'✅ PASS' if gui_success else '❌ FAIL'}")
    print()
    
    if all_success:
        print("🎉 ALL TESTS PASSED! 🎉")
        print("\nThalix is ready for release!")
    else:
        print("⚠️  SOME TESTS FAILED ⚠️")
        print("\nPlease review the failures above before releasing.")
    
    print("\n" + "=" * 80 + "\n")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
