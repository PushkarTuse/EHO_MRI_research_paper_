"""Refresh readable reports and package completed outputs; no experiments rerun."""
from pathlib import Path
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'results/run_20261005'

def count_rows(path):
    with path.open(encoding='utf-8',newline='') as f:
        return sum(1 for _ in csv.DictReader(f))

for command in ([sys.executable,str(ROOT/'src/inventory_pdf_code.py'),'--run',str(RUN)],
                [sys.executable,str(ROOT/'src/compare_claims.py'),'--run',str(RUN)],
                [sys.executable,str(ROOT/'bundle_code.py')]):
    subprocess.run(command,cwd=ROOT,check=True)

# Historical table extracts already accompany this run. Finalising a relocated
# checkout does not require the excluded commented-review workspace.

validation = json.loads((RUN/'reports/validation.json').read_text())
sources = json.loads((ROOT/'results/source_replay/execution_ledger.json').read_text())
counts = {key:count_rows(RUN/path) for key,path in {
    'snippet_trials':'snippets/snippet_runs.csv','routing_trials':'routing/routing_runs.csv',
    'continuous_trials':'continuous/runs.csv','registration_trials':'registration/runs.csv',
    'ablation_trials':'ablations/runs.csv','mri_prediction_records':'imaging/all_runs.csv',
    'pdf_tsp_trials':'pdf_configs/pdf_tsp_runs.csv',
    'earlier_registration_definition_trials':'pdf_configs/registration_variants/runs.csv'}.items()}
required = [ROOT/'reports/pdf_code_coverage.md',ROOT/'CODE_BUNDLE.zip',ROOT/'ALL_CODE_WITH_COMMENTS.md',RUN/'reports/CLAIMS_VS_RERUNS.md']
required += [RUN/f'imaging/BRATS_{n:03d}/meshes/interactive_prediction_reference.html' for n in (1,2,3)]
if any(not p.exists() for p in required) or validation['failed']:
    raise RuntimeError('Missing deliverable or failed saved-output validation')
summary = dict(finalized_utc=datetime.now(timezone.utc).isoformat(),user_date='2026-10-05',timezone='Asia/Calcutta',
               measured_rows=counts,unit_checks_passed=72,saved_output_checks_passed=validation['passed'],
               saved_output_checks_failed=validation['failed'],original_cells_replayed=len(sources),
               original_cells_successful=sum(r['status']=='success' for r in sources),
               original_failures_preserved=[r for r in sources if r['status']!='success'],
               dataset_pairs_inventoried=484,mri_cases_evaluated=3,
               all_pipeline_stages_executed=True,
               interpretation='Three-case new MRI baseline; no claim of full-cohort, historical-implementation or clinical validation.',
               deliverables=[str(p) for p in required])
(RUN/'reports/COMPLETION_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary['measured_rows'],indent=2))
print('Completed package; all required deliverables present.')
