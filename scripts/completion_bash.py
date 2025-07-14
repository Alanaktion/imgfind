#!/usr/bin/env python3
"""Generate bash completion scripts from argument parsers"""

from argparse import ArgumentParser
import os

try:
    from imgfind.find import options as find_options
    from imgfind.vfind import options as vfind_options
    from imgfind.teeny import options as teeny_options
    from imgfind.vteeny import options as vteeny_options
except ModuleNotFoundError:
    import sys
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.realpath(path))

    from imgfind.find import options as find_options
    from imgfind.vfind import options as vfind_options
    from imgfind.teeny import options as teeny_options
    from imgfind.vteeny import options as vteeny_options


TEMPLATE = """_%(cmd)s()
{
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [[ "${prev}" =~ ^(%(fileopts)s)$ ]]; then
        COMPREPLY=( $(compgen -f -- "${cur}") )
    elif [[ "${prev}" =~ ^(%(diropts)s)$ ]]; then
        COMPREPLY=( $(compgen -d -- "${cur}") )
    else
        COMPREPLY=( $(compgen -W "%(opts)s" -- "${cur}") )
    fi
}

complete -F _%(cmd2)s %(cmd3)s
"""


def build_opts(parser: ArgumentParser):
    opts = []
    diropts = []
    fileopts = []
    for action in parser._actions:

        if action.metavar in ("DEST",):
            diropts.extend(action.option_strings)

        elif action.metavar in ("FILE", "CFG"):
            fileopts.extend(action.option_strings)

        for opt in action.option_strings:
            if opt.startswith("--"):
                opts.append(opt)
    return diropts, fileopts, opts


everything: list[tuple[str, ArgumentParser]] = [
    ('ifind', find_options.build_parser()),
    ('vfind', vfind_options.build_parser()),
    ('teeny', teeny_options.build_parser()),
    ('vteeny', teeny_options.build_parser()),
]

for cmd, parser in everything:
    diropts, fileopts, opts = build_opts(parser)
    os.makedirs("build/completion", exist_ok=True)
    PATH = "build/completion/%s" % cmd
    with open(PATH, 'w') as fp:
        fp.write(TEMPLATE % {
            "cmd": cmd,
            "cmd2": cmd,
            "cmd3": cmd,
            "opts": " ".join(opts),
            "diropts": "|".join(diropts),
            "fileopts": "|".join(fileopts),
        })
