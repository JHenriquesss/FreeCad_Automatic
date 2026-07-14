# Revisão — Vento por zona (por água) na tesoura (NBR 6123 Tabela 5)

Conferência do sênior. Fecha a **dívida (c)** do backlog do parecer 6.b: a tesoura
recebia a sucção de vento como `min(net_cob)` (Cpe−Cpi **mais negativo**) aplicado
**UNIFORME em todo o vão** — um estado **fictício** (as duas águas nunca atingem o
pico de sucção simultaneamente). NBR 6123 Tabela 5 dá o Cpe **por água**
(barlavento EF / sotavento GH) atuando **simultaneamente** — o estado de projeto
real. Fase 6.11. Criado 2026-07-12.

> **STATUS: ✅ HOMOLOGADO (após 3 correções + 1 hardening)** (2026-07-12). Parecer:
> conceito e economia **aprovados**; 4 pontos levantados. **1 crítico REAL acatado**
> (faltava o caso de vento a **0°/longitudinal**, que gera uplift SIMÉTRICO e pode
> governar) + **2 fixes** (cumeeira = média; γg de pressão) + **1 refutado-com-prova**
> (Cpi: não havia estado fictício — ver abaixo — mas foi tornado explícito). Base
> Tabela 5 **verbatim** (PDF pág 15, imagem). Economia **re-medida com o envelope
> completo**.

## Parecer sênior — respostas

| Pt | Alegação | Veredito / ação |
|---|---|---|
| **🔴 1 (Cpi)** | Extração de Cpi **independente** por água → estado fictício (Cpi diferente em cada água) | **REFUTADO como bug presente, mas ACATADO como hardening.** Prova: `net[cs][sup]=Cpe[sup]−Cpi_cs` aplica **um** Cpi a **todas** as superfícies; `min` por água = `Cpe_água − max(Cpi)` → **ambas as águas vêm SEMPRE do mesmo Cpi** (o `max`), pois `Cpe` é constante e só `−Cpi` varia, idêntico. Estado fictício **matematicamente impossível**. Ainda assim, refatorei para **par fixo explícito** (`net = Cpe − Cpi_max`), blindando contra mudanças futuras. Comportamento idêntico. |
| **🔴/🟡 2 (vento 0°)** | Falta o caso de vento a **0°** (longitudinal): ambas as águas na mesma zona → uplift SIMÉTRICO, pode governar | **PROCEDENTE — CRÍTICO, ACATADO.** `cpe_telhado` só dava o 90° (transversal). Adicionei `cpe_telhado_longitudinal` (Tabela 5, colunas α=0°, **EG/FH verbatim**). O `rodar_galpao` agora **envelopa 90° (por água) + 0° (simétrico EG)** e reporta o caso governante. Sem isso, o refino **removia carga real** (era o real furo, não a economia). |
| **🟡 3 (cumeeira)** | Nó da cumeeira devia usar a **média** `(w_barl+w_sot)/2`, não o `min` | **ACATADO.** `_P_vento_zonas`: cumeeira (`x=L/2`) = média das águas (área tributária = ½ barlavento + ½ sotavento). Remove superconservadorismo residual. |
| **🟡 4 (γg pressão)** | Se a água vira **pressão** (Cpe>0), o peso é **desfavorável** → γg=1,4, não 0,9 | **ACATADO.** `_gamma_g_dead(wv)`: **0,9** (sucção, peso favorável) / **1,4** (pressão, peso desfavorável), por nó. Galpão de baixa inclinação = sucção → inalterado; fecha o furo teórico p/ θ≥30°/galpão aberto. |

## Economia — re-medida com o envelope COMPLETO (honesta)

O valor anterior (u 1,04→0,96) vinha de um **envelope incompleto** (só 90°). Com o **0°
enveloped**:

| Caso | barlavento | sotavento | governa? |
|---|---|---|---|
| 90° transversal (por água) | −7,97 | −5,72 | **sim** (u=0,928) |
| 0° longitudinal (EG simétrico) | −6,41 | −6,41 | não (mais brando aqui) |
| uniforme-pior (antigo) | −7,97 aplicado a tudo | | u=1,04 (fictício) |

Para **este** galpão (slope 20%, θ=11,3°): a barlavento EF (−1,94) domina, o EG
longitudinal (−1,57) é mais brando → **90° governa, u=0,928** (a cumeeira-média baixou
de 0,956→0,928). Para **telhados rasos** (θ≈5°), EG≈EF → o **0° simétrico pode
governar** — agora **sempre enveloped**. A economia é **real e completa**, não mais um
artefato de caso omitido.

## Por que o uniforme-pior estava errado (superconservador)

O Cpe de barlavento (EF) e o de sotavento (GH) da Tabela 5 são o estado de vento
**simultâneo** de UMA direção de vento. Aplicar `min(EF, GH)` às **duas** metades ao
mesmo tempo cria um carregamento que **não existe** fisicamente — sobrecarrega a água
menos solicitada. O correto é: água a barlavento com seu Cpe, água a sotavento com o
seu, **ao mesmo tempo** → é o que o módulo passa a fazer, com **envelope das 2
direções** de vento (a treliça é simétrica, mas o envelope é mantido para robustez a
cargas assimétricas — mne-2).

## Economia real (caso 20 m, telhado do smoke)

Ver a tabela de economia **re-medida com o envelope completo (90°+0°)** na seção
"Parecer sênior — respostas" acima. `u_max` honesto = **0,928** (90° governa neste
galpão de slope 20%).

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
- `_P_vento_zonas(t, trib, w_barl, w_sot, w_dead, direction)` — cargas nodais **por
  água**: metade barlavento com `w_barl`, sotavento com `w_sot`; **cumeeira = média
  `(w_barl+w_sot)/2`** (parecer pt.3). Combinação NBR 8681: `1,4·w_vento(água) +
  γg·w_dead`, com `γg = _gamma_g_dead(wv)` = **0,9** (sucção) / **1,4** (pressão)
  (parecer pt.4).
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
