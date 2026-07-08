# Revisão — Dimensionamento ao fogo (NBR 14323:2013)

Conferência do sênior. Verifica elementos de aço em situação de incêndio:
curva ISO 834, fatores de redução ky/kE, massividade (u/A), combinação
excepcional e proteção passiva.

Código: `fogo_nbr14323.py`. Criado 2026-07-08.

> **STATUS: ✅ HOMOLOGADO (2026-07-08)** — sênior aprovou. Única observação:
> diferença de 0,001 no kE (0,059 vs 0,058 por interpolação exata) devido ao
> passo incremental do método — irrelevante para a segurança.

---

## 1. Método

1. **Curva ISO 834:** `θ_g = 20 + 345·log₁₀(8t + 1)` com t em minutos
2. **Fator de massividade u/A:** perímetro exposto / área da seção (NBR 14323 Tab.6.3)
3. **Temperatura no aço sem proteção:** método incremental simplificado (NBR 14323 Anexo A)
4. **Fatores de redução k_y(θ) e k_E(θ):** da NBR 14323 Tab.6.2 / Fakury (interpolação linear entre pontos tabelados)
5. **Combinação excepcional:** `F_d = γ_g·G_k + ψ₂·Q_k` (NBR 8681), γ_g=1,1, ψ₂=0,2/0,4/0,6
6. **Proteção passiva:** espessura de intumescente ou spray por carta de cobertura (Tab.6.13 / 6.7 Fakury)

## 2. Selftest

HEA200, fy=250 MPa, Gk=100 kN, Qk=30 kN, TRRF=60min:
- `θ_aço = 942°C`, `ky = 0,052`, `kE = 0,059`
- `u/A = 222,9 /m`
- Proteção intumescente reduz temperatura significativamente

**PASSED.**

## 3. FLAGS

1. **TRRF** — deve ser definido conforme NBR 14432 e exigência do corpo de bombeiros local (input da skill)
2. **Verificação completa** — requer análise de cada elemento (coluna, viga, ligação) com os esforços da combinação excepcional reduzidos por ky e kE. O módulo fornece a temperatura e os fatores de redução.
3. **Proteção passiva** — as cartas de cobertura são de fabricantes específicos (Nullifire, Blaze Shield, etc.); o módulo usa valores típicos da literatura (Fakury / CBCA). Confirmar com o fornecedor.
4. **Efeitos de dilatação térmica** — não considerados (fora do escopo simplificado; análise avançada requer modelo termo-mecânico).
