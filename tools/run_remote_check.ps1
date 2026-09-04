<#
.SYNOPSIS
  Roda o --check-remote (G35) para cada fonte do registro e grava um log.

.DESCRIPTION
  O --check-remote existe desde o G35 (tools/extrai_fonte_externa.py) mas nada
  na suite o executava: o CI roda `pytest -m "not build"` (offline) e os testes
  G35 mockam o download (deterministico, sem rede — D81/G45). Resultado: o unico
  guarda que prova que o PDF guardado ainda e o que a URL serve nunca rodava.

  Este script e o executor periodico, no mesmo molde do job de build
  (tools/run_build_suite.ps1): percorre fontes_externas/registro.json e roda
  `python tools/extrai_fonte_externa.py --check-remote --id <id>` por entrada.
  Somente leitura: nao toca em registro.json nem nos PDFs guardados.

  Por que LOCAL e nao CI de nuvem: depende de rede para servidores de origem
  (prefeitura, UFPE, site comercial) — lento e flaky. A maquina do dev roda
  quando quer (manual ou tarefa agendada) e o CI segue offline e deterministico.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\run_remote_check.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot          # raiz do repo (tools\ -> ..)
$reg = Join-Path $repo "fontes_externas\registro.json"
$extrator = Join-Path $repo "tools\extrai_fonte_externa.py"
$logdir = Join-Path $PSScriptRoot "remote-check-logs"
if (-not (Test-Path $logdir)) { New-Item -ItemType Directory -Path $logdir | Out-Null }

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$log   = Join-Path $logdir "remote_$stamp.log"
$latest = Join-Path $logdir "LATEST.txt"

if (-not (Test-Path $reg)) {
    $msg = "[$stamp] ERRO: registro nao encontrado: '$reg' - remote-check NAO rodou."
    $msg | Tee-Object -FilePath $log
    $msg | Out-File -FilePath $latest -Encoding utf8
    exit 2
}

$registro = Get-Content -LiteralPath $reg -Raw -Encoding utf8 | ConvertFrom-Json
$ids = @($registro.fontes | ForEach-Object { $_.id })
"[$stamp] Remote-check G35: $($ids.Count) fonte(s) em $reg" | Tee-Object -FilePath $log

$falhas = @()
foreach ($id in $ids) {
    "----- --check-remote --id $id -----" | Tee-Object -FilePath $log -Append
    & python "$extrator" --check-remote --id "$id" 2>&1 | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE
    if ($code -ne 0) { $falhas += "$id (exit $code)" }
}

$resumo = if ($falhas.Count -eq 0) { "$($ids.Count)/$($ids.Count) PASS" } else { "$($ids.Count - $falhas.Count)/$($ids.Count) PASS; FALHAS: $($falhas -join '; ')" }
$fim = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$status = if ($falhas.Count -eq 0) { "OK" } else { "FALHA" }
$linha = "[$fim] REMOTE-CHECK: $status | $resumo | log: $log"
$linha | Tee-Object -FilePath $log -Append
$linha | Out-File -FilePath $latest -Encoding utf8

if ($falhas.Count -eq 0) { exit 0 } else { exit 1 }
