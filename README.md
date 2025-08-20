# ComfyUI FFmpeg Node

A custom ComfyUI node that allows you to run FFmpeg commands directly within your ComfyUI workflows.

## Features

- **Multiple Input Support**: Up to 2 MP4 input files
- **Smart Concatenation**: Intelligent aspect ratio detection and automatic cropping
- **Customizable Commands**: Full FFmpeg command control with placeholder substitution
- **Output Path Control**: Specify where the result file should be saved
- **Execution Control**: Toggle to enable/disable execution
- **Error Handling**: Comprehensive error reporting for debugging

## Installation

1. Clone or download this repository to your ComfyUI `custom_nodes` directory
2. Restart ComfyUI
3. The node will appear in the node browser under "video/ffmpeg"

## Usage

### Basic Setup

1. Add the "FFmpeg Command Runner" node to your workflow
2. Configure the inputs:
   - **Input MP4 1**: Path to your first MP4 file (required)
   - **Input MP4 2**: Path to second MP4 file (optional, required for SMART_CONCAT)
   - **Output Path**: Where to save the result file
   - **FFmpeg Command**: Use `SMART_CONCAT` for intelligent concatenation or custom FFmpeg commands
   - **Execute**: Toggle to run the command

## Smart Concatenation

The node features intelligent video concatenation that automatically detects aspect ratios and applies appropriate cropping to create seamless video combinations.

### How SMART_CONCAT Works

1. **Analyzes both input videos** using ffprobe to detect dimensions
2. **Determines aspect ratios**:
   - **Landscape**: width > height (e.g., 1920×1080)
   - **Portrait**: height > width (e.g., 1080×1920)
   - **Square**: width = height (e.g., 1080×1080)
3. **Chooses output resolution**:
   - Both landscape/square → **1920×1080**
   - Both portrait/square → **1080×1920**
   - Mixed orientations → **1080×1080** (square)
4. **Applies intelligent cropping** (not squeezing) to maintain visual quality
5. **Concatenates videos** with consistent resolution and smooth transitions

### SMART_CONCAT Usage

Simply use `SMART_CONCAT` as your FFmpeg command, with optional parameters:

#### Basic Smart Concat
```
SMART_CONCAT
```
*Uses defaults: trim1=0.5:4.5, trim2=0.5:7.5, crf=18, preset=veryfast*

#### Custom Trim Times
```
SMART_CONCAT trim1=1.0:5.0 trim2=2.0:8.0
```

#### Custom Quality Settings
```
SMART_CONCAT crf=20 preset=slow
```

#### Full Custom Parameters
```
SMART_CONCAT trim1=0:3 trim2=1:6 crf=15 preset=medium
```

### SMART_CONCAT Parameters

- **trim1=start:end** - Trim timing for first video (seconds)
- **trim2=start:end** - Trim timing for second video (seconds)
- **crf=value** - Video quality (lower = better, 15-25 recommended)
- **preset=value** - Encoding speed (ultrafast, veryfast, fast, medium, slow, veryslow)

### Command Placeholders

For custom FFmpeg commands, use these placeholders:

- `{input1}` - First input file
- `{input2}` - Second input file (if provided)
- `{output}` - Output file path

### Example Commands

#### Basic Video Conversion
```
ffmpeg -i {input1} -c:v libx264 -preset fast -crf 23 {output}
```

#### Video Concatenation
```
ffmpeg -i {input1} -i {input2} -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" {output}
```

#### Video with Custom Settings
```
ffmpeg -i {input1} -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 128k {output}
```

#### Extract Audio
```
ffmpeg -i {input1} -vn -c:a mp3 -b:a 192k {output}
```

## Requirements

- ComfyUI installed and running
- FFmpeg installed on your system
- Python 3.7+

## FFmpeg Installation

### macOS
```bash
brew install ffmpeg
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### Windows
Download from [FFmpeg official website](https://ffmpeg.org/download.html)

## Troubleshooting

- **"FFmpeg command failed"**: Check your FFmpeg command syntax and ensure FFmpeg is installed
- **"Input file not found"**: Verify the file paths are correct and files exist
- **"Output file not found"**: Check if the output directory is writable

## Security Note

This node executes shell commands. Only use it with trusted FFmpeg commands and input files.

## License

MIT License - feel free to modify and distribute.
