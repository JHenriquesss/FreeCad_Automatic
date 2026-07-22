<#
.SYNOPSIS
  Roda a suite de testes de BUILD 3D (pytest -m build) do galpao_fw e grava um log.

.DESCRIPTION
  Os testes marcados `build` exigem o FreeCAD (freecadcmd.exe) e sao LENTOS
  (~5 min os 9), por isso ficam DESELECTED no regresso padrao (`-m "not build"`).
  Consequencia: regressoes de GEOMETRIA 3D (interpenetracao de pecas) passam em
  silencio - foi assim que 2 bugs de interferencia calha/condutor sobreviveram
  varias sessoes. Este script e a guarda periodica: roda SO os testes de build e
  registra pass/fail com timestamp.

  NAO mata o FreeCAD que voce tenha aberto: os testes de build usam freecadcmd em
  subprocessos ISOLADOS (nao o bridge da porta 9875).

.PARAMETER FreeCadCmd
  Caminho do freecadcmd.exe. Default: C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe
  (tambem respeitado via variavel de ambiente FREECADCMD pelos proprios testes).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\run_build_suite.ps1
#>
[CmdletBinding()]
param(
    [string]$FreeCadCmd = "C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot          # raiz do repo (tools\ -> ..)
$gal  = Join-Path $repo "framework\galpao_fw"
$logdir = Join-Path $PSScriptRoot "build-logs"
if (-not (Test-Path $logdir)) { New-Item -ItemType Directory -Path $logdir | Out-Null }

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$log   = Join-Path $logdir "build_$stamp.log"
$latest = Join-Path $logdir "LATEST.txt"

if (-not (Test-Path $FreeCadCmd)) {
    $msg = "[$stamp] ERRO: freecadcmd nao encontrado em '$FreeCadCmd' - suite de build NAO rodou."
    $msg | Tee-Object -FilePath $log
    $msg | Out-File -FilePath $latest -Encoding utf8
    exit 2
}
$env:FREECADCMD = $FreeCadCmd

"[$stamp] Rodando suite de build (pytest -m build) em $gal" | Tee-Object -FilePath $log
Push-Location $gal
try {
    # -m build: so os testes de build ; -p no:cacheprovider: sem cache ruidoso.
    & python -m pytest tests/ -m build -p no:cacheprovider 2>&1 | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

# Resumo: ultima linha significativa do pytest (ex.: "9 passed in 319s")
$resumo = (Select-String -Path $log -Pattern "passed|failed|error" | Select-Object -Last 1).Line
$fim = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$status = if ($code -eq 0) { "OK" } else { "FALHA (exit $code)" }
$linha = "[$fim] BUILD SUITE: $status | $resumo | log: $log"
$linha | Tee-Object -FilePath $log -Append
$linha | Out-File -FilePath $latest -Encoding utf8

exit $code
