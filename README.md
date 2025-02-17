# imgfind

A simple Python utility to find and modify images in a filesystem, somewhat similar to [findutils](https://www.gnu.org/software/findutils/).

Also included are lightweight wrappers for ffprobe and GraphicsMagick via `vfind` and `teeny` utilities, for finding video files and quickly recompressing/optimizing images, respectively.

## Installation

Requires Python 3.5 or higher, but you should really be using the latest stable release.

```bash
python3 -m pip install -U imgfind
```

## Usage

The main utility installs as `ifind` globally, can be invoked with `python3 -m imgfind.find` if not on PATH.

Use `--help` to see all available options. Some examples:

```bash
# list all 2160p images in the current directory
ifind -w 3840 -h 2160

# list all 16:9 aspect ratio images in the current directory
ifind --ratio 16:9

# generate 200px-max thumbnail images from all images in ./src, storing them in ./thumbnails
ifind ./src --convert jpg --resize-max 200 --dest ./thumbnails

# find all PNG images in the user's Pictures directory that are at least 1920 pixels wide, and convert them to WebP using ImageMagick (via --exec)
ifind ~/Pictures --min-width 1920 --format png --exec 'magick convert -format webp {}'

# Convert large landscape images to 1080p wallpapers
ifind ./wallpapers --min-width 1920 --ratio landscape \
  --exec 'gm mogrify -format jpg -quality 85 -resize 1920x1080^ -gravity Center -crop 1920x1080 {}'
```

### Finding video files

If [ffmpeg](https://ffmpeg.org) is installed, the `vfind` utility can be used similarly to `ifind` to find video files.

Use `--help` to see all available options. Some examples:

```bash
# list all 2160p videos in the current directory
vfind --res 2160

# list all 16:9 aspect ratio videos in the current directory
vfind --ratio 16:9

# Advanced filtering can be done via Python expressions
# Find portrait videos with either H.265/HEVC or AV1 codecs, and 50 fps or higher
vfind --ratio portrait --filter 'fps >= 50 and re.search(r"265|hevc|av1", video_codec)'

# use without package in path
python3 -m imgfind.vfind
```

### Optimizing image files

If [GraphicsMagick](http://www.graphicsmagick.org/) is installed, the `teeny` utility can be used to optimize or recompress images. **This utility is not lossless by default and will, by design, result in loss of quality for processed images.**

> Contributions are encouraged to help update this utility to work with Pillow and ImageMagick as fallbacks for GraphicsMagick, even if functionality would be more limited in those cases.

The most simple behavior is to pass a single image file, which will replace it with a more optimized/heavily compressed version if needed. Use `--help` to see all available options.

```bash
# optimize a single image
teeny example.jpg

# optimize a directory recursively
# recursive operations run conversion subprocesses in parallel for improved performance
teeny -r ~/Pictures/Wallpapers

# convert all PNG images to WebP at 70% quality, resizing to a maximum height of 1080px
teeny -r --glob '*.png' -f webp --quality 70 --height 1080 .

# use without package in path
python3 -m imgfind.teeny
```

## Building

You can run the imgfind code directly if you have the dependencies (Pillow/piexif) installed. No building is required as long as Pillow has been built. The imgfind package will handle updating paths at runtime if needed should you import or execute it outside of your site-packages.

If you want to build a release and optionally install locally or upload it to PyPI:

```bash
# Generate completion files (optional)
python3 scripts/completion_bash.py
python3 scripts/completion_fish.py
python3 scripts/completion_zsh.py

# Build package
python3 -m pip install -U build twine
python3 -m build --wheel

# Upload build to PyPI
twine upload dist/*
```
