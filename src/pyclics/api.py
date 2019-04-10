import json
import pkg_resources

from clldutils.apilib import API
from clldutils.path import write_text, read_text
from clldutils.misc import lazyproperty
from clldutils import jsonlib
from csvw.dsv import UnicodeWriter
from zope.component import getGlobalSiteManager, getUtility

from pyclics.db import Database
from pyclics.models import Network
from pyclics import interfaces
from pyclics import plugin

__all__ = ['Clics']


def register_clusterer(registry, obj, name=None):
    registry.registerUtility(obj, interfaces.IClusterer, name or obj.__name__)


def register_colexifier(registry, obj):
    registry.registerUtility(obj, interfaces.IColexifier)


def register_clicsfom(registry, obj):
    registry.registerUtility(obj, interfaces.IClicsForm)


class Clics(API):
    _log = None

    def __init__(self, repos=None):
        API.__init__(self, repos=repos)

        # Initialize component registry:
        self.gsm = getGlobalSiteManager()

        # Add methods to register utilities to the registry, so plugins don't have to deal with
        # ZCA details at all:
        self.gsm.register_clusterer = register_clusterer.__get__(self.gsm)
        self.gsm.register_colexifier = register_colexifier.__get__(self.gsm)
        self.gsm.register_clicsform = register_clicsfom.__get__(self.gsm)

        # Load defaults for pluggable functionality first:
        plugin.includeme(self.gsm)

        # Now load third-party plugins:
        for ep in pkg_resources.iter_entry_points('clics.plugin'):
            ep.load()(self.gsm)

    @lazyproperty
    def cluster_algorithms(self):
        res = []
        for util in self.gsm.registeredUtilities():
            if util.provided == interfaces.IClusterer:
                res.append(util.name)
        return res

    def get_clusterer(self, name):
        return getUtility(interfaces.IClusterer, name)

    @lazyproperty
    def colexifier(self):
        return getUtility(interfaces.IColexifier)

    @lazyproperty
    def clicsform(self):
        return getUtility(interfaces.IClicsForm)

    def existing_dir(self, *comps, **kw):
        d = self.path()
        comps = list(comps)
        while comps:
            d = d.joinpath(comps.pop(0))
            if not d.exists():
                d.mkdir()
            assert d.is_dir()
        if kw.get('clean'):
            for p in d.iterdir():
                if p.is_file():
                    p.unlink()
        return d

    @lazyproperty
    def db(self):
        return Database(self.path('clics.sqlite'), self.clicsform)

    @lazyproperty
    def graph_dir(self):
        return self.existing_dir('graphs')

    def file_written(self, p):
        if self._log:
            self._log.info('{0} written'.format(p))
        return p

    def csv_writer(self, comp, name, delimiter=',', suffix='csv'):
        p = self.existing_dir(comp).joinpath('{0}.{1}'.format(name, suffix))
        self.file_written(p)
        return UnicodeWriter(p, delimiter=delimiter)

    def json_dump(self, obj, *path):
        p = self.existing_dir(*path[:-1]) / path[-1]
        jsonlib.dump(obj, p, indent=2)
        self.file_written(p)

    def write_js_var(self, var_name, var, *path):
        p = self.path(*path)
        v = json.loads(read_text(p)[:-1].partition('=')[2]) if p.exists() else {}
        v[var_name] = var
        write_text(p, 'var CLUSTERS = ' + json.dumps(v, indent=2) + ';')
        self.file_written(p)

    def save_graph(self, graph, network, threshold, edgefilter):
        network = Network(network, threshold, edgefilter, self.graph_dir)
        return self.file_written(network.save(graph))

    def load_graph(self, network, threshold, edgefilter):
        return Network(network, threshold, edgefilter, self.graph_dir).graph
