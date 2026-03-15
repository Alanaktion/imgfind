import os
import logging
import pyvips


log = logging.getLogger()


def convert(filename: str, dest_format: str, quality: int | None = None,
            size: tuple[int, int] | None = None,
            threads: int | None = None, keep_exif: bool = False):
    img: pyvips.Image = pyvips.Image.new_from_file(filename) # type: ignore
    if img is None:
        raise ValueError(f"Failed to load image: {filename}")
    if size is not None:
        vscale: float|None = None
        if size[0] is not None and size[1] is not None:
            scale: float = size[0] / img.get('width') # type: ignore
            vscale = size[1] / img.get('height') # type: ignore
        else:
            scale: float = size[0] / img.get('width') if size[0] is not None \
                    else size[1] / img.get('height')

        img.affine((scale, 0, 0, vscale if vscale is not None else scale)) # type: ignore

    base_name = os.path.splitext(filename)[0]
    output_path = f"{base_name}.{dest_format}"

    if dest_format == 'jpg':
        img.write_to_file(output_path, Q=quality)
    elif dest_format == 'webp':
        img.write_to_file(output_path)
    elif dest_format == 'jxl':
        img.write_to_file(output_path, Q=quality)
    elif dest_format == 'avif':
        from PIL import Image
        pil_result = Image.fromarray(img.numpy())
        pil_result.save(output_path, quality=quality)


def img_format(filename: str) -> dict[str, str | bool | int]:
    # Best-effort implementation using libvips. Some fields (quality, scenes)
    # may not be available from the loader and will fall back to defaults.
    img: pyvips.Image = pyvips.Image.new_from_file(filename, access='sequential') # type: ignore

    if img is None:
        return {
            'format': '',
            'alpha': False,
            'quality': 0,
            'scenes': 1,
            'width': 0,
            'height': 0,
        }

    # Determine format from filename extension as a reliable fallback.
    ext = os.path.splitext(filename)[1].lower()
    if ext.startswith('.'):
        ext = ext[1:]
    ext_map = {
        'jpg': 'JPEG', 'jpeg': 'JPEG', 'jpe': 'JPEG', 'jfif': 'JPEG',
        'png': 'PNG', 'webp': 'WEBP', 'tif': 'TIFF', 'tiff': 'TIFF',
        'heic': 'HEIF', 'heif': 'HEIF', 'avif': 'AVIF', 'jxl': 'JXL',
        'gif': 'GIF', 'bmp': 'BMP'
    }
    fmt = ext_map.get(ext, '')

    # alpha channel
    try:
        alpha = bool(img.hasalpha())
    except Exception:
        alpha = False

    # width / height
    try:
        width = int(img.get('width')) # type: ignore
    except Exception:
        width = 0
    try:
        height = int(img.get('height')) # type: ignore
    except Exception:
        height = 0

    # scenes / pages (best-effort)
    scenes = 1
    try:
        # some loaders expose "n-pages" or "n_frames" metadata
        for key in ('n_pages', 'n-pages', 'n_frames', 'n-pages'):
            try:
                val = img.get(key)
            except Exception:
                val = None
            if val is not None:
                try:
                    scenes = int(val) # type: ignore
                    break
                except Exception:
                    pass
    except Exception:
        scenes = 1

    # quality: libvips does not reliably expose input JPEG quality; return 0
    quality = 0

    return {
        'format': fmt,
        'alpha': alpha,
        'quality': quality,
        'scenes': scenes,
        'width': width,
        'height': height,
    }
