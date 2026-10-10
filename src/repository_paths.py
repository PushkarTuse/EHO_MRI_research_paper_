"""Resolve repository and externally supplied dataset paths after relocation.

Historical measurement JSON/CSV files retain the original machine's paths.
This module translates those paths when reading files; it never edits evidence.
The dataset is deliberately external and selected with --dataset or
EHO_DATASET_PATH, with data/Task01_BrainTumour as the portable default.
"""
from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]


def dataset_path(override=None, *, root=None):
    """Return the external dataset location; explicit CLI input wins over env."""
    repository = Path(root or ROOT).resolve()
    value = override or os.environ.get("EHO_DATASET_PATH")
    return Path(value).expanduser().resolve() if value else repository / "data/Task01_BrainTumour"


def _contained(base, parts):
    """Reject traversal in relative paths and in relocated historical suffixes."""
    base = Path(base).resolve()
    candidate = base.joinpath(*parts).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError(f"Saved path escapes its allowed root: {parts!r}")
    return candidate


def resolve_saved_path(value, *, root=None, dataset=None, run=None, must_exist=True):
    """Read a saved file from the current clone instead of a former checkout.

    Native absolute paths inside an explicitly supplied run directory are
    accepted before relocating historical prefixes. Recognised historical
    prefixes end at code_reruns, the repository name or Task01_BrainTumour.
    Relative paths are confined to this repository. An
    unrecognised absolute path is rejected rather than opening an arbitrary
    location. File existence is checked unless explicitly disabled by a caller.
    """
    repository = Path(root or ROOT).resolve()
    raw = str(value).replace("\\", "/")
    parts = tuple(part for part in raw.split("/") if part)
    folded = [part.casefold() for part in parts]
    data_marker = "task01_braintumour"
    current = Path(raw)
    run_root = Path(run).resolve() if run is not None else None
    if run_root is not None and current.is_absolute() and current.resolve().is_relative_to(run_root):
        candidate = current.resolve()
    elif data_marker in folded:
        index = folded.index(data_marker)
        candidate = _contained(dataset_path(dataset, root=repository), parts[index + 1:])
    else:
        markers = {"code_reruns", "eho_mri_research_paper", repository.name.casefold()}
        indexes = [i for i, part in enumerate(folded) if part in markers]
        if indexes:
            candidate = _contained(repository, parts[indexes[-1] + 1:])
        elif Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute():
            # A native path inside the current checkout needs no old prefix.
            current = Path(raw).resolve()
            configured_data = dataset_path(dataset, root=repository)
            if not current.is_relative_to(repository) and not current.is_relative_to(configured_data):
                raise ValueError(f"Unrecognised external saved path: {value}")
            candidate = current
        else:
            candidate = _contained(repository, parts)
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"Resolved saved path does not exist: {candidate}")
    return candidate
