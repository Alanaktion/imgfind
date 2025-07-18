from functools import lru_cache
import logging
import os
import re
import shutil
import subprocess

gm = shutil.which('gm')
log = logging.getLogger()


@lru_cache
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
    print([gm, 'identify', '-ping', '-format',
         '/'.join(parts) + r'\n', filename])
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
        'format': str(out_parts[0], 'utf-8'),
        'alpha': out_parts[1] != b'false',
        'quality': _int_def(out_parts[2]),
        'scenes': _int_def(out_parts[3], 1),
        'width': _int_def(out_parts[4]),
        'height': _int_def(out_parts[5]),
    }
    return fmt


def convert(filename: str, dest_format: str, quality: int | None = None,
            size: tuple[int, int] | None = None,
            threads: int | None = None, keep_exif: bool = False):
    gm_args = ['-format', dest_format]
    if quality:
        gm_args += ['-quality', str(quality)]
    if threads:
        gm_args += ['-limit', 'threads', str(threads)]
    if size:
        gm_args += ['-geometry', f'{size[0] or ""}x{size[1] or ""}']
    if not keep_exif:
        gm_args += ['+profile', '*']
    gm_args += ['-preserve-timestamp', filename]

    if ':' in filename:
        log.warning('Filename contains ":", gm may not behave correctly: %s',
                    filename)

    run([gm, 'mogrify'] + gm_args, check=True)


def alpha_used(filename: str, min_values: int = 1) -> bool:
    # Returns number of unique colors in alpha channel.
    result = run([gm, 'convert', '-channel', 'Opacity', filename,
                  '-format', '%k', 'info:-'], capture_output=True)
    return _int_def(result.stdout.strip()) > min_values


def _int_def(val, default=0) -> int:
    try:
        return int(val)
    except ValueError:
        return default


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    log.debug('$ %s', ' '.join(cmd))
    result = subprocess.run(cmd, **kwargs)
    if kwargs.get('capture_output'):
        log.debug('> %s', result.stdout.decode())
    return result
