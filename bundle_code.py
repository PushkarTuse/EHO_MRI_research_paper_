"""Package documented code and preserved text sources without copying the dataset.

Inputs: this completed workspace. Outputs: CODE_BUNDLE.zip and a consolidated
readable source listing. The listing preserves module boundaries; execute
run_all.py rather than concatenating mutually shadowing notebook definitions.
"""
from pathlib import Path
import zipfile
import hashlib
import json

ROOT = Path(__file__).resolve().parent
files = sorted(set([*ROOT.glob('*.py'), *ROOT.glob('*.ps1'), ROOT/'README.md', ROOT/'requirements-lock.txt',
                    *(ROOT/'src').glob('*.py'), *(ROOT/'tests').glob('*.py'), *(ROOT/'reports').glob('*.md'),
                    *(ROOT/'sources').rglob('*.py'), *(ROOT/'sources').glob('*.ipynb'),
                    *(ROOT/'sources').glob('*.txt'), *(ROOT/'sources').glob('*.json')]))
files = [p for p in files if p.exists()]
with zipfile.ZipFile(ROOT/'CODE_BUNDLE.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path,path.relative_to(ROOT))
parts = ['# Consolidated code with module boundaries', '', 'Run `run_all.py` as the entry point. Original notebook snippets are preserved separately in `sources`; they intentionally contain redefinitions and must not be combined into a single shared namespace beyond their documented replay.', '']
for path in [*ROOT.glob('*.py'),*(ROOT/'src').glob('*.py')]:
    parts += [f'## {path.relative_to(ROOT)}', '', '```python', path.read_text(encoding='utf-8'), '```', '']
(ROOT/'ALL_CODE_WITH_COMMENTS.md').write_text('\n'.join(parts),encoding='utf-8')
manifest = [{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files]
(ROOT/'reports/final_code_bundle_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Bundled {len(files)} files; dataset and environment remain local and are not duplicated.')
