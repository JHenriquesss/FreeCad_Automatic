# Revisão — Pórtico treliçado (tesoura)

Geração de treliça de cobertura tipo Warren ou Pratt para galpões.
**Isostática:** `b + r = 2j`. Banzo superior parabólico.

Código: `tesoura.py`. Criado 2026-07-08.

> **STATUS: ✅ HOMOLOGADO (2026-07-08)** — isostática (b+r=2j),
> Warren 31 barras, Pratt 29 barras, sem sobreposição nos apoios.

---

## 1. Método

- **Banzo superior:** `y = 4h·i·(n−i)/n²` (parábola)
- **Warren:** 8 painéis → 17 nós, 31 barras (8 sup + 7 inf + 16 diag).
  Nós inferiores defasados (meio do painel). Sem banzo inf nos apoios —
  as diagonais conectam diretamente os apoios.
- **Pratt:** 8 painéis → 16 nós, 29 barras (8 sup + 8 inf + 7 mont + 6 diag).
  1 diagonal por painel interno (painéis 2 a 7; extremos já triangulados
  pela convergência dos banzos).
- **Verificação:** `b + 3 = 2j` (isostática, sem mecanismo nem redundância).

## 2. Selftest

`gera_trelica(20, 2.5, 8, "warren")`: 31+3=34=2·17 ✅
`gera_trelica(20, 2.5, 8, "pratt")`: 29+3=32=2·16 ✅

**PASSED.**
