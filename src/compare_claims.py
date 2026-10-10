"""Compare actual reruns with the original manuscript without relabelling evidence.

Inputs: a completed run directory, preserved source replay and original manuscript.
Outputs: claim-level CSV, human-readable verification report, measured summary
tables and an output manifest. Historical plotting constants are never treated
as freshly measured image quality. Patient and seed variability remain distinct.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import zipfile
from xml.etree import ElementTree as ET
import numpy as np
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "manuscripts"


def markdown(frame, columns=None):
    if frame.empty:
        return "No completed measurements in this table.\n"
    frame = frame[columns] if columns else frame
    def cell(value):
        if pd.isna(value): return "—"
        if isinstance(value, (float, np.floating)): return f"{value:.6g}"
        return str(value).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(frame.columns) + " |", "| " + " | ".join("---" for _ in frame.columns) + " |"]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None)]
    return "\n".join(lines) + "\n"


def read_csv(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    report = run / "reports"
    report.mkdir(exist_ok=True)
    original = PROJECT / "without_citations_draft.pdf"
    pages = [p.extract_text() or "" for p in PdfReader(original).pages]
    (ROOT / "sources/original_manuscript_extracted.txt").write_text("\n\n".join(f"PDF PAGE {i+1}\n{p}" for i,p in enumerate(pages)), encoding="utf-8")
    rewritten = PROJECT / "without_citations_draft_rewritten.docx"
    if rewritten.exists():
        with zipfile.ZipFile(rewritten) as archive:
            tree = ET.fromstring(archive.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = ["".join(p.itertext()) for p in tree.findall(".//w:p", ns)]
        # Only Word text elements, excluding XML indentation/attributes.
        paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", ns)) for p in tree.findall(".//w:p", ns)]
        (ROOT / "sources/rewritten_manuscript_extracted.txt").write_text("\n".join(paragraphs), encoding="utf-8")
    claims = [
        ("Sections 3–5; Tables 1–2; Figure 1", "EHO gives the best TSP distance and runtime at all sizes", "10–100-city table; EHO 3200.4567 at 80, 2680.2345 at 90", "Not established", "Source variants differ; singleton clans disable follower operations in notebook cell33. New valid routes and equal-budget results are reported separately. Historical tables have no recoverable complete seed/configuration provenance.", "routing/routing_runs.csv; snippets/snippet_runs.csv; source_replay/cell_033_output.txt"),
        ("Section 5.2; Figures 2–3", "Capacity-feasible VRP and EHO superiority", "EHO 523.85; PSO 693.38", "Historical comparison invalid as evidence of constrained superiority", "Recovered VRP cost accepts omitted/duplicated customers and does not enforce demand/capacity. Rerun feasibility is explicitly checked; corrected capacity-decoded experiments are new measurements.", "routing/routing_routes_and_validation.json; routing/routing_defect_demonstrations.json"),
        ("Section 6.1; Table 3; Figure 4", "Rastrigin convergence advantage", "Historical iteration checkpoints 1,200,400,600,800,1000", "Configuration-dependent; fresh replication provided", "Cells6/7 are rerun unchanged with three controlled seeds. Shared-budget reference implementations and shifted-function ablations are distinct. Origin-centred functions favour centre contraction; no universal superiority follows.", "continuous/summary.csv; continuous/raw/; ablations/summary.csv"),
        ("Section 6.2; Table 4; Figure 5", "Lowest Ackley value also means best efficiency", "EHO 4.80/0.21845s; PSO 5.09/0.11082s; GA 15.81/0.09717s; ACO 19.94/0.52352s", "Historical table already contains a quality/time trade-off", "EHO is slower than GA and PSO in that table. Figure5 plots objective values although caption says execution time. Reruns measure objective, consistent returned position, evaluations and timing independently.", "continuous/runs.csv; source_replay/cell_002_output.txt"),
        ("Section 7; Figures 6–8", "Medical registration robustness and EHO superior accuracy", "MSE PSO .133565; EHO .135149; GA .134779; ACO .138497", "Synthetic source experiment; universal accuracy claim contradicted by listed numbers", "Source uses a generated random field, integer circular shifts and EHO20 vs others50 requested iterations. PSO and GA have lower historical MSE than EHO. Added anatomical experiment is one slice with a known imposed rigid transform, not clinical registration validation.", "registration/summary.csv; registration/anatomical_geometry_summary.csv; source_replay/cell_015_output.txt"),
        ("Section 7.6.3; Figure 9", "50 independent images demonstrate scalability and parallel efficiency", "EHO17s; PSO68s; GA60s; ACO>50s", "Workload replay only", "Generator resets seed42 on each call, producing repeated identical inputs. Search budgets differ and no parallel executor is used in the recovered workload. Source replay saves actual current elapsed times.", "source_replay/cell_017_output.txt; source_replay/cell_017_values.json"),
        ("Section 8.3.1; Figure 10", "Measured MRI enhancement PSNR/SSIM", "EHO/PSO13.72dB,.67; GA14.33dB,.89", "Underlying historical measurements not recoverable", "Plotting code contains literal values and labels error bars hypothetical. Fresh input-versus-enhanced PSNR/SSIM measure similarity to normalized input; they do not establish denoising or reproduce the historical contrast/noise objective.", "source_replay/cell_023_figure_009.png; imaging/all_runs.csv"),
        ("Section 8.3.2; Figure 11", "EHO fastest enhancement and real-time readiness", "EHO .3004s; GA .3948s; PSO .6414s", "Literal plotting constants, not recovered timing logs", "New whole-volume processing timing, optimiser timing, RSS and export overhead are separately recorded. Different tasks/hardware/implementation prevent validation of the old per-slice times. Clinical real-time readiness is not tested.", "imaging/all_records.json; imaging/run_manifest.json"),
        ("Section 8.3.3; Figure 12", "Noise suppression with anatomical preservation", "Original slice71 and enhanced images", "Qualitative historical images; new contrast baseline evaluated", "Original case/modality/noise model is unspecified. New case IDs, FLAIR channel, normalization, fixed objective and image-only slice choices are recorded. No clean denoising reference was found.", "imaging/BRATS_001/*_slice_*.png; sources/major_last_codes_pages.json"),
        ("Section 8.4; Figure 13", "Single-slice 3D surface proves reconstruction fidelity", "Individual slice model", "Surface generation is recoverable in concept, fidelity claim unestablished", "Existing EHO/PSO STL pairs are byte-identical and span only z0–3 in stored coordinates. New full-volume Marching Cubes meshes use NIfTI affine; mesh display resolution is declared and masks are evaluated at native resolution.", "existing_meshes/mesh_audit.json; imaging/BRATS_001/meshes/"),
        ("Sections 8.5–8.6; Figures 14–15", "Optimised brain tumour detection, localisation and surgical planning", "Whole brain and tumour-region pictures", "New segmentation evaluated; historical clinical claim unsupported", "No recovered tumour-prediction implementation exists in supplied sources. A new image-only FLAIR/Otsu/connected-component baseline supplies predicted masks; label>0 references are evaluated only after predictions. Given reference labels are never called detected tumours.", "imaging/per_case_seed_summary.csv; imaging/across_case_summary.csv; imaging/*/meshes/"),
        ("Section 4; contributions and conclusion", "Dimensional scaling and adaptive control cause robust convergence improvements", "Dimensionality exponent, attraction schedule, repulsion/separation", "New reconstructed hypothesis tested explicitly", "Supplied task-specific source bodies do not implement the complete stated formulation. Prespecified new reference algorithms and leave-one-component-out/shifted-function experiments establish only their measured behaviour at declared settings.", "continuous/raw/; ablations/protocol.json; ablations/summary.csv"),
    ]
    frame = pd.DataFrame(claims, columns=["Manuscript location", "Claim", "Historical number or output", "Audit conclusion", "Reason and rerun interpretation", "Evidence files"])
    frame.to_csv(report / "claim_comparison.csv", index=False)
    source_ledger = json.loads((ROOT / 'results/source_replay/execution_ledger.json').read_text())
    source_counts = {status: sum(r['status'] == status for r in source_ledger) for status in sorted({r['status'] for r in source_ledger})}
    image_case = read_csv(run / 'imaging/per_case_seed_summary.csv')
    image_across = read_csv(run / 'imaging/across_case_summary.csv')
    registration_geometry = read_csv(run / 'registration/anatomical_geometry_summary.csv')
    key_findings = ["## Main measured findings", ""]
    if not image_across.empty:
        key = image_across[['method','n_cases','dice_whole_tumour_case_mean','dice_whole_tumour_case_sd','enhancement_seconds_case_mean','segmentation_seconds_case_mean']]
        mod = image_across[image_across.method == 'modified_eho'].iloc[0]
        direct = image_across[image_across.method == 'direct_otsu'].iloc[0]
        key_findings += [markdown(key), f"Modified EHO's newly reconstructed contrast/threshold pipeline achieves mean whole-tumour Dice {mod.dice_whole_tumour_case_mean:.3f} across {int(mod.n_cases)} cases, compared with {direct.dice_whole_tumour_case_mean:.3f} for direct Otsu. Modified EHO takes about {mod.enhancement_seconds_case_mean + mod.segmentation_seconds_case_mean:.3f}s for enhancement plus segmentation, while direct Otsu's segmentation takes about {direct.segmentation_seconds_case_mean:.3f}s and omits enhancement. These are distinct processing paths. These measurements determine whether there is an advantage over the simple deterministic baseline; the source report does not assume one. Other stochastic methods can reach almost identical histogram partitions and masks; equal masks are an observed outcome, not invented independent improvements.", ""]
        selected = image_case[image_case.method.isin(['modified_eho','direct_otsu'])][['case_id','method','n_seeds','dice_whole_tumour_mean','dice_whole_tumour_seed_sd','precision_whole_tumour_mean','recall_whole_tumour_mean']]
        key_findings += ["Per-case overlap shows why the cohort mean alone is insufficient:", "", markdown(selected)]
    if not registration_geometry.empty:
        geometry = registration_geometry.set_index('method')['mean']
        key_findings += [f"In the new anatomical rigid-perturbation test, modified EHO has mean geometric grid error {geometry['modified_eho']:.4g} resized pixels; PSO {geometry['pso']:.4g}, ACOR {geometry['acor']:.4g} and GA {geometry['ga']:.4g}. The numbers quantify performance on this declared transform-recovery task, rather than demonstrating a general or clinical registration result.", ""]
    key_findings += ["Modified EHO attains low objectives on unshifted Ackley/Rastrigin but loses that advantage on the prespecified translated functions. This exposes origin sensitivity and prevents a general superiority conclusion. Component ablations and full seed distributions are included below. Historical VRP route infeasibility and hardcoded MRI plotting values remain separate issues that new successful execution cannot repair retrospectively.", ""]
    lines = ["# Manuscript claims versus actual code reruns", "",
             "These are fresh runs on the local CPU. Recovered code, repaired constraints and newly reconstructed MRI experiments have separate provenance. The original manuscript and images were not overwritten. Historical constants are retained as historical constants. No measurement has been invented to reconcile a discrepancy.", "",
             "## Execution coverage", "",
             "The original MRI notebook's 33 code cells were replayed in order; plots, stdout and a cell ledger are in `results/source_replay`. The brute-force source's invalid matrix/syntax are preserved and diagnosed; its exact solver is exercised on a valid eight-city instance. Newly supplied 15/95-city TSP snippets are faithfully replayed. Controlled routing, continuous optimisation, synthetic/anatomical registration, whole-volume enhancement, image-only segmentation and 3D export have fresh logged outputs.", "",
             f"Original notebook replay outcomes: {source_counts}. Cell10's forward dependency failure is retained; its executable PSO operator equivalent is covered by cell11. See `reports/pdf_code_coverage.md` for source correspondence, duplicate definitions and PDF-specific parameter harnesses.", "",
             "MRI evaluation uses the first three lexically selected labelled Task01_BrainTumour cases (001–003), with three seeds per optimiser and a deterministic Otsu baseline. All 484 listed image/label pairs were inventoried; this run does not evaluate all 484. Case variation and search-seed variation are reported separately. Registration uses one anatomical slice with synthetic perturbation. No ML/DL comparison or clinical performance study has been run.", "",
             *key_findings, "## Claim-level findings", "", markdown(frame), "## Measured summaries", ""]
    for title, relative in [("Continuous objectives: source and matched budgets", "continuous/summary.csv"), ("Registration: source and matched budgets", "registration/summary.csv"), ("Geometric registration error (grid points, resized pixels)", "registration/anatomical_geometry_summary.csv"), ("MRI whole-tumour segmentation: patient means", "imaging/across_case_summary.csv"), ("MRI seed variation within each patient", "imaging/per_case_seed_summary.csv"), ("Component ablations and shifted objectives", "ablations/summary.csv")]:
        table = read_csv(run / relative)
        lines += ["### " + title, "", markdown(table)]
    routes = read_csv(run / "routing/routing_runs.csv")
    if not routes.empty:
        summary = routes.groupby(["tag", "task", "size", "method"]).agg(runs=("seed", "size"), feasible_runs=("feasible", "sum"), objective_mean=("returned_objective", "mean"), objective_sd=("returned_objective", "std"), time_mean_s=("elapsed_seconds_instrumented", "mean"), objective_calls_mean=("objective_calls", "mean"), invalid_calls_mean=("invalid_calls", "mean")).reset_index()
        summary.to_csv(report / "routing_summary.csv", index=False)
        lines += ["### Routing: feasibility must precede cost ranking", "", markdown(summary), "A cost from an infeasible route cannot be interpreted as a valid solution. Instrumented source timings include validation/profiling overhead and unequal search budgets.", ""]
    image = read_csv(run / "imaging/all_runs.csv")
    if not image.empty:
        timing_columns = [c for c in image if c.endswith("_seconds") or "psnr" in c or "ssim" in c]
        means = image.groupby(["case_id", "method"])[timing_columns].mean().reset_index()
        means.to_csv(report / "imaging_quality_time_by_case.csv", index=False)
        lines += ["### Imaging appearance and stage time (mean over seeds)", "", markdown(means), "Input similarity is a measure of departure from the input image. It is not noise-removal accuracy. Enhancement/segmentation times and process RSS are implementation measurements; end-to-end time also includes input/output, evaluation and mesh rendering.", ""]
    lines += ["## Scientific interpretation", "",
              "Successful execution does not confirm the manuscript's universal superiority claims. Historical feasibility defects, constant-only MRI graphs and absent measurement provenance require revision of those claims. Fresh valid-route and image-mask results may be cited with their new protocol; they cannot be retroactively assigned to the original figures. A threshold segmentation surface is a useful reproducible baseline, but anatomical overlap determines its accuracy. Mesh smoothness or visual resemblance alone does not establish tumour detection or surgical suitability.", "",
              "Five seeds give limited evidence about optimiser randomness. The continuous paired Wilcoxon tests include Holm adjustment and remain exploratory. Three patients cannot establish clinical generalization. All label-dependent metrics are evaluation only; no learned training, trained checkpoint or downstream diagnosis was introduced.", "",
              "## Primary implementation references", "",
              "Coordinate transforms follow the [NiBabel coordinate-system documentation](https://nipy.org/nibabel/coordinate_systems.html). Surface extraction follows [scikit-image Marching Cubes](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes). Dataset label/modality mapping and licensing are taken from the local `dataset.json`; labels are 0,1,2,3 in this Task01 release, rather than an assumed label4 mapping.", ""]
    lines += ['## Modality axis versus spatial depth', '', 'The screenshot on PDF page92 (printed page82) explicitly reports the enhanced slice and Mayavi input shape as (240,240,4). Task01 supplies four modalities per spatial slice, while the selected native image shape is (240,240,155,4). A four-channel slice must not be treated as four anatomical depth slices. Existing thin STL geometry with z extent0–3 is consistent with a possible modality/depth-axis confusion, but the absent original mesh source prevents proving its generating operation. The new pipeline extracts FLAIR[...,0] and preserves all155 spatial slices, image affine and q/s forms before surface extraction.', '']
    pdf_config = read_csv(run / 'pdf_configs/pdf_tsp_runs.csv')
    if not pdf_config.empty:
        pdf_summary = pdf_config.groupby(['pdf_configuration','size','method']).agg(runs=('seed','size'),cost_mean=('returned_objective','mean'),cost_sd=('returned_objective','std'),feasible=('feasible','sum'),calls_mean=('objective_calls','mean')).reset_index()
        lines += ['## Additional PDF configuration replays', '', markdown(pdf_summary), 'These recover the PDF harness settings separately from the notebook defaults. Operator/configuration correspondence is documented in `reports/pdf_code_coverage.md`.', '']
    dormant = read_csv(run / 'pdf_configs/registration_variants/summary.csv')
    if not dormant.empty:
        lines += ['### Overwritten source registration definitions', '', markdown(dormant), 'These previously dormant function groups are new seeded experiments on recovered function bodies. Their outcomes are not historical experiments simply because the definitions appear earlier in a notebook.', '']
    (report / "CLAIMS_VS_RERUNS.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size} for p in run.rglob("*") if p.is_file()]
    (report / "output_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Comparison saved: {report / 'CLAIMS_VS_RERUNS.md'}")


if __name__ == "__main__":
    main()
