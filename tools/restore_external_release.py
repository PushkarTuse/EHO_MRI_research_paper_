"""Verify and safely extract downloaded external-validation release ZIPs.

Purpose: restore all 115 viewers, native predictions, meshes and detailed records
into a clone without silently replacing user-modified files. Inputs are the
published manifest and its 13 downloaded ZIP assets. No network or credential
access is performed. Quantitative records are restored byte-for-byte.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True, type=Path, help="Directory holding all downloaded ZIP assets")
    parser.add_argument("--manifest", type=Path, default=repository / "reports/EXTERNAL_RELEASE_MANIFEST.json")
    parser.add_argument("--destination", type=Path, default=repository, help="Repository root; extraction stays within this path")
    parser.add_argument("--verify-only", action="store_true", help="Check archive hashes and inventories without extracting")
    arguments = parser.parse_args()
    destination = arguments.destination.resolve()
    manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    restored, preserved = 0, 0
    for record in manifest["assets"]:
        archive = arguments.assets / record["asset"]
        if archive.stat().st_size != record["size_bytes"] or digest(archive) != record["sha256"]:
            raise ValueError("Release archive fails SHA256/size verification: " + archive.name)
        expected = {item["path"]: item for item in record["files"]}
        with zipfile.ZipFile(archive) as source:
            if {item.filename for item in source.infolist()} != set(expected):
                raise ValueError("Release ZIP differs from its published inventory: " + archive.name)
            for entry in source.infolist():
                relative = PurePosixPath(entry.filename)
                if relative.is_absolute() or ".." in relative.parts or ":" in entry.filename or "\\" in entry.filename:
                    raise ValueError("Unsafe ZIP member: " + entry.filename)
                target = (destination / entry.filename).resolve()
                if not target.is_relative_to(destination):
                    raise ValueError("ZIP member escapes destination: " + entry.filename)
                if arguments.verify_only:
                    continue
                if target.exists():
                    if target.is_file() and digest(target) == expected[entry.filename]["sha256"]:
                        preserved += 1
                        continue
                    raise ValueError("Refusing to overwrite a modified existing file: " + str(target))
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(entry) as reader, target.open("xb") as writer:
                    shutil.copyfileobj(reader, writer, 4 * 1024 * 1024)
                if digest(target) != expected[entry.filename]["sha256"]:
                    raise ValueError("Extracted member checksum mismatch: " + str(target))
                restored += 1
        print("Verified " + archive.name, flush=True)
    print(json.dumps({"status": "verified" if arguments.verify_only else "restored",
                      "archives": len(manifest["assets"]), "restored_files": restored,
                      "preserved_identical_files": preserved}), flush=True)


if __name__ == "__main__":
    main()
