"""Independently validate saved masks, reported metrics and benchmark outputs.

Inputs: completed run directory. Outputs: validation.json plus a 3D static preview
for each case. This checks actual files, not just successful process exit codes.
Reference masks are used here only to recalculate evaluation after execution.
"""
from pathlib import Path
import argparse
import json
import hashlib
import sys
import numpy as np
import nibabel as nib
import pandas as pd
from imaging import segmentation_metrics, mesh_from_mask
from repository_paths import dataset_path, resolve_saved_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--dataset", type=Path, default=dataset_path(), help="Dataset location, or set EHO_DATASET_PATH")
    args = ap.parse_args()
    run = args.run.resolve()
    configuration = json.loads((run / 'environment.json').read_text())['args']
    checks = []
    def check(condition, label):
        checks.append({"check": label, "passed": bool(condition)})
    for name in ("continuous", "registration"):
        table = pd.read_csv(run / name / "runs.csv")
        matched = table[table.protocol == "matched_evaluations"]
        check(np.all(matched.evaluations == (configuration['budget'] if name == "continuous" else configuration['image_budget'])), name + " matched objective budgets")
        check(np.allclose(matched.objective, matched.returned_x_objective, rtol=1e-10, atol=1e-12), name + " returned candidate/objective consistency")
        check(np.isfinite(table.objective).all(), name + " finite measured objectives")
    routes = pd.read_csv(run / "routing/routing_runs.csv")
    corrected = routes[routes.tag == "new_corrective_permutation_adaptation"]
    check(corrected.feasible.all(), "all corrected final TSP/VRP routes feasible")
    check((corrected.objective_calls == configuration['budget']).all(), "corrected routing evaluation budgets")
    check(np.allclose(corrected.returned_objective, corrected.recomputed_objective), "corrected returned routing costs independently recomputed")
    exact = json.loads((run / "routing/routing_exact_8.json").read_text())
    check(np.isfinite(exact["value"]) and exact["value"] > 0, "eight-city exact optimum recorded")
    pdf = pd.read_csv(run / 'pdf_configs/pdf_tsp_runs.csv')
    completion = json.loads((run / 'pdf_configs/completion.json').read_text())
    check(not completion['failures'], 'PDF parameter harnesses completed without failure')
    check(pdf.feasible.all(), 'PDF TSP routes independently feasible')
    check(np.allclose(pdf.returned_objective, pdf.recomputed_objective), 'PDF TSP returned costs independently recomputed')
    check(set(pdf.pdf_configuration) == {'major','local'}, 'both additional PDF harnesses covered')
    images = run / "imaging"
    manifest = json.loads((images / "run_manifest.json").read_text())
    check(manifest["status"] == "completed", "MRI run completed")
    records = json.loads((images / "all_records.json").read_text())
    for row in records:
        prefix = f"{row['case_id']} {row['method']} seed{row['seed']}"
        prednii = nib.load(resolve_saved_path(row["prediction_path"], dataset=args.dataset, run=run))
        refnii = nib.load(images / row["case_id"] / "reference_whole_tumour.nii.gz")
        pred = np.asarray(prednii.dataobj)
        ref = np.asarray(refnii.dataobj)
        check(pred.shape == ref.shape and np.allclose(prednii.affine, refnii.affine), prefix + " geometry")
        check(set(np.unique(pred)).issubset({0, 1}), prefix + " binary saved prediction")
        independent = segmentation_metrics(pred > 0, ref > 0, refnii.affine)
        for metric in ("dice_whole_tumour", "iou_whole_tumour", "tp", "fp", "fn", "tn"):
            check(np.isclose(independent[metric], row["evaluation"][metric]), prefix + " " + metric)
        check(row.get("reference_evaluation_after_prediction") is True, prefix + " evaluation boundary recorded")
        if "enhancement" in row:
            check(row["enhancement"]["evaluations"] == manifest["budget_per_optimizer_stage"] and row["segmentation"]["evaluations"] == manifest["budget_per_optimizer_stage"], prefix + " measured stage budgets")
    for case in manifest["cases"]:
        folder = images / case["case_id"]
        source = nib.load(resolve_saved_path(case["image"], dataset=args.dataset))
        enhanced = list(folder.glob("*_enhanced_normalized_flair.nii.gz"))
        check(len(enhanced) == len(manifest["methods"]), case["case_id"] + " representative enhanced volumes saved")
        for file in enhanced:
            out = nib.load(file)
            data = np.asarray(out.dataobj)
            check(out.shape == source.shape[:3] and np.allclose(out.affine, source.affine), file.name + " original image geometry")
            check(np.isfinite(data).all() and data.min() >= 0 and data.max() <= 1, file.name + " bounded finite intensities")
        check((folder / "meshes/interactive_prediction_reference.html").stat().st_size > 10000, case["case_id"] + " self-contained interactive mesh")
        for file in (folder / "meshes").glob("*.ply"):
            import trimesh
            mesh = trimesh.load_mesh(file, process=False)
            check(np.isfinite(mesh.vertices).all() and len(mesh.faces) > 0, file.name + " exported mesh integrity")
        static_preview(folder)
    report = run / "reports"
    failures = [r for r in checks if not r["passed"]]
    bundle = {"src/" + p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")}
    (report / "validation.json").write_text(json.dumps({"checks": checks, "passed": len(checks)-len(failures), "failed": len(failures), "final_code_sha256": bundle}, indent=2), encoding="utf-8")
    print(f"Saved-output validation: {len(checks)-len(failures)} passed, {len(failures)} failed")
    if failures:
        print(json.dumps(failures, indent=2))
        raise SystemExit(1)


def static_preview(folder):
    """Render saved predicted/reference surfaces from the actual physical coordinates."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    pred_path = sorted(folder.glob("modified_eho_seed*_prediction.nii.gz"))[0]
    prednii = nib.load(pred_path)
    refnii = nib.load(folder / "reference_whole_tumour.nii.gz")
    surfaces = [mesh_from_mask(np.asarray(nii.dataobj) > 0, nii.affine, stride=2) for nii in (prednii,refnii)]
    all_vertices = np.concatenate([v for v,f in surfaces if len(v)])
    lo, hi = all_vertices.min(axis=0), all_vertices.max(axis=0)
    centre = (lo+hi)/2; radius = max(float((hi-lo).max())/2, 1)
    fig = plt.figure(figsize=(11, 5))
    for index, (nii, title, colour) in enumerate(((prednii, "Modified EHO: predicted threshold mask", "crimson"), (refnii, "Given reference: whole tumour", "royalblue"))):
        vertices, faces = surfaces[index]
        ax = fig.add_subplot(1, 2, index + 1, projection="3d")
        if len(vertices):
            ax.add_collection3d(Poly3DCollection(vertices[faces], facecolor=colour, edgecolor="none", alpha=.7))
        ax.set_xlim(centre[0]-radius,centre[0]+radius)
        ax.set_ylim(centre[1]-radius,centre[1]+radius)
        ax.set_zlim(centre[2]-radius,centre[2]+radius)
        ax.set_box_aspect((1,1,1)); ax.view_init(elev=25, azim=-55)
        ax.set(xlabel="World x (mm)", ylabel="World y (mm)", zlabel="World z (mm)", title=title)
    fig.suptitle(folder.name + " | display stride2; native masks used for evaluation")
    fig.tight_layout(); fig.savefig(folder / "meshes/prediction_reference_preview.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
