import pytest
import io
import zipfile
from pathlib import Path
from osw_ingestion.archive import normalize_zip_member_name
from datetime import datetime
from osw_ingestion.archive import build_archive_blob_path
from osw_ingestion.archive import (validate_zip_contents, plan_bronze_landing,land_bronze_files,)


def test_accepts_valid_filename():
    assert normalize_zip_member_name("Products.XML") == "Products.XML"


def test_normalizes_windows_separators():
    assert normalize_zip_member_name(r"Products\Inventory.XML") == "Products/Inventory.XML"


def test_rejects_directory_traversal():
    with pytest.raises(ValueError):
        normalize_zip_member_name("../secret.txt")


def test_rejects_unix_absolute_path():
    with pytest.raises(ValueError):
        normalize_zip_member_name("/etc/passwd")


def test_rejects_windows_absolute_path():
    with pytest.raises(ValueError):
        normalize_zip_member_name(r"C:\secret.txt")

def test_build_archive_blob_path_matches_known_output():
    result = build_archive_blob_path(
        inbound_path="osw-de-poc/inbound/",
        source_blob_path="osw-de-poc/inbound/OSW_DataEngineering_Source_20260929_002.zip",
        etag='"0x8DF1E3490CF36DF"',
        last_modified=datetime(2026, 9, 29),
    )
    assert result == "osw-de-poc/archive/2026/09/OSW_DataEngineering_Source_20260929_002_0x8DF1E3490CF36DF.zip"

def make_zip(files: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def test_validate_zip_contents_rejects_unsafe_path():
    zip_bytes = make_zip({"../evil.txt": b"data"})
    with pytest.raises(ValueError):
        validate_zip_contents(zip_bytes)


def test_plan_bronze_landing_builds_expected_paths():
    zip_bytes = make_zip({"oneapp/customers/v1/customers.xml": b"<root></root>"})
    ingestion_timestamp = datetime(2026, 9, 29, 21, 22, 39)

    plan = plan_bronze_landing(
        zip_bytes,
        application_name="oneapp",
        version="v1",
        bronze_root="/lakehouse/default/Files/oneapp",
        ingestion_timestamp=ingestion_timestamp,
    )

    assert plan == [{
        "source_member": "oneapp/customers/v1/customers.xml",
        "entity": "customers",
        "version": "v1",
        "file_name": "customers.xml",
        "bronze_path": "/lakehouse/default/Files/oneapp/customers/v1/2026/09/29/21/customers.xml",
    }]


def test_plan_bronze_landing_rejects_wrong_application():
    zip_bytes = make_zip({"wrongapp/customers/v1/customers.xml": b"data"})
    with pytest.raises(ValueError):
        plan_bronze_landing(
            zip_bytes,
            application_name="oneapp",
            version="v1",
            bronze_root="/tmp/bronze",
            ingestion_timestamp=datetime(2026, 1, 1),
        )


def test_land_bronze_files_writes_expected_content(tmp_path):
    content = b"<root><customer/></root>"
    zip_bytes = make_zip({"oneapp/customers/v1/customers.xml": content})
    bronze_root = str(tmp_path / "bronze")

    plan = plan_bronze_landing(
        zip_bytes,
        application_name="oneapp",
        version="v1",
        bronze_root=bronze_root,
        ingestion_timestamp=datetime(2026, 1, 1, 0, 0),
    )

    written = land_bronze_files(zip_bytes, plan)

    assert len(written) == 1
    assert Path(written[0]).read_bytes() == content