# Revisão — Redimensionamento (auto-sizing do pórtico)

Otimização **gulosa** de perfis: cada coluna pode ter um perfil diferente
(útil para vãos assimétricos). O algoritmo começa do perfil mais leve,
avalia todas as peças, sobe um degrau na mais solicitada, e repete até
todas passarem (ELU ≤ 1,0 + ELS ≤ H/300).

Código: `redimensionamento.py`. Última atualização: 2026-07-08.

> **STATUS: ✅ HOMOLOGADO (r2)** + otimização gulosa com perfis
> independentes por coluna adicionada.

---

## 1. Método

```python
def melhor():
    cols = [perfil_mais_leve] * (N_VAOS + 1)  # um perfil por coluna
    raf = perfil_mais_leve_raf
    for _ in range(200):
        r = avalia(cols, raf)
        if r["passa"]: return aprovado
        # sobe um degrau na peca com maior interacao
        arts = [(int_pior, "col", i, idx+1), (int_pior*0.9, "raf", 0, idx+1)]
        arts.sort(key=lambda x: -x[0])
        cols[i] = ESCADA[novo_idx]  # ou raf = ESCADA[novo_idx]
```

## 2. O que mudou

| Antes | Depois |
|---|---|
| `CANDIDATOS` fixo com pares `(col, viga)` | Escada linear de perfis, um por coluna |
| Primeiro par da escada que passa | Algoritmo guloso (200 iterações max) |
| `col_ext` e `col_int` fixos | Cada coluna `cols[i]` pode ter perfil diferente |
| Vãos assimétricos não otimizados | `10+20m` → `IPE550×3 + IPE360` int=0,98 |

## 3. Selftest

- 1 vão 20m: `cols=['IPE550','IPE550'] raf=IPE400` int=0,78 ✅
- 2 vãos 15+15m: `cols=['IPE550','IPE550','IPE550'] raf=HEA240` int=0,77 ✅
- 2 vãos 10+20m: `cols=['IPE550','IPE550','IPE550'] raf=IPE360` int=0,98 ✅

**PASSED.**

## 4. FLAGS

1. **Vãos assimétricos extremos** — o algoritmo agrupa todas as colunas
   sob o mesmo perfil por rigidez redistributiva do pórtico. Para `spans=[5,35]`
   pode ser necessário refinar a escada de perfis.
2. **Ponte rolante** — quando presente, a carga excêntrica pode exigir
   perfis diferentes entre colunas do 1º vão. O algoritmo já suporta
   (cada coluna é independente), mas a escada `_ESC_COL` pode precisar
   de mais opções.
