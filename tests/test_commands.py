import shutil
import logging

import pytest

from pyclics.api import Clics
from pyclics.__main__ import main


@pytest.fixture
def api(repos, db):
    dbfname = repos.joinpath('clics.sqlite')
    if not dbfname.exists():
        shutil.copy(str(db.fname), str(dbfname))
    return Clics(str(repos))


@pytest.fixture
def _main(repos):
    def cmd(*args, **kw):
        main(args=['--repos', str(repos)] + list(args), **kw)
    return cmd


def test_bad_seed(_main):
    with pytest.raises(SystemExit):
        _main('-s', 'x', 'load')


def test_help(_main, capsys):
    _main()
    out, _ = capsys.readouterr()
    assert 'usage:' in out


def test_load(mocker, glottolog, concepticon, dataset, _main, caplog):
    mocker.patch('pyclics.commands.load.iter_datasets', lambda **kw: [dataset])
    _main('load', '--glottolog', glottolog, '--concepticon', concepticon)
    with caplog.at_level(logging.INFO):
        _main(
            'load', '--unloaded', '--glottolog', glottolog, '--concepticon', concepticon,
            log=logging.getLogger(__name__))
        assert any('skipping' in rec.message for rec in caplog.records)
    _main('geojson', '--glottolog', glottolog)


def test_datasets(capsys, _main):
    _main('datasets', '--unloaded')
    _, _ = capsys.readouterr()

    _main('datasets')
    out, err = capsys.readouterr()


def test_cluster_algos(capsys, _main):
    _main('cluster', '_')
    out, _ = capsys.readouterr()
    assert 'infomap' in out


def test_unknown_cluster_algo(_main):
    with pytest.raises(SystemExit):
        _main('cluster', 'abc')


def test_workflow(api, mocker, capsys, _main):
    _main('-s', '10', 'colexification')
    out, err = capsys.readouterr()
    assert 'Concept B' in out

    _main('cluster', 'infomap')
    # test overwriting:
    _main('cluster', 'infomap')

    _main('cluster', 'subgraph', 'neighbor_weight=1')
    _main('graph_stats')
    out, _ = capsys.readouterr()
    assert '499' in out and '480' in out and '209' in out

    _main('cluster', 'infomap', 'normalize=1')

    _main('-t', '3', 'colexification')
    _main('-t', '3', 'graph_stats')
    out, _ = capsys.readouterr()
    assert 'edges          0' in out

    _main('-t', '3', '--edgefilter', 'languages', 'colexification')
    _main('-t', '3', '--edgefilter', 'languages', 'graph_stats')
    out, err = capsys.readouterr()
    assert 'edges        118' in out

    _main('-t', '5', '--edgefilter', 'words', 'colexification')
    _main('-t', '5', '--edgefilter', 'words', 'graph_stats')
    out, err = capsys.readouterr()
    assert 'edges         69' in out
