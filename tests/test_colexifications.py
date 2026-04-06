from cltoolkit import Wordlist

from pyclics.colexifications import get_colexifications


def test_get_colexifications(dataset):
    wl = Wordlist([dataset.cldf_reader()])
    _ = get_colexifications(wl)
