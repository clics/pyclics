import sys
import argparse
import random
from pathlib import Path

import numpy
from clldutils.clilib import ArgumentParserWithLogging

import pyclics
from pyclics.api import Clics
import pyclics.commands

assert pyclics.commands

random.seed(123456)
numpy.random.seed(123456)


def main():  # pragma: no cover
    parser = ArgumentParserWithLogging(pyclics.__name__)

    # The following three options are used to determine the graph name:
    parser.add_argument('-t', '--threshold', type=int, default='1')
    parser.add_argument('-f', '--edgefilter', default='families')
    parser.add_argument('-g', '--graphname', default='network')

    parser.add_argument('--unloaded', action='store_true', default=False)
    parser.add_argument('-o', '--output', default=None, help='output directory')
    parser.add_argument('--api', help=argparse.SUPPRESS, default=Clics(Path('.')))
    args = parser.parse_args()
    if args.output:
        args.api.repos = Path(args.output)
    sys.exit(parser.main(parsed_args=args))
