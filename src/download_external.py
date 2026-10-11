"""Download and inventory the official MSLesSeg release without running author code.

Only the five files of Figshare record 27919209 are acquired. Original archives
and source metadata are preserved; reference voxels are never used for selection.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import shutil
import stat
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

import nibabel as nib
import numpy as np


API_URL = "https://api.figshare.com/v2/articles/27919209"
SOURCE_URL = "https://springernature.figshare.com/articles/dataset/MSLesSeg_baseline_and_benchmarking_of_a_new_Multiple_Sclerosis_Lesion_Segmentation_dataset/27919209"
EXPECTED_FILES = {
    "MSLesSeg Dataset.zip": (52771814, 1473284755),
    "MSLesSeg_RAW.zip": (53623946, 1295472528),
    "MSLesSeg-2024-main.zip": (53623967, 10966086),
    "mat_files.zip": (54605591, 148946),
    "README.md": (54605609, 2059),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def request(url: str, headers: dict | None = None):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "MSLesSeg-research-inventory/1.0", **(headers or {})}),
        timeout=60,
    )


def download_file(item: dict, archives: Path, progress_path: Path) -> dict:
    destination = archives / item["name"]
    partial = destination.with_name(destination.name + ".part")
    expected_size = int(item["size"])
    expected_md5 = item["computed_md5"]
    if destination.exists():
        actual_md5 = md5_file(destination)
        if destination.stat().st_size != expected_size or actual_md5 != expected_md5:
            raise ValueError(f"Preserved file does not match official checksum: {destination}")
        print(f"Verified existing {destination.name}", flush=True)
        return {"name": destination.name, "path": str(destination.resolve()), "size_bytes": expected_size,
                "md5": actual_md5, "official_md5": expected_md5, "verified": True, "source_url": item["download_url"]}

    for attempt in range(1, 9):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > expected_size:
            raise ValueError(f"Partial file exceeds published size: {partial}")
        if offset == expected_size:
            break
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        start_time, start_offset, last_progress = time.monotonic(), offset, 0.0
        try:
            # Cache busting refreshes the redirect to Figshare's expiring signed URL.
            url = item["download_url"] + f"?download=1&inventory_request={time.time_ns()}"
            with request(url, headers) as response:
                status = response.status
                if status == 206:
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                    if not match or int(match[1]) != offset or int(match[3]) != expected_size:
                        raise ValueError(f"Unsafe resume response for {destination.name}: {response.headers.get('Content-Range')}")
                    mode = "ab" if offset else "wb"
                elif status == 200:
                    if offset:
                        print(f"Server ignored Range; restarting {destination.name} safely", flush=True)
                    declared = response.headers.get("Content-Length")
                    if declared and int(declared) != expected_size:
                        raise ValueError(f"Unexpected response size for {destination.name}: {declared}")
                    offset = 0
                    start_offset = 0
                    mode = "wb"
                else:
                    raise ValueError(f"Unexpected HTTP status {status}")
                with partial.open(mode) as output:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        if offset + len(block) > expected_size:
                            raise ValueError(f"Response exceeds official size for {destination.name}")
                        output.write(block)
                        offset += len(block)
                        now = time.monotonic()
                        if now - last_progress >= 15:
                            output.flush()
                            progress = {"updated_utc": utc_now(), "stage": "download", "file": destination.name,
                                        "received_bytes": offset, "expected_bytes": expected_size, "attempt": attempt,
                                        "percent": round(100 * offset / expected_size, 2)}
                            write_json(progress_path, progress)
                            rate = (offset - start_offset) / max(now - start_time, 0.001) / 1e6
                            print(f"Download {destination.name}: {offset/1e6:.1f}/{expected_size/1e6:.1f} MB ({progress['percent']:.1f}%), {rate:.1f} MB/s", flush=True)
                            last_progress = now
                    output.flush()
                    os.fsync(output.fileno())
            if offset != expected_size:
                raise OSError(f"Incomplete response: {offset} of {expected_size} bytes")
            break
        except (OSError, TimeoutError, urllib.error.URLError, http.client.HTTPException) as error:
            print(f"Download attempt {attempt} interrupted: {type(error).__name__}: {error}", flush=True)
            if attempt == 8:
                raise
            time.sleep(min(20, 2 * attempt))
    print(f"Checking published MD5: {destination.name}", flush=True)
    actual_md5 = md5_file(partial)
    if actual_md5 != expected_md5:
        raise ValueError(f"MD5 mismatch; preserved partial for inspection: {partial}")
    partial.replace(destination)
    return {"name": destination.name, "path": str(destination.resolve()), "size_bytes": expected_size,
            "md5": actual_md5, "official_md5": expected_md5, "verified": True, "source_url": item["download_url"]}


def validated_zip_target(root: Path, member: zipfile.ZipInfo) -> Path:
    name = member.filename.replace("\\", "/")
    relative = PurePosixPath(name)
    if (relative.is_absolute() or PureWindowsPath(name).drive or ".." in relative.parts or "\x00" in name
            or any(":" in part or PureWindowsPath(part).is_reserved() for part in relative.parts)):
        raise ValueError(f"Unsafe ZIP path: {member.filename}")
    mode = member.external_attr >> 16
    kind = stat.S_IFMT(mode)
    if stat.S_ISLNK(mode) or kind not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError(f"ZIP links/special files are forbidden: {member.filename}")
    destination = (root / Path(*relative.parts)).resolve()
    if destination != root and root not in destination.parents:
        raise ValueError(f"ZIP member escapes extraction root: {member.filename}")
    return destination


def crc32_file(path: Path) -> int:
    import zlib
    checksum = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            checksum = zlib.crc32(block, checksum)
    return checksum & 0xFFFFFFFF


def extract_zip(archive: Path, extracted: Path, progress_path: Path, official_md5: str) -> dict:
    root = (extracted / archive.stem).resolve()
    root.mkdir(parents=True, exist_ok=True)
    marker = root / "_extraction_complete.json"
    if marker.exists():
        record = json.loads(marker.read_text(encoding="utf-8"))
        if record["archive_md5"] == official_md5:
            print(f"Reusing verified extraction: {root}", flush=True)
            return record
        raise ValueError(f"Extraction marker refers to a different archive: {root}")
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        targets = [(member, validated_zip_target(root, member)) for member in members]
        total_bytes = sum(member.file_size for member in members)
        if shutil.disk_usage(root).free < total_bytes + 1024**3:
            raise OSError(f"Insufficient extraction space: need {total_bytes + 1024**3} bytes")
        completed = 0
        last_progress = 0.0
        for index, (member, target) in enumerate(targets, 1):
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.stat().st_size != member.file_size or crc32_file(target) != member.CRC:
                    raise ValueError(f"Existing extracted file differs from archive: {target}")
            else:
                temporary = target.with_name(target.name + ".extracting")
                with source.open(member) as input_stream, temporary.open("wb") as output_stream:
                    shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
                if temporary.stat().st_size != member.file_size or crc32_file(temporary) != member.CRC:
                    raise ValueError(f"Extraction failed CRC: {target}")
                temporary.replace(target)
            completed += member.file_size
            now = time.monotonic()
            if now - last_progress >= 15:
                write_json(progress_path, {"updated_utc": utc_now(), "stage": "extraction", "archive": archive.name,
                                          "members_done": index, "members_total": len(members),
                                          "uncompressed_bytes_done": completed, "uncompressed_bytes_total": total_bytes})
                print(f"Extract {archive.name}: {index}/{len(members)} members, {completed/1e9:.2f}/{total_bytes/1e9:.2f} GB", flush=True)
                last_progress = now
    record = {"archive": str(archive.resolve()), "archive_md5": official_md5, "root": str(root),
              "members": len(members), "uncompressed_bytes": total_bytes, "completed_utc": utc_now(),
              "author_code_executed": False}
    write_json(marker, record)
    return record


def natural_key(value: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def build_manifest(processed_root: Path, report_path: Path) -> dict:
    """Pair files by names only; do not inspect label data or lesion statistics."""
    files = sorted(processed_root.rglob("*.nii*"), key=lambda path: natural_key(str(path)))
    images = [path for path in files if re.search(r"(?:^|_)FLAIR(?:\.nii(?:\.gz)?)$", path.name, re.IGNORECASE)]
    cases, missing, unused_labels = [], [], []
    paired_labels = set()
    for image in images:
        match = re.fullmatch(r"(?P<subject>P\d+)(?:_(?P<session>T\d+))?_FLAIR\.nii(?:\.gz)?", image.name, re.IGNORECASE)
        if not match:
            raise ValueError(f"Unexpected FLAIR name; inspect layout before inventory: {image}")
        subject = match["subject"].upper()
        session = (match["session"] or "T1").upper()
        prefix = image.name[:re.search(r"_FLAIR", image.name, re.IGNORECASE).start()]
        labels = [path for path in image.parent.iterdir() if path.is_file() and
                  re.fullmatch(re.escape(prefix) + r"_(?:MASK|GT|LESION(?:_MASK)?)\.nii(?:\.gz)?", path.name, re.IGNORECASE)]
        if len(labels) != 1:
            missing.append({"image_path": str(image.resolve()), "label_candidates": [str(path.resolve()) for path in labels]})
            continue
        label = labels[0]
        paired_labels.add(label.resolve())
        partition_parts = [part.lower() for part in image.relative_to(processed_root).parts]
        if any(part in ("train", "training", "training set", "training_set") for part in partition_parts):
            partition = "training"
        elif any(part in ("test", "testing", "test set", "test_set", "testing set", "testing_set") for part in partition_parts):
            partition = "testing"
        else:
            partition = "unspecified"
        cases.append({"case_id": f"{subject}_{session}", "subject_id": subject, "native_subject_id": subject, "session_id": session,
                      "partition": partition, "image_path": str(image.resolve()), "label_path": str(label.resolve()),
                      "modality": "FLAIR", "allowed_labels": [0, 1], "foreground_labels": [1]})
    for path in files:
        if re.search(r"_(?:MASK|GT|LESION(?:_MASK)?)\.nii(?:\.gz)?$", path.name, re.IGNORECASE) and path.resolve() not in paired_labels:
            unused_labels.append(str(path.resolve()))
    if not cases or missing:
        print(json.dumps({"images_found": len(images), "cases_paired": len(cases), "missing": missing,
                          "first_nifti_paths": [str(path) for path in files[:20]]}, indent=2), flush=True)
        raise ValueError("FLAIR/reference pairing incomplete; adapt filename parser to the observed release")
    cases.sort(key=lambda case: (natural_key(case["subject_id"]), natural_key(case["session_id"])))
    if len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("Duplicate case IDs in processed archive")
    header_examples = []
    for case in cases[:5]:
        # nibabel loads the header and proxy here; no get_fdata / label voxel reads.
        image, label = nib.load(case["image_path"]), nib.load(case["label_path"])
        header_examples.append({"case_id": case["case_id"], "image_shape": list(image.shape),
                                "label_shape": list(label.shape), "image_spacing": list(map(float, image.header.get_zooms()[:3])),
                                "label_spacing": list(map(float, label.header.get_zooms()[:3])),
                                "image_physical_units": list(image.header.get_xyzt_units()),
                                "label_physical_units": list(label.header.get_xyzt_units()),
                                "image_orientation": list(nib.aff2axcodes(image.affine)),
                                "label_orientation": list(nib.aff2axcodes(label.affine)),
                                "image_affine": image.affine.tolist(), "label_affine": label.affine.tolist()})
    # This protocol audit happens after all cases are paired and ordered. It only
    # validates the supplied binary encoding; it never controls case selection.
    encoding_examples = []
    for case in cases[:5]:
        observed_values = np.unique(np.asanyarray(nib.load(case["label_path"]).dataobj)).tolist()
        encoding_examples.append({"case_id": case["case_id"], "observed_label_values": observed_values})
        if any(value not in (0, 1) for value in observed_values):
            raise ValueError(f"Label encoding differs from published binary convention: {case['case_id']}: {observed_values}")
    manifest = {"dataset": "MSLesSeg", "dataset_name": "MSLesSeg", "license": "CC BY 4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/", "doi": "10.6084/m9.figshare.27919209",
                "source_url": SOURCE_URL, "source_api_url": API_URL, "created_utc": utc_now(),
                "preprocessing": {"provided_by": "dataset authors", "brain_extraction": "FSL BET",
                                  "registration": "FSL FLIRT affine, 12 degrees of freedom, MNI152",
                                  "template_spacing_mm": [1, 1, 1], "reported_orientation": "LAS",
                                  "reported_shape": [182, 218, 182]},
                "selection": {"criterion": "all filename-matched FLAIR/reference pairs; unselected source inventory",
                              "reference_voxels_read_for_selection": False, "lesion_metrics_used_for_selection": False,
                              "primary_cohort_selected": False},
                "counts": {"sessions": len(cases), "subjects": len({case['subject_id'] for case in cases}),
                           "training_sessions": sum(case["partition"] == "training" for case in cases),
                           "testing_sessions": sum(case["partition"] == "testing" for case in cases)},
                "protocol_checks": {"header_examples": header_examples, "label_encoding_examples": encoding_examples,
                                    "reference_voxels_read_for_encoding_audit_only": True, "unpaired_labels": unused_labels,
                                    "missing_label_pairs": missing, "all_source_files_preserved": True}, "cases": cases}
    write_json(report_path, manifest)
    print(f"Manifest saved: {report_path}; {manifest['counts']}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    workspace = Path(__file__).resolve().parents[1]
    parser.add_argument("--dataset-root", type=Path, default=workspace / "external_datasets" / "MSLesSeg")
    parser.add_argument("--manifest", type=Path, default=workspace / "reports" / "mslesseg_case_manifest.json")
    args = parser.parse_args()
    root = args.dataset_root.resolve()
    archives, extracted = root / "archives", root / "extracted"
    archives.mkdir(parents=True, exist_ok=True)
    extracted.mkdir(parents=True, exist_ok=True)
    metadata_path = root / "source_metadata.json"
    if metadata_path.exists():
        preserved = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata = preserved["official_response"]
    else:
        with request(API_URL) as response:
            metadata = json.load(response)
        write_json(metadata_path, {"retrieved_utc": utc_now(), "api_url": API_URL, "official_response": metadata})
    if metadata["license"]["url"] != "https://creativecommons.org/licenses/by/4.0/":
        raise ValueError("Official dataset license has changed; inspect metadata before proceeding")
    items = {item["name"]: item for item in metadata["files"]}
    if set(items) != set(EXPECTED_FILES):
        raise ValueError("Official file inventory has changed; inspect metadata before proceeding")
    for name, (file_id, size) in EXPECTED_FILES.items():
        if items[name]["id"] != file_id or items[name]["size"] != size:
            raise ValueError(f"Official metadata differs from the authorized release: {name}")
    checksums, extractions = [], []
    progress_path = root / "progress.json"
    for name in EXPECTED_FILES:
        result = download_file(items[name], archives, progress_path)
        checksums.append(result)
        write_json(root / "checksums.json", {"updated_utc": utc_now(), "files": checksums})
        if name.lower().endswith(".zip"):
            extraction = extract_zip(archives / name, extracted, progress_path, result["md5"])
            extractions.append(extraction)
            write_json(root / "extraction_inventory.json", {"archives": extractions})
            if name == "MSLesSeg Dataset.zip":
                if args.manifest.exists():
                    print(f"Preserving frozen source manifest: {args.manifest.resolve()}", flush=True)
                else:
                    build_manifest(Path(extraction["root"]), args.manifest.resolve())
    write_json(progress_path, {"updated_utc": utc_now(), "stage": "complete", "verified_files": len(checksums),
                              "safely_extracted_archives": len(extractions), "manifest": str(args.manifest.resolve()),
                              "author_code_executed": False})
    print("All five official files verified; four ZIP archives extracted; original source files preserved.", flush=True)


if __name__ == "__main__":
    main()
