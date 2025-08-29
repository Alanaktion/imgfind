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
from ..lib.graphicsmagick import gm
from ..lib.imagemagick import magick, mogrify

if gm:
    from ..lib.graphicsmagick import img_format, convert
elif magick or mogrify:
    from ..lib.imagemagick import img_format, convert
else:
    try:
        import pyvips
    except ImportError:
        from ..lib.pillow import img_format, convert
    else:
        from ..lib.libvips import img_format, convert


log = logging.getLogger()
args: Options

pngcrush = shutil.which('pngcrush')
pngquant = shutil.which('pngquant')


def parse_args():
    # Allow checking dependency versions, bypassing normal behavior
    if '--version' in sys.argv:
        if gm:
            run([gm, '-version'])
        if magick:
            run([magick, '-version'])
        if ffmpeg:
            run([ffmpeg, '-version'])
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

    if args.format == 'avif' and gm:
        global convert
        # GM does not support writing AVIF files, use ImageMagick or Pillow
        if magick or mogrify:
            from ..lib.imagemagick import convert as magick_convert
            convert = magick_convert
        else:
            from ..lib.pillow import convert as pillow_convert
            convert = pillow_convert

    if args.crush and not pngcrush and \
            (args.keep_format or args.format == 'jpg'):
        log.warning('pngcrush not found on PATH, PNGs will not be crushed. '
                    'Use --no-crush to ignore.')
    if args.quantize and not pngquant:
        log.warning('pngquant not found on PATH, PNGs will not be quantized. '
                    'Remove --quantize to ignore.')
    if args.gif in ('mp4', 'hevc', 'webm', 'av1') and not ffmpeg:
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
    except subprocess.CalledProcessError as e:
        if args.verbose >= logging.WARNING:
            print(e)
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
    ifmt = img_format(filename)
    if not should_convert(filename):
        level = logging.DEBUG if args.recursive else logging.INFO
        log.log(level, 'Skip: %s', os.path.basename(filename))
        return None

    convert(filename, args.format, args.quality,
            resize(ifmt), args.threads, args.keep_exif)
    if args.recursive:
        log.info('Convert: %s', os.path.basename(filename))

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

    # Use generic conversion when target format supports alpha
    if args.format in ('webp', 'avif'):
        return handle_generic(filename)

    ifmt = img_format(filename)

    # Handle APNG
    if ifmt['scenes'] > 1:
        return handle_gif(filename)

    if args.keep_format:
        _handle_png_optimize(filename, ifmt)
        return filename

    size = resize(ifmt)

    # Check for alpha channel
    if ifmt['alpha']:
        # Check if alpha channel is actually used
        alpha_used = False

        if magick or mogrify:
            from ..lib.imagemagick import alpha_used as check_alpha
            alpha_used = check_alpha(filename)
        elif gm:
            from ..lib.graphicsmagick import alpha_used as check_alpha
            alpha_used = check_alpha(filename)

        if alpha_used:
            if not args.crush and not args.quantize and not size:
                log.debug('Skipping PNG with alpha: %s',
                          os.path.basename(filename))
                return None

            if not size:
                log.info('Crush PNG with alpha: %s',
                         os.path.basename(filename))
            elif args.recursive:
                log.info('Resize: %s', os.path.basename(filename))
            _handle_png_optimize(filename, ifmt)
            return filename

    if not should_convert(filename):
        return None

    if args.recursive:
        log.info('Convert: %s', os.path.basename(filename))

    convert(filename, args.format, args.quality,
            size, args.threads, args.keep_exif)
    out_filename = os.path.splitext(filename)[0] + '.' + args.format
    return out_filename if keep_smaller(out_filename, filename) else None


def _handle_png_optimize(filename: str, ifmt: dict):
    """Optimize a PNG image without changing to another format"""
    size = resize(ifmt)
    if size:
        # Resize PNG with maximum compression
        # TODO: quantize/crush, especially if orig was indexed color
        result = convert(filename, 'png', 100, size,
                         args.threads, args.keep_exif)
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
    ifmt = img_format(filename)
    if ifmt['scenes'] <= 1:
        return handle_generic(filename)

    if not args.gif:
        log.debug('Skipping animated GIF: %s', os.path.basename(filename))
        return None

    if args.gif in ('mp4', 'hevc', 'webm', 'av1'):
        return handle_gif_ffmpeg(filename)

    if args.recursive:
        log.info('Convert: %s', os.path.basename(filename))

    if magick or mogrify:
        # Use ImageMagick
        from ..lib.imagemagick import convert as magick_convert
        magick_convert(filename, args.gif, args.quality,
                       resize(ifmt), args.threads, args.keep_exif)
    else:
        # Use Pillow
        from ..lib.pillow import convert as pillow_convert
        pillow_convert(filename, args.gif, args.quality,
                       resize(ifmt), args.threads, args.keep_exif)

    new_filename = os.path.splitext(filename)[0] + '.' + args.gif
    return new_filename if keep_smaller(new_filename, filename) else filename


def handle_gif_ffmpeg(filename: str) -> str | None:
    if not ffmpeg:
        log.debug('Skipping animated GIF: %s', os.path.basename(filename))
        return None

    log.debug('Converting animated GIF: %s', os.path.basename(filename))

    # TODO: Handle final frame delay not applying correctly when looping
    filters = ''
    if args.gif in ('webp', 'avif'):
        filters = 'trunc(iw/2)*2:-2'
    ffargs_pre, ffargs, ext = ffmpeg_args(args.gif, filters, args.threads)
    if os.path.splitext(filename)[1].lower() == '.gif':
        ffargs_pre += ['-f', 'gif']
    pixfmt = ['-pix_fmt', 'yuv420p']
    ffargs = [ffmpeg, '-hide_banner'] + \
        ffargs_pre + ['-i', filename] + pixfmt + ffargs

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
            if not args.keep_original:
                os.unlink(orig_file)
            return True
    except OSError:
        return False


def resize(ifmt: dict) -> tuple[int | None, int | None] | bool:
    if args.res and min(ifmt['width'], ifmt['height']) > args.res:
        if ifmt['width'] > ifmt['height']:
            return (None, args.res)
        else:
            return (args.res, None)
    if args.width and ifmt['width'] > args.width:
        return (args.res, None)
    if args.height and ifmt['height'] > args.height:
        return (None, args.res)

    return False


def should_convert(filename: str) -> bool:
    ifmt = img_format(filename)

    do_convert = False
    if resize(ifmt):
        do_convert = True
    if ifmt['format'] in ('WEBP', 'JPEG'):
        if args.quality is not None and ifmt['quality'] > args.quality + 5:
            do_convert = True
        elif args.force_format and args.format.upper() != ifmt['format']:
            do_convert = True
    else:
        do_convert = True
    if ifmt['alpha'] and args.format not in ('webp', 'avif'):
        do_convert = False

    return do_convert


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
