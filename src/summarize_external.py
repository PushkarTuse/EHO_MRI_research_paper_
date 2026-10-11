"""Patient-level external lesion statistics, claim audit and local results dashboard.

Reads compact CSV measurements, never cohort convergence histories. The primary
cohort is each patient's earliest numeric session from the prespecified manifest,
even if that session has failed or is not yet available. Later sessions cannot
silently replace missing primary observations. Session and RNG counts are never
represented as independent patient counts.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

PRIMARY_STUDY = "primary_largest_6_connected_component"
SECONDARY_STUDY = "prespecified_secondary_all_components"
BOOTSTRAP_SEED = 20261011
BOOTSTRAP_RESAMPLES = 5000
PRIMARY_ANALYSIS = "earliest_numeric_session_per_patient"
LONGITUDINAL_ANALYSIS = "all_available_sessions_mean_within_patient"
QUALITY_METRICS = ("dice_lesion", "iou_lesion", "precision_lesion", "recall_lesion", "prediction_ml", "reference_ml")
RESOURCE_METRICS = ("enhancement_seconds", "segmentation_seconds", "enhancement_sampled_peak_rss_mb", "segmentation_sampled_peak_rss_mb")
BASELINES = ("direct_otsu", "original_eho", "pso", "ga", "acor")


def clean_json(value):
    if isinstance(value, dict):
        return {str(key): clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(clean_json(value), indent=2, allow_nan=False), encoding="utf-8")


def numeric_session(value):
    text = str(value)
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if len(numbers) != 1:
        raise ValueError(f"Session identifier must contain exactly one numeric timepoint: {value!r}")
    return float(numbers[0])


def earliest_cases(cases):
    earliest = {}
    identifiers = set()
    for case in cases:
        identifier = str(case["case_id"])
        if identifier in identifiers:
            raise ValueError("Duplicate manifest case ID")
        identifiers.add(identifier)
        subject = str(case.get("subject_id", case.get("subject", "")))
        if not subject:
            raise ValueError("Manifest must declare native subject_id")
        session = str(case.get("session_id", case.get("session", "")))
        candidate = {**case, "case_id": identifier, "subject_id": subject, "session_id": session,
                     "numeric_session": numeric_session(session)}
        previous = earliest.get(subject)
        if previous is None or (candidate["numeric_session"], identifier) < (previous["numeric_session"], previous["case_id"]):
            earliest[subject] = candidate
    return earliest


def bootstrap_mean(values, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return {"n_patients": 0, "mean": None, "sd": None, "median": None, "ci95_low": None, "ci95_high": None}
    indexes = np.random.default_rng(seed).integers(0, len(values), size=(resamples, len(values)))
    means = values[indexes].mean(axis=1)
    low, high = np.quantile(means, [.025, .975])
    return {"n_patients": len(values), "mean": float(values.mean()), "sd": float(values.std(ddof=1)) if len(values) > 1 else None,
            "median": float(np.median(values)), "ci95_low": float(low), "ci95_high": float(high)}


def paired_stats(candidate, baseline, resamples=BOOTSTRAP_RESAMPLES):
    candidate, baseline = np.asarray(candidate, float), np.asarray(baseline, float)
    if candidate.shape != baseline.shape:
        raise ValueError("Paired endpoints must have equal shape")
    valid = np.isfinite(candidate) & np.isfinite(baseline)
    difference = candidate[valid] - baseline[valid]
    summary = bootstrap_mean(difference, resamples=resamples)
    summary["difference_direction"] = "candidate minus baseline"
    summary["median_paired_difference"] = float(np.median(difference)) if len(difference) else None
    summary["positive_pairs"] = int(np.count_nonzero(difference > 0))
    summary["negative_pairs"] = int(np.count_nonzero(difference < 0))
    summary["tied_pairs"] = int(np.count_nonzero(difference == 0))
    if not len(difference):
        summary["wilcoxon_two_sided_p"] = None
    elif np.all(difference == 0):
        summary["wilcoxon_two_sided_p"] = 1.
    else:
        summary["wilcoxon_two_sided_p"] = float(wilcoxon(difference, alternative="two-sided", zero_method="wilcox", method="auto").pvalue)
    return summary


def holm_adjust(pvalues, family_size=None):
    values = list(pvalues)
    finite = [index for index, value in enumerate(values) if value is not None and np.isfinite(value)]
    ordered = sorted(finite, key=lambda index: values[index])
    size = len(ordered) if family_size is None else int(family_size)
    if size < len(ordered):
        raise ValueError("Holm family size cannot be smaller than the observed comparisons")
    adjusted = [None] * len(values)
    previous = 0.
    for rank, index in enumerate(ordered):
        previous = max(previous, min(1., values[index] * (size - rank)))
        adjusted[index] = previous
    return adjusted


def load_measurements(run, manifest):
    metadata = json.loads(Path(manifest).read_text(encoding="utf-8"))
    cases = metadata["cases"]
    selection = earliest_cases(cases)
    frame = pd.read_csv(Path(run) / "all_runs.csv", dtype={"case_id": str, "subject_id": str, "session_id": str, "partition": str})
    required = {"case_id", "subject_id", "session_id", "partition", "method", "seed", "study", *QUALITY_METRICS}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError("all_runs.csv missing required fields: " + ", ".join(sorted(missing)))
    identifiers = {str(case["case_id"]) for case in cases}
    if not set(frame.case_id).issubset(identifiers):
        raise ValueError("Measured case ID absent from prespecified manifest")
    if frame.duplicated(["study", "case_id", "method", "seed"]).any():
        raise ValueError("Duplicate study/case/method/seed measurement")
    lookup = {str(case["case_id"]): case for case in cases}
    for row in frame[["case_id", "subject_id", "session_id"]].drop_duplicates().itertuples(index=False):
        case = lookup[row.case_id]
        if row.subject_id != str(case.get("subject_id", case.get("subject"))) or row.session_id != str(case.get("session_id", case.get("session"))):
            raise ValueError("Measurement subject/session identity differs from manifest")
    config_path = Path(run) / "run_manifest.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    expected_methods = config.get("methods", ["original_eho", "modified_eho", "pso", "ga", "acor"])
    expected_seeds = set(config.get("seeds", [0, 1, 2]))
    primary = frame[frame.study == PRIMARY_STUDY]
    complete_cases = []
    incomplete = []
    for identifier in sorted(set(primary.case_id)):
        group = primary[primary.case_id == identifier]
        errors = []
        for method in expected_methods + ["direct_otsu"]:
            actual = set(group.loc[group.method == method, "seed"].astype(int))
            expected = {0} if method == "direct_otsu" else expected_seeds
            if actual != expected:
                errors.append(method + " seed coverage")
        if errors:
            incomplete.append({"case_id": identifier, "missing": errors})
        else:
            complete_cases.append(identifier)
    frame = frame[frame.case_id.isin(complete_cases)].copy()
    secondary_incomplete = []
    secondary_complete = []
    for identifier in complete_cases:
        group = frame[(frame.case_id == identifier) & (frame.study == SECONDARY_STUDY)]
        errors = []
        secondary_methods = [method for method in ("modified_eho", "direct_otsu") if method in expected_methods or method == "direct_otsu"]
        for method in secondary_methods:
            actual = set(group.loc[group.method == method, "seed"].astype(int))
            expected = {0} if method == "direct_otsu" else expected_seeds
            if actual != expected:
                errors.append(method + " secondary seed coverage")
        if errors:
            secondary_incomplete.append({"case_id": identifier, "missing": errors})
        else:
            secondary_complete.append(identifier)
    frame = frame[(frame.study != SECONDARY_STUDY) | frame.case_id.isin(secondary_complete)].copy()
    reference_counts = frame[frame.study == PRIMARY_STUDY].groupby("case_id").reference_ml.mean()
    empty_reference_cases = sorted(reference_counts.index[reference_counts == 0].tolist())
    coverage = {"manifest_sessions": len(cases), "manifest_patients": len(selection), "completed_sessions": len(complete_cases),
                "completed_patients_with_any_session": frame.subject_id.nunique(), "incomplete_case_seed_coverage": incomplete,
                "missing_primary_patients": sorted(subject for subject, case in selection.items() if case["case_id"] not in complete_cases),
                "primary_cases": {subject: case["case_id"] for subject, case in sorted(selection.items())},
                "missing_or_unmeasured_sessions": sorted(identifiers.difference(complete_cases)),
                "completed_secondary_sessions": len(secondary_complete), "secondary_incomplete_case_seed_coverage": secondary_incomplete,
                "empty_reference_sessions": empty_reference_cases,
                "empty_reference_primary_patients": sorted(subject for subject, case in selection.items() if case["case_id"] in empty_reference_cases),
                "cohort_complete": len(complete_cases) == len(cases)}
    return frame, metadata, selection, coverage, config


def patient_values(frame, selection):
    metrics = [metric for metric in QUALITY_METRICS + RESOURCE_METRICS if metric in frame.columns]
    identifiers = ["study", "case_id", "subject_id", "session_id", "partition", "method"]
    sessions = frame.groupby(identifiers, dropna=False)[metrics].mean().reset_index()
    selected_ids = {case["case_id"] for case in selection.values()}
    primary = sessions[sessions.case_id.isin(selected_ids)].copy()
    primary["analysis"] = PRIMARY_ANALYSIS
    primary["n_sessions"] = 1
    all_sessions = sessions.groupby(["study", "subject_id", "method"], dropna=False)[metrics].mean().reset_index()
    counts = sessions.groupby(["study", "subject_id", "method"], dropna=False).size().rename("n_sessions").reset_index()
    all_sessions = all_sessions.merge(counts, on=["study", "subject_id", "method"])
    all_sessions["analysis"] = LONGITUDINAL_ANALYSIS
    return pd.concat([primary, all_sessions], ignore_index=True), sessions


def summarize_patients(values):
    summaries = []
    metrics = [metric for metric in QUALITY_METRICS + RESOURCE_METRICS if metric in values.columns]
    for (analysis, study, method), group in values.groupby(["analysis", "study", "method"]):
        for metric in metrics:
            summaries.append({"analysis": analysis, "study": study, "method": method, "metric": metric,
                              **bootstrap_mean(group[metric]), "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
                              "bootstrap_seed": BOOTSTRAP_SEED, "bootstrap_unit": "patient",
                              "n_patient_observations_available": len(group), "n_undefined_patient_endpoints": int(group[metric].isna().sum())})
    return summaries


def method_comparisons(values):
    comparisons = []
    for analysis in (PRIMARY_ANALYSIS, LONGITUDINAL_ANALYSIS):
        group = values[(values.analysis == analysis) & (values.study == PRIMARY_STUDY)]
        wide = group.pivot(index="subject_id", columns="method", values="dice_lesion")
        if "modified_eho" not in wide:
            continue
        family = []
        for baseline in BASELINES:
            if baseline not in wide:
                continue
            paired = wide[["modified_eho", baseline]].dropna()
            family.append({"analysis": analysis, "study": PRIMARY_STUDY, "metric": "dice_lesion", "candidate": "modified_eho",
                           "baseline": baseline, **paired_stats(paired.modified_eho, paired[baseline]),
                           "holm_family": "five prespecified primary Dice comparisons within " + analysis})
        adjusted = holm_adjust([row["wilcoxon_two_sided_p"] for row in family], family_size=len(BASELINES))
        for row, pvalue in zip(family, adjusted):
            row["holm_adjusted_p"] = pvalue
            row["holm_family_observed_comparisons"] = len(family)
            row["holm_family_complete"] = len(family) == len(BASELINES)
        comparisons.extend(family)
    return comparisons


def component_comparisons(values):
    comparisons = []
    for analysis in (PRIMARY_ANALYSIS, LONGITUDINAL_ANALYSIS):
        for method in ("modified_eho", "direct_otsu"):
            group = values[(values.analysis == analysis) & (values.method == method)]
            for metric in ("dice_lesion", "recall_lesion"):
                wide = group.pivot(index="subject_id", columns="study", values=metric)
                if PRIMARY_STUDY not in wide or SECONDARY_STUDY not in wide:
                    continue
                paired = wide[[PRIMARY_STUDY, SECONDARY_STUDY]].dropna()
                comparisons.append({"analysis": analysis, "method": method, "metric": metric,
                                    "candidate": SECONDARY_STUDY, "baseline": PRIMARY_STUDY,
                                    **paired_stats(paired[SECONDARY_STUDY], paired[PRIMARY_STUDY]),
                                    "interpretation": "prespecified component-rule ablation; secondary minus frozen primary; no favorable session reselection",
                                    "inference_role": "exploratory paired effect size; no confirmatory significance claim"})
    return comparisons


def read_ancillary(studies):
    results = {"status": "not supplied", "training": "none", "learned_model_comparison": "not measured", "files": [], "summaries": []}
    if studies is None:
        return results
    studies = Path(studies).resolve()
    results.update(status="available" if studies.exists() else "directory not available", root=str(studies))
    if not studies.exists():
        return results
    protocol_path = studies / "run_manifest.json"
    if protocol_path.exists():
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        results["run_status"] = protocol.get("status", "unspecified")
    for relative, kind, endpoints in (("registration/runs.csv", "registration", ("objective", "grid_landmark_rmse_pixels", "seconds")),
                                      ("controlled_noise/runs.csv", "controlled_noise", ("clean_roi_psnr_db", "clean_roi_ssim", "clean_foreground_eroded_ssim", "seconds"))):
        path = studies / relative
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        results["files"].append({"path": str(path), "kind": kind, "rows": len(frame), "columns": list(frame.columns)})
        subject_key = next((key for key in ("subject_id", "subject", "case_id") if key in frame.columns), None)
        if not subject_key or "method" not in frame:
            continue
        conditions = [key for key in ("sigma", "noise_sigma") if key in frame.columns]
        for group_key, group in frame.groupby(["method"] + conditions, dropna=False):
            group_key = group_key if isinstance(group_key, tuple) else (group_key,)
            condition = dict(zip(["method"] + conditions, group_key))
            for metric in endpoints:
                if metric not in group:
                    continue
                # RNG runs and corruptions are averaged within a subject first.
                subjects = group.groupby(subject_key)[metric].mean()
                results["summaries"].append({"study": kind, **condition, "metric": metric,
                                             **bootstrap_mean(subjects), "observational_unit": "subject mean across seed/corruption repetitions",
                                             "clinical_validation": False})
    if not results["files"]:
        results["status"] = "no completed measurement CSVs yet"
    return results


def format_number(value, digits=4):
    return "not available" if value is None or pd.isna(value) else f"{float(value):.{digits}g}"


def markdown_table(rows, keys):
    if not rows:
        return "No completed observations available.\n"
    rendered = ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for key in keys) + " |"]
    for row in rows:
        cells = []
        for key in keys:
            value = row.get(key)
            cells.append((format_number(value) if isinstance(value, (int, float)) or value is None else str(value)).replace("|", "/"))
        rendered.append("| " + " | ".join(cells) + " |")
    return "\n".join(rendered) + "\n"


def write_audit(output, statistics):
    coverage, summaries = statistics["coverage"], statistics["patient_metric_summaries"]
    primary_dice = [row for row in summaries if row["analysis"] == PRIMARY_ANALYSIS and row["study"] == PRIMARY_STUDY and row["metric"] == "dice_lesion"]
    primary_pairs = [row for row in statistics["paired_method_comparisons"] if row["analysis"] == PRIMARY_ANALYSIS]
    direct = next((row for row in primary_pairs if row["baseline"] == "direct_otsu"), None)
    lines = ["# External MRI lesion validation: measured claims audit", "",
             f"Dataset: {statistics['dataset'].get('dataset_name', statistics['dataset'].get('dataset', 'external manifest'))}. The manifest contains {coverage['manifest_sessions']} image series from {coverage['manifest_patients']} patients. Series are repeated sessions, not independent patients.", "",
             f"Completed imaging: {coverage['completed_sessions']} series. Primary patient observations use only the earliest numeric session selected from the entire manifest before outcomes are examined. {len(coverage['missing_primary_patients'])} primary patients are missing; later sessions are never substituted. Cohort complete: {coverage['cohort_complete']}.", "",
             "Training: none. Learned-model comparison: not measured. This is the frozen unsupervised FLAIR contrast/Otsu threshold baseline, not a learned lesion detector. Reference lesions are evaluated after all predictions for each case are saved. The independent saved-mask checks recompute native-grid overlap and confirm unchanged prediction checksums.", "",
             "Here native-grid evaluation means the unchanged grid of the supplied input file. MSLesSeg inputs are supplied after brain extraction and affine registration to the MNI152 template at 1 mm spacing. Reported mL values are volumes on that supplied registration grid, not native-acquisition lesion burden. No inverse acquisition transform or clinical lesion-burden validation was measured.", "",
             f"Empty expert-reference masks: {len(coverage['empty_reference_sessions'])} completed sessions and {len(coverage['empty_reference_primary_patients'])} earliest-session patients. Undefined precision/recall remain null; metric-specific n_patients and n_undefined_patient_endpoints record exclusions. No zero denominator is replaced with a favorable score except the declared both-empty Dice/IoU convention of one.", "",
             "## Primary patient-level lesion overlap", "",
             "Seeds are averaged within the earliest session; patients receive equal weight. SD is between patients. Mean confidence intervals use 5,000 patient bootstrap resamples with seed 20261011. These intervals describe this retrospective cohort; they do not establish clinical effectiveness.", "",
             markdown_table(primary_dice, ["method", "n_patients", "mean", "sd", "median", "ci95_low", "ci95_high"]),
             "## Prespecified paired comparisons", "",
             "Differences are modified EHO minus the named baseline on the same patients. The bootstrap confidence interval estimates the patient mean paired difference. The median paired difference and positive/negative/tied patient counts describe its distribution separately.", "",
             "The two-sided Wilcoxon signed-rank test uses ranks of nonzero difference magnitudes together with their signs. It is not a test of the mean paired difference. A location interpretation relies on the relevant symmetry/shift assumptions; a skewed difference distribution can have a negative mean and positive median, and the mean bootstrap interval can contain zero while the signed-rank test rejects. A p-value alone therefore establishes neither mean superiority nor mean inferiority.", "",
             "Wilcoxon uses zero_method=wilcox; all-zero differences have p=1. Holm correction uses the five prespecified Dice comparisons within each analysis, including a five-test multiplier when fewer comparisons are available. An incomplete five-comparison family is flagged in the CSV and must not be described as the full planned confirmatory family.", "",
             markdown_table(primary_pairs, ["baseline", "n_patients", "mean", "median_paired_difference", "positive_pairs", "negative_pairs", "tied_pairs", "ci95_low", "ci95_high", "wilcoxon_two_sided_p", "holm_adjusted_p"])]
    if direct:
        lines += ["", f"The observed modified-EHO minus direct-Otsu patient-mean Dice difference is {format_number(direct['mean'])}, with bootstrap 95% CI [{format_number(direct['ci95_low'])}, {format_number(direct['ci95_high'])}]. The paired median is {format_number(direct['median_paired_difference'])}; {direct['positive_pairs']} patients have positive differences, {direct['negative_pairs']} negative differences, and {direct['tied_pairs']} exact ties. Its Holm-adjusted two-sided Wilcoxon p-value is {format_number(direct['holm_adjusted_p'])}. These endpoints answer different questions; the signed-rank p-value does not establish the sign of the mean benefit."]
        if direct["mean"] is not None and direct["median_paired_difference"] is not None and direct["mean"] * direct["median_paired_difference"] < 0:
            lines += ["", "The mean and median point in opposite directions in this observed comparison. Larger losses can outweigh more frequent small gains in the mean. This distributional imbalance must be reported rather than resolved by selecting the favorable statistic."]
        if direct["ci95_low"] is not None and direct["ci95_low"] <= 0 <= direct["ci95_high"]:
            lines += ["", "The mean-difference bootstrap interval contains zero, so this analysis does not establish a direction for the patient mean Dice advantage at that interval level, regardless of the signed-rank p-value."]
    observed_dice_means = [row["mean"] for row in primary_dice if row["mean"] is not None]
    if observed_dice_means and max(observed_dice_means) <= .1:
        lines += ["", f"All measured primary method mean Dice values are at most 0.1 (observed range {format_number(min(observed_dice_means))}–{format_number(max(observed_dice_means))}). The absolute expert-lesion overlap is poor across these methods. Small paired differences do not turn this threshold pipeline into an effective lesion detector."]
    lines += ["", "## Repeated-session and component-rule sensitivity", "",
              "The separately labelled all-session analysis averages seeds within a session, sessions within a patient, then patients equally. It does not count 115 series as 115 people. It retains all available sessions, without favorable session selection.", "",
              "The prespecified all-components ablation changes only the component retention rule for modified EHO and direct Otsu. It is an additional experiment and does not replace the frozen largest-component primary result. Paired Dice/recall effects appear below; significance is exploratory and does not select a new favorable protocol.", "",
              f"Secondary component-rule seed coverage is checked independently: {coverage['completed_secondary_sessions']} complete secondary sessions; {len(coverage['secondary_incomplete_case_seed_coverage'])} incomplete secondary sessions are excluded from secondary comparisons without altering complete primary observations.", "",
              markdown_table([row for row in statistics["component_ablation_comparisons"] if row["analysis"] == PRIMARY_ANALYSIS], ["method", "metric", "n_patients", "mean", "ci95_low", "ci95_high"]),
              "## Processing time and memory", "",
              "Enhancement and segmentation wall times are measured CPU processing stages; they exclude caller saving, reference evaluation, and mesh export. The deterministic Otsu path omits enhancement. Observed process RSS is sampled every 50 ms and includes imported libraries and image arrays. It is neither GPU memory nor an exact allocation peak. Patient-level summaries of available time/RSS columns are in patient_metric_summary.csv; case manifests retain loading and total I/O/evaluation/mesh resources. No real-time or deployment claim follows from these measurements.", "",
              "Primary imaging budgets count exactly 1,500 optimizer objective calls per stage, including initialization. Ancillary registration and noisy-contrast optimization each count 1,500 search objective calls plus one separate postsearch returned-candidate verification call; registration also makes one known-transform calibration call per case. These are additional checks outside the counted optimizer budget, not 1,500 total objective executions. Timing endpoints describe their recorded processing paths and are not interchangeable with image loading, saving or rendering time.", "",
              "## Frozen SSIM mask qualification", "",
              "The inherited primary appearance_metrics implementation uses binary_erosion with the default cross structuring element repeated win_size//2 times. For a 7-pixel SSIM window this gives a diamond-shaped erosion, not erosion by the complete 7×7 square. Its saved roi_ssim_rule text therefore overstates complete-window containment: pixels near corners of foreground boundaries may contribute SSIM windows containing background. Frozen primary values are preserved and this limitation is disclosed here. Whole-slice SSIM also includes background. The ancillary controlled-noise clean_foreground_eroded_ssim uses an explicit square-window erosion and has a distinct metric definition.", "",
              "## Relationship to the earlier tumour experiment", "",
              "The earlier BraTS reconstruction had mean whole-tumour Dice 0.736661 for modified EHO and 0.752200 for direct Otsu across three patients. These are tumour/oedema results from a different dataset and pathology. External MS lesion endpoints are reported separately and are never pooled with those three cases. Fresh external measurements cannot substantiate unknown historical MRI objectives, manually entered plot scores, or clinical claims.", "",
              "## Manuscript claim checks", "",
              "| Claim | What the measured experiment supports | Remaining limit |",
              "| --- | --- | --- |",
              "| Enhancement quality / anatomical preservation | Input-versus-enhanced PSNR/SSIM describe departure from the same normalized input. Supplied MNI-grid geometry is preserved. | A clean clinical denoising reference and diagnostic quality assessment were not supplied. Identity can maximize input similarity; inherited ROI-SSIM has the erosion limitation described above. |",
              "| Robust detection / localization | Native-grid expert lesion overlap and the prespecified component ablation quantify this external retrospective cohort. | Highest-intensity threshold masks and the largest-component rule are exploratory hypotheses; no clinical detector or surgical validation was measured. |",
              "| Optimizer superiority | Equal counted objective budgets and paired patient Dice comparisons can support only the observed task-specific differences. | Histogram-objective convergence alone does not establish lesion overlap superiority or general superiority. |",
              "| Anatomical registration robustness | Available known rigid-perturbation studies measure MSE and geometric grid displacement. | A synthetic transform on one MRI slice is not independent patient-to-patient or clinical registration accuracy. |",
              "| Noise suppression | Available controlled Gaussian-corruption studies compare postprediction quality with the uncorrupted normalized image. | Simulated corruption is not a clinical noisy/clean acquisition pair, and a contrast transform is not a trained denoiser. |", "",
              "## Ancillary image-only studies", "", f"Availability: {statistics['ancillary_studies']['status']}.", "",
              markdown_table(statistics["ancillary_studies"]["summaries"], ["study", "method", "sigma", "metric", "n_patients", "mean", "sd", "ci95_low", "ci95_high"]),
              "Known-transform registration and simulated-noise experiments remain separately identified. Missing studies are not assigned values. Their RNG repetitions are averaged within subjects before across-subject summaries.", "",
              "## Files", "", "Open VIEW_EXTERNAL_RESULTS.html for every manifest case and its saved interactive prediction/reference view. primary_patient_values.csv, patient_metric_summary.csv, paired_method_comparisons.csv, component_ablation_comparisons.csv and statistics.json provide the machine-readable results."]
    (output / "EXTERNAL_CLAIMS_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def local_link(target, output):
    return quote(Path(os.path.relpath(Path(target).resolve(), Path(output).resolve())).as_posix(), safe="/")


def make_dashboard(run, output, metadata, sessions, selection, statistics):
    case_values = {}
    for row in sessions[sessions.study == PRIMARY_STUDY].to_dict("records"):
        case_values.setdefault(row["case_id"], {})[row["method"]] = {key: clean_json(row.get(key)) for key in QUALITY_METRICS + RESOURCE_METRICS}
    selected_ids = {case["case_id"] for case in selection.values()}
    rows = []
    data = []
    for case in sorted(metadata["cases"], key=lambda row: (str(row.get("subject_id", "")), numeric_session(row.get("session_id", "")), row["case_id"])):
        identifier = str(case["case_id"])
        folder = run / identifier
        interactive = folder / "meshes/interactive_prediction_reference.html"
        status = "ready" if (folder / "case_completed.json").exists() and identifier in case_values else "pending or failed"
        links = [f'<a href="{html.escape(local_link(interactive, output))}" target="_blank">3D prediction / reference{(" (pending)" if not interactive.exists() else "")}</a>']
        preview = folder / "meshes/prediction_reference_preview.png"
        if preview.exists():
            links.append(f'<a href="{html.escape(local_link(preview, output))}" target="_blank">Preview</a>')
        slices = sorted(folder.glob("modified_eho_slice_*.png"))
        for file in slices:
            links.append(f'<a href="{html.escape(local_link(file, output))}" target="_blank">Slice {html.escape(file.stem.rsplit("_", 1)[-1])}</a>')
        item = {"case_id": identifier, "subject_id": str(case.get("subject_id", "")), "session_id": str(case.get("session_id", "")),
                "partition": str(case.get("partition", "")), "primary": identifier in selected_ids, "status": status,
                "methods": case_values.get(identifier, {})}
        data.append(item)
        fields = [item["case_id"], item["subject_id"], item["session_id"], item["partition"], "yes" if item["primary"] else "no", status]
        cells = "".join('<td>' + html.escape(field) + '</td>' for field in fields)
        cells += ''.join('<td class="metric" data-metric="' + metric + '"></td>' for metric in ("dice_lesion", "recall_lesion", "precision_lesion", "prediction_ml"))
        rows.append(f'<tr data-index="{len(data)-1}">{cells}<td class="links">' + ' · '.join(links) + '</td></tr>')
    methods = sorted({method for case in data for method in case["methods"]})
    method_options = ''.join(f'<option value="{html.escape(method)}"{" selected" if method == "modified_eho" else ""}>{html.escape(method)}</option>' for method in methods)
    coverage = statistics["coverage"]
    summary_rows = [row for row in statistics["patient_metric_summaries"] if row["analysis"] == PRIMARY_ANALYSIS and row["study"] == PRIMARY_STUDY and row["metric"] == "dice_lesion"]
    summary_html = ''.join('<tr>' + ''.join('<td>'+html.escape(str(row.get(key)) if key in ("method", "n_patients") else format_number(row.get(key)))+'</td>' for key in ("method", "n_patients", "mean", "sd", "ci95_low", "ci95_high"))+'</tr>' for row in summary_rows)
    payload = json.dumps(clean_json(data), allow_nan=False).replace("<", "\\u003c")
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>External MRI lesion results</title><style>
body{font:15px system-ui,sans-serif;max-width:1550px;margin:32px auto;padding:0 24px;background:#f5f7fb;color:#1a283e}h1{font-size:30px;margin-bottom:8px}.lead{max-width:1000px;line-height:1.65}.cards{display:flex;flex-wrap:wrap;gap:14px;margin:24px 0}.card{background:white;border:1px solid #d9e1ed;border-radius:10px;padding:16px 24px;min-width:170px}.card strong{display:block;font-size:28px;color:#143c71}.card span{color:#54647a}.panel{background:white;border:1px solid #d9e1ed;border-radius:10px;padding:20px;margin:20px 0;overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #e4e9f0;vertical-align:top}th{background:#e9eff8;color:#143c71;white-space:nowrap}td.metric{text-align:right}.controls{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin:12px 0}input,select{padding:9px;border:1px solid #b8c7db;border-radius:6px;font:inherit}button{font:inherit;background:none;color:inherit;border:0;padding:0;cursor:pointer}a{color:#135cad}small,.note{color:#54647a;line-height:1.6}.links{min-width:260px}#caseTable tbody tr:nth-child(even){background:#fafcff}</style>
<h1>External MRI lesion results</h1><p class="lead">Frozen image-only FLAIR threshold predictions evaluated against separate expert lesion references. The primary analysis uses each patient's earliest numeric session. Seeds and repeated sessions are averaged within patients.</p>
<div class="cards"><div class="card"><strong>MANIFEST_PATIENTS</strong><span>independent manifest patients</span></div><div class="card"><strong>MANIFEST_SESSIONS</strong><span>total image series</span></div><div class="card"><strong>COMPLETED_SESSIONS</strong><span>completed series</span></div><div class="card"><strong>MISSING_PRIMARY</strong><span>missing primary patients</span></div></div>
<p class="note">Training: none. Learned-model comparison: not measured. Blue surfaces in each 3D view are the supplied reference, not an algorithm prediction. References are displayed at native stride one; prediction display may use stride two. All overlap metrics use unchanged input-file masks. MSLesSeg inputs are supplied on a preprocessed MNI152 registration grid; mL values describe that supplied grid, not native-acquisition lesion burden. Earlier three-patient BraTS Dice means (modified EHO 0.736661, direct Otsu 0.752200) concern a different tumour pathology and are not pooled here.</p>
<div class="panel"><h2>Primary patient Dice</h2><p class="note">Equal-weight patients; 5,000 patient bootstrap resamples, seed 20261011. SD is between patients.</p><table><thead><tr><th>Method</th><th>Patients</th><th>Mean</th><th>SD</th><th>95% CI low</th><th>95% CI high</th></tr></thead><tbody>SUMMARY_ROWS</tbody></table>
<p><a href="EXTERNAL_CLAIMS_AUDIT.md">Claims audit</a> · <a href="statistics.json">Statistics JSON</a> · <a href="patient_metric_summary.csv">Patient summaries CSV</a> · <a href="paired_method_comparisons.csv">Paired comparisons CSV</a> · <a href="component_ablation_comparisons.csv">Component ablation CSV</a></p></div>
<div class="panel"><h2>All manifest cases</h2><div class="controls"><label>Find <input id="filter" placeholder="Case, patient, session, partition"></label><label>Metric method <select id="method">METHOD_OPTIONS</select></label><label><input type="checkbox" id="primaryOnly"> Earliest sessions only</label><span id="count"></span></div>
<p class="note">Case values are seed means for the frozen primary component rule. Every manifest case has its own 3D-view link; pending links become available when the case finishes. Click any column heading to sort.</p>
<table id="caseTable"><thead><tr>HEADERS</tr></thead><tbody>CASE_ROWS</tbody></table></div>
<script>const cases=CASE_DATA;const table=document.getElementById('caseTable');let sortColumn=-1,sortAscending=true;
function update(){const method=document.getElementById('method').value,query=document.getElementById('filter').value.toLowerCase(),only=document.getElementById('primaryOnly').checked;let visible=0;for(const row of table.tBodies[0].rows){const item=cases[Number(row.dataset.index)];const text=[item.case_id,item.subject_id,item.session_id,item.partition,item.status].join(' ').toLowerCase();row.hidden=!text.includes(query)||(only&&!item.primary);if(!row.hidden)visible++;for(const cell of row.querySelectorAll('.metric')){const value=(item.methods[method]||{})[cell.dataset.metric];cell.textContent=value==null?'—':Number(value).toFixed(cell.dataset.metric==='prediction_ml'?2:4);cell.dataset.sort=value==null?'':String(value);}}document.getElementById('count').textContent=visible+' of '+cases.length+' cases';}
for(const id of ['method','filter','primaryOnly'])document.getElementById(id).addEventListener(id==='filter'?'input':'change',update);
for(const [index,header] of Array.from(table.tHead.rows[0].cells).entries()){header.querySelector('button').addEventListener('click',()=>{sortAscending=index===sortColumn?!sortAscending:true;sortColumn=index;const rows=Array.from(table.tBodies[0].rows);rows.sort((a,b)=>{const x=a.cells[index].dataset.sort??a.cells[index].textContent,y=b.cells[index].dataset.sort??b.cells[index].textContent;if(x==='')return y===''?0:1;if(y==='')return -1;const numeric=x.trim()!==''&&y.trim()!==''&&Number.isFinite(Number(x))&&Number.isFinite(Number(y));const difference=numeric?Number(x)-Number(y):x.localeCompare(y,undefined,{numeric:true});return sortAscending?difference:-difference;});for(const row of rows)table.tBodies[0].appendChild(row);});}update();</script></html>'''
    substitutions = {"MANIFEST_PATIENTS": str(coverage["manifest_patients"]), "MANIFEST_SESSIONS": str(coverage["manifest_sessions"]),
                     "COMPLETED_SESSIONS": str(coverage["completed_sessions"]), "MISSING_PRIMARY": str(len(coverage["missing_primary_patients"])),
                     "SUMMARY_ROWS": summary_html, "METHOD_OPTIONS": method_options, "CASE_ROWS": ''.join(rows), "CASE_DATA": payload,
                     "HEADERS": ''.join('<th><button>'+name+'</button></th>' for name in ("Case", "Patient", "Session", "Partition", "Primary", "Status", "Dice", "Recall", "Precision", "Prediction mL", "Saved views"))}
    for key, value in substitutions.items():
        document = document.replace(key, value)
    (output / "VIEW_EXTERNAL_RESULTS.html").write_text(document, encoding="utf-8")


def save_plots(values, comparisons, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    group = values[(values.analysis == PRIMARY_ANALYSIS) & (values.study == PRIMARY_STUDY)]
    methods = [method for method in ("modified_eho", "direct_otsu", "original_eho", "pso", "ga", "acor") if method in set(group.method)]
    if methods:
        figure, axis = plt.subplots(figsize=(9, 5), constrained_layout=True)
        for index, method in enumerate(methods):
            observed = group.loc[group.method == method, "dice_lesion"].dropna().to_numpy()
            offsets = np.random.default_rng(BOOTSTRAP_SEED).uniform(-.18, .18, len(observed))
            axis.scatter(index + offsets, observed, s=17, alpha=.55)
            if len(observed):
                axis.plot([index-.2, index+.2], [observed.mean()]*2, color="black", linewidth=2)
        axis.set(xticks=range(len(methods)), xticklabels=methods, ylabel="Native-grid lesion Dice", ylim=(-.02, 1.02),
                 title="Earliest numeric session per patient; seed means; black line = patient mean")
        axis.tick_params(axis="x", rotation=20)
        figure.savefig(output / "primary_patient_dice.png", dpi=170)
        plt.close(figure)
    rows = [row for row in comparisons if row["analysis"] == PRIMARY_ANALYSIS and row["mean"] is not None]
    if rows:
        figure, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
        means = np.array([row["mean"] for row in rows])
        lower, upper = np.array([row["ci95_low"] for row in rows]), np.array([row["ci95_high"] for row in rows])
        axis.errorbar(means, np.arange(len(rows)), xerr=np.vstack((np.maximum(0, means-lower), np.maximum(0, upper-means))), fmt="o", capsize=4)
        axis.axvline(0, color="gray", linestyle="--")
        axis.set(yticks=np.arange(len(rows)), yticklabels=[row["baseline"] for row in rows], xlabel="Modified EHO minus baseline patient Dice",
                 title="Paired differences; 95% patient-bootstrap intervals")
        figure.savefig(output / "paired_dice_differences.png", dpi=170)
        plt.close(figure)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--run", required=True, type=Path, help="External imaging root containing all_runs.csv")
    result.add_argument("--manifest", required=True, type=Path)
    result.add_argument("--studies", type=Path, help="Optional image-only registration/noise study root")
    result.add_argument("--output", type=Path, help="Default: imaging root parent / reports")
    return result


def run(args):
    imaging_root, manifest_path = Path(args.run).resolve(), Path(args.manifest).resolve()
    output = Path(args.output).resolve() if args.output else imaging_root.parent / "reports"
    output.mkdir(parents=True, exist_ok=True)
    frame, metadata, selection, coverage, config = load_measurements(imaging_root, manifest_path)
    values, sessions = patient_values(frame, selection)
    summaries, pairs, components = summarize_patients(values), method_comparisons(values), component_comparisons(values)
    values[values.analysis == PRIMARY_ANALYSIS].to_csv(output / "primary_patient_values.csv", index=False)
    values.to_csv(output / "patient_values_all_analyses.csv", index=False)
    values[values.analysis == LONGITUDINAL_ANALYSIS].to_csv(output / "all_session_patient_values.csv", index=False)
    sessions.to_csv(output / "session_seed_means.csv", index=False)
    pd.DataFrame(summaries).to_csv(output / "patient_metric_summary.csv", index=False)
    pd.DataFrame(pairs).to_csv(output / "paired_method_comparisons.csv", index=False)
    pd.DataFrame(components).to_csv(output / "component_ablation_comparisons.csv", index=False)
    statistics = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run": str(imaging_root), "manifest": str(manifest_path),
                  "dataset": {key: value for key, value in metadata.items() if key != "cases"}, "coverage": coverage,
                  "protocol": {"primary_observational_unit": "patient at earliest numeric manifest session; seed means",
                               "secondary_observational_unit": "patient mean across all available sessions after seed averaging",
                               "bootstrap_resamples": BOOTSTRAP_RESAMPLES, "bootstrap_seed": BOOTSTRAP_SEED,
                               "primary_paired_endpoint": "dice_lesion", "wilcoxon": "two-sided; zero_method=wilcox; all-zero difference p=1",
                               "wilcoxon_estimand": "signed ranks of nonzero paired differences; symmetric-location interpretation requires assumptions; not a test of the mean paired difference",
                               "multiplicity": "Holm across five prespecified method pairs separately within each analysis",
                               "training": "none", "learned_model_comparison": "not measured"},
                  "patient_metric_summaries": summaries, "paired_method_comparisons": pairs, "component_ablation_comparisons": components,
                  "ancillary_studies": read_ancillary(args.studies)}
    write_json(output / "statistics.json", statistics)
    write_audit(output, statistics)
    make_dashboard(imaging_root, output, metadata, sessions, selection, statistics)
    save_plots(values, pairs, output)
    print(json.dumps({"status": "completed", "manifest_patients": coverage["manifest_patients"], "completed_sessions": coverage["completed_sessions"],
                      "missing_primary_patients": len(coverage["missing_primary_patients"]), "output": str(output)}), flush=True)
    return statistics


if __name__ == "__main__":
    run(parser().parse_args())
