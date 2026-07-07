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
    lim_flecha = gp.EAVE / 300.0            # H/300 galpao (NBR 8800 Tab. C.1)
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
- **ELS**: flecha lateral ≤ **H/300** — deslocamento horizontal do topo dos pilares
  de galpão (NBR 8800:2008 **Tabela C.1**, "Galpões em geral e edifícios de um
  pavimento"; limite duro, sem nota). Ver §5.1 (era H/150, corrigido).

Escada `CANDIDATOS` (mais leve → mais pesado, peso ≈ ΣA): HEA200/HEA180 →
HEB300/IPE550. `melhor()` adota o **primeiro que passa** e deixa o estado global
no perfil adotado.

---

## 3. Pontos de conferência (FLAGS)

1. **Peso ≈ ΣA·L** (proxy do consumo de aço, ponderado pelos comprimentos) — só
   informa o memorial; a **seleção é por ordem da escada** (primeiro que passa),
   que é monótona nas duas componentes (§5.2).
2. **H/300** para flecha lateral do topo do pilar (Tabela C.1) — **resolvido**
   (era H/150; §5.1).
3. **Lb** fixos (coluna 2,0 m; viga 1,67 m) por default — as terças travam a mesa
   externa; a **mesa interna comprimida no nó** só está travada se houver
   **mão-francesa** nesses espaçamentos. Premissa de wiring, ver §5.4.
4. **K = 1** com 2ª ordem (4.9.6.2) — correto (§5.3).
5. Base **engastada** assumida no redim (fixed=True).

---

## 4. Onde revisar

| Assunto | Função | Referência |
|---|---|---|
| Avaliação por candidato | `avalia` | módulos 2, 3 |
| Escolha do mais leve | `melhor` | — |
| Limite de flecha | `LIM_FLECHA` | NBR 8800 Tabela C.1 |
| Escada de perfis | `CANDIDATOS` | — |

---

## 5. Resposta ao parecer do sênior (rodada 1 — 2026-07-07)

Motor de 2ª ordem e cadeia de orquestração aprovados. Um **defeito real de ELS**
(H/150) corrigido, um proxy tornado honesto, e duas confirmações. Ponto duro (o
limite de flecha) conferido **contra o PDF da NBR 8800 Tabela C.1** — não de memória.

### 5.1 — `H/150` → `H/300` — DEFEITO CONFIRMADO, CORRIGIDO

O parecer alega que H/150 é leniente demais para galpão. **Verificado no PDF**,
Tabela C.1, texto literal:

> "Galpões em geral e edifícios de um pavimento: **Deslocamento horizontal do topo
> dos pilares em relação à base → H/300**"

Limite **duro**, sem nota de rodapé de exceção. (A linha de H/400 é do **nível da
viga de rolamento**, não do topo do pilar.) O código usava `gp.EAVE / 150.0` —
**2× tolerante demais**. Corrigido para `gp.EAVE / 300.0` em todas as ocorrências
(constante `LIM_FLECHA`, `avalia`, `_tabela`).

**Impacto real:** com H/150 (lim 40 mm, EAVE 6 m) o par mais leve HEA200/HEA180
passava com flecha 30,8 mm (≈ H/195) — estrutura esbelta demais, como o parecer
alertou (rasgo nos furos das telhas, fadiga dos costureiros). Com **H/300** (20 mm)
esse par **reprova** e o adotado sobe para **HEB200/IPE300** (flecha 16,3 mm ≤ 20;
interações 0,42/0,43). O envelope de ELU nunca esteve em jogo (0,67/0,87 < 1); era
puramente rigidez lateral, que o limite errado mascarava.

### 5.2 — Peso ≈ ΣA → ΣA·L — proxy tornado honesto (sem efeito na seleção)

O parecer nota (com razão teórica) que `ΣA` ignora os comprimentos de coluna e
viga. Dois pontos:

1. A **seleção** em `melhor()` é por **ordem da escada** (primeiro que passa),
   **não** por `_peso_rel`. A escada `CANDIDATOS` é monótona nas **duas**
   componentes (HEA200<HEB200<HEB220…​ e HEA180<IPE300<IPE330…), então qualquer
   soma ponderada positiva preserva a ordem → `ΣA` e `ΣA·L` dão a **mesma**
   ordenação. **Sem impacto na escolha.**
2. Ainda assim, `_peso_rel` foi tornado honesto: `2·(A_col·L_col + A_raf·L_raf)`
   (usa os comprimentos reais de `est.SEC`), para o valor informado no memorial
   não induzir a erro se alguém inserir um candidato fora de ordem.

### 5.3 — K = 1 com 2ª ordem — CONFIRMADO

MAES (rigidez 0,8 + nocional) captura P-Δ/P-δ; a NBR 8800 **4.9.6.2** dispensa o K
por nomograma quando a 2ª ordem é feita na análise → `Kx=Ky=1,0` na verificação de
`Nc,Rd` é correto. ✅

### 5.4 — Lb fixos e a mesa interna do nó — FLAG reforçado

O parecer alerta (com razão) que `lb_raf=1,67`/`lb_col=2,0` pressupõem travamento
das **duas mesas**. No nó pórtico o momento é negativo → **mesa interna comprimida**,
que as terças (na mesa externa) **não** travam. Esses Lb só se sustentam se houver
**mão-francesa** ligando a mesa interna às terças nesses espaçamentos — que é
exatamente o que o módulo [mão-francesa](REVISAO-MAO-FRANCESA.md) dimensiona
(`Lb_max` pela interação 5.5.1.2). Registrado como premissa de wiring (FLAG 3):
o redim assume Lb travado; o plano de mão-francesa deve realizar esses Lb. Sem
alteração de código (é decisão de projeto, não erro de fórmula).

### 5.5 — Não-regressão

Módulo roda a escada completa OK. Sob H/300 o adotado passa a ser HEB200/IPE300
(antes HEA200/HEA180 sob o limite incorreto). `_peso_rel` não altera a seleção.

---

## 6. Homologação (rodada 2 — 2026-07-07)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 8800:2008.**

Sênior homologou os 4 pontos: (1) **H/300** da Tabela C.1 corrige a rigidez —
constatação de que o galpão de alma cheia é **governado por ELS** (interações
0,42/0,43 ≪ 1), clássico; (2) **K=1** referendado pelo MAES (4.9.6.2, rigidez 0,8
+ nocional); (3) `_peso_rel = 2·(A_col·L_col + A_raf·L_raf)` escala com o volume
real, seleção *first-fit* imune a mínimo local dada a escada monótona; (4) **Lb
fixo** aceito como **contrato de software** — o redim exige "passa se travada a
cada 1,67 m", a [mão-francesa](REVISAO-MAO-FRANCESA.md) assume o dever de entregar
essa contenção da mesa interna.

### 6.1 — Pergunta de fecho: transferência do momento de base engastada

O sênior pergunta como o M da base engastada (`fixed=True`) chega à fundação e aos
chumbadores. Rastreado no código (`rodar_galpao.py`):

- `_casos_base_envelope()` lê a **reação do nó de base direto do solve de 2ª ordem**,
  por combinação ELU: `N=R[3·nBaseL+1]`, `V=R[3·nBaseL]`, `M=R[3·nBaseL+2]` — o
  mesmo `R` amplificado (MAES) que o redim usa. **Sem simplificação** do M.
- Alimenta a **fundação** via `fs.dimensiona_sapata_env(sap, casos_base)` — o M
  engastado governa tombamento/flexão/compressão diagonal por combinação
  (envelope, ver [REVISAO-FUNDACAO.md](REVISAO-FUNDACAO.md) §4).
- A **mesma** reação alimenta `base_chumbador` (placa + chumbadores), caso "Base
  engastada — M=…" (`rodar_galpao.py` ~L269).

Os três consumidores (redim, fundação, base) leem a **mesma** reação da **mesma**
análise → consistência garantida; o M elevado do engaste não é perdido nem
recalculado. Fora do escopo deste módulo (é orquestração), registrado para
rastreabilidade.

Módulo `redimensionamento.py` liberado. **1 correção de código** (flecha
H/150→H/300) + `_peso_rel` ponderado por comprimento.
