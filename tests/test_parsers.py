import pytest

from osw_ingestion.parsers import parse_xml_records


SAMPLE_XML = """<Customers>
    <Customer>
        <customer_id>1</customer_id>
        <name>Acme Corp</name>
    </Customer>
    <Customer>
        <customer_id>2</customer_id>
        <name>Globex</name>
    </Customer>
</Customers>"""


def test_parse_xml_records_returns_list_of_dicts():
    records = parse_xml_records(SAMPLE_XML)
    assert records == [
        {"customer_id": "1", "name": "Acme Corp"},
        {"customer_id": "2", "name": "Globex"},
    ]


def test_parse_xml_records_rejects_empty_root():
    with pytest.raises(ValueError):
        parse_xml_records("<Customers></Customers>")