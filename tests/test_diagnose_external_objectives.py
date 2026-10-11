"""Small synthetic checks for post hoc patient units and objective directions."""
from argparse import Namespace
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import diagnose_external_objectives as diagnostic


def fixture_csv(tmp_path):
    root = tmp_path / "imaging"
    root.mkdir()
    cases = [dict(case_id="P1_T10", subject_id="P1", session_id="T10"),
             dict(case_id="P1_T2", subject_id="P1", session_id="T2"),
             dict(case_id="P2_T1", subject_id="P2", session_id="T1")]
    for case in cases:
        case.update(partition="synthetic", image_path="NEVER_OPEN_IMAGE.nii.gz", label_path="NEVER_OPEN_LABEL.nii.gz")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"dataset": "synthetic", "cases": cases}), encoding="utf-8")
    (root / "run_manifest.json").write_text(json.dumps({"status": "completed", "protocol": {"methods": list(diagnostic.METHODS), "seeds": list(diagnostic.SEEDS)}}))
    rows = []
    for case in cases:
        for index, method in enumerate(diagnostic.METHODS):
            for seed in diagnostic.SEEDS:
                # A later P1 timepoint deliberately has the opposite ranking.
                dice = (5 - index) / 10 if case["session_id"] == "T10" else (index + 1) / 10
                if case["subject_id"] == "P2":
                    dice = .3  # All ties must remain undefined, not omitted.
                rows.append({**{key: case[key] for key in ("case_id", "subject_id", "session_id")},
                             "method": method, "seed": seed, "study": diagnostic.PRIMARY,
                             "dice_lesion": dice + (seed - 1) * .01,
                             "enhancement_objective": -index - seed * .1,
                             "segmentation_objective": index - seed * .2})
        rows.append({**{key: case[key] for key in ("case_id", "subject_id", "session_id")},
                     "method": "direct_otsu", "seed": 0, "study": diagnostic.PRIMARY,
                     "dice_lesion": .2, "enhancement_objective": None, "segmentation_objective": None})
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "all_runs.csv", index=False)
    return root, manifest, frame


def load_means(tmp_path):
    root, manifest, frame = fixture_csv(tmp_path)
    measured, selected, metadata, config = diagnostic.load_saved_measurements(root, manifest)
    return diagnostic.patient_seed_means(measured, selected), root, manifest, frame


def test_numeric_earliest_and_seed_means_do_not_pool_timepoints(tmp_path):
    means, root, manifest, frame = load_means(tmp_path)
    assert len(means) == 12
    first = means[(means.subject_id == "P1") & (means.method == "modified_eho")].iloc[0]
    assert first.case_id == "P1_T2"
    assert first.dice_lesion == pytest.approx(.2)
    assert first.enhancement_objective == pytest.approx(-1.1)
    assert first.n_seed_records == 3
    selected = diagnostic.earliest_patients(json.loads(manifest.read_text())["cases"])
    assert all("label_path" not in row and "image_path" not in row for row in selected.values())


def test_negative_objective_direction_and_constant_ties_are_retained(tmp_path):
    means, *_ = load_means(tmp_path)
    correlations = diagnostic.patient_correlations(means)
    p1 = correlations[correlations.subject_id == "P1"].set_index("stage")
    assert p1.loc["enhancement", "spearman_negative_objective_vs_dice"] == pytest.approx(1.)
    assert p1.loc["segmentation", "spearman_negative_objective_vs_dice"] == pytest.approx(-1.)
    p2 = correlations[correlations.subject_id == "P2"]
    assert len(p2) == 2 and set(p2.correlation_sign) == {"undefined"}
    assert set(p2.definition_status) == {"constant_objective_or_dice_all_ties"}
    counts = diagnostic.descriptive_counts(correlations, diagnostic.paired_differences(means))
    assert all(row["n_manifest_patients"] == 2 and row["undefined"] == 1 for row in counts["within_patient_correlation_counts"])
    discordance = {row["stage"]: row for row in counts["paired_objective_dice_direction_counts"]}
    assert discordance["segmentation"]["objective_improved_dice_worsened"] == 1
    assert discordance["enhancement"]["both_worsened"] == 1
    assert all(row["either_tied"] == 1 for row in discordance.values())


def test_partial_ties_use_average_ranks_without_false_undefined(tmp_path):
    means, *_ = load_means(tmp_path)
    group = means[(means.subject_id == "P1") & means.method.isin(diagnostic.METHODS)].copy()
    group.loc[group.method == "original_eho", "dice_lesion"] = group.loc[group.method == "modified_eho", "dice_lesion"].iloc[0]
    record = diagnostic.correlation_record(group, "enhancement")
    assert record["n_unique_dice"] == 4
    assert record["dice_has_partial_or_complete_ties"]
    assert record["correlation_sign"] == "positive"
    assert record["spearman_negative_objective_vs_dice"] == pytest.approx(.9746794345)


def test_missing_earliest_or_one_seed_stays_missing_without_later_replacement(tmp_path):
    root, manifest, frame = fixture_csv(tmp_path)
    frame = frame[~((frame.case_id == "P1_T2") & (frame.method == "ga") & (frame.seed == 2))]
    frame.to_csv(root / "all_runs.csv", index=False)
    measured, selected, *_ = diagnostic.load_saved_measurements(root, manifest)
    means = diagnostic.patient_seed_means(measured, selected)
    ga = means[(means.subject_id == "P1") & (means.method == "ga")].iloc[0]
    assert not ga.complete_seed_coverage and np.isnan(ga.dice_lesion)
    assert ga.case_id == "P1_T2"
    correlations = diagnostic.patient_correlations(means)
    assert set(correlations[correlations.subject_id == "P1"].definition_status) == {"missing_seed_coverage_or_nonfinite_endpoint"}
    assert not correlations[correlations.subject_id == "P1"].objective_has_partial_or_complete_ties.any()
    frame = frame[frame.case_id != "P1_T2"]
    frame.to_csv(root / "all_runs.csv", index=False)
    measured, selected, *_ = diagnostic.load_saved_measurements(root, manifest)
    means = diagnostic.patient_seed_means(measured, selected)
    assert set(means[means.subject_id == "P1"].case_id) == {"P1_T2"}
    assert not means[means.subject_id == "P1"].complete_seed_coverage.any()


def test_nonfinite_seed_endpoint_is_not_averaged_away(tmp_path):
    root, manifest, frame = fixture_csv(tmp_path)
    frame.loc[(frame.case_id == "P1_T2") & (frame.method == "ga") & (frame.seed == 2), "enhancement_objective"] = np.inf
    frame.to_csv(root / "all_runs.csv", index=False)
    measured, selected, *_ = diagnostic.load_saved_measurements(root, manifest)
    means = diagnostic.patient_seed_means(measured, selected)
    ga = means[(means.subject_id == "P1") & (means.method == "ga")].iloc[0]
    assert ga.complete_seed_coverage and ga.n_finite_enhancement_objective == 2
    assert np.isnan(ga.enhancement_objective)


def test_signed_pairs_and_direct_otsu_missing_objectives(tmp_path):
    means, *_ = load_means(tmp_path)
    pairs = diagnostic.paired_differences(means)
    p1_ga = pairs[(pairs.subject_id == "P1") & (pairs.baseline == "ga")].set_index("endpoint")
    assert p1_ga.loc["dice_lesion", "candidate_minus_baseline"] == pytest.approx(-.2)
    assert p1_ga.loc["enhancement_objective", "candidate_minus_baseline"] == pytest.approx(2.)
    assert p1_ga.loc["enhancement_objective", "improvement_direction_difference"] == pytest.approx(-2.)
    assert p1_ga.loc["segmentation_objective", "improvement_direction_difference"] == pytest.approx(2.)
    direct = pairs[(pairs.baseline == "direct_otsu") & pairs.endpoint.str.endswith("_objective")]
    assert direct.candidate_minus_baseline.isna().all()
    assert set(direct.status) == {"direct_otsu_does_not_optimize_stage"}
    assert len(direct) == 4


def test_csv_only_end_to_end_posthoc_provenance_and_preserved_outputs(tmp_path, monkeypatch):
    root, manifest, frame = fixture_csv(tmp_path)
    output = tmp_path / "posthoc"
    original = Path.open

    def guarded_open(path, *args, **kwargs):
        assert not str(path).endswith((".nii", ".nii.gz")), "No image or label reads are permitted"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    result = diagnostic.run(Namespace(run=root, manifest=manifest, output=output))
    assert result["status"] == "completed" and not result["prespecified"]
    assert result["initiated_after_pilot_observed"] and not result["native_voxel_files_accessed"]
    assert result["coverage"]["manifest_patients"] == 2
    assert len(pd.read_csv(output / "within_patient_correlations.csv")) == 4
    text = (output / "POSTHOC_OBJECTIVE_LOCALIZATION_CONCLUSIONS.md").read_text(encoding="utf-8")
    assert "not prespecified" in text and "method's own enhanced-image histogram" in text
    assert "no correlation p-values" in text.lower()
    assert (output / "patient_paired_objective_vs_dice.png").exists()
    assert (output / "within_patient_correlation_counts.png").exists()
    with pytest.raises(FileExistsError, match="preserved"):
        diagnostic.run(Namespace(run=root, manifest=manifest, output=output))


def test_duplicate_identity_or_running_job_rejected(tmp_path):
    root, manifest, frame = fixture_csv(tmp_path)
    pd.concat([frame, frame.iloc[:1]]).to_csv(root / "all_runs.csv", index=False)
    with pytest.raises(ValueError, match="Duplicate"):
        diagnostic.load_saved_measurements(root, manifest)
    (root / "run_manifest.json").write_text(json.dumps({"status": "running"}))
    with pytest.raises(ValueError, match="finished"):
        diagnostic.load_saved_measurements(root, manifest)
