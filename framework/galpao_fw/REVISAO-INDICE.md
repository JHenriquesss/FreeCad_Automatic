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
| 4 | Vento | [REVISAO-VENTO.md](REVISAO-VENTO.md) | NBR 6123 | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 |
| 5 | Terças (formado a frio) | [REVISAO-TERCAS.md](REVISAO-TERCAS.md) | NBR 14762 | ✅ HOMOLOGADO (r2, 2026-07-06) — §8/§9 |
| 6 | Secundários (longarina/escora/montante) | [REVISAO-SECUNDARIOS.md](REVISAO-SECUNDARIOS.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 |
| 7 | Base (placa + chumbadores) | [REVISAO-BASE.md](REVISAO-BASE.md) | NBR 8800 + AISC DG1 + ACI 318 | ✅ HOMOLOGADO §9-§12 · 🆕 interação T-V §13 (2026-07-08) PENDENTE |
| 8 | Ligações (joelho/parafusos) | [REVISAO-LIGACOES.md](REVISAO-LIGACOES.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §7/§8 |
| 9 | Ponte rolante | [REVISAO-PONTE.md](REVISAO-PONTE.md) | NBR 8800 + NBR 8400 | ✅ **100% HOMOLOGADO** · fadiga Anexo K §9 + 50% lateral B.7.3.4 §9.1 (2026-07-08) |
| 10 | Mão-francesa / Lb | [REVISAO-MAO-FRANCESA.md](REVISAO-MAO-FRANCESA.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §5/§6 |
| 11 | Contraventamento | [REVISAO-CONTRAVENTAMENTO.md](REVISAO-CONTRAVENTAMENTO.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §6/§7 |
| 12 | Redimensionamento (auto-sizing) | [REVISAO-REDIMENSIONAMENTO.md](REVISAO-REDIMENSIONAMENTO.md) | — (usa 3) | ✅ HOMOLOGADO (r2, 2026-07-07) — §5/§6; fix flecha H/150→H/300 (Tab.C.1) |
| 13 | Junta de dilatação / temperatura | [REVISAO-JUNTA-DILATACAO.md](REVISAO-JUNTA-DILATACAO.md) | Bellei / FCC Report 65 | ✅ HOMOLOGADO (2026-07-08) — §1-§4 |
| 14 | Sismo (forças horizontais equivalentes) | [REVISAO-SISMO.md](REVISAO-SISMO.md) | NBR 15421:2023 | ✅ HOMOLOGADO (2026-07-08) — §1-§5 |

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

**Fixes de geometria do build 3D** (calha invertida, telha sobre as terças, chapa
de ápice, regra de auditoria da calha) — `build_galpao.py`, verificados ao vivo no
FreeCAD (0 interferências / 0 conexões suspeitas). Módulo não-matemático; sem doc
de método, mas registrado no `wiki/04-decisions.md` (D7).

Ainda **em aberto** (análise de lacunas): **fundações profundas** (estaca/tubulão)
— única grande. Base **100 % completa nos modos do concreto** (§9-§13); armadura de
ancoragem entra como WARNING (hairpin) ao projeto de fundação.

---

**12 módulos matemáticos HOMOLOGADOS (r2, 2026-07-07)** + **7 features novas
(punção, recalque, ancoragem, cone ACI, cortante-tríade, fadiga+lateral, junta)
TODAS HOMOLOGADAS (2026-07-08)** + build fixes verificados no FreeCAD.

Última atualização do índice: 2026-07-07.
