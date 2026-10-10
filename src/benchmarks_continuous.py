"""Numerical benchmark runner and independently instrumented source reruns.

Examples (run sequentially, without concurrent timing workloads):
  python benchmarks_continuous.py --output ../results/continuous --mode all
  python benchmarks_continuous.py --output ../results/smoke --mode matched --seeds 0 --budget 60

Source mode compiles ONLY imports/classes/functions of code cells 2, 6 and 7
in separate namespaces. It never runs notebook top-level plotting or harness
calls, and does not rewrite function bodies. Both legacy NumPy and Python RNGs
are seeded before each algorithm; this is a new seeded rerun, not reproduction
of an unrecorded historical RNG state. Wrappers count every objective call.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import platform
import random
from pathlib import Path
from time import perf_counter
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon
from optimizers import METHODS, optimise

BASE = Path(__file__).resolve().parents[1]


def rastrigin(x):
    x=np.asarray(x)
    return float(10*x.size+np.sum(x*x-10*np.cos(2*np.pi*x)))


def ackley(x):
    x=np.asarray(x)
    return float(-20*np.exp(-.2*np.sqrt(np.mean(x*x)))-np.exp(np.mean(np.cos(2*np.pi*x)))+20+np.e)


def json_default(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,Path):return str(x)
    raise TypeError(type(x).__name__)


def save_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=json_default),encoding='utf8')


def load_notebook_definitions(path,code_cell_number):
    """Read a user-supplied cell; execute inspected numerical definitions only."""
    notebook=json.loads(Path(path).read_text(encoding='utf8'))
    cells=[c for c in notebook['cells'] if c['cell_type']=='code']
    cell=cells[code_cell_number-1]
    source=''.join(cell['source'])
    tree=ast.parse(source)
    selected=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.ClassDef))]
    allowed={'numpy','random','time','math','matplotlib','scipy'}
    for node in selected:
        if isinstance(node,ast.Import):mods=[a.name.split('.')[0] for a in node.names]
        elif isinstance(node,ast.ImportFrom):mods=[(node.module or '').split('.')[0]]
        else:continue
        if not set(mods)<=allowed:raise ValueError(f'Unexpected source import {mods}')
    namespace={'__name__':f'isolated_notebook_cell_{code_cell_number}'}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path)+f':code_cell_{code_cell_number}','exec'),namespace)
    provenance=dict(notebook=str(Path(path).resolve()),notebook_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                    code_cell=code_cell_number,cell_id=cell.get('id',cell.get('metadata',{}).get('id')),
                    source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                    selection='imports, classes and functions only; later redefinitions in same cell prevail',
                    seeding='NumPy legacy and Python random reset independently before each algorithm')
    return namespace,provenance


def measured_source_call(namespace,objective_name,invoke,seed):
    """Run unmodified source function through a tracing objective wrapper."""
    original=namespace[objective_name]
    history=[];best=np.inf;best_x=None;calls=0
    def traced(x,*args,**kwargs):
        nonlocal best,best_x,calls
        value=float(original(x,*args,**kwargs));calls+=1
        if best_x is None or value<best:best=value;best_x=np.array(x,dtype=float).copy()
        history.append((calls,float(best)))
        return value
    np.random.seed(seed);random.seed(seed)
    namespace[objective_name]=traced
    start=perf_counter()
    try:returned=invoke(namespace)
    finally:namespace[objective_name]=original
    seconds=perf_counter()-start
    returned_x=np.asarray(returned[0],dtype=float).copy()
    # This independent consistency evaluation is outside the recorded timing/budget.
    return dict(x=returned_x,fun=float(returned[1]),history=history,evaluations=calls,
                seconds=seconds,best_observed_fun=float(best),best_observed_x=best_x,
                source_extra_return=(returned[2:] if len(returned)>2 else []))


def save_run(out,task,method,seed,result,protocol):
    tag=f'{task}__{method}__seed{seed}'
    out=Path(out)
    full=dict(result,task=task,method=method,seed=int(seed),protocol=protocol)
    save_json(out/'raw'/f'{tag}.json',full)
    pd.DataFrame(result['history'],columns=['evaluation','best_objective']).to_csv(out/'raw'/f'{tag}_history.csv',index=False)
    return dict(task=task,method=method,seed=int(seed),protocol=protocol,
                objective=float(result['fun']),seconds=float(result['seconds']),
                evaluations=int(result['evaluations']),
                returned_x_objective=float(result.get('returned_x_objective',result['fun'])),
                best_observed_objective=float(result.get('best_observed_fun',result['fun'])),
                result_file=str((out/'raw'/f'{tag}.json').resolve()))


def summarize(out,rows):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    frame=pd.DataFrame(rows);frame.to_csv(out/'runs.csv',index=False)
    if frame.empty:return
    summary=frame.groupby(['protocol','task','method'],sort=False).agg(
        runs=('objective','size'),objective_mean=('objective','mean'),objective_sd=('objective','std'),
        objective_median=('objective','median'),objective_min=('objective','min'),objective_max=('objective','max'),
        seconds_mean=('seconds','mean'),seconds_sd=('seconds','std'),
        evaluations_min=('evaluations','min'),evaluations_max=('evaluations','max')).reset_index()
    summary.to_csv(out/'summary.csv',index=False)
    tests=[]
    matched=frame[frame.protocol=='matched_evaluations']
    for task,g in matched.groupby('task'):
        pivot=g.pivot(index='seed',columns='method',values='objective')
        if 'modified_eho' not in pivot:continue
        for other in pivot.columns:
            if other=='modified_eho':continue
            pairs=pivot[['modified_eho',other]].dropna();diff=pairs['modified_eho']-pairs[other]
            if len(pairs)>=2 and np.any(diff):
                p=float(wilcoxon(diff,zero_method='wilcox',alternative='two-sided',method='auto').pvalue)
            else:p=1.
            tests.append(dict(task=task,comparison=f'modified_eho minus {other}',n=len(pairs),
                              mean_paired_difference=float(diff.mean()),median_paired_difference=float(diff.median()),
                              wins=int((diff<0).sum()),ties=int((diff==0).sum()),losses=int((diff>0).sum()),
                              wilcoxon_two_sided_p=p,
                              caution='Exploratory paired seeds on ONE instance; small n; no patient or dataset generalisation'))
    if tests:
        tests=pd.DataFrame(tests)
        # Holm across every comparison in this output family.
        ordered=np.argsort(tests.wilcoxon_two_sided_p.to_numpy());adjusted=np.empty(len(tests));last=0.
        for rank,idx in enumerate(ordered):
            last=max(last,min(1.,(len(tests)-rank)*tests.iloc[idx].wilcoxon_two_sided_p));adjusted[idx]=last
        tests['holm_adjusted_p']=adjusted;tests.to_csv(out/'paired_seed_statistics.csv',index=False)
    for (protocol,task),group in frame.groupby(['protocol','task']):
        fig,ax=plt.subplots(figsize=(8,5))
        for method,mg in group.groupby('method'):
            hs=[]
            for file in mg.result_file:
                r=json.loads(Path(file).read_text(encoding='utf8'));hs.append(np.asarray(r['history'],float))
            # Shared shortest budget avoids holding curves beyond an observed endpoint.
            max_common=int(min(h[-1,0] for h in hs));grid=np.unique(np.r_[1,np.linspace(1,max_common,min(200,max_common)).astype(int)])
            curves=np.array([h[np.searchsorted(h[:,0],grid,side='right')-1,1] for h in hs])
            mean=curves.mean(axis=0);sd=curves.std(axis=0,ddof=1) if len(hs)>1 else np.zeros(len(grid))
            ax.plot(grid,mean,label=method);ax.fill_between(grid,mean-sd,mean+sd,alpha=.12)
        ax.set(xlabel='Counted objective evaluations',ylabel='Best observed objective (mean ± seed SD)',title=f'{task}: {protocol}')
        ax.set_yscale('symlog',linthresh=1e-6);ax.grid(alpha=.25);ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(out/f'{protocol}_{task}_convergence.png',dpi=170);plt.close(fig)


def run_matched(out,seeds,budget,population):
    rows=[]
    for task,fun,limit in [('rastrigin_10d',rastrigin,5.12),('ackley_10d',ackley,32.768)]:
        for seed in seeds:
            # Deterministic per-seed permutation reduces fixed-order timing bias.
            order=np.random.default_rng(seed+7103).permutation(METHODS)
            for method in order:
                result=optimise(fun,[(-limit,limit)]*10,str(method),seed,budget,population)
                result['returned_x_objective']=fun(result['x'])
                rows.append(save_run(out,task,str(method),seed,result,'matched_evaluations'))
                print(f'{task} {method} seed={seed} f={result["fun"]:.7g} evals={result["evaluations"]}',flush=True)
    return rows


def run_original(out,seeds,notebook):
    rows=[]
    for task,cell,objective,iterations in [('source_ackley_cell2',2,'ackley',100),
                                         ('source_rastrigin_cell6',6,'rastrigin',1000),
                                         ('source_rastrigin_cell7',7,'rastrigin',1000)]:
        methods=['pso','eho','ga','aco'] if objective=='ackley' else ['pso','eho']
        for seed in seeds:
            for method in methods:
                ns,provenance=load_notebook_definitions(notebook,cell)
                bounds=np.array([[-32.768,32.768]]*10) if objective=='ackley' else (-5.12,5.12)
                def invoke(namespace):
                    fn=namespace[f'{method}_{objective}']
                    return fn(10,50,5,iterations,bounds) if method=='eho' else fn(10,50,iterations,bounds)
                result=measured_source_call(ns,objective,invoke,seed)
                result['returned_x_objective']=float(ns[objective](result['x']))
                result['provenance']=provenance
                result['config']=dict(dimensions=10,population=50,clans=5 if method=='eho' else None,
                                      iterations=iterations,bounds=np.asarray(bounds).tolist())
                rows.append(save_run(out,task,method,seed,result,'source_unchanged_bodies'))
                print(f'{task} {method} seed={seed} returned={result["fun"]:.7g} reevaluated={result["returned_x_objective"]:.7g}',flush=True)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--seeds',default='0,1,2,3,4')
    ap.add_argument('--source-seeds',default='0,1,2');ap.add_argument('--budget',type=int,default=3000)
    ap.add_argument('--population',type=int,default=30);ap.add_argument('--mode',choices=['all','matched','source'],default='all')
    ap.add_argument('--notebook',type=Path,default=BASE/'sources/mri_optimisation.ipynb')
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    save_json(args.output/'protocol.json',dict(arguments=vars(args),python=platform.python_version(),platform=platform.platform(),
        numpy=np.__version__,timing='perf_counter includes trace/objective and optimizer overhead; sequential process',
        distinction='source reruns preserve bodies but have unequal budgets; matched implementations are new references'))
    rows=[]
    if args.mode in ('all','source'):rows.extend(run_original(args.output,[int(s) for s in args.source_seeds.split(',')],args.notebook))
    if args.mode in ('all','matched'):rows.extend(run_matched(args.output,[int(s) for s in args.seeds.split(',')],args.budget,args.population))
    summarize(args.output,rows)


if __name__=='__main__':main()
