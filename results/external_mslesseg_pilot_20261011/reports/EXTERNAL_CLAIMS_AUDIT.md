# External MRI lesion validation: measured claims audit

Dataset: MSLesSeg. The manifest contains 115 image series from 75 patients. Series are repeated sessions, not independent patients.

Completed imaging: 1 series. Primary patient observations use only the earliest numeric session selected from the entire manifest before outcomes are examined. 74 primary patients are missing; later sessions are never substituted. Cohort complete: False.

Training: none. Learned-model comparison: not measured. This is the frozen unsupervised FLAIR contrast/Otsu threshold baseline, not a learned lesion detector. Reference lesions are evaluated after all predictions for each case are saved. The independent saved-mask checks recompute native-grid overlap and confirm unchanged prediction checksums.

Here native-grid evaluation means the unchanged grid of the supplied input file. MSLesSeg inputs are supplied after brain extraction and affine registration to the MNI152 template at 1 mm spacing. Reported mL values are volumes on that supplied registration grid, not native-acquisition lesion burden. No inverse acquisition transform or clinical lesion-burden validation was measured.

Empty expert-reference masks: 0 completed sessions and 0 earliest-session patients. Undefined precision/recall remain null; metric-specific n_patients and n_undefined_patient_endpoints record exclusions. No zero denominator is replaced with a favorable score except the declared both-empty Dice/IoU convention of one.

## Primary patient-level lesion overlap

Seeds are averaged within the earliest session; patients receive equal weight. SD is between patients. Mean confidence intervals use 5,000 patient bootstrap resamples with seed 20261011. These intervals describe this retrospective cohort; they do not establish clinical effectiveness.

| method | n_patients | mean | sd | median | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- | --- |
| acor | 1 | 0.006647 | not available | 0.006647 | 0.006647 | 0.006647 |
| direct_otsu | 1 | 0.006009 | not available | 0.006009 | 0.006009 | 0.006009 |
| ga | 1 | 0.006647 | not available | 0.006647 | 0.006647 | 0.006647 |
| modified_eho | 1 | 0.007064 | not available | 0.007064 | 0.007064 | 0.007064 |
| original_eho | 1 | 0.006948 | not available | 0.006948 | 0.006948 | 0.006948 |
| pso | 1 | 0.006647 | not available | 0.006647 | 0.006647 | 0.006647 |

## Prespecified paired comparisons

Differences are modified EHO minus the named baseline on the same patients. Two-sided Wilcoxon tests use zero_method=wilcox; all-zero differences have p=1. Holm correction uses the five prespecified Dice comparisons within each analysis, including a five-test multiplier when fewer comparisons are available. An incomplete five-comparison family is flagged in the CSV and must not be described as the full planned confirmatory family.

| baseline | n_patients | mean | ci95_low | ci95_high | wilcoxon_two_sided_p | holm_adjusted_p |
| --- | --- | --- | --- | --- | --- | --- |
| direct_otsu | 1 | 0.001055 | 0.001055 | 0.001055 | 1 | 1 |
| original_eho | 1 | 0.0001155 | 0.0001155 | 0.0001155 | 1 | 1 |
| pso | 1 | 0.0004164 | 0.0004164 | 0.0004164 | 1 | 1 |
| ga | 1 | 0.0004164 | 0.0004164 | 0.0004164 | 1 | 1 |
| acor | 1 | 0.0004164 | 0.0004164 | 0.0004164 | 1 | 1 |


The observed modified-EHO minus direct-Otsu patient-mean Dice difference is 0.001055, with bootstrap 95% CI [0.001055, 0.001055]. Its Holm-adjusted two-sided Wilcoxon p-value is 1. Interpretation follows the measured sign and uncertainty; superiority is not assumed.

## Repeated-session and component-rule sensitivity

The separately labelled all-session analysis averages seeds within a session, sessions within a patient, then patients equally. It does not count 115 series as 115 people. It retains all available sessions, without favorable session selection.

The prespecified all-components ablation changes only the component retention rule for modified EHO and direct Otsu. It is an additional experiment and does not replace the frozen largest-component primary result. Paired Dice/recall effects appear below; significance is exploratory and does not select a new favorable protocol.

Secondary component-rule seed coverage is checked independently: 1 complete secondary sessions; 0 incomplete secondary sessions are excluded from secondary comparisons without altering complete primary observations.

| method | metric | n_patients | mean | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| modified_eho | dice_lesion | 1 | 0.0002299 | 0.0002299 | 0.0002299 |
| modified_eho | recall_lesion | 1 | 0.03632 | 0.03632 | 0.03632 |
| direct_otsu | dice_lesion | 1 | 3.842e-05 | 3.842e-05 | 3.842e-05 |
| direct_otsu | recall_lesion | 1 | 0.00933 | 0.00933 | 0.00933 |

## Processing time and memory

Enhancement and segmentation wall times are measured CPU processing stages; they exclude caller saving, reference evaluation, and mesh export. The deterministic Otsu path omits enhancement. Observed process RSS is sampled every 50 ms and includes imported libraries and image arrays. It is neither GPU memory nor an exact allocation peak. Patient-level summaries of available time/RSS columns are in patient_metric_summary.csv; case manifests retain loading and total I/O/evaluation/mesh resources. No real-time or deployment claim follows from these measurements.

Primary imaging budgets count exactly 1,500 optimizer objective calls per stage, including initialization. Ancillary registration and noisy-contrast optimization each count 1,500 search objective calls plus one separate postsearch returned-candidate verification call; registration also makes one known-transform calibration call per case. These are additional checks outside the counted optimizer budget, not 1,500 total objective executions. Timing endpoints describe their recorded processing paths and are not interchangeable with image loading, saving or rendering time.

## Frozen SSIM mask qualification

The inherited primary appearance_metrics implementation uses binary_erosion with the default cross structuring element repeated win_size//2 times. For a 7-pixel SSIM window this gives a diamond-shaped erosion, not erosion by the complete 7×7 square. Its saved roi_ssim_rule text therefore overstates complete-window containment: pixels near corners of foreground boundaries may contribute SSIM windows containing background. Frozen primary values are preserved and this limitation is disclosed here. Whole-slice SSIM also includes background. The ancillary controlled-noise clean_foreground_eroded_ssim uses an explicit square-window erosion and has a distinct metric definition.

## Relationship to the earlier tumour experiment

The earlier BraTS reconstruction had mean whole-tumour Dice 0.736661 for modified EHO and 0.752200 for direct Otsu across three patients. These are tumour/oedema results from a different dataset and pathology. External MS lesion endpoints are reported separately and are never pooled with those three cases. Fresh external measurements cannot substantiate unknown historical MRI objectives, manually entered plot scores, or clinical claims.

## Manuscript claim checks

| Claim | What the measured experiment supports | Remaining limit |
| --- | --- | --- |
| Enhancement quality / anatomical preservation | Input-versus-enhanced PSNR/SSIM describe departure from the same normalized input. Supplied MNI-grid geometry is preserved. | A clean clinical denoising reference and diagnostic quality assessment were not supplied. Identity can maximize input similarity; inherited ROI-SSIM has the erosion limitation described above. |
| Robust detection / localization | Native-grid expert lesion overlap and the prespecified component ablation quantify this external retrospective cohort. | Highest-intensity threshold masks and the largest-component rule are exploratory hypotheses; no clinical detector or surgical validation was measured. |
| Optimizer superiority | Equal counted objective budgets and paired patient Dice comparisons can support only the observed task-specific differences. | Histogram-objective convergence alone does not establish lesion overlap superiority or general superiority. |
| Anatomical registration robustness | Available known rigid-perturbation studies measure MSE and geometric grid displacement. | A synthetic transform on one MRI slice is not independent patient-to-patient or clinical registration accuracy. |
| Noise suppression | Available controlled Gaussian-corruption studies compare postprediction quality with the uncorrupted normalized image. | Simulated corruption is not a clinical noisy/clean acquisition pair, and a contrast transform is not a trained denoiser. |

## Ancillary image-only studies

Availability: not supplied.

No completed observations available.

Known-transform registration and simulated-noise experiments remain separately identified. Missing studies are not assigned values. Their RNG repetitions are averaged within subjects before across-subject summaries.

## Files

Open VIEW_EXTERNAL_RESULTS.html for every manifest case and its saved interactive prediction/reference view. primary_patient_values.csv, patient_metric_summary.csv, paired_method_comparisons.csv, component_ablation_comparisons.csv and statistics.json provide the machine-readable results.
