"""External-adapter correctness without patient outcome or parameter tuning."""
from argparse import Namespace
import hashlib
import json
from pathlib import Path
import sys

import nibabel as nib
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import external_imaging as external


def save_nifti(path, data, affine=None, units="mm"):
    nii = nib.Nifti1Image(data, np.eye(4) if affine is None else affine)
    nii.header.set_xyzt_units(units)
    nib.save(nii, path)
    return nii


def fixture_dataset(tmp_path, labels=None):
    data = tmp_path / "dataset"
    data.mkdir()
    image = np.random.default_rng(77).uniform(1, 100, size=(12, 13, 14)).astype(np.float32)
    image[0, ...] = 0
    image_path, label_path = data / "subject01_flair.nii.gz", data / "subject01_expert.nii.gz"
    affine = np.diag([-1., 2., 3., 1.])
    affine[:3, 3] = [14., -4., 20.]
    save_nifti(image_path, image, affine)
    if labels is None:
        labels = np.zeros(image.shape, np.uint8)
        labels[2:5, 4:7, 6:9] = 1
        labels[8:10, 8:10, 10:12] = 1
    save_nifti(label_path, labels, affine)
    case = dict(case_id="subject01_session01", subject_id="subject01", session_id="1", partition="train",
                image_path=str(image_path), label_path=str(label_path), modality="FLAIR", allowed_labels=[0, 1], foreground_labels=[1])
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"dataset": "synthetic external adapter fixture", "license": "test data", "cases": [case]}))
    return path, case


def arguments(manifest, output, resume=False):
    return Namespace(manifest=manifest, output=output, cases=None, resume=resume,
                     methods="modified_eho", seeds="0,1", budget=36, population=6, mesh_stride=2)


def test_manifest_uses_native_ids_and_declared_labels(tmp_path):
    manifest, case = fixture_dataset(tmp_path)
    cases, metadata = external.load_manifest(manifest)
    assert cases[0]["case_id"] == "subject01_session01"
    assert cases[0]["subject_id"] == "subject01"
    assert metadata["license"] == "test data"
    original = json.loads(manifest.read_text())
    original["cases"].append(case)
    manifest.write_text(json.dumps(original))
    with pytest.raises(ValueError, match="unique"):
        external.load_manifest(manifest)


def test_3d_loader_preserves_geometry_and_rejects_undefined_units(tmp_path):
    path, case = fixture_dataset(tmp_path)
    normalized, roi, nii, metadata = external.load_image(case["image_path"])
    assert normalized.shape == nii.shape == roi.shape == (12, 13, 14)
    assert normalized.dtype == np.float32
    assert not roi[0].any()
    assert np.linalg.det(nii.affine[:3, :3]) == pytest.approx(-6.)
    no_units = tmp_path / "undefined_units.nii.gz"
    save_nifti(no_units, np.ones((5, 5, 5), np.float32), units="unknown")
    with pytest.raises(ValueError, match="explicitly be mm"):
        external.load_image(no_units)


def test_reference_value_and_geometry_mismatch_rejected(tmp_path):
    path, case = fixture_dataset(tmp_path)
    _, _, source, _ = external.load_image(case["image_path"])
    values = np.zeros(source.shape, np.uint8)
    values[4, 4, 4] = 2
    save_nifti(case["label_path"], values, source.affine)
    with pytest.raises(ValueError, match="undeclared"):
        external.load_reference(case, source)
    shifted = source.affine.copy()
    shifted[0, 3] += .001
    save_nifti(case["label_path"], np.zeros(source.shape, np.uint8), shifted)
    with pytest.raises(ValueError, match="geometry mismatch"):
        external.load_reference(case, source)


def test_lesion_metrics_preserve_counts_volume_and_empty_semantics():
    prediction = np.array([1, 1, 0, 0], bool).reshape(2, 2, 1)
    reference = np.array([1, 0, 1, 0], bool).reshape(2, 2, 1)
    metrics = external.lesion_metrics(prediction, reference, np.diag([-2., 3., 4., 1.]), [1])
    assert metrics["dice_lesion"] == .5
    assert metrics["prediction_ml"] == pytest.approx(.048)
    assert metrics["reference_rule"] == "label in [1]"
    assert not any("tumour" in key for key in metrics)
    empty = external.lesion_metrics(np.zeros_like(prediction), np.zeros_like(reference), np.eye(4), [1])
    assert empty["dice_lesion"] == empty["iou_lesion"] == 1.
    assert empty["precision_lesion"] is empty["recall_lesion"] is None


def test_display_falls_back_when_decimation_erases_tiny_lesion():
    mask = np.zeros((5, 5, 5), bool)
    mask[1, 1, 1] = True
    vertices, faces, detail = external.display_surface(mask, np.diag([-1., 2., 3., 1.]), 2)
    assert len(vertices) and len(faces)
    assert detail["actual_stride"] == 1
    assert detail["fallback_for_erased_positive_mask"]
    vertices, faces, detail = external.display_surface(np.zeros_like(mask), np.eye(4), 2)
    assert not len(vertices) and not len(faces)
    assert detail["native_positive_voxels"] == 0


def test_reference_surface_keeps_every_isolated_component_at_native_resolution(tmp_path):
    reference = np.zeros((8, 8, 8), bool)
    reference[2, 2, 2] = True
    reference[5, 5, 5] = True  # This separate lesion disappears from a stride-two mask.
    roi = np.zeros_like(reference)
    roi[1:7, 1:7, 1:7] = True
    exports = external.save_mesh_comparison(roi, {"modified_eho": reference}, reference, np.eye(4), tmp_path, 2)
    assert exports["reference_display_stride"] == 1
    assert exports["requested_prediction_display_stride"] == 2
    assert exports["reference_lesion"]["actual_stride"] == 1
    import trimesh
    mesh = trimesh.load_mesh(tmp_path / "reference_lesion.ply", process=False)
    components = mesh.split(only_watertight=False)
    assert len(components) == 2
    np.testing.assert_allclose(sorted(component.centroid[0] for component in components), [2., 5.])


def test_all_predictions_saved_before_labels_and_resume_preserves_completed_case(tmp_path, monkeypatch):
    manifest, case = fixture_dataset(tmp_path)
    output = tmp_path / "output"
    real_load = external.nib.load
    accesses = []
    def checked_load(path, *args, **kwargs):
        if Path(path).resolve() == Path(case["label_path"]):
            folder = output / case["case_id"]
            boundary = json.loads((folder / "prediction_boundary.json").read_text())
            # Two primary seeds, two secondary seeds and two direct Otsu masks.
            assert boundary["predictions_saved"] == 6
            assert all(Path(value).exists() for value in boundary["prediction_paths"])
            for prediction_path in boundary["prediction_paths"]:
                assert real_load(prediction_path).shape == (12, 13, 14)
            assert (folder / "modified_eho_seed0_enhanced_normalized_flair.nii.gz").exists()
            accesses.append(str(path))
        return real_load(path, *args, **kwargs)
    monkeypatch.setattr(external.nib, "load", checked_load)
    result = external.run(arguments(manifest, output))
    assert result["status"] == "completed" and result["output_records"] == 6
    assert len(accesses) == 1
    folder = output / case["case_id"]
    records = json.loads((folder / "case_records.json").read_text())
    for record in records:
        assert record["reference_evaluation_after_prediction"]
        assert record["saved_output_validation"]["independent_saved_mask_metrics_match"]
        if "enhancement" in record:
            assert record["enhancement"]["evaluations"] == record["segmentation"]["evaluations"] == 36
    primary = {row["seed"]: row for row in records if row["method"] == "modified_eho" and row["study"] == external.PRIMARY}
    secondary = {row["seed"]: row for row in records if row["method"] == "modified_eho" and row["study"] == external.SECONDARY}
    assert all(secondary[seed]["evaluation"]["prediction_ml"] >= primary[seed]["evaluation"]["prediction_ml"] for seed in primary)
    html = (folder / "meshes/interactive_prediction_reference.html").read_text(encoding="utf-8")
    assert "Expert reference lesions" in html and "modified_eho predicted threshold mask" in html
    assert "whole tumour" not in html
    prediction_path = folder / "modified_eho_seed0_prediction.nii.gz"
    original_bytes, original_mtime = prediction_path.read_bytes(), prediction_path.stat().st_mtime_ns
    monkeypatch.setattr(external, "predict_case", lambda *args: pytest.fail("Completed case was rerun"))
    resumed = external.run(arguments(manifest, output, resume=True))
    assert resumed["status"] == "completed"
    assert prediction_path.read_bytes() == original_bytes and prediction_path.stat().st_mtime_ns == original_mtime
    assert len(accesses) == 1
    with pytest.raises(FileExistsError, match="fresh output"):
        external.run(arguments(manifest, output))


def test_partial_failure_preserved_before_resume(tmp_path, monkeypatch):
    manifest, case = fixture_dataset(tmp_path)
    output = tmp_path / "output"
    actual = external.predict_case
    def fail_once(case, directory, args, protocol_sha):
        directory.mkdir()
        (directory / "partial_evidence.txt").write_text("preserve interrupted attempt")
        raise ValueError("injected interrupted attempt")
    monkeypatch.setattr(external, "predict_case", fail_once)
    result = external.run(arguments(manifest, output))
    assert result["status"] == "completed_with_failures" and result["failed_cases"] == 1
    monkeypatch.setattr(external, "predict_case", actual)
    resumed = external.run(arguments(manifest, output, resume=True))
    assert resumed["status"] == "completed"
    archives = list((output / "partial_attempts").glob("*/partial_evidence.txt"))
    assert len(archives) == 1 and archives[0].read_text() == "preserve interrupted attempt"


def test_subject_summary_does_not_count_sessions_as_independent_people(tmp_path):
    rows = []
    for subject, session, dice in (("a", "1", .1), ("a", "2", .3), ("b", "1", .8)):
        rows.append(dict(study=external.PRIMARY, case_id=subject+session, subject_id=subject, session_id=session,
                         partition="train", method="direct_otsu", seed=0, dice_lesion=dice))
    external.summarize(rows, tmp_path)
    import csv
    with (tmp_path / "across_subject_summary.csv").open() as handle:
        result = next(csv.DictReader(handle))
    assert int(result["n_cases"]) == 3 and int(result["n_subjects"]) == 2
    assert float(result["dice_lesion_subject_mean"]) == pytest.approx(.5)
