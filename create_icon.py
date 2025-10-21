#!/usr/bin/env python3
"""
Icon creation script for Elden Ring Stutter Fix GUI
Creates proper icon files from your Elden Ring images
"""

import os
from PIL import Image

def create_icon():
    """Create icon files from Elden Ring images"""
    assets_dir = "assets"
    
    # Check if assets directory exists
    if not os.path.exists(assets_dir):
        print("Assets directory not found!")
        return
    
    # List available images
    print("Available images in assets folder:")
    for file in os.listdir(assets_dir):
        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"  - {file}")
    
    print("\nCreating icon files...")
    
    # Try to create icon from elden_ring_icon.jpg
    icon_source = os.path.join(assets_dir, "elden_ring_icon.jpg")
    if os.path.exists(icon_source):
        try:
            # Create different icon sizes
            sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            
            for size in sizes:
                img = Image.open(icon_source)
                img = img.resize(size, Image.Resampling.LANCZOS)
                icon_path = os.path.join(assets_dir, f"icon_{size[0]}x{size[1]}.ico")
                img.save(icon_path)
                print(f"Created: {icon_path}")
            
            # Create main icon
            img = Image.open(icon_source)
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
            main_icon = os.path.join(assets_dir, "app_icon.ico")
            img.save(main_icon)
            print(f"Created main icon: {main_icon}")
            
        except Exception as e:
            print(f"Error creating icon: {e}")
    else:
        print(f"Icon source not found: {icon_source}")
    
    # Try to create background from elden_ring_bg.jpg
    bg_source = os.path.join(assets_dir, "elden_ring_bg.jpg")
    if os.path.exists(bg_source):
        try:
            img = Image.open(bg_source)
            # Create a smaller version for the GUI
            img_small = img.resize((1000, 800), Image.Resampling.LANCZOS)
            bg_optimized = os.path.join(assets_dir, "elden_ring_bg_optimized.jpg")
            img_small.save(bg_optimized, quality=85)
            print(f"Created optimized background: {bg_optimized}")
            
        except Exception as e:
            print(f"Error creating background: {e}")
    else:
        print(f"Background source not found: {bg_source}")

def setup_window_icon():
    """Set up window icon for the application"""
    try:
        import tkinter as tk
        from PIL import ImageTk
        
        # Create a simple test window to set icon
        root = tk.Tk()
        root.title("Elden Ring Stutter Fix")
        
        # Try to set icon
        icon_path = os.path.join("assets", "app_icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
            print("Window icon set successfully!")
        else:
            print("Icon file not found, creating it...")
            create_icon()
            
        root.destroy()
        
    except Exception as e:
        print(f"Error setting window icon: {e}")

if __name__ == "__main__":
    print("Elden Ring Asset Setup")
    print("=" * 30)
    create_icon()
    print("\nIcon setup complete!")
    print("\nTo use the icon in your GUI, the application will automatically")
    print("try to load the icon from assets/app_icon.ico")
