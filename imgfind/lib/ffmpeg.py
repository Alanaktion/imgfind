import json
import shutil
import subprocess


ffmpeg = shutil.which('ffmpeg')
ffprobe = shutil.which('ffprobe')


def probe_file(filename: str) -> dict:
    if not ffprobe:
        raise Exception('ffprobe: command not found')
    result = subprocess.run([ffprobe, '-print_format', 'json',
                             '-show_format', '-show_streams', filename],
                            capture_output=True, check=True)
    return json.loads(result.stdout)
