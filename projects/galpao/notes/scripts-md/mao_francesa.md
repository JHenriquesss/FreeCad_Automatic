# Mao-francesa (contencao da mesa inferior) - mao_francesa.py

Arquivo: `projects/galpao/calc/mao_francesa.py`
Gerado: 2026-07-05
Base: NBR 8800:2008 item 5.5.1.2 (interacao flexo-compressao) + Anexo G (FLT).

## Problema que resolve

Antes, a mao-francesa (flange brace) era **heuristica crua**: o modelo colocava
um braco em TODA terca (offset +/-150..300 mm chutado) e, em paralelo, o check
usava um `Lb=1,67 m` **hardcoded e desconectado** da colocacao. Dois palpites
soltos, sem engenharia ligando um ao outro.

Agora o espacamento das maos-francesas e **derivado do calculo**: a mesa inferior
do rafter e comprimida sob succao de vento (e junto ao joelho sob gravidade); o
braco cria um ponto de travamento que reduz o comprimento destravado `Lb`.
Invertendo a verificacao da barra, acha-se o maior `Lb` que ainda passa e, dele,
quantos bracos sao necessarios.

## Metodo (nao heuristica)

- `interacao(Lb)` e monotona **crescente** em `Lb` (reduzir `Lb` aumenta `Nc,Rd`
  pelo `Ne` do eixo fraco e `Mrd` pelo FLT). Por **bissecao** acha-se o maior
  `Lb` tal que `interacao (5.5.1.2) <= 1,0`. Reusa `check_nbr8800.verifica` -
  mesma equacao do check da secao, garantindo consistencia (nao FLT puro, que
  seria contra a seguranca ao ignorar o axial).
- `Lb_max` = espacamento maximo admissivel entre bracos.
- Dado o espacamento real das tercas ao longo da agua desenvolvida,
  `stride = floor(Lb_max / s_terca)` = a cada quantas tercas colocar um braco;
  `Lb_usado = stride * s_terca` (verificado `<= Lb_max`).
- `n_bracos_meia = ceil(n_terca/stride) - 1`; `n_bracos_portico = 2 * meia`.
- Se nem totalmente travada a barra passa (`interacao(Lb_min) > 1`), travar NAO
  resolve -> retorna `ok=False`, exige secao maior.

Joelho (viga-coluna) e cumeeira contam como pontos ja travados (sem braco).

## Integracao

- `calc/rodar_galpao.py` (Gate 7): pega o combo de maior `|Msd|` na viga, roda
  `plano_mao_francesa`, salva `gate7-mao-francesa.txt`, e usa `Lb_usado` como o
  `Lb` da viga no check de perfis (fecha o circuito calc <-> Lb).
- `work/build_galpao.py`: `MF_STRIDE` (default 2, do calc) posiciona os bracos so
  nas tercas interiores multiplas do passo, via `configurar(mf_stride=...)`.

## Resultado (referencia HEA180, galpao 20x10 engastado)

```
====================================================================
MAO-FRANCESA (contencao da mesa inferior) - HEA180
NBR 8800 5.5.1.2 - espacamento por inversao da interacao flexo-compressao
====================================================================
  Esforcos na mesa comprimida . Nsd=39.8 kN ; Msd=61.3 kN.m ; Vsd=20.8 kN
  Comprimento da meia-agua L .. 5.025 m
  Espacamento das tercas s .... 1.675 m
  Lp (plastico) ............... 2.250 m
  Lr (FLT elastico) ........... 8.497 m
  Interacao totalmente travada. 0.855
  Lb_max (interacao=1.00) ..... 4.643 m
  Passo adotado ............... 1 braco a cada 2 terca(s)
  Lb usado (maior tramo) ...... 3.350 m
  Interacao em Lb_usado ....... 0.913 (OK)
  Bracos por meia-agua ........ 1
  Bracos por portico .......... 2
====================================================================
```

Efeito no projeto: **2 bracos/portico** (era 4 sem base / brace-em-toda-terca),
`Lb=3,35 m`, interacao da viga **0,93** (antes 0,87 com o `Lb=1,67` assumido).
Metade das maos-francesas, agora justificada pela norma.

## Codigo completo

Ver `projects/galpao/calc/mao_francesa.py`. Nucleo: `lb_maximo` (bissecao da
interacao), `plano_mao_francesa` (stride + n_bracos), `relatorio_pt` (memorial
PT), `_selftest` (referencia HEA180 + casos de mais esforco e de "travar nao
resolve").
