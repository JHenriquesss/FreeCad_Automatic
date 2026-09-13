# Backlog de goals executáveis — pós-G125 (2026-09-12)

> **FILA CONSUMIDA (2026-09-13).** Os cinco goals foram executados e auditados (G131,
> [[04-decisions#D157]]). Não reexecute. A fila aberta é `BACKLOG-GOALS-G132-G136.md`.
>
> | Goal | Verbete | Auditoria |
> |---|---|---|
> | G126 cimento declarado | D152 | pacote e conta liam o cimento de lugares diferentes; casa/prédio afirmavam piso sem içamento; catch-all e cópias da linha — corrigidos |
> | G127 fct,m em fonte única | D153 | bateu (99 valores HEAD == árvore, 9 fcks) |
> | G128 edição nas 3 tipologias | D154 | topo × payload: o payload vencia calado — corrigido; a chave carimba a edição inteira trocando 2 pontos — G132 |
> | G129 censo de colisões | D155 | bateu (portão vivo verde) |
> | G130 dívidas no pacote | D156 | bateu (18/24/30); byte corrompido no verbete — corrigido |

Fila ~~ABERTA~~ consumida. Cinco goals (G126–G130). As filas anteriores estão fechadas e ficam apenas
como registro — não reexecute nada de lá: `BACKLOG-GOALS.md` (G78–G88),
`BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`, `BACKLOG-GOALS-G107-G112.md`,
`BACKLOG-GOALS-G114-G118.md` e `BACKLOG-GOALS-G120-G124.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-12 na branch `feat/tipologias-e-verticais-de-projeto`,
na auditoria do lote G120–G124 (G125, verbete D151). O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis. A auditoria do G125 achou uma classe só, em
quatro lugares: **a lente olhava para onde o dado já estava declarado, e não para onde ele é
produzido.** Este arco vai aos lugares de produção — o default que ninguém declarou, a conta
copiada, a folha que ninguém confere, a exigência que ninguém verifica.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

**Nenhuma norma ausente para este arco.** Conferidas por identificador: NBR 6118 (F016 2014,
F150 2023, F098 Em1:2026), 16868, 17240, 5626, 10898, 15575, 5419, 15421, 7190, 9062,
10897, 16820, 5410, 6120, 15749 e 8681.

- Declarado no G125: NBR 8522 e 8965 **não** estão no acervo e **não** são fonte de cálculo —
  aparecem só como remissão do texto da 6118, isentas por (arquivo, número) em
  `tests/test_normas_catalogo.py::REMISSOES_DA_NORMA_TRANSCRITA`.

---

## Convenções que todo goal deste repo segue

1. **Baseline nos dois sentidos**, e toda lente nova com teste que fica **vermelho quando o
   defeito é injetado**.
2. **Injeção em `tmp_path`**, nunca mutando o repo.
3. **Substring → parse → renderizar.** Para norma e para folha: **olhe a imagem**.
4. **Saturação silenciosa**, incluindo `OK` por item que não chega ao veredito (G113).
5. **Asserção tautológica**, incluindo teste que confere um literal contra ele mesmo (G119).
6. **Três aceites por folha:** está certa, sai no manifesto, diz o que desenha.
7. **Instrumento tem de conseguir acusar** (G119) — e, **novo no G125**, acusar **por parte**.
   O medidor de memória do G121 só acendia `falhou` quando os dois lados se perdiam juntos;
   cego só para o freecad.exe, dizia `falhou: False` com 14,7 MB.
8. **Constante "medida" que a produção não lê é comentário** (G119).
9. **NOVO (G125) — a lente parte de onde o dado é PRODUZIDO, não de onde já foi declarado.**
   O G122 inventariou a 8.2.5 pelo grep "6118" e deixou fora 5 dos 10 módulos que fazem a
   conta; o G123 conferiu o carimbo nas peças do galpão, e 4 folhas de concreto de casa e
   prédio saíam sem ele. Portão de cobertura parte da conta ou do emissor, e a citação é
   conferida contra eles — nunca o contrário.
10. **NOVO (G125) — o resumo da suíte se lê inteiro antes de fechar.** A suíte do G119 deu
    `test_normas_catalogo` vermelho num lote que terminou depois do relatório, e ninguém leu.
    Goal só fecha com o resultado de **todos** os lotes lido.

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**:
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_sequencia.confere()`,
`varredura_constantes_orfas.confere()`, `tests/test_folhas_g77.py`,
`tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py`,
`tests/test_carimbo_mapa_g112.py` e `tests/test_normas_catalogo.py`.

**O verbete é parte da entrega.** **Uma fonte só:** dado que o cliente recebe mora na
produção; lente e teste importam de lá.

---

## Ordem e dependência

- **G126** é independente e é o que mais toca veredito hoje. Faça-o primeiro.
- **G127 antes de qualquer migração da 8.2.5.** Com 11 cópias da fórmula, virar a edição
  seria editar 11 lugares à mão.
- **G128** depende do G123 (entregue). Não vira a chave.
- **G129** e **G130** são independentes.

---

# GOALS

## G126 · O cimento que ninguém declarou

**Prioridade: alta.** Toca veredito do içamento do pré-moldado.

**Medido (G125):**
- `galpao_concreto.py:262` passa `spec.get("cimento", "CPV")` ao içamento, e
  `premoldado_nbr9062.py:255` repete `caso.get("cimento", "CPV")`. **Nem o `ProjetoSpec`
  nem o wizard têm campo de cimento** (grep em `projeto_spec.py`, `wizard*.py` e
  `rodar_galpao.py`: zero ocorrências) — pelo caminho do produto, o galpão de concreto
  **sempre** calcula o içamento com CPV.
- O CPV tem o menor `s` da 12.3.3 (0,20): é o default **mais favorável**. Medido na função
  real, `fckj_idade(30e3, 7, cimento)`: CPV 24562, CPII 23364, CPIII 20516 kN/m². O default
  dá **+19,7 %** de resistência aos 7 dias sobre um CPIII que ninguém excluiu.
- `premoldado_nbr9062.fckj_idade` tem **outro** default, `cimento="CPII"` (linha 64).
- Cimento **desconhecido** (qualquer string fora da tabela, ex. `"XYZ"`) vira `s = 0,25` em
  silêncio: `edicao_nbr6118_g123.py:241` (`S_PADRAO_DESCONHECIDO`). Medido: `"XYZ"` dá o
  mesmo número do CPII.
- **Não medido:** quantos casos do repo mudam de veredito de içamento com o cimento
  conservador.

**Entregar:**
- Cimento ausente **não** vira CPV nem CPII: aplica-se a regra do **piso conservador** para
  dado ausente (G6: o maior `s` da tabela), **declarada na folha e no memorial** — ou a
  entrada bloqueia. A escolha vai escrita no verbete, com o motivo.
- Cimento desconhecido **levanta**, com a lista dos válidos. Nunca vira 0,25.
- O cimento entra no `ProjetoSpec`/wizard como dado declarado, opcional, com a ausência dita.

**Aceite:** vermelho por injeção (spec sem cimento não sai com CPV; string inválida levanta);
os casos do repo que mudam de veredito listados um a um no verbete, com o número antes e
depois; nenhum default de cimento sobrando (grep por `"CPV"`/`"CPII"` como default de `get`
ou de parâmetro).

**Não fazer:** escolher o cimento do projeto. Piso conservador não é "o cimento provável".

---

## G127 · A fct,m em onze cópias

**Prioridade: alta.** Pré-requisito de qualquer troca de edição da 8.2.5.

**Medido (G125):**
- A fórmula do C55+ (`2,12 ln(1 + 0,11 fck)`) está escrita **11 vezes em 10 módulos**:
  `base_chumbador:99`, `estaca_profunda:388`, `fissuracao_nbr6118:59`,
  `fundacao_sapata:681`, `laje_concreto:441`, `pilar_concreto:407`, `piso_industrial:73`,
  `premoldado_nbr9062:91`, `viga_baldrame:47,78`, `viga_protendida:70`.
- A do até-C50 (`0,3 fck^(2/3)`) em **12 linhas**: as mesmas, mais `base_chumbador:798`
  (autoteste com fck 25 — não é conta de produção).
- Hoje as cópias **concordam**: todas com limiar `fck <= 50`. Nada impede que divirjam.
- O G122 mediu a diferença da 2023 (+1,3 % no C60); o G125 criou
  `confronto_2014_2023_g122.sites_formula_fctm`, que acha a conta por regex fora de
  comentário. **Não medido:** se alguma cópia converte unidade de outro jeito
  (MPa × kN/m² na entrada e na saída).

**Entregar:**
- Uma função de produção para fct,m (e fctk,inf/sup, se as cópias os derivam), com a faixa
  de validade declarada; os 10 módulos passam a chamá-la. **Número idêntico**, conferido
  módulo a módulo.
- `sites_formula_fctm` passa a reprovar **cópia nova** fora da fonte.

**Aceite:** número bit a bit igual antes e depois em cada módulo (C20, C50, C55, C60, C90);
vermelho por injeção (fórmula colada num módulo em `tmp_path` acusa); o item 52 do
inventário e o `CONFRONTO_G122` apontam para a fonte única.

**Não fazer:** trocar para a fórmula da 2023. Virar a edição é decisão do usuário (G123).

---

## G128 · A declaração da edição chega às três tipologias

**Prioridade: média.** Fecha os abertos (a) e (b) do D151.

**Medido (G125):**
- O G123 fiou a chave `norma_6118_edicao` só no galpão. Casa e prédio carimbam o
  parâmetro **ausente** (`desenho_pavimento._sufixo_edicao`,
  `desenho_fundacao_edificio._sufixo_edicao`): um projeto de casa que declare `2023+Em1`
  sairia com folha dizendo 2014.
- A compatibilização avalia furo em viga (13.2.5.1-b, ponto NÚMERO-MUDA) e as três
  tipologias chamam `gerar_pendencias` **sem** `edicao`: `edificio_adapter.py:1540`,
  `casa_residencial.py:1513`, `galpao_adapter.py:52`.
- O caderno de encargos escreve `**Normas:** ... NBR 6118 ...` sem edição
  (`caderno_encargos.py:247`; medido 4× no caderno da casa e 4× no do prédio).

**Entregar:** a edição declarada no projeto chega ao carimbo das folhas de casa e prédio, à
compatibilização das três tipologias e ao caderno — sempre da fonte única
`edicao_nbr6118_g123`. Sem o parâmetro, o comportamento é o de hoje **e a peça diz qual é**.

**Aceite:** rodada real das três tipologias com a chave ausente e com `2023+Em1`: toda peça
de concreto declara a edição que a conta usou (vermelho por injeção: folha que diz 2014 com a
chave em `2023+Em1` reprova); o furo circular de 125 mm muda de veredito com a chave, e só
com ela.

**Não fazer:** virar a chave em projeto nenhum do repo.

---

## G129 · Os rótulos que se sobrepõem e nenhum portão vê

**Prioridade: média.** Classe "a folha diz o que desenha" (convenção 6).

**Medido (G125)** com `desenho_svg_base.colisoes_de_rotulo_svg` sobre as folhas de uma
rodada real de casa e prédio:
- **6 de 27 folhas** têm colisão, **48 pares** no total: `planta-eletrica.svg` 15,
  `planta-baixa.svg` 8, `telhado-tesoura.svg` 8, `quadro-cargas.svg` 7,
  `detalhes-concreto-casa.svg` 5, `planta-laje-pavimento-tipo.svg` 5.
- A função existe desde o G56 e 11 arquivos de teste a usam, cada um para a sua folha —
  **nenhum censo** a roda sobre todas as folhas entregues.
- **Não medido:** o galpão (a rodada é cara: meça), e quantos pares são falso-positivo da
  estimativa de largura (`0,6 × size` por caractere).

**Entregar:** censo de colisão sobre toda folha que o manifesto entrega, com baseline
congelado nos dois sentidos (par novo = vermelho; par que some sem triagem = vermelho), e
cada par existente **triado olhando o PNG** (regra 3): colisão real vira correção na folha;
falso-positivo vira isenção com motivo.

**Aceite:** vermelho por injeção (rótulo empurrado sobre outro em `tmp_path`); os 48 pares com
triagem escrita; nenhuma isenção sem o PNG conferido.

---

## G130 · As 39 dívidas que o cliente não vê

**Prioridade: média.** A outra metade do G124.

**Medido (G125):**
- `varredura_constantes_orfas.ORFAS_TRIADAS` tem **39 DÍVIDAS** com cláusula — exigências de
  norma escritas e não verificadas. Exemplos: fvk da alvenaria **armada** (NBR 16868-1
  11.4.3); raios de detecção (NBR 17240 5.4.1); pressão dinâmica mínima na rede (NBR 5626
  6.9.4); R ≤ 1 Ω para área com explosivo (aterramento).
- **Nenhuma chega ao cliente:** zero menções (nome, cláusula ou "não verificado") nos
  documentos entregues de uma rodada real de casa e prédio (`documentos/*.md`).
- O mecanismo de escopo declarado já existe: pendências `not_available` que travam a
  aprovação (G57, `pacote_no_manifesto(pendencias=...)`).
- **Não medido:** o galpão; e quais das 39 se aplicam a cada tipologia.

**Entregar:** cada dívida aplicável à tipologia sai no pacote legal como exigência **não
verificada pelo framework**, com a cláusula, vinda de `ORFAS_TRIADAS` (fonte única). A que
não se aplica diz por quê, no código.

**Aceite:** rodada real das três tipologias; toda dívida aplicável aparece no documento
entregue (vermelho por injeção: dívida nova em `ORFAS_TRIADAS` que não chega ao pacote
reprova); a lista por tipologia no verbete.

**Não fazer:** implementar as verificações (cada uma é um goal próprio) nem ligar constante em
conta para tirá-la da lista.

---
