# Backlog de goals executáveis — pós-G131 (2026-09-13)

Fila **ABERTA**. Cinco goals (G132–G136). As filas anteriores estão fechadas e ficam apenas
como registro — não reexecute nada de lá: `BACKLOG-GOALS.md` (G78–G88),
`BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`, `BACKLOG-GOALS-G107-G112.md`,
`BACKLOG-GOALS-G114-G118.md`, `BACKLOG-GOALS-G120-G124.md` e `BACKLOG-GOALS-G126-G130.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-13 na branch `feat/tipologias-e-verticais-de-projeto`,
na auditoria do lote G126–G130 (G131, verbete D157). O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis. A auditoria do G131 achou a classe do G125 pela
terceira vez, agora do lado da entrega: **o documento declarava um valor e a conta usava
outro.** Corrigiu os três casos que mediu (cimento topo × payload, edição topo × payload,
piso de içamento declarado numa casa sem içamento). Este arco vai atrás do mesmo desencontro
onde ele ainda mora: a edição que se declara inteira trocando dois pontos, o concreto que a
viga protendida usa sem o projeto dizer, a pergunta que nenhuma conta lê, a declaração
escrita à mão e a fctd com γc fixo.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

**Nenhuma norma ausente para este arco.** Conferidas por identificador: NBR 6118:2014
(F016), NBR 6118:2023 (F150), NBR 6118 Emenda 1:2026 (F098) e NBR 9062:2017 (F137).

- **Não conferido na página:** a Tab. 12.1 da 6118 (γc por combinação), que o G136 cita.
  Olhe a imagem da F016 antes de escrever qualquer valor (convenção 3).

---

## Convenções que todo goal deste repo segue

1. **Baseline nos dois sentidos**, e toda lente nova com teste que fica **vermelho quando o
   defeito é injetado**.
2. **Injeção em `tmp_path`**, nunca mutando o repo.
3. **Substring → parse → renderizar.** Para norma e para folha: **olhe a imagem**.
4. **Saturação silenciosa**, incluindo `OK` por item que não chega ao veredito (G113).
5. **Asserção tautológica**, incluindo teste que confere um literal contra ele mesmo (G119).
6. **Três aceites por folha:** está certa, sai no manifesto, diz o que desenha.
7. **Instrumento tem de conseguir acusar** (G119) — e acusar **por parte** (G125).
8. **Constante "medida" que a produção não lê é comentário** (G119).
9. **A lente parte de onde o dado é PRODUZIDO** — a conta, o emissor — e confere a citação
   contra ele (G125).
10. **O resumo da suíte se lê inteiro antes de fechar** (G125) — e a lista de arquivos da
    suíte inclui as subpastas `tests/branches` e `tests/trunk` (289 arquivos; `tests/test_*.py`
    sozinho pega 246).
11. **NOVO (G131) — injete o valor em cada lugar de entrada que o produto aceita.** O G126
    conferiu as peças só sem cimento, onde o topo do project-spec e o payload do turnkey
    coincidem por acaso. Com CPII no topo, o pacote dizia CPII e a conta usava o piso; com
    CPII no payload, o contrário. Portão de declaração injeta em **cada** entrada (topo do
    project-spec, `turnkey.<disciplina>`, `ProjetoSpec`/wizard), confere **toda** peça contra o
    que a conta gravou no resultado, e divergência entre entradas levanta. "Não se aplica" é
    um terceiro valor declarado, nunca o piso de uma conta que não existe.

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**:
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_sequencia.confere()`,
`varredura_constantes_orfas.confere()`, `tests/test_folhas_g77.py`,
`tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py`,
`tests/test_carimbo_mapa_g112.py` e `tests/test_normas_catalogo.py` — mais o portão próprio
de cada fonte única que o goal tocar (`test_edicao_nbr6118_g123.py`,
`test_edicao_tipologias_g128.py`, `test_cimento_nbr6118_g126.py`,
`test_fctm_fonte_unica_g127.py`).

**Otimização de conta (D158):** só com prova de número idêntico — hash do resultado inteiro
antes e depois, `==` contra a implementação anterior e o vermelho de uma reordenação. O molde
está em `tests/test_pilar_solver_equivalencia_d158.py` e `tests/test_fsm_cache_d158.py`.

**O verbete é parte da entrega.** **Uma fonte só:** dado que o cliente recebe mora na
produção; lente e teste importam de lá.

---

## Ordem e dependência

- **G133** é o único que toca veredito hoje. Faça-o primeiro.
- **G135 antes do G132.** Com a declaração da edição escrita à mão em 22 cópias e 46 rótulos,
  redesenhar o carimbo seria editar dezenas de lugares.
- **G134** e **G136** são independentes.

---

# GOALS

## G133 · A viga protendida num concreto que o projeto não declarou

**Prioridade: alta.** Toca veredito da viga de cobertura do galpão de concreto.

**Medido (G131):**
- `galpao_concreto.py:222-223` chama
  `vp.dimensiona_viga_protendida({"vao": vao, "fck": max(fck, 40e3), "q": w_beam})`. Com o
  projeto em C30, a viga é calculada em **C40**.
- `viga_protendida.py:154`: `fckj = cfg.get("fckj", fck)` — a verificação no ato da
  protensão usa o fck de 28 dias. O `galpao_concreto` não passa `fckj`.
- Função real, galpão de concreto de vão 15 m em C30: `tipo_viga = "protendida"`; no ato,
  `lim_comp = -28000 kN/m²` (= 0,70 × 40 MPa: fck e fckj = 40 MPa). O `relatorio_pt` diz
  "C30" e "VIGA DE COBERTURA (protendida): secao 20x60 cm ; 4 cordoalhas Ø12,7 -> ATENDE"; o
  `executivo_concreto.memorial` **não menciona C40**.
- O relatório próprio da viga diz "[A CONFIRMAR: fckj na idade da protensao, perdas (9.6.3),
  classe de agressividade.]" (`viga_protendida.py:233`). **Não medido:** se esse aviso chega
  ao memorial e às folhas do galpão.
- **Não medido:** quantos casos do repo mudam de veredito com o fck do projeto e o fckj na
  idade de transferência.

**Entregar:** o fck da viga protendida e o fckj de transferência passam a ser dados
**declarados** (entrada, com a ausência dita) — nunca `max(fck, 40e3)` calado. Se o
framework precisar de um piso para seguir, ele é declarado na folha e no memorial como piso.
Folha e memorial dizem o concreto que a **conta** usou.

**Aceite:** vermelho por injeção (spec em C30 que sai verificado em C40 sem declaração
reprova); os casos do repo listados um a um no verbete, com o número antes e depois; a
convenção 11 (injetar em cada entrada do produto).

**Não fazer:** escolher o fck de fábrica nem a idade de protensão de projeto nenhum.

---

## G135 · A declaração da edição escrita à mão

**Prioridade: média.** Pré-requisito do G132.

**Medido (G131):**
- O texto do carimbo (`"assumida 2014"` / `"Projeto calculado pela NBR 6118"`) aparece fora
  de `edicao_nbr6118_g123` **22 vezes em 6 arquivos**: `executivo_concreto.py`
  184, 185, 187, 235, 236, 238; `caderno_encargos.py` 245, 246, 248, 295, 297;
  `pacote_legal.py` 316, 317, 319, 529, 531; `techdraw_concreto.py` 360, 361, 363;
  `rodar_galpao.py` 1575, 1576; `relatorio_calculo.py` 521. Quase todas moram em fallback de
  `except`, que dentro do pacote nunca dispara.
- `"6118:2014"` escrito à mão, fora de comentário: **46 linhas em 22 arquivos**
  (`viga_continua` 4, `relatorio_calculo` 4, `compatibilizacao` 4, `caderno_encargos` 4,
  `pilar_concreto` 3; 2 em `viga_protendida`, `viga_concreto`, `viga_baldrame`,
  `techdraw_concreto`, `pilar_continuo`, `pacote_legal`, `laje_concreto`, `fundacao_sapata`,
  `executivo_concreto`, `escada_concreto`; 1 em `viga_baldrame_edificio`, `rodar_galpao`,
  `puncao_nbr6118`, `perdas_protensao_nbr6118`, `fissuracao_nbr6118`, `desenho_pavimento`,
  `desenho_concreto`). Exemplo: `fundacao_sapata.py:662`, "PARTE B - CONCRETO ARMADO (NBR
  6118:2014)".
- O G131 removeu as mesmas cópias da **linha de cimento**; o G127 fez isso para a conta da
  fct,m (`fctm_nbr6118_g127.confere_copias` é o molde).

**Entregar:** a declaração da edição vem só da fonte única; censo de cópias do texto fora
dela, com baseline nos dois sentidos; cada `"6118:2014"` escrito à mão triado — carimbo de
cálculo (passa a vir da fonte) ou citação histórica (isenta com motivo).

**Aceite:** vermelho por injeção (cópia do carimbo colada num módulo em `tmp_path` acusa);
sem a chave, a saída das três tipologias é byte-idêntica.

---

## G132 · A edição que se declara inteira trocando dois pontos

**Prioridade: alta.** Latente: nenhum project-spec do repo declara a chave, mas o primeiro
que declarar sai com declaração falsa.

**Medido (G131):**
- `edicao_nbr6118_g123.MODULOS_COM_TROCA` tem **2 pontos**: `premoldado_nbr9062` 12.3.3
  (fckj do içamento) e `compatibilizacao` 13.2.5.1 (furo em viga). Todo o resto calcula pela
  2014 com qualquer chave.
- Com a chave, `carimbo_edicao("2023+Em1")` diz "Projeto calculado pela NBR 6118:2023 +
  Emenda 1:2026 (edicao declarada no projeto)" e `sufixo_folha_edicao` põe
  " (NBR 6118:2023 + Emenda 1:2026)" no título da folha.
- **Casa real** (spec persistido, `norma_6118_edicao: "2023+Em1"` injetada em memória): as 4
  folhas PE-CO (`planta-formas.svg`, `armacao-vigas-pilares-casa.svg`,
  `detalhes-concreto-casa.svg`, `fundacao-locacao-formas-casa.svg`) e o caderno dizem
  2023+Em1. Na **mesma entrega**, `reports/adapter-result.json` traz "SAPATA - PARTE B
  (CONCRETO ARMADO) - NBR 6118:2014" — e é o memorial que está certo: nenhuma conta da casa
  troca com a chave.
- O portão do G128 (`tests/test_edicao_tipologias_g128.py::_confronto_folha_edicao`) compara
  a folha com a chave de **entrada**, não com a conta.
- **Não medido:** prédio e galpão com a chave (espera-se a mesma forma; meça).

**Entregar:** a peça declara a edição que a **sua** conta usou. Com a chave em 2023+Em1, peça
sem conta que troca declara 2014; o carimbo do projeto diz a composição (quais itens seguem a
2023+Em1, o resto pela 2014) — tudo da fonte única. O portão parte da conta
(`MODULOS_COM_TROCA` × o que a peça calcula), não da chave.

**Aceite:** rodada real das três tipologias com a chave: nenhuma contradição entre folha,
memorial e pacote na mesma entrega (vermelho por injeção: folha que diz 2023+Em1 numa peça
sem conta que troca reprova); sem a chave, byte-idêntico.

**Não fazer:** migrar mais itens para a 2023; virar a chave em projeto nenhum do repo.

---

## G134 · A pergunta do cimento que nenhuma conta lê

**Prioridade: média.** Classe "constante que a produção não lê é comentário" (convenção 8),
agora numa pergunta ao usuário.

**Medido (G131):**
- `wizard.py:197` pergunta "Tipo de cimento do concreto p/ o fckj do icamento";
  `ProjetoSpec.cimento` (`projeto_spec.py:159`) e `to_rodar_params` (`projeto_spec.py:941`)
  repassam `p["cimento"]` ao `rodar_galpao`.
- Censo por AST: `to_rodar_params` escreve **30 chaves**; 2 não aparecem como literal em
  `rodar_galpao.py` — `norma_6118_edicao` (lida de forma indireta por `edicao_de_spec`,
  `rodar_galpao.py:1554`: **não** é morta) e `cimento` (**zero leitores**). O `rodar_galpao` é
  o galpão **metálico**, sem içamento de pré-moldado.
- O içamento só é calculado pelo `galpao_concreto` dentro do turnkey, cuja entrada é o
  project-spec (topo ou `turnkey.concreto`, ligados no G131) — não o `ProjetoSpec`.
- A varredura de campos mortos do wizard (S39) conta `p[chave] = ...` como campo fiado; por
  isso não acusou.

**Entregar:** a pergunta sai do fluxo metálico com o motivo escrito, ou passa a chegar a uma
conta que a usa; e um censo das chaves de `to_rodar_params` sem leitor (direto ou por função
de leitura declarada), com baseline nos dois sentidos.

**Aceite:** vermelho por injeção (chave nova em `to_rodar_params` sem leitor reprova); a
triagem das 30 chaves no verbete.

**Não fazer:** tirar `cimento` do project-spec do turnkey — lá ele é lido (G131).

---

## G136 · A fctd em seis cópias, com γc escrito à mão

**Prioridade: baixa.** A continuação do G127 um degrau abaixo.

**Medido (G131):**
- Depois do G127, a fct,m mora numa fonte, mas `fctd = 0,7 · fctm / 1,4` ficou em **6
  módulos** com o `1.4` literal: `estaca_profunda.py:387`, `fundacao_sapata.py:680`,
  `laje_concreto.py:440`, `pilar_concreto.py:407`, `viga_baldrame.py:46`,
  `viga_protendida.py:127`. O `base_chumbador.py:99` usa uma constante própria (`GC`).
- O D153 manteve a fctd nos módulos de propósito ("é de outra cláusula"), e
  `fctm_nbr6118_g127` já expõe `fctk_inf`.
- **Não medido:** a Tab. 12.1 da 6118 na página da F016; se algum destes módulos é chamado
  numa combinação que não a normal.

**Entregar:** `fctd = fctk,inf / γc` numa fonte, com γc como parâmetro e o valor da
combinação normal declarado a partir da página; as 6 cópias passam a chamá-la; cópia nova
reprova.

**Aceite:** número bit a bit igual (C20, C50, C55, C60, C90) módulo a módulo; vermelho por
injeção.

**Não fazer:** mudar o γc de caso nenhum.
