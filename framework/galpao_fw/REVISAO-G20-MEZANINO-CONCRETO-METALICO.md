# REVISAO — G20: mezanino de concreto dentro do galpão metálico

Primeira costura concreto × metálico em uso real: laje, viga e pilar de
concreto encontrando a estrutura metálica do galpão dentro de um envelope já
validado, sem criar envelope novo.

## 1. O que passou a existir

| Arquivo | Papel |
|---|---|
| `galpao_mezanino.py:1-28` | `rodar(spec)` STATELESS: retângulo interior (x0,y0,Lx,Ly,h) em m + 4 pilares nos cantos + 4 vigas de contorno + 1 laje maciça. Laje por `laje_concreto` (NBR 6118, Tabelas de Bares), vigas por `viga_concreto`, pilares por `pilar_concreto`, sapatas por `fundacao_sapata` |
| `fronteiras.py:216-246` | Três fronteiras novas: F18 geometria em m (posição dentro do envelope), F19 laje h em cm com realimentação de carga, F20 seção de viga/pilar em m. `galpao_mezanino` registrado como escritor nas fronteiras existentes de dims/centro/p1p2 |
| `galpao_turnkey.py:101-104,241` | Orquestração: despacha para `galpao_mezanino.rodar`, inclui `mezanino` no mapa de verticais |
| `tests/test_mezanino.py:1-13` | 11 testes: `rodar()` ATENDE para amostra 6×5 a 3 m dentro do galpão 40×20×6; `membros_bim` (4 pilares + 4 vigas + 1 laje + 4 sapatas) com contratos F01/F03/F04/F05/F15/F18/F19/F20; posição DENTRO com rejeição fora; federado sem clash revisável quando interior; turnkey com IFC + quantitativo |

Commit: `bb551ca feat(g20)` — 2 arquivos, 867 linhas. Verificado:
`test_mezanino` + `test_fronteiras` + `test_G21` + tools, 268 passed.

## 2. A regra que organiza tudo: dentro do envelope, nas mesmas coordenadas

- O envelope é o do galpão metálico validado (`comprimento, vao, pe_direito`
  em m); o mezanino ocupa um RETÂNGULO INTERIOR validado contra ele
  (`galpao_mezanino.py:7-9`, `fronteiras.py` F18).
- Origem (0,0,0) no canto do galpão (X=comprimento, Y=vão, Z=altura), a mesma
  do `modelo_neutro` do aço — a costura já sai federada sem transformação
  (`galpao_mezanino.py:15-20`), ao contrário de `galpao_concreto` (X=vão
  centrado, precisa de `_concreto_no_frame_comum`).
- Unidades: modelo neutro em mm (F01/F03/F04/F18), laje em cm no raw
  (F16/F19, com feedback de carga), seção de viga/pilar em m (F04/F20).

## 3. O que este G20 NÃO faz (Ask, Do Not Invent)

- Não arbitra porta de acesso (escada vive em `escada_concreto`, fora daqui).
- Não cria viga intermediária quando o retângulo cresce (1 painel só; mais
  painéis é outra tipologia).
- Não inventa ponte térmica nem detalhe de chumbamento na estrutura metálica —
  interferência fica com `checa_interferencia`/clash federado
  (`galpao_mezanino.py:22-26`).
- Fronteiras do mezanino verificadas por asserção declarativa (a fronteira
  existe e casa), NÃO por mutação como as três do G8 na prova do G21 — que
  segue cobrindo só `galpao_concreto` e `edificio_multipavimento` (nota do
  commit `bb551ca`).
