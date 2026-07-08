# Revisão — Escadas industriais metálicas

Dimensionamento de escadas retas em aço: longarinas (perfil U ou I),
degraus (chapa xadrez/grelha), patamares. Conforme NBR 8800, NBR 6120, NR-18.

Código: `escada.py`. Criado 2026-07-08. Última correção: 2026-07-08.

> **STATUS: ✅ HOMOLOGADO (2026-07-08)** — correções de geometria (espelho
> ceil, n_pisos = n_espelhos-1, Blondel, patamar, flecha) aplicadas.

---

## 1. Método

1. **Geometria:** `n_espelhos = ceil(desnivel/0,18)` (sempre p/ cima),
   `espelho = desnivel/n_espelhos ≤ 18 cm`, `n_pisos = n_espelhos - 1`,
   `piso = projecao/n_pisos`
2. **Blondel:** `62 ≤ 2e + p ≤ 64` (cm) — obrigatório, trava se fora
3. **Patamar:** se `desnivel > 3,20 m` → erro (exige patamar intermediário)
4. **Longarina:** viga inclinada, verificação ELU + ELS (flecha ≤ L/300)
5. **Carga acidental:** 3,0 kN/m² (NBR 6120, acesso público), parametrizável
6. **Guarda-corpo:** NR-18 — altura 1,20 m, rodapé 0,20 m

## 2. Selftest

Desnível 3,0 m, projeção 4,5 m, largura 1,20 m:
- 17 espelhos (176 mm) + 16 pisos (281 mm)
- Blondel = 63,4 cm ✅
- Longarina HEA160, flecha 5,3 mm ≤ L/300 ✅

**PASSED.**

## 3. FLAGS

1. **Carga de utilização** — default 3 kN/m². Para rotas de fuga ou
   grande fluxo, usar 4-5 kN/m² (parametrizável).
2. **Guarda-corpo** — NR-18 exige 1,20 m de altura + rodapé ≥ 0,15 m.
3. **Degraus** — chapa xadrez ou grelha por catálogo do fabricante.
4. **Patamar** — desníveis > 3,2 m exigem patamar intermediário
   (fora do escopo atual do módulo).
