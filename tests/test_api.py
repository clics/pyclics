import collections

import pytest

from pyclics.api import Clics


@pytest.fixture
def api(tmpdir, mocker):
    res = Clics(str(tmpdir))
    res._log = mocker.Mock()
    return res


def test_iter_colexifications(api):
    Form = collections.namedtuple('Form', 'form clics_form concepticon_id')
    # Variants for the same concept resulting in the same clics_form should only be counted once!
    res = list(api._iter_colexifications([
        Form('a', 'x', '1'),
        Form('b', 'x', '1'),
        Form('c', 'x', '2'),
        Form('d', 'x', '2'),
    ]))
    assert len(res) == 1
    assert len(list(res[0])) == 1

    res = list(api._iter_colexifications([
        Form('a', 'x', '1'),
        Form('b', 'x', '2'),
        Form('c', 'x', '3'),
        Form('d', 'x', '4'),
    ]))
    assert len(res) == 1
    assert len(list(res[0])) == 6


def test_iter_subgraphs(api, graph, mocker):
    class Network:
        def __init__(self, *args, **kw):
            self.graph = graph
    mocker.patch('pyclics.api.Network', Network)
    assert list(api.iter_subgraphs(None, None, None))


def test_csv_writer(api):
    with api.csv_writer('test', 'test') as w:
        w.writerows([['a', 'b', 'c'], [1, 2, 3]])
    assert (api.repos / 'test' / 'test.csv').exists()
    assert api._log.info.called


def test_json_dump(api):
    api.json_dump({}, 'test.json')
    assert (api.repos / 'test.json').exists()
    assert api._log.info.called
