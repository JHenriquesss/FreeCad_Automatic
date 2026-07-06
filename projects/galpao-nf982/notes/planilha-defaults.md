# Planilha de decisões secundárias (batch-defaults) - galpao-nf982

Revise num passe. `[C]` = influencia pass/fail. `[!]` = A CONFIRMAR (catálogo/fabricante/norma).

Projeto: galpao-nf982 (depósito 20×10×6, base engastada, ponte leve 100 kN)
Data: 2026-07-05

## Espaçamentos e contagem
| Parâmetro | Default | Justificativa |
|---|---|---|
| BAY entre pórticos `[C]` | 5,0 m | do Gate 2 |
| Terças por água `[C]` | 3 | vão de terça ~1,7 m |
| Tirantes de parede (longarina) `[C]` | 2 | UPE100 só passa com 2 |
| Montantes de oitão | 2 | oitão 10 m em 3 panos |

## Cargas características
| Parâmetro | Default | Justificativa |
|---|---|---|
| G telha+terça | 0,27 kN/m² | telha trapezoidal simples (Gate 1) |
| Peso próprio viga | 0,35 kN/m | HEA180 |
| Q sobrecarga | 0,25 kN/m² | NBR 8800 mínimo |
| Tapamento parede | 0,10 kN/m² | telha simples |
| Nsd tirante cobertura `[!]` | 8,0 kN | componente do peso na água |

## Vento (do Gate 5)
| Parâmetro | Default | Justificativa |
|---|---|---|
| V0 `[!]` | 35 m/s | isopleta litoral norte fluminense — CONFIRMAR pela coordenada |
| Categoria | II | terreno aberto/plano (Gate 5) |
| Classe | B | maior dimensão 20 m |
| S3 | 0,95 | depósito (grupo 2) |
| Ca arrasto (long.) `[!]` | 1,2 | Figura 4 — ler do gráfico |

## Perfis placeholder (redimensionamento ajusta)
| Peça | Default | |
|---|---|---|
| Coluna | HEA200 | |
| Viga | HEA180 | |
| Escora/cumeeira/oitão | HEA160 | |
| Longarina | UPE100 `[!]` | props/J/Cw catálogo |
| Terça | Ue 200×75×25×2,65 | |
| Viga de rolamento (ponte) `[!]` | VS500 (soldado) | props do catálogo — CONFIRMAR |

## Ponte rolante `[!]` (DADOS DO FABRICANTE — A CONFIRMAR)
| Parâmetro | Default (exemplo 100 kN) | |
|---|---|---|
| Capacidade Q | 100 kN (~10 tf) | |
| Peso da ponte | 60 kN | |
| Peso do trole | 15 kN | |
| Aproximação mínima | 1,0 m | |
| Nº rodas/lado | 2 | |
| Coef. de impacto φ | 1,10 | NBR 8400/fabricante |
| Fração surto lateral | 0,10 | |
| Fração frenagem | 0,10 | |
| Altura do trilho (Hvr) | 4,5 m | |

## Base e ligações / coeficientes
Iguais à referência validada (placa 450×550×40 + 4×d20; γg,fav pórtico 1,00 / terça 0,90; flecha H/300…H/150). Ver PARAMS_REF.

---
Overrides (edite aqui o que mudar):
-
