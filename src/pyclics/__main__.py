import sys
import contextlib
import random
import argparse

import numpy
from clldutils.clilib import register_subcommands, get_parser_and_subparsers
from clldutils.loglib import Logging

from pyclics import Clics
import pyclics.commands


def setseed(s):
    if s is not None:
        try:
            s = int(s)
        except ValueError:
            raise argparse.ArgumentError(None, 'seed must be an integer')
        random.seed(s)
        numpy.random.seed(s)
        return s


def main(args=None, catch_all=False, parsed_args=None, log=None):
    parser, subparsers = get_parser_and_subparsers('clics')
    parser.add_argument(
        '--repos',
        help="Repository or output directory",
        default=Clics('.'),
        type=Clics)

    parser.add_argument('-s', '--seed', type=setseed, default=None)
    parser.add_argument('-t', '--threshold', type=int, default='1')
    parser.add_argument('-f', '--edgefilter', default='families')
    parser.add_argument('-g', '--graphname', default='network')

    register_subcommands(subparsers, pyclics.commands)

    args = parsed_args or parser.parse_args(args=args)

    if not hasattr(args, "main"):
        parser.print_help()
        return 1

    args.api = args.repos
    with contextlib.ExitStack() as stack:
        if not log:
            stack.enter_context(Logging(args.log, level=args.log_level))
        else:
            args.log = log
        try:
            return args.main(args) or 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0
        except argparse.ArgumentError as e:
            print(e)
            return main([args._command, '-h'])
        except Exception as e:  # pragma: no cover
            if catch_all:
                print(e)
                return 1
            raise


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main() or 0)
