"""Native-grid external lesion evaluation of the frozen image-only baseline.

The primary protocol is unchanged from the measured BraTS reconstruction. A
separately named all-components ablation is prespecified for multifocal lesions.
References are first opened only after every prediction for that case is saved.
Case completion markers permit restart without holding cohort histories in RAM.
"""
from __future__ import annotations

import os
for _thread_setting in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_setting] = "1"

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
import time
import traceback
import uuid
from pathlib import Path

import nibabel as nib
import numpy as np
import psutil
from scipy import ndimage

try:
    from . import imaging
except ImportError:
    import imaging

PRIMARY = "primary_largest_6_connected_component"
SECONDARY = "prespecified_secondary_all_components"
PROVENANCE = "external_lesion_evaluation_of_frozen_unsupervised_reconstruction_2026-10-11"
METRICS = ("dice_lesion", "iou_lesion", "precision_lesion", "recall_lesion", "prediction_ml", "reference_ml",
           "roi_input_similarity_psnr_db", "selected_slice_input_ssim_mean", "selected_slice_roi_input_ssim_mean",
           "enhancement_seconds", "segmentation_seconds", "enhancement_objective", "segmentation_objective")


def write_json(path, value):
    """Replace a JSON file atomically so interrupted writes cannot mark completion."""
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(imaging.jsonable(value), indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def load_manifest(path, count=None):
    path = Path(path).resolve()
    metadata = json.loads(path.read_text(encoding="utf-8"))
    rows = metadata.get("cases")
    if not isinstance(rows, list) or not rows:
        raise ValueError("External manifest must have a nonempty cases list")
    cases, identifiers = [], set()
    for row in rows:
        case = dict(row)
        identifier = str(case.get("case_id", ""))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier) or identifier in identifiers:
            raise ValueError("Case IDs must be unique, nonempty and safe directory names")
        identifiers.add(identifier)
        for key in ("image_path", "label_path"):
            source = Path(case[key])
            case[key] = str((source if source.is_absolute() else path.parent / source).resolve())
        if case.get("modality", "").upper() != "FLAIR":
            raise ValueError("Frozen external primary study requires explicitly declared FLAIR")
        allowed = case.get("allowed_labels")
        foreground = case.get("foreground_labels")
        if not allowed or not foreground or 0 not in allowed or 0 in foreground or not set(foreground).issubset(allowed):
            raise ValueError("Declare allowed_labels including background 0 and nonzero foreground_labels")
        case["subject_id"] = str(case.get("subject_id", identifier))
        case["session_id"] = str(case.get("session_id", ""))
        case["partition"] = str(case.get("partition", "unspecified"))
        cases.append(case)
    cases.sort(key=lambda row: row["case_id"])
    if count is not None:
        if count < 1 or count > len(cases):
            raise ValueError("--cases must be between 1 and the manifest case count")
        cases = cases[:count]
    return cases, {key: value for key, value in metadata.items() if key != "cases"}


def validate_geometry(nii, name):
    if len(nii.shape) != 3 or min(nii.shape) < 1:
        raise ValueError(f"{name} must be a native 3D NIfTI")
    if not np.isfinite(nii.affine).all() or abs(np.linalg.det(nii.affine[:3, :3])) < 1e-12:
        raise ValueError(f"{name} affine must be finite and nonsingular")
    if nii.header.get_xyzt_units()[0] != "mm":
        raise ValueError(f"{name} spatial units must explicitly be mm for mL and world-coordinate meshes")


def load_image(path):
    nii = nib.load(str(path))
    validate_geometry(nii, "Image")
    values = np.asarray(nii.dataobj, dtype=np.float32)
    normalized, roi, preprocessing = imaging.preprocess_flair(values)
    preprocessing["nonfinite_voxels_excluded"] = int(np.count_nonzero(~np.isfinite(values)))
    return normalized, roi, nii, preprocessing


def load_reference(case, source_nii):
    """This function may be called only after the prediction-save boundary."""
    nii = nib.load(case["label_path"])
    validate_geometry(nii, "Reference")
    if nii.shape != source_nii.shape or not np.allclose(nii.affine, source_nii.affine, rtol=0, atol=1e-5):
        raise ValueError("Image/reference geometry mismatch; no automatic resizing or resampling")
    values = np.asarray(nii.dataobj)
    if not np.isfinite(values).all() or not np.isin(values, case["allowed_labels"]).all():
        raise ValueError("Reference contains nonfinite or undeclared label values")
    reference = np.isin(values, case["foreground_labels"])
    return reference, nii, np.unique(values).tolist()


def lesion_metrics(prediction, reference, affine, foreground_labels):
    measured = imaging.segmentation_metrics(prediction, reference, affine)
    renamed = {key.replace("whole_tumour", "lesion"): value for key, value in measured.items()}
    renamed["reference_rule"] = "label in " + json.dumps(foreground_labels)
    renamed["specificity_scope"] = "complete native image grid including background"
    return renamed


def raw_highest_class(enhanced, roi, record):
    if record["method"] == "direct_otsu":
        return roi & (enhanced > record["thresholds"]["thresholds"][-1])
    return roi & (enhanced >= record["thresholds"]["thresholds"][-1])


def save_panels(normalized, enhanced, prediction, reference, slices, stem, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for index in slices:
        figure, axes = plt.subplots(1, 4, figsize=(13, 4), constrained_layout=True)
        for axis, values, name in zip(axes, (normalized[..., index], enhanced[..., index], prediction[..., index], reference[..., index]),
                                      ("Normalized FLAIR", "Contrast transform", "Predicted threshold mask", "Expert reference lesions")):
            axis.imshow(values.T, cmap="gray", origin="lower", vmin=0, vmax=1)
            axis.set_title(name)
            axis.axis("off")
        figure.suptitle(f"{title} | image-only selected axis-2 slice {index} | image-grid orientation")
        figure.savefig(str(stem) + f"_slice_{index}.png", dpi=140)
        plt.close(figure)


def display_surface(mask, affine, stride):
    vertices, faces = imaging.mesh_from_mask(mask, affine, stride)
    actual = stride
    if np.any(mask) and not len(vertices) and stride != 1:
        vertices, faces = imaging.mesh_from_mask(mask, affine, 1)
        actual = 1
    return vertices, faces, {"requested_stride": stride, "actual_stride": actual,
                             "native_positive_voxels": int(np.count_nonzero(mask)),
                             "fallback_for_erased_positive_mask": actual != stride}


def save_mesh_comparison(roi, masks, reference, affine, output, stride=2):
    import plotly.graph_objects as go
    output = Path(output)
    output.mkdir(exist_ok=True)
    figure = go.Figure()
    entries = [("image_foreground", "Brain context (nonzero FLAIR foreground)", roi, "lightgray", .12),
               ("reference_lesion", "Expert reference lesions (given labels)", reference, "royalblue", .50)]
    palette = ("orange", "crimson", "seagreen", "purple", "magenta", "darkcyan")
    entries += [(method + "_prediction", method + " predicted threshold mask", mask, palette[index % len(palette)], .65)
                for index, (method, mask) in enumerate(masks.items())]
    exports = {"evaluation_downsampled": False, "coordinate_units": "mm", "reference_is_prediction": False,
               "reference_display_stride": 1, "requested_prediction_display_stride": stride}
    for slug, name, mask, colour, opacity in entries:
        display_stride = 1 if slug == "reference_lesion" else stride
        vertices, faces, detail = display_surface(mask, affine, display_stride)
        detail.update(imaging.write_mesh(vertices, faces, output / slug))
        exports[slug] = detail
        if len(vertices):
            figure.add_trace(go.Mesh3d(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
                                      i=faces[:, 0], j=faces[:, 1], k=faces[:, 2], name=name,
                                      color=colour, opacity=opacity, showlegend=True,
                                      visible=True if slug in ("image_foreground", "modified_eho_prediction") else "legendonly"))
    figure.update_layout(title="External FLAIR: image-only predictions and independent expert lesion reference",
                         scene=dict(xaxis_title="World x (mm)", yaxis_title="World y (mm)", zaxis_title="World z (mm)", aspectmode="data"),
                         legend=dict(title="Click to compare predictions and reference"),
                         annotations=[dict(text="Frozen unsupervised exploratory baseline. Blue = supplied expert reference. Display decimation does not affect native-grid metrics.",
                                           x=.5, y=0, xref="paper", yref="paper", showarrow=False)],
                         margin=dict(l=0, r=0, t=70, b=60))
    figure.write_html(str(output / "interactive_prediction_reference.html"), include_plotlyjs=True, full_html=True)
    write_json(output / "mesh_manifest.json", exports)
    return exports


def compact_record(record):
    flat = imaging.flatten_record(record)
    flat.update({key: record[key] for key in ("study", "subject_id", "session_id", "partition")})
    flat["prediction_path"] = record["prediction_path"]
    flat["prediction_sha256"] = record["prediction_sha256"]
    flat["reference_evaluation_after_prediction"] = record["reference_evaluation_after_prediction"]
    return flat


def verify_saved_record(record, reference_path, foreground_labels):
    prediction_nii = nib.load(record["prediction_path"])
    reference_nii = nib.load(str(reference_path))
    validate_geometry(prediction_nii, "Saved prediction")
    validate_geometry(reference_nii, "Saved reference")
    if prediction_nii.shape != reference_nii.shape or not np.allclose(prediction_nii.affine, reference_nii.affine, rtol=0, atol=1e-5):
        raise ValueError("Saved prediction/reference geometry differs")
    prediction, reference = np.asarray(prediction_nii.dataobj), np.asarray(reference_nii.dataobj)
    if not np.isin(prediction, [0, 1]).all() or not np.isin(reference, [0, 1]).all():
        raise ValueError("Saved masks must be binary")
    if imaging.sha256(record["prediction_path"]) != record["prediction_sha256"]:
        raise ValueError("Saved prediction checksum changed after prediction")
    recomputed = lesion_metrics(prediction > 0, reference > 0, prediction_nii.affine, foreground_labels)
    for key, actual in recomputed.items():
        expected = record["evaluation"][key]
        if isinstance(actual, (int, float)) and not isinstance(actual, bool):
            if expected is None or not np.isclose(actual, expected, rtol=1e-12, atol=1e-12):
                raise ValueError("Independent saved-mask metric mismatch: " + key)
        elif actual != expected:
            raise ValueError("Independent saved-mask metadata mismatch: " + key)
    return {"binary_masks": True, "same_native_grid": True, "prediction_sha256_unchanged": True,
            "independent_saved_mask_metrics_match": True}


def predict_case(case, directory, args, protocol_sha):
    directory.mkdir(exist_ok=True)
    with imaging.ResourceMeasurement() as total_measure:
        with imaging.ResourceMeasurement() as load_measure:
            normalized, roi, nii, preprocessing = load_image(case["image_path"])
        slices = imaging.select_slices(roi)
        common = {"case_id": case["case_id"], "subject_id": case["subject_id"], "session_id": case["session_id"],
                  "partition": case["partition"], "modality": "FLAIR", "provenance": PROVENANCE}
        pending = []
        for method in args.methods_list:
            for seed in args.seeds_list:
                print(f"IMAGE-ONLY {case['case_id']} {method} seed={seed}", flush=True)
                enhanced, prediction, details = imaging.predict_from_image(normalized, roi, method, seed, args.budget, args.population)
                stem = directory / f"{method}_seed{seed}"
                prediction_path = str(stem) + "_prediction.nii.gz"
                imaging.save_mask(prediction, nii, prediction_path)
                record = {**details, **common, "study": PRIMARY, "method": method, "seed": seed,
                          "budget_per_stage": args.budget, "prediction_path": prediction_path,
                          "prediction_sha256": imaging.sha256(prediction_path),
                          "appearance": imaging.appearance_metrics(normalized, enhanced, roi, slices),
                          "component_rule": "largest 6-connected component; frozen primary protocol"}
                if seed == args.seeds_list[0]:
                    enhanced_path = str(stem) + "_enhanced_normalized_flair.nii.gz"
                    imaging.save_volume(enhanced, nii, enhanced_path)
                    record.update(enhanced_volume_path=enhanced_path, enhanced_volume_sha256=imaging.sha256(enhanced_path))
                write_json(str(stem) + "_prediction_record.json", record)
                for stage in ("enhancement", "segmentation"):
                    imaging.write_csv(str(stem) + f"_{stage}_convergence.csv",
                                      [{"evaluations": point[0], "best_objective": point[1]} for point in record[stage]["history"]])
                pending.append(record)
                if method == "modified_eho":
                    secondary_path = str(stem) + "_all_components_prediction.nii.gz"
                    raw = raw_highest_class(enhanced, roi, record)
                    imaging.save_mask(raw, nii, secondary_path)
                    secondary = {**record, "study": SECONDARY, "prediction_path": secondary_path,
                                 "prediction_sha256": imaging.sha256(secondary_path),
                                 "component_rule": "all highest-intensity-class components; prespecified secondary experiment",
                                 "shared_optimization_with_primary": True}
                    write_json(str(stem) + "_all_components_prediction_record.json", secondary)
                    pending.append(secondary)
                del enhanced, prediction
        with imaging.ResourceMeasurement() as baseline_measure:
            baseline, thresholds = imaging.reference_free_otsu_baseline(normalized, roi)
        baseline_path = directory / "direct_otsu_prediction.nii.gz"
        imaging.save_mask(baseline, nii, baseline_path)
        baseline_record = {**common, "study": PRIMARY, "method": "direct_otsu", "seed": 0, "budget_per_stage": None,
                           "prediction_path": str(baseline_path), "prediction_sha256": imaging.sha256(baseline_path),
                           "thresholds": thresholds, "segmentation_resources": baseline_measure.record(),
                           "appearance": imaging.appearance_metrics(normalized, normalized, roi, slices),
                           "reference_labels_accessed": False,
                           "component_rule": "largest 6-connected component; deterministic unenhanced direct Otsu"}
        write_json(directory / "direct_otsu_prediction_record.json", baseline_record)
        pending.append(baseline_record)
        secondary_path = directory / "direct_otsu_all_components_prediction.nii.gz"
        imaging.save_mask(raw_highest_class(normalized, roi, baseline_record), nii, secondary_path)
        secondary = {**baseline_record, "study": SECONDARY, "prediction_path": str(secondary_path),
                     "prediction_sha256": imaging.sha256(secondary_path),
                     "component_rule": "all highest-intensity-class components; prespecified secondary experiment",
                     "shared_optimization_with_primary": True}
        write_json(directory / "direct_otsu_all_components_prediction_record.json", secondary)
        pending.append(secondary)
        del baseline
        # No reference file is opened above this explicit, per-case boundary.
        write_json(directory / "prediction_boundary.json", {"case_id": case["case_id"], "predictions_saved": len(pending),
                   "prediction_paths": [record["prediction_path"] for record in pending],
                   "reference_labels_accessed": False, "protocol_sha256": protocol_sha})
        print(f"INDEPENDENT EVALUATION {case['case_id']}: {len(pending)} predictions saved", flush=True)
        reference, reference_nii, label_values = load_reference(case, nii)
        reference_path = directory / "reference_lesion.nii.gz"
        imaging.save_mask(reference, reference_nii, reference_path)
        representatives = {}
        for record in pending:
            prediction = np.asarray(nib.load(record["prediction_path"]).dataobj) > 0
            record["evaluation"] = lesion_metrics(prediction, reference, nii.affine, case["foreground_labels"])
            record["reference_evaluation_after_prediction"] = True
            record["saved_output_validation"] = verify_saved_record(record, reference_path, case["foreground_labels"])
            suffix = "_all_components" if record["study"] == SECONDARY else ""
            write_json(directory / f"{record['method']}_seed{record['seed']}{suffix}_evaluated.json", record)
            if record["study"] == PRIMARY and (record["method"] == "direct_otsu" or record["seed"] == args.seeds_list[0]):
                representatives[record["method"]] = prediction.copy()
                enhanced = imaging.apply_enhancement(normalized, roi, record["enhancement"]["x"]) if "enhancement" in record else normalized
                save_panels(normalized, enhanced, prediction, reference, slices, directory / record["method"], case["case_id"] + " " + record["method"])
        with imaging.ResourceMeasurement() as mesh_measure:
            meshes = save_mesh_comparison(roi, representatives, reference, nii.affine, directory / "meshes", args.mesh_stride)
        imaging.save_convergence_plots([record for record in pending if record["study"] == PRIMARY], directory)
        case_manifest = {**case, "protocol_sha256": protocol_sha, "image_sha256": imaging.sha256(case["image_path"]),
                         "label_sha256": imaging.sha256(case["label_path"]), "shape": nii.shape, "affine": nii.affine,
                         "spatial_units": "mm", "qform_code": int(nii.header["qform_code"]), "sform_code": int(nii.header["sform_code"]),
                         "observed_label_values": label_values, "preprocessing": preprocessing,
                         "slices": slices, "slice_selection": "index 71 if in range plus maximal finite nonzero image ROI area; labels excluded",
                         "loading_preprocessing_resources": load_measure.record(), "mesh_resources": mesh_measure.record(), "meshes": meshes,
                         "reference_mask_sha256": imaging.sha256(reference_path)}
    case_manifest["total_resources_including_io_evaluation_mesh"] = total_measure.record()
    write_json(directory / "case_manifest.json", case_manifest)
    write_json(directory / "case_records.json", pending)
    write_json(directory / "case_completed.json", {"case_id": case["case_id"], "protocol_sha256": protocol_sha,
               "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "records": len(pending),
               "case_records_sha256": imaging.sha256(directory / "case_records.json"),
               "case_manifest_sha256": imaging.sha256(directory / "case_manifest.json")})
    return [compact_record(record) for record in pending]


def resume_case(case, directory, protocol_sha):
    marker = json.loads((directory / "case_completed.json").read_text(encoding="utf-8"))
    if marker["protocol_sha256"] != protocol_sha:
        raise ValueError("Completed case uses a different protocol")
    for name in ("case_records", "case_manifest"):
        if imaging.sha256(directory / (name + ".json")) != marker[name + "_sha256"]:
            raise ValueError("Completed case metadata checksum mismatch")
    manifest = json.loads((directory / "case_manifest.json").read_text(encoding="utf-8"))
    for key in ("image", "label"):
        if imaging.sha256(case[key + "_path"]) != manifest[key + "_sha256"]:
            raise ValueError("Completed case input checksum changed")
    if imaging.sha256(directory / "reference_lesion.nii.gz") != manifest["reference_mask_sha256"]:
        raise ValueError("Completed reference mask checksum changed")
    records = json.loads((directory / "case_records.json").read_text(encoding="utf-8"))
    for record in records:
        if imaging.sha256(record["prediction_path"]) != record["prediction_sha256"]:
            raise ValueError("Completed prediction checksum changed")
        if "enhanced_volume_path" in record and imaging.sha256(record["enhanced_volume_path"]) != record["enhanced_volume_sha256"]:
            raise ValueError("Completed enhanced volume checksum changed")
    return [compact_record(record) for record in records]


def preserve_partial_case(directory, output):
    """Keep interrupted attempt evidence before recomputing an incomplete case."""
    directory, output = Path(directory).resolve(), Path(output).resolve()
    if not directory.is_relative_to(output) or directory == output:
        raise ValueError("Partial case directory must be inside the run output")
    archive = output / "partial_attempts"
    archive.mkdir(exist_ok=True)
    destination = archive / (directory.name + "_" + time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "_" + uuid.uuid4().hex[:8])
    if not destination.resolve().is_relative_to(output):
        raise ValueError("Partial case archive must remain inside the run output")
    directory.rename(destination)
    print(f"PRESERVED PARTIAL ATTEMPT {destination}", flush=True)


def summarize(rows, output):
    per_case = []
    for study, case, method in sorted({(row["study"], row["case_id"], row["method"]) for row in rows}):
        group = [row for row in rows if (row["study"], row["case_id"], row["method"]) == (study, case, method)]
        result = {"study": study, "case_id": case, "subject_id": group[0]["subject_id"], "session_id": group[0]["session_id"],
                  "partition": group[0]["partition"], "method": method, "n_seeds": len(group)}
        for metric in METRICS:
            values = [row[metric] for row in group if row.get(metric) is not None]
            result[metric + "_mean"] = float(np.mean(values)) if values else None
            result[metric + "_seed_sd"] = float(np.std(values, ddof=1)) if len(values) > 1 else None
        per_case.append(result)
    subjects = []
    for study, subject, method in sorted({(row["study"], row["subject_id"], row["method"]) for row in per_case}):
        group = [row for row in per_case if (row["study"], row["subject_id"], row["method"]) == (study, subject, method)]
        result = {"study": study, "subject_id": subject, "method": method, "n_sessions": len(group)}
        for metric in METRICS:
            values = [row[metric + "_mean"] for row in group if row[metric + "_mean"] is not None]
            result[metric + "_subject_mean"] = float(np.mean(values)) if values else None
        subjects.append(result)
    across = []
    for study, method in sorted({(row["study"], row["method"]) for row in subjects}):
        group = [row for row in subjects if (row["study"], row["method"]) == (study, method)]
        result = {"study": study, "method": method, "n_subjects": len(group), "n_cases": sum(row["n_sessions"] for row in group),
                  "aggregation": "seed mean within session; session mean within subject; equal-weight subject mean"}
        for metric in METRICS:
            values = [row[metric + "_subject_mean"] for row in group if row[metric + "_subject_mean"] is not None]
            result[metric + "_subject_mean"] = float(np.mean(values)) if values else None
            result[metric + "_subject_sd"] = float(np.std(values, ddof=1)) if len(values) > 1 else None
        across.append(result)
    imaging.write_csv(output / "per_case_seed_summary.csv", per_case)
    imaging.write_csv(output / "per_subject_summary.csv", subjects)
    imaging.write_csv(output / "across_subject_summary.csv", across)
    imaging.write_csv(output / "across_case_summary.csv", across)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--cases", type=int, help="Lexically first cases; default is every manifest case")
    result.add_argument("--resume", action="store_true")
    result.add_argument("--methods", default=",".join(imaging.METHODS))
    result.add_argument("--seeds", default="0,1,2")
    result.add_argument("--budget", type=int, default=1500)
    result.add_argument("--population", type=int, default=30)
    result.add_argument("--mesh-stride", type=int, default=2)
    return result


def run(args):
    args.manifest, args.output = Path(args.manifest).resolve(), Path(args.output).resolve()
    args.methods_list, args.seeds_list = args.methods.split(","), [int(value) for value in args.seeds.split(",")]
    if not args.methods_list or len(set(args.methods_list)) != len(args.methods_list) or any(method not in imaging.METHODS for method in args.methods_list):
        raise ValueError("Methods must be unique members of the frozen method list")
    if not args.seeds_list or len(set(args.seeds_list)) != len(args.seeds_list) or min(args.seeds_list) < 0:
        raise ValueError("Seeds must be unique nonnegative integers")
    if args.budget < 1 or args.population < 4 or args.mesh_stride < 1:
        raise ValueError("Budget must be positive, population >=4, mesh stride >=1")
    cases, metadata = load_manifest(args.manifest, args.cases)
    code_hashes = {name: imaging.sha256(Path(__file__).parent / name) for name in ("external_imaging.py", "imaging.py", "optimizers.py")}
    protocol = {"provenance": PROVENANCE, "manifest_sha256": imaging.sha256(args.manifest), "cases": cases,
                "methods": args.methods_list, "seeds": args.seeds_list, "budget_per_optimizer_stage": args.budget,
                "population": args.population, "normalization_percentiles": [1, 99], "hist_bins": imaging.HIST_BINS,
                "enhancement_bounds": imaging.ENHANCEMENT_BOUNDS, "threshold_bounds": imaging.THRESHOLD_BOUNDS,
                "primary_component_rule": "largest 6-connected component", "secondary_component_rule": "all highest-class components for modified EHO and direct Otsu",
                "selection": "lexically sorted native case IDs; no reference outcomes used", "reference_access": "after all case predictions saved",
                "geometry": "native 3D image grid; strict affine match; mm; no resampling", "mesh_stride": args.mesh_stride,
                "reference_display_stride": 1, "requested_prediction_display_stride": args.mesh_stride,
                "labels_used_for_training_or_tuning": False, "source_code_sha256": code_hashes}
    protocol_sha = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode("utf-8")).hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "run_manifest.json"
    if manifest_path.exists():
        if not args.resume:
            raise FileExistsError("Use a fresh output directory or --resume; completed cases are immutable")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["protocol_sha256"] != protocol_sha:
            raise ValueError("Resume requires the identical manifest, cases, code and protocol")
    else:
        manifest = {"protocol": protocol, "protocol_sha256": protocol_sha, "dataset_metadata": metadata,
                    "cases": cases, "methods": args.methods_list, "seeds": args.seeds_list,
                    "budget_per_optimizer_stage": args.budget, "population": args.population,
                    "environment": {"python": sys.version, "platform": platform.platform(), "processor": platform.processor(),
                                    "logical_cpus": psutil.cpu_count(), "ram_gb": psutil.virtual_memory().total / 2**30,
                                    "device": "CPU", "thread_environment": {key: os.environ[key] for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
                                    "libraries": {package: importlib.metadata.version(package) for package in ("numpy", "scipy", "nibabel", "scikit-image", "plotly", "trimesh")}},
                    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    manifest.update(status="running", completed_cases=0, failed_cases=0)
    write_json(manifest_path, manifest)
    flat_rows, failures = [], []
    started = time.perf_counter()
    csv_path = args.output / "all_runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = None
        for index, case in enumerate(cases):
            directory = args.output / case["case_id"]
            try:
                if (directory / "case_completed.json").exists():
                    print(f"RESUME {case['case_id']}: verified completed case", flush=True)
                    rows = resume_case(case, directory, protocol_sha)
                else:
                    if directory.exists():
                        preserve_partial_case(directory, args.output)
                    rows = predict_case(case, directory, args, protocol_sha)
                if writer is None:
                    fields = list(dict.fromkeys(key for row in rows for key in row))
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                flat_rows.extend(rows)
                manifest["completed_cases"] += 1
            except Exception as error:
                failure = {"case_id": case["case_id"], "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
                           "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                           "partial_case_policy": "uncompleted case recomputed on --resume; completed cases verified and preserved"}
                failures.append(failure)
                manifest["failed_cases"] += 1
                directory.mkdir(exist_ok=True)
                write_json(directory / "case_failure.json", failure)
                with (args.output / "failure_log.jsonl").open("a", encoding="utf-8") as failure_handle:
                    failure_handle.write(json.dumps(failure) + "\n")
                print(f"CASE FAILED {case['case_id']}: {error}", flush=True)
            manifest["processed_cases"] = index + 1
            write_json(manifest_path, manifest)
            print(f"PROGRESS {index + 1}/{len(cases)} completed={manifest['completed_cases']} failed={manifest['failed_cases']}", flush=True)
    if flat_rows:
        summarize(flat_rows, args.output)
    write_json(args.output / "current_failures.json", failures)
    manifest.update(status="completed" if not failures else "completed_with_failures", output_records=len(flat_rows),
                    total_seconds_this_invocation=time.perf_counter() - started,
                    completed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    write_json(manifest_path, manifest)
    print(json.dumps({"status": manifest["status"], "completed_cases": manifest["completed_cases"], "failed_cases": len(failures), "output": str(args.output)}), flush=True)
    return manifest


if __name__ == "__main__":
    outcome = run(parser().parse_args())
    if outcome["failed_cases"]:
        raise SystemExit(1)
