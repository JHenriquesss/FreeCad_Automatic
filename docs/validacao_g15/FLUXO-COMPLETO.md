# Fluxo completo G19 — dos 9 campos ao 4º caso em 1 comando

> **Objetivo:** transformar `projects/galpao-sjb` de `blocked 9` para `ready` e validar contra obra real em `python -m validacao_sistema_g15` (22/23 checks) — sem inventar obra.

## 1. Estado atual (sem obra real)

```powershell
python tools/validar_9_campos.py --spec projects/galpao-sjb/project-spec.json
# FALTAM 9 | blocked 9 (invalid_common_geometry 3 + pending_discipline_input 6)
python tools/ingestao_sjb.py --check
# status: blocked 9
python -m validacao_sistema_g15  # em framework/galpao_fw
# 22/22 PASS (19 G15 + 2 SJB AGUARDANDO + 1 proposta 36×24 0.0% + 1 generica SKIP)
# G19 quarto caso: SJB status=blocked (9 campos) | proposta agente 36x24 ready 0.0%
```

`proposta-obra-conhecida-AGENTE-36x24.json` (`36×24×7 bay6 V0=40 sigma250`) prova que o caminho funciona: `tools/validar_9_campos.py --spec proposta-...` → `ready` e `tools/gerar_sidecar.py` → `23206 kg 235.99 kNm 0.0%`.

## 2. Preencher os 9 campos (sem inventar)

Ver `CHECKLIST-9-CAMPOS.md` (tabela 9), `ESQUEMA-9-CAMPOS.json`, `ENTRADAS-PENDENTES.md`.

```powershell
# 1) Geometria (3 números >0)
python tools/ingestao_sjb.py --set-geometria 36 24 7
# ou edite projects/galpao-sjb/project-spec.json: turnkey.geometria.comprimento/vao/pe_direito

# 2) Disciplinas (6 objetos, não string __PENDENTE__)
#    Use proposta-...36x24.json e project-spec-framework-teste.json como FORMA,
#    mas substitua cada valor por sondagem/ENEL/cargas reais:
#    - turnkey.concreto: fck, fyk, sigma_solo_adm (SPT), tipo fundação
#    - turnkey.aco: perfis, vento V0/cat/classe/s1/s3/z, cargas G/Q/self
#    - turnkey.eletrico: tensao_V, cargas, concessionaria.protocolo ENEL
#    - turnkey.incendio/climatizacao/hidraulica: sub-specs completos

# 3) Validar
python tools/validar_9_campos.py --spec projects/galpao-sjb/project-spec.json --json
# deve ir: gate_status blocked 9 → ready 0, esquema_ok true, can_start_loop2 true
python tools/ingestao_sjb.py --check  # deve ir: blocked 9 → ready
```

## 3. Rodar Loop 2 (quando ready)

```powershell
python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/project-spec.json --out-dir projects/galpao-sjb/run-001 --require-source-refs
# ou: --verify-source-refs para checar 14 source_refs status 2 (nlm login --check)
```

## 4. Anexar memorial e gerar sidecar

```powershell
# 1) Anexe o PDF do escritório
# docs/validacao_g15/galpao-sjb-memorial.pdf  (com CREA/ART, data, página)

# 2) Gere o sidecar a partir do seu spec ready (extrai peso/Mcol do framework)
python tools/gerar_sidecar.py --spec projects/galpao-sjb/project-spec.json --out docs/validacao_g15/galpao-sjb-valores-referencia.json --fonte "Memorial Galpao SJB - Eng Fulano CREA 123456 ART 2024-001 pg 4"

# 3) Substitua os valores do sidecar pelos do memorial real (tolerâncias G19: peso 10% M 15% V 5%)
#    Guard d·sen45: declare se L_rafter é inclinado (10.05) ou projeção (10.0)
```

Template: `galpao-sjb-valores-referencia.json.template`. Guard `validacao_sistema_g15.py:623` rejeita sidecar sintético (`PROPOSTA`/`EXEMPLO`) como real.

## 5. Reaplicar o harness como 4º caso em 1 comando (promessa da REVISAO)

```powershell
cd framework/galpao_fw
python -m validacao_sistema_g15
# com SJB ready + memorial → [PASS] Galpao SJB memorial vs framework (obra real) peso 1.2% Mcol 0.8% | fonte: Memorial ... CREA ...
# G19 quarto caso: SJB status=ready | proposta agente 36x24 ready 0.0% | comando: python -m validacao_sistema_g15
# G19: SJB READY + memorial presente - 4o caso validando contra obra real
# RESULTADO: TODOS PASSARAM  (23/23)

pytest framework/galpao_fw/tests/branches/g15/test_validacao_sistema.py -q  # 38-39 tests (22/23 parametrizados + trunks)
```

Sem obra real, o mesmo comando dá `22/23 PASS` com `2 SKIP AGUARDANDO` + `1 proposta 0.0%` + `1 generica SKIP` — prova que framework não inventa obra e que o caminho do 4º caso já funciona.

Ver também: `QUARTO-CASO-1-COMANDO.md` (1 comando), `CHECKLIST-9-CAMPOS.md` (9 campos), `ESQUEMA-9-CAMPOS.json`, `tools/validar_9_campos.py`, `tools/gerar_sidecar.py`, `tools/demo_g19_4o_caso.py`.
