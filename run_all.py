"""Run the research recovery/verification stages sequentially on this machine.

Inputs: preserved notebooks/snippets, Task01_BrainTumour and fixed seed/budget
configuration. Outputs: dated immutable measurements, stage logs and a claim
comparison report. Reconstructed experiments have explicit provenance; they do
not replace the historical manuscript values. Use --cases 484 for an expanded
cohort; the default is a complete pipeline on three prespecified volumes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from repository_paths import dataset_path
DEFAULT_DATASET = dataset_path()
STAGES = ("tests", "snippets", "pdf_configs", "routing", "continuous", "registration", "ablations", "imaging", "comparison", "validation")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=ROOT / "results/run_20261005")
    parser.add_argument("--stages", default=",".join(STAGES))
    parser.add_argument("--cases", type=int, default=3)
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--imaging-seeds", default="0,1,2")
    parser.add_argument("--budget", type=int, default=3000)
    parser.add_argument("--image-budget", type=int, default=1500)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.dataset = dataset_path(args.dataset)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(exist_ok=True)
    stages = args.stages.split(",")
    if any(stage not in STAGES for stage in stages):
        parser.error(f"Stages must be drawn from {STAGES}")
    # BLAS thread caps reduce uncontrolled oversubscription, not external OS load.
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "1"
    env.update(MPLBACKEND="Agg", PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    py = sys.executable
    commands = {
        "tests": [py, "-m", "pytest", str(ROOT / "tests"), "-q"],
        "snippets": [py, str(ROOT / "src/replay_snippets.py"), "--output", str(output / "snippets"), "--seeds", "0,1,2"],
        "pdf_configs": [py, str(ROOT / "src/replay_pdf_configs.py"), "--output", str(output / "pdf_configs"), "--seeds", "0,1,2", "--variants", "1"],
        "routing": [py, str(ROOT / "src/routing.py"), "--output", str(output / "routing"), "--seeds", args.seeds, "--budget", str(args.budget)],
        "continuous": [py, str(ROOT / "src/benchmarks_continuous.py"), "--output", str(output / "continuous"), "--seeds", args.seeds, "--budget", str(args.budget), "--mode", "all"],
        "registration": [py, str(ROOT / "src/registration.py"), "--output", str(output / "registration"), "--seeds", args.seeds, "--budget", str(args.image_budget), "--mode", "all", "--anatomical", str(args.dataset / "imagesTr/BRATS_001.nii.gz")],
        "ablations": [py, str(ROOT / "src/ablations.py"), "--output", str(output / "ablations"), "--seeds", args.seeds, "--budget", str(args.budget)],
        "imaging": [py, str(ROOT / "src/imaging.py"), "--dataset", str(args.dataset), "--output", str(output / "imaging"), "--cases", str(args.cases), "--seeds", args.imaging_seeds, "--budget", str(args.image_budget)],
        "comparison": [py, str(ROOT / "src/compare_claims.py"), "--run", str(output)],
        "validation": [py, str(ROOT / "src/validate_outputs.py"), "--run", str(output), "--dataset", str(args.dataset)],
    }
    ledger_path = output / "stage_ledger.json"
    ledger = json.loads(ledger_path.read_text()) if args.resume and ledger_path.exists() else []
    if ledger_path.exists() and not args.resume:
        raise FileExistsError("Use a new output path or --resume; previous measured outputs are preserved")
    import psutil
    environment = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "user_timezone": "Asia/Calcutta",
        "python": sys.version, "executable": py, "platform": platform.platform(),
        "logical_cpus": psutil.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
        "ram_bytes": psutil.virtual_memory().total, "thread_environment": {k: env[k] for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
        "device": "CPU; no GPU training or inference", "args": vars(args),
        "dependency_versions": {p: importlib.metadata.version(p) for p in ("numpy", "scipy", "pandas", "matplotlib", "nibabel", "scikit-image", "trimesh", "plotly")},
        "source_code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in (ROOT / "src").glob("*.py")},
        "recovered_notebook_replay": str(ROOT / "results/source_replay/execution_ledger.json"),
        "interpretation": "Original replay already completed separately. Each reconstructed stage has a distinct protocol. Seeds are not patients. New runs do not verify unknown historical configurations.",
    }
    if not (output / "environment.json").exists():
        write_json(output / "environment.json", environment)
    for stage in stages:
        if args.resume and any(r["stage"] == stage and r["returncode"] == 0 for r in ledger):
            print(f"RESUME: {stage} completed; preserving results", flush=True)
            continue
        command = commands[stage]
        print(f"START {stage}: {subprocess.list2cmdline(command)}", flush=True)
        started = time.perf_counter()
        log = output / "logs" / f"{stage}.log"
        # A retry appends to logs; it never deletes source data or measurements.
        with log.open("a", encoding="utf-8") as handle:
            handle.write("\nCOMMAND " + json.dumps(command) + "\n")
            handle.flush()
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
        entry = {"stage": stage, "command": command, "returncode": result.returncode,
                 "elapsed_seconds_including_process_startup_and_reporting": time.perf_counter() - started,
                 "finished_utc": datetime.now(timezone.utc).isoformat(), "log": str(log)}
        ledger.append(entry)
        write_json(ledger_path, ledger)
        print(f"END {stage}: exit={result.returncode}, seconds={entry['elapsed_seconds_including_process_startup_and_reporting']:.2f}", flush=True)
        if result.returncode:
            raise SystemExit(f"Stage {stage} failed; inspect {log} before resuming")


if __name__ == "__main__":
    main()
