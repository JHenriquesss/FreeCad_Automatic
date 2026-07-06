# Revisão — Redimensionamento (auto-sizing do pórtico)

Conferência do sênior. Escolhe o par (coluna, viga) **mais leve** que faz o
pórtico passar, com base engastada, rodando a cadeia completa por candidato.
**Não redefine método** — orquestra os módulos já validados variando perfis.

Código: `redimensionamento.py`. Última atualização: 2026-07-06.

---

## 1. Cadeia por candidato

Para cada par (col, raf) da escada:
1. pórtico (`galpao_portico`) → flecha lateral no beiral (ELS);
2. 2ª ordem (`estabilidade_b1b2`, MAES + rigidez 0,8 + nocional) → Msd/Nsd/Vsd
   amplificados (ver [REVISAO-PORTICO.md](REVISAO-PORTICO.md));
3. verificação NBR 8800 (`check_nbr8800`, K=1) em **todas as combinações** →
   pior interação por peça (ver [REVISAO-CHECK-NBR8800.md](REVISAO-CHECK-NBR8800.md)).

```python
def avalia(col, raf, fixed=True, lb_col=LB_COL, lb_raf=LB_VIGA):
    _aplica(col, raf, fixed)
    a = est.analyse()                       # esforcos amplificados (2a ordem)
    drift = gp.analyse()["drift"]           # flecha lateral (ELS)
    lim_flecha = gp.EAVE / 150.0            # H/150 (telha metalica)
    for g, prof, Lb in (("coluna", col, lb_col), ("viga", raf, lb_raf)):
        sec = perfis.PERFIS[prof] ; L = est.SEC[g]["L"]
        worst = max((chk.verifica(sec, FY, L=L, Nsd=r[g]["Nsd"], Msd=r[g]["Msd"],
                                  Vsd=r[g]["Vsd"], Kx=1.0, Ky=1.0, Lb=Lb)
                     for r in a["combos"]), key=lambda x: x["interacao"])
        inter[g] = worst["interacao"]
    passa = (inter["coluna"] <= 1.0 and inter["viga"] <= 1.0 and drift <= lim_flecha)
```

---

## 2. Critério de aprovação e escada

- **ELU**: interação ≤ 1,00 (coluna e viga).
- **ELS**: flecha lateral ≤ **H/150** (telha metálica, NBR 8800 Anexo C / Bellei).

Escada `CANDIDATOS` (mais leve → mais pesado, peso ≈ ΣA): HEA200/HEA180 →
HEB300/IPE550. `melhor()` adota o **primeiro que passa** e deixa o estado global
no perfil adotado.

---

## 3. Pontos de conferência (FLAGS)

1. **Peso ≈ ΣA** (proxy do consumo de aço) para ordenar a escada — confirmar que
   a escada está monótona em peso real.
2. **H/150** para flecha lateral (telha metálica) — confirmar o limite adotado.
3. **Lb** fixos (coluna 2,0 m; viga 1,67 m) por default — na prática vêm das
   longarinas/terças e da mão-francesa.
4. **K = 1** com 2ª ordem (4.9.6.2).
5. Base **engastada** assumida no redim (fixed=True).

---

## 4. Onde revisar

| Assunto | Função | Referência |
|---|---|---|
| Avaliação por candidato | `avalia` | módulos 2, 3 |
| Escolha do mais leve | `melhor` | — |
| Limite de flecha | `LIM_FLECHA` | NBR 8800 Anexo C |
| Escada de perfis | `CANDIDATOS` | — |
