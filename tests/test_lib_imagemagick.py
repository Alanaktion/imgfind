"""Tests for the ImageMagick backend (imgfind.lib.imagemagick)."""
import shutil
import pytest
from PIL import Image


pytestmark = pytest.mark.skipif(
    shutil.which('magick') is None and shutil.which('identify') is None,
    reason='ImageMagick (magick/identify) not available',
)


@pytest.fixture(autouse=True)
def clear_cache():
    from imgfind.lib.imagemagick import img_format
    img_format.cache_clear()
    yield
    img_format.cache_clear()


def _make_jpeg(path, width=100, height=80, quality=90):
    img = Image.new('RGB', (width, height), color=(120, 80, 40))
    img.save(path, format='JPEG', quality=quality)
    return path


def _make_png(path, width=100, height=80, alpha=False):
    mode = 'RGBA' if alpha else 'RGB'
    color = (0, 128, 255, 180) if alpha else (0, 128, 255)
    img = Image.new(mode, (width, height), color=color)
    img.save(path, format='PNG')
    return path


def _make_webp(path, width=100, height=80, quality=80):
    img = Image.new('RGB', (width, height), color=(200, 100, 50))
    img.save(path, format='WEBP', quality=quality)
    return path


# --- img_format tests ---

def test_img_format_jpeg(tmp_path):
    from imgfind.lib.imagemagick import img_format
    p = _make_jpeg(tmp_path / 'test.jpg', width=120, height=80, quality=90)
    fmt = img_format(str(p))
    assert fmt['format'] == 'JPEG'
    assert fmt['width'] == 120
    assert fmt['height'] == 80
    assert fmt['scenes'] == 1
    assert isinstance(fmt['quality'], int)
    assert 1 <= fmt['quality'] <= 100


def test_img_format_png_no_alpha(tmp_path):
    from imgfind.lib.imagemagick import img_format
    p = _make_png(tmp_path / 'test.png', width=200, height=100, alpha=False)
    fmt = img_format(str(p))
    assert fmt['format'] == 'PNG'
    assert fmt['width'] == 200
    assert fmt['height'] == 100
    assert fmt['scenes'] == 1


def test_img_format_png_with_alpha(tmp_path):
    from imgfind.lib.imagemagick import img_format
    p = _make_png(tmp_path / 'test.png', width=64, height=64, alpha=True)
    fmt = img_format(str(p))
    assert fmt['format'] == 'PNG'
    assert fmt['alpha'] is True


def test_img_format_webp(tmp_path):
    from imgfind.lib.imagemagick import img_format
    p = _make_webp(tmp_path / 'test.webp', width=50, height=50, quality=75)
    fmt = img_format(str(p))
    assert fmt['format'] == 'WEBP'
    assert fmt['width'] == 50
    assert fmt['height'] == 50


# --- convert tests ---

def test_convert_jpeg_to_webp(tmp_path):
    from imgfind.lib.imagemagick import convert
    p = _make_jpeg(tmp_path / 'test.jpg')
    convert(str(p), 'webp', quality=80)
    out = tmp_path / 'test.webp'
    assert out.exists()
    with Image.open(out) as img:
        assert img.format == 'WEBP'
        assert img.width == 100
        assert img.height == 80


def test_convert_png_to_jpg(tmp_path):
    from imgfind.lib.imagemagick import convert
    p = _make_png(tmp_path / 'test.png')
    convert(str(p), 'jpg', quality=85)
    out = tmp_path / 'test.jpg'
    assert out.exists()
    with Image.open(out) as img:
        assert img.format == 'JPEG'


def test_convert_with_resize_width(tmp_path):
    """Resize by specifying target width only."""
    from imgfind.lib.imagemagick import convert
    p = _make_jpeg(tmp_path / 'test.jpg', width=200, height=100)
    convert(str(p), 'jpg', quality=80, size=(50, None))
    with Image.open(p) as img:
        assert img.width == 50


def test_convert_with_resize_height(tmp_path):
    """Resize by specifying target height only."""
    from imgfind.lib.imagemagick import convert
    p = _make_jpeg(tmp_path / 'test.jpg', width=200, height=100)
    convert(str(p), 'jpg', quality=80, size=(None, 50))
    with Image.open(p) as img:
        assert img.height == 50


# --- alpha_used tests ---

def test_alpha_used_with_alpha(tmp_path):
    from imgfind.lib.imagemagick import alpha_used
    p = _make_png(tmp_path / 'test.png', alpha=True)
    result = alpha_used(str(p))
    assert isinstance(result, bool)


def test_alpha_used_without_alpha(tmp_path):
    from imgfind.lib.imagemagick import alpha_used
    p = _make_png(tmp_path / 'test.png', alpha=False)
    result = alpha_used(str(p))
    assert result is False
