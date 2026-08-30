# Edifício multipavimento — caso de integração da tipologia `edificio`

Edifício residencial de 8 pavimentos-tipo + cobertura, malha 3 × 2 vãos
(14,0 m × 9,0 m), pé-direito 2,90 m, concreto C30 e aço CA-50.

**Isto não é um projeto liberado para obra.** É o caso que exercita a cadeia
de cálculo do G3 pelo Project Loop de ponta a ponta. Falta o que está
declarado como `not_available` no escopo da disciplina — veja abaixo.

## Como rodar

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/edificio-multipavimento/project-spec.json `
  --out-dir exports/edificio --no-ifc
```

## O que sai

- `project-run.json` — manifesto com o estado da disciplina `estrutura`, os
  cinco gates do G3 (`fechamento_carga`, `reducao_6120`, `pilares`, `laje`,
  `vigas`) e o registro da redução da NBR 6120 §6.12;
- `drawings/planta-formas-pavimento-tipo.svg` — planta de formas do
  pavimento-tipo com os 12 pilares e a descida de cargas.

Não há IFC nem modelo 3D: o adaptador declara apenas `report` e `drawings`.
Capacidade não declarada é capacidade que não existe.

## O contrato de entrada

`turnkey.estrutura` é obrigatório e não tem default de engenharia. Sem ele o
Loop devolve `blocked` com `missing_structure_input` — o adaptador não arbitra
um edifício.

`turnkey.geometria` (o envelope comum que o Loop usa para coordenar) e
`turnkey.estrutura.geometria` (os vãos que a estrutura calcula) são duas
declarações do mesmo prédio. O adaptador confere as duas: `comprimento` contra
a soma de `vaos_x`, `vao` contra a soma de `vaos_y` e os dois pés-direitos,
com tolerância de 10 mm. Divergir devolve `geometry_mismatch`, não um projeto
em que o Loop coordena um envelope e a estrutura calcula outro.

## O que este caso NÃO cobre

Todos declarados como `not_available` no `scope` da disciplina, para que o
manifesto os publique em vez de omiti-los (itens abertos da seção 10 de
`framework/galpao_fw/REVISAO-G3-MULTIPAVIMENTO.md`):

| Item | Situação |
| --- | --- |
| `vento` | a descida implementada é gravitacional; falta a parcela por pavimento |
| `desaprumo` | 11.3.3.4.1 não entra nos esforços |
| `estabilidade_global` | nada alimenta γz com `dM_tot_d` de múltiplos pavimentos |
| `alvenaria_estrutural` | bloqueada por fonte — NBR 16868 ausente do acervo |
| `fundacao` | a descida entrega `N_base`; ninguém a dimensiona aqui |
| `vibracao_piso` | aberto desde a auditoria de gaps do G2 |

Nenhuma disciplina termina `passed`: aprovação para obra exige responsável
técnico e ART.

## Fontes

Referenciadas em `source_refs.estrutura`, todas verificadas no acervo:

- ABNT NBR 6118:2023 + Emenda 1:2026 — projeto de estruturas de concreto;
- ABNT NBR 6120:2019 — ações para o cálculo de estruturas de edificações;
- ABNT NBR 8681:2025 — ações e segurança nas estruturas.

## Nota sobre a seção dos pilares

O orquestrador adota a menor seção que atende, como o resto do framework. Numa
malha residencial de 9 pavimentos isso leva os pilares de canto e de
extremidade ao limite prático — seções finas e muito armadas. Para um projeto
mais folgado, passe uma lista `SECOES_PILAR` começando mais alta; a política em
si não foi alterada aqui.
