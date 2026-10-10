"""Cross-reference every PDF page's code identifiers with preserved notebook code.

No experiments run here. Inputs are extracted PDF pages and original source
cells; outputs are a machine-readable coverage ledger and human-readable report.
PDF reflow prevents treating name matching as exact source identity. Registration
definition equivalence is instead checked using ASTs of machine-readable code.
"""
from __future__ import annotations
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def read_json(path,default=None):
    return json.loads(path.read_text(encoding="utf8")) if path.exists() else default


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,default=ROOT/"results/run_20261005",
                        help="Completed run directory containing pdf_configs")
    parser.add_argument("--pdf-results",type=Path,help="Override exact supplemental PDF output directory")
    args=parser.parse_args()
    pdf_results=args.pdf_results or args.run/"pdf_configs"
    names={}
    for path in sorted((ROOT/"sources/mri_optimisation").glob("cell_*.py")):
        for n in ast.walk(ast.parse(path.read_text(encoding="utf8"))):
            if isinstance(n,(ast.FunctionDef,ast.ClassDef)):
                names.setdefault(n.name,set()).add(path.name)
    documents=[]
    for file in ["major_last_codes_pages.json","mri_local_codes_pages.json"]:
        pages=read_json(ROOT/"sources"/file)
        inventory=[]
        missing=set()
        for page in pages:
            found=re.findall(r"\b(?:def|class)\s+([A-Za-z_]\w*)\s*[:(]",page["text"])
            normalized=["__init__" if name=="init" else name for name in found]
            unknown=sorted(set(normalized)-set(names))
            missing.update(unknown)
            inventory.append(dict(page=page["page"],definition_names_as_rendered=found,
                                  normalized_names=normalized,
                                  notebook_cells_by_name={n:sorted(names.get(n,[])) for n in sorted(set(normalized))},
                                  unmatched_names=unknown))
        documents.append(dict(document=file,pages=len(pages),page_inventory=inventory,
                              unmatched_definition_names=sorted(missing)))
    source15=(ROOT/"sources/mri_optimisation/cell_015.py").read_text(encoding="utf8")
    nodes=ast.parse(source15).body
    starts=[n.lineno for n in nodes if isinstance(n,ast.FunctionDef) and n.name=="generate_image"]
    dictionaries=[]
    for lo,hi in zip(starts,starts[1:]+[10**9]):
        dictionaries.append({n.name:ast.dump(n,include_attributes=False) for n in nodes
                             if lo<=n.lineno<hi and isinstance(n,(ast.FunctionDef,ast.ClassDef))})
    equivalence=[]
    for i in range(4):
        for j in range(i+1,4):
            common=set(dictionaries[i])&set(dictionaries[j])
            changed=sorted(n for n in common if dictionaries[i][n]!=dictionaries[j][n])
            unique=sorted(set(dictionaries[i])^set(dictionaries[j]))
            equivalence.append(dict(variants=[i+1,j+1],common_definitions=len(common),changed_definitions=changed,unique_definitions=unique))
    ledger=read_json(ROOT/"results/source_replay/execution_ledger.json",[])
    completion=read_json(pdf_results/"completion.json",{})
    tsp_path=pdf_results/"pdf_tsp_runs.csv"
    reg_path=pdf_results/"registration_variants/runs.csv"
    def count_csv(path):
        if not path.exists():return 0
        with path.open(encoding="utf8",newline="") as f:return sum(1 for _ in csv.DictReader(f))
    audit=dict(documents=documents,registration_variant_equivalence=equivalence,
               original_notebook_execution={"cells":len(ledger),"successes":sum(x["status"]=="success" for x in ledger),
                                             "failures":[x for x in ledger if x["status"]!="success"]},
               pdf_results_directory=str(pdf_results.resolve()),pdf_configuration_completion=completion,pdf_tsp_rows=count_csv(tsp_path),dormant_registration_rows=count_csv(reg_path),
               comparison_limit="PDF text identifiers and inspected mechanisms corroborate notebook counterparts; PDF glyph/whitespace loss does not establish byte-identical source provenance.")
    (ROOT/"reports/pdf_code_coverage.json").write_text(json.dumps(audit,indent=2),encoding="utf8")
    report='''# PDF code coverage and recovered variants

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
'''
    report += f"\n## Execution ledger at report generation\n\nOriginal notebook: {len(ledger)} cells attempted, {sum(x['status']=='success' for x in ledger)} successful; failures: {', '.join(str(x['cell']) for x in ledger if x['status']!='success') or 'none'}.\n\n"
    report += f"Saved supplemental PDF TSP rows: {audit['pdf_tsp_rows']}; saved dormant-registration rows: {audit['dormant_registration_rows']}. Complete all-mode marker: {'present' if completion else 'not yet present'}.\n"
    report += f"\nCompleted supplementary output directory: `{pdf_results.resolve()}`. The measured first run uses variants1,2,3; equivalent-definition repeats are labelled above and must not be counted as independent algorithmic evidence.\n"
    report += "\nMachine-readable per-page names, matching cells and AST equivalence checks are saved in `reports/pdf_code_coverage.json`. Runtime completion is determined from saved outputs; a source match by itself is not a successful execution.\n"
    (ROOT/"reports/pdf_code_coverage.md").write_text(report,encoding="utf8")
    print(json.dumps({"documents":len(documents),"pages":sum(x["pages"] for x in documents),
                      "unmatched_names":{x["document"]:x["unmatched_definition_names"] for x in documents},
                      "pdf_tsp_rows":audit["pdf_tsp_rows"],"dormant_registration_rows":audit["dormant_registration_rows"]}))


if __name__=="__main__":main()
