# 04 — Log de decisões

Formato: `Dn — data — decisão. Porquê. Alternativa rejeitada.` Append-only.

## D1 — 2026-07-06 — Base concreto sem 0,85
`base_chumbador` σc,Rd = fck/(γc·γn)·√(A2/A1) ≤ fck, γc=γn=1,40, **sem** o 0,85. Porquê: NBR 8800 6.6.5 não traz o 0,85 (isso é AISC/ACI). Rejeitado: parecer que pedia 0,85.

## D2 — 2026-07-07 — Ligações: ruptura do metal-base da solda
`ligacoes.fw_rd_base` passa a `min(0,60·fy·Ag/γa1 escoamento, 0,60·fu·Anv/γa2 ruptura)`. Porquê: NBR 8800 Tab.8 + 6.5.5; o `0,60·fy·Ag/γa1` original era a linha de penetração total, errado p/ filete. Alternativa rejeitada (mesmo parecer): "interação exclui esmagamento" — falso, gate `min(Fvrd,Fcrd)` já existia.

## D3 — 2026-07-07 — Ponte: seção monossimétrica
`ponte_rolante` aceita override `Wy_top`/`Zy_top` (fallback `Wy/2`). Porquê: `Wy/2` só vale p/ I bissimétrico; viga de rolamento média/alta usa I+U na mesa sup. Retrocompatível (sem override = idêntico).

## D4 — 2026-07-07 — Fundação: rho_min(fck) + adesão na área efetiva
(a) `RHO_MIN` fixo → `rho_min(fck)` Tabela 17.3 (NBR 6118). Porquê: 0,15% só vale piso até fck 30; sobe p/ fck>30 (0,164%@35…0,208%@50). Adota valor de **viga** (mais exigente que laje 2-dir 0,67·ρmin) → cobre qualquer classificação. fck≤30 devolve 0,0015 (sem regressão).
(b) Adesão (coesão) passa a atuar só na **área de contato efetiva** `A_ef=B·min(x,L)`; atrito segue `N_tot·μ`. Porquê: sob uplift (e>L/6) só B·x toca o solo (Velloso & Lopes). Contato total → idêntico.

## D5 — 2026-07-07 — Redim: flecha lateral H/150 → H/300
`redimensionamento` LIM_FLECHA = EAVE/300 (todas as ocorrências). Porquê: NBR 8800 **Tabela C.1** literal — "Galpões e edifícios de um pavimento: deslocamento horizontal do topo dos pilares em relação à base = H/300" (limite duro, sem nota; H/400 é do nível da viga de rolamento). H/150 era 2× tolerante. **Impacto real:** perfil adotado muda HEA200/HEA180 → HEB200/IPE300 (galpão de alma cheia governado por ELS, interações 0,42/0,43≪1). `_peso_rel` também virou 2·(A_col·L_col+A_raf·L_raf) (proxy honesto, não muda seleção — que é ordem da escada monótona).

## D6 — 2026-07-07 — Pareceres normativos rejeitados (padrão)
3 pareceres tentaram import de norma estrangeira ou misread: (a) base 0,85 [D1]; (b) contravento "Anexo L da NBR 8800 = contenção nodal" — **falso, Anexo L é vibrações**; Pbr/βbr é AISC 360 App 6; a NBR 8800 trata rigidez de contenção via imperfeição equivalente 4.9.3.2; (c) mão-francesa "lo/hi não inicializado / não expande hi" — artefato do snippet resumido do doc; código real completo. **Regra:** conferir sempre contra o PDF + código real, não o parecer.

## D7 — 2026-07-07 — Build 3D: defeitos de teto + regra de auditoria + ápice
`build_galpao.py`. Confirmado empírico no FreeCAD (ver [[06-open-threads#T6]]).
(a) **Calha invertida** lado D: `roll=-90` abria a boca para baixo (+Y→−Z); ambos os lados agora `roll=+90` (boca +Z, para cima). (b) **Telha enterrada nas terças**: `zr=EAVE_H+200` deixava a telha ~94mm abaixo do topo da terça; agora `zr=EAVE_H+_off+TCL/2` com `_off=max(zb+UE_SEC[0]−rafter_z(y))` MEDIDO das terças assentadas (POFF era só estimativa; `_assenta` levanta ~5mm). (c) **Nova regra em `verifica_conexoes`**: orientação da calha por centro de massa (`CenterOfMass.z > BoundBox.Center.z` ⇒ invertida) — boundbox não distingue (simétrico), CM sim. (d) **Chapa de emenda no ápice** `cumeeira_conn()`: os 2 rafters se encontravam sem ligação de momento; add chapa de topo + 4 M24 (`CONEX_CUMEEIRA_*`) por pórtico. Pontos cegos que deixaram (a)/(b) passar: calha→auditor media só `ZMin`; telha→é `PELE`, fora do clash.

## D8 — 2026-07-07 — Fundação: punção da sapata flexível (19.5)
`fundacao_sapata.puncao_sapata()` + integração em `dimensiona_sapata_B`. Fecha a pendência (antes forçava rígida e só flagava). Flexível (`h<(a−ap)/3`) → verifica C' a 2d: `τSd=F_ef/(u·d)` (19.5.2.1), `τRd1=0,13(1+√(20/d))(100ρfck)^⅓` (19.5.3.2), `u=2(C1+C2)+4πd`, alívio `F_ef=N_d−σ·A_C'` (reação do solo dentro de C', modelo de sapata), `ρ=√(ρx·ρy)`, `σcp=0` conservador. Rígida dispensa (22.6.2.2, já coberta pela compr. diagonal). Fórmulas do PDF NBR 6118. Selftest #11. Não-regressivo (exemplo rígido inalterado). Escopo: auto-sizer ainda sobe h→rígida; punção é o caminho p/ geometria flexível.

## D9 — 2026-07-07 — Base: ancoragem do chumbador no concreto (NBR 6118 9.4.2)
`base_chumbador.ancoragem_chumbador()`. Fecha o lado do concreto (só tinha aço/placa/bearing). Aderência: `fbd=η1η2η3·fctd` (9.3.2.1, η1=1,0 barra lisa), `lb=(φ/4)(fyd/fbd)` (9.4.2.4), `lb,nec=α·lb·(As,cal/As,ef)≥lb,min`, α=0,7 c/ gancho (9.4.2.5). Saída = embutimento requerido `lb,nec` (como t_req), **informativo** (não gateia OK salvo `gate_ancoragem=True`). Razão: aderência de barra lisa é conservadora e subestima gancho/placa mecânico. **Cone de arrancamento + grupo (ACI 318 Ch.17) seguem FLAG** — não há ACI no acervo p/ citar; aderência NBR não cobre o cone. Fórmulas do PDF NBR 6118. Selftest #5. Não-regressivo (auto-sizer inalterado). Ex.: d20 liso, Ft,Sd 63 kN → lb,nec 593mm.

## D10 — 2026-07-07 — Ponte: fadiga da viga de rolamento (NBR 8800 Anexo K)
`ponte_rolante.verifica_fadiga()` + `_FADIGA_K1` (Tabela K.1 do PDF). Antes era só FLAG; agora calcula `σSR=Msdx/Wx` (K.3) vs `σadm=(327·Cf/N)^0,333≥σTH` (K.4). Carga de fadiga B.7.3.4 = 1 ponte com impacto; como P=φ·Rmax (caract. c/ impacto, sem γf) e a móvel zera, faixa≈Msdx. Tabela K.1 lida do PDF: A(250e8,165) B(120e8,110) B'(61e8,83) C(44e8,69) D(22e8,48) E(11e8,31) E'(3.9e8,18). Categoria (`cat_fadiga` default B) e N ciclos (`n_ciclos`, NBR 8400) são INPUT (não inventa detalhe). Entra no OK da viga. Selftest. Não-regressivo (VS500 inalterado). Limite: só flexão vertical; lateral/biaxial (K.3.3) = refinamento.

## D11 — 2026-07-07 — Fundação: recalque elástico (ELS, NBR 6122)
`fundacao_sapata.recalque_elastico()` + integração em `verifica_sapata_A`. Fecha o deslocamento da fundação (só tinha capacidade/estabilidade). NBR 6122 remete a métodos geotécnicos → teoria da elasticidade (Veloso & Lopes / Perloff 1975, lido do PDF): `ρ = q_liq·B·(1−ν²)·Iw/Es`. B=menor dim; Iw rígido círculo 0,79 / quadrado 0,88 (Tab.5.1). Es, ν, Iw, ρ_adm = INPUT (Ask). Sem `Es_solo` → não calcula (FLAG, não afeta OK_A); com Es → entra no OK_A (só reprova se exceder). Carga de serviço (N_serv; envelope ELU conservador). Selftest #12. Não-regressivo. Limites: recalque imediato/elástico (homogêneo); Steinbrenner (estratificado) e adensamento (argila) ficam fora; ρ_adm 25mm default + diferencial ≤15mm (Tab.C.1) a confirmar.

## D0 — política permanente
Push direto na `main` bloqueado pelo auto-mode classifier → usar branch + PR. Assistente não pode se auto-conceder permissão (escrever allow-rule = bypass, bloqueado). Usuário roda via `!` ou adiciona regra manualmente.
