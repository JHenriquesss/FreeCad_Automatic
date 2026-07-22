# tools/ — job periódico da suíte de build 3D

## Por que existe

Os testes marcados `build` (9, em `framework/galpao_fw/tests/`) constroem o modelo
3D no FreeCAD (`freecadcmd.exe`) e verificam invariantes de geometria — inclusive
**interpenetração de peças** (`checa_interferencia`). São **lentos** (~5 min) e por
isso ficam **deselected** no regresso padrão:

```bash
python -m pytest tests/ -m "not build"     # o green bar do dia a dia (rápido)
```

Consequência: **regressões de geometria 3D passam em silêncio**. Foi assim que dois
bugs de interferência calha/condutor (condutor Ø150 × chapa de base; calha/condutor ×
coluna tapered) sobreviveram várias sessões. Este job é a **guarda periódica**.

## Componentes

- **`run_build_suite.ps1`** — roda `pytest -m build`, grava log com timestamp em
  `tools/build-logs/` (ignorado no git) e um resumo em `build-logs/LATEST.txt`.
  Exit code = o do pytest. Não mexe no FreeCAD que você tenha aberto (os testes usam
  `freecadcmd` em subprocessos isolados, não o bridge da porta 9875).
- **`register_build_task.ps1`** — registra/remove a tarefa agendada do Windows
  `GalpaoFW-BuildSuite` que chama o runner. Local (não CI de nuvem) porque os testes
  exigem o FreeCAD 1.1 instalado.

## Uso

```powershell
# rodar a suíte de build agora (manual)
powershell -ExecutionPolicy Bypass -File tools\run_build_suite.ps1

# registrar o job semanal (domingo 03:00, default)
powershell -ExecutionPolicy Bypass -File tools\register_build_task.ps1

# variações
powershell -ExecutionPolicy Bypass -File tools\register_build_task.ps1 -Frequencia Daily -Hora 02:00
powershell -ExecutionPolicy Bypass -File tools\register_build_task.ps1 -Remover

# disparar a tarefa registrada manualmente / ver o resultado
Start-ScheduledTask -TaskName GalpaoFW-BuildSuite
Get-Content tools\build-logs\LATEST.txt
```

Se `freecadcmd.exe` não estiver no caminho padrão, passe `-FreeCadCmd <path>` ao
runner (ou defina a variável de ambiente `FREECADCMD`).
