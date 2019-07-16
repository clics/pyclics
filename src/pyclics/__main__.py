import sys
import random
from pathlib import Path

import numpy
from clldutils.clilib import ArgumentParserWithLogging, ParserError

import pyclics
from pyclics.api import Clics
import pyclics.commands

assert pyclics.commands


def setseed(s):
    if s is not None:
        try:
            s = int(s)
        except ValueError:
            raise ParserError('seed must be an integer')
        random.seed(s)
        numpy.random.seed(s)
        return s


def main():  # pragma: no cover
    parser = ArgumentParserWithLogging(pyclics.__name__)

    # The following three options are used to determine the graph name:
    parser.add_argument('-s', '--seed', type=setseed, default=None)
    parser.add_argument('-t', '--threshold', type=int, default='1')
    parser.add_argument('-f', '--edgefilter', default='families')
    parser.add_argument('-g', '--graphname', default='network')

    parser.add_argument('--unloaded', action='store_true', default=False)
    parser.add_argument('-o', '--output', default=None, help='output directory')
    parser.add_argument('--api', help="Repository", type=Clics, default='.')
    args = parser.parse_args()
    if args.output:
        args.api.repos = Path(args.output)
    sys.exit(parser.main(parsed_args=args))
