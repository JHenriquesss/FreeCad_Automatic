> **FILA CONSUMIDA (2026-09-12).** Os cinco goals foram executados e auditados no G119
> (verbete `wiki/04-decisions.md#D145`). Este arquivo fica como registro — **não reexecute
> nada daqui**. A fila aberta é `BACKLOG-GOALS-G120-G124.md`.
>
> | goal | entregue | verbete |
> |------|----------|---------|
> | G114 | caderno reusa o turnkey: um `tk.rodar` só | D142 |
> | G115 | armação de pilar por trecho de lances iguais (42 no prédio) | D143 |
> | G116 | inventário do impacto 2014 → 2023+Em1 (51 itens) | D141 |
> | G117 | camada de texto da F150 decodificada (260 p.) | D140 |
> | G118 | PE05 do aço com número: o topo travava nos tirantes | D144 |
>
> Corrigido na auditoria (D145): o medidor de bytes desconhecidos que não podia acusar (e
> sob ele "fck ≤ 50 MPa" saía "fck ± 50 MPa"), a guarda de intervalo que nunca reprovava,
> o mapa de trechos sem confronto, a exceção nova na PE05 sem contraventamento de cobertura,
> o código morto da fileira e a âncora de pesos que a produção não lia.
>
> **Medido depois do G114:** `tests/test_indice_disco_rodada_g102.py`, que morreu quatro
> vezes por memória no G113, **completou** — 6 passed em 1230 s.

# Backlog de goals executáveis — pós-G113 (2026-09-11)

Fila **ABERTA**. Cinco goals (G114–G118). As filas anteriores estão fechadas e ficam apenas
como registro — não reexecute nada de lá: `BACKLOG-GOALS.md` (G78–G88),
`BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md` e `BACKLOG-GOALS-G107-G112.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-11 na branch `feat/tipologias-e-verticais-de-projeto`,
na auditoria do lote G107–G112 (G113, verbete D139). O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis. Este arco tem uma frente nova e grande: o
framework calcula pela **NBR 6118:2014**, e o acervo agora tem a **2023 + Emenda 1:2026**, que
juntas são a norma vigente. O G116 mede o impacto — **não migra**. Migrar a base normativa é
decisão do usuário, e ela precisa do número na mão.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

Nenhuma norma ausente.

- **F150 — NBR 6118:2023, Versão corrigida 2 (30.01.2024).** A **camada de texto está
  embaralhada** (cifra de fonte: "Todos os direitos" sai `7RGRVRVGLUHLWRV`; espaços entre
  palavras perdidos; fórmulas sem texto útil). A página **renderiza correta**. Busca por texto
  e NotebookLM leem lixo até o G117.
- **F098 — Emenda 1:2026.** Texto **legível**. 62 instruções Substituir/Incluir em 51 itens.

---

## Convenções que todo goal deste repo segue

1. **Baseline nos dois sentidos**, e toda lente nova com teste que fica **vermelho quando o
   defeito é injetado**.
2. **Injeção em `tmp_path`**, nunca mutando o repo.
3. **Substring → parse → renderizar.** Para norma com texto ilegível: **leia a página
   renderizada**, nunca a camada de texto.
4. **Saturação silenciosa** — incluindo a variante do G113: resultado por item (`OK` por
   painel) que **não chega ao veredito** global. Todo `OK` novo entra num portão.
5. **Asserção tautológica** — incluindo teste que **reimplementa a fórmula** que devia chamar.
6. **Três aceites por folha:** está certa, sai no manifesto, diz o que desenha.

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**:
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_sequencia.confere()`,
`tests/test_folhas_g77.py` (censo de folhas × `FOLHAS`), `tests/test_alcancabilidade.py`,
`tests/test_guardas_d86_g69.py` (censo das guardas `confere_*`/`verifica_fechamento*` ×
`TRIADAS_G69`), `tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py` e
`tests/test_carimbo_mapa_g112.py`.
**Por que a lista nominal:** o G110 criou `desenho_pavimento.confere_armacao_pilares` e o lote
G107–G112 foi entregue com o censo das guardas VERMELHO — a guarda nova entrou sem triagem em
`TRIADAS_G69` e sem a linha de origem dos dois lados no cabeçalho do teste (regra D86/D87).
Quem rodou "os baselines" de memória não rodou esse. Guarda nova (`confere_*`) exige as duas
coisas, e o censo é o que impede a lista de virar silêncio.

**Regra nova: o verbete é parte da entrega.** Nos dois últimos lotes, 9 de 13 goals chegaram
sem verbete em `wiki/04-decisions.md` e a auditoria os escreveu. Goal sem verbete não está
fechado.

**Uma fonte só.** Dado que o cliente recebe mora na produção; lente e teste importam de lá.
O G112 entregou a tabela canônica dentro de um script avulso e uma cópia de 150 linhas na
produção (corrigido no G113, D138).

---

## Ordem e dependência

- **G117 antes do G116:** o G116 precisa ler a 2023, e hoje só dá pela imagem.
- **G114 e G115** são independentes e podem ir a qualquer momento.
- **G118** é pesado (FreeCAD gráfico, modelo 3D): feche outros apps antes.

---

# GOALS

## G114 · O portão do G102 leva 923 s porque o caderno roda o turnkey duas vezes

**Prioridade: alta.** Custo da suíte e do Loop.

**Medido (G113):**
- `tests/test_indice_disco_rodada_g102.py` escreve `CUSTO_MEDIDO_SEG` do galpão: **38,5 s →
  923 s** depois do G107 (o galpão passou a rodar com `generate_2d=True`).
- A causa, escrita no próprio teste: `caderno_turnkey.montar_caderno` chama
  `tk.rodar(spec, out_dir)` (`:343`) — e o adaptador do galpão **já tem** o resultado do
  turnkey (`turnkey_result`, que ele recebe no hook).
- O teste roda na suíte non-build: ~16 min a cada rodada completa.
- **Medido na auditoria G113, e não é só tempo:** este arquivo derrubou **quatro** execuções
  por falta de memória nesta máquina (8 GB, 1,5–1,9 GB livres) — em lotes de 50, 22 e 11
  arquivos e, por fim, **sozinho**, morrendo antes de escrever o primeiro ponto (arquivo de
  saída com 0 byte). Sem órfãos em nenhuma delas.
- **Consequência:** a suíte completa **não fecha** nesta máquina enquanto ele existir na forma
  atual, e o `CUSTO_TETO_SEG` de 1800 s não mede isso — ele afere tempo, não memória. O aceite
  do G114 passa a incluir **caber**: o portão tem de rodar junto dos outros, ou o teto tem de
  ser de memória também.
- Dois resíduos do G108 no mesmo módulo: a âncora da regra de pesos é **900 s** (estimativa do
  T13), e o G109 mediu o aço em **~578 s**; e `tests/test_caderno_pesos_g108.py` recalcula a
  fração com fórmula própria em vez de chamar `caderno_turnkey._stage_timeout`.

**Entregar:**
- `montar_caderno` aceita o resultado do turnkey já calculado e não recalcula quando o recebe;
  o adaptador passa o que tem. Sem mudar o resultado (mesmas pranchas, mesmo caderno).
- A âncora dos pesos passa a ser o número medido (D133), com a origem escrita.
- O teste do G108 chama a função de reserva real.

**Aceite:** custo medido antes/depois e escrito no teste (`CUSTO_MEDIDO_SEG`); a rodada do
galpão produz o mesmo manifesto (lista de artefatos idêntica) com um `tk.rodar` só — conte as
chamadas por injeção. Se não cair, o resultado negativo vai para o verbete.

---

## G115 · A armação de pilar do prédio mostra só o lance de base

**Prioridade: alta.** A gaiola dos andares de cima não chega ao cliente.

**Medido (G113):**
- `desenho_pavimento` (G110) desenha uma fileira por pilar, do **lance de base**
  (`lances[-1]`). O rodapé da folha declara isso — não é silêncio.
- No spec persistido do prédio (`projects/edificio-multipavimento`), **8 dos 12 pilares**
  mudam de seção ou de As entre lances (9 lances cada). A casa tem 1 lance — não é afetada.
- A 18.4 da 2023 é idêntica à da 2014 (conferido pela imagem no G113, D136).

**Entregar:**
- Uma fileira por **trecho de lances iguais** (mesma seção e mesmo As): "lances 1–5: 19×30,
  As 2,28 | lances 6–9: 19×40, As …". Pilar sem mudança continua com uma fileira.
- Drawing-vs-data: a folha soma exatamente os lances de cada pilar do resultado.

**Aceite:** vermelho por injeção (lance com seção trocada no dado → a folha antiga reprova na
lente); `confere_folha_svg`; renderizada e olhada (a altura da folha cresce com as fileiras —
lembre do G77: folha de altura fixa com conteúdo que cresce).

---

## G116 · O impacto de migrar a NBR 6118 de 2014 para 2023 + Emenda 1

**Prioridade: alta. Este goal mede e escreve — não muda cálculo.** Depende do G117.

**Medido (G113):**
- O framework calcula pela 2014 (F016). A vigente é a 2023 (F150) + Em1:2026 (F098).
- A Em1 traz **62 instruções em 51 itens**. Entre eles, itens que o framework implementa:
  **15.7.3** (redução de rigidez, citando galpões), **15.8.1** (λ ≤ 200, exceto pilar pouco
  comprimido com Nd < 0,10 fcd Ac), **17.3.5.2.4** (As + A's ≤ 4 % Ac fora das emendas),
  **18.3.x**, 17.4.x, 19.5.x. Lista completa extraída do texto da F098.
- A 18.4 (pilares) **não muda** — conferida pela imagem.
- **Não medido:** as diferenças 2014 → 2023 **fora** da emenda (a 2023 é uma edição nova,
  não só a 2014 corrigida).

**Entregar:**
- Um inventário escrito (`wiki/`), item a item: artigo, o que diz a 2014, o que diz a 2023+Em1,
  **onde o framework o implementa** (arquivo:linha), e se o número/regra muda.
- Para cada item que muda: um caso do repo que mostre o efeito (o mesmo pilar/viga pelas duas
  regras), sem alterar o módulo.

**Aceite:** o inventário cobre os 51 itens da Em1 e os itens que o framework cita da 6118
(varredura por AST/grep das citações "6118"/"17.3"/"15.8" nos módulos). Cada citação do
framework tem uma linha no inventário — nos dois sentidos.

**Não fazer:** trocar a base normativa de nenhum módulo. É decisão do usuário, e ela vem
depois deste número.

---

## G117 · A camada de texto da NBR 6118:2023 (F150)

**Prioridade: média.** Destrava o G116 e a consulta à norma.

**Medido (G106/G113):**
- Corpo com cifra de fonte: letras ASCII deslocadas por um valor fixo ("7"→"T", "R"→"o"),
  mais uma tabela curta para acentos ("k"→"â", "t"→"í", "m"→"ã", "p"→"é"…); espaços entre
  palavras perdidos em muitos parágrafos; fórmulas sem texto útil.
- As três cópias recebidas tinham a **mesma** cifra — outra cópia não resolve.
- Não há Tesseract instalado na máquina.

**Entregar — uma das duas, escrita:**
- **(a)** decodificar a cifra num `.txt` local (fora do git: `fontes/` é ignorado), com a
  tabela de decodificação escrita e os espaços reconstruídos; ou
- **(b)** OCR das páginas renderizadas (se o usuário instalar o Tesseract).

**Aceite:** amostra de 10 páginas — o texto produzido bate com a página renderizada e lida
(regra 3), incluindo uma de fórmula. Declarar o que não sai (fórmulas, tabelas).

**Não fazer:** subir ao NotebookLM sem o OK do usuário — é publicar num serviço externo.

---

## G118 · A PE05 do aço trava no recompute

**Prioridade: média. Pesado.**

**Medido (G109, D133):**
- 16 de 17 pranchas do aço têm número por prancha (total ~578 s). A **PE05_CONTRAVENTAMENTO**
  deu timeout sistemático (2 × 1200 s no harness + 540 s no diagnóstico), travando no
  `doc.recompute()` da página. O build dela é instantâneo (1 página + 1 cota).
- A máquina tinha ~1 GB livre nas rodadas.

**Entregar:** a causa da trava — medida, não suposta: re-medir com folga de memória; se
repetir, fatiar o recompute (vista a vista) com o harness do G105 e achar o objeto que trava.

**Aceite:** a PE05 tem número, **ou** o objeto que trava está nomeado e o executivo sai sem
travar (a folha declara o que não pôde desenhar). Nunca estimar a PE05 pelas irmãs (D133).
