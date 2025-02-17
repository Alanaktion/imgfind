import os
from setuptools import setup


def check_file(f):
    path = os.path.join(os.path.dirname(__file__), f)
    return os.path.exists(path)


# TODO: run completion build: scripts/completion*.py automatically
data_files = [
    (path, [f for f in files if check_file(f)])
    for (path, files) in [
        ("share/bash-completion/completions", [
            "build/completion/ifind",
            "build/completion/vfind",
            "build/completion/teeny",
        ]),
        ("share/zsh/site-functions", [
            "build/completion/_ifind",
            "build/completion/_vfind",
            "build/completion/_teeny",
        ]),
        ("share/fish/vendor_completions.d", [
            "build/completion/ifind.fish",
            "build/completion/vfind.fish",
            "build/completion/teeny.fish",
        ]),
    ]
]

setup(data_files=data_files)
