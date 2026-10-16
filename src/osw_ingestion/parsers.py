import xml.etree.ElementTree as ET


def parse_xml_records(xml_content) -> list[dict]:
    """Parse flat XML records into a list of dictionaries.

    Expects a root element whose children are records, and whose
    grandchildren are the record's fields (tag -> text).
    """
    root = ET.fromstring(xml_content)

    record_elements = [element for element in root if len(element) > 0]

    if not record_elements:
        raise ValueError("No records found in XML content.")

    records = []
    for record_element in record_elements:
        record = {}
        for field in record_element:
            record[field.tag] = field.text
        records.append(record)

    return records