# Revisão — Calhas e condutores (Bellei §2.4 / NBR 10844)

Dimensionamento hidráulico de calhas de beiral e condutores verticais para
galpões industriais. Inclui área de contribuição, vazão pelo método racional,
seção por Manning-Strickler, diâmetro de condutores e carga de água no pórtico.

Código: `calhas.py`. Criado 2026-07-08.

> **STATUS: 🆕 PENDENTE SÊNIOR** — módulo novo.

---

## 1. Método

1. **Área de contribuição:** `A = L_calha · (L_água + h_elev/2)` (NBR 10844)
2. **Vazão de projeto:** `Q = I · A / 60` (I em mm/h, A em m², Q em L/min)
3. **Seção da calha:** Manning-Strickler `Q = 60000 · As · Rh^(2/3) · i^(1/2) / n`
4. **Regra prática Bellei:** 1 cm² de seção para cada 1 m² de telhado
5. **Condutores:** diâmetro por faixa de vazão (mín. 75 mm)
6. **Carga de água:** peso da lâmina d'água considerada no pórtico

## 2. Selftest

Galpão 20×10 m, 2 águas, calha no beiral:
- `A_contrib = 52,5 m²`, `Q = 131 L/min` (I=150 mm/h)
- Calha 200×80 mm → lâmina 24 mm (borda livre 70%) ✅
- Bellei: As_total 160 cm² ≥ 52,5 cm² ✅
- Condutores: 2× d75 mm

**PASSED.**

## 3. FLAGS

1. **Intensidade pluviométrica I (mm/h)** — depende da região e TR adotado.
   Default 150 mm/h (Sudeste, TR=5 anos). Confirmar com dados locais.
2. **Forma da calha** — retangular ou trapezoidal. Geometria definida pelo
   projeto de detalhamento (chaparia).
3. **Condutores** — diâmetro mínimo 75 mm; recomenda-se distribuir a cada
   10–15 m de fachada. O dimensionamento exato segue ábacos da NBR 10844.
4. **Calhas centrais (águas-furtadas)** — em galpões multi-vão, a calha
   central recebe água de duas águas simultâneas. Dimensionar com o dobro
   da área de contribuição.
5. **Calhas autoportantes** — para grandes vãos, usar chapa ≥ 5 mm e
   verificar estruturalmente como viga contínua entre pórticos.
