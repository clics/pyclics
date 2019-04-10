from collections import defaultdict

import igraph

__all__ = ['networkx2igraph', 'get_communities', 'parse_kwargs']


def networkx2igraph(graph):
    """Helper function converts networkx graph to igraph graph object."""
    newgraph = igraph.Graph(directed=graph.is_directed())
    nodes = {}
    for i, (node, data) in enumerate(graph.nodes(data=True)):
        data = {a: b for a, b in data.items()}
        newgraph.add_vertex(
            i, Name=node, **{a: b for a, b in data.items() if a not in ['Name', 'name']})
        nodes[node] = i
    for node1, node2, data in graph.edges(data=True):
        newgraph.add_edge(nodes[node1], nodes[node2], **{a: b for a, b in data.items()})
    return newgraph


def get_communities(graph, name='infomap'):
    """
    :return: a dict mapping cluster names to lists of nodes in the cluster.
    """
    comms = defaultdict(list)
    for node, data in graph.nodes(data=True):
        if name in data:
            comms[data[name]].append(node)
    return comms


def parse_kwargs(*args):
    res = {}
    for arg in args:
        name, _, value = arg.partition('=')
        res[name] = value or None
    return res
