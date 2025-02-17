import sys

if __package__ == "" and not hasattr(sys, "frozen"):
    import os
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.realpath(path))

import imgfind

if __name__ == "__main__":
    sys.exit(imgfind.main())
