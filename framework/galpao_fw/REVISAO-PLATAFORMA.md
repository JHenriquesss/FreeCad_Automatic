# Revisão — Plataformas e passarelas industriais

Dimensionamento de plataformas e passarelas de aço para galpões industriais.
Inclui vigas secundárias (perfil I ou U), verificação ELU/ELS, flecha L/350,
frequência natural > 3 Hz e guarda-corpo (NR-18).

Código: `plataforma.py`. Criado 2026-07-08.

> **STATUS: ✅ HOMOLOGADO (2026-07-08)** — documentação de frequência e
> guarda-corpo corrigidas conforme parecer.

---

## 1. Método

1. **Cargas:** permanente (peso próprio + piso) + acidental (3 a 5 kN/m²
   conforme uso, NBR 6120) + carga concentrada de 2 kN (verificação local).
2. **Viga secundária:** dimensionamento de perfis HEA/IPE, verificação via
   NBR 8800 (flexão + cortante + interação), admitindo contenção lateral
   contínua pelo piso ($L_b \approx 0$).
3. **ELS — Flecha:** combinação frequente (Anexo C NBR 8800):
   $$G + 0,6Q \le \frac{L}{350}$$
4. **Vibração:** frequência natural $f \ge 3\text{ Hz}$ (Bellei) para viga
   biapoiada com massa uniformemente distribuída:
   $$f = \frac{\pi}{2} \sqrt{\frac{E \cdot I \cdot g}{W \cdot L^3}}$$
   Onde $E$ em kN/m², $I$ em m⁴, $g = 9,80665\text{ m/s}^2$, $W = G + 0,2Q$
   (carga total da massa vibrante em kN), $L$ em m.
   Implementação equivalente no código:
   `f = √(980,665·E·I / (W·L³)) / (2π)` (980,665 = g em cm/s²).
5. **Guarda-corpo:** NR-18 — altura 1,20 m, carga horizontal 0,9 kN/m no
   corrimão, rodapé 0,20 m. Momento fletor na base do montante:
   $$M_{montante} = (q \cdot e) \cdot h$$
   Onde $q = 0,9\text{ kN/m}$, $e$ = espaçamento entre montantes (m),
   $h = 1,20\text{ m}$.

## 2. Selftest

Vão 6 m, carga total 5 kN/m² (2+3), b_trib = 1,5 m:
- Perfil: HEA200, interação 0,346
- Flecha: 13,0 mm ≤ L/350 = 17,1 mm ✅ (G + 0,6·Q = 5,7 kN/m)
- Frequência: 6,02 Hz ≥ 3 Hz ✅ (massa vibrante: G + 0,2·Q = 3,9 kN/m)

**PASSED.**

## 3. FLAGS

1. **Carga de utilização** — depende do uso (operação, manutenção, inspeção).
   Default 3 kN/m². Confirmar com o cliente/NBR 6120.
2. **Contenção lateral** — assumida contínua (piso fixado na mesa superior).
   Se piso solto (grelha sem fixação), a viga deve ser verificada sem
   contenção → perfil maior.
3. **Piso de grelha (grating)** — dimensionamento por catálogo do fabricante
   (carga admissível × vão). O módulo não calcula a grelha.
4. **Vibração** — o critério de frequência > 3 Hz é conservador para
   passarelas de pedestres. Para plataformas sem circulação humana
   constante, pode ser relaxado.
5. **Guarda-corpo** — o dimensionamento dos montantes e do corrimão
   (flexão + flambagem) é projeto executivo. O módulo fornece os esforços.
