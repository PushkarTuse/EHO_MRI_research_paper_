# Code inventory and execution checklist

This workspace contains source extraction, faithful reruns where runnable source exists,
and separately labelled corrected or reconstructed experiments. New results must not
be presented as recovery of undocumented historical measurements.

| Stage | Sources | Execution and saved evidence |
|---|---|---|
| Source and data inventory | Both code PDFs, both notebooks, original/revised manuscript, dataset.json | Source hashes, every notebook cell, PDF page text, available cases |
| Exact and heuristic TSP | Notebook TSP/brute-force cells; report pp38–48 | Exact small-instance optimum; EHO/GA/PSO/ACO routes, time, feasibility, repeated seeds |
| Capacitated VRP | Notebook VRP cells; local code PDF pp8–13 | Legacy invalid-route diagnosis; corrected constrained routing, costs and route plots |
| Rastrigin | Notebook cells; report pp55–56 | Recorded source variant and controlled methods; objectives, seeds, convergence, mean and SD |
| Ackley | Notebook cells; report pp49–54 | Source variant and controlled methods; quality/time trade-off and evaluation counts |
| Synthetic registration | Repeated notebook definitions; report pp61–89 | Preserved transform conventions; MSE, timing, unequal historical budgets versus controlled budget |
| Repeated-pair scalability | Notebook workload cell | Legacy repeated identical inputs explicitly labelled; no independent-patient claim |
| MRI image processing | Report pp90–96; plotting-only MRI notebook cells | Label source formulas versus reconstructed objective; image outputs and actual metrics |
| MRI segmentation before modelling | Dataset image modalities and held-out masks | Image-only predicted whole-tumour masks, separate reference masks; Dice/IoU/precision/recall |
| Slice and full-volume 3D | Report surface description; existing source STL files | Anatomically indexed volume and predicted-mask meshes in physical coordinates; reference mesh separate |
| Claims comparison | Original/revised manuscript tables and figures | Old numbers, fresh run summaries, comparability limits and conclusions |
| Reproducibility | Current environment and runner | Pinned dependencies, commands, configuration, tests, machine details, run logs |

The original MRI plotting cell contains constants and hypothetical error bars. Running
that cell reproduces a chart, not an enhancement experiment. The report describes
Marching Cubes and rendering without providing a recoverable imaging objective or
validated tumour-prediction routine in those cells. Reconstructed modules are clearly
identified. Ground-truth labels are used for evaluation and reference rendering only.

The initial imaging run uses three deterministically selected available labelled
volumes and multiple optimiser seeds. It runs full-volume segmentation and modelling;
this is a reproducibility study, not evaluation of all 484 listed training cases.
No test-set labels, neural network training or clinical deployment are implied.

## Extracted code cells

| Notebook | Code cell | ID | Functions | Syntax |
|---|---:|---|---|---|
| mri_optimisation.ipynb | 1 | FWSk31Pht-45 |  | valid |
| mri_optimisation.ipynb | 2 | NUWPKqmHsw-M | ackley, pso_ackley, eho_ackley, ga_ackley, aco_ackley, test_optimization_algorithms_on_ackley | valid |
| mri_optimisation.ipynb | 3 | Ym-Tygbqt7OU |  | valid |
| mri_optimisation.ipynb | 4 | 4M2RU1aOsyhd |  | valid |
| mri_optimisation.ipynb | 5 | VJruhXC2w7QL |  | valid |
| mri_optimisation.ipynb | 6 | DqvpY4QhxQKc | rastrigin, pso_rastrigin, eho_rastrigin, test_pso_vs_eho_on_rastrigin | valid |
| mri_optimisation.ipynb | 7 | x-YFemkPxWV_ | rastrigin, pso_rastrigin, eho_rastrigin, test_pso_vs_eho_on_rastrigin_with_values | valid |
| mri_optimisation.ipynb | 8 | TWsZGnVczEzV |  | valid |
| mri_optimisation.ipynb | 9 | clOfZzt90M-c |  | valid |
| mri_optimisation.ipynb | 10 | b4zg1Jr_0SW8 | pso_vrp, test_pso_vs_eho_on_vrp | valid |
| mri_optimisation.ipynb | 11 | am4gqqH21Rvn | vrp_cost, generate_customers, calc_distance_matrix, visualize_routes, pso_vrp, eho_vrp, test_pso_vs_eho_with_visualization | valid |
| mri_optimisation.ipynb | 12 | 3zplxKU44mnk |  | valid |
| mri_optimisation.ipynb | 13 | vHjv9kCv7Amr |  | valid |
| mri_optimisation.ipynb | 14 | JLNpRtXI7DcC |  | valid |
| mri_optimisation.ipynb | 15 | SE8d7DD07EZu | generate_image, apply_transformation, mse, objective_function, pso_registration, eho_registration, ga_crossover, ga_mutate, ga_registration, aco_registration, generate_image, apply_transformation, mse, objective_function, pso_registration, eho_registration, ga_crossover, ga_mutate, ga_registration, aco_registration, generate_image, apply_transformation, mse, objective_function, pso_registration, eho_registration, ga_crossover, ga_mutate, ga_registration, aco_registration, generate_image, apply_transformation, mse, objective_function, pso_registration, eho_registration, ga_crossover, ga_mutate, ga_registration, aco_registration, plot_transformation, test_optimization_algorithms_on_medical_image_registration | valid |
| mri_optimisation.ipynb | 16 | 3net9pLwAmpI |  | valid |
| mri_optimisation.ipynb | 17 | JSUoVdCS7dZ- | generate_image, apply_transformation, mse, objective_function, pso_registration, eho_registration, ga_crossover, ga_mutate, ga_registration, aco_registration, run_experiment_with_increasing_datasets, plot_execution_time_vs_dataset_size | valid |
| mri_optimisation.ipynb | 18 | mlJWMiXwArZ- |  | valid |
| mri_optimisation.ipynb | 19 | mIL4-9Y2BKu1 |  | valid |
| mri_optimisation.ipynb | 20 | tQWwLYbTBTtY |  | valid |
| mri_optimisation.ipynb | 21 | rkCjgCGQBUXR |  | valid |
| mri_optimisation.ipynb | 22 | Poj47BoSBc10 |  | valid |
| mri_optimisation.ipynb | 23 | 2tjKZcqUBlvN |  | valid |
| mri_optimisation.ipynb | 24 | wxTV6CeXBrTV |  | valid |
| mri_optimisation.ipynb | 25 | zymAfEfyCjgi |  | valid |
| mri_optimisation.ipynb | 26 | D5eetr5yCk-4 |  | valid |
| mri_optimisation.ipynb | 27 | tIjPvx1fCqE2 |  | valid |
| mri_optimisation.ipynb | 28 | xvW4cpuqDlgm | generate_distance_matrix, calculate_route_length, order_crossover, swap_mutation, initialize_population, select_parents, ga_tsp, elephant_herding_optimization, aco_tsp, pso_tsp | valid |
| mri_optimisation.ipynb | 29 | qGalLxxRXjwL |  | valid |
| mri_optimisation.ipynb | 30 | cU7GsB9kXqGS |  | valid |
| mri_optimisation.ipynb | 31 | jQUu5RDeXwHq |  | valid |
| mri_optimisation.ipynb | 32 | E0k5ZsFfX3_y |  | valid |
| mri_optimisation.ipynb | 33 | IM37HOmAUhET | generate_distance_matrix, calculate_route_length, order_crossover, swap_mutation, initialize_population, select_parents, ga_tsp, elephant_herding_optimization, aco_tsp, pso_tsp | valid |
| brute_force.ipynb | 1 | gNj0hDkTRNGx | generate_distance_matrix, tsp_brute_force, main | valid |
| brute_force.ipynb | 2 | B4Liisd2QNS5 |  | invalid syntax, line 152 |

Listed training cases: 484. Available image/label pairs: 484.

## Additional source and missing-stage completion

`code_snippets.txt` supplies two complete TSP programs: 15 cities (30 candidates,
15 EHO clans) and 95 cities (50 EHO/GA candidates, five EHO clans, ten ACO/PSO
candidates). Both are preserved in `sources/code_snippets_original.txt` and
`code_snippets_block_1.py` / `code_snippets_block_2.py`. Their original algorithms
are replayed, with route validation and actual objective-call counts. Neither
program reads MRI or contains the continuous dimensionality-scaled modification.

| Missing original executable stage | Theory available | Completed implementation and evidence |
|---|---|---|
| Complete modified continuous EHO | Dimensional scaling, attraction/repulsion schedules, poor-member separation | `optimizers.py`: prespecified reconstructed formulation; `ablations.py`: component and shifted-function experiments |
| MRI enhancement objective | Percentile normalization, contrast/noise/structure discussion; plotted PSNR/SSIM constants | `imaging.py`: declared contrast/departure/saturation objective with saved transformed volumes; input-similarity metrics labelled accordingly |
| Tumour-prediction function | Tumour localisation described without prediction rule | `imaging.py`: new image-only FLAIR/Otsu/component baseline, predictions saved before reference labels are opened, independently evaluated |
| Full-volume reconstruction source | Volumetric assembly and Marching Cubes description; surface screenshots | `imaging.py`: physical-coordinate brain-context/predicted/reference meshes for all selected cases |
| Complete historical provenance | Tables/figures and some notebook outputs | `compare_claims.py`: historical claims remain distinct from new measurements; source hashes, run configurations, logs and stage ledger saved |

The missing stages have executable replacements with explicit mathematical choices.
Their fresh results test those choices; they do not prove that these implementations
generated the original manuscript's numbers or figures. Routing/function benchmarks
use their own original synthetic inputs; only imaging stages consume MRI data.
