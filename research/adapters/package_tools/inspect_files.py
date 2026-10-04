"""File-only bounded PE inventory. Labels are relative; no binary is loaded."""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.adapters.inspect_qik_inventory import inspect_pe, read_bounded


def inventory(root: Path) -> dict[str, object]:
    if root.is_symlink() or not root.exists():
        raise ValueError("Input must exist and not be a symbolic link")
    paths = [root] if root.is_file() else sorted(root.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("Linked inputs are not accepted")
    files = [p for p in paths if p.is_file()]
    if len(files) > 4096:
        raise ValueError("Input exceeds 4096-file bound")
    entries = []
    total = 0
    for path in files:
        data = read_bounded(path, 512 * 1024 * 1024)
        total += len(data)
        if total > 2 * 1024**3:
            raise ValueError("Input exceeds 2 GiB total bound")
        entries.append({"file": path.name if root.is_file() else path.relative_to(root).as_posix(),
                        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                        "pe": inspect_pe(data)})
    return {"schema": "wht/static-file-inventory-v1", "files": entries,
            "scope": "file metadata only; signatures, loading and hardware not qualified"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inventory(args.input), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as error:
        logging.error("Inspection failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
