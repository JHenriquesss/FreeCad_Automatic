# Revisão — Integração da fundação profunda (ProjetoSpec + build 3D)

Conferência do sênior. **NÃO** é revisão de método — o método já está homologado
([ESTACA](REVISAO-ESTACA.md): Aoki-Velloso + Décourt + Teixeira + bloco por
bielas-e-tirantes; [BALDRAME](REVISAO-BALDRAME.md): flexão + amarração NBR 6118).
Esta revisão trata do **WIRING**: como a fundação profunda entra no contrato de
dados (`projeto_spec.py`) e como sua **geometria** é desenhada no modelo 3D
(`build_galpao.py`), sem inventar nenhum número — tudo vem do cálculo/envelope.
Fase 3 do pipeline. Criado 2026-07-10.

> **STATUS: ⏳ PENDENTE — aguarda parecer do sênior.**
> Cálculo inalterado; revisar apenas as **decisões de integração e geometria**
> marcadas com **[Q1]…[Q6]** abaixo.

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
