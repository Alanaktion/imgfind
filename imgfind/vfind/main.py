from fractions import Fraction
import glob
import logging
import os
import re
import subprocess
from os import system
from shlex import quote

from .options import build_parser
from ..lib.ffmpeg import probe_file, EXTENSIONS


log = logging.getLogger()


def match_file(filename, args) -> bool:
    name = os.path.basename(filename)
    stat = os.stat(filename)
    try:
        meta = probe_file(filename)
    except subprocess.CalledProcessError as e:
        log.info(e, exc_info=True)
        return False
    else:
        if 'streams' not in meta:
            log.info('%s: Unsupported ffprobe output: %s', name, meta)
            return False

    video = {}
    audio = {}
    for stream in meta['streams']:
        if stream['codec_type'] == 'video':
            video = stream
        if stream['codec_type'] == 'audio':
            audio = stream

    # Calculate reused common values
    w = video.get('width')
    h = video.get('height')
    res = None
    aspect = None
    ratio_str = None
    if w is not None and h is not None:
        res = min(w, h)
        aspect = Fraction(w, h)
        aspect_ratio = aspect.as_integer_ratio()
        ratio_str = f'{aspect_ratio[0]}:{aspect_ratio[1]}'

    if args.filter:
        # Add useful filtering modules to eval globals
        modules = {
            're': re,
        }
        # Flatten filterable values
        data = {
            'container': meta['format']['format_name'].split(','),
            'video_codec': video.get('codec_name'),
            'audio_codec': audio.get('codec_name'),
            'width': w,
            'height': h,
            'res': res,
            'aspect': aspect,
            'ratio': ratio_str,
            'fps': eval(video.get('r_frame_rate',
                                  video.get('avg_frame_rate', '0'))),
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
        }
        # Add full metadata dict to locals
        data.update(meta)
        for filter in args.filter:
            if not eval(filter, modules, data):
                log.debug('%s: filter expression "%s" did not match',
                          name, filter)
                return False

    if args.container:
        format: str = meta['format']['format_name']
        if args.container.lower() not in format.split(','):
            log.debug('%s: container (%s) did not match', name, format)
            return False
    if args.video_codec:
        val = video.get('codec_name')
        if args.video_codec == 'none':
            if val:
                log.debug('%s: video codec (%s) did not match', name, val)
                return False
        elif val != args.video_codec.lower():
            log.debug('%s: video codec (%s) did not match', name, val)
            return False
    if args.audio_codec:
        val = audio.get('codec_name')
        if args.audio_codec == 'none':
            if val:
                log.debug('%s: audio codec (%s) did not match', name, val)
                return False
        elif val != args.audio_codec.lower():
            log.debug('%s: audio codec (%s) did not match', name, val)
            return False
    if args.res:
        if res != args.res:
            log.debug('%s: res (%s) did not match', name, res)
            return False
    if args.height:
        if h != args.height:
            log.debug('%s: height (%s) did not match', name, h)
            return False
    if args.width:
        if w != args.width:
            log.debug('%s: width (%s) did not match', name, w)
            return False
    if args.ratio:
        if w is None or h is None:
            return False
        if args.ratio.casefold() == 'square':
            if w != h:
                return False
        elif args.ratio.casefold() == 'portrait':
            if w >= h:
                return False
        elif args.ratio.casefold() == 'landscape':
            if w <= h:
                return False
        else:
            ratio = args.ratio.split(':')
            if len(ratio) != 2:
                raise ValueError(
                    'Invalid aspect ratio: {}'.format(args.ratio))
            if aspect != Fraction(args.ratio.replace(':', '/')):
                return False
    if args.fps:
        val = eval(video.get('r_frame_rate',
                             video.get('avg_frame_rate', '0')))
        if round(val, -1) != round(args.fps, -1):
            log.debug('%s: fps (%s) did not match', name, val)
            return False

    return True


def init_logging(loglevel: int):
    handler = logging.StreamHandler()
    handler.setLevel(loglevel)
    log.setLevel(logging.NOTSET)
    log.addHandler(handler)


def main():
    parser = build_parser()
    args = parser.parse_args()
    init_logging(args.log_level)
    os.chdir(args.dir)
    cwd = os.getcwd()

    for f in glob.glob('**/*', recursive=True):
        # ffprobe can read many file types, we only want to match some of them.
        if os.path.splitext(f)[1][1:].lower() not in EXTENSIONS:
            continue
        if not os.path.isfile(f):
            continue
        if match_file(f, args):
            print(f)
            name = os.path.basename(f)
            _dir = os.path.dirname(f)
            if args.exec is not None:
                kwargs = {
                    "name": quote(name),
                    "dir": quote(_dir),
                }
                system(args.exec.format(quote(f), **kwargs))
            if args.execdir is not None:
                os.chdir(_dir)
                system(args.execdir.replace('{}', quote(name)))
                os.chdir(cwd)
