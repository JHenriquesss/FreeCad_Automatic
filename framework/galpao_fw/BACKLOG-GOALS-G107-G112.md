# Backlog de goals executáveis — pós-G106 (2026-09-11)

Fila **ABERTA**. Seis goals (G107–G112). As filas anteriores estão fechadas e ficam apenas
como registro — não reexecute nada de lá:
`BACKLOG-GOALS.md` (G78–G88), `BACKLOG-GOALS-G91-G97.md` (G91–G97) e
`BACKLOG-GOALS-G99-G105.md` (G99–G105).

Cada goal abaixo é **autocontido**: um agente que abra este arquivo sem ter visto a
conversa consegue executá-lo. Traz o que foi **medido** (com endereço no código), o que
entregar, o critério de aceite e as armadilhas conhecidas deste projeto que se aplicam.

**Regra de leitura:** medido em 2026-09-11 na branch `feat/tipologias-e-verticais-de-projeto`,
na auditoria do lote G99–G105 (G106). O que **não** foi medido está dito como não medido.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**
(`not_available` com o dado nomeado), nunca se preenche.

**O norte:** o framework existe para gerar **construções inteiras confiáveis**. O arco
G99–G105 trocou declaração por folha onde o emissor existia. Este arco fecha o que a
auditoria achou entre "a folha sai" e "a folha diz a verdade": o índice que promete pilar e
ninguém desenha, a laje de um painel só, o carimbo com código diferente do índice, e o
`freecad.exe` que continua no caminho de quem não precisa dele.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

Nenhuma norma ausente. A que faltava chegou em 2026-09-11:

- **ABNT NBR 6118:2023 (norma-base), F150** — 4ª edição, 28.08.2023, **Versão corrigida 2
  de 30.01.2024** (incorpora as Erratas 1 e 2). Junto com a
  **Emenda 1:2026 (F098)** equivale à NBR 6118:2026. O framework ainda calcula pela **2014**
  (F016).
- **Atenção: a camada de texto da F150 está embaralhada** no corpo (cifra de fonte:
  "Todos os direitos" sai "7RGRVRVGLUHLWRV", ~40 % dos tokens, espaços perdidos). A página
  **renderiza correta** — conferido na imagem da p.171 (18.4.2). Busca por texto e NotebookLM
  leem lixo: para citar a 2023, **renderize a página e leia a imagem**, ou produza antes uma
  versão com OCR/decodificação.
- O G110 (armação de pilar, 18.4) calcula pela 2014 e **diz isso na folha**; confrontar a
  18.4 da 2014 com a 2023 + Em1 é parte do goal, pela imagem.

---

## Convenções que todo goal deste repo segue

1. **Baseline nos dois sentidos.** Varredura/guarda sem baseline congelado nos dois
   sentidos é relatório, não portão. Toda lente nova precisa de um teste que fique
   **vermelho quando o defeito é injetado** e verde no caso bom.
2. **Vermelho por injeção, nunca mutando o repo.** Injete o defeito em `tmp_path`.
3. **A escada: substring → parse → renderizar.** `ET.fromstring`; para folha,
   `desenho_svg_base.confere_folha_svg`; quando o alvo for legibilidade, **renderize e olhe**
   (`caderno_casa_edificio.svg_para_png` serve).
4. **Saturação silenciosa.** Tabela que satura + gate que não reprova + `OK=True`. E a
   variante que o G106 achou: **texto cortado** (`ln[:220]`, `break` no fim da página) é
   saturação do mesmo jeito — o dado some sem aviso.
5. **Asserção tautológica.** Se o valor de comparação deriva do resultado — **ou é uma
   constante escrita à mão que o teste nunca mede** — a asserção não mede nada.
6. **"A folha está certa" e "a folha sai" são dois aceites.** E um terceiro, deste arco:
   **"a folha diz o que desenha"** — título e carimbo batem com a geometria (o G106 achou
   "ARMAÇÃO DE VIGAS E PILARES" numa folha só de vigas).

**Regra do lote (funcionou pela primeira vez no G99–G105 — manter):** ao fim de cada goal,
rode os portões de censo antes de declarar verde —
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_sequencia.confere()`,
`desenho_svg_base.censo_de_folhas` × `FOLHAS`, `tests/test_alcancabilidade.py` e os baselines.

**Except que devolve vazio apaga a causa.** O G106 achou `except Exception: return {"files": []}`
no hook elétrico da casa: a exceção sumia e o laço caía num motivo genérico falso. Todo
`except` novo em hook registra `type(exc).__name__: exc` no motivo.

**Ferramentas prontas para reusar:** `varredura_indice_disco` (G91 + `extra_no_disco` do G102),
`varredura_disciplina_prancha` (G103), `prancha_svg_direta` (G104), 
`tools_harness_aco_por_prancha` (G105), `desenho_svg_base.confere_folha_svg`.

---

## Ordem e dependência

- **Bloco 1 (G107, G108):** o ganho do G104 chega ao Loop. G108 depende do G107 só para
  ter rodada a medir; os dois podem ir juntos.
- **Bloco 2 (G109):** fecha o aceite do G105. Pesado (constrói o 3D) — **feche o `opencode` e
  outros apps antes**; a máquina tem 8 GB e a suíte já foi morta por memória.
- **Bloco 3 (G110, G111, G112):** a folha diz o que desenha. Independentes entre si.

---

# GOALS

## G107 · O galpão emite as pranchas de esquema puro sem `freecad.exe`

**Prioridade: alta.** O G104 criou a rota e ela não chega ao Loop.

**Medido (G106):**
- `galpao_adapter._emit_drawings` (`:392`) sai com `not_available: freecad.exe nao encontrado`
  **antes** de qualquer disciplina. Hidráulica, incêndio e climatização não precisam mais do
  executável desde o G104 (`montar_pranchas(..., backend="svg")` é o default) e mesmo assim
  não saem.
- Consequência medida no G102: o portão de rodada real roda o galpão com
  `generate_2d=False`, então do galpão ele só mede índice × **mapa** — o lado do disco nunca
  é exercitado (escrito no D130).
- `caderno_turnkey.montar_caderno` também chama `tk.render_federado` e
  `montar_prancha_coordenacao` (FreeCAD gráfico). **Não medido:** o que esses dois fazem com
  `freecad_exe=None` — medir é a primeira tarefa.

**Entregar:**
- Sem `freecad.exe`, o deliverable `drawings` do galpão emite o que não precisa dele e
  declara **por código** o que precisa (aço, concreto, coordenação), com o motivo
  `freecad.exe nao encontrado` nomeado em cada um. Nunca o deliverable inteiro sumindo por
  causa de três disciplinas.
- `tests/test_indice_disco_rodada_g102.py`: o galpão passa a rodar com `generate_2d=True`,
  e os códigos PE-HI/PE-IN/PE-CL são confrontados com o disco de verdade.

**Aceite:** o galpão sem `freecad.exe` sai com `status` parcial nomeado e os PDFs de esquema
no manifesto; vermelho por injeção (desligar a rota SVG faz os códigos voltarem a
`faltando`).

**Armadilha:** `status: generated` com metade das disciplinas faltando é o "orçamento parcial
que se diz fechado" do G7. O status tem de dizer que é parcial.

---

## G108 · O prazo do caderno ainda reserva tempo de FreeCAD para quem leva menos de 1 s

**Prioridade: alta.** É o custo do aço, que estoura ~15 min (06-open-threads T13).

**Medido (G106):**
- `caderno_turnkey._STAGE_WEIGHTS` (`:49`): aço 7,0; concreto 2,0; elétrico 1,5;
  **hidráulica 1,25; incêndio 1,0; climatização 1,0**; mezanino cai no default 1,0.
- A reserva é recalculada sobre o **tempo restante** (`reserve_stage`, `:351`), na ordem de
  `galpao_turnkey.DISCIPLINAS` (concreto, aço, elétrico, incêndio, climatização, hidráulica,
  mezanino). Quando o aço reserva, os pendentes somam 12,75 e ele recebe **7/12,75 = 55 %**
  do que resta. Com as três disciplinas SVG a peso próximo de zero, receberia ~74 %.
- Tempo medido das três pela rota SVG no G104 (D125): 0,56 s, 0,62 s e 0,57 s.
- **Não medido:** se o mezanino despacha alguma prancha (o peso 1,0 dele pode ser reserva
  para nada).

**Entregar:**
- Pesos que venham da **medição** (D125 para as três; medir o mezanino), nunca de palpite,
  com a origem escrita ao lado de cada peso.
- Um teste que calcule a fração do aço com os pesos vivos e trave o valor.

**Aceite:** a fração do aço sobe, e o número está escrito no teste com a conta. Se a medição
mostrar que não sobe, o resultado negativo vai para o verbete e o goal fecha assim mesmo.

---

## G109 · O número por prancha do aço: fechar o aceite do G105

**Prioridade: média. Pesado — feche outros apps antes.**

**Medido (G106):**
- O aceite do G105 era *"o número por prancha existe e está escrito"*, e ele **não existe**:
  o D127 registra `not_available` porque não há `*.FCStd` em `projects/`.
- Isso **não é** bloqueio de fonte: o modelo se constrói (`montar_modelo`, com fallback
  headless via `freecadcmd` desde o S19; `rodar_projeto`).
- A ferramenta está pronta: `python tools_harness_aco_por_prancha.py --fcstd <modelo> --out <dir>`,
  com um processo por prancha e kill via WMI.

**Entregar:**
- O FCStd de um projeto persistido (sugestão: `projects/galpao-ufpe`), construído pela rota
  existente e **não versionado** (é saída de rodada).
- Os tempos por prancha (t_build/t_hlr/t_cotas/t_export) escritos no verbete e congelados
  como orçamento do `conferir_orcamento`.

**Aceite:** o número existe. Se a máquina não aguentar, o que falhou (qual prancha, qual
fase, quanto de memória) é o resultado e vai escrito. Medição que só vale quando confirma
não é medição.

**Não fazer:** otimizar prancha nenhuma neste goal (`ferramenta-antes-de-iterar`).

---

## G110 · PE-CO-02 promete "Armação pilares/vigas" e nenhuma tipologia desenha pilar

**Prioridade: alta.** A promessa está no índice das duas tipologias de concreto.

**Medido (G106):**
- `pacote_legal._PRANCHAS["concreto"]` promete **"Armacao pilares/vigas"** em PE-CO-02.
- Casa (G100) e prédio mapeiam PE-CO-02 para a folha de **vigas**
  (`desenho_pavimento.prancha_armacao_vigas_svg`). Não existe emissor de armação de pilar na
  árvore (busca por `def .*pilar.*_svg` só acha o wrapper da casa, que desenha vigas).
- O dado **existe**: `pilar_continuo.dimensiona` publica por lance `b`, `h`, `As_cm2`,
  `taxa_pct`, `Nd`, esbeltez, e o `detalhe` de `pilar_concreto` traz o estribo adotado
  (φ, s, ramos) e o `s_limite_governante` da 18.4.3 (D84). A casa publica `estrutura.pilares`
  (dict por pilar, P11…P43).
- A bitola longitudinal **não** é calculada: só entra se `phi_long_mm` for declarado
  (`pilar_concreto.py:683`).

**Entregar:**
- Um quadro de armação de pilares (uma primitiva, as duas tipologias), com seção, As, taxa,
  estribo e o limite governante — tudo lido do resultado.
- O arranjo de barras sai **declarado** ("arranjo não detalhado: `phi_long_mm` não
  declarado") onde não houver bitola. Escolher bitola para preencher o quadro é inventar dado.
- Folha nova entra em `FOLHAS` (G77) e no mapa das duas tipologias (N:1 com a de vigas ou
  código próprio — decidir e escrever).

**Aceite:** drawing-vs-data (a folha lista exatamente os pilares do resultado, contados);
`confere_folha_svg`; renderizada e olhada; a folha diz que calcula pela NBR 6118:2014.

---

## G111 · PE-CO-03 desenha um painel de seis e não diz qual

**Prioridade: média.**

**Medido (G106):**
- A casa do spec persistido tem **6 painéis**: (3,5×4,0 caso 4) ×2, (3,5×4,0 caso 8) ×2,
  (3,4×4,0 caso 4) ×2. `estrutura.laje` é **um** dict — o painel crítico `crit` que
  `estrutura_casa` passa a `dimensiona_laje` (`:1752`) para convergir a espessura.
- A folha (`desenho_concreto.planta_laje_svg`) titula "painel 3.50 x 4.00" e mostra o quadro
  de ferros **desse** painel. Não diz que é o crítico, nem que existem outros cinco, nem que
  a armadura deles não foi detalhada. O prédio faz o mesmo.
- **Não medido:** se o critério de `crit` garante que o painel de caso 8 (outras vinculações,
  mesmas dimensões) tem momentos menores. Medir antes de escrever "governa".

**Entregar — uma das duas, escrita:**
- **(a)** detalhar todos os painéis (um `dimensiona_laje` por painel, mesma `h`), um quadro
  de ferros por painel; ou
- **(b)** a folha diz "painel crítico N de 6" e lista os outros como **não detalhados**, com
  o motivo.

**Aceite:** drawing-vs-data — o número de painéis na folha (desenhados ou listados) é igual a
`len(pavimento.paineis)`; vermelho por injeção (painel a mais no resultado).

---

## G112 · O carimbo do galpão usa um código e o índice usa outro

**Prioridade: média.** Quem confere o caderno contra o índice não consegue casar as folhas.

**Medido (G106):**
- O carimbo das pranchas do galpão (`techdraw_hidraulica.py:32,49`,
  `techdraw_incendio.py:48,65`, `techdraw_climatizacao.py:27,43`, e a rota SVG do G104 em
  `prancha_svg_direta.PRANCHAS`) diz **PE-HID-01/02, PE-INC-01/02, PE-CLI-01/02**.
- O índice (`pacote_legal._PRANCHAS`) promete **PE-HI-01..03, PE-IN-01..03, PE-CL-01**.
- Não é só o prefixo: PE-HI-02 no índice é "Esgoto/ventilação", e **PE-HID-02** no carimbo é
  o **quadro de dimensionamento**. O mesmo número designa folhas diferentes.
- **Não medido:** aço (PE01…PE16 contra PE-ES-01..03) e concreto do galpão.

**Entregar:**
- Uma lente: para cada folha emitida, o código do carimbo pertence ao conjunto de códigos
  que o mapa da tipologia atribui àquele arquivo. Baseline nos dois sentidos.
- Corrigir os carimbos que a lente reprovar, **ou** escrever por que o carimbo usa numeração
  própria e onde está a tabela de correspondência que o cliente recebe.

**Aceite:** a lente roda sobre as três tipologias; vermelho por injeção (carimbo trocado em
`tmp_path`).
