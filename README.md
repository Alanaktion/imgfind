# imgfind

A simple Python utility to find images in a filesystem, similar to [findutils](https://www.gnu.org/software/findutils/).

## Installation

Requires Python 3.10 or higher, and the Pillow library.

```bash
python -m pip install -U imgfind
```

## Usage

Installs as `ifind` globally, can be invoked with `python3 -m imgfind` if not on PATH.

Use `--help` to see all available options. Example usage:

```bash
imgfind ~/Pictures --min-width 1920 --format png --exec 'convert -format webp "{}"'
```

## Building

```bash
python3 -m pip install -U build twine
python3 -m build --wheel .
twine upload dist/*
```
