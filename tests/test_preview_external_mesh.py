"""Static previews use saved physical coordinates, separate labels and no raw GT."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import preview_external_mesh as preview


def test_two_cube_preview_preserves_world_coordinates_and_reference_label(tmp_path):
    case = tmp_path / "P1_T1"
    (case / "meshes").mkdir(parents=True)
    meshes = {}
    for name, center, extent in (("image_foreground", [30., -20., 60.], [20., 30., 40.]),
                                 ("modified_eho_prediction", [32., -20., 63.], [6., 8., 10.]),
                                 ("reference_lesion", [27., -19., 59.], [2., 3., 4.])):
        mesh = trimesh.creation.box(extents=extent)
        mesh.apply_translation(center)
        mesh.export(case / "meshes" / (name + ".ply"))
        meshes[name] = {"status": "exported", "actual_stride": 1 if name == "reference_lesion" else 2}
    (case / "meshes/mesh_manifest.json").write_text(json.dumps({"coordinate_units": "mm", **meshes}))
    affine = np.diag([-2., 3., 4., 1.])
    affine[:3, 3] = [40., -30., 40.]
    (case / "case_manifest.json").write_text(json.dumps({"shape": [20, 20, 20], "affine": affine.tolist()}))
    result = preview.render_case(case, "Synthetic two-cube geometry check", max_faces=6, dpi=60)
    assert (case / "preview3D.png").stat().st_size > 1000
    assert (case / "meshes/prediction_reference_preview.png").exists()
    assert result["reference_label_volume_opened"] is False
    assert result["predictions_or_metrics_recomputed"] is False
    assert result["surfaces"]["reference_lesion"]["saved_faces"] == result["surfaces"]["reference_lesion"]["rendered_faces"]
    np.testing.assert_allclose(result["surfaces"]["modified_eho_prediction"]["world_bounds"], [[29., -24., 58.], [35., -16., 68.]])
    np.testing.assert_allclose(result["axis_bounds_world_mm"], [[1., -31.5, 38.], [41., 28.5, 118.]])
    assert result["surfaces"]["reference_lesion"]["source_display_stride"] == 1


def test_postcohort_descriptive_selection_is_labelled_and_uses_patient_earliest_sessions(tmp_path):
    cases = [dict(case_id="P10_T1", subject_id="P10", session_id="T1"),
             dict(case_id="P1_T2", subject_id="P1", session_id="T2"),
             dict(case_id="P1_T1", subject_id="P1", session_id="T1"),
             dict(case_id="P2_T1", subject_id="P2", session_id="T1")]
    manifest = {"status": "running", "cases": cases}
    (tmp_path / "run_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="completed cohort"):
        preview.descriptive_cases(tmp_path)
    manifest["status"] = "completed"
    (tmp_path / "run_manifest.json").write_text(json.dumps(manifest))
    import csv
    with (tmp_path / "all_runs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "method", "study", "dice_lesion"])
        writer.writeheader()
        for identifier, dice in (("P1_T1", .2), ("P1_T2", .99), ("P2_T1", .1), ("P10_T1", .5)):
            writer.writerow(dict(case_id=identifier, method="modified_eho", study="primary_largest_6_connected_component", dice_lesion=dice))
    selected = preview.descriptive_cases(tmp_path)
    assert selected[0][0].name == "P1_T1"
    assert "P1_T2" not in {path.name for path, label in selected}
    assert any("lowest" in label and path.name == "P2_T1" for path, label in selected)
    assert any("highest" in label and path.name == "P10_T1" for path, label in selected)
