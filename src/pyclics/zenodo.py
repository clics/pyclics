import re
from xml.etree import ElementTree

import attr
import requests

BASE_URL = "https://zenodo.org/oai2d?verb=ListRecords"
URL = BASE_URL + "&set=user-clics&metadataPrefix=oai_dc"
REQ_PATTERN = re.compile("https://github.com/(?P<repos>[^/]+/[^.]+).git@(?P<tag>v[0-9.]+)#")
TAG_PATTERN = re.compile("https://github.com/[^/]+/[^/]+/tree/(?P<tag>[a-zA-Z0-9.]+)")


@attr.s
class OAIRecord:
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
            return 'lessersunda/lexirumah-data'  # pragma: no cover
        if 'Bangime' in self.title:
            return 'lingpy/language-island-paper'  # pragma: no cover
        return self.title.split(':')[0]

    @property
    def dataset_id(self):
        if 'lexirumah' in self.title.lower():  # pragma: no cover
            return 'lexirumah'
        if 'Bangime' in self.title:  # pragma: no cover
            return 'hantganbangime'
        return self.repos.split('/')[1]

    @property
    def tag(self):
        if 'lexirumah' in self.title.lower():  # pragma: no cover
            return re.search('(?P<tag>v[0-9.]+)', self.title).group('tag')
        for rel in self.relations:
            m = TAG_PATTERN.search(rel)
            if m:
                return m.group('tag')
        raise ValueError(self.id)  # pragma: no cover

    @property
    def doi_md(self):
        return "[![DOI](https://zenodo.org/badge/DOI/{0}.svg)](https://doi.org/{0})".format(
            self.doi)


def iter_records():
    url = URL
    while url:
        recs = ElementTree.fromstring(requests.get(url).text)
        for rec in recs.findall('.//{http://www.openarchives.org/OAI/2.0/}record'):
            yield OAIRecord.from_oai(rec)
        rt = recs.find('.//{http://www.openarchives.org/OAI/2.0/}resumptionToken')
        if rt is None or not rt.text:
            break
        url = BASE_URL + '&resumptionToken=' + rt.text  # pragma: no cover
