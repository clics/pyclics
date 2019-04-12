"""
Pluggable functionality for CLICS
"""
import itertools
from collections import defaultdict
import string

from unidecode import unidecode
from tqdm import tqdm

from pyclics.util import networkx2igraph

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

    :param forms: The forms of a wordlist.

    :return: colexifictions, a dictionary taking the entries as keys and tuples
        consisting of a concept and its index as values
    :rtype: dict

    Note
    ----
    Colexifications are identified using a hash (Python dictionary) and a
    linear iteration through the graph. As a result, this approach is very
    fast, yet the results are potentially a bit counter-intuitive, as they are
    presented as a dictionary containing word values as keys. To get all
    colexifications in sets, however, you can just take the values of the
    dictionary.
    """
    cols = defaultdict(list)
    for form in forms:
        if form.clics_form and form.concepticon_id:
            cols[form.clics_form].append(form)
    return list(cols.values())


#
# Cluster algorithms:
#
def subgraph(graph, kw):
    all_nodes = {n for n in graph.nodes}
    all_edges = {tuple(sorted(e, key=lambda i: int(i))) for e in graph.edges()}
    subgraphs = []
    for node, data in graph.nodes(data=True):
        generations = [{node}]
        while generations[-1] and len(set.union(*generations)) < 30 and len(generations) < 3:
            nextgen = set.union(*[set(graph[n].keys()) for n in generations[-1]])
            if len(nextgen) > 50:
                break  # pragma: no cover
            else:
                generations.append(set.union(*[set(graph[n].keys()) for n in generations[-1]]))
        subgraphs.append(list(set.union(*generations)))

    # Iterate over subgraphs by descending number of nodes:
    for sg in sorted(subgraphs, key=lambda i: len(i), reverse=True):
        if (not all_nodes) and (not all_edges):
            break
        all_nodes -= set(sg)
        all_edges -= set(itertools.combinations(sorted(sg, key=lambda i: int(i)), 2))
        yield sg


def infomap(graph, kw):
    edge_weights = kw.pop('weight', 'FamilyWeight')
    vertex_weights = str('FamilyFrequency')

    _graph = graph
    for n, d in tqdm(_graph.nodes(data=True), desc='vertex-weights', leave=False):
        d[vertex_weights] = int(d[vertex_weights])

    if kw.pop('normalize', False):
        for edgeA, edgeB, data in tqdm(_graph.edges(data=True), desc='normalizing', leave=False):
            data[str('weight')] = data[edge_weights] ** 2 / (
                _graph.node[edgeA][vertex_weights] +
                _graph.node[edgeB][vertex_weights] -
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
