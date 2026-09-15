# Backlog de goals executáveis — pós-G142 / D172 (2026-09-14)

> **FILA CONSUMIDA** (2026-09-15): G143–G148 executados; auditoria em D176 (commit
> `076a69f`). A fila aberta é [BACKLOG-GOALS-G149-G153.md](BACKLOG-GOALS-G149-G153.md).

Fila **ABERTA**. Seis goals (G143–G148). As filas anteriores estão fechadas e ficam apenas
como registro — não reexecute nada de lá: `BACKLOG-GOALS.md` (G78–G88),
`BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`, `BACKLOG-GOALS-G107-G112.md`,
`BACKLOG-GOALS-G114-G118.md`, `BACKLOG-GOALS-G120-G124.md`, `BACKLOG-GOALS-G126-G130.md`,
`BACKLOG-GOALS-G132-G136.md` e `BACKLOG-GOALS-G137-G142.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-14 na branch `feat/tipologias-e-verticais-de-projeto`
(commit `d998a5f`), na auditoria do lote G137–G142 (D172). O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis — o cliente informa o projeto e recebe cálculo,
3D e todas as folhas. O arco G137–G142 fechou as folhas que o galpão prometia e não emitia. A
auditoria D172 mostrou o preço de reaproveitar emissor: ele traz os fallbacks dele (`or 1`
desenhou hidrante inventado). Este arco ataca a mesma família nos dois lados — **o default
calado que decide a geometria** (a estaca do galpão) e **o fallback calado que decide o
desenho** (47 nos emissores) — mais o gate do mezanino que some num `except`, a folha que o
mezanino ainda não tem, e o custo real de rodar tudo isso numa máquina de 8 GB.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

**Nenhuma norma ausente trava este arco.** Varredura: 60 NBR citadas em
`framework/galpao_fw/*.py` contra o catálogo inteiro; 4 sem entrada, todas triadas:
- **NBR 5413** — substituída pela NBR ISO/CIE 8995-1:2013, que está no acervo (F102);
  lacuna pré-existente congelada em `tests/test_normas_catalogo.LACUNAS_PRE_EXISTENTES`.
- **NBR 13438** — nome de material na tabela de pesos (`cargas_nbr6120.py:115`), não fonte de
  conta; mesma lacuna congelada (junto com a NBR 5444, simbologia, coberta pela IEC 60617 F148).
- **NBR 8522** e **NBR 8965** — remissões do texto da NBR 6118 transcrito nas lentes G116/G122;
  isentas por (arquivo, número) em `REMISSOES_DA_NORMA_TRANSCRITA`.

**Bloqueado por DADO de projeto, não por norma (fora deste arco):** PE-IN-03 escada do galpão
(geometria da escada não declarada no spec; fronteira G101), PE-EL-03 da casa (malha de
aterramento e SPDA não declarados; D171), PE-AR-01 implantação e PE-AR-03 cortes da casa
(lote, recuos, cotas), fundação por laudo SPT externo (T44).

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
12. **A suíte do goal roda pelo runner paralelo** (D164/D165), a partir de
    `framework/galpao_fw`, com o interpretador de nome curto 8.3:
    `…\VENV~1\Scripts\python.exe tools/suite_paralela.py -n 3` (~21 min; grava
    `resumo.json` — o goal só fecha com `rc_pytest` 0 **e** `quebras` vazio). O runner já põe
    `PYTHONUTF8=1` (D172): não precisa no shell. Não edite o repositório com a suíte rodando.
    Teste novo que sobe freecad.exe/freecadcmd.exe entra em `tests/censo_freecad.GRUPO_FREECAD`
    com o motivo medido. A serial `pytest tests` e o portão do executivo de aço
    (`GALPAO_AUDITORIA=1`) rodam **na auditoria do lote**, não em cada goal. Máquina de 8 GB:
    rodada pesada uma por vez; os aplicativos do usuário ficam abertos.
13. **NOVO (D172) — emissor ou conta reaproveitados trazem os fallbacks deles.** Antes de fechar:
    rode com o dado **ausente** e com **zero**, um por um; folha nova ligada em código comum
    (`config_de_spec`, `montar_pranchas`) fica num `try` próprio; injete a falha **só na folha
    nova** e confira que as antigas seguem no status. O teste do goal não pode esperar o erro
    da disciplina inteira (foi assim que o `test_hidrantes_g138.test_04` congelou o defeito).

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**
antes da suíte: `varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.confere()`,
`tests/test_folhas_g77.py`, `tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py`,
`tests/test_carimbo_mapa_g112.py`, `tests/test_normas_catalogo.py`,
`tests/test_galpao_indice_g93.py`, `tests/test_suite_paralela_d164.py` e
`tests/test_auditoria_g137_g142_d172.py` — mais o portão próprio de cada fonte que o goal
tocar. Goal que muda folha do galpão roda também `tests/test_indice_disco_rodada_g102.py`
**isolado** (`-s`, ~11 min, re-congela o custo com o número medido se ele mudar).

**Otimização de conta (D158):** só com prova de número idêntico. **O verbete é parte da
entrega.** **Uma fonte só:** dado que o cliente recebe mora na produção.

---

## Ordem e dependência

- **G143** e **G144** primeiro: são os dois que podem mudar **veredito** (geometria de estaca
  calada; gate que some e deixa `ATENDE` True). Independentes entre si.
- **G145** antes de **G146**: a folha do mezanino vai reaproveitar emissores do prédio, e a
  varredura diz quais fallbacks deles mordem com dado ausente.
- **G146** depois de **G144** (a folha não pode desenhar um mezanino cujo gate sumiu).
- **G147** independente (precisa de máquina livre para a medição de referência).
- **G148** por último e **com decisão do usuário** na parte 2.

---

# GOALS

## G143 · A estaca do galpão com diâmetro e comprimento que ninguém declarou

**Prioridade: alta.**

**Medido.**
- `galpao_concreto.py:351`: `D_e = spec.get("D_estaca", 0.30); L_e = spec.get("L_estaca", 8.0)`.
  Rodada real (`galpao_concreto.rodar`, galpão 10 × 40 × 6, `tipo_fundacao="estaca"`, perfil
  SPT de `tests/test_build_concreto.py:114`) **sem** `D_estaca`/`L_estaca`: `estaca.capacidade`
  sai com **D = 0,30 m, L = 8,0 m**, `grupo.n` = 1, e a PE-CO-04 (adaptador do G140) desenha
  D 0,30 / L 8,0. Com `D_estaca=0.30, L_estaca=10.0` declarados, L = 10,0. Varredura de todas as
  strings do resultado: **nenhuma** menciona D_estaca/L_estaca ou diz que o valor foi assumido.
  O rótulo da geometria (`fund_geom`, `:360`) imprime "D30 L8" como se fosse projeto.
- No mesmo bloco, outros valores do código entram na conta sem declaração no resultado (não
  medido se decidem veredito): `tipo_estaca` "pre_moldada" (`:354`), `cota_apoio` 0,5 na
  recomendação SPT (`:340`), `B_max_sapata` 2,5 (`:341`), `mu_solo` 0,5 (`:371`),
  `sigma_solo_adm` 200 sem SPT (`:367-368`; o G140 declara na **folha** PE-CO-04, não medido no
  memorial nem nos sinais de revisão do adaptador).
- A regra do repo já existe: D102/G75 — *default que decide veredito: declarar ou recusar*.

**Entregar.**
1. Para cada valor da lista, medir por injeção (convenção 11: spec do turnkey, sub-spec do
   concreto, wizard se aceitar) se ele muda geometria, capacidade ou veredito — tabela no
   verbete, com o número antes e depois.
2. O que decide geometria/capacidade sem dado declarado: **recusa nomeada** (como a estaca sem
   SPT já faz, `:348-350`) **ou** declaração que chega ao memorial, à folha e aos sinais de
   revisão (`default: True` que o `_review_signals` do adaptador lê) — escolha por item com o
   motivo escrito, seguindo o D102. Nunca um valor novo arbitrado.
3. `projects/*/project-spec.json` que dependem do valor calado: listados (grep), e o que muda
   neles dito no verbete.

**Aceite.** Vermelho por injeção em cada porta de entrada (valor ausente → recusa ou
declaração; declarado → número do spec); casa e prédio byte-idênticos; os três aceites da
PE-CO-04 com estaca, olhando o PNG, com D/L declarados e sem.

**Não fazer.** Escolher diâmetro, comprimento, atrito ou tensão "melhores"; mudar Aoki-Velloso,
Décourt ou Teixeira.

## G144 · O gate de interferência do mezanino que some num `except`

**Prioridade: alta.**

**Medido.** `galpao_mezanino.py:321-329`:
```python
try:
    interf = checa_interferencia(res)
    gates["interferencia"] = {...}
    ...
except Exception:
    pass
res["interferencia"] = gates.get("interferencia")
```
Se `checa_interferencia` levanta, o gate **não existe**, `reprovados` não o cita, `ATENDE`
continua **True** e `res["interferencia"]` vira `None` — o G106 ("except que devolve vazio") e o
G113 ("OK por item fora do veredito") no mesmo lugar. Não medido: se algum spec real faz a
checagem levantar (o goal mede por injeção).

**Entregar.** Falha da checagem vira estado **nomeado** que chega ao veredito (reprovado ou
inconclusivo declarado, com a exceção no texto) — nunca `ATENDE` True sem a checagem; o mesmo
padrão procurado nos outros `except Exception: pass` do `galpao_mezanino.py` e do caminho do
mezanino no `galpao_turnkey`, com a lista no verbete.

**Aceite.** Injeção (`checa_interferencia` levantando, em `tmp_path`/monkeypatch) → veredito
não-OK com o motivo; caso normal byte-idêntico (selftest e `test_mezanino_indice_g141`);
federado e BIM do mezanino intactos.

**Não fazer.** Mudar a geometria ou a regra da checagem de interferência.

## G145 · Os 47 fallbacks `or 0` / `or 1` dos emissores de folha

**Prioridade: média-alta.**

**Medido.** `grep -cE 'or 0\b|or 0\.0\b|or 1\b'` nos emissores (2026-09-14, após D172):
`desenho_incendio.py` 16 · `desenho_fundacao_edificio.py` 8 · `desenho_escada_edificio.py` 5 ·
`desenho_alvenaria.py` 5 · `desenho_eletrico.py` 4 · `desenho_hidraulica.py` 3 ·
`desenho_coordenacao.py` 2 · `desenho_casa_residencial.py` 2 · `techdraw_eletrico.py` 1 ·
`desenho_pavimento.py` 1 — **47**. Um deles (`int(N_hidrantes or 0) or 1`) desenhava hidrante
inventado quando o emissor do prédio passou a receber o galpão (D172). No adaptador do G140,
`D_m`/`L_m`/`N_pilar` com `or 0.0` são **mortos hoje** (medido: as chaves existem no resultado da
estaca e da sapata), mas nenhum teste congela isso. Não medido: quais dos 47 recebem dado que
pode faltar. A contagem é por linha de grep (uma linha pode ter dois).

**Entregar.**
1. Lente de produção (`varredura_fallback_folha.py`, stdlib, fonte única) que lista cada
   ocorrência por AST (não por grep) e a classifica contra o **produtor** do dado (convenção 9):
   (a) **morto** — o produtor sempre entrega a chave (prova: a função e o teste que a garante);
   (b) **vivo** — o dado pode faltar ou valer zero numa rodada real.
2. Baseline congelada nos dois sentidos (fallback novo sem triagem reprova; triado que some
   reprova), com vermelho por injeção.
3. Cada (b): a folha **declara** a ausência em texto (nunca um número) e ganha teste um por um
   no emissor — dado ausente, zero e presente (convenção 13).

**Aceite.** Lente vermelha por injeção; nenhum (b) sem teste; prédio e casa byte-idênticos
onde o dado existe; `test_folhas_g77` verde; três aceites olhando o PNG para cada folha que
mudou.

**Não fazer.** Trocar `or 0` por `or 1` (ou outro número) "para desenhar algo"; apagar
fallback sem provar no produtor.

## G146 · PE-MZ-01: a folha do mezanino calculado

**Prioridade: média.** Depende de G144; aproveita G145.

**Medido.**
- D170: com mezanino executado, PE-MZ-01 é prometida e sai **pulada** — "mezanino calculado sem
  prancha dedicada … sem emissor TechDraw ligado ao hook"
  (`galpao_adapter._motivo_folha_galpao_nao_emitida`).
- O cálculo entrega (`galpao_mezanino.rodar`, `:305-319`): `laje` (com `armaduras`),
  `vigas`/`viga_X`/`viga_Y`, `pilar` (`hx`, `hy`, `As_cm2`, `Nk`), `sapatas`, e a posição
  `x0`, `y0`, `Lx`, `Ly`, `h` dentro do envelope.
- Primitivas provadas do prédio: `desenho_pavimento.planta_formas_svg(pav)` lê o dict de
  `pavimento_tipo.monta` (`vaos_x`, `vaos_y`, `area_m2`, `paineis[i,j,lx,ly,caso]`, `pilares`,
  `:284-305`); `prancha_armacao_vigas_pilares_svg(vigas_verificacao, pilares)`
  (`desenho_pavimento.py:797`). Não medido: a diferença de forma entre o resultado do mezanino e
  essas entradas (o G138 e o G140 começaram por esse test_01).

**Entregar.** Folha PE-MZ-01 (formas + armação do mezanino) a partir do resultado do cálculo,
por adaptação na produção (uma fonte só), arquivo `MZ01_MEZANINO.pdf` já mapeado; pela rota sem
freecad.exe se as primitivas permitirem (medir); campo que o cálculo não produz sai declarado na
folha. Mapa, motivo e correspondência de numeração atualizados; a pulada continua para mezanino
não executado.

**Aceite.** Rodada com mezanino declarado (spec de teste em `tmp_path`): PE-MZ-01 no disco, no
manifesto e no índice; três aceites olhando o PNG, com **cada** viga, pilar e sapata do
resultado desenhados um por um; convenção 13 (mezanino sem sapata aprovada, laje sem armadura,
falha só na folha nova); vermelho por injeção; prédio byte-idêntico.

**Não fazer.** Mudar o cálculo do mezanino; pôr mezanino num `projects/*/project-spec.json`.

## G147 · O prazo do executivo de aço numa máquina carregada

**Prioridade: média.**

**Medido.**
- Portão de auditoria do aço (`tests/test_executivo_aco_completo_d165.py`, 3D 900 s + executivo
  2400 s, freecad.exe sozinho): **1038,9 s** (D165), **1067,3 s** (D166), **1937,2 s** (D172,
  648 MB livres; freecad.exe vivo com 1136 s de CPU — não travado).
- Produção: `ProjectLoopOptions.timeout_seconds` = 2100 (`project_loop.py:150`), repartido por
  peso (`caderno_turnkey._STAGE_WEIGHTS`): aço 787,7 s + 3D 210 s, medidos com máquina livre
  (`:88-109`). **Concreto 2,0 e elétrico 1,5 são literais "SEM MEDICAO"** (`:117-118`,
  convenção 8).
- Não medido: rodada de produção do galpão com `executivo_aco=True` em máquina carregada; o
  tempo real de concreto e elétrico.

**Entregar.** (1) Cronometrar concreto e elétrico no mesmo protocolo do G139 (processo reiniciado
por amostra) e trocar os literais por pesos medidos. (2) Rodar a produção do galpão
(`projects/galpao-tp-g95`, opções padrão, `executivo_aco=True`) com a máquina livre e com a
máquina no estado de uso normal, registrando memória livre mínima e quais etapas estouram. (3) Se
o prazo não cobre o medido carregado: decisão com os números no verbete (prazo derivado da
medição, ou timeout nomeado mantido com a frequência medida) — nunca palpite.

**Aceite.** Nenhum peso "SEM MEDICAO" restante; tabela livre × carregada no verbete; G102
intacto (`executivo_aco=False` fica); vermelho por injeção se o prazo passar a ler constante não
medida.

**Não fazer.** Paralelizar pranchas dentro do freecad.exe; fechar aplicativos do usuário para
medir.

## G148 · Metade da suíte é uma rodada do galpão, e a memória não tem piso

**Prioridade: média. A parte 2 precisa de decisão do usuário antes de ser executada.**

**Medido.**
- Runner (D172): 1225 s no total; `test_indice_disco_rodada_g102.py::test_01` sozinho
  **643,7 s (52 %)**. Os seguintes mais lentos: builds 3D do FreeCAD de 44–74 s.
- Serial de referência: **67 min** com 1,1–1,6 GB livres (35 min no D165); a 1ª tentativa foi
  **morta pelo harness por memória baixa** em 24 %.
- Memória livre mínima nas corridas pelo runner: 159 MB (D171), 308 e 416 MB (D172). O runner só
  **registra** `memoria_livre_min_mb` (`tools/suite_paralela.py`); não há piso. Pico medido do
  G102 galpão: 2076,6 MB (`CUSTO_MEDIDO_MEM_MB`).

**Entregar.**
1. Piso de memória livre no runner, derivado do medido (freecad.exe e pico do G102, número e
   motivo escritos): cruzado o piso, grava quais testes estavam em cada worker (o censo já sabe)
   e sai como `quebra` nomeada — sem matar processo do usuário. Vermelho por injeção (amostrador
   falso).
2. **Opção para o usuário decidir antes:** o galpão do G102 sai da suíte do goal para o tier de
   auditoria (como o executivo de aço no D165); casa e prédio ficam. A convenção 12 já roda o
   G102 isolado em todo goal que muda folha do galpão. O goal **mede** o ganho antes de propor.

**Aceite.** Piso com teste vermelho nos dois sentidos; se a parte 2 for aprovada, suíte do goal
com o novo tempo medido e o G102-galpão no portão de auditoria com o mesmo censo.

**Não fazer.** Mover cobertura sem o OK do usuário; baixar `-n` sem medir.
