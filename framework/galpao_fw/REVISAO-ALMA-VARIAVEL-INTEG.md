# Revisão — Integração do pórtico de alma variável (tapered)

Conferência do sênior. O gerador de seções `alma_variavel.secao_tapered` já está
homologado ([ALMA-VARIAVEL](REVISAO-ALMA-VARIAVEL.md)). Esta revisão trata da
**INTEGRAÇÃO**: o pórtico de mísula de alma variável entra na análise (rigidez
variável por segmento), no ProjetoSpec (gate) e no build 3D (loft). Fase 6.b.
Criado 2026-07-10.

> **STATUS: 🔁 PARECER 1 ATENDIDO — REVER** (2026-07-11). Q2 (CRÍTICO) corrigido:
> **verificação FLA/FLM/FLT + flexo-compressão por segmento** (não assume mais o
> joelho). Q4 aprovado. Q1 (coluna tapered) e Q3 (panel zone/doubler no nó)
> aceitos como **backlog** (features maiores). Prova empírica: no caso 600→300 mm
> sob vento, **governa o segmento 7 (cumeeira, h=319 mm, util 0,68), NÃO o joelho**
> (h=581 mm, util 0,17) — confirma a tese do parecer.

## PARECER SÊNIOR 1 — respostas

| Q | Ponto | Decisão |
|---|---|---|
| Q1 | discretização 8 seg + **coluna tapered** | seções no ponto médio OK; **coluna tapered = backlog** (aceito; hoje só o rafter). |
| Q2 | **seção do joelho NÃO governa** [CRÍTICO] | **ATENDIDO** — loop de estados-limite por segmento (§6). |
| Q3 | panel zone / doubler plate no nó alto | **FLAG/backlog** — verificação do painel da coluna + enrijecedor diagonal fica p/ o executivo do nó. |
| Q4 | não-regressão prismático | **OK** (aprovado pelo sênior). |

## 6. Verificação por segmento (Q2 — implementado 2026-07-11)

Em alma variável o módulo `Wx` cai de forma ~quadrática com a altura, mais rápido
que o `Msd` decresce a partir do joelho → a **utilização pica num segmento
intermediário/da cumeeira**, não no joelho. Implementado:

- `alma_variavel.props_I(h, bf, tw, tf)` — props **completas** (A, Ix, Iy, Wx, Zx,
  ry, rx, …) por seção; `secao_tapered` embute `props` em cada segmento.
- `galpao_portico.analyse()` devolve `rafter_segmentos`: envelope ELU de `M/N/V`
  **por elemento** do rafter + a seção local + a combinação governante.
- `rodar_galpao` (gate6): para cada um dos `2·NSEG` segmentos, roda
  `check_nbr8800.verifica` (FLA/FLM/FLT + flexo-compressão) com a **seção local**,
  `Lb` da mão-francesa e os esforços **amplificados pelo B2 do MAES** (2ª ordem;
  B2 é multiplicador global, não muda qual segmento governa). Reporta o
  **segmento governante** e sinaliza `[!]` quando **não** é o joelho.
- `res["alma_variavel"]`: `interacao_max_seg`, `seg_governante`, `governa_joelho`.
- Teste `test_verificacao_por_segmento`: exige o campo e confere que, neste caso,
  o governante **não** é o joelho.

**Exemplo (gate6-alma-variavel.txt), h 600→300, vento:**

```
  seg |  h(mm) | Msd(kN.m) | interacao | governa
    0E |    581 |      52.3 |      0.17 | C1_Gdesf_W1   <- joelho (NAO governa)
    ...
    7E |    319 |     115.6 |      0.68 | C1_Gdesf_W1   <- GOVERNA (cumeeira)
  >> GOVERNA o segmento 7E (h=319 mm, interacao=0.68)  [!] NAO e o joelho
```

---

## 1. Análise com rigidez variável (galpao_portico)

O rafter deixa de ser prismático quando `tipo_portico="alma_variavel"`: cada um
dos `NSEG` (=8) segmentos do rafter recebe a **sua** seção (A, I) de
`secao_tapered(h_joelho, h_cumeeira, …)` — funda no joelho, rasa na cumeeira.
`_chain_var` cria os elementos com `A`/`I` por segmento; `frame2d.add_element`
já aceitava seção por elemento.

- Rafter esquerdo: eave→ridge (h_joelho no beiral → h_cumeeira na cumeeira).
- Rafter direito: ridge→eave (espelhado). Coluna segue prismática.
- A distribuição de momentos passa a refletir a rigidez variável (mísula atrai
  momento para o joelho — comportamento esperado do pórtico de mísula).

**[Q1]** Concorda em modelar a mísula como I duplamente simétrico com **altura
linear** entre joelho e cumeeira, 8 segmentos (`secao_tapered` no ponto médio de
cada segmento)? Quer a coluna também tapered ou só o rafter (hoje só o rafter)?

---

## 2. Verificação de estados-limite (o ponto a decidir)

Hoje: a análise usa a rigidez variável (correto), e o memorial
(`gate6-alma-variavel.txt`) **tabela as seções por segmento** (h/A/I/Wx) + peso
linear médio, sinalizando que a **seção do joelho governa** a flexo-compressão.

**A verificação por segmento (FLA/FLM/FLT com seção variável) está marcada
"A CONFIRMAR"** — não é feita automaticamente por segmento; a seção do joelho
(mais solicitada) é o ponto de controle.

**[Q2]** Aceita, para o anteprojeto, verificar a **seção do joelho** (mais funda,
maior momento) como governante, deixando a verificação segmento-a-segmento
(esp. FLT com o banzo comprimido de altura variável — Anexo H / mísula) como
trabalho de detalhamento? Ou exige a verificação por segmento já nesta fase?

> **RESPOSTA:** parecer **vetou** assumir o joelho — implementada a **verificação
> por segmento** (§6). Confirmado empiricamente que o joelho não governa.

---

## 3. Gate + build 3D

- **Gate:** `estrutura.tipo_portico` (prismatico|alma_variavel) — default
  prismático (não bloqueia); inválido bloqueia. `estrutura.tapered`
  {h_joelho, h_cumeeira, bf, tw, tf} (m) = geometria da mísula (dado de projeto).
- **3D:** `build_galpao.tapered_rafter` faz **loft** entre o perfil I do joelho e o
  da cumeeira (`Part.makeLoft`, sólido); cai no prismático se h_joelho==h_cumeeira.
  Take-off/cobertura/pranchas inalterados (o rafter é um sólido como antes).

**[Q3]** O detalhe do **joelho** (chapa de topo/mísula) hoje é dimensionado com a
seção prismática de referência; com a mísula de 600 mm no joelho, a chapa/enrijec.
do joelho deve acompanhar essa altura. Sinalizo como FLAG de detalhamento —
confirma que fica para o executivo do nó?

**[Q4]** A **não-regressão** está garantida: `tipo_portico=prismatico` (default)
mantém a ref 20×10 byte-idêntica (sentinela reseta o estado tapered entre projetos
no mesmo processo). Confirma que o prismático não deve mudar em nada.

---

## 4. Não-regressão / evidência

- `galpao_portico._selftest` e `alma_variavel._selftest` verdes.
- Frame prismático (TAPERED=None) idêntico ao anterior; frame tapered tem
  `I_joelho > 1,5·I_cumeeira` (rigidez variável real).
- `smoke_executivo`: 6º caso `alma_var` (calc+3D loft+pranchas+PDF); casos
  prismáticos (padrão/vão/largo/ponte/estaca) inalterados.
- `tests/test_fase6b_alma_variavel.py` (7 fast + 1 build).

---

*Método (secao_tapered) homologado em ALMA-VARIAVEL. Esta doc cobre a integração
análise+spec+3D. A verificação por segmento é FLAG [Q2].*
