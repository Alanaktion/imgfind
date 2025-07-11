import argparse
from fractions import Fraction
from functools import cache
import glob
import logging
import os
import subprocess

from .options import build_parser
from ..lib import ffmpeg as ff


log = logging.getLogger()
args: argparse.Namespace


def main():
    global args
    args = build_parser().parse_args()
    init_logging(args.log_level)

    if not ff.ffprobe or not ff.ffmpeg:
        log.error('ffmpeg and ffprobe must be available.')
        raise Exception()

    for f in args.file:
        file = os.path.expanduser(f)

        if not os.path.exists(file):
            raise FileNotFoundError(file)

        if os.path.isdir(file):
            if not args.recursive:
                raise IsADirectoryError(file)
            handle_dir(file)
            continue

        if not handle_file(file):
            log.error('Unsupported type: %s', os.path.basename(file))


def handle_dir(dir: str):
    """Recursively handle all matched videos in a directory"""

    pattern = '**/*.[mwaforyMWAFORY3]*'
    if args.glob:
        pattern = args.glob if '/' in args.glob else '**/' + args.glob
    cwd = os.getcwd()
    os.chdir(dir)
    results: list[bool] = []
    for file in glob.iglob(pattern, recursive=True):
        results.append(handle_file(file))
    if not any(results):
        log.warning('No videos matched')
    os.chdir(cwd)


def handle_file(file: str) -> bool:
    """Handle a video file by path"""

    # Skip input files not in the supported extensions
    if os.path.splitext(file)[1][1:].lower() not in ff.EXTENSIONS:
        return False

    name = os.path.basename(file)
    data = probe_file(file)
    if not data.res:
        return False

    _geometry = geometry(args, data)
    if not _geometry and (args.keep_video_codec or
                          data.video_codec == args.video_codec):
        log.info('skip (already target dimensions/codec): %s', name)
        return True

    ffargs: list[str] = ['-hide_banner', '-i', file]

    # Scale video
    filters = []
    if _geometry:
        scaler = 'scale_vaapi' if ff.hwaccel == 'vaapi' else 'scale'
        filters += [f'{scaler}={_geometry}']
    if args.chroma_subsampling:
        # TODO: support 10-bit color?
        orig_fmt = data.pix_fmt
        pix_fmt = f'yuv{args.chroma_subsampling}p'
        if not orig_fmt or pix_fmt < orig_fmt:
            filters += [f'format={pix_fmt}']

    # Set output video codec
    if args.keep_video_codec:
        pre, post, _ = ff.ffmpeg_args(data.video_codec, ','.join(filters))
    else:
        pre, post, _ = ff.ffmpeg_args(args.video_codec, ','.join(filters))
    ffargs = pre + ffargs + post

    # Determine output container
    fmt, ext = container(file, args)

    # Set output audio codec
    if data.audio_codec:
        # Ensure Vorbis audio for WebM output container
        if fmt == 'webm':
            if args.audio_codec == 'copy' and data.audio_codec == 'vorbis':
                ffargs += ff.AUDIO_CODECS[args.audio_codec]
            else:
                ffargs += ff.AUDIO_CODECS['vorbis']
        else:
            ffargs += ff.AUDIO_CODECS[args.audio_codec]
    else:
        log.debug('no audio track: %s', name)
        ffargs.append('-an')

    # TODO: copy subtitles?
    # ffargs += ['-c:s', 'copy'] if args.subtitles else ['-sn']

    parts = os.path.splitext(file)
    dest = parts[0] + '.' + ext
    tmp_dest = parts[0] + '.teeny.' + ext
    ffargs += ['-f', fmt, tmp_dest]  # '-discard'

    # Run ffmpeg and delete original
    # TODO: only delete original if new one is smaller, right?
    try:
        run([ff.ffmpeg] + ffargs, check=True)
    except subprocess.CalledProcessError:
        # Clean up failed transcodes
        try:
            os.unlink(tmp_dest)
        except:
            pass
    else:
        if not args.keep_original:
            if os.path.exists(tmp_dest):
                os.unlink(file)
                os.rename(tmp_dest, dest)
        elif not os.path.exists(dest):
            os.rename(tmp_dest, dest)

    return True


class Meta():
    meta: dict
    container: tuple[str]
    video_codec: str
    pix_fmt: str | None
    audio_codec: str | None
    width: int
    height: int
    res: int
    ratio: Fraction

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])


@cache
def probe_file(filename: str) -> Meta:
    """Get basic metadata from an input file using ffprobe"""

    meta = ff.probe_file(filename)

    video = {}
    audio = {}
    for stream in meta['streams']:
        if stream['codec_type'] == 'video':
            video = stream
        if stream['codec_type'] == 'audio':
            audio = stream

    w = int(video.get('width', 0))
    h = int(video.get('height', 0))

    return Meta(
        meta=meta,  # TODO: remove if arbitrary value access is not needed
        # TODO: get primary name for container
        container=meta['format']['format_name'],
        video_codec=video.get('codec_name'),
        pix_fmt=video.get('pix_fmt'),
        audio_codec=audio.get('codec_name'),
        width=w,
        height=h,
        res=min(w, h),
        ratio=Fraction(w, h),
    )


def container(file, args) -> tuple[str, str]:
    """Determine target output container and extension, falling back to MKV"""

    container = args.container
    if args.keep_container:
        parts = os.path.splitext(file)
        container = parts[1][1:]

    supported = True
    if container == 'webm':
        if args.video_codec not in ('vp8', 'vp9', 'av1'):
            supported = False

    if not supported:
        log.warning('Container does not support target codecs, using MP4')
        # return 'matroska', 'mkv'
        return 'mp4', 'mp4'

    return container, container


def geometry(args, data: Meta) -> str | None:
    """Determine target output geometry, if resizing is needed"""

    w = None
    h = None
    if args.res:
        if args.res < data.res:
            if data.ratio > 1:
                h = args.res
            else:
                w = args.res
    elif args.height:
        if args.height < data.height:
            h = args.height
    elif args.width:
        if args.width < data.width:
            w = args.width

    if w:
        h = int(data.ratio.denominator / data.ratio.numerator * w)
    elif h:
        w = int(data.ratio.numerator / data.ratio.denominator * h)

    return f'{w}:{h}' if w else None


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    log.debug('$ %s', ' '.join(cmd))
    result = subprocess.run(cmd, **kwargs)
    if kwargs.get('capture_output'):
        log.debug('> %s', result.stdout.decode())
    return result


def init_logging(loglevel: int):
    handler = logging.StreamHandler()
    handler.setLevel(loglevel)
    log.setLevel(logging.NOTSET)
    log.addHandler(handler)
