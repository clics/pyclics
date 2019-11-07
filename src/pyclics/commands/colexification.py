"""
Compute the colexification graph
"""
import shutil
from pathlib import Path
from itertools import combinations

from tqdm import tqdm
import networkx as nx
import geojson
from clldutils.clilib import Table, add_format


def register(parser):
    add_format(parser, default='simple')
    parser.add_argument(
        '--show',
        help="Number of most common colexifications to display after computation",
        type=int,
        default=10)


def run(args):
    args.repos._log = args.log
    words = {}

    def clean(word):
        return ''.join([w for w in word if w not in '/,;"'])

    varieties = args.repos.db.varieties
    lgeo = geojson.FeatureCollection([v.as_geojson() for v in varieties])
    args.repos.json_dump(lgeo, 'app', 'source', 'langsGeo.json')

    app_source = args.repos.existing_dir('app', 'source')
    for p in Path(__file__).parent.parent.joinpath('app').iterdir():
        target_dir = app_source.parent if p.suffix == '.html' else app_source
        shutil.copy(str(p), str(target_dir / p.name))

    args.log.info('Adding nodes to the graph')
    G = nx.Graph()
    for concept in args.repos.db.iter_concepts():
        G.add_node(concept.id, **concept.as_node_attrs())

    args.log.info('Adding edges to the graph')
    for v_, forms in tqdm(args.repos.db.iter_wordlists(varieties), total=len(varieties), leave=False):
        for v in args.repos.colexifier(forms):
            for formA, formB in combinations(v, r=2):
                # check for identical concept resulting from word-variants
                if formA.concepticon_id != formB.concepticon_id:
                    words[formA.gid] = [formA.clics_form, formA.form]
                    if not G[formA.concepticon_id].get(formB.concepticon_id, False):
                        G.add_edge(
                            formA.concepticon_id,
                            formB.concepticon_id,
                            words=set(),
                            languages=set(),
                            families=set(),
                            wofam=[],
                        )

                    G[formA.concepticon_id][formB.concepticon_id]['words'].add(
                        (formA.gid, formB.gid))
                    G[formA.concepticon_id][formB.concepticon_id]['languages'].add(v_.gid)
                    G[formA.concepticon_id][formB.concepticon_id]['families'].add(v_.family)
                    G[formA.concepticon_id][formB.concepticon_id]['wofam'].append('/'.join([
                        formA.gid,
                        formB.gid,
                        formA.clics_form,
                        v_.gid,
                        v_.family,
                        clean(formA.form),
                        clean(formB.form)]))
    args.repos.json_dump(words, 'app', 'source', 'words.json')

    edges = {}
    for edgeA, edgeB, data in G.edges(data=True):
        edges[edgeA, edgeB] = (len(data['families']), len(data['languages']), len(data['words']))

    ignore_edges = []
    for edgeA, edgeB, data in G.edges(data=True):
        data['WordWeight'] = len(data['words'])
        data['words'] = ';'.join(sorted(['{0}/{1}'.format(x, y) for x, y in data['words']]))
        data['FamilyWeight'] = len(data['families'])
        data['families'] = ';'.join(sorted(data['families']))
        data['LanguageWeight'] = len(data['languages'])
        data['languages'] = ';'.join(data['languages'])
        data['wofam'] = ';'.join(data['wofam'])
        if args.edgefilter == 'families' and data['FamilyWeight'] < args.threshold:
            ignore_edges.append((edgeA, edgeB))
        elif args.edgefilter == 'languages' and data['LanguageWeight'] < args.threshold:
            ignore_edges.append((edgeA, edgeB))
        elif args.edgefilter == 'words' and data['WordWeight'] < args.threshold:
            ignore_edges.append((edgeA, edgeB))

    G.remove_edges_from(ignore_edges)

    nodenames = {r[0]: r[1] for r in args.repos.db.fetchall(
        "select distinct concepticon_id, concepticon_gloss from parametertable")}

    with Table(
        args, 'ID A', 'Concept A', 'ID B', 'Concept B', 'Families', 'Languages', 'Words'
    ) as table:
        count = 0
        for (nodeA, nodeB), (fc, lc, wc) in sorted(edges.items(), key=lambda i: i[1], reverse=True):
            if (nodeA, nodeB) not in ignore_edges:
                table.append([nodeA, nodenames[nodeA], nodeB, nodenames[nodeB], fc, lc, wc])
                count += 1
            if count >= args.show:
                break

    print(args.repos.save_graph(G, args.graphname, args.threshold, args.edgefilter))