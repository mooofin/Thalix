#!/usr/bin/env python3
"""
Asset setup script for Elden Ring Stutter Fix GUI
This script helps set up the background image and icon from your Elden Ring images
"""

import os
import shutil
from PIL import Image, ImageTk

def setup_assets():
    """Set up the assets for the Elden Ring GUI"""
    print("Setting up Elden Ring assets...")
    
    # Create assets directory if it doesn't exist
    assets_dir = "assets"
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
        print(f"Created {assets_dir} directory")
    
    # Instructions for the user
    print("\n" + "="*60)
    print("ELDEN RING ASSET SETUP")
    print("="*60)
    print("\nTo complete the setup, please:")
    print("\n1. Save your Elden Ring background image as:")
    print("   assets/elden_ring_bg.jpg")
    print("   (This will be used as the app background)")
    
    print("\n2. Save your Elden Ring character image as:")
    print("   assets/elden_ring_icon.png")
    print("   (This will be used as the app icon)")
    
    print("\n3. The background image should be:")
    print("   - High resolution (1920x1080 or higher)")
    print("   - Dark fantasy aesthetic")
    print("   - JPG format")
    
    print("\n4. The icon image should be:")
    print("   - Square format (512x512 or 256x256)")
    print("   - PNG format with transparency")
    print("   - Character portrait or symbol")
    
    print("\n" + "="*60)
    print("After adding your images, run the GUI with:")
    print("python run_gui.py")
    print("="*60)

def create_icon_from_image(image_path, output_path, size=(256, 256)):
    """Create an icon from an image"""
    try:
        if os.path.exists(image_path):
            img = Image.open(image_path)
            img = img.resize(size, Image.Resampling.LANCZOS)
            img.save(output_path)
            print(f"Created icon: {output_path}")
            return True
    except Exception as e:
        print(f"Error creating icon: {e}")
    return False

def create_background_from_image(image_path, output_path, size=(1920, 1080)):
    """Create a background from an image"""
    try:
        if os.path.exists(image_path):
            img = Image.open(image_path)
            img = img.resize(size, Image.Resampling.LANCZOS)
            img.save(output_path, quality=85)
            print(f"Created background: {output_path}")
            return True
    except Exception as e:
        print(f"Error creating background: {e}")
    return False

if __name__ == "__main__":
    setup_assets()
