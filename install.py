#!/usr/bin/env python3
"""
Installation script for the ComfyUI FFmpeg Node.
This script checks dependencies and provides installation instructions.
"""

import os
import sys
import subprocess

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, check=True)
        print("✅ FFmpeg is installed")
        print(f"   Version: {result.stdout.split('\n')[0]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg is not installed")
        return False

def check_comfyui():
    """Check if we're in a ComfyUI custom_nodes directory."""
    current_dir = os.path.basename(os.getcwd())
    parent_dir = os.path.basename(os.path.dirname(os.getcwd()))
    
    if current_dir == "comfyui-ffmpeg-node" and parent_dir == "custom_nodes":
        print("✅ Node is in the correct ComfyUI custom_nodes directory")
        return True
    else:
        print("❌ Node is not in a ComfyUI custom_nodes directory")
        print(f"   Current: {os.getcwd()}")
        return False

def main():
    """Main installation check."""
    print("ComfyUI FFmpeg Node - Installation Check")
    print("=" * 50)
    
    ffmpeg_ok = check_ffmpeg()
    comfyui_ok = check_comfyui()
    
    print("\n" + "=" * 50)
    
    if ffmpeg_ok and comfyui_ok:
        print("✅ All checks passed!")
        print("\nTo complete installation:")
        print("1. Restart ComfyUI")
        print("2. Look for 'FFmpeg Command Runner' in the node browser")
        print("3. The node will appear under 'video/ffmpeg' category")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        
        if not ffmpeg_ok:
            print("\nTo install FFmpeg:")
            print("  macOS: brew install ffmpeg")
            print("  Ubuntu/Debian: sudo apt install ffmpeg")
            print("  Windows: Download from https://ffmpeg.org/download.html")
        
        if not comfyui_ok:
            print("\nTo install this node:")
            print("1. Copy this directory to your ComfyUI custom_nodes folder")
            print("2. Restart ComfyUI")

if __name__ == "__main__":
    main()
