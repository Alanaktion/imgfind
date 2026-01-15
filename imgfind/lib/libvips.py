import os
import logging
import pyvips


log = logging.getLogger()


def convert(filename: str, dest_format: str, quality: int | None = None,
            size: tuple[int, int] | None = None,
            threads: int | None = None, keep_exif: bool = False):
    with pyvips.Image.new_from_file(filename) as img:
        if size is not None:
            vscale = None
            if size[0] is not None and size[1] is not None:
                scale = size[0] / img.get('width')
                vscale = size[1] / img.get('height')
            else:
                scale = size[0] / img.get('width') if size[0] is not None \
                        else size[1] / img.get('height')

            result = img.resize(scale, vscale=vscale)
        else:
            result = img

        base_name = os.path.splitext(filename)[0]
        output_path = f"{base_name}.{dest_format}"

        if dest_format == 'jpg':
            result.jpegsave(output_path, Q=quality)
        elif dest_format == 'webp':
            result.webpsave(output_path)
        elif dest_format == 'jxl':
            result.jxlsave(output_path, Q=quality)
        elif dest_format == 'avif':
            from PIL import Image
            pil_result = Image.fromarray(result.numpy())
            pil_result.save(output_path, quality=quality)
