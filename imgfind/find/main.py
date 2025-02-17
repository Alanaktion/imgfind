from pathlib import Path
from os import system
from shlex import quote
from PIL import Image, UnidentifiedImageError
import sys

from .options import parse_args, Options
from .actions import do_actions
from ..lib import exif


class NotMatchedError(Exception):
    pass


def match_image(f: Path, args: Options) -> Image.Image:
    i = Image.open(f)
    if i.format is None:
        raise NotMatchedError
    if args.format is not None and \
            i.format.casefold() != args.format.casefold():
        raise NotMatchedError
    if args.width is not None and i.width != args.width:
        raise NotMatchedError
    if args.height is not None and i.height != args.height:
        raise NotMatchedError
    if args.min_width is not None and i.width < args.min_width:
        raise NotMatchedError
    if args.min_height is not None and i.height < args.min_height:
        raise NotMatchedError
    if args.max_width is not None and i.width > args.max_width:
        raise NotMatchedError
    if args.max_height is not None and i.height > args.max_height:
        raise NotMatchedError
    if args.ratio is not None:
        if args.ratio.casefold() == 'square':
            if i.width != i.height:
                raise NotMatchedError
        elif args.ratio.casefold() == 'portrait':
            if i.width >= i.height:
                raise NotMatchedError
        elif args.ratio.casefold() == 'landscape':
            if i.width <= i.height:
                raise NotMatchedError
        else:
            ratio = args.ratio.split(':')
            if len(ratio) != 2:
                raise ValueError(
                    'Invalid aspect ratio: {}'.format(args.ratio))
            if i.width / i.height != int(ratio[0]) / int(ratio[1]):
                raise NotMatchedError
    if args.animated is not None and \
            getattr(i, 'is_animated') != args.animated:
        raise NotMatchedError
    if args.ai is not None:
        is_ai = exif.image_is_stablediffusion(i)
        if is_ai != args.ai:
            raise NotMatchedError

    return i


def main():
    args = parse_args()

    pathname = '*' if args.no_recurse else '**/*'
    if args.name is not None:
        pathname = args.name if args.no_recurse else '**/' + args.name
    for dir in args.dir:
        for f in Path(dir).glob(pathname):
            if f.is_dir():
                continue
            try:
                with match_image(f, args) as src:
                    if src is None:
                        continue

                    if args.print or args.exec is None:
                        print(f)

                    if args.exec is not None:
                        system(args.exec.replace('{}', quote(str(f))))

                    if args.scale or args.resize_max or args.resize_w \
                            or args.resize_h or args.convert:
                        do_actions(src, f, args)

                    if args.delete:
                        f.unlink()

            except NotMatchedError:
                continue

            except UnidentifiedImageError:
                continue

            except OSError as e:
                print(f'{f}:', e, file=sys.stderr)
                continue
