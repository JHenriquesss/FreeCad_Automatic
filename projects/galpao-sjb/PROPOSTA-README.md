# Proposta 36x24 — obra tipo SJB que o agente conhece (hipótese)

Esta pasta contém **além** do `project-spec.json` bloqueado (9 campos `__PENDENTE__`):

- `proposta-obra-conhecida-AGENTE-36x24.json` — **PROPOSTA DO AGENTE, NÃO É OBRA REAL**.
  - Geometria hipotética plausível para SJB: `36 × 24 × 7.0 m`, `bay 6.0 m`, `7 pórticos`.
  - Vento `V0=40 cat IV B z=8.2` (ridge), `G=0.3 Q=0.25`, `sigma_solo_adm=250 kPa`, elétrica `ENEL BT 380V 20kW+2×75cv`.
  - Origem: cópia de `project-spec-framework-teste.json` com `turnkey.aco.geometria` e `structure.geometria` ajustadas.
  - `preflight_project(..., require_source_refs=True)` → `ready` (0 erros), `can_start_project_loop=True`.
  - `project_loop.run_project` → `romaneio_peso_primario_kg=23206`, `Mcol=235.99 kNm`, `HEB280/HEB260 + IPE450`, `status=failed` por `pilar lambda_y=103.9>90` (fora da faixa NBR 6118) + `needs_review` em elétrica/hidráulica por `A CONFIRMAR` — demonstra que o pipeline **roda** quando os 9 campos existem.

- `docs/validacao_g15/proposta-36x24-exemplo-valores-referencia.json` — sidecar **sintético** gerado do run acima (`peso 23206`, `Mcol 235.99`). Não destrava G19; serve para `tools/demo_g19_4o_caso.py` provar que o harness compara `0.00%` quando memorial e framework coincidem.

## Como usar esta proposta

1. **Ver o gate destravar (sem precisar de obra real):**
   ```powershell
   python -c "import json, project_loop; s=json.load(open('projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json',encoding='utf-8')); print(project_loop.preflight_project(s, options={'require_source_refs':True})['status'])"
   # -> ready
   ```

2. **Rodar Loop 2 hipotético:**
   ```powershell
   python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json --out-dir projects/galpao-sjb/run-proposta-36x24 --require-source-refs
   ```

3. **Ver o harness em modo demo (não é obra real):**
   ```powershell
   python tools/demo_g19_4o_caso.py
   # peso 23206 err 0.00% PASS, Mcol 235.99 err 0.00% PASS
   ```

## Para transformar em obra real

Substitua **cada** hipótese desta proposta pelo valor do **memorial/ENEL/sondagem** da sua obra e grave como `projects/galpao-sjb/project-spec.json` (canônico), depois anexe `docs/validacao_g15/galpao-sjb-memorial.pdf` + `galpao-sjb-valores-referencia.json` (do template). Então:

```powershell
python -m validacao_sistema_g15  # 21/21 PASS com comparação real contra obra (não mais SKIP)
```

Enquanto `project-spec.json` continuar `blocked` com 9 erros, o G19 permanece `AGUARDANDO OBRA REAL` — comportamento correto.
