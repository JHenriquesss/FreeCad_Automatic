# Revisão — Sucção de vento auto-acoplada à tesoura (NBR 6123)

Conferência do sênior. Fecha o último item do backlog da fase 6.b: a **sucção de
vento na cobertura** deixa de ser INPUT manual (`w_vento_kN_m`, default 0) e passa a
ser **auto-acoplada** da NBR 6123 (`(Cpe−Cpi)·q`) como carga de uplift na tesoura.
Fase 6.7. Criado 2026-07-11.

> **STATUS: A REVISAR (parecer 1 respondido).** Reusa `vento_nbr6123.compute` (**já
> homologado**) — nenhum coeficiente novo. Override explícito do usuário honrado.

## Parecer sênior 1 — respostas

| Pt | Alegação | Veredito / ação |
|---|---|---|
| 1 | `q = 0,613·Vk²` daria N/m², não kN/m² | **Doc corrigido; código já certo.** `vento.compute` faz `q = 0,613·Vk²/1000` (N/m²→kN/m²). O sênior admitiu "o motor provavelmente está correto"; era só o texto do markdown sem o `/1000`. |
| 2 | Sinal do uplift `0,9·(−w_grav)` inverte a gravidade (soma em vez de opor) | **PROCEDENTE — corrigido (bug real).** Convenção do solver: `w>0` = p/ baixo. `w_grav>0` (baixo), `w_vento<0` (cima). O `−w_grav` levava a gravidade p/ cima → **somava** ao uplift (superdimensionava). Corrigido para `1,4·w_vento + 0,9·w_dead` (vetores opostos). **Além disso**, o estabilizante passa a excluir a sobrecarga `Q` (NBR 8681: carga variável não resiste ao uplift) → `w_dead = (G+self)·bay`. |
| 4 | Envelope uniforme (min de todas as zonas) é conservador/antieconômico | **ACEITO como V1 + backlog.** O envelope global usa o Cpe médio da zona de cobertura de maior sucção. Ponderação por área de influência das zonas (menos aço) = dívida técnica p/ fase futura. |

## Base normativa (via `vento_nbr6123`, homologado)

- `q = 0,613·Vk²` **[N/m²]** → `/1000` → **[kN/m²]** (o código faz a conversão);
  `net = Cpe − Cpi` por superfície (telhado Tabela 5 + Cpi Tabela 4).
- **Envelope** = superfície de cobertura de **maior sucção** (net mais negativo).

## 1. Acoplamento (rodar_galpao, gate6 tesoura)

```
w_vento_auto = min( vr.net[caso][cobertura_*] ) · q · bay      [kN/m, uplift < 0]
```
Usa o **mesmo `vr`** já computado (nada recalculado). Aplicado como `w_vento_kN_m`
na `verifica_tesoura`, cuja combinação de uplift é `1,4·w_vento + 0,9·w_dead`
(`w_vento<0` sobe, `w_dead>0` desce → **vetores opostos**; a gravidade permanente
alivia a sucção). Sob sucção máxima o banzo inferior **reverte** para compressão. O
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
