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
| 1 | Fundação (sapata) | [REVISAO-FUNDACAO.md](REVISAO-FUNDACAO.md) | NBR 6118 | ⬜ pendente sênior |
| 2 | Pórtico (análise 1ª+2ª ordem) | [REVISAO-PORTICO.md](REVISAO-PORTICO.md) | NBR 8800 An. D | ⬜ pendente sênior |
| 3 | Verificação de perfil | [REVISAO-CHECK-NBR8800.md](REVISAO-CHECK-NBR8800.md) | NBR 8800 | ⬜ pendente sênior |
| 4 | Vento | [REVISAO-VENTO.md](REVISAO-VENTO.md) | NBR 6123 | ⬜ pendente sênior |
| 5 | Terças (formado a frio) | [REVISAO-TERCAS.md](REVISAO-TERCAS.md) | NBR 14762 | ⬜ pendente sênior |
| 6 | Secundários (longarina/escora/montante) | [REVISAO-SECUNDARIOS.md](REVISAO-SECUNDARIOS.md) | NBR 8800 | ⬜ pendente sênior |
| 7 | Base (placa + chumbadores) | [REVISAO-BASE.md](REVISAO-BASE.md) | NBR 8800 + AISC DG1 | ⬜ pendente sênior |
| 8 | Ligações (joelho/parafusos) | [REVISAO-LIGACOES.md](REVISAO-LIGACOES.md) | NBR 8800 | ⬜ pendente sênior |
| 9 | Ponte rolante | [REVISAO-PONTE.md](REVISAO-PONTE.md) | NBR 8800 + NBR 6120 | ⬜ pendente sênior |
| 10 | Mão-francesa / Lb | [REVISAO-MAO-FRANCESA.md](REVISAO-MAO-FRANCESA.md) | NBR 8800 | ⬜ pendente sênior |
| 11 | Contraventamento | [REVISAO-CONTRAVENTAMENTO.md](REVISAO-CONTRAVENTAMENTO.md) | NBR 8800 | ⬜ pendente sênior |
| 12 | Redimensionamento (auto-sizing) | [REVISAO-REDIMENSIONAMENTO.md](REVISAO-REDIMENSIONAMENTO.md) | — (usa 3) | ⬜ pendente sênior |

Módulos **não-matemáticos** (não precisam de conferência de método): `frame2d`
(solver genérico, validado contra solução fechada), `build_galpao`/`dxf_vistas`
(geometria/desenho), `rodar_galpao`/`rodar_projeto`/`framework` (orquestração),
`projeto_spec` (contrato de dados), `terreno` (KML), `perfis` (tabela de perfis).

Última atualização do índice: 2026-07-06.
