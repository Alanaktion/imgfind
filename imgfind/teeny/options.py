import argparse
import logging


class Options(argparse.Namespace):
    pass


def build_parser():
    parser = argparse.ArgumentParser(description='Optimize an image file')
    parser.add_argument('file', nargs='+')

    parser.add_argument('-r', '--recursive', action='store_true',
                        help='operate on all files in the specified path')
    parser.add_argument('--glob',
                        help='operate on files matching this pattern')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose',
                       action='store_const', dest='log_level',
                       default=logging.INFO, const=logging.DEBUG)
    group.add_argument('-q', '--quiet',
                       action='store_const', dest='log_level',
                       default=logging.INFO, const=logging.WARNING)

    parser.add_argument('-p', '--progress', action='store_true',
                        help='show overall progress for recursive operations')

    fmt = parser.add_argument_group('format options')
    group = fmt.add_mutually_exclusive_group()
    group.add_argument('-f', '--format', choices=['jpg', 'webp', 'avif'],
                       default='jpg',
                       help='Target file format. If "jpg", images with '
                            'transparency will not be converted, but other '
                            'images will be. If "webp" or "avif", any input '
                            'image will be converted.')
    group.add_argument('-k', '--keep-format', action='store_true',
                       help='Keep original format, only recompress')
    fmt.add_argument('-F', '--force-format', action='store_true',
                     help='Convert to specified format whenever possible')
    fmt.add_argument('-K', '--keep-original', action='store_true',
                     help='Preserve original file when changing formats')
    fmt.add_argument('--quality', type=int, default=85, metavar='INT',
                     help='Target JPEG/WEBP quality')
    fmt.add_argument('--gif', choices=['mp4', 'hevc', 'webm', 'av1', 'webp', 'avif'],
                     help='Convert animated GIFs to the specified format. '
                          'mp4 and hevc will use hardware encoder if possible')
    fmt.add_argument('-x', '--keep-exif', action='store_true',
                     help='Preserve EXIF metadata')

    # TODO: support size deltas? e.g. only resize if >100px larger
    size = parser.add_argument_group('size options')
    group = size.add_mutually_exclusive_group()
    group.add_argument('--res', type=int, metavar='INT',
                       help='Limit minimum dimension to this value')
    group.add_argument('--width', type=int, metavar='INT',
                       help='Limit width to this value')
    group.add_argument('--height', type=int, metavar='INT',
                       help='Limit height to this value')

    png = parser.add_argument_group('png options')
    group = png.add_mutually_exclusive_group()
    group.add_argument('--no-crush', dest='crush', action='store_false',
                       help='Do not optimize PNG images with transparency '
                       '(lossless)')
    group.add_argument('--quantize', action='store_true',
                       help='Quantize PNG images with transparency (lossy)')

    sub = parser.add_argument_group('subprocess options')
    sub.add_argument('--threads', type=int,
                     help='Limit threads on subprocesses (ffmpeg and GM)')
    sub.add_argument('--no-parallel', action='store_false', dest='parallel',
                     help='Do not run conversions in parallel when running '
                          'recursively.')

    return parser
