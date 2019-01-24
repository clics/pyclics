from zope.interface import Interface


class IClicsForm(Interface):
    def __call__(self, form):
        """
        :param form: a `pyclics.models.Form` instance.
        :return: a string value, derived from form to be compared when computing colexifications.
        """


class IColexifier(Interface):
    def __call__(self, wordlist):
        """
        :param wordlist: a `list` of `pyclics.models.Form` instances.
        :return: a `list` of `list`s, partitioning the forms.
        """


class IClusterer(Interface):
    def __call__(self, graph, kw):
        """
        :param graph: a `networkx.Graph` instance representing the colexification network.
        :param kw: `dict` of keyword arguments passed from the command line.
        :return: a generator of `list`s of node names, representing the clusters detected by \
        the algorithm.
        """
