# Revisão — Vento por zona (por água) na tesoura (NBR 6123 Tabela 5)

Conferência do sênior. Fecha a **dívida (c)** do backlog do parecer 6.b: a tesoura
recebia a sucção de vento como `min(net_cob)` (Cpe−Cpi **mais negativo**) aplicado
**UNIFORME em todo o vão** — um estado **fictício** (as duas águas nunca atingem o
pico de sucção simultaneamente). NBR 6123 Tabela 5 dá o Cpe **por água**
(barlavento EF / sotavento GH) atuando **simultaneamente** — o estado de projeto
real. Fase 6.11. Criado 2026-07-12.

> **STATUS: 🟡 PENDENTE SÊNIOR** (2026-07-12). Aguarda parecer. Base **no corpus**
> (`vento_nbr6123.cpe_telhado`, Tabela 5, **homologado** no item 27). **Não é
> mudança de método** — é aplicar a Tabela 5 corretamente (cada água seu Cpe), em vez
> da simplificação superconservadora `min` uniforme.

## Por que o uniforme-pior estava errado (superconservador)

O Cpe de barlavento (EF) e o de sotavento (GH) da Tabela 5 são o estado de vento
**simultâneo** de UMA direção de vento. Aplicar `min(EF, GH)` às **duas** metades ao
mesmo tempo cria um carregamento que **não existe** fisicamente — sobrecarrega a água
menos solicitada. O correto é: água a barlavento com seu Cpe, água a sotavento com o
seu, **ao mesmo tempo** → é o que o módulo passa a fazer, com **envelope das 2
direções** de vento (a treliça é simétrica, mas o envelope é mantido para robustez a
cargas assimétricas — mne-2).

## Economia real (caso 20 m, telhado do smoke)

| Carregamento | w barlavento | w sotavento | u_max |
|---|---|---|---|
| **Uniforme-pior** (antigo, `min` em todo o vão) | −7,97 | −7,97 | **1,04 — REPROVA** |
| **Por zona** (Tabela 5, simultâneo) | −7,97 | **−5,72** | **0,96 — PASSA** |

O mesmo perfil que **reprovava** sob o estado fictício **passa** sob o carregamento
real. Sem mudar perfil nem norma.

## Base normativa (já homologada — item 27)

`vento_nbr6123.cpe_telhado(θ)` → `{cobertura_barlavento, cobertura_sotavento}` (Tabela 5,
telhado duas águas). `rodar_galpao` monta `vr["net"][cpi][superfície] = Cpe − Cpi` e
extrai, **por água**, o mais negativo sobre os casos de Cpi:
`net_barlavento`, `net_sotavento`. `w_água = net_água · q · bay`.

**Não** se usa o Cpe **local** de borda/canto (`cpe_medio`, Tabela 5 zonas hachuradas)
na tesoura — esse é para **telha/terça/fixador** (pressão localizada), não para o
pórtico (mne-4). A tesoura usa o Cpe **global por água**.

## Módulo `tesoura.py`

- `_trib_sup(t)` — tributária inclinada por nó do banzo superior (refatorado; cumeeira
  contada 1× — mne-5).
- `_P_vento_zonas(t, trib, w_barl, w_sot, w_dead, direction)` — cargas nodais da
  combinação de uplift **por água**: metade barlavento com `w_barl`, sotavento com
  `w_sot`; cumeeira → água mais desfavorável (conservador). Combinação NBR 8681:
  `1,4·w_vento(água) + 0,9·w_dead`.
- `cargas_vento_zonas(cfg, w_barl, w_sot, direction)` — wrapper testável.
- `verifica_tesoura`: se `cfg["w_vento_zonas"]` presente → combo de vento vira
  **envelope das 2 direções** (barl↔sot espelhado); ausente → escalar uniforme
  (**back-compat**, mne-3).

## Integração (`rodar_galpao`)

`net_barlavento`/`net_sotavento` → `w_vento_zonas=(w_barl,w_sot)` por default. **Override
manual** (`trelica.w_vento_kN_m`) mantém o escalar uniforme (prioridade). `res["tesoura"]`
reporta `w_vento_barl_kN_m`, `w_vento_sot_kN_m` e `w_vento_uniforme_kN_m` (o antigo,
para comparação transparente). Memorial mostra os três + a combinação.

## Não-regressão

- Sem zonas (escalar): idêntico ao anterior (mne-3). Override manual preservado.
- `w_barl == w_sot` reproduz o escalar exato (`test_zonas_iguais_reproduz_escalar`).
- Pórticos não-tesoura (prismático/alma variável) intocados.
- `_selftest` da tesoura verde; suítes 6.7 + 6.c (incl. build) verdes.

## Checklist de testes (`tests/test_fase611_vento_zona_tesoura.py`)

| Teste | Cobre |
|---|---|
| `test_zonas_iguais_reproduz_escalar` | consistência com o caso uniforme |
| `test_zonas_diferentes_cargas_diferem` | wiring: metades recebem cargas distintas |
| `test_envelope_2_direcoes_simetrico` | envelope independe de qual água é "barlavento" (mne-2) |
| `test_zona_menos_ou_igual_aco` | por zona ≤ uniforme-pior (economia) |
| `test_agua_em_pressao_sinal_correto` | água em pressão soma à gravidade, não vira alívio |
| `test_backcompat_escalar` | escalar sem zonas inalterado (mne-3) |
| `test_selftest_roda` | selftest |
| `test_integra_reporta_zonas` | rodar reporta as 3 sucções (me-3) |

8 testes verdes.

## Notas / backlog

- Envelope das 2 direções mantido por robustez (mne-2); em treliça simétrica as
  direções são espelhadas, mas cargas assimétricas (ex.: lanternim) exigem os dois.
- Vento por zona **local** de borda/canto continua no seu lugar próprio (telha/terça),
  desacoplado do pórtico.
