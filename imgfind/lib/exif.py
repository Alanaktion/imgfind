import os
import piexif
import piexif.helper
from PIL import Image, PngImagePlugin


def image_is_stablediffusion(i: Image.Image) -> bool:
    comment = image_get_comment(i)
    return 'CFG scale:' in comment


def image_get_comment(i: Image.Image) -> str:
    """Get EXIF comment or PNG info from image"""
    items = (i.info or {}).copy()

    if 'parameters' in items:
        return items['parameters']

    if 'prompt' in items:
        return items['prompt']

    if 'exif' in items:
        exif_data = items['exif']
        try:
            exif = piexif.load(exif_data)
        except OSError:
            exif = None
        exif_comment = (exif or {}).get('Exif', {}).get(
            piexif.ExifIFD.UserComment, b'')
        try:
            exif_comment = piexif.helper.UserComment.load(exif_comment)
        except ValueError:
            exif_comment = exif_comment.decode('utf8', errors='ignore')

        if exif_comment:
            return exif_comment

    elif 'comment' in items:
        if isinstance(items['comment'], bytes):
            return items['comment'].decode('utf8', errors='ignore')
        else:
            return items['comment']

    return ''


def file_get_comment(filename: str) -> str:
    return image_get_comment(Image.open(filename))


def file_write_comment(filename: str, comment: str, info_key: str = 'parameters'):
    """Write a string into the EXIF comment or PNG info for a file"""
    extension = os.path.splitext(filename)[1]

    if extension.lower() == '.png':
        image = Image.open(filename)
        pnginfo_data = PngImagePlugin.PngInfo()
        pnginfo_data.add_text(info_key, comment)
        image.save(filename, format='png', pnginfo=pnginfo_data)

    elif extension.lower() in (".jpg", ".jpeg", ".webp"):
        encoded = piexif.helper.UserComment.dump(comment, encoding="unicode")
        exif_bytes = piexif.dump({
            "Exif": {
                piexif.ExifIFD.UserComment: encoded,
            },
        })

        piexif.insert(exif_bytes, filename)

    elif extension.lower() == '.avif':
        image = Image.open(filename)
        image.save(filename, format='avif', comment=comment)

    else:
        raise NotImplementedError


def file_get_all(filename: str) -> dict:
    """Return all available EXIF and image info for a file as a dict."""
    image = Image.open(filename)
    result: dict = {
        'format': image.format,
        'size': image.size,
    }

    items = (image.info or {}).copy()
    if items:
        info_out: dict = {}
        for k, v in items.items():
            if isinstance(v, bytes):
                try:
                    info_out[k] = v.decode('utf8', errors='ignore')
                except Exception:
                    info_out[k] = repr(v)
            else:
                info_out[k] = v
        result['info'] = info_out

    # load EXIF blocks when available
    if 'exif' in items:
        exif_data = items['exif']
        try:
            exif = piexif.load(exif_data)
        except Exception:
            exif = None

        if exif:
            exif_out: dict = {}
            for ifd_name, ifd_dict in exif.items():
                sub: dict = {}
                for tag, value in ifd_dict.items():
                    tag_name = piexif.TAGS.get(ifd_name, {}).get(tag, {}).get('name', str(tag))
                    if isinstance(value, bytes):
                        # decode user comment specially
                        if ifd_name == 'Exif' and tag == piexif.ExifIFD.UserComment:
                            try:
                                sub[tag_name] = piexif.helper.UserComment.load(value)
                            except Exception:
                                try:
                                    sub[tag_name] = value.decode('utf8', errors='ignore')
                                except Exception:
                                    sub[tag_name] = repr(value)
                        else:
                            try:
                                sub[tag_name] = value.decode('utf8', errors='ignore')
                            except Exception:
                                sub[tag_name] = repr(value)
                    else:
                        sub[tag_name] = value
                exif_out[ifd_name] = sub
            result['exif'] = exif_out

    return result
