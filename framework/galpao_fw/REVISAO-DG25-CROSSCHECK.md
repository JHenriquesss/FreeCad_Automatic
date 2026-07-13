# Revisão — Cross-check DG25 da FLT de mísula (VALIDAÇÃO, não dimensionamento)

Conferência do sênior. Fecha a **dívida (b)** do backlog do parecer 6.b como
**conferência independente**: calcula o momento de FLT **elástico** `M_eLTB` de um
trecho de barra afunilada pelo **AISC Design Guide 25 §5.4.3** e compara com o `Mcr`
do **NBR 8800 Anexo J**. Fase 6.12. Criado 2026-07-12.

> **STATUS: 🟡 PENDENTE SÊNIOR** (2026-07-12). **É VALIDAÇÃO, não dimensionamento.**
> Não altera nenhuma utilização — o dimensionamento continua **100% NBR Anexo J**
> (item 36, homologado). DG25 é **AISC/LRFD, informativo**. Base **verbatim** do
> DG25 (pág 60–61, lida por imagem — a camada de texto do PDF é corrompida).

## O que o cross-check faz

Você (sênior) ofereceu o "fator γ" do DG25 como conferência da FLT tapered. Implementei
o **momento de FLT elástico** do DG25 (`M_eLTB = F_eLTB·Sxc`, o numerador de
`γ_eLTB = F_eLTB/fr`, Eq. 5.4-13) e comparo com o `Mcr` da NBR para o mesmo trecho.

## Base normativa (AISC DG25 §5.4.3, pág 60–61 — verbatim das imagens)

| Item | Fórmula |
|---|---|
| **F_eLTB** (5.4-10 = Spec. F4-5) | `Cb·π²E/(Lb/rt)²·√(1 + 0,078·(J/(Sxc·ho))·(Lb/rt)²)` — props na seção do **MEIO** do trecho |
| **rt** (5.4-11 = F4-10) | `bfc/√(12·(ho/d + (1/6)·aw·h²/(ho·d)))` |
| **ho** | distância entre centroides das mesas `= d − tf` (I duplo-sim) |
| **hc** | `2×`(centroide→face interna da mesa comp.) `= hw` (I duplo-sim) |
| **aw** | `hc·tw/(bfc·tfc)` (para rt, **sem** o limite de 10) |
| **J** (5.4-12) | esbelta (`hc/tw>5,70√(E/Fy)`) ou `Iyc/Iy≤0,23` → `J=0`; senão `h·tw³/3 + 2·[bf·tf³/3·(1−0,63·tf/bf)]` |
| **M_eLTB** | `F_eLTB · Sxc` (Sxc = Wx) |

Coeficientes `0,078 / 5,70 / 0,63 / 1/6` lidos verbatim (mne-2).

## Diferença-chave: seção de referência

| Método | Seção usada para o momento de FLT elástico |
|---|---|
| **AISC DG25** (5.4.3, passo 1) | seção do **MEIO** do comprimento destravado |
| **NBR 8800 Anexo J** (J.4.2) | seção de **MAIOR altura** |

Essa é a origem da divergência — e o achado da conferência.

## Resultados

**Base sã (prismático):** com `h1=h2` (meio ≡ funda), `razão DG25/NBR = 0,998`. As
**fórmulas concordam** a 0,2% (F4-5 ≡ F2). Prova que a máquina está correta.

**Galpão tapered (smoke, h_joelho 0,90 → 0,45 / coluna 0,90 → 0,35):**

| Membro | M_eLTB (DG25, meio) | Mcr (NBR, funda) | razão | veredito |
|---|---|---|---|---|
| Rafter | — | — | **0,544** | DIVERGE |
| Coluna | — | — | **0,447** | DIVERGE |

## Interpretação (SEM falso alarme)

A divergência de ~2× vem **exclusivamente** da seção de referência (meio × funda),
**não** de erro de fórmula (o prismático converge a 0,998). **Não** implica que o
`flt_misula` seja inseguro na utilização, porque a **utilização** do NBR é
**auto-consistente**: demanda (`max M/Wx · Wx_funda`) e resistência são ambas
tomadas na seção funda (J.4.1/J.4.2 como pacote). O cross-check compara **momentos
absolutos**, não a margem de segurança.

**O que a conferência entrega ao sênior:** um número **AISC independente** para
sanity-check. A leitura honesta: o Anexo J (seção funda) é **liberal** frente ao DG25
(seção meio) no **momento elástico** de FLT para tapers fortes. Se o sênior quiser um
dimensionamento mais conservador, o DG25 aponta o caminho — mas isso seria **decisão
de método**, fora do escopo desta fase. Aqui **nada muda**.

## Módulo `dg25_ltb.py`

`hc`, `ho`, `aw`, `rt`, `e_alma_esbelta`, `J_dg`, `f_eltb`, `m_eltb`, `nbr_mcr`,
`cross_check_flt(segs, fy, Lb, Cb, tol=0,20)` → `{M_dg, M_nbr, razao, converge,
sec_meio, sec_funda}`. Puro (sem numpy — importável no build). `_selftest`.

## Integração (`rodar_galpao`) — informativa

Cross-check na FLT do **rafter** e da **coluna** tapered (Lb do regime governante).
Memorial: `[CROSS-CHECK DG25 (informativo, não-normativo)] M_eLTB(meio)=… ;
Mcr(NBR,funda)=… ; razão=… → CONVERGE/DIVERGE`. `res["alma_variavel"]`:
`dg25_razao_raf/col`, `dg25_converge_raf/col`. **Utilização byte-idêntica ao 6.11**
(mne-1) — só acrescenta linhas de relatório.

## Não-regressão

- Nenhuma utilização/`interacao_max_*` muda (cross-check só reporta).
- Ref prismática 20×10 não entra (só ramo tapered).
- Suítes tapered + build verdes.

## Checklist de testes (`tests/test_fase612_dg25_crosscheck.py`)

| Teste | Cobre |
|---|---|
| `test_rt_formula` | `rt` = 5.4-11 verbatim |
| `test_J_dg_compacta_positiva` | J>0 (alma compacta) |
| `test_J_dg_slender_zero` | alma esbelta → J=0 (mne-2) |
| `test_m_eltb_positivo_e_decresce_com_Lb` | M_eLTB↑ com Lb↓ |
| `test_prismatico_converge` | meio≡funda → razão≈1, CONVERGE (mne-5) |
| `test_razao_independe_de_cb` | Cb cancela na razão |
| `test_taper_forte_sinaliza_sem_excecao` | taper forte → DIVERGE sem exceção, seções distintas (mne-3) |
| `test_selftest_roda` | selftest (prismático 0,998) |
| `test_integra_reporta_razao_sem_mudar_util` | rodar reporta razão; FLT util intacta (mne-1) |

9 testes verdes.

## Notas / backlog

- `Cb` próprio do DG25 (5.4-1/5.4-2) não implementado: cancela na razão → o
  cross-check é Cb-independente. Fica como refino se o sênior quiser o `Fcr` de
  projeto completo (Rpc/Rpg/Rpt + mapeamento inelástico — o "sabor AISC" do que o
  Anexo G/H já faz).
- Divergência meio×funda: **decisão de método do sênior**, não bug. Documentada, não
  aplicada.
