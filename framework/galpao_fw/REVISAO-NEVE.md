# Revisão — Carga de neve em coberturas (EN 1991-1-3)

Carga de neve em telhados de 2 águas simétricos conforme EN 1991-1-3.
Três cenários: simétrico + 2 assimétricos. Suporte a deslizamento impedido.

Código: `neve.py`. Criado 2026-07-08.

> **STATUS: ✅ HOMOLOGADO (2026-07-08)** — casos em tuplas (E,D),
> deslizamento_livre implementado.

---

## 1. Método

`s = mu · Ce · Ct · sk` (EN 1991-1-3 §4.1). Premissa: águas simétricas (θ₁ = θ₂).

- **mu** (Tabela 5.2): θ≤30°→0,8; 30°<θ<60°→0,8·(60−θ)/30; θ≥60°→0
- **deslizamento_livre** (bool, default True): se False (platibanda/retentores),
  mu nunca reduz abaixo de 0,8 (§5.3.3)
- **Cenários** (cada um como tupla água_E, água_D):
  - Simétrico: (µ·base, µ·base)
  - Assimétrico 1: (0,5·µ·base, µ·base)
  - Assimétrico 2: (µ·base, 0,5·µ·base)

## 2. Selftest

`carga_neve(1.0, 20°, 1.0, 1.0)`:
- Simétrico = (0.8, 0.8) ✅
- Assim1 = (0.4, 0.8), Assim2 = (0.8, 0.4) ✅

`carga_neve(1.0, 45°, deslizamento_livre=False)`:
- mu = 0.8 (travado), simétrico = (0.8, 0.8) ✅

**PASSED.**
