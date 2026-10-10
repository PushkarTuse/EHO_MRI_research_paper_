"""Replay both newly recovered TSP programs without changing algorithm bodies.

Input: original ``code_snippets.txt``. Output: exact source copies, measured run
records, stdout, routes, objective-call trajectories and source/configuration
audit. TSP uses its source-generated Euclidean coordinates, not MRI intensities.

The original programs did not seed Python's random module. This harness supplies
controlled seeds and preserves each program's internal NumPy seed42 reset.
Definition-level observer wrappers and a Python profiler measure fitness calls;
their overhead is included in instrumented runtime and historical printed time.
No original algorithm, population, iteration count, or acceptance rule is fixed.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import functools
import hashlib
import io
import json
from pathlib import Path
import random
import sys
import time

import numpy as np

from routing import Trace, save_json, tour_cost, validate_tsp, write_csv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "sources/code_snippets_original.txt"
ALGORITHMS = {"ga_tsp": "GA", "elephant_herding_optimization": "EHO",
              "aco_tsp": "ACO", "pso_tsp": "PSO"}


def recover_blocks(path: Path):
    """Keep exact bytes and split at the second top-level import-random line.

    AST line positions only identify the boundary. The saved executable blocks
    retain source characters and line endings; neither is reformatted.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    tree = ast.parse(text)
    starts = [n.lineno for n in tree.body if isinstance(n, ast.Import)
              and any(alias.name == "random" for alias in n.names)]
    if len(starts) != 2:
        raise ValueError("Expected two complete TSP programs starting with import random")
    lines = text.splitlines(keepends=True)
    blocks = ["".join(lines[:starts[1] - 1]), "".join(lines[starts[1] - 1:])]
    return raw, blocks, starts


def run_block(source: str, block_id: int, seed: int, output: Path):
    """Execute the entire recovered harness and observe algorithm return values.

    Top-level AST nodes are executed in source order in a single namespace, so
    each algorithm's original definitions, calls, and print statements execute.
    Algorithms are wrapped only after definition; their function bodies remain
    the exact compiled source. A profiler observes independent class costs and
    nested EHO operators, avoiding missed objective calls in class methods.
    """
    namespace = {"__name__": "recovered_tsp_program"}
    source_label = f"recovered_snippets_block_{block_id}.py"
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    random.seed(seed)
    np.random.seed(seed)
    rows, details, traces = [], [], []
    occurrences = {}

    def wrap_algorithm(original, name):
        @functools.wraps(original)
        def observed(*args, **kwargs):
            matrix = np.asarray(args[0])
            n = int(args[1])
            trace = Trace(lambda r: validate_tsp(r, n))
            counters = {"crossover_calls": 0, "mutation_calls": 0}

            def profile(frame, event, result):
                if frame.f_code.co_filename != source_label:
                    return
                function = frame.f_code.co_name
                if event == "call":
                    if function == "order_crossover": counters["crossover_calls"] += 1
                    if function == "swap_mutation": counters["mutation_calls"] += 1
                elif event == "return" and function == "calculate_route_length" and result is not None:
                    # Global cost takes route; Elephant and Ant each have their
                    # own direct cost method and a position/route attribute.
                    candidate = frame.f_locals.get("route")
                    if candidate is None and "self" in frame.f_locals:
                        item = frame.f_locals["self"]
                        candidate = getattr(item, "position", getattr(item, "route", None))
                    if candidate is not None:
                        trace.observe(candidate, float(result))

            prior = sys.getprofile()
            sys.setprofile(profile)
            start = time.perf_counter()
            try:
                route, value = original(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                sys.setprofile(prior)
            run_id = f"snippet_block{block_id}_TSP{n}_{ALGORITHMS[name]}_seed{seed}"
            occurrences[run_id] = occurrences.get(run_id, 0) + 1
            if occurrences[run_id] > 1:
                run_id += f"_occurrence{occurrences[run_id]}"
            check = validate_tsp(route, n)
            recomputed = tour_cost(route, matrix)
            config = dict(zip(original.__code__.co_varnames[:original.__code__.co_argcount], args))
            config.update(kwargs)
            config.pop("distance_matrix", None)
            record = {"run_id": run_id, "block": block_id, "task": "TSP", "size": n,
                      "method": ALGORITHMS[name], "seed": seed,
                      "returned_objective": float(value), "recomputed_objective": recomputed,
                      "feasible": check["valid"], "objective_calls": trace.calls,
                      "invalid_calls": trace.invalid_calls, "seconds_instrumented": elapsed,
                      **counters}
            rows.append(record)
            details.append({**record, "route": route, "validation": check, "config": config,
                            "source_sha256": source_hash,
                            "returned_matches_recomputed": bool(np.isclose(value, recomputed)),
                            "best_observed_objective": trace.best,
                            "best_observed_route": trace.best_candidate})
            traces.extend({"run_id": run_id, **v} for v in trace.history)
            return route, value
        return observed

    capture = io.StringIO()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        for node in ast.parse(source).body:
            module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
            exec(compile(module, source_label, "exec"), namespace)
            if isinstance(node, ast.FunctionDef) and node.name in ALGORITHMS:
                namespace[node.name] = wrap_algorithm(namespace[node.name], node.name)
    log = output / f"block{block_id}_seed{seed}_stdout.txt"
    log.write_text(capture.getvalue(), encoding="utf-8")
    save_json(output / f"block{block_id}_seed{seed}_details.json", details)
    write_csv(output / f"block{block_id}_seed{seed}_convergence.csv", traces)
    return rows, details


def relation_audit(blocks):
    """Identify overlap by definition names and bodies, not assumed provenance."""
    references = []
    for path in sorted((ROOT / "sources" / "mri_optimisation").glob("cell_*.py")):
        try:
            nodes = ast.parse(path.read_text(encoding="utf-8")).body
        except SyntaxError:
            continue
        definitions = {n.name: ast.dump(n, include_attributes=False)
                       for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        if not set(ALGORITHMS).intersection(definitions): continue
        for i, source in enumerate(blocks, 1):
            recovered = {n.name: ast.dump(n, include_attributes=False)
                         for n in ast.parse(source).body
                         if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            common = sorted(set(definitions) & set(recovered))
            identical = [name for name in common if definitions[name] == recovered[name]]
            references.append({"snippet_block": i, "notebook_source": str(path),
                               "common_definitions": common, "identical_ast_definitions": identical,
                               "changed_definitions": sorted(set(common) - set(identical))})
    return references


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--blocks", default="1,2")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    raw, blocks, starts = recover_blocks(args.source)
    (ROOT / "sources" / "code_snippets_original.txt").write_bytes(raw)
    for i, block in enumerate(blocks, 1):
        (ROOT / "sources" / f"code_snippets_block_{i}.py").write_bytes(block.encode())
    seeds = [int(s) for s in args.seeds.split(",")]
    block_ids = [int(s) for s in args.blocks.split(",")]
    if any(i not in {1, 2} for i in block_ids): raise ValueError("blocks must be 1 or 2")
    manifest = {"original_path": str(args.source), "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_length": len(raw), "block_start_lines": starts,
                "block1": "15-city complete comparison; population30, EHO15 clans, iterations100, ACO50 ants.",
                "block2": "95-city complete comparison; GA/EHO50 candidates100 iterations and EHO5 clans; ACO/PSO10 candidates100 iterations.",
                "source_relations": relation_audit(blocks), "seeds": seeds,
                "fidelity": "Function bodies and top-level harness execute unchanged. Python random is seeded; observer wrappers and profiler add measurement overhead. Internal NumPy seed42 remains.",
                "MRI_relation": "Neither program reads MRI data or constructs masks/meshes; TSP input remains its original synthetic Euclidean matrix.",
                "evidence_status": "Fresh measured source replay; not proof these programs generated historical manuscript numbers.",
                "limits": "Different populations and actual fitness-call budgets prevent a controlled speed superiority inference. Neither EHO implements continuous dimensionality scaling or adaptive alpha/beta schedules."}
    save_json(args.output / "snippet_source_manifest.json", manifest)
    if args.inventory_only: return
    rows, details = [], []
    for seed in seeds:
        for block_id in block_ids:
            print(f"RUN block{block_id} seed{seed} start", flush=True)
            rr, dd = run_block(blocks[block_id-1], block_id, seed, args.output)
            rows.extend(rr); details.extend(dd)
            write_csv(args.output / "snippet_runs.csv", rows)
            save_json(args.output / "snippet_routes_and_validation.json", details)
            print(f"RUN block{block_id} seed{seed} done: {len(rr)} algorithms", flush=True)
    print(f"Completed {len(rows)} faithful observed runs", flush=True)


if __name__ == "__main__":
    main()
