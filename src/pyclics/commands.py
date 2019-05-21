from collections import defaultdict
from itertools import combinations, groupby
import sqlite3
from pathlib import Path
import shutil

from tqdm import tqdm
import geojson
from clldutils.clilib import command, ParserError
from clldutils.markup import Table
from clldutils import jsonlib
from pyconcepticon.api import Concepticon
from pyglottolog.api import Glottolog
from pylexibank.dataset import iter_datasets
import networkx as nx
from networkx.readwrite import json_graph
from tabulate import tabulate

from pyclics.util import get_communities
from pyclics import interfaces


@command('datasets')
def list_(args):
    """List datasets available for loading or already loaded.

    clics [--unloaded] list
    """
    if args.unloaded:
        i = 0
        for i, ds in enumerate(iter_datasets()):
            print(ds.cldf_dir)
        if not i:
            print('No datasets installed')  # pragma: no cover
    else:
        table = Table(
            '#', 'Dataset', 'Glosses', 'Concepticon', 'Varieties', 'Glottocodes', 'Families')
        try:
            concept_counts = {r[0]: r[1:] for r in args.api.db.fetchall('concepts_by_dataset')}
        except sqlite3.OperationalError:  # pragma: no cover
            print('No datasets loaded yet')
            return

        varieties = args.api.db.varieties
        var_counts = {}
        for dsid, vs in groupby(varieties, lambda v: v.source):
            vs = list(vs)
            var_counts[dsid] = (
                len(vs), len(set(v.glottocode for v in vs)), len(set(v.family for v in vs)))

        for count, d in enumerate(args.api.db.datasets):
            table.append([
                count + 1,
                d.replace('lexibank-', ''),
                concept_counts[d][1],
                concept_counts[d][0],
                var_counts[d][0],
                var_counts[d][1],
                var_counts[d][2],
            ])
        table.append([
            '',
            'TOTAL',
            0,
            args.api.db.fetchone(
                """\
select
    count(distinct p.concepticon_id) from parametertable as p, formtable as f, languagetable as l
where
    f.parameter_id = p.id and f.dataset_id = p.dataset_id
    and f.language_id = l.id and f.dataset_id = l.dataset_id
    and l.glottocode is not null
    and l.family != 'Bookkeeping'
""")[0],
            len(varieties),
            len(set(v.glottocode for v in varieties)),
            len(set(v.family for v in varieties))
        ])
        print(table.render(tablefmt='simple'))


@command()
def load(args):
    """Load installed datasets into the CLICS sqlite DB

    clics load /path/to/concepticon-data /path/to/glottolog
    """
    if len(args.args) != 2:
        raise ParserError('concepticon and glottolog repos locations must be specified!')
    concepticon = Path(args.args[0])
    if not concepticon.exists():
        raise ParserError('concepticon repository does not exist')
    glottolog = Path(args.args[1])
    if not glottolog.exists():
        raise ParserError('glottolog repository does not exist')

    args.log.info('using {0.__name__} implementation {1.__module__}:{1.__name__}'.format(
        interfaces.IClicsForm, args.api.clicsform))
    args.api.db.create(exists_ok=True)
    args.log.info('loading datasets into {0}'.format(args.api.db.fname))
    try:
        in_db = args.api.db.datasets
    except (ValueError, sqlite3.OperationalError):
        args.log.error('The existing database schema looks incompatible.')
        args.log.error('You may re-load all datasets after first removing {0}.'.format(
            args.api.db.fname))
        return
    for ds in iter_datasets():
        if args.unloaded and ds.id in in_db:
            args.log.info('skipping {0} - already loaded'.format(ds.id))
            continue
        args.log.info('loading {0}'.format(ds.id))
        args.api.db.load(ds)
        with args.api.db.connection() as conn:
            from_clause = "FROM formtable WHERE form IS NULL"
            conc_id_fix = "FROM parametertable WHERE Concepticon_ID = 0"

            n = args.api.db.fetchone("SELECT count(id) " + from_clause, conn=conn)[0]
            c = args.api.db.fetchone("SELECT count(id) " + conc_id_fix, conn=conn)[0]

            if n:
                args.log.info('purging {0} empty forms from db'.format(n))
                conn.execute("DELETE " + from_clause)
                conn.commit()

            if c:
                args.log.info('purging {0} problematic concepts from db.'.format(c))
                conn.execute("DELETE " + conc_id_fix)
                conn.commit()

    args.log.info('loading Concepticon data')
    args.api.db.load_concepticon_data(Concepticon(str(concepticon)))
    args.log.info('loading Glottolog data')
    args.api.db.load_glottolog_data(Glottolog(str(glottolog)))
    return


@command()
def colexification(args):
    """Compute the colexification graph

    clics colexification
    """
    args.api._log = args.log
    words = {}

    def clean(word):
        return ''.join([w for w in word if w not in '/,;"'])

    varieties = args.api.db.varieties
    lgeo = geojson.FeatureCollection([v.as_geojson() for v in varieties])
    args.api.json_dump(lgeo, 'app', 'source', 'langsGeo.json')

    app_source = args.api.existing_dir('app', 'source')
    for p in Path(__file__).parent.joinpath('app').iterdir():
        target_dir = app_source.parent if p.suffix == '.html' else app_source
        shutil.copy(str(p), str(target_dir / p.name))

    args.log.info('Adding nodes to the graph')
    G = nx.Graph()
    for concept in args.api.db.iter_concepts():
        G.add_node(concept.id, **concept.as_node_attrs())

    args.log.info('Adding edges to the graph')
    for v_, forms in tqdm(args.api.db.iter_wordlists(varieties), total=len(varieties), leave=False):
        for v in args.api.colexifier(forms):
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
    args.api.json_dump(words, 'app', 'source', 'words.json')

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

    nodenames = {r[0]: r[1] for r in args.api.db.fetchall(
        "select distinct concepticon_id, concepticon_gloss from parametertable")}

    table = Table('ID A', 'Concept A', 'ID B', 'Concept B', 'Families', 'Languages', 'Words')
    count = 0
    for (nodeA, nodeB), (fc, lc, wc) in sorted(edges.items(), key=lambda i: i[1], reverse=True):
        if (nodeA, nodeB) not in ignore_edges:
            table.append([nodeA, nodenames[nodeA], nodeB, nodenames[nodeB], fc, lc, wc])
            count += 1
        if count >= 10:
            break
    print(table.render(tablefmt='simple'))
    print(args.api.save_graph(G, args.graphname, args.threshold, args.edgefilter))


@command()
def cluster(args):
    """Cluster the colexification graph using one of the installed cluster algorithms.

    clics cluster CLUSTER_ALGORITHM

Run "clics cluster list" for a linst of available cluster algorithms.
    """
    from pyclics.util import parse_kwargs

    algo = args.args[0]
    if algo == 'list':
        print('Available algorithms:')
        for name in args.api.cluster_algorithms:
            print(name)
        return

    if algo not in args.api.cluster_algorithms:
        raise ParserError('Unknown cluster algorithm: {0}'.format(algo))

    graph = args.api.load_graph(args.graphname, args.threshold, args.edgefilter)
    args.log.info('graph loaded')
    kw = vars(args)
    kw.update(parse_kwargs(*args.args[1:]))
    neighbor_weight = int(kw.pop('neighbor_weight', 5))

    clusters = sorted(args.api.get_clusterer(algo)(graph, vars(args)), key=lambda c: (-len(c), c))
    args.log.info('computed clusters')

    D, Com = {}, defaultdict(list)
    for i, cluster in enumerate(clusters, start=1):
        for vertex in cluster:
            D[vertex] = str(i)
            Com[i].append(vertex)

    # Annotate the graph with the cluster info:
    for node, data in graph.nodes(data=True):
        data.update({algo: D.get(node, '0'), 'ClusterName': '', 'CentralConcept': ''})

    # get the articulation points etc. immediately
    for idx, nodes in sorted(Com.items()):
        sg = graph.subgraph(nodes)
        if len(sg) > 1:
            d_ = sorted(sg.degree(), key=lambda x: x[1], reverse=True)
            d = [graph.node[a]['Gloss'] for a, b in d_][0]
            cluster_name = '{0}_{1}_{2}'.format(algo, idx, d)
        else:
            d = graph.node[nodes[0]]['Gloss']
            cluster_name = '{0}_{1}_{2}'.format(algo, idx, graph.node[nodes[0]]['Gloss'])
        for node in nodes:
            graph.node[node]['ClusterName'] = cluster_name
            graph.node[node]['CentralConcept'] = d

    args.log.info('computed cluster names')

    cluster_dir = args.api.existing_dir('app', 'cluster', algo, clean=True)
    cluster_names = {}
    removed = []
    for idx, nodes in tqdm(sorted(Com.items()), desc='export to app', leave=False):
        sg = graph.subgraph(nodes)
        for node, data in sg.nodes(data=True):
            data['OutEdge'] = []
            neighbors = [
                n for n in graph if
                n in graph[node] and
                graph[node][n]['FamilyWeight'] >= neighbor_weight and
                n not in sg]
            if neighbors:
                sg.node[node]['OutEdge'] = []
                for n in neighbors:
                    sg.node[node]['OutEdge'].append([
                        graph.node[n]['ClusterName'],
                        graph.node[n]['CentralConcept'],
                        graph.node[n]['Gloss'],
                        graph[node][n]['WordWeight'],
                        n
                    ])
        if len(sg) > 1:
            jsonlib.dump(
                json_graph.adjacency_data(sg),
                cluster_dir / (graph.node[nodes[0]]['ClusterName'] + '.json'),
                sort_keys=True)
            for node in nodes:
                cluster_names[graph.node[node]['Gloss']] = graph.node[node]['ClusterName']
        else:
            removed += [list(nodes)[0]]
    graph.remove_nodes_from(removed)
    for node, data in graph.nodes(data=True):
        if 'OutEdge' in data:
            data['OutEdge'] = '//'.join(['/'.join([str(y) for y in x]) for x in data['OutEdge']])
    removed = []
    for nA, nB, data in tqdm(graph.edges(data=True), desc='remove edges', leave=False):
        if graph.node[nA][algo] != graph.node[nB][algo] and data['FamilyWeight'] < 5:
            removed += [(nA, nB)]
    graph.remove_edges_from(removed)

    args.api.save_graph(graph, algo, args.threshold, args.edgefilter)
    args.api.write_js_var(algo, cluster_names, 'app', 'source', 'cluster-names.js')


@command('graph-stats')
def graph_stats(args):
    """Display summary statistics about a colexification graph.

    clics graph-stats
    """
    graph = args.api.load_graph(args.graphname, args.threshold, args.edgefilter)
    print(tabulate([
        ['nodes', len(graph)],
        ['edges', len(graph.edges())],
        ['components', len(list(nx.connected_components(graph)))],
        ['communities', len(get_communities(graph))]
    ]))
