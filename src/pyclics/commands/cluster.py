"""
Cluster the colexification graph using one of the installed cluster algorithms.
Note: You must run "clics makeapp" before running this, to setup the scaffolding for the app.

Run "clics cluster _" for a list of available cluster algorithms.
"""
import collections
import argparse

from networkx.readwrite import json_graph
from tqdm import tqdm
from clldutils.clilib import Table, add_format
from clldutils import jsonlib


def register(parser):
    parser.add_argument(
        'algorithm',
        help='Name of cluster algorithm to use (pass "_" to list available algorithms)',
    )
    parser.add_argument(
        'args',
        nargs='*',
        metavar='CLUSTER_ARGS',
        help="Arguments to pass to the cluster algorithm, formatted as 'arg=value'",
    )
    add_format(parser, default='simple')


def run(args):
    from pyclics.util import parse_kwargs

    algo = args.algorithm

    if algo not in args.repos.cluster_algorithms:
        with Table(args, 'algorithm', 'description') as table:
            for name, desc in args.repos.cluster_algorithms.items():
                table.append((name, desc))
        if args.algorithm != '_':
            raise argparse.ArgumentError(None, 'Unknown cluster algorithm: {0}'.format(algo))
        return

    if not args.repos.repos.joinpath('app', 'source', 'words.json').exists():
        raise argparse.ArgumentError(None, '"clics makeapp" must be run first')

    graph = args.repos.load_graph(args.graphname, args.threshold, args.edgefilter)
    args.log.info('graph loaded')
    kw = vars(args)
    kw.update(parse_kwargs(*args.args))
    neighbor_weight = int(kw.pop('neighbor_weight', 5))

    clusters = sorted(args.repos.get_clusterer(algo)(graph, vars(args)), key=lambda c: (-len(c), c))
    args.log.info('computed clusters')

    D, Com = {}, collections.defaultdict(list)
    for i, cluster in enumerate(clusters, start=1):
        for vertex in cluster:
            D[vertex] = str(i)
            Com[i].append(vertex)

    # Annotate the graph with the cluster info:
    for node, data in graph.nodes(data=True):
        data.update({algo: D.get(node, '0'), 'ClusterName': '', 'CentralConcept': ''})

    # get the articulation points etc. immediately
    for idx, nodes in sorted(Com.items()):
        sg = graph.subgraph(nodes)
        if len(sg) > 1:
            d_ = sorted(sg.degree(), key=lambda x: x[1], reverse=True)
            d = [graph.nodes[a]['Gloss'] for a, b in d_][0]
            cluster_name = '{0}_{1}_{2}'.format(algo, idx, d)
        else:
            d = graph.nodes[nodes[0]]['Gloss']
            cluster_name = '{0}_{1}_{2}'.format(algo, idx, graph.nodes[nodes[0]]['Gloss'])
        for node in nodes:
            graph.nodes[node]['ClusterName'] = cluster_name
            graph.nodes[node]['CentralConcept'] = d

    args.log.info('computed cluster names')

    cluster_dir = args.repos.existing_dir('app', 'cluster', algo, clean=True)
    cluster_names = {}
    removed = []
    for idx, nodes in tqdm(sorted(Com.items()), desc='export to app', leave=False):
        sg = graph.subgraph(nodes)
        for node, data in sg.nodes(data=True):
            data['OutEdge'] = []
            neighbors = [
                n for n in graph if
                n in graph[node] and
                graph[node][n]['FamilyWeight'] >= neighbor_weight and
                n not in sg]
            if neighbors:
                sg.nodes[node]['OutEdge'] = []
                for n in neighbors:
                    sg.nodes[node]['OutEdge'].append([
                        graph.nodes[n]['ClusterName'],
                        graph.nodes[n]['CentralConcept'],
                        graph.nodes[n]['Gloss'],
                        graph[node][n]['WordWeight'],
                        n
                    ])
        if len(sg) > 1:
            fn = cluster_dir / (
                (str(idx) if algo == 'subgraph' else graph.nodes[nodes[0]]['ClusterName']) +
                '.json')
            jsonlib.dump(json_graph.adjacency_data(sg), fn, sort_keys=True)
            for node in nodes:
                cluster_names[graph.nodes[node]['Gloss']] = fn.stem
        else:
            removed += [list(nodes)[0]]
    graph.remove_nodes_from(removed)
    for node, data in graph.nodes(data=True):
        if 'OutEdge' in data:
            data['OutEdge'] = '//'.join(['/'.join([str(y) for y in x]) for x in data['OutEdge']])
    removed = []
    for nA, nB, data in tqdm(graph.edges(data=True), desc='remove edges', leave=False):
        if graph.nodes[nA][algo] != graph.nodes[nB][algo] and data['FamilyWeight'] < 5:
            removed += [(nA, nB)]
    graph.remove_edges_from(removed)

    args.repos.save_graph(graph, algo, args.threshold, args.edgefilter)
    args.repos.write_js_var(algo, cluster_names, 'app', 'source', 'cluster-names.js')
