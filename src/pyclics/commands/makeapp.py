"""
Create a local Javascript-powered app to explore a colexification network.

Note: Requires free disk space in the order of 2GB if subgraph clustering is computed.
"""
import pathlib
import shutil
import collections

import geojson

from pyclics.commands import cluster


def register(parser):
    parser.add_argument(
        'cluster',
        nargs='*',
        metavar='CLUSTER_METHODS',
        help="Cluster algorithms to run, formatted as 'METHOD[arg=value[;arg=value]]'",
        default=['subgraph', 'infomap'],
    )


def parse_cluster_method(s):
    algo, args = s, []
    if '[' in s:
        algo, args = s.split('[')
        assert args.endswith(']')
        args = args[:-1].split(';')
        args = [arg.strip() for arg in args]
    return algo.strip(), args


def run(args):
    args.repos._log = args.log

    varieties = args.repos.db.varieties
    lgeo = geojson.FeatureCollection([v.as_geojson() for v in varieties])
    args.repos.json_dump(lgeo, 'app', 'source', 'langsGeo.json')

    app_source = args.repos.existing_dir('app', 'source')
    for p in pathlib.Path(__file__).parent.parent.joinpath('app').iterdir():
        target_dir = app_source.parent if p.suffix == '.html' else app_source
        shutil.copy(str(p), str(target_dir / p.name))

    if app_source.joinpath('cluster-names.js').exists():  # pragma: no cover
        app_source.joinpath('cluster-names.js').unlink()

    words = collections.OrderedDict()
    for _, formA, formB in args.repos.iter_colexifications(varieties):
        words[formA.gid] = [formA.clics_form, formA.form]
    args.repos.json_dump(words, 'app', 'source', 'words.json')

    clusters = [parse_cluster_method(s) for s in args.cluster]
    for algo, arg in clusters:
        args.log.info('clustering ({0}[{1}]) ...'.format(algo, arg))
        args.algorithm = algo
        args.args = arg
        cluster.run(args)
    print("""Run
    clics runapp
to open the app in a browser.""")
