"""Inventory already-decoded QIK blocks as files; never load vendor code.

Input is a private directory containing block-NNNN-type-N.bin files produced by
a separately reviewed static extractor. This tool validates XML file-to-block
association, sizes and the absence of unexplained data blocks. It does not
authenticate the archive, decode it, install it or qualify any device capability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pefile

MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_XML_BYTES = 8 * 1024 * 1024
BLOCK_PATTERN = re.compile(r"block-(\d{4,})-type-(\d+)\.bin")


def read_bounded(path: Path, limit: int) -> bytes:
    """Reject links and unexpectedly large inputs before and during a read."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"Invalid or oversized input: {path.name}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Input grew past size bound: {path.name}")
    return data


def inspect_pe(data: bytes) -> dict[str, object] | None:
    if not data.startswith(b"MZ"):
        return None
    try:
        image = pefile.PE(data=data)
    except pefile.PEFormatError as error:
        raise ValueError("MZ payload is not a parseable PE image") from error
    try:
        version: dict[str, str] = {}
        for group in getattr(image, "FileInfo", []):
            for entry in group:
                for table in getattr(entry, "StringTable", []):
                    for key, value in table.entries.items():
                        if key in (b"FileVersion", b"ProductVersion", b"OriginalFilename"):
                            version[key.decode("ascii")] = value.decode("utf-8", errors="replace")
        exports = getattr(getattr(image, "DIRECTORY_ENTRY_EXPORT", None), "symbols", [])
        return {
            "machine": hex(image.FILE_HEADER.Machine),
            "architecture": {0x14C: "x86", 0x8664: "x64", 0xAA64: "ARM64"}.get(
                image.FILE_HEADER.Machine, "unknown"),
            "has_clr_directory": bool(image.OPTIONAL_HEADER.DATA_DIRECTORY[14].VirtualAddress),
            "version_resource": version,
            "imports": sorted(entry.dll.decode("ascii", errors="replace")
                              for entry in getattr(image, "DIRECTORY_ENTRY_IMPORT", [])),
            "exports": sorted(entry.name.decode("ascii", errors="replace")
                              for entry in exports if entry.name),
            "has_debug_directory": bool(image.OPTIONAL_HEADER.DATA_DIRECTORY[6].VirtualAddress),
            "has_certificate_directory": bool(image.OPTIONAL_HEADER.DATA_DIRECTORY[4].VirtualAddress),
        }
    finally:
        image.close()


def inspect_blocks(directory: Path) -> dict[str, object]:
    """Return a deterministic receipt; fail rather than silently omit payloads."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Expected a regular decoded-block directory")
    metadata = read_bounded(directory / "block-0001-type-2.bin", MAX_XML_BYTES)
    # The inspected QIK metadata is UTF-8. Reject alternate encodings rather than
    # letting XML auto-detection bypass declaration checks (e.g. UTF-16 NUL bytes).
    xml_text = metadata.decode('utf-8-sig')
    if '\0' in xml_text:
        raise ValueError('UTF-8 XML without NUL bytes is required')
    if "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        raise ValueError("DTD/entity declarations are not accepted")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise ValueError("Invalid package XML") from error
    if root.tag != "QIKPackage":
        raise ValueError("Expected QIKPackage metadata")
    blocks: dict[int, Path] = {}
    index_blocks = 0
    for path in sorted(directory.iterdir()):
        match = BLOCK_PATTERN.fullmatch(path.name)
        if not match:
            continue
        identifier, kind = map(int, match.groups())
        if kind == 1:
            if identifier in blocks:
                raise ValueError("Duplicate payload block ID")
            blocks[identifier] = path
        elif kind == 255:
            index_blocks += 1
        elif kind != 2 or identifier != 1:
            raise ValueError("Unexpected non-payload block")
    if index_blocks != 1:
        raise ValueError("Expected exactly one extracted index block")
    entries: list[dict[str, object]] = []
    seen: set[int] = set()
    folders = 0
    for item in root.iter("QIKFileInfo"):
        values = {child.tag: child.text for child in item}
        if len(values) != len(item):
            raise ValueError("Duplicate metadata field")
        folder = values.get("isFolder")
        if folder == "true":
            folders += 1
            continue
        if folder != "false":
            raise ValueError("Invalid isFolder value")
        try:
            identifier = int(values["ID"] or "")
            expected = int(values["Filesize"] or "")
        except (KeyError, ValueError) as error:
            raise ValueError("Invalid file ID or length") from error
        if identifier <= 1 or identifier in seen or identifier not in blocks:
            raise ValueError("Duplicate or missing file-to-block association")
        if expected < 0 or expected > MAX_FILE_BYTES:
            raise ValueError("Invalid declared payload size")
        name = values.get("DestPath")
        if not name:
            raise ValueError("Missing destination label")
        # DestPath is a label only: never use vendor paths to write/open a file.
        data = read_bounded(blocks[identifier], MAX_FILE_BYTES)
        if len(data) != expected:
            raise ValueError(f"Payload size mismatch for block {identifier}")
        seen.add(identifier)
        entries.append({
            "id": identifier, "destination_label": name,
            "file_type": values.get("FileType"), "block_file": blocks[identifier].name,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "pe": inspect_pe(data),
        })
    if set(blocks) != seen:
        raise ValueError("Unmapped payload blocks remain")
    return {
        "schema": "wht/qik-payload-inventory-v1",
        "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
        "file_count": len(entries), "folder_count": folders,
        "files": sorted(entries, key=lambda entry: entry["id"]),
        "scope": "decoded-file association and PE metadata only; no code execution",
        "limitations": ["extractor/container offsets not revalidated here",
                        "certificate presence is not signature verification",
                        "CLR presence does not determine managed process bitness"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blocks", type=Path, help="One already-decoded QIK block directory")
    args = parser.parse_args()
    try:
        result = inspect_blocks(args.blocks)
    except (OSError, ValueError) as error:
        logging.error("Inventory failed: %s", error)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
