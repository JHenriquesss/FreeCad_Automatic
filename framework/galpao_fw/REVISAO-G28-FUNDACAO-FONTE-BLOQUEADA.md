# G28 — Fundação: caça à fonte SPT ou declaração de bloqueio

> **BLOQUEADO — fonte ausente.** O vertical de fundação (G9, G17, G18) é o que
> mais evoluiu no framework e é o único vertical **sem nenhum caso externo com
> laudo de sondagem SPT**. Esta revisão registra a caça e declara o bloqueio
> honesto, no mesmo precedente da alvenaria estrutural (NBR 16868 ausente).
> Até que um pacote de licitação replicável traga o laudo SPT anexo, o vertical
> permanece sem validação externa por fonte — e isso está escrito.
>
> Precedente honesto:
> - Alvenaria estrutural — `REVISAO-GAPS-G2-LAJE-ALVENARIA-MULTIPAV.md:130-144`
>   (acervo não cobre NBR 16868, 48 fontes varridas, bloqueio declarado),
>   `REVISAO-G3-MULTIPAVIMENTO.md:64-70` (continua bloqueada por fonte),
>   `REVISAO-G11-VIBRACAO-E-15575.md:25,247`, `edificio_adapter.py:16,76`,
>   `estrutura_casa.py:630,713`, `edificio_multipavimento.py:582`
>   listam `alvenaria_estrutural: not_available / bloqueada por fonte`.
>   O bloqueio é publicado no spec (`scope`), no README de tipologia e na
>   REVISAO, com motivo normativo citável.
> - G28 aplica o **mesmo padrão à fundação**: não inventar tensão admissível,
>   não arbitrar perfil SPT, e registrar que o caso externo falta porque a fonte
>   falta.

---

## 1. O que o vertical de fundação entrega (por que ele é o mais sensível)

| Gate | Módulo | O que faz | Fronteira |
|------|--------|-----------|-----------|
| G9 | `fundacao_edificio.py:29-56`, `geotecnia_spt.py` | Descida `N_base` + `SPT declarado` → `geotecnia_spt.recomenda_fundacao` (sapata × estaca) → `fundacao_sapata` / `estaca_profunda` por pilar; tombamento global `M·x/Σx²` e `V_base` repartido; IFC `IfcFooting`/`IfcPile` | SPT é **entrada declarada**, sem `SIGMA_SOLO_DEFAULT` (`REVISAO-G9-FUNDACAO-EDIFICIO.md:27-31`). Sem `estrutura.fundacao` escopo volta a `not_available` (`fundacao_nao_declarada`). |
| G17 | `fundacao_edificio.py:54,215,534`, `estabilidade_edificio.py:267,498`, `viga_baldrame_edificio.py` | Momento na base por pilar (portico heterogêneo), sapata de divisa / viga de equilíbrio deixam de ser ignoradas | `momento_base_pilar` era `not_available` em G9; G17 o extrai do pórtico plano diferenciado por prumada (`REVISAO-G9:95`). |
| G18 | `viga_baldrame_edificio.py:4`, `recalque_edificio.py:4`, `edificio_adapter.py:139-148` | Viga baldrame + recalque diferencial deixam `not_available` quando declarados | Fronteiras **dentro** da fundação, nomeadas em vez de omitidas (`REVISAO-G9:95`, `edificio_adapter.py:91-148`). |

Regra do projeto (`REVISAO-G9:27-34`): **arbitrar tensão do solo decidiria a fundação inteira a partir de um número que ninguém mediu** — é tratado como bug, não como default. Por isso a validação externa exige um **laudo SPT real** (perfis por furo, `N_SPT` a cada metro, classificação, `N.A.`, cota, ART) — não um item de planilha que diz "sondagem".

---

## 2. Auditoria das três fontes existentes — nenhuma traz laudo

| Fonte (`fontes_externas/registro.json`) | Classe | Tem SPT? | Prova |
|---|---|---|---|
| `licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL` — Escola Quitandinha 401,75 m² (Petrópolis 014/2023) `registro.json:21-32` | `licitacao_executada` (maior autoridade) | **Não — só serviço** | `comparacao.json:89` já registra *banda* mas `fixture.json:12-76` só tem `area_construir`, `volume_concreto_25MPa` (59,84 m³), `volume_capeamento` (23,07 m³), `forma` — **nenhum `N_SPT`, nenhum perfil, nenhum boletim**. Memória EMOP lista **quantitativos** por código (59,84 m³ concreto 25 MPa + 23,07 m³ capeamento) e não a geometria da escola; `relatorio.txt:21-28` confirma que Petrópolis tem `Sondagem, 3 furos × 10 m` apenas como **item de serviço** — o serviço, não o laudo. Sem `pagina` + `trecho_literal` de `N_SPT` não há proveniência para `geotecnia_spt`. |
| `tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL` — UFPE 44×90 (2×22 m, 90 m, 7 m) `registro.json:47-58` | `tcc_academico` | **Não** | `fixture.json:11-81` traz 9 perfis (`W150x29,8`, `W310x39`, `U 200x60`, `d16`…) + `bay 7,5 m`, **zero sondagem**. `comparacao.json`/`relatorio.txt` (G25) discutem FLT, Lb, peso — geotecnia ausente. |
| `tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL` — UFSM 25×54 treliçado `registro.json:60-71` | `tcc_academico` | **Não** | `fixture.json:25-81` (vão 25/54/6, `h1.8`) + `comparacao.json:27-28` ressalva densidade 156 chars/pág — CYPE 3D, **sem SPT**. Medição fitz 4 pág 625 chars (156/pág vs UFPE 696/pág) prova que são tabelas vetoriais, não memorial sondagem. |
| `tcc-exemplo-ufmg-2023-galpao-24x36__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL` | `tcc_academico` (exemplo sintético) | **Não** | `exemplo_dummy.pdf` sintético `registro.json:34-45` — demonstração do protocolo G24, não fonte real. |

**Conclusão da auditoria:** as três fontes externas reais do repositório não contêm nenhum `N_SPT`, perfil estratigráfico, cota de `N.A.` ou recomendação de fundação com `pagina`+`trecho_literal` auditável. O vertical com **mais evolução (G9→G17→G18)** é o **único sem caso externo** — o que motivou G28.

---

## 3. Caça à fonte — FNDE é o caminho mais provável (replicado e completo), mas o padrão separa a sondagem

A hipótese de G28: *os projetos padrão do FNDE são o caminho mais provável, por serem replicados e completos — um pacote de licitação FNDE com o laudo SPT anexo seria replicável em qualquer ente*.

### 3.1 O que o padrão FNDE realmente entrega

Varredura web 2026-09-03 (8 consultas, 30+ PDFs) em `gov.br/fnde`:

**ProInfância Tipo B/C — Projeto Básico e Encartes (pregões RP 093/2012, 009/2013):**
> "Somente após a realização da sondagem do terreno é que será elaborado o Projeto Executivo de Fundações, conforme Encarte E, e caso a Fundação Típica proposta não se adeque ao terreno, deverá ser apresentada outra solução de fundação" — `PE-009-2013 Projeto Básico §5.1 SDG`.

> "5.1. Sondagem do Terreno – SDG – Sondagem ... NBR 6484:1997 (SPT) ... quantidade NBR 8036:1983 ... O relatório técnico de sondagens irá embasar a elaboração do Projeto Executivo de Fundação ... tomando por base a Fundação Típica constante do Projeto de Transposição" — mesmo doc §5.1. Na composição: *mobilização + transporte + profundidade média de 20 m por furo*.

> "Quando da elaboração do Projeto de Transposição ... deve-se considerar uma Fundação Típica ... não havendo necessidade neste momento de apresentação do Projeto Executivo da mesma. Não serão incluídos no Projeto de Transposição elementos de projeto referentes à implantação no terreno, tais como, sondagem, paisagismo, fechamento..." — mesmo doc §2.

**Caderno de Informações Técnicas FNDE — Consulta Pública 4/2025 (implantação):**
> "A sondagem à percussão, conforme NBR 6484/2020, é procedimento técnico indispensável ... com emissão de ART" (`CIT §3.1`).
> "Deverá ser entregue relatório técnico que deverá conter, no mínimo: planta de localização dos furos, perfis individuais, seções geotécnicas, resistência à penetração, classificação do solo, profundidade do lençol freático ... e recomendação da fundação mais adequada" (`CIT §3.1`).
> "O projeto executivo de fundação será responsável ... a partir de relatório de sondagens geotécnicas previamente realizadas e fornecidos pelo município contratante" (`CIT §3.3`).

**Creche Pré-Escola Tipo 1 — Memorial Descritivo (revisões R01/R02/R03) e CQG35ARQMED, PROINFÂNCIA Tipo B/C:**
> "O FNDE fornece um projeto de fundações básico, baseado em previsões/estimativas ... com a finalidade de estabelecer custos estimados para o repasse financeiro. O Ente federado requerente deve ... desenvolver o projeto executivo de fundações, em total obediência às prescrições das Normas próprias da ABNT. O projeto executivo confirmará ou não as previsões ... caso haja divergências, deverá ser homologado pela CGEST" — `Memorial Tipo 1 §4.1.2`, `ProInfância B §4.1`.

> "Sugere-se que sejam realizados ensaios geotécnicos julgados pertinentes ... Para subsidiar ... o ente deverá providenciar os ensaios geotécnicos necessários. Deverá ser adotada solução compatível com intensidade das cargas, capacidade de suporte ... conforme resultados dos ensaios" — mesmo memorial.

**Leopoldina/MG — ETP Creche Tipo 1 Novo PAC (Concorrência semi-integrada 2025):**
> "A Administração fornecerá à contratada informações essenciais, como o relatório da sondagem do terreno, anexo a este processo, para embasar o desenvolvimento dos projetos executivos" — `ETP Leopoldina §3.2`. **Prova de que o pacote que traz SPT existe, mas é anexo municipal ao processo de implantação, não peça do padrão central.**

**Implicação:** o padrão FNDE **não inclui laudo SPT**. Ele publica a *Fundação Típica* (hipotética, para estimar repasse) e cria o item `SDG — Sondagem do Terreno (furo)` (280 furos no RP 009/2013, `Tabela 7: Tipo B 7 furos / Tipo C 4 furos` no SIMEC) cuja execução e laudo são **delegados ao ente** e só então o Projeto Executivo de Fundação é contratado (Encarte E, `CIT §3.3 a`). Replicável como **especificação**, não como **laudo**.

### 3.2 O que foi encontrado além do padrão (serviços avulsos, laudos dispersos)

| Onde | O que tem | Por que não serve como caso FNDE replicável |
|------|-----------|---------------------------------------------|
| Peritiba/SC — PE33/2025 PL180/2025 | 168 m lineares em 24 pontos, NBR 6484/2020, com ART e relatório final | Licitação **de serviço de sondagem** (contrata sondagem), não pacote obra FNDE com fundação dimensionada a partir do laudo — seria validar empresa de sondagem, não `geotecnia_spt → fundacao_sapata`. |
| Terra de Areia/RS — Dispensa 145/2026, ETP 20D45... | ETP + TR + Memorial Descritivo SPT para Escola Infantil, 3 furos, NBR 6484/8036, coleta a cada metro, boletim com cota, perfis, `N` 15+15+15 | Contratação **antes da obra** (serviço avulso) — laudo ainda não existe no processo; item planilha `Sondagem, 3 furos × 10 m` idêntico a Petrópolis (o serviço, não o resultado). |
| UENP/PR — Dispensa 21.317.460-6 | 3 furos até 15 m / impenetrabilidade, boletim com estratigrafia, cota de camada vegetal, N.A. após 24 h, perfil geotécnico NBR 6502 | Serviço de campus, não obra FNDE padrão; sem projeto estrutural que use o laudo. |
| MPMG — SEI 19.16.2431... (Mariana/Ibirité/Janaúba) | SPT + mista, 15 m solo estimado, NBR 8036 área ≤1200 m² → 1 furo/200 m² | Planejamento de sedes MPMG, não FNDE; estimativa de profundidade, sem laudo anexado. |
| GO — FEMBOM Hidrolândia (Sislog GO) | Laudo real com 2 furos, 14/12/2023, perfis individuais, `N` 13/29/40/42/52, Aterro/Argila arenosa, `N.A. 8,45 m`, ART Lauanny | **Laudo real existe**, mas é de **corpo de bombeiros** (obra 688889/8122227), não escola FNDE padrão; área pequena, não replicável como pacote FNDE e sem memorial estrutural que o referencie. |
| Boa Vista/RR — UBS Porte IV Caranã (PMBV-SMOU, jul/22) | Relatório SPT 3 furos com croqui, quadro `N` 10,37, classificação `ARGILOSO ARENOSO BRANCO`, `N.A. 2,62 m`, sondador Nílton Cruz, RT Rodrigo Avila CAU A122866-8 | **Laudo real existe** (3 furos, perfis, N.A.), mas de **UBS**; Nisolede? Seria `hipotese_divergente` tipológica e não testa o fluxo `SPT → fundação de edifício escolar FNDE`. |

**Balanço:** laudos SPT reais **existem** no ecossistema Transparência/licitações (GO, Boa Vista p.1-7), e o padrão FNDE **prevê** que o laudo venha como anexo municipal (Leopoldina comprova). Mas no prazo de G28 nenhum **pacote obra FNDE (Creche Tipo 1/2, Escola 5/9/13 salas, ProInfância B/C) com laudo SPT anexado ao próprio edital da obra** foi localizado no repositório central `gov.br/fnde` — o mecanismo institucional separa o serviço `SDG` da obra e o laudo fica no processo do ente (ex.: `leopoldina.mg.gov.br/abrir_arquivo.aspx/...` que exige scraping municipal).

Não forçar OCR de tabelas vetoriais/imagem nem inventar `N_SPT` sem `pagina`+`trecho_literal` é regra do protocolo G24 (`fontes_externas/README.md:114-144`, `framework/galpao_fw/fontes_externas_protocolo.py:fechar_divergencia`). Um laudo sintético ou com densidade <300 chars/pág sem trecho literal reproduz exatamente o caso `tcc-externo2` (G26) que já foi declarado `nao_comparavel` por baixa densidade (156 chars/pág vs 696).

---

## 4. Decisão G28 — BLOQUEADO (fonte ausente), com precedente honesto

**Veredito G28:** `BLOQUEADO — fonte ausente` para o caso externo de fundação com SPT.

- **Não há invenção:** `geotecnia_spt.py` continua sem default; `fundacao_edificio.py` mantém `fundacao: not_available` sem sondagem e `sondagem declarada` como única porta de entrada. O framework não arbitra `σ_adm`.
- **Não há regressão:** `fontes_externas/registro.json` permanece com 4 entradas (3 reais + 1 exemplo sintético). Nenhuma verificação passou a usar estimativa `110 kg/m³` ou `σ=N/50` sem SPT.
- **Há registro:** esta REVISAO, `fontes_externas/BLOQUEIO-G28-FUNDACAO-SPT.md` (sumário), `wiki/06-open-threads.md#T44` (thread aberta) e `projects/edificio-multipavimento/README.md` (quadro de fronteiras) publicam o bloqueio com motivo — nos quatro lugares do precedente alvenaria.

Critério de desbloqueio (explícito, auditável):
1. Localizar pacote de licitação **obra FNDE padrão** (Creche Tipo 1/2, Escola 9/13, ProInfância B/C, Cobertura Quadra 35 m) **com laudo SPT anexado ao edital da obra** (não só contratação de serviço de sondagem), contendo por furo: locação em planta, **perfis individuais com classificação + `N` a cada metro (15+15+15) + gráfico**, `N.A.` e recomendação, com ART — mesmas exigências do `CIT FNDE §3.1` e `NBR 6484/8036/6502`.
2. Coletar via `tools/extrai_fonte_externa.py --url <pdf-laudo> --classe licitacao_executada --id <municipio-fnde-tipoX>` (gera `registro.json`, `fonte.json`, `fixture.json` esqueleto, `comparacao.json` esqueleto, `original.pdf` com sha256).
3. Preencher `fixture.json` com `pagina`+`trecho_literal` por `N_SPT`/`cota`/`N.A.` e `comparacao.json` com `veredito` do enum fechado G24 (`framework_errado` só com `citacao_normativa` NBR 6118/6122/6484) e `medicao_mesma_definicao` (profundidade de assentamento vs `N_médio` no bulbo, `B` vs `L`, bulbos sobrepostos).
4. Só então fechar T44: o caso vira o **primeiro caso externo da fundação**, espelhando G25 (UFPE, aço) e G27 (Petrópolis, quantitativos) — sem ele, a validação do vertical permanece em `[A CONFIRMAR]` no spec (`fundacao.sondagem: "A CONFIRMAR — perfil SPT"` — `REVISAO-G9:100`).

Até lá, o que não vale — deixar o vertical sem caso externo sem ninguém ter escrito por quê — está cumprido: está escrito aqui, com a caça auditável acima.

---

## 5. Referências auditáveis

- Petrópolis: `fontes_externas/licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/relatorio.txt:11-28`, `fixture.json:12-88`, `comparacao.json:69-133`, `registro.json:21-32` (f9a260c704b6...)
- UFPE 44×90: `fontes_externas/tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/fixture.json:11-81`, `relatorio.txt:20-30`, `registro.json:47-58` (1c7334f60d81...)
- 25×54 treliçado: `fontes_externas/tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/fixture.json:25-81`, `relatorio.txt:17-45`, `comparacao.json:27-112`, `registro.json:60-71` (1fe6f59af568...)
- FNDE — ProInfância Tipo B/C, PE 093/2012, PE 009/2013, RDC 093/2012: `http://www.fnde.gov.br/portaldecompras/...download=1298/1254/1295` (Projeto Básico §5.1 SDG, §2 Transposição, Encarte E, Volume V, NBR 6484/8036, 280 furos, 7/4 por tipologia, fundação típica)
- FNDE — Creche Tipo 1 R03/R02, CQG35ARQMED, ProInfância Tipo C: `gov.br/fnde/.../projeto-tipo-1`, `CQG35ARQMEDGER0_R00.pdf`, `MEMORIAL PADRAO DO FNDE CRECHE TIPO B.pdf` (Memorial §4.1.2: FNDE fornece fundação básica para estimativa, ente projeta executivo)
- FNDE — Consulta Pública 4/2025 CIT: `gov.br/fnde/.../caderno_de_informacoes_tecnicas___implantacoes.pdf` (§3.1 sondagem com ART, §3.3 projeto executivo a partir de sondagem do município, NBR 6484/8036/6502/9603/9820)
- FNDE — Escola 12 salas, 9 salas, 5 salas, Cobertura Quadra 35 m: `gov.br/fnde/.../projeto-espaco-educativo-...`, `gov.br/fnde/.../anexo-a-diretriz-programatica_r01.pdf` (Acórdão TCU 3030/2012 exige relatório de sondagem no projeto básico)
- Leopoldina/MG — ETP Creche Tipo 1 Novo PAC semi-integrada: `leopoldina.mg.gov.br/abrir_arquivo.aspx/...Concorrencia_Publica_2_2025_ANEXO_II...189862...` (Administração fornece relatório da sondagem anexo)
- Peritiba/SC — PE33/2025 PL180/2025 (168 m 24 pontos), Terra de Areia/RS — Dispensa 145/2026 (3 furos), UENP/PR — Dispensa 21.317.460-6 (3 furos 15 m), MPMG SEI 19.16.2431... (SPT 15 m + mista, 1 furo/200 m²), FEMBOM GO — Sislog GO (2 furos 14/12/2023, `N` 13/29/40), Boa Vista/RR — UBS Porte IV (3 furos jul/22, `N.A. 2,62 m`, RT CAU A122866-8)
- Protocolo G24: `fontes_externas/README.md` (G24, hierarquia `licitacao_executada > ... > tcc_academico`, enum `framework_errado/fonte_errada/hipotese_divergente/nao_comparavel/nao_conclusivo`), `fontes_externas/registro.json:1-11` (`_aviso`, `_rotulo_quatro_lugares`), `framework/galpao_fw/fontes_externas_protocolo.py`, `framework/galpao_fw/tests/test_fontes_externas_protocolo.py`
- Fundacão — evolução: `REVISAO-G9-FUNDACAO-EDIFICIO.md:1-34,122-133` (G9), `edificio_adapter.py:24,91,139-148` (G17/G18), `estabilidade_edificio.py:267,498`, `fundacao_edificio.py:29-56`, `viga_baldrame_edificio.py:4-38`, `recalque_edificio.py:4-33`
- Precedente alvenaria: `REVISAO-GAPS-G2-LAJE-ALVENARIA-MULTIPAV.md:130-144` (tabela bloqueio NBR 16868), `REVISAO-G3-MULTIPAVIMENTO.md:64-70`, `REVISAO-G11-VIBRACAO-E-15575.md:247`
