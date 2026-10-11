"""Release restoration must preserve existing files and reject unsafe ZIP paths."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "tools/restore_external_release.py"


def fixture_release(tmp_path, member="results/example/measurement.csv"):
    payload = b"patient,value\nP1,0.0289\n"
    assets = tmp_path / "assets"
    assets.mkdir()
    archive = assets / "part.zip"
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr(member, payload)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"assets": [{"asset": archive.name, "size_bytes": archive.stat().st_size,
        "sha256": sha(archive.read_bytes()), "files": [{"path": member, "size_bytes": len(payload), "sha256": sha(payload)}]}]}))
    destination = tmp_path / "clone"
    command = [sys.executable, str(SCRIPT), "--assets", str(assets), "--manifest", str(manifest), "--destination", str(destination)]
    return command, destination, member, payload


def test_restores_original_bytes_and_preserves_identical_existing(tmp_path):
    command, destination, member, payload = fixture_release(tmp_path)
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert (destination / member).read_bytes() == payload
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert '"preserved_identical_files": 1' in second.stdout


def test_refuses_to_overwrite_user_modified_measurement(tmp_path):
    command, destination, member, _ = fixture_release(tmp_path)
    path = destination / member
    path.parent.mkdir(parents=True)
    path.write_bytes(b"user measurement")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Refusing to overwrite" in result.stderr
    assert path.read_bytes() == b"user measurement"


def test_rejects_traversal_before_creating_external_file(tmp_path):
    command, destination, member, _ = fixture_release(tmp_path, "../outside.txt")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Unsafe ZIP member" in result.stderr
    assert not (destination.parent / "outside.txt").exists()
