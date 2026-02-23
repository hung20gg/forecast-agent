param(
    [string]$DatasetPath = "hung20gg/financial-forecast",
    [string]$OutputFile,
    [string]$AgentType = "react",
    [int]$NumWorker = 2
)

$ErrorActionPreference = "Stop"

$ModelName = "gpt-4.1-mini"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ([string]::IsNullOrWhiteSpace($OutputFile)) {
    $OutputFile = Join-Path $ProjectRoot "data/eval_results_$ModelName.jsonl"
}

$outputDir = Split-Path -Parent $OutputFile
if (-not [string]::IsNullOrWhiteSpace($outputDir) -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$scriptPath = Join-Path $ProjectRoot "scripts/run/run_evaluation.py"

python $scriptPath `
    --dataset_path $DatasetPath `
    --output_file $OutputFile `
    --agent_type $AgentType `
    --base_model $ModelName `
    --num_worker $NumWorker
