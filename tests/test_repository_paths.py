"""Relocation must find clone files and may not escape through saved suffixes."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repository_paths import dataset_path, resolve_saved_path


def test_clone_precedes_former_checkout(tmp_path):
    clone = tmp_path / "clone"
    target = clone / "results/run_20261005/mask.nii.gz"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"current clone")
    assert resolve_saved_path(r"D:\RANDOM\research_paper_iim\code_reruns\results\run_20261005\mask.nii.gz", root=clone) == target


def test_repository_prefix_and_relative_paths(tmp_path):
    target = tmp_path / "results/example.json"
    target.parent.mkdir()
    target.write_text("{}")
    assert resolve_saved_path("/old/EHO_MRI_research_paper/results/example.json", root=tmp_path) == target
    assert resolve_saved_path("results/example.json", root=tmp_path) == target


def test_dataset_override_and_environment(tmp_path, monkeypatch):
    external = tmp_path / "external"
    target = external / "imagesTr/BRATS_001.nii.gz"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"nifti")
    monkeypatch.setenv("EHO_DATASET_PATH", str(external))
    assert dataset_path(root=tmp_path) == external
    assert dataset_path(tmp_path / "explicit", root=tmp_path) == tmp_path / "explicit"
    assert resolve_saved_path(r"D:\MInor Project\datasets\New folder\Task01_BrainTumour\imagesTr\BRATS_001.nii.gz", root=tmp_path) == target


def test_default_dataset_is_clone_local(tmp_path, monkeypatch):
    monkeypatch.delenv("EHO_DATASET_PATH", raising=False)
    assert dataset_path(root=tmp_path) == tmp_path / "data/Task01_BrainTumour"


def test_current_external_dataset_with_different_folder_name(tmp_path):
    external = tmp_path / "data-renamed"
    target = external / "imagesTr/BRATS_001.nii.gz"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"nifti")
    assert resolve_saved_path(target, root=tmp_path / "clone", dataset=external) == target


@pytest.mark.parametrize("run_name", ["external-run", "code_reruns", "Task01_BrainTumour"])
def test_current_external_run_precedes_historical_markers(tmp_path, run_name):
    run = tmp_path / run_name
    target = run / "imaging/BRATS_001/modified_eho_seed0_prediction.nii.gz"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"fresh prediction")
    assert resolve_saved_path(target, root=tmp_path / "clone", run=run) == target


def test_external_run_does_not_allow_unrelated_file(tmp_path):
    unrelated = tmp_path / "unrelated/mask.nii.gz"
    unrelated.parent.mkdir()
    unrelated.write_bytes(b"unrelated")
    with pytest.raises(ValueError):
        resolve_saved_path(unrelated, root=tmp_path / "clone", run=tmp_path / "external-run")


def test_external_run_traversal_is_rejected(tmp_path):
    run = tmp_path / "external-run"
    with pytest.raises(ValueError):
        resolve_saved_path(run / "../outside.json", root=tmp_path / "clone", run=run, must_exist=False)


def test_external_run_missing_prediction_is_rejected(tmp_path):
    run = tmp_path / "external-run"
    with pytest.raises(FileNotFoundError):
        resolve_saved_path(run / "missing.nii.gz", root=tmp_path / "clone", run=run)


def test_explicit_run_preserves_historical_clone_relocation(tmp_path):
    clone = tmp_path / "clone"
    run = clone / "results/run_20261005"
    target = run / "imaging/BRATS_001/mask.nii.gz"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"published prediction")
    saved = "D:/former/code_reruns/results/run_20261005/imaging/BRATS_001/mask.nii.gz"
    assert resolve_saved_path(saved, root=clone, run=run) == target


@pytest.mark.parametrize("saved", ["../outside.json", "results/../../outside.json", "D:/old/code_reruns/../outside.json", "D:/old/Task01_BrainTumour/../outside.json"])
def test_traversal_is_rejected(tmp_path, saved):
    with pytest.raises(ValueError):
        resolve_saved_path(saved, root=tmp_path, dataset=tmp_path / "data", must_exist=False)


def test_unknown_absolute_path_rejected(tmp_path):
    with pytest.raises(ValueError):
        resolve_saved_path("D:/unrelated/file.json", root=tmp_path, must_exist=False)


def test_missing_clone_file_cannot_fall_back(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_saved_path("D:/old/code_reruns/results/missing.json", root=tmp_path)
