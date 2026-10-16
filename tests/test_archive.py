import pytest

from osw_ingestion.archive import normalize_zip_member_name


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