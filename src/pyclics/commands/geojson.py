"""

"""
import itertools

from cldfbench.cli_util import add_catalog_spec
from geojson import FeatureCollection, Feature, Point, dumps
from clldutils.misc import nfilter
from clldutils.color import qualitative_colors

from pyclics.util import catalog


def register(parser):
    add_catalog_spec(parser, 'glottolog')


def run(args):
    with catalog('glottolog', args) as glottolog:
        languoids = {l.id: l for l in glottolog.api.languoids()}

    l2point = {}
    for l in languoids.values():
        if l.latitude is not None:
            l2point[l.id] = Point((l.longitude, l.latitude))

    for l in languoids.values():
        if l.id not in l2point and l.level.name == 'dialect':
            for _, gc, _ in reversed(l.lineage):  # pragma: no cover
                if gc in l2point:
                    l2point[l.id] = l2point[gc]

    def valid_languoid(gc):
        if gc in l2point:
            return languoids[gc]

    langs_by_family, isolates = {}, []
    for family, langs in itertools.groupby(
        args.api.db.fetchall("select id, glottocode, family from languagetable order by family"),
        lambda r: r[2],
    ):
        langs = nfilter([valid_languoid(gc) for gc in set(l[1] for l in langs)])
        if family:
            langs_by_family[family] = langs
        else:
            isolates = langs

    colors = qualitative_colors(len(langs_by_family) + len(isolates))

    def feature(l, color):
        if l.level.name == 'dialect':
            fam = 'dialect'  # pragma: no cover
        else:
            fam = languoids[l.lineage[0][1]].name if l.lineage else 'isolate'
        return Feature(
            id=l.id,
            geometry=l2point[l.id],
            properties={
                'title': '{0} [{1}]'.format(l.name, fam),
                'fill-opacity': 0.5,
                'marker-size': 'small',
                'marker-color': color},
        )

    features, i = [], 0
    for i, (fam, langs) in enumerate(
            sorted(langs_by_family.items(), key=lambda i: (-len(i[1]), i[0]))):
        for lang in langs:
            features.append(feature(lang, colors[i]))

    for j, lang in enumerate(isolates):  # pragma: no cover
        features.append(feature(lang, colors[i + j + 1]))

    (args.api.repos / 'languoids.geojson').write_text(
        dumps(FeatureCollection(features), indent=4), encoding='utf8')
