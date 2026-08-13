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

## Loop supervisionado de desenvolvimento

O loop descobre uma lacuna observável, consulta o NotebookLM com fontes prontas,
planeja uma tarefa pequena, cria uma worktree isolada, executa RED/targeted/
regressão/build quando aplicável, revisa e registra o resultado. O modo padrão
de trabalho deve ser `supervised`; `dry-run` não edita código e `autonomous`
continua sujeito aos limites e proibições do supervisor.

Pré-requisitos:

```powershell
nlm login --check
python -m pytest tools/loops -q
```

O mapa `fontes/notebooklm-mapa.md` escolhe o notebook pela pasta local e
`fontes/catalogo.csv` identifica título, caminho e hash das fontes. Uma fonte
ausente ou não pronta gera `.loop-runtime/manual-source-requests.md` e estaciona
a rodada; não se deve inventar conteúdo normativo.

Comandos:

```powershell
python -m tools.loops --mode dry-run --max-iterations 1
python -m tools.loops --mode supervised --executor codex --max-iterations 1
python -m tools.loops --mode supervised --executor claude --resume <loop_id>
python -m tools.loops --mode supervised --recover-orphan
```

Em `supervised` e `autonomous`, `--max-iterations N` permite encadear até N
tarefas independentes na mesma execução. Uma tarefa estacionada por
`manual_source_required` é adiada somente naquela execução e a fila continua;
falhas de implementação, testes, revisão ou timeout interrompem o scheduler para
diagnóstico humano. `dry-run` sempre executa uma única simulação. O resumo da fila
fica em `.loop-runtime/scheduler-last.json`.
Se um executor morrer antes de persistir sua fase, `--recover-orphan` estaciona
explicitamente o ledger ativo como `orphaned_loop`, preservando worktree e
artefatos; a execução seguinte deve ser iniciada em um comando separado.

O adaptador de pesquisa impõe limite de 180 s para cada comando `nlm`, decodifica
a saída como UTF-8 e só aceita respostas com citações e trechos textuais
auditáveis. Formatos incompletos do NotebookLM geram `manual-source-requests.md`
e estacionam a rodada; não são tratados como evidência normativa.

O estado fica em `.loop-runtime/ledger.json`, com artefatos em
`.loop-runtime/runs/<loop_id>/`. O root Git não é editado pelo agente; a promoção
é commit local na worktree e merge/push permanecem manuais. Para recuperar uma
falha, examine o ledger e o resumo da sessão, corrija a causa ou forneça a fonte
solicitada e use `--resume`. Um ledger ativo deve ser retomado antes de iniciar
outra rodada.

Cada candidata que reúne uma lacuna de uma disciplina deve declarar `topic` e
`source_paths` no ledger. `source_paths` usa caminhos relativos à pasta `fontes/`
e limita a consulta do NotebookLM exatamente a essas fontes; caminhos de pastas
diferentes não podem ser misturados na mesma candidata. Se uma fonte declarada
estiver ausente, não pronta ou sem evidência textual auditável, a rodada estaciona
e grava a solicitação manual. Isso evita que uma pesquisa ampla do notebook seja
confundida com validação da norma correta.

Os gates têm timeouts separados para comandos e build. O build FreeCAD é uma
guarda própria e só é obrigatório para tarefas marcadas como build. Todos os
testes do loop usam fakes e não chamam rede; a primeira execução real deve ser
precedida por `nlm login --check` e revisão manual da candidata, pergunta e
source IDs.
