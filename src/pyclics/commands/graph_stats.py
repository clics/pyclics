"""
Display summary statistics about a colexification graph.
"""
import networkx as nx
from tabulate import tabulate

from pyclics.util import get_communities


def run(args):
    graph = args.repos.load_graph(args.graphname, args.threshold, args.edgefilter)
    print(tabulate([
        ['nodes', len(graph)],
        ['edges', len(graph.edges())],
        ['components', len(list(nx.connected_components(graph)))],
        ['communities', len(get_communities(graph))]
    ]))
