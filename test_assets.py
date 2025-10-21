#!/usr/bin/env python3
"""
Test script to check assets and their properties
"""

import os
from PIL import Image

def test_assets():
    """Test all assets in the assets folder"""
    assets_dir = "assets"
    
    if not os.path.exists(assets_dir):
        print("❌ Assets directory not found!")
        return
    
    print("🔍 Testing Elden Ring Assets")
    print("=" * 40)
    
    # List all files
    files = os.listdir(assets_dir)
    print(f"📁 Found {len(files)} files in assets folder:")
    for file in files:
        print(f"   - {file}")
    
    print("\n🖼️  Testing image files:")
    
    # Test each image file
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.ico'))]
    
    for img_file in image_files:
        img_path = os.path.join(assets_dir, img_file)
        try:
            with Image.open(img_path) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format
                print(f"✅ {img_file}: {width}x{height}, {mode}, {format_name}")
        except Exception as e:
            print(f"❌ {img_file}: Error - {e}")
    
    print("\n🎯 Recommended usage:")
    print("   Background: elden_ring_bg.jpg (should be landscape)")
    print("   Icon: app_icon.ico (should be square)")
    
    # Test specific files
    print("\n🔧 Testing specific files:")
    
    # Test background
    bg_files = ["elden_ring_bg.jpg", "elden_ring_bg_optimized.jpg", "image1.jpg", "images.jpg"]
    for bg_file in bg_files:
        bg_path = os.path.join(assets_dir, bg_file)
        if os.path.exists(bg_path):
            try:
                with Image.open(bg_path) as img:
                    width, height = img.size
                    print(f"✅ Background candidate: {bg_file} ({width}x{height})")
            except Exception as e:
                print(f"❌ Background candidate: {bg_file} - Error: {e}")
    
    # Test icons
    icon_files = ["app_icon.ico", "elden_ring_icon.jpg", "er.png"]
    for icon_file in icon_files:
        icon_path = os.path.join(assets_dir, icon_file)
        if os.path.exists(icon_path):
            try:
                with Image.open(icon_path) as img:
                    width, height = img.size
                    print(f"✅ Icon candidate: {icon_file} ({width}x{height})")
            except Exception as e:
                print(f"❌ Icon candidate: {icon_file} - Error: {e}")

if __name__ == "__main__":
    test_assets()
