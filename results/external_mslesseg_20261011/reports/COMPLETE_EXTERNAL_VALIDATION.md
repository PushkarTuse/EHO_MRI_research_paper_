# Completed external brain MRI validation — 11 October 2026

The reconstructed imaging pipeline executed successfully, but its external lesion
accuracy is poor. Code execution, geometric consistency and diagnostic performance
are separate conclusions. The unfavorable results are retained in full.

## Dataset selection and acquisition

MSLesSeg was the best immediate match because it supplies FLAIR MRI and independent
expert lesion masks on a common grid. Its multifocal MS lesions also test the
largest-component assumption inherited from the exploratory tumour pipeline.

All five official files, totaling 2,779,874,374 bytes (2.78 GB decimal), were
downloaded and matched their published MD5s. All four ZIP archives were safely
extracted. Raw MRI, processed MRI, masks, author source, transforms, metadata and
original archives remain preserved. No dataset-author source was executed.

- [Official dataset deposit](https://doi.org/10.6084/m9.figshare.27919209)
- [Dataset paper](https://doi.org/10.1038/s41597-025-05250-y)
- [Download checksums](../../../data/MSLesSeg/checksums.json)
- [Complete access and fit ranking](../../../reports/external_dataset_access_20261011.md)

ISLES'22 and IXI also expose immediate official downloads. ISLES'22 is the next
strong pathology-mask cohort, with native multimodal geometry requiring explicit
handling. IXI is useful for structural MRI, enhancement and registration, without
lesion-mask validation. MSSEG/MSSEG-2, ADNI and OASIS-3/4 require approved access.
OASIS-1 has reachable direct archives alongside current access/terms requirements.
RSNA haemorrhage data requires account/terms or controlled access and supports CT
classification, rather than the present MRI mask task. CQ500's original official
download host could not be reached. These other datasets were assessed, not
downloaded during this execution.

## Completed studies and reproducibility

The frozen primary experiment covers **115 scans from 75 patients**, including
both source partitions without training or label-based tuning. Primary statistics
use each patient's earliest numeric session, averaging seeds within that session.
The 40 follow-up scans remain in a separate patient-weighted longitudinal analysis.

Original EHO, modified EHO, PSO, GA and ACOR use seeds 0/1/2, population 30 and
1,500 counted evaluations per enhancement and segmentation stage. Direct Otsu is
a deterministic, unenhanced control. The five stochastic methods perform a total
of 5,175,000 counted search evaluations across the full cohort.

The full experiment completed without failed cases: **1,840 primary records and
460 separately named component-ablation records**, totaling 2,300. The ablation
retains all threshold components for modified EHO and direct Otsu; it does not
replace the frozen primary results. Reference masks are opened only after all
predictions for a case have been saved.

The separately measured ancillary experiments completed **75 registration runs**
and **126 controlled-noise/control runs** on P1_T1, P2_T1 and P3_T1. These are
three independent patients with repeated stochastic trials, not 201 patients.
The post hoc objective/localization diagnostic is explicitly identified as having
been initiated after the pilot; it changes no prediction or primary analysis.

The original manuscript's exact historical MRI implementation was not recovered.
These are new measurements of the documented reconstructed hypothesis. They do
not authenticate historical plotted PSNR/SSIM/time constants, existing identical
EHO/PSO STL pairs, or a historical slice-ordering-as-TSP implementation.

## Primary lesion accuracy

Dice uses saved full-resolution masks. The following mean and SD are between
75 patient seed means, not between 225 independent trials. Mean confidence
intervals use 5,000 patient bootstrap resamples with seed 20261011.

| Method | Mean Dice | SD | 95% CI for patient mean |
|---|---:|---:|---|
| Modified EHO | 0.028920 | 0.039245 | 0.020753–0.037926 |
| Original EHO | 0.028132 | 0.037780 | 0.020306–0.036784 |
| PSO | 0.028073 | 0.037267 | 0.020327–0.036601 |
| GA | 0.028074 | 0.037264 | 0.020330–0.036599 |
| ACOR | 0.028062 | 0.037257 | 0.020321–0.036586 |
| Direct Otsu | 0.034811 | 0.088921 | 0.019913–0.058050 |

Modified EHO's mean precision is **0.015186** and mean recall **0.903267**. High
recall accompanies very extensive nonreference predictions, rather than accurate
localization. Its mean predicted volume is **739.473 mL**, versus **10.751 mL**
for the expert reference. These are volumes on the supplied affine-registered
MNI152 grid, not native-acquisition clinical lesion burden.

Modified EHO minus direct Otsu has mean paired Dice difference **−0.005892**,
bootstrap CI **[−0.02143, 0.002918]**. The paired median is **+0.000353**: 51
patients show positive differences, 22 negative differences and two ties. The
Holm-adjusted signed-rank p-value is **0.001067**. Signed ranks and the mean
bootstrap interval address different estimands; skewed differences can yield
opposite mean and median signs. The p-value does not establish mean superiority
or inferiority. Absolute Dice remains poor for every method.

Retaining all components changes modified-EHO patient-mean Dice by only
**+0.0005135**, with CI **[−0.000891, 0.001894]**, while increasing recall by
about 0.04646. Removing the largest-component restriction does not resolve the
low precision or broad intensity-class predictions.

## Registration and noise stress tests

The registration study applies a known rigid perturbation to anatomical slices
and measures displacement of five geometric grid landmarks on a resized grid.
It is not interpatient, deformable or clinical landmark registration.

| Method | Mean grid-landmark RMSE, pixels | SD between three patient means |
|---|---:|---:|
| Modified EHO | 3.546785 | 0.227313 |
| Original EHO | 1.154792 | 0.196295 |
| PSO | 0.007653 | 0.002673 |
| GA | 0.010838 | 0.004232 |
| ACOR | 0.004651 | 0.000289 |

Modified EHO does not support a transform-recovery superiority claim on this
controlled test. Smaller pixel RMSE is preferred.

For Gaussian-corrupted normalized slices, the known uncorrupted image is used
only after predictions for evaluation. Results below average the three corruption
seeds within each patient, then the three patients. PSNR is measured within the
fixed input ROI with intensity range one; SSIM uses complete square windows
inside that ROI.

| Noise SD | Method | Mean clean-reference PSNR, dB | Mean eroded-foreground SSIM |
|---:|---|---:|---:|
| 0.03 | Modified EHO contrast transform | 21.7717 | 0.822922 |
| 0.03 | Noisy identity | 30.5628 | 0.908131 |
| 0.03 | Fixed Gaussian sigma1 | 25.8960 | 0.877494 |
| 0.08 | Modified EHO contrast transform | 17.5412 | 0.555008 |
| 0.08 | Noisy identity | 22.1359 | 0.649255 |
| 0.08 | Fixed Gaussian sigma1 | 25.0991 | 0.831442 |

The contrast transform worsens clean-reference fidelity on both corruption levels.
It contains no spatial denoising model. This finding addresses these synthetic
conditions; it is not a clinical noisy/clean acquisition experiment.

## Computation and interpretation

Mean primary modified-EHO enhancement and segmentation stage times are 0.185249 s
and 0.171616 s. These exclude loading, saving, independent evaluation and mesh
generation. Direct Otsu segmentation averages 0.119966 s and omits enhancement.
The full 115-series primary invocation takes 2,370.724 s, including its output and
visualization work. All methods are CPU-based and training-free; no learned-model
training or inference comparison was measured. RSS, hardware and exact timing
definitions are retained in the manifests and detailed patient summaries.

Both MRI stages have two optimization variables. The millions of image voxels
are not millions of optimization dimensions; this study does not validate a
high-dimensional-search claim. The separate registration search has three variables.

The post hoc diagnostic also finds that modified EHO has a worse source-histogram
enhancement objective than GA on all 75 patients, while its Dice improves on 37,
worsens on 36 and ties on two. Objective optimization and lesion localization
are not interchangeable. Segmentation objectives use method-specific enhanced
histograms and must not be presented as identical downstream objective instances.

## Validation and visualization

Independent saved-output verification passed **155,498 checks**, covering all
115 cases and 2,300 masks, with no global or case failures. It recomputes overlap
and header-based volumes, checks native-grid geometry and source/prediction hashes,
checks recorded histories/budgets and prediction-before-reference records, and
verifies 920 PLY and 920 STL artifacts. Mesh digests are current audit evidence;
the original runner supplied no historical mesh-hash baseline.

The code suite has **127 passing tests**. The 69 warnings are library deprecation
warnings, not failed checks. Functional tests do not demonstrate clinical accuracy.

All 115 `interactive_prediction_reference.html` files are present. The HTML audit
passed **4,512 checks** across trace arrays, triangle indices, bundled Plotly,
JavaScript syntax and **366 local dashboard links**, including the additional
study-navigation links. Static previews of the first, median,
lowest and highest modified-EHO Dice cases were rendered and inspected. Reference
surfaces retain native stride one; display decimation never enters overlap metrics.

Browser interaction with local files was not tested: the browser tool rejects
the `file:` scheme. The saved-data/syntax audit and static previews are documented
as such. Blue viewer surfaces are supplied expert MS lesions; predictions are
separate traces. A valid surface export is not proof of accurate lesion detection.

The inherited primary ROI-SSIM record overstates square-window containment:
the implementation uses repeated cross erosion. Its original numbers are retained
with this qualification. The ancillary noise study uses an explicit square erosion.
Ancillary optimizers have 1,500 counted search calls plus a returned-candidate
verification call; registration also evaluates the known transform once per case.

## Consequences for the paper

The current evidence supports an executable, training-free contrast/threshold
baseline with traceable 3D exports. It does not support broad lesion-detection,
denoising, registration-superiority, real-time deployment or diagnostic-benefit
claims. These MS results remain separate from the earlier three-case BraTS tumour
results; they test cross-pathology transfer of the reconstructed pipeline.

The next substantive improvement is a lesion-aware segmentation formulation with
spatial or anatomical information, evaluated against appropriate task baselines
on a prospectively locked development/test split. Switching optimizers alone
does not repair the shared highest-intensity-class assumption. Contrast enhancement
and denoising should be described and evaluated as separate operations.

- [Open the complete results dashboard](VIEW_EXTERNAL_RESULTS.html)
- [Detailed claim/statistics audit](EXTERNAL_CLAIMS_AUDIT.md)
- [Independent full validation](external_validation_full.json)
- [Post hoc objective diagnostic](../posthoc_objectives_v2/POSTHOC_OBJECTIVE_LOCALIZATION_CONCLUSIONS.md)
- [All source code and reproduction commands](../../../EXTERNAL_VALIDATION_README.md)
