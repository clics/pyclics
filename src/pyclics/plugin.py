"""
Pluggable functionality for CLICS
"""
import itertools
import string

from unidecode import unidecode
from tqdm import tqdm

from pyclics.util import networkx2igraph, iter_subgraphs

#
# Computation of the CLICS form of a lexeme:
#
# unidecode converts "ə" to "@"
ALLOWED_CHARACTERS = string.ascii_letters + string.digits + '@'


def clics_form(word):
    if word:
        return ''.join(c for c in unidecode(word) if c in ALLOWED_CHARACTERS).lower()


#
# Computation of colexifications among the forms of a wordlist:
#
def full_colexification(forms):
    """
    Calculate all colexifications inside a wordlist.

    :param forms: The forms of a wordlist, **sorted by clics_form**.

    :return: Generator of colexifictions - i.e. of `list`s, grouping `forms` by `clics_form`.

    Notes
    -----
    - Of variant forms for the same concept, resulting in the same `clics_form`, only one form
      will be picked.
    - Colexifications are identified using a hash (Python dictionary) and a
      linear iteration through the graph. As a result, this approach is very fast.
    """
    # We assume the forms to be sorted by clics_form already:
    expected, seen = len(forms), 0
    for _, _forms in itertools.groupby(forms, lambda f: f.clics_form):
        cids = set()
        fs = []
        for f in _forms:
            seen += 1
            if f.concepticon_id not in cids:
                fs.append(f)
                cids.add(f.concepticon_id)
        yield fs
    if expected != seen:  # pragma: no cover
        raise ValueError('forms not properly ordered')


#
# Cluster algorithms:
#
def subgraph(graph, kw):
    all_nodes = {n for n in graph.nodes}
    all_edges = {tuple(sorted(e, key=lambda i: int(i))) for e in graph.edges()}
    subgraphs = [sg for _, sg in iter_subgraphs(graph)]

    # Iterate over subgraphs by descending number of nodes:
    for sg in sorted(subgraphs, key=lambda i: len(i), reverse=True):
        if (not all_nodes) and (not all_edges):
            # all nodes and edges are included in at least one subgraph
            break  # pragma: no cover
        all_nodes -= set(sg)
        all_edges -= set(itertools.combinations(sorted(sg, key=lambda i: int(i)), 2))
        yield sg
    else:
        if all_nodes:  # pragma: no cover
            raise ValueError('unclustered nodes: {0}'.format(all_nodes))


def infomap(graph, kw):
    edge_weights = kw.pop('weight', 'FamilyWeight')
    vertex_weights = str('FamilyFrequency')

    _graph = graph
    for n, d in tqdm(_graph.nodes(data=True), desc='vertex-weights', leave=False):
        d[vertex_weights] = int(d[vertex_weights])

    if kw.pop('normalize', False):
        for edgeA, edgeB, data in tqdm(_graph.edges(data=True), desc='normalizing', leave=False):
            data[str('weight')] = data[edge_weights] ** 2 / (
                _graph.nodes[edgeA][vertex_weights] +
                _graph.nodes[edgeB][vertex_weights] -
                data[edge_weights])
        vertex_weights = None
        edge_weights = 'weight'

    graph = networkx2igraph(_graph)

    comps = graph.community_infomap(
        edge_weights=str(edge_weights), vertex_weights=vertex_weights)

    for comp in comps.subgraphs():
        yield [graph.vs[vertex['name']]['ConcepticonId'] for vertex in comp.vs]


def includeme(registry):
    registry.register_clicsform(clics_form)
    registry.register_colexifier(full_colexification)
    registry.register_clusterer(subgraph)
    registry.register_clusterer(infomap)
