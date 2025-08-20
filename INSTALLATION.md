# Quick Installation Guide

## Prerequisites
- ComfyUI installed and running
- FFmpeg installed on your system

## Installation Steps

1. **Copy the node**: This directory should already be in your ComfyUI `custom_nodes` folder
2. **Restart ComfyUI**: Completely restart ComfyUI to load the new node
3. **Find the node**: Look for "FFmpeg Command Runner" in the node browser under "video/ffmpeg" category

## Verify Installation

Run the installation check:
```bash
python3 install.py
```

## Test the Node

Run the test script to verify functionality:
```bash
python3 test_node.py
```

## Usage

1. Add "FFmpeg Command Runner" to your workflow
2. Set input MP4 file paths
3. Set output file path
4. Write your FFmpeg command using placeholders:
   - `{input1}` - First input file
   - `{input2}` - Second input file (optional)
   - `{input3}` - Third input file (optional)
   - `{output}` - Output file path
5. Set execute to True
6. Run the workflow

## Example Commands

- **Basic conversion**: `ffmpeg -i {input1} -c:v libx264 -preset fast -crf 23 {output}`
- **Extract audio**: `ffmpeg -i {input1} -vn -c:a mp3 -b:a 192k {output}`
- **Video concatenation**: `ffmpeg -i {input1} -i {input2} -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" {output}`

## Troubleshooting

- **Node not appearing**: Make sure ComfyUI was completely restarted
- **FFmpeg errors**: Check your command syntax and ensure FFmpeg is installed
- **File not found**: Verify input file paths are correct
