# Continuous optimisation and registration: provenance

## Recovered-source reruns

`benchmarks_continuous.py --mode source` isolates imports, classes and function definitions from MRI notebook code cells 2 (Ackley), 6 and 7 (Rastrigin). Function bodies are unchanged. Every objective call is traced; this includes redundant calls made by historical implementations. NumPy's legacy RNG and Python's RNG are reset before each method. These new seeded runs cannot reproduce an unrecorded historical seed or hardware timing. Returned objective, independently re-evaluated returned position, and best value observed by the tracer are saved separately, exposing any inconsistency instead of repairing it silently.

`registration.py --mode source` similarly replays cell 15's active definitions, using the original seed-42 random field, linear rotation, circular integer translations, and full-array MSE. Its EHO cap is 20 iterations despite a requested 50; the other source methods retain their original loops. Source objective-call counts differ. Source results therefore do not constitute a fair equal-budget method ranking or anatomical registration validation.

## New bounded reference implementations

`optimizers.py` supplies a shared continuous objective-evaluation cap, including initialization, leader updates, separation and all candidate evaluations. Frozen source positions make clan updates simultaneous. The globally best evaluated candidate is retained independently of later population deterioration. Initialization is shared by seed and bounds; each method subsequently uses its own sequence of random operations. A generation may end part-way through when the objective budget is exhausted.

`original_eho` implements leader attraction, matriarch-to-clan-centre updating and uniform replacement of a clan's worst member. Its finite box clipping and continuous replacement rule are explicit implementation decisions. It is a literature-aligned reference, not recovered authors' EHO software.

`modified_eho` reconstructs the draft's proposed follower attraction scaled by dimension to the power minus gamma, attraction declining to a floor, repulsion increasing toward a cap, and interpolation-based poor-member separation. Progress is measured by consumed objective evaluations rather than manuscript iteration count so that comparisons have equal computational search budgets. The centre update uses beta_center, distinct from repulsion_max and dimensional exponent gamma. Coefficients are prespecified defaults exposed in the API. This complete combination was not found in the recovered historical benchmark bodies; new results cannot retrospectively validate the historical variant.

`pso` uses personal/global bests and bounded positions; `ga` uses tournament selection, arithmetic crossover, Gaussian mutation and elite survival. `acor` is a new ACOR-inspired rank-weighted Gaussian archive sampler. It is not discrete Ant Colony System and not the manuscript's historical continuous pheromone-shift implementation. All baseline names, operator choices and parameter values are saved with raw results.

## Anatomical rigid perturbation experiment

Optional `--anatomical` accepts a 3D NIfTI or one selected channel of 4D data; Task01_BrainTumour channel 0 is FLAIR. It uses axis-2 slice 71 by default, image-only positive-pixel percentile normalization and a declared resize to maximum 128 pixels. A known 12-degree, (4,-3)-pixel pull mapping generates a moving image with the inverse affine transform. Candidate maps have the same pull convention. Registration MSE uses a fixed interior foreground mask; no segmentation reference is loaded, used to choose the slice, or used as an objective.

The additional geometric endpoint is RMS mapping error on five geometric grid points in resized-image pixels. These are not expert anatomical landmarks, and the endpoint is not clinical target-registration error. Interpolation prevents an exactly zero residual even at the known transform. This single-slice synthetic perturbation of an anatomical scan tests recovery of a specified transform; it is not independent real-patient registration or clinical diagnostic accuracy.

## Reporting and statistics

Raw positions, complete incumbent histories, objective-call counts, execution times, source hashes and configurations are saved. Summary mean and sample SD describe repeated seeds within one fixed task instance. Paired Wilcoxon tests and Holm adjustment are exploratory, with very small seed counts; seeds are not independent patients and do not establish cohort generalization. Seed uncertainty is kept separate from MRI patient variation.

Tests check exact objective accounting, bounded evaluated positions, copied consistent incumbents, monotone best-observed histories, seed reproducibility, known zero benchmark minima, affine identity and translation signs, inverse transform generation, and 4D image-only loading. They make no assertion that one optimizer must win.

## Shifted-function ablations and origin bias

The EHO matriarch-to-centre update multiplies the centre by beta_center, contracting coordinates toward zero. Strong values on the unshifted Ackley and Rastrigin functions, whose minima are at zero, may reflect this origin dependence. `ablations.py` therefore uses two fixed, explicitly recorded optimum translations chosen before comparative runs. All six EHO variants share bounds, initialization seeds and objective-call budgets. Variants disable dimension scaling, coefficient schedules, repulsion or the reconstructed interpolation-based separation individually; the last retains the original uniform worst-member replacement. Prespecified settings are unchanged across functions and variants. These experiments test the newly reconstructed combination and its components rather than asserting that the historical manuscript implementation contained them.
