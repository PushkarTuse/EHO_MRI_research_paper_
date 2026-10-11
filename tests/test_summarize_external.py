"""Patient/session units, prespecified selection, bootstrap and paired inference."""
from argparse import Namespace
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import summarize_external as summary


def fixture_measurements(tmp_path, omit_earliest=False):
    root = tmp_path / "imaging"
    root.mkdir()
    cases = [dict(case_id="P1_T10", subject_id="P1", session_id="T10", partition="training"),
             dict(case_id="P1_T2", subject_id="P1", session_id="T2", partition="training"),
             dict(case_id="P2_T1", subject_id="P2", session_id="T1", partition="testing")]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"dataset_name": "synthetic MS lesion cohort", "license": "test fixture", "cases": cases}))
    methods = ["original_eho", "modified_eho", "pso", "ga", "acor"]
    seeds = [0, 1, 2]
    (root / "run_manifest.json").write_text(json.dumps({"methods": methods, "seeds": seeds}))
    values = {"P1_T2": .2, "P1_T10": .9, "P2_T1": .6}
    rows = []
    for case in cases:
        if omit_earliest and case["case_id"] == "P1_T2":
            continue
        directory = root / case["case_id"]
        (directory / "meshes").mkdir(parents=True)
        (directory / "meshes/interactive_prediction_reference.html").write_text("<!doctype html><title>fixture reference lesions</title>")
        (directory / "case_completed.json").write_text("{}")
        (directory / "modified_eho_slice_71.png").write_bytes(b"fixture link only")
        for method in methods + ["direct_otsu"]:
            for seed in ([0] if method == "direct_otsu" else seeds):
                base = values[case["case_id"]]
                dice = base + (.05 if method == "modified_eho" else 0.)
                row = {**case, "study": summary.PRIMARY_STUDY, "method": method, "seed": seed,
                       "dice_lesion": dice, "iou_lesion": dice / (2 - dice), "precision_lesion": .4,
                       "recall_lesion": .5, "prediction_ml": 4., "reference_ml": 5.,
                       "enhancement_seconds": .2 if method != "direct_otsu" else None,
                       "segmentation_seconds": .3, "enhancement_sampled_peak_rss_mb": 100. if method != "direct_otsu" else None,
                       "segmentation_sampled_peak_rss_mb": 150.}
                rows.append(row)
                if method in ("modified_eho", "direct_otsu"):
                    rows.append({**row, "study": summary.SECONDARY_STUDY, "dice_lesion": dice + .02, "recall_lesion": .7})
    pd.DataFrame(rows).to_csv(root / "all_runs.csv", index=False)
    return root, path


def test_earliest_numeric_session_does_not_use_lexicographic_order():
    cases = [dict(case_id="P1_T10", subject_id="P1", session_id="T10"),
             dict(case_id="P1_T2", subject_id="P1", session_id="T2")]
    assert summary.earliest_cases(cases)["P1"]["case_id"] == "P1_T2"
    with pytest.raises(ValueError, match="numeric"):
        summary.numeric_session("baseline")


def test_patient_units_average_seeds_sessions_in_correct_order(tmp_path):
    root, path = fixture_measurements(tmp_path)
    frame, metadata, selection, coverage, config = summary.load_measurements(root, path)
    values, sessions = summary.patient_values(frame, selection)
    primary = values[(values.analysis == summary.PRIMARY_ANALYSIS) & (values.study == summary.PRIMARY_STUDY) & (values.method == "direct_otsu")]
    longitudinal = values[(values.analysis == summary.LONGITUDINAL_ANALYSIS) & (values.study == summary.PRIMARY_STUDY) & (values.method == "direct_otsu")]
    assert len(primary) == len(longitudinal) == 2
    assert primary.dice_lesion.mean() == pytest.approx(.4)
    assert longitudinal.dice_lesion.mean() == pytest.approx(.575)
    assert int(longitudinal.loc[longitudinal.subject_id == "P1", "n_sessions"].iloc[0]) == 2
    assert coverage["manifest_patients"] == 2 and coverage["manifest_sessions"] == 3


def test_missing_earliest_case_is_never_replaced_by_favorable_later_session(tmp_path):
    root, path = fixture_measurements(tmp_path, omit_earliest=True)
    frame, metadata, selection, coverage, config = summary.load_measurements(root, path)
    values, sessions = summary.patient_values(frame, selection)
    primary = values[values.analysis == summary.PRIMARY_ANALYSIS]
    assert "P1" not in set(primary.subject_id)
    assert coverage["missing_primary_patients"] == ["P1"]
    assert not coverage["cohort_complete"]


def test_incomplete_seed_coverage_excludes_case_for_all_methods(tmp_path):
    root, path = fixture_measurements(tmp_path)
    frame = pd.read_csv(root / "all_runs.csv")
    frame = frame[~((frame.case_id == "P1_T2") & (frame.method == "ga") & (frame.seed == 2))]
    frame.to_csv(root / "all_runs.csv", index=False)
    checked, metadata, selection, coverage, config = summary.load_measurements(root, path)
    assert "P1_T2" not in set(checked.case_id)
    assert coverage["missing_primary_patients"] == ["P1"]
    assert coverage["incomplete_case_seed_coverage"][0]["missing"] == ["ga seed coverage"]


def test_incomplete_secondary_seed_coverage_does_not_alter_primary(tmp_path):
    root, path = fixture_measurements(tmp_path)
    frame = pd.read_csv(root / "all_runs.csv")
    frame = frame[~((frame.case_id == "P1_T2") & (frame.study == summary.SECONDARY_STUDY) & (frame.method == "modified_eho") & (frame.seed == 2))]
    frame.to_csv(root / "all_runs.csv", index=False)
    checked, metadata, selection, coverage, config = summary.load_measurements(root, path)
    assert "P1_T2" in set(checked[checked.study == summary.PRIMARY_STUDY].case_id)
    assert "P1_T2" not in set(checked[checked.study == summary.SECONDARY_STUDY].case_id)
    assert not coverage["missing_primary_patients"]
    assert coverage["secondary_incomplete_case_seed_coverage"][0]["missing"] == ["modified_eho secondary seed coverage"]


def test_bootstrap_reproducible_and_at_patient_level():
    first = summary.bootstrap_mean([.1, .3, .8])
    second = summary.bootstrap_mean([.1, .3, .8])
    assert first == second
    assert first["n_patients"] == 3
    assert first["mean"] == pytest.approx(.4)
    assert first["sd"] == pytest.approx(np.std([.1, .3, .8], ddof=1))
    assert first["ci95_low"] <= first["mean"] <= first["ci95_high"]
    empty = summary.bootstrap_mean([np.nan])
    assert empty["mean"] is None and empty["n_patients"] == 0


def test_paired_ties_and_holm_known_values():
    tied = summary.paired_stats([.2, .3, .5], [.2, .3, .5])
    assert tied["mean"] == tied["ci95_low"] == tied["ci95_high"] == 0
    assert tied["wilcoxon_two_sided_p"] == 1
    np.testing.assert_allclose(summary.holm_adjust([.01, .04, .03, .002, .5]), [.04, .09, .09, .01, .5])
    assert summary.holm_adjust([.01], family_size=5) == [.05]
    partial = summary.paired_stats([.2, np.nan, .6], [.1, .3, .4])
    assert partial["n_patients"] == 2 and partial["mean"] == pytest.approx(.15)


def test_negative_mean_positive_median_are_preserved_as_distinct_paired_estimands():
    baseline = np.full(7, .5)
    candidate = baseline + np.array([.01, .01, .01, .01, 0., -.02, -.4])
    result = summary.paired_stats(candidate, baseline)
    assert result["mean"] < 0
    assert result["median_paired_difference"] == pytest.approx(.01)
    assert (result["positive_pairs"], result["negative_pairs"], result["tied_pairs"]) == (4, 2, 1)
    assert result["n_patients"] == 7
    assert sum(result[key] for key in ("positive_pairs", "negative_pairs", "tied_pairs")) == 7


def test_five_prespecified_method_pairs_and_component_direction(tmp_path):
    root, path = fixture_measurements(tmp_path)
    frame, metadata, selection, coverage, config = summary.load_measurements(root, path)
    values, sessions = summary.patient_values(frame, selection)
    pairs = summary.method_comparisons(values)
    primary = [row for row in pairs if row["analysis"] == summary.PRIMARY_ANALYSIS]
    assert len(primary) == 5 and all(row["holm_family_complete"] for row in primary)
    assert all(row["mean"] == pytest.approx(.05) for row in primary)
    components = summary.component_comparisons(values)
    primary_components = [row for row in components if row["analysis"] == summary.PRIMARY_ANALYSIS]
    assert len(primary_components) == 4
    assert all(row["mean"] == pytest.approx(.02 if row["metric"] == "dice_lesion" else .2) for row in primary_components)


def test_complete_report_dashboard_links_every_manifest_case_and_optional_studies(tmp_path):
    root, path = fixture_measurements(tmp_path, omit_earliest=True)
    output = tmp_path / "reports"
    result = summary.run(Namespace(run=root, manifest=path, studies=None, output=output))
    assert result["coverage"]["missing_primary_patients"] == ["P1"]
    assert result["ancillary_studies"]["status"] == "not supplied"
    assert len(result["paired_method_comparisons"]) == 10
    primary = pd.read_csv(output / "primary_patient_values.csv")
    assert set(primary.analysis) == {summary.PRIMARY_ANALYSIS}
    document = (output / "VIEW_EXTERNAL_RESULTS.html").read_text(encoding="utf-8")
    for case in json.loads(path.read_text())["cases"]:
        assert f"{case['case_id']}/meshes/interactive_prediction_reference.html" in document
    assert "Earliest sessions only" in document
    assert "not native-acquisition lesion burden" in document
    audit = (output / "EXTERNAL_CLAIMS_AUDIT.md").read_text(encoding="utf-8")
    assert "0.736661" in audit and "0.752200" in audit
    assert "never pooled" in audit and "Training: none" in audit
    assert (output / "primary_patient_dice.png").exists()
    assert (output / "paired_dice_differences.png").exists()


def test_ancillary_summaries_average_repeated_rng_runs_within_subject(tmp_path):
    studies = tmp_path / "studies"
    (studies / "registration").mkdir(parents=True)
    frame = pd.DataFrame([dict(subject="P1", method="pso", objective=.1, grid_landmark_rmse_pixels=1., seconds=.2),
                          dict(subject="P1", method="pso", objective=.3, grid_landmark_rmse_pixels=3., seconds=.2),
                          dict(subject="P2", method="pso", objective=.8, grid_landmark_rmse_pixels=8., seconds=.2)])
    frame.to_csv(studies / "registration/runs.csv", index=False)
    result = summary.read_ancillary(studies)
    metric = next(row for row in result["summaries"] if row["metric"] == "grid_landmark_rmse_pixels")
    assert metric["n_patients"] == 2 and metric["mean"] == 5
    assert metric["clinical_validation"] is False
