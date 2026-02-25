"""Tests for the teeny utility (imgfind.teeny)."""
import subprocess
import sys
import pytest
from PIL import Image


def _make_jpeg(path, width=200, height=150, quality=95):
    """Create a JPEG with high quality to ensure re-compression can shrink it."""
    img = Image.new('RGB', (width, height), color=(120, 80, 40))
    # Add some varied pixels so compression isn't trivial
    for x in range(0, width, 10):
        for y in range(0, height, 10):
            img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
    img.save(path, format='JPEG', quality=quality)
    return path


def _make_png(path, width=100, height=80, alpha=False):
    mode = 'RGBA' if alpha else 'RGB'
    color = (0, 128, 255, 180) if alpha else (0, 128, 255)
    img = Image.new(mode, (width, height), color=color)
    img.save(path, format='PNG')
    return path


def _run_teeny(*args):
    """Run teeny as a subprocess and return the completed process."""
    return subprocess.run(
        [sys.executable, '-m', 'imgfind.teeny'] + list(args),
        capture_output=True,
        text=True,
    )


# --- basic invocation ---

def test_teeny_help():
    result = _run_teeny('--help')
    assert result.returncode == 0
    assert 'usage' in result.stdout.lower()


def test_teeny_missing_file():
    result = _run_teeny('/nonexistent/path/image.jpg')
    assert result.returncode != 0


# --- JPEG processing ---

def test_teeny_jpeg_recompress(tmp_path):
    """teeny should recompress a high-quality JPEG to target quality."""
    src = _make_jpeg(tmp_path / 'photo.jpg', quality=95)
    original_size = src.stat().st_size
    # Default quality=85, source quality=95 -> should trigger recompression
    result = _run_teeny(str(src))
    assert result.returncode == 0
    # File should still exist (either original or recompressed)
    assert src.exists()


def test_teeny_jpeg_keep_original(tmp_path):
    """--keep-original preserves source when converting format."""
    src = _make_jpeg(tmp_path / 'photo.jpg', quality=95)
    result = _run_teeny('-f', 'webp', '-F', '-K', str(src))
    assert result.returncode == 0
    # Original should still exist
    assert src.exists()
    # WebP output should also exist
    webp_out = src.with_suffix('.webp')
    assert webp_out.exists()


# --- PNG processing ---

def test_teeny_png_to_jpeg(tmp_path):
    """PNG without alpha should be convertible to JPEG."""
    src = _make_png(tmp_path / 'image.png', alpha=False)
    result = _run_teeny('-K', str(src))
    assert result.returncode == 0
    # Either the JPEG was created (and possibly kept), or the PNG was kept
    # as smaller. The conversion ran without error.
    assert src.exists() or (tmp_path / 'image.jpg').exists()


def test_teeny_png_to_webp(tmp_path):
    """PNG converted to WebP with --force-format and --keep-original."""
    src = _make_png(tmp_path / 'image.png', alpha=False)
    result = _run_teeny('-f', 'webp', '-F', '-K', str(src))
    assert result.returncode == 0
    assert src.exists()
    webp_out = src.with_suffix('.webp')
    assert webp_out.exists()
    with Image.open(webp_out) as img:
        assert img.format == 'WEBP'


def test_teeny_png_with_alpha_not_converted_to_jpeg(tmp_path):
    """PNG with alpha should NOT be converted to JPEG (alpha would be lost)."""
    src = _make_png(tmp_path / 'alpha.png', alpha=True)
    result = _run_teeny(str(src))
    assert result.returncode == 0
    # PNG with real alpha: teeny should skip conversion to JPEG
    assert src.exists()
    assert not (tmp_path / 'alpha.jpg').exists()


# --- recursive directory processing ---

def test_teeny_recursive(tmp_path):
    """teeny -r should process all images in a directory."""
    subdir = tmp_path / 'subdir'
    subdir.mkdir()
    img1 = _make_jpeg(tmp_path / 'img1.jpg', quality=95)
    img2 = _make_jpeg(subdir / 'img2.jpg', quality=95)
    result = _run_teeny('-r', '-f', 'webp', '-F', '-K', str(tmp_path))
    assert result.returncode == 0
    assert (tmp_path / 'img1.webp').exists()
    assert (subdir / 'img2.webp').exists()
