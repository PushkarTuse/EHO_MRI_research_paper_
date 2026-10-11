# Original MRI claims mapped to the MSLesSeg evaluation — 11 October 2026

**Status: full imaging and ancillary execution are complete.** The original
claim-to-endpoint map below was prepared before final cohort results. It is
preserved as a methodological map rather than a second numerical report.
The measured findings are in the [completed execution report](../results/external_mslesseg_20261011/reports/COMPLETE_EXTERNAL_VALIDATION.md)
and [detailed statistics audit](../results/external_mslesseg_20261011/reports/EXTERNAL_CLAIMS_AUDIT.md).
The original manuscript, rewritten draft, existing BraTS results and historical
source reports remain preserved.

## Evidence and provenance

The original claims below are located in the saved
[original manuscript extraction](../sources/external_validation_manuscript_sources/original_extracted.txt),
especially Sections 7 and 8. The
[rewritten draft](../sources/external_validation_manuscript_sources/rewritten_extracted.txt)
already distinguishes generated registration fields, input similarity, surface
display and clinical outcomes. The
[historical claims audit](../results/run_20261005/reports/CLAIMS_VS_RERUNS.md#L41),
[MRI method notes](imaging_method_notes.md#L3)
and [registration/source notes](source_method_notes.md#L3)
establish that the recovered sources do not specify the original executable MRI
enhancement objective or lesion-prediction pipeline. Historical MRI plot values
were literal constants; the existing named EHO/PSO STL pairs were byte-identical.
A new successful experiment cannot authenticate those earlier values or restore
their missing provenance.

The frozen external method is a new reconstruction carried over from the BraTS
rerun: finite nonzero FLAIR foreground; whole-volume 1st/99th percentile scaling;
two-parameter gamma/contrast adjustment; the unchanged histogram contrast,
departure and saturation objective; three-class Otsu threshold search; highest
intensity class; largest six-connected component. Original EHO, modified EHO,
PSO, GA and the ACOR-inspired method receive equal counted budgets. ACOR is not
the historical ACO-labelled implementation. The
[prespecified external protocol](external_validation_protocol_20261011.md)
and [case manifest](mslesseg_case_manifest.json)
define the new cohort and outputs.

The official MSLesSeg dataset contains 115 MRI series from 75 patients and
expert lesion references. Its authors supplied brain extraction and affine
registration to a 1 mm MNI152 grid. These operations are upstream dataset
preprocessing. They are not evidence that the new EHO experiment registered the
cohort. The [dataset paper](https://www.nature.com/articles/s41597-025-05250-y)
and [official preprocessing repository](https://github.com/alessiarondinella/MSLesSeg-2024)
document this preparation.

## Claim-to-endpoint map

| Original location and claim | New endpoint and comparator | Result that would support a bounded claim | Result that would weaken or refute that claim; limits |
|---|---|---|---|
| **Section 7.5–7.7; Figures 6–8:** EHO provides robust medical registration and superior accuracy. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L511) | Separate known rigid perturbation on the earliest sessions of the first three numeric subject IDs. Five optimizer seeds, 1,500 evaluations and population 30 per method. Fixed-mask MSE, returned transform, and geometric grid-landmark RMSE in resized pixels. Compare all five optimizers, unregistered MSE and residual at the known transform. | Lower MSE accompanied by lower transform error under the same budget supports recovery of this prespecified rigid perturbation on those anatomical slices. Consistent improvements across three subjects strengthen that narrow conclusion. | Higher transform error, unsuccessful recovery or worse results than task-matched comparators contradict a superiority claim on this test. Low MSE alone cannot establish anatomical correspondence. These are geometric grid points, not expert landmarks; pixel RMSE is not clinical TRE in mm. There is no interpatient, multimodal or deformable registration experiment. |
| **Sections 7.2, 7.4 and 7.5.1:** noise modelling and smoothed fitness make registration noise robust. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L461) | The new registration experiment uses a known transform; the separate noise study measures intensity fidelity after controlled corruption. | No current endpoint establishes this specific registration-under-noise claim. | The intensity noise study cannot be relabelled as noisy registration validation. No noise-level sweep of transform recovery, smoothing-of-fitness ablation or acquisition-noise model is tested. Keep this claim unestablished even if both separate studies succeed. |
| **Section 7.6.3; Figure 9:** 50 images establish scalability and efficient parallel evaluation. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L566) | Full-volume stage timings, observed process RSS and end-to-end run resource records on the external series; distinct subject/session identifiers. | Measurements can support a stated processing cost on this hardware, input size and implementation. | The historical workload repeated the same generated field and did not run a parallel executor. The current sequential cohort evaluation is not a scaling law, GPU benchmark, parallel-efficiency study or workflow-throughput measurement. Faster optimizer-only search does not establish faster complete imaging. |
| **Sections 8.1–8.3; Figure 10:** PSNR/SSIM prove noise suppression and preservation of anatomical details. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L673) | Primary input-versus-enhanced PSNR/SSIM describe departure from the same normalized input. Additional controlled noise study uses the known uncorrupted normalized slice as an evaluation-only reference, Gaussian standard deviations 0.03/0.08 and corruption seeds 0/1/2. Compare every frozen contrast method against noisy identity and fixed Gaussian sigma1; retain ROI PSNR, ROI SSIM and complete-window eroded-foreground SSIM. | Improvement over noisy identity on the clean-reference metrics supports improved fidelity for these simulated corruptions. Improvement over smoothing would support a comparison with that particular fixed control. Report any PSNR/SSIM trade-off. | Lower clean-reference PSNR/SSIM than identity means the contrast transform worsens fidelity on that condition even if its contrast objective improves. Primary input similarity alone cannot demonstrate denoising: identity maximizes it. Gaussian corruption of normalized MRI is not a clinical noisy/clean acquisition pair, and the contrast transform contains no fitted denoising model. |
| **Section 8.3.2–8.3.3; Figures 11–12:** EHO is the fastest enhancement approach and ideal for real-time imaging. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L718) | Equal-evaluation stage timing and quality together; deterministic Otsu omits enhancement. Ancillary methods record optimizer-only time, while case manifests record processing and I/O/rendering separately. | A lower measured cost at comparable endpoint quality supports a task-specific quality/computation trade-off. | A faster method with worse lesion overlap or worse clean-reference fidelity does not dominate. The old slice-time constants are not replicated by new whole-volume timing. No latency target, deployment, streaming workflow, reader turnaround or real-time service was measured. |
| **Section 8.4; Figure 13:** an individual slice becomes an accurate, smoother 3D anatomical model. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L739) | New full 3D binary predictions produce affine-aware meshes; saved mask geometry and world-coordinate consistency are checked independently. | Checks can establish that a displayed surface is traceable to the complete saved mask and its supplied spatial grid. | A single 2D slice does not determine full 3D anatomy. Smoothness alone is not fidelity. No surface-distance or Hausdorff endpoint is part of the present study; do not call a visually smoother mesh more geometrically accurate. Existing identical STL pairs remain insufficient optimizer-comparison evidence. |
| **Section 8.5.1:** MRI slice ordering is TSP-reducible and EHO reduces misalignment. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L771) | The new pipeline preserves supplied voxel order, NIfTI affine, orientation and spacing. Registration is a separate controlled study. | Preservation checks support faithful use of the supplied geometry. | No routing optimizer chooses or rearranges slices. Routing success provides no reconstruction validation. Reordering indexed slices by intensity similarity could change anatomy; it is not an evaluated part of the new pipeline. |
| **Sections 8.5.2 and 8.6.1; Figures 14–15:** intensity processing identifies abnormal tissue with high precision and localizes pathology. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L787) | Saved-mask voxel Dice/IoU, precision/recall, FP/FN counts and grid-space volume discrepancy against expert MS lesion references. Compare frozen methods and direct Otsu on the same patients. Prediction/reference traces and image-only slice panels are displayed separately. | Good overlap and precision/recall on the full frozen cohort can support retrospective MS lesion-mask agreement for this specified method. A positive paired patient effect can support an observed advantage over a particular baseline. | Poor precision or many FP voxels refute high specificity to annotated pathology for this cohort. Poor recall or large FN counts refute successful complete lesion retention. Expert reference meshes are supplied annotations, not detected lesions. MS lesion overlap cannot validate tumour diagnosis, tumour subtyping, preoperative assessment or surgical benefit. |
| **Section 8.6.1:** intensity segmentation differentiates normal and pathological tissues. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L812) | Highest-class threshold masks assessed against lesion references; inspect FP/FN overlays alongside precision, recall and predicted/reference volume. | Reference agreement supports the segmentation endpoint, conditional on the supplied annotations. | The scalar intensity objective supplies no normal-tissue class or clinical lesion classifier. A bright normal structure can be retained as a candidate component. FP voxels establish disagreement with the reference, not their tissue identity: claiming a particular physiological structure caused the FP requires inspection or anatomical labels. Whole-grid specificity includes abundant zero background and must not disguise poor lesion precision. |
| **Broader MRI transfer claim:** the same processing should retain abnormalities beyond a single dominant tumour region. | Frozen largest-component prediction versus the **prespecified all-components ablation**, only for modified EHO and direct Otsu, with identical upstream thresholds; paired patient Dice and recall changes plus precision/FP burden. | Improved recall after retaining all components supports the hypothesis that the largest-component rule discards candidate dispersed lesions. Better Dice as well indicates a net overlap benefit for this cohort. | A largest-component rule keeps only one connected candidate object; this is a structural limitation when reference lesions are dispersed. Increasing recall while greatly increasing FP does not establish a successful replacement. Worse all-component Dice weakens the claim that component selection alone explains failure. Keep the frozen primary result and report the ablation separately. |
| **Sections 8.5–8.6:** 3D models permit accurate assessment of lesion size and spatial relationships. | Millimetre-coordinate exports and predicted/reference volumes on the supplied registered grid, with full-resolution mask evaluation. Reference display uses stride1; prediction display may use stride2 with a declared fallback. | Correct geometry and same-grid volumes support reproducible representations in the supplied MNI coordinate space. | Authors' 12-DOF affine registration may change volume relative to the original acquisition. These mL values are **MNI-grid mask volumes**, not native-acquisition lesion burden. No inverse mapping, clinical volume calibration or surgical localization was tested. Display decimation can omit small predicted components and never replaces full-resolution mask metrics. |
| **Section 7.8, conclusion and future directions:** training-free optimization, AI integration or efficiency imply advantages over deep learning. [Original source](../sources/external_validation_manuscript_sources/original_extracted.txt#L586) | No fitted model is required by these methods; measured per-image search time and process RSS are available. | Report “training requirement: none” and the actual processing cost. | Learned-model comparison is **not measured**. Absence of training does not prove lower total cost, lower inference latency, higher accuracy or superiority to a pretrained model. Published dataset-baseline scores use different protocols and cannot be inserted as a matched comparator. No hybrid arm has been run. |

## How to interpret failure without changing the hypothesis

Optimization quality and lesion accuracy are different endpoints. The enhancement
optimizer minimizes a histogram objective; the segmentation optimizer maximizes
three-class intensity separation. Neither objective contains lesion references.
Good convergence can therefore coexist with poor lesion Dice. If multiple methods
reach nearly the same objective or threshold mask, describe that equivalence in
the measured outputs; do not fabricate different clinical benefits from their
names. Worse objective and worse overlap can indicate both search failure and an
unsuitable processing hypothesis, whereas good objective with poor overlap points
to objective/task mismatch. These are interpretations to assess after results,
not preset explanations for an unfavorable case.

The physiological-structure false-positive hypothesis needs special care. A
large bright component outside expert lesion masks is not automatically an MS
lesion and is not automatically a particular normal structure. Save and inspect
the FLAIR overlay. Quantify disagreement as FP voxels, low precision and excess
registered-grid predicted volume; identify tissue only if the images or additional
anatomical evidence justify it. Do not replace a failed image-only prediction
with the supplied reference mesh in a demonstration.

For multifocal pathology, the prespecified component ablation isolates one
decision: discard every candidate component except the largest, or retain them
all. It does not retrain the contrast objective, choose a lesion-specific
threshold, remove physiological tissue using references, or select a favorable
case. Both ablation improvements and additional false positives belong in the
report. A prospective redesigned lesion method would be separate subsequent work.

## Analysis and reporting rules

The primary independent observations are the 75 patients' earliest numeric
manifest sessions, selected before outcomes. Optimizer seeds are averaged within
that session. Additional sessions are reported separately, averaging sessions
within each patient; 115 series and repeated seeds are not 115 or 345 independent
patients. Failed or incomplete earliest sessions are flagged, never replaced with
a favorable later session. Undefined precision/recall, empty-reference conditions
and missing cases must be counted explicitly.

Pair comparisons on the same patients, report effect sizes and patient-bootstrap
intervals, and use the prespecified two-sided Wilcoxon/Holm procedure. A confidence
interval spanning zero or a nonsignificant test does not demonstrate equivalent
methods. Three subjects in the ancillary studies support a controlled stress-test
description, not population-level clinical conclusions.

When the full run finishes, insert measured values from the completed artifacts:
the primary `all_runs.csv`, `primary_patient_values.csv`,
`patient_metric_summary.csv`, `paired_method_comparisons.csv` and
`component_ablation_comparisons.csv`; ancillary `registration/runs.csv` and
`controlled_noise/runs.csv`, their subject summaries and paired quality
differences; the recorded completion manifests and saved-output checks. Report
the full-cohort coverage before any ranking. The new MS lesion results remain
separate from the earlier three-case BraTS tumour/oedema rerun.

Suggested result wording before measurements: “We evaluate transfer of a frozen
training-free FLAIR contrast/threshold baseline to expert-labelled MS lesions,
with separate controlled transform-recovery and Gaussian-corruption studies.
Supplied MNI-grid masks are evaluated before their surfaces are interpreted;
clinical denoising, tumour diagnosis, surgical usefulness and learned-model
superiority are outside the measured endpoints.”
