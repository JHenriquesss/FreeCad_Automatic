# Quarto caso em 1 comando — G19 (promessa do final da REVISAO-G15)

> **Promessa:** `REVISAO-G15-VALIDACAO-SISTEMA.md:335` — *“Com ele, o harness do G15 se reaplica como quarto caso em um comando — já está escrito e previsto no final da revisão.”*
> **Comando:** `python -m validacao_sistema_g15` em `framework/galpao_fw` (22 checks) — `framework/galpao_fw/validacao_sistema_g15.py:862` — `pytest framework/galpao_fw/tests/branches/g15/test_validacao_sistema.py -q` (36 tests).

## O que o comando faz hoje (sem obra real)

```powershell
cd framework/galpao_fw
python -m validacao_sistema_g15
```

Saída atual (2026-09-03, SJB `blocked` 9 campos):

```
[PASS] Vento amostra 20x28.5 V0=45 catII/B (Vk/q)
[PASS] Sistema vs manual CBCA (portico W310x38,7, Fd1) err=0.76%  V 0.4% H 0.1% M 0.8%
...
[PASS] Galpao SJB preflight bloqueado corretamente (9 campos, G19 guard)
[PASS] Galpao SJB memorial vs framework (AGUARDANDO OBRA REAL)  SKIP
[PASS] Obra conhecida agente 36x24 (hipotese SJB, proposta agente) peso 0.0% Mcol 0.0%
RESULTADO: TODOS PASSARAM
G19 quarto caso: SJB status=blocked (9 campos) | proposta agente 36x24 ready 0.0% | comando: python -m validacao_sistema_g15
G19: AGUARDANDO OBRA REAL - preencher projects/galpao-sjb/project-spec.json (9 campos, ver CHECKLIST-9-CAMPOS.md) + docs/validacao_g15/galpao-sjb-memorial.pdf + sidecar do template para virar validacao contra concreto
```

- `19` checks G15 (`vento`, `CBCA`, `parede`, `equilibrio`, `seções`, `armadura`, `quantitativos`, `elétrica 6/`, `hidráulica 2/`, `estrutura 2/`, `d·sen45` guard) — `19/19 PASS`.
- `2` guards SJB G19 — `blocked` 9 (`invalid_common_geometry`3 + `pending_discipline_input`6) → `PASS` com `SKIP AGUARDANDO` (prova que framework **não inventa obra**).
- `1` proposta agente `36×24` (`ready`, `23206 kg` `235.99 kNm` `HEB280/HEB260 IPE450`) → `PASS 0.0%` (`PROPOSTA NAO E OBRA REAL`).

`22/22 PASS` sem obra real = `SJB blocked` correto + `proposta` demonstra que o caminho do 4º caso já funciona.

## O que o mesmo comando fará com obra real

1. **Preencher os 9 campos** (`docs/validacao_g15/CHECKLIST-9-CAMPOS.md` / `ESQUEMA-9-CAMPOS.json` / `tools/validar_9_campos.py`):
   ```powershell
   python tools/ingestao_sjb.py --check          # blocked 9
   # edite projects/galpao-sjb/project-spec.json a partir de project-spec.template.json
   # ou: Copy-Item projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json projects/galpao-sjb/project-spec.json
   # e substitua cada hipótese por sondagem/ENEL/cargas reais
   python tools/validar_9_campos.py --spec projects/galpao-sjb/project-spec.json  # ready
   ```

2. **Anexar memorial** (`docs/validacao_g15/README.md`):
   ```powershell
   # docs/validacao_g15/galpao-sjb-memorial.pdf  (PDF do escritório, com CREA/ART)
   # docs/validacao_g15/galpao-sjb-valores-referencia.json  (do galpao-sjb-valores-referencia.json.template)
   ```

3. **Reaplicar o mesmo comando:**
   ```powershell
   python -m validacao_sistema_g15
   ```

   Saída então:
   ```
   [PASS] Galpao SJB preflight ready (G19 guard)
   [PASS] Galpao SJB memorial vs framework (obra real) peso 1.2% Mcol 0.8% | fonte: Memorial ... CREA ...
   [PASS] Obra conhecida agente 36x24 ...
   RESULTADO: TODOS PASSARAM
   G19 quarto caso: SJB status=ready | proposta agente 36x24 ready 0.0% | comando: python -m validacao_sistema_g15
   G19: SJB READY + memorial presente - 4o caso validando contra obra real
   ```

   Sem mudar código. Guard `d·sen45` e tolerâncias G15 (`V 5%`, `H/M 15%`, `peso 10%`, `elétrica 2%`) reaplicam-se número-a-número.

## Guard contra dado inventado

- `validacao_sistema_g15.py:623` rejeita sidecar sintético como real: se `_aviso/fonte` contiver `PROPOSTA`/`EXEMPLO SINTETICO` → `BLOQUEADO - sidecar sintetico FAIL`.
- Teste `pytest ...::test_g19_guard_rejeita_sidecar_sintetico_como_real` prova.
- Divergência `>10%` no peso → `FAIL` — `pytest ...::test_g19_detecta_divergencia_peso`.

## Rastreabilidade

- Harness: `framework/galpao_fw/validacao_sistema_g15.py:862` `CHECKS=22` `rodar()`
- Gate: `framework/galpao_fw/project_loop.py:584` `preflight_project(..., require_source_refs=True)` (9 erros)
- Checklist auditada: `docs/validacao_g15/CHECKLIST-9-CAMPOS.md` ↔ `pytest ...::test_g19_checklist_9_campos_batem_com_preflight` (9 linhas ↔ 9 erros) + `ESQUEMA-9-CAMPOS.json` ↔ `test_g19_esquema_9_campos_valida_blocked_e_ready`
- Demo: `tools/demo_g19_4o_caso.py` + `tools/ingestao_sjb.py --check` + `tools/validar_9_campos.py`
