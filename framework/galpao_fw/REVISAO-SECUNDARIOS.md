# Revisão — Secundários (longarina, escora, montante)

Conferência do sênior. Peças secundárias pela **NBR 8800:2008**:
(1) longarina de parede (girt, U laminado, flexão biaxial); (2) escora de
beiral/cumeeira (I, flexo-compressão); (3) montante de oitão.

Código: `secundarios_nbr8800.py` (reusa `check_nbr8800`).
Última atualização: 2026-07-06.

> Propriedades de perfil (UPE incl. J/Cw) = catálogo (**A CONFIRMAR**). UPE100-180
> de structolution.com / EN 10365, marcados A CONFIRMAR.

---

## 1. Longarina de parede (U) — flexão biaxial

- **Eixo forte (x)**: vento normal à parede; vão = distância entre pórticos;
  mesa comprimida sob sucção travada por linhas de tirante →
  `Lb = vão/(n_tirantes+1)`. Mrdx pelo **Anexo G** (FLT/FLM/FLA), com **J e Cw
  do U vindos do catálogo** (não de fórmula de I).
- **Eixo fraco (y)**: peso do tapamento + peso próprio;
  `Mrdy = min(Zy, 1,5·Wy)·fy/γa1` (5.4.2, sem FLT no eixo fraco).
- **Interação** (5.5.1, N≈0): `Mx/Mrdx + My/Mrdy ≤ 1`.

```python
def _mrd_eixo_forte_U(sec, fy, Lb, Cb=1.0):
    if "Cw" not in sec or "J" not in sec:
        return None, "INCONCLUSIVO: faltam J/Cw do U (catalogo) para o FLT.", {...}
    # ... mesmas formulas de check_nbr8800.momento_resistente (FLT/FLM/FLA)
```

Sem J/Cw no dict → **INCONCLUSIVO** (não inventa).

---

## 2. Escora de beiral / cumeeira (I) — flexo-compressão

Axial do contraventamento longitudinal (vento no oitão, arrasto Fa) + flexão do
peso próprio no vão entre pórticos. Reusa `check_nbr8800.verifica` (perfil I,
mesma interação 5.5.1.2 e Anexo G) — ver [REVISAO-CHECK-NBR8800.md](REVISAO-CHECK-NBR8800.md).

---

## 3. Dimensionamento (escadas)

`dimensiona_secundarios`: longarina sobe a escada `ESCADA_UPE` (UPE100→180) ×
número de tirantes (sag rods); escora/montante sobem escada HEA. Adota o mais
leve que passa.

---

## 4. Pontos de conferência (FLAGS)

1. **UPE J/Cw** (torção/empenamento) do catálogo — sem eles o FLT é inconclusivo.
   Valores atuais de structolution.com (EN 10365) — A CONFIRMAR no fornecedor.
2. `Mrdy = min(Zy, 1,5·Wy)·fy/γa1` — limite de plastificação (5.4.2).
3. Escora: axial vem do arrasto `Fa` (ver [REVISAO-VENTO.md](REVISAO-VENTO.md));
   fração de Fa por escora depende do arranjo do contraventamento — A CONFIRMAR.

---

## 5. Onde revisar

| Assunto | Função | Item NBR 8800 |
|---|---|---|
| Mrdx do U (FLT) | `_mrd_eixo_forte_U` | Anexo G |
| Mrdy | `verifica_longarina` | 5.4.2 |
| Interação biaxial | `verifica_longarina` | 5.5.1 |
| Escora | `check_nbr8800.verifica` | 5.5.1.2 |
| Escadas | `dimensiona_secundarios` | — |
