# Revisão — Ponte rolante + viga de rolamento

Conferência do sênior. Ação de ponte rolante pela **NBR 8800:2008** (+ NBR 8400
para classes/impacto): cargas verticais/transversais/longitudinais, viga de
rolamento e a reação empacotada para o pórtico (console/pilar).

Código: `ponte_rolante.py` (reusa `check_nbr8800`). Referência do método:
"Dimensionamento de elementos estruturais de aço e mistos" (cap. 4) + NBR 8800.
Última atualização: 2026-07-07.

> φ (impacto), frac_lateral, frac_long = **fabricante / NBR 8400 (A CONFIRMAR)** —
> não inventados; entram flagados.

---

## 1. Cargas de roda (Rmax/Rmin)

Ponte encostada, trole na aproximação mínima `a` de um trilho:

```python
def cargas_de_roda(Q, peso_ponte, peso_trole, vao_ponte, aprox_min, n_rodas_lado):
    S = vao_ponte
    movel = Q + peso_trole
    R_trilho_max = peso_ponte / 2.0 + movel * (S - aprox_min) / S
    R_trilho_min = peso_ponte / 2.0 + movel * aprox_min / S
    return (R_trilho_max / n_rodas_lado, R_trilho_min / n_rodas_lado,
            R_trilho_max, R_trilho_min)
```

Vertical majorado por **φ** (impacto, 1,10 leve … 1,25 pesada/siderúrgica).

---

## 2. Forças horizontais

```python
def forcas_horizontais(Q, peso_trole, R_roda_max, n_rodas_lado, frac_lateral, frac_long):
    n_total = 2 * n_rodas_lado
    H_transv_roda = frac_lateral * (Q + peso_trole) / n_total   # surto (aceleracao trole)
    H_long_trilho = frac_long * R_roda_max * n_rodas_lado        # frenagem (rodas motoras)
    return H_transv_roda, H_long_trilho
```

---

## 3. Viga de rolamento — momento por carga móvel

```python
def _m_max_movel(P, d, L):
    # Momento maximo absoluto de 2 cargas iguais P espacadas d, vao L (biapoiada)
    if d < L:
        m2 = (2.0 * P / L) * (L / 2.0 - d / 4.0) ** 2
    else:
        m2 = 0.0
    return max(m2, P * L / 4.0)
```

Flexão vertical `Msdx = _m_max_movel(P, d, L)`; lateral do surto
`Msdy = _m_max_movel(Ht, d, L)`. **Surto atua no topo do trilho → só a mesa
superior resiste** (~metade das props):

```python
Wy_top = sec.get("Wy_top", Wy / 2.0)     # override p/ secao MONOSSIMETRICA
Zy_top = sec.get("Zy_top", Zy / 2.0)     # (mesa sup com U/chapa) - parecer 4
Mrdy = min(Zy_top, 1.5 * Wy_top) * fy / GA1
inter = Msdx / Mrdx + Msdy / Mrdy        # Mrdx pelo Anexo G (check)
```

---

## 4. ELS (flecha) e fadiga

```python
def limite_flecha_vertical(cap_kN, siderurgica):
    if siderurgica and cap_kN >= 200.0: return 1000.0   # L/1000
    if cap_kN >= 200.0: return 800.0                     # L/800
    return 600.0                                          # L/600
```

Flecha com carga **sem impacto** (`Pk = P/φ`). Horizontal L/400 (L/600
siderúrgica). Coluna: deslocamento no nível da viga ≤ Hvr/400. **Fadiga**
(Anexo K) sinalizada para pontes pesadas — não fabrica categoria de detalhe.

---

## 5. Pontos de conferência (FLAGS)

1. **φ, frac_lateral (~0,10), frac_long (~0,10)** — fabricante/NBR 8400.
2. Frenagem nas **rodas motoras**: reduzir frac_long por n_motoras/n_rodas.
3. Surto só na mesa superior (metade das props) — Fakury 4.4.2.
4. Fadiga: Anexo K sinalizado, não automatizado.

---

## 6. Onde revisar

| Assunto | Função | Item |
|---|---|---|
| Cargas de roda | `cargas_de_roda` | NBR 8800 cap. cargas |
| Horizontais | `forcas_horizontais` | NBR 8800 / 8400 |
| Momento móvel | `_m_max_movel` | mecânica |
| Viga rolamento | `verifica_viga_rolamento` | Anexo G + biaxial |
| Flecha | `limite_flecha_vertical` | ELS NBR 8800 |

---

## 7. Resposta ao parecer do sênior (rodada 1 — 2026-07-07)

Parecer **sem erro apontado** — só notas de atenção. Auditoria independente
confrontou os pontos duros com o PDF da NBR 8800 (Anexo B.7 e Anexo C Tabela C.1)
e conferiu as fórmulas na mão.

### 7.1 — Confirmações verificadas contra o PDF

- **Cargas de roda** (estática): `R_max = P_ponte/2 + (Q+trole)·(S−a)/S`, trole na
  aproximação mínima → reação máxima no trilho próximo. Equilíbrio exato. ✅
- **Flecha 2 rodas** (conferida na mão): `δ = P·a·(3L²−4a²)/(24EI)` com
  `a=(L−d)/2` → `P(L−d)(2L²+2Ld−d²)/(48EI)`, exatamente o do código. Caso
  d→0 recai em 2P no meio = `PL³/24EI`. ✅
- **Momento móvel** (Barré): `Mmax=(2P/L)(L/2−d/4)²`; troca para `PL/4` (uma roda)
  quando `d > (2−√2)L ≈ 0,586L` — limiar confere. ✅
- **Limites de flecha** (Tabela C.1, pág. lida do PDF): vertical L/600 (<200 kN),
  **L/800** (≥200), **L/1000** (siderúrgica); horizontal L/400 (L/600 sider., ≤50 mm
  sider., diferencial entre pilares ≤15 mm). `limite_flecha_vertical` = **exato**. ✅
- **B.7.2 b)** longitudinal (frenagem): "10 % das cargas verticais máximas das
  rodas **não majoradas pelo impacto**, no topo do trilho de cada lado" — o código
  usa `R_roda_max` (SEM φ) × `n_rodas_lado` → **por trilho**, correto. ✅
- **B.7.2 a)** transversal (surto): aplicada no topo do trilho, distribuída entre
  os lados (∝ rigidez); código `frac·(Q+trole)/n_total`, por lado = metade. ✅
- **B.7.3.4** fadiga: 1 ponte, cargas com impacto + 50 % das horizontais →
  sinalizado Anexo K (não fabrica categoria de detalhe). ✅
- Unidades: transversal **por roda**, longitudinal **por trilho** — já documentado
  no relatório (`kN/roda` vs `kN/trilho`) e reempacotado coerente em
  `reacao_no_portico`. Nota do parecer atendida. ✅

### 7.2 — Seção monossimétrica: `Wy/2` — MELHORIA APLICADA

**Ponto real do parecer (§4).** O `Wy_top = Wy/2` só vale para **I bissimétrico**
(inércia lateral ~toda nas mesas). Vigas de rolamento de média/alta capacidade
usam seção **monossimétrica** (perfil I com U/chapa soldada na mesa superior para
ganhar inércia lateral) — aí `Wy_sup ≠ Wy/2` e o `/2` seria **incorreto**. Fix:
aceitar override direto do banzo superior:
```python
Wy_top = sec.get("Wy_top", Wy / 2.0)     # fallback = metade (bissimetrico)
Zy_top = sec.get("Zy_top", Zy / 2.0)
```
Mesmo padrão do projeto (não inventa geometria; se o perfil real é assimétrico, o
eng. informa `Wy_top`/`Zy_top` do banzo). Não-regressivo: sem override, comportamento
idêntico (VS500 do selftest inalterado).

### 7.3 — Não-regressão

Selftest `ponte_rolante` OK. Ponte 100 kN, viga VS500 bay 5 m: Msdx 91,4 / Msdy 3,6;
interação 0,28+0,11=0,39 OK; flecha 2,5 mm (L/600) OK; reação pórtico R=132,9 kN,
M_exc 39,9 kN·m. Aguarda re-revisão.

---

## 8. Homologação (rodada 2 — 2026-07-07)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 8800:2008 / NBR 8400.**

Sênior homologou. Confirmado: (1) override `Wy_top`/`Zy_top` para seção
monossimétrica (I + U na mesa superior) com fallback `Wy/2` retrocompatível —
evita superdimensionamento sem perder o conservadorismo de Fakury; (2) fadiga
como FLAG (Anexo K depende da **categoria de detalhe** de fabricação — enrijecedores,
furação, tipo de solda do trilho — fora do alcance das forças macroscópicas do
modelo); (3) dedução da flecha `δ=Pa(3L²−4a²)/24EI → P(L−d)(2L²+2Ld−d²)/48EI` com
teste-limite `d→0 ⇒ 2P no centro`; (4) indexação kN/roda × kN/trilho isolada,
evitando falha de transferência viga→console.

Módulo `ponte_rolante.py` liberado para o orquestrador.

---

## 9. Fadiga da viga de rolamento (NBR 8800 Anexo K) — feature adicionada 2026-07-07

> **STATUS: 🆕 PENDENTE SÊNIOR** — feature nova (pós-homologação r2). A conferir:
> `σ_SR = Msdx/Wx` (K.3), `σ_adm = (327·Cf/N)^0,333 ≥ σ_TH` (K.4), a **Tabela K.1**
> (valores lidos do PDF), a carga de fadiga B.7.3.4 e a categoria/N como INPUT.

Fecha a lacuna: antes só um FLAG "a verificar"; agora **calcula** a faixa de tensões
e compara com a admissível. Fórmula extraída do PDF (não de memória):

- **K.4 a)** — faixa admissível `σ_SR = (327·C_f / N)^0,333 ≥ σ_TH` [MPa].
- **Tabela K.1** (lida do PDF): `(C_f×10⁸, σ_TH)` — A (250; 165), **B (120; 110)**,
  B' (61; 83), **C (44; 69)**, D (22; 48), E (11; 31), E' (3,9; 18).
- **K.3** — faixa de tensões por análise elástica: `σ_SR,Sd = M_fad / W_x`.

**Carga de fadiga (B.7.3.4):** 1 ponte com impacto. Como `P = φ·R_roda,max`
(característico com impacto, **sem** γ_f) e a carga móvel **zera** quando a ponte se
afasta, a faixa de variação ≈ o próprio momento da ponte: `M_fad = Msdx`. Logo
`σ_SR,Sd = Msdx/W_x`.

**Parametrização (Ask, Do Not Invent):** a **categoria do detalhe** (`cat_fadiga`,
default **B** = metal-base junto à solda longitudinal contínua mesa-alma) e o
**número de ciclos** `N` (`n_ciclos`, do regime — NBR 8400) são INPUT. O código não
fabrica a categoria: enrijecedores/ligações transversais soldadas são **C**, e o
detalhe do trilho pode ser pior — o engenheiro confirma. Entra no `OK` da viga.

Ex. (ponte 100 kN, VS500, bay 5 m, cat B, N=2×10⁶): `σ_SR=57 MPa ≤ σ_adm=125 MPa`
(`u=0,46`) → OK. Selftest confere a fórmula K.4 (categorias A/C/E/E'), o piso
`σ_TH` (muitos ciclos) e `σ_SR=Msdx/Wx`. Não-regressivo: Msdx/interação/flecha do
VS500 inalterados.

> **Limite:** faixa de tensões da **flexão vertical** (dominante). A parcela lateral
> (surto no topo do trilho) e a combinação biaxial (K.3.3) ficam como refinamento;
> a categoria real do detalhe de fabricação continua sendo a decisão do projetista.
