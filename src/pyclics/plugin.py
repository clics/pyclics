from tqdm import tqdm

from pyclics.interfaces import IClusterer, IGraph
from pyclics.util import networkx2igraph
from pyclics.hlc import HLC


def register_cluster_algorithm(registry, algo, name=None):
    registry.registerAdapter(algo, (IGraph,), IClusterer, name or algo.__name__)


def hlc(graph, kw):
    _graph = networkx2igraph(graph)
    algo = HLC(_graph)
    algo.run()
    for community in algo.run():
        yield _graph.vs[community]["name"]


def infomap(graph, kw):
    edge_weights = kw['weight']
    vertex_weights = str('FamilyFrequency')
    normalize = kw['normalize']

    _graph = graph
    for n, d in tqdm(_graph.nodes(data=True), desc='vertex-weights', leave=False):
        d[vertex_weights] = int(d[vertex_weights])

    if normalize:
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
    register_cluster_algorithm(registry, infomap)
    register_cluster_algorithm(registry, hlc)
