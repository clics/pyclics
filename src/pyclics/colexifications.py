"""
Module provides methods for the detection and handling of colexifications in wordlists.
"""

import networkx as nx
from lingpy.align.pairwise import Pairwise
from collections import defaultdict
from lingpy.algorithm import extra
from lingpy.algorithm import clustering as cluster
from itertools import combinations
import numpy as np


def get_colexifications(
        wordlist, family=None, concepts=None, languages=None):
    """
    @param wordlist: A cltoolkit Wordlist instance.
    @param family: A string for a language family (valid in Glottolog). When set to None, won't filter by family.
    @param concepts: A list of concepticon glosses that will be compared with the glosses in the wordlist.
        If set to None, concepts won't be filtered.
    @returns: A networkx.Graph instance.
    """
    graph = nx.Graph()
    if languages is None:
        if family is None:
            languages = [language for language in wordlist.languages]
        else:
            languages = [language for language in wordlist.languages if language.family == family]
    
    if concepts is None:
        concepts = [concept.concepticon_gloss for concept in wordlist.concepts]

    for language in languages:
        cols = defaultdict(list)
        for form in language.forms_with_sounds:
            if form.concept.concepticon_gloss in concepts:
                tform = str(form.sounds)
                cols[tform] += [form]

        # add nodes to the graph
        colexs = []
        for tokens, forms in cols.items():
            colexs += [
                    (
                        tokens, 
                        [f for f in forms if f.concept], 
                        [f.concept.id for f in forms if f.concept]
                        )
                    ]
            for (f, concept) in zip(colexs[-1][1], colexs[-1][2]):
                try:
                    graph.nodes[concept]["occurrences"] += [f.id]
                    graph.nodes[concept]["words"] += [tokens]
                    graph.nodes[concept]["varieties"] += [language.id]
                    graph.nodes[concept]["languages"] += [language.glottocode]
                    graph.nodes[concept]["families"] += [language.family]
                except KeyError:
                    graph.add_node(
                            concept,
                            occurrences=[f.id],
                            words=[tokens],
                            varieties=[language.id],
                            languages=[language.glottocode],
                            families=[language.family]
                            )

        for tokens, forms, all_concepts in colexs:
            if len(set(all_concepts)) > 1:
                for (f1, c1), (f2, c2) in combinations(zip(forms, all_concepts), r=2):
                    if c1 == c2:
                        continue
                    # identical concepts need to be excluded
                    try:
                        graph[c1][c2]["count"] += 1
                        graph[c1][c2]["words"] += [tokens]
                        graph[c1][c2]["varieties"] += [language.id]
                        graph[c1][c2]["languages"] += [language.glottocode]
                        graph[c1][c2]["families"] += [language.family]
                    except KeyError:
                        graph.add_edge(
                                c1,
                                c2,
                                count=1,
                                words=[tokens],
                                varieties=[language.id],
                                languages=[language.glottocode],
                                families=[language.family],
                                )
    for nA, nB, data in graph.edges(data=True):
        graph[nA][nB]["variety_count"] = len(set(data["varieties"]))
        graph[nA][nB]["language_count"] = len(set(data["languages"]))
        graph[nA][nB]["family_count"] = len(set(data["families"]))
    for node, data in graph.nodes(data=True):
        graph.nodes[node]["language_count"] = len(set(data["languages"]))
        graph.nodes[node]["variety_count"] = len(set(data["varieties"]))
        graph.nodes[node]["family_count"] = len(set(data["families"]))
    return graph


def weight_by_cognacy(
        graph, 
        threshold=0.45,
        cluster_method="infomap",
        ):
    """
    Function weights the data by computing cognate sets.

    :todo: compute cognacy for concept slots to determine self-colexification
    scores.
    """
    if cluster_method == "infomap":
        cluster_function = extra.infomap_clustering
    else:
        cluster_function = cluster.flat_upgma

    for nA, nB, data in graph.edges(data=True):
        if data["count"] > 1:
            # assemble languages with different cognates
            if data["count"] == 2:
                pair = Pairwise(data["words"][0], data["words"][1])
                pair.align(distance=True)
                if pair.alignments[0][2] <= threshold:
                    weight = 1
                else:
                    weight = 2
            else:
                matrix = [[0 for _ in data["words"]] for _ in data["words"]]
                for (i, w1), (j, w2) in combinations(
                        enumerate(data["words"]), r=2):
                    pair = Pairwise(w1.split(), w2.split())
                    pair.align(distance=True)
                    matrix[i][j] = matrix[j][i] = pair.alignments[0][2]

                results = cluster_function(
                        threshold, 
                        matrix,
                        taxa=data["languages"])
                weight = len(results)
        else:
            weight = 1
        graph[nA][nB]["cognate_count"] = weight


def get_transition_matrix(graph, steps=10, weight="weight", normalize=False):
    """
    Compute transition matrix following Jackson et al. 2019
    """
    # prune nodes excluding singletons
    nodes = []
    for node in graph.nodes:
        if len(graph[node]) >= 1:
            nodes.append(node)
    a_matrix: list[list[int]] = [[0 for _ in nodes] for _ in nodes]

    for node_a, node_b, data in graph.edges(data=True):
        idx_a, idx_b = nodes.index(node_a), nodes.index(node_b)
        a_matrix[idx_a][idx_b] = a_matrix[idx_b][idx_a] = data[weight]
    d_matrix = [[0 for _ in nodes] for _ in nodes]
    diagonal = [sum(row) for row in a_matrix]
    for i in range(len(nodes)):
        d_matrix[i][i] = 1 / diagonal[i]

    p_matrix = np.matmul(d_matrix, a_matrix)
    new_p_matrix = sum([np.linalg.matrix_power(p_matrix, i) for i in range(1,
                                                                           steps + 1)])

    # we can normalize the matrix by dividing by the number of time steps
    if normalize:
        new_p_matrix = new_p_matrix / steps

    return new_p_matrix, nodes, a_matrix
