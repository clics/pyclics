from xml.etree import ElementTree

import pytest

from pyclics.zenodo import iter_records, OAIRecord


@pytest.fixture
def xml():
    return """\
<?xml version='1.0' encoding='UTF-8'?>
<?xml-stylesheet type="text/xsl" href="/static/xsl/oai2.xsl"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="">
  <responseDate>2019-11-12T16:48:03Z</responseDate>
  <request verb="ListRecords" set="user-clics" metadataPrefix="oai_dc">
    https://zenodo.org/oai2d
  </request>
  <ListRecords>
    <record>
      <header>
        <identifier>oai:zenodo.org:3268395</identifier>
        <datestamp>2019-11-11T07:43:43Z</datestamp>
        <setSpec>user-clics</setSpec>
        <setSpec>user-lexibank</setSpec>
      </header>
      <metadata>
        <oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                   xsi:schemaLocation="">
          <dc:creator>Robert Forkel</dc:creator>
          <dc:creator>Christoph Rzymski</dc:creator>
          <dc:date>2019-07-04</dc:date>
          <dc:description>Cite the source dataset as

Carling, Gerd (ed.) 2017. Diachronic Atlas of Comparative Linguistics Online.
Lund: Lund University. (DOI/URL: https://diacl.ht.lu.se/. ). Accessed on: 2019-02-07.
</dc:description>
          <dc:identifier>https://zenodo.org/record/3268395</dc:identifier>
          <dc:identifier>10.5281/zenodo.3268395</dc:identifier>
          <dc:identifier>oai:zenodo.org:3268395</dc:identifier>
          <dc:relation>url:https://github.com/lexibank/diacl/tree/v1.1</dc:relation>
          <dc:relation>doi:10.5281/zenodo.2634298</dc:relation>
          <dc:relation>url:https://zenodo.org/communities/clics</dc:relation>
          <dc:relation>url:https://zenodo.org/communities/lexibank</dc:relation>
          <dc:rights>info:eu-repo/semantics/openAccess</dc:rights>
          <dc:title>lexibank/diacl: Diachronic Atlas of Comparative Linguistics</dc:title>
          <dc:type>info:eu-repo/semantics/other</dc:type>
          <dc:type>dataset</dc:type>
        </oai_dc:dc>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""


def test_OAIRecord(xml):
    rec = OAIRecord.from_oai(ElementTree.fromstring(xml).find(
        './/{http://www.openarchives.org/OAI/2.0/}record'))
    assert '10.5281/zenodo.3268395' in rec.doi_md
    assert rec.tag and rec.repos and rec.dataset_id


def test_iter_records(mocker, xml):
    class requests:
        def get(self, *args, **kw):
            return mocker.Mock(text=xml)
    mocker.patch('pyclics.zenodo.requests', requests)
    assert len(list(iter_records())) == 1
