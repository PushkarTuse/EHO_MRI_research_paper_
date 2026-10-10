"""Paired, fixed-budget ablation of newly reconstructed EHO modifications.

Run after other measured experiments, with no concurrent performance workload:
  python src/ablations.py --output results/ablations --seeds 0,1,2,3,4 --budget 3000

Fixed translated optima expose the origin dependence of the matriarch rule.
Neither the shifts nor coefficients are selected from measured outcomes.
These are new methods experiments, not reruns of historical manuscript data.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from optimizers import optimise
from benchmarks_continuous import ackley,rastrigin,save_json,save_run,summarize

SHIFT_DIRECTION=np.array([-1.,.75,-.5,.25,1.,-.75,.5,-.25,.875,-.875])
VARIANTS={
    'original_eho':('original_eho',{}),
    'modified_all':('modified_eho',{}),
    'modified_nodim':('modified_eho',{'dimensional_scaling':False}),
    'modified_noschedule':('modified_eho',{'scheduling':False}),
    'modified_norepulsion':('modified_eho',{'repulsion':False}),
    # Disable the NEW interpolation-based operator, retaining original replacement.
    'modified_noseparation':('modified_eho',{'interpolated_separation':False}),
}
TASKS={
    'rastrigin_shifted_10d':(rastrigin,5.12,2.*SHIFT_DIRECTION),
    'ackley_shifted_10d':(ackley,32.768,20.*SHIFT_DIRECTION),
}


def shifted_objective(x,base,shift):
    """Translate the fixed objective; its known minimizer is exactly shift."""
    return base(np.asarray(x,float)-np.asarray(shift,float))


def paired_ablation_statistics(out,rows):
    """Small-sample seed comparisons; no independent-instance inference."""
    frame=pd.DataFrame(rows);tests=[]
    for task,g in frame.groupby('task'):
        pivot=g.pivot(index='seed',columns='method',values='objective')
        for variant in pivot.columns:
            if variant=='modified_all':continue
            pairs=pivot[['modified_all',variant]].dropna()
            diff=pairs.modified_all-pairs[variant]
            p=float(wilcoxon(diff,zero_method='wilcox',method='auto').pvalue) if len(pairs)>=2 and np.any(diff) else 1.
            tests.append(dict(task=task,comparison=f'modified_all minus {variant}',n=len(diff),
                              mean_paired_difference=float(diff.mean()),median_paired_difference=float(diff.median()),
                              wins=int((diff<0).sum()),ties=int((diff==0).sum()),losses=int((diff>0).sum()),
                              wilcoxon_two_sided_p=p,
                              interpretation='Five seeds on one fixed shift per function; exploratory only'))
    if not tests:return
    tests=pd.DataFrame(tests);order=np.argsort(tests.wilcoxon_two_sided_p.to_numpy())
    adjusted=np.empty(len(tests));last=0.
    for rank,idx in enumerate(order):
        last=max(last,min(1.,(len(tests)-rank)*tests.iloc[idx].wilcoxon_two_sided_p));adjusted[idx]=last
    tests['holm_adjusted_p']=adjusted
    tests.to_csv(Path(out)/'paired_ablation_statistics.csv',index=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seeds',default='0,1,2,3,4')
    ap.add_argument('--budget',type=int,default=3000)
    ap.add_argument('--population',type=int,default=30)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    seeds=[int(v) for v in args.seeds.split(',')]
    protocol=dict(arguments=vars(args),variants=VARIANTS,
        fixed_shift_direction=SHIFT_DIRECTION,
        tasks={name:dict(bounds=[[-limit,limit]]*10,shift=shift,
                        objective='base(x - shift)',known_optimum=0.)
               for name,(_,limit,shift) in TASKS.items()},
        shift_selection='Fixed deterministic vectors written before experiment; no outcome-dependent shift or hyperparameter selection',
        variant_note='modified_noseparation disables interpolated separation only; original uniform worst-member replacement remains',
        schedule_note='Disabling scheduling holds attraction at alpha and repulsion at repulsion_max; it removes the time ramps',
        timing='Sequential optimizer and objective calls only; excludes file writes and plotting',
        limitation='New reconstructed operators, five seeds and one shift per function; no historical validation or general convergence proof')
    save_json(args.output/'protocol.json',protocol);rows=[]
    for task,(base,limit,shift) in TASKS.items():
        objective=lambda x:shifted_objective(x,base,shift)
        for seed in seeds:
            order=np.random.default_rng(seed+93071).permutation(list(VARIANTS))
            for variant in order:
                method,flags=VARIANTS[str(variant)]
                result=optimise(objective,[(-limit,limit)]*10,method,seed,args.budget,args.population,**flags)
                result.update(optimizer_implementation=method,variant=str(variant),
                              returned_x_objective=objective(result['x']),
                              fixed_shift=shift.copy(),distance_to_known_optimum=float(np.linalg.norm(result['x']-shift)))
                row=save_run(args.output,task,str(variant),seed,result,'matched_evaluations')
                row['distance_to_known_optimum']=result['distance_to_known_optimum'];rows.append(row)
                print(f'{task} {variant} seed={seed} f={result["fun"]:.7g} evals={result["evaluations"]}',flush=True)
    summarize(args.output,rows)
    paired_ablation_statistics(args.output,rows)


if __name__=='__main__':main()
