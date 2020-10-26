"""
Compute the colexification graph
"""

import csv
from collections import defaultdict

import networkx as nx
from clldutils.clilib import Table, add_format


def register(parser):
    add_format(parser, default="simple")
    parser.add_argument(
        "--show",
        help="Number of most common colexifications to display after computation",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--colex2lang",
        help="Path to output with the list of languages colexifying a concept. Only written if an output file is provided.",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--colexstats",
        help="Path to output with the colexification statistics per language. Only written if an output file is provided.",
        type=str,
        default=None,
    )


def run(args):
    args.repos._log = args.log

    def clean(word):
        return "".join([w for w in word if w not in '/,;"'])

    varieties = args.repos.db.varieties

    args.log.info("Adding nodes to the graph")
    G = nx.Graph()
    for concept in args.repos.db.iter_concepts():
        G.add_node(concept.id, **concept.as_node_attrs())

    args.log.info("Adding edges to the graph")
    for v_, formA, formB in args.repos.iter_colexifications(varieties):
        if not G[formA.concepticon_id].get(formB.concepticon_id, False):
            G.add_edge(
                formA.concepticon_id,
                formB.concepticon_id,
                words=set(),
                languages=set(),
                families=set(),
                wofam=[],
            )

        G[formA.concepticon_id][formB.concepticon_id]["words"].add(
            (formA.gid, formB.gid)
        )
        G[formA.concepticon_id][formB.concepticon_id]["languages"].add(v_.gid)
        G[formA.concepticon_id][formB.concepticon_id]["families"].add(v_.family)
        G[formA.concepticon_id][formB.concepticon_id]["wofam"].append(
            "/".join(
                [
                    formA.gid,
                    formB.gid,
                    formA.clics_form,
                    v_.gid,
                    v_.family,
                    clean(formA.form),
                    clean(formB.form),
                ]
            )
        )

    # If either the colex2lang or colexstats files are requested,
    # build map of variety name to Glottocode, a map of concepts,
    # and collected the statistics
    if any([args.colex2lang, args.colexstats]):
        lang_map = {
            "%s-%s" % (dataset_id, lang_id): glottocode
            for dataset_id, lang_id, glottocode in args.repos.db.fetchall(
                "SELECT dataset_ID, ID, Glottocode FROM languagetable"
            )
        }

        # Collect lists of concepts for each language variety, so that we can
        # check if a colexification would be possible in it (i.e., if there is
        # enough data)
        concepts = defaultdict(set)
        for dataset_id, lang_id, concepticon_id in args.repos.db.fetchall(
            """
            SELECT f.dataset_ID, f.Language_ID, p.Concepticon_ID
            FROM formtable AS f, parametertable AS P
            WHERE f.Parameter_ID = p.ID AND f.dataset_ID = p.dataset_ID"""
        ):
            concepts["%s-%s" % (dataset_id, lang_id)].add(concepticon_id)

        # Iterate over all edges and collect data
        all_counts, threshold_counts = defaultdict(int), defaultdict(int)
        all_possible, threshold_possible = defaultdict(int), defaultdict(int)
        colex2lang = defaultdict(set)
        for concept_a, concept_b, data in G.edges(data=True):
            # Collect concept2languages info
            for lang, glottocode in lang_map.items():
                if lang in data["languages"]:
                    colex2lang[concept_a, concept_b].add(glottocode)

            # Collect language colexification affinity (David Gil's request)
            # Don't consider the edge if we don't have at least one language in it
            if not data["languages"]:
                continue

            # Check if the current concept pair passes the threshold filter
            filter_family, filter_lang, filter_words = True, True, True
            if args.edgefilter == "families":
                filter_family = len(data["families"]) >= args.threshold
            if args.edgefilter == "languages":
                filter_lang = len(data["languages"]) >= args.threshold
            if args.edgefilter == "words":
                filter_words = len(data["words"]) >= args.threshold
            pass_filter = all([filter_family, filter_lang, filter_words])

            # Inspect all languages
            for lang in lang_map:
                if lang in data["languages"]:
                    all_counts[lang] += 1
                    all_possible[lang] += 1
                    if pass_filter:
                        threshold_counts[lang] += 1
                        threshold_possible[lang] += 1
                else:
                    if concept_a in concepts[lang] and concept_b in concepts[lang]:
                        all_possible[lang] += 1
                        if pass_filter:
                            threshold_possible[lang] += 1

    edges = {}
    for edgeA, edgeB, data in G.edges(data=True):
        edges[edgeA, edgeB] = (
            len(data["families"]),
            len(data["languages"]),
            len(data["words"]),
        )

    ignore_edges = []
    for edgeA, edgeB, data in G.edges(data=True):
        data["WordWeight"] = len(data["words"])
        data["words"] = ";".join(
            sorted(["{0}/{1}".format(x, y) for x, y in data["words"]])
        )
        data["FamilyWeight"] = len(data["families"])
        data["families"] = ";".join(sorted(data["families"]))
        data["LanguageWeight"] = len(data["languages"])
        data["languages"] = ";".join(data["languages"])
        data["wofam"] = ";".join(data["wofam"])
        if args.edgefilter == "families" and data["FamilyWeight"] < args.threshold:
            ignore_edges.append((edgeA, edgeB))
        elif args.edgefilter == "languages" and data["LanguageWeight"] < args.threshold:
            ignore_edges.append((edgeA, edgeB))
        elif args.edgefilter == "words" and data["WordWeight"] < args.threshold:
            ignore_edges.append((edgeA, edgeB))

    G.remove_edges_from(ignore_edges)

    nodenames = {
        r[0]: r[1]
        for r in args.repos.db.fetchall(
            "select distinct concepticon_id, concepticon_gloss from parametertable"
        )
    }

    with Table(
        args, "ID A", "Concept A", "ID B", "Concept B", "Families", "Languages", "Words"
    ) as table:
        count = 0
        for (nodeA, nodeB), (fc, lc, wc) in sorted(
            edges.items(), key=lambda i: i[1], reverse=True
        ):
            if (nodeA, nodeB) not in ignore_edges:
                table.append(
                    [nodeA, nodenames[nodeA], nodeB, nodenames[nodeB], fc, lc, wc]
                )
                count += 1
            if count >= args.show:
                break

    print(args.repos.save_graph(G, args.graphname, args.threshold, args.edgefilter))

    # Output colex2lang info
    if args.colex2lang:
        with open(args.colex2lang, "w") as tsvfile:
            tsvfile.write("CONCEPT_A\tCONCEPT_B\tGLOTTOCODES\n")
            for entry, langs in colex2lang.items():
                tsvfile.write("%s\t%s\t%s\n" % (entry[0], entry[1], ",".join(langs)))

    # Output per-language info
    if args.colexstats:
        with open(args.colexstats, "w") as tsvfile:
            writer = csv.DictWriter(
                tsvfile,
                delimiter="\t",
                fieldnames=[
                    "LANG_KEY",
                    "GLOTTOCODE",
                    "COLEXIFICATIONS_ALL",
                    "POTENTIAL_ALL",
                    "COLEXIFICATIONS_THRESHOLD",
                    "POTENTIAL_THRESHOLD",
                ],
            )
            writer.writeheader()
            for lang in sorted(lang_map):
                writer.writerow(
                    {
                        "LANG_KEY": lang,
                        "GLOTTOCODE": lang_map[lang],
                        "COLEXIFICATIONS_ALL": all_counts[lang],
                        "POTENTIAL_ALL": all_possible[lang],
                        "COLEXIFICATIONS_THRESHOLD": threshold_counts[lang],
                        "POTENTIAL_THRESHOLD": threshold_possible[lang],
                    }
                )
