from zope.interface import Interface, Attribute


class IGraph(Interface):
    """marker interface"""


class IClusterer(Interface):
    def __call__(self, graph, **kw):
        pass
