# Code completeness audit for repository publication

Audited 11 October 2026 against the actual source files, coverage reports and saved execution records. This audit does not rerun experiments or modify their implementations.

## Conclusion

The declared end-to-end experimental pipeline is executable and has completed its saved run: source comparisons, corrected routing, continuous optimization, ablations, registration, MRI preprocessing/enhancement, an exploratory segmentation baseline, full-volume surface generation and claim comparison. **The original historical MRI pipeline has not been completely recovered.** Missing enhancement, segmentation and reconstruction source was replaced with explicitly documented new implementations. Those implementations must be published as reconstructed methods, rather than as the source that generated the historical manuscript figures.

Publication is appropriate as a reproducible research/code-recovery repository with this distinction prominently stated. It does not establish publication readiness of the manuscript or verify its blanket superiority claims.

## Coverage by use case

| Use case | Recovered original code | Repair/reconstruction | Saved execution evidence | Historical completeness |
|---|---|---|---|---|
| Source extraction and inventory | Two notebooks, 35 individually preserved cells, both code PDFs and added `code_snippets.txt` | Page/function correspondence and source hashes added | 33 MRI notebook cells attempted: 32 successful, cell10 dependency failure preserved | All PDF function names have counterparts; matching names alone do not prove identical implementations |
| Exact small TSP | Brute-force solver recovered | Valid common eight-city instance and a syntax-only adapter for the second brute/EHO source | Exact optimum, route validity and heuristic gaps saved | Original first matrix is ragged; second source has invalid syntax. Neither original top-level program is silently labelled runnable |
| Original EHO/GA/ACO/PSO TSP | Notebook cells28/33; 15-city and95-city snippet programs; distinct PDF harness configurations | Observer harnesses record routes and objective calls without changing source method bodies | 24 snippet trials, 144 PDF TSP trials; recovered-source routing included in170 routing rows | Historical seeds/settings/table-generating provenance remains incomplete; singleton clans disable follower updates in some originals |
| Capacity-constrained VRP | Cell11 complete utilities and search; cell10 partial equivalent search | New feasibility-preserving decoder/search, independent original-route validator | Source omissions/duplicates/capacities recorded; corrected valid routes saved | Cell10 fails before helpers are defined; the original distance-only objective does not enforce feasibility |
| Ackley and Rastrigin | Notebook cells2/6/7 | New shared-budget reference methods alongside unchanged-body runs | 74 continuous trial rows, objective histories and measured timing | Historical complete seed/hardware provenance unavailable; methods and budgets differ |
| Continuous EHO modification | Theory describes dimensional scaling and adaptive parameters | New prespecified complete implementation in `optimizers.py`, with named parameters and exact budget accounting | Shared-budget trials and60 ablation trials, including shifted optima | Complete historical combined formulation was not found in recovered source; results belong to the reconstructed hypothesis |
| Classical continuous baselines | Historical task-specific PSO/GA/ACO code preserved | New bounded PSO/GA and ACOR-inspired archive sampler | Configurations, evaluated incumbents and complete histories saved | ACOR-inspired baseline is explicitly distinct from original pheromone-shift code and discrete ACS |
| Synthetic registration and scaling | Cell15 repeated definitions and cell17 workload | Dormant definitions isolated; active originals preserved | 62 registration rows,36 dormant-definition rows, full scaling replay | Original input generator repeats identical random fields; EHO20 versus other50 iterations prevents equal-budget speed claims |
| Anatomical registration | No corresponding historical anatomical experiment source | New known rigid perturbation of BRATS_001 FLAIR slice71 with geometry evaluation | Five seeds per reference optimizer, images and geometric errors saved | One imposed-transform slice experiment; no independent clinical registration validation |
| MRI normalization/enhancement | Percentile/slice-processing theory and literal plotting arrays; no executable historical imaging objective | New gamma/contrast/departure/saturation objective and native-grid volume outputs | Three patient volumes, stochastic seeds0/1/2; appearance metrics and stage timings saved | Original clean/noisy reference, case identity, enhancement measurements and code remain unavailable; input similarity is not denoising accuracy |
| MRI segmentation before3D | No historical executable tumour-prediction routine in supplied materials | New image-only multilevel Otsu/high-intensity/component baseline with separate reference-mask evaluation | 48 prediction records: five stochastic methods×three seeds×three cases, plus three direct-Otsu records | Whole-tumour proxy, not learned tumour-subregion classification; no ML/DL training or benchmark completed |
| Full-volume brain/prediction/reference3D | Marching Cubes description and existing STL artefacts | New affine-aware native-mask geometry export; stride2 display meshes and self-contained HTML | All three case views and PLY/STL outputs saved; native masks evaluated independently | Original surface-generation source absent. Existing EHO/PSO STL pairs are byte-identical and thin; new meshes cannot authenticate them |
| Claim comparison and reproducibility | Original/revised manuscripts and historical tables/figures | New audit, counted budgets, machine/runtime manifests and output validation |72 unit tests and552 saved-output checks passed; all declared run stages completed | Successful validation verifies executable artifacts, not universal scientific superiority |

## Added snippets were fully accounted for

`code_snippets.txt` contains two TSP programs, not MRI implementation: block1 has15 cities and block2 has95. The original bytes and two executable blocks are preserved, with SHA256 provenance. Both were replayed for seeds0/1/2 with every returned tour checked. Their algorithm differences and unequal populations are retained. They supply no missing historical continuous EHO, enhancement or tumour-prediction code.

## Scope boundaries that must remain visible

- All484 listed image/label pairs were inventoried. MRI quantitative evaluation covers only BRATS_001, BRATS_002 and BRATS_003. Three stochastic seeds per patient are not extra patients.
- No learned model was trained or compared. No current output establishes tumour-subregion classification, diagnosis, real-time clinical readiness, hospital cost savings or surgical validation.
- Original synthetic scalability is a repeated-input workload, not a50-patient experiment.
- Historical MRI graphs use literal values and hypothetical uncertainty; these are preserved historical plotting inputs, not newly measured MRI results.
- Original failed sources remain evidence: MRI cell10 `generate_customers` NameError; brute-force ragged matrix; brute/EHO trailing syntax artifact. Source repair adapters and newly corrected methods are labelled separately.
- Fresh source timing includes current hardware and, where used, observer overhead. It cannot retrospectively verify the old table timings.
- The actual saved MRI run uses seeds0/1/2. Method notes also describe a reproducible five-seed option; do not confuse that option with the completed run.

## Repository inclusion and exclusion recommendations

Include the runnable `src/`, `tests/`, dependency lock, runner scripts, method/coverage notes, source hashes, recovered original cells and notebooks, original snippets, measured tabular results and histories, stage ledger, relevant plots and a documented final3D reference/view. Include the user's original and rewritten manuscripts and requested screen-recording video, identified as research drafts and a visualization recording.

Exclude the commented-review manuscript as requested; `.venv`, caches, duplicate extracted `Code_bundle_` trees, duplicate ZIPs, credentials/tokens, private account/session material, and unrelated personal or administrative documents. Store the dataset externally with acquisition/licensing instructions instead of committing the full clinical image corpus. Large derived NIfTI/mesh/HTML/video assets should use Git LFS or release assets with a manifest; the prediction/reference distinction and dataset-derived attribution must remain clear. Preserve historical and new measurements in different paths.

## Evidence consulted

- `code_reruns/README.md`
- `code_reruns/reports/CODE_INVENTORY.md`
- `code_reruns/reports/pdf_code_coverage.md` and JSON counterpart
- `code_reruns/reports/routing_method_notes.md`
- `code_reruns/reports/source_method_notes.md`
- `code_reruns/reports/imaging_method_notes.md`
- Existing `code_reruns/src/` modules, including `optimizers.py`
- `code_reruns/results/run_20261005/stage_ledger.json`
- `code_reruns/results/run_20261005/reports/COMPLETION_SUMMARY.json`
- `code_reruns/results/run_20261005/reports/CLAIMS_VS_RERUNS.md`
- `code_reruns/results/run_20261005/logs/tests.log`
- `code_reruns/results/source_replay/brute_source_validation.json` and cell10 failure log

The conclusions above are based on the recorded files and execution ledgers. No additional experiments were represented as completed during this publication audit.
