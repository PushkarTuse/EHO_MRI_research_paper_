# External brain MRI validation — MSLesSeg

This workspace evaluates the frozen, reconstructed BraTS processing hypothesis on
an independent MS lesion cohort. It preserves previous source files, historical
results, and the original manuscript. New measurements do not authenticate
historical plotted constants or establish tumour diagnosis on MS images.

## What was selected

The official MSLesSeg release provides processed FLAIR images and independently
annotated binary lesion masks. All five deposited files were downloaded, checked
against their published MD5s, and retained, including raw MRI and author
preprocessing source. Evaluation uses all 115 processed FLAIR/mask pairs from
75 patients. There is no fitting or tuning on either official partition.

Dataset: https://doi.org/10.6084/m9.figshare.27919209

Dataset paper: https://doi.org/10.1038/s41597-025-05250-y

The deposit declares CC BY 4.0. Cite the dataset and its authors when using it.

## Files and roles

| File / directory | Purpose |
|---|---|
| `reports/external_dataset_access_20261011.md` | Official availability, licensing and suitability assessment for every requested dataset |
| `reports/external_validation_protocol_20261011.md` | Frozen primary protocol and separately identified sensitivity studies |
| `reports/mslesseg_case_manifest.json` | Complete case/patient/session inventory and absolute source paths |
| `external_datasets/MSLesSeg/` | Original downloads, checksums, metadata, extracted images, labels and author source |
| `src/download_external.py` | Resumable, checksum-verified official downloader and guarded ZIP extraction |
| `src/external_imaging.py` | Native-grid full-volume pipeline, independent mask evaluation and 3D exporters |
| `src/external_studies.py` | Anatomical rigid-perturbation and controlled-noise studies |
| `src/summarize_external.py` | Patient statistics, paired comparisons, claim audit and interactive results index |
| `src/validate_external_results.py` | Independent saved-output consistency verification |
| `src/verify_external_html.py` | Saved viewer trace arrays, dashboard links and JavaScript syntax audit |
| `src/diagnose_external_objectives.py` | Explicitly post hoc objective/localization diagnostic, without changing predictions |
| `src/build_external_index.py` | Add all study, audit and figure links to the local results dashboard |
| `results/external_mslesseg_pilot_20261011/` | Preserved one-case execution pilot; excluded from the full-cohort statistical analysis |
| `results/external_mslesseg_20261011/` | Primary full-cohort outputs and reports |
| `results/mslesseg_additional_20261011/` | Separate controlled-noise and registration studies |

## Reproduce locally

Run these commands in `D:\RANDOM\research_paper_iim\code_reruns` using the existing
isolated environment. Use a fresh output directory for a new measured experiment;
completed predictions are immutable. `--resume` resumes the matching primary
protocol and checks completed artifacts instead of replacing them.

```powershell
# Acquire the official source release and create/preserve its manifest.
& '.\.venv\Scripts\python.exe' -X utf8 -u 'src/download_external.py'

# All 115 image series, five stochastic methods, three seeds, 1,500 evaluations
# per optimization stage; direct Otsu and separate component-rule ablation.
& '.\.venv\Scripts\python.exe' -X utf8 -u 'src/external_imaging.py' --manifest 'reports/mslesseg_case_manifest.json' --output 'results/external_mslesseg_20261011/imaging'

# Run after the primary experiment so competing CPU work does not confound time.
& '.\.venv\Scripts\python.exe' -X utf8 -u 'src/external_studies.py' --manifest 'reports/mslesseg_case_manifest.json' --output 'results/mslesseg_additional_20261011' --subjects 3

# Independent patient-level analysis and viewer index.
& '.\.venv\Scripts\python.exe' -X utf8 'src/summarize_external.py' --run 'results/external_mslesseg_20261011/imaging' --manifest 'reports/mslesseg_case_manifest.json' --studies 'results/mslesseg_additional_20261011'

# Full independent saved-mask and provenance validation.
& '.\.venv\Scripts\python.exe' -X utf8 'src/validate_external_results.py' --imaging-dir 'results/external_mslesseg_20261011/imaging' --manifest 'reports/mslesseg_case_manifest.json'

# Optional descriptive objective-versus-lesion-overlap analysis; a fresh output
# directory preserves earlier diagnostic reports. This is explicitly post hoc.
& '.\.venv\Scripts\python.exe' -X utf8 'src/diagnose_external_objectives.py' --run 'results/external_mslesseg_20261011/imaging' --manifest 'reports/mslesseg_case_manifest.json' --output 'results/external_mslesseg_20261011/posthoc_objectives_v2'

# Static first/median/lowest/highest-case mesh previews; run after timed studies.
& '.\.venv\Scripts\python.exe' -X utf8 'src/preview_external_mesh.py' --run 'results/external_mslesseg_20261011/imaging'

# File-based HTML audit (does not execute or render a browser page).
& '.\.venv\Scripts\python.exe' -X utf8 'src/build_external_index.py' --run 'results/external_mslesseg_20261011/imaging' --studies 'results/mslesseg_additional_20261011' --diagnostic 'results/external_mslesseg_20261011/posthoc_objectives_v2'
& '.\.venv\Scripts\python.exe' -X utf8 'src/verify_external_html.py' --run 'results/external_mslesseg_20261011/imaging'
```

The validator command is documented by `src/validate_external_results.py --help`.
The source manifest contains machine-specific absolute paths; regenerate it in a
new workspace from the downloaded release rather than guessing a dataset layout.

## Reading the results

Open `results/external_mslesseg_20261011/reports/VIEW_EXTERNAL_RESULTS.html` for
patient statistics, all case links, slices, convergence plots and individual
`interactive_prediction_reference.html` viewers. Blue surfaces show supplied
expert reference lesions. Predicted threshold masks are distinct traces and
must never be described as the supplied reference or a detected tumour.

The primary analysis averages random seeds within the earliest numeric session
per patient, then gives each of the 75 patients equal weight. Forty additional
sessions are retained for a separately labelled longitudinal sensitivity analysis.
Three optimizer seeds are not three patients. All-components results are a
prespecified ablation; they do not replace the original largest-component result.

Overlap uses full-resolution masks. The reference mesh uses stride 1 to preserve
small lesions. Prediction meshes can use stride 2; display sampling never enters
Dice calculation. Coordinates use the supplied affine in millimetres. Reported
mL values describe the supplied MNI152 registered grid, not native-acquisition
clinical lesion burden.

The viewer files were audited as saved HTML/JSON, including every case link,
finite mesh coordinates, triangle indices and JavaScript syntax. Static previews
were inspected directly. Browser interaction with local file URLs could not be
tested because the browser tool's URL policy disallows the `file:` scheme; this
file-based audit is not presented as a completed browser rendering test.

The primary PSNR/SSIM reference is the normalized input, so those measures indicate
appearance change. The additional noise study has a known uncorrupted synthetic
reference and addresses a different question. It is not a clinical denoising
validation. The inherited primary ROI SSIM uses cross-shaped erosion repeated
three times for a seven-pixel window; it does not enforce full square-window
containment despite the legacy `roi_ssim_rule` wording. The additional study uses
an explicit square window. Preserve this distinction when comparing metrics.

All stochastic primary stages have 1,500 counted optimization evaluations.
Registration and the controlled-noise study also evaluate the returned parameters
once after optimization to check consistency; registration additionally computes
a truth-transform calibration once per case. Verification is not an extra search
step. Time definitions and training requirements appear alongside quality.

No learned model, clinical classification or deployment outcome is measured by
this execution. Poor external predictions must remain visible in the reports.

## Publication and local paths

Read [release extraction instructions](reports/EXTERNAL_PUBLICATION.md).
Use `--manifest reports/mslesseg_case_manifest_local.json` for acquisition in a clone; the supplied frozen manifest retains original machine paths. Replace the manifest argument in every new-run command with that local manifest. Extract all release assets before opening the dashboard.
