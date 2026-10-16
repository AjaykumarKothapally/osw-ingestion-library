from pathlib import PurePosixPath
import re
import os
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime

def normalize_zip_member_name(name: str) -> str:
    """Normalize a ZIP member path and reject unsafe paths."""
    path = name.replace("\\", "/")
    normalized = PurePosixPath(path)

    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(f"Unsafe ZIP entry: {name}")

    if ".." in normalized.parts:
        raise ValueError(f"Unsafe ZIP entry: {name}")

    return path

def build_archive_blob_path(
    inbound_path: str,
    source_blob_path: str,
    etag: str,
    last_modified: datetime,
) -> str:
    """Build the archive destination path for a processed source ZIP."""
    inbound_root = inbound_path.rstrip("/")
    archive_parent = inbound_root.rsplit("/", 1)[0]

    etag_for_filename = etag.strip('"').replace("/", "_")
    source_file_name = PurePosixPath(source_blob_path).name
    source_file_stem = PurePosixPath(source_file_name).stem
    archive_file_name = f"{source_file_stem}_{etag_for_filename}.zip"

    return (
        f"{archive_parent}/archive/"
        f"{last_modified:%Y}/{last_modified:%m}/"
        f"{archive_file_name}"
    )


def validate_zip_contents(zip_bytes: bytes) -> None:
    """Check ZIP integrity and reject unsafe member paths."""
    with ZipFile(BytesIO(zip_bytes)) as zip_ref:
        bad_file = zip_ref.testzip()
        if bad_file is not None:
            raise ValueError(f"ZIP validation failed. Corrupt entry: {bad_file}")

        for member in zip_ref.infolist():
            if member.is_dir():
                continue
            normalize_zip_member_name(member.filename)


def plan_bronze_landing(
    zip_bytes: bytes,
    application_name: str,
    version: str,
    bronze_root: str,
    ingestion_timestamp: datetime,
) -> list[dict]:
    """Work out, for every file in the ZIP, where it should land in bronze."""
    plan = []

    with ZipFile(BytesIO(zip_bytes)) as zip_ref:
        for member in zip_ref.infolist():
            if member.is_dir():
                continue

            member_path = PurePosixPath(normalize_zip_member_name(member.filename))

            if len(member_path.parts) < 4:
                raise ValueError(f"Unexpected ZIP structure: {member.filename}")

            application = member_path.parts[0]
            entity = member_path.parts[1]
            member_version = member_path.parts[2]
            file_name = member_path.name

            if application != application_name:
                raise ValueError(
                    f"Unexpected application '{application}' in {member.filename}. "
                    f"Expected '{application_name}'."
                )

            if member_version != version:
                raise ValueError(
                    f"Unexpected version '{member_version}' in {member.filename}. "
                    f"Expected '{version}'."
                )

            bronze_path = (
                f"{bronze_root.rstrip('/')}/{entity}/{member_version}/"
                f"{ingestion_timestamp:%Y}/{ingestion_timestamp:%m}/"
                f"{ingestion_timestamp:%d}/{ingestion_timestamp:%H}/"
                f"{file_name}"
            )

            plan.append({
                "source_member": member.filename,
                "entity": entity,
                "version": member_version,
                "file_name": file_name,
                "bronze_path": bronze_path,
            })

    return plan


def land_bronze_files(zip_bytes: bytes, plan: list[dict]) -> list[str]:
    """Extract each planned file from the ZIP and write it to its bronze path."""
    written_paths = []

    with ZipFile(BytesIO(zip_bytes)) as zip_ref:
        for item in plan:
            file_content = zip_ref.read(item["source_member"])
            bronze_path = item["bronze_path"]

            os.makedirs(os.path.dirname(bronze_path), exist_ok=True)

            with open(bronze_path, "wb") as output_file:
                output_file.write(file_content)

            written_size = os.path.getsize(bronze_path)
            if written_size != len(file_content):
                raise RuntimeError(
                    f"Bronze validation failed for {item['source_member']}. "
                    f"Expected {len(file_content)} bytes, written {written_size} bytes."
                )

            written_paths.append(bronze_path)

    return written_paths