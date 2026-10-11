# External MRI lesion validation: measured claims audit

Dataset: MSLesSeg. The manifest contains 115 image series from 75 patients. Series are repeated sessions, not independent patients.

Completed imaging: 115 series. Primary patient observations use only the earliest numeric session selected from the entire manifest before outcomes are examined. 0 primary patients are missing; later sessions are never substituted. Cohort complete: True.

Training: none. Learned-model comparison: not measured. This is the frozen unsupervised FLAIR contrast/Otsu threshold baseline, not a learned lesion detector. Reference lesions are evaluated after all predictions for each case are saved. The independent saved-mask checks recompute native-grid overlap and confirm unchanged prediction checksums.

Here native-grid evaluation means the unchanged grid of the supplied input file. MSLesSeg inputs are supplied after brain extraction and affine registration to the MNI152 template at 1 mm spacing. Reported mL values are volumes on that supplied registration grid, not native-acquisition lesion burden. No inverse acquisition transform or clinical lesion-burden validation was measured.

Empty expert-reference masks: 0 completed sessions and 0 earliest-session patients. Undefined precision/recall remain null; metric-specific n_patients and n_undefined_patient_endpoints record exclusions. No zero denominator is replaced with a favorable score except the declared both-empty Dice/IoU convention of one.

## Primary patient-level lesion overlap

Seeds are averaged within the earliest session; patients receive equal weight. SD is between patients. Mean confidence intervals use 5,000 patient bootstrap resamples with seed 20261011. These intervals describe this retrospective cohort; they do not establish clinical effectiveness.

| method | n_patients | mean | sd | median | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- | --- |
| acor | 75 | 0.02806 | 0.03726 | 0.01252 | 0.02032 | 0.03659 |
| direct_otsu | 75 | 0.03481 | 0.08892 | 0.01095 | 0.01991 | 0.05805 |
| ga | 75 | 0.02807 | 0.03726 | 0.01252 | 0.02033 | 0.0366 |
| modified_eho | 75 | 0.02892 | 0.03924 | 0.01232 | 0.02075 | 0.03793 |
| original_eho | 75 | 0.02813 | 0.03778 | 0.01246 | 0.02031 | 0.03678 |
| pso | 75 | 0.02807 | 0.03727 | 0.01252 | 0.02033 | 0.0366 |

## Prespecified paired comparisons

Differences are modified EHO minus the named baseline on the same patients. The bootstrap confidence interval estimates the patient mean paired difference. The median paired difference and positive/negative/tied patient counts describe its distribution separately.

The two-sided Wilcoxon signed-rank test uses ranks of nonzero difference magnitudes together with their signs. It is not a test of the mean paired difference. A location interpretation relies on the relevant symmetry/shift assumptions; a skewed difference distribution can have a negative mean and positive median, and the mean bootstrap interval can contain zero while the signed-rank test rejects. A p-value alone therefore establishes neither mean superiority nor mean inferiority.

Wilcoxon uses zero_method=wilcox; all-zero differences have p=1. Holm correction uses the five prespecified Dice comparisons within each analysis, including a five-test multiplier when fewer comparisons are available. An incomplete five-comparison family is flagged in the CSV and must not be described as the full planned confirmatory family.

| baseline | n_patients | mean | median_paired_difference | positive_pairs | negative_pairs | tied_pairs | ci95_low | ci95_high | wilcoxon_two_sided_p | holm_adjusted_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| direct_otsu | 75 | -0.005892 | 0.000353 | 51 | 22 | 2 | -0.02143 | 0.002918 | 0.0002134 | 0.001067 |
| original_eho | 75 | 0.0007878 | 0 | 37 | 36 | 2 | -0.0009818 | 0.003043 | 0.6943 | 1 |
| pso | 75 | 0.0008466 | 8.122e-06 | 38 | 35 | 2 | -0.0007227 | 0.002955 | 0.4972 | 1 |
| ga | 75 | 0.0008461 | 0 | 37 | 36 | 2 | -0.0007248 | 0.002953 | 0.5326 | 1 |
| acor | 75 | 0.0008575 | 8.122e-06 | 38 | 35 | 2 | -0.0007158 | 0.002968 | 0.4833 | 1 |


The observed modified-EHO minus direct-Otsu patient-mean Dice difference is -0.005892, with bootstrap 95% CI [-0.02143, 0.002918]. The paired median is 0.000353; 51 patients have positive differences, 22 negative differences, and 2 exact ties. Its Holm-adjusted two-sided Wilcoxon p-value is 0.001067. These endpoints answer different questions; the signed-rank p-value does not establish the sign of the mean benefit.

The mean and median point in opposite directions in this observed comparison. Larger losses can outweigh more frequent small gains in the mean. This distributional imbalance must be reported rather than resolved by selecting the favorable statistic.

The mean-difference bootstrap interval contains zero, so this analysis does not establish a direction for the patient mean Dice advantage at that interval level, regardless of the signed-rank p-value.

All measured primary method mean Dice values are at most 0.1 (observed range 0.02806–0.03481). The absolute expert-lesion overlap is poor across these methods. Small paired differences do not turn this threshold pipeline into an effective lesion detector.

## Repeated-session and component-rule sensitivity

The separately labelled all-session analysis averages seeds within a session, sessions within a patient, then patients equally. It does not count 115 series as 115 people. It retains all available sessions, without favorable session selection.

The prespecified all-components ablation changes only the component retention rule for modified EHO and direct Otsu. It is an additional experiment and does not replace the frozen largest-component primary result. Paired Dice/recall effects appear below; significance is exploratory and does not select a new favorable protocol.

Secondary component-rule seed coverage is checked independently: 115 complete secondary sessions; 0 incomplete secondary sessions are excluded from secondary comparisons without altering complete primary observations.

| method | metric | n_patients | mean | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| modified_eho | dice_lesion | 75 | 0.0005135 | -0.000891 | 0.001894 |
| modified_eho | recall_lesion | 75 | 0.04646 | 0.03113 | 0.06394 |
| direct_otsu | dice_lesion | 75 | 0.0006008 | 3.706e-05 | 0.001479 |
| direct_otsu | recall_lesion | 75 | 0.03268 | 0.02127 | 0.04671 |

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

Availability: available.

| study | method | sigma | metric | n_patients | mean | sd | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| registration | acor | not available | objective | 3 | 0.001108 | 0.0001182 | 0.0009884 | 0.001225 |
| registration | acor | not available | grid_landmark_rmse_pixels | 3 | 0.004651 | 0.0002885 | 0.004319 | 0.004845 |
| registration | acor | not available | seconds | 3 | 0.7228 | 0.007483 | 0.7163 | 0.731 |
| registration | ga | not available | objective | 3 | 0.001111 | 0.0001204 | 0.0009889 | 0.00123 |
| registration | ga | not available | grid_landmark_rmse_pixels | 3 | 0.01084 | 0.004232 | 0.006327 | 0.01472 |
| registration | ga | not available | seconds | 3 | 0.7392 | 0.01574 | 0.7218 | 0.7524 |
| registration | modified_eho | not available | objective | 3 | 0.026 | 0.001136 | 0.02517 | 0.0273 |
| registration | modified_eho | not available | grid_landmark_rmse_pixels | 3 | 3.547 | 0.2273 | 3.297 | 3.742 |
| registration | modified_eho | not available | seconds | 3 | 0.7038 | 0.01183 | 0.6902 | 0.7116 |
| registration | original_eho | not available | objective | 3 | 0.008689 | 0.001786 | 0.007049 | 0.01059 |
| registration | original_eho | not available | grid_landmark_rmse_pixels | 3 | 1.155 | 0.1963 | 0.9772 | 1.366 |
| registration | original_eho | not available | seconds | 3 | 0.699 | 0.01524 | 0.6863 | 0.7159 |
| registration | pso | not available | objective | 3 | 0.001109 | 0.000118 | 0.0009891 | 0.001225 |
| registration | pso | not available | grid_landmark_rmse_pixels | 3 | 0.007653 | 0.002673 | 0.004844 | 0.01017 |
| registration | pso | not available | seconds | 3 | 0.6702 | 0.007155 | 0.662 | 0.6751 |
| controlled_noise | acor | 0.03 | clean_roi_psnr_db | 3 | 21.09 | 3.104 | 18.29 | 24.43 |
| controlled_noise | acor | 0.03 | clean_roi_ssim | 3 | 0.8259 | 0.007368 | 0.82 | 0.8341 |
| controlled_noise | acor | 0.03 | clean_foreground_eroded_ssim | 3 | 0.8117 | 0.005229 | 0.8086 | 0.8178 |
| controlled_noise | acor | 0.03 | seconds | 3 | 0.09707 | 0.001463 | 0.09599 | 0.09874 |
| controlled_noise | acor | 0.08 | clean_roi_psnr_db | 3 | 16.89 | 1.59 | 15.93 | 18.73 |
| controlled_noise | acor | 0.08 | clean_roi_ssim | 3 | 0.5749 | 0.04245 | 0.5346 | 0.6193 |
| controlled_noise | acor | 0.08 | clean_foreground_eroded_ssim | 3 | 0.5375 | 0.04949 | 0.4898 | 0.5886 |
| controlled_noise | acor | 0.08 | seconds | 3 | 0.1011 | 0.0044 | 0.09706 | 0.1058 |
| controlled_noise | ga | 0.03 | clean_roi_psnr_db | 3 | 21.09 | 3.1 | 18.29 | 24.42 |
| controlled_noise | ga | 0.03 | clean_roi_ssim | 3 | 0.8259 | 0.007375 | 0.82 | 0.8342 |
| controlled_noise | ga | 0.03 | clean_foreground_eroded_ssim | 3 | 0.8118 | 0.00524 | 0.8086 | 0.8178 |
| controlled_noise | ga | 0.03 | seconds | 3 | 0.09848 | 0.0003365 | 0.0981 | 0.09872 |
| controlled_noise | ga | 0.08 | clean_roi_psnr_db | 3 | 16.89 | 1.589 | 15.93 | 18.73 |
| controlled_noise | ga | 0.08 | clean_roi_ssim | 3 | 0.5749 | 0.04247 | 0.5346 | 0.6193 |
| controlled_noise | ga | 0.08 | clean_foreground_eroded_ssim | 3 | 0.5375 | 0.0495 | 0.4898 | 0.5886 |
| controlled_noise | ga | 0.08 | seconds | 3 | 0.1026 | 0.003854 | 0.09931 | 0.1068 |
| controlled_noise | gaussian_sigma1 | 0.03 | clean_roi_psnr_db | 3 | 25.9 | 0.5555 | 25.26 | 26.31 |
| controlled_noise | gaussian_sigma1 | 0.03 | clean_roi_ssim | 3 | 0.8867 | 0.02297 | 0.8604 | 0.9028 |
| controlled_noise | gaussian_sigma1 | 0.03 | clean_foreground_eroded_ssim | 3 | 0.8775 | 0.02536 | 0.8485 | 0.8952 |
| controlled_noise | gaussian_sigma1 | 0.03 | seconds | 3 | 0.0004285 | 2.38e-05 | 0.0004113 | 0.0004556 |
| controlled_noise | gaussian_sigma1 | 0.08 | clean_roi_psnr_db | 3 | 25.1 | 0.4976 | 24.53 | 25.44 |
| controlled_noise | gaussian_sigma1 | 0.08 | clean_roi_ssim | 3 | 0.8449 | 0.03236 | 0.8075 | 0.8646 |
| controlled_noise | gaussian_sigma1 | 0.08 | clean_foreground_eroded_ssim | 3 | 0.8314 | 0.03598 | 0.7899 | 0.8536 |
| controlled_noise | gaussian_sigma1 | 0.08 | seconds | 3 | 0.0004596 | 4.403e-05 | 0.0004088 | 0.0004851 |
| controlled_noise | modified_eho | 0.03 | clean_roi_psnr_db | 3 | 21.77 | 2.784 | 19.24 | 24.75 |
| controlled_noise | modified_eho | 0.03 | clean_roi_ssim | 3 | 0.8365 | 0.004147 | 0.8321 | 0.8403 |
| controlled_noise | modified_eho | 0.03 | clean_foreground_eroded_ssim | 3 | 0.8229 | 0.007072 | 0.8156 | 0.8297 |
| controlled_noise | modified_eho | 0.03 | seconds | 3 | 0.05953 | 0.001784 | 0.05751 | 0.06089 |
| controlled_noise | modified_eho | 0.08 | clean_roi_psnr_db | 3 | 17.54 | 1.408 | 16.69 | 19.17 |
| controlled_noise | modified_eho | 0.08 | clean_roi_ssim | 3 | 0.592 | 0.04494 | 0.5494 | 0.6389 |
| controlled_noise | modified_eho | 0.08 | clean_foreground_eroded_ssim | 3 | 0.555 | 0.05195 | 0.505 | 0.6087 |
| controlled_noise | modified_eho | 0.08 | seconds | 3 | 0.06098 | 0.003405 | 0.0588 | 0.0649 |
| controlled_noise | noisy_identity | 0.03 | clean_roi_psnr_db | 3 | 30.56 | 0.02094 | 30.54 | 30.58 |
| controlled_noise | noisy_identity | 0.03 | clean_roi_ssim | 3 | 0.9169 | 0.02376 | 0.8912 | 0.9381 |
| controlled_noise | noisy_identity | 0.03 | clean_foreground_eroded_ssim | 3 | 0.9081 | 0.02662 | 0.8794 | 0.9319 |
| controlled_noise | noisy_identity | 0.03 | seconds | 3 | 1.683e-05 | 2.89e-06 | 1.503e-05 | 2.017e-05 |
| controlled_noise | noisy_identity | 0.08 | clean_roi_psnr_db | 3 | 22.14 | 0.08052 | 22.05 | 22.21 |
| controlled_noise | noisy_identity | 0.08 | clean_roi_ssim | 3 | 0.6813 | 0.06215 | 0.6154 | 0.7389 |
| controlled_noise | noisy_identity | 0.08 | clean_foreground_eroded_ssim | 3 | 0.6493 | 0.06944 | 0.5755 | 0.7134 |
| controlled_noise | noisy_identity | 0.08 | seconds | 3 | 1.848e-05 | 4.072e-06 | 1.477e-05 | 2.283e-05 |
| controlled_noise | original_eho | 0.03 | clean_roi_psnr_db | 3 | 20.66 | 3.121 | 18.53 | 24.24 |
| controlled_noise | original_eho | 0.03 | clean_roi_ssim | 3 | 0.8231 | 0.01247 | 0.8103 | 0.8352 |
| controlled_noise | original_eho | 0.03 | clean_foreground_eroded_ssim | 3 | 0.8089 | 0.01226 | 0.7953 | 0.819 |
| controlled_noise | original_eho | 0.03 | seconds | 3 | 0.05755 | 0.0009057 | 0.05692 | 0.05858 |
| controlled_noise | original_eho | 0.08 | clean_roi_psnr_db | 3 | 16.99 | 1.355 | 16.17 | 18.56 |
| controlled_noise | original_eho | 0.08 | clean_roi_ssim | 3 | 0.5772 | 0.04628 | 0.5327 | 0.6251 |
| controlled_noise | original_eho | 0.08 | clean_foreground_eroded_ssim | 3 | 0.5398 | 0.05331 | 0.4879 | 0.5944 |
| controlled_noise | original_eho | 0.08 | seconds | 3 | 0.06015 | 0.001914 | 0.05905 | 0.06236 |
| controlled_noise | pso | 0.03 | clean_roi_psnr_db | 3 | 21.09 | 3.104 | 18.29 | 24.43 |
| controlled_noise | pso | 0.03 | clean_roi_ssim | 3 | 0.8259 | 0.007367 | 0.82 | 0.8341 |
| controlled_noise | pso | 0.03 | clean_foreground_eroded_ssim | 3 | 0.8117 | 0.005228 | 0.8086 | 0.8178 |
| controlled_noise | pso | 0.03 | seconds | 3 | 0.06946 | 0.002664 | 0.06697 | 0.07227 |
| controlled_noise | pso | 0.08 | clean_roi_psnr_db | 3 | 16.89 | 1.596 | 15.91 | 18.73 |
| controlled_noise | pso | 0.08 | clean_roi_ssim | 3 | 0.5748 | 0.04229 | 0.5346 | 0.619 |
| controlled_noise | pso | 0.08 | clean_foreground_eroded_ssim | 3 | 0.5374 | 0.04933 | 0.4898 | 0.5883 |
| controlled_noise | pso | 0.08 | seconds | 3 | 0.06805 | 0.001264 | 0.0669 | 0.0694 |

Known-transform registration and simulated-noise experiments remain separately identified. Missing studies are not assigned values. Their RNG repetitions are averaged within subjects before across-subject summaries.

## Files

Open VIEW_EXTERNAL_RESULTS.html for every manifest case and its saved interactive prediction/reference view. primary_patient_values.csv, patient_metric_summary.csv, paired_method_comparisons.csv, component_ablation_comparisons.csv and statistics.json provide the machine-readable results.
