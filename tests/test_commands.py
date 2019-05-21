from __future__ import unicode_literals
import shutil
import logging

import pytest
from clldutils.clilib import ParserError

from pyclics.api import Clics
from pyclics import commands
from pyclics import __main__  # noqa


@pytest.fixture
def api(repos, db):
    dbfname = repos.joinpath('clics.sqlite')
    if not dbfname.exists():
        shutil.copy(str(db.fname), str(dbfname))
    return Clics(str(repos))


def test_load(mocker, tmpdir, repos, dataset, caplog):
    with pytest.raises(ParserError):
        commands.load(mocker.Mock(args=[]))
    with pytest.raises(ParserError):
        commands.load(mocker.Mock(args=[str(repos), str(repos.joinpath('abc'))]))
    with pytest.raises(ParserError):
        commands.load(mocker.Mock(args=[str(repos.joinpath('abc')), str(repos)]))
    tmpdir.join('load').mkdir()
    api = Clics(str(tmpdir.join('load')))
    mocker.patch('pyclics.commands.iter_datasets', lambda: [dataset])
    commands.load(mocker.Mock(args=[str(repos), str(repos)], api=api))
    commands.load(mocker.Mock(args=[str(repos), str(repos)], api=api, unloaded=True))

    api.db.fname.write_bytes(b'')
    commands.load(mocker.Mock(args=[str(repos), str(repos)], api=api, log=logging.getLogger()))
    assert 'removing' in caplog.text


def test_list(api, mocker, capsys):
    commands.list_(mocker.Mock(api=api, unloaded=True))
    _, _ = capsys.readouterr()

    commands.list_(mocker.Mock(api=api, unloaded=False))
    out, err = capsys.readouterr()
    assert '9' in out


def test_cluster_algos(api, mocker, capsys):
    commands.cluster(mocker.Mock(api=api, args=['list']))
    out, _ = capsys.readouterr()
    assert 'infomap' in out


def test_unknown_cluster_algo(api, mocker):
    with pytest.raises(ParserError):
        commands.cluster(mocker.Mock(api=api, args=['unknown-algo']))


def test_workflow(api, mocker, capsys):
    args = mocker.Mock(
        args=[],
        api=api,
        graphname='g',
        threshold=1,
        edgefilter='families',
        weight='FamilyWeight')
    commands.colexification(args)
    out, err = capsys.readouterr()
    assert 'Concept B' in out

    args.args.append('infomap')
    commands.cluster(args)
    # test overwriting:
    commands.cluster(args)

    args.args = ['subgraph', 'neighbor_weight=1']
    commands.cluster(args)
    #commands.articulationpoints(args)
    commands.graph_stats(args)
    out, _ = capsys.readouterr()
    assert '499' in out and '480' in out and '209' in out

    args.args = ['infomap', 'normalize=1']
    commands.cluster(args)

    args.threshold = 3
    commands.colexification(args)
    commands.graph_stats(args)
    out, _ = capsys.readouterr()
    assert 'edges          0' in out
    args.threshold, args.edgefilter = 3, 'languages'
    commands.colexification(args)
    commands.graph_stats(args)
    out, err = capsys.readouterr()
    assert 'edges        118' in out
    args.threshold, args.edgefilter = 5, 'words'
    commands.colexification(args)
    commands.graph_stats(args)
    out, err = capsys.readouterr()
    assert 'edges         69' in out
