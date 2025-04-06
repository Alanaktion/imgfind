from functools import cache
import glob
import logging
from multiprocessing import get_context
import os
import re
import shutil
import subprocess
import sys

from .options import build_parser, Options
from ..lib.exif import file_write_comment, file_get_comment
from ..lib.ffmpeg import ffmpeg, ffmpeg_args


log = logging.getLogger()
args: Options

gm = shutil.which('gm')
magick = shutil.which('magick')
pngcrush = shutil.which('pngcrush')
pngquant = shutil.which('pngquant')


def parse_args():
    # Allow checking dependency versions, bypassing normal behavior
    if '--version' in sys.argv:
        run([gm, '-version'])
        if magick:
            run([magick, '-version'])
        if pngcrush:
            run([pngcrush, '-version'])
        if pngquant:
            run([pngquant, '--version'])
        sys.exit(0)

    parser = build_parser()
    return parser.parse_args(namespace=Options)


def main():
    global args
    args = parse_args()  # type: ignore
    init_logging(args.log_level)

    if not gm:
        log.error('gm not found on PATH. Install GraphicsMagick.')
        raise Exception()
    if args.crush and not pngcrush:
        log.warning('pngcrush not found on PATH, PNGs with transparency '
                    'will not be crushed. Use --no-crush to ignore.')
    if args.quantize and not pngquant:
        log.warning('pngquant not found on PATH, PNGs with transparency '
                    'will not be quantized. Remove --quantize to ignore.')
    if args.gif and not ffmpeg:
        log.warning('ffmpeg not found on PATH, GIF animations will not be '
                    'converted to videos. Remove --gif to ignore.')

    for f in args.file:
        file = os.path.expanduser(f)

        if not os.path.exists(file):
            raise FileNotFoundError(file)

        if os.path.isdir(file):
            if not args.recursive:
                raise IsADirectoryError()
            handle_dir(file)
            continue
        # elif args.recursive:
        #     raise NotADirectoryError()

        if not handle_file(file):
            log.error('Unsupported type: %s', os.path.basename(file))


def handle_dir(dir: str):
    """Recursively handle all matched images in a directory"""
    pattern = '**/*.[wjptbhgWJPTBHG]*'
    if args.glob:
        pattern = args.glob if '/' in args.glob else '**/' + args.glob
    cwd = os.getcwd()
    os.chdir(dir)
    iglob = glob.iglob(pattern, recursive=True)
    ctx = get_context('fork')
    with ctx.Pool(processes=None if args.parallel else 1) as pool:
        results = []
        count = 0

        def callback(r):
            results.append(r)
            if args.progress:
                # TODO: make this not trash
                print('[%3d/%3d]' % (len(results), count))
        for file in iglob:
            try:
                count += 1
                pool.apply_async(_handle_file_iter, (file,), callback=callback)
            except UnicodeEncodeError as e:
                print(e)
                pass
        pool.close()
        pool.join()
    if not any(results):
        log.warning('No images matched')
    os.chdir(cwd)


def _handle_file_iter(file: str) -> bool:
    try:
        return handle_file(file)
    except subprocess.CalledProcessError:
        return False


def handle_file(file: str) -> bool:
    """Handle an image by path"""
    outfile = None
    comment = None
    if args.keep_exif:
        comment = file_get_comment(file)
    if re.search(r'\.webp$', file, re.IGNORECASE):
        # TODO: Handle animated WebP in some way that works okay.
        outfile = handle_generic(file)
    elif re.search(r'\.j(p([eg]|eg)|fif?|if)$', file, re.IGNORECASE):
        outfile = handle_generic(file)
    elif re.search(r'\.png$', file, re.IGNORECASE):
        outfile = handle_png(file)
        # if args.force_format:
        #     handle_generic(file)
        # else:
        #     handle_png(file)
    elif re.search(r'\.tiff?$', file, re.IGNORECASE):
        if not args.keep_format:
            outfile = handle_generic(file)
    elif re.search(r'\.bmp$', file, re.IGNORECASE):
        if not args.keep_format:
            outfile = handle_generic(file)
    elif re.search(r'\.gif$', file, re.IGNORECASE):
        if not args.keep_format:
            outfile = handle_gif(file)
    elif re.search(r'\.hei[fc]$', file, re.IGNORECASE):
        if not args.keep_format:
            outfile = handle_generic(file)
    else:
        return False

    if args.keep_exif and comment and outfile:
        file_write_comment(outfile, comment)

    return True


def handle_generic(filename: str) -> str | None:
    gargs = gm_args(filename)
    if not gargs:
        level = logging.DEBUG if args.recursive else logging.INFO
        log.log(level, 'Skip: %s', os.path.basename(filename))
        return None

    if args.recursive:
        log.info('Convert: %s', os.path.basename(filename))
    run([gm, 'mogrify'] + gargs, check=True)

    new_filename = os.path.splitext(filename)[0] + '.' + args.format
    return new_filename if keep_smaller(new_filename, filename) else filename


def handle_png(filename: str) -> str | None:
    # Check for extra data after IDAT
    with open(filename, 'rb') as f:
        f.seek(-8, os.SEEK_END)
        block = f.read(8)
        f.close()
        if b'IEND' not in block:
            # Also skips non-PNG files with .png suffix, which is probably good
            log.info('Skip PNG with extra data: %s',
                     os.path.basename(filename))
            return None

    # Handle WebP conversion regardless of alpha channel
    if args.format == 'webp':
        return handle_generic(filename)

    fmt = img_format(filename)

    # TODO: Handle APNG (maybe generic multi-frame for all formats?)
    if fmt['scenes'] > 1:
        return handle_gif(filename)

    if args.keep_format:
        _handle_png_optimize(filename, fmt)
        return filename

    # Check for alpha channel
    if fmt['alpha']:
        # Check if alpha channel is actually used
        alpha_used = False

        if magick:
            # Returns 0-2^16 for minimum alpha value, we'll keep alpha if it is
            # equal or below 52428 (80% opacity).
            result = run([magick, 'identify', '-channel', 'alpha',
                          '-format', '%[min]', filename], capture_output=True)
            alpha_used = _int_def(result.stdout.strip()) <= 52428
        else:
            # Returns number of unique colors in alpha channel, we'll keep
            # alpha if it is more than one.
            result = run([gm, 'convert', '-channel', 'Opacity', filename,
                          '-format', '%k', 'info:-'], capture_output=True)
            alpha_used = _int_def(result.stdout.strip()) > 1

        if alpha_used:
            _geometry = geometry(fmt)
            if not args.crush and not args.quantize and not _geometry:
                log.debug('Skipping PNG with alpha: %s',
                          os.path.basename(filename))
                return None

            if not _geometry:
                log.info('Crush PNG with alpha: %s',
                         os.path.basename(filename))
            elif args.recursive:
                log.info('Resize: %s', os.path.basename(filename))
            _handle_png_optimize(filename, fmt)
            return filename

    if args.recursive:
        log.info('Convert: %s', os.path.basename(filename))

    gargs = gm_args(filename, fmt)
    if not gargs:
        gargs = ['-format', 'jpg', '-quality', str(args.quality),
                 '-preserve-timestamp', filename]
    run([gm, 'mogrify'] + gargs, check=True)
    jpg_filename = os.path.splitext(filename)[0] + '.jpg'
    return jpg_filename if keep_smaller(jpg_filename, filename) else None


def _handle_png_optimize(filename: str, fmt: dict):
    """Optimize a PNG image without changing to another format"""
    _geometry = geometry(fmt)
    if _geometry:
        # Resize PNG with maximum compression, removing profiles
        # TODO: quantize/crush, especially if orig was indexed color
        gm_args = []
        if not args.keep_exif:
            gm_args = ['+profile', '*']
        run([gm, 'mogrify', '-format', 'png', '-quality', '100',
             '-geometry', _geometry] + gm_args + ['-preserve-timestamp',
                                                  filename], check=True)
        return

    tmp_filename = re.sub(r'\.png$', '.tmp.png', filename, flags=re.IGNORECASE)
    if args.quantize and pngquant:
        # Lossy quantization (32bpp to 8bpp with dithering)
        result = run([pngquant, '--ext', '.tmp.png', '--skip-if-larger',
                      filename])
    elif args.crush and pngcrush:
        # Lossless recompression
        result = run([pngcrush, '-q', '-oldtimestamp', filename, tmp_filename])
        # run(['optipng', '-strip', 'all', filename])
    else:
        return

    if result.returncode == 0 and keep_smaller(tmp_filename, filename):
        os.rename(tmp_filename, filename)


def handle_gif(filename: str) -> str | None:
    fmt = img_format(filename)
    if fmt['scenes'] <= 1:
        return handle_generic(filename)

    if not args.gif or not ffmpeg:
        log.debug('Skipping animated GIF: %s', os.path.basename(filename))
        return None

    log.debug('Converting animated GIF: %s', os.path.basename(filename))
    ext = args.gif

    # TODO: Handle final frame delay not applying correctly when looping

    ffargs_pre, ffargs, ext = ffmpeg_args(args.gif, threads=args.threads)
    ffargs = [ffmpeg, '-hide_banner'] + \
        ffargs_pre + ['-i', filename] + ffargs

    dest = os.path.splitext(filename)[0] + '.' + ext
    ffargs.append(dest)
    run(ffargs, check=True)

    return dest if keep_smaller(dest, filename) else None


def keep_smaller(new_file, orig_file) -> bool:
    """Keep original file if output ends up larger

    Returns True if the new file is kept"""
    if new_file == orig_file:
        return False
    try:
        in_size = os.path.getsize(orig_file)
        out_size = os.path.getsize(new_file)
        if out_size >= in_size:
            log.info('Keep smaller original image: %s',
                     os.path.basename(orig_file))
            os.unlink(new_file)
            return False
        else:
            os.unlink(orig_file)
            return True
    except OSError:
        return False


def _int_def(val, default=0) -> int:
    try:
        return int(val)
    except ValueError:
        return default


@cache
def img_format(filename: str) -> dict[str, bool | int]:
    jpeg = re.search(r'\.j(p([eg]|eg)|fif?|if)$', filename, re.IGNORECASE)
    parts = [
        '%m',  # Magick format
        '%A',  # transparency supported
        '%[JPEG-Quality]' if jpeg else '%Q',  # JPEG/compression quality
        '%n',  # number of scenes, will output one entire fmt str per scene
        '%w',  # width
        '%h',  # height
    ]
    result: subprocess.CompletedProcess[bytes] = run(
        [gm, 'identify', '-ping', '-format',
         '/'.join(parts) + r'\n', filename],
        capture_output=True
    )
    try:
        out = result.stdout.strip().splitlines()[0]
    except IndexError:
        out = b'/////'
    out_parts = out.split(b'/')
    fmt = {
        'magick': str(out_parts[0], 'utf-8'),
        'alpha': out_parts[1] != b'false',
        'quality': _int_def(out_parts[2]),
        'scenes': _int_def(out_parts[3], 1),
        'width': _int_def(out_parts[4]),
        'height': _int_def(out_parts[5]),
    }
    return fmt


def geometry(fmt: dict) -> str | None:
    """Determine target geometry for the image"""
    # TODO: support size deltas? e.g. only resize if >100px larger
    if args.res and min(fmt['width'], fmt['height']) > args.res:
        return (f'x{args.res}' if fmt['width'] > fmt['height'] else
                f'{args.res}x')
    if args.width and fmt['width'] > args.width:
        return f'{args.width}x'
    if args.height and fmt['height'] > args.height:
        return f'x{args.height}'

    return None


def gm_args(filename: str, fmt: dict | None = None) -> list[str]:
    """Determine GM Mogrify/Convert args for specified input file"""
    if fmt is None:
        fmt = img_format(filename)

    do_convert = False
    _geometry = geometry(fmt)
    if _geometry:
        do_convert = True
    if fmt['magick'] in ('WEBP', 'JPEG'):
        if fmt['quality'] > args.quality + 5:
            do_convert = True
        elif args.force_format and args.format.upper() != fmt['magick']:
            do_convert = True
    else:
        do_convert = True
    if fmt['alpha'] and args.format != 'webp':
        do_convert = False
    if fmt['scenes'] > 1:
        do_convert = False  # Not handling ffmpeg in GM logic

    if not do_convert:
        return []

    gm_args = []
    if not args.keep_format:
        gm_args += ['-format', args.format]
    gm_args += ['-quality', str(args.quality)]
    if args.threads:
        gm_args += ['-limit', 'threads', str(args.threads)]
    if _geometry:
        gm_args += ['-geometry', _geometry]
    if ':' in filename:
        log.warning('Filename contains ":", gm may not behave correctly: %s',
                    filename)
    if not args.keep_exif:
        gm_args += ['+profile', '*']
    gm_args += ['-preserve-timestamp', filename]
    return gm_args


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
