# Planilha de decisões secundárias (batch-defaults)

> Modo batch-defaults (ver `skills/build-warehouse/references/batch-defaults.md`).
> Revise em UM passe. Edite a coluna **Adotado** nas linhas que quiser; o resto
> mantém o Default (justificado). `[C]` = influencia pass/fail, veja primeiro.
> `[!]` = A CONFIRMAR contra catálogo/norma. Ao final, o que ficar `[!]` sem
> confirmação vai flagado no memorial.

Projeto: __________  |  Data: __________  |  Eng.: __________

## Espaçamentos e contagem
| Parâmetro | Default | Adotado | Justificativa |
|---|---|---|---|
| BAY entre pórticos `[C]` | 5.0 m | | econômico; ≤6 m evita terça pesada |
| Terças por água `[C]` | 3 | | vão de terça ~1.7 m |
| Tirantes de parede (longarina) `[C]` | 2 | | UPE100 só passa com 2 no BAY 5 m |
| Montantes de oitão | 2 | | oitão 10 m em 3 panos |

## Cargas características
| Parâmetro | Default | Adotado | Justificativa |
|---|---|---|---|
| G telha+terça | 0.27 kN/m² | | telha trapezoidal + terças |
| Peso próprio viga | 0.35 kN/m | | HEA180 |
| Q sobrecarga | 0.25 kN/m² | | NBR 8800 mínimo |
| Tapamento parede | 0.10 kN/m² | | telha simples |
| Tapamento porta (verga) | 0.15 kN/m² | | folha + acessórios |
| Nsd tirante cobertura `[!]` | 8.0 kN | | componente do peso na água |

## Vento
| Parâmetro | Default | Adotado | Justificativa |
|---|---|---|---|
| Classe | B | | dimensão 20–50 m |
| S1 topografia | 1.00 | | terreno plano |
| Ca arrasto `[!]` | 1.2 | | Figura 4 — ler do gráfico |
| Terça/longarina contínua? | não | | conservador (1/8) |

## Perfis placeholder (redimensionamento ajusta)
| Peça | Default | Adotado | Justificativa |
|---|---|---|---|
| Coluna | HEA200 | | engastada 0.67 |
| Viga | HEA180 | | c/ mão-francesa 0.93 |
| Escora/cumeeira/oitão | HEA160 | | escora 0.07, oitão 0.43 |
| Longarina | UPE100 `[!]` | | props/J/Cw catálogo |
| Terça | Ue 200×75×25×2.65 | | iteração 0.95 |

## Barras tracionadas
| Parâmetro | Default | Adotado | Justificativa |
|---|---|---|---|
| Contraventamento | d20 MR250 | | u=0.66 |
| Tirantes / mão-francesa | d16 MR250 | | tração leve |
| Pré-tensionada (esticador)? | sim | | dispensa L/r≤300 |

## Base e ligações
| Parâmetro | Default | Adotado | Justificativa |
|---|---|---|---|
| fck | 25 MPa | | usual |
| Placa de base | 450×550×40 | | M≈60 kN·m |
| Chumbadores | 4×d20 A307 | | 2 tracionados |
| Parafusos joelho | 4×d24 fub 825 | | ligação de momento |
| Clip de terça | 2×M12 (exceção) | | secundária |

## Coeficientes / limites
| Parâmetro | Default | Adotado | Justificativa |
|---|---|---|---|
| γg,fav pórtico | 1.00 | | NBR 8800 Tab.1 (a) |
| γg,fav terça | 0.90 | | conservador p/ sucção |
| Flecha ELS | H/300…H/150 | | escada por combinação |

---
Overrides (registre aqui as decisões que mudou, com o porquê — trilha p/ ART):
-
