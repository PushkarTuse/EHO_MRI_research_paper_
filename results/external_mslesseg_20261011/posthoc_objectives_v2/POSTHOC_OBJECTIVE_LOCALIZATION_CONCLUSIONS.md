# Post hoc objective–lesion-overlap diagnostic

This descriptive study was initiated after inspecting the external pilot. It was not prespecified and does not change the frozen primary analysis or predictions.

Selection: each of 75 manifest patients' earliest numeric session, with no replacement by a later session. Stochastic method endpoints are means of seeds 0, 1, 2; all three finite values and complete seed coverage are required. 75 patients have complete stochastic seed coverage.

For each patient and stage, Spearman(−objective, Dice) uses exactly five method means. Partial ties receive average ranks; a constant endpoint, missing stage value or incomplete seed coverage gives an undefined correlation that remains in the patient table and denominator. No correlation p-values, pooled seed/timepoint inference, or causal claim are produced.

Enhancement objectives share the patient's source-image histogram. Segmentation objectives use each method's own enhanced-image histogram, so their between-method differences compare different downstream objective instances. A better objective can coexist with poorer lesion localization; this diagnostic does not identify which anatomical tissue produces a false positive.

Direct Otsu is an unenhanced deterministic baseline. Its Dice can be paired with modified EHO, but it has neither recorded optimization objective; those objective differences are explicitly undefined and are not replaced with zero.

## Within-patient correlation counts

| Stage | Positive | Negative | Zero | Undefined | All-tie undefined |
|---|---:|---:|---:|---:|---:|
| enhancement | 34 | 37 | 2 | 2 | 2 |
| segmentation | 36 | 35 | 2 | 2 | 2 |

Positive means larger negative objective tends to accompany larger Dice among the five methods within that patient. Negative means the rankings run in opposite directions. Undefined patients are retained; these counts are descriptive.

## Modified EHO paired signed differences

| Baseline | Endpoint | Mean raw difference | Improved | Worsened | Tied | Undefined |
|---|---|---:|---:|---:|---:|---:|
| ga | dice_lesion | 0.00084607689 | 37 | 36 | 2 | 0 |
| ga | enhancement_objective | 0.0043331291 | 0 | 75 | 0 | 0 |
| ga | segmentation_objective | 0.002667322 | 0 | 75 | 0 | 0 |
| direct_otsu | dice_lesion | -0.0058915051 | 51 | 22 | 2 | 0 |
| direct_otsu | enhancement_objective | undefined | 0 | 0 | 0 | 75 |
| direct_otsu | segmentation_objective | undefined | 0 | 0 | 0 | 75 |

Raw difference is modified EHO minus baseline; positive Dice and negative objectives are preferred. The plots convert objective differences to gain in negative objective, so both positive axes denote improvement. Each plotted point is one patient's seed means; no images or masks are opened.

| Stage, modified EHO versus GA | Both improved | Better objective, worse Dice | Worse objective, better Dice | Both worsened | Either tied | Undefined |
|---|---:|---:|---:|---:|---:|---:|
| enhancement | 0 | 0 | 37 | 36 | 2 | 0 |
| segmentation | 0 | 0 | 37 | 36 | 2 | 0 |

## Dataset-level interpretation

The tables describe alignment between optimization scores and expert-mask overlap on this cohort. They neither validate clinical denoising or diagnosis nor compare against a learned model. Objective convergence alone cannot establish lesion-localization accuracy. The paired plot can expose patients with better recorded objectives and worse Dice, without establishing a causal mechanism.

Files: `patient_seed_means.csv`, `within_patient_correlations.csv`, `paired_signed_differences.csv`, `correlation_counts.csv`, `paired_difference_counts.csv`, `paired_objective_dice_direction_counts.csv`, `diagnostic_summary.json`, and two PNG figures. Source CSV and manifest checksums are recorded in the JSON.
