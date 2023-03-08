from argparse import ArgumentParser
from pathlib import Path
from os import system
from PIL import Image, UnidentifiedImageError


def parser():
    parser = ArgumentParser(
        description='Find image files.', add_help=False)
    parser.add_argument('dir', type=str, nargs='?', default='.',
                        help='directory to search')
    parser.add_argument('--help', action='help',
                        help='show this help message and exit')
    parser.add_argument('-n', '--name', type=str,
                        help='match files with this glob pattern')
    parser.add_argument('--no-recurse', action='store_true',
                        help='don\'t recurse subdirectories')
    parser.add_argument('-f', '--format', type=str,
                        help='match images with this format')
    parser.add_argument('-w', '--width', type=int,
                        help='match images with this exact width')
    parser.add_argument('-h', '--height', type=int,
                        help='match images with this exact height')
    parser.add_argument('-mw', '--min-width', type=int,
                        help='match images with at least this width')
    parser.add_argument('-mh', '--min-height', type=int,
                        help='match images with at least this height')
    parser.add_argument('--max-width', type=int,
                        help='match images less than or equal to this width')
    parser.add_argument('--max-height', type=int,
                        help='match images less than or equal to this height')
    parser.add_argument('-r', '--ratio', type=str,
                        help='match images with this aspect ratio')
    parser.add_argument('--exec', type=str,
                        help='execute this command on each file')
    parser.add_argument('--print', action='store_true',
                        help='print matching files even when operating on them')
    parser.add_argument('--delete', action='store_true',
                        help='delete matching files')

    return parser.parse_args()


def match_image(f, args) -> bool:
    with Image.open(f) as i:
        if args.format != None and \
                i.format.casefold() != args.format.casefold():
            return False
        if args.width != None and i.width != args.width:
            return False
        if args.height != None and i.height != args.height:
            return False
        if args.min_width != None and i.width < args.min_width:
            return False
        if args.min_height != None and i.height < args.min_height:
            return False
        if args.max_width != None and i.width > args.max_width:
            return False
        if args.max_height != None and i.height > args.max_height:
            return False
        if args.ratio != None:
            if args.ratio.casefold() == 'square':
                if i.width != i.height:
                    return False
            elif args.ratio.casefold() == 'portrait':
                if i.width >= i.height:
                    return False
            elif args.ratio.casefold() == 'landscape':
                if i.width <= i.height:
                    return False
            else:
                ratio = args.ratio.split(':')
                if len(ratio) != 2:
                    raise ValueError(
                        'Invalid aspect ratio: {}'.format(args.ratio))
                if i.width / i.height != int(ratio[0]) / int(ratio[1]):
                    return False
    return True


def main():
    args = parser()

    pathname = '*' if args.no_recurse else '**/*'
    if args.name != None:
        pathname = args.name if args.no_recurse else '**/' + args.name

    for f in Path(args.dir).glob(pathname):
        if f.is_dir():
            continue
        try:
            if not match_image(f, args):
                continue
            if args.exec != None:
                system(args.exec.replace('{}', str(f)))
            if args.print or args.exec == None:
                print(f)
            if args.delete:
                f.unlink()
        except UnidentifiedImageError:
            continue


if __name__ == "__main__":
    main()
