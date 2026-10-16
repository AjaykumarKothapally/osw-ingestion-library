from pathlib import PurePosixPath
import re


def normalize_zip_member_name(name: str) -> str:
    """Normalize a ZIP member path and reject unsafe paths."""
    path = name.replace("\\", "/")
    normalized = PurePosixPath(path)

    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(f"Unsafe ZIP entry: {name}")

    if ".." in normalized.parts:
        raise ValueError(f"Unsafe ZIP entry: {name}")

    return path