# Revisão — Integração da fundação profunda (ProjetoSpec + build 3D)

Conferência do sênior. **NÃO** é revisão de método — o método já está homologado
([ESTACA](REVISAO-ESTACA.md): Aoki-Velloso + Décourt + Teixeira + bloco por
bielas-e-tirantes; [BALDRAME](REVISAO-BALDRAME.md): flexão + amarração NBR 6118).
Esta revisão trata do **WIRING**: como a fundação profunda entra no contrato de
dados (`projeto_spec.py`) e como sua **geometria** é desenhada no modelo 3D
(`build_galpao.py`), sem inventar nenhum número — tudo vem do cálculo/envelope.
Fase 3 do pipeline. Criado 2026-07-10.

> **STATUS: ✅ HOMOLOGADO** (2026-07-11) — parecer 1: Q2–Q6 corrigidos. Parecer 2:
> sênior validou Q2/Q4/Q5/Q6 (matemática canônica confirmada) e condicionou a
> homologação a **dois ajustes normativos**, ambos aplicados (§7):
> **(Q1) FS default 3,0** com gate no `validar()` que bloqueia FS<3,0 sem
> `fundacao.estaca.prova_de_carga=True` (NBR 6122); **(Q3b) bloco rígido exige
> tan θ ≥ 1,0** (θ≥45°), não 0,57. Build revalidado (estaca, 0 interferências).

## PARECER SÊNIOR 1 — respostas Q1…Q6 (§6 detalha)

| Q | Ponto do sênior | Decisão |
|---|---|---|
| Q1 | FS=2,0 viola 6122; exige 3,0 s/ prova de carga | **DIVERGE** — mantém 2,0 (semi-empírico Aoki-Velloso, Cintra & Aoki 2010 / Veloso & Lopes 2012, refs do método). FLAG p/ sênior; PDF 6122 escaneado, não citável. `D`/`L` seguem default A CONFIRMAR. |
| Q2 | Falta momento na distribuição das estacas | **ATENDE** — `carga_estaca_grupo` (flexo-compressão, Navier); wire de `M_base` do envelope. Bloco 1–2 estacas não resiste (S=0) → momento vai p/ tirantes (Q5); grupo 2×2 verifica N_max. |
| Q3 | coroa e distância à face | **ATENDE** — `coroa = max(150 mm, D/2)`. |
| Q3b | h=1,2·D gera bloco flexível | **ATENDE** — `altura_bloco_rigido`: h derivado do ângulo da biela (tan θ alvo 1,0 ∈[0,57;2]), não constante. |
| Q4 | pedestal fixo 500 mm | **ATENDE (param)** — build lê `ped` do modelo (cota de arrasamento); default 500 A CONFIRMAR. Gate obrigatório = FLAG. |
| Q5 | falta travamento transversal (1–2 estacas) | **ATENDE** — baldrame nas 2 direções quando n≤2 (NBR 6122); dispensado p/ malha 2×2+. |
| Q6 | clash concreto×concreto ok, evitar dupla contagem | **ATENDE** — tramos de baldrame de face a face do pedestal (vão livre) → sem sobreposição no take-off. |

## 6. Correções aplicadas (2026-07-11)

**Cálculo (`estaca_profunda.py`):**
- `carga_estaca_grupo(N, offsets, Mx, My)` — `N_i = N/n ± Mx·yi/Σyi² ± My·xi/Σxi²`;
  marca `traciona_por_momento` e `resiste_no_grupo`.
- `offsets_grupo(n, esp)` — malha igual à do build (1 central / 2 linha-X / 4 malha).
- `altura_bloco_rigido(esp, a_pilar, …, tan_alvo=1,0)` — `d=tan·braço`, `h=d+cob+emb`;
  default de altura no `verifica_estaca` (bloco rígido por construção).
- `verifica_estaca`: com `Mx/My` monta offsets e reporta `grupo_momento`
  (util_max, OK). Só é resistido no grupo quando há braço nas 2 direções (n=4);
  em 1–2 estacas o momento é anotado como carga dos tirantes de baldrame.

**Wiring (`rodar_galpao.py`):** `M_base = max|M|` do envelope da base → `ecfg["Mx"]`.

**Build (`build_galpao.py`):** `coroa=max(150,D/2)`; `ped` do modelo (default 500);
baldrame longitudinal **e transversal** (n≤2) com vão livre `tramo−pdim`.

## 7. PARECER SÊNIOR 2 — ajustes finais (2026-07-11)

Sênior validou Q2 (Navier), Q4, Q5 e Q6. Dois ajustes p/ homologar:

**Q1 — FS (resolvido por gate, sem adjudicar norma escaneada):** em vez de fixar
2,0 ou 3,0 unilateralmente, encodei a **condicional que sênior E literatura
concordam**: FS=2,0 exige prova de carga. Implementado:
- `estaca_profunda.FS_GLOBAL = 3,0` e mapper `to_map_rodar_params` default 3,0;
- `projeto_spec.validar()`: `tipo==estaca` com `FS<3,0` e sem
  `fundacao.estaca.prova_de_carga==True` → **BLOQUEIA** com mensagem citando 6122;
- campo novo `fundacao.estaca.prova_de_carga` (bool);
- testes: `test_fs_menor_que_3_sem_prova_bloqueia`, `test_fs_2_com_prova_de_carga_valida`.
Assim o default é seguro (3,0) e 2,0 só sai com prova de carga — atende o sênior
e a NBR, sem eu ter que citar cláusula de PDF ilegível.

**Q3b — bloco rígido tan θ ≥ 1,0 (θ≥45°):** `altura_bloco_rigido` agora com piso
`tan_alvo=1,0` (era 0,57); `bloco_coroamento` classifica `rigido = tan θ ≥ 1,0`
e `ok_angulo = 1,0 ≤ tan θ ≤ 2,0`. Blocos com tan θ < 1,0 caem no caminho
**flexível** (verifica punção, conservador) em vez de serem tratados como rígidos
sem armadura de cisalhamento. Faixa 35°–45° (fissuração/fadiga da biela) fica
FLAG — o projeto deve usar tan θ ≥ 1,0.

---

## 1. Gate de decisão — `fundacao.tipo` (sapata | estaca)

`projeto_spec.novo()` agora nasce com `fundacao.tipo = __PENDENTE__` →
**bloqueia** cálculo e desenho até o engenheiro decidir rasa (sapata) ou profunda
(estaca). É **exclusivo**: um pé recebe sapata **ou** estaca, nunca os dois
(guard `mne-2` no build e no `to_build_kwargs`).

- `fundacao.tipo == "estaca"` torna **requeridos** (via `validar()`):
  - `fundacao.estaca.perfil_spt` — perfil da sondagem (camadas `{tipo, N, dz}`);
  - `fundacao.estaca.tipo_estaca` — pré-moldada / metálica / escavada / …
- Estes **não têm default** (são dado de sítio — regra *Ask, Do Not Invent*).
  `D`, `L`, `FS` têm default (A CONFIRMAR): D=0,30 m; L=10,0 m; FS=2,0.

**[Q1]** Concorda que `perfil_spt` e `tipo_estaca` devem **bloquear** (sem default),
e que `D`/`L`/`FS` podem ter default "A CONFIRMAR" preenchido pelo engenheiro?

---

## 2. Solicitações do modelo → cálculo (envelope)

No `rodar_galpao`, a fundação profunda consome as **reações da base do pórtico**
(mesmo envelope da sapata):

| Grandeza | Origem | Uso |
|---|---|---|
| `N_pilar` | **maior compressão** vertical na base (envelope) | capacidade / nº de estacas / biela do bloco |
| `N_uplift` | **maior tração** (reação negativa) na base | tração da estaca (atrito lateral, peso do bloco alivia) |
| `V_base_max` | max\|V\| horizontal na base | `N_amarracao` da viga de baldrame |

**[Q2]** A estaca é dimensionada para a **maior compressão** e verificada à
**maior tração** do envelope (incl. combinação excepcional sísmica, que já entra no
envelope da base). Confirma que é essa a envoltória correta para a fundação
profunda (e não uma combinação por caso)?

---

## 3. Geometria desenhada no 3D (`build_galpao.py`)

Todo número da geometria vem do cálculo — **nada inventado** (guard `mne-1`):

- **Estacas** — `n` = `n_estacas` (teto de N_pilar/P_adm), diâmetro `D` e
  comprimento/embutimento `L` do `verifica_estaca`. Cilindros descendo da face
  inferior do bloco. Disposição em planta pelo `_estaca_offsets(n, esp)`:
  `n=1` central · `n=2` linha · `n=4` malha 2×2 · demais em fileira, passo
  `espacamento` (default 3·D).
- **Bloco de coroamento** — altura `h` do `bloco_coroamento` (= `max(0,4; 1,2·D)`
  quando o modelo de biela não se aplica); **planta = envelope do grupo + coroa**
  de 150 mm em cada lado (`Bx`, `Ly` calculados da malha de estacas).
- **Pedestal** — 500 mm do bloco até a face inferior da placa de base (liga o
  pilar metálico ao bloco).
- **Viga de baldrame** — seção `b × h` do `verifica_baldrame`, uma por linha de
  coluna, ligando fundações de pórticos adjacentes (vão = baia), topo na cota da
  face inferior da placa de base.

**[Q3]** A **planta do bloco** é geométrica (envelope das estacas + coroa de
150 mm), não normativa — a armadura/altura vêm do cálculo. Aceita a coroa de
150 mm como praxe, ou prefere outro valor / vínculo à norma?

**[Q4]** O **pedestal de 500 mm** é fixo no build (igual ao da sapata). Deve virar
parâmetro do gate (altura de arrasamento / cota de bloco da sondagem)?

**[Q5]** A **viga de baldrame** foi desenhada ao longo das **baias** (entre
pórticos), na direção do comprimento. Confirma essa direção de amarração (e não
transversal, no plano do pórtico)?

---

## 4. Auditoria do modelo (não-regressão)

- A fundação de concreto é **monolítica**: estaca+bloco+baldrame+pedestal se
  interpenetram de propósito → o `checa_interferencia` isenta pares
  **concreto×concreto** de fundação (`_e_fundacao`). Aço×concreto continua sendo
  verificado (um bloco furando um pilar **acusaria**).
- Take-off: estaca/bloco/baldrame entram no **subtotal de concreto** (ρ=2500 kg/m³),
  fora da tonelagem de aço.
- Cobertura das pranchas: os novos sólidos entram na **planta de fundações**
  (`_pr_fundacoes`), então o guard anti-silhueta não acusa peça órfã.
- **Referência 20×10 com sapata inalterada** (sapata continua sendo o caminho
  default; nenhum sólido de estaca aparece) — prova de não-regressão.

**[Q6]** Aceita a hipótese de **bloco monolítico** para dispensar o clash interno
concreto×concreto de fundação, mantendo o clash aço×concreto?

---

## 5. Resíduos / FLAGs (não bloqueiam — trabalho futuro)

- Viga de **equilíbrio de divisa** (estaca excêntrica com bloco fora do eixo) —
  fora do escopo desta fase.
- Armadura da estaca (fuste) e detalhamento do bloco no 2D (ferragem) — o 2D
  desenha a **planta** de fundações; o detalhamento executivo de ferragem é etapa
  posterior.
- Espaçamento mínimo entre estacas (2,5–3·D) hoje é o default `3·D`; se a sondagem
  exigir malha mais apertada/aberta, é input do gate.

---

*Método: já homologado em ESTACA/BALDRAME. Esta doc cobre só a integração
spec+3D. Evidência: `smoke_executivo` caso `estaca` (calc+3D+pranchas+PDF verde);
`tests/test_fase3_fundacao_profunda.py` (13 fast + 1 build).*
