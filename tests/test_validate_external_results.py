"""Independent validator tests use tiny arrays and file headers, never patient data."""
from pathlib import Path
import struct
import sys

import nibabel as nib
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import validate_external_results as validator


def header(spacing=(1, 1, 1), units="mm"):
    result = nib.Nifti1Header()
    result.set_data_shape((2, 2, 2))
    result.set_zooms(spacing)
    result.set_xyzt_units(units)
    return result


def test_confusion_counts_and_millilitres():
    prediction = np.array([1, 1, 1, 0, 0, 0, 0, 0], dtype=bool)
    reference = np.array([1, 1, 0, 1, 0, 0, 0, 0], dtype=bool)
    values = validator.independent_metrics(prediction, reference, header())
    assert {key: values[key] for key in ("tp", "fp", "fn", "tn")} == dict(tp=2, fp=1, fn=1, tn=4)
    assert values["dice_lesion"] == pytest.approx(2 / 3)
    assert values["precision_lesion"] == values["recall_lesion"] == pytest.approx(2 / 3)
    assert values["iou_lesion"] == 0.5
    assert values["specificity"] == 0.8
    assert values["prediction_ml"] == values["reference_ml"] == 0.003
    assert values["voxel_volume_ml"] == 0.001
    assert validator.independent_metrics(prediction, reference, header((1, 2, 3)))["prediction_ml"] == pytest.approx(0.018)


@pytest.mark.parametrize("prediction,reference,dice,precision,recall", [
    ([0, 0], [0, 0], 1.0, None, None),
    ([0, 0], [1, 0], 0.0, None, 0.0),
    ([1, 0], [0, 0], 0.0, 0.0, None),
    ([1, 1], [1, 1], 1.0, 1.0, 1.0),
])
def test_empty_and_perfect_mask_conventions(prediction, reference, dice, precision, recall):
    values = validator.independent_metrics(np.array(prediction, dtype=bool), np.array(reference, dtype=bool), header())
    assert values["dice_lesion"] == dice
    assert values["precision_lesion"] == precision
    assert values["recall_lesion"] == recall


def test_metrics_reject_ambiguous_units_and_broadcasting():
    with pytest.raises(ValueError, match="millimetre"):
        validator.independent_metrics(np.zeros(2, bool), np.zeros(2, bool), header(units="unknown"))
    with pytest.raises(ValueError, match="identical"):
        validator.independent_metrics(np.zeros((2, 1), bool), np.zeros(2, bool), header())


def test_methods_seeds_and_secondary_inventory():
    records = [dict(study=study, method=method, seed=seed) for study, method, seed in validator.EXPECTED_KEYS]
    assert len(records) == 20
    assert validator.record_keys_complete(records)
    assert not validator.record_keys_complete(records[:-1])
    assert not validator.record_keys_complete(records + records[:1])
    changed = [dict(row) for row in records]
    changed[0]["seed"] = 9
    assert not validator.record_keys_complete(changed)


def test_corrupted_metric_is_rejected():
    assert validator.number_matches("0.6666666666666666", 2 / 3)
    assert validator.number_matches(None, None)
    assert not validator.number_matches(None, 0)
    assert not validator.number_matches(0.6667, 2 / 3)
    assert not validator.number_matches(float("nan"), float("nan"))


def test_mesh_headers_and_truncated_bodies(tmp_path):
    ply = tmp_path / "sample.ply"
    ply.write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 3\nelement face 1\nend_header\n")
    assert validator.ply_counts(ply) == dict(vertex=3, face=1)
    ply.write_bytes(b"ply\nformat ascii 1.0\n")
    with pytest.raises(ValueError, match="Incomplete"):
        validator.ply_counts(ply)
    stl = tmp_path / "sample.stl"
    stl.write_bytes(bytes(80) + struct.pack("<I", 1) + bytes(50))
    assert validator.stl_count(stl) == 1
    stl.write_bytes(bytes(80) + struct.pack("<I", 1))
    with pytest.raises(ValueError, match="body size"):
        validator.stl_count(stl)
    stl.write_bytes(bytes(20))
    with pytest.raises(ValueError, match="Incomplete"):
        validator.stl_count(stl)


def test_reference_name_search_crosses_chunk_boundary(tmp_path):
    path = tmp_path / "viewer.html"
    marker = "Expert reference lesions (given labels)"
    path.write_bytes(b"a" * (1024 * 1024 - 8) + marker.encode() + b"</html>")
    assert validator.file_contains(path, marker)
    assert not validator.file_contains(path, "missing")


def test_geometry_headers_detect_bad_units_without_voxel_reads(monkeypatch):
    image = nib.Nifti1Image(np.zeros((1, 1, 1), np.uint8), np.diag([-1., 1., 1., 1.]))
    image.header.set_data_shape((182, 218, 182))
    image.header.set_xyzt_units("mm")
    monkeypatch.setattr(validator.nib, "load", lambda _: image)
    audit = validator.Audit()
    validator.geometry("unused", audit, "valid header")
    # The in-memory image shape comes from its data object, so native-grid shape
    # correctly fails even though the manually set header dimensions look valid.
    assert any("native 3D shape" in row["message"] for row in audit.failures)
    image.header.set_xyzt_units("unknown")
    audit = validator.Audit()
    validator.geometry("unused", audit, "bad header")
    assert any("spatial units" in row["message"] for row in audit.failures)


def test_audit_retains_actionable_expected_actual_values():
    audit = validator.Audit()
    audit.check(True, "pass")
    audit.check(False, "wrong Dice", expected=0.5, actual=0.2)
    assert audit.checked == 2
    assert audit.failures == [dict(message="wrong Dice", expected=0.5, actual=0.2)]


def test_cli_metadata_switch_and_manifest_default():
    arguments = validator.parser().parse_args(["--imaging-dir", "example", "--metadata-only"])
    assert arguments.metadata_only is True
    assert arguments.imaging_dir == Path("example")
    assert arguments.manifest.name == "mslesseg_case_manifest.json"
