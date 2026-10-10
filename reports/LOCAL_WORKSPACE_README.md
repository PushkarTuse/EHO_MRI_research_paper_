# Research code recovery and measured reruns

Everything for this execution is in `D:\RANDOM\research_paper_iim\code_reruns`.
The dataset remains at `D:\MInor Project\datasets\New folder\Task01_BrainTumour`.
It was already available locally: all 484 listed training image/label pairs exist.
No download was necessary.

## Start with these files

- `reports/CODE_INVENTORY.md`: source-to-use-case checklist, recovered code cells and reconstructed stages.
- `results/run_20261005/reports/CLAIMS_VS_RERUNS.md`: historical claims versus actual measured results.
- `results/run_20261005/reports/claim_comparison.csv`: claim-level evidence table.
- `results/run_20261005/stage_ledger.json`: exact executed commands, return codes and elapsed stage times.
- `results/run_20261005/logs/`: full stdout/stderr for each stage.
- `results/run_20261005/imaging/BRATS_001/meshes/interactive_prediction_reference.html`: interactive brain/prediction/reference models; equivalent files are saved for cases 002 and 003.
- `results/run_20261005/imaging/all_runs.csv`: actual segmentation, appearance, time and resource metrics.
- `ALL_CODE_WITH_COMMENTS.md`: consolidated readable listing of all runnable modules.
- `CODE_BUNDLE.zip`: code, tests, notes and preserved text sources; the dataset and environment are not duplicated.

The executed package passes 72 unit checks and 552 independent saved-output checks.
Successful file validation does not imply that EHO wins the comparisons. The new MRI
baseline has mean Dice0.737 versus direct Otsu0.752 across the three evaluated cases;
the detailed report also records poor shifted-function and anatomical-registration
results for the reconstructed modified EHO setting.

## What was recovered and what was implemented

| Use case | Recovered source | Executable module | Output |
|---|---|---|---|
| Notebook replay | Original two notebooks; 35 code cells preserved individually | `src/replay_sources.py` | `results/source_replay`: 33-cell ledger, plots and stdout; brute-source diagnosis |
| Added 15/95-city TSP programs | `code_snippets.txt`, original bytes preserved | `src/replay_snippets.py` | `results/run_20261005/snippets`: routes, actual objective calls, validity and timing |
| Additional PDF configurations and dormant definitions | PDF TSP parameter harnesses and overwritten registration function groups | `src/replay_pdf_configs.py` | `results/run_20261005/pdf_configs`: distinct configurations, earlier registration variants, source correspondence |
| Exact small TSP | Original brute-force function; malformed original matrix separately diagnosed | `src/routing.py` | Exact eight-city optimum and heuristic gaps |
| Original TSP EHO/GA/PSO/ACO | Notebook cells 28/33 and added snippets | `src/routing.py`, `src/replay_snippets.py` | Unchanged-body reruns with independent route checks |
| Corrected discrete TSP/VRP | New feasibility-preserving adaptations | `src/routing.py` | Equal-budget tours and capacity-feasible routes, convergence and raw results |
| Original VRP EHO/PSO | Notebook cell 11 | `src/routing.py` | Explicit omissions/duplicates/capacity diagnostics; invalid cost is not ranked as valid |
| Original Rastrigin/Ackley | Notebook cells 2/6/7 | `src/benchmarks_continuous.py` | Returned versus re-evaluated values, evaluation counts, three seeds |
| Shared-budget optimisers | New reference EHO, draft-inspired modified EHO, PSO, GA and ACOR-inspired implementations | `src/optimizers.py` | Copied best evaluated candidates, bounds, configuration and complete histories |
| Controlled numerical comparison | New reference implementations with equal search budget | `src/benchmarks_continuous.py` | Five seeds, mean ± SD, convergence, exploratory paired tests with Holm correction |
| Component ablations / origin bias | New prespecified leave-one-component-out and shifted-function tests | `src/ablations.py` | Fixed shifts, six variants, raw histories and statistics |
| Original synthetic registration / workload scaling | Notebook cells 15/17 | `src/registration.py`, `src/replay_sources.py` | Source transform semantics, unequal original budgets, repeated identical-input workload |
| Anatomical registration | New known rigid perturbation of case001 FLAIR slice71 | `src/registration.py` | MSE, actual geometric grid error, aligned images, five seeds |
| MRI preprocessing / enhancement | PDF theory: slice processing and percentile intensity rescaling; no original executable enhancement routine | `src/imaging.py` | New fixed contrast/departure objective, enhanced full-volume NIfTIs and appearance metrics |
| MRI segmentation before 3D | No executable prediction routine in supplied sources; new image-only baseline | `src/imaging.py` | FLAIR/Otsu high-intensity masks, fixed component rule, independent Dice/IoU evaluation |
| Full-volume 3D brain/tumour surfaces | PDF description of Marching Cubes; original STL artefacts audited separately | `src/imaging.py` | Affine-aware PLY/STL and self-contained HTML; prediction/reference visibly distinguished |
| Draft comparison and output validation | Original PDF, rewritten DOCX, measured files | `src/compare_claims.py`, `src/validate_outputs.py` | Claim table, measured summaries, output manifest and integrity checks |

Code modules contain purpose, input/output and method documentation. Preserved original
cells are unchanged; explanatory notes sit in the runners and method reports.

## Reproduce the run

The isolated environment is `.venv`; dependencies are pinned in
`requirements-lock.txt`. This run uses CPU processing and one BLAS thread. GPU
hardware is not used and no learned model is trained.

If setting up an extracted code bundle in a new folder with Python3.12 available:

```powershell
py -3.12 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r '.\requirements-lock.txt'
```

From this directory in PowerShell:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -u '.\run_all.py' --resume
```

`--resume` preserves stages that have already completed in the ledger. To create a
fresh independent run rather than reuse completed measurements:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -u '.\run_all.py' --output '.\results\my_new_run'
```

The default MRI cohort is three lexically selected cases, with seeds 0/1/2 and
1,500 objective calls for each enhancement and threshold-selection stage.
Numerical/routing experiments use five seeds and 3,000 calls. Original source
experiments retain their original unequal budgets and record that fact.

To evaluate a larger cohort, choose a fresh output and a declared case count:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -u '.\run_all.py' --output '.\results\expanded_cohort' --stages imaging,comparison --cases 484
```

This expanded command is provided for reproducibility; the saved execution covers
three cases, not all 484. Labelled training cases are a retrospective evaluation
subset here, not a hidden challenge test set. Seeds are not additional patients.

To replay every original MRI notebook cell again, including the longer repeated
synthetic-input scaling workload:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -u '.\src\replay_sources.py' --output '.\results\source_replay_new'
```

Run stages sequentially when using elapsed times. The measured source routing
observer adds validity/profiling overhead; its runtime cannot be treated as an
uninstrumented original timing or an equal-budget speed ranking.

## MRI outputs and their meaning

Each case directory contains predictions for every optimiser and seed, prediction
records written before labels are opened, then separately evaluated records. The
first seed also saves each enhanced float32 volume on the original NIfTI grid,
image-only selected slice panels, and predicted-mask meshes. Ground truth
is stored as `reference_whole_tumour.nii.gz` and rendered separately. The complete
volume is used for Dice/IoU; only displayed meshes use stride2 decimation.

Task01 modality0 is FLAIR. Whole-tumour reference is the union of labels1/2/3,
as defined by the local release. No assumed label4 mapping is used. Image/label
geometry must match; masks are not silently resized. NIfTI affine and q/s forms
are retained, and exported vertices are transformed into world millimetres.

The reconstructed enhancement objective optimises contrast, departure from the
input and saturation. PSNR/SSIM against the normalized input measure appearance
similarity; they cannot verify noise removal without a clean/noise reference.
The image-only segmentation baseline optimises three-class Otsu variance and
selects the highest-intensity largest connected component. Its actual overlap
with given tumour labels determines accuracy. Surface generation alone is not
evidence of successful tumour detection or clinical suitability.

## Method details and provenance

- `reports/routing_method_notes.md`
- `reports/source_method_notes.md`
- `reports/imaging_method_notes.md`
- `reports/pdf_code_coverage.md`
- `sources/source_manifest.json`, `sources/notebook_cell_inventory.json`
- `sources/major_last_codes_pages.json`, `sources/mri_local_codes_pages.json`
- `results/existing_meshes/mesh_audit.json`

New measurements cannot retrospectively validate undocumented historical settings.
The manuscript's literal MRI graph values and hypothetical error bars remain
historical plotting data. The recovered code did not contain the complete proposed
dimensionality/schedule formulation or a tumour detector; those stages have been
implemented transparently and evaluated as new experiments.
