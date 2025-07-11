import argparse
import logging


def build_parser():
    parser = argparse.ArgumentParser(description='Make a video file teeny')
    parser.add_argument('file', nargs='+')

    parser.add_argument('-r', '--recursive', action='store_true',
                        help='operate on all videos in the specified path')
    parser.add_argument('--glob',
                        help='operate on files matching this pattern')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-V', '--verbose',
                       action='store_const', dest='log_level',
                       default=logging.INFO, const=logging.DEBUG)
    group.add_argument('-q', '--quiet',
                       action='store_const', dest='log_level',
                       default=logging.INFO, const=logging.WARNING)

    fmt = parser.add_argument_group('format options')
    cnt = fmt.add_mutually_exclusive_group()
    cnt.add_argument('-c', '--container', choices=['mp4', 'webm', 'mkv'],
                     default='mp4')
    cnt.add_argument('--keep-container', action='store_true',
                     help='keep the original container, only re-encode')
    cdc = fmt.add_mutually_exclusive_group()
    cdc.add_argument('-v', '--video-codec', metavar='CODEC', default='hevc',
                     choices=['h264', 'hevc', 'vp8', 'vp9', 'av1'])
    cdc.add_argument('--keep-video-codec', action='store_true',
                     help='keep original codec, only re-encode if resizing')
    fmt.add_argument('-a', '--audio-codec', metavar='CODEC', default='copy',
                     choices=['copy', 'aac', 'vorbis', 'none'])
    fmt.add_argument('-C', '--chroma-subsampling', metavar='Ybr',
                     choices=['444', '422', '420'])

    # TODO: make a flexible quality setting?
    # fmt.add_argument('--quality', type=int, default=80, metavar='INT',
    #                  help='Target quality')

    size = parser.add_argument_group('size options')
    group = size.add_mutually_exclusive_group()
    group.add_argument('--res', type=int, metavar='INT',
                       help='limit minimum dimension to this value')
    group.add_argument('--width', type=int, metavar='INT',
                       help='limit width to this value')
    group.add_argument('--height', type=int, metavar='INT',
                       help='limit height to this value')

    parser.add_argument('-k', '--keep-original', action='store_true')

    return parser
