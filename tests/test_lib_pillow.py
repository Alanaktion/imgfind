"""Tests for the Pillow backend (imgfind.lib.pillow)."""
import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def clear_cache():
    from imgfind.lib.pillow import img_format
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


def _make_gif(path, width=100, height=80):
    img = Image.new('P', (width, height), color=0)
    img.save(path, format='GIF')
    return path


# --- img_format tests ---

def test_img_format_jpeg(tmp_path):
    from imgfind.lib.pillow import img_format
    p = _make_jpeg(tmp_path / 'test.jpg', width=120, height=80, quality=90)
    fmt = img_format(str(p))
    assert fmt['format'] == 'JPEG'
    assert fmt['width'] == 120
    assert fmt['height'] == 80
    assert fmt['scenes'] == 1
    assert isinstance(fmt['quality'], int)
    assert 1 <= fmt['quality'] <= 100


def test_img_format_png_no_alpha(tmp_path):
    from imgfind.lib.pillow import img_format
    p = _make_png(tmp_path / 'test.png', width=200, height=100, alpha=False)
    fmt = img_format(str(p))
    assert fmt['format'] == 'PNG'
    assert fmt['width'] == 200
    assert fmt['height'] == 100
    assert fmt['alpha'] is False
    assert fmt['scenes'] == 1


def test_img_format_png_with_alpha(tmp_path):
    from imgfind.lib.pillow import img_format
    p = _make_png(tmp_path / 'test.png', width=64, height=64, alpha=True)
    fmt = img_format(str(p))
    assert fmt['format'] == 'PNG'
    assert fmt['alpha'] is True


def test_img_format_webp(tmp_path):
    from imgfind.lib.pillow import img_format
    p = _make_webp(tmp_path / 'test.webp', width=50, height=50, quality=75)
    fmt = img_format(str(p))
    assert fmt['format'] == 'WEBP'
    assert fmt['width'] == 50
    assert fmt['height'] == 50
    assert fmt['scenes'] == 1


def test_img_format_gif(tmp_path):
    from imgfind.lib.pillow import img_format
    p = _make_gif(tmp_path / 'test.gif', width=40, height=40)
    fmt = img_format(str(p))
    assert fmt['format'] == 'GIF'
    assert fmt['scenes'] >= 1


# --- convert tests ---

def test_convert_jpeg_to_webp(tmp_path):
    from imgfind.lib.pillow import convert
    src = _make_jpeg(tmp_path / 'src.jpg')
    convert(str(src), 'webp', quality=80)
    out = tmp_path / 'src.webp'
    assert out.exists()
    with Image.open(out) as img:
        assert img.format == 'WEBP'
        assert img.width == 100
        assert img.height == 80


def test_convert_png_to_jpg(tmp_path):
    from imgfind.lib.pillow import convert
    src = _make_png(tmp_path / 'src.png')
    convert(str(src), 'jpg', quality=85)
    out = tmp_path / 'src.jpg'
    assert out.exists()
    with Image.open(out) as img:
        assert img.format == 'JPEG'


def test_convert_with_resize_width(tmp_path):
    """Convert and resize by specifying target width only."""
    from imgfind.lib.pillow import convert
    src = _make_jpeg(tmp_path / 'src.jpg', width=200, height=100)
    convert(str(src), 'jpg', quality=80, size=(50, None))
    out = tmp_path / 'src.jpg'
    assert out.exists()
    with Image.open(out) as img:
        assert img.width == 50
        assert img.height == 25  # half of 100


def test_convert_with_resize_height(tmp_path):
    """Convert and resize by specifying target height only."""
    from imgfind.lib.pillow import convert
    src = _make_jpeg(tmp_path / 'src.jpg', width=200, height=100)
    convert(str(src), 'jpg', quality=80, size=(None, 50))
    out = tmp_path / 'src.jpg'
    assert out.exists()
    with Image.open(out) as img:
        assert img.height == 50
        assert img.width == 100  # double of 50


def test_convert_with_explicit_size(tmp_path):
    """Convert and resize to explicit (w, h)."""
    from imgfind.lib.pillow import convert
    src = _make_jpeg(tmp_path / 'src.jpg', width=200, height=100)
    convert(str(src), 'webp', quality=80, size=(60, 40))
    out = tmp_path / 'src.webp'
    assert out.exists()
    with Image.open(out) as img:
        assert img.width == 60
        assert img.height == 40


# --- guess_quality tests ---

def test_guess_quality_jpeg(tmp_path):
    from imgfind.lib.pillow import guess_quality
    p = _make_jpeg(tmp_path / 'test.jpg', quality=85)
    with Image.open(p) as img:
        q = guess_quality(img)
    assert isinstance(q, int)
    assert 1 <= q <= 100


def test_guess_quality_png(tmp_path):
    from imgfind.lib.pillow import guess_quality
    p = _make_png(tmp_path / 'test.png')
    with Image.open(p) as img:
        q = guess_quality(img)
    assert q == 100  # PNG always returns 100


def test_guess_quality_webp(tmp_path):
    from imgfind.lib.pillow import guess_quality
    p = _make_webp(tmp_path / 'test.webp', quality=80)
    with Image.open(p) as img:
        q = guess_quality(img)
    assert isinstance(q, int)
    assert 1 <= q <= 100
