"""
Module provides methods for the detection and handling of colexifications in wordlists.
"""
from itertools import combinations
from collections import defaultdict

import networkx as nx
from lingpy.align.pairwise import Pairwise
from lingpy.algorithm import extra
from lingpy.algorithm import clustering as cluster
import numpy as np


class Graph(nx.Graph):
    def update_concept(self, concept, **kw):
        try:
            for k, v in kw.items():
                self.nodes[concept][k].append(v)
        except KeyError:
            self.add_node(concept, **{k: [v] for k, v in kw.items()})

    def update_edge(self, c1, c2, **kw):
        try:
            self[c1][c2]['count'] += 1
            for k, v in kw.items():
                self[c1][c2][k].append(v)
        except KeyError:
            self.add_edge(c1, c2, count=1, **{k: [v] for k, v in kw.items()})


def get_colexifications(
        wordlist,
        family=None,
        languages=None,
        concept_attr="concepticon_gloss"
) -> Graph:
    """
    @param wordlist: A cltoolkit Wordlist instance.
    @param family: A string for a language family (valid in Glottolog). When set to None, won't \
    filter by family.
    @param concepts: A list of concepticon glosses that will be compared with the glosses in the \
    wordlist. If set to None, concepts won't be filtered.
    @returns: A networkx.Graph instance.

    @todo: discuss if we should add a form_factory, deleting tones,
           and the like, for this part of the analysis as well,
           as we do for partial colexifications
    """
    graph = Graph()
    # concept lookup checks for relevant concepticon attribute
    concept_lookup = lambda x: getattr(x, concept_attr) if x else None

    if languages is None:
        languages = [lg for lg in wordlist.languages if family is None or (lg.family == family)]

    concepts = [concept_lookup(concept) for concept in wordlist.concepts if concept_lookup(concept)]

    for language in languages:
        cols = defaultdict(list)
        for form in language.forms_with_sounds:
            if concept_lookup(form.concept) in concepts:
                cols[str(form.sounds)].append(form)

        # add nodes to the graph
        colexs: list[tuple[str, list, list]] = []
        for tokens, forms in cols.items():
            colexs.append((
                tokens,
                [f for f in forms if f.concept],
                [concept_lookup(f.concept) for f in forms if f.concept]
            ))
            for f, concept in zip(colexs[-1][1], colexs[-1][2]):
                graph.update_concept(
                    concept,
                    forms=f.id,
                    words=tokens,
                    varieties=language.id,
                    languages=language.glottocode,
                    families=language.family)

        for tokens, forms, all_concepts in colexs:
            if len(set(all_concepts)) > 1:
                for (f1, c1), (f2, c2) in combinations(zip(forms, all_concepts), r=2):
                    if c1 == c2:
                        continue
                    # identical concepts need to be excluded
                    graph.update_edge(
                        c1, c2,
                        forms="{0}/{1}".format(f1.id, f2.id),
                        words=tokens,
                        varieties=language.id,
                        languages=language.glottocode,
                        families=language.family)
    counts = [
        ("varieties", "variety"),
        ("languages", "language"),
        ("families", "family"),
        ("forms", "form")]
    for nA, nB, data in graph.edges(data=True):
        for pl, sg in counts:
            graph[nA][nB][sg+"_count"] = len(set(data[pl]))
    for node, data in graph.nodes(data=True):
        for pl, sg in counts:
            graph.nodes[node][sg+"_count"] = len(set(data[pl]))
    return graph


def weight_by_cognacy(
        graph, 
        threshold=0.45,
        cluster_method="infomap",
        label="cognate_count"
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
                for (i, w1), (j, w2) in combinations(enumerate(data["words"]), r=2):
                    pair = Pairwise(w1.split(), w2.split())
                    pair.align(distance=True)
                    matrix[i][j] = matrix[j][i] = pair.alignments[0][2]
                weight = len(cluster_function(threshold, matrix, taxa=data["languages"]))
        else:
            weight = 1
        graph[nA][nB][label] = weight


def get_transition_matrix(graph, steps=10, weight="weight", normalize=False):
    """
    Compute transition matrix following Jackson et al. 2019

    @param graph: The graph as networkx object.
    @param steps: The number of steps in which the random walk repeats.
    @param normalize: Decide if matrix should be normalized by dividing by the number of steps.
    """
    # prune nodes excluding singletons
    nodes = [node for node in graph.nodes if len(graph[node]) >= 1]
    a_matrix: list[list[int]] = [[0 for _ in nodes] for _ in nodes]

    for node_a, node_b, data in graph.edges(data=True):
        idx_a, idx_b = nodes.index(node_a), nodes.index(node_b)
        a_matrix[idx_a][idx_b] = a_matrix[idx_b][idx_a] = data[weight]
    d_matrix = [[0 for _ in nodes] for _ in nodes]
    diagonal = [sum(row) for row in a_matrix]
    for i in range(len(nodes)):
        d_matrix[i][i] = 1 / diagonal[i]

    p_matrix = np.matmul(d_matrix, a_matrix)
    new_p_matrix = sum([np.linalg.matrix_power(p_matrix, i) for i in range(1, steps + 1)])

    # we can normalize the matrix by dividing by the number of time steps
    if normalize:
        new_p_matrix = new_p_matrix / steps

    return new_p_matrix, nodes, a_matrix


def normalize_weights(graph, name, node_attr, edge_attr, factor=10, smoothing=1):
    for nA, nB, data in graph.edges(data=True):
        nA_attr, nB_attr = graph.nodes[nA][node_attr], graph.nodes[nB][node_attr]
        score = data[edge_attr]
        if score <= smoothing:
            score = 0
        data[name] = factor * (score ** 2)/(min(nA_attr, nB_attr) ** 2)
