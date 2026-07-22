<#
.SYNOPSIS
  Registra (ou remove) uma tarefa AGENDADA do Windows que roda a suite de build
  periodicamente via tools\run_build_suite.ps1.

.DESCRIPTION
  Cria a tarefa "GalpaoFW-BuildSuite" no Agendador de Tarefas do Windows. Por que
  LOCAL e nao CI de nuvem: os testes de build exigem o FreeCAD 1.1 instalado
  (freecadcmd.exe); instalar essa versao especifica num runner a cada execucao
  seria lento e fragil. A maquina do dev ja tem o FreeCAD -> tarefa local e o
  encaixe certo. Idempotente: re-registrar substitui a tarefa.

.PARAMETER Frequencia
  Weekly (default) ou Daily.

.PARAMETER Dia
  Dia da semana p/ Weekly (default Sunday).

.PARAMETER Hora
  Hora de inicio HH:mm (default 03:00).

.PARAMETER Remover
  Remove a tarefa em vez de registrar.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\register_build_task.ps1
  powershell -ExecutionPolicy Bypass -File tools\register_build_task.ps1 -Remover
#>
[CmdletBinding()]
param(
    [ValidateSet("Weekly", "Daily")] [string]$Frequencia = "Weekly",
    [ValidateSet("Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday")]
    [string]$Dia = "Sunday",
    [string]$Hora = "03:00",
    [switch]$Remover
)

$ErrorActionPreference = "Stop"
$nome = "GalpaoFW-BuildSuite"
$runner = Join-Path $PSScriptRoot "run_build_suite.ps1"

if ($Remover) {
    if (Get-ScheduledTask -TaskName $nome -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $nome -Confirm:$false
        Write-Output "Tarefa '$nome' removida."
    } else {
        Write-Output "Tarefa '$nome' nao existe (nada a remover)."
    }
    return
}

if (-not (Test-Path $runner)) { throw "runner nao encontrado: $runner" }

$acao = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$runner`""

if ($Frequencia -eq "Weekly") {
    $gatilho = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Dia -At $Hora
} else {
    $gatilho = New-ScheduledTaskTrigger -Daily -At $Hora
}

# roda mesmo em bateria / acorda a maquina nao e exigido; se perdeu o horario
# (maquina desligada), roda assim que possivel.
$cfg = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Remove versao anterior (idempotente) e registra no contexto do usuario atual.
if (Get-ScheduledTask -TaskName $nome -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $nome -Confirm:$false
}
Register-ScheduledTask -TaskName $nome -Action $acao -Trigger $gatilho `
    -Settings $cfg -Description "Roda a suite de build 3D do galpao_fw (pytest -m build) e grava log em tools\build-logs." | Out-Null

$quando = if ($Frequencia -eq "Weekly") { "$Frequencia $Dia $Hora" } else { "$Frequencia $Hora" }
Write-Output "Tarefa '$nome' registrada: $quando -> $runner"
Write-Output "Logs em: $(Join-Path $PSScriptRoot 'build-logs')  |  resumo: LATEST.txt"
Write-Output "Rodar agora (teste): Start-ScheduledTask -TaskName '$nome'"
