# Revisão — Pórtico de múltiplos vãos (geminado / multi-span)

## 1. O que muda

O framework foi generalizado de **1 vão** para **N vãos** (N ≥ 1). Isso permite
projetar galpões geminados: um pórtico único com N+1 colunas e N cumeeiras,
compartilhando colunas internas entre vãos adjacentes. A retrocompatibilidade
com projetos de 1 vão é total — o fluxo existente (projetos galpao, galpao-ensaio)
não é alterado.

## 2. Módulos modificados

### 2.1 `galpao_portico.py`

**`SPAN` (float) → `SPANS` (list de floats)**

```python
# 1 vão (retrocompatível):
configurar(span=20.0, ...)

# 2 vãos de 20m cada:
configurar(spans=[20.0, 20.0], ...)
```

**`_frame()`** — cria N+1 colunas e N cumeeiras:
- `ix["nBases"]` — lista de N+1 nós de base
- `ix["nEaves"]` — lista de N+1 nós de beiral
- `ix["nRidges"]` — lista de N nós de cumeeira
- `ix["cols"]` — lista de N+1 grupos de elementos de coluna
- `ix["rafts"]` — lista de N pares de vigas (E, D)

Para 1 vão, mantém chaves antigas (`nBaseL/R`, `nEaveL/R`, `nRidge`, `colL/R`, `rafL/R`).

**Cases de carga** — generalizados:
- `case_G`, `case_Q`: UDL em todas as vigas de todos os vãos
- `case_sismo`: E distribuído em todos os N+1 beirais
- `case_ponte`: mantido na 1ª coluna (simplificação — futuramente paramétrico por vão)

**Vento** — `_wind_unico()` (1 vão, tabelas clássicas) + `_wind_multi()` (N vãos,
Tabela 7 NBR 6123: coeficientes exatos por tramo — 1º barlavento: -0,9 a -1,1;
intermediários: -0,3; último sotavento: -0,3 a -0,4, interpolados entre 5° e 10°).

**`analyse()`** — retorna `results` com:
- `colunas` — lista de resultados por coluna (N+1)
- `vigas` — lista de resultados por vão (N)
- `coluna_pior`, `viga_pior` — piores casos

Para 1 vão, mantém `coluna` e `viga` retrocompatíveis.

### 2.2 `estabilidade_b1b2.py`

**`SEC` (dict de 2 grupos) → `SEC_COLS` (lista de N+1) + `SEC_VIGAS` (lista de 2N)**

```python
SEC_COLS[i] = {"A": ..., "I": ..., "L": EAVE}    # i = 0..N (N+1 colunas)
SEC_VIGAS[i] = {"A": ..., "I": ..., "L": ...}     # i = 0..2N-1 (2 por vão)
```

**`_analisa_combo()`** — generalizado:
- Contenções fictícias em **todos** os N+1 beirais
- `sumN` = soma das reações verticais em **todas** as N+1 bases
- `sumH` = soma das reações das contenções em todos os beirais
- `dh` = máximo drift entre todos os beirais
- B2 calculado com os totais do andar (válido para N vãos conforme Anexo D)
- Resultados por grupo: `col_0` a `col_{N}`, `viga_{i}_{E/D}`

Para 1 vão, mantém `coluna` e `viga` retrocompatíveis.

**`_apply_case()`** — generalizado: itera por todos os vãos/colunas para aplicar
UDLs de G, Q e vento.

### 2.3 `redimensionamento.py`

**Candidatos**: tripla `(col_ext, col_int, viga)` em vez de par `(col, viga)`.

```python
CANDIDATOS = [
    ("HEA200", "HEA180", "HEA180"),  # col_ext, col_int, viga
    ("HEB200", "IPE300", "HEA160"),
    ...
]
```

**`_aplica()`** — seta `gp.A_COL/I_COL` com o perfil externo, e `est.SEC_COLS[i]`
com externo para i=0/N e interno para i=1..N-1.

**`avalia()`** — itera por todas as combinações e todos os grupos (col_0..N,
viga_0_E..viga_{N-1}_D), verifica cada um pelo `check_nbr8800`, toma a pior
interação.

## 3. Ainda não implementado (para próxima sprint)

| Item | Módulo | Motivo |
|---|---|---|
| `rodar_galpao.py` multi-vão | orquestrador | Requer refatoração da extração de esforços (base, joelho, etc.) |
| `build_galpao.py` multi-vão | modelo 3D FreeCAD | Geometria multi-vão no FreeCAD |
| Vento NBR 6123 Tabela 7 completa | `vento_nbr6123.py` | ✅ Implementado via `cpe_telhado_multiplo()` — coeficientes exatos Tab.7 |
| Ponte rolante em vão específico | `galpao_portico.py` | Hoje a ponte só atua na 1ª coluna |
| Seções diferentes por coluna/viga | `redimensionamento.py` | Hoje col_ext e col_int são uniformes por tipo |
| DXF multi-vão | `dxf_vistas.py` | Vistas 2D para N vãos |

## 4. Selftest

```python
# 1 vão (retrocompatibilidade)
configurar(span=20.0, eave=6.0, ridge=6.5, bay=5.0, base_fixed=True)
analyse()  # retorna coluna+viga retrocompatíveis

# 2 vãos
configurar(spans=[20.0, 20.0], eave=6.0, ridge=6.5, bay=5.0, base_fixed=True)
analyse()  # retorna colunas[3] + vigas[2]
```

## 5. Módulos envolvidos (7 módulos, todos concluídos)

| Módulo | Função |
|---|---|
| `galpao_portico.py` | Geometria N+1 colunas, N cumeeiras; casos G/Q/W/Ponte/Sismo; vento NBR 6123 Tab.7 |
| `estabilidade_b1b2.py` | MAES B1/B2 com N+1 beirais, N+1 bases, resultados por grupo `col_0..N`, `viga_{i}_{E/D}` |
| `redimensionamento.py` | Auto-sizing com tripla (col_ext, col_int, viga) |
| `rodar_galpao.py` | Orquestrador com extração multi-base e multi-joelho |
| `build_galpao.py` | Modelo 3D FreeCAD: N+1 colunas com bases, 2N vigas, N cumeeiras, terças por vão |
| `dxf_vistas.py` | DXF: pórtico, planta e elevação para N vãos |
| `vento_nbr6123.py` | `cpe_telhado_multiplo()` — Tabela 7 NBR 6123 |

**Vento Tab.7:** 1º tramo barlavento Cpe -0,9 a -1,1 (interp. 5°-10°); tramos intermediários -0,3; último sotavento -0,3 a -0,4. Interpolação linear entre 5° e 10°.

**Teste 2 vãos 15m:** drift 22,7mm, B2 1,003, perfis HEB240/IPE360/HEB200.

**Status: ✅ COMPLETO — aguardando revisão sênior.**
