# Purpose: rerun the documented recovery/verification pipeline in the isolated env.
# Inputs: optional additional run_all.py arguments. Outputs: results/ and logs/.
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PipelineArguments)
$ErrorActionPreference = 'Stop'
$TaskRoot = $PSScriptRoot
$TaskPython = Join-Path $TaskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $TaskPython)) {
    throw 'Create .venv and install requirements-lock.txt as described in README.md.'
}
& $TaskPython -X utf8 -u (Join-Path $TaskRoot 'run_all.py') @PipelineArguments
if ($LASTEXITCODE -ne 0) { throw "Pipeline failed with exit code $LASTEXITCODE. Read the stage log." }
