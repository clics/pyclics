"""
Run and open the local CLICS app in a browser.

Stop with CTRL-q
"""
import argparse
import subprocess
import webbrowser
import time

from clldutils.clilib import confirm


def register(parser):  # pragma: no cover
    parser.add_argument(
        '--port',
        help='Port number to server the app on',
        default=8000,
        type=int,
    )


def run(args):  # pragma: no cover
    appdir = args.repos.repos / 'app'
    if not list(appdir.joinpath('cluster').iterdir()):
        raise argparse.ArgumentError(
            None,
            'There are no clusters in {0}!\nYou may have to run "clics cluster" first'.format(
                appdir))
    proc = subprocess.Popen(
        ['python', '-u', '-m', 'http.server', str(args.port)],
        cwd=str(appdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(2)
    url = 'http://localhost:{0}'.format(args.port)
    webbrowser.open(url)
    print('You should now see {0} opened in yur browser. If you are done using the app, press '
          'enter'.format(url))
    try:
        if confirm('quit?'):
            proc.terminate()
    finally:
        proc.terminate()
