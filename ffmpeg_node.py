import os
import subprocess
import re
import time
import json
from datetime import datetime
from urllib.parse import urlparse

# Try to import ComfyUI modules, but don't fail if they're not available
try:
    import folder_paths
    from server import PromptServer
    COMFYUI_AVAILABLE = True
except ImportError:
    COMFYUI_AVAILABLE = False


class FFmpegNode:
    """
    A ComfyUI node that runs FFmpeg commands with URL inputs.
    Accepts HTTP/HTTPS URLs to video files and processes them with FFmpeg.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_mp4_1": ("STRING", {"default": "", "multiline": False, "placeholder": "URL to first MP4 file (e.g., https://example.com/video1.mp4)"}),
                "input_mp4_2": ("STRING", {"default": "", "multiline": False, "placeholder": "URL to second MP4 file (optional, e.g., https://example.com/video2.mp4)"}),
                "output_path": ("STRING", {"default": "", "multiline": False, "placeholder": "Complete output file path (e.g., /path/to/output.mp4)"}),
                "video_length": ("FLOAT", {"default": 4.0, "min": 0.1, "max": 60.0, "step": 0.1, "display": "number"}),
                "trim_start": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 30.0, "step": 0.1, "display": "number"}),
                "trim_end": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 30.0, "step": 0.1, "display": "number"}),
                "ffmpeg_command": ("STRING", {
                    "default": "SMART_CONCAT",
                    "multiline": True,
                    "placeholder": "FFmpeg command. Use SMART_CONCAT for intelligent aspect ratio detection and cropping, or custom commands with {inputs}/{input1}/{input2} and {output}."
                }),
                "execute": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("status_message", "output_file_path")
    FUNCTION = "run_ffmpeg"
    CATEGORY = "video/ffmpeg"
    
    def get_video_dimensions(self, video_path):
        """
        Get video dimensions using ffprobe.
        Returns (width, height) or None if failed.
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-select_streams', 'v:0', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
                return (width, height)
        except Exception as e:
            print(f"[FFmpeg Node] Error getting video dimensions for {video_path}: {str(e)}")
        return None
    
    def is_valid_url(self, url):
        """
        Check if the provided string is a valid URL.
        Returns True for valid HTTP/HTTPS URLs, False otherwise.
        """
        try:
            result = urlparse(url.strip())
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False
    
    def validate_url_input(self, url, input_name):
        """
        Validate a URL input and return error message if invalid.
        Returns None if valid, error string if invalid.
        """
        if not url.strip():
            return None  # Empty URLs are allowed (optional input)
        
        if not self.is_valid_url(url):
            return f"ERROR: {input_name} must be a valid HTTP/HTTPS URL (e.g., https://example.com/video.mp4)"
        
        return None
    
    def determine_output_resolution_and_crop(self, input1_path, input2_path, trim1_start=0.5, trim1_end=4.5, trim2_start=0.5, trim2_end=7.5):
        """
        Analyze input videos and determine the best output resolution and crop filters.
        Returns (resolution_width, resolution_height, filter_complex) or None if failed.
        """
        # Get dimensions of both videos
        dims1 = self.get_video_dimensions(input1_path)
        dims2 = self.get_video_dimensions(input2_path)
        
        if not dims1 or not dims2:
            return None
        
        w1, h1 = dims1
        w2, h2 = dims2
        
        # Determine aspect ratio categories
        # Landscape: width > height (e.g., 1920x1080)
        # Portrait: height > width (e.g., 1080x1920) 
        # Square: width == height (e.g., 1080x1080)
        
        is_landscape_1 = w1 > h1
        is_portrait_1 = h1 > w1
        is_square_1 = w1 == h1
        
        is_landscape_2 = w2 > h2
        is_portrait_2 = h2 > w2
        is_square_2 = w2 == h2
        
        # Determine output resolution based on user's requirements
        if (is_landscape_1 or is_square_1) and (is_landscape_2 or is_square_2):
            # Both are landscape/square -> output landscape 1920x1080
            target_w, target_h = 1920, 1080
        elif (is_portrait_1 or is_square_1) and (is_portrait_2 or is_square_2):
            # Both are portrait/square -> output portrait 1080x1920
            target_w, target_h = 1080, 1920
        else:
            # One landscape, one portrait -> output square 1080x1080
            target_w, target_h = 1080, 1080
        
        # Generate crop filters for each input
        def get_crop_filter(w, h, target_w, target_h, input_idx, trim_start, trim_end):
            # Calculate scale factor to fit the smaller dimension
            scale_factor = max(target_w / w, target_h / h)
            scaled_w = int(w * scale_factor)
            scaled_h = int(h * scale_factor)
            
            # Calculate crop offsets to center the crop
            crop_x = max(0, (scaled_w - target_w) // 2)
            crop_y = max(0, (scaled_h - target_h) // 2)
            
            return f"[{input_idx}:v]trim=start={trim_start}:end={trim_end},setpts=PTS-STARTPTS,scale={scaled_w}:{scaled_h},crop={target_w}:{target_h}:{crop_x}:{crop_y}[v{input_idx}]"
        
        # Generate filter complex
        filter1 = get_crop_filter(w1, h1, target_w, target_h, 0, trim1_start, trim1_end)
        filter2 = get_crop_filter(w2, h2, target_w, target_h, 1, trim2_start, trim2_end)
        
        filter_complex = f'"{filter1};{filter2};[v0][v1]concat=n=2:v=1:a=0[outv]"'
        
        print(f"[FFmpeg Node] Video 1: {w1}x{h1}, Video 2: {w2}x{h2}")
        print(f"[FFmpeg Node] Target resolution: {target_w}x{target_h}")
        print(f"[FFmpeg Node] Filter complex: {filter_complex}")
        
        return (target_w, target_h, filter_complex)
    
    def create_smart_concat_command(self, input1_path, input2_path, output_path, trim1_start=0.5, trim1_end=4.5, trim2_start=0.5, trim2_end=4.5, crf=19, preset="veryfast"):
        """
        Create a smart concat command that automatically detects aspect ratios and applies appropriate cropping.
        """
        result = self.determine_output_resolution_and_crop(input1_path, input2_path, trim1_start, trim1_end, trim2_start, trim2_end)
        if not result:
            return None
        
        target_w, target_h, filter_complex = result
        
        command = f'ffmpeg -i "{input1_path}" -i "{input2_path}" -y -filter_complex {filter_complex} -map "[outv]" -an -c:v libx264 -crf {crf} -preset {preset} "{output_path}"'
        
        return command
    
    def run_ffmpeg(self, input_mp4_1, input_mp4_2, output_path, video_length, trim_start, trim_end, ffmpeg_command, execute):
        """
        Execute the FFmpeg command with the provided inputs.
        """
        # Handle None value for execute parameter
        execute = execute if execute is not None else True
        
        if not execute:
            return ("FFmpeg execution skipped", "")
        
        # Validate inputs - return error messages instead of raising exceptions
        # Handle None values safely
        input_mp4_1 = input_mp4_1 or ""
        input_mp4_2 = input_mp4_2 or ""
        output_path = output_path or ""
        ffmpeg_command = ffmpeg_command or ""
        
        if not input_mp4_1.strip():
            return ("ERROR: At least one input MP4 URL is required", "")
        
        if not output_path.strip():
            return ("ERROR: Output path is required", "")
        
        if not ffmpeg_command.strip():
            return ("ERROR: FFmpeg command is required", "")
        
        # Validate timing parameters - handle None values
        video_length = video_length if video_length is not None else 4.0
        trim_start = trim_start if trim_start is not None else 0.5
        trim_end = trim_end if trim_end is not None else 0.5
        
        if video_length <= 0:
            return ("ERROR: Video length must be greater than 0", "")
        
        if trim_start < 0:
            return ("ERROR: Trim start cannot be negative", "")
        
        if trim_end < 0:
            return ("ERROR: Trim end cannot be negative", "")
        
        if trim_start + video_length > 3600:  # 1 hour safety limit
            return ("ERROR: Trim start + video length cannot exceed 1 hour", "")
        
        # Ensure output_path has a filename (not just a directory)
        if os.path.isdir(output_path) or output_path.endswith('/') or output_path.endswith('\\'):
            return ("ERROR: Output path must include a filename (e.g., /path/to/output.mp4)", "")
        
        # Validate URL inputs
        url_error = self.validate_url_input(input_mp4_1, "First input URL")
        if url_error:
            return (url_error, "")
        
        if input_mp4_2.strip():
            url_error = self.validate_url_input(input_mp4_2, "Second input URL")
            if url_error:
                return (url_error, "")
        
        # Prepare input URLs list
        input_files = []
        if input_mp4_1.strip():
            input_files.append(input_mp4_1.strip())
        if input_mp4_2.strip():
            input_files.append(input_mp4_2.strip())
        
        # Validate filter_complex usage
        if "[1:v]" in ffmpeg_command and len(input_files) < 2:
            return (f"ERROR: Command references [1:v] (second input) but only {len(input_files)} input URL(s) provided", "")
        if "[1:a]" in ffmpeg_command and len(input_files) < 2:
            return (f"ERROR: Command references [1:a] (second input audio) but only {len(input_files)} input URL(s) provided", "")
        
        # Check for unsupported third input references
        if any(ref in ffmpeg_command for ref in ["[2:v]", "[2:a]", "{input3}"]):
            return ("ERROR: This node only supports 2 inputs. Third input references ([2:v], [2:a], {input3}) are not supported", "")
        
        # Add unique timestamp to output filename
        output_dir = os.path.dirname(output_path)
        output_filename = os.path.basename(output_path)
        
        # Split filename and extension
        if '.' in output_filename:
            name_part, ext_part = os.path.splitext(output_filename)
        else:
            name_part = output_filename
            ext_part = '.mp4'  # Default extension if none provided
        
        # Generate timestamp (YYYYMMDD_HHMMSS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create new filename with timestamp
        timestamped_filename = f"{name_part}_{timestamp}{ext_part}"
        output_path = os.path.join(output_dir, timestamped_filename) if output_dir else timestamped_filename
        
        print(f"[FFmpeg Node] Output filename with timestamp: {output_path}")
        
        # Check for smart concat command
        if "SMART_CONCAT" in ffmpeg_command.upper():
            if len(input_files) != 2:
                return ("ERROR: SMART_CONCAT requires exactly 2 input URLs", "")
            
            # Calculate trim times based on parameters
            # Both videos use the same timing parameters
            trim1_start = trim_start
            trim1_end = trim_start + video_length
            trim2_start = trim_start  
            trim2_end = trim_start + video_length
            
            # Default encoding parameters (can still be overridden in command)
            crf = 18
            preset = "veryfast"
            
            # Look for encoding parameters in the command (optional overrides)
            import re
            crf_match = re.search(r'crf=(\d+)', ffmpeg_command)
            if crf_match:
                crf = int(crf_match.group(1))
            
            preset_match = re.search(r'preset=(\w+)', ffmpeg_command)
            if preset_match:
                preset = preset_match.group(1)
            
            print(f"[FFmpeg Node] Using timing - Start: {trim_start}s, Length: {video_length}s, End trim: {trim_end}s")
            print(f"[FFmpeg Node] Calculated trim times - Video1: {trim1_start}-{trim1_end}s, Video2: {trim2_start}-{trim2_end}s")
            
            # Generate the smart concat command
            smart_command = self.create_smart_concat_command(
                input_files[0], input_files[1], output_path,
                trim1_start, trim1_end, trim2_start, trim2_end, crf, preset
            )
            
            if not smart_command:
                return ("ERROR: Failed to analyze video dimensions for smart concat", "")
            
            command = smart_command
        else:
            # Prepare the command by replacing placeholders
            command = ffmpeg_command
            
            # Build input parameters automatically
            input_params = ""
            for i, input_file in enumerate(input_files):
                input_params += f'-i "{input_file}" '
            
            # Replace input placeholders
            if len(input_files) >= 1:
                command = command.replace("{input1}", f'"{input_files[0]}"')
            if len(input_files) >= 2:
                command = command.replace("{input2}", f'"{input_files[1]}"')
            
            # Replace special {inputs} placeholder with all input parameters
            command = command.replace("{inputs}", input_params.strip())
            
            # Replace output placeholder
            command = command.replace("{output}", f'"{output_path}"')
        
        # If command doesn't contain explicit -i parameters, try to auto-fix
        if command.startswith("ffmpeg ") and " -i " not in command:
            # Insert input parameters after "ffmpeg"
            command = command.replace("ffmpeg ", f"ffmpeg {input_params}", 1)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                return (f"ERROR: Could not create output directory: {str(e)}", "")
        
        try:
            # Log the command for debugging
            print(f"[FFmpeg Node] Executing command: {command}")
            
            # Execute the FFmpeg command with real-time progress
            return self._execute_ffmpeg_with_progress(command, output_path)
                
        except Exception as e:
            error_msg = f"ERROR: Unexpected error running FFmpeg: {str(e)}. Command: {command}"
            return (error_msg, "")
    
    def _execute_ffmpeg_with_progress(self, command, output_path):
        """
        Execute FFmpeg command with real-time progress display.
        """
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        output_lines = []
        duration = None
        
        print(f"[FFmpeg Node] Starting FFmpeg process...")
        
        try:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    
                    # Parse duration from FFmpeg output
                    if "Duration:" in line and duration is None:
                        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}', line)
                        if duration_match:
                            hours, minutes, seconds = map(int, duration_match.groups())
                            duration = hours * 3600 + minutes * 60 + seconds
                            print(f"[FFmpeg Node] Video duration: {duration}s")
                    
                    # Parse progress from FFmpeg output
                    if "time=" in line and duration:
                        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.\d{2}', line)
                        if time_match:
                            hours, minutes, seconds = map(int, time_match.groups())
                            current_time = hours * 3600 + minutes * 60 + seconds
                            progress_percent = min(100, (current_time / duration) * 100)
                            
                            # Extract additional info
                            fps_match = re.search(r'fps=\s*(\d+\.?\d*)', line)
                            speed_match = re.search(r'speed=\s*(\d+\.?\d*)x', line)
                            
                            fps = fps_match.group(1) if fps_match else "N/A"
                            speed = speed_match.group(1) if speed_match else "N/A"
                            
                            print(f"[FFmpeg Node] Progress: {progress_percent:.1f}% ({current_time}/{duration}s) | FPS: {fps} | Speed: {speed}x")
                    
                    # Show other important messages
                    elif any(keyword in line.lower() for keyword in ['error', 'warning', 'failed']):
                        print(f"[FFmpeg Node] {line}")
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Collect all output for error reporting
            full_output = "\n".join(output_lines)
            
            if return_code != 0:
                error_msg = f"ERROR: FFmpeg failed (exit code {return_code}). Output: {full_output[-500:]}"  # Last 500 chars
                return (error_msg, "")
            
            # Check if output file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    warning_msg = f"WARNING: Output file created but is 0 bytes. FFmpeg output: {full_output[-300:]}"
                    return (warning_msg, output_path)
                else:
                    success_msg = f"SUCCESS: FFmpeg created {file_size:,} byte file at {output_path}"
                    print(f"[FFmpeg Node] {success_msg}")
                    return (success_msg, output_path)
            else:
                warning_msg = f"WARNING: FFmpeg completed but output file not found: {output_path}"
                return (warning_msg, "")
                
        except Exception as e:
            process.kill()
            error_msg = f"ERROR: Exception during FFmpeg execution: {str(e)}"
            return (error_msg, "")


# Node mappings
NODE_CLASS_MAPPINGS = {
    "FFmpegNode": FFmpegNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FFmpegNode": "FFmpeg Command Runner",
}
