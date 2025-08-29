from pathlib import Path
from PIL import Image

from .options import Options


def do_actions(src: Image.Image, f: Path, args: Options):
    dest = src.copy()

    res = max(src.width, src.height)
    if args.scale or (args.resize_max and args.resize_max < res) \
            or (args.resize_w and args.resize_w < src.width) \
            or (args.resize_h and args.resize_h < src.height):
        scale = args.scale or (args.resize_max / res if args.resize_max
                               else args.resize_w / src.width if args.resize_w
                               else args.resize_h / src.height)
        size = (args.resize_w or int(src.width * scale),
                args.resize_h or int(src.height * scale))
        dest = dest.resize(size, Image.Resampling.BILINEAR)

    format: str | None = None
    if args.convert:
        format = args.convert.lower()
    elif src.format:
        format = src.format.lower()

    suffix = f.suffix
    if format == 'jpg' or format == 'jpeg':
        if dest.mode == 'RGBA':
            dest = dest.convert('RGB')
        suffix = '.jpg'
    elif format == 'png':
        suffix = '.png'
    elif format == 'avif':
        suffix = '.avif'
    elif format == 'webp':
        suffix = '.webp'
    elif format == 'jxl' or format == 'jpegxl':
        suffix = '.jxl'
    elif format is not None:
        raise ValueError('Unsupported output format ' + format)

    destpath = Path(args.dest or f.parent, f.with_suffix(suffix).name)
    dest.save(destpath, quality=args.quality)
