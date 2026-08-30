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
| `alvenaria_estrutural` | bloqueada por fonte — NBR 16868 ausente do acervo |
| `fundacao` | a descida entrega `N_base`; ninguém a dimensiona aqui |
| `vibracao_piso` | aberto desde a auditoria de gaps do G2 |

## Ação horizontal

`turnkey.estrutura.vento` é opcional, mas sem ele o escopo recua: `vento`,
`desaprumo`, `estabilidade_global` e `deslocamento_lateral_els` voltam a
`not_available`, e o resultado emite `acao_horizontal_nao_avaliada` dizendo que
a descida ficou apenas gravitacional. Declarado, saem calculados:

- **vento por pavimento** (NBR 6123 4.2.3, `Fa = Ca q Ae`), com `q` recalculado
  em cada cota pelo `S2`, e a faixa tributária do topo valendo meio pé-direito;
- **desaprumo** (NBR 6118 11.3.3.4.1), `θ1 = 1/(100√H)` limitado a
  `[1/300, 1/200]`, `θa = θ1·√((1+1/n)/2)`, e a regra a/b/c dos 30 % comparada
  pelos momentos na base — com `θa` **sem** `θ1mín`, como a norma manda;
- **γz** (15.5.3) por análise de pórtico plano de 1ª ordem com a rigidez de
  15.7.3 (0,8 EcIc pilares, 0,4 EcIc vigas, `Ec = 1,10 Ecs` por 15.5.1);
- **deslocamento lateral em serviço** (Tabela 13.3): `H/1700` no topo e
  `Hi/850` entre pavimentos, combinação frequente `ψ1 = 0,30`, com `Ecs` e
  seção **bruta** por 14.6.4.1 — a rigidez reduzida de 15.7.3 é exclusiva do
  ELU e usá-la aqui dobraria o deslocamento sem amparo normativo.

### `ca` é entrada, não resultado

O coeficiente de arrasto da NBR 6123 para edificação paralelepipédica está na
norma **apenas como ábaco** (Figuras 4 e 5 — confirmado no acervo; não existe
tabela de números). Digitalizar curva de imagem foi o que produziu as seis
células erradas nas tabelas de Bares, e é o mesmo motivo pelo qual o shed
multi-vão segue bloqueado. Então o projetista lê `Ca` da Figura 4 com `h/l1` e
`l1/l2` e o declara; o spec marca a proveniência como `A CONFIRMAR`. Sem `Ca`
declarado o módulo levanta `ValueError` — não arbitra.

### Hipótese de distribuição

O vento total de uma direção é dividido **igualmente** entre os pórticos planos
paralelos a ela. Vale para diafragma rígido e pórticos iguais, que é o caso da
malha ortogonal regular. Malha irregular ou núcleo rígido exige distribuição
por rigidez, e isso não é feito aqui.

O pórtico global usa **a menor** das seções adotadas no lance da base — escolha
conservadora, já que o modelo de pórtico plano tem uma seção única e menor
rigidez significa maior γz e maior deslocamento.

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
