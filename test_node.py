#!/usr/bin/env python3
"""
Test script for the FFmpeg node.
This script tests the node functionality without requiring ComfyUI to be running.
"""

import os
import sys
import tempfile
import subprocess

# Add the current directory to the path so we can import the node
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ffmpeg_node import FFmpegNode

def test_ffmpeg_node():
    """Test the FFmpeg node functionality."""
    print("Testing FFmpeg Node...")
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        test_file = f.name
        f.write(b"test content")
    
    try:
        # Test the node
        node = FFmpegNode()
        
        # Test input validation
        print("\n1. Testing input validation...")
        result = node.run_ffmpeg(
            input_mp4_1="",
            input_mp4_2="",
            output_path="",
            ffmpeg_command="",
            execute=True
        )
        if result[0].startswith("ERROR:"):
            print(f"✅ Input validation working: {result[0]}")
        else:
            print(f"❌ Input validation failed - expected error message but got: {result[0]}")
        
        # Test with valid inputs (using a simple command)
        print("\n2. Testing with valid inputs...")
        try:
            result = node.run_ffmpeg(
                input_mp4_1=test_file,
                input_mp4_2="",
                output_path="/tmp/test_output.txt",
                ffmpeg_command="cp {input1} {output}",
                execute=True
            )
            print(f"✅ Command execution successful: {result[0]}")
        except Exception as e:
            print(f"❌ Command execution failed: {e}")
        
        # Test with execute=False
        print("\n3. Testing with execute=False...")
        try:
            result = node.run_ffmpeg(
                input_mp4_1=test_file,
                input_mp4_2="",
                output_path="/tmp/test_output.txt",
                ffmpeg_command="cp {input1} {output}",
                execute=False
            )
            print(f"✅ Execute=False working: {result[0]}")
        except Exception as e:
            print(f"❌ Execute=False failed: {e}")
            
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.unlink(test_file)
    
    print("\n✅ FFmpeg Node test completed!")

if __name__ == "__main__":
    test_ffmpeg_node()
