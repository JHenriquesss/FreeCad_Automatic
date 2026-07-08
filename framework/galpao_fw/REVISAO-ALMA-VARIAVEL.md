# Revisão — Pórtico de alma variável (tapered member)

Gera seções transversais ao longo de uma viga I de alma variável
(altura variando linearmente de h1 a h2). Premissa: perfil I
**duplamente simétrico** (mesas superior e inferior iguais).

Cada segmento tem sua própria seção (A, Av, I, W) para análise por
elementos finitos no frame2d. Recomenda-se nseg ≥ 8 para precisão
aceitável (< 2% erro na matriz de rigidez).

Código: `alma_variavel.py`. Criado 2026-07-08.

> **STATUS: ✅ HOMOLOGADO (2026-07-08)** — Av adicionado, nseg=8,
> simetria documentada.

---

## 1. Método

- `h(t) = h1 + (h2 − h1)·t` (ponto médio do segmento)
- `A = 2·bf·tf + (h − 2·tf)·tw`
- `Av = (h − 2·tf)·tw` (área de cisalhamento, alma)
- `I = (bf·h³ − (bf−tw)·(h−2·tf)³) / 12`
- `W = 2·I / h`

## 2. Selftest

`secao_tapered(0.60, 0.30, 0.20, 0.008, 0.0125, 8)`:
- 8 segmentos, alturas decrescentes 0.60 → 0.30 m
- I do 1º > I do último ✅, Av > 0 ✅
- Constante (h1=h2) retorna h correto ✅

**PASSED.**
