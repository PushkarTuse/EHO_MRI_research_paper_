"""Replay original notebook cells, saving their real outputs and failures.

The saved Python text is executed unchanged in notebook order. Instrumentation only
redirects stdout and Matplotlib display to files, sets an initial seed, and records
elapsed time. The notebook's own later seeds/redefinitions remain in effect.
Hand-entered MRI graphs are labelled historical plotting rather than measurements.
The malformed brute-force example is validated and documented, not launched as an
unbounded factorial computation; routing.py separately executes its exact solver
on a valid small instance. No missing MRI source is invented by this script.
"""
from pathlib import Path
import argparse,contextlib,json,random,time,traceback,ast
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]

def replay(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    source=ROOT/'sources/mri_optimisation'
    env={'__name__':'__main__'}
    random.seed(0);np.random.seed(0)
    ledger=[];current=[0];figcount=[0]
    def save_show(*args,**kwargs):
        for num in plt.get_fignums():
            fig=plt.figure(num);figcount[0]+=1
            path=output/f'cell_{current[0]:03d}_figure_{figcount[0]:03d}.png'
            fig.savefig(path,dpi=135,bbox_inches='tight')
        plt.close('all')
    plt.show=save_show
    for path in sorted(source.glob('cell_*.py')):
        index=int(path.stem.split('_')[1]);current[0]=index;start=time.perf_counter()
        print(f'SOURCE CELL {index} START',flush=True)
        rec={'cell':index,'file':str(path),'status':'success','classification':'original code execution'}
        if index==23:rec['classification']='historical plotting constants; not new MRI measurements; uncertainty arrays are hypothetical'
        if index==17:rec['classification']='historical scalability: identical synthetic image pairs and unequal search budgets'
        with (output/f'cell_{index:03d}_output.txt').open('w',encoding='utf8') as log:
            try:
                with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                    exec(compile(path.read_text(encoding='utf8'),str(path),'exec'),env)
                    save_show()
            except Exception as exc:
                rec['status']='failed_as_supplied';rec['error']=f'{type(exc).__name__}: {exc}'
                log.write(traceback.format_exc());plt.close('all')
        rec['seconds']=time.perf_counter()-start
        observed={}
        for key,value in env.items():
            if not any(s in key.lower() for s in ['best_value','best_distance','times','distances','history','convergence']):continue
            try:
                a=np.asarray(value)
                if a.dtype.kind in 'biuf' and a.size<=10000:observed[key]=a.tolist()
            except Exception:pass
        (output/f'cell_{index:03d}_values.json').write_text(json.dumps(observed,indent=2),encoding='utf8')
        ledger.append(rec)
        (output/'execution_ledger.json').write_text(json.dumps(ledger,indent=2),encoding='utf8')
        print(f'SOURCE CELL {index} {rec["status"]} {rec["seconds"]:.2f}s',flush=True)
    # Brute force's original test matrix is ragged and its second cell has invalid syntax.
    brute=[]
    for path in sorted((ROOT/'sources/brute_force').glob('cell_*.py')):
        code=path.read_text(encoding='utf8');rec={'file':str(path)}
        try:
            tree=ast.parse(code)
            main=next((x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main'),None)
            matrix=None
            if main:
                for x in ast.walk(main):
                    if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='distance_matrix' for t in x.targets):matrix=ast.literal_eval(x.value)
            rec.update(status='invalid_input_not_run',row_lengths=[len(x) for x in matrix],reason='Source matrix is ragged/nonmetric. Exact original solver is rerun on a valid eight-city instance by routing.py.')
        except SyntaxError as e:rec.update(status='syntax_error_as_supplied',error=str(e))
        brute.append(rec)
    (output/'brute_source_validation.json').write_text(json.dumps(brute,indent=2),encoding='utf8')
    return ledger

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True)
    a=ap.parse_args();replay(a.output)
