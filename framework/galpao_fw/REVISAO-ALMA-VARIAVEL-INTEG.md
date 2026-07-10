# Revisão — Integração do pórtico de alma variável (tapered)

Conferência do sênior. O gerador de seções `alma_variavel.secao_tapered` já está
homologado ([ALMA-VARIAVEL](REVISAO-ALMA-VARIAVEL.md)). Esta revisão trata da
**INTEGRAÇÃO**: o pórtico de mísula de alma variável entra na análise (rigidez
variável por segmento), no ProjetoSpec (gate) e no build 3D (loft). Fase 6.b.
Criado 2026-07-10.

> **STATUS: ⏳ PENDENTE — aguarda parecer do sênior.**
> Revisar as decisões de integração/modelagem marcadas **[Q1]…[Q4]**.

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
