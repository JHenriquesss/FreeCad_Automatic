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
| 32 | Pórtico alma variável — **integração** (análise + spec + 3D) | [REVISAO-ALMA-VARIAVEL-INTEG.md](REVISAO-ALMA-VARIAVEL-INTEG.md) | integração (secao_tapered já homologado) | ✅ HOMOLOGADO (2026-07-11) — solver absolvido; FLT trecho + Lb dinâmico ok |
| 33 | Pórtico treliçado (tesoura) — **cálculo novo** + 3D | [REVISAO-TESOURA-INTEG.md](REVISAO-TESOURA-INTEG.md) | método dos nós (novo) + NBR 8800 (barras) | ✅ HOMOLOGADO (2026-07-11) — Q5 duas águas + ruptura líq. + compressão 2 eixos + guard n_paineis par |
| 34 | Coluna de alma variável (tapered) — fecha Q1 da fase 6.b | [REVISAO-COLUNA-TAPERED.md](REVISAO-COLUNA-TAPERED.md) | integração (secao_tapered já homologado) + NBR 8800 Anexo J.3/J.4 | ✅ HOMOLOGADO (2026-07-11) — parecer 2 refutado (acusação de citação falsa caiu); +compressão global J.3 +continuidade estrita; sênior retratou-se |
| 35 | Zona de painel do joelho (cisalhamento + doubler) — fecha Q3 da fase 6.b | [REVISAO-ZONA-PAINEL.md](REVISAO-ZONA-PAINEL.md) | NBR 8800 §5.7.7 + §5.7.2/3/4/6 + §5.4.3 (verbatim do PDF) | ✅ HOMOLOGADO (2026-07-11) — FSd−V_col + enrugamento §5.7.4 + esbeltez doubler; parecer 2 (0,80/0,40 AISC) refutado com imagens do PDF |
| 36 | FLT de mísula (Anexo J) — refino tapered; corrige framing do "fator γ" | [REVISAO-FLT-MISULA.md](REVISAO-FLT-MISULA.md) | NBR 8800 Anexo J (J.4.1/J.4.2) + §5.4.2.3a Cb (verbatim do PDF) | ✅ HOMOLOGADO (2026-07-11) — todas as cláusulas aprovadas; nota técnica (h_m/Wx por segmento) verificada |
| 37 | Sucção de vento auto-acoplada à tesoura | [REVISAO-VENTO-TESOURA.md](REVISAO-VENTO-TESOURA.md) | NBR 6123 (Cpe−Cpi)·q + NBR 8681 (combinação uplift) | ✅ HOMOLOGADO (2026-07-11) — bug de sinal do uplift corrigido (`+0,9·w_dead`, sem Q); "aprovado para merge" |
| 38 | Momento resistente de alma esbelta (Anexo H) — fecha 4b do parecer 2 | [REVISAO-ALMA-ESBELTA.md](REVISAO-ALMA-ESBELTA.md) | NBR 8800 Anexo H (H.2.1/2.2/2.3 + kpg) + F.2 kc (verbatim do PDF) | ✅ HOMOLOGADO (2026-07-11) — despacho h/tw>5,70√(E/fy); Wxc+kpg; FLM/Cb já corretos (parecer refutado); "aprovado para merge" |
| 39 | Interação M-V no joelho de alma esbelta (verificação por tensões) — fecha dívida (d) da fase 6.b | [REVISAO-TENSAO-PONTO.md](REVISAO-TENSAO-PONTO.md) | NBR 8800 §5.5.2.3 (alíneas a–d, σ/τ da teoria da elasticidade; pág 57 verbatim) + von Mises suplementar (não-NBR, flag) | ✅ HOMOLOGADO (2026-07-12) — "APROVADO COM OBSERVAÇÕES": σ/τ/Qf/von Mises milimetricamente corretos (dedução reversa); 3 observações de premissa (χn=1,0, cos²θ, von Mises na instab.) acatadas como documentação; zero bug de fórmula |
| 40 | Cortante da alma com mesas inclinadas (barra tapered) — fecha dívida (a) da fase 6.b | [REVISAO-CORTANTE-TAPERED.md](REVISAO-CORTANTE-TAPERED.md) | Equilíbrio (mecânica) — NÃO-NBR; Anexo J (J.1–J.4) não trata cortante, J.1.2→§5.4.3 (prova verbatim) | ✅ HOMOLOGADO (2026-07-12) — mecânica/topologia/norma/testes aprovados (Blodgett/Salmon-Johnson); **corrigido braço de alavanca**: adverso usa `h_0=h_m−tf` (era `h_m`, subestimava acréscimo → inseguro), favorável mantém `h_m`; sem regressão (galpão haunch) |
| 41 | Vento por zona na tesoura (90° por água + 0° longitudinal) — fecha dívida (c) da fase 6.b | [REVISAO-VENTO-ZONA-TESOURA.md](REVISAO-VENTO-ZONA-TESOURA.md) | NBR 6123 Tabela 5 (Cpe 90° EF/GH + 0° EG/FH, verbatim pág 15) + NBR 8681 | ✅ HOMOLOGADO (2026-07-12) — parecer: **+caso vento 0° (uplift simétrico, faltava e podia governar)**, cumeeira=média, γg pressão (0,9/1,4), Cpi par-fixo explícito (refutado como bug, mantido); envelope 90+0; u=0,928 honesto |
| 42 | Cross-check DG25 da FLT de mísula (VALIDAÇÃO, não dimensionamento) — fecha dívida (b) da fase 6.b | [REVISAO-DG25-CROSSCHECK.md](REVISAO-DG25-CROSSCHECK.md) | AISC Design Guide 25 §5.4.3 (M_eLTB elástico, F4-5; pág 60–61 verbatim por imagem) vs NBR 8800 Anexo J | ✅ HOMOLOGADO (2026-07-12) — "aprovado para integração": F_eLTB/rt/J impecáveis; sênior confirmou o ~0,5 = `(h_meio/h_max)²` (não erro); Cb-cancela esclarecido como premissa de teste; DIVERGE mantido como alerta visual |
| 43 | Enrijecedores transversais da alma (painel do joelho) — fecha dívida (e) da fase 6.b | [REVISAO-ENRIJECEDOR-PAINEL.md](REVISAO-ENRIJECEDOR-PAINEL.md) | NBR 8800 §5.4.3.1 (kv=5+5/(a/h)², V_Rd; §5.4.3.1.3 b/t, I_st≥a·tw³·j, j=[2,5/(a/h)²]−2≥0,5; pág 50–51 verbatim por imagem) | ✅ HOMOLOGADO — APROVADO COM LOUVOR (2026-07-13) — "matematicamente exato e normativamente irrepreensível"; **1 acolhido** (`a_min→a_max`); 2 refutações confirmadas (eixo I singelo = plano médio NBR §5.4.3.1.3c; §5.4.3.2 = tubular ≠ tension field); `ist_singelo` opt-in elogiado |
| 44 | DG25 full — Cb tapered (5.4-1/2) + Mn nominal completo (Rpc/Rpg/F_L/3 regiões) — refino do item 42 | [REVISAO-DG25-FULL.md](REVISAO-DG25-FULL.md) | AISC Design Guide 25 §5.4.1–5.4.3 (5.4-1..5.4-21; pág 58–62 verbatim por imagem) vs NBR 8800 Anexo J/G | ✅ HOMOLOGADO E ENCERRADO — validado p/ integração (2026-07-13) — "escopo cumprido com rigor"; `γ·f_r=F_eLTB` "mais elegante"; 5% inelástico = diferença de método; 3 resoluções aceitas (F_L monossim. já coberto 5.4-15; sinais Cb documentados; aw≤10 verbatim) |
| 45 | props_I_mono — propriedades de perfil I monossimétrico (Wxc/Wxt, Iyc/Iy, hc/hp, Cw, J, rt) — habilita o ramo monossimétrico real do DG25 (fecha refino do item 44) | [REVISAO-PROPS-MONO.md](REVISAO-PROPS-MONO.md) | Mecânica de seção (redução exata ao duplo-simétrico `props_I`); DG25 5.4-11/5.4-15 | ✅ HOMOLOGADO SEM RESSALVAS (fase 6.15, 2026-07-13): parecer pegou rt 5.4-11 hc²→**hw²** (h livre da alma), corrigido e re-aprovado; dupl-sim inalterado, mono era +2,3% contra a segurança. 11 testes |
| 46 | DG25 envelope — FLB (§5.4.4), TFY (§5.4.5), ruptura (§5.4.6), envelope min (§5.4.7) | [REVISAO-DG25-ENVELOPE.md](REVISAO-DG25-ENVELOPE.md) | AISC Design Guide 25 §5.4.4–5.4.7 (5.4-14..5.4-32; pág 62–64 verbatim por imagem) | ✅ PARECER — 1 CORRIGIDO/1 REJEITADO (fase 6.16, 2026-07-13): F1 kc 5.4-24 hc→**hw** (corrigido, +7,8% contra segurança no mono); F2 teto Mp Sxt (rejeitado — DG25 5.4-28 verbatim usa Sxt). 12 testes |
| 47 | Forças transversais localizadas + enrijecedor de apoio | [REVISAO-FORCAS-LOCALIZADAS.md](REVISAO-FORCAS-LOCALIZADAS.md) | NBR 8800 §5.7.2–5.7.9 (6,25tf²; 1,10(5k+ln); enrugamento 0,66/0,33; Cr[0,94+0,37]; 24tw³; enrij. Lb=0,75h faixa 12tw/25tw; pág 57–62 verbatim por imagem) | ⏳ AGUARDANDO PARECER (fase 6.17, 2026-07-13) — fecha backlog "enrijecedor de apoio §5.7.4" |
| 48 | Viga de equilíbrio de divisa sobre estacas (variante profunda) | [REVISAO-VIGA-EQUILIBRIO.md](REVISAO-VIGA-EQUILIBRIO.md) | Alonso/Velloso & Lopes (R'=P·l/(l−e), estática já validada em `sapata_divisa`) + estaca_profunda + NBR 6118 (viga RC) | ⏳ AGUARDANDO PARECER (fase 6.18, 2026-07-13) — wiring ramifica estaca/sapata em `rodar_galpao` |
| 49 | Executivo 2D — glyph AWS de solda (headless via DrawViewSymbol) + quadros PE09 legíveis | [REVISAO-EXECUTIVO-POLISH.md](REVISAO-EXECUTIVO-POLISH.md) | AWS A2.4 (símbolo de filete) + TechDraw | ⏳ AGUARDANDO PARECER (fases 6.19/6.12, 2026-07-13) — polimento visual; resolve o último resíduo do 2D (T6) |

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
