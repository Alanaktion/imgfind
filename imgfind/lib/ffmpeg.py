import json
import os
import platform
import shutil
import subprocess


EXTENSIONS = [
    # Video
    '3g2', '3gp', 'avi', 'flv', 'm2ts', 'm4v', 'mj2', 'mkv', 'mov',
    'mp4', 'mpeg', 'mpg', 'ogv', 'rmvb', 'webm', 'wmv', 'y4m',
    # Audio
    'aiff', 'ape', 'au', 'flac', 'm4a', 'mka', 'mp3', 'oga', 'ogg',
    'ogm', 'opus', 'wav', 'wma',
]
AUDIO_CODECS = {
    'copy': ['-c:a', 'copy'],
    'aac': ['-c:a', 'aac'],
    'vorbis': ['-c:a', 'libvorbis'],
    'none': ['-an'],  # remove audio track entirely
}


ffmpeg = shutil.which('ffmpeg')
ffprobe = shutil.which('ffprobe')

vaapi_driver = os.environ.get('LIBVA_DRIVER_NAME')
arch = platform.machine()
system = platform.system()

hwaccel = 'vaapi' if vaapi_driver else (
    'videotoolbox' if system == 'Darwin' else None)


def probe_file(filename: str) -> dict:
    if not ffprobe:
        raise Exception('ffprobe: command not found')
    result = subprocess.run([ffprobe, '-hide_banner', '-print_format', 'json',
                             '-show_format', '-show_streams', filename],
                            capture_output=True, check=True)
    return json.loads(result.stdout)


def ffmpeg_args(vcodec: str, filters: str = '',
                threads: int | None = None) -> tuple[list[str], list[str], str]:
    pre_args = []
    args = []
    ext = vcodec
    if hwaccel and vcodec in ('mp4', 'h264', 'hevc', 'h265',):
        pre_args += [
            '-threads', '1',
            '-hwaccel', hwaccel,
        ]
        if hwaccel == 'vaapi':
            pre_args += [
                '-hwaccel_output_format', hwaccel,
                '-vaapi_device', '/dev/dri/renderD128',
            ]
        # TODO: detect compatible input resolution for hwupload:
        # filteraccel = 'opencl' if hwaccel == 'videotoolbox' else hwaccel
        # args += ['-vf', filters + f"format='nv12|{filteraccel},hwupload'",]
        if filters:
            args += ['-vf', filters]
    else:
        if threads:
            pre_args += ['-threads', str(threads)]
        if filters:
            args += ['-vf', filters]

    if vcodec in ('mp4', 'h264',):
        if hwaccel:
            args += ['-c:v', f'h264_{hwaccel}',]
            if hwaccel == 'vaapi':
                args += ['-rc_mode', '1', '-qp', '20']
            elif hwaccel == 'videotoolbox' and arch == 'arm64':
                # Constant-quality only supported on Apple Silicon
                args += ['-q:v', '20']
        else:
            args += ['-c:v', 'libx264', 'crf', '20', '-preset', 'slow']

    elif vcodec in ('hevc', 'h265',):
        if hwaccel:
            args += ['-c:v', f'hevc_{hwaccel}',]
            if hwaccel == 'vaapi':
                args += ['-rc_mode', '1', '-qp', '28']
            elif hwaccel == 'videotoolbox' and arch == 'arm64':
                # Constant-quality only supported on Apple Silicon
                args += ['-q:v', '28']
        else:
            args += ['-c:v', 'libx265', '-crf', '28', '-preset', 'slow']

    elif vcodec == 'vp8':
        args += ['-c:v', 'libvpx', '-crf', '20']
    elif vcodec in ('webm', 'vp9',):
        args += ['-c:v', 'libvpx-vp9', '-crf', '20']
    elif vcodec == 'av1':
        args += ['-c:v', 'libsvtav1', '-crf', '28']

    if vcodec in ('h264', 'hevc', 'h265',):
        ext = 'mp4'
    elif vcodec in ('vp8', 'vp9', 'av1',):
        ext = 'webm'

    return (pre_args, args, ext)
