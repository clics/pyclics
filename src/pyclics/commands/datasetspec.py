"""
Write datasets.md according to datasets.txt
"""
import re

from clldutils.markup import Table

from pyclics.zenodo import iter_records

REQ_PATTERN = re.compile("https://github.com/(?P<repos>[^/]+/[^.]+).git@(?P<tag>v[0-9.]+)#")


def run(args):  # pragma: no cover
    # Read datasets.txt:
    datasets = {}
    for line in args.repos.repos.joinpath('datasets.txt').read_text(encoding='utf8').splitlines():
        m = REQ_PATTERN.search(line)
        if not m:
            raise ValueError('Unknown requirement format: {0}'.format(line))
        datasets[m.group('repos')] = m.group('tag')

    # Read what's on Zenodo:
    records = {(rec.repos, rec.tag): rec for rec in iter_records()}

    table = Table('#', 'Title', 'Release', 'DOI', 'ID')
    for i, spec in enumerate(sorted(datasets.items()), start=1):
        rec = records.get(spec)
        if not rec:
            args.log.warning('{0} missing on Zenodo'.format(spec))
            table.append([i, spec, '', 'not submitted to CLICS community on Zenodo', ''])
        else:
            table.append([i, rec.title, rec.tag, rec.doi_md, rec.dataset_id])

    args.repos.repos.joinpath('datasets.md').write_text(
        "# Datasets\n\n{0}".format(table.render()),
        encoding='utf8')
