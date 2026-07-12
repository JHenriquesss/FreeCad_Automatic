# Revisão — Cortante da alma com mesas inclinadas (barra tapered)

Conferência do sênior. Fecha a **dívida (a)** do backlog do parecer 6.b: numa barra de
seção variável, as **mesas inclinadas** carregam parte da força cortante via a
componente transversal da força de mesa; a **alma** vê um cortante efetivo menor
(haunch/joelho) ou maior (geometria adversa). Fase 6.10. Criado 2026-07-12.

> **STATUS: 🟡 PENDENTE SÊNIOR** (2026-07-12). Aguarda parecer.
> **Ponto de honestidade ao revisor:** isto **NÃO é cláusula da NBR 8800** — é
> **equilíbrio (mecânica)**. O **Anexo J** (barras de seção variável) tem apenas
> **J.1** (aplicabilidade), **J.2** (tração), **J.3** (compressão) e **J.4**
> (momento/FLT); **não trata cortante**. Por **J.1.2**, o que não está excetuado
> segue a Seção 5 → o cortante segue **§5.4.3 por seção** (o verificador já faz).
> Este módulo é um **refino por equilíbrio**, não uma citação normativa, e **não
> inventa coeficiente** (a componente é geométrica exata).

## Prova de que o Anexo J não trata cortante (PDF verbatim)

`nbr8800_2008_1.pdf` — sumário do Anexo J e corpo:

| Cláusula | Título |
|---|---|
| **J.1** | Aplicabilidade (I/H/caixão duplo-simétrico; mesas de seção constante; **altura da alma varia linearmente**) |
| **J.1.2** | *"…devem ser efetuados conforme a Seção 5, **exceto nos casos a seguir**…"* |
| **J.2** | Força axial de **tração** (área da seção de menor altura) |
| **J.3** | Força axial de **compressão** (seção de menor altura; flambagem racional) |
| **J.4** | Momento fletor resistente (**FLT**: λ da seção de maior altura J.4.2; Cb racional J.4.1) |

Cortante **não** está entre as exceções (J.2–J.4) → cai na regra geral (§5.4.3). O
alívio das mesas é, portanto, **adicional** e **não-normativo**.

## Base (equilíbrio, I duplo-simétrico)

Braço do binário ≈ `h_m` (altura da seção). Força de mesa `F = M/h_m`. Cada mesa
inclina `(dh/dx)/2` em relação ao eixo; as **duas** mesas somam uma componente
transversal `F·(dh/dx) = (M/h_m)·(dh/dx)`. Logo:

```
V_alma = V − (M/h_m)·(dh/dx)          (sinal pela geometria)
```

`dh/dx = (h2 − h1)/L_seg`. **Sinal** derivado da geometria (mne-4): `sentido=+1`
(alívio) quando a seção de **maior |M|** coincide com a de **maior altura**
(profundidade e momento co-crescem — caso joelho); `−1` (acréscimo) caso contrário.

## Política de segurança (calc assinado; NBR silente)

| Componente | Tratamento |
|---|---|
| **Adversa** (mesa **aumenta** o cortante da alma) | **SEMPRE contada** — `V_usar = max(\|V\|, \|V_ef\|)` (mne-3) |
| **Favorável** (alívio) | **OPT-IN** do engenheiro: creditada só com `creditar_cortante_mesa_inclinada=True`. Default **False** → usa `V` cheio (conservador) (mne-2) |

Assim o memorial que o sênior assina **nunca** ganha economia não-normativa sem
decisão explícita, mas **nunca** perde uma parcela adversa. A **reserva** disponível é
sempre reportada (`cortante_mesa_alivio_kN`), para o engenheiro decidir com
transparência.

## Módulo `cortante_tapered.py`

`dh_dx(h1,h2,L)` · `v_alma_efetivo(M,V,h_m,dhdx,sentido)` · `sentido_haunch(segs)`
(deriva o sinal da geometria) · `cortante_efetivo_conservador(...,creditar)` →
`{V_usar, V_efetivo, alivio, acrescimo, creditado}` · `_selftest`. Puro (sem numpy).

## Integração (`rodar_galpao`)

Nos segmentos tapered do **rafter** e da **coluna**: `dh/dx` do membro
(`(h_joelho−h_cumeeira)/L_raft` ; `(h_joelho−h_col_base)/H_col`), `sentido` da
geometria, e o `Vsd` de `chk.verifica` passa a `cme["V_usar"]`. Flag de spec
`estrutura.creditar_cortante_mesa_inclinada` (mapper → `params`). `res["alma_variavel"]`
reporta `cortante_mesa_alivio_kN`, `cortante_mesa_creditado`, `cortante_mesa_sentido`.
Só no ramo alma variável → **ref prismática 20×10 intocada** (dh/dx=0 → V_ef=V).

## Não-regressão

- Prismático: `dh/dx=0` → `V_alma_efetivo = V` exato (mne-5). Ref 20×10 não entra no
  bloco tapered.
- Default `creditar=False`: utilização **idêntica** ao check de V cheio (só reporta a
  reserva). Crédito nunca **piora** a utilização (`test_credito_nao_piora_utilizacao`).
- Suítes 6.4/6.6/6.9/6.b + build tapered: verdes.

## Checklist de testes (`tests/test_fase610_cortante_tapered.py`)

| Teste | Cobre |
|---|---|
| `test_dhdx_tapered_e_prismatico` | `dh/dx=(h2−h1)/L`; prismático → 0 |
| `test_haunch_alivio` | haunch → `V_alma < V` |
| `test_prismatico_sem_efeito` | `dh/dx=0` → `V_ef=V` (mne-5) |
| `test_M_zero_sem_efeito` | M=0 → `V_ef=V` |
| `test_adverso_acrescimo` | adverso → `V_alma > V` (mne-3) |
| `test_conservador_favoravel_nao_credita` | default não credita; reporta reserva (mne-2) |
| `test_conservador_favoravel_credita` | opt-in credita o alívio |
| `test_conservador_adverso_sempre_conta` | adverso entra sem opt-in (mne-3) |
| `test_conservador_prismatico_creditar_nada_muda` | prismático + opt-in → nada muda (mne-5) |
| `test_selftest_roda` | selftest |
| `test_integra_reporta_reserva` | rodar reporta `cortante_mesa_alivio_kN` (me-3) |
| `test_credito_nao_piora_utilizacao` | crédito não aumenta a interação da coluna |

12 testes verdes.

## Notas / backlog

- Braço do binário tomado `= h_m` (aproximação usual; o braço exato `h_m − tf` daria
  alívio marginalmente **maior** → adotar `h_m` é conservador no crédito).
- Interação do cortante efetivo com a verificação por tensões §5.5.2.3 (fase 6.9): o
  `τ` da junção usa o `V` de entrada; se o engenheiro creditar o alívio, o `V` já
  chega reduzido — coerente.
