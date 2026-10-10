"""Imaging correctness checks on synthetic volumes; no patient outcomes are tuned."""
from argparse import Namespace
import json
from pathlib import Path
import sys

import nibabel as nib
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import imaging


def test_preprocessing_excludes_nonfinite_and_background():
    image = np.zeros((5, 5, 5), np.float32)
    image[1:4, 1:4, 1:4] = np.arange(1, 28).reshape(3, 3, 3)
    image[0, 0, 0] = np.nan
    image[0, 0, 1] = np.inf
    normalized, roi, record = imaging.preprocess_flair(image)
    assert roi.sum() == 27
    assert np.isfinite(normalized).all()
    assert np.all(normalized[~roi] == 0)
    assert normalized.min() == 0 and normalized.max() == 1
    assert record["roi_voxels"] == 27


def test_prediction_uses_no_label_inputs_and_consumes_both_budgets():
    rng = np.random.default_rng(123)
    image = rng.uniform(.1, 1., size=(12, 13, 14)).astype(np.float32)
    roi = np.ones(image.shape, bool)
    first = imaging.predict_from_image(image, roi, "modified_eho", 7, 36, 6)
    second = imaging.predict_from_image(image, roi, "modified_eho", 7, 36, 6)
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])
    assert first[1].dtype == bool and first[1].shape == image.shape
    assert first[2]["reference_labels_accessed"] is False
    assert first[2]["enhancement"]["evaluations"] == 36
    assert first[2]["segmentation"]["evaluations"] == 36


def test_mask_and_enhancement_nifti_preserve_grid_and_forms(tmp_path):
    affine = np.diag([-2., 3., 4., 1.])
    affine[:3, 3] = [17., -8., 42.]
    source = nib.Nifti1Image(np.zeros((5, 6, 7, 4), np.float32), affine)
    source.header.set_xyzt_units("mm", "sec")
    source.set_qform(affine, code=1)
    source.set_sform(affine, code=2)
    values = np.linspace(0, 1, 210, dtype=np.float32).reshape(5, 6, 7)
    volume_path, mask_path = tmp_path / "enhanced.nii.gz", tmp_path / "mask.nii.gz"
    imaging.save_volume(values, source, volume_path)
    imaging.save_mask(values > .5, source, mask_path)
    for path, dtype in ((volume_path, np.float32), (mask_path, np.uint8)):
        saved = nib.load(path)
        assert saved.shape == (5, 6, 7)
        assert saved.get_data_dtype() == np.dtype(dtype)
        np.testing.assert_allclose(saved.affine, affine)
        np.testing.assert_allclose(saved.get_qform(), affine)
        np.testing.assert_allclose(saved.get_sform(), affine)
        assert int(saved.header["qform_code"]) == 1
        assert int(saved.header["sform_code"]) == 2
        assert saved.header.get_xyzt_units() == ("mm", "sec")
    np.testing.assert_allclose(nib.load(volume_path).get_fdata(), values)
    assert set(np.unique(nib.load(mask_path).get_fdata())) == {0., 1.}
    with pytest.raises(ValueError, match="original 3D image grid"):
        imaging.save_volume(np.zeros((5, 6, 8)), source, tmp_path / "bad.nii.gz")


def test_metrics_known_counts_and_volume():
    prediction = np.array([1, 1, 0, 0], bool).reshape(2, 2, 1)
    reference = np.array([1, 0, 1, 0], bool).reshape(2, 2, 1)
    result = imaging.segmentation_metrics(prediction, reference, np.diag([2., 3., 4., 1.]))
    assert (result["tp"], result["fp"], result["fn"], result["tn"]) == (1, 1, 1, 1)
    assert result["dice_whole_tumour"] == .5
    assert result["iou_whole_tumour"] == pytest.approx(1 / 3)
    assert result["prediction_ml"] == pytest.approx(.048)
    assert result["recall_whole_tumour"] == .5
    with pytest.raises(ValueError, match="same grid"):
        imaging.segmentation_metrics(prediction, np.zeros((2, 2, 2)), np.eye(4))


def test_mesh_coordinates_follow_affine_not_array_indices():
    mask = np.zeros((7, 8, 9), bool)
    mask[2:5, 2:6, 3:7] = True
    affine = np.diag([-2., 3., 4., 1.])
    affine[:3, 3] = [20., -10., 5.]
    vertices, faces = imaging.mesh_from_mask(mask, affine, stride=1)
    assert len(faces) > 0
    np.testing.assert_allclose(vertices.min(axis=0), [11., -5.5, 15.])
    np.testing.assert_allclose(vertices.max(axis=0), [17., 6.5, 31.])
    vertices, faces = imaging.mesh_from_mask(np.zeros_like(mask), affine)
    assert vertices.shape == faces.shape == (0, 3)


def test_appearance_identity_reports_infinite_psnr_explicitly():
    image = np.random.default_rng(0).uniform(size=(10, 10, 8)).astype(np.float32)
    result = imaging.appearance_metrics(image, image, np.ones_like(image, bool), [3])
    assert result["roi_input_similarity_psnr_db"] is None
    assert result["identity_psnr_infinite"] is True
    assert result["selected_slice_input_ssim"][0]["input_similarity_ssim"] == 1.
    assert result["selected_slice_input_ssim"][0]["roi_input_similarity_ssim"] == 1.


def test_small_pipeline_saves_predictions_before_reference_access(tmp_path, monkeypatch):
    """End-to-end I/O boundary test across two cases, including 3D exports."""
    dataset, output = tmp_path / "dataset", tmp_path / "out"
    (dataset / "imagesTr").mkdir(parents=True)
    (dataset / "labelsTr").mkdir()
    training = []
    for case_id in ("CASE_001", "CASE_002"):
        values = np.random.default_rng(4).uniform(.2, 100, size=(12, 12, 12, 4)).astype(np.float32)
        values[0, ...] = 0
        label = np.zeros((12, 12, 12), np.uint8)
        label[5:8, 5:8, 5:8] = 3
        image_path = dataset / "imagesTr" / f"{case_id}.nii.gz"
        label_path = dataset / "labelsTr" / f"{case_id}.nii.gz"
        nib.save(nib.Nifti1Image(values, np.eye(4)), image_path)
        nib.save(nib.Nifti1Image(label, np.eye(4)), label_path)
        training.append({"image": f"./imagesTr/{case_id}.nii.gz", "label": f"./labelsTr/{case_id}.nii.gz"})
    (dataset / "dataset.json").write_text(json.dumps({"modality": {"0": "FLAIR"}, "training": training}))
    real_load = nib.load
    reference_accesses = []
    def checked_load(path, *args, **kwargs):
        path = Path(path)
        if path.parent == dataset / "labelsTr":
            case_dir = output / path.name.removesuffix(".nii.gz")
            assert len(list(case_dir.glob("modified_eho_seed*_prediction.nii.gz"))) == 2
            assert (case_dir / "direct_otsu_prediction.nii.gz").exists()
            assert (case_dir / "modified_eho_seed0_enhanced_normalized_flair.nii.gz").exists()
            reference_accesses.append(path.name)
        return real_load(path, *args, **kwargs)
    monkeypatch.setattr(imaging.nib, "load", checked_load)
    imaging.run(Namespace(dataset=dataset, output=output, cases=2, seeds="0,1",
                          methods="modified_eho", budget=36, population=6,
                          mesh_stride=2, no_mesh=False))
    assert reference_accesses == ["CASE_001.nii.gz", "CASE_002.nii.gz"]
    manifest = json.loads((output / "run_manifest.json").read_text())
    assert manifest["status"] == "completed" and manifest["output_records"] == 6
    for case_id in ("CASE_001", "CASE_002"):
        meshes = json.loads((output / case_id / "meshes/mesh_manifest.json").read_text())
        assert meshes["evaluation_downsampled"] is False
        assert (output / case_id / "meshes/interactive_prediction_reference.html").exists()
        assert "modified_eho_prediction" in meshes
        assert "reference_whole_tumour" in meshes
    with pytest.raises(FileExistsError, match="fresh output directory"):
        imaging.run(Namespace(dataset=dataset, output=output, cases=2, seeds="0,1",
                              methods="modified_eho", budget=36, population=6,
                              mesh_stride=2, no_mesh=False))
