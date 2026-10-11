"""Independent validation of the complete 115-series MSLesSeg saved evaluation.

Metadata-only mode reads completed JSON records, small NIfTI headers and mesh
headers while a run is active. Full mode requires a completed run and recomputes
binary metrics from native saved masks; it never imports the experimental runner.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

import nibabel as nib
import numpy as np

PRIMARY = "primary_largest_6_connected_component"
SECONDARY = "prespecified_secondary_all_components"
METHODS = ("original_eho", "modified_eho", "pso", "ga", "acor")
SEEDS = (0, 1, 2)
BUDGET = 1500
EXPECTED_CASES = 115
EXPECTED_RECORDS = 2300
EXPECTED_KEYS = {(PRIMARY, method, seed) for method in METHODS for seed in SEEDS}
EXPECTED_KEYS |= {(PRIMARY, "direct_otsu", 0), (SECONDARY, "direct_otsu", 0)}
EXPECTED_KEYS |= {(SECONDARY, "modified_eho", seed) for seed in SEEDS}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def number_matches(actual, expected):
    if actual is None or expected is None:
        return actual is None and expected is None
    try:
        return math.isfinite(float(actual)) and math.isfinite(float(expected)) and math.isclose(
            float(actual), float(expected), rel_tol=1e-11, abs_tol=1e-12)
    except (ValueError, TypeError):
        return False


class Audit:
    def __init__(self):
        self.checked = 0
        self.failures = []

    def check(self, condition, message, expected=None, actual=None):
        self.checked += 1
        if not bool(condition):
            self.failures.append({"message": message, "expected": expected, "actual": actual})
        return bool(condition)

    def exception(self, message, error):
        self.check(False, message, actual=f"{type(error).__name__}: {error}")


def geometry(path, audit, scope, expected=None, forms_from=None):
    image = nib.load(str(path))  # Headers and proxy only; no voxel reads here.
    audit.check(image.shape == (182, 218, 182), scope + ": native 3D shape", [182, 218, 182], list(image.shape))
    audit.check(image.header.get_xyzt_units()[0] == "mm", scope + ": spatial units", "mm", image.header.get_xyzt_units()[0])
    audit.check(np.allclose(image.header.get_zooms()[:3], [1, 1, 1], rtol=0, atol=1e-6), scope + ": 1 mm header spacing",
                [1, 1, 1], list(map(float, image.header.get_zooms()[:3])))
    audit.check(np.isfinite(image.affine).all() and abs(np.linalg.det(image.affine[:3, :3])) > 1e-12,
                scope + ": finite nonsingular affine")
    audit.check(tuple(nib.aff2axcodes(image.affine)) == ("L", "A", "S"), scope + ": LAS orientation")
    audit.check(math.isclose(abs(float(np.linalg.det(image.affine[:3, :3]))), 1.0, rel_tol=0, abs_tol=1e-6),
                scope + ": affine voxel volume is 1 mm3")
    if expected is not None:
        audit.check(image.shape == expected.shape and np.allclose(image.affine, expected.affine, rtol=0, atol=1e-5),
                    scope + ": same native grid and affine as input/reference")
    if forms_from is not None:
        for form in ("qform", "sform"):
            original, original_code = getattr(forms_from, "get_" + form)(coded=True)
            saved, saved_code = getattr(image, "get_" + form)(coded=True)
            matches = int(original_code) == int(saved_code) and ((original is None and saved is None) or
                      (original is not None and saved is not None and np.allclose(original, saved, rtol=0, atol=1e-5)))
            audit.check(matches, scope + ": preserved " + form + " and code")
    return image


def binary_data(image, audit, scope):
    values = np.asarray(image.dataobj)
    valid = np.isfinite(values).all() and np.isin(values, [0, 1]).all()
    audit.check(valid, scope + ": finite binary 0/1 encoding")
    if not valid:
        raise ValueError(scope + " contains nonfinite or nonbinary values")
    return values > 0


def independent_metrics(prediction, reference, header):
    if prediction.shape != reference.shape:
        raise ValueError("Prediction and reference must have identical voxel grids")
    if header.get_xyzt_units()[0] != "mm":
        raise ValueError("Millilitre arithmetic requires explicitly declared millimetre units")
    spacing = tuple(map(float, header.get_zooms()[:3]))
    if len(spacing) != 3 or not all(math.isfinite(value) and value > 0 for value in spacing):
        raise ValueError("Millilitre arithmetic requires three finite positive spacings")
    tp = int(np.count_nonzero(prediction & reference))
    predicted = int(np.count_nonzero(prediction))
    referenced = int(np.count_nonzero(reference))
    fp, fn = predicted - tp, referenced - tp
    tn = int(prediction.size) - tp - fp - fn
    voxel_ml = math.prod(spacing) / 1000.0
    denominator = predicted + referenced
    union = predicted + referenced - tp
    recall = tp / referenced if referenced else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "dice_lesion": 2 * tp / denominator if denominator else 1.0,
            "iou_lesion": tp / union if union else 1.0,
            "precision_lesion": tp / predicted if predicted else None,
            "recall_lesion": recall, "sensitivity_lesion": recall,
            "specificity": tn / (tn + fp) if tn + fp else None,
            "prediction_ml": predicted * voxel_ml, "reference_ml": referenced * voxel_ml,
            "voxel_volume_ml": voxel_ml}


def ply_counts(path):
    with Path(path).open("rb") as stream:
        header = []
        for _ in range(200):
            line = stream.readline(4096)
            if not line:
                raise ValueError("Incomplete PLY header")
            decoded = line.decode("ascii").strip()
            header.append(decoded)
            if decoded == "end_header":
                break
        else:
            raise ValueError("PLY header exceeds supported limit")
    if header[0] != "ply":
        raise ValueError("PLY signature missing")
    counts = {}
    for line in header:
        words = line.split()
        if len(words) == 3 and words[:2] in (["element", "vertex"], ["element", "face"]):
            counts[words[1]] = int(words[2])
    return counts


def stl_count(path):
    with Path(path).open("rb") as stream:
        prefix = stream.read(84)
    if len(prefix) != 84:
        raise ValueError("Incomplete binary STL header")
    faces = struct.unpack("<I", prefix[80:84])[0]
    if Path(path).stat().st_size != 84 + 50 * faces:
        raise ValueError("Binary STL body size disagrees with declared triangle count")
    return faces


def file_contains(path, needle):
    """Find a byte string with bounded memory, including across block boundaries."""
    needle = needle.encode("utf-8")
    remainder = b""
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            block = remainder + block
            if needle in block:
                return True
            remainder = block[-max(0, len(needle) - 1):]
    return False


def record_keys_complete(records):
    observed = [(row.get("study"), row.get("method"), row.get("seed")) for row in records]
    return set(observed) == EXPECTED_KEYS and len(set(observed)) == len(observed)


def validate_meshes(directory, case_manifest, counts, audit, metadata_only):
    mesh_directory = directory / "meshes"
    mesh_manifest = read_json(mesh_directory / "mesh_manifest.json")
    audit.check(mesh_manifest == case_manifest["meshes"], "mesh manifest matches case manifest")
    for key, expected in {"evaluation_downsampled": False, "reference_is_prediction": False,
                          "coordinate_units": "mm", "reference_display_stride": 1}.items():
        audit.check(mesh_manifest.get(key) == expected, "mesh protocol " + key, expected, mesh_manifest.get(key))
    expected_slugs = {"image_foreground", "reference_lesion", "direct_otsu_prediction"} | {method + "_prediction" for method in METHODS}
    actual_slugs = {key for key, value in mesh_manifest.items() if isinstance(value, dict)}
    audit.check(actual_slugs == expected_slugs, "mesh entries cover context, reference, and all six primary representatives")
    html = mesh_directory / "interactive_prediction_reference.html"
    audit.check(html.is_file() and html.stat().st_size > 10000, "standalone interactive HTML exists")
    if html.exists():
        # Read the final HTML area without loading the bundled Plotly library.
        with html.open("rb") as stream:
            stream.seek(max(0, html.stat().st_size - 1000000))
            tail = stream.read().decode("utf-8", errors="replace")
        audit.check("Expert reference lesions (given labels)" in tail or
                    file_contains(html, "Expert reference lesions (given labels)"), "HTML explicitly names supplied expert reference")
        audit.check("reference" in tail.lower() and "</html>" in tail.lower(), "HTML has a complete reference comparison document")
    mesh_evidence = {}
    for slug in sorted(actual_slugs):
        entry = mesh_manifest[slug]
        if slug == "reference_lesion":
            audit.check(entry.get("actual_stride") == 1 and entry.get("requested_stride") == 1,
                        "reference display uses full-resolution stride 1")
        if slug in counts:
            audit.check(entry.get("native_positive_voxels") == counts[slug], slug + ": native mask voxel count matches independently loaded mask",
                        counts[slug], entry.get("native_positive_voxels"))
        if entry.get("status") == "empty_mask_no_surface":
            audit.check(entry.get("vertices") == 0 and entry.get("faces") == 0 and entry.get("native_positive_voxels") == 0,
                        slug + ": empty surface corresponds to an empty native mask")
            continue
        audit.check(entry.get("status") == "exported", slug + ": mesh export status")
        evidence = {}
        for extension in ("ply", "stl"):
            path = Path(entry.get(extension, ""))
            audit.check(path.is_file() and path.resolve().parent == mesh_directory.resolve(), slug + ": " + extension + " file exists within this case")
            if not path.is_file():
                continue
            evidence[extension + "_bytes"] = path.stat().st_size
            if extension == "ply":
                header = ply_counts(path)
                audit.check(header.get("vertex") == entry.get("vertices"), slug + ": PLY vertex count", entry.get("vertices"), header.get("vertex"))
                audit.check(header.get("face") == entry.get("faces"), slug + ": PLY face count", entry.get("faces"), header.get("face"))
            else:
                faces = stl_count(path)
                audit.check(faces == entry.get("faces"), slug + ": binary STL triangle count", entry.get("faces"), faces)
                audit.check(True, slug + ": binary STL body size")
            if not metadata_only:
                evidence[extension + "_sha256"] = sha256(path)
                if extension + "_sha256" in entry:
                    audit.check(evidence[extension + "_sha256"] == entry[extension + "_sha256"], slug + ": stored mesh checksum")
        mesh_evidence[slug] = evidence
    return mesh_evidence


def validate_case(case, directory, protocol_sha, metadata_only):
    audit = Audit()
    result = {"case_id": case["case_id"], "status": "pending", "records": []}
    marker_path = directory / "case_completed.json"
    if not marker_path.exists():
        if (directory / "case_failure.json").exists():
            audit.check(False, "runner recorded case failure", actual=read_json(directory / "case_failure.json"))
            result["status"] = "failed"
        result.update(checks=audit.checked, failures=audit.failures)
        return result, []
    try:
        marker = read_json(marker_path)
        case_manifest = read_json(directory / "case_manifest.json")
        records = read_json(directory / "case_records.json")
        result["records_observed"] = len(records)
        for metadata in (marker, case_manifest):
            audit.check(metadata.get("case_id") == case["case_id"], "case identity agrees with source manifest")
            audit.check(metadata.get("protocol_sha256") == protocol_sha, "case uses the frozen run protocol")
        audit.check(all(case_manifest.get(field) == value for field, value in case.items()),
                    "case metadata preserves all source-manifest fields")
        audit.check(marker.get("records") == 20 and len(records) == 20, "exactly 20 records per case", 20, len(records))
        for name in ("case_records", "case_manifest"):
            audit.check(sha256(directory / (name + ".json")) == marker.get(name + "_sha256"), name + ": completion checksum")
        boundary = read_json(directory / "prediction_boundary.json")
        audit.check(boundary.get("reference_labels_accessed") is False and boundary.get("predictions_saved") == 20,
                    "all 20 predictions saved before per-case reference evaluation")
        audit.check(boundary.get("protocol_sha256") == protocol_sha, "prediction boundary protocol hash")
        expected_paths = {str(Path(record["prediction_path"]).resolve()) for record in records}
        audit.check(expected_paths == {str(Path(path).resolve()) for path in boundary.get("prediction_paths", [])},
                    "prediction boundary lists precisely the saved record paths")
        audit.check(record_keys_complete(records),
                    "16 primary and four secondary records cover all prespecified methods/seeds")
        source = geometry(case["image_path"], audit, "source image")
        source_reference = geometry(case["label_path"], audit, "source reference", expected=source)
        saved_reference_path = directory / "reference_lesion.nii.gz"
        saved_reference = geometry(saved_reference_path, audit, "saved reference", expected=source, forms_from=source_reference)
        reference = None
        mesh_counts = {}
        if not metadata_only:
            result["source_and_reference_checksums"] = {}
            for kind in ("image", "label"):
                current_sha = sha256(case[kind + "_path"])
                result["source_and_reference_checksums"][kind + "_sha256"] = current_sha
                audit.check(current_sha == case_manifest.get(kind + "_sha256"), "unchanged source " + kind + " checksum")
            current_sha = sha256(saved_reference_path)
            result["source_and_reference_checksums"]["reference_mask_sha256"] = current_sha
            audit.check(current_sha == case_manifest.get("reference_mask_sha256"), "saved reference checksum")
            reference = binary_data(saved_reference, audit, "saved reference")
            original_reference = binary_data(source_reference, audit, "source reference")
            audit.check(np.array_equal(reference, original_reference), "saved expert reference equals supplied 0/1 mask voxel-for-voxel")
            mesh_counts["reference_lesion"] = int(np.count_nonzero(reference))
            image_values = np.asarray(source.dataobj)
            mesh_counts["image_foreground"] = int(np.count_nonzero(np.isfinite(image_values) & (image_values != 0)))
            del image_values, original_reference
        for record in records:
            identity = f"{record.get('study')}/{record.get('method')}/seed{record.get('seed')}"
            record_audit = Audit()
            evidence = {"study": record.get("study"), "method": record.get("method"), "seed": record.get("seed")}
            record_audit.check(record.get("case_id") == case["case_id"], identity + ": record case ID")
            for field in ("subject_id", "session_id", "partition"):
                record_audit.check(record.get(field) == case.get(field), identity + ": " + field)
            record_audit.check(record.get("reference_labels_accessed") is False and record.get("reference_evaluation_after_prediction") is True,
                               identity + ": explicit image-only prediction then reference evaluation")
            if record.get("method") == "direct_otsu":
                record_audit.check(record.get("budget_per_stage") is None and "enhancement" not in record and "segmentation" not in record,
                                   identity + ": deterministic baseline has no optimizer budget")
            else:
                record_audit.check(record.get("budget_per_stage") == BUDGET, identity + ": declared stage budget", BUDGET, record.get("budget_per_stage"))
                for stage in ("enhancement", "segmentation"):
                    details = record[stage]
                    history = np.asarray(details.get("history", []), dtype=float)
                    valid_shape = history.shape == (BUDGET, 2)
                    record_audit.check(details.get("evaluations") == BUDGET and valid_shape, identity + ": " + stage + " consumes exactly 1500 calls")
                    if valid_shape:
                        record_audit.check(np.array_equal(history[:, 0], np.arange(1, BUDGET + 1)), identity + ": " + stage + " consecutive objective counts")
                        record_audit.check(np.isfinite(history).all() and np.all(np.diff(history[:, 1]) <= 1e-12), identity + ": " + stage + " finite nonincreasing incumbent history")
                        record_audit.check(number_matches(details.get("fun"), history[-1, 1]), identity + ": " + stage + " final history objective")
                    expected_seed = int(record["seed"]) + (100000 if stage == "segmentation" else 0)
                    record_audit.check(details.get("seed") == expected_seed and details.get("method") == record.get("method"), identity + ": " + stage + " optimizer seed/method")
                    config = details.get("config", {})
                    record_audit.check(config.get("max_evals") == BUDGET and config.get("population") == 30, identity + ": " + stage + " frozen budget/population")
                    convergence_path = directory / f"{record['method']}_seed{record['seed']}_{stage}_convergence.csv"
                    with convergence_path.open(newline="", encoding="utf-8") as stream:
                        convergence = list(csv.DictReader(stream))
                    saved_history = np.asarray([[float(row["evaluations"]), float(row["best_objective"])] for row in convergence])
                    record_audit.check(valid_shape and saved_history.shape == history.shape and np.array_equal(saved_history, history),
                                       identity + ": " + stage + " convergence CSV exactly matches objective history")
            suffix = "_all_components" if record.get("study") == SECONDARY else ""
            stem = record["method"] if record.get("method") == "direct_otsu" else f"{record['method']}_seed{record['seed']}"
            prediction_record = read_json(directory / f"{stem}{suffix}_prediction_record.json")
            added_fields = {"evaluation", "reference_evaluation_after_prediction", "saved_output_validation"}
            record_audit.check(prediction_record == {key: value for key, value in record.items() if key not in added_fields},
                               identity + ": prediction-stage record preserved through reference evaluation")
            evaluated = read_json(directory / f"{record['method']}_seed{record['seed']}{suffix}_evaluated.json")
            record_audit.check(evaluated == record, identity + ": evaluated record equals case_records entry")
            prediction_path = Path(record["prediction_path"])
            record_audit.check(prediction_path.resolve().parent == directory.resolve(), identity + ": prediction stays in case output directory")
            prediction_image = geometry(prediction_path, record_audit, identity + " prediction", expected=source, forms_from=source)
            if not metadata_only:
                current_sha = sha256(prediction_path)
                evidence["prediction_sha256"] = current_sha
                record_audit.check(current_sha == record.get("prediction_sha256"), identity + ": prediction checksum unchanged")
                prediction = binary_data(prediction_image, record_audit, identity + " prediction")
                actual = independent_metrics(prediction, reference, saved_reference.header)
                evidence["independently_recomputed_metrics"] = actual
                for metric, value in actual.items():
                    record_audit.check(number_matches(value, record["evaluation"].get(metric)), identity + ": independently recomputed " + metric,
                                       record["evaluation"].get(metric), value)
                if record["study"] == PRIMARY and record["seed"] == 0:
                    mesh_counts[record["method"] + "_prediction"] = actual["tp"] + actual["fp"]
                if "enhanced_volume_path" in record:
                    enhanced_path = Path(record["enhanced_volume_path"])
                    record_audit.check(enhanced_path.resolve().parent == directory.resolve(), identity + ": enhanced volume stays in case output directory")
                    current_sha = sha256(enhanced_path)
                    evidence["enhanced_volume_sha256"] = current_sha
                    record_audit.check(current_sha == record.get("enhanced_volume_sha256"), identity + ": enhanced volume checksum unchanged")
                    geometry(enhanced_path, record_audit, identity + " enhanced volume", expected=source, forms_from=source)
                del prediction
            evidence.update(checks=record_audit.checked, failures=record_audit.failures)
            result["records"].append(evidence)
            audit.checked += record_audit.checked
            audit.failures.extend(record_audit.failures)
        result["mesh_evidence"] = validate_meshes(directory, case_manifest, mesh_counts, audit, metadata_only)
        result["status"] = "failed" if audit.failures else "metadata_checked" if metadata_only else "validated"
    except Exception as error:
        audit.exception("case validation could not complete", error)
        result["status"] = "failed"
        records = []
    result.update(checks=audit.checked, failures=audit.failures)
    return result, records


def validate(args):
    started = time.monotonic()
    directory, manifest_path = args.imaging_dir.resolve(), args.manifest.resolve()
    source_manifest, run = read_json(manifest_path), read_json(directory / "run_manifest.json")
    audit = Audit()
    protocol = run["protocol"]
    expected_protocol_sha = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode("utf-8")).hexdigest()
    audit.check(expected_protocol_sha == run.get("protocol_sha256"), "canonical frozen protocol SHA256")
    audit.check(sha256(manifest_path) == protocol.get("manifest_sha256"), "source manifest unchanged since protocol freeze")
    cases = source_manifest["cases"]
    ids = [case["case_id"] for case in cases]
    audit.check(len(cases) == EXPECTED_CASES and len(set(ids)) == EXPECTED_CASES, "all 115 unique source sessions required", EXPECTED_CASES, len(cases))
    audit.check(len({case["subject_id"] for case in cases}) == 75, "75 unique source patients required")
    audit.check({case["case_id"] for case in run["cases"]} == set(ids) and run["cases"] == protocol["cases"], "run covers all source sessions under one protocol")
    audit.check(sorted(run["cases"], key=lambda case: case["case_id"]) == sorted(cases, key=lambda case: case["case_id"]),
                "run case definitions exactly equal the official source inventory")
    audit.check(run.get("methods") == list(METHODS) and run.get("seeds") == list(SEEDS), "five methods and optimizer seeds 0/1/2")
    audit.check(run.get("budget_per_optimizer_stage") == BUDGET and run.get("population") == 30, "frozen 1500-call stage budgets and population 30")
    frozen_sources = protocol.get("source_code_sha256", {})
    audit.check(set(frozen_sources) == {"external_imaging.py", "imaging.py", "optimizers.py"},
                "all three executed imaging source files have frozen checksums")
    for name, expected in frozen_sources.items():
        path = Path(__file__).parent / name
        audit.check(path.is_file() and sha256(path) == expected, "frozen source code checksum: " + name)
    active = run.get("status") == "running"
    if not args.metadata_only:
        audit.check(run.get("status") == "completed" and run.get("failed_cases") == 0 and run.get("completed_cases") == EXPECTED_CASES,
                    "full voxel validation requires a completed, failure-free 115-case run", "completed / 115 / 0 failures",
                    {key: run.get(key) for key in ("status", "completed_cases", "failed_cases")})
        if active:
            raise RuntimeError("Full voxel validation is blocked while the evaluation is running; use --metadata-only")
    results, indexed_records = [], {}
    for case_number, case in enumerate(cases, start=1):
        result, records = validate_case(case, directory / case["case_id"], expected_protocol_sha, args.metadata_only)
        results.append(result)
        for record in records:
            indexed_records[(case["case_id"], record["study"], record["method"], record["seed"])] = record
        if result["status"] == "failed":
            print(f"FAIL {case['case_id']}: " + "; ".join(row["message"] for row in result["failures"][:6]), flush=True)
        if case_number % 5 == 0 or case_number == len(cases):
            print(json.dumps({"progress_cases": case_number, "expected_cases": len(cases), "last_case_id": case["case_id"],
                              "last_case_status": result["status"], "elapsed_seconds": round(time.monotonic() - started, 1)}), flush=True)
    completed = sum(result["status"] not in ("pending", "failed") for result in results)
    pending = [result["case_id"] for result in results if result["status"] == "pending"]
    if not active or not args.metadata_only:
        audit.check(completed == EXPECTED_CASES, "all 115 cases have valid completion records", EXPECTED_CASES, completed)
        audit.check(len(indexed_records) == EXPECTED_RECORDS, "2300 total saved records required", EXPECTED_RECORDS, len(indexed_records))
        audit.check(run.get("output_records") == EXPECTED_RECORDS, "runner output count is 2300", EXPECTED_RECORDS, run.get("output_records"))
        audit.check(run.get("failed_cases") == 0 and run.get("status") == "completed", "runner completed without failed cases")
        with (directory / "all_runs.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        csv_keys = [(row["case_id"], row["study"], row["method"], int(row["seed"])) for row in rows]
        audit.check(len(rows) == EXPECTED_RECORDS and len(set(csv_keys)) == EXPECTED_RECORDS and set(csv_keys) == set(indexed_records),
                    "aggregate CSV contains exactly the unique validated records")
        for row, key in zip(rows, csv_keys):
            if key not in indexed_records:
                continue
            record = indexed_records[key]
            for metric, value in record["evaluation"].items():
                if isinstance(value, (int, float)) or value is None:
                    reported = None if row.get(metric, "") == "" else row[metric]
                    audit.check(number_matches(reported, value), "aggregate CSV metric " + repr(key) + " " + metric, value, reported)
    failed_cases = [result["case_id"] for result in results if result["status"] == "failed"]
    failed = bool(audit.failures or failed_cases)
    status = "failed" if failed else "in_progress" if active else "metadata_checked" if args.metadata_only else "validated"
    report = {"validator": "independent_saved_masks_MSLesSeg_v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "validator_source_sha256": sha256(__file__), "protocol_sha256": expected_protocol_sha,
              "mode": "metadata_only" if args.metadata_only else "full_voxel", "status": status,
              "complete_cohort_validated": status == "validated", "imaging_dir": str(directory), "source_manifest": str(manifest_path),
              "expected_cases": EXPECTED_CASES, "expected_records": EXPECTED_RECORDS, "cases_checked": completed,
              "records_checked": len(indexed_records), "pending_cases": pending, "failed_case_ids": failed_cases,
              "run_status_at_snapshot": run.get("status"), "global_checks": audit.checked, "global_failures": audit.failures,
              "total_checks": audit.checked + sum(result["checks"] for result in results), "cases": results,
              "volume_arithmetic": "positive voxel count times product of NIfTI header spacing in mm, divided by 1000",
              "metadata_only_deferred_checks": ["mask voxel encodings and metrics", "source/prediction/enhanced NIfTI checksums", "mesh body checksums"] if args.metadata_only else [],
              "mesh_checksum_scope": "validator records current file digests; runner supplied no baseline mesh digests",
              "seconds": time.monotonic() - started}
    report_path = args.report.resolve() if args.report else directory.parent / "reports" / (
        "external_validation_metadata.json" if args.metadata_only else "external_validation_full.json")
    if report_path in (manifest_path, directory / "run_manifest.json"):
        raise ValueError("Validation report must not overwrite a frozen manifest")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_name(report_path.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(report_path)
    print(json.dumps({"status": status, "cases_checked": completed, "records_checked": len(indexed_records),
                      "failed_case_ids": failed_cases, "global_failures": len(audit.failures), "report": str(report_path)}), flush=True)
    return 1 if failed else 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--imaging-dir", type=Path, required=True)
    result.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] / "reports" / "mslesseg_case_manifest.json")
    result.add_argument("--report", type=Path)
    result.add_argument("--metadata-only", action="store_true")
    return result


if __name__ == "__main__":
    sys.exit(validate(parser().parse_args()))
