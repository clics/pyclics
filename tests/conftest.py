from tempfile import NamedTemporaryFile
from pathlib import Path
import shutil

import pytest
from pylexibank.dataset import Dataset
import cldfcatalog.repository

from pyclics.db import Database
from pyclics.plugin import clics_form


@pytest.fixture
def repos(tmpdir):
    return Path(str(tmpdir))


def _make_repos(name, tmpdir):
    gl = Path(str(tmpdir.join(name)))
    shutil.copytree(cldfcatalog.repository.get_test_repo(str(tmpdir)).working_dir, str(gl))
    for d in Path(__file__).parent.joinpath(name).iterdir():
        if d.is_dir():
            shutil.copytree(str(d), str(gl / d.name))
    return str(gl)


@pytest.fixture
def glottolog(tmpdir):
    return _make_repos('glottolog', tmpdir)


@pytest.fixture
def concepticon(tmpdir):
    return _make_repos('concepticon', tmpdir)


@pytest.fixture(scope='session')
def dataset():
    class ClicsDataset(Dataset):
        dir = str(Path(__file__).parent / 'dataset')
        id = 'td'

    return ClicsDataset()


@pytest.fixture(scope='session')
def db(dataset):
    tmp = NamedTemporaryFile(delete=False)
    db = Database(tmp.name, clics_form)
    db.create(exists_ok=True)
    db.load(dataset)
    with db.connection() as conn:
        conn.execute("update LanguageTable set glottocode = 'glot1234', family='family'")
        conn.execute("""\
update ParameterTable set 
    concepticon_id = cast(random() as text),
    concepticon_gloss = 'gloss',
    ontological_category = 'oc',
    semantic_field = 'sf'""")
        conn.commit()
    yield db
    Path(tmp.name).unlink()
