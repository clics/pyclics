from cltoolkit import Wordlist
from pycldf import Dataset
from pyclts import CLTS
from lingpy import Pairwise
from lingpy.algorithm import cluster
from itertools import combinations, product
from lexibank_chenhmongmien import Dataset as CHM
import networkx as nx
from collections import defaultdict
from tabulate import tabulate
from lingpy.algorithm import extra
from lingpy.convert.graph import networkx2igraph


def get_colexifications(wordlist):
    G = nx.Graph()
    for language in wordlist.languages:
        cols = defaultdict(list)
        for form in language.forms_with_sounds:
            tform = str(form.sounds)
            cols[tform] += [form]
        for tokens, forms in cols.items():
            if len(forms) > 1:
                for f1, f2 in combinations(forms, r=2):
                    if f1.concept and f2.concept and (
                            f1.concept.id != f2.concept.id):
                        c1, c2 = f1.concept.id, f2.concept.id
                        if not c1 in G:
                            G.add_node(
                                    c1, 
                                    occurrences=[f1.id],
                                    words=[tokens],
                                    languages=[language.id],
                                    families=[language.family]
                                    )
                        else:
                            G.nodes[c1]["occurrences"] += [f1.id]
                            G.nodes[c1]["words"] += [tokens]
                            G.nodes[c1]["languages"] += [language.id]
                            G.nodes[c1]["families"] += [language.family]
                        if not c2 in G:
                            G.add_node(
                                    c2, 
                                    occurrences=[f2.id],
                                    words=[" ".join(tokens)],
                                    languages=[language.id],
                                    families=[language.family]
                                    )
                        else:
                            G.nodes[c2]["occurrences"] += [f2.id]
                            G.nodes[c2]["words"] += [tokens]
                            G.nodes[c2]["languages"] += [language.id]
                            G.nodes[c2]["families"] += [language.family]

                        try:
                            G[c1][c2]["count"] += 1
                            G[c1][c2]["words"] += [tokens]
                            G[c1][c2]["languages"] += [language.id]
                            G[c1][c2]["families"] += [language.family]
                        except:
                            G.add_edge(
                                    c1,
                                    c2,
                                    count=1,
                                    words=[tokens],
                                    languages=[language.id],
                                    families=[language.family],
                                    weight=0
                                    )
    return G


def cluster_colexifications(
        graph, threshold=0.45, method="sca",
        cluster_method="infomap"):
    if cluster_method == "infomap":
        clusterm = extra.infomap_clustering
    else:
        clusterm = cluster.flat_upgma

    forms = defaultdict(list)
    edges = {}
    for nA, nB, data in graph.edges(data=True):
        if data["count"] > 1:
            # assemble languages with different cognates
            if data["count"] == 2:
                pair = Pairwise(data["words"][0], data["words"][1])
                pair.align(distance=True)
                if pair.alignments[0][2] <= threshold:
                    weight
            else:
                matrix = [[0 for i in data["words"]] for j in data["words"]]
                for (i, w1), (j, w2) in combinations(
                        enumerate(data["words"]), r=2):
                    pair = Pairwise(w1.split(), w2.split())
                    pair.align(distance=True)
                    matrix[i][j] = matrix[j][i] = pair.alignments[0][2]

                results = clusterm(
                        threshold, 
                        matrix,
                        taxa=data["languages"])
                weight = len(results)
        else:
            weight = 0.5
        graph[nA][nB]["weight"] = weight
    

wl = Wordlist([Dataset.from_metadata(CHM().cldf_dir / "cldf-metadata.json")],
        ts=CLTS().bipa)
G = get_colexifications(wl)
cluster_colexifications(G)


# make graph nice
delis = []
for nA, nB, data in G.edges(data=True):
    if data['weight'] < 2:
        delis += [(nA, nB)]
    for x in ['words', 'families', 'languages']:
        data[x] = ' // '.join(data[x])
for node, data in G.nodes(data=True):
    for x in ["words", "languages", "families"]:
        data[x] = " // ".join(data[x])

G.remove_edges_from(delis)

IG = networkx2igraph(G)
for i, nodes in enumerate(IG.community_infomap(edge_weights="weight")):
    for node in nodes:
        G.nodes[IG.vs[node]["Name"]]["infomap"] = i+1
IG2 = networkx2igraph(G)
IG2.write_gml("chen.gml")

table = []
for nA, nB, data in G.edges(data=True):
    if data["weight"] > 1:
        table += [[nA, nB, data["count"], data["weight"]]]

print(tabulate(table))

