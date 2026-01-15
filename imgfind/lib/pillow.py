from functools import lru_cache
import os
import struct

from PIL import Image


@lru_cache
def img_format(filename: str) -> dict[str, bool | int]:
    with Image.open(filename) as img:
        return {
            'format': img.format,
            'alpha': img.has_transparency_data,
            'quality': guess_quality(img),
            'scenes': img.n_frames,
            'width': img.width,
            'height': img.height,
        }


def convert(filename: str, dest_format: str, quality: int | None = None,
            size: tuple[int, int] | None = None,
            threads: int | None = None, keep_exif: bool = False):
    with Image.open(filename) as img:
        aspect_ratio = img.width / img.height
        if size:
            if size[0] is not None and size[1] is None:
                new_size = (size[0], size[0] // aspect_ratio)
            elif size[0] is None and size[1] is not None:
                new_size = (size[1] * aspect_ratio, size[1])
            else:
                new_size = size
            img = img.resize(new_size)

        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}.{dest_format}"
        # TODO: conditionally handle exif, quality.
        img.save(output_path, quality=quality)


def guess_quality(img: Image) -> int:
    # JPEG quantization estimate
    if img.format == 'JPEG':
        qtables = img.quantization
        q1 = qtables[0] if 0 in qtables else list(qtables.values())[0]

        if q1[0] >= 50:
            quality_factor = (200 - q1[0] * 2) / 100
        else:
            quality_factor = 50 / q1[0]

        estimated_quality = int(quality_factor * 100)
        return max(1, min(100, estimated_quality))

    # WebP filesize estimate
    if img.format == 'WEBP' and img.filename:
        file_size = os.path.getsize(img.filename)
        pixels = img.width * img.height
        bytes_per_pixel = file_size / pixels
        if bytes_per_pixel > 2.0:
            return 100
        estimated_quality = int(bytes_per_pixel * 80)
        return max(1, min(100, estimated_quality))

    return 100
