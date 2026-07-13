# Revisão — Polimento do executivo 2D: glyph de solda AWS + quadros PE09

Duas melhorias no projeto executivo 2D (`techdraw_exec.py`), ambos itens de
**polimento visual** do backlog (não são lacunas de dado). Fases 6.19 (glyph) e
6.12 (PE09). Criado 2026-07-13.

> **STATUS: ⏳ AGUARDANDO PARECER** (2026-07-13). Cosmético — não altera cálculo
> nem geometria; valida-se **visualmente** (PNGs re-renderizados).

## 1. Glyph de solda AWS (fase 6.19)

O símbolo gráfico de solda (`DrawWeldSymbol`) é feature **só-GUI** (não instanciável
headless) — era o único resíduo aberto do executivo 2D (T6). **Resolvido** por SVG
inline via `TechDraw::DrawViewSymbol` (renderiza headless).

- `_svg_solda_filete(perna_mm, campo, todo_contorno)` gera o símbolo AWS A2.4 de
  **filete**: linha de referência + seta ao pé da junta + triângulo do filete
  (perna vertical à esquerda) + perna em mm + círculo de **todo-o-contorno** +
  bandeira de **campo** (opcional).
- `_glifo_solda(...)` coloca via `DrawViewSymbol` (`Symbol=<svg>`, `Scale`).
- **Ligado ao dado do cálculo:** disparado nos detalhes de ligação quando o callout
  tras `perna_solda_mm` (gusset/console). O número da perna = o do memorial.
- **Validado visual** em PE14 (console, perna 6 mm) e PE11 (gusset): símbolo legível
  com círculo de contorno + "6" + triângulo do filete.

**O que revisar:** o símbolo é AWS de filete arrow-side com todo-o-contorno; a perna
é o valor do cálculo. A convenção arrow-side/other-side (posição relativa à linha)
é simplificada — o dado (tipo filete + perna + contorno) está correto e rastreável.

## 2. Quadros do PE09 legíveis (fase 6.12)

Os quadros (verificações + materiais + notas) do PE09 renderizavam com fonte pequena
numa folha A1 esparsa (observação de QA visual anterior — não-defeito). Ampliados via
`DrawViewSpreadsheet.Scale` (célula+texto juntos, sem clipar):

- Quadro de verificações e de materiais: `escala=1,5`; cabeçalhos `tam` 7→9;
  reposicionados (x=210 / x=560) para não colidir com a ampliação.
- Notas técnicas: `escala=1,4`.
- **Validado visual** em PE09: quadros legíveis, sem colisão, carimbo limpo mantido.

**O que revisar:** apenas legibilidade/layout. Conteúdo dos quadros (utilizações do
cálculo, takeoff do modelo 3D, notas) inalterado.

## Cobertura de teste

`tests/test_fase619_glifo_solda.py` — 5 testes do gerador de SVG (XML bem-formado;
perna + triângulo + linha de referência; círculo de todo-o-contorno; bandeira de
campo; sem perna omite texto). O render foi validado **visualmente** (o teste de
render completo é o `smoke_executivo`, 7/7).

## Escopo

Polimento visual do 2D. Nenhum impacto em cálculo, geometria 3D ou dados de
fabricação. Não-regressão: `smoke_executivo` 7/7 (todas as pranchas + memorial PDF).
