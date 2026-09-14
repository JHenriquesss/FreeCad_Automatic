# Backlog de goals executáveis — pós-G136 / D165 (2026-09-13)

Fila **ABERTA**. Seis goals (G137–G142). As filas anteriores estão fechadas e ficam apenas
como registro — não reexecute nada de lá: `BACKLOG-GOALS.md` (G78–G88),
`BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`, `BACKLOG-GOALS-G107-G112.md`,
`BACKLOG-GOALS-G114-G118.md`, `BACKLOG-GOALS-G120-G124.md`, `BACKLOG-GOALS-G126-G130.md` e
`BACKLOG-GOALS-G132-G136.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-13 na branch `feat/tipologias-e-verticais-de-projeto`,
na auditoria do lote G132–G136 e no D164/D165 (suíte paralela, G102 sem o executivo de aço).
O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis — o cliente informa o projeto e recebe cálculo,
3D e **todas as folhas**. As auditorias G125–G131 fecharam o desencontro entre o que a conta
usa e o que a entrega declara. O que falta agora é do lado das **folhas**: medido nas rodadas
reais das três tipologias, o prédio sai com 15 folhas e nenhuma pulada, mas o galpão — a
tipologia de origem do framework — pula **6 folhas prometidas**, e em **nenhuma** rodada de
produção sai uma prancha de aço. Três dessas folhas têm o emissor pronto e provado em outra
tipologia: é a classe do G79/G89, **folha certa que ninguém emite**.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

**Nenhuma norma ausente para este arco.** Conferidas por identificador: NBR 8800:2008
(F028), NBR 9062:2017 (F137), NBR 6122:2022 (F038), NBR 13714:2000 (F072), NBR 5410:2004
(F058), NBR 5419-1/2/3:2026 (F060–F062).

**Bloqueado por DADO de projeto, não por norma (fora deste arco, medido na casa real):**
PE-AR-01 implantação (`site.lote` com dimensões, recuos e orientação não declarados),
PE-AR-03 cortes/fachadas (cotas de soleira/terreno não declaradas), fundação por laudo SPT
externo (T44). Emissor sem o dado seria desenho inventado.

**Escopo `not_available` do prédio (medido no `adapter-result.json`, fora deste arco):**
alvenaria estrutural, recalque diferencial, viga baldrame, NBR 15575 fachada / impacto de
corpo mole-duro / carga concentrada no piso.

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
10. **O resumo da suíte se lê inteiro antes de fechar** (G125); a lista inclui `tests/branches`
    e `tests/trunk` (`find tests -name 'test_*.py'`).
11. **Injete o valor em cada lugar de entrada que o produto aceita** (G131); "não se aplica"
    é um terceiro valor declarado.
12. **NOVO (D164/D165) — a suíte do goal roda pelo runner paralelo**, a partir de
    `framework/galpao_fw`, com o interpretador de nome curto 8.3:
    `…\VENV~1\Scripts\python.exe tools/suite_paralela.py -n 3` (~27 min; grava
    `resumo.json` com `quebras` — o goal só fecha com `rc_pytest` 0 **e** `quebras` vazio).
    Não edite o repositório com a suíte rodando (o portão de `git status` acusa). Teste novo
    que sobe freecad.exe/freecadcmd.exe entra em `tests/censo_freecad.GRUPO_FREECAD` com o
    motivo medido — o censo reprova nos dois sentidos. A suíte serial `pytest tests` (1 thread
    de BLAS a mais, número bit a bit) e o portão lento do executivo de aço
    (`GALPAO_AUDITORIA=1`) rodam **na auditoria do lote**, não em cada goal.

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**
antes da suíte: `varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.confere()`,
`tests/test_folhas_g77.py`, `tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py`,
`tests/test_carimbo_mapa_g112.py`, `tests/test_normas_catalogo.py`,
`tests/test_galpao_indice_g93.py` e `tests/test_suite_paralela_d164.py` — mais o portão
próprio de cada fonte que o goal tocar. Goal que muda folha do galpão roda também
`tests/test_indice_disco_rodada_g102.py` **isolado** (`-s`, ~10 min, re-congela o custo com o
número medido se ele mudar).

**Otimização de conta (D158):** só com prova de número idêntico. **O verbete é parte da
entrega.** **Uma fonte só:** dado que o cliente recebe mora na produção.

---

## Ordem e dependência

- **G137** primeiro: é o único que muda o que sai em **toda** rodada de produção do galpão, e
  mexe no prazo do caderno que G138–G140 também usam.
- **G139 antes de G138 e G140**: a coordenação decide como o hook passa disciplinas ao
  caderno; as outras duas folhas entram pelo mesmo hook.
- **G141** e **G142** são independentes.

---

# GOALS

## G137 · O caderno do galpão sai sem nenhuma prancha de aço

**Prioridade: alta.**

**Medido.**
- Rodada real de produção do galpão (`projects/galpao-tp-g95`, opções do G102, perfil
  cProfile, D164): 997 s, 937 s esperando o freecad.exe. O executivo de aço recebe
  **459 s** do prazo global de 1200 s (`caderno_turnkey._STAGE_WEIGHTS`, peso do aço 7,0
  derivado de `_T_MEDIDO_SEG["aco"] = 578`) e estoura: `timeout 459.18 s aguardando
  pranchas`, **zero pranchas de aço** no disco, `RELATORIO-CONSOLIDADO` com "Pranchas 2D:
  NAO GERADO". PE-ES-01/02/03 saem puladas com motivo genérico.
- O próprio framework já mediu o executivo acima do prazo: ~578 s nas 16 pranchas (D133/G109)
  + PE05 ≈ 209 s (G118), sem contar o modelo 3D (~3,5 min na mesma rodada).
- O mapa do índice cobre **3** arquivos de aço (`galpao_adapter._PRANCHA_ARQUIVO_GALPAO`:
  PE04_PORTICO, PE07_DET_JOELHO, PE01_COBERTURA); o `techdraw_exec` emite PE01…PE16
  (`techdraw_exec.py:662-1768`). Numa corrida em que PE02_FUNDACOES e PE03_ELEVACOES chegaram
  ao disco antes do corte (D164, 26 min 58 s), o G102 reprovou por `extra_no_disco`: folha
  emitida sem código.
- D165: o G102 passou a rodar o galpão com `executivo_aco=False` (as folhas de aço saem
  puladas com a causa nomeada). O executivo **completo** foi medido à parte, com prazo folgado
  (`rodar_tudo` sobre `turnkey.aco` do mesmo spec, 3D 900 s / executivo 2400 s, freecad.exe
  sozinho): **1038,9 s** no total, `ok=True`, **15 PDFs** (PE01–PE14 e PE16; não sai PE15).
  **Só 3 têm código** no índice; **12 saem sem código**: PE02_FUNDACOES, PE03_ELEVACOES,
  PE05_CONTRAVENTAMENTO, PE06_DET_BASE, PE08_FECHAMENTO, PE09_QUADROS, PE10_DET_CUMEEIRA,
  PE11_DET_GUSSET_COB, PE12_DET_GUSSET_PAR, PE13_DET_CLIPE_GIRT, PE14_CROQUIS, PE16_MONTAGEM.
  Congelado como baseline `SEM_CODIGO_ACO` em `tests/test_executivo_aco_completo_d165.py`
  (portão de auditoria, `GALPAO_AUDITORIA=1`). Não medido: o tempo por prancha nesta rodada
  (o harness do G105 mede) e o tempo em rodada de produção sem folga.

**Entregar.**
1. Código do índice para **cada** prancha que o executivo de aço emite (mapa 1:1 medido contra
   o `techdraw_exec`, não suposto), com título na fonte do índice (`pacote_legal._PRANCHAS`).
2. Prazo do aço que **cabe no tempo medido**: o prazo sai do tempo cronometrado por prancha
   (harness `tools_harness_aco_por_prancha.py`, G105), nunca de palpite; se o prazo global de
   1200 s não comporta, o prazo global muda com o motivo escrito ou o aço deixa de dividir o
   prazo com as outras disciplinas — decisão registrada no verbete com os números.
3. O portão lento `tests/test_executivo_aco_completo_d165.py` (baseline `SEM_CODIGO_ACO`
   nos dois sentidos) fica com a baseline **vazia**.

**Aceite.** Rodada de produção do galpão (opções padrão) emite todas as pranchas de aço no
disco, no manifesto e no caderno; o índice x disco fecha sem `extra_no_disco`; vermelho por
injeção (prancha nova sem código, código sem prancha). Três aceites por folha (convenção 6)
para ao menos PE02 e PE03, olhando o PNG.

**Não fazer.** Mudar geometria, cálculo ou conteúdo das pranchas; tirar `executivo_aco=False`
do G102 (o portão rápido fica rápido).

## G138 · PE-IN-02 detalhes de hidrantes do galpão: o emissor existe e não é chamado

**Prioridade: média.**

**Medido.** Na rodada real do galpão a folha sai pulada: "not_available: sem emissor de
detalhe de hidrantes e rotas nesta rodada (PE-IN-02 Detalhes hidrantes/rotas)"
(`galpao_adapter._motivo_folha_galpao_nao_emitida`). O emissor existe e está provado:
`desenho_incendio.detalhes_hidrantes_rotas_svg` (`desenho_incendio.py:426`) /
`gerar_detalhes_hidrantes` (`:477`), chamado **só** pelo prédio
(`edificio_adapter.py:1166`), com guarda de folha (`test_folhas_g77.py:323`) e teste de
geometria (`test_edificio_pranchas_g56.py:205`). O G101 já registrou que a entrada tem a
"shape do prédio" — o resultado do incêndio do galpão (`galpao_seguranca_incendio`) tem outra
forma. Não medido: quais campos faltam no resultado do galpão para o emissor.

**Entregar.** A folha PE-IN-02 do galpão emitida pelo emissor existente, a partir do resultado
do cálculo de incêndio do galpão (adaptação de entrada na produção, uma fonte só); campo que o
cálculo do galpão não produz sai declarado na folha, nunca inventado. Mapa e motivo de
ausência atualizados (`_PRANCHA_ARQUIVO_GALPAO["PE-IN-02"]` hoje aponta `INC03_DETALHES.pdf`).

**Aceite.** Rodada real do galpão com PE-IN-02 no disco, no manifesto e no índice; três
aceites da folha olhando o PNG; vermelho por injeção (emissor desligado volta a pular com
motivo). O prédio segue byte-idêntico.

**Não fazer.** Recalcular hidrantes; mexer na rota SVG do G104.

## G139 · PE-CD-01 coordenação do galpão: o hook nunca emite

**Prioridade: média.**

**Medido.** `caderno_turnkey.montar_caderno` só emite a prancha formal de coordenação quando
`disciplinas is None` (`caderno_turnkey.py:479`); o hook do galpão sempre passa o recorte
`normalized["requested_disciplines"]` (`galpao_adapter._emit_drawings`), então PE-CD-01 sai
pulada em toda rodada: "sem emissor de coordenacao ligado ao hook nesta rodada … montar_caderno
so emite a prancha com disciplinas=None". O emissor existe (`galpao_turnkey.
montar_prancha_coordenacao`, `techdraw_coordenacao`) e o render federado roda na mesma rodada
(57 s no perfil do D164).

**Entregar.** A prancha de coordenação emitida na rodada do adaptador quando há ≥ 2
disciplinas executadas, com o recorte de disciplinas respeitado (a coordenação é de quem
rodou), dentro do prazo do caderno com peso medido (hoje `coordenacao` tem peso 0,75 literal
— medir e escrever o tempo, convenção 8).

**Aceite.** Rodada real do galpão com PE-CD-01 no disco, manifesto e índice; três aceites
olhando o PNG; recorte de 1 disciplina segue sem coordenação, com motivo; vermelho por injeção.

**Não fazer.** Mudar a checagem de clash.

## G140 · PE-CO-04 locação e formas da fundação do galpão pré-moldado

**Prioridade: média.**

**Medido.** Rodada real do galpão: "not_available: sem emissor de locacao e formas da
fundacao nesta rodada (PE-CO-04 …); a fundacao do pre-moldado sai dimensionada sem folha de
locacao emitida". A casa tem `desenho_casa_residencial.fundacao_locacao_formas_casa_svg`
(`:733`) e o prédio `desenho_fundacao_edificio` (folha PE-CO-04 do prédio emitida — prédio
real sem nenhuma folha pulada). O galpão de concreto dimensiona sapata/bloco
(`galpao_concreto`) sem folha.

**Entregar.** Folha de locação e formas da fundação do galpão pré-moldado a partir do
resultado dimensionado (eixos, cálices/sapatas, cotas), reaproveitando as primitivas das
outras tipologias; dado que o resultado não traz sai declarado.

**Aceite.** Rodada real do galpão com PE-CO-04 no disco, manifesto e índice; três aceites
olhando o PNG (cada sapata do resultado desenhada, uma por uma — nunca contagem contra
contagem); vermelho por injeção.

**Não fazer.** Redimensionar fundação.

## G141 · O mezanino calculado que evapora do índice

**Prioridade: média.**

**Medido.** `galpao_turnkey.DISCIPLINAS` inclui `mezanino` (`galpao_turnkey.py:41`,
despachado por `_run_mezanino`, `:100`, e levado ao BIM, `:240-244`); `pacote_legal._PRANCHAS`
**não** tem a disciplina, então ela é executada e some no `continue` do índice — o D89 vivo,
do lado da promessa (D121). Travado por assert em `tests/test_indice_disco_g91.py:304-305`, não
consertado. Nenhum `projects/*/project-spec.json` declara mezanino (0 ocorrências): não há
rodada real no repo que exercite o caminho.

**Entregar.** Mezanino executado aparece no índice e no pacote com código e folha (ou com a
ausência de folha declarada por código, motivo nomeado), e um spec de teste com mezanino
declarado exercita a rodada real; o assert que trava o defeito vira o portão do comportamento
novo.

**Aceite.** Rodada com mezanino: índice x disco fecha; sem mezanino, byte-idêntico; vermelho
por injeção.

**Não fazer.** Mudar o cálculo do mezanino; inventar geometria de mezanino num project-spec do
repo (o spec de teste mora em `tmp_path` ou fixture de teste, dito).

## G142 · PE-EL-03 infraestrutura e aterramento da casa

**Prioridade: baixa.**

**Medido.** Casa real: "not_available: sem emissor de infraestrutura/aterramento nesta rodada
(PE-EL-03 Infraestrutura/aterramento); malha de aterramento e SPDA nao declarados e sem folha
emitida". O prédio emite a folha com `desenho_eletrico.infra_aterramento_edificio_svg`
(`desenho_eletrico.py:439`), chamada só por `edificio_adapter.py:1114`. Na casa faltam **dois**
dados declarados (malha de aterramento e SPDA) — a parte que depende deles não pode ser
desenhada.

**Entregar.** Folha PE-EL-03 da casa com o que o cálculo elétrico da casa produz
(infraestrutura), e aterramento/SPDA declarados como ausentes na própria folha com o dado que
falta nomeado; se nada da folha é desenhável sem os dados, a folha segue pulada com o motivo
atual e o goal registra a medição.

**Aceite.** Três aceites olhando o PNG; vermelho por injeção; prédio byte-idêntico.

**Não fazer.** Dimensionar SPDA ou malha sem dado declarado.
