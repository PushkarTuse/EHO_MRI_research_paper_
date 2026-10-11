"""Post hoc CSV-only objective-versus-lesion-overlap diagnostic.

Initiated after inspection of the external pilot, not prespecified. No prediction,
optimization, NIfTI access, patient selection changes, or inferential tests occur.
The five method points within a patient are descriptive comparisons, not five
independent patients. Segmentation objectives use method-specific enhanced-image
histograms, unlike the shared source histogram used by enhancement objectives.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

METHODS = ("original_eho", "modified_eho", "pso", "ga", "acor")
SEEDS = (0, 1, 2)
PRIMARY = "primary_largest_6_connected_component"
ENDPOINTS = ("dice_lesion", "enhancement_objective", "segmentation_objective")
STAGES = ("enhancement", "segmentation")
SIGN_TOLERANCE = 1e-12
PROVENANCE = "post_hoc_after_external_pilot_objective_localization_diagnostic_2026-10-11"


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(json_safe(value), indent=2, allow_nan=False), encoding="utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def natural_key(value):
    return tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(value)))


def earliest_patients(cases):
    """Sanitize manifest identities; never retain image or label paths."""
    selected, seen = {}, set()
    for case in cases:
        identifier = str(case["case_id"])
        if identifier in seen:
            raise ValueError("Duplicate manifest case ID")
        seen.add(identifier)
        subject = str(case.get("subject_id", case.get("subject", "")))
        session = str(case.get("session_id", case.get("session", "")))
        numbers = re.findall(r"\d+(?:\.\d+)?", session)
        if not subject or len(numbers) != 1:
            raise ValueError("Manifest requires subject identity and one numeric session timepoint")
        identity = {"case_id": identifier, "subject_id": subject, "session_id": session,
                    "partition": str(case.get("partition", "")), "numeric_session": float(numbers[0])}
        previous = selected.get(subject)
        if previous is None or (identity["numeric_session"], natural_key(identifier)) < (previous["numeric_session"], natural_key(previous["case_id"])):
            selected[subject] = identity
    return selected


def load_saved_measurements(run, manifest):
    run, manifest = Path(run), Path(manifest)
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    cases = metadata["cases"]
    if not cases:
        raise ValueError("Full manifest must contain at least one patient")
    selected = earliest_patients(cases)
    config_path = run / "run_manifest.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    if config.get("status") not in (None, "completed", "completed_with_failures"):
        raise ValueError("Wait until the external imaging job has finished")
    protocol = config.get("protocol", config)
    if set(protocol.get("methods", METHODS)) != set(METHODS) or set(protocol.get("seeds", SEEDS)) != set(SEEDS):
        raise ValueError("Diagnostic requires the frozen five methods and seeds 0, 1, 2")
    frame = pd.read_csv(run / "all_runs.csv", dtype={"case_id": str, "subject_id": str, "session_id": str})
    required = {"case_id", "subject_id", "session_id", "method", "seed", "study", *ENDPOINTS}
    if required.difference(frame.columns):
        raise ValueError("all_runs.csv missing fields: " + ", ".join(sorted(required.difference(frame.columns))))
    lookup = {str(case["case_id"]): case for case in cases}
    for row in frame[["case_id", "subject_id", "session_id"]].drop_duplicates().itertuples(index=False):
        if row.case_id not in lookup:
            raise ValueError("Measurement case ID absent from full manifest")
        case = lookup[row.case_id]
        if row.subject_id != str(case.get("subject_id", case.get("subject"))) or row.session_id != str(case.get("session_id", case.get("session"))):
            raise ValueError("Measurement subject/session differs from manifest")
    if frame.duplicated(["study", "case_id", "method", "seed"]).any():
        raise ValueError("Duplicate study/case/method/seed measurement")
    numeric_seed = pd.to_numeric(frame.seed, errors="raise")
    if not np.isfinite(numeric_seed).all() or not (numeric_seed == np.floor(numeric_seed)).all():
        raise ValueError("Measurement seeds must be finite integers")
    frame["seed"] = numeric_seed.astype(int)
    for endpoint in ENDPOINTS:
        frame[endpoint] = pd.to_numeric(frame[endpoint], errors="raise")
    primary = frame[frame.study == PRIMARY].copy()
    if not set(primary.method).issubset(set(METHODS) | {"direct_otsu"}):
        raise ValueError("Unexpected primary method")
    return primary, selected, metadata, config


def patient_seed_means(frame, selected):
    """One row per fixed earliest-session patient and method, even if missing."""
    records = []
    for subject in sorted(selected, key=natural_key):
        identity = selected[subject]
        case_rows = frame[frame.case_id == identity["case_id"]]
        for method in (*METHODS, "direct_otsu"):
            rows = case_rows[case_rows.method == method]
            expected = {0} if method == "direct_otsu" else set(SEEDS)
            actual = set(rows.seed)
            complete = actual == expected and len(rows) == len(expected)
            record = {**identity, "method": method, "n_expected_seeds": len(expected), "n_seed_records": len(rows),
                      "complete_seed_coverage": complete, "observed_seeds": ",".join(map(str, sorted(actual)))}
            for endpoint in ENDPOINTS:
                values = rows[endpoint].to_numpy(dtype=float)
                finite = values[np.isfinite(values)]
                record["n_finite_" + endpoint] = len(finite)
                if method == "direct_otsu" and endpoint.endswith("_objective"):
                    # Direct Otsu performs neither of these stochastic stages.
                    record[endpoint] = None
                else:
                    record[endpoint] = float(finite.mean()) if complete and len(finite) == len(expected) else None
            records.append(record)
    return pd.DataFrame(records)


def sign(value, tolerance=SIGN_TOLERANCE):
    if value is None or not np.isfinite(value):
        return "undefined"
    if abs(value) <= tolerance:
        return "zero"
    return "positive" if value > 0 else "negative"


def correlation_record(group, stage):
    """Average ranks handle partial ties; constant endpoints remain undefined."""
    group = group.set_index("method").reindex(METHODS)
    objective = -group[stage + "_objective"].to_numpy(dtype=float)
    dice = group.dice_lesion.to_numpy(dtype=float)
    finite = np.isfinite(objective) & np.isfinite(dice)
    unique_objective = len(np.unique(objective[np.isfinite(objective)]))
    unique_dice = len(np.unique(dice[np.isfinite(dice)]))
    if not finite.all():
        rho, reason = None, "missing_seed_coverage_or_nonfinite_endpoint"
    elif unique_objective < 2 or unique_dice < 2:
        rho, reason = None, "constant_objective_or_dice_all_ties"
    else:
        rho, reason = float(spearmanr(objective, dice).statistic), "defined_average_ranks_for_ties"
    return {"stage": stage, "n_expected_method_points": len(METHODS), "n_finite_method_pairs": int(finite.sum()),
            "n_unique_negative_objectives": unique_objective, "n_unique_dice": unique_dice,
            "objective_has_partial_or_complete_ties": unique_objective < int(np.isfinite(objective).sum()),
            "dice_has_partial_or_complete_ties": unique_dice < int(np.isfinite(dice).sum()),
            "spearman_negative_objective_vs_dice": rho, "correlation_sign": sign(rho), "definition_status": reason}


def patient_correlations(means):
    records = []
    for subject, group in means.groupby("subject_id", sort=False):
        identity = group.iloc[0]
        for stage in STAGES:
            records.append({"subject_id": subject, "case_id": identity.case_id, "session_id": identity.session_id,
                            **correlation_record(group[group.method.isin(METHODS)], stage)})
    return pd.DataFrame(records)


def paired_differences(means):
    records = []
    for subject, group in means.groupby("subject_id", sort=False):
        lookup = group.set_index("method")
        candidate = lookup.loc["modified_eho"]
        for baseline_name in ("ga", "direct_otsu"):
            baseline = lookup.loc[baseline_name]
            for endpoint in ENDPOINTS:
                left, right = candidate[endpoint], baseline[endpoint]
                available = pd.notna(left) and pd.notna(right) and np.isfinite(left) and np.isfinite(right)
                raw_difference = float(left - right) if available else None
                desirability_difference = raw_difference if endpoint == "dice_lesion" else (-raw_difference if available else None)
                records.append({"subject_id": subject, "case_id": candidate.case_id, "session_id": candidate.session_id,
                                "candidate": "modified_eho", "baseline": baseline_name, "endpoint": endpoint,
                                "candidate_value": left, "baseline_value": right,
                                "candidate_minus_baseline": raw_difference,
                                "difference_direction": "modified_eho minus baseline; lower objective and higher Dice are preferred",
                                "improvement_direction_difference": desirability_difference,
                                "improvement_sign": sign(desirability_difference),
                                "status": "defined" if available else ("direct_otsu_does_not_optimize_stage" if baseline_name == "direct_otsu" and endpoint.endswith("_objective") else "missing_or_nonfinite_endpoint")})
    return pd.DataFrame(records)


def descriptive_counts(correlations, paired):
    correlation_counts, pair_counts, discordance_counts = [], [], []
    for stage, group in correlations.groupby("stage", sort=False):
        counts = group.correlation_sign.value_counts()
        correlation_counts.append({"stage": stage, "n_manifest_patients": len(group),
                                   **{kind: int(counts.get(kind, 0)) for kind in ("positive", "negative", "zero", "undefined")},
                                   "n_partial_or_complete_objective_ties": int(group.objective_has_partial_or_complete_ties.sum()),
                                   "n_partial_or_complete_dice_ties": int(group.dice_has_partial_or_complete_ties.sum()),
                                   "n_undefined_all_ties": int((group.definition_status == "constant_objective_or_dice_all_ties").sum())})
    for (baseline, endpoint), group in paired.groupby(["baseline", "endpoint"], sort=False):
        counts = group.improvement_sign.value_counts()
        finite = pd.to_numeric(group.candidate_minus_baseline, errors="coerce").dropna()
        pair_counts.append({"baseline": baseline, "endpoint": endpoint, "n_manifest_patients": len(group),
                            **{kind: int(counts.get(kind, 0)) for kind in ("positive", "negative", "zero", "undefined")},
                            "mean_candidate_minus_baseline": float(finite.mean()) if len(finite) else None,
                            "median_candidate_minus_baseline": float(finite.median()) if len(finite) else None})
    ga = paired[paired.baseline == "ga"].pivot(index="subject_id", columns="endpoint", values="improvement_direction_difference")
    for stage in STAGES:
        counts = {kind: 0 for kind in ("both_improved", "objective_improved_dice_worsened", "objective_worsened_dice_improved", "both_worsened", "either_tied", "undefined")}
        for objective, dice in ga[[stage + "_objective", "dice_lesion"]].itertuples(index=False, name=None):
            direction_objective, direction_dice = sign(objective), sign(dice)
            if "undefined" in (direction_objective, direction_dice):
                kind = "undefined"
            elif "zero" in (direction_objective, direction_dice):
                kind = "either_tied"
            else:
                kind = {("positive", "positive"): "both_improved", ("positive", "negative"): "objective_improved_dice_worsened",
                        ("negative", "positive"): "objective_worsened_dice_improved", ("negative", "negative"): "both_worsened"}[(direction_objective, direction_dice)]
            counts[kind] += 1
        discordance_counts.append({"stage": stage, "candidate": "modified_eho", "baseline": "ga", "n_manifest_patients": len(ga), **counts})
    return {"within_patient_correlation_counts": correlation_counts, "paired_difference_counts": pair_counts,
            "paired_objective_dice_direction_counts": discordance_counts}


def plot_differences(paired, correlations, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ga = paired[paired.baseline == "ga"].pivot(index="subject_id", columns="endpoint", values="improvement_direction_difference")
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for axis, stage in zip(axes, STAGES):
        objective = stage + "_objective"
        valid = ga[[objective, "dice_lesion"]].dropna()
        axis.scatter(valid[objective], valid.dice_lesion, s=22, alpha=.7)
        axis.axhline(0, color="grey", linewidth=.8)
        axis.axvline(0, color="grey", linewidth=.8)
        axis.set(xlabel=f"Gain in negative {stage} objective (modified EHO − GA)",
                 ylabel="Dice gain (modified EHO − GA)", title=f"{stage.capitalize()}: {len(valid)} paired patients")
    figure.suptitle("Post hoc descriptive objective–overlap differences; one point per earliest-session patient")
    figure.savefig(output / "patient_paired_objective_vs_dice.png", dpi=160)
    plt.close(figure)
    figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for axis, stage in zip(axes, STAGES):
        group = correlations[correlations.stage == stage]
        counts = group.correlation_sign.value_counts()
        labels = ("positive", "negative", "zero", "undefined")
        axis.bar(labels, [counts.get(label, 0) for label in labels], color=["#447744", "#aa5544", "#888888", "#bb9955"])
        axis.set(title=f"{stage.capitalize()} ({len(group)} patients)", ylabel="Patient count")
    figure.suptitle("Within-patient Spearman(−objective, Dice), five seed-mean method points")
    figure.savefig(output / "within_patient_correlation_counts.png", dpi=160)
    plt.close(figure)


def report_text(result):
    coverage = result["coverage"]
    lines = ["# Post hoc objective–lesion-overlap diagnostic", "",
             "This descriptive study was initiated after inspecting the external pilot. It was not prespecified and does not change the frozen primary analysis or predictions.", "",
             f"Selection: each of {coverage['manifest_patients']} manifest patients' earliest numeric session, with no replacement by a later session. Stochastic method endpoints are means of seeds 0, 1, 2; all three finite values and complete seed coverage are required. {coverage['patients_with_complete_stochastic_seed_coverage']} patients have complete stochastic seed coverage.", "",
             "For each patient and stage, Spearman(−objective, Dice) uses exactly five method means. Partial ties receive average ranks; a constant endpoint, missing stage value or incomplete seed coverage gives an undefined correlation that remains in the patient table and denominator. No correlation p-values, pooled seed/timepoint inference, or causal claim are produced.", "",
             "Enhancement objectives share the patient's source-image histogram. Segmentation objectives use each method's own enhanced-image histogram, so their between-method differences compare different downstream objective instances. A better objective can coexist with poorer lesion localization; this diagnostic does not identify which anatomical tissue produces a false positive.", "",
             "Direct Otsu is an unenhanced deterministic baseline. Its Dice can be paired with modified EHO, but it has neither recorded optimization objective; those objective differences are explicitly undefined and are not replaced with zero.", "",
             "## Within-patient correlation counts", "", "| Stage | Positive | Negative | Zero | Undefined | All-tie undefined |", "|---|---:|---:|---:|---:|---:|"]
    for row in result["within_patient_correlation_counts"]:
        lines.append(f"| {row['stage']} | {row['positive']} | {row['negative']} | {row['zero']} | {row['undefined']} | {row['n_undefined_all_ties']} |")
    lines += ["", "Positive means larger negative objective tends to accompany larger Dice among the five methods within that patient. Negative means the rankings run in opposite directions. Undefined patients are retained; these counts are descriptive.", "",
              "## Modified EHO paired signed differences", "", "| Baseline | Endpoint | Mean raw difference | Improved | Worsened | Tied | Undefined |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in result["paired_difference_counts"]:
        mean = "undefined" if row["mean_candidate_minus_baseline"] is None else f"{row['mean_candidate_minus_baseline']:.8g}"
        lines.append(f"| {row['baseline']} | {row['endpoint']} | {mean} | {row['positive']} | {row['negative']} | {row['zero']} | {row['undefined']} |")
    lines += ["", "Raw difference is modified EHO minus baseline; positive Dice and negative objectives are preferred. The plots convert objective differences to gain in negative objective, so both positive axes denote improvement. Each plotted point is one patient's seed means; no images or masks are opened.", "",
              "| Stage, modified EHO versus GA | Both improved | Better objective, worse Dice | Worse objective, better Dice | Both worsened | Either tied | Undefined |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for row in result["paired_objective_dice_direction_counts"]:
        lines.append(f"| {row['stage']} | {row['both_improved']} | {row['objective_improved_dice_worsened']} | {row['objective_worsened_dice_improved']} | {row['both_worsened']} | {row['either_tied']} | {row['undefined']} |")
    lines += ["",
              "## Dataset-level interpretation", "",
              "The tables describe alignment between optimization scores and expert-mask overlap on this cohort. They neither validate clinical denoising or diagnosis nor compare against a learned model. Objective convergence alone cannot establish lesion-localization accuracy. The paired plot can expose patients with better recorded objectives and worse Dice, without establishing a causal mechanism.", "",
              "Files: `patient_seed_means.csv`, `within_patient_correlations.csv`, `paired_signed_differences.csv`, `correlation_counts.csv`, `paired_difference_counts.csv`, `paired_objective_dice_direction_counts.csv`, `diagnostic_summary.json`, and two PNG figures. Source CSV and manifest checksums are recorded in the JSON.", ""]
    return "\n".join(lines)


def run(args):
    started = time.perf_counter()
    frame, selected, metadata, config = load_saved_measurements(args.run, args.manifest)
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use a fresh output directory; existing reports are preserved")
    output.mkdir(parents=True, exist_ok=True)
    means = patient_seed_means(frame, selected)
    correlations = patient_correlations(means)
    paired = paired_differences(means)
    stochastic = means[means.method.isin(METHODS)]
    complete = stochastic.groupby("subject_id").complete_seed_coverage.all()
    result = {"provenance": PROVENANCE, "prespecified": False, "initiated_after_pilot_observed": True,
              "analysis_unit": "patient earliest numeric session; RNG seeds averaged within method",
              "methods_per_patient": list(METHODS), "optimizer_seeds": list(SEEDS),
              "correlation": "descriptive within-patient Spearman of negative objective and Dice; no p-values",
              "sign_tolerance": SIGN_TOLERANCE, "native_voxel_files_accessed": False,
              "dataset": metadata.get("dataset_name", metadata.get("dataset", "external dataset")),
              "source_csv": str(Path(args.run).resolve() / "all_runs.csv"), "source_csv_sha256": sha256(Path(args.run) / "all_runs.csv"),
              "manifest": str(Path(args.manifest).resolve()), "manifest_sha256": sha256(args.manifest),
              "source_run_status": config.get("status", "not recorded"),
              "coverage": {"manifest_patients": len(selected), "manifest_sessions": len(metadata["cases"]),
                           "patients_with_complete_stochastic_seed_coverage": int(complete.sum()),
                           "incomplete_primary_patients": list(complete.index[~complete]),
                           "selected_primary_cases": {subject: case["case_id"] for subject, case in selected.items()}},
              **descriptive_counts(correlations, paired)}
    means.to_csv(output / "patient_seed_means.csv", index=False)
    correlations.to_csv(output / "within_patient_correlations.csv", index=False)
    paired.to_csv(output / "paired_signed_differences.csv", index=False)
    pd.DataFrame(result["within_patient_correlation_counts"]).to_csv(output / "correlation_counts.csv", index=False)
    pd.DataFrame(result["paired_difference_counts"]).to_csv(output / "paired_difference_counts.csv", index=False)
    pd.DataFrame(result["paired_objective_dice_direction_counts"]).to_csv(output / "paired_objective_dice_direction_counts.csv", index=False)
    plot_differences(paired, correlations, output)
    (output / "POSTHOC_OBJECTIVE_LOCALIZATION_CONCLUSIONS.md").write_text(report_text(result), encoding="utf-8")
    result.update(status="completed", seconds=time.perf_counter() - started,
                  completed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  diagnostic_code_sha256=sha256(__file__))
    write_json(output / "diagnostic_summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Completed imaging directory containing all_runs.csv")
    parser.add_argument("--manifest", required=True, type=Path, help="Full external cohort manifest")
    parser.add_argument("--output", required=True, type=Path, help="Fresh output directory")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({"status": result["status"], "patients": result["coverage"]["manifest_patients"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
