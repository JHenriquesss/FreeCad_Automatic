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
| 1 | Fundação (sapata) | [REVISAO-FUNDACAO.md](REVISAO-FUNDACAO.md) | NBR 6118 | ✅ HOMOLOGADO (r2, 2026-07-07) — §8/§9; fix ρ_min(fck) + adesão na área efetiva |
| 2 | Pórtico (análise 1ª+2ª ordem) | [REVISAO-PORTICO.md](REVISAO-PORTICO.md) | NBR 8800 An. D | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 |
| 3 | Verificação de perfil | [REVISAO-CHECK-NBR8800.md](REVISAO-CHECK-NBR8800.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-06) — §7/§8 |
| 4 | Vento | [REVISAO-VENTO.md](REVISAO-VENTO.md) | NBR 6123 | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 |
| 5 | Terças (formado a frio) | [REVISAO-TERCAS.md](REVISAO-TERCAS.md) | NBR 14762 | ✅ HOMOLOGADO (r2, 2026-07-06) — §8/§9 |
| 6 | Secundários (longarina/escora/montante) | [REVISAO-SECUNDARIOS.md](REVISAO-SECUNDARIOS.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-06) — §6/§7 |
| 7 | Base (placa + chumbadores) | [REVISAO-BASE.md](REVISAO-BASE.md) | NBR 8800 + AISC DG1 | ✅ HOMOLOGADO (r2, 2026-07-07) — §7/§8 |
| 8 | Ligações (joelho/parafusos) | [REVISAO-LIGACOES.md](REVISAO-LIGACOES.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §7/§8 |
| 9 | Ponte rolante | [REVISAO-PONTE.md](REVISAO-PONTE.md) | NBR 8800 + NBR 8400 | ✅ HOMOLOGADO (r2, 2026-07-07) — §7/§8 |
| 10 | Mão-francesa / Lb | [REVISAO-MAO-FRANCESA.md](REVISAO-MAO-FRANCESA.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §5/§6 |
| 11 | Contraventamento | [REVISAO-CONTRAVENTAMENTO.md](REVISAO-CONTRAVENTAMENTO.md) | NBR 8800 | ✅ HOMOLOGADO (r2, 2026-07-07) — §6/§7 |
| 12 | Redimensionamento (auto-sizing) | [REVISAO-REDIMENSIONAMENTO.md](REVISAO-REDIMENSIONAMENTO.md) | — (usa 3) | ✅ HOMOLOGADO (r2, 2026-07-07) — §5/§6; fix flecha H/150→H/300 (Tab.C.1) |

Módulos **não-matemáticos** (não precisam de conferência de método): `frame2d`
(solver genérico, validado contra solução fechada), `build_galpao`/`dxf_vistas`
(geometria/desenho), `rodar_galpao`/`rodar_projeto`/`framework` (orquestração),
`projeto_spec` (contrato de dados), `terreno` (KML), `perfis` (tabela de perfis).

**Todos os 12 módulos matemáticos HOMOLOGADOS (rodada 2, 2026-07-07).**

Última atualização do índice: 2026-07-07.
