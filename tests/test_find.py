"""Tests for imgfind.find.main (match_image and related utilities)."""
import argparse
import pytest
from pathlib import Path
from PIL import Image


def _make_options(**kwargs):
    """Create a minimal Options namespace with default values."""
    defaults = dict(
        format=None,
        width=None,
        height=None,
        ratio=None,
        animated=None,
        wrong_ext=False,
        ai=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_jpeg(path, width=100, height=80, quality=85):
    img = Image.new('RGB', (width, height), color=(100, 150, 200))
    img.save(path, format='JPEG', quality=quality)
    return path


def _make_png(path, width=100, height=80, alpha=False):
    mode = 'RGBA' if alpha else 'RGB'
    color = (0, 200, 100, 200) if alpha else (0, 200, 100)
    img = Image.new(mode, (width, height), color=color)
    img.save(path, format='PNG')
    return path


def _make_gif(path, width=100, height=80):
    img = Image.new('P', (width, height), color=0)
    img.save(path, format='GIF')
    return path


# --- match_image: basic ---

def test_match_image_jpeg(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg')
    args = _make_options()
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_png(tmp_path):
    from imgfind.find.main import match_image
    p = _make_png(tmp_path / 'test.png')
    args = _make_options()
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


# --- match_image: format filter ---

def test_match_image_format_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg')
    args = _make_options(format='jpeg')
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_format_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg')
    args = _make_options(format='png')
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


# --- match_image: width filter ---

def test_match_image_width_exact_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=80)
    args = _make_options(width=100)
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_width_exact_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=80)
    args = _make_options(width=200)
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


def test_match_image_width_expr_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    from imgfind.find.options import relative_int
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=80)
    args = _make_options(width=relative_int('>= 100'))
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_width_expr_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    from imgfind.find.options import relative_int
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=80)
    args = _make_options(width=relative_int('> 200'))
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


# --- match_image: height filter ---

def test_match_image_height_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=80)
    args = _make_options(height=80)
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_height_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=80)
    args = _make_options(height=100)
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


# --- match_image: ratio filter ---

def test_match_image_ratio_landscape(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=200, height=100)
    args = _make_options(ratio='landscape')
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_ratio_landscape_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=200)
    args = _make_options(ratio='landscape')
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


def test_match_image_ratio_portrait(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=200)
    args = _make_options(ratio='portrait')
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_ratio_square(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=100)
    args = _make_options(ratio='square')
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_ratio_square_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=100, height=80)
    args = _make_options(ratio='square')
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


def test_match_image_ratio_numeric(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    # 4:3 ratio
    p = _make_jpeg(tmp_path / 'test.jpg', width=400, height=300)
    args = _make_options(ratio='4:3')
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_ratio_numeric_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_jpeg(tmp_path / 'test.jpg', width=400, height=300)
    args = _make_options(ratio='16:9')
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


# --- match_image: animated filter ---

def test_match_image_animated_static(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_gif(tmp_path / 'test.gif')
    # --no-animated: match static images only
    args = _make_options(animated=False)
    img = match_image(Path(p), args)
    assert img is not None
    img.close()


def test_match_image_animated_filter_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    p = _make_gif(tmp_path / 'test.gif')
    # --animated: match animated only; this is a static GIF
    args = _make_options(animated=True)
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


# --- match_image: wrong_ext filter ---

def test_match_image_wrong_ext(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    # Save a PNG file with a .jpg extension
    img = Image.new('RGB', (100, 80), color=(50, 100, 150))
    p = tmp_path / 'test.jpg'
    img.save(p, format='PNG')
    args = _make_options(wrong_ext=True)
    result = match_image(Path(p), args)
    assert result is not None
    result.close()


def test_match_image_wrong_ext_no_match(tmp_path):
    from imgfind.find.main import match_image, NotMatchedError
    # Correct extension
    p = _make_jpeg(tmp_path / 'test.jpg')
    args = _make_options(wrong_ext=True)
    with pytest.raises(NotMatchedError):
        match_image(Path(p), args)


# --- compare_value ---

def test_compare_value_int_match():
    from imgfind.find.main import compare_value
    assert compare_value(100, 100) is True


def test_compare_value_int_no_match():
    from imgfind.find.main import compare_value
    assert compare_value(100, 200) is False


def test_compare_value_callable_match():
    from imgfind.find.main import compare_value
    assert compare_value(lambda x: x >= 100, 150) is True


def test_compare_value_callable_no_match():
    from imgfind.find.main import compare_value
    assert compare_value(lambda x: x >= 100, 50) is False
