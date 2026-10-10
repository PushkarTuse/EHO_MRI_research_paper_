"""New, unsupervised MRI contrast/threshold baseline; not recovered historical code.

Labels never enter preprocessing, enhancement, threshold selection, component
selection, or slice selection. The CLI writes every prediction for a case before
opening that case's reference label volume. See imaging_method_notes.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
import threading
import time
from contextlib import AbstractContextManager
from pathlib import Path

import nibabel as nib
import numpy as np
import psutil
from scipy import ndimage
from skimage import measure
from skimage.filters import threshold_multiotsu
from skimage.metrics import structural_similarity

METHODS = ("original_eho", "modified_eho", "pso", "ga", "acor")
PROVENANCE = "new_unsupervised_reconstruction_2026-10-04_not_historical_MRI_code"
HIST_BINS = 256
ENHANCEMENT_BOUNDS = [(0.7, 1.5), (0.8, 1.3)]
THRESHOLD_BOUNDS = [(0.02, 0.98), (0.02, 0.98)]


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(jsonable(value), indent=2, allow_nan=False), encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class ResourceMeasurement(AbstractContextManager):
    """Process RSS sampled every 50ms: observed peak, not an allocator exact peak."""
    def __enter__(self):
        self.process = psutil.Process()
        self.baseline = self.process.memory_info().rss
        self.peak = self.baseline
        self.stop = threading.Event()
        self.started = time.perf_counter()
        self.worker = threading.Thread(target=self._sample, daemon=True)
        self.worker.start()
        return self

    def _sample(self):
        while not self.stop.wait(0.05):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __exit__(self, *args):
        self.peak = max(self.peak, self.process.memory_info().rss)
        self.stop.set()
        self.worker.join()
        self.seconds = time.perf_counter() - self.started
        return False

    def record(self):
        return {"seconds": self.seconds, "baseline_rss_mb": self.baseline / 2**20,
                "sampled_peak_rss_mb": self.peak / 2**20,
                "sampled_rss_increase_mb": (self.peak - self.baseline) / 2**20,
                "rss_sampling_seconds": 0.05}


def preprocess_flair(flair):
    """Nonzero finite image ROI; fixed 1st/99th percentiles, no labels."""
    image = np.asarray(flair, dtype=np.float32)
    if image.ndim != 3:
        raise ValueError("A 3D FLAIR volume is required")
    roi = np.isfinite(image) & (image != 0)
    if not np.any(roi):
        raise ValueError("No nonzero finite MRI voxels")
    low, high = np.percentile(image[roi], [1.0, 99.0])
    if high <= low:
        raise ValueError("Image has no usable intensity range")
    normalized = np.zeros(image.shape, dtype=np.float32)
    normalized[roi] = np.clip((image[roi] - low) / (high - low), 0, 1)
    return normalized, roi, {"percentiles": [1.0, 99.0], "low": float(low),
                             "high": float(high), "roi_voxels": int(roi.sum())}


def load_flair(path):
    nii = nib.load(str(path))
    if len(nii.shape) != 4 or nii.shape[3] < 1:
        raise ValueError("Expected Task01 4D image with FLAIR modality at index 0")
    flair = np.asarray(nii.dataobj[..., 0], dtype=np.float32)
    return flair, nii


def image_histogram(image, roi, bins=HIST_BINS):
    counts, edges = np.histogram(image[roi], bins=bins, range=(0.0, 1.0))
    total = counts.sum()
    if total == 0:
        raise ValueError("Empty ROI")
    return counts.astype(float) / total, (edges[:-1] + edges[1:]) * 0.5


def intensity_transform(values, gamma, contrast):
    return np.clip((np.power(np.clip(values, 0, 1), gamma) - 0.5) * contrast + 0.5, 0, 1)


def enhancement_objective(histogram):
    """Minimise -RMS contrast + 0.5 departure MSE + 0.05 saturation mass."""
    weights, centers = histogram
    def objective(parameters):
        gamma, contrast = np.asarray(parameters)
        adjusted = intensity_transform(centers, gamma, contrast)
        mean = np.dot(weights, adjusted)
        rms_contrast = np.sqrt(np.dot(weights, (adjusted - mean)**2))
        departure = np.dot(weights, (adjusted - centers)**2)
        saturation = np.dot(weights, (adjusted <= 0) | (adjusted >= 1))
        return float(-rms_contrast + 0.5 * departure + 0.05 * saturation)
    return objective


def apply_enhancement(image, roi, parameters):
    adjusted = np.zeros(image.shape, dtype=np.float32)
    adjusted[roi] = intensity_transform(image[roi], *parameters)
    return adjusted


def otsu_objective(histogram):
    """Three-class between-class variance, using 256 bins; no pathology labels."""
    weights, centers = histogram
    bins = len(weights)
    cumulative_w = np.r_[0.0, np.cumsum(weights)]
    cumulative_m = np.r_[0.0, np.cumsum(weights * centers)]
    total_mean = cumulative_m[-1]
    def objective(parameters):
        cuts = np.sort(np.clip(np.floor(np.asarray(parameters) * bins).astype(int), 1, bins - 1))
        if cuts[0] >= cuts[1]:
            return 1.0
        edges = [0, int(cuts[0]), int(cuts[1]), bins]
        between = 0.0
        for start, end in zip(edges[:-1], edges[1:]):
            mass = cumulative_w[end] - cumulative_w[start]
            if mass < 1e-10:
                return 1.0
            average = (cumulative_m[end] - cumulative_m[start]) / mass
            between += mass * (average - total_mean)**2
        return float(-between)
    return objective


def largest_component(mask):
    labels, count = ndimage.label(np.asarray(mask, bool), structure=ndimage.generate_binary_structure(3, 1))
    if count == 0:
        return np.zeros(mask.shape, dtype=bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def mask_from_thresholds(image, roi, parameters):
    """Highest-intensity class, largest 6-connected component; fixed rule."""
    cuts = np.sort(np.clip(np.floor(np.asarray(parameters) * HIST_BINS).astype(int), 1, HIST_BINS - 1))
    threshold = float(cuts[1] / HIST_BINS)
    raw = np.asarray(roi, bool) & (image >= threshold)
    prediction = largest_component(raw)
    return prediction, {"thresholds": (cuts / HIST_BINS).tolist(),
                        "raw_positive_voxels": int(raw.sum()),
                        "positive_voxels": int(prediction.sum()), "connectivity": 6}


def select_slices(roi):
    """Historical index71 if in range plus maximal nonzero-ROI area, image only."""
    greatest_area = int(np.argmax(np.count_nonzero(roi, axis=(0, 1))))
    return sorted(set([greatest_area] + ([71] if roi.shape[2] > 71 else [])))


def appearance_metrics(original, enhanced, roi, slices):
    differences = original[roi] - enhanced[roi]
    mse = float(np.mean(differences**2))
    # JSON null encodes the infinite identity PSNR; value accompanies a flag.
    psnr = float(-10 * np.log10(mse)) if mse > 0 else None
    selected = []
    for index in slices:
        a, b = original[..., index], enhanced[..., index]
        win = min(7, min(a.shape))
        if win % 2 == 0:
            win -= 1
        if win >= 3:
            ssim, ssim_map = structural_similarity(a, b, data_range=1.0, win_size=win, full=True)
            valid = ndimage.binary_erosion(roi[..., index], iterations=win // 2)
            roi_ssim = float(ssim_map[valid].mean()) if valid.any() else None
        else:
            ssim, roi_ssim = None, None
        selected.append({"slice_index_axis2": index, "input_similarity_ssim": ssim,
                         "roi_input_similarity_ssim": roi_ssim,
                         "roi_ssim_rule": "average SSIM map where complete window is in nonzero ROI"})
    return {"roi_input_departure_mse": mse, "roi_input_similarity_psnr_db": psnr,
            "identity_psnr_infinite": mse == 0, "selected_slice_input_ssim": selected,
            "selected_slice_input_ssim_mean": float(np.mean([r["input_similarity_ssim"] for r in selected if r["input_similarity_ssim"] is not None])),
            "selected_slice_roi_input_ssim_mean": float(np.mean([r["roi_input_similarity_ssim"] for r in selected if r["roi_input_similarity_ssim"] is not None])) if any(r["roi_input_similarity_ssim"] is not None for r in selected) else None,
            "reference_meaning": "same normalized input; appearance similarity, NOT denoising/diagnostic accuracy"}


def optimise_stage(objective, bounds, method, seed, budget, population):
    try:
        from .optimizers import optimise
    except ImportError:
        from optimizers import optimise
    return optimise(objective, bounds, method, seed, max_evals=budget, population=population)


def predict_from_image(normalized, roi, method, seed, budget, population=30):
    """Only image inputs. No label/mask-of-tumour argument or reference access."""
    with ResourceMeasurement() as enhancement_measurement:
        enh = optimise_stage(enhancement_objective(image_histogram(normalized, roi)),
                             ENHANCEMENT_BOUNDS, method, seed, budget, population)
        enhanced = apply_enhancement(normalized, roi, np.asarray(enh["x"]))
    with ResourceMeasurement() as segmentation_measurement:
        seg = optimise_stage(otsu_objective(image_histogram(enhanced, roi)),
                             THRESHOLD_BOUNDS, method, seed + 100000, budget, population)
        prediction, threshold_info = mask_from_thresholds(enhanced, roi, seg["x"])
    return enhanced, prediction, {"enhancement": enh, "segmentation": seg,
          "enhancement_resources": enhancement_measurement.record(),
          "segmentation_resources": segmentation_measurement.record(), "thresholds": threshold_info,
          "provenance": PROVENANCE, "reference_labels_accessed": False}


def reference_free_otsu_baseline(normalized, roi):
    """Deterministic library multilevel-Otsu, no contrast optimisation."""
    weights, centers = image_histogram(normalized, roi)
    thresholds = threshold_multiotsu(classes=3, hist=(weights, centers))
    # library threshold values use bin centers: classify exact returned boundary.
    raw = roi & (normalized > thresholds[-1])
    return largest_component(raw), {"thresholds": thresholds.tolist(), "raw_positive_voxels": int(raw.sum())}


def save_volume(values, source_nii, path, dtype=np.float32):
    """Save a 3D result on the original image grid, preserving spatial metadata.

    Input is a volume with the image's first-three-axis shape. Output is a new
    NIfTI with copied units, affine, qform and sform; source files stay unchanged.
    """
    values = np.asarray(values, dtype=dtype)
    if values.shape != source_nii.shape[:3]:
        raise ValueError("Output volume must use the original 3D image grid")
    header = source_nii.header.copy()
    header.set_data_dtype(dtype)
    nii = nib.Nifti1Image(values, source_nii.affine, header)
    qform, qcode = source_nii.get_qform(coded=True)
    sform, scode = source_nii.get_sform(coded=True)
    if qform is not None:
        nii.set_qform(qform, int(qcode))
    if sform is not None:
        nii.set_sform(sform, int(scode))
    nib.save(nii, str(path))


def save_mask(mask, source_nii, path):
    """Save a binary prediction on the original image grid."""
    save_volume(np.asarray(mask, bool), source_nii, path, dtype=np.uint8)


def segmentation_metrics(prediction, reference, affine):
    prediction, reference = np.asarray(prediction, bool), np.asarray(reference, bool)
    if prediction.shape != reference.shape:
        raise ValueError("Evaluation masks must have exactly the same grid; no resizing")
    tp = int(np.count_nonzero(prediction & reference))
    fp = int(np.count_nonzero(prediction & ~reference))
    fn = int(np.count_nonzero(~prediction & reference))
    tn = int(np.count_nonzero(~prediction & ~reference))
    union = tp + fp + fn
    dice_den = 2 * tp + fp + fn
    voxel_ml = abs(float(np.linalg.det(np.asarray(affine)[:3, :3]))) / 1000.0
    recall = tp / (tp + fn) if tp + fn else None
    return {"dice_whole_tumour": 2 * tp / dice_den if dice_den else 1.0,
            "iou_whole_tumour": tp / union if union else 1.0,
            "precision_whole_tumour": tp / (tp + fp) if tp + fp else None,
            "recall_whole_tumour": recall, "sensitivity_whole_tumour": recall,
            "specificity": tn / (tn + fp) if tn + fp else None,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "prediction_ml": (tp + fp) * voxel_ml, "reference_ml": (tp + fn) * voxel_ml,
            "voxel_volume_ml": voxel_ml, "reference_rule": "label>0: union of labels 1,2,3"}


def mesh_from_mask(mask, affine, stride=2):
    """Display-only decimation with affine correction; evaluation stays full resolution."""
    stride = int(stride)
    if stride < 1:
        raise ValueError("stride must be positive")
    reduced = np.asarray(mask, bool)[::stride, ::stride, ::stride]
    if not reduced.any():
        return np.empty((0, 3)), np.empty((0, 3), dtype=int)
    padded = np.pad(reduced.astype(np.uint8), 1)
    vertices, faces, _, _ = measure.marching_cubes(padded, level=0.5)
    vertices = (vertices - 1.0) * stride
    world = nib.affines.apply_affine(affine, vertices)
    return world, faces


def write_mesh(vertices, faces, stem):
    if len(vertices) == 0:
        return {"status": "empty_mask_no_surface", "vertices": 0, "faces": 0}
    import trimesh
    surface = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    surface.export(str(stem) + ".ply")
    surface.export(str(stem) + ".stl")
    return {"status": "exported", "vertices": len(vertices), "faces": len(faces),
            "ply": str(stem) + ".ply", "stl": str(stem) + ".stl"}


def save_mesh_comparison(image_roi, masks, reference, affine, output, stride=2):
    """Prediction and reference stay visibly separate; reference is never called detection."""
    import plotly.graph_objects as go
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    figure = go.Figure()
    export_record = {}
    entries = [("Brain context (nonzero FLAIR)", image_roi, "lightgray", .13),
               ("Reference whole tumour (given labels)", reference, "royalblue", .45)]
    palette = ["crimson", "orange", "seagreen", "purple", "magenta", "darkcyan"]
    entries += [(name + " predicted threshold mask", mask, palette[i % len(palette)], .65)
                for i, (name, mask) in enumerate(masks.items())]
    for i, (name, mask, color, opacity) in enumerate(entries):
        vertices, faces = mesh_from_mask(mask, affine, stride)
        slug = "brain_context" if i == 0 else "reference_whole_tumour" if i == 1 else list(masks)[i - 2] + "_prediction"
        export_record[slug] = write_mesh(vertices, faces, output / slug)
        if len(vertices):
            figure.add_trace(go.Mesh3d(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
                             i=faces[:, 0], j=faces[:, 1], k=faces[:, 2], name=name,
                             color=color, opacity=opacity, showlegend=True,
                             visible=True if i in (0, 2) else "legendonly", flatshading=False))
    figure.update_layout(title="Image-only threshold predictions and independent reference labels",
                         scene=dict(xaxis_title="World x (mm)", yaxis_title="World y (mm)",
                                    zaxis_title="World z (mm)", aspectmode="data"),
                         legend=dict(title="Click to compare predictions/reference"),
                         annotations=[dict(text="Unsupervised exploratory baseline. Blue = supplied reference, not prediction. Display meshes are decimated; metrics use full-resolution masks.",
                                           x=.5, y=0, xref="paper", yref="paper", showarrow=False)],
                         margin=dict(l=0, r=0, t=70, b=65))
    figure.write_html(str(output / "interactive_prediction_reference.html"), include_plotlyjs=True, full_html=True)
    export_record["display_stride"] = stride
    export_record["evaluation_downsampled"] = False
    write_json(output / "mesh_manifest.json", export_record)
    return export_record


def save_slice_panels(normalized, enhanced, prediction, reference, slices, output, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for index in slices:
        fig, axes = plt.subplots(1, 4, figsize=(13, 4), constrained_layout=True)
        panels = [normalized[..., index], enhanced[..., index], prediction[..., index], reference[..., index]]
        labels = ["Normalized FLAIR", "Contrast transform", "Predicted threshold mask", "Reference whole tumour"]
        for ax, values, label in zip(axes, panels, labels):
            ax.imshow(values.T, cmap="gray", origin="lower", vmin=0, vmax=1)
            ax.set_title(label)
            ax.axis("off")
        fig.suptitle(f"{title} | axis-2 slice {index} | image-grid orientation")
        fig.savefig(str(output) + f"_slice_{index}.png", dpi=160)
        plt.close(fig)


def select_cases(dataset, count):
    dataset = Path(dataset)
    metadata = json.loads((dataset / "dataset.json").read_text(encoding="utf-8"))
    if metadata.get("modality", {}).get("0", "").upper() != "FLAIR":
        raise ValueError("Dataset modality 0 must be FLAIR")
    if count < 1:
        raise ValueError("At least one case is required")
    training = sorted(metadata["training"], key=lambda row: row["image"])
    selected = []
    for row in training[:count]:
        image, label = dataset / row["image"], dataset / row["label"]
        if not image.exists() or not label.exists():
            raise FileNotFoundError(f"Missing selected image/label path: {image}, {label}")
        selected.append({"case_id": image.name.removesuffix(".nii.gz"), "image": image, "label": label})
    return selected, metadata


def flatten_record(record):
    result = {key: record[key] for key in ("case_id", "method", "seed", "budget_per_stage", "provenance")}
    result.update(record["evaluation"])
    result.update({key: value for key, value in record["appearance"].items() if not isinstance(value, (dict, list))})
    for stage in ("enhancement", "segmentation"):
        if stage in record:
            result[stage + "_objective"] = record[stage]["fun"]
            result[stage + "_evaluations"] = record[stage]["evaluations"]
        resource = record.get(stage + "_resources", {})
        for key in ("seconds", "sampled_peak_rss_mb", "sampled_rss_increase_mb"):
            result[stage + "_" + key] = resource.get(key)
    return result


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize(records):
    """Seeds are summarized within case; case means are separate observational units."""
    metrics = ("dice_whole_tumour", "iou_whole_tumour", "precision_whole_tumour", "recall_whole_tumour", "prediction_ml",
               "roi_input_similarity_psnr_db", "selected_slice_input_ssim_mean", "selected_slice_roi_input_ssim_mean",
               "enhancement_seconds", "segmentation_seconds", "enhancement_objective", "segmentation_objective",
               "enhancement_sampled_peak_rss_mb", "segmentation_sampled_peak_rss_mb")
    flat_records = [flatten_record(record) for record in records]
    per_case = []
    for case in sorted({r["case_id"] for r in records}):
        for method in sorted({r["method"] for r in records}):
            rows = [r for r in flat_records if r["case_id"] == case and r["method"] == method]
            if not rows:
                continue
            record = {"case_id": case, "method": method, "n_seeds": len(rows)}
            for metric in metrics:
                values = [r[metric] for r in rows if r.get(metric) is not None]
                record[metric + "_mean"] = float(np.mean(values)) if values else None
                record[metric + "_seed_sd"] = float(np.std(values, ddof=1)) if len(values) > 1 else None
            per_case.append(record)
    across_cases = []
    for method in sorted({r["method"] for r in records}):
        rows = [r for r in per_case if r["method"] == method]
        record = {"method": method, "n_cases": len(rows)}
        for metric in metrics:
            values = [r[metric + "_mean"] for r in rows if r[metric + "_mean"] is not None]
            record[metric + "_case_mean"] = float(np.mean(values)) if values else None
            record[metric + "_case_sd"] = float(np.std(values, ddof=1)) if len(values) > 1 else None
        across_cases.append(record)
    return per_case, across_cases


def save_convergence_plots(records, output):
    """Mean +/- seed SD of measured incumbents on the same per-case objective."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for case in sorted({r["case_id"] for r in records}):
        figure, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
        for axis, stage in zip(axes, ("enhancement", "segmentation")):
            for method in METHODS:
                rows = [r for r in records if r["case_id"] == case and r["method"] == method]
                if not rows:
                    continue
                histories = [np.asarray(r[stage]["history"], float) for r in rows]
                counts = [len(history) for history in histories]
                if len(set(counts)) != 1:
                    raise ValueError("Comparison histories must have equal evaluation budgets")
                values = np.stack([history[:, 1] for history in histories])
                x = histories[0][:, 0]
                mean = values.mean(axis=0)
                line, = axis.plot(x, mean, label=f"{method} (n={len(rows)})")
                if len(rows) > 1:
                    sd = values.std(axis=0, ddof=1)
                    axis.fill_between(x, mean-sd, mean+sd, color=line.get_color(), alpha=.15)
            axis.set(xlabel="Counted objective evaluations", ylabel="Best objective (lower is better)", title=stage.capitalize())
            axis.legend(fontsize=7)
        figure.suptitle(case + " | mean +/- seed SD | reconstructed image-only objective")
        figure.savefig(Path(output) / f"{case}_convergence.png", dpi=160)
        plt.close(figure)


def run(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    selected, metadata = select_cases(args.dataset, args.cases)
    seeds = [int(x) for x in args.seeds.split(",")]
    methods = args.methods.split(",")
    if any(method not in METHODS for method in methods):
        raise ValueError("Unknown optimizer method")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be nonempty and unique")
    if not methods or len(set(methods)) != len(methods):
        raise ValueError("Methods must be nonempty and unique")
    if (output / "run_manifest.json").exists():
        raise FileExistsError("Choose a fresh output directory; measured runs are immutable")
    manifest = {"provenance": PROVENANCE, "dataset": str(Path(args.dataset).resolve()),
                "dataset_metadata": {k: v for k, v in metadata.items() if k not in ("training", "test")},
                "cases": selected, "seeds": seeds, "methods": methods,
                "budget_per_optimizer_stage": args.budget, "population": args.population,
                "protocol": {"normalization_percentiles": [1, 99], "roi": "finite nonzero FLAIR",
                             "enhancement_bounds": ENHANCEMENT_BOUNDS, "otsu_bounds": THRESHOLD_BOUNDS,
                             "hist_bins": HIST_BINS, "segmentation_class": "highest of three Otsu classes",
                             "component_rule": "largest 6-connected component, fixed before evaluation",
                             "selection": "lexically first cases from training manifest; no labels examined",
                             "reference_access": "after ALL methods/seeds predicted masks saved for each case",
                             "cohort_role": "retrospective evaluation subset of MSD training set; not hidden challenge test set",
                             "labels_used_for_training_or_tuning": False, "mesh_stride": args.mesh_stride},
                "environment": {"python": sys.version, "platform": platform.platform(), "processor": platform.processor(),
                                "logical_cpus": psutil.cpu_count(), "ram_gb": psutil.virtual_memory().total / 2**30,
                                "libraries": {p: importlib.metadata.version(p) for p in ("numpy", "scipy", "nibabel", "scikit-image", "plotly", "trimesh")}},
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": "running"}
    # Persist protocol before any label is opened or a prediction generated.
    write_json(output / "run_manifest.json", manifest)
    all_records = []
    case_resources = []
    started = time.perf_counter()
    for case_index, case in enumerate(selected):
        directory = output / case["case_id"]
        directory.mkdir()
        with ResourceMeasurement() as load_measure:
            flair, nii = load_flair(case["image"])
            normalized, roi, preprocessing = preprocess_flair(flair)
            del flair
        slices = select_slices(roi)
        case_manifest = {**case, "image_sha256": sha256(case["image"]), "shape": normalized.shape,
                         "affine": nii.affine, "preprocessing": preprocessing, "slices": slices,
                         "loading_preprocessing_resources": load_measure.record()}
        pending = []
        for method in methods:
            for seed in seeds:
                print(f"IMAGE-ONLY prediction {case['case_id']} {method} seed={seed}", flush=True)
                enhanced, prediction, details = predict_from_image(normalized, roi, method, seed, args.budget, args.population)
                stem = directory / f"{method}_seed{seed}"
                prediction_path = str(stem) + "_prediction.nii.gz"
                save_mask(prediction, nii, prediction_path)
                record = {"case_id": case["case_id"], "method": method, "seed": seed,
                          "budget_per_stage": args.budget, **details,
                          "prediction_path": prediction_path, "prediction_sha256": sha256(prediction_path),
                          "appearance": appearance_metrics(normalized, enhanced, roi, slices)}
                write_json(str(stem) + "_prediction_record.json", record)
                # Representative enhanced volume is retained for every method/case.
                # This is a normalized intensity transform, not a restored raw MRI.
                if seed == seeds[0]:
                    enhancement_path = str(stem) + "_enhanced_normalized_flair.nii.gz"
                    save_volume(enhanced, nii, enhancement_path)
                    record["enhanced_volume_path"] = enhancement_path
                    record["enhanced_volume_sha256"] = sha256(enhancement_path)
                    record["enhanced_volume_units"] = "normalized intensity [0,1]"
                    write_json(str(stem) + "_prediction_record.json", record)
                for stage in ("enhancement", "segmentation"):
                    write_csv(str(stem) + f"_{stage}_convergence.csv",
                              [{"evaluations": h[0], "best_objective": h[1]} for h in record[stage]["history"]])
                pending.append(record)
                del prediction, enhanced
        with ResourceMeasurement() as baseline_measure:
            baseline_mask, baseline_params = reference_free_otsu_baseline(normalized, roi)
        baseline_path = directory / "direct_otsu_prediction.nii.gz"
        save_mask(baseline_mask, nii, baseline_path)
        pending.append({"case_id": case["case_id"], "method": "direct_otsu", "seed": 0,
                        "budget_per_stage": None, "provenance": "deterministic_skimage_3class_otsu_on_unenhanced_input",
                        "prediction_path": str(baseline_path), "prediction_sha256": sha256(baseline_path),
                        "segmentation_resources": baseline_measure.record(), "thresholds": baseline_params,
                        "appearance": appearance_metrics(normalized, normalized, roi, slices), "reference_labels_accessed": False})
        del baseline_mask
        # Evaluation boundary: labels are opened for the first time below.
        print(f"INDEPENDENT EVALUATION: all predictions saved for {case['case_id']}", flush=True)
        label_nii = nib.load(str(case["label"]))
        if label_nii.shape != normalized.shape or not np.allclose(label_nii.affine, nii.affine, atol=1e-5):
            raise ValueError("Image/reference geometry mismatch: no silent resampling")
        label_values = np.asarray(label_nii.dataobj)
        if not np.isfinite(label_values).all() or not np.isin(label_values, [0, 1, 2, 3]).all():
            raise ValueError("Task01 reference must contain finite labels 0,1,2,3")
        case_manifest["observed_label_values"] = np.unique(label_values).tolist()
        reference = label_values > 0
        del label_values
        save_mask(reference, label_nii, directory / "reference_whole_tumour.nii.gz")
        case_manifest["label_sha256"] = sha256(case["label"])
        representative_masks = {}
        for record in pending:
            prediction = np.asarray(nib.load(record["prediction_path"]).dataobj) > 0
            record["evaluation"] = segmentation_metrics(prediction, reference, nii.affine)
            record["reference_evaluation_after_prediction"] = True
            write_json(directory / f"{record['method']}_seed{record['seed']}_evaluated.json", record)
            if record["seed"] == seeds[0] or record["method"] == "direct_otsu":
                representative_masks[record["method"]] = prediction.copy()
                enhanced = (apply_enhancement(normalized, roi, record["enhancement"]["x"])
                            if "enhancement" in record else normalized)
                save_slice_panels(normalized, enhanced, prediction, reference, slices,
                                  directory / record["method"], case["case_id"] + " " + record["method"])
            all_records.append(record)
        if not args.no_mesh:
            with ResourceMeasurement() as mesh_measure:
                meshes = save_mesh_comparison(roi, representative_masks, reference, nii.affine, directory / "meshes", args.mesh_stride)
            case_manifest["mesh_resources"] = mesh_measure.record()
            case_manifest["meshes"] = meshes
        write_json(directory / "case_manifest.json", case_manifest)
        case_resources.append(case_manifest)
        del normalized, roi, reference, representative_masks
    write_json(output / "all_records.json", all_records)
    write_csv(output / "all_runs.csv", [flatten_record(r) for r in all_records])
    per_case, across_case = summarize(all_records)
    write_csv(output / "per_case_seed_summary.csv", per_case)
    write_csv(output / "across_case_summary.csv", across_case)
    save_convergence_plots(all_records, output)
    manifest.update({"status": "completed", "total_seconds_including_io_mesh_evaluation": time.perf_counter() - started,
                     "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "output_records": len(all_records), "case_manifests": [str(output / c["case_id"] / "case_manifest.json") for c in selected]})
    write_json(output / "run_manifest.json", manifest)
    print(json.dumps({"status": "completed", "runs": len(all_records), "output": str(output)}), flush=True)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--dataset", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--cases", type=int, default=3)
    result.add_argument("--seeds", default="0,1,2,3,4")
    result.add_argument("--methods", default=",".join(METHODS))
    result.add_argument("--budget", type=int, default=1500)
    result.add_argument("--population", type=int, default=30)
    result.add_argument("--mesh-stride", type=int, default=2)
    result.add_argument("--no-mesh", action="store_true")
    return result


if __name__ == "__main__":
    run(parser().parse_args())
