# Revisão — Momento resistente de alma esbelta (NBR 8800 Anexo H)

Conferência do sênior. Fecha o **ponto 4b do parecer 2 da coluna tapered**: o
`ValueError` que abortava quando a alma do joelho é esbelta é substituído pelo
dimensionamento à flexão de **vigas de alma esbelta** (NBR 8800 **Anexo H**),
habilitando mísulas altas de alma fina — o caso econômico real. Fase 6.8. Criado
2026-07-11.

> **STATUS: ✅ HOMOLOGADO** (2026-07-11). Parecer 2: **"APROVADO PARA MERGE"** com
> **mea-culpa** — os "dois erros críticos" do parecer 1 (FLM inelástico, trava do
> Cb) já estavam no código; o revisor baseou-se na tabela sintética do markdown.
> *"A revisão matemática atesta 100% da integridade do Anexo H."* kpg, kc, FLT (com
> trava no platô), FLM (sem Cb), despacho por `h/tw > 5,70√(E/fy)` e back-compat
> Anexo G — todos validados. Base **verbatim** do PDF (págs 147–149 + 136).

## Parecer sênior 1 — respostas

| Pt | Alegação | Veredito |
|---|---|---|
| 1 | Ramo **inelástico da FLM (H.2.3) omitido** | **IMPROCEDENTE (código correto).** `alma_esbelta.py` linha ~117-118 tem o ramo inelástico `kp·(1−0,3(λ−λp)/(λr−λp))·Wx·fy`, **sem Cb** (correto). Só a tabela do markdown abreviava — corrigida. Teste `test_flm_inelastico_presente` adicionado. |
| 2 | **Trava do Cb na FLT (H.2.2) ausente** | **IMPROCEDENTE (código correto).** Linhas ~105-108: ambos os ramos já têm `min(..., platô)`. Teste `test_cb_nao_excede_plato` (Cb=2,5 no inelástico) adicionado — **confirma que a trava engata**. |
| 3 | `h/tw ≤ 260` assume alma sem enrijecedores | **NOTA acatada.** Guard mantido; comentário/TODO adicionado (com enrijecedores no painel o limite depende de a/h). |
| 4 | H.2.1 redundante em duplo-simétrico | **NOTA (sem ação).** Mantido por coerência normativa; governa em monossimétricas (`Wxt ≪ Wxc`). Sênior pediu "deixe como está". |

Pontos 1 e 2 (os "dois erros críticos") **já estavam corretos no código** — o parecer
leu a tabela abreviada do markdown como omissão (mesmo padrão do parecer da zona de
painel). Testes novos travam os comportamentos.

## Contexto (parecer 2, ponto 4b)

O parecer apontou, com razão em seu núcleo, que travar o cálculo com `ValueError`
quando a alma fica esbelta limita a rotina — mísulas otimizadas podem ter alma
esbelta no joelho. **A NBR 8800 tem o Anexo H exatamente para isto** (não é
necessário AISC nem "alma cheia genérica"). O `ValueError` continua como guard
correto **fora** da validade do Anexo H (`Aw/Afc > 10` ou `h/tw > 260`).

## Base normativa (NBR 8800:2008 Anexo H + F.2, verbatim)

| Cláusula | Fórmula |
|---|---|
| **H.1.2** | alma esbelta: `λ = h/tw > 5,70·√(E/fy)` |
| **H.1.3** | validade: `Aw/Afc ≤ 10` ; `h/tw ≤ 260` |
| **H.2.1** | escoamento da mesa tracionada: `M_Rd = Wxt·fy/γa1` |
| **H.2.2** | FLT: `λ=Lb/ryT` ; `λp=1,10√(E/fy)` ; `λr=π√(E/(0,7fy))` ; platô `kpg·Wxc·fy` ; inel. `min(kpg·Cb·(1−0,3(λ−λp)/(λr−λp))·Wxc·fy, platô)` ; elást. `min(kpg·Cb·π²E·Wxc/λ², platô)` — **trava no platô** (Cb não pode superar `kpg·Wxc·fy`) |
| **H.2.3** | FLM: `λ=bf/2tf` ; `λp=0,38√(E/fy)` ; `λr=0,95√(kc·E/(0,7fy))` ; platô `kpg·Wxc·fy` ; **inel.** `kpg·(1−0,3(λ−λp)/(λr−λp))·Wxc·fy` (**sem Cb**) ; elást. `0,90·kpg·E·kc·Wxc/λ²` |
| **kpg** | `1 − ar/(1200+300·ar)·(hc/tw − 5,70√(E/fy)) ≤ 1,0` ; `ar=Aw/Afc≤10` ; `hc=hw` (duplo-sim.) |
| **F.2** | `kc = 4/√(h/tw)` , `0,35 ≤ kc ≤ 0,76` |

`ryT` = raio de giração (eixo fraco) de (mesa comprimida + 1/3 da alma comprimida).
`M_Rd = min(H.2.1, H.2.2, H.2.3)`. Premissa: I duplo-simétrico → `Wxc=Wxt=Wx`,
`hc=hw`.

## 1. Módulo `alma_esbelta.py`

`e_esbelta`, `kc`, `kpg`, `ryt`, `_valida` (H.1.3) e `mrd_alma_esbelta(sec, fy, Lb, Cb)`
→ `{M_Rd, Mn, gov, fora_validade, kpg, kc, ryT, M_esc/M_flt/M_flm, anexo:"H"}`.
`_selftest`.

## 2. Despacho (check_nbr8800.momento_resistente)

No topo de `momento_resistente`: se `h/tw > 5,70√(E/fy)` → chama `alma_esbelta`
(import lazy, sem circular) e retorna `(Mn, gov, det)` com `det["anexo"]="H"` e
`Mn_flt/Mn_flm` compatíveis com `verifica`/`flt_misula`. **Alma compacta/semicompacta
→ Anexo G inalterado** (`det["anexo"]="G"`). Assim tudo a jusante (verificação por
segmento, FLT de mísula, coluna tapered) passa a **calcular** seções de alma esbelta
em vez de abortar.

## 3. Não-regressão

- Ref prismática 20×10 (HEA200/HEA180, alma compacta): `col=0,654 / viga=0,909`
  **inalterada** (não entra no despacho).
- Suítes 6.4 + 6.6 + 6.b: **26/26** verdes.
- `mne-5`: alma esbelta usa `Wxc` (não `Zx/Mpl`); `det["Mpl"]=None` no ramo H.

## Checklist de testes (`tests/test_fase68_alma_esbelta.py`)

| Teste | Cobre |
|---|---|
| `test_web_esbelta_detectada` | fixture `h/tw > 5,70√(E/fy)` |
| `test_kc_dentro_limites` | `kc ∈ [0,35; 0,76]` (mne-3) |
| `test_kpg_nao_maior_que_1` | `kpg ≤ 1` (mne-3) |
| `test_mrd_reduzido_por_kpg` | `M_Rd < Wxc·fy/γa1` + governante |
| `test_guard_validade_aw_afc` | `Aw/Afc>10` sinaliza (mne-4) |
| `test_momento_resistente_nao_aborta_esbelta` | despacho H (não ValueError) |
| `test_compacta_usa_anexo_g_inalterado` | Anexo G intocado (mne-2, `Mpl=Zx·fy`) |
| `test_misula_alma_fina_calcula` | mísula alma fina fim-a-fim (`flt_misula`) |
| `test_cb_nao_excede_plato` | trava FLT: Cb=2,5 no inelástico não passa do platô (parecer pt.2) |
| `test_flm_inelastico_presente` | ramo inelástico da FLM existe, sem Cb (parecer pt.1) |

11 testes verdes.

## Notas / backlog

- Cortante da alma esbelta (flambagem por cisalhamento) já é verificada por
  `chk.verifica` (3 domínios, kv=5) — o Anexo H trata do **momento**.
- Refinos ofertados no parecer 2: alívio de cortante das mesas inclinadas (4a) e
  γ do AISC DG25 como cross-check — backlog.
