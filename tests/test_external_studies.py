"""Image-only stress-study boundaries and exact optimizer budgets."""
from argparse import Namespace
import json
from pathlib import Path
import sys

import nibabel as nib
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import external_studies as studies
import registration


def phantom_volume(depth=3):
    rr, cc = np.indices((80, 84))
    phantom = np.exp(-((rr - 31) ** 2 + (cc - 46) ** 2) / 100)
    phantom[(rr - 40) ** 2 + (cc - 42) ** 2 > 34 ** 2] = 0
    volume = np.zeros((80, 84, depth), np.float32)
    volume[:, :, depth - 1] = phantom * 100
    return volume


def test_numeric_subject_and_earliest_session_without_label_fields(tmp_path):
    cases = []
    for subject in (10, 2, 1, 3):
        for session in (2, 1):
            cases.append(dict(id=f"P{subject}_T{session}", subject=f"P{subject}", session=session,
                              image_path=f"P{subject}_T{session}.nii.gz", label_path="MUST_NOT_OPEN"))
    selected = studies.select_cases({"cases": cases}, tmp_path / "manifest.json")
    assert [c["case_id"] for c in selected] == ["P1_T1", "P2_T1", "P3_T1"]
    assert all("label_path" not in c for c in selected)
    assert Path(selected[0]["image_path"]).parent == tmp_path
    official_schema = [{"case_id": c["id"], "subject_id": c["subject"], "session_id": c["session"],
                        "image_path": c["image_path"]} for c in cases]
    assert studies.select_cases({"cases": official_schema}, tmp_path / "manifest.json") == selected
    with pytest.raises(ValueError, match="exactly three"):
        studies.select_cases({"cases": cases}, tmp_path / "manifest.json", 2)


def test_short_volume_fallback_preserves_truth_and_return_consistency(tmp_path):
    path = tmp_path / "image.nii.gz"
    nib.save(nib.Nifti1Image(phantom_volume(), np.eye(4)), path)
    fixed, moving, bounds, truth, mask, points, meta = studies.load_anatomical_case(path)
    assert meta["slice_index"] == 2
    assert "maximal" in meta["slice_selection_rule"]
    assert meta["reference_labels_accessed"] is False
    assert max(fixed.shape) <= 128
    np.testing.assert_array_equal(truth, [12, 4, -3])
    np.testing.assert_array_equal(bounds, [[-30, 30], [-12, 12], [-12, 12]])
    error = np.mean((fixed[mask] - registration.rigid_warp(moving, truth)[mask]) ** 2)
    assert error < np.mean((fixed[mask] - moving[mask]) ** 2) * .02
    assert registration.geometric_error(fixed.shape, truth, truth, points) == 0
    # Existing helper must yield exactly the same arrays on the selected slice.
    legacy = registration.make_anatomical_case(path, slice_index=2)
    for actual, expected in zip((fixed, moving, bounds, truth, mask, points), legacy[:6]):
        np.testing.assert_allclose(actual, expected)


def test_preferred_slice_and_nonfinite_handling(tmp_path):
    volume = phantom_volume(depth=72)
    volume[0, 0, 71] = np.inf
    volume[0, 1, 71] = np.nan
    path = tmp_path / "image.nii.gz"
    nib.save(nib.Nifti1Image(volume, np.eye(4)), path)
    fixed, moving, *_rest, meta = studies.load_anatomical_case(path)
    assert meta["slice_index"] == 71
    assert np.isfinite(fixed).all() and np.isfinite(moving).all()
    clean, roi, metadata = studies.load_noise_case(path)
    assert metadata["slice_index"] == 71
    assert not roi[0, 0] and not roi[0, 1]
    assert np.isfinite(clean).all()


def test_4d_channel_selection_and_usable_foreground(tmp_path):
    values = np.stack((phantom_volume(), np.full((80, 84, 3), 999, np.float32)), axis=3)
    path = tmp_path / "image.nii.gz"
    nib.save(nib.Nifti1Image(values, np.eye(4)), path)
    clean, roi, metadata = studies.load_noise_case(path)
    assert metadata["modality_index"] == 0 and clean.std() > .01
    assert roi.any() and not roi.all()
    with pytest.raises(ValueError, match="4D"):
        studies.load_image_volume(path, 2)
    with pytest.raises(ValueError, match="sufficient"):
        studies.foreground_slice(np.zeros((10, 10, 2)))


def test_noise_is_seeded_roi_only_and_clean_is_immutable():
    clean = np.linspace(0, 1, 400, dtype=np.float32).reshape(20, 20)
    roi = np.zeros(clean.shape, bool)
    roi[2:18, 2:18] = True
    original = clean.copy()
    first, noise = studies.corrupt_image(clean, roi, .08, 2)
    again, _ = studies.corrupt_image(clean, roi, .08, 2)
    different, _ = studies.corrupt_image(clean, roi, .08, 1)
    np.testing.assert_array_equal(clean, original)
    np.testing.assert_array_equal(first, again)
    assert not np.array_equal(first, different)
    assert np.all(first[~roi] == 0) and np.all(noise[~roi] == 0)
    assert first.min() >= 0 and first.max() <= 1


@pytest.mark.parametrize("method", studies.METHODS)
def test_noisy_only_objective_has_exact_budget_and_consistent_incumbent(method):
    noisy = np.random.default_rng(7).uniform(0, 1, (20, 20)).astype(np.float32)
    roi = np.ones(noisy.shape, bool)
    first, result = studies.contrast_prediction(noisy, roi, method, 2, budget=37, population=6)
    second, _ = studies.contrast_prediction(noisy, roi, method, 2, budget=37, population=6)
    np.testing.assert_array_equal(first, second)
    assert result["evaluations"] == 37 and len(result["history"]) == 37
    histogram = studies.imaging.image_histogram(noisy, roi)
    expected = studies.imaging.enhancement_objective(histogram)(result["x"])
    assert result["fun"] == pytest.approx(expected, abs=1e-12)
    assert result["returned_x_objective"] == result["fun"]


def test_reference_metrics_and_complete_ssim_window():
    clean = np.random.default_rng(3).uniform(0, 1, (20, 20)).astype(np.float32)
    roi = np.ones(clean.shape, bool)
    identity = studies.clean_reference_metrics(clean, clean, roi)
    assert identity["clean_roi_psnr_db"] is None
    assert identity["clean_psnr_infinite"] is True
    assert identity["clean_roi_ssim"] == 1
    assert identity["clean_foreground_eroded_ssim"] == 1
    assert identity["ssim_eroded_foreground_pixels"] == 14 ** 2
    noisy, _ = studies.corrupt_image(clean, roi, .03, 0)
    result = studies.clean_reference_metrics(clean, noisy, roi)
    assert result["clean_roi_mse"] > 0
    assert result["clean_roi_psnr_db"] == pytest.approx(-10 * np.log10(result["clean_roi_mse"]))


def test_small_full_study_never_opens_labels_and_saves_all_outputs(tmp_path, monkeypatch):
    cases = []
    for subject in (1, 2, 3):
        path = tmp_path / f"P{subject}_T1.nii.gz"
        nib.save(nib.Nifti1Image(phantom_volume(), np.eye(4)), path)
        cases.append(dict(id=f"P{subject}_T1", subject=subject, session=1,
                          image_path=str(path), label_path=str(tmp_path / "forbidden_labels.nii.gz")))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"cases": cases}), encoding="utf-8")
    real_load = nib.load
    opened = []
    def guarded_load(path, *args, **kwargs):
        assert "forbidden_labels" not in str(path)
        opened.append(str(path))
        return real_load(path, *args, **kwargs)
    monkeypatch.setattr(studies.nib, "load", guarded_load)
    monkeypatch.setattr(studies, "BUDGET", 13)
    monkeypatch.setattr(studies, "POPULATION", 6)
    monkeypatch.setattr(studies, "REGISTRATION_SEEDS", (0,))
    monkeypatch.setattr(studies, "CORRUPTION_SEEDS", (0,))
    monkeypatch.setattr(studies, "NOISE_SIGMAS", (.03,))
    output = tmp_path / "out"
    protocol = studies.run(Namespace(manifest=manifest, output=output, subjects=3))
    assert protocol["status"] == "completed"
    assert protocol["registration_runs"] == 15 and protocol["noise_runs"] == 21
    assert protocol["reference_labels_accessed"] is False
    assert len(opened) == 6
    assert (output / "registration/across_subject_summary.csv").exists()
    assert (output / "controlled_noise/across_subject_summary.csv").exists()
    assert (output / "controlled_noise/paired_quality_differences.csv").exists()
    assert (output / "controlled_noise/quality_summary.png").exists()
    evaluated = list((output / "controlled_noise").glob("*/*_evaluated.json"))
    assert len(evaluated) == 21
    for path in evaluated:
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["evaluation_after_prediction_saved"] is True
        assert record["clean_reference_used_by_optimizer"] is False
        assert record["evaluations"] == (13 if record["method"] in studies.METHODS else 0)
    with pytest.raises(FileExistsError, match="fresh"):
        studies.run(Namespace(manifest=manifest, output=output, subjects=3))
