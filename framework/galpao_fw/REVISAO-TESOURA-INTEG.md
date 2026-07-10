# Revisão — Pórtico treliçado (tesoura): cálculo novo + integração

Conferência do sênior. O `tesoura.py` já homologado era **só geração de geometria**
(nós + barras, isostática b+r=2j — [TESOURA](REVISAO-TESOURA.md)). Esta fase
**cria o cálculo de esforços** (solver + verificação) e integra ao pipeline
(spec + rodar + 3D). Fase 6.c. Criado 2026-07-10.

> **STATUS: ⏳ PENDENTE — aguarda parecer do sênior.**
> Método NOVO (solver + verificação de barras) — revisar **[Q1]…[Q5]**.

---

## 1. Solver de esforços — método dos nós (NOVO)

`tesoura.resolve_trelica(t, P_nos)`: treliça plana **isostática**, esforços axiais
pelo **equilíbrio nodal** (método dos nós). Sistema linear quadrado
`2j × (b+3)` (b barras + 3 reações; isostático ⇒ b+3=2j), resolvido por
`numpy.linalg.solve`.

- Apoios: nó 0 = pino (Rx, Ry); nó `n_paineis` = rolete (Ry). Treliça **biapoiada**
  no topo dos pilares.
- Convenção: **N>0 = tração**. Sob gravidade, o banzo **inferior traciona**, o
  **superior comprime** (verificado em teste).
- **Equilíbrio global conferido** (teste): ΣRv = Σcargas; ΣRx = 0.

**[Q1]** Aceita o modelo **biapoiado isostático** (treliça simplesmente apoiada nos
pilares, sem continuidade de pórtico)? É o modelo usual de tesoura sobre pilares;
o pilar é verificado à parte com a reação da treliça.

**[Q2]** As barras são modeladas como **rótulas ideais** (só força axial), sem
momento de nó. Confirma (padrão para treliça isostática)?

---

## 2. Verificação das barras (reusa NBR 8800)

`verifica_tesoura(cfg)`: para cada barra, com o esforço N do solver:
- **Tração** (N>0): escoamento da seção bruta `Nt,Rd = A·fy/γa1`.
- **Compressão** (N<0): flambagem `Nc,Rd = χ·Q·A·fy/γa1`, com `χ` de
  `check_nbr8800.chi_compressao(λ0)` (λ0 do índice de esbeltez KL/r, K=1) e `Q` de
  `fator_Q` (flambagem local). **Reusa os primitivos homologados** — sem fórmula nova.
- Combinações: **gravidade** `1,4·w_grav` e **vento** `1,4·w_vento + 0,9·(−w_grav)`
  (alívio/uplift). Pega a pior utilização por barra.

**[Q3]** `w_grav = (G+Q+peso próprio)·bay` (carga de cobertura × largura tributária).
A **sucção de vento** `w_vento` é **INPUT** (gate `trelica.w_vento_kN_m`; default 0
com FLAG "informar sucção") — não inventada. Confirma deixar o vento como input do
projeto (a sucção vem do módulo de vento; hoje não é auto-acoplada à treliça)?

**[Q4]** Perfis de banzo/diagonal são **dado de projeto** (gate; I duplamente
simétrico). O sizing verifica a utilização; não auto-dimensiona o perfil. OK para
anteprojeto?

---

## 3. Integração (spec + 3D)

- **Gate:** `estrutura.tipo_portico="tesoura"` + `estrutura.trelica`
  {h, n_paineis, tipo (warren/pratt), perfil_banzo, perfil_diagonal}. Inválido bloqueia.
- **3D:** `build_galpao._desenha_tesoura` desenha as barras (banzos + diagonais/
  montantes) como cilindros no plano do pórtico, biapoiadas no topo dos pilares
  (banzo superior parabólico até EAVE_H+h). **Sem joelho/cumeeira** (treliça
  rotulada, não pórtico de momento). Geometria da treliça **replicada numpy-free**
  no build (build é self-contained).
- **Memorial:** `gate6-tesoura.txt` + METODOS `3c`.

**[Q5]** As **terças/telha** hoje seguem o plano de cobertura pela inclinação
(`slope`), independente do banzo superior parabólico da treliça — pode haver
diferença entre o plano da telha e o apex da treliça. Sinalizo como FLAG de
compatibilização geométrica (terças sobre os nós do banzo superior) para o
executivo. Confirma que fica para o detalhamento?

---

## 4. Não-regressão / evidência

- `tesoura._selftest` (geometria isostática) + solver (equilíbrio global) + 
  `verifica_tesoura` verdes.
- `numpy` importado **sob demanda** (só no solver) → `gera_trelica` importável no
  build sem numpy.
- `smoke_executivo`: 7º caso `tesoura` (calc+3D barras+pranchas); prismático/
  alma_variável inalterados.
- `tests/test_fase6c_tesoura.py` (7 fast + 1 build).

---

*Solver + verificação são MÉTODO NOVO (a geometria `gera_trelica` já era
homologada). A auto-integração da sucção de vento e a compatibilização
terça↔banzo são FLAGs [Q3]/[Q5].*
