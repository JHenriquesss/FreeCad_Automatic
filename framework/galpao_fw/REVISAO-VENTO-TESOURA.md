# Revisão — Sucção de vento auto-acoplada à tesoura (NBR 6123)

Conferência do sênior. Fecha o último item do backlog da fase 6.b: a **sucção de
vento na cobertura** deixa de ser INPUT manual (`w_vento_kN_m`, default 0) e passa a
ser **auto-acoplada** da NBR 6123 (`(Cpe−Cpi)·q`) como carga de uplift na tesoura.
Fase 6.7. Criado 2026-07-11.

> **STATUS: A REVISAR (sênior).** Reusa `vento_nbr6123.compute` (**já homologado** —
> itens 6/24 do índice) — nenhum coeficiente novo. Override explícito do usuário
> continua honrado.

## Base normativa (via `vento_nbr6123`, homologado)

- `q = 0,613·Vk²` (kN/m²); `net = Cpe − Cpi` por superfície (telhado Tabela 5 +
  Cpi Tabela 4). O `vr = vento.compute(...)` já roda no gate5 do pórtico.
- **Envelope** = superfície de cobertura de **maior sucção** (net mais negativo).

## 1. Acoplamento (rodar_galpao, gate6 tesoura)

```
w_vento_auto = min( vr.net[caso][cobertura_*] ) · q · bay      [kN/m, uplift < 0]
```
Usa o **mesmo `vr`** já computado (nada recalculado). Aplicado como `w_vento_kN_m`
na `verifica_tesoura`, cuja combinação de uplift é `1,4·w_vento + 0,9·(−w_grav)`
(sinal negativo = sucção sobe, alivia a gravidade → inverte esforços nos banzos). O
gate `gate6-tesoura.txt` reporta `net`, `q`, `bay`, `w_vento` e a fonte, citando a
NBR 6123.

**Override:** se o usuário informar `estrutura.trelica.w_vento_kN_m`, esse valor
vence (`fonte = "input"`); senão `fonte = "auto"`. `res["tesoura"]` ganha
`w_vento_auto_kN_m`, `w_vento_usado_kN_m`, `w_vento_fonte`.

## 2. Efeito medido

Ref 10×20 m, bay 5 m, V0=40 m/s: envelope cobertura `net = −1,73`, `q = 0,787`
kN/m² → `w_vento = −1,73·0,787·5 = −6,808 kN/m` (uplift). Tesoura: `u_max = 0,665`,
OK (a sucção inverte a tração/compressão dos banzos, mas os perfis atendem).

## 3. Não-regressão

Acoplamento **só na tesoura** (mne-4): calc sweep 7/7 → `w_vento_fonte` só aparece
no caso tesoura (`auto`); prismático/alma var/ponte/estaca `None`. Sinal negativo
(uplift, mne-2). Envelope usa **cobertura**, não parede (mne-5). Tesoura executivo
end-to-end OK.

## Checklist de testes (`tests/test_fase67_vento_tesoura.py`)

| Teste | Cobre |
|---|---|
| `test_succao_auto_negativa` | `w_vento_auto < 0` (uplift) + fonte auto |
| `test_succao_auto_casa_net_q_bay` | `== min(net_cob)·q·bay` |
| `test_override_honrado` | input explícito vence (mne-3) |
| `test_gate_cita_nbr6123` | gate cita NBR 6123 |
| `test_prismatico_sem_w_vento_auto` | só tesoura (mne-4) |

5 testes. Não-regressão: calc sweep 7/7 (só tesoura muda); tesoura executivo end-to-end.

## Notas / limites de escopo

- A sucção é aplicada como carga **distribuída uniforme** de cobertura (envelope
  global). A distribuição por zona (borda/canto, Cpe médio local) segue como
  refino — para a tesoura global o envelope uniforme é conservador e suficiente.
