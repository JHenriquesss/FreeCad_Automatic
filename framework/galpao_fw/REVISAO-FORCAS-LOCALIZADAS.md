# Revisão — Forças transversais localizadas + enrijecedor de apoio (NBR 8800 §5.7)

Novo módulo `forcas_localizadas.py` com a Seção 5.7 completa da NBR 8800:2008
(mesas e almas de perfis I/H sob forças transversais localizadas) **e** o projeto
do **enrijecedor de apoio** (§5.7.8/5.7.9). Fecha o backlog "enrijecedor de apoio
§5.7.4". Fase 6.17. Criado 2026-07-13.

> **STATUS: ✅ HOMOLOGADO SEM IMPEDITIVOS** (2026-07-13). Auditoria do sênior conferiu
> as 4 contas manuais (501,8 / 552 / 414 / 163,4 kN) por engenharia reversa e bateu
> casas decimais. 2 ressalvas processuais atendidas — ver §Parecer. Método **verbatim**
> do PDF (`pesquisa/aço/nbr8800_2008_1.pdf`, pág 57–62). Unidades SI (m, kN).

## Base normativa (NBR 8800 §5.7 — verbatim)

| Estado-limite | Fórmula (γa1 = 1,10) | Função |
|---|---|---|
| **5.7.2** Flexão local da mesa | `F_Rd = 6,25·tf²·fy/γa1` (dispensa se l_carga<0,15 bf; ½ se dist<10 tf) | `flexao_local_mesa` |
| **5.7.3** Escoamento local da alma | `1,10·(5k+ln)·fy·tw/γa1` (interior) · `1,10·(2,5k+ln)·fy·tw/γa1` (extremidade) | `escoamento_local_alma` |
| **5.7.4** Enrugamento da alma | `0,66·tw²/γa1·[1+3(ln/d)(tw/tf)^1,5]·√(E·fy·tf/tw)` (≥d/2); `0,33·tw²·[...]` (<d/2, 2 sub-ramos por ln/d) | `enrugamento_alma` |
| **5.7.5** Flambagem lateral da alma | `Cr·tw³·tf/(γa1·h²)·[0,94+0,37·((h/tw)/(l/bf))³]` (rot. impedida, ≤2,30); `[0,37·(.)³]` (rot. livre, ≤1,70). Cr=32E se Msd<Mr, 16E se ≥ | `flambagem_lateral_alma` |
| **5.7.6** Flambagem da alma (par) | `24·tw³·√(E·fy)/(h·γa1)` (½ se par a <d/2 da extremidade) | `flambagem_alma_compressao` |

`k` = tf + perna do filete (soldado) ou tf + raio (laminado); `h` = d−2·tf (soldado).

### §5.7.9 Enrijecedor de apoio (barra comprimida)

```
5.7.9.4:  dimensionar como barra comprimida (§5.3), flambagem por flexão em eixo
          no PLANO MÉDIO DA ALMA.
   Seção  = enrijecedores + faixa de alma  (12·tw extremidade / 25·tw interna)
   Lb     = 0,75·h
   I      = t_st·(2·b_st+tw)³/12  (par; = ist_par da fase 6.13)  ; r=√(I/A_eff)
   Ne     = π²·E·I/Lb² ; λ0 = √(A_eff·fy/Ne) (Q=1) ; χ = chi_compressao(λ0)
   N_Rd   = χ·A_eff·fy/γa1
5.7.9.5:  (a) b_st + tw/2 ≥ b_ref/3   (b) t_st ≥ tf/2  e  t_st ≥ b_st/15
```

## O que revisar

1. **Coeficientes verbatim** — conferir os `1,10`, `6,25`, `0,66/0,33`, `24`,
   `0,94/0,37`, `Cr=32E/16E`, `12tw/25tw`, `Lb=0,75h` contra as imagens das pág 67–71
   (renderizadas). Em particular o `1,10` do 5.7.3 (extração RTL do PDF era ambígua;
   confirmado na imagem: `1,10·(5k+ln)` / `1,10·(2,5k+ln)`).
2. **Enrijecedor como barra comprimida (5.7.9.4):** eixo no **plano médio da alma**
   → `I = ist_par` (reusa a fase 6.13, item 43 homologado); faixa de alma
   colaborante 12tw/25tw; `Lb=0,75h`; `χ` pela `chi_compressao` (Tabela 4 / §5.3.3).
3. **Geometria 5.7.9.5** — largura `b_st+tw/2≥b_ref/3` e espessura `t_st≥max(tf/2, b_st/15)`.
4. **Agregador `reacao_apoio`** — aplica os estados de uma **extremidade** de viga
   (escoamento ramo extremidade + enrugamento ramo extremidade + flambagem lateral se
   deslocamento lateral não impedido) e decide `precisa_enrijecedor` (5.7.8).
5. **Dimensionador `dimensiona_enrijecedor_apoio`** — varre chapas comerciais,
   retorna a menor `(b_st,t_st)` que atende `F_sd` **e** a geometria 5.7.9.5.

## Valores conferidos à mão (perfil 600×250, tw=8, tf=16, fy=345 MPa)

- Flexão local mesa: `6,25·0,016²·345000/1,10 = 501,8 kN` ✓
- Escoamento alma interior/extremidade: `552 / 414 kN` ✓
- Flambagem alma (par): `24·0,008³·√(2e8·3,45e5)/(0,568·1,10) = 163,4 kN` ✓

## Cobertura de teste (fase 6.17)

`tests/test_fase617_forcas_localizadas.py` — 11 testes: valores verbatim (flexão,
escoamento int/ext, flambagem par + ½); dispensa 5.7.2.1; ramos do enrugamento;
aplicabilidade da flambagem lateral (razão ≤2,30) + Cr 32E/16E; geometria 5.7.9.5;
enrijecedor barra comprimida (Lb=0,75h, faixa 12tw); dimensionador; agregador
`precisa_enrijecedor`.

## Parecer do sênior (2026-07-13) — HOMOLOGADO, 2 ressalvas processuais

Sem erro de método. Coeficientes verbatim confirmados (1,10; 6,25; 0,66/0,33;
32E/16E; 2,30/1,70; 12tw/25tw; Lb=0,75h). Contas manuais auditadas por eng. reversa:
`k=20 mm` (=tf+a, filete 4 mm) e `ln=100 mm` fecham flexão 501,8 / escoamento 552/414
/ flambagem par 163,4 kN. Agregador `reacao_apoio` corretamente filtra os estados de
extremidade e exclui a flambagem da alma (par de forças).

**R1 (processual) — documentar `k`/`ln` no teste. ATENDIDO.** `test_fase617` ganhou
constantes nomeadas `K_REF=0,020` e `LN_REF=0,100` com comentário do racional
(k=tf+a; ln=comprimento de atuação) e os resultados esperados anotados nas asserções.

**R2 (matemático) — inércia do enrijecedor `I_par`. ACEITO como simplificação.**
`I = t_st·(2b_st+tw)³/12` (chapa cheia contínua) despreza a inércia própria da faixa
de alma colaborante e trata a lacuna como `t_st` (não `tw`). A inércia exata da seção
em cruz seria `I − t_st·tw³/12 + L_faixa·tw³/12`. Erro ≈ **0,05%** (termo cúbico
central irrelevante frente ao cubo do braço das abas). Direção: leve **super**estimativa
de I → χ marginalmente maior (contra a segurança), porém <0,05% — desprezível. A
**área efetiva** `A_eff` (que domina `λ0=√(A_eff fy/Ne)`) **já inclui** a faixa 12tw/25tw.
Mantido conforme prática tradicional (parecer endossa). Registrado como FLAG explícito.

## Escopo (FLAGs — Ask-Do-Not-Invent)

- `ln` (comprimento de atuação da força), `k` (perna do filete/raio), e a distância
  à extremidade são **dado de fabricação/geometria** — parâmetros de entrada.
- Soldas enrijecedor↔mesa/alma (5.7.9.1/2/3) e esmagamento local (6.6.2 no caso de
  extremidades ajustadas) = detalhamento executivo (fora do escopo deste módulo).
