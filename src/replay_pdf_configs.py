"""Execute PDF-only harness configurations and dormant registration definitions.

Inputs: preserved notebook cell28/cell33 TSP bodies and four definition groups in
cell15, corroborated by the two PDFs. Outputs: exact extracted function source,
explicit PDF parameter harnesses, observed costs/routes, synthetic image arrays,
registration transforms and convergence. PDF text is reflowed and not runnable;
matched machine-readable function bodies are used unchanged.

PDF configuration replay is separate from literal full-notebook execution.
Dormant registration definitions were overwritten before the historical harness
ran. Their controlled replay is a NEW experiment with recovered source methods.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
from pathlib import Path
import traceback

import numpy as np

from benchmarks_continuous import measured_source_call, save_run, summarize
from registration import save_alignment
from replay_snippets import run_block
from routing import cell_source, save_json, write_csv

ROOT = Path(__file__).resolve().parents[1]


def source_definitions(cell):
    source, meta = cell_source("mri_optimisation.ipynb", cell)
    selected = [ast.get_source_segment(source, n) for n in ast.parse(source).body
                if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef))]
    return "\n\n".join(selected) + "\n", meta


def tsp_program(kind):
    """Use unmodified cell33/cell28 functions with PDF44/PDF36 parameters."""
    if kind == "major":
        source, meta = source_definitions(33)
        harness = '''
pop_size = 30
num_herds = 15
num_ants = 50
max_iterations = 50
max_generations = 50
for num_cities in range(1, 101, 10):
    print(f"Running tests for {num_cities} cities...")
    dist_matrix = generate_distance_matrix(num_cities)
    best_route_ga, best_distance_ga = ga_tsp(dist_matrix, num_cities, pop_size, max_generations)
    best_route_eho, best_distance_eho = elephant_herding_optimization(dist_matrix, num_cities, pop_size, num_herds, max_iterations)
    best_route_aco, best_distance_aco = aco_tsp(dist_matrix, num_cities, num_ants, max_iterations)
    best_route_pso, best_distance_pso = pso_tsp(dist_matrix, num_cities, pop_size, max_iterations)
    print("GA/EHO/ACO/PSO distances:", best_distance_ga, best_distance_eho, best_distance_aco, best_distance_pso)
'''
        provenance = dict(document="major_last_codes_draft.pdf", pages=list(range(38,46)),
                          configuration_page=44, function_source=meta, block_id=101,
                          cities=list(range(1,101,10)),population=30,eho_clans=15,
                          nominal_iterations=50,aco_ants=50,
                          actual_loops="EHO150, GA50, PSO50, ACO16; n1 guards skip all search",
                          n1="Each source function has num_cities<2 guard; record actual outcomes. No expected failure is fabricated.")
    elif kind == "local":
        source, meta = source_definitions(28)
        harness = '''
num_cities = 15
pop_size = 30
num_herds = 15
max_generations = 100
max_iterations = 100
num_ants = 50
distance_matrix = generate_distance_matrix(num_cities)
for occurrence in range(2):
    # The PDF calls all four methods once for console output and again for plots.
    best_route_ga, best_distance_ga = ga_tsp(distance_matrix, num_cities, pop_size, max_generations)
    best_route_eho, best_distance_eho = elephant_herding_optimization(distance_matrix, num_cities, pop_size, num_herds, max_iterations)
    best_route_aco, best_distance_aco = aco_tsp(distance_matrix, num_cities, num_ants, max_iterations)
    best_route_pso, best_distance_pso = pso_tsp(distance_matrix, num_cities, pop_size, max_iterations)
    print("GA/EHO/ACO/PSO distances:", best_distance_ga, best_distance_eho, best_distance_aco, best_distance_pso)
'''
        provenance = dict(document="mri_local_codes.pdf", pages=list(range(33,38)),
                          configuration_page=36, function_source=meta, block_id=102,
                          cities=[15],population=30,eho_clans=15,nominal_iterations=100,
                          aco_ants=50,repeated_comparisons=2,
                          difference_from_new_snippet1="Cell28 EHO mutation decays0.2*(1-t/T) and ACO beta2/deposit100; snippet1 uses fixed mutation0.2 and ACO beta5/inverse-cost deposition.")
    else: raise ValueError(kind)
    return source + harness, provenance


def registration_groups():
    """Keep each overwritten group of original top-level definitions distinct."""
    source, meta = cell_source("mri_optimisation.ipynb",15)
    nodes=ast.parse(source).body
    starts=[n.lineno for n in nodes if isinstance(n,ast.FunctionDef) and n.name=="generate_image"]
    ends=starts[1:]+[10**9]
    imports=[ast.get_source_segment(source,n) for n in nodes if isinstance(n,(ast.Import,ast.ImportFrom))]
    groups=[]
    for variant,(start,end) in enumerate(zip(starts,ends),1):
        selected=[n for n in nodes if start<=n.lineno<end and isinstance(n,(ast.FunctionDef,ast.ClassDef))]
        # The final variant's plot/harness definitions may be retained, but the
        # historical top-level call is excluded. Earlier groups have no harness.
        text="\n\n".join(imports+[ast.get_source_segment(source,n) for n in selected])+"\n"
        functions=[n for n in selected if isinstance(n,ast.FunctionDef)]
        capped=any(n.name=="eho_registration" and "min(max_iterations, 20)" in ast.get_source_segment(source,n) for n in functions)
        groups.append((text,dict(source=meta,variant=variant,first_line=start,
                                  end_line_exclusive=end if end<10**9 else len(source.splitlines())+1,
                                  function_names=[n.name for n in selected],eho_cap20=capped,
                                  sha256=hashlib.sha256(text.encode()).hexdigest(),
                                  invoked_by_historical_harness=variant==4)))
    return groups


def run_registration_variants(output,seeds,variants):
    target=output/"registration_variants"
    (target/"raw").mkdir(parents=True,exist_ok=True)
    groups=registration_groups()
    rows=[]
    fixed=np.random.RandomState(42).rand(100,100)
    bounds=[(-45,45),(-20,20),(-20,20)]
    inventory=[]
    for index in variants:
        text,provenance=groups[index-1]
        (ROOT/"sources"/f"registration_cell15_variant{index}.py").write_text(text,encoding="utf8")
        inventory.append(provenance)
        for seed in seeds:
            for method in ["pso","eho","ga","aco"]:
                namespace={"__name__":f"isolated_registration_variant{index}"}
                exec(compile(text,f"cell15_registration_variant{index}","exec"),namespace)
                moving=namespace["apply_transformation"](fixed,25,5,-3)
                def invoke(ns):
                    fn=ns[f"{method}_registration"]
                    return fn(fixed,moving,30,5,50,bounds) if method=="eho" else fn(fixed,moving,30,50,bounds)
                result=measured_source_call(namespace,"objective_function",invoke,seed)
                result["returned_x_objective"]=float(namespace["objective_function"](result["x"],fixed,moving))
                result["provenance"]=provenance
                result["config"]=dict(population=30,eho_clans=5,nominal_iterations=50,
                                       actual_eho_cap=20 if provenance["eho_cap20"] else None,bounds=bounds,
                                       image_type="seed42 uniform random field",true_forward_transform=[25,5,-3])
                task=f"synthetic_source_cell15_variant{index}"
                rows.append(save_run(target,task,method,seed,result,"new_experiment_recovered_dormant_source" if index<4 else "source_final_definitions"))
                aligned=namespace["apply_transformation"](moving,*result["x"])
                np.savez_compressed(target/"raw"/f"{task}__{method}__seed{seed}_images.npz",fixed=fixed,moving=moving,aligned=aligned)
                save_alignment(target,task,method,seed,fixed,moving,aligned)
                print(f"variant{index} {method} seed{seed} MSE={result['fun']:.7g} calls={result['evaluations']}",flush=True)
        save_json(target/"source_variant_manifest.json",inventory)
        write_csv(target/"runs.csv",rows)
    summarize(target,rows)
    return rows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--seeds",default="0,1,2")
    parser.add_argument("--mode",choices=["all","configs","variants"],default="all")
    parser.add_argument("--variants",default="1",
                        help="Default only unique uncapped variant1; variant3 is identical, variant2 equals already-replayed final variant4")
    parser.add_argument("--inventory-only",action="store_true")
    args=parser.parse_args(argv)
    args.output.mkdir(parents=True,exist_ok=True)
    seeds=[int(x) for x in args.seeds.split(",")]
    variants=[int(x) for x in args.variants.split(",")]
    if any(x not in {1,2,3,4} for x in variants):raise ValueError("variant must be1..4")
    manifest=[]
    for kind in ["major","local"]:
        text,meta=tsp_program(kind)
        (ROOT/"sources"/f"pdf_configuration_{kind}_tsp.py").write_text(text,encoding="utf8")
        manifest.append(meta)
    save_json(args.output/"pdf_configuration_manifest.json",manifest)
    save_json(args.output/"registration_definition_groups.json",[m for _,m in registration_groups()])
    if args.inventory_only:return
    rows,details,failures=[],[],[]
    if args.mode in {"all","configs"}:
        for seed in seeds:
            for kind in ["major","local"]:
                text,meta=tsp_program(kind)
                try:
                    print(f"PDF {kind} TSP seed{seed} start",flush=True)
                    rr,dd=run_block(text,meta["block_id"],seed,args.output)
                    for record in rr+dd:
                        record["pdf_configuration"]=kind
                        record["protocol"]="pdf_parameter_harness_matched_original_function_bodies"
                    rows.extend(rr);details.extend(dd)
                    write_csv(args.output/"pdf_tsp_runs.csv",rows)
                    save_json(args.output/"pdf_tsp_routes_and_validation.json",details)
                    print(f"PDF {kind} TSP seed{seed} done: {len(rr)} methods/cases",flush=True)
                except Exception as error:
                    failures.append(dict(kind=kind,seed=seed,error=repr(error),traceback=traceback.format_exc()))
                    save_json(args.output/"pdf_configuration_failures.json",failures)
                    raise
    if args.mode in {"all","variants"}:run_registration_variants(args.output,seeds,variants)
    save_json(args.output/"completion.json",dict(mode=args.mode,seeds=seeds,tsp_runs=len(rows),
              registration_variants=variants if args.mode in {"all","variants"} else [],failures=failures))


if __name__=="__main__":main()
