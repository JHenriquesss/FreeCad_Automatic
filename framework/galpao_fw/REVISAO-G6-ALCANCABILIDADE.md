# G6 — Religar a camada de entrega (alcançabilidade)

**Problema.** A barra verde cobre o cálculo, nunca a alcançabilidade. Vinte e um
módulos com testes passando não eram importados por nenhuma porta de entrada do
framework — orçamento, cronograma, caderno de encargos e pacote legal
**não existiam** do ponto de vista de quem roda o Loop.

**Ferramenta.** Fecho transitivo dos `import` a partir das entradas
(`project_loop`, `project_loop_cli`, `builtin_adapters`, `galpao_turnkey`,
`rodar_projeto`, `rodar_galpao`, `galpao_adapter`, `casa_residencial`,
`edificio_adapter`, `residencial_eletrica`, `wizard`, `framework`). Virou teste
executável: `tests/test_alcancabilidade.py`. Zero ilha fora do que está
declarado lá — e a declaração é conferida, não só listada.

---

## 1. Mecanismo novo no Loop

`register_adapter` aceitava só os 5 hooks do núcleo (`report`, `coordination`,
`ifc`, `model_3d`, `drawings`). Agora um adaptador pode declarar **entregáveis
adicionais**: um hook fora do núcleo só é aceito se **o mesmo nome estiver em
`deliverables`** — não existe entregável que o manifesto não anuncie. A ordem
declarada é a ordem de execução (o cronograma custeia com a planilha que o
orçamento acabou de gravar). Uma exceção num hook vira `failed` com o detalhe,
sem derrubar os demais.

Implementação: `project_loop.CORE_HOOKS` / `CORE_DELIVERABLES` /
`_run_extra_deliverable_hooks`; os hooks em `entregaveis_projeto.py`.

## 2. Decisão módulo a módulo

| Módulo | Decisão | Onde chega ao usuário |
|---|---|---|
| `orcamento` | entregável `orcamento` | `orcamento/planilha.json`, `curva-abc.json`, `relatorio.txt` |
| `cronograma` | entregável `cronograma` | `cronograma/cpm.json`, `curva-s.json`, `curva-s.svg`, `relatorio.txt` |
| `caderno_encargos` | entregável `caderno_encargos` | `documentos/caderno-encargos.md` + `.json` |
| `pacote_legal` | entregável `pacote_legal` | `documentos/pacote-legal.md` + `.json` |
| `terraplenagem` | entregável `obras_sitio` | `sitio/obras-sitio.json` (só com `site.terraplenagem`) |
| `esgoto_reuso` | entregável `obras_sitio` | idem (só com `site.saneamento`) |
| `fotovoltaico` | entregável `fotovoltaico` | `fotovoltaico/fotovoltaico.json` + `geracao.svg` |
| `comissionamento_fv` | dentro de `fotovoltaico` | evidência de campo → validação; sem ela, o **checklist** NBR 16274 |
| `desenho_concreto` | entregável `desenhos_concreto` (galpão) + `drawings` do edifício | `drawings-svg/concreto-armacao.svg`, `concreto-formas.svg`; `drawings/planta-laje-pavimento-tipo.svg` |
| `executivo_concreto` | via `desenho_concreto` | quadro de aço / memorial dentro da prancha |
| `desenho_piso` | dentro de `desenhos_concreto` | `drawings-svg/piso-juntas.svg` (quando há piso) |
| `props_I_mono` | **deduplicado** | `alma_variavel.props_I` delega a ele (implementação única de propriedades de perfil I) |
| `forcas_localizadas` | **wire de engenharia** | NBR 8800 5.7 na viga de rolamento (ver §4) |
| `build_concreto` / `build_eletrico` / `build_federado` | falso-positivo | enviados ao FreeCAD como **texto-fonte**; a ponte por string é conferida pelo teste |
| `build_final` / `demo_engenheiro` / `tools_probe_pe13` / `validacao` / `verificar_amostra` | scripts avulsos | marcados `SCRIPT AVULSO` no cabeçalho, conferido pelo teste |

Nada foi apagado: todo módulo tinha consumidor legítimo depois de olhado.

## 3. O que os entregáveis **não** fazem

- **Não inventam dado de sítio.** Sem `site.terraplenagem` / `site.saneamento` /
  `site.fotovoltaico`, o entregável sai `not_requested` com o motivo — cota de
  terreno, IDF, taxa de infiltração e HSP são dado local, não default.
- **Não passam preço de referência por cotação.** A planilha sai com
  `a_confirmar` apontando a SINAPI vigente enquanto o usuário não declarar
  `gestao.orcamento.precos`; o BDI padrão idem.
- **Não atestam comissionamento.** Sem evidência de campo sai o *checklist* a
  preencher, nunca um "APROVADO".
- **Não escondem curva S parcial.** A curva S pesa o avanço físico pelo custo;
  se só parte das atividades tem custo, ela satura antes do fim da obra. O
  manifesto declara `atividades_custeadas`/`atividades_totais` e o aviso — em vez
  de inventar custo para as atividades que o orçamento não cobre.

## 4. Achados de engenharia que a religação expôs

**(a) NBR 8800 5.7 ausente na viga de rolamento.** `forcas_localizadas` (flexão
local da mesa, escoamento e enrugamento local da alma, flambagem lateral da alma,
enrijecedor de apoio) nunca era chamado. A viga de rolamento era verificada só à
flexão biaxial, flecha e fadiga — **faltava o modo de ruína mais clássico dessa
viga**: esmagamento/enrugamento da alma sob a roda e sob a reação no console.

Wire em `ponte_rolante.verifica_forcas_localizadas`, dobrado em `viga["OK"]` (e
portanto no quadro-resumo, linha "Viga rolamento"). Sem os dados do trilho e da
solda mesa-alma adota-se o **piso conservador `ln = 0`, `k = tf`** (o filete só
acrescenta): passar nele é passar de verdade; reprovar nele só significa que o
trilho precisa ser informado — nenhum número é inventado.

Na amostra (VS500, ponte de 100 kN, bay 5 m): a roda passa (F_sd 73,1 ≤ F_Rd
160,0 kN); a **reação no console não passa** no piso conservador (132,9 > 80,0 kN)
e o §5.7.8 exige enrijecedor de apoio — que passa a ser **dimensionado**
(§5.7.9: 2 chapas 84 × 8 mm, N_Rd 479 kN) em vez de só reprovar.

**(a2) Laje dimensionada sem prancha.** `desenho_concreto.planta_laje_svg`
(formas + armadura + quadro de ferros) não tinha consumidor. O edifício
multipavimento dimensionava a laje e o resultado só existia como número no
relatório. Ligado ao hook `drawings` do `edificio_adapter` — o galpão de pórtico
não tem laje, então a prancha sai onde há laje.

**(b) Ruído de ponto flutuante classificado como monossimetria.** Com
`props_I` delegando a `props_I_mono`, `Sxt` e `Sxc` passam a vir de `Ix/ct` e
`Ix/cc`: numa seção duplamente simétrica são o mesmo número a menos de ~1e-16
relativo. O `>=` cru em `dg25_ltb.mn_tfy` classificava esse ruído como
monossimetria e fazia o estado TFY "aplicar" numa seção simétrica (M_n idêntico
ao CFY, mas estado espúrio no envelope). Corrigido com tolerância numérica
declarada (`_TOL_SIMETRIA`).

Equivalência de `props_I` × `props_I_mono` conferida chave a chave em 5 seções
(máx. 2,3e-15 relativo) e `rt` conferido contra a fórmula própria do `dg25_ltb`
(0 a 1,3e-16).

## 5. Contrato de entrada novo (opcional)

```jsonc
{
  "gestao": {
    "orcamento":  { "quantitativos": {"aco_estrutural": 12000},
                    "precos": {"aco_estrutural": ["Aço (cotação)", "kg", 20.0]},
                    "bdi_pct": 18.0 },
    "cronograma": { "atividades": [{"id": "...", "nome": "...", "dur": 10,
                                    "pred": []}] },
    "caderno_encargos": { "disciplinas": ["concreto", "aco"] }
  },
  "site": {
    "terraplenagem": { "grid_terreno": [[...]], "cota_plataforma": 100.0,
                       "area_celula_m2": 400.0, "empolamento": 1.25,
                       "greide_equilibrio": true,
                       "drenagem": {"C": 0.8, "i_mm_h": 120.0, "area_ha": 0.8,
                                    "largura_canaleta_m": 0.6,
                                    "declividade": 0.005} },
    "saneamento":    { "esgoto": {"N": 20, "C": 50.0, "T": 1.0, "K": 65.0,
                                  "Lf": 1.0,
                                  "taxa_infiltracao_L_m2_dia": 40.0},
                       "reuso":  {"precip_mm_mes": [12 valores],
                                  "area_captacao_m2": 800.0,
                                  "demanda_L_mes": 60000.0} },
    "fotovoltaico":  { "HSP": 5.2, "consumo_kwh_mes": 30000.0,
                       "comissionamento": { /* evidência de campo */ } }
  }
}
```

Coeficientes da NBR 7229 (C, T, K, Lf), IDF, taxa de infiltração, empolamento e
HSP são **entrada obrigatória** — o módulo estrutura, não inventa.

## 6. Testes

- `tests/test_alcancabilidade.py` — 5 testes: zero ilhas; entradas existem;
  a ponte por string dos `build_*` continua viva (filtro de nome morto);
  scripts avulsos se declaram e não são importados.
- `tests/branches/project_loop/test_entregaveis_projeto.py` — 18 testes pelo
  lado do **usuário** (`run_project`): status no manifesto, artefato com hash,
  SVG que **abre** como XML (substring não prova render), `not_requested` sem
  dado de sítio, FV sem HSP não finge dimensionar, falha de um entregável não
  derruba os outros, preço do usuário substitui a referência.
