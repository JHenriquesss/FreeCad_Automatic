# Backlog de goals executáveis — pós-G153 / D179 (2026-09-16)

Fila **ABERTA**. Quatro goals: **G154 fechado** (D180, `4018471`); **G155, G156 e G157
abertos**, nesta ordem, **um de cada vez**. Todas as decisões do usuário já foram tomadas
(2026-09-17, seção "Decisões tomadas"): nenhum goal para para perguntar. As filas anteriores estão fechadas e ficam apenas como registro — não reexecute nada
de lá: `BACKLOG-GOALS.md` (G78–G88), `BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`,
`BACKLOG-GOALS-G107-G112.md`, `BACKLOG-GOALS-G114-G118.md`, `BACKLOG-GOALS-G120-G124.md`,
`BACKLOG-GOALS-G126-G130.md`, `BACKLOG-GOALS-G132-G136.md`, `BACKLOG-GOALS-G137-G142.md`,
`BACKLOG-GOALS-G143-G148.md` e `BACKLOG-GOALS-G149-G153.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-16 na branch `feat/tipologias-e-verticais-de-projeto`
(commit `6d94510`), na auditoria do lote G149–G153 (D179). O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis — o cliente informa o projeto e recebe cálculo,
3D e todas as folhas. A auditoria D179 achou que **uma citação normativa errada** (FS 3,0 da
estaca "pela NBR 6122") viveu dois meses no código e o G149 a levou para a folha — porque o
backlog anterior afirmou "valor normativo, no acervo" **sem ler a página**. O arco G154–G157
fecha o que essa descoberta abre: o **material do modelo** que decide veredito sem ninguém
declarar, as **folhas do prédio e da casa** que não dizem que reprovaram, a **lente das
citações** com número e sem item, e o **verbete/fases** que o lote deixou sem número.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

**Nenhuma norma ausente trava este arco.** A NBR 6122:2022 está no acervo (F038 PDF original,
F132 OCR); o D179 conferiu 6.2.1.2.1 na **página 18 do PDF** (imagem). Seguem as 4 sem entrada
já triadas (nenhuma é fonte de conta):
- **NBR 5413** — substituída pela NBR ISO/CIE 8995-1:2013, no acervo (F102); lacuna congelada
  em `tests/test_normas_catalogo.LACUNAS_PRE_EXISTENTES`.
- **NBR 13438** — nome de material na tabela de pesos (`cargas_nbr6120.py:115`); mesma lacuna
  congelada (junto com a NBR 5444, simbologia, coberta pela IEC 60617 F148).
- **NBR 8522** e **NBR 8965** — remissões do texto da NBR 6118 transcrito nas lentes G116/G122;
  isentas em `REMISSOES_DA_NORMA_TRANSCRITA`.

**Estar no catálogo não é ter lido o item.** "No acervo" sem a página conferida é afirmação,
não medida (D179). O OCR (F132) tem erros de leitura: a citação se confere **na imagem do PDF**.

**Bloqueado por DADO de projeto, não por norma (fora deste arco):** PE-IN-03 escada do galpão
(geometria não declarada; fronteira G101), PE-EL-03 da casa (malha e SPDA não declarados;
D171), PE-AR-01 implantação e PE-AR-03 cortes da casa (lote, recuos, cotas), fundação por laudo
SPT externo (T44).

---

## Protocolo de execução em sequência (2026-09-17)

**Por que existe.** O G155 começou a editar a árvore (09:19) **antes** do commit do G154
(11:06): os dois rodaram ao mesmo tempo na mesma cópia. O G154 teve de fechar a suíte num
worktree à parte (o WIP do G155 quebrava a guarda), e o G155 ficou pela metade, sem commit. O
backlog também deixava escolhas abertas ("proveniência **ou** pergunta", "depois do G154 **se**…",
"a escolha vai ao usuário"). Este protocolo fecha as duas portas.

1. **Um goal por vez, na ordem G155 → G156 → G157.** Nunca abra dois goals ao mesmo tempo, nem
   em outra janela/sessão. O próximo só começa depois do commit do anterior.
2. **Checagem de entrada (antes de editar qualquer arquivo):**
   - `git log --oneline` tem o commit do goal anterior (G155: `4018471` G154; G156: o commit
     "G155:"; G157: o commit "G156:"). Se não tiver, **não comece**: encerre dizendo qual falta.
   - `git status --short` só pode mostrar o WIP **do próprio goal** (ver "Estado de partida" de
     cada um). Arquivo modificado que não é do goal → **não comece**: encerre listando os
     arquivos. Nunca apague, reverta ou faça stash de trabalho alheio.
   - Nenhum `pytest`/`suite_paralela`/`freecad*` rodando (liste os processos). Se houver, é outra
     execução: encerre dizendo o PID.
3. **Sem perguntas no meio.** As decisões estão abaixo. Escolha que o backlog não previu segue a
   **regra conservadora**: não muda número, veredito, default nem trava; declara a ausência; a
   escolha vai ao verbete numa linha **"Pendência ao usuário:"**; o goal **continua** até o commit.
4. **Fechamento:** suíte pelo runner no código final (conv. 12 e 16), verbete com número D e
   linha no `wiki/03-phases.md` **no mesmo commit**, commit com o prefixo `G15x:`. O goal só
   termina com a árvore limpa (`git status --short` vazio).
5. **Interrupção** (queda, contexto, máquina): o próximo disparo do **mesmo** goal retoma pelo
   `git status`/`git diff` — nunca começa o goal seguinte.

---

## Decisões tomadas (usuário, 2026-09-17)

- **FS da estaca: (a) manter 3,0 adotado e declarado.** Nenhum goal muda o número ou a trava
  do `validar`. O texto já diz "adotado no D38" com 6.2.1.2.1/6.2.1.2.2 ao lado (D179).
- **G155 retoma o WIP** que está na árvore (não descarta, não recomeça).
- **Disparo:** um `/goal` por vez, em sequência, com a checagem de entrada do protocolo.
- **Imprevisto:** regra conservadora do protocolo, item 3 (seguir e registrar; não parar).
- **G156, divergência de citação:** corrige só a atribuição ("adotado", com o item da norma ao
  lado), lista na tabela do verbete como pendência ao usuário; **nenhum número muda**.
- **G157, numeração:** os quatro verbetes recebem os próximos D livres **depois** do último D
  existente no momento do G157, na ordem G149, G150, G151, G152.

Registro do FS (para consulta):

- **Código:** `estaca_profunda.FS_GLOBAL = 3.0` (`:68`), adotado no **D38** (parecer de
  2026-07-11, "sem citar o PDF 6122 escaneado"); `projeto_spec.validar()` **bloqueia FS < 3,0
  sem `fundacao.estaca.prova_de_carga`** (`:274-300`); o wizard pergunta com 3,0 de padrão.
- **Acervo (NBR 6122:2022, p.18):** 6.2.1.2.1 — FS global **2,0** para estaca por método
  semiempírico; 6.2.1.2.2 — **1,6** com prova de carga estática na fase de projeto. O **3,00** é
  da **Tabela 1** (fundação **rasa**).
- **D179 fez só a atribuição:** o resultado, o memorial, a folha, o wizard e a mensagem do
  `validar` dizem agora "3,0 adotado no D38; NBR 6122:2022 6.2.1.2.1 fixa 2,0 — confirmar". O
  número e a trava **não mudaram**.
- **Escolhido (a)** em 2026-09-17. A alternativa (b), alinhar a 2,0/1,6, não está em goal
  nenhum deste lote.

---

## Convenções que todo goal deste repo segue

1. **Baseline nos dois sentidos**, e toda lente nova com teste que fica **vermelho quando o
   defeito é injetado**.
2. **Injeção em `tmp_path`**, nunca mutando o repo.
3. **Substring → parse → renderizar.** Para norma e para folha: **olhe a imagem**.
4. **Saturação silenciosa**, incluindo `OK` por item que não chega ao veredito (G113) e texto
   cortado (G106).
5. **Asserção tautológica**, incluindo teste que confere um literal contra ele mesmo (G119).
6. **Três aceites por folha:** está certa, sai no manifesto, diz o que desenha.
7. **Instrumento tem de conseguir acusar** (G119) — e acusar **por parte** (G125).
8. **Constante "medida" que a produção não lê é comentário** (G119).
9. **A lente parte de onde o dado é PRODUZIDO** — a conta, o emissor — e confere a citação
   contra ele (G125).
10. **O resumo da suíte se lê inteiro antes de fechar** (G125); a lista inclui `tests/branches`
    e `tests/trunk` (`find tests -name 'test_*.py'`).
11. **Injete o valor em cada lugar de entrada que o produto aceita** (G131); "não se aplica"
    é um terceiro valor declarado.
12. **A suíte do goal roda pelo runner paralelo** (D164/D165), a partir de
    `framework/galpao_fw`, com o interpretador de nome curto 8.3:
    `…\VENV~1\Scripts\python.exe tools/suite_paralela.py -n 3` (~17 min; grava
    `resumo.json` — o goal só fecha com `rc_pytest` 0 **e** `quebras` vazio). O runner põe
    `PYTHONUTF8=1` (D172), confirma o piso de 200 MB em 3 amostras seguidas (D178) e termina só a
    árvore do próprio filho (D176). Não edite o repositório com a suíte rodando. Teste novo que
    sobe freecad.exe/freecadcmd.exe entra em `tests/censo_freecad.GRUPO_FREECAD` com o motivo
    medido. A serial `pytest tests` e os portões de auditoria (`GALPAO_AUDITORIA=1`: executivo
    de aço D165 e galpão do G102 D177) rodam **na auditoria do lote**, não em cada goal. Máquina
    de 8 GB: rodada pesada uma por vez; os aplicativos do usuário ficam abertos.
13. **(D172) Emissor ou conta reaproveitados trazem os fallbacks deles.** Rode com o dado
    **ausente** e com **zero**, um por um; folha nova ligada em código comum fica num `try`
    próprio; injete a falha **só na folha nova**.
14. **(D176) A prova tem de exercitar o caminho que falha.** Kill/abort se prova com processo
    real ocupado; folha com várias páginas confere as marcas entre páginas e contra o BIM.
15. **NOVO (D179) — norma citada é norma LIDA.** Toda frase que atribui um número a uma NBR
    traz o **item** e foi conferida **na imagem da página** do acervo. "Está no catálogo" não é
    leitura. Número do código que diverge da página **não se troca no goal**: a atribuição se
    corrige ("adotado", com o item da norma ao lado) e a escolha vai ao usuário **como
    pendência no verbete, sem parar o goal** (protocolo, item 3). Isso vale para
    o backlog também: o D179 achou a afirmação falsa **no backlog anterior**.
16. **NOVO (D179) — o fechamento é do código commitado.** Mudou código depois da corrida que
    fecha (mesmo "sem mudar o caminho verde")? Rode de novo. O verbete tem **número D** e a
    linha no `wiki/03-phases.md` entra **no mesmo commit** (o lote G149–G152 fechou sem as
    duas). Processo filho que o teste lança **não herda** o censo nem o worker da corrida de
    fora, e arquivo de teste gerado para o runner aninhado leva um `pytest.ini` ao lado (sem
    ele a raiz vira `C:\Users\<user>` e a coleta varre o Temp — a serial da D179 caiu assim).

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**
antes da suíte: `varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.confere()`,
`tests/test_folhas_g77.py`, `tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py`,
`tests/test_carimbo_mapa_g112.py`, `tests/test_normas_catalogo.py`,
`tests/test_galpao_indice_g93.py`, `tests/test_suite_paralela_d164.py`,
`tests/test_auditoria_g137_g142_d172.py`, `tests/test_auditoria_g143_g148_d176.py`,
`tests/test_auditoria_g149_g153_d179.py`, `tests/test_fallback_folha_g145.py`,
`tests/test_fallback_get_g150.py`, `tests/test_titulo_carimbo_g151.py`,
`tests/test_veredito_folha_g152.py`, `tests/test_piso_memoria_g153.py` e
`tests/test_estaca_g149.py` — mais o portão próprio de cada fonte que o goal tocar. Goal que
muda folha do galpão roda também o portão do galpão **isolado e serial**
(`GALPAO_AUDITORIA=1 pytest -s tests/test_indice_disco_rodada_g102.py::test_10_portao_rodada_real_galpao_na_auditoria`,
~11 min).

**Otimização de conta (D158):** só com prova de número idêntico. **O verbete é parte da
entrega.** **Uma fonte só:** dado que o cliente recebe mora na produção.

---

## Ordem e dependência

Estritamente sequencial, sem ramificação:

1. **G154** — FECHADO (D180, `4018471`).
2. **G155** — retoma o WIP; parte de `4018471`.
3. **G156** — parte do commit do G155.
4. **G157** — parte do commit do G156 (lê o que os outros escreveram).

---

# GOALS

## G154 · O material do modelo que decide veredito sem ninguém declarar

**FECHADO** em 2026-09-17 (D180, commit `4018471`). Não reexecutar; mantido como registro.

**Prioridade: alta.**

**Medido.**
- `projeto_spec.novo()` (`:125`) cria **todo** spec com `fundacao.fck = 25e3` e
  `fundacao.fyk = 500e3`; o wizard **não pergunta** nenhum dos dois (`wizard.py`: só
  `sigma_solo`, `tipo` e `estaca` escrevem em `fundacao`, `:317-343`).
- Leitores medidos: `estaca_parametros_g143.resolver_estaca_metalica` (bloco herda com a origem
  "material do projeto" — o D179 corrigiu o **texto** para "pode ser o valor do modelo
  PS.novo — confirmar", **não** a origem); `fundacao_edificio.py:352,427,666,747,756`
  (`spec_fundacao.get("fck", materiais["fck"])` — herda do material do prédio);
  `fundacao_sapata_corrida.py:173` (`spec_fundacao.get("fck", 25e3)` — **25 MPa calado**);
  `projeto_spec.py:598` (valida > 0) e `rodar_galpao.py:849`.
- O G149 mediu (bloco n=2, N=600): **fck 25→15 MPa vira a biela de OK para REPROVA**. O valor
  do modelo decide veredito.
- Não medido: se o `fyk`, o `cobrimento` e o `phi_barra` do modelo (`:125-127`) mudam veredito;
  quantos specs do repo (`projects/*`) têm o `fck` igual ao do modelo.

**Entregar.**
1. Medir por injeção, em cada porta (spec do metálico, wizard, prédio, sapata corrida da casa),
   se `fck/fyk/cobrimento/phi_barra` da fundação mudam veredito — tabela antes/depois.
2. Distinguir **declarado** de **modelo**: o spec tem de saber de onde veio o material da
   fundação (proveniência ao lado do número ou pergunta no wizard). Declara-ou-recusa (D102),
   por item, com motivo; a sapata corrida deixa de calar 25 MPa.
3. A folha e o memorial dizem a origem do material que a conta usou.

**Aceite.** Vermelho por injeção em cada porta (modelo sem confirmação → declarado como modelo
na folha/memorial, ou recusa nomeada; declarado → o número do spec com "declarado"); as specs
do repo seguem rodando (G102 casa/prédio verdes; o galpão no portão de auditoria se a folha do
galpão mudar); PNG olhado.

**Não fazer.** Escolher outro fck "melhor"; mudar a classe de agressividade; tirar o valor do
modelo sem dar ao wizard a pergunta (o caminho do usuário não pode quebrar).

**Armadilhas.** `novo()` escreve o número antes de qualquer resposta — comparar com 25e3 não
distingue declarado de modelo (o usuário pode declarar 25). A proveniência tem de nascer onde o
número nasce.

---

## G155 · As folhas do prédio e da casa que não dizem que reprovaram

**Prioridade: média-alta.**

**Estado de partida (medido em 2026-09-17, 12:40) — RETOMAR, não recomeçar.** Uma execução
anterior do G155, sobreposta ao G154, deixou WIP sem commit sobre `4018471`: 16 arquivos
(`desenho_alvenaria`, `desenho_casa_residencial`, `desenho_climatizacao`, `desenho_concreto`,
`desenho_coordenacao`, `desenho_eletrico`, `desenho_eletrico_residencial`,
`desenho_escada_edificio`, `desenho_fundacao_edificio`, `desenho_hidraulica`,
`desenho_incendio`, `desenho_pavimento`, `desenho_piso`, `edificio_adapter`,
`veredito_folha_g152` com `veredito_para_folha_svg`/`injetar_veredito_no_svg`,
`tests/test_folhas_g77.py` com 2 isenções) e o novo `tests/test_veredito_folha_g155.py`. Nesse
WIP: `test_veredito_folha_g155` + `g152` **10 passed**; `test_guardas_um_eixo_g83` +
`test_folhas_g77` **96 passed** (o D180 registrou que o `BASELINE_G83` quebrava antes; hoje
está verde — conferir se foi triado com motivo, não só atualizado). **Não medido:** a regra do
lote, a suíte inteira, os PNG olhados, o verbete e a linha de fase. O goal começa lendo
`git diff`, confere cada disciplina da lista abaixo contra o que já existe, completa o que
faltar e fecha pelo protocolo. Esses 17 caminhos são o único WIP permitido na checagem de
entrada.

**Decidido para este goal:** disciplina sem veredito no resultado (nem `ATENDE` nem
`atende_global`) **não ganha** veredito na folha — a folha diz "veredito não disponível no
resultado" e o caso vai ao verbete (regra conservadora). Folha de conferência interna da casa
também declara.

**Medido.**
- O G152 cobriu os `techdraw_*` e a rota SVG do **galpão**. Os emissores do prédio/casa
  (`desenho_*.py`) por grep: `desenho_fundacao_edificio` **0** "REPROVA", `desenho_eletrico` 0,
  `desenho_hidraulica` 0, `desenho_incendio` 0, `desenho_climatizacao` 0,
  `desenho_coordenacao` 0, `desenho_piso` 0; têm alguma marca: `desenho_escada_edificio` 13,
  `desenho_casa_residencial` 7, `desenho_eletrico_residencial` 6, `desenho_pavimento` 4,
  `desenho_alvenaria` 3, `desenho_concreto` 3.
- O veredito do prédio existe por disciplina (`gestao_edificio.disciplinas_pacote`,
  `:758-798`, "veredito": ATENDE/REPROVA com `reprovados`); o adaptador emite as folhas em
  `edificio_adapter.py:898` (pavimento), `:982` (fundação), `:1095` (elétrico), `:1125`
  (hidráulica), `:1152` (incêndio).
- Não medido: o que cada folha do prédio/casa diz com o veredito reprovado **injetado**; se as
  marcas existentes (escada 13, pavimento 4) nomeiam os gates ou só a peça.

**Entregar.** Medir disciplina por disciplina (prédio e casa) com o veredito reprovado
injetado; a folha reprovada declara o veredito e os gates, lidos do resultado pela **fonte
única do G152** (`veredito_folha_g152`, estender, nunca copiar). ATENDE byte-idêntica.

**Aceite.** Vermelho por injeção em cada disciplina com folha; ATENDE byte-idêntica (hash);
PNG olhado de cada folha reprovada; `test_veredito_folha_g152` e o G102 casa/prédio verdes.

**Não fazer.** Parar de emitir a folha reprovada; decidir gate na folha; mudar o carimbo do
galpão (já fechado).

**Armadilhas.** O prédio tem dois dialetos de veredito (`ATENDE` por disciplina e
`atende_global` do pacote) — a fonte única do G152 já lê os dois. A casa tem folhas de
conferência interna (sem código no índice): também dizem.

---

## G156 · A citação normativa com número e sem item

**Prioridade: média.**

**Estado de partida:** commit do G155 no `git log`, árvore limpa.

**Decidido para este goal:** frase que não dá para conferir porque a norma **não está no
acervo** ou a página é ilegível entra na tabela como "não conferível" (com o motivo) e fica
como está; frase de fonte que não é NBR (livro, catálogo) fica fora da lente, com a regra
escrita no teste. Nenhuma das duas para o goal.

**Medido.**
- O D179 achou `FS 3,0 "NBR 6122"` em resultado, memorial, folha, wizard e `validar` — a página
  diz 2,0 (6.2.1.2.1). Viveu do D38 (2026-07-11) ao D179 porque nenhuma lente confere número
  citado contra a página.
- AST heurística (literais com `NBR nnnn` + número e **sem** padrão de item `n.n`/Tabela/Anexo)
  nos módulos de produção: **25 literais em 21 arquivos** — por ex. `climatizacao_nbr16401.py:87`
  ("27*n + 1,5*A (NBR 16401-3)"), `desempenho_nbr15575.py:295` ("0,6 mm"),
  `incendio_edificio.py:120` ("3,0 m < H <= 5,0 m ... NBR 10897"), `fogo_nbr14323.py:80`,
  `fundacao_sapata_corrida.py:164`, `validacao.py` 2, `techdraw_hidraulica.py` 2. A heurística
  é **ruidosa** (docstrings, números que não são da norma); a triagem é o goal.
- A lente do D179 (`test_auditoria_g149_g153_d179::test_03`) só cobre "3,0" + "NBR 6122".
- Achado de 2026-09-17 ao catalogar a F152 (**entra na triagem mesmo que a heurística não o
  pegue**, por ser comentário): `instalacao_eletrica.py:123` atribui "os diametros externos dos
  cabos" à **NBR NM 280** (F151, que trata do condutor). O diâmetro externo do cabo isolado está
  na **NBR NM 247-3:2002** (F152), Tabela 1 (p.5 da norma / p.12 do arquivo; 2,5 mm² classe 1 =
  3,2 a 3,9 mm, conferido na imagem). Corrige só a atribuição; `_ELETRODUTO_POR_SECAO` não muda.
  A lente cobre também "NBR NM nnn".

**Entregar.** Lente AST (baseline nos dois sentidos) de toda frase que atribui número a NBR:
cada uma com o **item** e triada contra a **imagem da página** do acervo (tabela: frase, item,
página, confere/diverge/não é da norma). Divergência: corrige a **atribuição** (como o D179) e
lista para o usuário; nunca troca o número.

**Aceite.** Baseline triada; injeção de citação sem item reprova nomeando arquivo:linha;
divergências no verbete com a página; nenhum número de conta mudou (suíte com os mesmos
resultados).

**Não fazer.** Trocar número "para bater com a norma"; confiar no OCR sem olhar a imagem;
citar de memória.

**Armadilhas.** O OCR (F132) tem erros ("uilizado", "deteminacao"): procure pelo item, confira
na imagem. Muitas frases são remissão ("ver NBR 6118"), não atribuição de número — triagem,
não regra cega.

---

## G157 · O verbete sem número e a fase sem linha

**Prioridade: média-baixa.**

**Estado de partida:** commit do G156 no `git log`, árvore limpa. A guarda cobre também os
goals G154–G156 (já têm D) e o próprio G157.

**Medido.**
- `wiki/04-decisions.md`: os verbetes do G149, G150, G151 e G152 têm cabeçalho `## G1xx - …`
  **sem número D**; só o G153 virou D178. Nenhum dos cinco goals escreveu em
  `wiki/03-phases.md` (o D179 escreveu as linhas na auditoria).
- O D178 fechou pela corrida A e **mudou código depois** (fix do censo + comentário) sem rodar
  a suíte de novo; a auditoria D179 rodou.
- Não há guarda que cobre isso: o D176 e o D179 acharam a falta lendo o arquivo.

**Entregar.** Guarda (teste) que lê `04-decisions` e `03-phases`: todo goal fechado no
`git log` desde o G149 tem verbete **com número D** e linha na fase; baseline nos dois sentidos
(goal sem verbete reprova; verbete de goal inexistente reprova). Numerar os quatro verbetes sem
D **sem reescrever o conteúdo** (links `[[04-decisions#…]]` conferidos).

**Aceite.** Vermelho por injeção (verbete sem D, fase sem linha) em `tmp_path`; os links da
wiki resolvem; nenhum teste de conteúdo mudou.

**Não fazer.** Reescrever verbete antigo; renumerar D já existentes.

**Armadilhas.** O D178 (G153) e o D179 (auditoria) já existem: os quatro verbetes recebem
números novos depois do último D, e o índice diz a qual goal cada um pertence (a ordem dos
números não é a ordem dos goals).
