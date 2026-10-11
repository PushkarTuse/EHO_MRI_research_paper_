"""Prespecified image-only registration and controlled Gaussian-noise studies.

The earliest sessions of the first three numeric subject IDs are selected from
the external cohort manifest, without opening segmentation references. The
registration study reuses the existing known pull-transform/bounds/objective.
The noise study freezes the primary contrast objective; its normalized original
image is a synthetic clean reference for evaluation only, not clinical ground
truth. Neither experiment demonstrates clinical registration or denoising.

Usage: python external_studies.py --manifest reports/mslesseg_case_manifest.json
       --output results/mslesseg_additional --subjects 3
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import time
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage
from skimage.metrics import structural_similarity

import imaging
import registration
from optimizers import METHODS, optimise

BUDGET = 1500
POPULATION = 30
REGISTRATION_SEEDS = (0, 1, 2, 3, 4)
CORRUPTION_SEEDS = (0, 1, 2)
NOISE_SIGMAS = (0.03, 0.08)
GAUSSIAN_SIGMA_PIXELS = 1.0
PROTOCOL_VERSION = "external_image_only_stress_studies_20261011_v1"


def natural_key(value):
    return tuple((1, int(part)) if part.isdigit() else (0, part.lower())
                 for part in re.split(r"(\d+)", str(value)) if part)


def safe_tag(value):
    tag = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))
    if tag in ("", ".", ".."):
        raise ValueError("Case ID does not provide a usable output name")
    return tag


def select_cases(manifest, manifest_path, subjects=3):
    """Return only image fields; label paths are neither resolved nor opened."""
    if subjects != 3:
        raise ValueError("This prespecified study requires exactly three subjects")
    entries = manifest.get("cases", []) if isinstance(manifest, dict) else manifest
    if not isinstance(entries, list) or not entries:
        raise ValueError("Manifest must contain a nonempty cases list")
    cases = []
    for entry in entries:
        subject = entry.get("subject", entry.get("subject_id"))
        session = entry.get("session", entry.get("session_id", entry.get("timepoint")))
        case_id = entry.get("id", entry.get("case_id"))
        image_path = entry.get("image_path", entry.get("image"))
        if any(value is None for value in (subject, session, case_id, image_path)):
            raise ValueError("Each case needs id, subject, session and image_path")
        if str(entry.get("modality", "FLAIR")).upper() != "FLAIR":
            raise ValueError("Additional studies require the declared FLAIR image")
        path = Path(image_path)
        if not path.is_absolute():
            path = Path(manifest_path).resolve().parent / path
        cases.append(dict(case_id=str(case_id), subject=str(subject), session=str(session),
                          partition=entry.get("partition"), image_path=str(path.resolve()),
                          modality="FLAIR", modality_index=int(entry.get("modality_index", 0))))
    cases.sort(key=lambda c: (natural_key(c["subject"]), natural_key(c["session"]),
                              natural_key(c["case_id"])))
    selected, seen = [], set()
    for case in cases:
        if case["subject"] not in seen:
            selected.append(case)
            seen.add(case["subject"])
        if len(selected) == subjects:
            break
    if len(selected) != subjects:
        raise ValueError("Manifest has fewer than three distinct subjects")
    if len({safe_tag(c["case_id"]) for c in selected}) != len(selected):
        raise ValueError("Selected case IDs collide as output names")
    return selected


def load_image_volume(path, modality=0):
    """Load only a manifest-selected image, with safe finite foreground handling."""
    image = nib.load(str(path))
    native_shape = list(image.shape)
    if len(image.shape) == 4:
        if not 0 <= modality < image.shape[3]:
            raise ValueError("Invalid 4D FLAIR channel")
        volume = np.asarray(image.dataobj[..., modality], dtype=np.float32)
    elif len(image.shape) == 3:
        volume = np.asarray(image.dataobj, dtype=np.float32)
    else:
        raise ValueError("Image must be a 3D NIfTI or a selected 4D channel")
    if not all(size > 0 for size in volume.shape):
        raise ValueError("Empty image dimensions")
    return volume, dict(image_path=str(Path(path).resolve()), native_shape=native_shape,
                       selected_volume_shape=list(volume.shape), nifti_affine=image.affine.tolist(),
                       modality="FLAIR", modality_index=modality if len(native_shape) == 4 else None,
                       reference_labels_accessed=False)


def foreground_slice(volume, preferred=None, positive_only=False):
    foreground = np.isfinite(volume) & ((volume > 0) if positive_only else (volume != 0))
    areas = np.count_nonzero(foreground, axis=(0, 1))
    if preferred is not None and 0 <= preferred < volume.shape[2] and areas[preferred] >= 20:
        return int(preferred), "prespecified axis-2 slice 71 with usable finite foreground"
    index = int(np.argmax(areas))
    if areas[index] < 20:
        raise ValueError("No slice has sufficient finite nonzero foreground")
    return index, "maximal finite nonzero image foreground area; ties use lowest slice index"


def _anatomical_arrays(volume, index, max_size):
    fixed = volume[:, :, index].astype(float)
    positive = fixed[np.isfinite(fixed) & (fixed > 0)]
    if positive.size < 20:
        raise ValueError("Selected slice lacks finite positive anatomical content")
    high = float(np.percentile(positive, 99.5))
    fixed = np.clip(np.where(np.isfinite(fixed), fixed, 0.0) / high, 0, 1)
    factor = min(1.0, max_size / max(fixed.shape))
    if factor < 1:
        fixed = ndimage.zoom(fixed, factor, order=1, prefilter=False)
    truth = np.array([12.0, 4.0, -3.0])
    matrix, offset = registration.affine_parameters(fixed.shape, truth)
    inverse = np.linalg.inv(matrix)
    moving = ndimage.affine_transform(fixed, inverse, -inverse @ offset, order=1,
                                     mode="constant", cval=0.0, prefilter=False)
    bounds = np.array([[-30.0, 30.0], [-12.0, 12.0], [-12.0, 12.0]])
    rr, cc = np.indices(fixed.shape)
    centre = (np.asarray(fixed.shape) - 1) / 2
    radius = min(centre) - np.sqrt(2) * 12 - 2
    if radius <= 3:
        raise ValueError("Image too small for prespecified translation range")
    mask = (((rr - centre[0]) ** 2 + (cc - centre[1]) ** 2 <= radius ** 2) & (fixed > 0))
    if mask.sum() < 20:
        raise ValueError("Insufficient fixed interior foreground support")
    r = radius / 2
    landmarks = np.array([centre, centre + [r, 0], centre + [-r, 0],
                          centre + [0, r], centre + [0, -r]])
    return fixed, moving, bounds, truth, mask, landmarks, high, factor


def load_anatomical_case(path, slice_index=71, max_size=128, modality=0):
    """Preserve registration.py truth/bounds/scaling; adapt short-volume slices."""
    if max_size < 32:
        raise ValueError("max_size must be >=32")
    volume, metadata = load_image_volume(path, modality)
    index, rule = foreground_slice(volume, slice_index, positive_only=True)
    try:
        arrays = _anatomical_arrays(volume, index, max_size)
    except ValueError:
        # An in-range preferred slice may still lack interior support after resize.
        fallback, fallback_rule = foreground_slice(volume, positive_only=True)
        if fallback == index:
            raise
        index, rule = fallback, "slice71 unusable for fixed interior mask; " + fallback_rule
        arrays = _anatomical_arrays(volume, index, max_size)
    fixed, moving, bounds, truth, mask, landmarks, high, factor = arrays
    metadata.update(slice_index=int(index), slice_axis=2, slice_selection_rule=rule,
                    evaluation_shape=list(fixed.shape), resize_factor=factor,
                    positive_percentile_99_5=high, truth_pull_parameters=truth.tolist(),
                    pixel_mask_count=int(mask.sum()),
                    fixed_mask="circular interior safe for bounds, intersected with fixed>0",
                    intensity_normalisation="clip(raw / finite positive-pixel 99.5th percentile,0,1)",
                    limitation="anatomical slice with synthetic rigid perturbation; not clinical patient registration")
    return fixed, moving, bounds, truth, mask, landmarks, metadata


def load_noise_case(path, modality=0):
    volume, metadata = load_image_volume(path, modality)
    normalized, roi, preprocessing = imaging.preprocess_flair(volume)
    index, rule = foreground_slice(volume)
    metadata.update(slice_index=index, slice_axis=2, slice_selection_rule=rule,
                    preprocessing=preprocessing, evaluation_shape=list(normalized.shape[:2]),
                    clean_reference="known normalized uncorrupted input; synthetic study only",
                    clean_reference_used_by_optimizer=False)
    return normalized[:, :, index].copy(), roi[:, :, index].copy(), metadata


def corrupt_image(clean, roi, sigma, corruption_seed):
    if clean.ndim != 2 or roi.shape != clean.shape or not roi.any():
        raise ValueError("Corruption requires a 2D image with matching nonempty ROI")
    noise = np.zeros(clean.shape, dtype=np.float32)
    noise[roi] = np.random.default_rng(corruption_seed).normal(0, sigma, int(roi.sum()))
    noisy = np.zeros(clean.shape, dtype=np.float32)
    noisy[roi] = np.clip(clean[roi] + noise[roi], 0, 1)
    return noisy, noise


def contrast_prediction(noisy, roi, method, optimizer_seed, budget=BUDGET, population=POPULATION):
    """No clean reference argument: optimization sees only the noisy histogram."""
    histogram = imaging.image_histogram(noisy, roi)
    objective = imaging.enhancement_objective(histogram)
    result = optimise(objective, imaging.ENHANCEMENT_BOUNDS, method, optimizer_seed,
                      max_evals=budget, population=population)
    result["returned_x_objective"] = objective(result["x"])
    validate_result(result, budget)
    prediction = imaging.apply_enhancement(noisy, roi, result["x"])
    return prediction, result


def validate_result(result, budget):
    if result["evaluations"] != budget or len(result["history"]) != budget:
        raise AssertionError("Optimizer did not consume the declared objective budget")
    history = np.asarray(result["history"], dtype=float)
    if not np.array_equal(history[:, 0], np.arange(1, budget + 1)):
        raise AssertionError("Objective history has missing evaluation counts")
    if not np.isfinite(history[:, 1]).all() or np.any(np.diff(history[:, 1]) > 1e-12):
        raise AssertionError("Incumbent objective history is nonfinite or increases")
    if not np.isclose(result["fun"], result["returned_x_objective"], atol=1e-12, rtol=1e-10):
        raise AssertionError("Returned parameter vector and reported objective disagree")


def clean_reference_metrics(clean, prediction, roi):
    """Evaluate only after a prediction exists; all intensities use data_range=1."""
    mse = float(np.mean((clean[roi].astype(float) - prediction[roi]) ** 2))
    win = min(7, min(clean.shape))
    win -= int(win % 2 == 0)
    full_ssim = roi_ssim = eroded_ssim = None
    valid_count = 0
    if win >= 3:
        full_ssim, ssim_map = structural_similarity(clean, prediction, data_range=1.0,
                                                   win_size=win, full=True)
        roi_ssim = float(ssim_map[roi].mean())
        eroded = ndimage.binary_erosion(roi, structure=np.ones((win, win), bool))
        valid_count = int(eroded.sum())
        eroded_ssim = float(ssim_map[eroded].mean()) if valid_count else None
    return dict(clean_roi_mse=mse, clean_roi_psnr_db=float(-10 * np.log10(mse)) if mse else None,
                clean_psnr_infinite=mse == 0, clean_roi_ssim=roi_ssim,
                clean_foreground_eroded_ssim=eroded_ssim,
                clean_full_array_ssim=float(full_ssim) if full_ssim is not None else None,
                ssim_window_size=win if win >= 3 else None,
                ssim_eroded_foreground_pixels=valid_count,
                ssim_eroded_rule="complete square SSIM window must lie inside finite nonzero image ROI")


def gaussian_control(noisy, roi):
    """Fixed image-only Gaussian sigma1; preserve the original foreground ROI."""
    result = ndimage.gaussian_filter(noisy, sigma=GAUSSIAN_SIGMA_PIXELS, mode="reflect")
    return np.where(roi, result, 0).astype(np.float32)


def save_quality_panel(directory, tag, clean, noisy, predictions):
    images = [("Synthetic clean reference", clean), ("Noisy identity", noisy)]
    images += [("Gaussian sigma1", predictions["gaussian_sigma1"])]
    images += [(method, predictions[method]) for method in METHODS]
    fig, axes = plt.subplots(2, 4, figsize=(12, 6))
    for ax, (title, data) in zip(axes.ravel(), images):
        ax.imshow(data, cmap="gray", vmin=0, vmax=1)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    fig.suptitle(tag + "; contrast methods are not trained denoisers", fontsize=10)
    fig.tight_layout()
    fig.savefig(directory / f"{tag}_quality_panel.png", dpi=120)
    plt.close(fig)


def run_noise_case(case, output, records, budget=BUDGET, population=POPULATION):
    directory = Path(output) / "controlled_noise" / safe_tag(case["case_id"])
    directory.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    clean, roi, metadata = load_noise_case(case["image_path"], case["modality_index"])
    metadata.update(case, load_preprocessing_seconds=perf_counter() - started)
    imaging.write_json(directory / "case.json", metadata)
    for sigma in NOISE_SIGMAS:
        for corruption_seed in CORRUPTION_SEEDS:
            tag = f"sigma{sigma:.2f}_corruption{corruption_seed}"
            noisy, noise = corrupt_image(clean, roi, sigma, corruption_seed)
            weights, centres = imaging.image_histogram(noisy, roi)
            np.savez_compressed(directory / f"{tag}_corruption.npz", clean=clean, noisy=noisy,
                                additive_gaussian_noise_before_clipping=noise, roi=roi)
            corruption = dict(case_id=case["case_id"], subject=case["subject"], sigma=sigma,
                              corruption_seed=corruption_seed,
                              noise_rule="independent zero-mean Gaussian within frozen image ROI, clipped [0,1]",
                              noise_generator="numpy.default_rng(corruption_seed)",
                              noise_before_clipping_mean=float(noise[roi].mean()),
                              noise_before_clipping_sd=float(noise[roi].std(ddof=1)),
                              noisy_clipped_zero_fraction=float(np.mean(noisy[roi] == 0)),
                              noisy_clipped_one_fraction=float(np.mean(noisy[roi] == 1)),
                              noisy_histogram_weights=weights, noisy_histogram_centres=centres,
                              objective="frozen -RMS contrast + 0.5 departure MSE + 0.05 saturation mass",
                              enhancement_bounds=imaging.ENHANCEMENT_BOUNDS,
                              reference_labels_accessed=False, clean_reference_used_by_optimizer=False)
            imaging.write_json(directory / f"{tag}_corruption.json", corruption)
            predictions = {}
            # Randomized method order is deterministic and independent of quality.
            for method in np.random.default_rng(corruption_seed + 1981).permutation(METHODS):
                method = str(method)
                prediction, result = contrast_prediction(noisy, roi, method, corruption_seed, budget, population)
                predictions[method] = prediction
                record = dict(case_id=case["case_id"], subject=case["subject"], session=case["session"],
                              sigma=sigma, corruption_seed=corruption_seed, optimizer_seed=corruption_seed,
                              seed_rule="distinct corruption/optimizer RNG roles share the prespecified integer",
                              method=method, evaluations=result["evaluations"], seconds=result["seconds"],
                              objective=result["fun"], returned_x_objective=result["returned_x_objective"],
                              parameters=result["x"], optimizer=result,
                              reference_labels_accessed=False, clean_reference_used_by_optimizer=False)
                # Persist the prediction before clean-reference evaluation.
                stem = directory / f"{tag}_{method}"
                np.savez_compressed(str(stem) + "_prediction.npz", prediction=prediction)
                imaging.write_json(str(stem) + "_prediction_record.json", record)
                imaging.write_csv(str(stem) + "_convergence.csv",
                                  [dict(evaluation=h[0], best_objective=h[1]) for h in result["history"]])
                record.update(clean_reference_metrics(clean, prediction, roi),
                              evaluation_after_prediction_saved=True)
                imaging.write_json(str(stem) + "_evaluated.json", record)
                records.append(record)
            for method in ("noisy_identity", "gaussian_sigma1"):
                started = perf_counter()
                prediction = noisy.copy() if method == "noisy_identity" else gaussian_control(noisy, roi)
                seconds = perf_counter() - started
                predictions[method] = prediction
                stem = directory / f"{tag}_{method}"
                np.savez_compressed(str(stem) + "_prediction.npz", prediction=prediction)
                record = dict(case_id=case["case_id"], subject=case["subject"], session=case["session"],
                              sigma=sigma, corruption_seed=corruption_seed, optimizer_seed=None,
                              method=method, evaluations=0, seconds=seconds, objective=None,
                              parameters={"sigma_pixels": GAUSSIAN_SIGMA_PIXELS, "boundary": "reflect"}
                              if method == "gaussian_sigma1" else {}, reference_labels_accessed=False,
                              clean_reference_used_by_optimizer=False,
                              evaluation_after_prediction_saved=True,
                              **clean_reference_metrics(clean, prediction, roi))
                imaging.write_json(str(stem) + "_evaluated.json", record)
                records.append(record)
            save_quality_panel(directory, tag, clean, noisy, predictions)
            print(f"noise {case['case_id']} sigma={sigma} corruption_seed={corruption_seed} completed", flush=True)


def noise_reports(output, records):
    directory = Path(output) / "controlled_noise"
    flat = [{key: value for key, value in record.items()
             if key not in ("optimizer", "parameters")} for record in records]
    frame = pd.DataFrame(flat)
    frame.to_csv(directory / "runs.csv", index=False)
    metrics = ["clean_roi_psnr_db", "clean_roi_ssim", "clean_foreground_eroded_ssim", "seconds", "objective"]
    per_case = frame.groupby(["case_id", "subject", "sigma", "method"])[metrics].agg(["mean", "std", "count"])
    per_case.columns = ["_".join(column) for column in per_case.columns]
    per_case = per_case.reset_index()
    per_case.to_csv(directory / "per_subject_corruption_summary.csv", index=False)
    means = [metric + "_mean" for metric in metrics]
    across = per_case.groupby(["sigma", "method"])[means].agg(["mean", "std", "count"])
    across.columns = ["_".join(column) for column in across.columns]
    across.reset_index().to_csv(directory / "across_subject_summary.csv", index=False)
    paired = []
    for baseline in ("noisy_identity", "gaussian_sigma1"):
        controls = frame[frame.method == baseline].set_index(["case_id", "sigma", "corruption_seed"])
        for record in flat:
            if record["method"] not in METHODS:
                continue
            control = controls.loc[(record["case_id"], record["sigma"], record["corruption_seed"])]
            row = {key: record[key] for key in ("case_id", "subject", "sigma", "corruption_seed", "method")}
            row["comparison"] = baseline
            for metric in metrics[:3]:
                row[metric + "_difference"] = (record[metric] - float(control[metric])
                                               if record[metric] is not None and pd.notna(control[metric]) else None)
            paired.append(row)
    pd.DataFrame(paired).to_csv(directory / "paired_quality_differences.csv", index=False)
    for (case_id, sigma), group in frame.groupby(["case_id", "sigma"]):
        fig, ax = plt.subplots(figsize=(7, 4))
        for method in METHODS:
            histories = [r["optimizer"]["history"] for r in records
                         if r["case_id"] == case_id and r["sigma"] == sigma and r["method"] == method]
            values = np.asarray(histories, float)[:, :, 1]
            ax.plot(np.arange(1, values.shape[1] + 1), values.mean(axis=0), label=method)
        ax.set(xlabel="Counted objective evaluations", ylabel="Frozen contrast objective",
               title=f"{case_id}: Gaussian sigma {sigma}; mean of 3 corruption replicates")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(directory / f"{safe_tag(case_id)}_sigma{sigma:.2f}_convergence.png", dpi=120)
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, metric in zip(axes, metrics[:2]):
        for method in tuple(METHODS) + ("noisy_identity", "gaussian_sigma1"):
            selected = per_case[per_case.method == method].groupby("sigma")[metric + "_mean"].agg(["mean", "std"])
            ax.errorbar(selected.index, selected["mean"], yerr=selected["std"], marker="o", label=method)
        ax.set(xlabel="Gaussian noise standard deviation", ylabel=metric,
               title="Subject means; error bars are SD over 3 subjects")
    axes[-1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(directory / "quality_summary.png", dpi=140)
    plt.close(fig)


def registration_reports(output, rows):
    directory = Path(output) / "registration"
    frame = pd.DataFrame(rows)
    frame.to_csv(directory / "runs.csv", index=False)
    metrics = ["objective", "seconds", "grid_landmark_rmse_pixels"]
    summary = frame.groupby(["case_id", "subject", "method"])[metrics].agg(["mean", "std", "count"])
    summary.columns = ["_".join(column) for column in summary.columns]
    summary = summary.reset_index()
    summary.to_csv(directory / "per_subject_seed_summary.csv", index=False)
    across = summary.groupby("method")[[metric + "_mean" for metric in metrics]].agg(["mean", "std", "count"])
    across.columns = ["_".join(column) for column in across.columns]
    across.reset_index().to_csv(directory / "across_subject_summary.csv", index=False)
    for case_id, group in frame.groupby("case_id"):
        fig, ax = plt.subplots(figsize=(7, 4))
        for method in METHODS:
            histories = [json.loads(Path(path).read_text(encoding="utf-8"))["history"]
                         for path in group.loc[group.method == method, "result_file"]]
            values = np.asarray(histories, float)[:, :, 1]
            ax.plot(np.arange(1, values.shape[1] + 1), values.mean(axis=0), label=method)
        ax.set(xlabel="Counted objective evaluations", ylabel="MSE on fixed interior foreground",
               title=f"{case_id}: known rigid perturbation; mean of 5 optimizer seeds")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(directory / f"{safe_tag(case_id)}_convergence.png", dpi=120)
        plt.close(fig)


def run(args):
    manifest_path, output = Path(args.manifest).resolve(), Path(args.output).resolve()
    selected = select_cases(json.loads(manifest_path.read_text(encoding="utf-8")), manifest_path, args.subjects)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use a fresh output directory; prior results are never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    (output / "registration").mkdir()
    started = perf_counter()
    protocol = dict(protocol_version=PROTOCOL_VERSION, status="running", manifest=str(manifest_path),
                    manifest_sha256=imaging.sha256(manifest_path), selected_cases=selected,
                    subject_selection="first 3 numeric subject IDs, earliest numeric session per subject",
                    methods=list(METHODS), objective_evaluations=BUDGET, population=POPULATION,
                    registration_seeds=list(REGISTRATION_SEEDS), registration_max_size=128,
                    registration_preferred_axis2_slice=71, noise_sigmas=list(NOISE_SIGMAS),
                    corruption_seeds=list(CORRUPTION_SEEDS), noise_optimizer_seeds=list(CORRUPTION_SEEDS),
                    gaussian_control_sigma_pixels=GAUSSIAN_SIGMA_PIXELS,
                    reference_labels_accessed=False, clean_reference_used_by_optimizer=False,
                    training="none", python=sys.version, platform=platform.platform(),
                    code_sha256={p.name: imaging.sha256(p) for p in
                                 (Path(__file__), Path(imaging.__file__), Path(registration.__file__),
                                  Path(__file__).with_name("optimizers.py"))},
                    interpretation="Controlled 2D image-only stress studies; no clinical registration/denoising claim",
                    statistical_units="Within-subject seed/corruption means, then SD over subjects; seeds are not patients")
    imaging.write_json(output / "run_manifest.json", protocol)
    registration_rows, noise_records = [], []
    try:
        for case in selected:
            load_started = perf_counter()
            fixed, moving, bounds, truth, mask, points, metadata = load_anatomical_case(
                case["image_path"], modality=case["modality_index"])
            metadata.update(case, load_preprocessing_seconds=perf_counter() - load_started)
            task = "anatomical_" + safe_tag(case["case_id"])
            rows = registration.run_matched_case(output / "registration", task, fixed, moving,
                bounds, REGISTRATION_SEEDS, BUDGET, POPULATION, registration.rigid_warp,
                mask, truth, points, metadata)
            for row in rows:
                result = json.loads(Path(row["result_file"]).read_text(encoding="utf-8"))
                validate_result(result, BUDGET)
                row.update(case_id=case["case_id"], subject=case["subject"], session=case["session"],
                           reference_labels_accessed=False)
            registration_rows.extend(rows)
        registration_reports(output, registration_rows)
        for case in selected:
            run_noise_case(case, output, noise_records, budget=BUDGET, population=POPULATION)
        noise_reports(output, noise_records)
        expected_reg = len(selected) * len(METHODS) * len(REGISTRATION_SEEDS)
        expected_noise = len(selected) * len(NOISE_SIGMAS) * len(CORRUPTION_SEEDS) * (len(METHODS) + 2)
        if len(registration_rows) != expected_reg or len(noise_records) != expected_noise:
            raise AssertionError("Study completion counts disagree with prespecified design")
        protocol.update(status="completed", registration_runs=len(registration_rows), noise_runs=len(noise_records),
                        completed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        total_seconds_including_io_metrics_reports=perf_counter() - started)
        (output / "README.md").write_text(
            "# External image-only stress studies\n\n"
            "Registration is a known synthetic rigid perturbation of anatomical MRI slices; geometric grid-landmark "
            "RMSE is in pixels and is not clinical TRE. Noise references are the known normalized uncorrupted images. "
            "Gaussian corruption is not a clinical noisy/clean pair. Segmentation labels are never read.\n\n"
            "The primary histogram contrast objective and optimizer defaults were frozen. Clean-reference PSNR/SSIM "
            "are independent postprediction endpoints; lower quality after contrast adjustment must be reported "
            "without selecting favorable subjects or noise realizations. Noisy identity and fixed Gaussian sigma1 "
            "are separately named controls.\n\n"
            "runs.csv retains individual measurements. Per-subject tables summarize repeated RNG runs first; "
            "across-subject tables use three distinct subjects as observational units. Full histories, prediction "
            "arrays, corruption arrays and static panels are retained. These small controlled studies support no "
            "clinical accuracy or optimizer superiority conclusion.\n", encoding="utf-8")
    except Exception as exc:
        protocol.update(status="failed", error=f"{type(exc).__name__}: {exc}",
                        completed_registration_runs=len(registration_rows), completed_noise_runs=len(noise_records))
        imaging.write_json(output / "run_manifest.json", protocol)
        raise
    imaging.write_json(output / "run_manifest.json", protocol)
    print(json.dumps(dict(status="completed", registration_runs=len(registration_rows),
                          noise_runs=len(noise_records), output=str(output))), flush=True)
    return protocol


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--subjects", type=int, default=3, choices=[3])
    return result


if __name__ == "__main__":
    run(parser().parse_args())
