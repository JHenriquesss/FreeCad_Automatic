# BACKLOG — pós-G76 (2026-09-09)

Estado: lote **G74–G76 commitado** (`33e3af8`, branch `feat/tipologias-e-verticais-de-projeto`).
Verificação do lote: 44 focais (`g74 + g75 + g76 + alcancabilidade`) + 249 vizinhos tocados
(telhado g66/g71/g72/g73, alvenaria g61/g62/g67, casa g58/g42/g13/g68, edifício, g11) =
**293 verdes, zero vermelhos**. Suíte inteira em processo único, medida no G75:
**3381 passed em 6687 s**.

Cada item abaixo tem **endereço** e **como foi medido**. O que não foi medido está dito
como não medido — nenhum item aqui é palpite sobre o que "provavelmente" falta.

---

## 0. Normas ausentes do acervo — **nenhuma** (medido em 2026-09-09)

Este bloco abre o backlog por regra: as normas que faltam são providenciadas fora do chat
e a lista se perde no scroll. **Desta vez a lista está vazia**, e isso é resultado de
medição, não de silêncio.

**Método.** Cruzamento por script entre (a) identificadores `NBR` extraídos de
`fontes/catalogo.csv` (148 linhas, 53 normas distintas) e (b) identificadores `NBR`
citados no código de `framework/galpao_fw/**/*.py` (57 distintos), excluído `.venv`.

**Resultado bruto:** 2 candidatas. Ambas triadas e **descartadas por medição**:

| Candidata | Veredito | Evidência |
|---|---|---|
| NBR ISO/CIE 8995-1 (13 menções) | **Falso positivo do regex** — está no acervo | `05_ELETRICA/ELETRICA__NBR__NBR-ISO-CIE-8995-1-2013__iluminacao-ambientes-trabalho-interior.pdf`; o padrão `NBR-?\d+` não casava o infixo `ISO-CIE` |
| NBR 7229 / NBR 13969 (10 menções) | **Superada, citada só como nota histórica** | `esgoto_reuso.py:6,9,26,39,56,63,131` diz "sucede/cancela NBR 7229:1993 e NBR 13969:1997"; a fonte de cálculo é a **NBR 17076:2024** (Anexo A.2), presente em `08_ESGOTO_PLUVIAL_REUSO/`. Há guarda: `tests/test_normas_catalogo.py:95` — *"NBR 7229/13969/13792 como fonte reprova; nota de procedência não"* (2 passed) |

**Conclusão:** o ciclo aberto em 2026-09-07 (14 PDFs providenciados no mesmo dia — 9062,
7190 completa, 14880, blocos/argamassas 6136/15270/14974/13281, IEC 60617) fechou de fato.
Nenhum módulo está hoje bloqueado por ausência de fonte no acervo.

**A única exceção não é norma, é caso externo** — ver item 5 (T44, fundação).

**Atualização pendente de documento, não de aquisição:** `fontes/fontes-faltantes.md`
ainda diz *"Destrava o telhado da casa, hoje `telhado_madeira: not_available`"*. O telhado
foi implementado em G66–G74. A linha está obsoleta e induz ao erro de recaçar fonte.

---

## 1. G77 — as 28 folhas que continuam sem guarda nem pixel  *(recomendado como próximo)*

**O que já existe.** O G76 construiu a lente e a validou nos dois sentidos:
`desenho_svg_base.confere_folha_svg` — parse XML (nunca substring), `viewBox == width×height`
com origem `0 0`, e maior `x`/`y` desenhado (`rect`/`line`/`circle`/`ellipse`/`text`) contido
na folha. Vermelha por injeção do emissor antigo (`width 1100.0 × height 2477 × viewBox … 100`
→ `viewBox-nao-e-WxH`; rect fora → `desenho-fora-da-folha`).

**O que falta, medido na árvore (2026-09-09).** **32 funções `*_svg` de folha em 14 módulos**
(excluídas `abre_svg`, `colisoes_de_rotulo_svg`, `confere_folha_svg`). A guarda genérica é
chamada em **4 folhas de 3 módulos**. Restam **28 folhas sem guarda e sem nunca terem sido
vistas como pixels**:

| Módulo | Folhas | Guardadas |
|---|---|---|
| `desenho_eletrico.py` | `diagrama_unifilar_svg`, `quadro_cargas_svg`, `planta_eletrica_svg`, `planta_eletrica_pavimento_svg`, `qdc_edificio_svg`, `diagrama_prumada_edificio_svg`, `infra_aterramento_edificio_svg` (7) | 0 |
| `desenho_casa_residencial.py` | `telhado_tesoura_svg` ✅, `conferencia_svg`, `esquema_hidraulico_svg`, `quadro_ambientes_svg` (4) | 1 |
| `desenho_concreto.py` | `planta_laje_svg` ✅, `planta_formas_svg`, `prancha_armacao_svg` (3) | 1 |
| `desenho_eletrico_residencial.py` | `unifilar_residencial_svg`, `quadro_cargas_residencial_svg`, `planta_eletrica_residencial_svg` (3) | 0 |
| `desenho_incendio.py` | `planta_seguranca_svg`, `detalhes_hidrantes_rotas_svg`, `planta_pavimento_edificio_svg` (3) | 0 |
| `desenho_alvenaria.py` | `elevacao_paredes_svg` ✅, `planta_fiadas_svg` ✅ (2) | 2 |
| `desenho_hidraulica.py` | `esquema_hidraulica_svg`, `planta_rede_edificio_svg` (2) | 0 |
| `desenho_pavimento.py` | `planta_formas_svg`, `prancha_armacao_vigas_svg` (2) | 0 |
| `desenho_climatizacao.py` | `esquema_climatizacao_svg` (1) | 0 |
| `desenho_coordenacao.py` | `coordenacao_svg` (1) | 0 |
| `desenho_piso.py` | `planta_juntas_svg` (1) | 0 |
| `compatibilizacao.py` | `matriz_svg` (1) | 0 |
| `cronograma.py` | `curva_s_svg` (1) | 0 |
| `fotovoltaico.py` | `grafico_svg` (1) | 0 |
| **Total** | **32** | **4** |

**O que esperar — e o que NÃO esperar.** O D104 já mediu: o padrão que causou o defeito
(cabeçalho emitido antes de as medidas existirem + remendo por `replace`) tem **zero
ocorrências** na árvore, e os ~20 cabeçalhos montados à mão são f-strings com as mesmas
variáveis de `width`/`height` — coerentes por construção. **Não espere epidemia de `viewBox`.**
O rendimento provável é **conteúdo que não cabe na folha** e **rótulo ilegível** — e o
primeiro a lente genérica pega sem renderizar nada.

**Forma de trabalho (herdada, não inventada):** baseline nos dois sentidos por módulo
(regra do G33, molde do `test_08` do G51); vermelho por **injeção**, nunca mutando o repo
(lição do D81); `renderizar-e-olhar` (Edge headless `--screenshot --window-size`) por
amostragem só nas folhas que a lente acusar. `colisoes_de_rotulo_svg` segue **estimador,
não guarda** — é conservador por construção (0,6·size por caractere) e acusa pares
legíveis no PNG; a regra é comparar coordenadas do que o PNG mostra colidir.

**Custo:** baixo — a ferramenta existe e é a mesma para as 28.

---

## 2. Telhado reprovado some do federado, em silêncio

`ATENDE` é condição para o telhado entrar no modelo federado. Um telhado **reprovado**
desaparece do clash — justo quando a interferência mais importa — e é a **única disciplina
com essa condição**.

- **Endereço:** `wiki/04-decisions.md:925` (D101/G72), *"Aberto, nomeado, não redesenhado"*.
- **Status:** aberto por decisão consciente do dono do G72, não por descuido da revisão.
- **Custo:** pequeno e afiado. É uma decisão de contrato (entra sempre e carimba REPROVADO,
  ou entra nunca e o escopo diz por quê), não um cálculo novo.
- **Parentesco:** mesma família da *saturação silenciosa* — o veredito ruim some em vez de
  aparecer.

---

## 3. As duas ausências que o G74 nomeou (precisam de dado declarado)

O G74 implementou a 6.6 do conjunto (`F1d = Nd/150`, `Fd = (2/3)·n·F1d`, `Kbr,1,min` com
`alpha_m = 1+cos(pi/m)`) e deixou **duas ausências nomeadas com artigo**, não mudas:

- **peça de travamento** — 6.6.2 p.29: seção e comprimento não declarados;
- **K real** — 6.6.4 p.31: rigidez real não declarada.

O gate 6.6 é hoje **informativo** (sem comparação carga × carga — evita a tautologia do D86).
Só destrava com declaração do usuário; **não arbitrar**.

---

## 4. Orçamento: os sistemas que nunca entraram na tabela

A guarda do G14 nomeia insumo **que está na tabela e ficou sem quantidade**
(`fechamento_lateral`); ela não vê os sistemas que **nunca entraram na tabela**.
Medida que expôs o buraco: R$ 790 mil ÷ 1134 m² ≈ **R$ 700/m²** contra CUB na casa de
R$ 2.500–3.000/m². A diferença é alvenaria, revestimento, esquadria, impermeabilização,
elevador e incêndio.

- **Endereço:** `wiki/04-decisions.md:773`.
- **Feito:** o `relatorio.txt` traz a seção **A CONFIRMAR** que os nomeia.
- **Aberto:** eles seguem fora do orçamento. A regra permanece **nomear, nunca estimar** —
  o próximo passo é quantificá-los a partir do modelo, não arbitrar preço.

---

## 5. T44 — fundação: caso externo BLOQUEADO (não é falta de norma)

O vertical de fundação é o que mais evoluiu (G9/G17/G18) e o **único sem caso externo com
laudo de sondagem**. Bloqueio **declarado com motivo escrito e critério de desbloqueio
auditável** — 8 buscas / 30+ PDFs no FNDE; o laudo, quando existe, é anexo municipal, não
peça central do pacote replicável.

- **Endereço:** `wiki/06-open-threads.md#T44`; `REVISAO-G28-FUNDACAO-FONTE-BLOQUEADA.md`;
  `fontes_externas/BLOQUEIO-G28-FUNDACAO-SPT.md`.
- **Critério de desbloqueio:** pacote de obra FNDE padrão com **laudo SPT anexado ao próprio
  edital**, via `tools/extrai_fonte_externa.py` + `pagina` + `trecho_literal` por `N_SPT`.
- **Não fazer:** arbitrar `σ_adm`. O framework segue sem inventar tensão de solo.

---

## 6. `A CONFIRMAR` residuais (dado do usuário, não cálculo)

- **Comprimento do patamar da escada** = largura do lance — NBR 9050/9077 não traz o valor
  na base (`escada.py`, D73/C5, `wiki/04-decisions.md:631`).
- **`bacia_caixa` 0,96 vs 0,15** — proveniência; conservador; decisão do usuário
  (S41, `auditoria-desenho-elet-hidr-s41`).

---

## 7. Dívida de documentação (barata, e enganosa se ficar)

- **`wiki/03-phases.md` para em S42**, enquanto `04-decisions.md` já está em **D104**. Quem
  ler as fases acredita que o trabalho parou há ~40 goals.
- **`fontes/fontes-faltantes.md`** diz `telhado_madeira: not_available` — falso desde o G66.
- **Verbete de memória `g13-estrutura-casa`** afirma que *"a viga contínua era analisada e
  nunca verificada — o G3 SEGUE com esse gap"*. **Medido hoje: fechado pelo G34** —
  `edificio_multipavimento.py:292-303` passa cada tramo por `viga_concreto.verifica_viga`
  com `M_d`/`M_d_neg`/`V_d` da envoltória (flexão M+/M−, cortante, ancoragem, flecha
  Tab. 13.3, fissuração). Registrado aqui para **não recaçar**.

---

## Fechados por medição nesta varredura (não reabrir)

| Suspeita herdada | Veredito medido |
|---|---|
| `LAMBDA_BLOCO`/`ALPHA_C`/`XD_LIM` órfãs em `fundacao_sapata` (D97) | **Fechado no G51** — renomeadas com sufixo `_C50` e `__getattr__` de compatibilidade que avisa (`fundacao_sapata.py:715-729`) |
| `s_limite_governante` "sobrescrito pelo rótulo da NOTA" em C55–C90 (D97) | **Não se confirma** — `pilar_concreto.py:700` **acrescenta** (`"%s + NOTA C55-C90 50%%"`), preserva qual limite cortou; guardado em `test_fctm_c60_g49.py:200-202` |
| NBR 8995 ausente do acervo | Falso positivo de regex — presente (item 0) |
| NBR 7229/13969 ausentes | Superadas pela 17076, citadas só como nota; há guarda (item 0) |

---

## Ordem recomendada

1. **G77 — as 28 folhas** (item 1): maior rendimento por custo, ferramenta pronta, cobertura
   hoje em 4/32.
2. **Telhado reprovado no federado** (item 2): pequeno, afiado, e é decisão de contrato.
3. **Dívida de documentação** (item 7): meia hora, e evita que a próxima sessão recace o que
   já está fechado.
4. Itens 3, 4, 5 aguardam **dado declarado** ou **caso externo** — não são trabalho de código
   parado, e arbitrar qualquer um deles seria inventar dado de projeto.
