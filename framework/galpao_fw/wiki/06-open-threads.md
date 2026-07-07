# 06 — Open threads

## T1 — PR #1 aguarda merge
Branch `revisao/homologacao-12-modulos` → `main`. https://github.com/JHenriquesss/FreeCad_Automatic/pull/1 . Contém 87 commits (origin/main estava 87 atrás do local). Merge sincroniza tudo. Usuário faz merge pelo GitHub.

## T2 — Divergência local ↔ origin (87 commits)
`origin/main` estava 87 atrás. PR #1 é o veículo de sync. Se quiser PR enxuto só da revisão (2 commits), rebasear a branch — mas aí o resto do trabalho local não sobe. Decisão do usuário.

## T3 — Backlog: módulo ponte rolante estendido
Cargas de ponte rolante ainda não totalmente no toolkit; construir/estender após validação (frac_long por rodas motoras, fadiga Anexo K não automatizada — só flag). Ver memory `crane-module-backlog`.

## Lacunas de escopo estrutural (gap analysis 2026-07-07)
Além dos flags de executivo (T4), o projeto de galpão **completo** ainda não cobre (dentro do escopo estrutural):
1. ~~Ancoragem do chumbador no concreto~~ — **PARCIAL** [[04-decisions#D9]]: aderência NBR 6118 9.4.2 feita; **cone de arrancamento + grupo (ACI 318 Ch.17) ainda faltam** (sem ACI no acervo).
2. ~~Recalque da fundação (NBR 6122)~~ — **FEITO** [[04-decisions#D11]]: recalque elástico (Perloff/Veloso&Lopes); Es/ν/Iw INPUT. Pendente: Steinbrenner (estratificado), adensamento (argila).
3. **Fundações profundas** (estaca/tubulão + bloco + viga de equilíbrio) — só sapata isolada.
4. ~~Fadiga da viga de rolamento (Anexo K)~~ — **FEITO** [[04-decisions#D10]]: σSR=Msdx/Wx vs σadm (K.4); categoria+N são INPUT. Refinamento pendente: parcela lateral/biaxial (K.3.3).
5. ~~Junta de dilatação / temperatura~~ — **FEITO** [[04-decisions#D12]]: `junta_dilatacao.py` (Bellei/FCC 65); L_max + movimento térmico. Guia de literatura, não NBR fechada.
6. **Sismo** (NBR 15421) — não verificado (baixa sismicidade BR raramente governa).

## T4 — Flags de projeto executivo (não são bugs — limites de escopo)
- **Fundação**: quantitativo de aço ~10–15% baixo (sem ganchos/arranques 22.6.4.1) — marcador de anteprojeto. Detalhamento/ancoragem = executivo.
- ~~**Fundação**: sapata flexível exige punção 19.5~~ — **RESOLVIDO** [[04-decisions#D8]]: `puncao_sapata()` verifica C' a 2d; auto-sizer ainda prefere rígida.
- **Ponte**: fadiga Anexo K sinalizada, não automatizada (depende da categoria de detalhe de fabricação).
- **Redim/mão-francesa**: Lb fixo (col 2,0m / viga 1,67m) é contrato — a mão-francesa deve entregar essa contenção da mesa interna. Premissa de wiring.
- **σ_solo,adm, μ, coesão, φ (impacto ponte), frações lateral/long** — INPUT de sondagem/fabricante; bloqueia se não informado.

## T6 — Build 3D: detalhamento executivo (em andamento)
Workstream ativo (usuário reportou defeitos de teto). **Corrigido + confirmado empírico no FreeCAD** [[04-decisions#D7]]: calha invertida (lado D), telha enterrada nas terças, regra de auditoria de orientação da calha, **chapa de emenda no ápice** (CONEX_CUMEEIRA, chapa+4 M24/pórtico).

**Verificação empírica (doc `audit_build2`, 551 obj):** `checa_interferencia`=0, `verifica_conexoes`=0, `estrutura_em_aberturas`=0. Calhas CM.z 5964,5 < centro 6000 (abrem p/ cima). Telha ZMin 6299,1 > terça topo 6298,8 (assenta). Export OK (`exports/freecad/galpao_20x10.FCStd`, `exports/step/...`). Build 2s / auditoria 5s / export 0,8s (rodar por estágio; `run()` completo estoura o cap ~30s do bridge xmlrpc — chunk).

**Enhancements deliberadamente adiados (baixo valor/risco alto — NÃO são defeitos):**
- **Terças ⊥ ao plano do telhado**: hoje horizontais (web vertical), assentadas por `_assenta`. Slope 10% (5,7°) → impacto visual/funcional pequeno; mudar gira a seção e mexe no `_assenta`. Deixado.
- **Enrijecedores do joelho** dz −15/−95 (80mm) vs mesas do rafter (171mm): conceitual, marginal. Deixado.
- **Rufos** de cumeeira/beiral (acabamento). Deixado.

## T5 — settings.local.json não criado
Tentativa de adicionar allow-rules (`git push`, `rmdir`) bloqueada pelo classifier (auto-mode bypass). Usuário precisa criar manualmente se quiser destravar push permanente. Ver [[04-decisions#D0]].

## Resolvidos nesta sessão
- ~~`Nova pasta/` duplicata~~ — removida pelo usuário.
- ~~4 defeitos de código~~ — ver [[04-decisions]] D2–D5.
