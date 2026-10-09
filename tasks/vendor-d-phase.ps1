# Phase D selective vendor: 1.16.1 -> 1.17.0
$ErrorActionPreference = 'Stop'
$root = 'C:\chatbot\dify'
$src  = 'C:\chatbot\dify-upstream-1.17.0'
$snap = Join-Path $root 'tasks\pre-vendor-d-snapshot'
$log  = Join-Path $root 'tasks\vendor-d-robocopy.log'

New-Item -ItemType Directory -Force -Path $snap | Out-Null
Set-Location $root

Write-Host '=== Snapshot overlay + hotspots + deferred RAG ==='
$overlayPaths = @(
  'api\services\omnichannel',
  'api\controllers\console\workspace\omnichannel.py',
  'api\controllers\console\workspace\zalo_personal.py',
  'api\controllers\console\workspace\mini_crm.py',
  'api\controllers\console\workspace\website_widget.py',
  'api\tasks\omnichannel_tasks.py',
  'api\core\tools\builtin_tool\providers\mini_crm',
  'api\tests\unit_tests\services\omnichannel',
  'api\tests\unit_tests\controllers\console\workspace\test_omnichannel.py',
  'web\app\(commonLayout)\omnichannel',
  'web\app\(commonLayout)\mini-crm',
  'web\app\components\mini-crm',
  'web\app\components\base\chat\omnichannel-rich-reply',
  'web\app\components\header\mini-crm-nav',
  'billing_saas',
  'landing',
  'zalo-personal-worker'
)
foreach ($p in $overlayPaths) {
  if (Test-Path $p) {
    $dest = Join-Path $snap $p
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item $p $dest -Recurse -Force
  }
}

# Custom omnichannel migrations
$migSnap = Join-Path $snap 'api\migrations\versions-custom'
New-Item -ItemType Directory -Force -Path $migSnap | Out-Null
Get-ChildItem 'api\migrations\versions\*.py' | Where-Object {
  $_.Name -match 'omnichannel|zalo|mini_crm|^o[12]|^l8m9|^m9n0'
} | ForEach-Object { Copy-Item $_.FullName $migSnap -Force }

# Hotspots
$hotspots = @(
  'api\core\app\apps\advanced_chat\app_generator.py',
  'api\core\app\apps\advanced_chat\generate_task_pipeline.py',
  'api\core\app\apps\agent_chat\app_generator.py',
  'api\core\app\apps\chat\app_generator.py',
  'api\core\app\task_pipeline\easy_ui_based_generate_task_pipeline.py',
  'api\core\app\helpers\chat_query.py',
  'api\core\workflow\node_runtime.py',
  'api\controllers\console\app\completion.py',
  'api\controllers\console\app\workflow.py',
  'api\controllers\console\explore\completion.py',
  'api\controllers\web\completion.py',
  'api\models\model.py',
  'api\models\account.py',
  'api\configs\feature\__init__.py',
  'docker\docker-compose.yaml',
  'docker\docker-compose-template.yaml',
  'docker\.env.example',
  'api\.env.example'
)
$hotSnap = Join-Path $snap 'hotspots'
New-Item -ItemType Directory -Force -Path $hotSnap | Out-Null
foreach ($h in $hotspots) {
  if (Test-Path $h) {
    $dest = Join-Path $hotSnap ($h -replace '[\\:]','_')
    Copy-Item $h $dest -Force
  }
}

# Deferred New RAG paths (keep 1.16.1)
$deferRag = @(
  'api\core\rag\datasource\vdb\vector_factory.py',
  'api\core\rag\extractor\extract_processor.py',
  'api\core\rag\extractor\firecrawl\firecrawl_app.py',
  'api\core\rag\extractor\notion_extractor.py',
  'api\core\rag\extractor\watercrawl\client.py',
  'api\core\rag\extractor\word_extractor.py',
  'api\core\rag\index_processor\index_processor.py',
  'api\core\rag\index_processor\processor\paragraph_index_processor.py',
  'api\core\rag\index_processor\processor\qa_index_processor.py',
  'api\core\rag\rerank\rerank_model.py',
  'api\core\rag\rerank\weight_rerank.py',
  'api\core\rag\retrieval\dataset_retrieval.py',
  'api\core\rag\retrieval\output_parser\structured_chat.py',
  'api\core\rag\retrieval\router\multi_dataset_function_call_router.py',
  'api\core\rag\retrieval\router\multi_dataset_react_route.py',
  'api\core\rag\summary_index\summary_index.py'
)
$ragSnap = Join-Path $snap 'deferred-rag'
New-Item -ItemType Directory -Force -Path $ragSnap | Out-Null
foreach ($r in $deferRag) {
  if (Test-Path $r) {
    $dest = Join-Path $ragSnap ($r -replace '[\\:]','_')
    Copy-Item $r $dest -Force
  }
}

Write-Host '=== Robocopy platform trees from 1.17.0 ==='
$robolog = @()
function Copy-Tree($rel, [string[]]$xd = @()) {
  $s = Join-Path $src $rel
  $d = Join-Path $root $rel
  if (-not (Test-Path $s)) { Write-Host "skip missing $rel"; return }
  $args = @($s, $d, '/E', '/IS', '/IT', '/NFL', '/NDL', '/NJH', '/NJS')
  foreach ($x in $xd) { $args += '/XD'; $args += (Join-Path $d $x) }
  Write-Host "copy $rel ..."
  robocopy @args | Out-Null
  # robocopy exit 0-7 = success
  if ($LASTEXITCODE -gt 7) { throw "robocopy failed $rel exit=$LASTEXITCODE" }
}

Copy-Tree 'api' @('services\omnichannel', 'core\tools\builtin_tool\providers\mini_crm')
Copy-Tree 'web'
Copy-Tree 'docker'
Copy-Tree 'packages'
Copy-Tree 'dify-agent'
Copy-Tree 'dify-agent-runtime'
Copy-Tree 'cli'
Copy-Tree 'sdks'
Copy-Tree 'e2e'

# Root metadata
foreach ($f in @('Makefile','AGENTS.md','CLAUDE.md','package.json','pnpm-workspace.yaml','pnpm-lock.yaml','.dockerignore')) {
  $sf = Join-Path $src $f
  if (Test-Path $sf) { Copy-Item $sf (Join-Path $root $f) -Force; Write-Host "copy root $f" }
}

Write-Host '=== Restore overlay ==='
foreach ($p in $overlayPaths) {
  $from = Join-Path $snap $p
  if (Test-Path $from) {
    $parent = Split-Path $p
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Copy-Item $from $p -Recurse -Force
  }
}
Get-ChildItem $migSnap -Filter *.py | ForEach-Object {
  Copy-Item $_.FullName 'api\migrations\versions' -Force
}

Write-Host '=== Restore deferred RAG (1.16.1) ==='
foreach ($r in $deferRag) {
  $from = Join-Path $ragSnap ($r -replace '[\\:]','_')
  if (Test-Path $from) {
    New-Item -ItemType Directory -Force -Path (Split-Path $r) | Out-Null
    Copy-Item $from $r -Force
  }
}

Write-Host '=== Restore hotspots (ours until manual merge) ==='
foreach ($h in $hotspots) {
  $from = Join-Path $hotSnap ($h -replace '[\\:]','_')
  if (Test-Path $from) {
    New-Item -ItemType Directory -Force -Path (Split-Path $h) | Out-Null
    Copy-Item $from $h -Force
  }
}

Write-Host '=== Done. Snapshot at' $snap
