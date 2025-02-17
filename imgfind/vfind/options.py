import argparse
import logging


def build_parser():
    parser = argparse.ArgumentParser(description='Find video/audio files')
    parser.add_argument('dir', nargs='?', default='.')

    filters = parser.add_argument_group('filters')
    filters.add_argument('-c', '--container')
    filters.add_argument('-v', '--video-codec')
    filters.add_argument('-a', '--audio-codec')
    filters.add_argument('-r', '--res', type=int)
    filters.add_argument('-H', '--height', type=int)
    filters.add_argument('-w', '--width', type=int)
    filters.add_argument('-R', '--ratio', type=str)
    filters.add_argument('-f', '--fps', type=float,
                         help='average fps, rounded to nearest multiple of 10')
    # filters.add_argument('-d', '--duration', type=int)

    parser.add_argument('-F', '--filter', metavar='EXPR', action='append',
                        help='Python expression to filter result')

    parser.add_argument('--exec', type=str,
                        help='execute this command on each file')
    parser.add_argument('--execdir', type=str,
                        help='execute this command from the file directory')
    parser.add_argument('-V', '--verbose',
                        action='store_const', dest='log_level',
                        default=logging.INFO, const=logging.DEBUG)

    return parser
