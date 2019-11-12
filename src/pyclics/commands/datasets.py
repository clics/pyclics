"""
List datasets available for loading or already loaded.
"""
import itertools
import sqlite3

from clldutils.clilib import Table, add_format

from cldfbench import iter_datasets


def register(parser):
    add_format(parser, default='simple')
    parser.add_argument(
        '--unloaded',
        help="list installed but not yet loaded datasets",
        action='store_true',
        default=False)


def run(args):
    if args.unloaded:
        i = 0
        for i, ds in enumerate(iter_datasets('lexibank.dataset')):
            print(ds.cldf_dir)
        if not i:
            print('No datasets installed')  # pragma: no cover
        return

    with Table(
            args,
            '#',
            'Dataset',
            'Parameters',
            'Concepticon',
            'Varieties',
            'Glottocodes',
            'Families',
    ) as table:
        try:
            concept_counts = {r[0]: r[1:] for r in args.repos.db.fetchall('concepts_by_dataset')}
        except sqlite3.OperationalError:  # pragma: no cover
            print('No datasets loaded yet')
            return

        varieties = args.repos.db.varieties
        var_counts = {}
        for dsid, vs in itertools.groupby(varieties, lambda v: v.source):
            vs = list(vs)
            var_counts[dsid] = (
                len(vs), len(set(v.glottocode for v in vs)), len(set(v.family for v in vs)))

        for count, d in enumerate(args.repos.db.datasets):
            table.append([
                count + 1,
                d.replace('lexibank-', ''),
                concept_counts[d][1],
                concept_counts[d][0],
                var_counts.get(d, [0])[0],
                var_counts.get(d, [0, 0])[1],
                var_counts.get(d, [0, 0, 0])[2],
            ])
        table.append([
            '',
            'TOTAL',
            0,
            args.repos.db.fetchone(
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
