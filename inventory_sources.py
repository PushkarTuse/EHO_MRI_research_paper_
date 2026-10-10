"""Inventory source artefacts and extract notebook cells without executing them.

Inputs: original notebooks, manuscript files and local dataset metadata.
Outputs: immutable cell copies, SHA256 manifest, code inventory and module plan.
PDF text is preserved separately because layout extraction is not executable Python.
"""
from pathlib import Path
import argparse, ast, hashlib, json, platform, sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'sources'
sys.path.insert(0, str(ROOT/'src'))
from repository_paths import dataset_path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=dataset_path())
    parser.add_argument('--output',type=Path,default=ROOT/'reports/inventory_current',
                        help='New inventory location; historical source manifests remain intact')
    args=parser.parse_args()
    DATA=dataset_path(args.dataset)
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    manifest=[];cells=[]
    source_paths=[
        ROOT/'manuscripts/without_citations_draft.pdf',
        ROOT/'manuscripts/without_citations_draft_rewritten.docx',
        SOURCE/'major_last_codes_draft.pdf',
        SOURCE/'mri_local_codes.pdf',
        DATA/'dataset.json',
        SOURCE/'mri_optimisation.ipynb',SOURCE/'brute_force.ipynb']
    for path in source_paths:
        manifest.append({'path':str(path),'bytes':path.stat().st_size,'sha256':digest(path)})
    for notebook in [SOURCE/'mri_optimisation.ipynb',SOURCE/'brute_force.ipynb']:
        nb=json.loads(notebook.read_text(encoding='utf8'));dest=SOURCE/notebook.stem;dest.mkdir(exist_ok=True)
        ci=0
        for i,c in enumerate(nb['cells']):
            if c['cell_type']!='code':continue
            ci+=1;code=''.join(c['source']);p=dest/f'cell_{ci:03d}.py'
            if p.exists():
                if p.read_text(encoding='utf8') != code:
                    raise ValueError(f'Preserved source differs from notebook: {p}')
            else:p.write_text(code,encoding='utf8')
            record={'notebook':notebook.name,'notebook_index':i,'code_cell_1based':ci,'id':c.get('id',c.get('metadata',{}).get('id')),'file':str(p.relative_to(ROOT)),'lines':len(code.splitlines())}
            try:
                tree=ast.parse(code)
                record['syntax']='valid';record['functions']=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))];record['classes']=[n.name for n in tree.body if isinstance(n,ast.ClassDef)]
            except SyntaxError as e:record['syntax']=f'{e.msg}, line {e.lineno}';record['functions']=[];record['classes']=[]
            cells.append(record)
            saved=dest/f'cell_{ci:03d}_saved_outputs.json'
            if saved.exists():
                if json.loads(saved.read_text(encoding='utf8')) != c.get('outputs',[]):
                    raise ValueError(f'Preserved notebook output differs: {saved}')
            else:saved.write_text(json.dumps(c.get('outputs',[]),ensure_ascii=False,indent=2),encoding='utf8')
    dataset=json.loads((DATA/'dataset.json').read_text())
    case_records=[]
    for entry in dataset['training']:
        image=DATA/entry['image'].removeprefix('./');label=DATA/entry['label'].removeprefix('./')
        case_records.append({'case':image.name.replace('.nii.gz',''),'image':str(image),'label':str(label),'image_exists':image.exists(),'label_exists':label.exists(),'image_bytes':image.stat().st_size if image.exists() else 0,'label_bytes':label.stat().st_size if label.exists() else 0})
    case_records.sort(key=lambda x:x['case'])
    (output/'source_manifest.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'sources':manifest,'python':sys.version,'platform':platform.platform()},indent=2),encoding='utf8')
    (output/'notebook_cell_inventory.json').write_text(json.dumps(cells,indent=2),encoding='utf8')
    (output/'dataset_case_inventory.json').write_text(json.dumps(case_records,indent=2),encoding='utf8')
    intro='''# Code inventory and execution checklist

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
    '''
    # The triple-quoted report lives inside main; strip only its code indentation.
    intro='\n'.join(line[4:] if line.startswith('    ') else line for line in intro.splitlines())+'\n'
    for c in cells:intro+=f"| {c['notebook']} | {c['code_cell_1based']} | {c['id']} | {', '.join(c['functions'])} | {c['syntax']} |\n"
    good=sum(x['image_exists'] and x['label_exists'] for x in case_records)
    intro+=f'\nListed training cases: {len(case_records)}. Available image/label pairs: {good}.\n'
    (output/'CODE_INVENTORY.md').write_text(intro,encoding='utf8')
    print(json.dumps({'code_cells':len(cells),'listed_training':len(case_records),'available_pairs':good,'first_three':[x['case'] for x in case_records if x['image_exists'] and x['label_exists']][:3]},indent=2))

if __name__=='__main__':
    main()
