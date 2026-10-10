"""Routing replay and explicitly NEW feasibility-preserving corrective experiments.

Historical operators are loaded from unmodified notebook cells using AST isolation.
Observer hooks count objective calls and validate candidates WITHOUT changing the
historical objective or its acceptance rules. These reruns do not authenticate
old manuscript tables. Repaired methods are separately implemented adaptations,
not a reproduction of the manuscript's dimensionality-scaled continuous EHO.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import time
from collections import Counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"


def jsonable(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.integer, np.floating)):
        return x.item()
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def save_json(path, data):
    Path(path).write_text(json.dumps(jsonable(data), indent=2, allow_nan=False), encoding="utf-8")


def matrix_validation(matrix):
    try:
        d = np.asarray(matrix, dtype=float)
    except (ValueError, TypeError):
        return {"valid": False, "reason": "ragged or nonnumeric matrix"}
    if d.ndim != 2 or d.shape[0] != d.shape[1]:
        return {"valid": False, "reason": "matrix must be square"}
    errors = []
    if not np.isfinite(d).all(): errors.append("nonfinite distance")
    if (d < 0).any(): errors.append("negative distance")
    if not np.allclose(np.diag(d), 0): errors.append("nonzero diagonal")
    if not np.allclose(d, d.T): errors.append("asymmetric distance")
    return {"valid": not errors, "reason": "; ".join(errors), "n": len(d)}


def validate_tsp(route, n):
    r = [] if route is None else list(route)
    integer = all(isinstance(i, (int, np.integer)) for i in r)
    counts = Counter(r) if integer else Counter()
    missing = sorted(set(range(n)) - set(counts))
    duplicates = sorted(k for k, v in counts.items() if v > 1)
    out_of_range = sorted(k for k in counts if k < 0 or k >= n)
    return {"valid": integer and len(r) == n and not missing and not duplicates and not out_of_range,
            "missing": missing, "duplicates": duplicates, "out_of_range": out_of_range,
            "integer_ids": integer, "length": len(r)}


def tour_cost(route, distance):
    r = np.asarray(route, dtype=int)
    if len(r) < 2: return 0.0
    return float(np.asarray(distance)[r, np.roll(r, -1)].sum())


def validate_vrp(routes, demands, capacity, vehicles):
    n = len(demands) - 1
    routes = [] if routes is None else [list(r) for r in routes]
    ids = [i for r in routes for i in r]
    integer = all(isinstance(i, (int, np.integer)) for i in ids)
    counts = Counter(ids) if integer else Counter()
    missing = sorted(set(range(1, n + 1)) - set(counts))
    duplicates = sorted(k for k, v in counts.items() if v > 1)
    out_of_range = sorted(k for k in counts if k < 1 or k > n)
    loads = [int(sum(demands[i] for i in r if isinstance(i, (int, np.integer)) and 0 <= i <= n)) for r in routes]
    overloaded = [i for i, load in enumerate(loads) if load > capacity]
    valid = integer and not missing and not duplicates and not out_of_range and not overloaded and len(routes) <= vehicles
    return {"valid": valid, "missing": missing, "duplicates": duplicates,
            "out_of_range": out_of_range, "loads": loads, "overloaded_routes": overloaded,
            "route_count": len(routes), "integer_ids": integer}


def vrp_distance(routes, distance):
    """Distance only; validation is deliberately a separate operation."""
    return float(sum(tour_cost([0] + list(r), distance) for r in routes if len(r)))


def split_permutation(permutation, demands, capacity, vehicles):
    """NEW corrective next-fit decoder; no customer can be omitted or duplicated.

    Returns None if this particular ordering requires more than `vehicles` routes.
    This is not an optimal split dynamic program and is not the historical code.
    """
    p = list(permutation)
    if not validate_tsp([i - 1 for i in p], len(demands) - 1)["valid"]:
        raise ValueError("VRP ordering must contain every non-depot customer once")
    routes, current, load = [], [], 0
    for c in p:
        if demands[c] > capacity: return None
        if current and load + demands[c] > capacity:
            routes.append(current)
            current, load = [], 0
        current.append(c)
        load += demands[c]
    if current: routes.append(current)
    return routes if len(routes) <= vehicles else None


class Trace:
    def __init__(self, validator):
        self.validator = validator
        self.calls = 0
        self.invalid_calls = 0
        self.best = math.inf
        self.best_feasible = math.inf
        self.best_candidate = None
        self.best_feasible_candidate = None
        self.history = []
        self.violations = Counter()

    def observe(self, candidate, value):
        self.calls += 1
        check = self.validator(candidate)
        if not check["valid"]:
            self.invalid_calls += 1
            for k in ("missing", "duplicates", "out_of_range", "overloaded_routes"):
                if check.get(k): self.violations[k] += 1
        if value < self.best:
            self.best, self.best_candidate = float(value), copy.deepcopy(candidate)
        if check["valid"] and value < self.best_feasible:
            self.best_feasible, self.best_feasible_candidate = float(value), copy.deepcopy(candidate)
        self.history.append({"evaluation": self.calls, "best_observed": self.best,
                             "best_feasible": self.best_feasible})
        return value


def notebook_cells(name):
    data = json.loads((SOURCES / name).read_text(encoding="utf-8"))
    return [(i, c) for i, c in enumerate(data["cells"]) if c["cell_type"] == "code"]


def cell_source(name, code_index):
    i, c = notebook_cells(name)[code_index - 1]
    return "".join(c["source"]), {"notebook": name, "code_cell_1based": code_index,
            "all_cell_0based": i, "cell_id": c.get("id", c.get("metadata", {}).get("id"))}


def isolate_definitions(name, code_index, constant_names=()):
    source, meta = cell_source(name, code_index)
    # The brute notebook literally ends in '+'. Only this standalone syntax
    # artifact is removed; its source file remains unmodified and is hashed.
    parsed = "\n".join(line for line in source.splitlines() if line.strip() != "+")
    tree = ast.parse(parsed)
    nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef))]
    for n in tree.body:
        if isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id in constant_names for t in n.targets):
            nodes.append(n)
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace = {"__name__": "isolated_historical_routing"}
    exec(compile(module, f"{name}:code_cell_{code_index}", "exec"), namespace)
    return namespace, meta


def source_inventory(output):
    inventory = []
    selected = {"mri_optimisation.ipynb": [10, 11, 28, 33], "brute_force.ipynb": [1, 2]}
    export = output / "source_cell_copies"
    export.mkdir(exist_ok=True)
    for name, indices in selected.items():
        for index in indices:
            source, meta = cell_source(name, index)
            parsed = "\n".join(line for line in source.splitlines() if line.strip() != "+")
            tree = ast.parse(parsed)
            definitions = [{"name": n.name, "kind": type(n).__name__, "line": n.lineno}
                           for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
            dest = export / f"{Path(name).stem}_code_cell_{index}.py.txt"
            dest.write_text(source, encoding="utf-8")
            inventory.append({**meta, "sha256": hashlib.sha256(source.encode()).hexdigest(),
                              "definitions": definitions, "source_copy": str(dest)})
    pdfs = []
    for name in ["major_last_codes_pages.json", "mri_local_codes_pages.json"]:
        pages = json.loads((SOURCES / name).read_text(encoding="utf-8"))
        matches = []
        for page in pages:
            names = re.findall(r"def\s+(generate_distance_matrix|calculate_route_length|order_crossover|swap_mutation|initialize_population|select_parents|ga_tsp|elephant_herding_optimization|aco_tsp|pso_tsp|vrp_cost|generate_customers|calc_distance_matrix|visualize_routes|pso_vrp|eho_vrp|test_pso_vs_eho_with_visualization)\s*\(", page["text"])
            if names: matches.append({"page": page["page"], "functions": names})
        pdfs.append({"extracted_source": name, "routing_code_pages": matches,
                     "execution_source": "Notebook counterpart; PDF text is documentary corroboration, not silently reinterpreted executable code."})
    save_json(output / "routing_source_inventory.json", {"notebook_cells": inventory, "pdf_documents": pdfs})


def fixed_tsp(n):
    # Replays the notebook's fixed NumPy seed42 Euclidean instances.
    xy = np.random.RandomState(42).rand(n, 2) * 100
    d = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
    return xy, d


def fixed_vrp():
    # Independent, explicitly fixed instance for paired algorithm seeds.
    r = random.Random(42)
    xy = np.array([(r.uniform(0, 100), r.uniform(0, 100)) for _ in range(21)])
    demands = np.random.RandomState(42).randint(1, 10, 21)
    demands[0] = 0
    d = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
    return xy, d, demands, 50, 5


def original_brute_force(distance):
    ns, meta = isolate_definitions("brute_force.ipynb", 1)
    start = time.perf_counter()
    # Suppress console printing only, not search operations. All n! routes execute.
    with open(os.devnull, "w") as f, contextlib.redirect_stdout(f):
        route, value = ns["tsp_brute_force"](distance)
    return {"route": list(route), "value": float(value), "seconds": time.perf_counter() - start,
            "evaluations": math.factorial(len(distance)), "source": meta,
            "tag": "faithful_brute_solver_valid_replay_matrix_stdout_redirected"}


def faithful_tsp(method, distance, seed, code_cell=33, active_herds=None):
    if code_cell not in {28, 33}:
        raise ValueError("The TSP replay supports source cells 28 and 33; cell10 is VRP code")
    if method not in {"EHO", "GA", "ACO", "PSO"}:
        raise ValueError(f"Unknown historical TSP method: {method}")
    ns, meta = isolate_definitions("mri_optimisation.ipynb", code_cell)
    random.seed(seed); np.random.seed(seed)
    n = len(distance)
    trace = Trace(lambda r: validate_tsp(r, n))
    mutations = {"calls": 0, "crossover_calls": 0}
    old_swap, old_cross = ns["swap_mutation"], ns["order_crossover"]
    def swap(r):
        mutations["calls"] += 1
        return old_swap(r)
    def cross(a, b):
        mutations["crossover_calls"] += 1
        return old_cross(a, b)
    ns["swap_mutation"], ns["order_crossover"] = swap, cross
    old_cost = ns["calculate_route_length"]
    def global_cost(route, d): return trace.observe(route, old_cost(route, d))
    ns["calculate_route_length"] = global_cost
    # EHO and ACO have independent distance methods; wrapping both avoids
    # undercounting their evaluations. Their methods do not call global_cost.
    for cls_name, arg in [("Elephant", "position"), ("Ant", "route")]:
        cls = ns[cls_name]
        original = cls.calculate_route_length
        def instrument(self, d, _original=original, _arg=arg):
            return trace.observe(getattr(self, _arg), _original(self, d))
        cls.calculate_route_length = instrument
    pop, iters, herds = ((100, 50, 100) if code_cell == 33 else (20, 100, 20))
    tag = "faithful_source_operators_replay_instance"
    if active_herds is not None:
        herds = active_herds
        tag = "source_operator_configuration_ablation_active_clans"
    start = time.perf_counter()
    if method == "EHO": result = ns["elephant_herding_optimization"](distance, n, pop, herds, iters)
    elif method == "GA": result = ns["ga_tsp"](distance, n, pop, iters)
    elif method == "ACO": result = ns["aco_tsp"](distance, n, 50, iters)
    else: result = ns["pso_tsp"](distance, n, pop, iters)
    seconds = time.perf_counter() - start
    route, reported = result
    return {"method": method, "tag": tag, "source": meta, "seed": seed, "size": n,
            "seconds": seconds, "route": route, "returned_objective": float(reported),
            "recomputed_objective": tour_cost(route, distance), "validation": validate_tsp(route, n),
            "trace": trace, "mutation_calls": mutations["calls"], "crossover_calls": mutations["crossover_calls"],
            "config": {"population": pop if method != "ACO" else 50, "nominal_iterations": iters, "herds": herds if method == "EHO" else None}}


def faithful_brute_eho(distance, seed):
    ns, meta = isolate_definitions("brute_force.ipynb", 2, ("NUM_CITIES", "DISTANCE_MATRIX"))
    original_matrix = copy.deepcopy(ns["DISTANCE_MATRIX"])
    ns["DISTANCE_MATRIX"] = distance
    random.seed(seed); np.random.seed(seed)
    trace = Trace(lambda r: validate_tsp(r, len(distance)))
    original = ns["Elephant"].calculate_route_length
    def instrument(self): return trace.observe(self.position, original(self))
    ns["Elephant"].calculate_route_length = instrument
    start = time.perf_counter()
    with open(os.devnull, "w") as f, contextlib.redirect_stdout(f):
        answer = ns["elephant_herding_optimization"](len(distance), 50, 10, 7)
    return {"method": "EHO_brute_notebook", "tag": "faithful_source_operators_replay_instance",
            "source": meta, "seed": seed, "size": len(distance), "seconds": time.perf_counter() - start,
            "route": answer.position, "returned_objective": float(answer.fitness),
            "recomputed_objective": tour_cost(answer.position, distance),
            "validation": validate_tsp(answer.position, len(distance)), "trace": trace,
            "original_hardcoded_matrix_validation": matrix_validation(original_matrix),
            "config": {"population": 50, "herds": 10, "iterations": 7}}


def faithful_vrp(method, distance, demands, capacity, vehicles, seed):
    ns, meta = isolate_definitions("mri_optimisation.ipynb", 11)
    random.seed(seed); np.random.seed(seed)
    trace = Trace(lambda r: validate_vrp(r, demands, capacity, vehicles))
    original = ns["vrp_cost"]
    def instrument(routes, dist_matrix): return trace.observe(routes, original(routes, dist_matrix))
    ns["vrp_cost"] = instrument
    start = time.perf_counter()
    args = (len(demands) - 1, vehicles, demands, capacity, distance, 30)
    if method == "EHO": result = ns["eho_vrp"](*args, 5, 100)
    else: result = ns["pso_vrp"](*args, 100)
    seconds = time.perf_counter() - start
    routes, value, historical_third_result = result
    return {"method": method, "tag": "faithful_source_operators_replay_instance", "source": meta,
            "seed": seed, "size": len(demands)-1, "seconds": seconds, "route": routes,
            "returned_objective": float(value), "recomputed_objective": vrp_distance(routes, distance),
            "validation": validate_vrp(routes, demands, capacity, vehicles), "trace": trace,
            "historical_third_result": historical_third_result,
            "config": {"population": 30, "herds": 5 if method == "EHO" else None, "iterations": 100}}


def ordered_crossover(a, b, rng):
    n = len(a)
    if n < 2: return list(a)
    lo, hi = sorted(rng.choice(n, 2, replace=False))
    child = [-1] * n
    child[lo:hi] = list(a[lo:hi])
    used = set(child[lo:hi])
    slots = list(range(hi, n)) + list(range(lo))
    rest = [v for v in list(b[hi:]) + list(b[:hi]) if v not in used]
    for i, v in zip(slots, rest): child[i] = int(v)
    return child


def swap_mutation(route, rng):
    result = list(route)
    if len(result) > 1:
        i, j = rng.choice(len(result), 2, replace=False)
        result[i], result[j] = result[j], result[i]
    return result


def swaps_toward(current, target):
    current = list(current)
    swaps = []
    for i, wanted in enumerate(target):
        if current[i] != wanted:
            j = current.index(wanted)
            swaps.append((i, j))
            current[i], current[j] = current[j], current[i]
    return swaps


def repaired_search(method, distance, seed, budget=3000, pop_size=30, vrp=None):
    """Matched candidate-evaluation budget; all methods retain a copied best.

    EHO/GA/PSO operate on permutations. VRP uses the same NEW next-fit decoder
    for EHO and PSO. ACO is a symmetric ant-system style adaptation with explicit
    alpha1,beta2,rho.5; it is not silently substituted for historical ACO.
    """
    if method not in {"EHO", "GA", "PSO", "ACO"}:
        raise ValueError(f"Unknown routing method: {method}")
    if vrp is not None and method == "ACO":
        raise ValueError("No repaired VRP ACO is specified")
    if budget < pop_size: raise ValueError("budget must be at least population size")
    if pop_size < 5: raise ValueError("population must support five nonempty herds")
    rng = np.random.default_rng(seed)
    n = len(distance) if vrp is None else len(distance)-1
    validator = (lambda r: validate_tsp(r, n)) if vrp is None else (lambda r: validate_vrp(r, vrp[0], vrp[1], vrp[2]))
    trace = Trace(validator)
    permutations = [rng.permutation(n).tolist() for _ in range(pop_size)]
    def score(p):
        if not validate_tsp(p, n)["valid"]: raise AssertionError("corrected operator broke permutation")
        if vrp is None:
            candidate, value = p, tour_cost(p, distance)
        else:
            demands, cap, vehicles = vrp
            candidate = split_permutation([i+1 for i in p], demands, cap, vehicles)
            value = vrp_distance(candidate, distance) if candidate is not None else math.inf
        return trace.observe(candidate, value)
    start = time.perf_counter()
    values = [score(p) for p in permutations]
    pbest = copy.deepcopy(permutations)
    pvalues = values.copy()
    velocity = [[] for _ in range(pop_size)]
    pheromone = np.ones((n, n))
    heuristic = np.divide(1., distance, out=np.zeros_like(distance), where=distance > 0) if vrp is None else None
    while trace.calls < budget:
        if method == "EHO":
            groups = np.array_split(rng.permutation(pop_size), 5)
            progress = trace.calls / budget
            for group in groups:
                leader = min(group, key=lambda k: values[k])
                guide = permutations[leader].copy()
                for i in group:
                    if i == leader: continue
                    child = ordered_crossover(permutations[i], guide, rng)
                    if rng.random() < 0.5*(1-progress): child = swap_mutation(child, rng)
                    v = score(child)
                    permutations[i], values[i] = child, v
                    if trace.calls >= budget: break
                if trace.calls >= budget: break
        elif method == "GA":
            new_population, new_values = [], []
            while len(new_population) < pop_size and trace.calls < budget:
                parents = []
                for _ in range(2):
                    contestants = rng.choice(pop_size, 3, replace=False)
                    parents.append(permutations[min(contestants, key=lambda k: values[k])])
                child = ordered_crossover(parents[0], parents[1], rng)
                if rng.random() < 0.2: child = swap_mutation(child, rng)
                new_population.append(child); new_values.append(score(child))
            if len(new_population) == pop_size:
                permutations, values = new_population, new_values
        elif method == "PSO":
            best_index = int(np.argmin(pvalues))
            guide = pbest[best_index].copy()
            for i in range(pop_size):
                child = permutations[i].copy()
                # Retain half of previous swap velocity, then sampled personal
                # and global displacement swaps. Every intermediate is a tour.
                v = [s for s in velocity[i] if rng.random() < 0.5]
                v += [s for s in swaps_toward(child, pbest[i]) if rng.random() < 0.5]
                v += [s for s in swaps_toward(child, guide) if rng.random() < 0.5]
                for a, b in v: child[a], child[b] = child[b], child[a]
                velocity[i] = v
                values[i], permutations[i] = score(child), child
                if values[i] < pvalues[i]: pvalues[i], pbest[i] = values[i], child.copy()
                if trace.calls >= budget: break
        elif method == "ACO":
            if vrp is not None: raise ValueError("No repaired VRP ACO is specified")
            tours, costs = [], []
            for _ in range(pop_size):
                route = [int(rng.integers(n))]
                remaining = set(range(n)) - set(route)
                while remaining:
                    candidates = np.array(sorted(remaining))
                    weights = pheromone[route[-1], candidates] * heuristic[route[-1], candidates]**2
                    probs = weights/weights.sum() if np.isfinite(weights).all() and weights.sum() > 0 else None
                    nxt = int(rng.choice(candidates, p=probs))
                    route.append(nxt); remaining.remove(nxt)
                tours.append(route); costs.append(score(route))
                if trace.calls >= budget: break
            pheromone *= 0.5
            for route, value in zip(tours, costs):
                if value > 0:
                    for a, b in zip(route, route[1:]+route[:1]):
                        pheromone[a, b] += 1/value
                        pheromone[b, a] += 1/value
        else: raise ValueError(method)
    seconds = time.perf_counter() - start
    if trace.best_feasible_candidate is None: raise RuntimeError("no feasible candidate found")
    return {"method": method, "tag": "new_corrective_permutation_adaptation",
            "seed": seed, "size": n, "seconds": seconds, "route": trace.best_feasible_candidate,
            "returned_objective": trace.best_feasible, "recomputed_objective": trace.best_feasible,
            "validation": validator(trace.best_feasible_candidate), "trace": trace,
            "config": {"population": pop_size, "candidate_evaluation_budget": budget,
                       "herds": 5 if method == "EHO" else None, "vrp_decoder": "next_fit" if vrp else None}}


def defect_demonstrations():
    _, d, demands, capacity, vehicles = fixed_vrp()
    ns, _ = isolate_definitions("mri_optimisation.ipynb", 11)
    valid = split_permutation(list(range(1, 21)), demands, capacity, vehicles)
    assert validate_vrp(valid, demands, capacity, vehicles)["valid"]
    omitted = [r.copy() for r in valid]; omitted[0] = omitted[0][1:]
    duplicated = [r.copy() for r in valid]; duplicated[-1].append(duplicated[0][0])
    depot_only = [[0] for _ in range(vehicles)]
    records = []
    for label, routes in [("valid", valid), ("omitted_customer", omitted), ("duplicate_customer", duplicated), ("depot_only_invalid", depot_only)]:
        records.append({"label": label, "routes": routes, "legacy_distance_score": ns["vrp_cost"](routes, d),
                        "validation": validate_vrp(routes, demands, capacity, vehicles)})
    return records


def write_csv(path, rows):
    if not rows: return
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def plot_convergence(results, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    repaired = [r for r in results if r["tag"] == "new_corrective_permutation_adaptation"]
    for task, size in sorted({(r["task"], r["size"]) for r in repaired}):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for method in sorted({r["method"] for r in repaired if r["task"] == task and r["size"] == size}):
            rr = [r for r in repaired if (r["task"],r["size"],r["method"]) == (task,size,method)]
            trajectories = np.array([[x["best_feasible"] for x in r["trace"].history] for r in rr])
            mean = trajectories.mean(axis=0)
            sd = trajectories.std(axis=0, ddof=1) if len(rr)>1 else np.zeros_like(mean)
            x = np.arange(1,len(mean)+1)
            ax.plot(x, mean, label=f"{method} (n={len(rr)})")
            if len(rr)>1: ax.fill_between(x, mean-sd, mean+sd, alpha=.12)
        ax.set(xlabel="Evaluated candidates including initial population", ylabel="Best feasible distance",
               title=f"{task} {size}: corrective adaptations; seed mean ± SD")
        ax.grid(alpha=.2); ax.legend(); fig.tight_layout()
        fig.savefig(out / f"routing_{task.lower()}_{size}_convergence.png", dpi=180)
        plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--budget", type=int, default=3000)
    parser.add_argument("--sizes", default="8,10,20,50,100")
    parser.add_argument("--legacy-sizes", default="8,20")
    parser.add_argument("--skip-legacy", action="store_true")
    parser.add_argument("--skip-plots", action="store_true")
    args = parser.parse_args(argv)
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in args.seeds.split(",")]
    sizes = [int(x) for x in args.sizes.split(",")]
    legacy_sizes = [int(x) for x in args.legacy_sizes.split(",")]
    source_inventory(output)
    save_json(output / "routing_defect_demonstrations.json", defect_demonstrations())
    datasets = {}
    matrices = {}
    for n in sorted(set(sizes + legacy_sizes + [8])):
        xy,d = fixed_tsp(n); matrices[n] = d
        datasets[f"TSP_{n}"] = {"coordinates":xy,"distance_matrix":d,"matrix_seed":42}
    xy,dv,demands,cap,vehicles = fixed_vrp()
    datasets["VRP_20"] = {"coordinates":xy,"distance_matrix":dv,"demands":demands,"capacity":cap,"vehicles":vehicles,"instance_seed":42}
    save_json(output / "routing_instances.json", datasets)
    exact = original_brute_force(matrices[8])
    save_json(output / "routing_exact_8.json", exact)
    results = []
    def add(result, task):
        result["task"] = task
        result["run_id"] = f"{task}_{result['size']}_{result['method']}_{result['tag']}_cell{result.get('source',{}).get('code_cell_1based','new')}_seed{result['seed']}"
        if task == "TSP" and result["size"] == 8:
            result["optimality_gap_percent"] = 100*(result["recomputed_objective"]-exact["value"])/exact["value"]
        results.append(result)
        print(result["run_id"], f"value={result['returned_objective']:.6f}", "valid="+str(result["validation"]["valid"]), "calls="+str(result["trace"].calls), flush=True)
    if not args.skip_legacy:
        for seed in seeds:
            for n in legacy_sizes:
                for method in ["EHO","GA","ACO","PSO"]:
                    add(faithful_tsp(method,matrices[n],seed),"TSP")
            # Alter only the herd count to expose the source singleton-clan defect.
            add(faithful_tsp("EHO",matrices[8],seed,active_herds=5),"TSP")
            add(faithful_brute_eho(matrices[8],seed),"TSP")
            for method in ["EHO","PSO"]:
                add(faithful_vrp(method,dv,demands,cap,vehicles,seed),"VRP")
    for n in sizes:
        for seed in seeds:
            for method in ["EHO","GA","ACO","PSO"]:
                add(repaired_search(method,matrices[n],seed,args.budget),"TSP")
    for seed in seeds:
        for method in ["EHO","PSO"]:
            add(repaired_search(method,dv,seed,args.budget,vrp=(demands,cap,vehicles)),"VRP")
    rows, trajectories = [], []
    for r in results:
        tr = r["trace"]
        rows.append({"run_id":r["run_id"],"task":r["task"],"size":r["size"],"method":r["method"],"tag":r["tag"],"seed":r["seed"],
                     "returned_objective":r["returned_objective"],"recomputed_objective":r["recomputed_objective"],"feasible":r["validation"]["valid"],
                     "best_feasible_observed":tr.best_feasible if math.isfinite(tr.best_feasible) else "", "objective_calls":tr.calls,
                     "invalid_calls":tr.invalid_calls,"invalid_fraction":tr.invalid_calls/tr.calls if tr.calls else 0,
                     "elapsed_seconds_instrumented":r["seconds"],"optimality_gap_percent":r.get("optimality_gap_percent",""),
                     "mutation_calls":r.get("mutation_calls",""),"crossover_calls":r.get("crossover_calls",""),
                     "source_cell_id":r.get("source",{}).get("cell_id","")})
        trajectories.extend({"run_id":r["run_id"],**jsonable(x)} for x in tr.history)
    write_csv(output / "routing_runs.csv", rows)
    write_csv(output / "routing_convergence.csv", trajectories)
    if not args.skip_plots: plot_convergence(results,output)
    details = []
    for r in results:
        item = {k:v for k,v in r.items() if k != "trace"}
        tr=r["trace"]
        item["feasibility_statistics"]={"calls":tr.calls,"invalid_calls":tr.invalid_calls,"violation_counts":dict(tr.violations),"best_feasible":tr.best_feasible,"best_feasible_route":tr.best_feasible_candidate}
        details.append(item)
    save_json(output / "routing_routes_and_validation.json",details)
    save_json(output / "routing_protocol.json", {
        "seeds":seeds,"corrective_sizes":sizes,"legacy_sizes":legacy_sizes,"budget":args.budget,"population_corrective":30,
        "pairing":"Same fixed instance, paired algorithm seeds; variation is search-seed variation, not instance/patient variation.",
        "timing":"Elapsed perf_counter includes observational validation/history hooks; source observer cost differs across call patterns. Do not present it as uninstrumented original runtime.",
        "source_fidelity":"AST-isolated original imports/classes/functions; excluded top-level plotting/harness; standalone trailing '+' omitted from brute-force cell2 only. Algorithms not silently repaired; replay matrices replace original invalid ragged matrix where stated.",
        "corrections":"New permutation EHO crossover+decaying swap, GA tournament3+order crossover+swap0.2, PSO swap velocity, ACO symmetric ant-system alpha1 beta2 evaporation.5 deposit1/cost. VRP both use new next-fit capacity decoder and reject excessive-route candidates.",
        "limits":"Five seeds only by default; no significance claims; one fixed instance per size; exact optimum computed only at8; no evidence these fresh runs generated the manuscript's historical tables; this is not the paper's continuous dimensionality-scaling EHO ablation.",
        "historical_defects":"Cell33 singleton clans suppress all EHO crossover/mutation; its configured150 loops vs ACO16 are unequal. Original VRP scoring admits omissions, duplicates and depot IDs. Brute notebook hardcoded matrix is ragged/asymmetric/nonzero diagonal. Source random.seed was unset; controlled reruns seed both RNGs.",
        "exact_8":exact})
    print(f"Wrote {len(rows)} measured runs to {output}",flush=True)


if __name__ == "__main__":
    main()
