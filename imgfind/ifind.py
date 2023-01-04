from argparse import ArgumentParser
from pathlib import Path
from os import system
from PIL import Image, UnidentifiedImageError


def main():
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
    parser.add_argument('--exec', type=str,
                        help='execute this command on each file')
    parser.add_argument('--print', action='store_true',
                        help='print matching files even when --exec is used')
    parser.add_argument('--delete', action='store_true',
                        help='delete matching files')

    args = parser.parse_args()

    pathname = '*' if args.no_recurse else '**/*'
    if args.name != None:
        pathname = args.name if args.no_recurse else '**/' + args.name

    for f in Path(args.dir).glob(pathname):
        if f.is_dir():
            continue
        try:
            with Image.open(f) as i:
                if args.format != None and \
                        i.format.casefold() != args.format.casefold():
                    continue
                if args.width != None and i.width != args.width:
                    continue
                if args.height != None and i.height != args.height:
                    continue
                if args.min_width != None and i.width < args.min_width:
                    continue
                if args.min_height != None and i.height < args.min_height:
                    continue
                if args.max_width != None and i.width > args.max_width:
                    continue
                if args.max_height != None and i.height > args.max_height:
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
