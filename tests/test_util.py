from networkx import Graph

from pyclics.util import iter_subgraphs, write_gml


def test_write_gml(tmp_path):
    g = Graph()
    g.add_node('n1', k=['a', 'b'])
    g.add_node('n2', k=['a', 'b'])
    g.add_edge('n1', 'n2', k=['a', 'b'])
    p = tmp_path / 'test.gml'
    write_gml(g, p)
    assert 'a//b' in p.read_text(encoding='utf8')


def test_iter_subgraphs(graph):
    assert len(list(iter_subgraphs(graph))) == 2
