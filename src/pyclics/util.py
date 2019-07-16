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


def iter_subgraphs(graph, max_distance=2, max_nodes_pre=30, max_nodes_post=50):
    """

    Parameters
    ----------
    graph
    max_distance: The maximal distance of nodes from a central node in the subgraph.
    max_nodes_pre: The maximal number of nodes in a subgraph before adding another generation of \
    children.
    max_nodes_post: The maximal number of nodes in a subgraph.

    Returns
    -------
    A generator, yielding (node, subgraph) pairs, where node is the central node of the subgraph
    specified as list of node IDs.
    """
    for node, data in graph.nodes(data=True):
        generations = [{node}]
        while (
            generations[-1]  # There are nodes in the last generation.
            and len(set.union(*generations)) <= max_nodes_pre  # Current subgraph is still small.
            and len(generations) <= max_distance  # Maximal node distance not reached yet.
        ):
            nextgen = set.union(*[set(graph[n].keys()) for n in generations[-1]])
            if len(nextgen) > max_nodes_post:
                # Adding another generation would push us over the limit.
                break  # pragma: no cover
            else:
                generations.append(set.union(*[set(graph[n].keys()) for n in generations[-1]]))
        yield node, list(set.union(*generations))


def parse_kwargs(*args):
    res = {}
    for arg in args:
        name, _, value = arg.partition('=')
        res[name] = value or None
    return res
