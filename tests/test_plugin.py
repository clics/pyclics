from pyclics.plugin import full_colexification
from pyclics.models import Form


def test_colexification():
    formA = Form('', '', 'xy', 'abcd', '', '1', '', '', '')
    formB = Form('', '', 'yz', 'abcd', '', '2', '', '', '')
    res = list(full_colexification([formA, formB]))
    assert len(res[0]) == 2
