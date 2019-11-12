"""
Write datasets.md according to datasets.txt
"""
import re
from xml.etree import ElementTree

import attr
import requests
from clldutils.markup import Table

BASE_URL = "https://zenodo.org/oai2d?verb=ListRecords"
URL = BASE_URL + "&set=user-clics&metadataPrefix=oai_dc"
REQ_PATTERN = re.compile("https://github.com/(?P<repos>[^/]+/[^.]+).git@(?P<tag>v[0-9.]+)#")
TAG_PATTERN = re.compile("https://github.com/[^/]+/[^/]+/tree/(?P<tag>[a-zA-Z0-9.]+)")


@attr.s
class OAIRecord:  # pragma: no cover
    id = attr.ib()
    title = attr.ib()
    relations = attr.ib()

    @classmethod
    def from_oai(cls, rec):
        return cls(
            id=rec.find('.//{http://www.openarchives.org/OAI/2.0/}identifier').text,
            title=rec.find('.//{http://purl.org/dc/elements/1.1/}title').text,
            relations=[
                e.text for e in rec.findall('.//{http://purl.org/dc/elements/1.1/}relation')],
        )

    @property
    def doi(self):
        return '10.5281/zenodo.{0}'.format(self.id.split(':')[-1])

    @property
    def repos(self):
        if 'lexirumah' in self.title.lower():
            return 'lessersunda/lexirumah-data'
        return self.title.split(':')[0]

    @property
    def tag(self):
        if 'lexirumah' in self.title.lower():
            return re.search('(?P<tag>v[0-9.]+)', self.title).group('tag')
        for rel in self.relations:
            m = TAG_PATTERN.search(rel)
            if m:
                return m.group('tag')
        raise ValueError(self.id)

    @property
    def doi_md(self):
        return "[![DOI](https://zenodo.org/badge/DOI/{0}.svg)](https://doi.org/{0})".format(
            self.doi)


def iter_records():  # pragma: no cover
    url = URL
    while url:
        recs = ElementTree.fromstring(requests.get(url).text)
        for rec in recs.findall('.//{http://www.openarchives.org/OAI/2.0/}record'):
            yield OAIRecord.from_oai(rec)
        rt = recs.find('.//{http://www.openarchives.org/OAI/2.0/}resumptionToken')
        if rt is None or not rt.text:
            break
        url = BASE_URL + '&resumptionToken=' + rt.text


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

    table = Table('#', 'Title', 'DOI')
    for i, spec in enumerate(sorted(datasets.items()), start=1):
        rec = records.get(spec)
        if not rec:
            args.log.warning('{0} missing on Zenodo'.format(spec))
            table.append([i, spec, 'not submitted to CLICS community on Zenodo'])
        else:
            table.append([i, rec.title, rec.doi_md])

    args.repos.repos.joinpath('datasets.md').write_text(
        "# Datasets\n\n{0}".format(table.render()),
        encoding='utf8')
