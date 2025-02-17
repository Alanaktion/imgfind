from argparse import ArgumentParser, Namespace
from pathlib import Path
from PIL import Image


class Options(Namespace):
    dir: list[Path]

    name: str
    no_recurse: bool
    format: str
    width: int
    height: int
    min_width: int
    min_height: int
    max_width: int
    max_height: int
    ratio: str
    animated: bool | None
    ai: bool | None

    print: bool
    exec: str
    delete: bool
    dest: Path
    scale: float
    resize_max: int
    resize_w: int
    resize_h: int
    convert: str
    quality: int


def dir_path(dir: str) -> Path:
    path = Path(dir)
    if not path.is_dir():
        raise NotADirectoryError(dir)
    return path


def dir_paths(dirs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for dir in dirs:
        path = Path(dir)
        if not path.is_dir():
            raise NotADirectoryError(dir)
        paths.append(path)
    return paths


def _supported_extensions():
    exts: list[str] = []
    for k in Image.registered_extensions().keys():
        exts.append(k[1:])
    return exts


def build_parser():
    parser = ArgumentParser(
        description='Find and operate on image files.', add_help=False)
    parser.add_argument('dir', type=dir_path, nargs='*', default=['.'],
                        help='directories to search')

    parser.add_argument('--help', action='help',
                        help='show this help message and exit')

    matching = parser.add_argument_group('matching options')

    matching.add_argument('-n', '--name', type=str,
                          help='match files with this glob pattern')
    matching.add_argument('--no-recurse', action='store_true',
                          help='don\'t recurse subdirectories')
    matching.add_argument('-f', '--format', type=str,
                          help='match images with this format')
    matching.add_argument('-w', '--width', type=int, metavar='DIM',
                          help='match images with this exact width')
    matching.add_argument('-h', '--height', type=int, metavar='DIM',
                          help='match images with this exact height')
    matching.add_argument('-mw', '--min-width', type=int, metavar='DIM',
                          help='match images with at least this width')
    matching.add_argument('-mh', '--min-height', type=int, metavar='DIM',
                          help='match images with at least this height')
    matching.add_argument('--max-width', type=int, metavar='DIM',
                          help='match images less than or equal to this width')
    matching.add_argument('--max-height', type=int, metavar='DIM',
                          help='match images less than or equal to this height')
    matching.add_argument('-r', '--ratio', type=str,
                          help='match images with this aspect ratio')
    matching.add_argument('--animated', action='store_const', const=True,
                          help='match animated images')
    matching.add_argument('--no-animated', action='store_const', const=False,
                          help='match non-animated images', dest='animated')

    matching.add_argument('--ai', action='store_const', const=True,
                          help='match images with metadata from generative AIs like Stable Diffusion')
    matching.add_argument('--no-ai', action='store_const', const=False,
                          help='do not match images with metadata from generative AIs like Stable Diffusion')

    actions = parser.add_argument_group('actions')

    actions.add_argument('--print', action='store_true',
                         help='print matching files')
    actions.add_argument('--exec', type=str,
                         help='execute this command on each file')
    actions.add_argument('--delete', action='store_true',
                         help='delete matching files')

    actions.add_argument('--dest', type=dir_path, metavar='DIR',
                         help='write modified files to this directory')

    resize = actions.add_mutually_exclusive_group()
    resize.add_argument('--scale', type=float,
                        help='scale images relative to original dimensions, e.g. 0.5 to scale to 50%%')
    resize.add_argument('--resize-max', type=int, metavar='DIM',
                        help='resize images to a maximum dimension, preserving aspect ratio')
    resize.add_argument('--resize-w', type=int, metavar='DIM',
                        help='resize images to a maximum width, preserving aspect ratio')
    resize.add_argument('--resize-h', type=int, metavar='DIM',
                        help='resize images to a maximum height, preserving aspect ratio')

    actions.add_argument('--convert', type=str, metavar='FORMAT',
                         help="convert images to a new format, e.g. 'jpg'")
    actions.add_argument('--quality', type=int, default=80,
                         help='compression quality for lossy image formats (default: %(default)s)')

    return parser


def parse_args() -> Options:
    parser = build_parser()
    try:
        args = parser.parse_args(namespace=Options)
        # if args.resize_max and (args.resize_h or args.resize_w):
        #     parser.error(f'argument --resize-max: not allowed with arguments --resize-w/h')
        return args  # type: ignore
    except NotADirectoryError as err:
        parser.error(f'not a directory: {err.args[0]}')
