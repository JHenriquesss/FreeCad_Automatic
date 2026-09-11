# Backlog de goals executáveis — pós-G98 (2026-09-10)

> **FILA CONSUMIDA (2026-09-11).** Os sete goals foram executados e auditados no G106 (D132).
> Registro apenas — não reexecutar. A fila aberta é `BACKLOG-GOALS-G107-G112.md`.
>
> | Goal | Verbete | Nota da auditoria |
> |---|---|---|
> | G99 | D128 | except que apagava a exceção do emissor — corrigido |
> | G100 | D129 | título prometia pilar — corrigido; a dívida do índice virou G110 |
> | G101 | D126 | ok |
> | G102 | D130 | teto de custo nunca medido; injeção sobre disco derivado do mapa — corrigidos |
> | G103 | D131 | ok (limite da fonte escrito) |
> | G104 | D125 | quadro cortado em 220 caracteres — corrigido; o Loop ainda não usa a rota (G107) |
> | G105 | D127 | ferramenta ok; o número por prancha não existe (G109) |

Fila **ABERTA**. Sete goals (G99–G105). As duas filas anteriores estão fechadas e vivem em
`BACKLOG-GOALS.md` (G78–G88) e `BACKLOG-GOALS-G91-G97.md` (G91–G97) apenas como registro —
não reexecute nada de lá.

Cada goal abaixo é **autocontido**: um agente que abra este arquivo sem ter visto a
conversa consegue executá-lo. Traz o que foi **medido** (com endereço no código), o que
entregar, o critério de aceite e as armadilhas conhecidas deste projeto que se aplicam.

**Regra de leitura:** medido em 2026-09-10 na branch `feat/tipologias-e-verticais-de-projeto`,
na auditoria do lote G91–G97 (G98). O que **não** foi medido está dito como não medido.
Nenhum item é palpite sobre o que "provavelmente" falta.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**
(`not_available` com artigo, ou `... nao declarado`), nunca se preenche.

**O norte:** o framework existe para gerar **construções inteiras confiáveis**. O arco
G91–G97 fez o pacote parar de mentir — todo código do índice hoje sai no disco **ou** sai
nomeado. Este arco troca declaração por folha onde o emissor já existe, e tira o
`freecad.exe` do caminho de quem não precisa dele.

---

## Convenções que todo goal deste repo segue

Estas seis regras são caras — cada uma custou um bug. Um agente que as ignore vai
reintroduzir um defeito conhecido.

1. **Baseline nos dois sentidos.** Varredura/guarda sem baseline congelado nos dois
   sentidos é relatório, não portão. Toda lente nova precisa de um teste que fique
   **vermelho quando o defeito é injetado** e verde no caso bom.
2. **Vermelho por injeção, nunca mutando o repo.** Injete o defeito em diretório
   temporário (`tmp_path`). Teste que muta a árvore viva já derrubou a suíte inteira.
3. **A escada: substring → parse → renderizar.** Parseie o XML (`ET.fromstring`); para
   folha, use `desenho_svg_base.confere_folha_svg`; quando o alvo for legibilidade,
   **renderize e olhe** (Edge headless, sem cairosvg/svglib).
4. **Saturação silenciosa.** Tabela que satura no maior valor + gate que não reprova +
   `OK=True` é a classe recorrente. Ao passar de *verificar* para *dimensionar*, o portão é
   o **detalhamento entregue** (adotado × necessário).
5. **Asserção tautológica.** Se o valor de comparação deriva do resultado, a asserção não
   mede nada. Compare com fonte independente (norma, exemplo resolvido, simetria).
6. **"A folha está certa" e "a folha sai" são dois aceites.** O emissor tem de estar ligado
   a um adaptador e o arquivo tem de aparecer no manifesto da rodada. `desenho_terraplenagem`
   cumpriu o critério do G79 ao pé da letra e era ilha (D108).

**Regra do lote, que já falhou três vezes:** ao fim de cada goal, rode os **portões de
censo** antes de declarar verde — `varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `desenho_svg_base.censo_de_folhas`,
`tests/test_alcancabilidade.py` e os baselines `BASELINE_G75`/`BASELINE_G91`/`TRIADAS_G69`.
Módulo novo que a lente não enxerga deixa a suíte vermelha, e o G98 achou exatamente isso
(`caderno_casa_edificio.py` sem isenção no G51).

**Ferramentas prontas que devem ser reusadas, não reescritas:**
`varredura_indice_disco.conferir_indice_disco` (índice↔disco, G91),
`varredura_asserts_sequencia` (G97), `desenho_svg_base.confere_folha_svg` e
`censo_de_folhas` (G76/G77), `caderno_casa_edificio.montar_caderno_svg` e
`svg_para_png` (G94), `caderno_turnkey._add_pagina_imagem`, `dossie._add_paginas_texto`.

---

## Ordem e dependência

- **Bloco 1 (G99, G100, G101):** independentes entre si. Trocam declaração por folha onde o
  emissor **já existe e está provado**. É o maior ganho por linha escrita do arco.
- **Bloco 2 (G102, G103):** o laço do G91 fica honesto. G102 depende do Bloco 1 apenas para
  ter folha nova a medir; pode ser feito antes.
- **Bloco 3 (G104, G105):** o `freecad.exe` sai do caminho de quem não precisa dele. O G105
  é o goal que o D118/G96 pediu explicitamente e depende do G104 para ter rota alternativa.

---

# GOALS

## G99 · A casa liga o elétrico que ela já calcula: 3 códigos declarados que têm emissor pronto

**Prioridade: alta.** Maior ganho por linha do arco: o emissor existe, está provado e não é
chamado.

**Medido (G98):**
- `casa_residencial._motivo_folha_casa_nao_emitida` declara PE-EL-01 (Unifilar), PE-EL-02
  (Planta de instalação) e PE-EL-04 (Quadros/QDC) como *"sem emissor ligado ao hook da casa"*.
  A declaração é **verdadeira** — e o emissor existe:
  `desenho_eletrico_residencial.gerar_desenhos_residenciais` (`:471`) emite exatamente
  `unifilar.svg`, `quadro-cargas.svg` (`:481-482`) e `planta-eletrica.svg` (`:490`), com
  triagem própria (`layout_not_declared`, `invalid_layout`).
- Quem o chama hoje é **só** `residencial_eletrica.py:432` — o adaptador da fixture sintética
  (G10). O adaptador da casa real não o chama: `_emitir_desenhos` chama apenas
  `dcr.gerar_desenhos_casa`.
- A casa **calcula** o elétrico: `result["eletrico"]["circuits"]` alimenta a conferência
  NBR 5410 e a planta baixa (G78).
- É a classe do G79/G89 outra vez: folha certa que ninguém emite. Declarar foi o mínimo
  honesto do G92; ligar é este goal.

**Entregar:**
- `gerar_desenhos_residenciais` chamada no hook de desenhos da casa, com os arquivos
  registrados no manifesto e as triagens próprias do emissor preservadas (não reescrever a
  triagem dele: `layout_not_declared` já nomeia o dado que falta).
- `_motivo_folha_casa_nao_emitida` perde os três ramos que deixam de ser verdade. Motivo que
  sobrevive ao fato vira nome morto — o defeito que derrubou o portão do G77.
- PE-EL-03 (Infraestrutura/aterramento) **continua declarado**: não há emissor e a malha não
  é declarada no spec da casa. Não inventar.

**Aceite:**
- Portão do G91 verde com os três códigos do lado do disco, não do lado do motivo.
- Cada folha passa em `confere_folha_svg` (regra 3: parse, não substring).
- Vermelho por injeção em `tmp_path`: desligar a chamada faz os três voltarem a `faltando`.

**Armadilha medida:** a planta elétrica exige `circuits.layout` válido. Sem layout declarado
o emissor pula com motivo — esse caminho tem de continuar saindo **nomeado**, e não virar
folha vazia (o bug irmão do G62 e da saturação no piso da Fase 6B).

---

## G100 · As folhas de concreto da casa: o prédio já tem os três emissores

**Prioridade: alta.**

**Medido (G98):**
- A casa declara PE-CO-02 (Armação pilares/vigas), PE-CO-03 (Detalhes) e PE-CO-04 (Locação e
  formas da fundação) como *"sem emissor ... nesta rodada"*, com a estrutura **calculada**
  (`estrutura.pavimento`, `estrutura.fundacao` — G13).
- O prédio emite os equivalentes: `armacao-vigas-pavimento-tipo.svg` e
  `fundacao-locacao-formas.svg` (`edificio_adapter._PRANCHA_ARQUIVO`, o segundo entregue pelo
  G80 via `desenho_fundacao_edificio.py`).
- **Não medido:** se os emissores do prédio aceitam a geometria da casa sem adaptação. Medir
  é a primeira tarefa do goal, não uma suposição.

**Entregar:**
- Reuso por **primitivas**, não por cópia (o precedente é a Fase 6B: uma só implementação de
  `esc()`). Se o emissor do prédio não servir, extrair a primitiva comum e deixar as duas
  tipologias chamando a mesma função.
- O que não puder sair continua declarado com o dado nomeado.

**Aceite:**
- Cada folha nova entra em `FOLHAS` (`tests/test_folhas_g77.py`) e passa no censo por AST —
  guarda sem portão de cobertura não escala (a lição inteira do G77).
- `confere_folha_svg` em todas: viewBox == W×H e conteúdo contido.
- Portão do G91 verde com os códigos do lado do disco.

**Armadilha medida:** a armadura de viga do prédio **sai vazia** porque as vigas do edifício
nunca são verificadas (G14). Na casa a viga contínua **é** verificada desde o G34 — conferir
de qual lado vem o dado antes de reusar o desenho, ou a folha sai correta e vazia.

---

## G101 · O galpão: escada de emergência e detalhes de hidrantes, ou a fronteira escrita

**Prioridade: média.**

**Medido (G98):**
- `galpao_adapter._motivo_folha_galpao_nao_emitida` declara PE-IN-02 (Detalhes
  hidrantes/rotas) e PE-IN-03 (Escada de emergência) sem emissor; PE-IN-03 diz também
  *"geometria da escada no spec do galpão não declarada"*.
- O prédio **tem** a folha de escada desde o G81: `desenho_escada_edificio.py` (PE-IN-03,
  planta e corte com espelho/piso, Blondel, largura exigida × adotada, tipo Tab.11).
- O executivo de incêndio do galpão emite `INC01_PLANTA` e `INC02_RESUMO`
  (`techdraw_incendio.py`), sem corte da coluna de hidrantes.

**Entregar — uma das duas, escrita:**
- **(a)** o galpão declara a escada no spec e reusa `desenho_escada_edificio`; ou
- **(b)** a fronteira: *galpão térreo não exige escada de emergência por [artigo]* — e então
  a disciplina **não promete** PE-IN-03 em vez de prometer e declarar ausente. Prometer o que
  a norma não exige polui o índice; a decisão vai para `wiki/04-decisions.md` com o artigo.
- PE-IN-02: medir se o dado do corte de hidrante existe em `galpao_seguranca_incendio` antes
  de decidir. Não medido.

**Aceite:** o caminho escolhido fica **escrito**, e o portão do G91 reflete a escolha (folha
no disco, ou código que a disciplina deixou de prometer). Ausência declarada continua sendo
entrega válida — o que não é entrega é ausência silenciosa.

**Não fazer:** arbitrar a altura, o número de pavimentos ou a ocupação do galpão para
"caber" numa exigência de escada. É valor normativo, e o framework não arbitra.

---

## G102 · O portão do G91 mede índice × mapa; falta medir índice × disco de uma rodada real

**Prioridade: alta.** É a dívida que o próprio G91 deixou escrita.

**Medido (G98):**
- Em `tests/test_indice_disco_g91.py`, os três quadros montam
  `"disco": sorted(mapa.values())` (`:73`, `:92`, `:113`) — o lado do disco **deriva do
  próprio mapa**. Naquele portão `faltando` nunca pode disparar: ele mede índice × **mapa**
  (`sem_mapa` e `sobrando`), que é real e útil, mas não é o que o nome promete.
- O lado do disco existe em `test_04` (disco furado sobre o mapa real) e nos portões por
  tipologia do G92/G93 — nenhum deles sobre uma **rodada de verdade** das três tipologias.
- É a convenção 5 aplicada ao próprio portão: valor de comparação derivado do resultado.
- **Também não medido por ninguém:** folha **no disco que o índice não promete**. A casa
  emite `quadro-ambientes.svg` e `conferencia-nbr5410.svg`
  (`desenho_casa_residencial.py:673,683`) e nenhum código do índice as reivindica. A lente do
  G91 só tem o lado do mapa (`sobrando`), não o lado do disco.

**Entregar:**
- Um portão que rode as três tipologias de verdade (specs de `projects/`, `generate_ifc`
  desligado para caber no CI) e confronte o índice com o **manifesto da rodada**.
- O quarto lado na lente: `extra_no_disco` — arquivo emitido que nenhum código reivindica.
  Cada extra sai isento **com motivo escrito** (folha de conferência interna é legítima) ou
  entra no índice.
- Renomear/dividir o portão do G91 para que o nome diga o que ele mede.

**Aceite:**
- Vermelho por injeção nos dois lados, em `tmp_path`.
- Custo do portão medido e escrito (é o que decide se ele roda no CI ou só a mão).

---

## G103 · Disciplina executada que o índice não promete: o D89 do lado da promessa

**Prioridade: média.** Barato.

**Medido (G98):**
- `"mezanino"` está em `galpao_turnkey.DISCIPLINAS` e **não** em `pacote_legal._PRANCHAS`
  (travado por assert em `tests/test_indice_disco_g91.py:290`, achado registrado e não
  consertado). A disciplina é calculada e **evapora no `continue`** do índice.
- É o D89 espelhado: o D89 conhecido é código prometido sem arquivo; este é disciplina
  entregue sem código. Nenhuma lente olha esse lado.

**Entregar:**
- Portão: toda disciplina que uma tipologia executa tem entrada em `_PRANCHAS` **ou** motivo
  escrito de por que não produz prancha (mezanino pode ser um caso legítimo — parte da
  estrutura, sem folha própria; então o motivo fica escrito e a exceção é nomeada).
- Aplicar às três tipologias, com as três fontes vivas (`galpao_turnkey.DISCIPLINAS`,
  `gestao_casa.disciplinas_pacote`, `gestao_edificio.disciplinas_pacote`).

**Aceite:** baseline nos dois sentidos; isenção sem motivo reprova (é a regra que derrubou o
G77, e a única que impede a lista de isentos de virar silêncio).

---

## G104 · Tirar o `freecad.exe` do caminho de quem só precisa virar SVG em PDF

**Prioridade: alta.** É a causa medida do custo das disciplinas que **não** têm 3D.

**Medido (G96/D118 e G98):**
- `galpao_hidraulica.montar_pranchas` (`:337`) diz na própria docstring: *"NÃO precisa de
  FCStd (o esquema é SVG do `desenho_hidraulica`). Roda o `freecad.exe` gráfico"*. O mesmo em
  `galpao_seguranca_incendio.py:172-188` e na climatização.
- Ou seja: três disciplinas com esquema **SVG puro** pagam uma instância gráfica de FreeCAD
  só para exportar PDF.
- A rota alternativa **já existe e está provada** desde o G94:
  `caderno_casa_edificio.svg_para_png` (pixmap do fitz; `doc.save()` direto sobre SVG falha)
  e `_add_pagina_imagem`.
- `_STAGE_WEIGHTS` (`caderno_turnkey.py:49-59`) reparte o orçamento de tempo; o aço leva 7,0.
  Quanto as três disciplinas SVG custam hoje **não foi medido isoladamente** — medir é parte
  do goal.

**Entregar:**
- Rota de exportação SVG → PDF sem `freecad.exe` para as disciplinas de esquema puro, com o
  carimbo A1 preservado.
- Medição antes/depois, com o processo reiniciado a cada rodada (o `freecad.exe` persiste e
  roda o módulo irmão antigo — D64).
- O caminho FreeCAD **continua existindo** para quem tem 3D; este goal não o remove.

**Aceite:**
- As pranchas saem com o mesmo conteúdo (parse + `confere_folha_svg`, e uma renderizada e
  olhada — regra 3).
- Ganho de tempo medido e escrito. Se não houver ganho, o resultado negativo vai para o
  verbete e o goal fecha assim mesmo — medição que só vale quando confirma a hipótese não é
  medição.

---

## G105 · O harness de medição por prancha do executivo de aço

**Prioridade: média. Este goal entrega ferramenta, não otimização.**

**Medido (D118/G96):**
- O aço executivo precisa do FreeCAD em **11** folhas projetadas
  (`DrawViewPart`/`DrawViewSection`); só PE09 (quadros) e PE16 (montagem) são 2D puro
  (`Spreadsheet`/`Annotation`).
- `freecadcmd` **não** exporta PDF (*"Cannot load Gui module"*); a exportação exige
  `freecad.exe` com GUI.
- **Nenhuma iteração manual de timing foi rodada** — o D118 diz isso explicitamente. O custo
  por prancha é desconhecido; só se sabe o peso do estágio inteiro (7,0) e que o executivo
  estoura ~15 min em rodada (06-open-threads T13).
- O precedente é `tools_probe_pe13.py`: uma execução mede o que a iteração manual não mede.

**Entregar:**
- Harness que meça **por prancha**: tempo de construção, tempo de HLR, tempo de export.
- Processo reiniciado a cada medição; kill via WMI `Terminate` (`taskkill` não derruba
  FreeCAD travado — D64).
- Baseline nos dois sentidos: uma prancha que fique mais lenta que o baseline reprova.

**Aceite:** o número por prancha existe e está escrito. **Não** otimizar nada neste goal: o
harness primeiro, a decisão depois (`ferramenta-antes-de-iterar` — já custou uma entrega
adiada por falta de medição).

**Pré-requisito escrito no D118 para qualquer migração de PE09/PE16 a SVG:**
`_notas_do_modelo` (`techdraw_exec.py:1462`) mede **3 números no BoundBox do 3D** (níveis,
gancho, contraventamento). Sem fonte declarada para eles fora do 3D, migrar é saturação
silenciosa (regra 4), não economia.
