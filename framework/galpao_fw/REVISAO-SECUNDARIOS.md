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

- **Eixo forte (x)**: vento normal à parede; vão = distância entre pórticos.
  **FLT sob sucção** — ver §6 (achado do parecer): sob sucção a mesa comprimida
  é a **interna (livre)**; tirante comum NÃO a trava. `Lb` parametrizado:
  `mesa_interna_travada=False` (default) → `Lb = vão` cheio;
  `True` → `Lb = vão/(n_maos_francesas+1)`. Mrdx pelo **Anexo G** (FLT/FLM/FLA),
  com **J e Cw do U vindos do catálogo** (não de fórmula de I).
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
4. **Lb da longarina sob sucção** (mesa interna livre) — ✅ tratado nesta rodada
   (ver §6.1); `mesa_interna_travada` decidido no gate.

---

## 5. Onde revisar

| Assunto | Função | Item NBR 8800 |
|---|---|---|
| Mrdx do U (FLT) | `_mrd_eixo_forte_U` | Anexo G |
| Mrdy | `verifica_longarina` | 5.4.2 |
| Interação biaxial | `verifica_longarina` | 5.5.1 |
| Escora | `check_nbr8800.verifica` | 5.5.1.2 |

---

## 6. Resposta ao parecer do sênior (rodada 1 — 2026-07-06)

### 6.1 — Lb da longarina sob SUCÇÃO: mesa interna livre — CORRIGIDO (decisão do eng.)

**Achado do parecer PROCEDE.** O código assumia `Lb = vão/(n_tirantes+1)` para
o FLT sob sucção, creditando o tirante (sag rod) com travar a mesa comprimida.
Sob **sucção** a mesa comprimida é a **interna (livre)**; um sag rod comum não
trava a mesa interna — só **mão-francesa** (cantoneira ligada à mesa interna) o
faz. Usar o Lb reduzido sob sucção é **contra a segurança**.

**Física:** sob pressão, a mesa externa (comprimida) é travada pelo tapamento +
tirante → FLT não crítico. Sob sucção, a mesa interna (comprimida) fica livre →
`Lb` = vão inteiro entre pórticos, salvo mão-francesa.

**Decisão do engenheiro** (perguntado no gate — não se inventa travamento): manter
as **duas** possibilidades, parametrizadas por `mesa_interna_travada`:

| Modo | `Lb` (FLT sucção) | Longarina (galpão 20×10) |
|---|---|---|
| `False` (default seguro) | `vão` cheio = 5 m | **UPE140** (inter 0,77) |
| `True` (mão-francesa) | `vão/(n_maos+1)` | UPE100 (inter 0,99) + detalhe |

Impacto: no default conservador, a longarina sobe **UPE100 → UPE140** (adicionar
tirante NÃO ajuda o FLT da mesa interna — só reduz o eixo fraco). Para manter
UPE100, o engenheiro declara `mesa_interna_travada=True` + `n_maos_francesas`
(vira item de fabricação com ART do detalhe).

**Wiring:** flag em `secundarios_nbr8800.verifica_longarina`; gate em
`projeto_spec` (`fechamento.mesa_interna_travada` / `n_maos_francesas`, default
seguro, não bloqueia) → `to_rodar_params`; default em `rodar_galpao.PARAMS_REF`.
Corrigido também o rótulo do memorial/resumo (mostrava "UPE100" fixo → agora o
perfil adotado real).

### 6.2 — Confirmações do parecer (corretas)

- `Mrdy = min(Zy, 1,5·Wy)·fy/γa1` (5.4.2, plastificação com limite 1,5W) ✅
- Interação biaxial `Mx/Mrdx + My/Mrdy ≤ 1` (5.5.1, N≈0) ✅
- Escora flexo-compressão via `check_nbr8800.verifica` (5.5.1.2, desvio 0,2) ✅
- J/Cw do U → INCONCLUSIVO se ausentes (não inventa); centro de cisalhamento do
  U fora da seção → torção exige tapamento travando o giro (premissa registrada).

### 6.3 — Não-regressão

Selftests `secundarios_nbr8800` (3 casos: conservador falha, mão-francesa passa,
UPE140 passa) e `projeto_spec` OK. Galpão 20×10: coluna 0,67 / viga 0,93
inalteradas; longarina adota UPE140 (default seguro); escora HEA160 0,07;
montante HEA160 0,43. Aguarda re-revisão.

---

## 7. Homologação (rodada 2 — 2026-07-06)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 8800:2008.**

Sênior homologou a solução paramétrica do Lb (flag `mesa_interna_travada`,
default seguro) e a física: sob pressão a mesa externa (comprimida) é travada
pelo tapamento/tirante; sob sucção a mesa interna (comprimida) fica livre →
`Lb = vão` salvo mão-francesa. Salto UPE100→UPE140 no default reconhecido como
reflexo exato da queda de Mrdx por FLT em vão longo.

Confirmados: Mrdy=min(Zy,1,5Wy)·fy/γa1 (5.4.2), interação biaxial (5.5.1),
escora flexo-compressão (5.5.1.2), trava INCONCLUSIVO por ausência de J/Cw do U.

Módulo `secundarios_nbr8800.py` liberado. Arquitetura protege contra o erro comum
(ignorar FLT sob sucção) e mantém flexibilidade de otimização se o detalhe de
mão-francesa for garantido.
| Escadas | `dimensiona_secundarios` | — |
