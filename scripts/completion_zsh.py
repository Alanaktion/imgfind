#!/usr/bin/env python3
"""Generate zsh completion scripts from argument parsers"""

import argparse
import os


try:
    from imgfind.find import options as find_options
    from imgfind.vfind import options as vfind_options
    from imgfind.teeny import options as teeny_options
except ModuleNotFoundError:
    import sys
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.realpath(path))

    from imgfind.find import options as find_options
    from imgfind.vfind import options as vfind_options
    from imgfind.teeny import options as teeny_options

TEMPLATE = """#compdef %(cmd)s

local curcontext="$curcontext"
typeset -A opt_args

local rc=1
_arguments -s -S \\
%(opts)s && rc=0

return rc
"""

TR = str.maketrans({
    "'": "'\\''",
    "[": "\\[",
    "]": "\\]",
})


def build_opts(parser: argparse.ArgumentParser):
    opts = []
    for action in parser._actions:

        if not action.option_strings or action.help == argparse.SUPPRESS:
            continue
        elif len(action.option_strings) == 1:
            opt = action.option_strings[0]
        else:
            opt = "{" + ",".join(action.option_strings) + "}"

        if action.help:
            opt += "'[" + action.help.translate(TR) + "]'"
            if action.default is not None:
                opt = opt.replace('%(default)s', str(action.default))

        if isinstance(action.metavar, str):
            opt += ":'<" + action.metavar.lower() + ">'"
            if action.metavar in ("FILE", "CFG", "DEST"):
                opt += ":_files"

        opts.append(opt)
    return opts


everything: list[tuple[str, argparse.ArgumentParser]] = [
    ('ifind', find_options.build_parser()),
    ('vfind', vfind_options.build_parser()),
    ('teeny', teeny_options.build_parser()),
]

for cmd, parser in everything:
    opts = build_opts(parser)
    os.makedirs("build/completion", exist_ok=True)
    PATH = "build/completion/_%s" % cmd
    with open(PATH, 'w') as fp:
        fp.write(TEMPLATE % {
            "cmd": cmd,
            "opts": "\\\n".join(opts),
        })
