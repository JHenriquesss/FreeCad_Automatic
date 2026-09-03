# REVISAO — G22: a prova de fronteiras muta cópia, não o repositório vivo

Higiene da prova do G21. O mecanismo é idêntico; o isolamento mudou: cada
defeito é injetado numa CÓPIA do pacote num diretório temporário e o pytest
roda contra essa cópia (cwd = tmp).

## 1. Por que mudou

A prova do G21 reescrevia `galpao_concreto.py` e `edificio_multipavimento.py`
no diretório de trabalho real. A restauração era cuidadosa (finally, assert de
conferência, baseline revalidado), mas se o processo morresse dentro da janela
de mutação — Ctrl+C, disco cheio, kill — o finally não roda e o repositório
fica com dois módulos quebrados (commit `346f04d`).

Com cópia, a classe de acidente está eliminada: se o processo morrer no meio,
o repositório permanece com os dois módulos intactos
(`tools/prova_fronteiras_G21.py:9-14`).

## 2. O que a prova faz

- Injeta deliberadamente os três defeitos do G8 e confirma que
  `test_fronteiras.py` fica VERMELHO em cada um — mutação em disco +
  subprocesso real de pytest, sem mocks irreais
  (`tools/prova_fronteiras_G21.py:3-7`).
- As três mutações (`tools/prova_fronteiras_G21.py:38-60`):
  - G21-1 dims em metros (sapata 1000× menor no IFC — `B * 1000.0` → `B`);
  - G21-2 ancoragem divergente (`"ancoragem": "base"` → `"eixo"`);
  - G21-3 laje que engrossa sem realimentar (10→12 cm, 0,5 kN/m² faltando).
- Baseline `test_fronteiras` verde antes e depois (20 passed);
  saída esperada documentada em `tools/prova_fronteiras_G21.py:20-24`.
- Uso: `python tools/prova_fronteiras_G21.py` (3 provas) ou `--keep-green`
  (só verifica baseline verde).

Commit: `346f04d test(g22)` — 1 arquivo
(`tools/prova_fronteiras_G21.py`, +104/−26).

## 3. O que este G22 NÃO fez

- Não mudou o que é verificado (mesmas 3 mutações, mesmos guardas do G21).
- Não estendeu a prova às fronteiras do mezanino (G20) — seguem por asserção
  declarativa, não por mutação.
