# Batch-Defaults Mode — one reviewable sheet instead of N buttons

Asking every secondary decision as its own gate button is impractical; silently
adopting reference defaults hides decisions from the engineer. **Batch-defaults
mode** does neither: it collects EVERY secondary decision into a single editable
sheet, pre-filled with the reference default + a justification + an
`A CONFIRMAR` flag, and hands it to the engineer for ONE review pass. The
engineer overrides any line; unedited lines keep the default. Maximum decisions
stay with the engineer, minimum friction.

## Rule: critical stays a gate, secondary goes to the sheet

- **CRITICAL → individual gate question** (Ask, Do Not Invent; never defaulted):
  use/occupancy, main dimensions (span, length, eave height), structural type,
  roof form (nº águas, inclinação, tipo de telha), base pinned/fixed, wind V0 +
  category + S3 + dominant opening, crane yes/no. These change the whole design.
- **SECONDARY → batch sheet** (defaulted, but shown and editable): everything
  below. Each has a defensible reference default; the engineer confirms or edits.

## Protocol

1. After the critical gates, the skill WRITES a project copy of the sheet to
   `projects/<slug>/notes/planilha-defaults.md` (from the catalog below, with the
   project's critical answers already substituted where they propagate).
2. The skill presents the sheet to the engineer in ONE message: "revise; edite as
   linhas que quiser, o resto adota o default (justificado)."
3. The engineer edits inline (or replies with overrides). The skill records the
   final values back into the sheet AND into `notes/assumptions.md`, marking any
   still-unconfirmed `A CONFIRMAR` item.
4. The skill maps the sheet to the module params (`rodar_galpao` params dict +
   `build_galpao.configurar`) and runs. Nothing secondary is adopted without
   having appeared on the sheet.

The engineer may also say "adota todos os defaults" — then the sheet is recorded
as-is (every line still visible/auditable), the fastest path, still explicit.

## The defaults catalog (reference = the validated 20×10 galpão)

Values below are the `PARAMS_REF`/`build_galpao` defaults. `[C]` = also drives a
pass/fail, review first. `[!]` = `A CONFIRMAR` against catalog/norm chart.

### Espaçamentos e contagem
| Parâmetro | Default | Justificativa |
|---|---|---|
| BAY (espaçamento entre pórticos) `[C]` | 5.0 m | econômico p/ vão ~10–20 m; ≤6 m evita terça pesada |
| Terças por água (n_por_agua) `[C]` | 3 | vão de terça ~1.7 m p/ telha trapezoidal |
| Linhas de tirante de parede (longarina) `[C]` | 2 | UPE100 no BAY 5 m só passa com 2 (0.99); 1 reprova (1.13) |
| Montantes de oitão | 2 | oitão de 10 m em 3 panos |
| Passo da mão-francesa | derivado | NÃO é escolha — vem de `mao_francesa` (inversão 5.5.1.2) |

### Cargas características
| Parâmetro | Default | Justificativa |
|---|---|---|
| G telha+terça (cobertura) | 0.27 kN/m² | telha trapezoidal simples + terças |
| Peso próprio viga (rafter_self) | 0.35 kN/m | HEA180 |
| Q sobrecarga cobertura | 0.25 kN/m² | NBR 8800 mínimo de manutenção |
| Peso tapamento parede (g_tapamento) | 0.10 kN/m² | telha simples de fechamento |
| Peso tapamento porta (verga) | 0.15 kN/m² | folha + acessórios |
| Nsd tirante de cobertura `[!]` | 8.0 kN | componente do peso na água — confirmar |

### Vento
| Parâmetro | Default | Justificativa |
|---|---|---|
| Classe (dimensão) | B | maior dimensão 20–50 m |
| S1 (topografia) | 1.00 | terreno plano |
| Ca (arrasto, vento long.) `[!]` | 1.2 | Figura 4 baixa turbulência — LER do gráfico |
| Terça/longarina contínua? | não (biapoiada) | conservador; 1/8 em vez de 1/10 |

### Perfis placeholder iniciais (o `redimensionamento` ajusta)
| Peça | Default | Justificativa |
|---|---|---|
| Coluna | HEA200 | passa engastada (0.67) |
| Viga | HEA180 | passa c/ mão-francesa (0.93) |
| Escora/cumeeira/oitão | HEA160 | leve; escora 0.07, oitão 0.43 |
| Longarina de parede | UPE100 `[!]` | props/J/Cw do catálogo — confirmar |
| Terça de cobertura | Ue 200×75×25×2.65 | iteração `tercas_iteracao` (0.95) |

### Barras tracionadas
| Parâmetro | Default | Justificativa |
|---|---|---|
| Contraventamento | barra d20, MR250 | u=0.66 c/ Fa=59 kN |
| Tirantes / mão-francesa | barra d16, MR250 | tração leve |
| Pré-tensionada (esticador)? | sim | dispensa limite de esbeltez L/r≤300 |

### Base e ligações
| Parâmetro | Default | Justificativa |
|---|---|---|
| fck concreto | 25 MPa | usual |
| Placa de base | 450×550×40 mm | engastada, M≈60 kN·m |
| Chumbadores | 4 × d20 A307 | 2 tracionados, straddle em Y |
| Parafusos do joelho | 4 × d24, fub 825 MPa | ligação de momento |
| Clip de terça | 2 × M12 (exceção 45 kN) | ligação secundária |

### Coeficientes / limites
| Parâmetro | Default | Justificativa |
|---|---|---|
| γg,fav (pórtico) | 1.00 | NBR 8800 Tab.1 nota (a) |
| γg,fav (terça) | 0.90 | escolha conservadora do RT p/ sucção |
| Flecha ELS cobertura | H/300…H/150 | escada por combinação |

## Notes

- `[C]` lines drive a pass/fail — review these first even in a fast pass.
- `[!]` lines stay `A CONFIRMAR` until the engineer confirms against the supplier
  catalog or the NBR 6123 Figura 4 chart; the memorial keeps the flag.
- The sheet is append-only per project: overrides are recorded, not overwritten,
  so the decision trail is auditable for the ART.
- See `references/calc-modules.md` for how each parameter maps to a module input,
  and `references/gates.md` for the critical-gate sequence that precedes the sheet.
