# G28 — Fundação: BLOQUEADO por fonte — sem laudo SPT anexado

> **CONCORDANCIA ENTRE CALCULISTAS — NAO E OBRA CONSTRUIDA**
> Nenhum número aqui valida o framework contra obra edificada.
> Este aviso replica-se em (1) nome do diretório/arquivo de bloqueio,
> (2) REVISAO-G28, (3) fontes_externas/README (protocolo G24) e
> (4) wiki 06-open-threads T44 — padrão de quatro lugares.

**Status G28:** `BLOQUEADO — fonte ausente` para caso externo de fundação com SPT.

- As três fontes do repo **não trazem sondagem com resultados**: Petrópolis tem `Sondagem, 3 furos × 10 m` só como **item de serviço** (o serviço, não o laudo) — `fontes_externas/licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/fixture.json` sem `N_SPT`; UFPE 44×90 e 25×54 treliçado idem — só perfis/galpão, sem `N_SPT`, `N.A.` ou perfil estratigráfico (`tcc-ufpe/.../fixture.json`, `tcc-externo2/.../fixture.json`).
- O vertical de fundação é o **mais evoluído** (G9 `fundacao_edificio.py:29` SPT como entrada declarada sem default; G17 momento por pilar; G18 baldrame+recalque — `REVISAO-G9`, `edificio_adapter.py:91-148`) e o **único sem caso externo** — dois TCCs de aço + uma licitação de quantitativos não cobrem `geotecnia_spt → fundacao_sapata/estaca`.
- **Caça FNDE 2026-09-03:** o padrão FNDE (ProInfância B/C, Creche Tipo 1/2, Escola 9/13 salas) **separa a sondagem** — `SDG — Sondagem do Terreno (furo)` NBR 6484/8036 como item orçado (280 furos no RP 009/2013; 7 furos Tipo B / 4 Tipo C no SIMEC) e entrega só **Fundação Típica hipotética** para estimar repasse; "Somente após a realização da sondagem ... será elaborado o Projeto Executivo de Fundações" (`PE-009-2013 §5.1`, `CIT FNDE 4/2025 §3.1/3.3`, `Memorial Tipo 1 §4.1.2`). O laudo, quando existe, é **anexo municipal** do processo de implantação (Leopoldina ETP: "Administração fornecerá ... relatório da sondagem ... anexo a este processo") — não peça central replicável. Laudos reais avulsos (GO FEMBOM 2 furos `N` 13/29/40 + `N.A. 8,45 m`; Boa Vista UBS 3 furos `N.A. 2,62 m`, RT CAU A122866-8; Peritiba 24 furos/168 m; Terra de Areia 3 furos) existem mas são **serviços de sondagem** ou obras não-FNDE dispersas, sem pacote obra+estrutura completo para reproduzir `N_SPT → sigma_adm → sapata/bloco/estaca` sob mesma definição.

**Precedente honesto:** alvenaria estrutural segue bloqueada por falta da NBR 16868 (`REVISAO-GAPS-G2:130-144`, `REVISAO-G3:64-70`, `REVISAO-G11:247`, `edificio_adapter.py:16,76`, `estrutura_casa.py:630,713` — `alvenaria_estrutural: not_available`). G28 replica o padrão à fundação: **não arbitrar `σ_adm`**, não inventar `N_SPT` sem `pagina`+`trecho_literal`, e publicar o buraco.

**Desbloqueio auditável:** pacote obra FNDE padrão com **laudo SPT anexado ao próprio edital da obra** (planta furos + perfis individuais com classificação + `N` a cada metro + gráfico + `N.A.` + ART), coletado via `tools/extrai_fonte_externa.py --classe licitacao_executada` e com `fixture.json` `pagina`+`trecho_literal` por `N_SPT` e `comparacao.json` enum G24 — só `framework_errado`+`citacao_normativa` (NBR 6118/6122/6484) autoriza calibrar. Até lá, o vertical fica sem caso externo **com motivo escrito** — o que não vale é ficar sem caso e sem registro.

Referência completa (caça, citações, tabelas): `framework/galpao_fw/REVISAO-G28-FUNDACAO-FONTE-BLOQUEADA.md`.
