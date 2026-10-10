# Routing recovery and execution protocol

The routing experiments consume Euclidean TSP distance matrices or customer
coordinates and demands. MRI pixels are not an appropriate input to those
unchanged benchmark programs. Imaging stages consume the local 4-D MRI volumes
separately. Every original source remains under `sources/`; rerun tables identify
whether operators were recovered unchanged or newly corrected.

## Complete code inventory

| Use case | Recovered source | Execution | Status / important constraint |
|---|---|---|---|
| Brute-force TSP | `sources/brute_force/cell_001.py` | `routing.py:original_brute_force` on the shared eight-city matrix | Solver enumerates all 8! permutations. Original top-level hardcoded matrix is ragged and is never silently repaired. |
| EHO-style TSP compared with brute force | `sources/brute_force/cell_002.py` | `routing.py:faithful_brute_eho` | Original trailing standalone `+` is a syntax artifact; omitted only from AST compilation. Original matrix retained; replay substitution is recorded. |
| EHO/GA/ACO/PSO TSP, early complete comparison | `sources/mri_optimisation/cell_028.py` | Full notebook replay; optional isolated operators through `faithful_tsp(..., code_cell=28)` | Twenty candidates and twenty clans leave every EHO clan with one member. Cell28 also repeats its comparisons for plotting, consuming additional RNG draws. |
| EHO/GA/ACO/PSO TSP, final configuration | `sources/mri_optimisation/cell_033.py` | Full notebook replay and instrumented `routing.py` | One hundred candidates and one hundred clans suppress all EHO follower updates. |
| Newly found 15-city comparison | `code_snippets.txt`, lines 1–285 | `replay_snippets.py`, block1 | Full original script; GA/EHO/PSO population30, EHO15 clans, all100 iterations; ACO50 ants. |
| Newly found 95-city comparison | `code_snippets.txt`, lines286 onward | `replay_snippets.py`, block2 | Full original script; GA/EHO population50, EHO5 clans; ACO/PSO10 candidates; all100 iterations. |
| PSO/EHO VRP | `sources/mri_optimisation/cell_010.py` and `cell_011.py` | Full notebook replay; cell11 observers through `routing.py` | Original distance objective ignores missing/duplicate customers and capacities. Both source variants remain available. |
| Corrected discrete benchmark | New `src/routing.py:repaired_search` | TSP8,10,20,50,100; VRP20 with five paired seeds | Separately documented new permutation methods and capacity decoder, equal3,000 candidate budget. These do not authenticate historical tables or implement the paper's continuous EHO equations. |

The source relationship report in
`results/snippet_replay/snippet_source_manifest.json` compares definition ASTs
against notebook cells. The 15-city snippet shares eleven identical definitions
with cell28; its EHO and ACO definitions differ. The 95-city snippet shares nine
identical definitions with cell28 and changes Particle, PSO, EHO and ACO.
Shared definitions establish overlap; they do not prove which script produced a
particular manuscript table.

## Faithful source replay

`replay_sources.py` executes the original notebook's code cells in their original
order. `replay_snippets.py` executes each complete newly supplied program in its
own namespace. The original bytes are copied to
`sources/code_snippets_original.txt`, SHA-256
`a1b21ede8ebf740e648f9a0b3c23b9e7281eca8c8e26c1f7be36b9a1e201ead0`.
The two recovered executable source blocks are also preserved without
reformatting.

The snippet harness observes costs through a Python profiler and wraps algorithm
entry/return to save routes. It does not alter the algorithm bodies, crossover,
mutation, parameters, stopping rules, or original print statements. Every cost
call is checked for a complete permutation and recorded as a trajectory.
The code resets NumPy to seed42 when generating coordinates; the harness seeds
Python's previously unseeded `random` module. Repeated controlled seeds therefore
vary search trajectories while retaining the same TSP instance.

Instrumented runtime includes profiler, validation and trajectory overhead. The
snippet's original printed timing also encloses these observer wrappers, so it
must not be relabelled as an uninstrumented historical timing. Full-notebook
replay timings and instrumented routing timings have different definitions and
are saved separately.

## Source issues demonstrated, not repaired in faithful results

1. In cells28 and33, population equals clan count. Each clan's only candidate is
   its leader, and `if elephant != herd_best` is never satisfied. Fresh cell33
   tests produce exactly100 initial cost evaluations and zero crossover or
   mutation calls. A lower source time thus describes essentially random
   initialization and shuffling, rather than a functioning iterative EHO search.
2. Cell33 runs EHO for `max_iterations * 3` (150 loops) and ACO for
   `max_iterations // 3` (16 loops), despite a common nominal value50. Its EHO
   mutation probability `0.5*(1-iteration/max_iterations)` becomes negative in
   later loops; comparison with a nonnegative random draw disables mutation.
3. Cell33 PSO accepts inertia, cognitive and social weights but does not use them
   in its permutation update. Calling that implementation a complete canonical
   weighted PSO is unsupported.
4. The 95-city source uses route values as position indices when choosing its
   swaps, rather than computing a sequentially updated displacement toward the
   global best. Because values happen to be valid indices, permutations remain
   valid, but the move is not necessarily the claimed directed displacement.
5. Original VRP cost sums distance only. Removing a customer may improve the
   score; depot-only routes have score0 while violating customer coverage.
   Customer duplication and overloaded routes can also receive finite scores.
   Every replay return and evaluated candidate is therefore audited separately
   for omissions, duplicates, IDs, capacity and vehicle count.
6. The original brute-force matrix contains rows of different lengths. It cannot
   be a valid shared distance matrix. Exact-optimum comparisons use an explicitly
   new common eight-city matrix; the original malformed matrix remains preserved.

These are code-supported defects. They do not imply invented intent or prove
deliberate data manipulation. Fresh runs are current measurements, not the
historical measurements whose raw logs were not supplied.

## New corrective implementations

The corrective methods preserve permutations and use copied incumbent solutions.
TSP closes each tour by returning to its first city. VRP treats customer0 as the
depot; every other customer must occur exactly once, every route load must be at
most capacity, and route count must not exceed the available fleet.

EHO is a discrete crossover-based adaptation: candidates are randomly allocated
to five nonempty clans, nonleaders undergo ordered crossover with the clan
leader, and swap mutation decays as `0.5*(1-progress)`. It is not the continuous
dimension-scaled EHO formulation. GA uses size3 tournament parent selection,
ordered crossover, and swap mutation0.2. PSO stores a swap velocity and samples
retained, personal-best and global-best displacements with probability0.5. ACO
uses a symmetric ant-system adaptation with alpha1, beta2, evaporation0.5 and
inverse-cost deposition. The same initial population size30 and exact3,000
candidate evaluations are used, including initialization.

VRP EHO and PSO decode each complete customer permutation using a next-fit
capacity split. An ordering requiring too many routes is rejected with infinite
cost. This decoder is feasible when it succeeds; it is not an optimal split
dynamic program. A failed decoder still consumes one candidate evaluation.

Only the small eight-city instance has a brute-force optimum. Five search seeds
on one fixed instance per size provide search variability; they do not provide
instance variability or a broad performance guarantee. Convergence bands are
measured mean±sampleSD, rather than hypothetical error bars. Statistical tests
over this small seed set cannot establish general superiority.

## Commands and outputs

```powershell
& 'code_reruns/.venv/Scripts/python.exe' -X utf8 -u 'code_reruns/src/replay_snippets.py' --output 'code_reruns/results/snippet_replay' --seeds '0,1,2'
& 'code_reruns/.venv/Scripts/python.exe' -X utf8 -u 'code_reruns/src/routing.py' --output 'code_reruns/results/routing' --seeds '0,1,2,3,4' --budget 3000
& 'code_reruns/.venv/Scripts/python.exe' -m pytest 'code_reruns/tests/test_routing.py' -q
```

Run measured experiments sequentially to avoid competing CPU load. Snippet
outputs include original stdout, returned/recomputed objectives, routes,
feasibility, measured objective-call counts and complete convergence CSVs.
Routing outputs additionally include the exact eight-city solver result,
VRP defect demonstrations, configuration, distance matrices and convergence
plots. A faithful rerun and a corrective rerun are identified by different tags.

The initial routing test suite contains twelve passing tests: validation of
coverage and capacities; next-fit fleet overflow; exact evaluation budgets;
monotone incumbent records; source singleton-clan no-update behavior; and
VRP distance-only defect demonstrations. These tests check relevant scientific
invariants rather than reproducing numerical claims from the manuscript.
