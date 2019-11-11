from networkx import Graph

from pyclics.util import iter_subgraphs


def test_iter_subgraphs(graph):
    assert len(list(iter_subgraphs(graph))) == 2
