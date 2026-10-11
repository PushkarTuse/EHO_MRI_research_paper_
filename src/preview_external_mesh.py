"""Static physical-coordinate previews from saved external prediction/reference PLYs.

No browser, raw reference labels or segmentation recomputation is involved.
--case-dir renders one saved case. --run selects explicitly labelled first,
median, lowest and highest Dice examples only after the cohort run completes.
Those descriptive selections never change predictions, metrics or inference.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

import numpy as np
import trimesh


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def read_surface(case_dir, manifest, name):
    detail = manifest.get(name, {})
    if detail.get("status") == "empty_mask_no_surface":
        return np.empty((0, 3)), np.empty((0, 3), dtype=int)
    path = Path(case_dir) / "meshes" / (name + ".ply")
    if not path.exists():
        raise FileNotFoundError("Saved PLY missing: " + str(path))
    mesh = trimesh.load_mesh(path, process=False)
    vertices, faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    if not np.isfinite(vertices).all() or vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("Saved surface must contain finite world-coordinate vertices")
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("Saved surface must contain triangular faces")
    return vertices, faces


def source_world_bounds(case_dir, surfaces):
    """Use the saved source affine/shape; no reference-volume voxel access."""
    path = Path(case_dir) / "case_manifest.json"
    if path.exists():
        metadata = json.loads(path.read_text(encoding="utf-8"))
        shape, affine = np.asarray(metadata.get("shape", [])), np.asarray(metadata.get("affine", []))
        if shape.shape == (3,) and affine.shape == (4, 4) and np.isfinite(affine).all():
            from itertools import product
            corners = np.asarray(list(product(*[(-.5, float(size)-.5) for size in shape])))
            world = corners @ affine[:3, :3].T + affine[:3, 3]
            return world.min(axis=0), world.max(axis=0), "supplied image-grid voxel-edge bounding box from saved affine and shape"
    vertices = [vertices for vertices, faces in surfaces if len(vertices)]
    if not vertices:
        return np.full(3, -1.), np.full(3, 1.), "empty saved surfaces; default box"
    world = np.concatenate(vertices)
    low, high = world.min(axis=0), world.max(axis=0)
    pad = np.maximum((high-low)*.04, 1.)
    return low-pad, high+pad, "saved mesh world-coordinate union plus display margin"


def draw_surface(axis, surface, colour, alpha, max_faces=None):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    vertices, faces = surface
    step = max(1, math.ceil(len(faces)/max_faces)) if max_faces else 1
    retained = faces[::step]
    if len(retained):
        axis.add_collection3d(Poly3DCollection(vertices[retained], facecolor=colour, edgecolor="none", alpha=alpha, rasterized=True))
    return {"saved_vertices": len(vertices), "saved_faces": len(faces), "rendered_faces": len(retained),
            "display_face_sampling_step": step, "coordinate_transform_applied": False,
            "world_bounds": [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()] if len(vertices) else None}


def case_dice_from_csv(case_dir):
    path = Path(case_dir).parent / "all_runs.csv"
    if not path.exists():
        return None
    values = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("case_id") == Path(case_dir).name and row.get("method") == "modified_eho" and row.get("study") == "primary_largest_6_connected_component":
                try:
                    values.append(float(row["dice_lesion"]))
                except (ValueError, TypeError):
                    continue
    return float(np.mean(values)) if values else None


def render_case(case_dir, selection_label="Explicit case preview", max_faces=100000, dpi=140):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    case_dir = Path(case_dir).resolve()
    manifest = json.loads((case_dir / "meshes/mesh_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("coordinate_units") != "mm":
        raise ValueError("Mesh manifest must explicitly declare millimetre world coordinates")
    names = ("image_foreground", "modified_eho_prediction", "reference_lesion")
    surfaces = {name: read_surface(case_dir, manifest, name) for name in names}
    low, high, bound_rule = source_world_bounds(case_dir, list(surfaces.values()))
    if np.any(high <= low):
        raise ValueError("Display bounding box must have positive extent")
    figure = plt.figure(figsize=(12, 6), constrained_layout=True)
    records = {}
    for index, (name, title, colour) in enumerate((("modified_eho_prediction", "Modified EHO: predicted threshold mask", "crimson"),
                                                  ("reference_lesion", "Expert reference lesions (given labels)", "royalblue"))):
        axis = figure.add_subplot(1, 2, index+1, projection="3d")
        context = draw_surface(axis, surfaces["image_foreground"], "gray", .04, max_faces)
        # Every saved reference triangle is retained to keep separate tiny lesions.
        records[name] = draw_surface(axis, surfaces[name], colour, .58 if index == 0 else .85, max_faces if index == 0 else None)
        records[name]["source_display_stride"] = manifest.get(name, {}).get("actual_stride")
        axis.set(xlim=(low[0], high[0]), ylim=(low[1], high[1]), zlim=(low[2], high[2]),
                 xlabel="World x (mm)", ylabel="World y (mm)", zlabel="World z (mm)", title=title)
        axis.set_box_aspect(high-low)
        axis.view_init(elev=22, azim=-58)
        if not len(surfaces[name][0]):
            axis.text2D(.5, .48, "Empty mask: no saved surface", transform=axis.transAxes, ha="center", color=colour)
    records["image_foreground"] = context
    dice = case_dice_from_csv(case_dir)
    metric_note = "" if dice is None else f" | primary seed-mean Dice {dice:.4f}"
    figure.suptitle(f"{case_dir.name} | {selection_label}{metric_note}\nSeparate saved prediction and expert reference; supplied MNI-grid coordinates", fontsize=12)
    preview = case_dir / "preview3D.png"
    figure.savefig(preview, dpi=dpi)
    # Conventional location is recognized by the results dashboard.
    compatible = case_dir / "meshes/prediction_reference_preview.png"
    figure.savefig(compatible, dpi=dpi)
    plt.close(figure)
    record = {"case_id": case_dir.name, "selection_label": selection_label, "primary_seed_mean_dice": dice,
              "preview_path": str(preview), "dashboard_preview_path": str(compatible), "coordinate_units": "mm",
              "axis_bounds_world_mm": [low.tolist(), high.tolist()], "axis_bounds_rule": bound_rule,
              "reference_label_volume_opened": False, "predictions_or_metrics_recomputed": False,
              "geometry": "saved PLY world coordinates used directly; no affine applied twice", "surfaces": records,
              "display_only_face_budget": max_faces, "reference_faces_sampled": False}
    write_json(case_dir / "preview3D_manifest.json", record)
    print(json.dumps({"case_id": case_dir.name, "preview": str(preview)}), flush=True)
    return record


def natural_key(value):
    return tuple((1, int(part)) if part.isdigit() else (0, part.casefold()) for part in re.split(r"(\d+)", str(value)) if part)


def descriptive_cases(run):
    """Select postcohort examples among prespecified earliest patient sessions."""
    run = Path(run).resolve()
    metadata = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "completed":
        raise ValueError("Descriptive best/median/worst selections require a completed cohort run")
    cases = metadata.get("cases", metadata.get("protocol", {}).get("cases", []))
    if not cases:
        raise ValueError("Run manifest must contain prespecified cases")
    ordered = sorted(cases, key=lambda case: (natural_key(case["subject_id"]), natural_key(case["session_id"]), natural_key(case["case_id"])))
    earliest = {}
    for case in ordered:
        earliest.setdefault(case["subject_id"], case["case_id"])
    values = {}
    with (run / "all_runs.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("method") == "modified_eho" and row.get("study") == "primary_largest_6_connected_component" and row["case_id"] in earliest.values():
                values.setdefault(row["case_id"], []).append(float(row["dice_lesion"]))
    means = sorted((float(np.mean(observed)), identifier) for identifier, observed in values.items())
    if not means:
        raise ValueError("No primary modified-EHO earliest-session Dice measurements available")
    selections = {}
    first = next(iter(earliest.values()))
    requested = [(first, "First patient in natural numeric subject order; earliest session"),
                 (means[(len(means)-1)//2][1], "Descriptive median primary patient seed-mean Dice"),
                 (means[0][1], "Descriptive lowest primary patient seed-mean Dice"),
                 (means[-1][1], "Descriptive highest primary patient seed-mean Dice")]
    for identifier, label in requested:
        selections.setdefault(identifier, []).append(label)
    return [(run / identifier, "; ".join(labels)) for identifier, labels in selections.items()]


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    group = result.add_mutually_exclusive_group(required=True)
    group.add_argument("--case-dir", type=Path)
    group.add_argument("--run", type=Path, help="Completed imaging root; render first/median/lowest/highest descriptive patient cases")
    result.add_argument("--label", default="Explicit case preview")
    result.add_argument("--max-faces", type=int, default=100000, help="Display-only context/prediction face limit; reference retains all saved faces")
    result.add_argument("--dpi", type=int, default=140)
    return result


def main(args):
    if args.max_faces < 1 or args.dpi < 40:
        raise ValueError("max-faces must be positive and dpi >=40")
    cases = descriptive_cases(args.run) if args.run else [(args.case_dir, args.label)]
    records = [render_case(directory, label, args.max_faces, args.dpi) for directory, label in cases]
    if args.run:
        write_json(Path(args.run) / "descriptive_preview_selection.json", {"selection_role": "postcohort descriptive examples only; no effect on metrics or inference", "cases": records})
    return records


if __name__ == "__main__":
    main(parser().parse_args())
