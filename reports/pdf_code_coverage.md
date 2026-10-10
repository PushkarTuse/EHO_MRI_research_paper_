# PDF code coverage and recovered variants

Physical PDF page numbers are used below; printed page numbers in the report
are ten lower in its main chapters. Both PDFs were searched page by page for
every Python `def` and `class` identifier, then cross-referenced against the
preserved notebook sources. Every extracted definition name has a notebook
counterpart. The major report renders `__init__` as `init` in places; this is
a PDF text-extraction artifact, not a silently corrected algorithm.

Name matching alone does not prove identical code. Method updates, stopping
rules, input generation, budgets and harness settings were inspected separately.
Original machine-readable bodies provide execution source where PDF line
wrapping and glyph loss prevent valid Python extraction. All original PDF text,
notebook cells and newly derived parameter harnesses remain preserved.

## Major project report: 105 pages

| Physical pages | Content / function group | Matched source | Coverage / distinction |
|---|---|---|---|
| 1–37 | Front matter, literature, algorithm theory and methodology | Manuscript/theory context | No additional complete Python routine. The dimensionality/adaptive/competitive discussion is not itself an executable implementation. |
| 38–45 | TSP: distance generator, GA operators, Elephant/clan crossover, Ant route construction, Particle swaps and comparison harness | Notebook cell33 functions | PDF-only harness population30/clans15, cities1,11,...91 differs from notebook100/100 and0,10,...90. Replayed by `replay_pdf_configs.py`; EHO150 loops and ACO16 remain unchanged. |
| 46–48 | TSP output charts and discussion | Cell33-like benchmark family | Figures are historical outputs; no additional executable algorithm. Fresh reruns do not authenticate plotted historical values. |
| 49–54 | Ackley objective, Particle/PSO, velocity-based Elephant/EHO, GA and Ant/ACO; comparison harness | Notebook cell2 | Full notebook execution plus repeated source benchmark runs cover these functions. This EHO is the source velocity/clan implementation, not the manuscript's continuous dimensionality-scaled model. |
| 55–56 | Rastrigin narrative, convergence output and figure | Notebook cells6 and7; local PDF4–7 | The major report supplies output values, not additional Rastrigin code. Both source variants are preserved and full notebook execution covers them. |
| 57–58 | VRP discussion / route figure | Notebook cells10 and11; local PDF8–13 | No extra executable VRP implementation in these pages. Cell10 dependency failure is retained; cell11 supplies complete equivalent routing operators and is executed. |
| 59–61 | Healthcare analogies, registration explanation, beginning of transformation routine | Notebook cell15 variant1 | Conceptual diagnostic/operational analogies do not constitute executed diagnosis or segmentation code. |
| 61–65 | Rotation/circular translation, MSE, EHO, GA, ACO; first registration definition group | Cell15 variant1, lines11–238 | Uncapped EHO definition group; its body matches variant3. Source definitions are recovered for separate controlled replay. |
| 66–72 | Registration redefinition with capped EHO | Cell15 variant2, lines239–476 | EHO capped20. Algorithm bodies match the final variant4, which the historical harness actually invokes. |
| 73–79 | Registration redefinition with uncapped EHO | Cell15 variant3, lines477–704 | Algorithm bodies identical to variant1 under AST comparison; duplicate definitions are not independent evidence. |
| 80–89 | Final registration redefinition, plotting, test harness and historical output | Cell15 variant4, lines705–1025 | Final definitions prevail. Full notebook and repeated registration-source measurements execute the30-candidate50-requested-iteration harness, including the EHO20 cap. |
| 90–91 | MRI enhancement prose / screenshots | Manuscript imaging description | No image enhancement objective or executable MRI loading/segmentation routine is supplied here. |
| 92–95 | MRI slice116 screenshot; hand-entered PSNR/SSIM/time chart source; plotted scalability and Mayavi view | Notebook cell23 chart; cell17 scalability | The chart reads constant arrays and hypothetical uncertainty. Executing it regenerates a chart rather than measuring MRI quality. |
| 96 | Photographs of thin slice mesh and full brain surface views | Historical images | No original source for masks, slice assembly, surface extraction or full-volume reconstruction. New imaging code is explicitly reconstructed separately. |
| 97–105 | Discussion, outcomes, references | Manuscript context | No further Python function or class identifier is present. |

## Local code PDF: 40 pages

| Physical pages | Content / function group | Matched notebook cell | Coverage / distinction |
|---|---|---|---|
| 1–3 | Ackley comparison and historical printed output | 1–3 | Complete source numerical methods; chart constants are historical plotting input. |
| 4–5 | First Rastrigin comparison | 6 | Source PSO/EHO variant with initial harness. |
| 5–7 | Rastrigin redefinition with convergence history / printed values | 7 | Later Rastrigin definitions are separately executed in notebook order. |
| 8–9 | Initial VRP Particle/PSO and incomplete comparison harness | 10 | Calls helpers before they are defined. Original cell10 fails as supplied and the failure is saved. |
| 9–13 | Complete VRP utilities, Particle/PSO, Elephant/EHO, plotting harness and output | 11 | Executed; external feasibility observers audit omissions, duplicates, capacities and customer IDs. |
| 14–16 | Registration variant1 | 15, lines11–238 | Uncapped group. |
| 17–19 | Registration variant2 | 15, lines239–476 | Capped EHO20 group. |
| 19–22 | Registration variant3 | 15, lines477–704 | Identical method bodies to variant1. |
| 22–26 | Final registration variant4, plot/test harness and output | 15, lines705–1025 | Identical algorithms to variant2; this final definition group is called. |
| 27–30 | Registration scalability / increasing-dataset experiment | 17 | Full notebook rerun executes10,20,30,40,50 image-pair settings. Generator resets seed42 on each call, so pairs repeat. EHO20 vs others50 iterations. |
| 31–32 | Mayavi limitation statement and constant MRI chart | 22–23 | No actual enhancement/3D implementation; arrays are13.72/13.72/14.33 PSNR, .67/.67/.89 SSIM and .3004/.3948/.6414 seconds in separately ordered labels. Error bars explicitly hypothetical. |
| 33–37 | TSP15-city method definitions and twice-run harness | 28 function bodies | PDF population30/clans15 differs from notebook20/20. PDF EHO decays mutation .2*(1-t/T); ACO beta2/deposit100. Separate PDF-configuration replay preserves both successive comparisons. |
| 38–40 | Final TSP scaling definitions; PDF ends partway through Particle class | 33 | Incomplete PDF tail recovered from the complete machine-readable cell33; no unique unseen routine. |

## Registration redefinition equivalence

Four groups occur in notebook cell15, but only two distinct algorithm sets exist.
AST comparison ignores comments/line positions while retaining operators,
constants and function structure:

- Variants1 and3 share all13 definitions exactly.
- Variants2 and4 share all13 algorithm/image definitions exactly; variant4 adds
  `plot_transformation` and the comparison test harness.
- Between the uncapped and capped groups, only `EHOElephant` and
  `eho_registration` change. The remaining11 shared definitions are identical.

Literal full-cell execution installs all four sets in order, then invokes only
the final harness. Earlier definitions therefore require a separately labelled
experiment if their behavior is to be measured. `replay_pdf_configs.py` saves
each group's exact source and provenance before controlled replay. The first
completed run may include variants1,2,3; repeated equivalent bodies must not
increase the claimed independent sample size. Future default runs use only
variant1 because variant3 is equivalent and variant2 is covered by finalvariant4.
These are random-field synthetic registration tests, not anatomical tumour
prediction or clinical diagnosis.

## VRP dependency and equivalence audit

Cell10's original first failure is `generate_customers` undefined. That cell
also expects an EHO function not yet supplied. Its `Particle` class is AST
identical to cell11. Its `pso_vrp` search is identical except that cell10 returns
two values while cell11 appends a third `None`. Consequently cell11 execution
covers the same search operators; the cell10 failure remains visible and is not
relabeled successful. A future dependency adapter would change execution
plumbing rather than supply a new algorithmic contribution.

## MRI/3D screenshots versus executable code

The major PDF92 screenshot prints enhanced slice116 arrays of shape
`(240,240,4)` and an alleged Mayavi reconstruction volume of the same shape.
The local dataset is4-D with four modality channels and155 spatial slices.
The screenshot is consistent with a modality axis being interpreted as a
four-layer spatial axis. Existing STL pairs span z0–3, which supports that
concern; original source/provenance is absent, so this relationship remains an
explicit inference rather than proof of the generating code.

The screenshot does not display a saved tumour-prediction mask. PDF96 includes
brain photographs, but these do not establish a prediction method, accuracy,
patient identity, affine/spacing or reproducible full-volume construction.
The new `imaging.py` therefore loads actual native volumes, keeps modality and
spatial axes distinct, predicts a separate candidate mask, evaluates against
reference labels afterward, and exports full-volume geometry. Its newly
reconstructed methods and results are distinguished from historic photographs.

## Additional executable coverage conclusion

No extra unique Python routine name was left unmatched in either PDF.
Two distinct PDF-only TSP harness configurations and the unique uncapped
registration group were identified and supplied executable replay code. The
major one-city case contains source guards in all four methods: actual smoke
execution returns the valid one-city route and distance0 with zero objective
evaluations. No expected failure is invented and no city is silently skipped.

PDF-only configurations use the original generated Euclidean matrix. Replacing
that matrix with MRI intensities would change their mathematical use case.
MRI enhancement, segmentation and reconstruction consume the actual dataset
through the separately reconstructed imaging implementation.

Full supplementary replay command:

```powershell
& 'code_reruns/.venv/Scripts/python.exe' -X utf8 -u 'code_reruns/src/replay_pdf_configs.py' --output 'code_reruns/results/new_run/pdf_configs' --seeds '0,1,2' --variants '1'
& 'code_reruns/.venv/Scripts/python.exe' -X utf8 'code_reruns/src/inventory_pdf_code.py' --run 'code_reruns/results/run_20261005'
```

The first command performs measured supplementary experiments sequentially;
the second refreshes this coverage report using actual completion records.

## Execution ledger at report generation

Original notebook: 33 cells attempted, 32 successful; failures: 10.

Saved supplemental PDF TSP rows: 144; saved dormant-registration rows: 36. Complete all-mode marker: present.

Completed supplementary output directory: `D:\RANDOM\research_paper_iim\code_reruns\results\run_20261005\pdf_configs`. The measured first run uses variants1,2,3; equivalent-definition repeats are labelled above and must not be counted as independent algorithmic evidence.

Machine-readable per-page names, matching cells and AST equivalence checks are saved in `reports/pdf_code_coverage.json`. Runtime completion is determined from saved outputs; a source match by itself is not a successful execution.
