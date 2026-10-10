# Manuscript claims versus actual code reruns

These are fresh runs on the local CPU. Recovered code, repaired constraints and newly reconstructed MRI experiments have separate provenance. The original manuscript and images were not overwritten. Historical constants are retained as historical constants. No measurement has been invented to reconcile a discrepancy.

## Execution coverage

The original MRI notebook's 33 code cells were replayed in order; plots, stdout and a cell ledger are in `results/source_replay`. The brute-force source's invalid matrix/syntax are preserved and diagnosed; its exact solver is exercised on a valid eight-city instance. Newly supplied 15/95-city TSP snippets are faithfully replayed. Controlled routing, continuous optimisation, synthetic/anatomical registration, whole-volume enhancement, image-only segmentation and 3D export have fresh logged outputs.

Original notebook replay outcomes: {'failed_as_supplied': 1, 'success': 32}. Cell10's forward dependency failure is retained; its executable PSO operator equivalent is covered by cell11. See `reports/pdf_code_coverage.md` for source correspondence, duplicate definitions and PDF-specific parameter harnesses.

MRI evaluation uses the first three lexically selected labelled Task01_BrainTumour cases (001–003), with three seeds per optimiser and a deterministic Otsu baseline. All 484 listed image/label pairs were inventoried; this run does not evaluate all 484. Case variation and search-seed variation are reported separately. Registration uses one anatomical slice with synthetic perturbation. No ML/DL comparison or clinical performance study has been run.

## Main measured findings

| method | n_cases | dice_whole_tumour_case_mean | dice_whole_tumour_case_sd | enhancement_seconds_case_mean | segmentation_seconds_case_mean |
| --- | --- | --- | --- | --- | --- |
| acor | 3 | 0.662152 | 0.397467 | 0.303851 | 0.320358 |
| direct_otsu | 3 | 0.7522 | 0.249854 | — | 0.190683 |
| ga | 3 | 0.662152 | 0.397467 | 0.284929 | 0.315903 |
| modified_eho | 3 | 0.736661 | 0.266068 | 0.219596 | 0.228968 |
| original_eho | 3 | 0.662641 | 0.398696 | 0.216876 | 0.22657 |
| pso | 3 | 0.662152 | 0.397467 | 0.257716 | 0.267389 |

Modified EHO's newly reconstructed contrast/threshold pipeline achieves mean whole-tumour Dice 0.737 across 3 cases, compared with 0.752 for direct Otsu. Modified EHO takes about 0.449s for enhancement plus segmentation, while direct Otsu's segmentation takes about 0.191s and omits enhancement. These are distinct processing paths. These measurements determine whether there is an advantage over the simple deterministic baseline; the source report does not assume one. Other stochastic methods can reach almost identical histogram partitions and masks; equal masks are an observed outcome, not invented independent improvements.

Per-case overlap shows why the cohort mean alone is insufficient:

| case_id | method | n_seeds | dice_whole_tumour_mean | dice_whole_tumour_seed_sd | precision_whole_tumour_mean | recall_whole_tumour_mean |
| --- | --- | --- | --- | --- | --- | --- |
| BRATS_001 | direct_otsu | 1 | 0.870706 | — | 0.879609 | 0.861981 |
| BRATS_001 | modified_eho | 3 | 0.867459 | 0.0030344 | 0.855113 | 0.880464 |
| BRATS_002 | direct_otsu | 1 | 0.465144 | — | 0.304849 | 0.980939 |
| BRATS_002 | modified_eho | 3 | 0.430512 | 0.404953 | 0.357404 | 0.975558 |
| BRATS_003 | direct_otsu | 1 | 0.920751 | — | 0.940292 | 0.902005 |
| BRATS_003 | modified_eho | 3 | 0.912013 | 0.0104177 | 0.912809 | 0.914815 |

In the new anatomical rigid-perturbation test, modified EHO has mean geometric grid error 4.303 resized pixels; PSO 0.01847, ACOR 0.01791 and GA 0.04236. The numbers quantify performance on this declared transform-recovery task, rather than demonstrating a general or clinical registration result.

Modified EHO attains low objectives on unshifted Ackley/Rastrigin but loses that advantage on the prespecified translated functions. This exposes origin sensitivity and prevents a general superiority conclusion. Component ablations and full seed distributions are included below. Historical VRP route infeasibility and hardcoded MRI plotting values remain separate issues that new successful execution cannot repair retrospectively.

## Claim-level findings

| Manuscript location | Claim | Historical number or output | Audit conclusion | Reason and rerun interpretation | Evidence files |
| --- | --- | --- | --- | --- | --- |
| Sections 3–5; Tables 1–2; Figure 1 | EHO gives the best TSP distance and runtime at all sizes | 10–100-city table; EHO 3200.4567 at 80, 2680.2345 at 90 | Not established | Source variants differ; singleton clans disable follower operations in notebook cell33. New valid routes and equal-budget results are reported separately. Historical tables have no recoverable complete seed/configuration provenance. | routing/routing_runs.csv; snippets/snippet_runs.csv; source_replay/cell_033_output.txt |
| Section 5.2; Figures 2–3 | Capacity-feasible VRP and EHO superiority | EHO 523.85; PSO 693.38 | Historical comparison invalid as evidence of constrained superiority | Recovered VRP cost accepts omitted/duplicated customers and does not enforce demand/capacity. Rerun feasibility is explicitly checked; corrected capacity-decoded experiments are new measurements. | routing/routing_routes_and_validation.json; routing/routing_defect_demonstrations.json |
| Section 6.1; Table 3; Figure 4 | Rastrigin convergence advantage | Historical iteration checkpoints 1,200,400,600,800,1000 | Configuration-dependent; fresh replication provided | Cells6/7 are rerun unchanged with three controlled seeds. Shared-budget reference implementations and shifted-function ablations are distinct. Origin-centred functions favour centre contraction; no universal superiority follows. | continuous/summary.csv; continuous/raw/; ablations/summary.csv |
| Section 6.2; Table 4; Figure 5 | Lowest Ackley value also means best efficiency | EHO 4.80/0.21845s; PSO 5.09/0.11082s; GA 15.81/0.09717s; ACO 19.94/0.52352s | Historical table already contains a quality/time trade-off | EHO is slower than GA and PSO in that table. Figure5 plots objective values although caption says execution time. Reruns measure objective, consistent returned position, evaluations and timing independently. | continuous/runs.csv; source_replay/cell_002_output.txt |
| Section 7; Figures 6–8 | Medical registration robustness and EHO superior accuracy | MSE PSO .133565; EHO .135149; GA .134779; ACO .138497 | Synthetic source experiment; universal accuracy claim contradicted by listed numbers | Source uses a generated random field, integer circular shifts and EHO20 vs others50 requested iterations. PSO and GA have lower historical MSE than EHO. Added anatomical experiment is one slice with a known imposed rigid transform, not clinical registration validation. | registration/summary.csv; registration/anatomical_geometry_summary.csv; source_replay/cell_015_output.txt |
| Section 7.6.3; Figure 9 | 50 independent images demonstrate scalability and parallel efficiency | EHO17s; PSO68s; GA60s; ACO>50s | Workload replay only | Generator resets seed42 on each call, producing repeated identical inputs. Search budgets differ and no parallel executor is used in the recovered workload. Source replay saves actual current elapsed times. | source_replay/cell_017_output.txt; source_replay/cell_017_values.json |
| Section 8.3.1; Figure 10 | Measured MRI enhancement PSNR/SSIM | EHO/PSO13.72dB,.67; GA14.33dB,.89 | Underlying historical measurements not recoverable | Plotting code contains literal values and labels error bars hypothetical. Fresh input-versus-enhanced PSNR/SSIM measure similarity to normalized input; they do not establish denoising or reproduce the historical contrast/noise objective. | source_replay/cell_023_figure_009.png; imaging/all_runs.csv |
| Section 8.3.2; Figure 11 | EHO fastest enhancement and real-time readiness | EHO .3004s; GA .3948s; PSO .6414s | Literal plotting constants, not recovered timing logs | New whole-volume processing timing, optimiser timing, RSS and export overhead are separately recorded. Different tasks/hardware/implementation prevent validation of the old per-slice times. Clinical real-time readiness is not tested. | imaging/all_records.json; imaging/run_manifest.json |
| Section 8.3.3; Figure 12 | Noise suppression with anatomical preservation | Original slice71 and enhanced images | Qualitative historical images; new contrast baseline evaluated | Original case/modality/noise model is unspecified. New case IDs, FLAIR channel, normalization, fixed objective and image-only slice choices are recorded. No clean denoising reference was found. | imaging/BRATS_001/*_slice_*.png; sources/major_last_codes_pages.json |
| Section 8.4; Figure 13 | Single-slice 3D surface proves reconstruction fidelity | Individual slice model | Surface generation is recoverable in concept, fidelity claim unestablished | Existing EHO/PSO STL pairs are byte-identical and span only z0–3 in stored coordinates. New full-volume Marching Cubes meshes use NIfTI affine; mesh display resolution is declared and masks are evaluated at native resolution. | existing_meshes/mesh_audit.json; imaging/BRATS_001/meshes/ |
| Sections 8.5–8.6; Figures 14–15 | Optimised brain tumour detection, localisation and surgical planning | Whole brain and tumour-region pictures | New segmentation evaluated; historical clinical claim unsupported | No recovered tumour-prediction implementation exists in supplied sources. A new image-only FLAIR/Otsu/connected-component baseline supplies predicted masks; label>0 references are evaluated only after predictions. Given reference labels are never called detected tumours. | imaging/per_case_seed_summary.csv; imaging/across_case_summary.csv; imaging/*/meshes/ |
| Section 4; contributions and conclusion | Dimensional scaling and adaptive control cause robust convergence improvements | Dimensionality exponent, attraction schedule, repulsion/separation | New reconstructed hypothesis tested explicitly | Supplied task-specific source bodies do not implement the complete stated formulation. Prespecified new reference algorithms and leave-one-component-out/shifted-function experiments establish only their measured behaviour at declared settings. | continuous/raw/; ablations/protocol.json; ablations/summary.csv |

## Measured summaries

### Continuous objectives: source and matched budgets

| protocol | task | method | runs | objective_mean | objective_sd | objective_median | objective_min | objective_max | seconds_mean | seconds_sd | evaluations_min | evaluations_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source_unchanged_bodies | source_ackley_cell2 | pso | 3 | 4.05096 | 1.60353 | 3.22656 | 3.02734 | 5.89898 | 0.0877751 | 0.00504261 | 5051 | 5051 |
| source_unchanged_bodies | source_ackley_cell2 | eho | 3 | 4.03443 | 0.940585 | 4.4849 | 2.95333 | 4.66506 | 0.14075 | 0.0295728 | 10051 | 10051 |
| source_unchanged_bodies | source_ackley_cell2 | ga | 3 | 18.1572 | 0.589223 | 18.2245 | 17.5372 | 18.7099 | 0.0585046 | 0.00425647 | 5151 | 5151 |
| source_unchanged_bodies | source_ackley_cell2 | aco | 3 | 19.1291 | 0.811318 | 18.9942 | 18.3936 | 19.9994 | 0.338717 | 0.0214323 | 5050 | 5050 |
| source_unchanged_bodies | source_rastrigin_cell6 | pso | 3 | 16.251 | 15.8674 | 11.9395 | 2.98488 | 33.8285 | 1.05284 | 0.204332 | 50051 | 50051 |
| source_unchanged_bodies | source_rastrigin_cell6 | eho | 3 | 8.4387 | 3.24095 | 7.20942 | 5.99224 | 12.1145 | 1.32539 | 0.251035 | 96610 | 96900 |
| source_unchanged_bodies | source_rastrigin_cell7 | pso | 3 | 34.5373 | 13.2839 | 27.8918 | 25.8876 | 49.8325 | 1.01071 | 0.10274 | 50051 | 50051 |
| source_unchanged_bodies | source_rastrigin_cell7 | eho | 3 | 8.4387 | 3.24095 | 7.20942 | 5.99224 | 12.1145 | 1.16314 | 0.130287 | 96610 | 96900 |
| matched_evaluations | rastrigin_10d | modified_eho | 5 | 0.000152201 | 0.000219095 | 5.73764e-05 | 3.09718e-05 | 0.000541643 | 0.0652479 | 0.00217727 | 3000 | 3000 |
| matched_evaluations | rastrigin_10d | pso | 5 | 15.1455 | 3.56503 | 15.9693 | 10.1842 | 19.2341 | 0.0909357 | 0.00559217 | 3000 | 3000 |
| matched_evaluations | rastrigin_10d | ga | 5 | 3.2726 | 1.22045 | 2.81033 | 1.93789 | 5.14343 | 0.151863 | 0.00607904 | 3000 | 3000 |
| matched_evaluations | rastrigin_10d | acor | 5 | 47.5483 | 7.67356 | 48.4542 | 38.5807 | 57.497 | 0.154448 | 0.00517191 | 3000 | 3000 |
| matched_evaluations | rastrigin_10d | original_eho | 5 | 0.139208 | 0.0405513 | 0.145853 | 0.0849682 | 0.186187 | 0.0582086 | 0.00142489 | 3000 | 3000 |
| matched_evaluations | ackley_10d | modified_eho | 5 | 0.00622729 | 0.00381825 | 0.00506189 | 0.00285433 | 0.0116324 | 0.0777226 | 0.00152269 | 3000 | 3000 |
| matched_evaluations | ackley_10d | pso | 5 | 0.0858212 | 0.0246294 | 0.084907 | 0.053013 | 0.121488 | 0.098148 | 0.00152466 | 3000 | 3000 |
| matched_evaluations | ackley_10d | ga | 5 | 0.841063 | 0.597433 | 0.814586 | 0.274853 | 1.70922 | 0.170214 | 0.00862905 | 3000 | 3000 |
| matched_evaluations | ackley_10d | acor | 5 | 0.0460094 | 0.0323007 | 0.0306093 | 0.0152138 | 0.093069 | 0.17354 | 0.00989856 | 3000 | 3000 |
| matched_evaluations | ackley_10d | original_eho | 5 | 0.341745 | 0.0435447 | 0.33506 | 0.292324 | 0.411554 | 0.0740304 | 0.00337926 | 3000 | 3000 |

### Registration: source and matched budgets

| protocol | task | method | runs | objective_mean | objective_sd | objective_median | objective_min | objective_max | seconds_mean | seconds_sd | evaluations_min | evaluations_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source_unchanged_bodies | synthetic_source_cell15 | pso | 3 | 0.134025 | 0.000659863 | 0.134344 | 0.133267 | 0.134466 | 0.672119 | 0.00944021 | 1500 | 1500 |
| source_unchanged_bodies | synthetic_source_cell15 | eho | 3 | 0.134529 | 0.000846897 | 0.134993 | 0.133551 | 0.135042 | 0.291374 | 0.0298128 | 630 | 630 |
| source_unchanged_bodies | synthetic_source_cell15 | ga | 3 | 0.134705 | 0.000750018 | 0.135061 | 0.133844 | 0.135212 | 0.72319 | 0.104705 | 1530 | 1530 |
| source_unchanged_bodies | synthetic_source_cell15 | aco | 3 | 0.139428 | 0.00107839 | 0.139112 | 0.138544 | 0.14063 | 0.701904 | 0.0608388 | 1500 | 1500 |
| matched_evaluations | synthetic_legacy_transform | ga | 5 | 0.133557 | 0.00043893 | 0.133242 | 0.133229 | 0.134044 | 1.00492 | 0.181626 | 1500 | 1500 |
| matched_evaluations | synthetic_legacy_transform | pso | 5 | 0.133539 | 0.000270033 | 0.133556 | 0.133267 | 0.133838 | 0.839304 | 0.110076 | 1500 | 1500 |
| matched_evaluations | synthetic_legacy_transform | acor | 5 | 0.133308 | 0.00014532 | 0.133267 | 0.133221 | 0.133564 | 0.891391 | 0.106364 | 1500 | 1500 |
| matched_evaluations | synthetic_legacy_transform | modified_eho | 5 | 0.135357 | 0.000124581 | 0.135442 | 0.135175 | 0.135447 | 0.794511 | 0.0545985 | 1500 | 1500 |
| matched_evaluations | synthetic_legacy_transform | original_eho | 5 | 0.134682 | 0.000532561 | 0.134618 | 0.133973 | 0.135441 | 0.775103 | 0.0768207 | 1500 | 1500 |
| matched_evaluations | anatomical_rigid_perturbation | ga | 5 | 0.000527176 | 5.79876e-06 | 0.00052549 | 0.000522585 | 0.000537272 | 1.16533 | 0.10659 | 1500 | 1500 |
| matched_evaluations | anatomical_rigid_perturbation | pso | 5 | 0.000522721 | 1.58968e-07 | 0.000522691 | 0.000522578 | 0.00052298 | 1.13734 | 0.208354 | 1500 | 1500 |
| matched_evaluations | anatomical_rigid_perturbation | acor | 5 | 0.000522573 | 5.76536e-13 | 0.000522573 | 0.000522573 | 0.000522573 | 1.21642 | 0.195659 | 1500 | 1500 |
| matched_evaluations | anatomical_rigid_perturbation | modified_eho | 5 | 0.0179388 | 0.00412476 | 0.0184975 | 0.012721 | 0.0236258 | 1.09001 | 0.132575 | 1500 | 1500 |
| matched_evaluations | anatomical_rigid_perturbation | original_eho | 5 | 0.0036343 | 0.00170685 | 0.00304476 | 0.00179636 | 0.00552798 | 1.07364 | 0.0623218 | 1500 | 1500 |

### Geometric registration error (grid points, resized pixels)

| method | count | mean | std |
| --- | --- | --- | --- |
| acor | 5 | 0.0179114 | 1.24524e-05 |
| ga | 5 | 0.0423625 | 0.0406172 |
| modified_eho | 5 | 4.30276 | 0.940214 |
| original_eho | 5 | 0.847985 | 0.34736 |
| pso | 5 | 0.0184706 | 0.00443913 |

### MRI whole-tumour segmentation: patient means

| method | n_cases | dice_whole_tumour_case_mean | dice_whole_tumour_case_sd | iou_whole_tumour_case_mean | iou_whole_tumour_case_sd | precision_whole_tumour_case_mean | precision_whole_tumour_case_sd | recall_whole_tumour_case_mean | recall_whole_tumour_case_sd | prediction_ml_case_mean | prediction_ml_case_sd | roi_input_similarity_psnr_db_case_mean | roi_input_similarity_psnr_db_case_sd | selected_slice_input_ssim_mean_case_mean | selected_slice_input_ssim_mean_case_sd | selected_slice_roi_input_ssim_mean_case_mean | selected_slice_roi_input_ssim_mean_case_sd | enhancement_seconds_case_mean | enhancement_seconds_case_sd | segmentation_seconds_case_mean | segmentation_seconds_case_sd | enhancement_objective_case_mean | enhancement_objective_case_sd | segmentation_objective_case_mean | segmentation_objective_case_sd | enhancement_sampled_peak_rss_mb_case_mean | enhancement_sampled_peak_rss_mb_case_sd | segmentation_sampled_peak_rss_mb_case_mean | segmentation_sampled_peak_rss_mb_case_sd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| acor | 3 | 0.662152 | 0.397467 | 0.574524 | 0.402334 | 0.61656 | 0.437874 | 0.941373 | 0.0462493 | 282.519 | 231.483 | 24.7843 | 2.26174 | 0.980335 | 0.000654624 | 0.954526 | 0.00825922 | 0.303851 | 0.0500193 | 0.320358 | 0.0501331 | -0.23105 | 0.0175412 | -0.048514 | 0.00793011 | 197.677 | 56.1064 | 291.562 | 52.4198 |
| direct_otsu | 3 | 0.7522 | 0.249854 | 0.642404 | 0.29674 | 0.70825 | 0.350671 | 0.914975 | 0.0605302 | 159.749 | 47.1185 | — | — | 1 | 0 | 1 | 0 | — | — | 0.190683 | 0.00883439 | — | — | — | — | — | — | 244.87 | 18.1192 |
| ga | 3 | 0.662152 | 0.397467 | 0.574524 | 0.402334 | 0.61656 | 0.437874 | 0.941373 | 0.0462493 | 282.519 | 231.483 | 24.7771 | 2.26365 | 0.98034 | 0.000652576 | 0.954524 | 0.00826576 | 0.284929 | 0.0162417 | 0.315903 | 0.0663472 | -0.231048 | 0.0175413 | -0.0485129 | 0.00792929 | 199.352 | 59.3913 | 280.872 | 62.5716 |
| modified_eho | 3 | 0.736661 | 0.266068 | 0.649172 | 0.267444 | 0.708442 | 0.305373 | 0.923612 | 0.0481534 | 248.181 | 181.029 | 26.2126 | 0.551228 | 0.97834 | 0.00224908 | 0.955285 | 0.00554838 | 0.219596 | 0.0355871 | 0.228968 | 0.0230543 | -0.227446 | 0.0174108 | -0.0466288 | 0.00755759 | 197.316 | 59.1191 | 314.77 | 53.8103 |
| original_eho | 3 | 0.662641 | 0.398696 | 0.575654 | 0.403464 | 0.622867 | 0.442951 | 0.936434 | 0.052141 | 283.807 | 237.95 | 24.3734 | 2.54221 | 0.981449 | 0.000827636 | 0.956547 | 0.00877837 | 0.216876 | 0.00736203 | 0.22657 | 0.0132765 | -0.229819 | 0.0176016 | -0.0480245 | 0.00780929 | 201.992 | 68.9094 | 310.448 | 59.7103 |
| pso | 3 | 0.662152 | 0.397467 | 0.574524 | 0.402334 | 0.61656 | 0.437874 | 0.941373 | 0.0462493 | 282.519 | 231.483 | 24.786 | 2.25928 | 0.980332 | 0.000652684 | 0.954525 | 0.00825791 | 0.257716 | 0.0614532 | 0.267389 | 0.0469414 | -0.23105 | 0.0175416 | -0.0485146 | 0.0079307 | 198.797 | 58.6762 | 298.065 | 57.6801 |

### MRI seed variation within each patient

| case_id | method | n_seeds | dice_whole_tumour_mean | dice_whole_tumour_seed_sd | iou_whole_tumour_mean | iou_whole_tumour_seed_sd | precision_whole_tumour_mean | precision_whole_tumour_seed_sd | recall_whole_tumour_mean | recall_whole_tumour_seed_sd | prediction_ml_mean | prediction_ml_seed_sd | roi_input_similarity_psnr_db_mean | roi_input_similarity_psnr_db_seed_sd | selected_slice_input_ssim_mean_mean | selected_slice_input_ssim_mean_seed_sd | selected_slice_roi_input_ssim_mean_mean | selected_slice_roi_input_ssim_mean_seed_sd | enhancement_seconds_mean | enhancement_seconds_seed_sd | segmentation_seconds_mean | segmentation_seconds_seed_sd | enhancement_objective_mean | enhancement_objective_seed_sd | segmentation_objective_mean | segmentation_objective_seed_sd | enhancement_sampled_peak_rss_mb_mean | enhancement_sampled_peak_rss_mb_seed_sd | segmentation_sampled_peak_rss_mb_mean | segmentation_sampled_peak_rss_mb_seed_sd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BRATS_001 | acor | 3 | 0.858021 | 0 | 0.751346 | 1.35974e-16 | 0.818442 | 0 | 0.901624 | 0 | 123.079 | 0 | 24.8784 | 0 | 0.980674 | 4.11945e-09 | 0.946278 | 0 | 0.355086 | 0.0176354 | 0.368628 | 0.0367284 | -0.21088 | 2.27771e-11 | -0.0393951 | 0 | 133.773 | 6.35694 | 238.109 | 39.2428 |
| BRATS_001 | direct_otsu | 1 | 0.870706 | — | 0.771018 | — | 0.879609 | — | 0.861981 | — | 109.485 | — | — | — | 1 | — | 1 | — | — | — | 0.200731 | — | — | — | — | — | — | — | 227.602 | — |
| BRATS_001 | ga | 3 | 0.858021 | 0 | 0.751346 | 1.35974e-16 | 0.818442 | 0 | 0.901624 | 0 | 123.079 | 0 | 24.8661 | 0.00886569 | 0.980674 | 1.55646e-07 | 0.946268 | 6.46092e-06 | 0.290869 | 0.0489142 | 0.389462 | 0.073784 | -0.210878 | 1.53141e-06 | -0.0393949 | 4.95958e-06 | 132.638 | 4.47155 | 211.952 | 24.4816 |
| BRATS_001 | modified_eho | 3 | 0.867459 | 0.0030344 | 0.765949 | 0.00473435 | 0.855113 | 0.0163641 | 0.880464 | 0.0109713 | 115.082 | 3.60746 | 26.3237 | 3.05892 | 0.980315 | 0.00201043 | 0.948945 | 0.00508324 | 0.197391 | 0.00363439 | 0.219465 | 0.00402902 | -0.207345 | 0.00223954 | -0.0379069 | 0.00107949 | 130.411 | 5.51603 | 258.344 | 0.283385 |
| BRATS_001 | original_eho | 3 | 0.860804 | 0.0089662 | 0.755697 | 0.0138519 | 0.836171 | 0.0418859 | 0.888902 | 0.0270533 | 119.082 | 9.35757 | 23.649 | 1.60658 | 0.981427 | 0.00117333 | 0.947556 | 0.00402846 | 0.208448 | 0.0153408 | 0.227939 | 0.00644106 | -0.209546 | 0.000529135 | -0.0390318 | 0.000505036 | 123.63 | 16.6282 | 243.352 | 11.5451 |
| BRATS_001 | pso | 3 | 0.858021 | 0 | 0.751346 | 1.35974e-16 | 0.818442 | 0 | 0.901624 | 0 | 123.079 | 0 | 24.8784 | 3.83156e-05 | 0.980674 | 5.40258e-08 | 0.946277 | 1.74626e-07 | 0.207357 | 0.00965477 | 0.225924 | 0.00809084 | -0.21088 | 6.60011e-09 | -0.0393951 | 0 | 132.608 | 7.66535 | 231.462 | 36.1152 |
| BRATS_002 | acor | 3 | 0.204765 | 0 | 0.11406 | 1.69967e-17 | 0.114163 | 0 | 0.992135 | 0 | 548.03 | 0 | 22.477 | 0.00863052 | 0.980749 | 1.09401e-05 | 0.962796 | 4.80067e-06 | 0.255143 | 0.0056312 | 0.268549 | 0.0270917 | -0.242737 | 2.32913e-06 | -0.0537953 | 3.04157e-06 | 220.397 | 6.16288 | 293.691 | 33.9398 |
| BRATS_002 | direct_otsu | 1 | 0.465144 | — | 0.303054 | — | 0.304849 | — | 0.980939 | — | 202.917 | — | — | — | 1 | — | 1 | — | — | — | 0.184134 | — | — | — | — | — | — | — | 243.273 | — |
| BRATS_002 | ga | 3 | 0.204765 | 0 | 0.11406 | 1.69967e-17 | 0.114163 | 0 | 0.992135 | 0 | 548.03 | 0 | 22.4703 | 0.0130519 | 0.980758 | 1.63919e-05 | 0.9628 | 6.89422e-06 | 0.266553 | 0.024582 | 0.260582 | 0.00770693 | -0.242736 | 3.49669e-06 | -0.0537924 | 2.31538e-06 | 218.952 | 6.18847 | 296.549 | 41.5098 |
| BRATS_002 | modified_eho | 3 | 0.430512 | 0.404953 | 0.343197 | 0.401364 | 0.357404 | 0.425599 | 0.975558 | 0.0298284 | 454.319 | 413.208 | 25.6142 | 3.47928 | 0.975892 | 0.00657866 | 0.959254 | 0.00686116 | 0.200755 | 0.00691249 | 0.212184 | 0.00673789 | -0.237838 | 0.00336086 | -0.0507383 | 0.00203143 | 219.022 | 7.32224 | 320.454 | 37.0851 |
| BRATS_002 | original_eho | 3 | 0.203688 | 0.0231182 | 0.113516 | 0.0143602 | 0.113621 | 0.0144045 | 0.992203 | 0.00132829 | 556.615 | 70.3631 | 22.2719 | 1.30699 | 0.982288 | 0.000739815 | 0.965097 | 0.00161142 | 0.22013 | 0.018798 | 0.239108 | 0.0229108 | -0.241208 | 0.000904845 | -0.053099 | 0.000826102 | 229.21 | 17.3191 | 330.253 | 43.3491 |
| BRATS_002 | pso | 3 | 0.204765 | 0 | 0.11406 | 1.69967e-17 | 0.114163 | 0 | 0.992135 | 0 | 548.03 | 0 | 22.4819 | 0.000112722 | 0.980743 | 1.12329e-07 | 0.962793 | 4.55238e-08 | 0.239601 | 0.0238733 | 0.257888 | 0.0246245 | -0.242739 | 2.98396e-08 | -0.053797 | 8.49837e-18 | 219.354 | 6.04527 | 331.646 | 19.7381 |
| BRATS_003 | acor | 3 | 0.92367 | 0 | 0.858166 | 0 | 0.917074 | 0 | 0.930362 | 1.35974e-16 | 176.447 | 0 | 26.9976 | 6.0768e-05 | 0.97958 | 2.06126e-07 | 0.954503 | 1.4084e-07 | 0.301324 | 0.0363618 | 0.323896 | 0.0491149 | -0.239532 | 4.61747e-08 | -0.0523517 | 0 | 238.859 | 6.15774 | 342.884 | 39.2429 |
| BRATS_003 | direct_otsu | 1 | 0.920751 | — | 0.85314 | — | 0.940292 | — | 0.902005 | — | 166.845 | — | — | — | 1 | — | 1 | — | — | — | 0.187183 | — | — | — | — | — | — | — | 263.734 | — |
| BRATS_003 | ga | 3 | 0.92367 | 0 | 0.858166 | 0 | 0.917074 | 0 | 0.930362 | 1.35974e-16 | 176.447 | 0 | 26.995 | 0.00184258 | 0.979588 | 5.73771e-06 | 0.954504 | 9.30259e-07 | 0.297364 | 0.0123173 | 0.297664 | 0.0157083 | -0.23953 | 1.381e-06 | -0.0523515 | 2.12624e-06 | 246.466 | 2.58842 | 334.113 | 31.4102 |
| BRATS_003 | modified_eho | 3 | 0.912013 | 0.0104177 | 0.838369 | 0.017518 | 0.912809 | 0.0579872 | 0.914815 | 0.0411102 | 175.141 | 19.6416 | 26.6997 | 1.75557 | 0.978812 | 0.00446002 | 0.957656 | 0.00815595 | 0.260643 | 0.0190226 | 0.255255 | 0.0433609 | -0.237154 | 0.00162092 | -0.0512412 | 0.00100239 | 242.513 | 6.47215 | 365.513 | 0.0383397 |
| BRATS_003 | original_eho | 3 | 0.923429 | 0.000120713 | 0.85775 | 0.0002083 | 0.918809 | 0.00841391 | 0.928198 | 0.00829047 | 175.724 | 3.16273 | 27.1991 | 0.21676 | 0.980633 | 0.000274867 | 0.956989 | 0.00123349 | 0.222051 | 0.0192881 | 0.212661 | 0.0119609 | -0.238702 | 0.00033188 | -0.0519425 | 0.000177504 | 253.135 | 25.8454 | 357.74 | 13.1811 |
| BRATS_003 | pso | 3 | 0.92367 | 0 | 0.858166 | 0 | 0.917074 | 0 | 0.930362 | 1.35974e-16 | 176.447 | 0 | 26.9976 | 2.21264e-05 | 0.97958 | 6.33748e-08 | 0.954503 | 6.88255e-08 | 0.326191 | 0.016546 | 0.318354 | 0.00985227 | -0.239532 | 1.66488e-08 | -0.0523517 | 0 | 244.428 | 3.87117 | 331.086 | 33.1348 |

### Component ablations and shifted objectives

| protocol | task | method | runs | objective_mean | objective_sd | objective_median | objective_min | objective_max | seconds_mean | seconds_sd | evaluations_min | evaluations_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| matched_evaluations | rastrigin_shifted_10d | modified_norepulsion | 5 | 79.4131 | 14.7992 | 74.7794 | 59.801 | 95.787 | 0.0642833 | 0.00429856 | 3000 | 3000 |
| matched_evaluations | rastrigin_shifted_10d | modified_noseparation | 5 | 60.4444 | 7.53886 | 57.4066 | 51.1704 | 69.5745 | 0.0825107 | 0.0114489 | 3000 | 3000 |
| matched_evaluations | rastrigin_shifted_10d | modified_all | 5 | 75.4294 | 9.53679 | 76.3005 | 59.801 | 84.6483 | 0.0887763 | 0.0222526 | 3000 | 3000 |
| matched_evaluations | rastrigin_shifted_10d | modified_noschedule | 5 | 73.7059 | 7.8176 | 76.0927 | 60.0445 | 79.6184 | 0.0801207 | 0.0134849 | 3000 | 3000 |
| matched_evaluations | rastrigin_shifted_10d | original_eho | 5 | 59.9135 | 6.39261 | 57.8591 | 55.0196 | 70.8771 | 0.0704706 | 0.00694502 | 3000 | 3000 |
| matched_evaluations | rastrigin_shifted_10d | modified_nodim | 5 | 72.507 | 6.98815 | 71.7303 | 65.4465 | 83.9181 | 0.0869527 | 0.0267877 | 3000 | 3000 |
| matched_evaluations | ackley_shifted_10d | modified_norepulsion | 5 | 19.7089 | 0.12554 | 19.7496 | 19.5013 | 19.8033 | 0.0968378 | 0.0143188 | 3000 | 3000 |
| matched_evaluations | ackley_shifted_10d | modified_noseparation | 5 | 18.9991 | 0.562732 | 19.1003 | 18.0704 | 19.5701 | 0.108818 | 0.0150693 | 3000 | 3000 |
| matched_evaluations | ackley_shifted_10d | modified_all | 5 | 19.6917 | 0.084296 | 19.7263 | 19.5905 | 19.7797 | 0.104998 | 0.0314586 | 3000 | 3000 |
| matched_evaluations | ackley_shifted_10d | modified_noschedule | 5 | 19.5164 | 0.199966 | 19.5525 | 19.2059 | 19.718 | 0.100333 | 0.0249257 | 3000 | 3000 |
| matched_evaluations | ackley_shifted_10d | original_eho | 5 | 17.9879 | 0.549058 | 17.9218 | 17.3087 | 18.8344 | 0.0876409 | 0.0173387 | 3000 | 3000 |
| matched_evaluations | ackley_shifted_10d | modified_nodim | 5 | 19.521 | 0.247039 | 19.5829 | 19.1022 | 19.7505 | 0.0979432 | 0.0133766 | 3000 | 3000 |

### Routing: feasibility must precede cost ranking

| tag | task | size | method | runs | feasible_runs | objective_mean | objective_sd | time_mean_s | objective_calls_mean | invalid_calls_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| faithful_source_operators_replay_instance | TSP | 8 | ACO | 5 | 5 | 279.038 | 3.54161 | 0.121533 | 800 | 0 |
| faithful_source_operators_replay_instance | TSP | 8 | EHO | 5 | 5 | 347.103 | 22.0534 | 0.0256177 | 100 | 0 |
| faithful_source_operators_replay_instance | TSP | 8 | EHO_brute_notebook | 5 | 5 | 277.322 | 0.201133 | 0.00826922 | 383.4 | 0 |
| faithful_source_operators_replay_instance | TSP | 8 | GA | 5 | 5 | 277.232 | 0 | 0.188828 | 10000 | 0 |
| faithful_source_operators_replay_instance | TSP | 8 | PSO | 5 | 5 | 298.996 | 29.5978 | 0.0644342 | 5101 | 0 |
| faithful_source_operators_replay_instance | TSP | 20 | ACO | 5 | 5 | 758.962 | 21.804 | 0.390893 | 800 | 0 |
| faithful_source_operators_replay_instance | TSP | 20 | EHO | 5 | 5 | 831.6 | 31.1682 | 0.0265386 | 100 | 0 |
| faithful_source_operators_replay_instance | TSP | 20 | GA | 5 | 5 | 663.695 | 21.3983 | 0.2732 | 10000 | 0 |
| faithful_source_operators_replay_instance | TSP | 20 | PSO | 5 | 5 | 700.354 | 62.7334 | 0.10737 | 5101 | 0 |
| faithful_source_operators_replay_instance | VRP | 20 | EHO | 5 | 0 | 571.493 | 40.4387 | 0.123039 | 3031 | 2986.2 |
| faithful_source_operators_replay_instance | VRP | 20 | PSO | 5 | 0 | 678.712 | 41.7812 | 0.202014 | 3031 | 2970 |
| new_corrective_permutation_adaptation | TSP | 8 | ACO | 5 | 5 | 277.232 | 0 | 0.718377 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 8 | EHO | 5 | 5 | 277.232 | 0 | 0.206455 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 8 | GA | 5 | 5 | 277.232 | 0 | 0.244575 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 8 | PSO | 5 | 5 | 277.232 | 0 | 0.104997 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 10 | ACO | 5 | 5 | 290.307 | 0 | 0.947374 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 10 | EHO | 5 | 5 | 290.307 | 0 | 0.218422 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 10 | GA | 5 | 5 | 290.307 | 2.84217e-14 | 0.265829 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 10 | PSO | 5 | 5 | 290.309 | 0.00518467 | 0.156419 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 20 | ACO | 5 | 5 | 387.137 | 0.968411 | 1.77202 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 20 | EHO | 5 | 5 | 446.649 | 34.9494 | 0.212849 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 20 | GA | 5 | 5 | 444.327 | 26.7481 | 0.303765 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 20 | PSO | 5 | 5 | 556.77 | 10.7364 | 0.208265 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 50 | ACO | 5 | 5 | 567.878 | 2.38533 | 4.44828 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 50 | EHO | 5 | 5 | 1128.12 | 64.5498 | 0.259571 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 50 | GA | 5 | 5 | 1138.78 | 65.6612 | 0.337527 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 50 | PSO | 5 | 5 | 1963.7 | 94.0941 | 0.517096 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 100 | ACO | 5 | 5 | 846.583 | 18.0518 | 10.1898 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 100 | EHO | 5 | 5 | 2599.61 | 91.7931 | 0.380495 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 100 | GA | 5 | 5 | 2733.43 | 125.618 | 0.457546 | 3000 | 0 |
| new_corrective_permutation_adaptation | TSP | 100 | PSO | 5 | 5 | 4351.22 | 104.263 | 1.16469 | 3000 | 0 |
| new_corrective_permutation_adaptation | VRP | 20 | EHO | 5 | 5 | 655.915 | 41.0863 | 0.445554 | 3000 | 0 |
| new_corrective_permutation_adaptation | VRP | 20 | PSO | 5 | 5 | 715.2 | 74.6163 | 0.421121 | 3000 | 0 |
| source_operator_configuration_ablation_active_clans | TSP | 8 | EHO | 5 | 5 | 277.232 | 0 | 0.249177 | 14350 | 0 |

A cost from an infeasible route cannot be interpreted as a valid solution. Instrumented source timings include validation/profiling overhead and unequal search budgets.

### Imaging appearance and stage time (mean over seeds)

| case_id | method | roi_input_similarity_psnr_db | identity_psnr_infinite | selected_slice_input_ssim_mean | selected_slice_roi_input_ssim_mean | enhancement_seconds | segmentation_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BRATS_001 | acor | 24.8784 | 0 | 0.980674 | 0.946278 | 0.355086 | 0.368628 |
| BRATS_001 | direct_otsu | — | 1 | 1 | 1 | — | 0.200731 |
| BRATS_001 | ga | 24.8661 | 0 | 0.980674 | 0.946268 | 0.290869 | 0.389462 |
| BRATS_001 | modified_eho | 26.3237 | 0 | 0.980315 | 0.948945 | 0.197391 | 0.219465 |
| BRATS_001 | original_eho | 23.649 | 0 | 0.981427 | 0.947556 | 0.208448 | 0.227939 |
| BRATS_001 | pso | 24.8784 | 0 | 0.980674 | 0.946277 | 0.207357 | 0.225924 |
| BRATS_002 | acor | 22.477 | 0 | 0.980749 | 0.962796 | 0.255143 | 0.268549 |
| BRATS_002 | direct_otsu | — | 1 | 1 | 1 | — | 0.184134 |
| BRATS_002 | ga | 22.4703 | 0 | 0.980758 | 0.9628 | 0.266553 | 0.260582 |
| BRATS_002 | modified_eho | 25.6142 | 0 | 0.975892 | 0.959254 | 0.200755 | 0.212184 |
| BRATS_002 | original_eho | 22.2719 | 0 | 0.982288 | 0.965097 | 0.22013 | 0.239108 |
| BRATS_002 | pso | 22.4819 | 0 | 0.980743 | 0.962793 | 0.239601 | 0.257888 |
| BRATS_003 | acor | 26.9976 | 0 | 0.97958 | 0.954503 | 0.301324 | 0.323896 |
| BRATS_003 | direct_otsu | — | 1 | 1 | 1 | — | 0.187183 |
| BRATS_003 | ga | 26.995 | 0 | 0.979588 | 0.954504 | 0.297364 | 0.297664 |
| BRATS_003 | modified_eho | 26.6997 | 0 | 0.978812 | 0.957656 | 0.260643 | 0.255255 |
| BRATS_003 | original_eho | 27.1991 | 0 | 0.980633 | 0.956989 | 0.222051 | 0.212661 |
| BRATS_003 | pso | 26.9976 | 0 | 0.97958 | 0.954503 | 0.326191 | 0.318354 |

Input similarity is a measure of departure from the input image. It is not noise-removal accuracy. Enhancement/segmentation times and process RSS are implementation measurements; end-to-end time also includes input/output, evaluation and mesh rendering.

## Scientific interpretation

Successful execution does not confirm the manuscript's universal superiority claims. Historical feasibility defects, constant-only MRI graphs and absent measurement provenance require revision of those claims. Fresh valid-route and image-mask results may be cited with their new protocol; they cannot be retroactively assigned to the original figures. A threshold segmentation surface is a useful reproducible baseline, but anatomical overlap determines its accuracy. Mesh smoothness or visual resemblance alone does not establish tumour detection or surgical suitability.

Five seeds give limited evidence about optimiser randomness. The continuous paired Wilcoxon tests include Holm adjustment and remain exploratory. Three patients cannot establish clinical generalization. All label-dependent metrics are evaluation only; no learned training, trained checkpoint or downstream diagnosis was introduced.

## Primary implementation references

Coordinate transforms follow the [NiBabel coordinate-system documentation](https://nipy.org/nibabel/coordinate_systems.html). Surface extraction follows [scikit-image Marching Cubes](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes). Dataset label/modality mapping and licensing are taken from the local `dataset.json`; labels are 0,1,2,3 in this Task01 release, rather than an assumed label4 mapping.

## Modality axis versus spatial depth

The screenshot on PDF page92 (printed page82) explicitly reports the enhanced slice and Mayavi input shape as (240,240,4). Task01 supplies four modalities per spatial slice, while the selected native image shape is (240,240,155,4). A four-channel slice must not be treated as four anatomical depth slices. Existing thin STL geometry with z extent0–3 is consistent with a possible modality/depth-axis confusion, but the absent original mesh source prevents proving its generating operation. The new pipeline extracts FLAIR[...,0] and preserves all155 spatial slices, image affine and q/s forms before surface extraction.

## Additional PDF configuration replays

| pdf_configuration | size | method | runs | cost_mean | cost_sd | feasible | calls_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| local | 15 | ACO | 6 | 320.526 | 0 | 6 | 5000 |
| local | 15 | EHO | 6 | 360.006 | 27.5356 | 6 | 1530 |
| local | 15 | GA | 6 | 486.76 | 22.5574 | 6 | 6000 |
| local | 15 | PSO | 6 | 546.753 | 31.9307 | 6 | 3031 |
| major | 1 | ACO | 3 | 0 | 0 | 3 | 0 |
| major | 1 | EHO | 3 | 0 | 0 | 3 | 0 |
| major | 1 | GA | 3 | 0 | 0 | 3 | 0 |
| major | 1 | PSO | 3 | 0 | 0 | 3 | 0 |
| major | 11 | ACO | 3 | 373.143 | 21.2155 | 3 | 800 |
| major | 11 | EHO | 3 | 316.974 | 35.8901 | 3 | 2280 |
| major | 11 | GA | 3 | 353.062 | 12.3988 | 3 | 3000 |
| major | 11 | PSO | 3 | 440.327 | 28.5159 | 3 | 1531 |
| major | 21 | ACO | 3 | 746.09 | 30.499 | 3 | 800 |
| major | 21 | EHO | 3 | 496.114 | 38.7352 | 3 | 2280 |
| major | 21 | GA | 3 | 778.803 | 85.5659 | 3 | 3000 |
| major | 21 | PSO | 3 | 823.047 | 29.2476 | 3 | 1531 |
| major | 31 | ACO | 3 | 1209.87 | 68.7112 | 3 | 800 |
| major | 31 | EHO | 3 | 703.128 | 27.0259 | 3 | 2280 |
| major | 31 | GA | 3 | 1194.97 | 29.8412 | 3 | 3000 |
| major | 31 | PSO | 3 | 1302.26 | 46.488 | 3 | 1531 |
| major | 41 | ACO | 3 | 1672.15 | 44.1771 | 3 | 800 |
| major | 41 | EHO | 3 | 1005.07 | 70.4159 | 3 | 2280 |
| major | 41 | GA | 3 | 1692.82 | 131.818 | 3 | 3000 |
| major | 41 | PSO | 3 | 1660.79 | 87.4557 | 3 | 1531 |
| major | 51 | ACO | 3 | 2054.61 | 86.5384 | 3 | 800 |
| major | 51 | EHO | 3 | 1274.44 | 40.1789 | 3 | 2280 |
| major | 51 | GA | 3 | 2156.4 | 17.1501 | 3 | 3000 |
| major | 51 | PSO | 3 | 2086.99 | 100.815 | 3 | 1531 |
| major | 61 | ACO | 3 | 2549.41 | 15.9614 | 3 | 800 |
| major | 61 | EHO | 3 | 1678.01 | 131.366 | 3 | 2280 |
| major | 61 | GA | 3 | 2676.66 | 96.0284 | 3 | 3000 |
| major | 61 | PSO | 3 | 2809.92 | 81.3311 | 3 | 1531 |
| major | 71 | ACO | 3 | 2981.4 | 78.1692 | 3 | 800 |
| major | 71 | EHO | 3 | 2081.38 | 120.779 | 3 | 2280 |
| major | 71 | GA | 3 | 3200.31 | 89.0722 | 3 | 3000 |
| major | 71 | PSO | 3 | 3182.66 | 110.21 | 3 | 1531 |
| major | 81 | ACO | 3 | 3470.49 | 71.3453 | 3 | 800 |
| major | 81 | EHO | 3 | 2357.24 | 97.9977 | 3 | 2280 |
| major | 81 | GA | 3 | 3595 | 213.248 | 3 | 3000 |
| major | 81 | PSO | 3 | 3556.42 | 55.6632 | 3 | 1531 |
| major | 91 | ACO | 3 | 3872.68 | 83.787 | 3 | 800 |
| major | 91 | EHO | 3 | 2626.58 | 81.4891 | 3 | 2280 |
| major | 91 | GA | 3 | 4028 | 143.046 | 3 | 3000 |
| major | 91 | PSO | 3 | 4106.68 | 107.42 | 3 | 1531 |

These recover the PDF harness settings separately from the notebook defaults. Operator/configuration correspondence is documented in `reports/pdf_code_coverage.md`.

### Overwritten source registration definitions

| protocol | task | method | runs | objective_mean | objective_sd | objective_median | objective_min | objective_max | seconds_mean | seconds_sd | evaluations_min | evaluations_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant1 | pso | 3 | 0.134025 | 0.000659863 | 0.134344 | 0.133267 | 0.134466 | 0.689876 | 0.0624926 | 1500 | 1500 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant1 | eho | 3 | 0.134638 | 0.000389306 | 0.134699 | 0.134222 | 0.134993 | 0.719197 | 0.0241432 | 1530 | 1530 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant1 | ga | 3 | 0.134705 | 0.000750018 | 0.135061 | 0.133844 | 0.135212 | 0.668077 | 0.0467384 | 1530 | 1530 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant1 | aco | 3 | 0.139428 | 0.00107839 | 0.139112 | 0.138544 | 0.14063 | 0.672847 | 0.0431503 | 1500 | 1500 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant2 | pso | 3 | 0.134025 | 0.000659863 | 0.134344 | 0.133267 | 0.134466 | 0.678469 | 0.0459084 | 1500 | 1500 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant2 | eho | 3 | 0.134529 | 0.000846897 | 0.134993 | 0.133551 | 0.135042 | 0.28128 | 0.0103277 | 630 | 630 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant2 | ga | 3 | 0.134705 | 0.000750018 | 0.135061 | 0.133844 | 0.135212 | 0.661136 | 0.0144658 | 1530 | 1530 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant2 | aco | 3 | 0.139428 | 0.00107839 | 0.139112 | 0.138544 | 0.14063 | 0.647515 | 0.0127105 | 1500 | 1500 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant3 | pso | 3 | 0.134025 | 0.000659863 | 0.134344 | 0.133267 | 0.134466 | 0.652739 | 0.0187285 | 1500 | 1500 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant3 | eho | 3 | 0.134638 | 0.000389306 | 0.134699 | 0.134222 | 0.134993 | 0.724165 | 0.051933 | 1530 | 1530 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant3 | ga | 3 | 0.134705 | 0.000750018 | 0.135061 | 0.133844 | 0.135212 | 0.66241 | 0.0498587 | 1530 | 1530 |
| new_experiment_recovered_dormant_source | synthetic_source_cell15_variant3 | aco | 3 | 0.139428 | 0.00107839 | 0.139112 | 0.138544 | 0.14063 | 0.669691 | 0.0249068 | 1500 | 1500 |

These previously dormant function groups are new seeded experiments on recovered function bodies. Their outcomes are not historical experiments simply because the definitions appear earlier in a notebook.
