# Índice — documentos de revisão (conferência matemática)

Um markdown por módulo de cálculo, para o engenheiro sênior conferir o
**método** e a **matemática** sem abrir o código-fonte. Cada doc traz: escopo,
itens da norma usados, fórmulas, **código verbatim** das rotinas de cálculo e
os FLAGS/pendências.

> CONCEITUAL — o framework calcula e dimensiona; o engenheiro responsável revisa
> e assina (ART). Métodos extraídos das normas em `pesquisa/aço/` (não de memória).

## Documentos

| # | Módulo | Doc | Norma principal | Status revisão |
|---|--------|-----|-----------------|----------------|
| 1 | Fundação (sapata) | [REVISAO-FUNDACAO.md](REVISAO-FUNDACAO.md) | NBR 6118 | ✅ HOMOLOGADO r2 · ✅ features punção (§10) + recalque (§11) HOMOLOGADAS (2026-07-07) |
| 2 | Pórtico (análise 1ª+2ª ordem) | [REVISAO-PORTICO.md](REVISAO-PORTICO.md) | NBR 8800 An. D | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 |
| 3 | Verificação de perfil | [REVISAO-CHECK-NBR8800.md](REVISAO-CHECK-NBR8800.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-06) — §7/§8 |
| 4 | Vento | [REVISAO-VENTO.md](REVISAO-VENTO.md) | NBR 6123 | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 · ✅ Cpe médio local borda/canto §8 (Tab.4/5, 2026-07-08) HOMOLOGADO |
| 5 | Terças (formado a frio) | [REVISAO-TERCAS.md](REVISAO-TERCAS.md) | NBR 14762 | ✅ HOMOLOGADO (r2, 2026-07-06) — §8/§9 |
| 6 | Secundários (longarina/escora/montante) | [REVISAO-SECUNDARIOS.md](REVISAO-SECUNDARIOS.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 |
| 7 | Base (placa + chumbadores) | [REVISAO-BASE.md](REVISAO-BASE.md) | NBR 8800 + AISC DG1 + ACI 318 | ✅ **100% HOMOLOGADO §9-§13** (ancoragem, cone, cortante-tríade, edge breakout, interação T-V trilinear+5/3, 2026-07-08) |
| 8 | Ligações (joelho/parafusos) | [REVISAO-LIGACOES.md](REVISAO-LIGACOES.md) | NBR 8800 | ✅ HOMOLOGADO r2 · ✅ detalhamento furos §9 (6.3.9/10/11, 2026-07-08) HOMOLOGADO |
| 9 | Ponte rolante | [REVISAO-PONTE.md](REVISAO-PONTE.md) | NBR 8800 + NBR 8400 | ✅ **100% HOMOLOGADO** · fadiga Anexo K §9 + 50% lateral B.7.3.4 §9.1 (2026-07-08) |
| 10 | Mão-francesa / Lb | [REVISAO-MAO-FRANCESA.md](REVISAO-MAO-FRANCESA.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §5/§6 |
| 11 | Contraventamento | [REVISAO-CONTRAVENTAMENTO.md](REVISAO-CONTRAVENTAMENTO.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §6/§7 |
| 12 | Redimensionamento (auto-sizing) | [REVISAO-REDIMENSIONAMENTO.md](REVISAO-REDIMENSIONAMENTO.md) | — (usa 3) | ✅ HOMOLOGADO (r2, 2026-07-07) — §5/§6; fix flecha H/150→H/300 (Tab.C.1) |
| 13 | Junta de dilatação / temperatura | [REVISAO-JUNTA-DILATACAO.md](REVISAO-JUNTA-DILATACAO.md) | Bellei / FCC Report 65 | ✅ HOMOLOGADO (2026-07-08) — §1-§4 |
| 14 | Sismo (forças horizontais equivalentes) | [REVISAO-SISMO.md](REVISAO-SISMO.md) | NBR 15421:2023 | ✅ HOMOLOGADO (2026-07-08) — §1-§5 · ✅ sismo→envelope excepcional §6 (5.4 / NBR 8681, 2026-07-09) HOMOLOGADO |
| 15 | Telha de cobertura (vão × carga) | [REVISAO-TELHA.md](REVISAO-TELHA.md) | NBR 14762 | ✅ HOMOLOGADO (2026-07-08) — §1-§6 |
| 16 | Viga de baldrame / amarração | [REVISAO-BALDRAME.md](REVISAO-BALDRAME.md) | NBR 6118 | ✅ HOMOLOGADO (2026-07-08) — correções de cisalhamento e armadura superior aplicadas |
| 17 | Fundação profunda (estaca + bloco) | [REVISAO-ESTACA.md](REVISAO-ESTACA.md) | Aoki-Velloso / NBR 6122 / NBR 6118 | ✅ HOMOLOGADO (2026-07-08) — correção uplift aplicada |

| 18 | Pórtico multi-vão (geminado, N≥2) | [REVISAO-MULTI-VAO.md](REVISAO-MULTI-VAO.md) | NBR 8800 + NBR 6123 Tab.7 | ✅ HOMOLOGADO |
| 19 | Sapata de divisa / viga alavanca | [REVISAO-DIVISA.md](REVISAO-DIVISA.md) | NBR 6122 / Velloso & Lopes | ✅ HOMOLOGADO |
| 20 | Dimensionamento ao fogo (NBR 14323) | [REVISAO-FOGO.md](REVISAO-FOGO.md) | NBR 14323:2013 + ISO 834 | ✅ HOMOLOGADO |
| 21 | Calhas e condutores | [REVISAO-CALHAS.md](REVISAO-CALHAS.md) | Bellei §2.4 / NBR 10844 | ✅ HOMOLOGADO |
| 22 | Plataformas e passarelas | [REVISAO-PLATAFORMA.md](REVISAO-PLATAFORMA.md) | NBR 8800 / NBR 6120 | ✅ HOMOLOGADO |
| 23 | Escadas industriais | [REVISAO-ESCADA.md](REVISAO-ESCADA.md) | NBR 8800 / NBR 6120 / NR-18 | ✅ HOMOLOGADO |
| 24 | Detalhamento de armadura | `fundacao_sapata.py` (ancoragem + quadro) | NBR 6118 9.4 | ✅ HOMOLOGADO |
| 25 | Carga de neve | [REVISAO-NEVE.md](REVISAO-NEVE.md) | EN 1991-1-3 | ✅ HOMOLOGADO |
| 26 | Pórtico alma variável | [REVISAO-ALMA-VARIAVEL.md](REVISAO-ALMA-VARIAVEL.md) | NBR 8800 | ✅ HOMOLOGADO |
| 27 | Pórtico treliçado (tesoura) | [REVISAO-TESOURA.md](REVISAO-TESOURA.md) | NBR 8800 | ✅ HOMOLOGADO |
| 28 | Gusset de contraventamento | [REVISAO-GUSSET.md](REVISAO-GUSSET.md) | NBR 8800 + Whitmore (AISC) | ✅ HOMOLOGADO (2026-07-10) |
| 29 | Console da ponte rolante (ligação) | [REVISAO-CONSOLE.md](REVISAO-CONSOLE.md) | NBR 8800 + grupo de solda elástico | ✅ HOMOLOGADO — APROVADO COM LOUVOR (2026-07-11) |
| 30 | Fundação profunda — **integração** (spec + 3D) | [REVISAO-FUNDACAO-PROFUNDA-INTEG.md](REVISAO-FUNDACAO-PROFUNDA-INTEG.md) | integração (método já em ESTACA/BALDRAME) | ✅ HOMOLOGADO (2026-07-11) — Q1 (FS gate 3,0/prova) + Q3b (tan≥1,0) + Q2–Q6 |
| 31 | Ponte rolante estendida — rodas motoras + NBR 8400 | [REVISAO-PONTE-8400.md](REVISAO-PONTE-8400.md) | NBR 8800 (frenagem) + NBR 8400-1:2019 Tab.9/12 | ✅ HOMOLOGADO (2026-07-11) — Q1 defesa aceita; Q2/Q3/Q4 ok |
| 32 | Pórtico alma variável — **integração** (análise + spec + 3D) | [REVISAO-ALMA-VARIAVEL-INTEG.md](REVISAO-ALMA-VARIAVEL-INTEG.md) | integração (secao_tapered já homologado) | 🔁 PARECER 1 ATENDIDO — REVER (2026-07-11) — Q2 (verificação por segmento) feito; Q1/Q3 backlog; Q4 ok |
| 33 | Pórtico treliçado (tesoura) — **cálculo novo** + 3D | [REVISAO-TESOURA-INTEG.md](REVISAO-TESOURA-INTEG.md) | método dos nós (novo) + NBR 8800 (barras) | 🆕 PENDENTE SÊNIOR (2026-07-10) — [Q1]…[Q5]; solver+verificação são método NOVO |

Módulos **não-matemáticos** (não precisam de conferência de método): `frame2d`
(solver genérico, validado contra solução fechada), `build_galpao`/`dxf_vistas`
(geometria/desenho), `rodar_galpao`/`rodar_projeto`/`framework` (orquestração),
`projeto_spec` (contrato de dados), `terreno` (KML), `perfis` (tabela de perfis).

---

## 🆕 Features novas para revisão (fecham a análise de lacunas do projeto completo)

Adicionadas **após** a homologação r2 dos 12 módulos — cada uma com método +
citação normativa do PDF + selftest. **TODAS HOMOLOGADAS (2026-07-07/08):**

| Feature | Módulo / doc | Norma / referência | Onde |
|---|---|---|---|
| ✅ Punção da sapata flexível | fundação | NBR 6118 19.5 | [FUNDACAO §10](REVISAO-FUNDACAO.md) — HOMOLOGADA |
| ✅ Recalque elástico da sapata | fundação | NBR 6122 / Perloff (Veloso & Lopes) | [FUNDACAO §11](REVISAO-FUNDACAO.md) — HOMOLOGADA |
| ✅ Ancoragem do chumbador (aderência) | base | NBR 6118 9.4.2 | [BASE §9](REVISAO-BASE.md) — HOMOLOGADA |
| ✅ Cone de arrancamento / grupo | base | ACI 318 Ch.17 (Nilson cap.21) | [BASE §10](REVISAO-BASE.md) — HOMOLOGADO |
| ✅ Cortante-tríade (atrito+chumbador+chaveta) | base | NBR 8800 (Fakury cap.11) | [BASE §11](REVISAO-BASE.md) — HOMOLOGADO |
| ✅ Fadiga da viga de rolamento (+50% lat B.7.3.4) | ponte | NBR 8800 Anexo K | [PONTE §9](REVISAO-PONTE.md) — HOMOLOGADA |
| ✅ Junta de dilatação / mov. térmico | junta (novo) | Bellei 4.5 / FCC Report 65 | [JUNTA](REVISAO-JUNTA-DILATACAO.md) — HOMOLOGADA |
| ✅ Ação sísmica (forças horiz. equiv.) | sismo (novo) | NBR 15421:2023 | [SISMO](REVISAO-SISMO.md) — HOMOLOGADA |
| ✅ Detalhamento de furos (espaçamento/borda) | ligações | NBR 8800 6.3.9/10/11 | [LIGACOES §9](REVISAO-LIGACOES.md) — HOMOLOGADO |
| ✅ Cpe médio local de borda/canto (telha/terça/fixador) | vento | NBR 6123 Tab.4/5 | [VENTO §8](REVISAO-VENTO.md) — HOMOLOGADO |
| ✅ Telha de cobertura (vão × carga) | telha (novo) | NBR 14762 | [TELHA](REVISAO-TELHA.md) — HOMOLOGADO |
| ✅ Sismo → envelope (combinação excepcional) | pórtico/estab./base | NBR 15421 5.4 / NBR 8681 | [SISMO §6](REVISAO-SISMO.md) — HOMOLOGADO |
| ✅ Viga de baldrame / amarração entre sapatas | baldrame (novo) | NBR 6118 | [BALDRAME](REVISAO-BALDRAME.md) — HOMOLOGADO (cisalhamento + armadura superior corrigidos) |
| ✅ Fundação profunda (estaca Aoki-Velloso + bloco) | estaca (novo) | Aoki-Velloso / NBR 6122 / 6118 | [ESTACA](REVISAO-ESTACA.md) — HOMOLOGADO (uplift corrigido) |

**Fixes de geometria do build 3D** (calha invertida, telha sobre as terças, chapa
de ápice, regra de auditoria da calha) — `build_galpao.py`, verificados ao vivo no
FreeCAD (0 interferências / 0 conexões suspeitas). Módulo não-matemático; sem doc
de método, mas registrado no `wiki/04-decisions.md` (D7).

**Análise de lacunas ENCERRADA** (2026-07-08): fechadas as 3 pequenas (furos,
Cpe local, telha), as 2 médias (sismo→envelope, baldrame) e a **grande** (fundação
profunda — estaca Aoki-Velloso + bloco). Resíduos como FLAG documentado:
Décourt-Quaresma (2º método de estaca, cross-check), verificação de biela/punção do
bloco, e efeitos de grupo/atrito negativo da estaca — trabalhos futuros, não
bloqueiam. Base **100 % completa nos modos do concreto** (§9-§13).

---

**27 módulos matemáticos + features — TODOS HOMOLOGADOS (2026-07-08).**
Pipeline: 23 gates, 35 módulos totais (incl. não-matemáticos: frame2d, build, dxf,
rodar, projeto_spec, perfis, framework). Testado end-to-end: galpão 24×12m →
FreeCAD 669 obj, 0 interferências, 20.156 kg aço.

Última atualização: 2026-07-08.
