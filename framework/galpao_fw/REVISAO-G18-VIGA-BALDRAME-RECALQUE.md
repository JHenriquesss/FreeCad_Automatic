# REVISAO — G18: viga baldrame + recalque diferencial no edifício

Fecha os dois últimos itens de escopo de fundação que o G9 deixou em
`not_available`: a viga que amarra as sapatas/blocos/estacas e o recalque
diferencial entre pilares. Fronteira, não cálculo novo — `viga_baldrame.py` já
servia o galpão e o recalque usa a curva SPT que `geotecnia_spt` já lia.

## 1. O que passou a existir

| Arquivo | Papel |
|---|---|
| `viga_baldrame_edificio.py:4-38` | Fronteira fundação do edifício → `viga_baldrame.py`. Vãos do grid + carga de parede → `verifica_baldrame`/`dimensiona_baldrame` → reações por linha (viga contínua) → por pilar → gate |
| `recalque_edificio.py:4-33` | Fronteira fundação → geotecnia. N + geometria + SPT/Es → `geotecnia_spt.recalque_elastico` ou `estaca_profunda.recalque_grupo` → recalque por pilar (mm) → diferencial máx−mín e distorção δ/L → gate |
| `edificio_adapter.py:139-143` | `viga_baldrame` e `recalque_diferencial` deixam de ser `not_available` quando declarados; seguem `not_available` quando não declarados |
| `edificio_adapter.py:295-310` | Predicados `declarada` delegando a `viga_baldrame_edificio.declarada` e `recalque_edificio.declarada` — escopo e cálculo usam o mesmo critério |
| `edificio_multipavimento.py:292-329` | Liga os dois módulos no cálculo do pavimento/torre |

Commit: `8400ca5 feat(g18)` — 2 arquivos, 716 linhas. Verificado: `branches/g9` + `branches/g15`, 77 passed.

## 2. A regra que organiza tudo: sem entrada declarada, sem cálculo

Parede arbitrada e recalque arbitrado são tratados como bug, não como default:

- Baldrame (`viga_baldrame_edificio.py:14-18`): a parede é ENTRADA DECLARADA
  (`parede {tipo, espessura_cm, altura}` da Tabela 2 da NBR 6120 ou `q_parede`
  em kN/m). Sem ela → `not_declared`, escopo segue `not_available`.
- Recalque (`recalque_edificio.py:16-20`): o módulo de deformabilidade Es é DADO
  DO LAUDO (A CONFIRMAR). Sem Es (ou sem perfil SPT que permita estimar) →
  `not_declared`. A curva SPT (`perfil_spt`) que `geotecnia_spt` já lê é a fonte
  para correlação quando Es não é declarado.
- Uma seção para a obra, uma geometria por linha: a verificação usa o MAIOR vão
  da malha (conservador) e reparte reações pilar a pilar via viga contínua, não
  por metade de vão (`viga_baldrame_edificio.py:20-23`).

## 3. O que entra e o que NÃO entra (ação horizontal, G23 completa)

- ENTRA no baldrame: `N_amarracao` = max|V| da fundação por pilar
  (`viga_baldrame_edificio.py:25-30`) — tração As = Nd/fyd.
- NÃO ENTRA no baldrame: M (momento fletor na base) — vai para sapata/estaca e
  travamento da divisa; o baldrame flexiona sob `q_parede`, não sob M
  (`viga_baldrame_edificio.py:31-33`, `viga_baldrame_edificio.py:264-266`).
- Recalque usa N característico como aproximação conservadora; a distinção
  ELU × serviço (N_serv) fica nomeada como limitação
  (`recalque_edificio.py:22-28`) — o G23 pode passar a alimentar N_serv distinto.

## 4. O que este G18 NÃO fez

- Não inventou método de baldrame nem de recalque — só ligou módulos já
  aferidos (`viga_baldrame`, `geotecnia_spt`, `fundacao_sapata`,
  `estaca_profunda`).
- Não dimensiona baldrame sem parede declarada nem recalque sem Es/SPT.
- Não fecha a N_serv × N_k para recalque (limitação nomeada, ver §3).
