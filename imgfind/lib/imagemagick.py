from functools import lru_cache
import logging
import os
import re
import shutil
import subprocess

# ImageMagick 7
magick = shutil.which('magick')

# ImageMagick 6
identify = shutil.which('identify')
mogrify = shutil.which('mogrify')

log = logging.getLogger()


@lru_cache
def img_format(filename: str) -> dict[str, bool | int]:
    jpeg = re.search(r'\.j(p([eg]|eg)|fif?|if)$', filename, re.IGNORECASE)
    parts = [
        '%m',  # Magick format
        '%A',  # transparency supported
        '%Q',  # compression quality
        '%n',  # number of scenes, will output one entire fmt str per scene
        '%w',  # width
        '%h',  # height
    ]
    result: subprocess.CompletedProcess[bytes] = run(
        ['identify', '-ping', '-format',
         '/'.join(parts) + r'\n', filename],
        capture_output=True
    )
    try:
        out = result.stdout.strip().splitlines()[0]
    except IndexError:
        out = b'/////'
    out_parts = out.split(b'/')
    fmt = {
        'format': str(out_parts[0], 'utf-8'),
        'alpha': out_parts[1] != b'Undefined',
        'quality': _int_def(out_parts[2]),
        'scenes': _int_def(out_parts[3], 1),
        'width': _int_def(out_parts[4]),
        'height': _int_def(out_parts[5]),
    }
    return fmt


def convert(filename: str, dest_format: str, quality: int | None = None,
            size: tuple[int, int] | None = None,
            threads: int | None = None, keep_exif: bool = False):
    magick_args = ['-format', dest_format]
    if quality:
        magick_args += ['-quality', str(quality)]
    if threads:
        magick_args += ['-limit', 'threads', str(threads)]
    if size:
        magick_args += ['-geometry', f'{size[0] or ""}x{size[1] or ""}']
    if not keep_exif:
        magick_args += ['+profile', '*']
    magick_args += [filename]

    run(['mogrify'] + magick_args, check=True)


def alpha_used(filename: str, min_alpha: int = 52428) -> bool:
    # Returns 0-2^16 for minimum alpha value, default to 80% of
    result = run(['identify', '-channel', 'alpha', '-format',
                 '%[min]', filename], capture_output=True)
    return _int_def(result.stdout.strip()) <= min_alpha


def _int_def(val, default=0) -> int:
    try:
        return int(val)
    except ValueError:
        return default


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    first = cmd.pop(0)
    if first == 'identify':
        cmd = ([magick, 'identify'] if magick else [identify]) + cmd
    if first == 'mogrify':
        cmd = ([magick, 'mogrify'] if magick else [mogrify]) + cmd
    log.debug('$ %s', ' '.join(cmd))
    result = subprocess.run(cmd, **kwargs)
    if kwargs.get('capture_output'):
        log.debug('> %s', result.stdout.decode())
    return result
