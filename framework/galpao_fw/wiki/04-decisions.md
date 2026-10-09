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

## D12 — 2026-07-07 — Junta de dilatação / movimento térmico (novo módulo)
`junta_dilatacao.py` + wire em `rodar_galpao` (`gate7-junta-dilatacao.txt`). Fecha a ação de temperatura em galpão longo. Bellei §4.5 / Federal Construction Council Report Nº65 (via AISC 2005), lido do PDF: `δ=α·dT·L` (α=12e-6/°C, dT=30°C ±15 Brasil); L_max entre juntas = 120m (aço retangular simétrico) / 60m (não-retangular), × soma de fatores (sem aquecimento −33%, AC+aquec +15%, base fixa −15%, rigidez assimétrica −25%). Galpão típico (retangular, sem aquec, engastado) → 120·0,52=62,4m. dT/condições = INPUT. Selftest. Guia de literatura (não cláusula NBR fechada) — flag. É recomendação + movimento; detalhe da junta = executivo.

## D13 — 2026-07-07 — Build 3D: joelho simétrico + folga da telha
Dois defeitos determinísticos que recorriam em TODO galpão gerado (`build_galpao.py`). (a) **Joelho invertido de um lado:** `v = cross(dirn,u)` trocava de sinal entre os beirais (dirn inverte em Y no cume) → mísula pendurava p/ baixo num lado e p/ CIMA no outro. Fix: `if v[2]>0: v=-v` (força +v p/ baixo nos dois lados). Removido o `sgn` que era calculado e nunca usado. Medido: mísulas E e D agora idênticas [5467→5994], ambas sob a viga. (b) **Terça aflora pela telha:** fix v2 (D7) acertou a cota mas com folga ZERO — face inf da telha (pele 0,65mm) coplanar ao topo da terça mais alta → aba lê como "acima da telha". Fix: `TELHA_GAP=20mm` (altura do clipe) em `zr/zrr`. Medido: 20mm de folga em todo o vão. Verificado no FreeCAD: 551 obj, 0 interferências, 0 conexões suspeitas. Não-matemático (geometria) — sem doc de método.

## D14 — 2026-07-08 — Base: cone de arrancamento do concreto (ACI 318 Ch.17)
`base_chumbador.cone_arrancamento_aci` fecha o modo de ruptura do concreto na tração (o que a aderência §9 não cobre). **Fonte:** não há ACI 318 no acervo → usei **Nilson, _Design of Concrete Structures_ 15ª ed. cap.21**, que reproduz o **ACI 318 Ch.17** (método CCD), lido do PDF. ACI é em unidades US (lb, in, psi) → rotina converte **entrada SI→US no contorno** p/ preservar as constantes exatas (kc=24, ANco=9hef², Np=8·Abrg·fc', Nsb=160·..., 1,9·fya), devolve kN (mesmo padrão da punção). Modos: breakout Ncbg (21.6, ψec/ψed/ψc/ψcp), pullout Npn (headed 8·Abrg·fc' / gancho 0,9·fc'·eh·da), side-face Nsb (21.12). φ Tab.21.1 (breakout cast-in Cond.B 0,70 / Cond.A 0,75; pullout 0,70). **Opt-in** via `caso["cone_geom"]` (geometria do bloco = projeto de fundação, Ask-Do-Not-Invent); informativo, gateia só se `gate_cone=True`. Selftest #6 reproduz Nilson Ex.21.3 (Ncbg=33,7 kip=149,7 kN) + Ex.21.6 (Npng=141,4 kip=628,9 kN) via entrada SI → isolamento de unidades provado. Nota física: gancho L tem pullout baixo (governa) → recado do ACI de usar cabeça/placa ou armadura de ancoragem. Em aberto: cortante (breakout/pryout do V), armadura de ancoragem (17.4.2.9), interação T-V (21.16).

## D15 — 2026-07-08 — Base: tríade de transferência de cortante (Fakury cap.11)
`base_chumbador.transferencia_cortante_base` fecha a física do cortante da placa de base (antes só Fv,Rd do chumbador + interação). **Fonte:** Fakury/Silva/Caldas, _Dimensionamento de elementos estruturais de aço e mistos_, cap.11 "Bases de pilar", lido do PDF — SI/NBR (preferido ao AISC DG1, ausente do acervo). Triagem automática por prioridade: (1) **atrito** Vat,Rd=min(0,7·µ·Nc,Sd; 0,2·fck·Y·B), µ=0,55 sem pintura (11.21) — só com compressão; (2) **chumbador** Vca,Sd=VSd−Vat (11.26); (3) **chaveta/barra de cisalhamento** dimensionada: hbc≥2·har, σbc=Vbc/(bbc·(hbc−har))≤σc,Rd (11.25/28), Mbc=Vbc·cbc com cbc=har+(hbc−har)/2 (11.23/24), tbc por plastificação. Crédito do atrito é **opt-in** (`atrito_cortante=True`) — exige compressão na mesma combinação do V; default conservador (todo V nos chumbadores, não-regressivo). Selftest #7: atrito resolve (V26/Nc200) e uplift (Nc=0 → chaveta). Edge breakout do concreto no cortante (ACI 318 Ch.17 Vcbg) fica FLAG — fórmulas do Nilson (Vb, AVc/AVco) já lidas, próxima sprint. Fecha a "tríade" pedida (atrito+chumbador+chaveta).

## D16 — 2026-07-08 — Ponte: fadiga inclui 50% da força lateral (B.7.3.4)
`ponte_rolante.verifica_fadiga` passa a somar a parcela lateral: `σ_SR = Msdx/Wx + 0,5·Msdy/Wy_top`. Porquê: **B.7.3.4** (lido verbatim do PDF NBR 8800) manda considerar "cargas verticais majoradas pelo impacto e **50% das forças horizontais**"; a versão anterior só usava a vertical (flag de refinamento). Surto atua na mesa superior → usa `Wy_top` (banzo sup, fallback `Wy/2`); `frac_fadiga_lat` parametrizável (default 0,5). Efeito: VS500 σ_SR 57→75 MPa (u 0,46→0,60), ainda passa; termo lateral +32% (Wy_top esbelto) — pode virar cat B↔C a alto N (ponto do parecer do sênior). Soma simples das fibras do topo (conservadora vs biaxial rigorosa K.3.3). Selftest checa split x/y. Atende recomendação do parecer rodada-fadiga.

## D17 — 2026-07-08 — Junta: log explicita δ/2 por lado + rigidez assimétrica
`junta_dilatacao.relatorio_pt` passa a imprimir `~δ/2 por lado` e a escolha executiva (furo oblongo/apoio deslizante que absorva δ/2 **OU** pilar de extremidade dimensionado p/ o momento do deslocamento imposto). Documentado `rigidez_assimetrica` (−25%) = contraventamento vertical X concentrado numa fachada (dilata contra o ponto rígido). Atende as 2 diretrizes do parecer de homologação da junta (matemática já estava exata: Lmax 62,4, 1 junta, δ=18mm). Módulo `junta_dilatacao` homologado. **Fecha o lote de 7 features novas — todas homologadas.**

## D18 — 2026-07-08 — Sismo: NBR 15421 (forças horizontais equivalentes)
Novo módulo `sismo_nbr15421.py` + wire em `rodar_galpao` (`gate7-sismo.txt`). Fecha a última grande lacuna (ação sísmica). Fonte: **NBR 15421:2023** entrou no acervo (`pesquisa/aço/`), lido do PDF. Método das forças horizontais equivalentes (Seção 9): H=Cs·W, Cs=2,5·ags0/(R/I) ≤ ags1/(T·(R/I)) ≥ 0,01; espectro Sa(T) 4 trechos (6.3); Ta=CT·hn^x (9.2); distribuição Fx=Cvx·H com k (9.3). Tabelas lidas: 1 (zonas/ag), 2 (classe terreno), 3 (Ca/Cv), 4 (I), 5 (categoria), 6 (R/Ω0/Cd), 10 (Cup). Triagem: zona 0 → dispensado (default, maior parte do BR); zona 1 → Fx=0,01·wx; zonas 2-4 → método completo. zona/classe/R/I/W = input do sítio (Ask-Do-Not-Invent). Selftest: espectro platô/ramo, Ca/Cv interp, Cs zona3 (0,1607), triagem 0/1/3. Combinação última EXCEPCIONAL (γq=1,0). Limites: só estático (modal Seção 10 / histórico 11 fora); torção/P-Δ/deslocamentos não automatizados; Ω0/Cd tabelados não aplicados.

## D19 — 2026-07-08 — Base: edge breakout no cortante (ACI 318 Ch.17)
`base_chumbador.edge_breakout_cisalhamento_aci` fecha o modo do concreto no cortante quando o V vai aos chumbadores perto da borda. Fonte: Nilson cap.21 = ACI 318 Ch.17 (CCD), lido do PDF. Vb=(7·(le/da)^0,2·√da)·λ·√fc'·ca1^1,5 ≤ 9·λ·√fc'·ca1^1,5 (21.3/21.4); AVco=4,5·ca1²; AVc=largura×min(1,5ca1,ha); ψed,V/ψc,V/ψh,V=√(1,5ca1/ha); Vcbg=(AVc/AVco)·ψ·Vb; paralelo à borda 2× (17.5.2.1); pryout Vcpg=kcp·Ncbg (kcp 1/2). φ 0,70 Cond.B. Mesmo isolamento US↔SI da tração. Opt-in (cone_geom+h_bloco), informativo; roda quando o mecanismo do cortante é "chumbador". Selftest #8 reproduz Nilson Ex.21.5 (Vb=13,56 kip=60,3 kN, AVco=288, ψed=0,90 p/ ca2<1,5ca1). Ex HEA200: Vcbg cap=33 kN vs V=26 → u=0,80. Fecha a lacuna do edge breakout que era FLAG (§11). Em aberto: ψec,V, interação T-V (21.16), armadura de ancoragem (17.4.2.9).

## D20 — 2026-07-08 — Base: warning de armadura de ancoragem (hairpin)
`edge_breakout_cisalhamento_aci` passa a expor `armadura_ancoragem = not ok_edge`; o relatório emite [WARNING] quando `u_edge>1`: projeto de fundação deve detalhar armadura de ancoragem em laço (hairpin/estribo) atravessando a ruptura (ACI 318 17.5.2.9), que dispensa o breakout do concreto. Atende recomendação do parecer de homologação do §12. Recado ao fundações (segregação de disciplinas), não trava a metálica. Selftest #8 checa flag u>1 vs caso folgado. Edge breakout §12 homologado.

## D21 — 2026-07-08 — Base: interação tração-cortante do concreto (ACI 318 17.6)
`base_chumbador.interacao_tracao_cortante_aci` combina cone de tração (§10) + edge breakout (§12) no modelo TRILINEAR do ACI 318 17.6 (Nilson 21.16): se Vua/φVn<0,2 → só tração; se Nua/φNn<0,2 → só cortante; senão Nua/φNn+Vua/φVn≤1,2. φNn/φVn = capacidades de cálculo governantes (menor modo de cada). Opt-in (roda quando cone + edge presentes), informativo. Selftest #9: 3 regimes + reprova (0,8+0,6=1,4>1,2). Ex HEA200 gancho: rN=3,34+rV=0,80 → u=3,45 NAO PASSA (pullout de gancho governa, coerente). Curva 5/3 (Fig.21.12) é alternativa; ACI Code usa trilinear. **Fecha a base 100% nos modos do concreto (§9-§13).**

## D22 — 2026-07-08 — Base: curva 5/3 opcional na interação T-V
`interacao_tracao_cortante_aci` ganha `curva_exata=True` (caso["interacao_curva_exata"]) → envoltória de potência (ACI 318 17.6.3 / Fig.21.12): (Nua/φNn)^(5/3)+(Vua/φVn)^(5/3)≤1. ~2-8% mais de capacidade central; trilinear continua default (auditabilidade). Atende sugestão do parecer de homologação do §13. Selftest #9: 0,65+0,65 reprova trilinear (1,3>1,2) mas passa 5/3 (0,978<1). §13 homologado — base 100% completa nos modos do concreto.

## D23 — 2026-07-08 — Ligações: detalhamento dos furos (6.3.9/10/11)
`ligacoes.verifica_espacamento` + `parafusos` deriva o `lf` (esmagamento 6.3.3.3) da GEOMETRIA (e_borda/s_furos) em vez de input solto. Regras lidas do PDF NBR 8800: 6.3.9 s≥2,7db (pref 3db) + livre entre furos ≥db; 6.3.10 s_max≤min(24t;300); lf=min(e_borda−dh/2; s_furos−dh), dh=db+1,5mm (Tab.12). Tabela 14 (furo-borda) fica FLAG — extração ambígua e a própria nota (a) remete ao 6.3.3.3 (resistência já calculada). Não fabriquei os valores mm da Tab.14 (zero-erro). Retrocompatível: sem geometria usa lf explícito. Selftest: s=60≥54 OK, livre 38,5≥20, lf=24,25; s=45<54 reprova. Pequena lacuna #1 (das pequenas antes das grandes).

## D24 — 2026-07-08 — Vento: Cpe médio local de borda/canto (Tab.4/5)
`vento_nbr6123` ganhou `cpe_local_parede` (Tab.4 col. cpe médio, faixa min(0,2b;h)), `cpe_local_cobertura` (Tab.5 col. cpe médio, envoltória das 4 zonas hachuradas interpolada em θ; faixa y=min(h;0,15b), zona min(max(b/3;a/4);2h)) e `sucao_local_fixacao` ((cpe_medio−cpi)·q, cpi=+0,8 arranque). Governa TELHA/TERÇA/FIXADOR de borda-canto, NÃO o pórtico. Ref 20×10 (h/b=0,6, θ=5,71°): envoltória cobertura −2,0 → sucção local −2,203 kN/m² = 62% acima da global. Tabelas lidas VERBATIM do PDF (págs.14-15) via render de imagem (grid é vetor, não extrai como texto). `_CPE_MEDIO_COB` guarda os 3 blocos h/b com `None` p/ células em branco. Aditivo: nova chave `local` no compute, sem tocar Cpe global/S2/q/Fa (não-regressivo). Orquestrador passa larg_b/alt_h/comp_a da geometria. Pequena lacuna #2. [[04-decisions#D23]] mesma sprint de lacunas pequenas.

## D25 — 2026-07-08 — Telha: verificação vão×carga (NBR 14762)
Novo `telha_cobertura.py`: telha como viga de 1 m sobre as terças. ELU M_Sd≤M_Rd=Wef·fy/γ (γ=1,10); ELS flecha L/180 grav / L/120 vento; `vao_max` inverte ambos p/ tabela vão×carga. Combos 1,25G+1,50Q e 1,40W−0,90G (W = sucção local do vento §8, fecha o par com [[04-decisions#D24]]). Continuidade simples/2vãos/contínua (coef M e flecha clássicos). Props da telha (Wef, Ief, peso) = CATÁLOGO do fabricante → param A CONFIRMAR (TELHA_EXEMPLO é ilustrativo, NÃO normativo); não recalcula Wef (catálogo já é efetivo). Não dimensiona o fixador (fabricante). Orquestrador: vão = √((span/2)²+(ridge−eave)²)/n_terca, W_sucao auto do vento local; gate7-telha.txt, item 6b no consolidado; só roda com params["telha"]. Ref 20×10: vão 1,68 m, sucção governa ELU (util 0,557), vão máx 2,19 m (ELS vento). Pequena lacuna #3 (última das pequenas).

## D26 — 2026-07-08 — Sismo → envelope do pórtico (combinação excepcional)
Sismo passa de "calculado e ignorado" a caso de carga no envelope. NBR 15421 §5.4 (verbatim): ação sísmica = EXCEPCIONAL (§5.2); combinação última excepcional NBR 8681 5.1.3.3 → γg=1,2 desfav (Q_uso≤5kN/m²) / 1,0 fav, γexc=1,0, γq=1,0; VENTO não entra (§5.4 explícito). Cobertura ψ2=0 → Q vertical não acompanha. Combos C6_sismo_G{desf,fav}_{P,N}: 1,2G±E / 1,0G±E (reversível). Força no pórtico E = H·(vão/comprimento) (cortante de piso por largura tributária), aplicada no beiral (case_sismo). gp.SISMO global (espelha PONTE); entra em galpao_portico (case_sismo+combos), estabilidade_b1b2 (_apply_case cs=SISMO, nt/lt automático pela contenção fictícia do beiral = igual vento), e base/joelho (_casos_mf_reac + _combos_elu(PONTE,SISMO)). Sismo calculado ANTES da análise (rs movido pra cima). Não-regressivo: ref zona 0 → E=0 → SISMO=None → envelope idêntico (coluna 0,42/viga 0,68/base −57,5 inalterados). Teste zona4/E/pêndulo/I1,25/W1500: Cs=0,394, E=147,7 kN/pórtico, C6 governa base (M=261,7) e sobe coluna a 0,91. FLAG: distribuição por largura tributária (pórtico interno), θ/P-Δ sísmico (9.6) e ortogonal 100/30 fora. Média #1. [[04-decisions#D24]] fecha as lacunas do envelope de ações.

## D27 — 2026-07-08 — Viga de baldrame / amarração entre sapatas (NBR 6118)
Novo `viga_baldrame.py`: viga RC entre sapatas com 2 papéis — (1) baldrame sob parede de fechamento → flexão 17.2.2 + ρmin (Tab.17.3); (2) amarração absorve a reação horizontal da base como tração As=Nd/fyd. Reaproveita fs._armadura_flexao/rho_min/detalha_barras (concreto já homologado). Detalhamento verificado no PDF: b_min=12cm (13.2.2 verbatim), estribo s_max=0,6d≤300mm (18.3.3.2). γf=1,4, fcd=fck/1,4, fyd=fyk/1,15. As_inf=max(As_flex+As_tie/2, As_min); As_sup=max(As_tie/2, As_min). N_amarração = max|V| da base no envelope (real, não regra empírica tipo Alonso Nd/20). Orquestrador: vao=bay, N auto, q_parede do fechamento (0=telha); gate7-baldrame.txt item 11b; só roda com params["baldrame"]. Ref 20×10 (telha, q_parede=0): As_min governa (20×40, 2Φ10), amarração 32,9 kN. FLAG: cortante VRd assume Vd≤0,67VRd2 (estribo min); viga de equilíbrio/alavanca de divisa fora de escopo. Média #2. [[04-decisions#D26]] fecha o par fundação: sismo no envelope da base + amarração das sapatas.

## D28 — 2026-07-08 — Fundação profunda: estaca (Aoki-Velloso) + bloco de coroamento
Novo `estaca_profunda.py` fecha a última lacuna grande. Capacidade da estaca Aoki-Velloso (1975): R_ult=R_ponta+R_lateral, R_ponta=(K·N_p/F1)·A_p, R_lat=Σ(α·K·N_l/F2)·U·Δz; P_adm=R_ult/FS (NBR 6122 FS=2,0 semi-empírico sem prova). Tab.12.6 (K[kPa]/α[%]) e Tab.12.7 (F1/F2) lidas do PDF Veloso&Lopes 2012 via RENDER DE IMAGEM (OCR corrompido) — K em kPa = kgf/cm²×100 (Cintra&Aoki). N limite 50. Bloco de coroamento por bielas-e-tirantes (Blévot/NBR 6118 22.3) por EQUILÍBRIO (não coeficiente memorizado): braço=esp/2−a_pilar/4, T=(N/n)·braço/d, As=T/fyd; 2 ou 4 estacas. Orquestrador: N_pilar=max|N| base envelope; gate7-estaca.txt item 11c; opt-in via params["estaca"] → ref permanece em sapata (rasa, não-regressivo). Décourt-Quaresma NÃO implementado — tabela C (12.12) não legível o suficiente, não fabriquei (zero-erro) → FLAG cross-check futuro. Biela comprimida/punção do bloco, atrito negativo, tração e efeito de grupo da estaca = fora de escopo (FLAG). Grande #1 (última). ANÁLISE DE LACUNAS ENCERRADA: 3 pequenas + 2 médias + 1 grande fechadas. [[04-decisions#D27]] par fundação (rasa+profunda+amarração).

## D29 — 2026-07-08 — Sprint de FLAGs residuais (pós-lacunas)
Fechados os FLAGs individuais enquanto aguardam pareceres: (1) Décourt-Quaresma como cross-check da estaca (Tab.12.12 C / Tab.12.13 r_l=N/3+1, lidas do PDF; relatório mostra os 2 métodos + dif%); (2) estaca à TRAÇÃO/uplift (só atrito lateral/FS; N_uplift = max reação negativa da base no envelope — governa no galpão pois base é uplift de vento); (3) biela comprimida + punção do bloco (NBR 6118 22.3.2: fcd1=0,85·αv2·fcd CCC, fcd3=0,72·αv2·fcd CCT, αv2=1−fck/250, σ=F/(A·sen²θ), tanθ∈[0,57;2]; rígido dispensa punção); (4) sismo θ/P-Δ (NBR 15421 9.5/9.6: δx=Cd·δxe/I, θ=Px·Δx/(Hx·hsx·Cd), <0,10 dispensa, 0,1<θ≤0,5/Cd amplifica 1/(1−θ); δxe=drift sísmico do pórtico); (5) block shear/rasgamento em bloco (NBR 8800 6.5.6: min(0,6fu·Anv;0,6fy·Agv)+Cts·fu·Ant /γa2). Todos verbatim do PDF, selftest PASSED, não-regressivos. Commits acf47b1→d76f5ad. FLAGs remanescentes (secundários/fora de escopo): Décourt 2ª versão α/β, ancoragem do tirante, atrito negativo/grupo da estaca, ortogonal 100/30 (só cat.C irregular 3D), T-stub/prying (EN 1993, fora da NBR), Tabela 14 furo-borda. [[04-decisions#D28]] completa a fundação profunda.

## D30 — 2026-07-08 — FLAGs remanescentes fechados (Tab.14, grupo, ancoragem, 100/30, T-stub)
2ª leva de FLAGs: (1) Tabela 14 furo-borda (NBR 8800, lida do PDF pg.94 por db mm) + dist. máxima 6.3.12 (12t≤150) — verifica_espacamento agora gate ok_borda_t14; (2) efeito de grupo Converse-Labarre η=1−(θ/90)[(m−1)n+(n−1)m]/(mn); (3) atrito negativo N_neg=U·Σ(f_neg·dz); (4) ancoragem do tirante do bloco (NBR 6118 9.3.2: fbd=η1η2η3·fctd, fctd=0,7·0,3fck^⅔/1,4, η1=2,25, lb=(φ/4)(fyd/fbd)); (5) ortogonal 100/30 sismo (NBR 15421 8.5, só cat.C irregular); (6) T-stub/prying da chapa de topo (EN 1993-1-8 6.2.4, 3 modos — fora da NBR, mas padrão p/ joelho). Todos verbatim do PDF (ou EN documentado), selftest PASSED, não-regressivos. Commits 8d05fcb→7644d30. FLAGs que PERMANECEM abertos por decisão honesta: Décourt 2ª versão α/β (tabelas 12.15/12.16 não legíveis no PDF, não fabricadas — versão inicial implementada); recalque do grupo (ELS, tópico separado); punção do bloco flexível (dispensada p/ rígido, caso comum). [[04-decisions#D29]] 1ª leva de FLAGs.

## D31 — 2026-07-08 — Últimos FLAGs da estaca (Décourt FS partido, recalque grupo, punção flexível)
Fechados os 3 que "permaneciam": (1) Décourt FS partido — Q_adm=R_lat/1,3+R_ponta/4,0 (Veloso&Lopes pg.288, lido do PDF: FS_lat=1,1·1,2≈1,3, FS_ponta=1,35·2,5·1,2≈4,0) — a admissível própria de Décourt, ponta mais penalizada; (2) recalque do grupo por radier equivalente (sapata fictícia a z=⅔L atrito/z=L ponta, espalhamento 1:4, recalque elástico reusando fundacao_sapata); (3) punção do bloco FLEXÍVEL (tanθ<0,57): C' a 2d, carga total sem alívio, τsd=N/(u·d)≤τrd1 (NBR 6118 19.5.3.2). Commit 343dfb4. Residuais verdadeiros (extensão, não gap): α/β de estacas escavadas (Décourt 1996 — Teixeira 1995 é outro método), punção rigorosa de bloco CEB/Blévot ao redor das estacas. TODOS os FLAGs corrigíveis fechados. [[04-decisions#D30]] 2ª leva.

## D32 — 2026-07-08 — Residuais fechados: Teixeira (3º método) + punção de bloco pilar+estaca
(1) Teixeira 1996 (Tab.12.16 α[tf/m²] por solo×tipo I-IV + β I=0,4/II=0,5/III=0,4/IV=0,6, lidas do PDF pg.290): q_p=α·Np, r_l=β·N_méd; FS global 2,0 (I/II/IV) ou partido 4,0/1,3 (III escavada). 3º método de capacidade — resolve o "α/β" residual com método nomeado e verificado (melhor que o α/β de escavadas do Décourt 1996, não disponível). Ref: Aoki 1600/Décourt 1272/Teixeira 1272 kN. (2) Punção rigorosa do bloco flexível: 2 contornos C' a 2d — pilar (↓) + cada estaca (↑, CEB/Blévot), τsd≤τrd1. Commit próximo. TODOS os residuais fechados; sobra só refinamento acadêmico (α/β escavadas Décourt 1996) coberto por Teixeira. [[04-decisions#D31]].

## D33 — 2026-07-09 — Projeto executivo 2D via TechDraw headless (não scripts de vistas)
Vistas/cotas/tabelas geradas por `techdraw_exec.py` (TechDraw nativo, HLR real), não pelos scripts antigos `vistas_fc`/`dxf_vistas` (deletados — redesenhavam linhas à mão; usuário rejeitou "lixo"). Headless via **`freecad.exe`** (não `freecadcmd`, que não carrega Gui → não exporta PDF); job por `QTimer.singleShot`; page aberta na MDI (`doubleClicked`)+`updateGui` antes do export senão sai vazio. NÃO usa MCP (:9875 corta ~30s no HLR cheio); `rodar_executivo` lança freecad.exe próprio + polling de `_status.json`. Cotas: `DrawViewDimension` ancorada em vértice cosmético 3D nos eixos de PROJETO (não bbox→inclui sapata), `Arbitrary=True`+FormatSpec literal (esquema de unidade exibia m). Fechar TODOS os docs via `App.closeDocument` antes de `quit()` (senão diálogo salvar→zumbi). Convenção fixa: comprimento em X, vão em Y (`comp_x=True`; inferir por bbox quebra se vão>comp). Commits e696b84→a271f24. Pranchas: 9 base A1 ISO5457 PDF+SVG+DXF+PNG. [[03-phases]].

## D34 — 2026-07-09 — Genericidade: guard de cobertura, sem curadoria manual
Regra: o script corta as vistas e mostra **tudo** — sem escolher a mão o que entra (curar prefixo removeu peça real, tubo/calha, do joelho → revertido). Detalhes projetam todo sólido na janela. Guard `_cobertura(doc,todos)`: pós-geração, todo TIPO de sólido (normalizado por lado D/E via `_tipo_solido`) aparece em ≥1 prancha (Source de vista OU dentro de bbox de crop `*_CROP`); o que não é desenhado nem está em `PREFIXOS_SEM_DESENHO` vira `nao_cobertos` → smoke falha. Converte acoplamento folha↔label de falha-silenciosa em falha-detectada. Achou 2 bugs: ESTICADOR em `_MIUDEZAS` (fora de `objs`) mas PE05 buscava de `objs` → nunca aparecia (corrigido: de `todos`); NERVURA faltava no PE02. Numeração de prancha dinâmica (total varia). [[06-open-threads#T6]].

## D35 — 2026-07-09 — Detalhes de ligação PE10–14: eixo de vista CURADO (não heurística)
1ª tentativa (engine genérica, eixo por heurística) projetava a chapa robusta de FRENTE → silhueta cinza chapada sem linhas. Fix: `_pr_ligacoes`/`_detalhe_ligacao` com **eixo de vista curado por tipo** (`_AXES`, tabela `LIGACOES`) — projetando no eixo certo os perfis conectados viram linhas (como o joelho). 1 prancha/tipo presente: cumeeira, gusset cob/parede, clipe girt, console (só ponte). Elevação + (quando útil) vista da chapa c/ furação. `_EXCLUI_LIGACAO`=(TELHA,TAPAMENTO,CALHA) fora do crop (placas grandes poluem). Guard anti-silhueta `_n_edges`≥15 no smoke. `PREFIXOS_SEM_DESENHO` reduzido a `("VAO",)` → toda peça desenhada. NÃO é desenho de fabricação (sem section/hachura/símbolo de solda; nota "conforme memorial"). Commit b0c2e89 (fase /dv detalhes-ligacao). [[03-phases]].

## D36 — 2026-07-09 — Memorial de cálculo em PDF único (método + cálculo)
`relatorio_calculo.py` (reportlab): 1 PDF pro sênior — capa + quadro de verificações + índice + por módulo MÉTODO (norma+procedimento, dict `METODOS` curado) + CÁLCULO (memorial). Lê `MEMORIAL-CONSOLIDADO.txt` (fonte única; seções delimitadas por `#`). Descarta módulos com corpo `(falta)`. Integrado no `build_final.py` (calc→PDF). Commits 91253ee, e8c9b81.

## D37 — 2026-07-09 — Detalhe de fabricação: callouts do cálculo (A+B), corte A em fallback
Ligações passam a ter callout de fabricação **rastreável ao cálculo** (nada inventado). Decisão A+B (C rejeitado: 2ª fonte de verdade + regressão no build_galpao). Como o cálculo só dimensionava base/joelho/clip, foram criados 2 módulos que **compõem primitivos homologados** (não fórmula nova): `gusset_ligacao.verifica_gusset` (Whitmore+block_shear+solda+compressão; Whitmore 30° = convenção AISC, FLAG análogo T-stub) e `console_ponte.verifica_console` (grupo de solda elástico + cisalhamento chapa; dimensiona a perna do filete). Ambos selftest PASSED, gate7-gusset/gate7-console, REVISAO-GUSSET/CONSOLE (PENDENTE sênior, índice 28/29). `joelho_adotado` (antes dropado) + gusset/console threaded ao cfg via `config_de_spec`; `_callout_fab(cfg,key)` anota só números do cfg (joelho "N×db, chapa t"; gusset/console "chapa t, solda perna"); clip sem dado → "conforme memorial". **Corte seccionado (A): `DrawViewSection` FALHA headless** (`failed to create section CS` mesmo em box trivial) → **fallback elevação** (callouts entregam o valor de fabricação). Guard mne-1: callout só do cfg (arquitetural). Commits me-1..me-6. [[03-phases]].

## D38 — 2026-07-10 — Fundação profunda vira cidadã do ProjetoSpec + 3D (fase 3)
Estaca (Aoki-Velloso)+bloco+baldrame, antes opt-in só via `params`, agora gate de 1ª classe. `fundacao.tipo`(sapata|estaca) BLOQUEIA; `fundacao.estaca.perfil_spt`+`tipo_estaca` requeridos condicionais (sondagem, sem default → `validar()` bloqueia); `baldrame` opt-in. Mappers `to_rodar_params` (monta cfg da estaca p/ rodar_galpao 411/426) + `to_build_kwargs` (dims mm; estaca EXCLUSIVA da sapata). `rodar_galpao` expõe geometria (D/L/n/espaçamento/bloco/baldrame) do envelope; `rodar_projeto.calcular` grava `estaca_adotada`/`bloco_adotado`/`baldrame_adotado`. `build_galpao`: `_desenha_estaca` (cilindros+bloco=envelope do grupo+coroa 150mm+pedestal 500mm) + baldrame entre pórticos; concreto de fundação MONOLÍTICO isento de clash interno concreto×concreto (`_e_fundacao`; aço×concreto continua verificado); take-off concreto; PE-02 cobre. Método já homologado (ESTACA/BALDRAME); PENDENTE = só integração/geometria: `REVISAO-FUNDACAO-PROFUNDA-INTEG.md` Q1–Q6, índice 30. Commit 9ac3c4f. [[03-phases]].

## D39 — 2026-07-10 — Ponte estendida: rodas motoras + NBR 8400-1:2019 (fase 4)
(1) Frenagem longitudinal age só nas RODAS MOTORAS: `forcas_horizontais(n_rodas_motoras)`, `H_long=frac_long·R_roda_max·n_motoras` (default n_lado=retrocompat; erro se >n_lado). Basis NBR 8800 (Q1 sênior). (2) NOVO `nbr8400.py` lê a **NBR 8400-1:2019** do PDF (`pesquisa/pdfcoffee...8400`), verbatim: `coef_dinamico(HC,Vh)`=Ψmín+β2·Vh (Tab.12 HC1-4: β2 0,17/0,34/0,51/0,68, Ψmín 1,05/1,10/1,15/1,20; cap Vh 1,5 p.21) e `n_ciclos(B0-B10)` (Tab.9, limite superior conservador). `analisa` usa classe HC/Vh→φ e classe B→N do Anexo K quando dadas, senão input flagado. **Fadiga Anexo K já existia** (T3 wiki desatualizado) — só recebe o N, inalterada. (3) Gate `REQUERIDOS_PONTE`: `validar()` bloqueia ponte incompleta (fabricante) se `ponte!=None`; `ponte=None` válido. PENDENTE `REVISA-PONTE-8400.md` Q1–Q4, índice 31. Commit 4d090e5. [[03-phases]].

## D40 — 2026-07-10 — Corte seccionado headless resolvido (fase 5), reverte D37-A
O `DrawViewSection` **constrói headless no FreeCAD 1.1** — o `failed to create section CS` de [[#D37]] era da versão antiga (probe: box→4 arestas). `techdraw_exec._secao_ligacao` adiciona corte hachurado `VLIG_SEC_*` a cada detalhe (plano pelo centro, normal=xdir da elevação), sem mexer na elevação/callouts. 2 gotchas: (a) enum válido de `CutSurfaceDisplay`=['Hide','Color','SvgHatch','PatHatch'] — `"Hatch"` NÃO existe; uso `SvgHatch` (svg embutido, sem .pat externo). (b) no `freecad.exe` (GUI headless) a geometria da seção computa DEFERIDA → `_n_edges` imediato lê 0 (falso zero) → NÃO descartar na hora; verificação de vazio movida pro guard final (`detalhes_secoes`, smoke exige ≥1 e nenhuma vazia). Cobertura ignora DrawViewSection (não-DrawViewPart). Símbolo AWS solda = `DrawWeldSymbol` GUI-only → segue callout texto. Commit f912e98. [[06-open-threads#T6]].

## D41 — 2026-07-10 — Wiring de módulos órfãos: calha + sapata de divisa (fase 6.a)
Auditoria achou 5 módulos homologados ÓRFÃOS (calc existia, pipeline não alcançava):
neve, calhas, sapata_divisa, alma_variavel, tesoura. Fase 6.a ligou os 2 menores:
`cobertura.chuva_I_mm_h` (NBR 10844) → `calhas.dimensiona` da geometria;
`fundacao.divisa` {dist_divisa} → `sapata_divisa.dimensiona_divisa` (P do envelope,
Alonso). Gates não bloqueiam (default/None). Memorial METODOS 13/11g. `neve` NÃO
wired (usuário não pediu — região sem neve). Commit 5fd4003. [[03-phases]].

## D42 — 2026-07-10 — Pórtico de alma variável (tapered): rigidez variável + loft (fase 6.b)
`estrutura.tipo_portico`=alma_variavel → rafter com seção por segmento
(`galpao_portico._chain_var` + `alma_variavel.secao_tapered`, funda no joelho→rasa
na cumeeira). `frame2d.add_element` já aceitava I/A por elemento. `configurar(tapered=)`
usa **sentinela `_UNSET`** (tapered=None RESETA → prismático byte-idêntico, crítico p/
não-regressão em processo compartilhado). 3D: `build_galpao.tapered_rafter` = loft
`Part.makeLoft` de 2 perfis I. Seção do JOELHO governa (verif. por segmento = FLAG).
Commit 21d9941. [[03-phases]].

## D43 — 2026-07-10 — Pórtico treliçado (tesoura): cálculo NOVO (método dos nós) + 3D (fase 6.c)
`tesoura.py` era SÓ geometria (nós+barras isostática); fase criou o cálculo.
`resolve_trelica` = método dos nós (equilíbrio nodal, sistema `2j×(b+3)`, numpy);
N>0 tração; banzo inf traciona/sup comprime. `verifica_tesoura` = combos grav+vento,
barras por NBR 8800 (tração escoamento / compressão chi·Q·A·fy via check_nbr8800).
**numpy LAZY** (só no solver) → `gera_trelica` importável no build sem numpy;
geometria da treliça **replicada numpy-free** no build_galpao (self-contained).
`_desenha_tesoura` barras biapoiadas no topo dos pilares, SEM joelho/cumeeira
(rotulada). Sucção de vento = INPUT. Commit 820b0e0. [[03-phases]].

## D44 — 2026-07-11 — Homologação dos 6 pareceres sênior (itens 28–33) + correções
Sessão fechou os 6 REVISAO-*.md pendentes (índice 28–33). **Padrão-chave: 3 dos "erros graves" NÃO procediam** — refutados com prova de bancada, sênior retratou-se (mesmo padrão [[#D6]]). **Regra reforçada: verificar cada alegação contra código+PDF, nunca aceitar/rejeitar cego.**
- **28 gusset** ([[#D37]]): 4 correções conceituais (AISC DG29): (a) `L_livre` desacoplado de `Lc`, `Kl=K·L_livre` (Thornton), `K=0,65` 2 bordas; (b) barra redonda `w0=d_barra` (não 0, singularidade); (c) ruptura da seção líquida `Ae·fu/γa2` (Ct, dh reusa `ligacoes._diam_furo`); (d) `__main__` imprime caso real Ø20 (bw=135,5/Nt=369,5). ✅
- **29 console** ([[#D37]]): parecer-1 REPROVOU por erro de estática do PRÓPRIO parecer (SRSS de colineares errado) → sênior mea-culpa. Correções: colineares HORIZONTAIS (f_h+f_bV+f_bH) somam algébrico, SRSS só com f_v; **2 cordões** (A_w=2L, Sw=L²/3); momento de Ht `Mz=Ht·(L/2+h_trilho)`; **chapa em balanço** (flexão na raiz M_Sd=Rv·ecc + cisalhamento 5.4); comprimento efetivo `L_ef=L−2·perna` (crateras). ✅ APROVADO COM LOUVOR.
- **30 fundação profunda** ([[#D38]]): (Q2) `carga_estaca_grupo` flexo-compressão N/n±Mx·yi/Σyi²±My·xi/Σxi², `offsets_grupo`, wire M_base do envelope; bloco 1-2 estacas não resiste (S=0)→tirantes de baldrame; (Q3) `coroa=max(150,D/2)`; (Q3b) `altura_bloco_rigido` do ângulo da biela **tan θ≥1,0** (não 1,2·D); (Q4) pedestal do modelo (cota arrasamento); (Q5) **baldrame transversal p/ n≤2** (NBR 6122 travamento 2 direções); (Q6) baldrame de face a face do pedestal (sem dupla contagem). **Q1 FS: gate condicional** — default 3,0, `FS<3,0` bloqueia sem `fundacao.estaca.prova_de_carga=True` (encoda a condicional que sênior+literatura concordam, sem citar PDF 6122 escaneado); `validar()` devolve `avisos` (auditoria). Build: 0 interferências. ✅
- **31 ponte 8400** ([[#D39]]): Q2 (min(Vh,1.5)) e Q3 (B10=8e6) **já estavam** no nbr8400.py. **Q1 H_long DEFENDIDO** — `R_roda_max=R_trilho_max/n_rodas_lado` é reação POR RODA (partilha igual), então `frac_long·R_roda_max·n_motoras=frac_long·ΣR_motoras≤frac_long·R_trilho_max`; não é superposição. Teto provado no selftest; docstring de `cargas_de_roda` explicita a partilha. ✅
- **32 alma variável** ([[#D42]]): parecer-1 Q2 (seção do joelho NÃO governa)→**verificação por segmento**. parecer-2 ponto-1 (array invertido) REFUTADO por 2 provas: frame2d bi-engastado EI 8:1 (rígido atrai mais M) + swap do taper (M segue rigidez). pontos 2/3 corrigidos: **FLT vira check de TRECHO** (member-level, seção mais funda, AISC DG25/Anexo H; FLA/FLM/flexo locais com Lb→0 no verifica), **Lb dinâmico pela mesa comprimida** (terças gravidade / mãos-francesas sucção). `props_I` completa; `analyse()` devolve `rafter_segmentos`; B2 global amplifica M. ✅
- **33 tesoura** ([[#D43]]): BLOQUEADO por Q5. **banzo superior RETO em duas águas** `y=(2h/L)·min(x,L−x)` (não parábola/bowstring) em `gera_trelica`+build `_trelica_geom` → terças nos nós → método dos nós válido; **tração ruptura líquida** `_nt_rd` min(escoam, Ct·(A−furos)·fu/γa2); **compressão 2 eixos** `_nc_rd` (no plano L/rx; fora Lb_y/ry); tributária inclinada; **guard n_paineis PAR** (raise em gera_trelica + bloqueio em validar; ímpar→cumeeira no meio da barra→flexão). Solver aprovado. ✅
Commits 718bbe8→35cda72 (branch `revisao/homologacao-12-modulos`). **REVISAO-INDICE.md: itens 1–33 todos ✅ HOMOLOGADO.**

## D45 — 2026-07-11 — Backlog do parecer 6.b esgotado (fases 6.4–6.8) + revisão itens 34–38
Sessão fechou os 4 itens de backlog do parecer da alma variável + 1 desdobramento,
todos por leitura **verbatim** do PDF. **Padrão-chave repetido: 8 alegações de "erro
grave" refutadas com a fonte primária; 1 bug real acolhido.** Enviar **imagem da
página do PDF** (via `SendUserFile`) encerrou disputas de citação.
- **6.4 coluna tapered** ([[03-phases]]): estende `secao_tapered` à COLUNA (base rasa
  `h_col_base`→joelho fundo `h_joelho`); `_chain_var` na coluna, `coluna_segmentos` no
  envelope; verificação por segmento + FLT member-level. **Parecer 1:** (2) add
  **compressão global Anexo J.3** (seção de MENOR altura + H total; a por-segmento com
  `L_seg` não capturava flambagem global) → `util_col_global`; (3) teste de
  continuidade → igualdade **estrita no nó** (`isclose 1e-9`, era ponto-médio tol 20%);
  (1/4a/4b defendidos). **Parecer 2 REFUTADO com PDF pág.151:** sênior alegou "Anexo J
  = forças concentradas / citação fabricada" — **falso**, Anexo J = "Requisitos para
  barras de seção variável" (J.3 compressão, J.4 FLT); os fenômenos que ele citou são
  §5.7 (corpo principal). Sênior retratou-se. Commits `1baef85`→`16cec73`. ✅
- **6.5 zona de painel do joelho** ([[03-phases]]): módulo novo `zona_painel.py` (NBR
  8800 **§5.7.7** cisalhamento do painel + estados locais **§5.7.2/3/4/6** + doubler
  §5.7.7.2). Nó rígido (prismático+alma var); tesoura pula. **Parecer 1:** (A)
  `FSd=M/dm−V_col` (equilíbrio nodal); (C) add **enrugamento §5.7.4** (coef **0,66/0,33**
  verbatim, NÃO 0,80/0,40 do AISC que o sênior pediu); (D) esbeltez do doubler por
  **§5.4.3** `t≥dc/λp` (não a fórmula imperial `hw/418√fy` do AISC) → `max(t_força,
  t_esbeltez)`. **Parecer 2 REFUTADO com imagens do PDF** (pág.68 §5.7.4.2=0,66/0,33;
  pág.67 §5.7.3.2 já completa no código). Doubler = `CONEX_JOELHO_*_DOUBLER_L/R` (só
  quando exigido; prefixo CONEX exclui da interferência). Commits `a4b336a`→`082319b`. ✅
- **6.6 FLT de mísula (Anexo J)** ([[03-phases]]): `flt_misula.py` substitui o método
  conservador (seção mais funda + Cb=1,0 + M_max) pelo **Anexo J**: λ da seção de MAIOR
  altura (**J.4.2**), `Cb` racional (**§5.4.2.3a**, Rm=1, teto 3,0, balanço→1,0),
  demanda na seção de **max M/Wx** (**J.4.1**). **NÃO usa fator γ** (AISC DG25, não
  normativo na NBR). Efeito só quando `Lb>Lp` (senão FLT no platô plástico). Rafter+coluna
  wired. Aprovado integralmente. Commit `caa5cfc`. ✅
- **6.7 sucção vento→tesoura** ([[03-phases]]): `w_vento` auto-acoplado da NBR 6123
  (`min(net cobertura)·q·bay`, uplift<0) em vez de INPUT manual; override honrado.
  **BUG REAL do parecer acolhido:** combinação de uplift `1,4·w_vento+0,9·(−w_grav)`
  invertia a gravidade (somava ao uplift) → corrigido p/ `1,4·w_vento+0,9·w_dead`
  (vetores opostos, convenção do solver `w>0`=baixo). **Bônus:** `w_dead` exclui a
  sobrecarga Q (NBR 8681: variável não estabiliza uplift). Validado: banzo inf
  reverte tração→compressão sob sucção. Commits `0d67ffc`→`3c5b1d6`. ✅
- **6.8 alma esbelta (Anexo H)** ([[03-phases]]): `alma_esbelta.py` — quando
  `h/tw>5,70√(E/fy)`, `momento_resistente` **despacha** ao Anexo H (Wxc+`kpg`, não
  Zx/Mpl) em vez de abortar com ValueError; compacta/semicompacta→Anexo G intocado.
  `kpg=1−ar/(1200+300ar)(hc/tw−5,70√(E/fy))≤1`; `kc=4/√(h/tw)∈[0,35;0,76]` (F.2);
  FLT com trava no platô; FLM sem Cb. **Parecer REFUTADO** (FLM inelástico + trava do
  Cb "omitidos") — já estavam no código; markdown abreviava. +testes de trava. Sênior
  mea-culpa. Commit `cfdbb03`→`a55a1fe`. ✅
**REVISAO-INDICE.md: itens 1–38 todos ✅ HOMOLOGADO.** Backlog do parecer 6.b esgotado.

## D46 — 2026-07-12/13 — Backlog balde 2 (fases 6.9–6.12) + pareceres itens 39–42
4 dívidas técnicas do parecer 6.b fechadas por código + validação, todas homologadas
pelo sênior. **25 módulos matemáticos.** Commits `6e3551f`→`a18b524`.

- **6.9 / item 39 — `tensao_ponto.py` (interação M-V no joelho, NBR 8800 §5.5.2.3, pág
  57 verbatim).** Verificação por TENSÕES da teoria da elasticidade: σ (fibra extrema
  + junção mesa-alma) e τ (junção, `Qf` real da mesa, não `V/Aw`); alíneas a–d
  SEPARADAS (a NBR **não** tem von Mises combinado — von Mises entra só suplementar,
  flag `base_vm`). Wired na coluna tapered de alma esbelta (`ae.e_esbelta`), entra no
  envelope `interacao_max_col`. Parecer: **0 bug** (σ/τ/Qf/von Mises "milimetricamente
  corretos"); 3 premissas documentadas (χn=1,0 coberta pelos checks paralelos; cos²θ
  desprezível p/ θ≈2,6°; von Mises suplementar).
- **6.10 / item 40 — `cortante_tapered.py` (cortante da alma com mesas inclinadas,
  EQUILÍBRIO, NÃO-NBR).** `V_alma=V−(M/h)(dh/dx)`; Anexo J (J.1–J.4) não trata cortante
  (J.1.2→§5.4.3). Adverso SEMPRE contado; alívio favorável OPT-IN
  (`creditar_cortante_mesa_inclinada`, default conservador). **BUG DE SEGURANÇA acolhido
  (parecer):** braço `h_m` subestimava o caso adverso → braço **assimétrico**: `h_0=h_m−tf`
  no adverso (seguro), `h_m` no favorável (conservador). Galpão é haunch (favorável) →
  sem regressão.
- **6.11 / item 41 — vento por zona na tesoura (`tesoura.py`+`vento_nbr6123.py`, NBR
  6123 Tabela 5).** Cada água seu Cpe simultâneo (barlavento EF / sotavento GH) em vez
  de `min` uniforme (estado fictício). **CRÍTICO acolhido (parecer):** faltava o **vento
  a 0° (longitudinal)** — as 2 águas na MESMA zona (EG) → uplift SIMÉTRICO, pode
  governar; sem ele o refino REMOVIA carga real (a "economia" 1,04→0,96 era artefato de
  envelope incompleto). Adicionado `cpe_telhado_longitudinal` (EG/FH verbatim pág 15) +
  envelope 90°+0°. +fixes: cumeeira = média `(w_barl+w_sot)/2`; `_gamma_g_dead` 0,9
  (sucção)/1,4 (pressão). Cpi refutado como bug (mesmo Cpi p/ as 2 águas por
  monotonicidade `argmin(Cpe−Cpi)=max Cpi`) + hardening par-fixo. u honesto = **0,928**.
- **6.12 / item 42 — `dg25_ltb.py` (cross-check AISC DG25 §5.4.3, VALIDAÇÃO informativa,
  NÃO dimensiona).** `M_eLTB=F_eLTB·Sxc` (F4-5, seção do MEIO) vs `Mcr` NBR Anexo J
  (seção FUNDA J.4.2). Base do DG25 lida por IMAGEM (texto do PDF corrompido; PDF que o
  usuário colocou no corpus destravou a dívida (b)). Prismático converge **0,998**
  (F4-5≡F2, base sã); tapered **DIVERGE 0,54/0,45** = diferença de seção de referência
  (meio×funda), NÃO erro de util (NBR auto-consistente). Parecer: **0 bug**; `rt` usa
  `hc=hw` (não `d`) confirmado; razão 0,544 = efeitos não-lineares combinados `Sx`+`Cw`
  (não `Sx∝h²` puro); Cb cancela por premissa de teste (Cb idêntico dos 2 lados), não
  intrínseco.

**Padrão dos pareceres (itens 39–42):** cada alegação verificada contra código + PDF.
**2 bugs reais acolhidos** (braço `h_0` item 40; vento 0° item 41). **1 refutação com
prova** aceita pelo sênior (Cpi). Imagens de PDF (Tabela 5 NBR 6123 pág 15; DG25 pág
60–61) para leitura verbatim. **REVISAO-INDICE.md: itens 1–42 todos ✅ HOMOLOGADO.**

## D47 — 2026-07-13 — Balde 3 (fases 6.13–6.14): dívida (e) + refino DG25
Resíduos NÃO-bug restantes fechados. **Crane NÃO entrou** — já estava 100% homologado
(itens 9 ponte, 29 console, 31 rodas-motoras+8400); o backlog "crane no toolkit" da
memória era estale (`ponte_rolante.py`+`nbr8400.py` existem e integrados). **26 módulos.**

- **6.13 / item 43 — `enrijecedor_painel.py` (enrijecedores transversais da alma, NBR
  8800 §5.4.3.1, pág 50–51 verbatim por imagem).** `kv=5+5/(a/h)²` (senão 5 se `a/h>3`
  ou `a/h>(260/(h/tw))²`); `V_Rd` 3 domínios com `λp/λr=1,10/1,37·√(kv·E/fy)`;
  requisitos §5.4.3.1.3 (b/t≤0,56√(E/fy); `I_st≥a·tw³·j`, `j=[2,5/(a/h)²]−2≥0,5`).
  Fecha o TODO do item 38: `alma_esbelta._valida(sec,a)` **relaxa o cap h/tw≤260** do
  Anexo H quando `a/h≤3` (enrijecido); `Aw/Afc≤10` continua. Wire informativo/opt-in na
  zona de painel (sugere maior `a` que atende `V_Sd`). `a=None`⇒kv=5 byte-idêntico.
- **6.14 / item 44 — DG25 full (`dg25_ltb.py` estendido, pág 58–62 verbatim por imagem).**
  Cb tapered por tensões (5.4-1/5.4-2), `Rpc` (5.4-4/5), `Rpg` (5.4-6/7), `F_L`, `Mn`
  nominal em 3 regiões (5.4-16/17/18) + CFY (5.4-8). Chave: `γ_eLTB·f_r=F_eLTB` ⇒ `f_r`
  cancela; `Mn` depende só de `F_eLTB`/`F_L`/`Fy`/`Rpc`/`Rpg`. `cross_check_capacidade`
  onde **Cb NÃO cancela** (não-linear nas regiões) — vs `cross_check_flt` (item 42,
  elástico, Cb cancela). Achado: prismático capacidade **0,951** (curva inelástica
  White-Kim ancorada em `Rpc·Myc`/`F_L` ≠ interpolação Anexo G ancorada em `Mp`/`ry` →
  ~5%), enquanto o elástico é ≡ 0,998. Ambos INFORMATIVOS — dimensionamento segue NBR.

**REVISAO-INDICE itens 43–44 ✅ HOMOLOGADOS (2026-07-13).** Item 43 **APROVADO COM
LOUVOR:** parecer apontou 3 pts — `a_min→a_max` acolhido (bug de nome); 2 refutados com
PDF (eixo I singelo = plano médio NBR §5.4.3.1.3c p/ ambos, ≠ AISC G2.2; §5.4.3.2 =
tubular ≠ tension field, NBR 8800:2008 sem campo de tração); `ist_singelo` (eixo-face,
conservador) opt-in elogiado. Item 44 **validado (sanity-check):** `γ·f_r=F_eLTB` "mais
elegante"; 5% inelástico = diferença de método (Cb externo NBR × embutido sob raiz
DG25); 3 apontamentos de escopo sem bug (F_L monossim. já coberto pelo ramo 5.4-15 via
`Wxt`; sinais Cb = premissa do chamador; `aw≤10` reflete DG25). Método lido verbatim
(NBR 8800 §5.4.3.1; AISC DG25 §5.4). Não-regressão: `cross_check_flt` intocado;
`a=None`⇒kv=5 idêntico. Ver [[06-open-threads#T11]].

## D48 — 2026-07-13/14 — Balde 4 (fases 6.15–6.19) + 9 correções de parecer
**Módulos novos:** `props_I_mono.py` (perfil I monossimétrico), `forcas_localizadas.py`
(NBR 8800 §5.7 + enrijecedor de apoio), `viga_equilibrio.py` (viga de divisa sobre
estacas). `dg25_ltb` estendido (envelope FLB/TFY/ruptura §5.4.4–7, mono-aware).
`techdraw_exec` ganhou glyph de solda AWS A2.4 headless.

**Correções dos pareceres (cada uma conferida contra PDF/estática antes de aceitar):**
- **rt (5.4-11) usa `hw`, não `hc`** (item 45). O `h` ao quadrado em `rt` é a altura
  LIVRE da alma; `hc` entra só no `aw`. Dupl-sim `hc=hw` ⇒ byte-idêntico; mono era
  +2,3% contra a segurança (FLT). Verbatim DG25 pág 61.
- **kc (5.4-24) usa `hw`, não `hc`** (item 46). Idem — `kc=4/√(h/tw)`, h=alma livre.
  Mono +7,8% contra a segurança. Verbatim DG25 pág 63.
- **Teto de Mp no Rpt (5.4-28) usa `Sxc`, não `Sxt`** (item 46). A eq 5.4-28 imprime
  `Sxt` mas remete a "termos como no Rpc"; o bloco Rpc (DG25 **pág 60**) define
  `Mp=Fy·Zx≤1,6·Fy·Sxc`. Logo `Sxt` = **erratum tipográfico**; AISC 360 F4 tem UMA
  definição de Mp (Sxc). **Rejeitei na 1ª rodada** (verbatim isolado de 5.4-28); o
  sênior insistiu, segui a remissão interna → sênior correto. Lição: quando a eq diz
  "as defined previously", **seguir a remissão** antes de cravar. Só difere quando
  Zx/Sxt>1,6 (teto Sxt clampava Rpt em 1,6).
- **M da viga de equilíbrio = `P·e`, não `R'·e`** (item 48). Estática de corpo rígido:
  corte no centroide do grupo, à direita só atua P no braço e ⇒ M=P·e; `ΔP·(l−e)=P·e`.
  `R'·e` superestimava por `l/(l−e)` → excesso de armadura. Selftest 1216→1050 kN·m.
- **Viga de equilíbrio: +cisalhamento §17.4 + peso próprio + pele** (item 48). V=ΔP
  constante ⇒ verifica biela VRd2 + estribo (reusa `viga_baldrame._verifica_cortante`);
  h itera até passar flexão E biela (subiu 79→102 cm). Peso próprio ~5% na contagem de
  estacas (`FATOR_PP=1,05`, `n_estacas(peso_bloco=)`). Armadura de pele §17.3.5.2.3
  (0,10% Ac,alma/face, teto 5 cm²/m, s≤20cm) para h>60cm.
- **Glyph de solda arrow/other/both (AWS A2.4)** (item 49). Posição do triângulo vs
  linha de referência = lado da junta (abaixo=arrow, acima=other, ambos=espelhado) —
  não pode ser engessado. `lado` lido do dado de fabricação (`cfg[callout]["lado_solda"]`,
  Ask-Do-Not-Invent, default arrow). Perna vertical sempre à esquerda.

**Aceito sem alteração:** inércia `I_par` do enrijecedor (chapa cheia, erro ~0,05%,
A_eff já inclui a faixa colaborante — parecer endossa, FLAG explícito).
**REVISAO-INDICE itens 45, 47, 48 HOMOLOGADOS; 46 e 49 em PARECER.** Ver [[03-phases#FECHADA — Balde 4 (backlog de gaps) fases 6.15–6.19 + homologação 45–49 — 2026-07-13/14]], [[06-open-threads#T12]].

## D49 — 2026-07-15 — Auditoria "Diretrizes Técnicas" (bugs 8.1–8.36) via NotebookLM
Auditoria confrontando o código com as normas via MCP NotebookLM. **36 achados triados:
33 bugs reais corrigidos + 3 falsos positivos.** Ritual: 1 pergunta/bug ao notebook antes
de corrigir; verdito verificado contra citação da norma (não de memória). Commits
`dad7b87`→`741221d`.

**Falsos positivos (sem mudança, confirmados no notebook):**
- **8.9** junta_dilatacao: fatores FCC Report 65 são **aditivos** ("soma algébrica dos
  vários fatores") — `base·(1+Σf)` correto; multiplicar seria não-conservador.
- **8.11** gusset: `L_livre=Lc` como fallback é **conservador** e já documentado (Thornton
  DG29); variáveis já desacopladas.
- **8.14** estabilidade: NBR 8800 **D.2.4** é literal `Vsd=Vnt+Vlt` — cortante NÃO leva B2
  (só M e N). `v=mf_nt+mf_lt` correto.

**Correções por tema:**
- **Concreto/fundação** (6118/6122): 8.1 cortante da viga alavanca (biela/estribo, itera
  h); 8.10 `b_viga=b_col_paralela`; 8.29 `sapata_ok` inclui `OK_B` (flexão/compr.diag/
  punção); 8.4/8.18/8.31 travamento transversal + baldrame long. + estaca no quadro.
- **Combinações** (8681): 8.2 Q não estabiliza uplift na `Gfav` (γq=0). γG favorável=**1,0**
  (NBR 8800 Tab.1, peso próprio metálico); combos são `C1_uplift_W*`/`C1_Gfav_W*`.
- **Aço** (8800): 8.3 `abs()` na flexo-tração 5.5.1.2; 8.15 fencepost `Lb_terca=L_raft/
  n_terca` (era `/(n+1)`); 8.16/8.22 travas B2/B1 (`denom≤0→inf`, `≥1,0`; MAES inválido
  se >1,40 rig. original / >1,55 reduzida); 8.17 console `(|M|+|Mz|)/M_Rd` (flexão reta,
  mesmo eixo forte); 8.21 `SEC_COLS_EXTERNO` preserva `I` por-coluna no B1 (frame de
  `galpao_portico` **e** `SEC_COLS_PORTICO` leva a rigidez real por coluna ao frame →
análise 2D + B2 (P-Δ) per-coluna, não só o B1 (resolvido 2026-07-15; ref 1 vão
inalterada; selftest: coluna central rígida atrai mais momento).
- **Física/unidade**: 8.5 escada peso próprio `(…)/2` (era `×largura` extra); 8.6 `delta`
  morto removido; 8.7 vibração 3 Hz **sempre** (L.1.2, sem isenção L≤4m); 8.12
  `Nsd_tirante` da geometria (componente tangencial acumulada `(1,25G+1,5Q)·(ridge−eave)·
  bay/(n_tir+1)`; 8,0 kN vira piso); 8.13 fogo intumescente = **método incremental Anexo
  B** (espessura via `λp/tp` e `ξ`; `λp` calibrado vs cartas de cobertura); 8.34 fogo
  `util=θ/θ_cr` (não °C absoluto; `θ_cr=550 °C` default, A CONFIRMAR).
- **Hidráulica/vento**: 8.8 calha `h_elevacao` (NBR 10844, parede vertical +50%); 8.20
  calha + divisa no quadro.
- **Observabilidade do QUADRO** (8.18–8.20, 8.23–8.36): verificações calculadas mas
  ausentes do resumo passavam "todos ATENDEM". Helpers `_uok`/`_uokd` forçam `util>1`
  quando o OK reprova com `util≤1` (base/interação, sapata/punção, viga-rolamento/fadiga).
  Ligados: tesoura, telha, contravento/gusset, console, zona de painel, sismo θ, junta,
  terreno. Corrigido `0 if ok else None` (mandava FALHA→None, pulada). `terreno.py`
  deixou de ser órfão (import + gate `params["terreno"]`); `rodar_projeto` exporta os
  novos subsistemas ao TechDraw (`resultados`+`estados`). Ver [[01-architecture#Quadro de
  verificações (pass/fail consolidado)]].

**Método/infra:** MCP NotebookLM `bf7feaa3-…`; git instalado via winget. **Laudo
`review_completo.md` consolidado aqui e removido — correções aplicadas:** nomes de arquivo
errados (`viga_ponte.py`→`ponte_rolante.py`; `placa_base.py`→`base_chumbador.py`); γG
uplift **1,00** (não 0,90); combos `C1_uplift_*` (não `C2_`); "sem regressão" depende do
smoke com pycufsm ([[06-open-threads#T13]]).

## D50 — 2026-07-16 — Turnkey: entrada única + orquestrador + escopo/ART + validação
Produtização "eu digo → ele entrega" na branch `revisao/homologacao-12-modulos` (PR #12).
Novos módulos: **`wizard.py`** (formulário guiado → `ProjetoSpec`; `_checa_faixa` valida
faixa por campo, `_avisos_coerencia` cruza campos, `PRESETS` 3 modelos; commit `09fe54f`);
**`rodar_projeto.rodar_tudo(spec)`** (entrada ÚNICA portável: calc + memorial PDF + 3D +
pranchas + `RELATORIO-CONSOLIDADO.txt`; degrada com graça sem FreeCAD); **veredito GLOBAL**
`res["atende_global"]`/`res["falhas_verificacao"]` exposto pelo `rodar_galpao` (antes o
`res["atende"]` só refletia o pórtico e escondia sub-gates reprovando); **`escopo.py`**
(envelope coberto + detecção fora-de-escopo — fogo global, sismo modal, fadiga ponte,
>2 águas, neve assimétrica — + carimbo ART/CREA); **`validacao.py`** (7 benchmarks
independentes: forma fechada, equilíbrio V/H, multi-vão, base engastada, MAES B1, vento;
+ **validação de SISTEMA `validacao_referencia`** reproduz o galpão do **manual CBCA "Galpões
para usos gerais" Cap.2** (pórtico W310x38,7, vão 15 m, base rotulada) sob Fd1 (1,25G+1,5Q,
sem vento) → reações/momento **<1%**: V 42,94/42,77, H 13,68/13,67, M 82,06/82,56).
Dados do CBCA extraídos do NotebookLM. Porquê: fecha a experiência turnkey + dá selo de
confiança. Commits `65d05a7`→`c86576d`. Ver [[06-open-threads#T14]].

## D51 — 2026-07-16 — Escopo ampliado (neve, multi-vão) + dossiê PDF + varredura visual
**Neve** (EN 1991-1-3, `neve.py` integrado): gate `neve` opcional no ProjetoSpec (`sk`
regional Ask-Do-Not-Invent); `rodar_galpao` usa o caso SIMÉTRICO como `Q_efetivo=max(Q,
neve_sim)` no pórtico; ASSIMÉTRICO calculado, `gate5-neve.txt`, sinalizado (fronteira de
escopo). **Multi-vão** exposto via `geometria.spans` (motor `galpao_portico`/`rodar_galpao`
e build 3D `build_galpao` JÁ suportavam; faltava ProjetoSpec/wizard `n_vaos` + mappers).
Verificado: 2 vãos → 3 colunas, **0 interferências**, pórtico/render 3D corretos.
**Dossiê PDF único** (`dossie.py`, PyMuPDF/fitz): mescla capa+relatório+memorial+pranchas;
`rodar_tudo` passo 5. **Prancha PE15_DET_BLOCO** de coroamento (só fundação profunda;
dims do bbox real do bloco, inclui coroa). **Varredura visual completa** das pranchas
(tesoura + estaca + ponte + alma_var + multi-vão + renders 3D): **6 defeitos de layout
corrigidos** — overlap notas×tabela PE09 (`_pos_notas`), numeração carimbo≠arquivo
(`_codigo_prancha` usa código de tipo do nome), overflow de título (`_cap_titulo` tira
"DETALHE - " + abrevia), callout terça cru (`_fmt_terca`), terminologia "sapatas" em
fundação profunda (`_quadro_fundacao`), corte da cumeeira sobre notas (`_pos_corte_ligacao`).
**Render 3D headless**: precisa `mw.showNormal()` + forçar `Visibility=True` + `ViewFit`
(senão saveImage sai BRANCO — GL offscreen). Suíte completa **256 passed**; test_validacao
17 puros. Commits `4f8696a`, `2f5af9b`, `714cbda`, `003f391` + fixes de pranchas. Ver [[06-open-threads#T14]].

## D52 — fix de sinal da UDL no frame2d (2026-07-17, BUG-RAIZ, contra-segurança)
`frame2d.solve()` aplicava a carga nodal equivalente da UDL com `F -= F_eq` (deveria `+=`;
`_fef_local` já retorna a carga equivalente = -{engastamento}) e o esforço de barra usava
`+ fef` (deveria `- fef`). Os DOIS erros se cancelavam em MAGNITUDE → selftests (asserts em
|valor|) e CBCA (compara módulo) nunca pegaram, mas **toda carga distribuída (gravidade)
entrava invertida**: deslocamento p/ cima, reação de base negativa → a sapata recebia a
gravidade como **uplift** → footings superdimensionadas (ref 2,5×3,0×0,9 → 1,5×2,0×0,6 m) E
uplift de vento mascarado. **Fix:** `F +=` na montagem; `f = k·d − fef` no esforço de barra.
Coluna/viga (envelope de |M|,|N|) inalteradas; CBCA e 7 benchmarks seguem verdes. Regressão
`tests/test_frame2d_sinal.py`. **Alternativa rejeitada:** negar N só na fronteira fundação
(quebra a consistência UDL×nodal nas combos G+W). Ver [[06-open-threads#T15]].

## D53 — vento correto: uplift, Cpe e Cpi por abertura (2026-07-17)
- **§2A** `galpao_portico._wind_unico` (1 vão) aplicava o telhado p/ BAIXO com `q` cru **sem
  Cpe** → anulava o arrancamento. Reescrito com pressão líquida `(Cpe−Cpi)·q` (Tab.4 paredes,
  Tab.5 telhado), = modelo do `_wind_multi`. Telhado a baixa inclinação vira sucção → **uplift
  real** (referência passa a detectar tração de base). Depende de [[04-decisions#D52]].
- **§2B** peso de alvenaria era somado na coluna de aço (conservador). Agora `cargas_parede`
  separa: leve → UDL na coluna; alvenaria autoportante → fundação (envelope, compressão +
  estabiliza uplift) + baldrame `q_parede`. Perfil de coluna igual telha×alvenaria.
- **`abertura_dominante`** (NBR 6123 6.2.5): `vento.cpi_por_abertura` — vedada usa Cpi
  +0,20/−0,30 (era sempre portão ±0,8/−0,6). Fio spec→mapper→pórtico.

## D54 — campos do wizard que eram coletados e IGNORADOS (2026-07-17)
Padrão recorrente: mapper (`to_rodar_params`/`to_build_kwargs`) não repassava o campo →
"dado morto". Corrigidos: (a) **peso de parede** (D53 §2B); (b) **janela lateral** (wizard
`(L,H)` × build faixa `(z_base,z_topo)` — quebrava o 3D; `_janela_band` converte com peitoril);
(c) **legislação/terreno** (mapper não passava `params[terreno]` + `analisa_terreno` exigia
polígono → gate SEMPRE pulado; agora mapeado + modo **área-only** TO/CA/TP, recuos pendentes
sem o lote); (d) **`cargas.tapamento`** morto/redundante removido do wizard. Testes
`test_carga_parede`, `test_aberturas_janela`, `test_terreno_mapper`.

## D55 — triagem da revisão externa de pipeline (2026-07-17)
Revisão (fuzzing Monte Carlo, ex-wiki/07) tinha acertos e **falsos positivos** — cada
alegação conferida no código. **REAIS corrigidos:** E IndexError na reprovação
(`["HEA200"]*(N_VAOS+1)`), C KeyError `Hvr` (`setdefault`), H cumeeira no global `RIDGE_Y`
estático (passa `ry/rh` por vão; verificado 3D y=10000), D solo SPT sem validação
(`estaca_profunda.TIPOS_SOLO` + gate), J `reportlab`/`pymupdf` ausentes, K rótulo de vão
desigual no dossiê. **FALSOS refutados:** F/G (build usa `SPAN` LOCAL correto — build de 20 m
0 interferências). Testes `test_crashes_wiki07`.

## D56 — features novas: bloco de fundação + telhado de 1 água (2026-07-17)
Normas extraídas verbatim do NotebookLM (memória `normas-bloco-shed`).
- **Bloco de fundação** (`fund_tipo='bloco'`): NBR 6122:2022 **7.8.2** — concreto simples,
  altura por **β≥60°** (`h≥tan60·(dim−pilar)/2`), sem armadura; σt≈fck/25≤0,8 MPa (Alonso).
  `fundacao_sapata.dimensiona_bloco_env` reusa o bearing da sapata; 3D = bloco alto.
- **Telhado de 1 água (shed)**, só 1 vão: pórtico assimétrico (2 colunas de alturas diferentes,
  1 rafter, sem cumeeira) em `_frame_shed`; vento **NBR 6123 Tabela 6** (`cpe_telhado_1agua`,
  metades H/L, sucção → uplift); build 3D `AGUAS==1` (rafter_z uma água), **0 interferências**.
  Multi-vão shed (dente-de-serra) **bloqueado**. Multi-vão heterogêneo: cumeeira por vão
  (`_ridge_h(i)`, 2D=3D). Testes `test_bloco_fundacao`, `test_shed`, `test_multivao_hetero`.

## D57 — VALIDAÇÃO DE SISTEMA contra livros resolvidos (2026-07-17)
Fecha o 2º caso-referência (pendência de [[06-open-threads#T14]]). Exemplos reais (NotebookLM,
Alonso "Exercícios de Fundações" + Bellei "Edifícios de Múltiplos Andares em Aço"):
sapata σ_solo **0,5%** e B×L **exato** (2,50×2,50); bloco h/β/σt **exato** (β=60°); pilar
NBR 8800 N_Rd **0,1%** (2503→2506 kN); vento q **exato** (0,787 kN/m²). Confirma a cadeia do
fix de sinal (N>0=compressão chega correto na fundação). `tests/test_validacao_alonso.py`;
memória `validacao-sistema-alonso`.

## D58 — validação de coerência no GATE, não só no wizard (2026-07-18)
Caça sessão 14 achou que `projeto_spec.validar` só checava PENDENTE/enums, não coerência física.
O caminho SPEC-DIRETO (`carregar_spec`/JSON) CERTIFICAVA lixo como `atende_global=True` (span<0,
ridge≤eave, slope≤0, V0=0, sigma_solo=5000→fundação subdimensionada) ou crashava (eave=0, vao_ponte=0).
As faixas duras do wizard (`_checa_faixa` banda "erro") só rodavam no terminal → assimetria
contra-segurança. **Decisão:** mover TODA a coerência/plausibilidade p/ `validar` (o gate que ambos
os caminhos atravessam). Cobre geometria, física, ponte, tesoura, fundação (fck/fyk/mu/gamma_f),
vento-enums (cat I-V, classe A/B/C), estaca (tipo AokiVelloso, D/L, SPT), baldrame, cargas, terreno,
opcionais. Bloqueia (não avisa) valores impossíveis. `tests/test_validacao_coerencia.py` (49).
PRs #13/#16/#18. Ver [[06-open-threads#T16]].

## D59 — mão-francesa: geometria 3D estava no plano ERRADO (2026-07-18)
A mão-francesa (flange brace) deve travar a mesa INFERIOR do rafter LATERALMENTE (fora do plano do
pórtico) sob sucção — o movimento da FLT (Bellei Fig 8.16/8.17, confirmado NotebookLM). O desenho
em `build_galpao` a punha em X CONSTANTE (plano do pórtico), apontando p/ baixo sem tocar a terça:
não travava nada. **Cálculo (`mao_francesa.py`) sempre correto** (inversão da interação); só a
geometria 3D errada. **Decisão:** extrair a geometria p/ módulo PURO `mao_francesa_geom.py`
(mesa inf → terça, offset LONGITUDINAL X, ~45°), testável sem FreeCAD. Guarda permanente
`test_mao_francesa_geom` exige `dx=|p2.x−p1.x|>0`. Executivo 2D projeta/recorta o 3D → herda o fix.
PR #15.

## D60 — tesoura: banzo INFERIOR sob uplift + Lb_y_inf (2026-07-18)
Sob uplift o banzo inferior COMPRIME e só trava fora do plano onde há mão-francesa (Bellei Fig 5.9).
`verifica_tesoura` usava `Lbar` (1 painel) = assume TODO nó travado (OTIMISTA, possível
não-conservador). **Decisão:** expor `cfg["Lb_y_inf"]` (espaçamento REAL dos travamentos);
back-compat (`None`=comportamento antigo) + o relatório DECLARA a premissa. Demo: `Lb_y_inf=8m` →
util do banzo inferior 0,52→3,18. `test_tesoura_lby_inf`. PR #19.

## D61 — z do vento < cumeeira: aviso, não bloqueio (2026-07-18)
`to_rodar_params` usa `v.get("z", ridge)`; spec-direto pode setar z<ridge (S2 cresce com z →
sub-representa o vento, não-conservador). **Decisão:** AVISO em `validar` (não bloqueia; vai p/ a
memória de cálculo/ART) quando z<ridge−0,05. Wizard sempre usa z=ridge. `_CFG` global do vento
NÃO é bug (`rodar_galpao:140` faz `vento.reset()` por projeto). PR #19.

## D62 — ponte/fadiga Anexo K verificado; escopo K.4b (2026-07-18)
NotebookLM confirmou verbatim vs NBR 8800: fadiga K.4a `σ_SR=(327·Cf/N)^0,333` (327=6,89476³ ksi→MPa),
toda a Tabela K.1 (Cf/σ_TH A..E'), B.7.3.4 (vertical+impacto + 50% horizontal). **Nada a mudar no
motor da ponte.** Exceção K.4b (parafuso/barra rosqueada: Cf=E'(3,9e8) mas σ_TH=D(48)) é cláusula
separada, fora do escopo da viga de rolamento — não coberta, documentada. Gap era só coerência de
entrada (ver [[#D58]]). PR #16.

## D63 — estaca: resistência de ponta na profundidade L, não na última camada (2026-07-19)
Revisão de `estaca_profunda`. Os 3 métodos (Aoki-Velloso/Décourt-Quaresma/Teixeira) usavam
`perfil[-1]` (ÚLTIMA camada do SPT) para a resistência de PONTA (N + tipo de solo), ignorando
a profundidade da ponta L. Perfil descendo ALÉM de L com camada mais forte (areia densa sob
argila mole) → ponta "via" a camada de baixo → R_ponta/P_adm SUPERESTIMADOS → estaca
subdimensionada CERTIFICADA (contra-segurança). Demo: D=0,40 L=5m (ponta argila N=3) dava
R_ponta=2872 kN (N=40 da areia a 15m) vs 43 kN correto. **Fix:** `_camada_na_ponta(perfil, L)`
(camada que contém L; boundary→camada de cima; L além→última) nos 3 métodos. `N_ponta`
explícito ainda prevalece. `test_estaca_ponta` (5). PR #23. Ver [[06-open-threads#T16]].

## D64 — executivo sempre encerra o freecad.exe (2026-07-19)
`rodar_executivo` só matava o subprocesso NO TIMEOUT, via `proc.kill()` (TerminateProcess) —
que NÃO derruba freecad.exe TRAVADO nem filhos. No sucesso nunca matava. → freecad.exe pendurado
segurando a porta 9875 (os zumbis que bloquearam o bridge). **Fix:** bloco `finally` +
`_matar_processo_freecad` (escalona `kill()`→`taskkill /F /T`→**WMI Terminate**, único que derruba
travado). Best-effort. `test_executivo_cleanup` (3). PR #22. Bridge sobe sozinho com a porta livre
(o "não autostart" era contaminação dos zumbis).

## D65 — build_galpao shipado como fonte precisa do sys.path (2026-07-19)
`build_galpao` é ENVIADO como texto p/ dentro do FreeCAD (não importado); imports de módulos
IRMÃOS (`mao_francesa_geom`, extraído em [[#D59]]) só resolvem com o dir no `sys.path` do FreeCAD.
Sem isso: ModuleNotFoundError, 3D success=False. Regressão do PR #15 invisível pq testes `build`
são deselecionados no CI; achada na verificação VISUAL (bridge). **Fix:** helper único
`rodar_projeto._ship_build_src` (montar_modelo + smoke + 5 build-tests fase3/64/65/6b/6c).
`test_ship_build_src` (3) guarda sem bridge. PRs #20, #24.

## D66 — PE07 crop do joelho menor (2026-07-19)
Varredura visual do executivo (bridge). O crop do nó do joelho era cubo 3×3×3 m (KW=1500) →
pegava ~1,5 m de coluna abaixo do beiral → recorte alto-e-fino → `_fit_escala` reduzia a escala
(1:10) e a ligação renderizava minúscula, ao contrário de base/cumeeira (1:5). **Fix:** janela
vertical menor/assimétrica (0,7 m abaixo, 1,0 m acima do beiral). 1:10→1:5, legível. PR #25.
Cosmético. `techdraw_exec` ~956.

## D67 — Sessão 16: mão-francesa completa + 4 varreduras sistemáticas (2026-07-21, PRs #40–#44)
Tema: **"o cálculo/modelo decide, o entregável não vê"**. 8+ defeitos, todos na periferia; motor OK.

**Mão-francesa (contenção da mesa inf., #41–#44):**
- **Pontas p/ fora** (#41): `sgn` alternava o lado longitudinal por água CEGO → no pórtico de
  oitão o braço mirava X<0 (fora do galpão), 4/24 a 361,8 mm da terça, sem travar nada. Fix em
  `mao_francesa_geom.segmentos`: nas extremidades aponta p/ DENTRO; interior mantém alternância.
- **Peça errada** (#43–#44): era barra redonda Ø16 (**tirante**, só tração); Fakury Fig. 5.22 exige
  a contenção **como de tração E compressão**. KL/r=233>200 (5.3.4.1) e N=19,7 kN > Nc,Rd=5,8 kN.
  Novo `contencao_lateral.py`: **NBR 8800 4.11.3.4** (NODAL: `Fbr=0,02·Msd·Cd/h0`, `Sbr=10·Msd·Cd·γr/
  (Lbb·h0)`, γr=1,35 — CUIDADO: 4.11.3.3 relativa usa 0,008 e 4, 2,5× menor) + **5.3.2** (Nc,Rd)
  + **E.1.4.2** (esbeltez equivalente da cantoneira ligada por 1 aba: `72+0,75·L/rx1` até 80, senão
  `32+1,25·L/rx1`; rx1 = eixo ∥ à aba). **E.1.4 é MAIS conservador** em braço curto (o termo 72·rx1
  embute a excentricidade) — eu havia registrado o inverso na memória; só corrigi MEDINDO.
- **Cantoneira do engenheiro:** `estrutura.mao_francesa={b_mm,t_mm}` (marcada `_a_confirmar`).
  Propriedades por **forma fechada** `perfis.cantoneira` (A=t(2b−t), I_min=Ix−|Ixy|, r_min), fillet
  desprezado (conservador), validada por **integração de polígono (Green) a 1e-9** — sem inventar
  catálogo (evita o erro "AR300"). Qs: Tab. F.1 **Grupo 3** (0,45√(E/fy)) — não "Grupo 2" (numeração
  do livro Fakury). Mesmo (b,t) vai p/ 3D (`l_member`) e gate. **Amostra L50x50x5 → u=0,59 → ATENDE.**

**4 varreduras (padrão: onde há 2 descrições da mesma coisa, uma envelhece):**
1. **Interpenetração de conexões** (#42) — `checa_interferencia` EXCLUI conexões (ponto cego).
   Medir volume comum peça-a-peça: porca de nível 100% no pedestal (gap de graute declarado
   `GROUT_GAP=30` mas não realizado); 2 esticadores com bbox IDÊNTICA no cruzamento do X
   (`frac`); gusset de parede 60,7% dentro da escora de beiral. Triagem: gancho-no-pedestal etc.
   são embutidos DE PROPÓSITO.
2. **Rótulo do takeoff × geometria** (#44) — **mísula era BLOCO MACIÇO** de 180 mm rotulado
   "chapa-9,5": 254 kg/peça → 3.052 kg = 6,2% do aço. Vira chapas soldadas (alma+mesa inf., a mesa
   comprimida que governa a FLT); **aço 49.140 → 46.538 kg (−2,6 t)**. + arruela chapa-10 vs 12 mm.
3. **Relatório × cálculo** (#44) — quadro de verificações OMITIA a mão-francesa (2 listas, 1
   atualizada); `rodar_tudo` devolvia `atende`=pórtico enquanto o relatório usava o global →
   CI aprovaria projeto que reprova. Agora `atende`=global + `atende_portico`/`falhas` nomeados.
4. **Notas da prancha × modelo** (#44) — datum "RN+0,00=topo do concreto" ERRADO (concreto −100,
   placa −70..+30; erro de 100 mm p/ quem loca cotas); gancho "180 mm" vs 60 real. Viram MEDIDAS
   (`_notas_do_modelo`, ⌀ por Volume/eixo). + quadro de materiais SUMIA em silêncio no
   `rodar_executivo` standalone (takeoff só gravado por `montar_modelo`) → agora emite aviso.

**Infra:** (a) **filtro de vigas MORTO** (#40): `"_VIGA_" in o.Name` nunca casava (nome real
`PORTICO_xx_Vyy`) → `vigas=[]` → `_assenta` no-op silencioso, terças/clipes penetrando 60%; fix
`re.match(r"^PORTICO_\d+_V\d+")` + assenta chapa→terça na ordem certa. (b) **cache de módulo
irmão** (#44): freecad.exe da ponte PERSISTE entre execuções; módulo irmão fica em `sys.modules`
e o 3D roda a versão ANTIGA — o fix das pontas (#41) ficou FORA do modelo (20/24) até o reload.
Fix no bootstrap `_ship_build_src`: descarta os irmãos do cache. Só apareceu por uma constante
NOVA (`DIAM_BRACO`) estourar AttributeError.

**Método:** medir o modelo e comparar com o gate — não raciocinar do código. Erros meus da sessão,
todos por AFIRMAR sem medir: bbox×eixo ("11 mm" que eram d·sen45); E.1.4 "menos conservador";
grupo da Tab. F.1. Testes novos travam a LIGAÇÃO entre as duas descrições, não o valor.

## D68 — PR #45: Gaps normativos Nível A/C + wizard tipo ligação + romaneio (2026-07-22)
Revisão técnica do PR #45 (`feat/gaps-nivel-a-contra-seguranca`). **Resultado: APROVADO.**
- **Fadiga da solda do console:** NBR 8800 Anexo K Tabela K.1 item 8.2 (categoria F, $C_f=150\times 10^{10}$, $\sigma_{TH}=55\text{ MPa}$). Frmula K.4b $\Delta\sigma = (11\times 10^4 C_f/N)^{0,167}$. `console_ponte.py` dimensiona a perna do filete cobrindo esttica e fadiga.
- **Força de atrito do vento:** NBR 6123 6.4.2 $F'_{at}$ no telhado + 2 paredes longitudinais descontando $4h$ ou $4l_1$ ($L_{ef}$). Soma no contraventamento longitudinal em `compute_longitudinal()`.
- **Pattern loading / carga em xadrez:** NBR 8681 em pórticos multi-vão ($N_{VAOS}\ge 2$). Casos $Q_a$ (vos pares) e $Q_b$ (vos mpares) com combos ELU $C2_{xadrez}$ amplificam momento de desequilbrio da coluna interna.
- **Gate de empocamento:** NBR 8800 9.3 declividade $\ge 3\%$ dispensa ($OK=True$); $<3\%$ reprova ($OK=False$) sinalizando anlise adicional do peso da gua acumulada.
- **Torção e efeitos combinados:** NBR 8800 5.5.2. Tubo retangular com 3 regimes $T_{rd}$ (5.5.2.1.3) e interao quadrtica 5.5.2.2. Perfil aberto I/U avaliado por tenso de Saint-Venant $\tau_t$ (se $>0,20\tau_{Rd}$, exige anlise de flexo-toro).
- **Wizard ligação e romaneio:** pergunta `tipo_ligacao` (`soldada`/`parafusada`, default `soldada`), valida via enum; `romaneio.py` agrupa peas primrias ($C1, V1..Vn$) com marca, quantidade e peso por perfil do clculo.

## D69 — PR #46: Bloco de Fabricação (piece marks 3D, lista de corte, tolerâncias, shop drawings PE14) e diafragma NBR 15421 (2026-07-22)
Revisão técnica do PR #46 (`feat/fabricacao-shop-drawings`). **Resultado: APROVADO.**
- **Piece marks 3D (`marcas_peca.py`):** atribui marca determinstica por categoria/perfil ($C1, V1, T1, TP1, PB1...$); grava a propriedade `Marca` no FCStd/BIM em `build_galpao.takeoff()`.
- **Quadro unificado de materiais / Lista de corte:** tabela nica `Q09M` na PE09 com colunas MARCA | ELEMENTO | PERFIL | QTD | CORTE(m) | MASSA(kg). Fallback limpo.
- **Quadro de tolerâncias (`tolerancias_fabricacao.py`):** tabela `Q09T` na PE09 com tolerncias de fabricao/montagem (NBR 8800 12.2/12.3 + Bellei Ap. C) e folga do furo-padro ($d_b<24\rightarrow +1,5\text{ mm}$, $d_b\ge 24\rightarrow +2,0\text{ mm}$).
- **Shop drawings por peça (PE14 CROQUIS DE FABRICAÇÃO):** prancha `PE14_CROQUIS` com 3 vistas projetadas A1 por pea principal ($C1, V1, MI1$), rtulo com corte e nota de solda AWS.
- **Efeito de diafragma da cobertura (`diafragma.py`):** classificao NBR 15421 8.3.2 (deflexo no plano $>2\times\text{drift}_{mdio}\rightarrow$ FLEXVEL), validando a distribuio tributria do 2D; suporte a diafragma RGIDO (rigidez + toro).

## D70 — PR #47: Plano de Montagem e Escoramento (NBR 8800 12.3 + AISC 303 + Bellei 7.6.4) (2026-07-22)
Revisão técnica do PR #47 (`feat/plano-montagem-escoramento`). **Resultado: APROVADO.**
- **Sequência de montagem:** 10 passos adaptados ao pórtico (Bellei 7.6.4), exigindo estaiamento prévio do 1º pórtico antes de desacoplar o guindaste, mantendo estais provisórios até a conclusão do contraventamento definitivo.
- **Guindaste e içamento (`guindaste_requerido`):** considera rafter pré-montado no solo (2 meias-águas), aplicando coeficiente de impacto de montagem $\gamma_{imp}=1,10$ (NBR 8800 4.2.6) e calculando o momento de carga em $t\cdot m$.
- **Estai provisório (`estai_provisorio`):** tração $T = F / (n \cdot \cos\alpha)$, compressão adicional na coluna e força de ancoragem de arrancamento $N = T \cdot \sin\alpha$.
- **Vento de montagem (`forca_lateral_montagem`):** fator de combinação de construção $\gamma_{f3} = 1,30$ (NBR 8800 4.9.6.5).
- **Tolerância de prumo (`tolerancia_prumo_montagem`):** $\max(H/500, 5\text{ mm})$ por coluna, teto $25\text{ mm}$ global (NBR 8800 12.3.3.1.1).
- **Graceful degradation:** dados de canteiro ausentes degradam para "A CONFIRMAR" sem inventar parâmetros. Prancha nova `PE16_MONTAGEM` com 4 quadros estruturados + notas NBR 8800.

## D71 — PR #48: Fix de interferência 3D calha/condutor x placa de base e coluna tapered (2026-07-22)
Revisão técnica do PR #48 (`fix/build-tesoura-tapered-interferencia`). **Resultado: APROVADO.**
- **CONDUTOR × PLACA_BASE (tesoura):** a folga fixa de 70 mm sobre a borda da chapa invadia a parede do tubo Ø150 (raio 75 mm > 70 mm). Fix: $DOWN\_Y = L/2 + CONDUTOR\_D/2 + 40$ (raio + folga).
- **CALHA/BOCAL/CONDUTOR × COLUNA (tapered):** $GUT\_Y$ derivava da seção nominal `COL_SEC[0]`, mas a coluna tapered é mais funda no joelho ($h_{joelho}$, no beiral). Fix: $GUT\_Y = \max(COL\_SEC[0], TAPERED\_MODEL[\text{"h\_joelho"}])$.
- **Resultado:** elimina 28 interferências pré-existentes; suíte de build 3D passa de 7 passed + 2 failed para **9 passed**.

## D72 — PR #49: Job periódico da suíte de build 3D (2026-07-22)
Revisão técnica do PR #49 (`chore/ci-build-suite-agendada`). **Resultado: APROVADO.**
- **Guarda de build 3D:** runner PowerShell `tools/run_build_suite.ps1` roda `pytest -m build`, gera logs em `tools/build-logs/` e atualiza `LATEST.txt`.
- **Agendador Windows:** `tools/register_build_task.ps1` cria a tarefa agendada local `GalpaoFW-BuildSuite` (Weekly, Domingo 03:00 default) idempotente com suporte a `-Remover`.
- **Uso:** previne que regressões silenciosas de geometria 3D (como as corrigidas no PR #48) ocorram no futuro.

## D73 — PR #54: Gaps A3 (FLT do console) e C5 (patamar de escada) — 2ª auditoria NLM (2026-07-22)
2ª auditoria de gaps no NotebookLM (wiki S17/S18 re-subida): 5 candidatos → **2 reais** (verificados no fonte), 3 falsos-positivos já cobertos. **Resultado: APROVADO.**
- **A3 (contra-segurança): FLT da chapa do console** (NBR 8800 Anexo G, Tabela G.1, "seções sólidas retangulares fletidas em relação ao eixo de maior momento de inércia"). Seção maciça NÃO tem flambagem local (G.1.2) → o bordo comprimido tomba por **flambagem lateral com torção**. Antes o `M_Rd` era $W f_y$ elástico ingênuo (instabilidade só flagada). `console_ponte.mrd_flt_chapa`: $L_b = 2\,ecc$ (balanço), $C_b=1$, $Z=t L^2/4$, $J=L t^3/3\,(1-0,63\,t/L)$, $r_y=t/\sqrt{12}$, $C_w\approx0$; $\lambda_p=0,13 E\sqrt{JA}/M_{pl}$, $\lambda_r=2,0 E\sqrt{JA}/M_r$, $M_{cr}=2,0 C_b E\sqrt{JA}/\lambda$ (G.2.2). **Validado contra exemplo resolvido (Pfeil) via NLM.** Chapa robusta → reserva plástica ($M_{pl}>W f_y$); chapa esbelta → reduz (FLT governa).
- **C5 (completude): patamar de escada** (`escada.py`). Antes ABORTAVA para desnível $>3,2$ m; galpão com pé-direito $>6$ m → escada de acesso reprovada. `_dimensiona_multi`: divide em $N$ lances $\le$ `limite_lance` + $(N-1)$ patamares; projeção do lance **derivada de Blondel** ($2e+p=63$ cm; fatiar a projeção fixa quebrava o Blondel); `limite_lance` parametrizável (3,20 NBR 9050 / 2,90 NR-18); sinaliza `espaco_suficiente`. Comprimento do patamar = largura do lance (**A CONFIRMAR** — NBR 9050/9077 não consta na base).
- **Falsos-positivos confirmados no código** (não reimplementar): Ief no ELS das terças (`tercas_nbr14762` já usa Ief/fallback), breakout/pullout/hairpin da base (`base_chumbador` já faz ACI 318 Ch.17), bloco raso (`fundacao_sapata.dimensiona_bloco_env`). Ponderação espacial do vento = economia (conservador aceito).
- Nota de processo: **os PRs #51 (tools) e #54 (gaps) chegaram órfãos da `main`** por artefato de merge de PRs empilhados (base mergeada antes do filho) — trazidos por cherry-pick em PR próprio. [[06-open-threads#T21]]

## D74 — PR #55: Gaps A3/C5 + wiki da S18 para a main (2026-07-22)
Cherry-pick dos Gaps A3 (FLT do console) e C5 (patamar de escada) e da wiki da Sessão 18 para a main (merge `83570c9`, 2026-07-22 21:58Z). Conteúdo presente no código: `console_ponte.mrd_flt_chapa` (console_ponte.py:38) e `escada._dimensiona_multi` (escada.py:22) — o mesmo conteúdo decidido em [[#D73]]. Porquê: os PRs #51–#54 chegaram órfãos da main por artefato de merge de PRs empilhados (base mergeada antes do filho, [[06-open-threads#T21]]); o cherry-pick traz o conteúdo já revisado numa única rodada limpa. Alternativa rejeitada: reencadear os merges empilhados (histórico divergente, risco de reabrir revisão).

## D75 — PR #56: Exportador IFC4 (BIM) no build 3D via ifc_map.py (2026-07-22)
`build_galpao.export()` passou a exportar IFC4 consumindo o `ifc_map.py` — mapa semântico nome-da-peça → categoria IFC (`ifc_map.py:20 ifc_tipo(nome)`, módulo PURO sem FreeCAD, testável; asserts do selftest: `PORTICO_01_C00`→Column, `VIGA_ROLAMENTO`→Beam, `TERCA`→Member, `PLACA_BASE`→Plate, `SAPATA`→Footing, `ESTACA`→Pile, `TELHA`→Covering, `CHUMBADOR`→MechanicalFastener). Gerou IFC4 de 1,67 MB com 789 elementos no modelo real. Porquê: interoperabilidade BIM — o galpão abre no Revit/Eberick com a categoria estrutural correta, não um sólido genérico (IfcBuildingElementProxy). Alternativa rejeitada: export nativo do FreeCAD (acoplado ao GUI, sem controle semântico das categorias).

## D76 — PRs #57/#59: montar_modelo com auto-fallback headless (2026-07-22/23)
`montar_modelo` passou a aceitar `headless=None` (default): tenta o bridge (FreeCAD aberto, porta 9875) e, se não responder, cai automaticamente para o freecadcmd HEADLESS (rodar_projeto.py:210-218, subprocesso próprio; o fluxo reusa `_ship_build_src` de [[#D65]]). Elimina a necessidade de manter o FreeCAD GUI aberto com o bridge. Porquê: automação/CI não podem depender de processo GUI interativo. Alternativa rejeitada: exigir bridge sempre (quebra execução desassistida). Correção de caminho (task-9): o PR #57 foi mergeado em branch intermediária (`feat/ifc-export-bim`, `f0026ae`); o conteúdo chegou à main via PR #59 (`5863532`, 2026-07-23 00:15Z).

## D77 — PR #58: modelo neutro de dados + emissor IFC4 puro-Python (2026-07-22)
`modelo_neutro.py` (dados neutros) + `ifc_emit.py` (emissor via `ifcopenshell`) emitem o IFC4 BIM da estrutura primária direto do cálculo, SEM invocar o FreeCAD (`ifc_emit.emitir_ifc_do_spec`, ifc_emit.py:523; `rodar_projeto.py:528-540` chama quando `ifcopenshell` disponível e degrada com graça). Porquê: caminho puro = determinístico, testável e sem dependência do GUI/exportIFC do FreeCAD. Alternativa rejeitada: estender o export do build_galpao (acoplado ao 3D, mais lento, exige FreeCAD).

## D78 — PR #60: secundários lineares no IFC puro (2026-07-23)
Correção de nome (task-9): o atributo `secundarios_lineares` citado no 00-index **não existe** no código; o PR #60 estendeu `modelo_neutro.py` com as funções reais `tercas()` (:116), `girts()` (:163), `tirantes_parede()` (:198), `contrav_cobertura()` (:222) e `frame_completo()` (:920), e `ifc_emit._perfil_ifc` (:204) emite o perfil/marca real. Terças, girts de parede, tirantes e contraventamento entram como `IfcMember` no IFC puro. Porquê: o modelo neutro cobre os secundários lineares com perfil/marca reais — BIM completo sem FreeCAD. Alternativa rejeitada: manter secundários fora do IFC puro (BIM só da estrutura primária).

## D79 — PR #61: modelo analítico + IFC4-Structural (2026-07-23)
**FALLBACK (c) do plano de revisão:** o módulo `modelo_analitico.py` **não existe** no disco nem no main (`git ls-tree main` vazio; só `tests/test_modelo_analitico.py`). A implementação real (verificada no código): função `galpao_portico.modelo_analitico()` (galpao_portico.py:305) + emissores `ifc_emit.emitir_ifc_analitico` (ifc_emit.py:533; emite `IfcStructuralAnalysisModel` :548, `IfcStructuralPointConnection` :559, `IfcBoundaryNodeCondition` :569, `IfcStructuralCurveMember` :579) e `emitir_ifc_analitico_do_spec` (:632). `rodar_projeto.py:533-535` grava `{slug}.ifc` (BIM físico) e `{slug}_analitico.ifc` (BIM estrutural p/ SAP2000/Eberick/Robot) em `EXPORT_DIR/ifc/`. Porquê: interoperabilidade estrutural (IfcStructuralAnalysisModel) direto do cálculo, sem FreeCAD. Alternativa rejeitada: citar o módulo inexistente (como em 00-index:74/05-glossary:46) — a decisão documenta a implementação real (função + emissores).

## D0 — política permanente
Push direto na `main` bloqueado pelo auto-mode classifier → usar branch + PR. Assistente não pode se auto-conceder permissão (escrever allow-rule = bypass, bloqueado). Usuário roda via `!` ou adiciona regra manualmente.




## D80 — "terminado" exige suíte completa verde (2026-09-03)
Um goal só está terminado quando a suíte completa passa, não quando os testes novos passam. **Porquê:** três lotes seguidos (G24–G28, G29–G32, G33–G36) foram entregues como terminados carregando cada um exatamente UMA guarda vermelha disparada pelo próprio lote — a contagem fixa `23 vs 26` do harness do G15, e depois a ilha `fontes_externas_protocolo` na guarda de alcançabilidade do G6. Nos três casos a falha foi achada por amostragem dirigida, e a fatia foi escolhida por palpite sobre o que a mudança ameaçava: nada garantia que houvesse só uma. As guardas estavam funcionando; o que faltava era rodá-las.

**O que tornava isso caro, e não é mais:** `pytest -n N` falhava neste repositório com `EOFError` no bootstrap do `execnet`, por causa do acento em `OneDrive\Área de Trabalho`. Junction sem acento não resolve (o venv reporta o `sys.prefix` real). Resolve invocar o interpretador pelo **nome curto 8.3**: `C:\Users\joseh\OneDrive\READET~1\dev\FREECA~1\FRAMEW~1\GALPAO~1\VENV~1\Scripts\python.exe`. A suíte cai de ~79 min (serial) para ~26 min.

**Alternativa rejeitada:** manter verificação por amostragem dirigida e confiar no revisor para escolher a fatia certa. Foi exatamente o que falhou três vezes seguidas — e o custo de errar cresce, porque cada lote novo herda o vermelho do anterior.

## D81 — teste que muta o repositório vivo não pode rodar em paralelo (2026-09-03)
A Parte C do `test_G21_prova_fronteiras.py` reescrevia `galpao_concreto.py` e `edificio_multipavimento.py` **no diretório de trabalho real** e restaurava no `finally`. Sob `pytest -n 4` os outros workers liam o arquivo mutado dentro dessa janela e ficavam vermelhos por **contaminação, não por defeito**. Medido em 2026-09-03: três execuções do mesmo arquivo sob `-n 4` deram três conjuntos diferentes de vermelhos (`A1`/`A3`/`C1`–`C3`), e uma delas passou inteira. A Parte C passa a mutar uma **cópia** do pacote (só os `.py` da raiz e de `tests/`, ~5 MB), com `cwd` na cópia — o mesmo mecanismo que o G22 já tinha aplicado a `tools/prova_fronteiras_G21.py` e que nunca chegara ao arquivo de teste. Depois do fix: 5/5 verdes sob `-n 4`, e uma asserção nova confirma que o módulo vivo continua byte a byte igual.

**Porquê importa mais do que parece:** o D80 exige suíte completa verde antes de declarar um goal terminado. Uma suíte não determinística não sustenta essa regra — a corrida de 44 min tida como "primeira suíte verde" foi, neste arquivo, **sorte de escalonamento**: o defeito é reproduzível no commit anterior (`01234c3`), portanto pré-existente. Um guarda que reprova por vizinhança não é guarda, e um verde que depende de escalonamento não é verde.

**Efeito colateral diagnosticado:** o sintoma na suíte não era uma falha de engenharia, era `TypeError: argument of type 'NoneType' is not iterable` — `result.stdout` vindo `None` do subprocesso sob paralelismo. A asserção agora concatena `stdout` e `stderr` com `or ""`, para que ausência de saída nunca se disfarce de defeito do framework.

**Alternativa rejeitada:** marcar o arquivo como `serial` e rodá-lo numa segunda passada fora do `-n 4`. Resolveria a contaminação, mas manteria a janela em que um `kill` deixa dois módulos quebrados no repositório — que é o acidente que o G22 existiu para eliminar.

**Não era um caso isolado.** Caçando o verde exigido pelo D80 saíram três rodadas seguidas com três falhas DIFERENTES, nenhuma de engenharia e nenhuma do lote em revisão: (1) a mutação em disco do G21 acima; (2) `test_g19_quarto_caso_1_comando_output`, que travava 900 s em `communicate` com o filho **já encerrado** (`returncode 1`) porque a ponta de escrita do pipe seguia aberta e a thread leitora nunca via EOF — corrigido redirecionando a saída para ARQUIVO, o que tira a dependência de EOF de handle e faz o prazo medir o tempo do filho; (3) `test_command_runner_marks_timeout`, que dava `timeout_seconds=0.1` a um filho e exigia a saída parcial, quando só a partida do interpretador no Windows custa ~0,15 s (subiu para 2,0 s, ainda muito abaixo do `sleep(10)`, então o caminho de timeout continua exercitado). Na sessão anterior eu já tinha "corrigido" o item (2) subindo o prazo de 180 s para 900 s: tratei demora onde o problema era um pipe que não fechava. **Regra que fica:** teste cujo veredito depende de carga de máquina, de escalonamento ou de handle herdado não é teste — é sorteio; e um sorteio dentro da suíte esvazia o D80 por dentro. A 4ª rodada fechou 3199 passed, 0 failed.

## D82 — dimensionar é comparar o adotado com o necessário, não escolher o maior da tabela (2026-09-04)
O G44 fez o fuste **dimensionar** o estribo (`Asw/s` pelo Modelo I) em vez de só verificar o mínimo, e com isso relaxou o portão de `cort_ok = ok_biela and ok_min` para `cort_ok = ok_biela` — correto em princípio: pelo Modelo I todo `Vd <= VRd2` é atendível por armadura transversal. Só que o detalhamento **tem teto**: com estribo fechado de 2 ramos, a maior bitola da tabela (φ10) no menor espaçamento praticável (5 cm) entrega 31,4 cm²/m, e o `fallback` devolvia esse teto sem dizer que ele não bastava. Medido em seção **corrente** (40×40, fck 30, `Vd` = 700 kN, `u_biela` = 0,955): necessário 40,81 cm²/m, adotado 31,42 cm²/m — **23% a menos**, com `cort_ok = True`, `OK = True`, e o φ10 c/5 seguindo para o quadro de aço do executivo. Pior: o mesmo caso **reprovava antes do G44**. A saturação silenciosa não passou despercebida — ela converteu um vermelho em verde.

**O fix:** `detalha_estribo_pilar` devolve o `Asw_prov` real também no teto, e `dimensiona_pilar` compara `prov >= req` (`Asw_atendido`) antes de `cort_ok`. Casos acima do teto voltam a reprovar, com a mensagem nomeando a saída (`Asw excede o estribo de 2 ramos detalhável: 40,81 > 31,42 cm²/m`) — cobri-los exige estribo de 4 ramos/suplementar, que este módulo ainda não detalha.

**Regra que fica:** quando um módulo passa de *verificar* para *dimensionar*, o portão migra do esforço resistente para o **detalhamento entregue**. Toda tabela de detalhamento (bitolas, espaçamentos, perfis, bitolas de condutor) tem um último item, e "escolher o último item" nunca é o mesmo que "atender". Onde houver `fallback` para o extremo de uma tabela, tem de haver uma comparação explícita entre o adotado e o necessário — e a guarda genérica varre a tabela inteira, não um caso.

**Alternativa rejeitada:** estender a tabela (φ12,5 / 4 ramos) para "não reprovar". Isso é detalhamento novo, não um ajuste de portão — e inventar regra de detalhamento para fazer um teste passar é como o gate nasce mentindo. Fail-closed até o detalhamento existir.

## D83 — o teto do estribo sobe com ramos, não com bitola (2026-09-04)
O G47 executou o detalhamento que o D82 deixou em aberto: `detalha_estribo_pilar` passa a oferecer 2/4/6 ramos (fechado simples + 1/2 grampos suplementares) com a regra literal do acervo — NBR 6118:2014 18.3.3.2 p.149 (`st,max = d ≤ 800 mm` se `Vd ≤ 0,20 VRd2`, senão `0,6d ≤ 350 mm`, via remissão de 18.4.3 p.151-152) e 18.2.4 p.145-146 (> 2 barras no trecho de `20φt` ou barra fora dele exige suplementar). A lista de bitolas fica **congelada em φ ≤ 10**: o teto sobe de 31,4 (2R) para 62,8 (4R) e 94,2 cm²/m (6R, extravaso para os 2/100 casos extremos da varredura em 50×50 fck 40) sem empurrar bitola — a armadilha do φ12,5 (2R a 49,1, que "apagava" só o caso 40×40/700) continua bloqueada por asserção (`phi <= 10`). O `s_t` adotado entra no dict (`s_t`/`s_t_max`/`st_ok`, e `cort_ok` exige `st_ok`) e no quadro de aço do executivo (`N2 (estribo 4R s_t=113mm)`, com o grampo somado ao comprimento/peso). Medido: a varredura 5 seções × 4 fck × 5 frações (100 casos, antes 26 acima do teto 2R, máx 69,27 cm²/m) agora atende 100/100 abaixo da biela; o caso 40×40/700 virou φ10 c/7 4R (44,88 ≥ 40,81); biela esmagada continua reprovando. A guarda específica do G44b foi **migrada** (mesmo nome, agora afirma 4R em vez de reprovação — mudança intencional de comportamento) e a guarda genérica (`prov < req` nunca com `cort_ok=True`) segue literalmente verde.

**NotebookLM (corrigido na revisão):** o G47 registrou "autenticação expirada, sem condição de reconsultar". **Não procede** — `nlm login` restaura a sessão sozinho (perfil Edge logado) e foi o que aconteceu na revisão; a auth do NotebookLM nunca é um bloqueio. A consulta feita depois **confirmou** as duas citações, palavra por palavra, e ainda trouxe a NOTA de 18.4.3 que a leitura do PDF tinha deixado passar (C55–C90: espaçamentos máximos reduzidos em 50 %, ganchos a 135°) — ver D85. As citações continuam literais do PDF local (256/256 páginas com texto extraível, regra de `st` em texto corrido, não em imagem); o cross-check só as reforçou.

**Alternativa rejeitada:** φ12,5 na lista (apagava o vermelho do caso-guia sem detalhar ramos e deixava o teto logo ali, em 49,1) e espaçamento < 5 cm (impediria o vibrador).

## D84 — o espaçamento do estribo de pilar não é o de viga (2026-09-04)
Achado revendo o G47, que leu a 18.4.3 e implementou dela só o lado que restringe o `st` transversal. A 18.4.3 (p.152, PDF do acervo) impõe limites **próprios** ao espaçamento longitudinal de pilar — *"o menor dos seguintes valores: 200 mm; menor dimensão da seção; 24 φ para CA-25, 12 φ para CA-50"* — e só **depois** manda comparar com os de 18.3, *"adotando-se o menor dos limites"*. O módulo calculava `s_estribo_max` exclusivamente pela regra de viga (`0,6d ≤ 300` / `0,3d ≤ 200`) desde o G39. Varredura de 775 casos: **87 adotavam espaçamento acima do teto de pilar**, o pior 14×50 com `s` = 270 mm contra 140 mm permitidos — quase o dobro, e num pilar esbelto, onde o espaçamento do estribo é justamente o que impede a flambagem da barra longitudinal.

**O fix:** `s_estribo_max` passa a ser o mínimo entre o limite de 18.3 e os de 18.4.3. Os dois primeiros (200 mm, menor dimensão) saem da geometria e valem sempre; o `12φ` só entra quando a bitola longitudinal é **declarada** (`phi_long_mm`) — arbitrar uma bitola para apertar ou afrouxar o limite seria inventar dado, e o campo `s_limite_governante` diz qual mandou. A mesma declaração ativa o `φt ≥ φ_long/4` da 18.4.3 (φ25 → φt mínimo 6,25 → adota φ6,3). Depois: 0 de 775.

**Regra que fica:** quando um elemento tem seção normativa própria, herdar o detalhamento de um elemento vizinho é uma decisão, não um default — e uma decisão que precisa aparecer. `bw`, `d` e `Vd` são os mesmos símbolos na viga e no pilar, e é isso que faz a fórmula de viga parecer aplicável. **O parentesco de símbolos não é parentesco de regra.** Irmão do D82: lá o portão olhava o esforço e não o detalhamento; aqui olhava o detalhamento certo pela tabela errada.

## D85 — o framework aceita C55–C90 e calcula com a fórmula de C50 (2026-09-04) — ABERTO
Achado no cross-check da 18.4.3 no NotebookLM (a NOTA sobre C55–C90 levou a olhar o resto). `pilar_concreto` aceita `fck` = 60 MPa sem reclamar e calcula `fctm = 0,3·fck^(2/3)` — expressão que a NBR 6118 8.2.5 restringe a concretos **até C50**. Acima disso vale `fctm = 2,12·ln(1 + 0,11·fck)`. A fórmula errada dá `fctm` **maior**, logo `Vc` maior e `ρsw,mín` menor: é **contra a segurança**, ~7 % em C60 e ~19 % em C90.

**Extensão medida:** 12 ocorrências em 11 módulos usam a expressão de C50 (`base_chumbador` ×2, `estaca_profunda`, `fundacao_sapata`, `laje_concreto`, `pilar_concreto`, `piso_industrial`, `premoldado_nbr9062`, `viga_baldrame` ×2, `viga_protendida`). Só **duas** tratam a faixa alta: `fissuracao_nbr6118.py:45` e `premoldado_nbr9062.py:73` — ou seja, **a fórmula certa já existe no repositório**, em dois lugares, e não foi aplicada nos outros. Três sítios carregam o comentário `# (fck<=50)` / `# (<= C50)`: o limite era conhecido e não virou guarda.

**Não corrigido aqui de propósito.** Não é ajuste de duas linhas: é varredura em 11 módulos com efeito em `Vc`, `ρsw,mín`, ancoragem, punção e fissuração, e cada um precisa de teste. Vira goal (G49), no molde do "método só vale até λ = 90 e `OK` = True" do G3 — a família de defeitos em que o módulo aceita a entrada fora da faixa do método e responde com um número que parece bom.

## D85/G49 — fechamento: fctm C55–C90 + NOTA de ductilidade (2026-09-04) — FECHADO
G49 aplicou `fctm = 2,12·ln(1+0,11·fck)` para fck > 50 MPa (8.2.5) em 9 sítios
runtime de 8 módulos: `base_chumbador.ancoragem_chumbador`,
`estaca_profunda.ancoragem_tirante`, `fundacao_sapata.comprimento_ancoragem`,
`laje_concreto.cortante_laje`, `pilar_concreto.verifica_cortante_pilar`,
`piso_industrial.resistencia_flexao_projeto`, `viga_baldrame._verifica_cortante`
+ `_flecha_alvenaria` (Mr), `viga_protendida._fctm`. Referências conferidas, não
reescritas: `fissuracao_nbr6118.py:45` e `premoldado_nbr9062.py:73` já certas.
`premoldado` listado no D85 era o ramo `<=50` da função já bipartida — sem
defeito; selftests com fck=25 fixo e `estaca 671` (C25) não são defeito.
Rejeitar fck > 50 foi explicitamente rejeitado: trocaria número errado por
recusa, com a fórmula certa a uma linha de distância.

**NOTA 18.4.3 C55–C90 (ductilidade) — decisão explícita: APLICAR.**
A NOTA diz "recomenda-se" espaçamentos máximos reduzidos em 50% e ganchos a
135°. Por ser recomendação, ignorar em silêncio era a falha a evitar. Decisão:
aplica o 50% como fail-closed (`s_estribo_max *= 0,5` em C55–C90, governante
`18.4.3 NOTA C55–C90 50% (G49)`) e expõe `nota_ductilidade_C55_C90` +
`gancho_135_exigido` no dict do pilar — o framework não detalha o ângulo do
gancho, então o gancho vira exigência declarada, não geometria inventada.
Cobertura: `tests/test_fctm_c60_g49.py` (8 testes por módulo C50×C60 exigindo
C60 < extrapolação errada + transversal que falha se algum módulo ainda usar
C50 acima de C50 + teste da NOTA).

## D86/G50 — o resto da família C55–C90 + a asserção tautológica (2026-09-05) — FECHADO
O G49 fechou **uma** variável da faixa alta (`fctm`, 8.2.5). A revisão mediu que a norma muda mais quatro coisas acima de C50, todas com o valor de C50 no código e **três já com o comentário `(fck<=50)`** — outra vez "o limite era conhecido e não virou guarda". Cláusulas lidas literalmente no PDF do acervo (p. 23, 24, 26, 91, 120), não de memória:

- **17.2.2 + 14.6.4.3** em `fundacao_sapata._armadura_flexao` (primitiva única de sapata/laje/viga): `lambda_bloco(fck)`, `alpha_c(fck)`, `xd_lim(fck)`. **1154 de 5154 casos** em C55–C90 passavam com `ok_dominio=True` e `x/d` acima do permitido; pior `x/d` real **0,695** contra limite 0,35, com o código reportando 0,449 ≤ 0,45. O erro tinha dupla origem: o limite errado **e** o `x/d` calculado com o `λ` errado, que o subestima — corrigir só o limite não fecharia.
- **8.2.8 `Eci`**: `5600·√fck` vale "de 20 MPa a 50 MPa"; acima superestimava o módulo em +4,2% (C60) a +13,8% (C90) → flecha e perda elástica de protensão subestimadas. Primitiva única `fissuracao_nbr6118.eci`, 6 sítios; sobrou uma só ocorrência de `5600` no repositório, dentro do ramo `fck<=50` da própria primitiva.
- **8.2.10.1** em `pilar_concreto`: `eps_cu`, `eps_c2` e o expoente `n` do parábola-retângulo por `fck`.
- **`gancho_135_exigido` sai do dict e entra no ARTEFATO** (quadro de aço + SVG). O D85/G49 dizia "vira exigência declarada"; ela estava declarada num dict que ninguém abria — nem o executivo, nem o desenho, nem o detector do G48 (a escapatória do `_retornos`: campo devolvido é campo "usado"). O teste mede o SVG e o quadro, não o dict.

**Asserção tautológica (bug de teste, achado na revisão).** `test_02_flecha_maior_que_extrapolacao` afirmava `d_pos > d_pos * (Ecs_novo/Ecs_err)` — razão < 1, logo verdade para qualquer implementação. Era o **único** teste do efeito no ELS e passaria com o `5600·√fck` de volta no lugar. Reescrito para **injetar** a extrapolação errada e comparar as duas flechas: 0,8100 mm (certo) × 0,7800 mm (errado) em C60. **REGRA:** asserção cujo lado direito deriva do lado esquerdo não mede nada — o comparativo tem de vir de uma execução independente (fórmula antiga injetada, fixture, ou valor literal aferido). Prima do "teste que checa substring e nunca parseia" e do "green bar não cobre o artefato".

**Continuidade C50 verificada bit-a-bit** (não por amostra): 6804 casos de flexão contra reimplementação com as constantes antigas, `Eci` de 20 a 50 MPa, o diagrama do pilar e `_sigma_c` em 204 pontos — **zero diferenças**. Guardas provadas vermelhas desfazendo os fixes numa cópia.

**Aberto:** `s_limite_governante` é sobrescrito pelo rótulo da NOTA em C55–C90 e perde qual limite foi cortado (rótulo, não cálculo). `LAMBDA_BLOCO`/`ALPHA_C`/`XD_LIM` de `fundacao_sapata` ficaram sem consumidor — armadilha para quem vier depois. **Escopo:** foi varrida a família 8.2.5/8.2.8/8.2.10.1/14.6.4.3/17.2.2; não se afirma exaustividade sobre outras cláusulas com faixa de validade em `fck`.

## D87/G51 — a faixa de validade declarada vira guarda (2026-09-05) — FECHADO
Terceira vez que a mesma assinatura paga (λ≤90 no G3, C50 no G49/G50): o limite do método está no comentário, o autor sabia, e não virou `if`. Desta vez o gap medido é o **θ da treliça de torção (17.5: 30..45°)**, escrito no cabeçalho de `torcao_nbr6118` e aceito sem cheque — com θ=20° o `OK` era `True` (TRd2=24,4 ≥ Td=20), número errado que parecia bom.

- **Ferramenta permanente** `varredura_faixa_validade.py` (estende a máquina de AST do G48, script avulso com teste-guarda): casa comentários/docstrings de faixa com a função dona e classifica em **guardada / desguardada / inverificável**. Enxerga **106 declarações distintas** (piso: 64), que rendem 157 linhas de relatório após o *fan-out* — uma linha de cabeçalho de módulo alcança até 14 funções (`pilar_concreto:36/41/42`). O contador de baldes conta linhas, não candidatos: as **21** declarações distintas com alguma desguardada são a lista de triagem real (52 linhas). O balde **inverificável** (caso Wenner: `a>>b` com `b` fora da assinatura) é o que impede o gerador de falso-positivo. Limites honestos da lente, documentados no teste: só 1 nível de delegação (as 27 do pilar, guardadas via `eps_cu/eps_c2/expoente_n/alpha_c_pilar`, aparecem desguardadas), só literais e constantes-literais (constante-expressão como `THETA_1_MIN=1/300` e o gate `PISO_MIN/MAX` passam batido), sem `in`/`min/max` por nome, e o casador erra sujeito em linha multi-parâmetro (`frac⊂fracao`) — cada um com FP medido no registro.
- **Fix θ (recusa fail-closed):** fora de 30..45, `OK=False` + `motivo` nomeado com G51; 45° bit-a-bit idêntico à fórmula pré-fix; sweep de θ falha se qualquer valor fora devolver `OK=True`; vermelho provado desfazendo o fix numa cópia (`and bool(theta_valido)` removido → θ=20 volta a `OK=True`). Direção conservadora: recusar em vez de saturar (saturar 50°→45° *aumentaria* o TRd2).
- **Triagem (G10):** só θ virou correção. Medidos e arquivados como FP: desaprumo (satura com `saturou` nomeado), escada (gate reprova, piso 0,13→`ok=False`), sismo zona (ValueError) + Ca/Cv (satura) + classe F (KeyError, fail-closed feio), pertinência à tabela (`carga_uso`, `coef_dinamico`), setpoint dentro da faixa (subestação 1,20 ∈ 1,15..1,30), hipótese de modelagem (tapamento), comentário metodológico e escopo de código. **ABERTO:** `rho_min` satura em C50 (`rho_min(90)==rho_min(50)==0,00208`) — o número certo exige a Tab. 17.3 C55–C90; sem número certo, sem correção.
- **Restos G50:** `s_limite_governante` composto (`"18.3 (viga) + NOTA C55-C90 50% (G49/G51)"`, cálculo intacto: metade exata); órfãs de `fundacao_sapata` privatizadas (`_C50`) com compat `fs.XD_LIM == 0,45` sob `DeprecationWarning`.

**Regra que fica:** limite de método escrito em comentário sem `if` que o compare é bug em espera — e a varredura que o encontraria tem de rodar no CI, não na cabeça do revisor.

### Revisão do G51 (mesmo dia) — quatro correções

A revisão mediu quatro coisas e as fechou aqui, por serem achado de revisão e não engenharia nova (nenhuma move número de projeto):

1. **A ferramenta era relatório, não guarda.** Medido por injeção: um módulo novo com faixa declarada e sem `if` era classificado corretamente como `desguardada` — e a suíte ficava **verde**, porque o teste só afirmava `len >= 64`. O `chaves_varridas()` do G51 nasceu **sem um único chamador**, enquanto todo antecessor (G33 `varredura_nao_verificados`, G40/G42/G43/G48 `varredura_descoberta`) congela baseline. Agora `DESGUARDADAS_TRIADAS` (21 entradas) é comparado **nos dois sentidos** — entrada nova é vermelha com a mensagem que ensina a saída, entrada que sumiu também (senão o baseline protege nome morto). Chave `(arquivo, declaração[:70])`, sem linha (muda a cada edição) e sem função (o fan-out multiplicaria por 14). Vermelho provado **duas vezes**: em `tmp_path` dentro do próprio teste (`varredura(raiz=...)`, para não mutar o repo vivo — causa do D81) e uma vez no repo real.
2. **`biela_ok` deixara de significar biela.** Com θ=20° a biela **passa** (Td=20 ≤ TRd2=24,4) e o relatório imprimia a desigualdade que vale e concluía `REPROVA (aumentar seção)` — remédio errado, a seção está sobrando. A chave estava suja de propósito, para a recusa alcançar o chamador. Agora `biela_ok` é só a biela, `OK = biela_ok and theta_valido`, e `viga_concreto` lê `OK`. A guarda **não** é no dicionário da torção: mede o `OK` da própria viga com θ forçado a 20° (h=0,60, onde a viga passa em tudo — com h=0,50 o ELS já reprovaria e o teste não mediria nada). O relatório passou a marcar as armaduras do caso recusado como "não usar": elas são os 63% de estribo que motivaram o goal, e continuavam sendo impressas para alguém copiar.
3. **A órfã idêntica ficara um módulo ao lado.** `pilar_concreto.LAMBDA_BLOCO = 0,80  # (fck<=50)`, zero consumidores — a mesma armadilha que o item 4 do G51 tirou de `fundacao_sapata`. Removida (o pilar integra parábola-retângulo, não usa bloco retangular); `ALPHA_C` fica, é consumida por `alpha_c_pilar`. A varredura **não** acusa órfãs — para aquela linha ela emite 14 registros, quatro deles `guardada`, casando o comentário com funções que nada têm a ver com a constante: o balde `guardada` também tem falso-positivo, e só os limites do lado `desguardada` estavam documentados.
4. **Os contadores do registro** confundiam linha de relatório com declaração (corrigido acima).

**Não feito, por escolha:** zerar as armaduras no dicionário do caso recusado. Mudaria o que sai para quem já consome, sem medida de quem consome — o relatório marca, o `OK` recusa, o número fica.

**Regra que fica (2ª formulação):** varredura sem baseline congelado é relatório. A do G33 já dizia isso no título — *"a varredura não pode crescer sozinha"* — e a lição é que a convenção existia no repo, com o nome da função já certo, e mesmo assim o lote parou na metade.

## D88/G52 — a obra inteira rodada, aberta e medida (2026-09-05) — FECHADO
Primeira vez que um projeto sai de ponta a ponta e é **conferido artefato por artefato** em vez de "rodou sem exceção". A suíte tinha 3268 testes verdes e o prédio entregava, ao mesmo tempo, uma laje dimensionada para uma carga que ninguém aplicava.

- **Achado grave (fronteira laje→viga).** `edificio_multipavimento` e `estrutura_casa` passavam `pav["g_kN_m2"]` como `g` de `dimensiona_laje`, cujo contrato é *permanente **além** do peso próprio* (ele soma `25·h` por dentro). A laje era dimensionada para `2·25h + revestimento` enquanto viga, pilar e fundação recebiam `25h + revestimento`. **Nenhum gate reprovava**: cada módulo estava certo, a junta é que estava errada — a assinatura do G3 (viga deitada), do G8 (laje que engrossa sem realimentar) e do G13 (viga analisada e nunca verificada). Corrigido para o revestimento; a laje do prédio volta a `h=0,10` e o preço de venda cai de R$ 860.208 para R$ 790.397 (**medido, não congelado**).
- **Índice × pasta.** O aviso "13 pranchas no índice, 3 emitidas" existia só no manifesto; agora está dentro do `pacote-legal.md`, que é o que alguém lê antes de protocolar (a contagem passou para antes da renderização do `.md`).
- **Orçamento parcial de segunda ordem.** A guarda do G14 nomeia insumo **que está na tabela e ficou sem quantidade** (`fechamento_lateral`); ela não via os sistemas que **nunca entraram na tabela**. R$ 790 mil ÷ 1134 m² ≈ R$ 700/m² contra CUB na casa de R$ 2.500–3.000/m² — a diferença é alvenaria, revestimento, esquadria, impermeabilização, elevador e incêndio. Agora o `relatorio.txt` traz a seção **A CONFIRMAR** que os nomeia. *Nomear, nunca estimar.*
- **Laço manifesto ⇄ pasta fechado (22 = 22).** O `_montar_result.json` do headless era recibo de canal lateral e ficava em `model/` fora do manifesto: lido, removido.
- **README nos dois sentidos.** O comando documentado omitia `--generate-2d` enquanto o texto prometia duas plantas; e havia uma terceira prancha (`armacao-vigas`) que o README não mencionava.
- **Degradação honesta provada em 4 variantes:** `Ca` ausente → `failed` nomeado; SPT ausente → `not_available` (a tensão do solo nunca é arbitrada); distâncias ausentes → `OK=false` nomeado. Nada é inventado no lugar do dado que falta.

### Revisão do G52 (mesmo dia) — três correções

1. **A correção mais grave do lote não tinha guarda.** Provado por injeção: com `"g": pav["g_kN_m2"]` de volta nas duas linhas, `branches/{edificio,g13,g14,g34,g9}` + `test_fronteiras` + `test_edificio_multipavimento` dão **186 passed**. O teste que o nome prometia — `test_G21_A3_laje_engrossa_sem_realimentar_fica_vermelha` — nunca chama `rodar`: ele recria a aritmética do defeito em variáveis locais (`h_na_carga_bug = h_declarada`) e prova a **conta**, não o **módulo**; fica verde com o defeito de volta (parente do D86). E a única guarda vizinha foi **afrouxada** de `>` para `>=` (legítimo — o `>` só passava *por causa* do bug — mas deixou a fronteira sem ninguém). Novo `test_fronteira_carga_laje_g52.py`: a asserção é a **relação** (`laje["g"] == pav["g_kN_m2"]`, os dois lados são o permanente total), com a decomposição `pp + revestimento declarado` provando que não são dois números errados concordando, e `REVEST=1,6` ≠ default para matar a chave se ela morrer no caminho. **Vermelho provado** nos dois módulos, com a mensagem que diagnostica.
2. **O `%%` chegou ao entregável.** A nota nova de `gestao_edificio` escrevia `~2%%` num literal que não passa por `%`-formatação (`relatorio_pt` faz `"- " + str(nota)`), e o `relatorio.txt:29` entregue imprimia `~2%%`. *Rótulo × artefato*, dentro da nota que o próprio goal acrescentou para fechar rótulo × artefato.
3. **O verde reportado não era o da suíte.** O lote reportou 3063 passed; a coleta da suíte dá **3268** (`3268/3291, 23 deselected`) — 205 a menos, num lote que mexeu em `orcamento`, `entregaveis_projeto`, `rodar_projeto`, `pacote_legal`, `gestao_edificio` e na fronteira que alimenta **casa e prédio**.

**Regra que fica:** um erro de junta não aparece no fechamento de carga nem na barra verde — os dois lados fecham, cada um com o seu número. Só aparece **abrindo o artefato** ou escrevendo a igualdade que atravessa a fronteira. E teste que recria o defeito em variáveis locais não é guarda do módulo: se ele não fica vermelho quando o defeito volta ao código, ele mede a aritmética do revisor.

## D89/G53-G54 — as instalações ganham geometria e o prédio ganha compatibilização (2026-09-06) — FECHADO
O `coordination: not_available` do edifício não era falta de encanamento — `compatibilizacao.py` está pronto e é agnóstico de disciplina desde o galpão. Faltava **o que coordenar**: elétrica, hidráulica e incêndio existiam como número (DN, seção, gates) e nunca como posição. Ligar o hook antes disso teria produzido um relatório estrutura×estrutura com zero pendências — entregável vazio que *parece* cobertura, no lugar de um `not_available` honesto.

- **G53 `bim_instalacoes_edificio.py`:** prumadas de água/esgoto/ventilação/pluvial, prumada elétrica + eletrocalha + quadro por pavimento, e coluna de hidrantes DN65, todas no **mesmo frame** do `bim_edificio` (mm, origem no canto, seção em metros). Traçado **convencional** — shaft determinístico a 1,0 m do canto — declarado como tal no cabeçalho e no aviso da hidráulica: as horizontais correm 250–400 mm abaixo do topo da laje, *dentro da altura da nervura*, para que o cruzamento com a viga seja detectável como furo e não como folga acima dela.
- **G54 hook:** `_write_coordination` no `edificio_adapter`, `coordination` em `DELIVERABLES`, com **três** portas de `not_available` (sem estrutura; sem instalação calculada; federado só com estrutura) — a guarda que impede o relatório vazio.
- **Medido na obra:** 390 membros, **126 conflitos** entre disciplinas — 72 estrutura×hidráulica, 45 elétrico×estrutura, 9 estrutura×incêndio. O tubo de queda furando as 9 lajes e a eletrocalha cruzando as VY aparecem por nome e volume. É a primeira vez que o framework aponta um furo que a estrutura não tem.

### Revisão do G53/G54 (mesmo dia) — três correções

1. **Filtro de nome morto: as 126 pendências diziam a coisa errada.** `compatibilizacao._ESTRUTURA` é `{"concreto","aco"}` — os nomes do galpão. O federado do edifício emite `"estrutura"`, que não está no conjunto, então **todo** par estrutura×instalação caía no ramo *"ambas são instalações"*. Medido lado a lado, o mesmo clash com dois nomes: `concretoxhidraulica` → *"prever passagem (furação/embutido) na estrutura"*, responsável `hidraulica`; `estruturaxhidraulica` → *"remanejar o traçado... reunião de coordenação"*, responsável `coordenacao`. A frase que é o **propósito do entregável** não aparecia em nenhum dos 126 registros nem em lugar nenhum do pacote (`grep` na pasta inteira: zero). Corrigido acrescentando o nome (não mudando o galpão, que segue por `concreto`/`aco`); depois do fix os responsáveis se repartem 72/45/9 pelas disciplinas certas. Guarda em `test_compatibilizacao.py`, vermelha provada.
2. **Código morto que fingia proveniência.** A altura da coluna acima da cobertura lia `gate_pressao_estatica.desnivel_m`, **multiplicava por zero** e somava 3000; o resultado era guardado em `h_res` e descartado no fim (`void = h_res; del void`), enquanto o membro usava `H_total + 3000.0` literal. Quem lesse concluiria que a altura vem do dimensionamento. Virou `H_RESERVATORIO_MM` declarada, com a limitação dita. (Mesma forma de linha morta em `_pe_direito`, removida.) Rodada re-medida: clash **bit a bit idêntico**, 390/126.
3. **O G53/G54 não registrou decisão nenhuma no wiki** — este verbete é da revisão.

**ABERTO (vira goal, não se corrige em revisão):** os 126 conflitos são todos `esperado: false` e `n_esperado: 0` — a triagem que o galpão tem (`_clash_esperado`) foi contornada, e `OK = not clashes` torna o portão **insatisfazível por construção**: uma prumada vertical *tem* de cruzar toda laje. Falta a terceira categoria — não é "contato de montagem intencional" (o `esperado` do galpão, ação *nenhuma*) nem conflito a remanejar, é **furo previsto**, que se fecha aprovando o negativo e verificando a estrutura. O `resolution_mode: manual_approval` e o `resolution_requests: []` já estão no manifesto e ninguém os consome: hoje não há como **fechar** uma pendência. Decidir essa taxonomia é engenharia, não revisão.

**Menor, também aberto:** `eletrica_edificio._escopo` promoveu `tracado_e_prumadas_reais` de `not_available` para `implemented`. A chave diz *reais* e o traçado é convencional, por decisão declarada do próprio módulo. A hidráulica é mais defensável (`tracado_das_prumadas`, com o aviso reescrito nomeando a convenção). O escopo é o mecanismo de honestidade deste framework; a palavra tem de caber no que existe.

**Regra que fica:** disciplina é nome, e nome atravessa fronteira de módulo sem aviso. O galpão chama a estrutura de `concreto`/`aco`, o prédio chama de `estrutura`, e a máquina de triagem — correta, testada, em produção — deu o veredicto errado 126 vezes sem uma linha de erro. Quando dois emissores alimentam o mesmo consumidor, o vocabulário é fronteira: ou é contrato explícito, ou é o próximo filtro de nome morto.

## D90 — 2026-09-06 — Compatibilização ganha a terceira categoria: furo previsto fecha por decisão registrada (G55)
`compatibilizacao` conhecia dois estados (montagem aprovada x conflito a remanejar) e o gate `OK = not clashes` era insatisfazível: prumada *tem* de furar laje. Agora há `furo_previsto` — cruzamento inevitável e legítimo cuja ação é prever a passagem e verificar admissibilidade — com veredito normativo, classificador declarado e fechamento por `resolution_requests`. Porquê: um relatório que nunca zera não é entregável, é alarme preso; o manifesto já carregava `resolution_mode: manual_approval` e ninguém o consumia.
- **Regra normativa, lida do acervo** (NBR 6118:2014 do `fontes/01_CONCRETO`, extração verbatim): `avalia_furo_viga` (13.2.5.1 a–d + face mínima "em qualquer caso" ≥5cm e 2×cobrimento), `avalia_abertura_laje` (13.2.5.2 a–c; lisa/cogumelo sempre verifica), `avalia_furo_vertical_viga` (21.3.3: d≤b/3 duro), contorno/cantos 21.3.1. Sem o dado o veredito é `a_confirmar` com o motivo nomeado — nunca um passe; limite duro violado é `reprovado`.
- **Classificador** (`classifica_cruzamento`): o tipo de peça não classifica (BeamxPipe existe nos dois mundos) — só vira furo o clash com geometria declarada transversal em Beam/Slab estrutura×instalação; longitudinal é conflito (embutido 13.2.6), pilar/sapata é conflito, sem hint é conflito.
- **Geometria do edifício** (`bim_instalacoes_edificio.cruzamentos_edificio`): |cos| entre eixos <0,5 → transversal; laje×tubo vertical → transversal, ×horizontal → longitudinal. Sem dims o veredito é `a_confirmar` — fechável por decisão de responsável, não por conta.
- **Gate**: `aplicar_resolucoes` + `gate_ok` — aprovada sai do denominador; aprovador+justificativa vão ao relatório e ao BCF (`topic_status` Closed + rastro). **Guardas que falham (ValueError → hook `failed`):** aprovação sem justificativa/aprovador, de `reprovado`, de conflito ou de montagem. Nota legada (`issue_id`+`status`+`note`) continua só nota: não fecha nem falha (texto não fecha conflito — `test_iteration_does_not_close_conflict_by_text_only` segue verde).
- **Galpão congelado:** sem hint, mesmos pares/classificação/ação/responsável (`test_galpao_congelado_sem_hint`); `OK` do manifesto passa a ser `gate_ok` (só-montagem agora passa, antes era False com clash esperado). `clash.json` segue cru; `pendencias.json`/BCF/relatório carregam categoria, veredito e resolução.
Rejeitado: marcar tudo como `esperado` (mentiria pior) e aprovar conflito por papel (botão de silenciar — a saturação silenciosa vestida de governança). Testes: `tests/test_compatibilizacao_g55.py` (23 testes, cada item com vermelho por injeção de defeito). Suíte: 254 passed em `branches/project_loop` + `branches/edificio`.

## D91/G56 — o prédio ganha as 10 pranchas que o índice promete (2026-09-06) — FECHADO
O índice (`pacote_legal._PRANCHAS`) numerava 13 folhas e o hook emitia 3, todas de concreto. Elétrica, hidráulica e incêndio calculavam (G12), tinham gates e posição (G53) — e zero folhas. O G52 fez o aviso "13 prometidas, 3 emitidas" aparecer no pacote-legal.md; este goal existe para o aviso sumir **por mérito**, e sumiu: a rodada do edifício agora emite 13/13 (`test_indice_de_pranchas_nao_passa_por_pasta_de_pranchas` atualizado para `emitidas == n_pranchas == 13`, sem o aviso de escopo).
- **Reuso por parâmetro, não por cópia:** os emissores nasceram para o galpão (um pavimento, um retângulo). A planta de instalação sai por pavimento-tipo e a hidráulica ganha o corte vertical das prumadas que o galpão nunca teve — como funções novas *nos mesmos módulos* (`desenho_eletrico.diagrama_prumada_edificio_svg`, `desenho_hidraulica.planta_rede_edificio_svg(rede=...)`, `desenho_incendio.planta_pavimento_edificio_svg`), sobre as primitivas de `desenho_svg_base`. Rejeitado: `desenho_*_edificio.py` paralelos.
- **Unificação das primitivas:** `desenho_hidraulica/incendio/coordenacao` definiam `_esc/_t/_line` próprios em vez de importar a base — o berço do bug de dupla-escapa do residencial. Agora importam (aliases preservados); `linha()` da base ganhou `dash` para não perder capacidade.
- **Coordenação tem folha, não matriz:** `_write_coordination` grava `matriz.svg` com kind `coordination-matrix`; a PE-CD-01 é a projeção do federado com clashes (`desenho_coordenacao.gerar_prancha`), registrada com kind `drawing` via `_emitir_coordenacao` — senão não conta no laço.
- **O que não sai, sai nomeado:** `emitidas + puladas == len(indice_pranchas)` no próprio hook (rede de segurança após as emissões por disciplina), com motivo por folha. É o laço manifesto⇄disco do G52 aplicado ao índice.
- **O nome que se perdia:** `gestao_edificio.disciplinas()` devolve "fundacao", que o `continue` do índice descartava em silêncio (D89 de novo). Decisão explícita: no **caderno** ela segue seção própria; no **pacote** `disciplinas_pacote()` traduz para "concreto" (`FUNDACAO_COBERTA_POR`, PE-CO-01 "Formas e fundações") — nunca atravessa e evapora.
- **Guardas:** `tests/test_edificio_pranchas_g56.py` (19 testes): cada prancha parseia o SVG como XML, confere geometria contra o dado (QDs == pavimentos servidos, DNs == calculados, hidrantes/detectores == sistemas) com par vermelho-por-injeção, e roda `colisoes_de_rotulo_svg` (novo equivalente na base), mais o laço índice⇄disco e o mapeamento da fundação.

## D92/G57 — SPDA e emergência do prédio: o `not_available` honesto atravessa o pacote legal (2026-09-06) — FECHADO
O goal pedia "Registrar D91" — número já ocupado pelo G56 acima, então o registro é D92 (o comando do goal valia pelo ato, não pelo número).
- **Premissa do goal corrigida por medição:** a NBR 17019:2022 **está** no acervo (`fontes/05_ELETRICA`, F056, 1 MB, catalogada) — o "fonte ausente do acervo desde o S30" não se confirma. O item de recarga segue `not_available`, mas com o motivo verdadeiro escrito ("sem projeto dedicado", norma presente), nunca "fonte ausente". NBR 5419-1..4 presentes; NBR 14880 (pressurização) ausente — a pressurização segue `not_available` no `incendio_edificio` sem retoque.
- **SPDA por reuso, não por cópia:** `_spda_do_predio` reaproveita `spda_nbr5419.dimensiona_spda` com o envelope do prédio (C=sum(vaos_x), L=sum(vaos_y), H=H_total). Ng **e** Cd (entorno, Tab.A.1) declarados, nunca default — a regra do SPT no G9; o Nd só é publicado com os dois, senão aviso nomeando o ausente. NP sem declaração é adotado como III **dizendo que adotou** (`spda_np_adotado`, `NP_declarado=False`) — o default herdado do galpão não atravessa em silêncio. Sem `eletrico.spda`, escopo `not_available` com aviso `spda_nao_avaliado`. Limitação nomeada: equipotencialização por pavimento e gaiola-vs-captor seguem fora.
- **Emergência pela essencial, não pela total:** `eletrico.emergencia` traz as quatro parcelas declaradas (elevador, pressurização, bombas de incêndio, iluminação); a essencial é a SOMA (derivada, não constante) e o gate exige essencial < total. O CONJUNTO de parcelas é derivado do incêndio: `_resumo_incendio` viaja no contexto (`tipo_escada_exigido`, blocos da 10898, hidrantes); parcela exigida e ausente vira aviso nomeado (`emergencia_pressurizacao_nao_declarada`, `..._bombas_...`, `..._iluminacao_...`), e a ausência do bloco nomeia o que o incêndio cria. Só a POTÊNCIA é declarada — nenhum módulo a calcula. Avisos, não gates (suite existente segue verde).
- **O portão da parte 2 decide de verdade:** com R1 declarado e R1 ≤ RT, a proteção é `dispensada_por_risco` — avaliação feita, resultado dispensa: sem NP/descidas prescritos, sem pendência no pacote (`spda_dispensada_por_risco`, relatório diz DISPENSADA). Captacão prescrita sem Nd (falta dado de sítio) vira pendência nomeada de "risco não avaliado" — o pacote não trava como ausente, mas não se cala.
- **O portão no pacote (o que fecha o goal):** `pacote_legal` ganha `pendencias` (itens PENDENTE no checklist + aviso no .md + `a_confirmar`); `gestao_edificio._pendencias_aprovacao` deriva SPDA/emergência do escopo do elétrico. Sem eles, checklist limpo — compatível com o galpão.
- **Guardas:** `tests/test_edificio_g57_spda_emergencia.py` (24 testes, 2 ponta a ponta): checklist cita SPDA/emergência ausentes, limpa quando declarados, essencial == soma e < total (muda com a parcela), conjunto derivado do incêndio (aviso nomeia o que ele cria; parcela exigida e ausente vira aviso; W/bloco implícito publicado), resumo viaja no contexto, Ng **e** Cd sem default, NP inválido recusado, recarga com motivo escrito; a ponta a ponta roda o spec persistido (`run_edificio` → `emitir_pacote_legal`) e lê o `pacote-legal.md` do disco — PENDENTE presente/ausente conforme o spec. Medido: G12 (10), G14 (3), guardas/eletrico/BIM/pacote (52) — verdes.

## D93/G58 — a casa nivela ao prédio: cinco entregáveis com quantitativos próprios (2026-09-06) — FECHADO
O goal pedia "Registrar D92" — número já ocupado pelo G57 acima, então o registro é D93 (o comando do goal valia pelo ato, não pelo número).
- **O que entra:** `casa_residencial.DELIVERABLES` vai de 4 para 9 (`coordination`, `orcamento`, `cronograma`, `caderno_encargos`, `pacote_legal`), na mesma ordem de execução do prédio (cronograma custeia com a planilha do orçamento), com os hooks registrados no adaptador.
- **A armadilha não se confirma por herança:** novo `gestao_casa.py` em vez de reusar `gestao_edificio` — a casa tem alvenaria+baldrame, telhado com área declarada e estrutura opcional (G13). `CODIGOS_APLICAVEIS` da casa inclui `telha_cobertura` (derivada da projeção declarada, SEM inclinação, madeira fora do preço e dita) e exclui `aco_estrutural`/`piso_industrial`. É a primeira vez que a guarda G14 (`aplicaveis` separando "a obra não tem" de "ninguém quantificou") é exercida contra outra tipologia: casa em sapatas sai com `estaca` em `nao_aplicaveis`; casa sem estrutura sai com o concreto em `sem_quantidade` e o orçamento se declara PARCIAL no .txt — nunca telhado zerado.
- **Coordenação, geometria antes do hook:** novo `bim_instalacoes_casa.py` (mesma forma do G53) — elétrica com a posição REAL declarada (pontos+quadro validados) e hidráulica com traçado CONVENCIONAL em shaft dito no perfil. Ponto de luz no teto é HOSPEDADO na laje, não furo (filtro `SlabxLuminaire` documentado — sem ele toda luminária virava "furação" com ação errada). Sem instalação calculada, `not_available` com motivo; federado só-estrutura, idem.
- **Fronteira declarada atravessa:** 3 pavimentos → estrutura `blocked` (`structure_input_rejected`) e os cinco novos respeitam em vez de contornar (orçamento/cronograma/coordenação `not_available` citando G13). A derivação lê SÓ o resultado calculado, nunca mede o spec direto.
- **Guardas:** `tests/test_casa_g58_nivelamento.py` (18 testes): nove entregáveis declarados, telha dentro/estaca fora/cobertura 100% no spec cheio, G14 sem estrutura e telhado-sem-área como falta nomeada, parcial declarado no disco, coordenação com 3 disciplinas e furos só `Beam/SlabxPipe`, luminária nunca furo, indisponibilidade motivada sem instalação, fronteira 3 pav, WBS com `cob`, caderno sem arquitetura (sem cláusulas na biblioteca), pacote com 14 pranchas e aviso índice⇄pasta, laço manifesto⇄disco e abertura de cada artefato.
- **Ponta a ponta inventada (G52):** sobrado de 2 pav inventado (`residencial_dormitorio`+`cobertura_manutencao`) roda `needs_review` — orçamento R$137.479/11 itens sem PARCIAL, cronograma 114 dias com `cob` no crítico, caderno 4 seções, pacote 14 pranchas/4 ART/memorial ATENDE com aviso, coordenação 125 membros/9 clashes só hidráulica, 4 SVG + 2 IFC, laço sem faltas. Medido: G58 (18), casa G4/G13/G8 (89), G14 (26), project_loop (234), edificio (34) — verdes.

## D94/G59 — o que sobra de dimensionamento: dois fixes, duas justificativas, um rename (2026-09-06) — FECHADO
O goal pedia "Registrar D93" — número já ocupado pelo G58 acima, então o registro é D94 (o comando do goal valia pelo ato, não pelo número, precedente do próprio G58).
- **Prédio baldrame/recalque: a declaração É a barreira certa, mas era omissão silenciosa parcial.** Carga de parede e Es são dados de entrada/de sítio — arbitrar qualquer dos dois seria o bug que o framework trata como tal desde o G9, então nada passa a rodar sem declaração. O que faltava era o motivo escrito: a casa avisa `viga_baldrame_nao_declarada` desde o G13 e o prédio calava. Agora `edificio_adapter` emite `viga_baldrame_nao_declarada` (peso do fechamento do térreo fora da fundação + N_amarracao da G23 sem caminho) e `recalque_nao_declarado` (Es/SPT ausente, sem verificação) sempre que o item está ausente sem erro nomeado. Escopo continua `not_available` — nenhum `not_available` novo, só motivo onde não havia.
- **Casa estabilidade/desaprumo: uma linha de justificativa em vez de um módulo (decisão antes de código, com acervo).** Lido literalmente no PDF do acervo (`fontes/01_CONCRETO`, NBR 6118:2014): γz (15.5.3, p. 105) e as rigidezes aproximadas (15.7.3, p. 106) valem para estruturas reticuladas com **no mínimo quatro andares** — casa de 1–2 pav está fora do campo do método, não "esquecida". O desaprumo global (11.3.3.4.1, p. 59) é exigido "sejam elas contraventadas ou não", mas sem ação horizontal declarada não há análise global onde ele entrasse; a imperfeição local vive no pilar via M1d,mín (11.3.3.4.3, aplicado em `pilar_concreto`). As chaves seguem `not_available` (nenhum status novo — os portões leem implemented vs not_available), e o artigo mora onde o framework põe motivo escrito: aviso `acao_horizontal_nao_avaliada`, relatório da estrutura e comentário do `escopo()`. Nenhum gate promete o que não calcula, então nada há a recusar.
- **ρmín C55–C90: FECHADO — a tabela estava no acervo.** Foto da p. 130 (linha Retangular): 55:0,211 60:0,219 65:0,226 70:0,233 75:0,239 80:0,245 85:0,251 90:0,256 %. `_RHO_MIN_TAB` estendido com os literais, C50 bit-a-bit intacto (todos os consumidores — viga, laje, baldrame, sapata, divisa — herdam). O teste que documentava a saturação (`test_06f`, G51) virou asserção dos valores + `rho(90) > rho(50)`; selftest da sapata idem. Último resíduo da família de alta resistência (D85/G49/G50/G51).
- **G54 corrigido aqui: `tracado_e_prumadas_reais` → `tracado_convencional_das_prumadas`.** A chave dizia *reais* e o traçado é convencional em shaft por decisão declarada do próprio módulo (`bim_instalacoes_edificio`, 1,0 m do canto). Renomeada no `_escopo` da elétrica + aviso `tracado_das_prumadas_convencional` espelhando a hidráulica; a hidráulica (`tracado_das_prumadas` + aviso) já era defensável e ficou. Único consumidor da chave antiga era o próprio teste, atualizado com asserção de ausência.
- **Guardas:** `test_06f` reescrito (G51), selftest `fundacao_sapata` item 10, `test_escopo_publica_tracado` (+ausência da chave antiga), `test_baldrame_e_recalque_nao_declarados_tem_motivo_escrito` (edifício), `test_o_nao_calculado_tem_artigo_e_nao_so_not_available` (casa, artigos no relatório).

## D95/G60 — a parede passa a existir como elemento: vertical de alvenaria estrutural (2026-09-07) — FECHADO
O goal pedia "Registrar D94" — número já ocupado pelo G59 acima, então o registro é D95 (o comando do goal valia pelo ato, não pelo número, precedente do G58/G59).
- **Fonte lida na página, não de memória.** A Parte 1 é scan sem camada de texto (pymupdf devolve zero caracteres nas 77 páginas): as seções foram lidas página a página no próprio PDF — errata (p. 1), Tab. 2 γm (p. 12), Tab. 1 Ea (p. 11), 6.2.2.3 fk (p. 12), 9.4.2 te (p. 23), Tab. 9 tetos 24/30 (p. 26), 11.2.1 NRd (p. 29), 11.2.2 pilar armado (p. 30), 11.3.2 Fig. 8 (p. 32), 11.3.3/11.3.4 (p. 33), 11.5.3.2 (p. 38), Anexo C (p. 53). A errata foi lida antes do corpo e é mais rica que o resumo do goal: 6 itens (11.2.2 Em→Ea; 11.3.2 legenda A′s/F′s tracionada→comprimida; 11.3.3 fyk→fyd; 11.5.3.2 qualificativo + fyk→fyd). O módulo novo é `alvenaria_estrutural.py`: γm Tab. 2 (2,0/1,5/1,0 ELS), fk de fpk declarado (0,70 bloco, 0,60 tijolo, 0,85 fppk; 6.2.2.3), Ea Tab. 1 por patamar (patamar fora do tabelado recusa, mesmo trato da Tab. 2 da 6120), λ=he/te com tetos Tab. 9 (24/30 + nota "a" da térrea com γm=3,0 como opção declarada), NRd 11.2.1 (0,9 no pilar), pilar armado 11.2.2 com Es/Ea da errata, flexão 11.3.3 com fyd da errata + redutores de aderência + teto 0,3·fd·b·d².
- **As quatro guardas do goal, todas como relação.** fpk ausente recusa (`fpk_nao_declarado`) e a assinatura prova que nenhum default entra (5 funções inspecionadas); λ acima do teto reprova sem trazer NRd no resultado (prova que não saturou); peso próprio interno 0,0 em todo resultado + `confere_fronteira_peso` no molde G52 (revestimento fora do default como filtro de nome morto); errata afirmada como relação (fs=0,75·fyk/1,15, fs≠fyk; Es/Ea contra o Ea da Tab. 1). Vermelho provado por mutação nos dois guardas de fórmula (sinal do `if` de λ, fyd→fyk). 10.1.1 (te≥14 cm acima de 2 pav) e Qh declarada (recusa `acao_horizontal_exige_contraventamento`, nunca vento zerado) completam o lote; 11.5 e Anexo C seguem `not_available` com motivo e endereço.
- **A ilha que o gate acusou virou consumidor de verdade.** `test_alcancabilidade` flagrou `alvenaria_estrutural` como inalcançável (nenhum import a partir das entradas) — e tinha razão: os dois memoriais diziam "(NBR 16868 ausente do acervo)", frase que o G60 tornou falsa. Em vez de um import decorativo, os dois `relatorio_pt` (`edificio_multipavimento`, `estrutura_casa`) importam o módulo e imprimem `linha_memorial_cadeia_gravitacional()` (fonte única, sem motivo congelado); o teste do G60 roda as duas cadeias e exige a linha nos memoriais. BIM/pranchas/costura no Loop ficam para o seguinte, com `not_available` motivado no `escopo()` do módulo (lote cálculo+BIM+executivo de tipologia nova é grande demais para ser revisável).
- **Falha pré-existente documentada, não assumida.** `branches/g34/test_vigas_edificio_fechadas.py::test_hook_de_desenhos_emite_a_prancha` (13 pranchas vs 3 esperadas) quebra no estado atual da árvore; bissecção por stash prova que a causa é o diff não-commitado do G55–G59 em `edificio_adapter.py` (269 inserções), não este lote: com só o comentário G60 revertido (diff da árvore mantido) continua vermelho; com caderno/fronteiras revertidos idem. Não mexido aqui — pertence ao lote dono do diff.
- **Guardas:** `tests/test_alvenaria_estrutural_g60.py` (12 testes), selftest do módulo, fronteira F21 em `fronteiras.py`, disciplina `alvenaria_estrutural` no `caderno_encargos` (Parte 2: prumo 9.3.4, argamassa/graute e prismas). Medido: G60 (12), alcancabilidade (5), caderno/fronteiras/cargas (76), varredura G51 incluindo baseline nos dois sentidos, descoberta G40/G43/G48, edificio+g13+g14 (101), project_loop+g9 (272), g55/g56/g57/g58/bim (89) — verdes.

## D96/G61–G65 — a alvenaria vira caminho de carga, e a laje passa a repartir pela charneira (2026-09-07) — FECHADO
Lote executado fora desta sessão; o registro abaixo é da revisão, e separa o que veio entregue do que a revisão corrigiu.
- **Entregue.** `fundacao_sapata_corrida.py` (NBR 6122, largura B pela faixa de 1 m, regra do G9 intacta: sem `sigma_solo_adm` nem `perfil_spt` o módulo recusa em vez de arbitrar) fecha o apoio que faltava — `TIPOS_FUNDACAO` ganha o quarto tipo e cada consumidor decide em voz alta (galpão e fundação por pilar recusam a corrida com endereço, D89). `estrutura_casa` ganha a tipologia portante com fronteira declarada (térrea, `MAX_PAVIMENTOS_ALVENARIA = 1`) e escopo honesto: sem pórtico, viga e pilar saem `not_available` em vez de dimensionar peça que ninguém constrói. G62: `desenho_alvenaria.py` sobre as primitivas do `desenho_svg_base` (nenhum `_esc` local — o berço da dupla-escapa) + BIM/IFC cruzado. G63: distribuição de Qh por rigidez 9.6.2 com flange capada em 6t (10.1.3) e parede sem rigidez que aparece **nomeada** em vez de sumir. G64: a lente do G51 vira portão de cobertura — todo `*.py` produz chave ou consta de `SEM_FAIXA_DECLARADA` com motivo, e cada termo novo da regex entrou com a contagem de falsos-positivos medida. G65: 7229→17076:2024 e 13792→16981:2021 conferidas **na página da vigente** (a fórmula da fossa sobrevive idêntica; 5.2.1/5.2.2 mantêm o 3,7 m), com uma varredura que cruza toda NBR citada contra o `catalogo.csv` e baseline nos dois sentidos.
- **Defeito de engenharia da revisão: a laje não se reparte por comprimento de parede.** O G61 dava a cada linha `carga_laje × L / L_total`. O framework já calcula o quinhão de cada borda pelas charneiras da 14.7.6.1 (`laje_concreto.reacoes_apoios`, aferido nos Quadros 7.8/7.9 de Carvalho, usado painel a painel pelo `pavimento_tipo`) — estava a uma chave de distância. Medido num painel de 4,0 × 9,0 m: a borda longa recebe **7,78 kN/m** e a repartição por comprimento dá **6,92 kN/m** — 11 % a menos **na parede que governa**, e 38 % a mais na curta. Corrigido com `quinhao_laje_por_linha`, que reusa as reações por painel; o baldrame passa a ser dimensionado pelo **maior** quinhão por metro (é uma seção para a obra), não pela média.
- **O gate de fechamento era tautológico (D86).** A "simetria por linha" recomputava a mesma fórmula da repartição, logo concordava consigo mesma e passaria com a carga indo para a parede errada — exatamente o que a lição do G3 manda pegar. Agora a simetria é uma **relação independente**: quando a lista de vãos é um palíndromo, as linhas espelhadas têm de receber o mesmo quinhão; plano assimétrico devolve `simetria_pares: 0`, e o teste exige ≥ 1 (gate que confere zero pares não é gate).
- **Apoio fictício: a laje apoiava em linha sem parede.** Com `linhas: "contorno"` e malha interna, a laje era calculada em painéis apoiados em BX-1/BY-1/BY-2 — linhas que ninguém ia construir — e o quinhão delas era espalhado no contorno. Passa a **recusar nomeando as linhas**, com a saída dita (`linhas='todas'` ou geometria de um painel só). A fixture do lote usava justamente `contorno`.
- **Duas paredes ocupavam o mesmo volume.** Só com a malha interna existindo o `confere_empilhamento` acusou: as paredes em Y recuavam te/2 apenas nas **pontas**, e cruzavam as linhas internas em X (4 conflitos, ~0,05 m³ cada; idem nas corridas). O emissor passa a cortar a linha em Y em cada cruzamento (um membro por trecho, sufixo `-T1`, `-T2`), com `n_trechos_parede` derivando o esperado do cálculo. Com contorno o corte devolve um trecho único — por isso o defeito ficou invisível.
- **Contagens congeladas.** Quatro asserções do G62 fixavam `== 4` paredes/sapatas — a foto do dia da fixture de contorno, a mesma armadilha do `len(arts) == 3` do G34 e do AR300. Passaram a derivar do resultado.
- **A sapata corrida trocava as direções quando B > 1 m.** Para manter a convenção "B é o menor lado", a faixa era montada como `min(B, 1) × max(B, 1)` — o que, na Parte B, faz o único balanço real (transversal, `(B - b_ped)/2`) ser medido **ao longo do muro**. Com M = 0 a Parte A não depende da ordem; a Parte B depende, e é ela que arma a peça: no caso medido (B = 2,00 m) o veredito de rigidez 22.6.1 saía `True` para uma peça que é flexível (h = 0,50 < (2,00−0,15)/3 = 0,617) e, com isso, a punção nem era verificada. A faixa passa a ser sempre B × 1,00 m.
- **A Parte B era calculada e nunca consultada.** A largura adotada saía do `OK_A` (solo) apenas; uma largura que reprovasse a flexão seria adotada assim mesmo — o irmão do "analisado e nunca verificado" do G13. Agora a escada adota a menor largura que passa **no solo e no concreto**, e a peça flexível sai nomeada (`corrida_flexivel`) em vez de omitida.
- **A folha desenhava verga e contraverga que ninguém dimensiona.** A elevação as põe sobre cada vão com 0,40 m de apoio de cada lado; não há flexão da verga nem armadura calculada em módulo algum. Desenho que sugere cálculo inexistente é rótulo dirigindo geometria — passou a `verga_contraverga: "not_available"` com motivo escrito, para o memorial não prometer o que não verifica.
- **A guarda do G65 quebraria o CI.** Ela lê `fontes/catalogo.csv`, e `fontes/` inteira é ignorada pelo git (o acervo são PDFs de norma) — num checkout limpo o arquivo não existe, e é assim que o CI de nuvem roda (`working-directory: framework/galpao_fw`, `pytest tests/`). Passou a `skipif` nomeado, válido só para o arquivo ausente: catálogo presente com citação sem lastro continua reprovando. Conferido escondendo o catálogo: 2 skipped, não 2 errors.
- **Guardas provadas no vermelho por injeção:** repor a repartição por comprimento deixa `test_quinhao_da_laje_e_o_da_charneira...` vermelho; anular a recusa deixa `test_laje_nao_pode_apoiar_em_linha_sem_parede` vermelho; reverter o corte dos cruzamentos deixa `confere_empilhamento` vermelho. A sobremedição dos cruzamentos no orçamento (a medição mede a linha inteira, o BIM corta) fica **dita na nota**, a favor do orçamento, em vez de silenciosa.

## D97/G66–G70 — o telhado de madeira, e a carga que fechava contra si mesma (2026-09-08) — FECHADO
Lote executado fora desta sessão; o registro separa o que veio entregue do que a revisão corrigiu. Toda conferência normativa desta revisão foi feita **na página**: a NBR 7190-1:2022 tem camada de texto (F136, pp. 10–68 do PDF) e a NBR 16868-1 é scan, lida renderizando as páginas (Tab. 4 na p. 13 impressa, 11.4.1/11.4.2 na p. 35).
- **Entregue.** `madeira_nbr7190.py` + `telhado_casa_madeira.py` (G66): tesoura Howe com esforços por equilíbrio nó a nó, terças, ligação em chapa de aço e descida que realimenta a casa — a Tab. 3 (20 classes × 12 propriedades), a Tab. 4/Tab. 5 de kmod, os γw, o embutimento 6.2.5, Hankinson, My,k = 0,3·fu·d^2,6, nef de 7.1.7, F90,Rk de 7.1.1 e os **doze modos a–l** da 7.3 conferem célula a célula com o PDF. G67: a alvenaria ganha 11.4 (τ = V/(b·h), só a alma nas seções com flange, τ ≤ fvk/γm) com a Tab. 4 exata (0,10+0,5σ≤1,0 / 0,15+0,5σ≤1,4 / 0,35+0,5σ≤1,7, σ das permanentes ×0,9) e o sobrado com vento por nível. G68: o sobrado de concreto sem vento passa a ser **recusado** em vez de sair ATENDE sem que força horizontal nenhuma tivesse existido, com γz publicado como *indicador* (15.5.3 fora do campo abaixo de 4 andares) — e de quebra fecha o gap do G13, a viga contínua analisada e nunca verificada. G70: a verga sai dimensionada (arco de descarga a 45°, laje só se cair dentro do triângulo, armadura **adotada × necessária** respeitando o D82).
- **A carga do telhado era 25 % maior que o telhado.** O tributário de cada nó do banzo superior espelhava o vizinho na ponta (`2·x0 − x1`), então o nó de **beiral levava painel inteiro** em vez de meio: com 4 painéis a tesoura carregava 5/4 de telhado. Medido: 18,85 kN lançados contra 15,08 kN de telhado real — razão 1,2503 — enquanto o quantitativo comprava os 91,8 m² corretos. A descida para as paredes e a fundação caiu de **113,07 kN para 90,46 kN** com o conserto.
- **E o gate de fechamento não podia enxergar isso (D86).** `fechamento_carga` compara a reação com a carga *lançada* — e a reação **sai** do equilíbrio dessa carga, então fecha por construção: reportava `erro_rel: 0,0` com o defeito dentro. Nasceu `confere_fechamento_area`, com origem independente (telha × área **inclinada** + sobrecarga × área **projetada**), e é ela que reprova o painel a mais. Reinjetar o tributário antigo deixa 6 testes vermelhos.
- **Tab. 14: o a2 de prego era o do Eurocode.** A norma pede **(3 + 6·|sen α|)·d** e o código trazia (3 + |sen α|)·d — a 90° a exigência é 9d e o portão aceitava 4d, menos da metade. O próprio módulo marcava "glyph ambíguo no PDF, A CONFIRMAR": a p. 53 está legível e resolve. É o AR300 outra vez — número lembrado de outra norma, congelado com ressalva.
- **A 6.2.4 tem duas condições e só uma estava implementada.** "Se a força estiver aplicada a menos de 7,5 cm da extremidade da peça **ou** a′ ≥ 15 cm, admite-se αn = 1". Só a segunda existia — e o apoio da tesoura é exatamente a ponta do banzo inferior, onde fc90,d saía até **2× maior** que o permitido. `alfa_n` passa a receber a posição; não declarada cai no piso (αn = 1), porque o ganho da Tab. 6 é contra a segurança quando a peça termina ali.
- **L/200 não existe na Tab. 21.** A faixa de δfin é L/150 a L/300, e o código adotava um número do meio dela citando a tabela; δnet,fin (L/250 a L/350) não era verificado. Agora a faixa é a guarda: sem declaração vale o **extremo estrito** (inst L/500, fin L/300, net L/350 — regra do piso conservador), declarado tem de cair dentro, e a contraflecha respeita o teto de 2/3 da 8.2. A terça da fixture passa folgada nos três (L/1148 e L/638).
- **`travado_borda_comprimida` era carimbo.** Booleano declarado que ninguém conferia, com a 6.5.6 marcada `not_available` — quando a **dispensa** da 6.5.6 está inteira no acervo (Tab. 8, βM por h/b). É a lição do G11: não era bloqueio de fonte. Virou número: declara-se L1 entre travamentos e o módulo confere L1 ≤ b·E0,ef/(βM·fm,d). Na fixture, βM = 11,13 e o limite é 3,46 m contra L1 = 2,0 m.
- **9.2.1 e 9.3 não existiam — nem no `escopo()`.** Área mínima de 50 cm² e espessura de 5 cm na peça principal (18 cm²/2,5 cm na secundária), e L0 ≤ 40× a dimensão comprimida (50× tracionada). Ausência silenciosa: a peça podia sair legal na conta e proibida na norma. Implementadas como portão por barra.
- **O apoio da terça valia meio tramo.** A terça corre a extensão inteira sobre várias tesouras — a tesoura **interior** recebe as duas meias-cargas dos tramos vizinhos (R = w·esp no mesmo modelo biapoiado-por-tramo que a flexão já adota), e o módulo usava R = w·esp/2. Metade do apoio interior: a utilização medida passou de 0,113 para 0,227, o dobro exato. Agora os dois casos são verificados e governa o pior — a ponta leva meio tramo, mas na extremidade da peça, onde o αn cai para 1.
- **A classe da chapa era opinião.** A 7.3 classifica por espessura (fina ≤ 0,5d, grossa ≥ d, interpolar no meio) e `config_73` era string livre: declarar "grossa" numa chapa fina dava os modos c/d/e, mais resistentes. Passa a exigir `t_chapa_mm` e a **medir** — com a exceção correta, que a chapa central de dupla seção vale "de qualquer espessura".
- **A elevação da alvenaria não desenhava — e era XML válido (pré-existente, G62).** `elevacao_paredes_svg` abria a folha com `abre_svg(W, 100)` e remendava o cabeçalho **por string** no fim. Os remendos de `width` e `viewBox` procuravam `"100"` num cabeçalho que já saía com `1100.0`: **nunca casavam** — o filtro de nome morto do PR #40. Só o `height` casava, e a folha ia para o disco com `height="2477"` e `viewBox="0 0 1100 100"`: o desenho esticado ~25× e cortado fora da área visível. Todas as guardas passavam porque leem **atributos**, não pixels, e nenhum teste renderizava. O cabeçalho passa a sair no fim, com as medidas reais (a largura vira 1126, valor que o remendo morto jamais aplicou). Guarda nova: a folha declara `viewBox` igual a `width`/`height` **e** que contém o maior x/y desenhado — vermelha por injeção do emissor antigo. Achado **renderizando**, no lote seguinte ao que o introduziu.
- **E, com a folha finalmente desenhando, a faixa de ajuste cobria o Nd/NRd.** A faixa de respaldo é desenhada *acima* do topo da parede e ninguém reservou a altura: ela subia sobre a linha que traz os números da verificação. Reservada; guarda geométrica compara o y do texto com o y da faixa, parede a parede.
- **Renderizar-e-olhar na prancha da tesoura.** O teste abria a folha e conferia duas substrings. Olhando o PNG: a coluna “Situação” repetia o veredito **global** nas cinco linhas — um telhado com uma barra reprovada carimbava REPROVA nas quatro que passam — e “Volume (m3)”, que é o telhado inteiro, ficava ao lado de “L/tesoura (m)” sem dizer qual é qual. Corrigidos os dois: situação por peça (derivada de `barras` + `terca`) e o título “Volume total (m3)”.
- **O censo do G69 era um baseline de um sentido só (D87).** A lente procurava apenas os 15 nomes que já esperava, nos 8 módulos que já conhecia, e só perguntava "sumiu alguma?". Guarda nova entrava verde — e entrou: `desenho_alvenaria.confere_vergas`, criada pelo **G70 no mesmo lote**, era invisível para o **G69 do mesmo lote**. O censo passa a varrer a árvore inteira e a cobrar os dois sentidos (17 guardas), com um segundo teste exigindo que a triagem escrita e o baseline falem da mesma lista.
- **A nota "a" da Tab. 9 entrava por default (pré-existente, G61).** Ela troca o teto de esbeltez de 24 para 30 **e** o γm de 2,0 para 3,0: muda o veredito. Medido: he/te = 27 sai `reprovado` sem a nota e `aprovado` com ela — e `estrutura_casa` assumia `True` (G61), depois `n == 1` (G67), contra a regra que o próprio G60 escreveu ("opção declarada, nunca silenciosa") e que a primitiva respeita (default `False`). Passa a ser declaração obrigatória, com recusa nomeada; e declará-la num sobrado é incoerência recusada — depois do vento, que é a fronteira mais funda.
- **E o baseline do G51 mordeu na suíte completa.** O G67 reescreveu o cabeçalho de `alvenaria_estrutural` (entraram 11.4 e o vento por nível) e a **quebra de linha mudou**: a lente chaveia por `declaracao[:70]`, então nasceu uma chave nova e a antiga sumiu sem que `sumidas` acusasse — nenhuma das duas era guarda de verdade, os "números" [9; 10,1; 2; 2] são *referência* (Tab. 9, 10.1.2, Tab. 2), não faixa de fpk. Triada com o motivo medido nesta revisão: he/te = 24,55 sai `OK=False` com `esbeltez_acima_do_teto` (teto 24, ou 30 com a nota "a") — reprova, não satura. Fica anotado que **reescrever um comentário rotaciona chaves** dessa lente.
- **Guardas:** 10 testes novos no G66 (todos por relação, com o par vermelho-por-injeção dentro), 1 no G61 (a nota "a" medida nos dois vereditos), 2 no G69 (censo nos dois sentidos + triagem escrita × baseline).

## D98/G71 — o telhado voa: sucção e uplift na tesoura (2026-09-08) — FECHADO
Toda conferência normativa foi feita **na página**: NBR 6123 Tab. 5 na p. 15 do PDF (renderizada — a extração de texto entrega só o entorno, os valores são imagem), cpi na 6.2.5/6.2.6 pp. 12–13 (texto), NBR 8681:2025 Tab. 1/Tab. 2 p. 14, 5.1.3.1 p. 12, 5.1.4.2 e Tab. 4 p. 15 (texto).
- **Entregue.** `telhado_casa_madeira` com `spec["vento"]` declarado (v0, categoria, classe, s1, s3, h_edificacao_m, cpi + cpi_origem): cpe de duas águas pela Tab. 5 com **bloco pelo h/b** (não o bloco do galpão), q com S2 da Tab. 1 (o mesmo `s2_factor` do galpão), pressão líquida (cpe − cpi)·q normal à água, dois casos (transversal α = 90° por água + longitudinal α = 0° simétrico com EG), três análises características (G, Q, W) combinadas por superposição — 1,4·(G+Q) ao lado de 0,9·G + 1,4·W (Q favorável = 0). Cada barra guarda (Nd_grav, Nd_uplift) e é verificada nos dois; ancoragem contra o arrancamento (sem peça declarada, reprova nomeando); terça sob momento invertido com o L1 da borda inferior (sem ele, reprova); descida com W de sucção + arrancamento por tesoura/total realimentando pilares (N_telh_arr), linhas (telhado_alivio_por_linha_kN), gate, memorial e prancha (linha de uplift/ancoragem ou "cadeia gravitacional").
- **A casa térrea não usa os números do galpão.** O galpão (h/b = 0,6, bloco 1/2–3/2) tem GH = −0,60; a casa térrea cai no bloco h/b ≤ 1/2, onde GH = −0,40. Fixar o bloco do galpão seria número de memória com carimbo de tabela — o bloco entra pelo h/b declarado e o teste confere os dois blocos contra a página e contra `vento_nbr6123.cpe_telhado`.
- **0,9 favorável, lido contra a vigente.** A NBR 8681:2025 Tab. 1/Tab. 2 (p. 14) traz permanente favorável = **1,0** (a 2003 trazia 0,9). Adotado 0,9 como **extremo estrito declarado** (menos estabilizante = mais arrancamento = conservador), com a fonte dita em `combinacoes` e no resultado (G_FAV). 5.1.3.1 (p. 12) exige os dois conjuntos (desfavorável + favorável); 5.1.4.2 (p. 15) zera a variável favorável; Tab. 4 dá o vento 1,4.
- **A guarda pedida mordeu nas duas injeções.** Sucção aplicada sem sinal (o bug `_wind_unico`): 5 testes vermelhos (inversão de sinal, par sem flip, ancoragem que deixa de ser exigida, descidas zeradas). Ancoragem bypassada: vermelho (quebra com KeyError — o gate é estrutural, não enfeite). Baseline no outro sentido: brisa (v0 = 5) não inventa arrancamento.
- **Medido na fixture.** v0 = 45, cat. III, q = 0,862 kN/m², cpi +0,8: 11/13 barras trocam de sinal (banzo inferior de +16,97 para −14,39 kN), arrancamento 9,87 kN/apoio (ancoragem 30 kN, util 0,33), terça inverte (w_d = −2,75 kN/m) e reprova com L1_inf = 6,0 m > 3,46 m da 6.5.6-b — e atende com L1_inf = 2,0 m.
- **Fora do escopo nomeado:** Cap. 9 da 6123 (dinâmico) e +2 águas, ambos `not_available` com motivo em `motivos_escopo()`.
- **Guardas:** 15 testes novos no G71 (relações + par vermelho-por-injeção dentro, ambos os sentidos); G66 segue verde (33).

## D99/G72 — o telhado entra no BIM: IfcMember/IfcBeam + federado + clash (2026-09-08) — FECHADO
O comando trazia "o último é D97"; conferido na árvore, o último é D98 — o verbete é D99.
Toda conferência normativa foi feita **na página**: a densidade é a rhom da Tab. 3 p.12 do F136 (via `madeira_nbr7190.propriedades_classe`, a mesma transcrição que o G66 confere célula a célula para C24/D40) — nunca "madeira" genérica.
- **Entregue.** `bim_telhado_madeira.py`: banzos/diagonais/montantes viram IfcMember, terças IfcBeam, material "Madeira {classe} (rho {rhom} kg/m3)" com a classe declarada e a densidade da Tab. 3; `telhado_casa_madeira.escopo()` ganha `bim_ifc: implemented` (a ausência passa a ser nomeada); `bim_instalacoes_casa.membros_federados_casa` inclui o telhado quando calculado e ATENDE — o federado e o clash da casa passam a ver a tesoura contra prumada/eletrocalha do sótão.
- **A guarda do G3 mordeu de verdade.** O default do emissor (`ifc_emit._base_axes` sem hint) põe o montante vertical da tesoura que vence em X com d fora do plano (y=(0,1,0), dot=1 com a normal) — a mesma classe da viga deitada de lado. O membro carrega `plano_normal` e o emissor aceita `ref_hint` (retrocompatível: sem a chave, idêntico); o teste mede os eixos locais emitidos (d coplanar, bf normal) em vez do nome, e o caso sem hint é vermelho por construção.
- **Portão do G8 nos dois sentidos.** `build_federado.solidos()` (disciplina T- = telhado, aditiva) dá a mesma contagem e o mesmo volume exato (bf·d·L) que o modelo puro; o volume medido bate com `vol_madeira_m3` do cálculo (rótulo contra geometria, tol 5e-3). Injeções vermelhas: tirar uma tesoura quebra a contagem, dobrar a terça quebra o volume, material genérico quebra a classe; sem telhado o federado segue sem a disciplina (baseline no outro sentido).
- **IFC aberto, não substring.** O teste abre o .ifc com ifcopenshell e conta `IfcMember`/`IfcBeam` contra o esperado recomputado da geometria, e lê `IfcMaterial` com a classe.
- **Guardas:** 9 testes novos em `tests/test_telhado_bim_g72.py`; G66 (33+), G71 (15), `test_ifc_emit`, `test_bim_edificio` (18) e `test_turnkey_bim` (8) seguem verdes.

## D100/G73 — o no da tesoura em madeira-madeira, lendo a pagina (2026-09-08) — FECHADO
O comando trazia "o último é D97"; conferido na árvore, o último é D99 — o verbete é D100.
Toda conferência normativa foi feita **renderizando o F136** (a extração de texto das fórmulas multilinha sai embaralhada, não ausente — medido nas pp.58-60 do PDF): 7.2 e Rk = Fv,Rk·nsp·nef na p.56, itens a-f nas pp.56-57 (Figs.19-21), Tab.18 (corte simples, Ia-III) nas pp.58-59, Tab.19 (corte duplo, Ia-III) nas pp.59-60, β = fe2,k/fe1,k e o Fax,Rk/4 na p.60, Tab.16 (pré-furação) na p.55 com a 7.1.11 na p.54, Tab.14 na p.53.
- **Entregue.** `madeira_nbr7190`: `_rk_madeira_madeira` (beta, 6 modos no corte simples, 4 no duplo com o 0,5 no Ib central por plano), `verifica_prefuracao_tab16` como portão próprio (prego 0,85·d conífera / 0,98·d folhosa, passante [d, d+1], rosca soberba 0,70·d) e `verifica_ligacao_madeira_madeira` (Rk = FvRk·nsp·nef, Rd com o teto kmod1 ≤ 1 da 7.1.2, Fax,Rk = 0 sem ensaio — conservador e dito na p.60). Reuso sem reescrever: embutimento, My,k, nef, Tab.14 e os portões 7.2 a-f vivem em `_gates_pinos_7190`, que vale igual nas duas ligações. `escopo()` passa `ligacao_madeira_madeira_7.2` a `implemented` (a ausência some do `motivos_escopo`). `telhado_casa_madeira`: o nó sai em madeira-madeira por declaração (`sistema: madeira_madeira` com `n_cortes` numérico 1|2 + `d0_mm`; ambíguo ou omisso recusa com endereço) e a chapa de aço continua disponível (default compatível, nada muda nela); relatório e prancha dizem o sistema, e a linha da ligação na folha mostra apoio e nó separadamente.
- **O cuidado nomeado se confirma e fica guardado.** A p.53 está legível: a2 de prego é (3 + 6·|sen α|)·d (9d a 90°) e o código já a traz assim desde o D97 — o teste do G73 a reafirma para que o Eurocode não volte.
- **O número que muda o veredito.** Na fixture, o corte duplo atende (util 0,29/0,53, governa o modo III do pino) e o simples reprova (util 1,06 no nó crítico, Rk metade exata) — `n_cortes` declarado como número, nunca carimbo.
- **Falha pré-existente documentada, não assumida.** `test_casa_g58_nivelamento.py::test_coordenacao_tem_as_tres_disciplinas` quebra na árvore atual: espera exatamente {estrutura, eletrico, hidraulica} mas o federado entrega `telhado` junto — disciplina que o G72 acrescenta em `bim_instalacoes_casa.membros_federados_casa` (arquivo que este lote não toca; o veredito da mensagem mostra o extra). Mesmo padrão do D95/G60 (diff não-commitado do lote vizinho quebrando o vizinho): não mexido aqui, pertence ao lote dono do diff.
- **Guardas:** 16 testes novos em `tests/test_telhado_madeira_g73.py` (todos por relação, com o par vermelho-por-injeção dentro: o 0,5 da Tab.19, o pré-furo errado, o simples que reprova onde o duplo passa, a folha que diz ONDE); G66, G71, G72 seguem verdes (78 no conjunto); selftest do módulo estendido (beta, 6×4 modos, Tab.16, escopo).

## D101/G71–G73 — a revisão do lote interrompido: o vermelho que o próprio lote declarou (2026-09-08) — FECHADO
O G74 **não chegou a começar** (a interrupção foi antes dele): `escopo()["estabilidade_lateral_6.5.6"]` segue `"dispensa_implementada"` e não há uma linha sobre a 6.6 na árvore. Não havia código pela metade a limpar — o que a interrupção deixou foi um lote não commitado com quatro vermelhos dentro, três deles só visíveis na suíte inteira.
- **O vermelho que o D100 declarou como sendo do vizinho era do mesmo lote.** `test_coordenacao_tem_as_tres_disciplinas` congelava `== {estrutura, eletrico, hidraulica}` e o G72 pôs o telhado no federado. O verbete atribuiu a falha "ao lote dono do diff" — só que o dono é o G72, no mesmo pacote não commitado. É o G69 outra vez, com outro rótulo. E um conjunto congelado também não sabe dizer se o quarto membro entrou por direito: a esperada passa a **sair da spec** (as três do núcleo sempre, `telhado` exatamente quando há `telhado_madeira` declarado), vermelho nos dois sentidos.
- **`except Exception: pass` apagando uma disciplina inteira.** A entrada do telhado em `bim_instalacoes_casa.membros_federados_casa` vinha embrulhada num catch-all: qualquer defeito na geometria da tesoura sumia com a disciplina do federado **e do clash**, e a prancha de coordenação sairia com três disciplinas como se o telhado não existisse — saturação silenciosa com outro nome. O `except` cobre agora só `ImportError` (a retrocompatibilidade que o docstring alega). Guarda nova provada por injeção: repondo o catch-all ela fica vermelha.
- **O censo do G69 mordeu — e é a segunda vez no mesmo padrão.** O G72 criou `confere_modelo`, `confere_volume` e `confere_orientacao` em `bim_telhado_madeira` e nenhuma foi triada. Agora são 20 guardas, com a origem dos dois lados escrita: contagem recomputada da geometria (não lida dos membros), volume medido nos membros emitidos × `vol_madeira_m3` do quantitativo, e eixos locais do emissor × normal do plano declarada — as três INDEPENDENTES.
- **A meta-guarda de cobertura do G51 mordeu junto.** `bim_telhado_madeira.py` produzia zero chaves e não constava da isenção. Triado: é emissor de geometria, a única constante é `TOL_VOL_REL` (tolerância de cross-check, não faixa de norma) e o ρm da Tab. 3 vem de `madeira_nbr7190`, que a lente já varre.
- **Aberto, nomeado, não redesenhado:** o telhado só entra no federado quando `ATENDE`. Um telhado **reprovado** some do clash em silêncio — justo quando a interferência mais importa —, e é a única disciplina com essa condição. Decisão do dono do G72, não da revisão.
- **Suíte:** 28 lotes de processo único, todos com veredito OK, zero vermelhos. A máquina (8 GB, com ~2 GB presos no navegador) derrubou o runner sete vezes; o log de retomada e a limpeza de pytest órfãos entre tentativas foram o que fez a varredura fechar.

## D102/G75 — os defaults que decidiam o veredito: declarar ou recusar (2026-09-09) — FECHADO
O caso que pagou: um `.get(chave, True)` fazia uma parede reprovada passar — a nota "a" da Tab.9 troca o teto de esbeltez de 24 para 30 E o gamma de 2,0 para 3,0 (he/te = 27 sai reprovado sem a nota, aprovado com ela), e o `estrutura_casa` assumia `habitacao_terrea=True` (G61) e depois `n == 1` (G67) enquanto a primitiva defaultava False e o G60 escrevia "opcao declarada, nunca silenciosa". Não é caso isolado: é padrão de fronteira entre módulo cuidadoso e wrapper que o chama.
- **Entregue.** 7 módulos no padrão declara-ou-recusa, cada recusa nomeada com `...nao declarado` (grep-ável): `estrutura_casa` (s1/s3 no vento do sobrado de concreto e no portante via `_vento_cfg_por_direcao`, `material`, `revestimento_cm` via `_revestimento_cm_declarado`, `linhas` do baldrame), `alvenaria_estrutural` (s1/s3), `estabilidade_edificio` (s1/s3), `telhado_casa_madeira` (`forro_fragil`/`n_paineis`/`categoria`), `pavimento_tipo` (`revestimento_cm`), `madeira_nbr7190` (7.2: `t2`/`fe2`/`t_madeira`/`alpha` sempre; 7.3: `t2`/`fe2` só para `chapas_laterais_*_dupla`, `t_madeira`+`alpha` sempre), `viga_baldrame_edificio` (`linhas`+`revestimento_cm`).
- **O mapa de superfície, aprendido no vermelho.** Cada camada recusa no seu idioma: vento-concreto LEVANTA `EntradaEstrutura` (molde G68); alvenaria cai em `gates["alvenaria_portante"]["reprovadas"]` + `fechamento_carga["erro"]`, nunca no top-level; baldrame em `baldrame_erro`; telhado em `EntradaTelhado`. Os 10 primeiros testes do runner saíram no palpite errado sobre onde cada recusa pousa — o vermelho ensinou o mapa, e o mapa ficou escrito nos testes.
- **A lente permanente.** `varredura_defaults_veredito.py` (família AST do G48/G51, sem vocabulário de faixa): casa `X.get(chave, default)` com chave em `NORMATIVAS_G75`; V2 pega o resgate por `or` (`cfg.get(chave) or padrão` mascara a ausência igual — e mascara até o zero declarado). Sem default o sítio sai `OBRIGATORIO`. Baseline nos dois sentidos (regra do G33, molde do test_08 do G51); vermelho por injeção em diretório temporário (lição do D81: sem mutar o repo). Registrada no G51 (`SEM_FAIXA_DECLARADA`: AST de .get, sem número de norma) e na alcançabilidade (`SCRIPTS_AVULSOS`, molde `varredura_descoberta`). O que a lente NÃO cobre está dito no cabeçalho dela (molde DIVIDA-LENTE do G51).
- **A triagem medida (rigor G10).** O que ficou tem número: `combinacao=normal` é o gamma máximo (2,0); `altura=pe_direito` é a carga máxima; `redutivel=False` é carga cheia; `z=h` é o S2 máximo; contraflecha omitida == 0,0 bit a bit; `As=0` não lê Ea (`tipo_bloco` default é morto — só lido onde o caminho armado já exigiu o declarado); punção `alpha=90` é o Hankinson-mínimo; `n_pavimentos`/`n_paineis` via `or` vivem nas camadas de gestão/emissão (a conta usa o n declarado do spec); `linhas=contorno` guardada pela recusa de linha-sem-parede; seções b/h/cobrimento/fck/fyk ditas na folha.
- **Fixtures que materializam o default antigo.** `revestimento_cm` 1,0/2,0, `s1`/`s3` 1,0, `linhas: contorno`, `forro_fragil: false`, `tipo_bloco` onde o caminho armado pede — os valores que o código arbitrava em silêncio, agora escritos no spec; nenhum número novo. `_terrea_g75` sem `fundacao`; `_sobrado_portante_g75` espelha a BASE do G67 em painel único. `project-spec.json` ganha `forro_fragil: false` (o e2e do G66 precisava).
- **Guardas:** 22 testes novos em `tests/test_defaults_veredito_g75.py` (test_01–03 ferramenta+baseline+vermelho-nos-dois-sentidos; test_10–21 um por fix; test_18b o default morto; test_30–35 a triagem medida). G51 (`SEM_FAIXA_DECLARADA`) + `test_alcancabilidade` + G75: 49 passed.
- **Suíte:** batch1 122, batch2 428+2 (os 2: G11 sem `parede_sobre_vigas`/`revestimento_cm` e vento sem s1/s3 — o próprio padrão G75 mordendo a fixture vizinha; corrigidos, 2/2 re-verdes), batch3 72; suíte inteira em processo único: **3381 passed in 6687.44s (1:51:27), zero vermelhos.**

## D103/G74 - o que a dispensa nao cobre: alternativo da 6.5.6 e contraventamento da 6.6 (2026-09-09) - FECHADO
O comando trazia "o ultimo e D97"; conferido na arvore, o ultimo e D102 - o verbete e D103.
Lido na pagina do F136 (PDF com camada de texto + figuras renderizadas e olhadas):
- 6.5.6 p.27: dispensa L1/b <= E0,ef/(beta_M.fm,d) com beta_M Tab.8 (gama_f=1,4, beta_E=4); alternativo tres linhas abaixo p.27: sigma_c,d <= E_c0,ef/((L1/b).beta_M), mesmos Tab.8 e mesmos dados (E_c0,ef = E0,ef da 5.8.7 p.15: E0,med = Ec0,med, E0,ef = kmod1.kmod2.E0,med).
- 6.6.2 pp.28-29: F1d = Nd/150 por no; Kbr,1,min = 2.alpha_m.pi2.E0,ef.I2/L1^3 com alpha_m = 1+cos(pi/m) p.29 (Tab.9 confere: 2/3/4/5/inf -> 1/1,5/1,7/1,8/2).
- 6.6.3 p.29: mesmo para banzo comprimido de trelica/viga (Nd = maxima do banzo ou Rcd; em viga exige rotacao impedida nas extremidades).
- 6.6.4 pp.30-31: cobertura sem analise rigorosa = trelicas verticais (duas diagonais em pelo menos 1 de cada 3 vaos + longitudinais ligando nos homologos, Fig.5) + horizontais/cobertura nas extremidades e intermediarias <= 20 m; por no F1d = Nd/150; extremidade Fd >= (2/3).n.F1d por no (Fig.6 p.30); rigidez Kbr >= (2/3).n.Kbr,1,min p.31.
- **Alternativo da 6.5.6 (madeira_nbr7190.verifica_flexao):** fora da dispensa por L1 (com rotacao impedida), a viga passa a ter resposta calculada: sigma <= E0,ef/(beta_M.L1/b). Sem rotacao segue teoria fora do lote e reprova. Tres testes que esperavam reprova com L1 longo (G66 dispensa a 6 m, G66 terca a 6 m, G71 borda inferior a 6 m) passaram a passar no alternativo com carga leve - atualizados para 10-12 m (onde o alternativo tambem falha) + caso leve que passa; baseline nos dois sentidos.
- **Booleano vira geometria (telhado):** `contraventamento_banzo_inf` (bool) saiu do contrato como `travado_borda_comprimida` saiu: sem numero nao ha L0 nem F1d. Novo `contraventamento_banzo_inf_m` (> 0, distancia entre travamentos do banzo inferior); L0_out = min(spacing, vao) na compressao (6.5) e na 9.3; fixtures G66/G71/G72/G73/G75 e project-spec migradas para 2,0 m (= barra de 2 m, mesmo comportamento gravitacional). Chave antiga recusa com endereco.
- **6.6 do conjunto (telhado.rodar):** Nd_sup/Nd_inf/Nd_gov do equilibrio lancado (max compressao dos banzos gravidade+uplift), F1d = Nd_gov/150, Fd = (2/3).n.F1d, Kbr,1,min do banzo inf (I2 = h.b3/12, E0,ef, L1 = min(spacing, vao), m = vao/L1) e Kbrmin = (2/3).n.Kbr,1,min; ext > 20 m avisa intermediaria exigida (faixa como guarda). Peca de travamento e K real seguem `not_available` com artigo (6.6.2 p.29 secao/comprimento nao declarados; 6.6.4 p.31 K real nao declarado) - escopo nomeia as duas ausencias; gate 6.6 e informativo (sem comparacao carga x carga, sem tautologia).
- **Folha aberta e olhada:** `telhado-tesoura.svg` ganha a linha do contraventamento (F1d/Fd/Kbrmin + "peca nao verificada", parseada no teste, nao substring) e mantem Situacao por peca (diagonal reprovada nao carimba as que passam); relatorio ganha o mesmo quadro. Altura da folha +20 px para a linha nova.
- **Guardas:** `tests/test_telhado_madeira_g74.py` (10 testes): alternativo passa/falha/rotacao, terca longa x muito longa, booleano recusa, espacamento 2 x 8 com uplift (2 passa, 8 reprova barras+9.3 e K cai), forcas como relacao (F1d = Nd/150, Fd e Kbrmin = (2/3).n..., alpha 2/3/inf, ext 10,4 x 22 m), escopo com as duas ausencias nomeadas, prancha parseada. G66 (2 testes) e G71 (1 teste) atualizados para o alternativo. Telhados G66/G71/G72/G73/G74: 89 passed; G51 cobertura+baseline e G75 ferramenta: verdes.

## D104/G76 - as 40 folhas que ninguem olhou: guarda generica + varredura + renderizar-e-olhar (2026-09-09) - FECHADO
O comando trazia "o ultimo e D97"; conferido na arvore, o ultimo e D103 - o verbete e D104.
- **Medido na arvore.** 34 funcoes `*_svg` de folha em 15 modulos (12 `desenho_*` + `compatibilizacao` + `cronograma` + `fotovoltaico`; sem contar `abre_svg`/`colisoes_de_rotulo_svg`, `venv` e testes o numero do comando - 41 em 18 - conta o mesmo conjunto mais os emissores de teste/ajuda). Um unico arquivo de teste renderizava pixels antes deste lote (`test_desenho_laje.py`, que abre o PNG para conferir `fill-opacity`). Os ~20 cabecalhos montados a mao na arvore ja declaram `viewBox` com as mesmas variaveis de `width`/`height` (f-strings `W`/`H`/`Hh`/`Hn`/`Wc`), e `abre_svg` tambem - coerentes por construcao.
- **Varredura do padrao que causou o defeito.** Cabecalho emitido antes de as medidas existirem + remendo por `replace` depois: zero ocorrencias na arvore (`desenho_*.py` sem nenhum `.replace` de `width`/`height`/`viewBox`/`"100"`). O remendo-por-string era unico da elevacao e ja saiu no D97 (cabecalho no fim, largura real 1126). Teste novo `test_varredura_sem_remendo_de_cabecalho_por_string` fica vermelho se o padrao voltar.
- **Guarda generica, sem renderizar (teria pego o caso sozinha).** `desenho_svg_base.confere_folha_svg`: parse XML (nunca substring), `viewBox == width/height` com origem 0 0, e maior x/y desenhado (rect/line/circle/ellipse/text) contido na folha. Vermelha por injecao do emissor antigo (`width 1100.0 x height 2477 x viewBox ... 100` reprova com `viewBox-nao-e-WxH`; rect fora reprova com `desenho-fora-da-folha`) e verde no baseline (folha dentro passa). Aplicada a laje, as duas folhas da alvenaria e a tesoura.
- **Renderizar-e-olhar (Edge headless --screenshot --window-size, sem cairosvg/svglib).** Quatro folhas principais geradas e abertas como PNG: `planta-laje.svg` (legivel: quadro, verificacoes e RESULTADO), `elevacao-paredes.svg` 1126x2540 (as 7 paredes desenham; linha de Nd/NRd legivel acima da faixa de ajuste reservada; verga ao lado do rotulo do vao, sem sobrepor), `planta-fiadas.svg` (amarracao legivel nas duas fiadas), `telhado-tesoura.svg` (tesoura + quadro por peca + linhas de uplift/ligacao/contraventamento legiveis). O estimador `colisoes_de_rotulo_svg` acusa 5 pares na laje e 8 na tesoura onde o PNG esta legivel (linhas do quadro VERIFICACOES e bloco vao/uplift/ligacao/contraventamento + cabecalho da tabela): conservador por construcao (largura 0.6*size por caractere), nao virou guarda - a regra e comparar coordenadas do que o PNG mostra colidir, nunca "parece bom", e aqui nada colide a ponto de ilegivel. Nenhuma guarda geometrica nova alem das duas do D97 (viewBox-contem + faixa-Nd).
- **Guardas:** `tests/test_folhas_viewbox_g76.py` (7 testes): base ok, viewBox antiga reprovada, fora-da-folha nos dois sentidos, varredura do remendo, laje + elevacao/fiadas + tesoura na generica. Suite: `test_folhas_viewbox_g76 + test_alvenaria_bim_pranchas_g62 + test_desenho_laje`: 53 passed.

## D105/G77 - as 28 folhas restantes: censo como portao, e a folha que tinha altura fixa (2026-09-09) - FECHADO
O G76 construiu a lente e a aplicou a 4 folhas de 32. Guarda que ninguem passa nas outras 28 nao impede nada; este lote fecha os dois lados.
- **A lente do censo (`desenho_svg_base.censo_de_folhas`).** AST, nunca substring: `def` de nivel de MODULO terminado em `_svg`, menos `NAO_E_FOLHA` (`abre_svg`, `colisoes_de_rotulo_svg`, `confere_folha_svg` - nomeadas, nao adivinhadas por heuristica). Mede **32 folhas em 14 modulos**, o mesmo numero medido a mao no BACKLOG. O portao (`test_toda_folha_da_arvore_esta_coberta_ou_isenta`) exige censo == cobertura, **nos dois sentidos**: folha nova sem caso fica vermelha, e caso apontando para folha que sumiu tambem. `ISENTAS` esta **vazio** - manter assim obriga folha nova a vir com caso ou com motivo escrito.
- **Vermelho por injecao, em diretorio temporario** (licao do D81: nunca mutar o repo): um `desenho_ficticio.py` com `planta_nova_svg` e acusado; apagado o arquivo, o censo volta a `{}`. Mais o baseline do que NAO conta: `def` aninhado dentro de outra funcao e arquivo `test_*.py` ficam de fora.
- **As 32 folhas emitidas de verdade**, de fixtures reais (galpao eletrico/incendio/hidraulica/climatizacao, predio do spec persistido, galpao de concreto, casa de alvenaria, casa residencial completa, eletrica residencial 6B, telhado, coordenacao/compatibilizacao/cronograma/fotovoltaico/piso). Nada sintetico onde havia caso real a mao.
- **O DEFEITO que a varredura achou - `desenho_concreto.prancha_armacao_svg` com `Hn = 380` FIXO.** A secao cresce com a peca: pilar de 90 cm = 315 px de altura, e a **cota de largura** (desenhada em `y0 + h + 16`) caia em **y = 383,5**, fora da folha. O numero era emitido, valido no XML, contado por toda guarda de atributo - e **invisivel na folha entregue**. A guarda que existia (`test_tudo_cabe_no_canvas`, desde a regressao da sapata) olhava **so o X, por regex sobre a fonte**: o Y nunca foi conferido. Agora a altura sai das secoes (`TOPO_SECAO`, `FOLGA_COTA`, `ALTURA_NOTA`, `_exige_gancho_135` extraido para ser lido ANTES do cabecalho - remendar cabecalho depois foi o defeito do G76). Folha de 380 fixo -> 409 no caso do pilar de 90 cm e 339 no de 70 cm.
- **Por que passou despercebido:** dependia da fixture. Com pilar de 70 cm a cota cabia (`y = 337,5 < 380`); com 90 cm, nao. O teste-guarda novo mede exatamente isso - a peca alta estoura a altura antiga e a baixa nao.
- **Legenda x desenho (renderizar-e-olhar, `desenho_incendio.planta_seguranca_svg`).** A planta e' count-driven; a legenda era uma **lista fixa de 10 itens**. Sem hidrante projetado a folha entregue anunciava o simbolo de hidrante, e o leitor procurava na planta um equipamento que ninguem dimensionou. Mesmo para chuveiro (N=0) e para detector LINEAR, desenhado como feixe tracejado e legendado com o simbolo pontual. A legenda passa a sair do conjunto `desenhado`, montado junto de cada laco (nao numa segunda descricao que envelhece), com a caixa acompanhando o numero de itens - o criterio que `desenho_coordenacao` ja aplicava as suas disciplinas.
- **Um teste CRISTALIZAVA o defeito.** `test_planta_sem_sprinklers_nao_quebra` exigia `"Chuveiro" in svg` num galpao SEM chuveiro, comentado como "legenda existe". Reescrito para medir os dois sentidos (com equipamento a legenda traz; sem, nao traz), mais um teste novo so para a legenda. Mesma familia do "inventei AR300 e criei teste que cristalizava o erro".
- **Folha valida e VAZIA tambem reprova.** `test_folha_nao_sai_em_branco`: descontados o fundo branco (rect do tamanho da folha) e o titulo, tem de sobrar conteudo. Passa igual numa folha de TABELA (armacao de vigas, quase so texto) e numa de GEOMETRIA (tesoura, quase so linha) sem virar tautologia.
- **Dois enganos MEUS de fixture, uteis como achado:** `prancha_armacao_vigas_svg` recebe `vigas_verificacao` (7 linhas / 17 tramos do G34) e nao `pavimento` - com o dict errado emite a tabela **vazia** dizendo "0 linhas / 0 tramos VERIFICADOS", sem reclamar; e `coordenacao_svg` le `p1`/`p2`, nao `bbox` - com a chave errada cai em "sem geometria federada". Ambos ficam anotados no proprio registro.
- **Renderizado e olhado** (Edge headless): armacao do galpao (a cota "40" agora aparece), armacao de vigas do predio (17 tramos legiveis), unifilar, planta de seguranca (legenda de 9 itens, cada simbolo ocorrendo no desenho), elevacao da alvenaria, rede de agua do predio e planta eletrica residencial. **Observacao aberta, nao redesenhada:** a planta de agua do pavimento-tipo desenha um unico ramal num pavimento vazio - e' o que foi dimensionado, mas a folha e' magra; decisao do dono da hidraulica, nao da varredura.
- **Suite:** 288 verdes nos modulos de desenho e consumidores diretos; 70 no proprio `test_folhas_g77`.

## D106/G78 - a casa ganha a planta baixa: layout canonico, cross-check e triagem (2026-09-09) - FECHADO
O comando trazia so G78; o ultimo verbete conferido na arvore e D105.
Medido: PE-AR-01/02/03 prometidas, 32 folhas no censo e nenhuma de arquitetura; a planta baixa pulava com posicoes_dos_ambientes_nao_declaradas - motivo falso para o spec persistido, que declara os 7 comodos com x/y/width/depth sob turnkey.eletrico.circuits.layout.rooms (os mesmos 7 nomes do programa; a eletrica residencial ja desenhava esses retangulos). Cross-check inedito confirmado: area do programa x area do layout batiam nos 7 comodos - e nada conferia isso.
- **Onde o layout mora (canonico).** turnkey.arquitetura.layout e o dono; turnkey.eletrico.circuits.layout.rooms segue existindo (quadro + posicoes de pontos sao eletricos) como ESPELHO. Com os dois declarados, cada retangulo tem de ser o mesmo (tolerancia de digitacao TOL_GEOM_M); o que diverge recusa com o endereco do canonico (molde do G74: layout_eletrico_diverge_do_canonico, comodo_canonico_ausente_no_espelho e comodo_do_espelho_ausente_no_canonico, todos com canonico=turnkey.arquitetura.layout) e bloqueia o eletrico. Sem canonico, vale o fallback eletrico com a proveniencia registrada. project-spec.json migrado (7 rooms copiados do espelho, byte a byte); manifesto e IFC passam a dizer arquitetura.layout.
- **Uma tolerancia para a mesma pergunta.** layout_ambientes.TOL_AREA_REL = 1e-3, a mesma de arquitetura_residencial (area x LxC) e de bim_casa_residencial.TOL_REL (rotulo x geometria); o teste trava as tres iguais para nao envelhecerem em silencio. conferir_areas_programa_layout (programa x layout, por ambiente, com os dois numeros no por_ambiente) e a conta unica: casa_residencial.conferir_geometria_layout delega a ela (forma preservada para a conferencia NBR 5410) e a planta so desenha com ela ok - divergente nao sai, sai skipped com o codigo.
- **PE-AR-02 de verdade.** planta_baixa_svg(arquitetura, layout): um retangulo por comodo posicionado, nome, dimensoes declaradas, area DO PROGRAMA, cotas gerais do envelope e o quadro programa x layout desenhado na folha; paredes/portas/janelas/cobertura ditas fora do escopo NA FOLHA (nada inventado). Passa em confere_folha_svg; renderizada e olhada no Edge headless (7 retangulos legiveis, cotas 10,40 x 8,00 m, quadro 7x7 batendo). Count-driven: rects com fill proprio == ambientes do programa; dimensoes e cotas reconferidas no teste a partir do JSON, nunca do SVG (sem tautologia).
- **PE-AR-01/PE-AR-03 triadas, nao implementadas.** Implantacao precisa de site.lote (dimensoes, recuos, orientacao); cortes de niveis (soleira/terreno) alem do pe-direito. O spec nao declara nenhum - e mesmo declarado ainda nao ha emissor: not_available com o dado nomeado (motivos_arquitetura_faltante, que le site na raiz do spec, onde o normalize o carrega). Nada arbitrado: recuo e soleira inventados seriam a geometria inventada que o modulo recusa na propria abertura.
- **Laco indice-disco.** _PRANCHA_ARQUIVO_CASA (PE-AR-01/02/03 -> arquivos) + conferencia no hook apos gerar: toda PE-AR emitida ou nomeada em skipped (molde do edificio no G56, forma dict da casa preservada). gerar_desenhos_casa(result, out_dir, turnkey=None, site=None): assinatura compativel (chamadas diretas sem turnkey caem no espelho validado).
- **Guardas:** tests/test_planta_baixa_g78.py (14 testes): tolerancia unica, cross-check nos dois sentidos + ambiente sem retangulo, canonico (passa, diverge-com-endereco, fallback, bloqueio no Loop), planta (guarda, drawing-vs-data com fonte independente, recusa de divergente em tmp_path, motivo antigo sem layout), triagem nos dois sentidos, laco indice-disco no Loop. FOLHAS ganha desenho_casa_residencial.planta_baixa_svg (censo: 32 -> 33). G4 (lista de pranchas + motivo) e G8 (proveniencia arquitetura.layout; sem-layout tira os dois) atualizados por merito.
- **Suite:** test_planta_baixa_g78 (14) + test_folhas_g77 (72, com a folha nova) + g4/g8 (47): verdes.

## D107/G86 - o telhado reprovado entra no federado, carimbado (2026-09-09) - FECHADO
O comando trazia so G86; o ultimo verbete conferido na arvore e D106.
Medido (reproduzido antes de decidir): telhado com carga absurda (telha 5,0 + sobrecarga 5,0) reprova de verdade (ATENDE=False, reprovados=[barras, tercas, ligacoes, apoio_madeira]) mas entrega geometria completa (5 pecas, vol 1,99 m3, 6 tesouras, vao 8,0 m) - e `membros_bim` devolvia [] (0 membros), o federado ficava so ['estrutura'] e o clash com 45 membros em vez de 128 (83 barras sumidas). O escopo dizia `telhado_madeira: not_available` e o memorial "[A CONFIRMAR: ... fora do escopo.]" - o veredito ruim sumia em quatro superficies, justo quando a interferencia mais importa.
- **Decisao: opcao (a) - entra sempre quando calculado, carimbado REPROVADO.** O clash e sobre ocupacao fisica, e a geometria (secoes adotadas, posicao) existe nos dois casos. A opcao (b) (nunca entrar) destruiria o clash dos 83 membros mesmo no caso bom e contrariaria o G72. O precedente contrario aparente (fundacao sem geometria -> skip, bim_edificio.py:417) nao se aplica: la nao ha peca a emitir; aqui ha. E todo o resto ja fazia (a): a folha carimba REPROVA por peca (desenho_casa_residencial), o orcamento mede a madeira sem gate de ATENDE (gestao_casa._madeira_telhado), o memorial da gestao carimba ATENDE/REPROVA - o federado era o unico que sumia.
- **Entregue.** `bim_telhado_madeira.membros_bim`: o gate passa de ATENDE para calculado (dict com vao_m + n_tesouras); cada membro carrega `situacao` (ATENDE/REPROVADO lido do calculo, nao dos membros - sem tautologia). `bim_instalacoes_casa.membros_federados_casa`: inclui quando calculado; geometria incoerente continua estourando (G74 intacto). `estrutura_casa`: escopo `telhado_madeira` implemented quando calculado sem erro (antes exigia ATENDE) e `_linha_telhado_memorial` diz REPROVA com os gates nomeados em vez de "fora do escopo".
- **Guardas:** `tests/test_telhado_federado_g86.py` (7 testes): reprovado entra carimbado, mesma geometria do ATENDE (contagem do caso bom como fonte independente + confere_volume rotulo x geometria), reprovado no clash (n_membros cresce), escopo + memorial proprios, IFC do reprovado aberto e contado, ATENDE segue carimbado, sem-telhado segue ausente. Sensibilidade provada: sob o gate antigo o reprovado nao entra (vermelho); sob o novo entra (verde). Sem folha nova, sem SVG tocado: parse/render nao se aplicam.
- **Suite:** g86 (7) + g72 (10) + g66/g58 (67) + g71/g73/g74/g75 (63) + coordenacao (9) + folhas_g77 (80) + pipeline/g84/g83 (10): verdes.

## D108/G89 - os portoes do proprio repo estavam vermelhos, e um deles desde o G77 (2026-09-09) - FECHADO
O lote G78-G88 estava inteiro na arvore e **nao commitado** (a armadilha do G74 outra vez).
Suite completa antes de mexer: **3563 passed, 6 failed**.
- **1 dos 6 nao era do lote, e foi reproduzido antes de ser culpado.**
  `test_g19_quarto_caso_1_comando_output` deu `TimeoutExpired` em 900 s na suite e **passa
  isolado em 285 s**: eu havia rodado os pipelines das tres tipologias em paralelo com o
  `-n auto`. Artefato de carga, nao regressao (receita do D81: reproduzir no cenario limpo
  antes de atribuir ao lote).
- **desenho_terraplenagem era ILHA.** O G79 entregou os dois emissores, com guarda e
  registro em `FOLHAS`, e parou ai: nenhum adaptador os importava. `_PRANCHAS["terraplenagem"]`
  prometia PE-TP-01/02 e o disco recebia zero. A propria `test_alcancabilidade` acusou -
  o criterio de aceite do goal ("passa em confere_folha_svg, entra em FOLHAS") foi cumprido
  ao pe da letra e o laco indice<->disco ficou aberto. **Licao de contrato: "a folha esta
  certa" e "a folha sai" sao dois aceites, e o segundo nao se deduz do primeiro.**
  Ligadas em `entregaveis_projeto.emitir_obras_sitio`, de onde o dado ja sai calculado
  (reuso de `_frente`, sem helper novo); frente ausente **nao vira folha vazia**.
  Guardas novas em `test_terraplenagem_pranchas_g79.py` (3): as duas folhas no disco +
  no manifesto + `confere_folha_svg`; so-a-grade emite so PE-TP-01; e a aresta de import
  medida por AST. **Vermelho por injecao provado:** arrancada a ligacao, 2 dos 3 ficam
  vermelhos; restaurada, 13 verdes.
- **O portao do G77 estava vermelho desde o proprio commit `fb53107`, e ninguem viu.**
  `test_09_cobertura` tem dois asserts em sequencia (`faltando`, depois `sobrando`); o
  primeiro mascarava o segundo. Com os 3 modulos novos isentos, apareceu o real:
  `desenho_svg_base.py` **produz** chave e a isencao dele virou **nome morto**. A chave e a
  linha 229 - o comentario "A guarda acima so vale para a folha em que alguem a chamar",
  que casa com `VALIDADE_RE`. Provado no HEAD (a lente e o arquivo do HEAD casam). O
  cabecalho da lente **proibe** reescrever comentario para agradar a expressao (G64), entao
  a correcao foi **tirar a isencao**, nao a prosa. **Licao: assert em sequencia esconde
  achado - o segundo so aparece quando o primeiro fecha.**
- **G87 x G66: a assercao que envelheceu.** `test_e2e_orcamento_cobre_a_madeira_e_nao_e_parcial`
  exigia `"ORCAMENTO PARCIAL" not in texto`, juntando "nenhum insumo DA TABELA sem
  quantidade" (o que o G66 quis provar) com "o orcamento esta fechado". O G87 separou os
  tres estados e a casa **tem** sistema fora da tabela (alvenaria, revestimento, esquadria):
  o carimbo esta certo, a assercao e' que estava errada. Reescrita para exigir que o
  parcial, quando aparece, seja **pelo que esta fora da tabela e nomeado** - nunca por
  buraco na tabela; o intent do G66 segue coberto por `sem_quantidade`/`cobertura_pct`.
- **Baselines atualizados com triagem, nao com numero novo.** `TRIADAS_G69` ganha 4 guardas
  (fundacao e escada = drawing-vs-data INDEPENDENTE; `confere_cobertura_galpao` = meta-guarda
  de contrato disco x indice, familia do item 16; `confere_folha_svg` = continente x conteudo,
  no censo desde o G76 e so agora triada) e a contagem do cabecalho passa de 20 para 24.
  `BASELINE_G75` ganha o par `gestao_edificio.n_pavimentos` (1 -> 2 no `get`, + o `or`):
  os dois lados sao dado declarado e o resultado alimenta **so o texto do motivo** - caso (a),
  fica.

## D109/G79 - terraplenagem calculava e nao desenhava (2026-09-09) - FECHADO
`terraplenagem.py` ja tinha `volumes_corte_aterro`, `greide_equilibrio`, `movimento_terra`,
`vazao_racional`, `canaleta_manning` e `dimensiona_drenagem`; `_PRANCHAS["terraplenagem"]`
prometia PE-TP-01/02 e o arquivo nao tinha **uma unica** funcao `*_svg`.
- **Entregue:** `desenho_terraplenagem.py` com `mapa_corte_aterro_svg` (mapa da malha por
  celula + greide de equilibrio cotado) e `planta_drenagem_svg` (canaletas com Q, largura,
  declividade, n de Manning). Ambas **count-driven** (um rect por no da grade; canaletas
  desenhadas == dimensionadas), pela armadilha medida da planta de incendio que desenhava
  `cols*rows != N`.
- **Nada assumido:** empolamento ausente sai `"... nao declarado"`, nunca 1,0 silencioso; o
  n de Manning omitido sai rotulado `(default, nao declarado)`. Canaleta insuficiente
  carimba REPROVA na folha e o `>OK<` **nao** aparece.
- **O que ficou aberto e foi fechado no G89:** os dois emissores nao eram importados por
  nenhum adaptador - eram **ilha**, e o disco recebia zero. Ver [[04-decisions#D108]].

## D110/G80 - a fundacao do predio ganha folha (2026-09-09) - FECHADO
`fundacao_edificio.dimensiona` cobre **todos** os pilares (geometria, momento na base,
sapata de divisa, viga de equilibrio, baldrame, recalque) e o mapa de pranchas do
`edificio_adapter` tinha 13 codigos, **nenhum de fundacao**. A unica sapata desenhada na
arvore era um detalhe dentro da armacao do galpao pre-moldado.
- **Entregue:** `desenho_fundacao_edificio.planta_fundacao_svg` - PE-CO-04, locacao/formas
  na malha de pilares, com dimensoes, cota de apoio e carga de projeto por elemento.
  `confere_desenho_fundacao` faz drawing-vs-data por **parse**: `<rect data-pilar>` contra o
  `por_pilar` do calculo (o esperado nunca vem do SVG).
- **A entrada no indice e parte do entregavel:** `_PRANCHAS["concreto"]` ganhou
  "Locacao e formas da fundacao". Sem ela a folha **evaporaria** no `continue` do indice -
  o D89, que ja aconteceu com a fundacao no G56 e a alvenaria no G62.
- **Nao arbitrado:** a tensao admissivel do solo continua sendo declaracao; o framework nao
  tem default e isso e intencional. A validacao de sistema contra laudo SPT externo segue
  bloqueada por fonte (T44) - o que **nao** bloqueia a folha: aqui se desenha o calculado.

## D111/G81 - a escada sai do quadro de texto e vira folha (2026-09-09) - FECHADO
A escada tinha calculo proprio (Blondel, lances, patamares, largura pela 9077 - declaracao
unica desde o G12) e aparecia **so como texto** no quadro do PPCI.
- **Entregue:** `desenho_escada_edificio.planta_escada_svg` - PE-IN-03, planta e corte com
  espelho, piso, degraus por lance, patamares, largura exigida x adotada e Blondel visivel.
  Um `rect` por degrau; `confere_desenho_escada` confere contagem e medidas contra
  `escada_concreto.dimensiona` + os gates do incendio.
- **O `A CONFIRMAR` ficou visivel, nao fechado.** O comprimento do patamar segue igualado a
  largura do lance porque a 9050/9077 nao traz o valor na base (ver `04-decisions.md:631`).
  A folha carimba isso e cita o minimo; **nao** se arbitrou o numero.
- `_PRANCHAS["incendio"]` ganhou o codigo (mesma razao do D110).

## D112/G82 - a hidraulica: 3 codigos, 1 arquivo, e o motivo escrito (2026-09-09) - FECHADO
O indice promete PE-HI-01/02/03. O **predio** cumpre os tres com tres arquivos; o **galpao**
tem um emissor so, que desenha as tres redes na mesma folha - e ninguem sabia que 1 arquivo
respondia por 3 codigos.
- **Decisao de contrato (nao calculo novo):** no galpao terreo, sem prumadas, **um** arquivo
  (`esquema-hidraulica.svg`) **cobre** os tres titulos, e isso fica escrito em
  `desenho_hidraulica.COBERTURA_GALPAO` + `confere_cobertura_galpao`, que devolve os codigos
  cobertos e os pulados **nomeados**. Separar seria copiar o mesmo retangulo tres vezes.
  No predio segue 1:1. O que nao servia era o silencio.
- **Triagem da folha magra da agua (aberta no G77):** `planta_rede_edificio_svg(rede="agua")`
  desenha um unico ramal porque **e o que foi dimensionado** - uma coluna servindo todos os
  pavimentos. Numero de prumadas e ramais por aparelho dependem da planta de arquitetura,
  que o framework nao tem para o predio. Desenhar mais seria **geometria inventada** (a
  armadilha nomeada no G78). **Veredito: folha mantida, o escopo diz por que.**

## D113/G83 - a varredura das guardas de um eixo so (2026-09-09) - FECHADO
O G77 achou uma guarda que media **so o X** (`test_tudo_cabe_no_canvas`, regex sobre a fonte
do SVG, 4 coletas de x/cx/x1/x2 e nenhuma de y). O defeito que ela deixou passar por anos: a
cota de largura do pilar caia **3,5 px abaixo** da folha, invisivel no entregue.
- **Ferramenta:** `varredura_guardas_um_eixo.py` (AST, familia do G48/G51/G75) mede tres
  sinais sintaticos - X_ONLY (e o espelho Y_ONLY), W_SEM_H (e H_SEM_W) e
  REGEX_COORD_SEM_PARSE (coordenada extraida por `re` sem nenhum parse no corpo). Regex
  sobre **rotulo** nao e coordenada e nao entra: checar texto nao e medir geometria.
- **Promocoes, sem apagar a guarda antiga** (o goal dizia "complete-o, nao o apague"):
  `test_tudo_cabe_no_canvas` ganhou o eixo Y + `ET.fromstring` + `confere_folha_svg`;
  `test_planta_cabe_no_canvas` ganhou parse + `confere_folha_svg`.
- **Triagem item a item, com motivo medido** (rigor G10): so os 2 de `desenho_concreto`
  viraram correcao; os demais ficaram com o motivo pelo qual **nao** sao bug (guarda
  legitimamente unidimensional - o eixo X e o objeto da guarda). O que a lente nao cobre
  esta dito no cabecalho, no molde DIVIDA-LENTE do G51. Baseline `BASELINE_G83` nos dois
  sentidos.

## D114/G84 - declara-ou-recusa nos 4 modulos com mais A CONFIRMAR (2026-09-09) - FECHADO
Medido fora de testes: `galpao_hidraulica` 16, `piso_industrial` 14, `secundarios_nbr8800` 13,
`montagem` 13. **O goal nao era zerar a contagem** - `A CONFIRMAR` e a forma honesta de nomear
dado do projetista, e este repo prefere isso a arbitrar.
- **O achado de metodo:** a lente do G75 **nao via nenhum sitio** nos quatro (0 de 101). O
  vocabulario dela era estreito demais para esses modulos. Estendido com 24 chaves: **101 ->
  152 sitios**, e cada um triado com numero.
- **Triagem (a) fica / (b) vira calculo / (c) vira recusa**, sempre com a medida do efeito:
  `i_pluvial_mm_h=150` decide o DN (100 -> DN125, 200 -> DN150) mas **sai flagado**;
  `p_alim_kPa=100` e gate **informativo** quando assumido e **efetivo** quando declarado
  (5 kPa reprova) - o silencio nao existe, esta escrito no gate; `metodo_agua='soma'` e o
  **conservador** dos dois que a 5626:2020 6.14.2 aceita; `decl_esgoto_pct` abaixo do minimo
  da 8160 4.2.3.2 levanta `ValueError` com endereco.
- **Baseline do G75 atualizado nos dois sentidos** com a triagem por escrito, nao com numero
  novo.

## D115/G85 - nove modulos que nenhum teste nomeava (2026-09-09) - FECHADO
Nao eram ilhas (a alcancabilidade estava verde) - eram **suspeitos**: importados por outros,
mas com o nome ausente de todo `tests/`. Um veredito por modulo, e onde se alegou cobertura
transitiva, o **defeito injetado** como evidencia.
- Comecou pelos dois de engenharia pesada, como o goal mandava: **`fogo_nbr14323`** (aco em
  incendio) aferido contra a curva ISO 834 e a Tab. 6.2 - `20 + 345 log10(8t+1)` conferido a
  mao, mais a fisica "protecao reduz a temperatura do aco"; **`distorcional_fsm`** contra a
  simetria da secao Ue e a flambagem de placa da alma (k=23,9, formula fechada) como ordem
  de grandeza do Mcrl.
- Demais: `recalque_edificio`, `junta_dilatacao`, `tercas_iteracao`, `layout_ambientes`
  (que o G78 passou a nomear na mesma semana), `pycufsm_compat`, `smoke_executivo` (so o
  testavel sem FreeCAD: `checar_carimbo` e `_acha_pendente`, com injecao de `__PENDENTE__`
  vazando). **`casa_residencial_sintetica`: decisao do G10 CONFIRMADA, nao redecidida.**
- Cada teste direto vem com par de injecao em memoria (monkeypatch), nunca mutando o repo.

## D116/G87 - o orcamento passa a ter tres estados (2026-09-09) - FECHADO
A guarda do G14 nomeava insumo **que estava na tabela** e ficou sem quantidade; os sistemas
que **nunca entraram na tabela** passavam em silencio. A medida que expos o buraco:
R$ 790 mil / 1134 m2 ~= **R$ 700/m2** contra CUB de R$ 2.500-3.000/m2 - a diferenca e
alvenaria, revestimento, esquadria, impermeabilizacao, elevador e incendio.
- **Tres estados, e o parcial nunca se diz fechado:** "a obra nao tem" (`nao_aplicaveis`),
  "ninguem quantificou" (`sem_quantidade` / `fora_tabela` sem quantidade) e "quantificado
  sem preco" (`sem_preco` / `fora_tabela` com quantidade). `estado_orcamento` publica
  `orcamento_fechado`.
- **Quantificar pelo MODELO, nunca pelo preco.** As contagens do incendio vem de
  `sistemas.totais_edificio` - o que o desenho conta, o orcamento quantifica. Insumo sem
  preco declarado sai **nomeado**, nao chutado; o elevador sai com quantidade `None` e o
  motivo escrito ("nenhum modulo dimensiona o elevador").
- **Efeito colateral de merito:** o carimbo novo derrubou uma assercao do G66 que juntava
  "tabela completa" com "orcamento fechado". Resolvido no G89 - ver [[04-decisions#D108]].

## D117/G88 - a divida de documentacao (2026-09-09) - FECHADO
`wiki/03-phases.md` parava em **S42** enquanto `04-decisions.md` ja estava em **D105**: quem
lesse as fases acreditaria que o trabalho parou ha ~45 goals. Arco **G43->G77** reconstruido
do git, `fontes/fontes-faltantes.md` corrigido (dizia que o telhado da casa estava
`not_available`, falso desde o G66) e o indice passou a apontar para `BACKLOG-GOALS.md`.
**Fechados por medicao, nao reabrir:** as constantes orfas `LAMBDA_BLOCO`/`ALPHA_C`/`XD_LIM`
ja foram renomeadas com sufixo `_C50` no G51; `s_limite_governante` **acrescenta** o rotulo
da NOTA C55-C90 em vez de sobrescrever; a viga continua do predio **e** verificada desde o
G34.

## D118/G96 - o aco executivo precisa do FreeCAD em 11 folhas, nao em 13 (2026-09-10) - FECHADO
Medição prancha a prancha pedida pelo G96, lida no fonte (construtor -> tipo de vista),
não suposta. O executivo de aço é `techdraw_exec.gerar_executivo` (`techdraw_exec.py:1809`,
ordem em `:1849-1873`): 11 construtores com vista + quadros + montagem. **Não existe
`desenho_aco.py`**: os 15 `desenho_*.py` cobrem as demais disciplinas/tipologias; o núcleo
aço só sai via TechDraw. `freecadcmd` NÃO exporta PDF ("Cannot load Gui module" —
`techdraw_exec.py:10`); a exportação exige `freecad.exe` com GUI.
- **Exigem geometria 3D real (11 grupos, DrawViewPart/DrawViewSection):** PE01 cobertura
  (`_pr_cobertura:657`, V01_COB:665 coarse), PE02 fundações (`:684`, V02_FUND:698), PE03
  elevações (`:728`, V03_OITAO:745 + V03_LATERAL:758), PE04 pórtico (`:782`, V04_PORTICO:812
  em HLR cheio), PE05 contraventamento (`:844`, V05_CV_LAT:868 + V05_CV_COB:882), PE06 base
  (`:892`, V06_BASE_FR:937 + V06_BASE_TOP:949), PE07 joelho (`:1041`, V07_JOELHO:1114 +
  `VLIG_SEC_*` DrawViewSection:1267, corte seccionado hachurado), PE08 fechamento (`:1421`,
  V08_FECH:1439 coarse), PE10+ ligações (`_pr_ligacoes:1402` -> `_detalhe_ligacao`: VLIG_ELEV
  DrawViewPart:1343 + VLIG_CHAPA:1354 + VLIG_SEC:1376 — corte de peça e vista projetada de
  conjunto), PE14 croquis (`:1662`, CROQ_* por marca:1702 — shop drawing projetado; o rótulo
  vem do `por_marca` do cfg, a vista vem do Shape), PE15 bloco (`:968`, V15_BLOCO_FR:1011 +
  V15_BLOCO_TOP:1021, com `Part.common` de recorte:997 — só fundação profunda).
- **Desenho 2D puro (2 folhas, só Spreadsheet/Annotation, zero vista):** PE09 quadros
  (`_pr_quadros:1517` — dados do cfg: resultados, por_marca/takeoff/romaneio) e PE16 montagem
  (`_pr_montagem:1731` — só `cfg["montagem"]`). O dado já é puro (`romaneio.py`, `montagem.py`);
  o emissor SVG ainda não existe.
- **Custo medido de cada via.** Via FreeCAD (atual): `_STAGE_WEIGHTS` dá ao aço **7,0**, o
  maior peso (`caderno_turnkey.py:49-59`; teste garante aço > 800 s de 1800 s); o stage divide
  50/50 entre 3D e executivo (`:292-298`); default global 1200 s (`:333`), ≥ 1800 s p/ 6
  disciplinas (COMO-RODAR); HLR é caro por sólido, modelo ~569 (`techdraw_exec.py:14-16`,
  gerais em CoarseView, detalhes em HLR de subconjuntos); em rodada, a tesoura calcula OK mas
  o executivo estoura ~15 min (06-open-threads T13). Via SVG puro: **wall-time não medido** —
  nenhum emissor de aço existe (ausência declarada, não default). Precedente independente:
  `desenho_concreto.py` prova o padrão, e o G94 fixa a rota SVG -> PNG -> PDF (Edge headless).
- **Ressalva que decide o sequenciamento:** hoje até SVG puro paga `freecad.exe` no fluxo do
  galpão — hidráulica/incêndio/climatização têm esquema SVG (`desenho_hidraulica/incendio/
  climatizacao.py`) mas o `montar_pranchas` os embrulha em `freecad.exe` só p/ exportar PDF
  (`galpao_hidraulica.py:337-349`, `galpao_seguranca_incendio.py:172-188`). Migrar PE09/PE16
  p/ SVG só economiza se a exportação sair do `freecad.exe` (fitz como o caderno, ou Edge
  como o G94). E a migração só vale com o contrato de dados honrado: `_notas_do_modelo`
  (`:1462`) mede 3 números no BoundBox do 3D (níveis, gancho, contraventamento) — sem fonte
  para eles no SVG, é saturação silenciosa (regra 4), não economia.
- **Decisão:** SIM, o aço executivo precisa do FreeCAD — para as 11 folhas projetadas, sem
  exceção nem atalho 2D. PE09 e PE16 migram para SVG puro quando (e só quando) houver emissor
  + rota de export sem `freecad.exe` + fonte declarada p/ os 3 números medidos. **Goal seguinte:
  o *harness* de medição por prancha** (ferramenta-antes-de-iterar — nenhuma iteração manual
  de timing foi rodada aqui): processo reiniciado a cada medição (o `freecad.exe` persiste e
  roda o módulo irmão antigo), kill via WMI `Terminate` (taskkill não derruba travado — D64),
  baseline nos dois sentidos. Este goal não produziu código: convenções 1–2 registradas para
  o harness exigir; classificação por leitura construtor->vista (regra 3, sem alegar
  legibilidade nova); comparação contra fonte independente — dual-route do concreto + mapa G93
  medido contra emissão real (regra 5).

## D119/G91 - o indice deixa de ter tres contratos (2026-09-10) - FECHADO
Tres implementacoes do mesmo laco indice<->disco e nenhuma delas ERA o contrato: o predio
confrontava todas as disciplinas do pacote (`edificio_adapter.py:995`, 15/15), a casa so
`["arquitetura"]` (3/3, recorte do proprio escopo) e o galpao nao tinha mapa nenhum.
`varredura_indice_disco.py` e' agora a maquina unica: funcao pura, quatro lados
(`codigos_prometidos`, `mapa_codigo_arquivo`, `nomes_no_disco`, `motivos_escritos`),
tres gaps (`faltando`, `sobrando`, `sem_mapa`). O `_base` normaliza `drawings/<nome>`
(sem isso toda folha emitida pelo predio viraria `faltando`), e `_motivos_validos` recusa
motivo em branco - motivo apagado e silencio, nao triagem. Entrada `None` **levanta**
`TypeError`: lente que devolve `OK` sobre lixo e a saturacao silenciosa vestida de rede de
seguranca. `registro_laco_quebrado` transforma o `except` do predio em funcao chamavel, e
G92/G93 reusam em vez de reimplementar.
**Limite dito aqui, para ninguem confiar no que a lente nao mede:** no portao das tres
tipologias (`tests/test_indice_disco_g91.py:141`) o lado "disco" e' `sorted(mapa.values())`
- derivado do proprio mapa. Aquele portao mede **indice x mapa** (`sem_mapa` e `sobrando`),
nao indice x disco; o lado do disco e' medido em `test_04` (disco furado sobre o mapa real)
e nos portoes por tipologia do G92/G93. A distincao esta escrita porque a convencao 5 e'
exatamente sobre isto: valor de comparacao derivado do resultado nao mede nada.

## D120/G92 - a casa confronta o pacote inteiro, nao o recorte que ela mesma escolheu (2026-09-10) - FECHADO
`casa_residencial._emit_drawings` lia `indice_de_pranchas(["arquitetura"])` enquanto
`gestao_casa.disciplinas_pacote` prometia ao cliente arquitetura + concreto + alvenaria +
hidraulica + eletrico + madeira. O laco conferia um **recorte do proprio escopo** - saturacao
silenciosa (regra 4) na forma de portao, com 13 codigos evaporando no `continue` do indice
(D89) e a suite verde. Agora a fonte e' UMA: `gc.disciplinas_pacote(result)`, a mesma do
pacote. `_PRANCHA_ARQUIVO_CASA` foi de 3 para **17** entradas (a uniao: 3 AR + 4 CO + 2 AL +
4 EL + 3 HI + 1 MD; a rodada sem alvenaria promete 15 e o laco ignora as extras).
`_motivo_folha_casa_nao_emitida` da a cada codigo o **dado que falta com nome** - lote nao
declarado, `estrutura.pavimento` ausente, `alvenaria.por_linha` ausente - nunca "nao
disponivel" sozinho.
**Aberto e medido:** PE-EL-01/02/04 saem declarados como "sem emissor ligado ao hook da
casa", e os emissores **existem e estao provados** (`desenho_eletrico_residencial.
gerar_desenhos_residenciais`, chamado so por `residencial_eletrica.py`). E a mesma classe do
G79/G89: folha certa que ninguem emite. Declarar foi o minimo honesto; ligar e' goal.

## D121/G93 - o galpao troca a contagem pelo codigo nomeado (2026-09-10) - FECHADO
`pacote_no_manifesto` comparava `len(indice_pranchas)` com o numero de artefatos
`kind == "drawing"` (`entregaveis_projeto.py:343`): **numero contra numero**. Um desenho a
mais, de qualquer nome, fechava a conta sem que um unico codigo do indice tivesse sido
conferido - parente da assercao tautologica do D86. `_PRANCHA_ARQUIVO_GALPAO` (19 entradas)
foi medido **contra o que o galpao realmente emite**, pagina TechDraw a pagina TechDraw
(`PE01_FORMAS`, `PE04_PORTICO`, `HID01_ESQUEMA`, `INC01_PLANTA`, `CLI01_ESQUEMA`,
`COORD01_PLANTA`...), nao suposto; a hidraulica mantem o N:1 do G82 (3 codigos, 1 arquivo) e
a lente nao chama isso de `sobrando`. A conta continua no `.md` como informacao ao leitor e
**deixa de ser o portao**.
**Aberto e medido:** `mezanino` esta em `galpao_turnkey.DISCIPLINAS` e **nao** em
`pacote_legal._PRANCHAS` - a disciplina e executada e evapora no `continue` do indice. E o
D89 vivo, do lado da promessa em vez do lado do arquivo. Travado por assert em
`tests/test_indice_disco_g91.py:290`, nao consertado.

## D122/G94 - caderno executivo de casa e predio, e o portao que impede caderno menor que o indice (2026-09-10) - FECHADO
So o galpao entregava caderno consolidado (36 paginas via `caderno_turnkey`); casa e predio
entregavam `.md`/`.json`. `caderno_casa_edificio.py` fecha a assimetria reusando o que ja
existia - `caderno_turnkey._add_pagina_imagem` e `dossie._add_paginas_texto` - com capa e
indice **proprios**, porque `_linhas_capa` espera o `R` do turnkey do galpao e fabricar esse
`R` seria dado inventado. Rota SVG -> PNG -> pagina pelo pixmap do fitz (`doc.save()` direto
sobre SVG falha; sempre pixmap). Duas camadas: `montar_caderno_svg` pura e testavel em CI,
e os dois hooks do Loop.
**O portao:** `n_pranchas + n_declaradas == len(indice)`. Folha prometida sem arquivo **e**
sem motivo reprova o caderno com o codigo nomeado, em vez de sair um caderno menor que o
indice - a forma do G87 (orcamento parcial que se diz fechado) aplicada a prancha. Folha
ausente vira **pagina de declaracao**, nao um buraco.

## D123/G95 - terraplenagem numa rodada real, com a premissa marcada como premissa (2026-09-10) - FECHADO
O G89 ligou PE-TP-01/02 ao Loop e provou com fixture em memoria; nenhum spec persistido
declarava `site.terraplenagem`, entao o caminho estava ligado e **nunca rodava**.
`projects/galpao-tp-g95/` declara os cinco dados e a rodada emite as duas folhas no
manifesto (`obras_sitio.status == "generated"`).
O ponto de metodo: grade topografica, empolamento, C e IDF **nao podem ser declarados sem
levantamento**, e um numero inventado num spec persistido sobrevive ao goal. Por isso o spec
carrega `test_assumptions` com `status: not_real_engineering_input` e
`source: agent_assumed_values`, e o portao **exige a procedencia escrita** - sem ela o teste
reprova. A conferencia dos volumes e' conta a mao na docstring (corte 1120 m3, aterro
1360 m3, Q = 0,325 m3/s), fonte independente do modulo sob teste (convencao 5).

## D124/G97 - o portao que escondia portao (2026-09-10) - FECHADO
`test_09_cobertura_todo_py_varrido_ou_isento` tinha **quatro** asserts independentes em
sequencia (`faltando`, `sobrando`, `sem_motivo`, `ausentes`): o primeiro a estourar impedia
a avaliacao dos outros tres. Foi assim que o portao do G77 ficou vermelho **desde o proprio
commit `fb53107`** sem ninguem ver (D108). `varredura_asserts_sequencia.py` acha a forma por
AST e a receita substituta e' coletar todos os lados, montar uma mensagem so e falhar uma
vez. Aplicada aos portoes existentes (G51, G69, G75, G77, G83) e ao G91.
A isencao que o goal exigia: assert que **depende** do anterior (`assert r is not None`
antes de `assert r["x"] == 3`) e correto e sai com motivo escrito - isencao sem motivo e
silencio, nao triagem, a mesma regra que derrubou o G77.

## D125/G104 - pranchas A1 sem freecad.exe para as tres disciplinas de esquema puro (2026-09-11) - FECHADO
Hidraulica, incendio e climatizacao **nao tem 3D** (o esquema e' SVG do `desenho_*`,
o quadro e' tabela+notas do `config_de_spec`) e mesmo assim cada uma pagava uma
instancia grafica de `freecad.exe` so para carimbar esse conteudo numa A1.
`prancha_svg_direta.py` e' a rota alternativa em Python puro: esquema SVG -> PNG
via pixmap do fitz (`caderno_casa_edificio.svg_para_png`; `doc.save()` direto sobre
SVG falha - G94) -> pagina A1, e quadro+notas verbatim do cfg + carimbo da funcao
propria da disciplina (`_carimbo_hid/_carimbo_inc/_carimbo_cli`, nunca o generico)
em pagina A1 de texto. Reuso, nao reescrita: o conteudo e' o **mesmo** `config_de_spec`
do FreeCAD, e os basenames sao os mesmos das paginas (`HID01_ESQUEMA`, `INC01_PLANTA`,
`CLI01_ESQUEMA` + quadros), entao `caderno_turnkey._coletar_pdfs` encontra sem mudanca.
**Medido** (galpao 40x20x6, processo novo a cada rodada, kill confirmado sem zumbi):
HID 15,25s -> 0,56s; INC 21,09s -> 0,62s; CLI 13,52s -> 0,57s; total ~49,9s -> ~1,75s
(~28x). O esquema-fonte e' byte-identico ao do FreeCAD (mesma funcao), entao "mesmo
conteudo" nao e' promessa: e' `confere_folha_svg` + `ET.fromstring` + `svg_para_png`
no teste, um esquema renderizado e olhado, e o quadro cobrado pelos numeros do
`rodar()` (DN/capacidade calculados, nunca derivados do proprio PDF - convencao 5).
O caminho FreeCAD **continua existindo** (`backend="freecad"` nos tres
`montar_pranchas`; o default virou `"svg"`): este goal nao o remove, e o G105 mede
o aco por cima dessa rota.

## D126/G101 - o galpao: PE-IN-03 sai da promessa sem escada declarada, PE-IN-02 segue declarado (2026-09-11) - FECHADO
Caminho **(b), escrito**: sem objeto escada no spec, a disciplina incendio do
galpao **deixa de prometer** PE-IN-03 em vez de prometer e declarar ausente.
`galpao_adapter._indice_galpao_com_fronteira` tira o codigo do indice e registra
`dispensadas` no manifesto com motivo `not_applicable` escrito (codigo + dado
nomeado: `escada=None` no spec); com escada declarada (`raw_spec`/`turnkey_spec`
com `escada` truthy) o codigo segue prometido — e, sem emissor, sai pulado com
o `_motivo` (ausencia declarada, nao silencio). O portao do G91 reflete a
escolha: dispensada nao e "faltando".
**Medido, sem arbitrar norma**: (1) `desenho_escada_edificio.planta_escada_svg({},
None)` levanta `ValueError: sem 'geometria'` — o emissor G81 exige o shape de
`escada_concreto.dimensiona` + gates de `incendio_edificio` (Tab.10/11); (2)
`galpao_seguranca_incendio.rodar` minimo devolve gates sem nada de escada
(iluminacao/sinalizacao/deteccao/sprinklers/hidrantes); (3) `projeto_spec`
traz `"escada": None` por default (opt-in com `desnivel/projecao/largura`);
(4) `escada.py` do galpao e metalica industrial (`n_espelhos/espelho_mm`,
`patamar_comprimento_m`) — shape incompativel com `geometria.n_degraus/
espelho/piso/patamar_m/largura_m/armadura`. Reuso direto falha nos dois eixos.
**Alternativa (a) rejeitada**: declarar a escada no spec e reusar o emissor
exigiria inventar desnivel, largura, tipo, ocupacao e altura — valor normativo,
e o framework nao arbitra. A fronteira aqui e estrutural (sem objeto, sem
promessa), nao isencao normativa: nenhum artigo e citado e nenhum e inventado;
a NBR 9077 rege saidas/escadas e a IT especifica do CBM local segue A CONFIRMAR.
**PE-IN-02 medido e decidido**: o `rodar()` do galpao calcula tipo/sistema/
N_hidrantes/vazao/reserva, mas nao DN de coluna/rede, tracado vertical nem
pavimentos (o corte DN65 so existe em
`desenho_incendio.detalhes_hidrantes_rotas_svg`, shape do predio com
`gates.rotas_verticais/escada_largura`). Desenha-lo seria inventar dado:
segue declarado ausente com o dado nomeado. Guarda em
`tests/test_galpao_escada_fronteira_g101.py` (7 passed: medicao independente,
baseline nos dois sentidos, rodada stub sem/com escada, vermelho por injecao
em `tmp_path`); G93 (7) e G91 (6) verdes, sem regressao.

## D127/G105 - o harness de medicao por prancha do executivo de aco (2026-09-11) - FECHADO (ferramenta; numero ABERTO)
Ferramenta, nao otimizacao (o D118 pediu exatamente este goal): `tools_harness_aco_por_prancha.py`
(SCRIPT AVULSO) mede por prancha t_build/t_hlr/t_cotas/t_export, um processo `freecad.exe` por
prancha, sempre encerrado via `RP._matar_processo_freecad` (kill -> taskkill /F /T -> WMI Terminate,
D64), agregado em JSON + CSV. Registro de 17 paginas (PE01-PE16 + colisao PE14_DET_CONSOLE x
PE14_CROQUIS pelo nome completo; PE15/PE14_CROQUIS condicionais saem com motivo, nunca zero
silencioso), classe hlr/coarse/2d por prancha (PE09/PE16 sao os controles 2D puros). Portao em
`tests/test_harness_aco_g105.py`: registro x fonte (assinaturas + LIGACOES), BASELINE_G105 nos
dois sentidos, vermelho por injecao em tmp_path (estouro de orcamento, prancha faltando, boot sem
despacho). Numeros por prancha: not_available — nao ha modelo FCStd no disco (verificado: nenhum
*.FCStd em projects/) e orcamento inventado seria dado arbitrado. Rodada manual quando houver
modelo: `python tools_harness_aco_por_prancha.py --fcstd <modelo.FCStd> --out <dir>`; os tempos
entao escritos viram o orcamento do `conferir_orcamento` (prancha mais lenta reprova).
Pre-requisito do D118 mantido: sem fonte declarada p/ os 3 numeros de `_notas_do_modelo` fora do
3D, migrar PE09/PE16 a SVG seria saturacao silenciosa, nao economia.
**Nota do G106:** o aceite do goal era "o numero por prancha existe e esta escrito" - e ele NAO
existe. "Nao ha FCStd no disco" nao e bloqueio de fonte: o modelo se constroi (`montar_modelo`,
fallback headless, S19). A ferramenta fecha; a medicao fica aberta e nomeada no backlog seguinte.

## D128/G99 - a casa liga o eletrico que ela ja calcula (2026-09-11) - FECHADO
`casa_residencial._emitir_desenhos` chama `desenho_eletrico_residencial.gerar_desenhos_residenciais`
sobre `resultado.eletrico` (o resultado ELETRICO, nao a casa inteira). PE-EL-01/02/04 saem no disco
(`unifilar.svg`, `quadro-cargas.svg`, `planta-eletrica.svg`) com as triagens proprias do emissor
intactas (`layout_not_declared`, `invalid_layout`); PE-EL-03 segue declarado (sem emissor, malha
nao declarada). Rodada real do spec persistido: 12 folhas no disco (eram 6).
**Corrigido no G106:** o `except` do hook devolvia `{"files": [], "skipped": {}}` e apagava a
excecao - o laco caia no motivo generico "sem emissor ligado", falso depois deste goal (o except
catch-all do G74, de novo). A falha agora viaja com a excecao para as tres folhas, e os tres
ramos de motivo voltaram com o dado CERTO (`resultado.eletrico.circuits ausente`), em vez de
sumir: motivo que sobrevive ao fato vira nome morto, mas motivo apagado cai no generico.
Guarda: `tests/test_casa_eletrica_g99.py` test_05.

## D129/G100 - as folhas de concreto da casa pelas primitivas do predio (2026-09-11) - FECHADO
Tres wrappers em `desenho_casa_residencial` (sem copia): PE-CO-02 ->
`desenho_pavimento.prancha_armacao_vigas_svg` (le `estrutura.vigas`, verificadas desde o G34),
PE-CO-03 -> `desenho_concreto.planta_laje_svg`, PE-CO-04 ->
`desenho_fundacao_edificio.planta_fundacao_svg` (so com `por_pilar`). Na casa em alvenaria
portante (vigas vazias, sapata corrida por linha) a ausencia vira `ValueError` com o dado nomeado
e vai para `skipped`, nunca folha vazia. As tres entram em `FOLHAS` do G77. Renderizadas e olhadas
no G106: 7 linhas/17 tramos, 12 sapatas com viga de equilibrio cotada, laje com quadro de ferros.
**Corrigido no G106 (rotulo x geometria):** o titulo da folha dizia "ARMACAO DE VIGAS E PILARES"
e a primitiva desenha so vigas. Titulo corrigido; o arquivo manteve o nome. A divida e maior e
anterior: o indice promete "Armacao pilares/vigas" em PE-CO-02 nas duas tipologias e **nenhuma
emite armacao de pilar** - aberto no backlog. Tambem medido: a PE-CO-03 desenha UM painel
(3,50 x 4,00) de uma casa com seis, sem dizer qual nem por que (o predio faz o mesmo).

## D130/G102 - indice x DISCO de rodada real, e o quarto lado da lente (2026-09-11) - FECHADO
`tests/test_indice_disco_rodada_g102.py` roda as tres tipologias sobre specs de `projects/`
(`generate_ifc` desligado) e confronta o indice com o MANIFESTO: sem_mapa, sobrando, faltando,
`extra_no_disco` (quarto lado novo em `varredura_indice_disco`, isencao escrita obrigatoria:
`quadro-ambientes.svg`, `conferencia-nbr5410.svg`), manifesto que mente (artefato sem arquivo) e
arquivo fora de `manifest["artifacts"]`. O G91 foi renomeado no docstring para o que mede
(indice x MAPA). Custo medido: casa 1,9 s, predio 34,8 s, galpao 38,5 s - roda no CI.
**Medido no G106, e escrito no teste:** em rodada real de casa/predio `faltando` nao dispara
nunca - o laco do proprio adaptador nomeia todo arquivo ausente. O lado do disco que so a rodada
real mede e manifesto x arquivo + extra. E o galpao roda com `generate_2d` desligado (sem
`freecad.exe` o deliverable inteiro sai `not_available`), entao do galpao so se mede indice x mapa.
**Corrigido no G106:** (1) o teto de custo so era conferido contra a constante escrita a mao
(test_05) - agora o test_01 cobra o tempo MEDIDO; (2) as injecoes do test_03/04 eram sobre disco
derivado do mapa, a forma do G91 - o test_06 injeta sobre rodada real da casa (apaga um arquivo
dito emitido; registra artefato sem codigo) e fica vermelho nos dois.

## D131/G103 - disciplina executada sem prancha: o D89 do lado da promessa (2026-09-11) - FECHADO
`varredura_disciplina_prancha.py` (funcao pura): disciplina executada tem entrada em
`pacote_legal._PRANCHAS`, cobertura declarada (`fundacao` -> `concreto`) ou isencao com motivo
escrito. Aplicada as tres fontes vivas; `mezanino` do galpao sai isento com motivo (parte da
estrutura, calculado e federado, sem prancha propria). BASELINE_G103 nos dois sentidos, injecao
em tmp_path, isencao em branco reprova.
**Limite medido (G106):** as fontes de casa/predio (`disciplinas_pacote`) ja traduzem `fundacao`
para `concreto` antes da lente - o ramo `COBERTA_POR` so e exercitado pelo teste, nunca pela
fonte viva. Nao e vermelho; e o que a lente mede.

## D132/G106 - auditoria do lote G99-G105 (2026-09-11) - FECHADO
Quatro defeitos, nenhum de engenharia de calculo, todos da mesma familia - **dado que some sem
aviso**: (1) a rota SVG-direta do G104 cortava cada linha do quadro em 220 caracteres e parava no
fim da A1 com `break`: dois itens do memorial da hidraulica (NBR 5626 e "posicoes esquematicas")
saiam pela metade, em silencio. Agora quebra linha e continua em pagina A1 de continuacao com o
carimbo; guarda compara cada nota do `config_de_spec` com o texto do PDF, e o corte antigo
re-injetado deixa a guarda vermelha. (2) except que apagava a excecao do emissor eletrico (D128).
(3) titulo que prometia pilar (D129). (4) portao de custo que nunca media (D130).
Os portoes de censo (G51, G97, G77, alcancabilidade) estavam **verdes** na entrega - a regra do
lote funcionou pela primeira vez: os dois modulos novos entraram com isencao e motivo.

## D133/G109 - o numero por prancha do aco existe: 16 de 17 medidas, PE05 declarada (2026-09-11) - FECHADO (numero; PE05 ABERTA)
FCStd construido pela rota existente (`RP.calcular` + `montar_modelo` headless via freecadcmd) do spec persistido `projects/galpao-ufpe/project-spec.json` (44x90 2 vaos; HEA240/HEA200/HEA240 + IPE400); saida em `projects/galpao-ufpe/saida/` (agora em `.gitignore`, mesma regra do `iterations/`). Tempos por prancha (soma build/hlr/cotas/export, s): PE01 187,7; PE02 58,8; PE03 211,9; PE04 15,4; PE06 6,4; PE07 7,5; PE08 28,6; PE09 7,6; PE10 12,8; PE11 8,6; PE12 10,7; PE13 12,0; PE14_CROQUIS 4,9; PE16 5,4 (total ≈ 578 s, compativel com os ~15 min do executivo em rodada); PE14_CONSOLE e PE15 condicionais ausentes no modelo (fundacao sapata), saem com motivo. Congelados como `MEDIDOS_G109`/`ORCAMENTO_G109` no harness; portao em `tests/test_orcamento_aco_g109.py` (esquema por parse, folga do teto verificada, vermelho por injecao em tmp_path; PE05 exatamente em faltando). PE05_CONTRAVENTAMENTO sem numero: timeout sistematico (2x1200 s no harness + 540 s no diag), trava no `doc.recompute()` da pagina — o build dela e instantaneo (1 pag + 1 cota). Maquina 8 GB com ~1 GB livre nas rodadas. Porquê: o aceite do G105 era o numero escrito, e medicao que so vale quando confirma nao e medicao. Rejeitado: estimar a PE05 pela classe coarse das irmas (dado arbitrado) ou zerar o total dela (saturacao silenciosa). A PE05 fica aberta e nomeada: re-medir em maquina com folga, ou fatiar o recompute dela, noutro goal.
Achado de percurso: o boot do harness nunca rodara de verdade — `PRANCHAS` nao existe dentro do freecad.exe (NameError em toda prancha). Corrigido passando so a entrada medida (`_ENT_`); a guarda G105 segue verde.

## D134/G107 - o galpao emite as pranchas de esquema sem freecad.exe (2026-09-11) - FECHADO
`galpao_adapter._emit_drawings` deixou de sair com `not_available` inteiro quando falta o
executavel: hidraulica/incendio/climatizacao (rota SVG-direta do G104) emitem, e
aco/concreto/eletrico/coordenacao saem declarados **por codigo**, com a causa proxima
("freecad.exe nao encontrado - a disciplina emite via TechDraw e nao tem rota sem executavel")
anexada ao motivo de cada um. Status novo `partial` quando ha folha e ha disciplina faltando
(o "orcamento parcial que se diz fechado" do G7 nao volta como `generated`). O registro no
manifesto passou de `_register_tree` (arvore inteira: json, FCStd, PNG, caderno) para
`_register_pranchas` (`*/pranchas/*.pdf`) - todas as disciplinas gravam ali
(`caderno_turnkey._coletar_pdfs`), conferido na auditoria. O portao do G102 passou a rodar o
galpao com `generate_2d=True`: PE-HI/PE-IN/PE-CL confrontados com disco de verdade, e as
segundas folhas (HID02/INC02/CLI02) isentas com motivo como `extra_no_disco`.
**Custo medido e escrito no teste:** a rodada do galpao no portao do G102 foi de 38,5 s para
**923 s** - `caderno_turnkey.montar_caderno` roda `tk.rodar` de novo, embora o adaptador ja tenha
o resultado do turnkey. Abaixo do teto de 1800 s, mas ~16 min dentro da suite non-build: aberto (G114).
**E nao e so tempo:** na auditoria G113 este arquivo derrubou QUATRO execucoes por falta de
memoria (maquina de 8 GB, 1,5-1,9 GB livres) - em lotes de 50, 22 e 11 arquivos e, por fim,
SOZINHO, morrendo antes do primeiro ponto (saida com 0 byte), sempre sem processo orfao. Logo,
rodar isolado NAO resolve: a suite completa nao fecha nesta maquina com o portao na forma
atual. O `CUSTO_TETO_SEG` de 1800 s nao ve isso - afere tempo, nao memoria. O G114 passa a ter
"caber na memoria" no aceite.

## D135/G108 - os pesos do prazo do caderno vem da medicao (2026-09-11) - FECHADO
`_STAGE_WEIGHTS`: hidraulica/incendio/climatizacao/mezanino de 1,25/1,0/1,0/1,0 para **0,01**
(piso: peso 0 daria prazo 0), cada um com a origem escrita ao lado (D125: 0,56/0,62/0,57 s;
mezanino sem dispatch, 0,0003 s). Regra: peso = 7,0 x t_medido / 900 s. A fracao do aco na
reserva sobe de 55 % para **82 %** (7/8,54), travada em `tests/test_caderno_pesos_g108.py`, com
injecao dos pesos antigos voltando aos 55 %.
**Nota da auditoria G113:** (1) a ancora de 900 s e a estimativa do T13; o G109 mediu o aco em
~578 s. Com 578 os pesos continuam abaixo do piso - o resultado nao muda, mas a ancora devia
ser o numero medido. (2) O teste recalcula a fracao com formula propria em vez de chamar
`caderno_turnkey._stage_timeout`; se a regra de reserva mudar, o teste nao ve.

## D136/G110 - PE-CO-02 passa a desenhar pilar (2026-09-11) - FECHADO (lances superiores ABERTOS)
Decisao N:1: a secao de pilares entra **abaixo** da de vigas no mesmo arquivo
(`desenho_pavimento.prancha_armacao_vigas_pilares_svg`, casa e predio), sem arquivo novo e sem
mexer em mapa/indice/FOLHAS. Uma fileira por pilar, do **lance de base** (`lances[-1]`): secao,
n de lances, Nd, As, taxa, estribo (phi, s, ramos) e o limite governante da 18.4.3. Sem
`phi_long_mm` declarado a celula diz "NAO DETALHADO" - bitola nao e arbitrada.
**Conferido na auditoria (pela imagem, a camada de texto da F150 e ilegivel):** a 18.4.2 e a
18.4.3 da NBR 6118:2023 sao identicas as da 2014 (diametro 10 mm a b/8, espacamentos,
200 mm / menor dimensao / 24phi CA-25 / 12phi CA-50, NOTA C55-C90), e a Em1:2026 nao altera a
18.4 (a unica mencao e a Figura 18.4, armadura de suspensao, na 18.3.6). A Em1 altera, porem,
a 15.8.1 que o subtitulo da folha cita - item do goal de migracao 2014 -> 2023.
**Corrigido no G113:** o rotulo do estribo usava padroes (5 mm, c/15, 2R) quando a chave
faltava - imprimiria um estribo nao calculado. Agora declara "-". (O dado real tem as chaves.)
**Aberto, medido:** no predio, **8 dos 12 pilares** mudam de secao ou de As entre lances, e a
folha mostra so a base. O rodape declara isso - nao e silencio -, mas a gaiola dos lances
superiores nao chega ao cliente.

## D137/G111 - PE-CO-03 detalha todos os paineis (2026-09-11) - FECHADO
Opcao (a): `laje_concreto.detalha_lajes_por_painel` roda um `dimensiona_laje` por painel com a
`h` que convergiu pelo critico (maior area), e a folha lista os seis paineis da casa (e os seis
do predio) com quadro de ferros cada. Medido: nos dois specs persistidos todos atendem com
h = 10 cm, inclusive os de caso 8.
**Corrigido no G113 (saturacao silenciosa latente):** o `OK` por painel nao chegava ao veredito.
Num spec em que um painel nao critico reprovasse com a h adotada, a folha o mostraria em
vermelho e a estrutura continuaria ATENDE. Portao novo `gates["lajes_por_painel"]` em
`estrutura_casa` e `edificio_multipavimento`; injecao em
`tests/test_laje_todos_paineis_g111.py` (um painel reprovado -> estrutura REPROVA e nomeia
"painel 2,1").

## D138/G112 - carimbo x indice: numeracao propria, com tabela para o cliente (2026-09-11) - FECHADO
Caminho (b) do goal. Lente `varredura_carimbo_mapa.py` (carimbo de cada arquivo pertence aos
codigos que o mapa atribui a ele; carimbos extraidos por AST dos `techdraw_*`) + tabela de
correspondencia de 22 entradas no `pacote-legal.md` do galpao (que folha do executivo responde
por que codigo do indice, e por que a numeracao difere: um esquema cobre N codigos, quadros sem
codigo, PE-01 em dois arquivos, aco com 17 folhas para 3 codigos).
**Corrigido no G113 (fonte unica):** a tabela canonica vivia na lente (script avulso) e
`entregaveis_projeto` carregava uma copia de ~150 linhas guardada por teste de igualdade - duas
listas para divergir, com a canonica onde o cliente nao le. Agora ha uma so,
`pacote_legal.CORRESPONDENCIA_NUMERACAO_GALPAO` (modulo sem imports: a lente importar
`entregaveis_projeto` direto dispara o ciclo project_loop -> adaptadores).

## D139/G113 - auditoria do lote G107-G112 (2026-09-11) - FECHADO
Portoes de censo **verdes** na entrega pela segunda vez seguida. Verbetes: so o G109 (D133)
chegou escrito; os outros cinco foram escritos na auditoria, a partir do codigo e de medicao.
**O lote foi entregue com um censo VERMELHO:** `tests/test_guardas_d86_g69.py` (censo das
guardas `confere_*` x `TRIADAS_G69`) reprovava desde o G110 - a guarda nova
`desenho_pavimento.confere_armacao_pilares` entrou na arvore sem entrada no baseline e sem a
linha de origem dos dois lados no cabecalho (regra D86/D87). So apareceu na suite inteira: a
"regra do lote" dizia "e os baselines", sem nomear arquivos, e quem rodou de memoria nao rodou
este. Triada como item 24 (A=nomes do dict `pilares`; B=ocorrencias no SVG; INDEPENDENTE, a
forma do irmao de vigas) e a regra do backlog seguinte passou a listar os censos **por nome de
arquivo**. E a terceira vez que "modulo/funcao nova invisivel ao censo" custa um vermelho
(G98, G106, G113) - a diferenca e que desta vez a lente ja existia e ninguem a rodou.

Seis correcoes: portao de laje por painel ligado ao veredito (D137), estribo sem padrao
inventado (D136), tabela do G112 em fonte unica (D138), o confronto 18.4 2014 x 2023 que o
G110 pedia e nao fez (D136), e o **status `partial` que o agregador nao conhecia**: o G107
criou o status e `project_loop._project_status` so olhava `failed`/`not_available` - a rodada
do galpao sem freecad.exe, com 3 de 7 disciplinas emitidas, saia **`passed`**. Achado pelo
unico vermelho da suite (`test_optional_freecad_deliverables_are_explicit_when_executable_is_missing`,
que cobrava o contrato antigo `not_available`); `partial` agora vale `needs_review`, e o teste
passou a cobrar o contrato novo (folha de esquema emitida + causa proxima nos pulados).
O mesmo buraco valia para o `partial` que `entregaveis_projeto` ja emitia desde antes. **Suite non-build desta auditoria:** verde em todos os oito lotes (549 + 262 + 420 + 486 + 499
+ 621 + 434 + 426), com os dois vermelhos corrigidos e reexecutados. **Uma excecao honesta:**
`tests/test_indice_disco_rodada_g102.py` NAO completou nesta maquina - morto por memoria em
quatro tentativas, a ultima rodando sozinho. Dele so rodaram os 4 testes leves (baseline,
injecoes e custo escrito); os dois que carregam rodada real (test_01 e test_06) ficaram sem
rodar, e isso esta dito aqui em vez de a suite ser apresentada como fechada.
Aberto e medido: portao do G102 com 923 s por `tk.rodar` duplicado;
lances superiores dos pilares; PE05 do aco sem numero; migracao 2014 -> 2023+Em1. A Em1 (texto
legivel, F098) traz **62 instrucoes Substituir/Incluir em 51 itens**, entre eles 15.7.3 (reducao
de rigidez, citando galpoes), 15.8.1 (lambda <= 200, exceto pilar pouco comprimido com
Nd < 0,10 fcd Ac), 17.3.5.2.4 (As + A's <= 4 % Ac fora das emendas) e 18.3.x - itens que o
framework implementa pela 2014.

## D140/G117 - a cifra da F150 decodificada (ramo a), G116 destravado (2026-09-11) - FECHADO
Ramo (a) do goal: `f150_decodifica.py` (tabela canonica, fonte unica;
lente e teste importam de la) decodifica a camada de texto do corpo da
F150 (`fontes/01_CONCRETO/...-projeto-estruturas-concreto.pdf`, 260 p.,
saida `...-dec.txt`, 639707 bytes, 14662 linhas, fora do git:
`fontes/` e ignorado). Medido no rawdict: base byte+29 para
letras/digitos/pontuacao ("7"->"T", "R"->"o", "2V"->"Os",
"UHTXLVLWRV"->"requisitos", "\x03"->espaco) nas TRES fontes subsetadas
*MT2 (ArialMT2/BoldMT2/ItalicMT2 - o G106/G113 so citava o corpo; os
cabecalhos em negrito/italico usam a mesma cifra e tambem sao
decodificados); 12 bytes reaproveitados para acentos (i->á, j->à,
k->â, m->ã, o->ç, p->é, r->ê, t->í, y->ó, {->ô, }->õ, ~->ú) +
"°/º/fi/fl/–/'/Á/“/”"; o par "\x03\x20" (espaco w=3.06 + espacador
w=2.21) renderiza UM espaco - "\x20" em MT2 nunca e "=" (o "=" real
mora nas fontes de formula). Vao no bbox reconstrui espacos sem codigo.
Aceite: 15 ancoras em 10 paginas (xvi, xvii, 5.1.2, 8.2.3, 9.4.2.6,
11.4.1.3, 14.4.1, 15.4.2, 17.4.2.3, 22.5.1.3), duas de formula (a prosa
ao redor), todas lidas na pagina RENDERIZADA (regra 3) e conferidas na
imagem nesta entrega. Declarado o que nao sai: miolo simbolico de
formulas/tabelas/figuras (o "phi" extrai como "I" da SymbolMT -
preservado, nao adivinhado), carimbo vermelho lateral e marca d'agua
(texto corrido). OCR (ramo b) rejeitado: sem Tesseract na maquina.
Suite: os 8 portoes nominais verdes + teste-guarda
`test_f150_decodifica_g117.py` (portao vivo/baseline/injecao em
tmp_path); a entrega tropecou nos dois censos que o G113 nomeou -
`confere_cobertura` (lente sem faixa: isenta com motivo) e o censo das
guardas (`confere_amostra` triada como item 25, INDEPENDENTE) - e os
fechou antes de declarar verde. Nao subir ao NotebookLM sem OK do
usuario (publicar em servico externo).

## D141/G116 - o impacto 2014 -> 2023+Em1, medido (2026-09-12) - FECHADO

Goal media e escreve, sem trocar base de modulo nenhum. Entrega:
`impacto_nbr6118_g116.py` (tabelas canonicas, fonte unica; lente e teste
importam de la), `tests/test_impacto_nbr6118_g116.py` (portao/baseline/
injecao em tmp_path/casos) e o inventario
`wiki/07-nbr6118-2023-em1-impacto-g116.md` (51 itens, 4 casos, Tabela 2 das
familias fora da Emenda, lacunas declaradas).

Medido, com endereco. A Emenda (F098, 23 pags, legivel) tem 85 cabecalhos
literais de instrucao - o G113 contou 51 itens e 62 instrucoes por
agrupamento; o portao confere os 85 um a um por substring (CABECALHOS_EM1,
particao congelada em CAB_PARA_ITEM, provada no teste), de modo que qualquer
contagem esta coberta. 2014 = 2023 pre-Em1 em todas as clausulas de
intersecao sondadas (13.2.5.1-b, 15.8.1, 17.3.5.2.4, 17.4.1.1.3, 19.5.4, 20.1;
F016 extraivel x F150 decodificada no G117), menos a 15.7.3: o paragrafo do
galpao nao existe em 2014 e ja existe na 2023 - novidade da edicao, fora da
Emenda (gap medido aqui; o resto do 2014 -> 2023 segue NAO MEDIDO, declarado
na Tabela 2, nunca default silencioso).

Resultado para a decisao do usuario. NUMERO-MUDA em 2 pontos: 13.2.5.1-b
(furo circular 12,1-12,5 cm entra na dispensa; framework
`compatibilizacao.avalia_furo_viga` pede verificacao a mais - conservador) e
12.3.3 (s = 0,20 para todo C60+: C60 CPIII 7d da 41032 em 2014 contra 49124
kN/m2 em 2023+Em1, +19,7%). REGRA-MUDA sem numero: Tab 13.3 (some o teta
0,0017 - constante orfa no framework, sem efeito), Tab 13.4 NOTA 2, 17.5.1.4.1
(he alternativo), 18.2.4 (grampo 135-180 g), 18.3.3.2 (barra de amarracao),
19.5.4 (C'' condicional). PROCESSO-NOVO: 5.3 ATP (maior novidade da Emenda) e
20.6 balanco/marquise - exigem criar gate, nao trocar conta. Todo o resto nos
pontos implementados e EDITORIAL (15.8.1, 17.3.5.2.4 e 19.5.4 ja diziam em
2014 o que a Em1 diz - inclusive a ressalva do pouco comprimido que o G113
apresentou como novidade). Casos C1-C4 chamam funcao real, sem alterar modulo
(contra assercao tautologica); 4 testes verdes.

Suite: os 8 portoes nominais verdes (faixa, asserts, folhas 92, alcance 5,
guardas 14, disciplina/indice/carimbo 17) + 4 do G116. Registros de borda:
script avulso em SCRIPTS_AVULSOS, isencao com motivo em SEM_FAIXA_DECLARADA;
funcoes nomeadas sem prefixo confere_/verifica_fechamento (fora do censo
D86/D87 por desenho); testes-portao com um assert so (G97).

## D142/G114 - o caderno reusa o turnkey: um `tk.rodar` so (2026-09-12) - FECHADO (parede nao remedida; memoria aberta)

`caderno_turnkey.montar_caderno(spec, out_dir, ..., R=None, turnkey_result=None)`
reusa o `R` que o adaptador do galpao ja tem do hook (`_run_turnkey` ->
`tk.rodar`) e so calcula quando nao recebe (`tk.rodar(spec, out_dir)` uma
vez); `galpao_adapter._emit_drawings` passa `R=turnkey_result`. Sem mudar o
resultado: o `R` so entra como leitura (`executadas`, `disciplinas[*].raw`,
`geometria`, `ATENDE`); `res["turnkey_reuso"]` declara o caminho. Porquê: o
portao do G102 media galpao 38,5 s -> 923 s depois do G107 (generate_2d=True)
pelos dois `tk.rodar` sobre o spec 44x90 de dois vaos (D134/D139), ~16 min na
suite non-build e 4 mortes por memoria nesta maquina (8 GB, 1,5-1,9 GB
livres, a ultima sozinho com saida 0 byte) — o teto de 1800 s mede tempo,
nao memoria. Rejeitado: recalcular "por seguranca" (o segundo calculo era o
custo); estimar o depois sem medir (ausencia se declara).

Medido, com endereco. Portao novo `tests/test_caderno_reuso_turnkey_g114.py`
(4 testes, tmp_path + monkeypatch, sem FreeCAD): com R zero chamadas a
`tk.rodar`, sem R exatamente uma, mesmo `n_pranchas`/`disciplinas`/`ATENDE`;
alias `turnkey_result=` igual a `R=`; defeito duplo injetado volta a 1
chamada (vermelho); adaptador passa o objeto que tem (identidade). Dois
residuos do G108 no mesmo lote: ancora 900 s (estimativa T13) ->
`_ANCORA_ACO_SEG = 578.0` medidos (D133/G109, 16 pranchas, PE05 sem numero,
G118), pesos no piso 0,01 inalterados (7x0,56/578 = 0,0068 etc.); teste
`test_caderno_pesos_g108.py` chama a reserva real (`_fracao_reserva` via
`_total_peso` + `_stage_timeout` com prazo congelado, nunca soma propria) +
`test_03_ancora_medida_d133`. Fonte unica: `_total_peso`/`_fracao_reserva` na
producao, lente e testes importam de la; `reserve_stage` interno usa
`_total_peso`. Fakes de `montar_caderno` em G93/G101 aceitam `R=`/`**_kw`.

Aceite honesto (negativo declarado, como manda o goal). O antes/depois de
parede NAO foi reescrito em `CUSTO_MEDIDO_SEG` (segue 2,7/35,7/923,0 s de
2026-09-11): a rodada integral do galpao OOM nesta maquina como na auditoria
G113, e numero inventado seria dado arbitrado. O ganho provado e 1 calculo a
menos por rodada (pico de memoria cai junto). O docstring do G102 registra
isso e aponta o verbete. Aberto: o teto segue de tempo; "caber" (rodar junto
dos outros ou teto de memoria) fica para o proximo passo — fatiar a rodada
ou medir memoria com harness, nunca default silencioso.

## D143/G115 - a armacao de pilar mostra todos os trechos (2026-09-12) - FECHADO

Fecha o ABERTO do D136: no predio, 8 dos 12 pilares mudavam de secao ou de
As entre lances e a folha (G110) mostrava so a base. Agora uma fileira por
TRECHO de lances iguais (mesma secao e mesmo As, contiguos) em
`desenho_pavimento.py` (`_trechos_pilar`, `_vals_fileira_trecho`,
`_escreve_secao_pilares` por trecho): LANCES e' o intervalo 1-based do topo
para a base ("1-5" ou "6"); secao, Nd, As, taxa, estribo, limite e arranjo
sao os do lance de BASE do trecho (o mais carregado). Pilar sem mudanca
continua com uma fileira ("1-9"). Coluna "SECAO BASE" volta a "SECAO".

Medido, com endereco. Predio (spec persistido, 9 lances por pilar): 12
pilares, **42 trechos** — P11/P13/P41/P43 "1-9" (1); P12/P42 "1-5","6","7",
"8","9" (5); P21/P23/P31/P33 "1-7","8","9" (3); P22/P32 "1-2" + "3".."9" (8).
Casa: 12 pilares de 1 lance, 12 trechos — inalterada, como previa o goal.
A 18.4 nao muda (D136, conferida pela imagem) — nenhuma clausula nova alem
das do G110.

Lente: `confere_armacao_pilares` por trecho (nome >= n_trechos por regex
G69 + intervalo/secao/As literais do trecho + soma dos lances cobertos ==
lances do resultado). A folha antiga (so a base) reprova nela quando ha
variacao — o vermelho por injecao do aceite (P11 com b 0.19->0.25 no lance
5: 1 trecho vira 3, mesma SVG reprova). Altura dinamica por fileiras
(isolada e combinada; licao do G77: altura fixa com conteudo que cresce
corta fileira). Triagem do item 24 atualizada para trechos; o baseline
`TRIADAS_G69` nao muda (mesma funcao, sem guarda nova). Tres aceites:
certa (dois confere ok + XML + `confere_folha_svg`), no manifesto (mesmo
arquivo PE-CO-02, sem churn em mapa/indice/FOLHAS) e diz o que desenha
(rodape: "uma fileira por trecho de lances iguais ... do lance de BASE do
trecho").

Suite: os 8 portoes nominais verdes (faixa, asserts, folhas 106, alcance +
disciplina/indice/carimbo 22, guardas) + G110 (8) + G115
`tests/test_armacao_pilares_trechos_g115.py` (8: 42 trechos, casa 12,
injecao de secao, fileira removida, vazio, norma/guarda, combinada
 17 tramos + 42 trechos em disco, render). Renderizada via
`svg_para_png` (fitz presente, PNG > 0); isolada H 1204, combinada H 1778.

## D144/G118 - a PE05 do aco tem numero: o topo travava nos tirantes sem oclusores (2026-09-12) - FECHADO

Causa medida, nao suposta, no modelo do G109 (galpao-ufpe 44x90 2 vaos, FCStd
2,4 MB, freecad.exe 1.1, maquina 8 GB com ~1,1-1,5 GB livres — a mesma
condicao do G109, entao memoria esta exonerada por medicao). Fatiado vista a
vista com o harness do G105 (um processo freecad.exe por variante, boots e
logs em tmp, producao intacta ate o fix):

- V4 so 12 ESTICADORes, lateral: t_hlr 4,4 s — o esticador sozinho e inocente.
- V8 so 12 CONTRAV, topo: t_hlr 4,9 s (20 s totais) — as diagonais sao inocentes.
- V1 so lateral (547 fontes, com esticador): t_hlr 123 s, total 209 s — passa.
- V13 contexto de 955 com oclusores, topo, esc 0,004: t_hlr 65 s, total 97 s.
- PE01 rehecha hoje pelo harness real: t_hlr 79,6 s (G109: 67,3 s) — reproduz.
- V7 so 432 TIRANTEs, topo, esc 0,004: 548 s de recompute + export travado.
- V2 so topo (547): >600 s. V3 ambas sem esticador (535+535): >600 s.
- V14 as 547 vistas de baixo (0,0,-1): >600 s. Memoria chata nos tres (~1,2 GB
  residentes, sem blowup): trava de CPU no HLR, nao OOM.

O veneno: os 432 TIRANTEs (barras redondas esbeltas, 48 verticais de parede
vistos de topo) numa vista de topo/fundo SEM os planos oclusores da cobertura
(TELHA/TAPAMENTO/TERCA). Sem oclusores o HLR vira combinatorio (548 s para
432 solidos triviais de 3 faces); com oclusores os mesmos 955 solidos saem em
~60 s. Escala exonerada (V13 usa a esc da PE05 e passa); direcao sozinha nao
explica (lateral passa, topo/fundo travam).

Fix na producao (`techdraw_exec._pr_contravent`): a vista de cobertura leva
so os CONTRAV (12); tirantes, esticadores e porticos seguem na lateral
(Source da V05_CV_LAT), entao `_cobertura` passa sem nada omitido e a folha
diz o que desenha (A05a vertical + A05b cobertura, mesmos titulos). Medido
pelo harness real: PE05 build 0,2 / hlr 128,0 / cotas 47,1 / export 34,1
(total ≈ 209 s), renderizada e olhada (PNG: X nas duas baias de extremidade
na lateral com cotas 7,50/7,00 m; cobertura com os 2 X dos dois vaos;
carimbo PE-05 05/09 ESC 1:250). Congelado em `MEDIDOS_G109`/`ORCAMENTO_G109`
(teto 240, mesma folga ~15 % da PE03) e o portao
`tests/test_orcamento_aco_g109.py` passa sem faltando (so as duas
condicionais sem numero); guarda nova `tests/test_pe05_topo_g118.py` (topo
sem TIRANTE + lateral cobre os 4 prefixos, vermelho por injecao, sem
FreeCAD). Rejeitado: estimar a PE05 pelas irmas (dado arbitrado, D133) e
zerar o total dela (saturacao silenciosa).

Tres aceites: certa (numero medido + PNG olhado + cobertura por Sources),
no manifesto (PDF/SVG/DXF/PNG exportados pelo harness) e diz o que desenha
(titulos e carimbo intactos). Para o G114: o total medido do aco agora e
≈ 788 s (17 medidas + 2 condicionais com motivo); a ancora segue 578 ate ele
decidir (comentario em `caderno_turnkey.py` atualizado, valor intacto).
Censos do lote verdes (faixa, asserts, folhas, alcance, guardas, disciplina,
indice, carimbo) + G105/G109/G118: 140 passed.


## D145/G119 - auditoria do lote G114-G118: a regua que nao podia acusar (2026-09-12) - FECHADO

Primeiro lote do projeto que chegou com verbete em TODOS os goals (D140-D144)
e com os oito censos nominais verdes - conferidos por medicao nesta auditoria,
nao por declaracao: `confere_cobertura` OK, `confere` (asserts) OK, e
folhas/alcance/guardas/disciplina/indice/carimbo 128 passed. Os numeros de
manchete tambem batem, medidos por conta propria: 42 trechos no spec
persistido do predio (mapa pilar a pilar identico), 639707 bytes no .txt
decodificado, e a conta do 12.3.3 (C60 CPIII 7 d: 41032 -> 49124 kN/m2,
+19,7 %) confere ate o ultimo digito. O G116 ainda corrige um erro MEU: a
ressalva do pilar pouco comprimido (15.8.1, "0,10 fcd Ac") que o D139
apresentou como novidade da Emenda ja esta na 2014, p.125, palavra por
palavra. Sete defeitos, dois deles de classe nova.

**1. A regua sem marca (G117) - a classe nova, e a pior.** `decodifica_char`
devolvia `chr(o + 29)` para todo byte fora da tabela. `DESCONHECIDO_FMT`
existia, e `decodifica_pdf` contava suas ocorrencias para relatar
`desconhecidos` - mas NADA nunca o escrevia. O medidor relatava `{}` porque
era estruturalmente incapaz de acusar. Sob ele, 16 codigos saiam como outro
caractere PLAUSIVEL: "2ª ordem" virava "2º ordem" (120x), "εc2 = 2,0 ‰"
virava "2,0 â" e - o pior - **"fck ≤ 50 MPa" virava "fck ± 50 MPa"**, um
limite normativo com outro operador. Nao era omissao, era TROCA: o cabecalho
declarava que "≥≤" moravam em outras fontes e nao sairiam, quando na verdade
saem nos spans MT2 (0x95 e 0x94) e saiam errados. Oito codigos foram
conferidos na PAGINA RENDERIZADA e mapeados (0x9D ª, 0x94 ≤, 0x95 ≥, 0xC2 ·,
0xC5 ‰, 0xCB Í, 0xBB /, 0xBFA ff, cada um com a pagina anotada na tabela);
byte alto fora da tabela agora vira marcador visivel. O medidor passou de
`{}` a 8 codigos / 372 ocorrencias. O .txt foi regerado (± zerado, 123 "ª",
42 "≤", 80 "≥") e o catalogo do acervo atualizado. Ancoras novas na amostra
(15 -> 19): nenhuma das 15 originais tinha ordinal feminino nem operador, e
foi exatamente por isso que a troca passou pela lente.
**Licao:** medidor de ausencia que ninguem consegue fazer disparar e' pior
que medidor nenhum - da' garantia. Todo `DESCONHECIDO`/`faltando`/`nao
coberto` precisa de um teste que o faca acusar (`test_05`).

**2. Default plausivel no lugar de ausencia (mesma raiz do 1).** A regra
`+29` nao tinha fundo: aplicava-se a qualquer byte, inclusive aos que ela
nao sabia ler. E a mesma familia do estribo padrao do G113 (D139) e do
default que decide veredito (G74): o palpite se disfarca de resultado porque
e' plausivel. Agora `_LIMITE_REGRA_MAIS_29` marca onde a regra acaba.

**3. A guarda que nunca reprovava (G115).** `confere_armacao_pilares`
conferia o intervalo do trecho por substring solta. Trecho de um lance so
sai "6" - e "6" casa em qualquer ponto do SVG (medido: uma folha sem
nenhum desses trechos contem "6", "3" e "7"). Metade da guarda - justamente
a dos trechos isolados, que sao a maioria no predio - nao conseguia
reprovar. Corrigido com `_celula`, que confere o conteudo do elemento de
texto (`>1-5<`), como `_escreve_fileira` emite. Vermelho por injecao provado:
apagada a celula "6", a lente reprova.

**4. Constante escrita a mao que o teste nao confrontava (G115).**
`_TRECHOS_MEDIDOS` (mapa pilar -> intervalos) so era conferido pelo TOTAL
(42) e por aquelas substrings cegas. O agrupamento por pilar podia mudar
inteiro sem nada reprovar, desde que a soma desse 42. `test_09` agora
compara item a item com `_trechos_pilar` sobre o spec persistido. O mapa
estava certo - a medicao confirmou os 42 e cada intervalo -, mas nada o
segurava.

**5. Excecao nova onde antes nao havia (G118).** A guarda de entrada da PE05
aceita `CONTRAV` *ou* `TIRANTE`; desde o G118 o topo leva so `CONTRAV`. Um
modelo so-tirante passa a entrada, `cob` fica vazio, `_bbox([])` devolve
None e `_fit_escala` estourava `AttributeError` - caminho que nao existia
antes (o topo levava o mesmo conjunto da lateral, garantido nao-vazio).
Nao e' alcancavel pelo `build_galpao` de hoje (CONTRAV e' incondicional),
mas a folha nao pode depender disso: agora a vista de topo nao sai e a nota
DECLARA a ausencia (`_AUSENCIA_CONTRAV_COBERTURA`), com teste.
**Licao:** quando um goal estreita o conjunto de uma vista, a guarda de
entrada tem de estreitar junto - senao o "ou" da entrada vira caminho morto.

**6. Codigo morto que duplica regra (G115).** `_vals_fileira_pilar` foi
mantida "por compatibilidade G110" e, depois da troca para fileira por
trecho, ninguem mais a chamava - nem producao, nem teste - enquanto
carregava uma segunda copia da montagem da fileira, livre para divergir da
real. Removida.

**O que NAO era defeito, e foi medido para dizer que nao era.** O reuso do
turnkey (G114) e' seguro nos dois pontos de risco: todo `_run_*` copia a
sub-spec antes de injetar geometria (`s = dict(sub)`), entao o `tk.rodar`
removido nao mutava nada que o caderno lesse depois; e o despacho de
pranchas do aco re-roda `RP.rodar_tudo` no seu proprio `disc_out`, sem
depender dos arquivos que aquele segundo `tk.rodar` gravava. O corte do
topo da PE05 (G118) tambem nao perde conteudo: `CONTRAV_COBERTURA` E' o
contraventamento de cobertura, e tirantes/esticadores/porticos seguem na
lateral. E o inventario do G116 NAO herdou o texto corrompido (zero "±"):
quem o escreveu leu a norma com cuidado nas clausulas que citou - o estrago
ficava so no artefato do acervo, que existe justamente para ser lido depois.

**7. A ancora que nao ancorava (G114).** `_ANCORA_ACO_SEG = 578.0` entrou no
lote como "a ancora dos pesos passa de 900 s estimados para os 578 s
medidos" - mas a producao nunca a LIA: `_STAGE_WEIGHTS` seguia com literais
e comentarios citando a conta. Trocar a ancora nao mudava peso nenhum. E o
teste `test_03_ancora_medida_d133` conferia que a constante valia 578 (o
literal contra ele mesmo) e procurava a string "900" no texto do arquivo -
tautologia com busca textual por cima. Agora `peso_medido(t)` implementa a
regra do G108 (7,0 x t / ancora, piso 0,01) e os quatro pesos com tempo
CRONOMETRADO derivam dela (`_T_MEDIDO_SEG`, com a origem por disciplina);
concreto e eletrico, que nunca foram medidos, seguem literais com o motivo
escrito - tempo inventado so para caber na formula seria dado arbitrado.
Pesos finais identicos aos de antes (conferido), e o teste agora move a
ancora pela metade e cobra que o peso dobre.
**Licao:** constante "medida" que a producao nao le e' comentario com
sintaxe de codigo. Medida em varredura: 95 constantes de modulo escritas e
nunca lidas no proprio modulo (goal G124 confere quais tambem nao saem por
import).

**Aberto ao fim da auditoria, dito em vez de escondido.** `CUSTO_MEDIDO_SEG` do portao
G102 segue `{"casa": 2.7, "predio": 35.7, "galpao": 923.0}` — os 923 s sao de ANTES do
reuso do G114. A corrida limpa e isolada do arquivo completou (6 passed, 1230 s), mas sem
`-s` o pytest engole o `print` do custo por tipologia; a segunda corrida, com `-s`, foi
morta por falta de memoria porque a maquina estava em uso ao lado dela. Re-congelar com um
numero nao medido seria dado arbitrado, entao a baseline fica velha e declarada, e a
remedicao abre o goal G121.

## D146/G121 - o portao mede memoria: o teto que faltava (2026-09-12) - FECHADO

Fecha o ABERTO do D145. O portao do G102 media so tempo; nas quatro mortes do G113 o
tempo nunca chegou perto do teto de 1800 s — o processo era morto antes, e o portao nao
via o que o matava. Agora ele mede o pico de memoria residente de cada rodada e cobra um
teto, no mesmo formato do custo de tempo.

**Medido, com endereco.** `medicao_memoria.py` (producao, stdlib-only, fonte unica: o
portao importa daqui) amostra a cada 1 s o RSS do processo pytest via
`psapi.GetProcessMemoryInfo` mais a soma de todos os `freecad.exe` via `EnumProcesses` +
`GetModuleBaseName` + `GetProcessMemoryInfo` — sem psutil, sem parse de `tasklist`
(dependente de locale). `pico_total` e o max por amostra de (processo + freecad) na MESMA
amostra, nao a soma dos picos. Corrida oficial isolada com `-s`, um pytest por vez
(maquina de 8 GB, ~2,5 GB livres, sem orfao, 2026-09-12):
`CUSTO_G102 casa=2.4s predio=28.9s galpao=1048.3s total=1079.5s`, 6 passed em 1079,8 s;
`MEM_G102 casa=107,0MB(proc=107,0,fc=0,0,n=0) predio=143,6MB(proc=143,6,fc=0,0,n=0)
galpao=1988,8MB(proc=174,4,fc=1819,7,n=1)`. Re-congelado em `CUSTO_MEDIDO_SEG`,
`CUSTO_MEDIDO_EM = "2026-09-12"` e, novo, `CUSTO_MEDIDO_MEM_MB` /
`CUSTO_MEDIDO_MEM_EM`. O galpao segue acima dos 923 s de antes do reuso — variacao de
maquina/rodada, nao regressao do G114 (o total 1079,5 s fica abaixo dos 1230 s da corrida
limpa pos-G114 do G119). O que o numero novo revela: o galpao mora no freecad.exe
(1819,7 de 1988,8 MB, um por vez); casa/predio nao sobem freecad (rota SVG pura) e vivem
abaixo de 160 MB. O "≈803 MB" observado a mao no G119 era um instante, nao o pico —
amostrar vence olhar.

**O teto, com a folga escrita.** `CUSTO_TETO_MEM_MB = 2500` por rodada (pico 1988,8 +
~25 %): a maquina tem 8 GB e o SO + fundo comem ~2 GB; o teto deixa a rodada respirar e
ainda reprova vazamento, freecad orfao concorrente ou disciplina nova que suba outro
freecad junto (`n_freecad_max` sai no print para auditar). Picos nao se somam entre
tipologias — o teto vale por rodada, nao no total. O `test_01` cobra os dois tetos sobre
o MEDIDO nesta rodada; o `test_05` trava os dois registros; o `test_07` (casa real em
`tmp_path`, ~3 s) prova o vermelho por injecao nos dois sentidos — sampler com
`n_amostras >= 2`, `falhou` falso e `pico_processo > 0` (medidor incapaz de acusar era
o defeito do G117), teto 0,01 reprova, teto folgado passa, pico None declara sem
reprovar — e sampler que falha em todas as amostras vira gap ("sem numero para
cobrar"), nunca verde silencioso.

**Duas acusacoes no caminho, as duas certas.** A lente de faixa flagrou
`medicao_memoria.py` como `faltando` — declarado com faixa de verdade
(`intervalo_s` entre 0,2 e 5 s: abaixo o proprio EnumProcesses perturba, acima um filho
curto passa entre amostras; fora da faixa, `ValueError`, nunca clamp), hoje `guardada`.
O alcance flagrou o mesmo arquivo como ilha — declarado script avulso com motivo e
`__main__` que sonda a maquina (`python medicao_memoria.py`), no molde das varreduras
que os testes importam. Sem psutil de proposito: dependencia nova para medir seria o
instrumento pesando na medida.

**Limite declarado.** A soma do freecad.exe e de TODOS os visiveis, nao so dos filhos
desta rodada — em corrida isolada equivale aos filhos; com outro freecad alheio o numero
sai MAIOR (conservador, nunca esconde pico). E um detalhe de 64-bit que custou um ciclo:
`GetCurrentProcess` devolve pseudo-handle -1 e o ctypes truncava para 32-bit (erro 6) —
protótipos com `HANDLE`/`DWORD` resolveram (`dbg_mem.py` ainda mostra o erro antigo,
era o script sem o fix, nao o modulo).

**Armadilha do goal, nao mordida.** A rodada oficial correu com captura do harness
(processo vigiado, nao arquivo de saida) — o 0 byte no meio da corrida nao apareceu
porque nada foi redirecionado para arquivo.

Suite do lote verde, um pytest por vez: faixa OK, asserts OK, folhas 92, alcance 5,
guardas 14, disciplina 5, indice 6, carimbo 6 — mais o G102 (test_01 oficial com `-s`,
test_02–07).

## D147/G120 - os 8 codigos que a F150 ainda nao lia: 7 na pagina, 1 declarado (2026-09-12) - FECHADO

Fecha a cifra do G117 e destrava o G122. Dos 8 codigos / 372 ocorrencias que o
G119 deixou como marcador visivel, **7 foram conferidos na PAGINA RENDERIZADA
(regra 3) e mapeados** — cada um com clip da imagem lido e a pagina anotada na
tabela: `0x81 ü` p.118 "(Rüsch)"; `0x92 ∞` p.50 "t∞ – vida útil da estrutura"
(16x: t∞, φ(t∞,t0), εcs(t∞,t0), σp∞); `0xA8 Δ` p.37 "cnom = cmín + Δc";
`0xEE ×` p.75 "-15 × 10-5" (4x); `0x101 ·` p.139 "αc = 0,85 · [1,0 – ..."
(7x, tambem p.188 "1,5 · FSd"); `0xED –` p.9/p.13/p.46/p.159/p.236 (143x:
sumario, figuras, tabela 8.1, formula, legenda); `0xBC5 –` p.218 tabela 23.2
(12x, celula vazia). **Nenhum glifo deduzido por contexto ou frequencia** —
cada mapeamento tem a imagem correspondente (12 clips lidos, do sumario a
tabela, do bold a prosa).

**Dois achados de subset, os dois com a conta escrita.** Tres bytes desenham o
MESMO traco do `0xB1` ("–", G119): ED e BC5 duplicam o glifo (larguras em
ArialMT2 regular: B1 6,11 pt, ED 5,84–6,42 pt, BC5 6,11 pt — metrica, nao outro
caractere; os tres usos conferidos na imagem). E `0x101` duplica o `0xC2`
("·", G119 p.42): o avanco difere (3,66 contra 3,06 pt no mesmo size) mas o
desenho e o mesmo ponto de multiplicacao (p.139 e p.188 lidas).

**O oitavo continua marcador, com o motivo escrito — era o caso que o goal
previa.** `0x0BD8` (188x, 188/188 imediatamente antes de item de lista "a)",
"b)", "c)"...) tem avanco fixo de 0,91 pt e NENHUMA marca visivel na pagina
renderizada (p.37 e p.52 conferidas em zoom 9x: so o recuo do item). E'
controle de layout do subset, nao glifo — mapear como "" ou " " seria
adivinhar. Segue `[<U+0BD8>]` declarado, com o motivo em `f150_decodifica.py`.

**Medido ao fim.** `desconhecidos` 372 → `{'0BD8': 188}` (lista nominal: so o
declarado). `.txt` regerado (260 p.; "±" e "²" seguem zerados; os do G119
intactos: 123 "ª", 42 "≤", 80 "≥"). `catalogo.csv` (F150) atualizado com os
restantes. Amostra 19 → 26 ancoras em 20 paginas (uma por codigo mapeado, cada
uma lida na imagem); `test_04` ganha `_MAPEADOS_G120`; `test_06` novo trava o
0BD8 como marcador declarado (remapear sem conferir a imagem quebra o teste e
exige triagem). **Vermelho por injecao 1:1 provado**: cada um dos 7 bytes
removido da tabela em memoria derruba exatamente a sua ancora. Nada subiu ao
NotebookLM (regra do goal).

Suite do lote verde: faixa OK, asserts OK, folhas + alcance + guardas +
disciplina + indice + carimbo + f150 **134 passed em 134 s**.

## D148/G122 - as diferencas 2014 -> 2023 que nao estao na Emenda: 1 numero novo, resto igual (2026-09-12) - FECHADO

Fecha a lacuna declarada na Tabela 2 do G116. Confronto secao a secao 2014 x 2023
pre-Emenda nas 45 familias que o framework cita (grep "6118" em 217 .py, 295 linhas;
mesma particao do G116), com texto das duas e veredito por familia. Diferenca de texto
so virou veredito com imagem das duas edicoes (200 dpi, lado a lado). Nenhum modulo
troca de base normativa.

**Medido, com endereco e imagem.** `confronto_2014_2023_g122.py` (producao, fonte unica;
o teste importa daqui) congela CONFRONTO_G122 (45) + MODULOS_POR_FAMILIA +
`cobre_inventario` (cada OK chega ao veredito global) + caso C5 que chama a funcao REAL.
Seis diferencas confirmadas na imagem, uma por uma:
8.2.5 fct,m C55+ F016 p.23 PDF41 "2,12 ln (1 + 0,11 fck)" x F150 p.23 PDF41
"2,12 ln [1 + 0,1 (fck + 8)]" (NUMERO-MUDA, item 52, caso C5);
8.2.8 Eci F016 p.24 PDF42 "NBR 8522 / 20-50 e 55-90" x F150 p.24 PDF42
"NBR 8522-1 e 8522-2 / <=50 e >50" (EDITORIAL, fecha o gap 51-54);
15.4.2 exemplo F016 p.103 PDF121 "...postes e em certos pilares de galpoes industriais."
x F150 p.103 PDF121 "...postes." (EDITORIAL);
15.7.2 F016 p.106 PDF124 "majoracao adicional dos esforcos horizontais" x F150 p.106
PDF124 "majoracao adicional das acoes horizontais" (EDITORIAL, 0,95 e 1,3 iguais);
15.7.3 paragrafo do galpao AUSENTE na F016 p.106 PDF124 x PRESENTE na F150 p.106 PDF124
("Em estruturas de edificacoes com menos de quatro andares...", novidade ja apontada
no G116 item 31, aqui reconfirmada ausente x presente);
18.2.3/18.2.4 frases novas F016 p.146 PDF164 (sem) x F150 p.147 PDF165 ("...no banzo
comprimido." + "O estribo suplementar deve atender ao minimo estabelecido em 18.4.3...",
REGRA-MUDA de detalhamento, sem numero).
Todo o resto IGUAL no numero e na regra aplicados (prosa equivalente a menos de
ortografia; 2014 = 2023 pre-Emenda em 13.2.5.1-b, 12.3.3-s, 15.8.1, 17.3.5.2.4, 17.4.1.1.3,
19.5.4-numero e 20.1, re-sondados aqui). Formula/tabela/figura e limite declarado por
familia (ver pagina renderizada), nunca silenciado; o que ficou ilegivel na extracao
e dito por clausula. O 0BD8 segue marcador declarado (G120).

**O numero novo.** 8.2.5 entra na Tabela 1 como item 52, no mesmo formato, com o caso
do repo: `premoldado_nbr9062._fctm` (2014, funcao real) da 4,300 MPa no C60 contra 4,355
MPa pela prescricao 2023 (+1,3%). [Corrigido no G125/D151: sao 10 modulos que CALCULAM fct,m C55+, nao 5 -
estaca_profunda, fissuracao_nbr6118, laje_concreto, pilar_concreto e
viga_baldrame faltavam; desenho_piso so cita.] Os modulos que aplicam fct,m (base_chumbador.py:83,
fundacao_sapata.py:675, piso_industrial.py:298, premoldado_nbr9062.py:67,
viga_protendida.py:66, desenho_piso.py:103) calculam pela 2014; migrar e decisao do
usuario (G123). 18.2.4 e REGRA-MUDA sem numero (executivo_concreto.py:60 admite
"90-180 graus envolvendo a barra": 90 graus segue tolerado na 2023 pre-Emenda; o
"preferencialmente 135-180" e da Emenda, item 40).

**Cobertura nos dois sentidos.** Cada citacao de "6118" no codigo tem linha na Tabela
2-G122 (45 linhas, cada uma com arquivo:linha; a geral lista as mencoes sem clausula
uma a uma, sem "e outros"); cada secao divergente tem endereco e pagina-imagem
(F016/F150 p. + PDF). O portao `cobre_inventario` cobra familias + modulos + ".py:"
nas divergentes, com acumuladores `faltando_familias` / `faltando_modulos` /
`sem_endereco` que disparam de verdade (vermelho por injecao em tmp_path nos tres
sentidos; intacto verde). Baseline congelado nos dois sentidos (45/45; 1 NUMERO-MUDA).

**Armadilha evitada.** O ".txt" decodificado mente em figura (simbolo sai letra) e a
primeira ocorrencia da clausula no corpo pode ser remissao, nao o texto (15.5 x 15.4,
17.2.5 x 17.2.4.4 novo). Janela titulada + SIM so triam; veredito so com a pagina
renderizada aberta. Nada subiu ao NotebookLM.

Suite do lote (lista nominal): faixa OK, asserts OK, folhas 92 (101,7 s), alcance 5,
guardas 14, disciplina 5, indice 6, carimbo 6 (36 em 32,2 s) + impacto+f150 10 +
confronto 4 (14 em 1,1 s).

## D149/G123 - o projeto declara por qual edicao da norma foi calculado: carimbo de fonte unica e chave desligada (2026-09-12) - FECHADO

Fecha o achado do G116/G119: o framework calcula pela NBR 6118:2014 (F016) e
nenhuma peca de concreto dizia isso, quando a vigente e a 2023 + Emenda 1:2026.
Este goal e o unico do arco que toca o que o cliente recebe — e nao decide por
ele: migrar e decisao do usuario. Entrega a declaracao e a chave; quem vira a
chave e ele. ATP (5.3) e marquise (20.6) nao entram: sao gate novo, nao troca
de conta.

**Fonte unica.** `edicao_nbr6118_g123.py` (producao; o teste importa daqui):
EDICOES_VALIDAS ("2014", "2023+Em1"), EDICAO_PADRAO "2014", DECLARACAO_2014
"NBR 6118:2014", DECLARACAO_2023_EM1 "NBR 6118:2023 + Emenda 1:2026",
S_CIMENTO_2014 (o dict que era de `premoldado_nbr9062.py:53`), limites
120/120/125 mm (13.2.5.1-b), MODULOS_COM_TROCA (2) + USO_ESPERADO (12) +
`resolver_edicao` (sem default silencioso) + `carimbo_edicao` (a folha diz
qual e mesmo sem o parametro) + `s_cimento`/`limite_furo_viga_mm` (os 2
numeros que leem a chave) + `contem_declaracao`/`confere_peca`/`confere_pecas`
(peca sem declaracao reprova, com o motivo nomeado) +
`arquivos_que_importam_edicao`/`confere_uso_edicao` por AST (string em
isencao nao e dependencia) + casos C1/C4 que chamam as funcoes REAIS nas duas
edicoes. "2023" sem Emenda nao e edicao: levanta ValueError em toda porta.

**Chave DESLIGADA, sem default silencioso.** `premoldado_nbr9062.fckj_idade`
ganha `edicao=None` (ausente = 2014, hoje; 2023+Em1: s = 0,20 para todo C60+,
qualquer cimento); `compatibilizacao.avalia_furo_viga` ganha
`edicao=None, forma_furo=None` (ausente = 120 mm, hoje; 2023+Em1: 125 mm SO
para circular explicita; retangular ou forma ausente fica em 12 cm,
conservador — liberar 125 retangular seria nao-conservador). `classifica_`
e `gerar_pendencias` repassam (a forma vem do hint). `verifica_icamento_pilar`
repassa via `caso["edicao"]`. Sem o parametro o numero e o de hoje e o carimbo
diz "edicao nao declarada no projeto — assumida 2014". `projeto_spec.novo`
ganha `norma_6118_edicao=None` (nao bloqueia); invalida BLOQUEIA no `validar`;
`to_rodar_params` repassa; `galpao_concreto.rodar` resolve, carrega em
`res["edicao_6118"]` e fia no icamento. 8.2.5 (G122 item 52) segue 2014
declarado, fora desta chave.

**Carimbo em toda peca de concreto, da fonte unica.** `desenho_concreto`
(armacao, formas, laje: sufixo no titulo existente, sem geometria nova —
`confere_folha_svg` segue verde), `techdraw_concreto.config_de_spec`
(notas 6 + linha do carimbo), `pacote_legal.gerar_pacote`/`markdown` (secao
"Norma de calculo do concreto (G123)", sai sempre), `executivo_concreto`
(quadro + memorial), `galpao_concreto.relatorio_pt`,
`rodar_galpao._consolidar` (MEMORIAL-CONSOLIDADO.txt),
`relatorio_calculo.gerar_pdf` (capa), via `entregaveis_projeto`
(spec repassado). Peca sem a declaracao reprova em `confere_pecas`
(`sem_declaracao` dispara de verdade).

**Aceite medido.** C1 no mesmo caso do repo (circular 125 mm, h = 600 mm):
2014 `a_confirmar` (limite 120) contra 2023+Em1 `admissivel` (limite 125),
com a fonte na clausula ("NBR 6118:2014" x "Emenda 1"). C4 no mesmo caso
(C60 CPIII 7 d, MESMA `fckj_idade` com a chave em cada posicao):
41032 kN/m2 em 2014 contra 49124 em 2023+Em1 (+19,7 %, literais do inventario,
nao formula reescrita). O portao confere que nenhum modulo troca por conta
propria (`confere_uso_edicao` por AST nos dois sentidos: extra ou faltando =
vermelho; `MODULOS_COM_TROCA` tem exatamente os 2, sem ATP nem marquise).
Vermelho por injecao em `tmp_path` nos tres acumuladores
(`sem_declaracao`, `extras`/`faltando`/`ausentes`); intacto verde; None
levanta (nao devolve OK sobre lixo).

**Armadilhas evitadas.** (a) Default silencioso: `edicao=None` declara a
ausencia na folha em vez de fingir escolha. (b) Furo retangular com 125:
forma ausente/retangular nao ganha a dispensa maior. (c) Substring em
isencao virando dependencia: o scan e por AST (`SEM_FAIXA` cita o nome sem
importar). (d) Renomear para escapar do G69: os 3 `confere_*` novos entram
triados no G69 (itens 26-28, INDEPENDENTES), nao renomeados. (e) Liturgia do
G119: o numero so vale porque a producao o le — `fckj_idade` muda com a chave
(C4 prova), `S_CIMENTO` da producao e o da fonte unica.

Suite do lote (lista nominal): faixa OK, asserts OK, folhas 92, alcance 5,
guardas 17 (14 + 3 do G123 triados), disciplina 5, indice 6, carimbo 6 +
edicao 5 (portao proprio).

## D150/G124 - as 61 constantes que ninguem lia: 7 fonte unica, 15 residuos, 39 dividas (2026-09-12) - FECHADO

Fecha a classe que apareceu duas vezes no G119 (D145 item 7): constante
"medida" que a producao nao le e comentario com sintaxe de codigo. O G119
media 95 nunca-lidas-no-proprio-modulo e 51 orfas no repo inteiro; remedido
neste goal na arvore de hoje: 97 / 60 — o delta e o arco G120-G123 (G122 e
G123 criaram e consumiram constantes; ex.: S_CIMENTO virou fonte unica no
G123, LIMITE_FORMULA_TABELA nasceu no G122). A 61a orfa (validacao.TOL) foi
achada pela propria lente nova: a medicao ad-hoc bebia do `.venv` e um
`TOL` de pacote terceiro a escondia; a lente exclui `.venv`/`__pycache__`.

**Maquina.** `varredura_constantes_orfas.py` (producao, fonte unica; o teste
importa daqui): definicao = atribuicao de topo em MAIUSCULAS (com `_`
inicial, licao do G98), uso = Name em Load, atributo `.NOME` ou
`from-import` em qualquer `.py` do diretorio (recursivo, incluindo tests/,
sem `.venv`); mencao em string NAO e uso. `confere()` nos dois sentidos —
`novas` (orfa sem triagem), `resolvidas` (triada que voltou a ser lida ou
sumiu: nome morto), `sem_motivo`, `sem_endereco`, `ausentes` — com
`ORFAS_TRIADAS` de 39 entradas, toda DIVIDA com motivo e endereco de
clausula (o teste cobra o padrao NBR|AISC|NR-|Mamede|Negrisoli|.py:linha).

**Triagem nominal, uma linha cada (61). FONTE UNICA (7, numero identico):**
RHO_MIN fundacao_sapata.py:765 (piso 0,15% no `rho_min`, via maximo);
ALTURA_VERGA_M alvenaria_estrutural.py:164 (primeira altura de
`dimensiona_verga_1133`, :1411); _IW_RIGIDO fundacao_sapata.py:256 (defaults
de `recalque_elastico` :259 e `caso.get` :348); CLASSES_UMIDADE
madeira_nbr7190.py:143 (validacao em `kmod` :228, mesma pertinencia das
chaves de KMOD2); CONFIGS_73 madeira_nbr7190.py:728 (mensagem de erro
:722-725 deriva dela, texto identico); ESCOPO_FUNDACAO_ABERTO
edificio_adapter.py:102 (`_escopo` :150-151 virou loop sobre a tupla);
TOL validacao.py:24 (4× `err < 1e-6` de equilibrio :72-:125, achada pela
lente). **RESIDUO (15, removidos):** TR_KCAL_H (conversao sem chamador);
TIPOS_ESCADA (enum nunca validado; Tab.11 implementa); LIMITE_FORMULA_TABELA
(escopo do G122 sem consumidor; o limite por familia segue no
CONFRONTO_G122; `cobre_inventario` intocado); TAXA_OCUPACAO_3MAIS (o 40%
segue narrado); G_ACO (deriva de E/NU); _COMB (envelope real em
gp._combos_elu); _SEP (parser casa `#`*10); _ROOM_FIELDS (alias sem leitor);
UNIDADE_DIMS/SECAO + ANCORAGEM_PADRAO de geometria_membros (re-exports sem
importador, import removido junto); UNIDADE_DIMS/SECAO de modelo_neutro
(idem); _SJB_SPEC_TEMPLATE (harness usa _SJB_SPEC); _DISCIPLINAS_DA_CASA
(`disciplinas()` implementa com as proprias condicoes). **DIVIDA (39, com
clausula em ORFAS_TRIADAS):** FVK_ARMADA_* ×4 (16868-1 11.4.3, so a Tab.4
nao armada calcula); R_MAX_EXPLOSIVO (1 ohm, Negrisoli); Q_BORDA_GUARDA_CORPO
(nota j Tab.10, so em prosa) e Q_ELEMENTO_ISOLADO_COBERTURA (6120 6.4, so em
prosa); DV_TERMINAL_MAX (5410 6.2.7); COMB_FACHADA (15575-4 7.2.1, d_h entra
pronto) e NOTA_B_TAB2 (15575-2 Tab.2 nota b); deteccao ×3 RAIO/AFASTAMENTO/
LINEAR_PAREDE (17240 5.4.1.1/5.4.1.2/5.4.4); Q_CONCENTRADA da escada (sem
clausula citada, declarado) e da plataforma + PESO_ACO (gaps de modelagem);
ETA1_LISA/ENTALHADA (6118 9.3.2.1, via parametro sem validacao);
UNIDADE_TIPO_ENUM (contrato F06 sem validacao; literais em orcamento
:308-309,347-348, ifc_emit :457, ifc_map :40); PSI0_SOBRECARGA (8681, 0,7
nunca aplicado); K_UMA_BORDA (AISC DG29, sem ramificacao bandeira);
SOBREPRESSAO_TRANSIENTE (5626 6.9.7) e P_DIN_MIN_REDE (5626 6.9.4, so o de
ponto e cobrado); iluminacao ×3 ESPACO_ALTO_MAX/FLUXO_DUPLO/FLUXO_EXCLUSIVO
(10898, teto e 5.2.4/5.2.3); THETA_APOIO_LIM (6118 Tab 13.3, ja citada no
G116); REFLETANCIA_* ×3 (Mamede 2.6.7.1.2, Fu por catalogo); GAMMA_W_ELS
(7190 5.8.6, sem conta ELS de resistencia); EPS_CS_PADRAO (6118 Tab.A.1);
ESP_FUNDO_MIN (9062 7.7.5.1, so a parede e verificada); PAREDE_MIN_MM
(10897 7.7.3); NIVEL_INTERMEDIARIO/INFERIOR (16820 6.3, so o superior sai);
_CUP (15421 Tab.10, sem extracao modal); CD_LOCALIZACAO (5419-2 Tab.A.1) e
RT_R3 (5419-2 Tab.4, so R1 avaliado).

**Nao feito de proposito.** Nenhuma constante foi ligada numa conta so para
"usa-la" (mudaria veredito por motivo administrativo): exigencia sem conta
virou divida, nao wiring. Nenhum portao de outro goal foi tocado
(`cobre_inventario` do G122, vocabulario do G97).

**Aceite medido.** Vermelho por injecao em `tmp_path` nos tres sentidos
(orfa nova acusa, curada vira `resolvida`, renomeada p/ minusculas continua
`resolvida` — licao do G98; intacto verde); isencao sem motivo/endereco
reprova; `test_07` trava os 7 rewires (orfas que voltaram acusam + numero
bit-a-bit: `rho_min(25)==0,0015`, mensagem da 7.3 identica, chaves do
escopo); `test_08` trava a ausencia dos 15 residuos. A lente entrou em
SEM_FAIXA_DECLARADA (cobertura D87) e em SCRIPTS_AVULSOS; o `test_01`
colapsado em mensagem unica passou pelo `confere` do G97 (a primeira versao
com 4 asserts em sequencia foi flagrada por ele — a lente mordeu o proprio
goal no caminho).

Suite do lote (lista nominal): faixa OK, asserts OK, folhas 92, alcance 5,
guardas 14, disciplina 5, indice 6, carimbo 6 + constantes 8 (portao
proprio) — 136 passed; faixa-51 + alcance + asserts-97 + constantes: 34
passed; selftests sapata e alvenaria verdes; 24 passed nos ramos de
madeira/edificio/escopo.

## D151/G125 - auditoria do lote G120-G124: o que a lente nao procurava (2026-09-12) - FECHADO

Auditoria por medicao do arco G120-G124 (D146-D150). Os numeros de manchete
bateram na remedicao: `desconhecidos` da F150 = `{'0BD8': 188}` e zero "±"
no .txt regerado; o "∞" (0x92) conferido na imagem (PDF p.14, "εcs(t∞,t0)");
a 8.2.5 lida nas paginas renderizadas das DUAS edicoes (PDF41: "2,12 ln (1 +
0,11 fck)" x "2,12 ln [1 + 0,1 (fck + 8)]"); o 12.3.3 do G123 da 41032 x 49124
na funcao real, e a regra nova so pega C60+ (medido de C20 a C90 com 4
cimentos: ate C55 os tres caminhos dao o mesmo numero; a unidade kN/m2 ->
MPa esta certa); os 15 residuos do G124 nao tem leitor em lugar nenhum do
repo (fora os worktrees de `.loop-runtime`). Faixa, asserts e orfas OK.

**Seis defeitos, corrigidos. A classe do arco: a lente olhava para onde o
dado ja estava declarado, e nao para onde ele e produzido.**

1. **G122 - o item NUMERO-MUDA listava 6 modulos; a conta mora em 10.** O
   confronto partiu do grep "6118" e deixou fora cinco modulos que CALCULAM
   fct,m C55+ e citam so "8.2.5" na linha da conta: `estaca_profunda:388`,
   `fissuracao_nbr6118:59`, `laje_concreto:441`, `pilar_concreto:407`,
   `viga_baldrame:47,78` (o `desenho_piso` so cita). Migrar a 8.2.5 pelo
   inventario esqueceria metade das contas. Corrigido:
   `sites_formula_fctm` procura a CONTA (regex fora de comentario) e
   `confere_sites_8_2_5` acusa nos dois sentidos (`nao_inventariados`,
   `sem_formula`); inventario (item 52 e Tabela 2-G122) e D148 corrigidos;
   triada 29 no G69; `test_05` com injecao em `tmp_path`.
2. **G122 - o endereco das divergentes era cobrado no texto inteiro.**
   `cobre_inventario` aceitava a divergente se houvesse um ".py:" em
   QUALQUER lugar do inventario: um endereco satisfazia todos, e apagar o da
   8.2.5 nao acusava nada (o teste de injecao apagava todos de uma vez).
   Agora e cobrado na linha `- <familia> |`; o `test_05` apaga so o da 8.2.5
   e exige `sem_endereco == ['8.2.5']`.
3. **G123 - quatro folhas de concreto saiam sem a edicao.** O `test_01`
   conferia so as pecas do GALPAO. Medido em rodada real de casa e predio:
   `planta-formas.svg`, `fundacao-locacao-formas-casa.svg`,
   `planta-formas-pavimento-tipo.svg` e `fundacao-locacao-formas.svg` sem
   declaracao; as de armacao e laje so passavam por citar "NBR 6118:2014"
   numa nota antiga - acerto por acaso, nao pelo carimbo. Corrigido: o
   sufixo da fonte unica nos titulos de `desenho_pavimento` (formas, vigas,
   pilares, vigas+pilares) e `desenho_fundacao_edificio`; `USO_ESPERADO`
   12 -> 14 com a triagem; `test_06` roda a casa real e confere as 4 PE-CO,
   com injecao. Remedido: as 8 PE-CO das duas tipologias declaram; o maior
   titulo estima 1320 px numa folha de 1420; as 5 colisoes de rotulo das
   folhas de laje/detalhes sao as mesmas com e sem o sufixo (preexistentes).
4. **G121 - o medidor de memoria era cego para o freecad.exe.** Se so o
   lado freecad falhava, a amostra virava 0,0 MB e `falhou` ficava falso -
   `falhou` so acendia com os DOIS lados perdidos. Injetado: pico 14,7 MB,
   `falhou: False`. No galpao o freecad e 91 % do pico: o teto de 2500 MB
   passaria sem ter medido o que carrega a rodada. Corrigido:
   `n_amostras_sem_freecad`/`freecad_mensuravel` no resumo, gap no
   `test_01`; e `CUSTO_MEDIDO_N_FREECAD = {casa 0, predio 0, galpao 1}`
   (da corrida oficial do D146) acusa a rodada que ve MENOS freecad do que a
   medida - o caso do `OpenProcess` negado, que devolve soma zero sem erro.
   `test_08` por monkeypatch.
5. **G116/G122 (e a minha auditoria G119) - `test_normas_catalogo`
   vermelho.** `impacto_nbr6118_g116.py` cita NBR 8522 e 8965, e o G122
   acrescentou a 8522 em `confronto_2014_2023_g122.py`, sem lastro no
   catalogo. O lote 06 da suite do G119 ja tinha dado esse vermelho - saiu
   depois do meu relatorio, e eu nao o li. Sao remissoes do TEXTO da norma
   (a Emenda exclui a 8965; a 8.2.8 remete o Eci a 8522), nao fonte de
   calculo, e nao estao no acervo. Corrigido sem inventar lastro:
   `REMISSOES_DA_NORMA_TRANSCRITA` por (arquivo, numero) - um modulo que
   passe a calcular pela 8522 continua reprovando - e teste de fantasma nos
   dois sentidos.
6. **G123 - laco morto** em `edicao_de_resultado` (`for chave in ...:
   pass`), removido.

**Aberto e declarado, nao corrigido.** (a) Casa e predio nao leem a chave
de edicao: o carimbo deles e o do parametro ausente ("NBR 6118:2014"). Um
spec de casa que declare `2023+Em1` sairia com folha dizendo 2014 - que e
por onde calculou, mas a declaracao do projeto nao chega a folha. (b) O
caderno de encargos cita "NBR 6118" sem edicao nas tres tipologias (fora da
lista do G123: pranchas, pacote legal, relatorio). (c) As 5 colisoes de
rotulo no quadro da planta de laje/detalhes de concreto, preexistentes. (d)
`fundacao_sapata.rho_min` aplica `max(RHO_MIN, tabela)` onde a tabela ja
vale 0,0015 - ligacao sem efeito, na fronteira do "ligar constante so para
usa-la" que o G124 proibia; mantida por ser semanticamente o piso da
17.3.5.2.1, dita aqui.

**Suite inteira, lida lote a lote (convencao nova 10).** 283 arquivos em 9 lotes
sequenciais, um pytest por vez: 540 + 216 + 336 + 466 + 369 + 465 + 569 + 392 + 408 =
**3761 passed, 0 falhas**. O executor foi morto por memoria no lote 06; o laco seguiu
(padrao do laco zumbi) e foi vigiado ate o `== FIM`, sem orfao ao final. **Fechado o
aberto do G119:** `test_build_eletrico::test_build_headless_gera_solidos_sem_clash` e
`test_build_federado::test_montar_3d_federado_vivo_e_consistente_com_aabb`, que falharam
 na suite do G119 ("freecadcmd headless nao gerou o resultado do modelo 3D"), passaram no
 lote 02 desta rodada sobre o mesmo codigo daqueles modulos - nao eram regressao. A causa
 daquela falha nao foi medida.

 ## D152/G126 - o cimento que ninguem declarou: piso conservador s=0,38 dito na folha e no memorial (2026-09-13) - FECHADO

 Fecha o medido do G125: `galpao_concreto.py:262` passava
 `spec.get("cimento", "CPV")` ao icamento e `premoldado_nbr9062.py:255`
 repetia `caso.get("cimento", "CPV")`, sem campo no ProjetoSpec/wizard -
 pelo caminho do produto, o galpao SEMPRE calculava com CPV, o `s` mais
 favoravel da 12.3.3. Remedido na funcao real: `fckj_idade(30e3, 7)` da CPV
 24562, CPII 23364, CPIII 20516 kN/m2 (os literais do goal); o default dava
 +19,7 % aos 7 dias sobre um CPIII que ninguem excluiu. Segundo default
 silencioso: `fckj_idade` tinha `cimento="CPII"`. Terceiro: desconhecido
 ("XYZ") virava `s = 0,25` em silencio, o mesmo numero do CPII.

 **Escolha escrita (exigida pelo goal): PISO CONSERVADOR DECLARADO, nao
 bloqueio. Motivo:** o G123 (mesma familia - dado que o projeto nao
 declarou) ja decidiu pela chave DESLIGADA, e o goal manda o campo de
 ProjetoSpec/wizard OPCIONAL ("com a ausencia dita"), o que e incompativel
 com bloqueio; travar todo spec antigo por um dado que nunca foi pedido
 seria punir o usuario pela omissao do framework. Piso nao e "o cimento
 provavel" (Nao fazer do goal): e o MAIOR `s` da tabela (0,38 = CPIII/CPIV
 = menor resistencia jovem), e a folha e o memorial dizem que ele foi usado
 PORQUE o cimento nao foi declarado. Cimento desconhecido LEVANTA
 ValueError com a lista dos validos em toda porta (nunca mais 0,25); nenhum
 cimento de projeto foi escolhido em spec nenhum do repo.

 **Fonte unica.** `cimento_nbr6118_g126.py` (producao; o teste importa
 daqui): CIMENTOS_VALIDOS (os 6 da 12.3.3, so identidade - os valores de
 `s` continuam em `edicao_nbr6118_g123.S_CIMENTO_2014`), PISO_S = 0,38,
 `normaliza_cimento` (desconhecido levanta; None nunca chega aqui),
 `resolver_cimento` (ausente = piso com a origem dita),
 `cimento_de_spec` (le a chave sem default), `linha_cimento` (o que a folha
 e o memorial dizem), `contem_declaracao_cimento`/`confere_pecas` (peca sem
 declaracao reprova; `sem_declaracao` dispara), `defaults_de_cimento`/
 `confere_defaults` (por AST: `.get("cimento", "<valido>")` ou parametro
 `cimento="<valido>"`; baseline vazio) e `arquivos_que_importam_cimento`/
 `confere_uso_cimento` (8 leitores; o executivo compoe o relatorio e nao
 importa - dito na fonte).

 **Fiacao (parte de onde o dado e PRODUZIDO, convencao 9).**
 `premoldado.fckj_idade` passa a `cimento=None`; `verifica_icamento_pilar`
 perde o `get` com CPV e devolve `cimento`/`cimento_origem`/`s_usado`;
 `galpao_concreto.rodar` resolve do spec (invalido BLOQUEIA com o motivo) e
 o resolvido viaja em `res["cimento"]`, `res["spec"]` e `gates["icamento"]`;
 `edicao_nbr6118_g123.s_cimento` aplica o piso ao ausente, levanta ao
 desconhecido, e `S_PADRAO_DESCONHECIDO` foi removido (so ele o lia; nenhum
 teste o citava; o confere das orfas segue verde). **Folha e memorial, da
 fonte unica:** `desenho_concreto` (2 SVG, bloco de 2 linhas no rodape com
 entrelinha que nem o estimador acusa e zero colisoes novas),
 `galpao_concreto.relatorio_pt` (+ `executivo_concreto.memorial`, que o
 compoe), `techdraw_concreto` notas e `pacote_legal` markdown (secao
 "Cimento do concreto (G126)"). **Entrada:** `ProjetoSpec.cimento`
 (opcional, ausente = piso dito; invalido bloqueia) + pergunta opcional no
 wizard + repasse em `to_rodar_params`. Nao feito de proposito: o PDF do
 memorial (a declaracao mora no memorial em texto, que o portao confere) e
 o quadro de aco (sem fckj).

 **Casos do repo, um a um, antes (CPV) x depois (piso), na funcao REAL
 (o "nao medido" do goal, agora medido). NENHUM vira veredito** - o OK do
 icamento e do aco (0,50 fyk) e a fissura informa; os numeros caem:
 ica8/selftest (t=3): fckj 19,9 -> 13,7 MPa, Mr,fiss 23,49 -> 18,36,
 fissura False -> False, OK True -> True; ica10/ponto-otimo (t=5): 22,8 ->
 17,8, 43,45 -> 36,88, False -> False, True -> True; ica14/pilar-longo
 (t=2): 17,3 -> 10,6, 6,03 -> 4,34, True -> True, False -> False;
 galpao10 e galpao15 (t=3): 19,9 -> 13,7, False -> False, gate True ->
 True. fckj(30e3,7): 24561,9 -> 20515,8 (= CPIII explicito, longe do CPV).
 Que o instrumento acusa quando ha o que acusar: fronteira construida L=12
 (40x40, As=12, t=3, Md=20,88) - Mr,fiss 23,49 (CPV, sem fissura) contra
 18,36 (piso, COM fissura). Travado em `test_04` com estes literais.

 **Aceite medido.** Vermelho por injecao em `tmp_path` nos quatro
 acumuladores (`sem_declaracao`, `defaults`, `extras`, intacto verde);
 invalida levanta nas 7 portas (`normaliza`, `resolver`, `cimento_de_spec`,
 `fckj_idade`, `verifica_icamento_pilar`, `rodar`, `s_cimento`), sempre com
 a lista dos validos; `None` em `confere_pecas` levanta TypeError e
 `normaliza(None)` levanta (ausencia nao e cimento invalido). As 3
 `confere_*` novas entram triadas no G69 (itens 30-32); o modulo novo entra
 isento com motivo em SEM_FAIXA_DECLARADA; o helper de nota entra isento
 com motivo em ISENTAS do G77 (nao e emissor de folha - a lente se adapta
 ao codigo, G64).

 **Suite do lote (lista nominal, lida inteira - convencao 10):** faixa OK
 (0/0/0/0), asserts OK, orfas OK (0 em tudo), folhas 92, alcance 5, guardas
 14 (com os 3 do G126 triados nos itens 30-32), disciplina 5, indice 6, carimbo 6, normas 3 +
 cimento 5 (portao proprio) - 136 passed, 0 falhas. Regressao alem do lote:
 edicao 6 (inclui rodada real), premoldado + galpao_concreto + guardas 52,
 desenho + executivo + techdraw + pacote 32, g50 + fronteiras 27, validacao
 + wizard + aco + tipo-ligacao 48, bloco + techdraw-concreto 11, faixa 22 -
  tudo verde.

  ## D153/G127 - a fct,m em onze copias vira fonte unica, sem mover um ulp (2026-09-13) - FECHADO

  Fecha o medido do G125: a expressao do ramo alto (`2,12 ln (1 + 0,11
  fck)`) estava escrita em 11 linhas de 10 modulos (base_chumbador:99,
  estaca_profunda:388, fissuracao_nbr6118:59, fundacao_sapata:681,
  laje_concreto:441, pilar_concreto:407, piso_industrial:73,
  premoldado_nbr9062:125, viga_baldrame:47,78, viga_protendida:70), todas
  com o limiar `fck <= 50` e o mesmo numero. Remedido na funcao real
  antes da migracao: fis/pm/vp devolvem 2210,4188991842316 kN/m2 em C20,
  4071,626424892359 em C50, 4140,418547667256 em C55, 4299,674284259645
  em C60 e 5064,177113178408 em C90. O "nao medido" do goal (unidades)
  foi medido: dois jeitos de entrar e sair sem divergencia de conta -
  MPa -> MPa (estaca, fundacao, piso) e kN/m2 -> kN/m2 (fissuracao,
  premoldado, protendida, baldrame/flecha); os quatro
  cortantes/ancoragens convertem no contorno. NENHUM caso do repo muda
  de numero, logo nenhum muda de veredito: o depois e `==` ao antes em
  todos os modulos x C20/C50/C55/C60/C90 (os literais acima, travados no
  `test_02`).

  **Fonte unica.** `fctm_nbr6118_g127.py` (producao; a lente e o teste
  importam daqui): `fctm_MPa` (MPa -> MPa, o miolo) + `fctm` (kN/m2 ->
  kN/m2, a mesma conta) + `fctk_inf/sup` nas duas unidades (as copias
  derivavam `0,7 * fctm` inline; nenhuma derivava o sup). O `fctd`
  (`fctk,inf / gamma_c`) continua nos modulos: e de outra clausula
  (9.3.2/17.4/19.4.1), e as linhas de baixo seguem intocadas. Cada
  modulo chama a primitiva do seu sistema de unidades.

  **Faixa declarada e guardada, sem travar a producao.** A faixa e o
  limiar entre os ramos (`fck <= 50 MPa`, com o `if` no corpo - a lente
  do G51 a ve guardada). A primeira versao travava fora de C20-C90 com
  ValueError - e a suite acusou o erro: `verifica_icamento_pilar` avalia
  fct,m no fckj jovem (13,74 MPa aos 3 dias no galpao de concreto), fora
  de C20. Trava dura ali mudaria veredito de peca real, entao o fckj
  jovem usa a mesma expressao por extrapolacao DECLARADA (dita na fonte,
  com o numero medido), e o `test_05` trava o limiar + o jovem em vez
  de travar a producao.

  **Fiacao (parte de onde o dado e PRODUZIDO, convencao 9).** Os 10
  modulos importam a fonte e apagam as 11 copias; o detector da conta
  (`RE_FCTM_C55`) mora na fonte e a lente do G122 o importa (um detector
  so). O item 8.2.5 do `CONFRONTO_G122` lista a fonte + quem so cita
  (desenho_piso); o caso C5 chama a fonte; o item 52 e a Tabela 2-G122
  do inventario apontam para a fonte unica. A 2023 (`0,1 * (fck + 8)`)
  nao entrou em nenhum dos 11 arquivos (`test_06` varre o codigo): virar
  a edicao segue decisao do usuario (G123).

  **Aceite medido.** Vermelho por injecao em `tmp_path` nos quatro
  acumuladores (`copias` fora da fonte, `fonte_apagada`, `extras`,
  `faltando`; comentario nao conta como conta; intacto verde); os 2
  `confere_*` novos entram triados no G69 (itens 33-34); `test_01` do
  G51 passa a cobrar a fct,m guardada na fonte; piso/viga_baldrame/
  viga_protendida (que so declaravam faixa pela copia) entram isentos
  com motivo em SEM_FAIXA_DECLARADA ("faixas vivem na fonte", o mesmo
  molde dos adaptadores); `test_05` do G122 atualizado (1 sitio, nao
  10).

  **Suite do lote (lista nominal, lida inteira - convencao 10):** faixa
  OK (0/0/0/0), asserts OK, orfas OK (0 em tudo), folhas 92, alcance 5,
  guardas 14 (com os 2 do G127 triados nos itens 33-34), disciplina 5,
  indice 6, carimbo 6, normas 3 + fonte-unica 6, confronto 5 e fctm-c60
  11 (portoes proprios) - tudo verde, 0 falhas. Regressao alem do lote:
  cimento 5 + edicao 6, 343 passed nos ramos de concreto tocados
  (baldrame, base, desenho, estaca, executivo, fissuracao, g50, laje,
  pilar, piso, premoldado, puncao, alonso, vibracao, protendida) e 49
  passed em galpao_concreto/bim/techdraw/laje-paineis/fronteira - tudo
  verde.

  ## D154/G128 - a declaracao da edicao chega as tres tipologias (2026-09-13) - FECHADO

  Fecha os abertos (a) e (b) do D151: o G123 tinha fiado a chave
  `norma_6118_edicao` so no galpao - casa e predio carimbavam o parametro
  ausente, as tres tipologias chamavam `gerar_pendencias` sem `edicao`, e o
  caderno escrevia "NBR 6118" sem edicao (4x na casa, 4x no predio).

  **Fonte unica.** `edicao_nbr6118_g123.py` (producao; o teste importa
  daqui): ganha `edicao_de_normalized` (le `raw_spec`, depois
  `turnkey_spec`; ausente = None, invalida levanta) e o USO_ESPERADO vai
  de 14 para 19 (+ casa_residencial, edificio_adapter, galpao_adapter,
  desenho_casa_residencial, caderno_encargos - triagem escrita na fonte e
  no item 28 do G69: so LEEM a chave e a repassam, nenhum troca conta;
  MODULOS_COM_TROCA intacto, 8.2.5 segue 2014 declarado, fora da chave).

  **Fiacao (parte de onde o dado e PRODUZIDO, convencao 9).** Folhas de
  casa/predio: `desenho_pavimento` (formas, vigas, pilares, combinada +
  `_subtitulo_pilares`, que era literal "2014" fixo), `desenho_fundacao_
  edificio` e `desenho_concreto` (laje, via `_carimbo_edicao` com edicao
  explicita vencendo o resultado) ganham `edicao=None` (ausente = hoje,
  byte-identico); `desenho_casa_residencial` resolve do turnkey e os hooks
  passam a declarada. Compat x3: os 3 adapters passam a declarada a
  `gerar_pendencias`, que carimba `edicao_6118` em cada pendencia (ausente
  = "2014", dito). Caderno: `gerar_caderno`/`markdown`/`caderno_de_turnkey`
  ganham `edicao` (a "NBR 6118" sai com a da conta + secao "Norma de
  calculo do concreto (G123)", sempre); pacote de casa/predio recebe o
  spec (o do galpao, o projeto declarado em vez do turnkey so).

  **Achado real no caminho (medido, nao suposto).** Com a chave injetada
  no topo, o pacote do galpao seguia dizendo 2014 (lia so o turnkey, que o
  normalize monta sem a chave) e o calculo do concreto nem a recebia
  (`galpao_turnkey` nao a repassa ao payload "concreto") - metade do
  projeto em 2023, metade em 2014, cada peca "certa" sozinha. Corrigido no
  goal: `_run_turnkey` repassa a declarada ao payload (o proximo da
  producao vence; sem ela, nada muda) e o pacote le o projeto declarado.
  Regra que vale daqui em diante: chave no topo do project-spec chega ao
  calculo do galpao; casa/predio nao calculam pela chave (so a
  compatibilizacao ramifica), por decisao do G123.

  **Aceite medido (rodada real x 2 chaves, tmp_path, repo intacto).**
  Casa: 4 PE-CO + pacote + caderno declaram 2014/2023+Em1, 61 pendencias
  carimbadas; predio: idem, 126 pendencias; galpao (sem 2D, o emissor de
  desenho e do G123): 2 SVG do calculo + pacote + caderno + 970
  pendencias, tudo na edicao da conta. Furo circular 125 mm: sem chave
  `a_confirmar`, com 2023+Em1 `admissivel`; retangular, sem-forma e sem
  hint nao mudam (so com ela). Vermelho por injecao: folha 2014 com chave
  2023 reprova nomeando os dois lados; "NBR 6118" sem edicao reprova;
  invalida levanta nas 4 portas novas. Nenhum project-spec.json do repo
  declara a chave (travado no `test_08`; virar a edicao segue decisao do
  usuario).

  **Suite do lote (lista nominal, lida inteira - convencao 10):** faixa
  OK (0/0/0/0), asserts OK, orfas OK (0 em tudo), folhas 92, alcance 5,
  guardas 14 (item 28 com os 5 do G128 triados), disciplina 5, indice 6,
  carimbo 6, normas 3 - 131 passed, 0 falhas. Portoes proprios: tipologias
  8 (inclui as 6 rodadas reais), edicao 6 (baseline 19 usos). Regressao
  alem do lote: compat 2 arquivos + caderno + armacao x2 + casa-indice +
  indice-g91 + caderno-casa-edificio + pacote/orcamento/fronteiras - 140
  passed, 0 falhas.

## D155/G129 - os rotulos que se sobrepoem, agora com censo: 19 colisoes reais corrigidas, 43 pares triados (2026-09-13) - FECHADO

Fecha o medido do G125: 6 de 27 folhas de casa+predio com colisao (48
pares) sem nenhum censo sobre todas as folhas entregues, e o galpao sem
medicao nenhuma. Remedido na arvore de hoje, rodada real casa+predio
(`run_project` nos specs persistidos, `generate_2d`): 12 + 15 = 27 SVGs
do manifesto, os mesmos 48 pares nas mesmas 6 folhas (planta-eletrica 15,
planta-baixa 8, telhado-tesoura 8, quadro-cargas 7, detalhes-concreto-casa
5, planta-laje-pavimento-tipo 5) - a remedicao bate com o G125 par a par.

**O galpao, medido.** O manifesto do galpao entrega PDFs
(`*/pranchas/*.pdf`, cobertos pelo G102), que o estimador SVG nao le; a
medicao parte de onde o dado e PRODUZIDO (convencao 9): o turnkey real do
spec persistido (`galpao-tp-g95`, `tk.rodar` puro sem freecad.exe, 29,7 s
- o custo de 923 s do G102 e freecad+caderno, nao o calculo) + os 8
emissores SVG que o `config_de_spec` rasteriza na rota G104. 14 pares em
4 fontes (planta-seguranca 8, diagrama-unifilar 3, planta-formas 2,
esquema-hidraulica 1; climatizacao, quadro-cargas, planta-eletrica e
prancha-armacao com 0). Total do censo: 35 folhas, 62 pares.

**Triagem par a par, PNG a PNG (regra 3, fitz como no G94/G104).**
19 colisoes REAIS, todas na eletrica residencial da casa real (a fixture
sintetica dos guardioes da folha tem 1 ponto por comodo e nunca acusou):
planta-eletrica 12 (etiquetas L-*/T-* sobrepostas - luz e tomada no mesmo
ponto do layout saiam com a etiqueta na mesma origem; no Banheiro
L-BAN/T-BAN-01/TUE-CHUV vinham 100 % sobrepostos, ilegivel) e
quadro-cargas 7 (o COMODO de 7 comodos atravessava TIPO/CARGA/I/SECAO/
DISJ.). 43 FPs em 4 familias, cada um com o motivo e o PNG: linhas
empilhadas legiveis (planta-baixa 8, RESUMO do incendio 8, legenda e
blocos de comodo); entrelinha apertada porem legivel sem toque de glifo
(telhado 8, unifilar 3, hidraulica 1, titulo/formas 1); bloco VERIFICACOES
(detalhes 5 + laje 5: textos SEM text-anchor, start real - o estimador
centra a caixa em middle e ainda superestima a largura em 0,6*size); e um
texto rotacionado (cota `90.00 m`, rotate -90, que o estimador ignora).

**Correcao na folha (F1/F2, desenho_eletrico_residencial.py).** F1: a
etiqueta do ponto tenta 10 deslocamentos fixos, em ordem, e fica no
primeiro que nao encosta em rotulo de comodo, no quadro nem em etiqueta
ja posta, na regua do G129 (censo 15 -> 3, os 3 FPs de bloco/legenda).
F2: a celula do quadro quebra em linhas que cabem na coluna
(`_quebra_celula`, item com virgula fica inteiro - "Dormitorio 01" nao
parte no meio) e a altura da linha acompanha a celula mais alta,
entrelinha 17 px em corpo 11 (caixa do estimador 15,4); a coluna GOVERN.
guarda a largura do "piso da tabela (norma 1,5 mm2)", que tem guardiao
proprio cobrando a string inteira (phase6b). Censo 7 -> 0, PNGs
posfix-*.png re-conferidos. A correcao nao muda a fixture sintetica
(quadro 0, planta 1 par de legenda, unifilar 0 - byte-comportamento
preservado onde nao havia colisao; phase6b 36 passed sem retoque).

**Portao (`varredura_colisoes_g129.py`, SCRIPT AVULSO; teste-guarda
`tests/test_colisoes_censo_g129.py`, 6 testes).** Fonte unica: o teste
importa de la (universo de 35, BASELINE de 43 pares em 9 folhas,
ISENCOES com PNG em todo motivo, CORRIGIDOS com os 19). `confere_censo`
nos dois sentidos (par novo, par sumido, sem_triagem, isencao morta,
folha nova, folha sumida); vermelho por injecao em `tmp_path` (rotulo
empurrado, motivo apagado, par sumido); malformada levanta e SVG
malformado vira par acusador. Integracao: item 35 + triagem no G69
(`confere_censo` casa no `confere_\\w+`; `conferir_` nao casaria e viraria
fantasma), isencao com motivo em SEM_FAIXA_DECLARADA, `pares_de_svg` em
ISENTAS do G77 (wrapper, nao emissor - a lente se adapta ao codigo, G64),
registro em SCRIPTS_AVULSOS. Teste novo em estilo de um assert so (G97).

**Achado de metodo.** O guardiao do quadro (`test_nenhum_texto_do_quadro_
invade_a_coluna_seguinte`) passava na fixture e a folha real transbordava:
guardiao por folha nao substitui censo sobre rodada real - era exatamente
o buraco que o G129 fechou.

**Nao-coverture declarada (na lente).** Rotulo x simbolo/linha (o
estimador so mede texto x texto); texto rotacionado alem do caso triado;
a fileira Momentos do VERIFICACOES segue com vao real curto (~8 px,
legivel, FP triado) - valor mais longo vira par novo e reabre a triagem.

**Suite do lote (lista nominal, lida inteira - convencao 10):** faixa OK
(0/0/0/0), asserts OK, orfas OK (0 em tudo), folhas 92, alcance 5,
guardas 14 (item 35 com o G129 triado), disciplina 5, indice 6, carimbo 6,
normas 3 - 137 passed, 0 falhas. Portao proprio: colisoes 6 (inclui as 3
rodadas vivas: casa 2,3 s + predio 30,9 s + turnkey do galpao 29,7 s).
Regressao alem do lote: phase6b 36 + casa-eletrica-g99 + casa-concreto +
laje-paineis + casa-indice + caderno-casa-edificio + golden-journey +
casa-adapter - tudo verde, 0 falhas.

## D156/G130 - as 39 dividas que o cliente nao ve: toda aplicavel no pacote, com a clausula da fonte unica (2026-09-13) - FECHADO

Fecha o medido do G125: `varredura_constantes_orfas.ORFAS_TRIADAS` tem 39
DIVIDAS com clausula - exigencias de norma escritas e nao verificadas - e
zero mencoes (nome, clausula ou "nao verificado") nos documentos entregues
de rodada real de casa e predio. Nao medido: o galpao; quais se aplicam a
cada tipologia (e o que este goal declara).

**Fonte unica.** `exigencias_nao_verificadas_g130.py` (producao; a lente e
o teste importam daqui): TIPOLOGIAS (casa/predio/galpao, "edificio" e alias
de "predio"), APLICABILIDADE (para cada chave de ORFAS: o conjunto onde
vale + o motivo escrito onde nao vale), `exigencias_para_tipologia` /
`nao_aplicaveis_para_tipologia` (leem ORFAS ao vivo: divida nova sem
triagem vira sem_triagem, nunca some), `linha_exigencia` /
`linhas_markdown` / `markdown_secao` (nome + arquivo + motivo + endereco da
fonte unica + a marca "não verificada pelo framework"),
`contem_exigencia` / `confere_documento` (portao por substring, por parte:
cada aplicavel tem de chegar ao veredito) e `confere_aplicabilidade` /
`confere_uso_exigencias` (baseline nos dois sentidos). A clausula/motivo
NAO sao copiados: moram em ORFAS_TRIADAS (fonte unica do G124), lidos ao
vivo. Nenhuma conta importa esta fonte para calcular (so PUBLICA).

**Fiacao (parte de onde o dado e PRODUZIDO, convencao 9).**
`pacote_legal.gerar_pacote` ganha `tipologia` (ausente = a uniao das tres,
o pacote nunca esconde divida por falta de rotulo; invalida levanta) e o
markdown ganha a secao obrigatoria G130, sempre (mesmo molde G123/G126);
os 3 emissores passam a tipologia (`gestao_casa` = casa,
`gestao_edificio` = predio, `entregaveis_projeto.emitir_pacote_legal` =
galpao, via `pacote_no_manifesto`). Sem tipologia = 39 itens; com
tipologia = o recorte.

**Promocao honesta no caminho (medida, nao suposta).** A fonte das
clausulas (`varredura_constantes_orfas.py`) se declarava SCRIPT AVULSO
("nao importada por ninguem") - e o G130 manda a producao ler ORFAS ao
vivo. O proprio guarda (`test_scripts_avulsos_nao_sao_importados_por_
ninguem`) manda "deixar de ser avulso, ou o import sai": a lente virou
MODULO DE PRODUCAO no cabecalho e saiu de SCRIPTS_AVULSOS (alcancavel via
pacote_legal <- adaptadores <- ENTRADAS, sem ilha). Sem string-import nem
copia de clausula para escapar do guarda (licao do G98).

**Lista por tipologia (exigida pelo goal; 18 + 24 + 30 = 39 na uniao).**
CASA (18): FVK_ARMADA_COEF/RHO_TETO/TAU0_MP/TETO_MP (16868-1 11.4.3, caminho
portante pode ser armado); R_MAX_EXPLOSIVO (quando houver area
classificada); Q_BORDA_GUARDA_CORPO (sacada/terraco) e
Q_ELEMENTO_ISOLADO_COBERTURA (6120 6.4); DV_TERMINAL_MAX (5410 6.2.7);
COMB_FACHADA (15575-4 7.2.1) e NOTA_B_TAB2 (15575-2 Tab.2 nota b);
ETA1_ENTALHADA/LISA (6118 9.3.2.1); UNIDADE_TIPO_ENUM (contrato F06);
SOBREPRESSAO_TRANSIENTE (5626 6.9.7) e P_DIN_MIN_REDE (5626 6.9.4);
THETA_APOIO_LIM (6118 Tab 13.3, tem laje); GAMMA_W_ELS (7190 5.8.6, tesoura
de madeira); _CUP (15421 Tab.10, quando houver extracao modal). Fora da
casa, com o motivo no codigo: deteccao x3 / iluminacao x3 / sinalizacao x2
/ sprinklers (unifamiliar sem sistema central exigido); escada/plataforma
x2/gusset/protensao/premoldado (sem aco industrial nem pre-moldado);
15575 nao se aplica ao galpao (abaixo); refletancias (so galpao); SPDA x2
(sem SPDA avaliado).
PREDIO (24): R_MAX_EXPLOSIVO; Q_BORDA + Q_ELEMENTO; DV_TERMINAL;
COMB_FACHADA + NOTA_B_TAB2; deteccao x3 (17240 5.4.1.1/5.4.1.2/5.4.4);
ETA1 x2; UNIDADE_TIPO_ENUM; hidraulica x2; iluminacao x3 (10898 + 5.2.4 +
5.2.3); THETA_APOIO_LIM; PAREDE_MIN_MM (10897 7.7.3);
NIVEL_INFERIOR/INTERMEDIARIO (16820 6.3); _CUP; CD_LOCALIZACAO (5419-2
Tab.A.1) + RT_R3 (5419-2 Tab.4). Fora do predio: FVK armada x4 (portico de
concreto, alvenaria e vedacao); escada/plataforma/gusset/PSI0/protensao/
premoldado/refletancias/madeira (sem esses sistemas).
GALPAO (30): R_MAX_EXPLOSIVO; Q_ELEMENTO_ISOLADO; DV_TERMINAL; deteccao
x3; Q_CONCENTRADA da escada industrial; ETA1 x2; UNIDADE_TIPO_ENUM;
PSI0_SOBRECARGA (8681); K_UMA_BORDA (AISC DG29); hidraulica x2;
iluminacao x3; REFLETANCIA_PAREDE/PISO/TETO (Mamede 2.6.7.1.2, metodo dos
lumens); EPS_CS_PADRAO (6118 Tab.A.1); PESO_ACO + Q_CONCENTRADA da
plataforma; ESP_FUNDO_MIN (9062 7.7.5.1); PAREDE_MIN_MM;
NIVEL_INFERIOR/INTERMEDIARIO; _CUP; CD_LOCALIZACAO + RT_R3. Fora do galpao:
FVK armada x4 (fechamento metalico); Q_BORDA (sem borda habitacional);
15575 x2 (habitacional); THETA (sem laje); GAMMA_W (sem madeira).

**Aceite medido (rodada real, spec persistido, repo intacto).** Casa (2,9 s)
18/18 no pacote-legal.md; predio (~35 s) 24/24; galpao sem 2D (~30 s,
o pacote independe dele) 30/30 - `confere_documento` OK nas tres.
Vermelho por injecao em `tmp_path`: divida nova em ORFAS (copia em memoria)
vira sem_triagem e o documento sem ela reprova; documento com
FVK_ARMADA_COEF arrancado reprova nomeando; tipologia invalida levanta nas
6 portas (lente x4 + pacote); intacto verde; "edificio" canoniza para
"predio". Nao feito de proposito: nenhuma verificacao implementada, nenhuma
constante ligada em conta (cada divida segue em ORFAS_TRIADAS).

**Suite do lote (lista nominal, lida inteira - convencao 10):** faixa OK
(0/0/0/0), asserts OK, orfas OK (0 em tudo), folhas 92, alcance 5, guardas
14 (itens 36-38 com o G130 triado), disciplina 5, indice 6, carimbo 6,
normas 3 - tudo verde, 0 falhas. Portao proprio: exigencias 6 (inclui as 3
rodadas vivas: casa + predio + galpao sem 2D). Baseline travado: 39
dividas, casa 18 / predio 24 / galpao 30, uniao 39; LEITORES_ESPERADOS 2
(a fonte + pacote_legal).

## D157/G131 - auditoria do lote G126-G130: a entrega declarava um valor e a conta usava outro (2026-09-13) - FECHADO

Auditoria por medicao do lote G126-G130 (D152-D156), sem confiar no que os
verbetes dizem.

**Bateram na remedicao.** G127: os 11 escalares do teste comparados HEAD
(pre-migracao, `git archive`) x arvore em 9 fcks (C20, C35, C50, C50,5, C55,
C60, C75, C90 e o fckj jovem 13,74 MPa) - 99 valores, zero divergencias com
`==`; os literais ANTES_MEDIDO do teste sao os do HEAD (nao tautologia). As
`0,3 fck^(2/3)` que sobraram (base_chumbador:797, estaca_profunda:672) sao
selftest de referencia, nao producao. G126: fckj(30e3,7) CPV 24562 x CPIII
20516 na funcao real; zero defaults por AST. G130: casa 18, predio 24,
galpao 30 no pacote de rodada real (portao proprio verde). G129: portao
vivo verde nas 3 rodadas.

**Defeitos corrigidos (5).**
1. **G126 - pacote e conta liam o cimento de lugares diferentes.** Rodada
real do galpao (`galpao-tp-g95`, sem 2D): com `"cimento": "CPII"` no TOPO
do project-spec, o pacote dizia "CPII (declarado no projeto)" e a conta
usava o piso (s=0,38); com CPII no payload `turnkey.concreto`, a conta usava
0,25 e o pacote dizia "nao declarado - piso". O teste do G126 conferia as
pecas so sem cimento e o pacote sem spec - a lente olhou a declaracao, nao o
caminho do produto (a classe do D151, pela terceira vez). Corrigido:
`cimento_do_turnkey(R)` le o que a conta gravou; `cimento_da_entrega` faz o
resultado vencer e LEVANTA quando o spec declara outro;
`galpao_adapter._run_turnkey` leva o topo ao payload e levanta com os dois
divergentes; `emitir_pacote_legal` passa o calculado. Remedido: topo CPII e
payload CPII saem CPII na conta, nas 2 folhas e no pacote; topo CPII x
payload CPIII falha a rodada com o motivo no project-run.json, sem pacote.
2. **G126 - casa e predio afirmavam "piso conservador s=0,38" no icamento
sem icamento nenhum calculado** (pacote-legal.md de rodada real). Terceiro
estado declarado na fonte unica: "sem icamento de pre-moldado calculado
nesta entrega - nenhum fckj depende do cimento" (ORIGEM_SEM_ICAMENTO; o
portao reconhece a marca).
3. **G128 - a mesma precedencia silenciosa na edicao.** Com 2023+Em1 no topo
e 2014 no payload concreto, pacote, caderno e pendencias diziam 2023+Em1 e a
conta e as 2 folhas diziam 2014 (medido, `contem_declaracao` por peca): o
payload vencia calado. Agora levanta; a mesma edicao nos dois lugares segue.
4. **G126 - `relatorio_pt` embrulhava a linha do cimento (e o carimbo do
G123 ao lado) num `except Exception`** que trocava qualquer erro por texto
fixo; e 3 fallbacks `except ImportError` (pacote, techdraw, desenho) mais o
do markdown repetiam a linha literal fora da fonte unica - o G127 acabava de
desfazer 11 copias de uma conta. Removidos: a linha vem so da fonte.
5. D156 com um byte corrompido na marca "nao verificada" - corrigido.

**Achado e NAO corrigido (vai para o backlog G132-G136, medido).**
(a) A chave 2023+Em1 carimba a edicao INTEIRA e so troca 2 pontos (12.3.3 no
icamento e 13.2.5.1 no furo): na casa real com a chave, as 4 folhas PE-CO e
o caderno dizem "calculado pela NBR 6118:2023 + Emenda 1:2026" e o memorial
da sapata, na MESMA entrega, diz "NBR 6118:2014" - o memorial esta certo. O
portao do G128 compara a folha com a chave de entrada, nao com a conta.
Latente (nenhum project-spec do repo declara a chave, test_08); redesenhar a
declaracao parcial toca os portoes G123/G128 inteiros - e goal.
(b) `ProjetoSpec.cimento` e a pergunta do wizard viajam por
`to_rodar_params` ao `rodar_galpao` metalico, que nao le a chave e nao tem
icamento de pre-moldado: pergunta sem conta.
(c) A viga protendida do galpao de concreto calcula com
`fck = max(fck, 40e3)` (galpao_concreto:223) e `fckj = fck` na
transferencia (viga_protendida:154).

**Suite (lista nominal, lida inteira - convencao 10): 3795 passed, 0 falhas,
289 arquivos.** Lotes: 522 + 158 + 297 + 381 + 401 + 459 + 325 + 511 (lote
07 sem o G102) + 403 + 330 + 8 (G102 isolado, 1150 s). Dois achados de
metodo no caminho: (1) o runner listava `tests/test_*.py` e pegava 246
arquivos - as subpastas `tests/branches` (42) e `tests/trunk` (1) ficavam de
fora; a lista passou a ser `find tests -name 'test_*.py'`; (2) o galpao com
freecad.exe (~2 GB de pico) nao cabe na memoria livre da maquina junto de
outros aplicativos abertos, e o harness matava o lote em segundo plano: o
G102 rodou isolado, como processo independente, e passou.

## D158 - tempo de suite: o solver do pilar e o FSM das tercas, sem mover um bit (2026-09-13) - FECHADO

Pedido do usuario: a suite atrasava o desenvolvimento; melhorar sem degradar
a qualidade - item 1 (medir com `--durations`) e item 2 (rodada real
compartilhada por sessao).

**Medido antes (item 1).** Lotes da suite de 289 arquivos: 00 42:43, 04
21:46, 05 12:26, 06 12:20; 01-03 e 07-09 somam ~26 min; o G102 isolado, 19
min. O perfil de uma rodada do predio (`edificio_adapter.run_edificio`, 23,5
s sem profiler) pos 99 % do tempo em `pilar_concreto._resultante_concreto`:
500 396 chamadas, 30,5 milhoes de `_sigma_c` e 31 milhoes de `_eps_fibra`,
com `eps_cu`/`eps_c2`/`expoente_n`/`alpha_c_pilar` recalculados por fibra;
80,5 % das chamadas de `_N_M_resistente` repetiam argumentos exatos. Por
isso cada teste do G12 levava ~29,5 s e o multipavimento ate 77 s - o custo
nao era o `run_project`. No galpao metalico, `distorcional_fsm.
curva_assinatura` (pycufsm) era 13,8 dos 18,5 s de um check do G15: 30
chamadas em 3 checks, 5 argumentos distintos (83 % de repeticao).

**Item 2 (rodada real compartilhada): NAO feito, com o motivo.** O
levantamento achou 4 grupos de mesmo spec persistido com as mesmas opcoes
RESOLVIDAS entre arquivos (predio com 2D, 7 usos; casa com 2D com e sem
IFC, 6 e 5; predio so IFC, 2) - e so um teste escreve numa pasta de rodada
real (o `test_06` do G102). Com o predio a ~7 s depois da otimizacao,
compartilhar economiza segundos e poe estado entre testes; as rodadas do
galpao que sobram sao injecoes diferentes. O helper escrito foi removido
antes de qualquer teste usa-lo.

**O que mudou (so tempo; nenhum numero).**
1. `pilar_concreto._resultante_concreto`: o que nao depende da fibra sai do
   laco; por fibra, as mesmas operacoes de ponto flutuante na mesma ordem.
   `_N_M_resistente` memorizado (`lru_cache(maxsize=65536, typed=True)`:
   funcao pura de floats, devolve tupla imutavel).
2. `distorcional_fsm.curva_assinatura`: a conta em `_curva_assinatura_calc`,
   memorizada (`maxsize=256`); a publica devolve COPIAS dos arrays.

**Prova de que nao degrada.**
(a) Predio inteiro: sha256 de `json.dumps(run_edificio(...))` identico no
HEAD (duas execucoes, determinismo conferido) e na arvore, `c679562d...`,
516 083 bytes; 23,5 s -> 4,6 s.
(b) `tests/test_pilar_solver_equivalencia_d158.py`: a integral `==` o laco
original (que chama as primitivas por fibra) em 448 casos (C20-C90, dominios
2, 3/4 e 5, fronteiras x23 e h); cache `==` `__wrapped__` frio e quente;
dimensionamento completo igual com cache limpo e cheio; e o VERMELHO: uma
operacao reordenada, algebricamente igual, e acusada pelo `==`.
(c) `tests/test_fsm_cache_d158.py`: cache igual a funcao crua (arrays e My);
mexer no array recebido nao contamina a proxima chamada; `mdist` igual frio e
quente. A injecao do `test_fsm_injecao_sem_minimos_vira_erro` troca
`_minimos_locais`, que atua depois da curva, e segue valendo.
(d) 3 checks do G15 com o cache x sem ele (`__wrapped__`, mesma arvore - o
HEAD extraido fora do repo nao roda estes checks, caminhos ancorados no
repo): sha256 identico nos 3; 62,9 s -> 29,3 s.

**Depois (mesmos lotes, mesma contagem).** 00: 42:43 -> 11:07 (522 = 522);
04: 21:46 -> 7:25 (401 = 401).

**Suite inteira depois (lista nominal, lida inteira - convencao 10): 3802
passed, 0 falhas, 291 arquivos, 2832 s (47 min).** Lotes de 30 arquivos:
586 + 351 + 328 + 389 + 334 + 436 + 512 + 325 + 282 + 259; 3802 = os 3795
do D157 + os 7 testes novos de equivalencia (4 do pilar, 3 do FSM). A suite
do D157, na mesma maquina, somou ~8269 s (2 h 18 min) por lotes: -66 %. O
que sobra de maior e o G102 (a rodada real das 3 tipologias com freecad.exe,
~19 min no lote 6) e os builds do FreeCAD, que o Python nao acelera.

**Licao de metodo.** Paralelizar ou compartilhar fixture antes de perfilar
teria atacado o custo errado: a suite era lenta por um laco puro do solver,
chamado dezenas de vezes por teste. Numa maquina de 8 GB, `-n auto` so
trocaria lentidao por processo morto. Otimizacao de conta so entra com prova
de numero identico (hash do resultado inteiro + `==` contra a implementacao
anterior + vermelho de uma reordenacao).

## D159/G133 - a viga protendida num concreto que o projeto nao declarou (2026-09-13) - FECHADO

**Medido (remedicao na funcao real, antes de mudar).** Galpao de concreto
de vao 15 m em C30: `tipo_viga = "protendida"`, no ato `lim_comp = -28000
kN/m²` (= 0,70 × 40 MPa: fck e fckj = 40 MPa vindos de `max(fck, 40e3)` em
`galpao_concreto.py:223` e `fckj = cfg.get("fckj", fck)` em
`viga_protendida.py:154`); o `relatorio_pt` dizia "C30" e "VIGA DE
COBERTURA (protendida): secao 20x60 cm ; 4 cordoalhas Ø12,7 -> ATENDE", e o
`executivo_concreto.memorial` nao mencionava C40. O "[A CONFIRMAR: fckj na
idade da protensao, ...]" da viga chegava ao memorial pelo executivo (que
compoe o relatorio da viga), mas NAO as folhas (`desenho_concreto`,
`techdraw_concreto`) nem ao relatorio do galpao.

**Entregue (fonte unica `protensao_fck_g133.py`, producao).** Chaves
`fck_protendida` / `fckj_protensao` (kN/m2, atalho MPa; invalido LEVANTA);
`resolver_entrada` (ausente = fck do projeto / fckj = fck usado, com a
origem dita - nunca C40 de fabrica, nunca idade inventada);
`protensao_do_turnkey` / `protensao_da_entrega` (o que a conta USOU vence;
declarado x usado divergentes LEVANTA, molde G131);
`linha_protensao` + `contem_declaracao_protensao` / `confere_pecas` (peca
sem declaracao reprova, por parte); `defaults_de_protensao` /
`confere_defaults` (por AST: `max(fck, <piso>)`, `get("fck_protendida"/
"fckj_protensao", <numero>)`, `get("fckj", <nao-fck>)` - o mecanismo da
ausencia dita, `cfg.get("fckj", fck)`, nao acusa); `confere_uso_protensao`
(8 leitores: a fonte + viga_protendida, galpao_concreto, desenho_concreto,
techdraw_concreto, pacote_legal, galpao_adapter, entregaveis_projeto; o
executivo compoe os relatorios e nao importa - dito na fonte, molde G126).
Terceiro valor declarado: "sem viga protendida" (viga de concreto armado,
casa, predio). Fiacao: a origem viaja na cfg ate o resultado da viga; o
galpao grava `res["protensao"]`; declaram o relatorio do galpao, o da viga,
o memorial, as 2 SVG (bloco no rodape, +56/+48 px), as notas do TechDraw
(do resultado) e o pacote (`## Protensao da viga (G133)`, do calculado);
o adapter leva o topo ao payload e levanta na divergencia. O
ProjetoSpec/wizard do galpao METALICO nao e entrada (sem viga protendida
la - nao repetir o G134, dito na fonte).

**Divergencia achada e corrigida no caminho (a classe do G131, quarta
vez).** A primeira fiacao deixava o relatorio da viga dizer "fck declarado
no projeto" enquanto o do galpao dizia "fck nao declarado" na mesma
entrega: o galpao passava `fckj` sempre explicito e a viga marcava origem
pela presenca da chave. Agora a origem viaja na cfg (`fck_origem`,
`fckj_origem`) e as duas pecas declaram igual (conferido `==` no teste).

**Casos do repo, um a um, na funcao REAL (antes = C40 declarado =
comportamento antigo; depois = piso C30).**

| caso | antes (C40) | depois (C30 piso) | veredito |
|---|---|---|---|
| A. galpao 15 m C30 (o do goal) | 20x60, 4Ø12,7; ato -28000/+4,21; Mrd 293,3 (u 0,90); Vc 183; Asw 2,81; perdas 18 % | 20x60, 4Ø12,7; ato -21000/+3,48; Mrd 280,9 (u 0,93); Vc 150; Asw 2,32; perdas 20 % | ATENDE -> ATENDE |
| B. galpao 20 m C30 (fixture do turnkey) | 20x60, 8 cord; Mrd 512,2 | 25x70, 8 cord; Mrd 622,4 | ATENDE -> ATENDE (troca de secao) |
| C. viga isolada 16 m C40 (selftest) | Mrd bit a bit igual com e sem `fckj` | - | ATENDE (nao muda) |
| D. projects/*/project-spec.json | nenhum declara as chaves (piso declarado em todos) | - | - |
| E. galpao 10 m C30 | viga de concreto armado, sem protendida | terceiro valor declarado | ATENDE |

**Aceite.** Vermelho por injecao em `tmp_path` (`max(fck, ...)` e default
numerico reinjetados acusam; spec C30 sem declaracao sai calculado em C30
com `lim_comp -21000`; peca antiga sem a linha reprova); convencao 11
(spec direto, payload `turnkey.concreto`, topo via adapter, os tres na
conta; topo x payload divergentes levantam; rodada real com as chaves no
topo sai C40 na conta, nas 2 SVG e no pacote); sem a chave, o caminho
declarado reproduz o numero antigo bit a bit (caso A antes: -28000 e Mrd
293,3 iguais ao HEAD); invalido levanta em toda porta.

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
`varredura_faixa_validade` (+1 entrada da fonte, sem faixa propria);
`test_folhas_g77` (a referencia historica de 380 px vale para secao+cota,
sem os blocos G126/G133; helper novo em ISENTAS);
`test_guardas_d86_g69` (+itens 39-41 e TRIADAS).

**Lista nominal do lote, lida inteira (convencao 10): tudo verde.**
faixa `confere_cobertura`, asserts `confere`, orfas `confere`,
`test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`,
`test_edicao_nbr6118_g123`, `test_edicao_tipologias_g128`,
`test_cimento_nbr6118_g126`, `test_fctm_fonte_unica_g127`.

**Suite inteira (find tests -name 'test_*.py', 292 arquivos = 291 + o
guarda novo), lida lote a lote: 3812 passed, 0 falhas.** Lotes: branches
756 (569 s) + raiz 518 + 635 + 632 + 736 + 526 + trunk 1 + G102 isolado 8
(1082 s); o G21 correu 2x (ordenacao case-sensitive x insensivel dos
lotes - duplicata inofensiva, cobertura conferida por lista). Nao virei
chave de projeto nenhum do repo (D: nenhum declara as chaves).

## D160/G135 - a declaracao da edicao escrita a mao vira fonte unica (2026-09-13) - FECHADO

**Medido (remedicao antes de mudar, na funcao real do scanner).**
O texto do carimbo ("assumida 2014" / "Projeto calculado pela NBR 6118")
fora de `edicao_nbr6118_g123` em **23 linhas de 6 arquivos**
(executivo_concreto 184/185/187/235/236/238, caderno_encargos
245/246/248/295/297, pacote_legal 322/323/325/546/548, techdraw_concreto
360/361/363, rodar_galpao 1575/1576, relatorio_calculo 521 - o backlog
contou 22 tratando cada fallback em duas linhas como uma copia; o censo
por regex conta 23 com a segunda linha do fallback do pacote).
Quase todas em fallback de `except` que dentro do pacote nunca dispara
(a classe do D157, quinta vez - o G131 removeu as mesmas copias da linha
de cimento). `"6118:2014"` a mao, fora de comentario: **49 linhas em 23
arquivos** (o backlog contou 46 em 22 na auditoria; a diferenca sao as 3
da propria fonte + o `_FONTE_6118` e o assert do selftest do caderno,
remedidos aqui).

**Entregue (fonte unica `edicao_nbr6118_g123.py`, producao).**
`RE_CARIMBO_COPIA` + `copias_carimbo_fora_da_fonte` /
`fonte_tem_carimbo` / `confere_copias` (so a fonte contem o texto do
carimbo, molde `fctm_nbr6118_g127.confere_copias`, baseline nos dois
sentidos) + `RE_ROTULO_2014` + `rotulos_6118_2014_fora_da_fonte` /
`confere_rotulos` (todo "6118:2014" fora daqui e citacao isenta em
`CITACOES_ISENTAS`, com motivo; baseline nos dois sentidos:
`extras` = rotulo novo sem triagem, `faltando` = isencao sem rotulo).
Fiacao: as 23 linhas de carimbo viram chamada a fonte (fallbacks
literais removidos, como o G131 fez para o cimento - import direto, sem
ramo isolado); os rotulos de calculo (`_FONTE_6118`, sufixo do
desenho_concreto, rotulo do techdraw/caderno, assert do selftest do
caderno via `DECLARACAO_2014`) idem; os **12 cabecalhos de memorial**
(fundacao_sapata 662/993, laje 828, pilar 793, pilar_continuo 243,
viga_baldrame 217, viga_baldrame_edificio 305, viga_concreto 191,
viga_continua 455, viga_protendida 245, escada 273) passam a chamar
`rotulo_edicao()` da fonte. `USO_ESPERADO`: 19 + os 10 memoriais = 29.

**Triagem dos rotulos (carimbo vira fonte; citacao isenta com motivo).**
Carimbo de calculo (14 sitios, todos fiados): as 23 linhas do carimbo +
`_FONTE_6118` + sufixo/rotulo fallbacks + 12 cabecalhos. Citacao
historica isenta (14 arquivos em `CITACOES_ISENTAS`): docstrings de
metodo (fissuracao 17.3.3.2, perdas 9.6.3, puncao 19.5, laje, pilar,
pilar_continuo 15.6/15.8, viga_baldrame, viga_concreto, viga_continua
38/222/238 - inclui o texto literal de 14.6.6.1-c citado, viga_protendida,
escada), docstrings Fonte de compatibilizacao (13.2.5/13.2.5.2/21.3.3),
tabela METODOS do relatorio_calculo (fonte do metodo por modulo, nao
carimbo da peca; migrar item a item e decisao do usuario, G132 Nao
fazer) e subtitulo default do desenho_pavimento (renderizacao do
parametro ausente, byte-identico; com a chave, `_subtitulo_pilares`
usa a fonte).

**Decisao escrita para o G132.** Os 12 cabecalhos chamam a fonte SEM a
chave (sempre 2014, byte-identico) - e o correto para estas pecas
tambem COM a chave, porque nenhuma conta delas troca (so 12.3.3 no
icamento e 13.2.5.1 no furo trocam, `MODULOS_COM_TROCA` intacto). Com a
chave em 2023+Em1, o carimbo do projeto diz 2023 e estes cabecalhos
dizem 2014 na mesma entrega: a contradicao e real e e o objeto do G132
(compor o carimbo do projeto por peca a partir da conta), nao deste
goal. Nao virei chave de projeto nenhum do repo (nenhum project-spec
declara `norma_6118_edicao`).

**Aceite.** Vermelho por injecao em `tmp_path` (carimbo colado fora da
fonte, rotulo novo sem triagem, isencao sem rotulo, leitura nova sem
triagem e nome morto - todos acusam; comentario nao conta; fonte sem o
carimbo acusa); sem a chave, rodada real das 3 tipologias declara 2014
em toda folha PE-CO / SVG de calculo + pacote + caderno, sem nenhum
"2023" (test_06: casa 4 PE-CO + predio 4 PE-CO + galpao 2 SVG sem 2D,
28 s); cada linha migrada rende o literal antigo byte a byte
(`rotulo/carimbo/sufixo(None)` + os 11 formatos de cabecalho contra os
literais escritos a mao no teste + memorial real do galpao e tabela e
relatorio B reais da sapata com os cabecalhos em 2014).

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
`test_edicao_nbr6118_g123` test_02 e `test_edicao_tipologias_g128`
test_06 (19 -> 29 usos, os 10 memoriais nomeados); `test_guardas_d86_g69`
(item 28: 19 -> 29 usos; itens 42-43: `confere_copias` e
`confere_rotulos` entram em TRIADAS_G69 com a triagem escrita).

**Lista nominal do lote, lida inteira (convencao 10): tudo verde.**
faixa `confere_cobertura`, asserts `confere`, orfas `confere`,
`test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`,
`test_edicao_nbr6118_g123` (6), `test_edicao_tipologias_g128` (9),
`test_cimento_nbr6118_g126`, `test_fctm_fonte_unica_g127`,
`test_edicao_carimbo_fonte_unica_g135` (6, novo).

**Suite inteira (find tests -name 'test_*.py', 293 arquivos = 292 + o
guarda novo), lida lote a lote: 3815 passed, 0 falhas.** Lotes:
branches 756 (568 s) + raiz 321 + 340 + 371 + 453 + 307 + 492 + 326 +
327 + resto 9 arquivos + trunk 1 (114 juntos, 34 s) + G102 isolado 8
(1062 s). Cobertura conferida por lista e por `--collect-only` da
arvore (3815 coletados = 3815 executados, sem sobreposicao entre
lotes: 42 + 249 + 1 + 1 = 293 arquivos); os 6 a mais sobre a suite do
D159 sao o guarda novo G135 (o D159, com outro fatiamento, somou 3812
com o G21 correndo 2x).

## D161/G132 - a edicao que se declara inteira trocando dois pontos (2026-09-13) - FECHADO

**Medido (remedicao nas 3 tipologias reais, spec persistido,
`norma_6118_edicao: "2023+Em1"` injetada em memoria, nunca no repo).**
Com a chave, a entrega dizia 2023+Em1 onde nenhuma conta troca - e o
memorial da sapata, em 2014, estava certo:
- casa: 4 folhas PE-CO + pacote + caderno em 2023; 61 pendencias (todas
  `conflito`, sem conta que troca) em 2023; sapata no adapter-result
  em 2014 ("SAPATA - PARTE B (CONCRETO ARMADO) - NBR 6118:2014").
- predio: 4 folhas PE-CO + pacote + caderno em 2023; 126
  `furo_previsto` em 2023 (81 de laje 13.2.5.2, SEM troca, clausulas
  em 2014; 45 de viga 13.2.5.1, COM troca, clausulas em 2023);
  sapata no adapter-result em 2014, sem nenhum "2023".
- galpao (turnkey, sem 2D): 2 SVG de calculo + pacote + caderno em
  2023; 688 `conflito` + 282 `montagem` em 2023.
So 2 pontos leem a chave (`MODULOS_COM_TROCA` intacto:
`premoldado_nbr9062` 12.3.3 no icamento, `compatibilizacao` 13.2.5.1
no furo em viga). O portao do G128 comparava a folha com a chave de
entrada, nao com a conta - por isso passava com a contradicao dentro.

**Entregue (tudo da fonte unica `edicao_nbr6118_g123.py`, producao).**
`edicao_da_peca` (a edicao que a SUA conta usou: sem troca, 2014 com
qualquer chave; invalida levanta), `carimbo_composicao` (o carimbo do
projeto: 2014 + os itens de `MODULOS_COM_TROCA` listados daqui em
2023+Em1; sem a chave ou 2014, o carimbo de hoje byte a byte),
`confronto_peca_conta` (o portao parte da conta: 2023 em peca sem
troca reprova nomeando os dois lados) e `contem_composicao` (o portao
do projeto). Fiacao: folhas de desenho resolvem por peca nos pontos
de carimbo (`desenho_pavimento._sufixo_edicao`/`_subtitulo_pilares`,
`desenho_fundacao_edificio._sufixo_edicao`,
`desenho_concreto._carimbo_edicao` - os wrappers da casa passam por
eles, sem mudanca); `gerar_pendencias` carimba `edicao_6118` por
pendencia (so furo transversal em viga segue a chave; laje, vertical,
conflito e montagem declaram 2014); pacote, caderno, memorial e
relatorio do galpao e prancha techdraw dizem a composicao; quadro de
aco declara 2014 (peca sem troca). Os 10 memoriais seguem sem a chave
(2014) - e o correto tambem com ela, sem mudanca de codigo. Clausulas
do caderno e linha de normas da techdraw citam a edicao declarada
(referencia de execucao, nao conta de peca - dito aqui para a
diferenca nao parecer esquecimento).

**Decisao escrita para o G134/G136.** `rodar_galpao.py` (galpao
METALICO, NBR 8800) e `relatorio_calculo.gerar_pdf` ("GALPAO EM ACO")
seguem com o carimbo de projeto antigo: nao ha calculo de concreto
naquele caminho e o aceite do G132 e a rodada das tres tipologias
do turnkey - trocar o carimbo la seria mudar peca fora do medido. O
`edicao_6118` do pacote segue sendo a edicao DECLARADA no projeto
(metadado); a composicao mora no `carimbo_edicao_6118` e no markdown.

**Nao feito (do goal).** Nenhum item migrado para a 2023 (8.2.5 e o
resto seguem 2014 declarado; `MODULOS_COM_TROCA` com 2 pontos);
nenhum project-spec do repo declara a chave (test_08 segue verde).

**Aceite.** Vermelho por injecao em `tmp_path` (folha 2023 em peca
sem troca acusa nomeando; composicao sem os itens acusa; invalida
levanta nas tres portas novas; conflito com a chave declara 2014 -
G128 test_04); rodada real das 3
tipologias com a chave sem contradicao (folhas 2014 por conta,
memorial 2014, pacote/caderno com a composicao, pendencias pela
conta x clausulas - G128 test_01/02/03 + G132 test_04); sem a chave,
byte-identico (composicao == carimbo de hoje, peca == 2014, literais
de hoje contra os escritos a mao no teste + casa real sem nenhum
"2023" - G132 test_05, G135 test_06 intacto).

**Baselines com motivo escrito (nao e verde por edicao).**
`USO_ESPERADO` segue 29 e `MODULOS_COM_TROCA` com 2 pontos (nenhum
modulo novo importa a fonte: tudo veio de quem ja lia);
`test_edicao_tipologias_g128` test_05/06/09 reescritos para o portao
da conta (subtitulo/sufixo com a chave rendem o literal de hoje;
pacote com a mesma edicao confere por composicao);
`CITACOES_ISENTAS` intacta (nenhum literal novo fora da fonte).

**Lista nominal do lote, lida inteira (convencao 10): tudo verde.**
faixa `confere_cobertura`, asserts `confere`, orfas `confere`,
`test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`,
`test_edicao_nbr6118_g123`, `test_edicao_tipologias_g128` (9),
`test_cimento_nbr6118_g126`, `test_fctm_fonte_unica_g127`,
`test_edicao_carimbo_fonte_unica_g135` (6),
`test_edicao_peca_conta_g132` (5, novo).

**Suite inteira (`pytest tests`, com `tests/branches` e `tests/trunk`,
convencao 10), lida de uma vez: 3820 passed, 0 falhas (46 min).**
Os 5 a mais sobre os 3815 do D160 sao o guarda novo G132.

## D162/G134 - a pergunta do cimento que nenhuma conta le: sai do fluxo metalico (2026-09-13) - FECHADO

**Medido (remedicao por AST antes de mudar, nas funcoes reais).**
`to_rodar_params` (projeto_spec.py) escrevia **30 chaves** de topo em `p`
(coleta por AST: `p["chave"]`, `p.setdefault/get/pop("chave", ...)`):
aguas, baldrame, base_fixed, calha, cargas, chuva_I_mm_h, cimento,
creditar_cortante_mesa_inclinada, divisa, escada, estaca, fogo, fu,
fundacao, fy, geometria, mf_sec, neve, norma_6118_edicao, parede,
plataforma, ponte, secundarios, tapered, telha, terreno, tipo_ligacao,
tipo_portico, trelica, vento. Cruzamento com os acessos a `params` no
`rodar_galpao.py` (por AST: `params["chave"]`, `params.get/setdefault/
pop("chave")`, `"chave" in params` - string em mensagem NAO e leitura,
o rigor do G126): **28 lidas direto, 1 via funcao declarada
(`norma_6118_edicao` por `edicao_de_spec`, importada com alias e chamada
em rodar_galpao.py:1554-1561 - NAO e morta) e 1 com zero leitores
(`cimento`: `grep cimento rodar_galpao.py` vazio). O `rodar_galpao` e o
galpao METALICO (NBR 8800), sem icamento de pre-moldado; o icamento so e
calculado pelo `galpao_concreto` dentro do turnkey, cuja entrada e o
project-spec (topo ou `turnkey.concreto`, ligados no G131) - nao o
ProjetoSpec. A pergunta do wizard ("Tipo de cimento do concreto p/ o
fckj do icamento", wizard.py:197) viajava por ProjetoSpec.cimento
(projeto_spec.py:159) e `p["cimento"]` (projeto_spec.py:941) ate um
orquestrador que nunca a lia. A varredura de campos mortos do wizard
(S39) conta `p[chave] = ...` como campo fiado; por isso nao acusou: ela
confere a ESCRITA, nunca a LEITURA. Classe da convencao 8 ("constante
que a producao nao le e comentario"), agora numa pergunta ao usuario.

**Entregue (fonte unica `chaves_to_rodar_g134.py`, producao).**
`CHAVES_ESPERADAS` (as 29 que ficam), `CHAVE_REMOVIDA` + motivo escrito
(`MOTIVO_REMOCAO_CIMENTO`), `LEITURAS_DECLARADAS` (`norma_6118_edicao`
via `edicao_nbr6118_g123.edicao_de_spec`: declarar sem importar+chamar
= vermelho), `chaves_escritas_por_to_rodar` / `leituras_diretas_em_rodar`
/ `usa_leitura_declarada` (as tres por AST, com `raiz` p/ injecao em
`tmp_path`, molde G51-rev), `chaves_sem_leitor` e `confere_censo` (o
portao: zero sem-leitor E escritas == esperadas; `sem_leitor`/`extras`/
`faltando` sao os acumuladores; nome `confere_censo` no molde G129 para
o censo de guardas do D86 enxergar). Fiacao da remocao, cada ponta com o
motivo escrito: o wizard nao pergunta mais (resposta legada explicita
em dict antigo BLOQUEIA com o caminho certo; ausente/None/"" segue OK);
`PS.novo()` nasce sem a chave (legado ausente/None/"" segue OK, specs
antigos continuam validos; valor explicito BLOQUEIA, distinguindo
"valido mas fora do fluxo" de "desconhecido" - o import da fonte do
G126 fica, mesmo `LEITORES_ESPERADOS`); `to_rodar_params` sem o repasse
(legado que chegar ate ali levanta em vez de seguir morto). Escolha do
goal: A PERGUNTA SAI - "chegar a uma conta que a usa" exigiria inventar
um uso para o `s` da 12.3.3 no metalico (arbitrar dado de projeto,
proibido no lote). **Nao feito (do goal):** tirar o cimento do
project-spec do turnkey - la ele e lido (G131; `cimento_de_spec`,
`cimento_do_turnkey`, `galpao_concreto.rodar`, `galpao_adapter`
topo->payload, pacote do resultado). Nenhum numero do metalico muda: a
chave nunca chegava a conta, entao a remocao e byte-identica por
construcao (test_04 roda o `rodar` sem a chave ate o veredito global).

**As 30 triadas (escrita x leitura x veredito).** Leitura = primeiro
acesso a `params` em `rodar_galpao.py` (linha medida acima):

| chave | escrita em to_rodar_params | leitura em rodar_galpao | veredito |
|---|---|---|---|
| aguas | p[aguas] | :208 `params.get("aguas", 2)` | viva, direta |
| baldrame | p.setdefault(baldrame) | :811 `params["baldrame"]` | viva, direta |
| base_fixed | p[base_fixed] | :211 `params.get("base_fixed", True)` | viva, direta |
| calha | p[calha] | :905 `params.get("calha")` | viva, direta |
| cargas | p[cargas] | :176 `params["cargas"]["Q"]` | viva, direta |
| chuva_I_mm_h | p[chuva_I_mm_h] | :921 `params.get("chuva_I_mm_h", 150.0)` | viva, direta |
| cimento | p[cimento] (G126) | nenhuma (grep vazio) | MORTA - removida (G134) |
| creditar_cortante_mesa_inclinada | p[creditar...] | :1026 `params.get("creditar_cortante_mesa_inclinada", False)` | viva, direta |
| divisa | p[divisa] | :960 `params.get("divisa")` | viva, direta |
| escada | p[escada] | :1492 `params.get("escada")` | viva, direta |
| estaca | p[estaca] | :840 `params.get("estaca")` | viva, direta |
| fogo | p[fogo] | :1460 `params.get("fogo")` | viva, direta |
| fu | p[fu] | :275 `params.get("fu", 400e3)` | viva, direta |
| fundacao | p.setdefault(fundacao) | :786 `params["fundacao"]` | viva, direta |
| fy | p[fy] | :275 `params["fy"]` | viva, direta |
| geometria | p[geometria] | :169 `params["geometria"]` | viva, direta |
| mf_sec | p[mf_sec] | :468 `params.get("mf_sec")` | viva, direta |
| neve | p[neve] | :178 `params.get("neve")` | viva, direta |
| norma_6118_edicao | p[norma_6118_edicao] | `edicao_de_spec(params)` (:1554-1561, import com alias + call) | viva, declarada |
| parede | p[parede] | :205 `params.get("parede")` | viva, direta |
| plataforma | p[plataforma] | :1503 `params.get("plataforma")` | viva, direta |
| ponte | p[ponte] | :242 `params.get("ponte")` | viva, direta |
| secundarios | p.setdefault(secundarios) | :562 `params["secundarios"]` | viva, direta |
| tapered | p[tapered] | :215 `params.get("tapered")` | viva, direta |
| telha | p.setdefault(telha) | :362 `params.get("telha")` | viva, direta |
| terreno | p[terreno] | :938 `params["terreno"]` (comentario-guia) / gate | viva, direta |
| tipo_ligacao | p[tipo_ligacao] | :236 `params.get("tipo_ligacao", "soldada")` | viva, direta |
| tipo_portico | p[tipo_portico] | :734 `params.get("tipo_portico")` | viva, direta |
| trelica | p[trelica] | :1288 `params.get("trelica")` | viva, direta |
| vento | p[vento] | :207/229 `params.get("vento")` | viva, direta |

Fora do baseline estatico, triada aqui: a familia condicional `mont_*`
(`p[_k]` em laco, so com `montagem_params` no spec; lida pelo gate de
montagem, `mont_` presente no rodar_galpao) e as chaves aninhadas
(`telha.cfg`, `secundarios.longarina`, `fundacao.tipo`: contrato de cada
gate, nao do mapper) - ditas na fonte para a ausencia nao parecer
esquecimento.

**Aceite.** Vermelho por injecao em `tmp_path` (chave nova sem leitor
reprova em `extras` E `sem_leitor`; `cimento` reinjetado reprova como
sem_leitor; `norma_6118_edicao` com literal solto mas sem o call
reprova - string em mensagem nao e leitura; nome morto reprova em
`faltando`; G134 test_03); convencao 11 (wizard, spec-direto e mapper:
os tres bloqueiam o cimento explicito com o motivo, e o legado
ausente/None/"" segue OK - G134 test_04); turnkey intacto (unidade +
conta real do `galpao_concreto` com e sem cimento, fckj do piso 13,7 -
G134 test_05; o turnkey pesado segue no G126 test_06, verde);
anti-tautologia (os 29 literais a mao contra o AST vivo - G134 test_06);
censo real zerado (29 escritas, zero sem-leitor - G134 test_01).

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
`varredura_faixa_validade` (+1 entrada da fonte, sem faixa propria);
`test_guardas_d86_g69` (item 44 + triada `("chaves_to_rodar_g134",
"confere_censo")` - o censo de guardas so enxerga `def confere_*`);
`test_cimento_nbr6118_g126` test_05 (a entrada metalica agora rejeita:
novo sem a chave, explicito bloqueia com o motivo, wizard nao pergunta
- o turnkey segue nos test_06/05); `cimento_nbr6118_g126` (o "nao
cobre" agora diz REMOVIDO com o apontador G134).

**Lista nominal do lote, lida inteira (convencao 10): tudo verde.**
faixa `confere_cobertura`, asserts `confere`, orfas `confere`,
`test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`,
`test_edicao_nbr6118_g123`, `test_edicao_tipologias_g128` (9),
`test_cimento_nbr6118_g126`, `test_fctm_fonte_unica_g127`,
`test_edicao_carimbo_fonte_unica_g135` (6),
`test_edicao_peca_conta_g132` (5), `test_chaves_to_rodar_g134` (6, novo).

**Suite inteira (`pytest tests`, com `tests/branches` e `tests/trunk`,
convencao 10), lida de uma vez: 3826 passed, 0 falhas (45 min).**
Os 6 a mais sobre os 3820 do D161 sao o guarda novo G134.

## D163/G136 - a fctd em sete copias vira fonte unica, com o γc da Tab. 12.1 (2026-09-13) - FECHADO

**Medido (remedicao por AST + regex antes de mudar, nas funcoes reais;
Tab. 12.1 lida na pagina renderizada da F016, convencao 3).**
A conta `0,7 * fctm / gamma_c` estava escrita em **7 sitios de
producao**: os 6 que o backlog contou com o `1.4` literal
(estaca_profunda:387, fundacao_sapata:683, laje_concreto:440,
pilar_concreto:440, viga_baldrame:46, viga_protendida:127) mais
base_chumbador:99 via a constante propria `GC` (= 1,40, mesmo numero).
Todas com o mesmo numero nos 5 fcks do aceite
(C20/C50/C55/C60/C90). A Tab. 12.1 (NBR 6118:2014 p. 71, 12.4.1, ELU),
lida na imagem da F016: combinacoes normais gamma_c = 1,4 /
especiais ou de construcao 1,2 / excepcionais 1,2 - o que as 7
gravavam e o da combinacao normal. Nenhum caso do repo chama estes
modulos em combinacao que nao a normal (remedido nos chamadores:
`ancoragem_tirante`, `comprimento_ancoragem`, `cortante_laje`,
`verifica_cortante_pilar`, `_verifica_cortante`,
`verifica_cortante_protendida` e `ancoragem_chumbador` so aparecem em
caminho ELU normal; nenhum recebe gamma_c). Medido ainda, para fixar
a ordem da fonte: a primitiva kN/m2 tem de derivar da MPa
(`fctd_MPa(fck/1000) * 1000`), nunca `fctk_inf(fck) / gamma_c` - a
ordem trocada difere em 1 ulp em C55
(2070.209273833628 contra ...282).

**Entregue (fonte unica `fctd_nbr6118_g136.py`, producao).**
`fctd_MPa` (MPa -> MPa, `(0,7 * fctm) / gamma_c`, a ordem das copias)
+ `fctd` (kN/m2 -> kN/m2, deriva da MPa) + `GAMMA_C_NORMAL` (1,4) /
`GAMMA_C_ESPECIAL_CONSTRUCAO` (1,2) / `GAMMA_C_EXCEPCIONAL` (1,2)
declarados da pagina + `RE_FCTD_COPIA` (o literal `0.7 * nome / gamma`
e o desvio `fctk_inf(...) / gamma` com literal) +
`copias_fctd_fora_da_fonte` / `fonte_tem_a_conta` / `confere_copias`
(so a fonte contem a conta, baseline nos dois sentidos) +
`arquivos_que_importam_fctd` (por AST) / `confere_uso_fctd`
(`LEITORES_ESPERADOS`: a fonte + os 7). Fiacao, cada modulo na
primitiva da ordem que ja usava (numero bit a bit por construcao):
base e laje `fctd_MPa(fck_MPa) * 1000.0`; estaca, fundacao, pilar e
baldrame `fctd_MPa(fck_MPa)`; protendida `fctd(fck)`. As linhas de
fctm que alimentavam a conta ficam (cada modulo segue importando a
fonte do G127: fundacao e laje so a usavam ali, e o baseline do G127
nao se toca sem motivo).

**Duas decisoes escritas.** (1) O backlog contou 6 com literal; a 7a
(base via `GC`) migrou junto: deixar uma copia de producao fora da
fonte para a lente nao ver seria o desencontro do D157 com outro
rotulo; o numero e o mesmo (`GC` = 1,40 = normal) e o γc de caso
nenhum mudou. (2) Os corpos de `def _selftest` estao fora da lente,
declarado na fonte: os asserts ali (ex. estaca_profunda:672)
RECOMPUTAM a formula como prova independente (anti-tautologia, G119);
a prova da migracao mora no guarda com literais escritos a mao. Sem
isso a lente mandaria reescrever a prova independente chamando a
fonte - tautologia.

**Aceite.** `==` modulo a modulo nos 5 fcks (G136 test_02, 12 sondas:
fctd/fbd/lb da base, fbd/lb de estaca e sapata, tau/Vrd1 da laje, Vc
de pilar e baldrame, Vc0 da protendida); hash sha256 das sondas igual
ao do antes (test_05, molde D158); vermelho de reordenacao (test_06,
molde D158 test_04: `*1000` antes do `/1,4` difere em C55, e o Vc com
os fatores reordenados difere em C55/C60/C90 - o `==` pega ulp, nao
so erro grosso); vermelho por injecao em `tmp_path` (test_03: literal,
via `GC`, desvio por fctk,inf, fonte apagada; comentario nao conta;
`_selftest` fora por declaracao; test_04: extra e nome morto);
gamma_c parametro com a normal por omissao e AST travando que nenhum
dos 7 passa gamma_c (test_01/test_07). Prova de terceiro: o
test_02 do G127 (literais pre-migracao de base/pilar/laje/baldrame)
segue verde sem retoque.

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
`fctm_nbr6118_g127.LEITORES_ESPERADOS` 12 -> 13 usos (a fonte do G136
deriva a fctd da fctk,inf daqui em vez de recomputar o 0,7; cabecalho
da fonte + item 34 do G69); `test_guardas_d86_g69` (item 45 + triadas
`("fctd_nbr6118_g136", "confere_copias")` e
`("fctd_nbr6118_g136", "confere_uso_fctd")` - o censo so enxerga
`def confere_*`); `varredura_faixa_validade` (+1 entrada da fonte em
SEM_FAIXA_DECLARADA, sem faixa propria: a faixa do fck vive no G127).

**Nao feito (do goal).** Mudar o γc de caso nenhum (todos os 7 chamam
com a omissao = normal 1,4); nenhum numero e nenhum veredito muda
(antes == depois bit a bit + hash).

**Lista nominal do lote, lida inteira (convencao 10): tudo verde.**
faixa `confere_cobertura`, asserts `confere`, orfas `confere`,
`test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`,
`test_edicao_nbr6118_g123`, `test_edicao_tipologias_g128` (9),
`test_cimento_nbr6118_g126`, `test_fctm_fonte_unica_g127`,
`test_edicao_carimbo_fonte_unica_g135` (6),
`test_edicao_peca_conta_g132` (5), `test_chaves_to_rodar_g134` (6),
`test_fctd_fonte_unica_g136` (7, novo).

**Suite inteira (`pytest framework/galpao_fw/tests`, com
`tests/branches` e `tests/trunk`, convencao 10), lida de uma vez:
3833 passed, 0 falhas (48 min 33 s).** Os 7 a mais sobre os 3826 do
D162 sao o guarda novo G136 (296 arquivos de teste; sem skips).

## D164 - a suite em paralelo: o que satura nao e o Python, e o FreeCAD vai numa fila so (2026-09-13)

**Pedido.** O lote G132-G136 fechou, mas a suite custou ~10 h ao longo dos 5
goals (48 min serial por goal, mais as corridas nominais). Melhorar sem
degradar a verificacao.

**Medido antes de mudar (convencao D158: perfilar primeiro).**
1. *O portao mais caro (G102, 999 s = 57 % da corrida).* cProfile da rodada
   real do galpao (`galpao-tp-g95`, mesmas opcoes): 997 s, dos quais 589 s em
   `time.sleep` (polling do `_status.json`) e 348 s em `subprocess.run` -
   937 s ESPERANDO o freecad.exe; Python proprio ~60 s. Linha do tempo do
   disco: modelo 3D do aco ~3,5 min, executivo do aco 19:39 -> 19:49 e
   **nenhuma prancha de aco emitida**: `timeout 459 s aguardando pranchas`.
   O prazo global do caderno (1200 s) reparte 459 s ao aco por peso, e o
   executivo medido e ~578 s + PE05 ~209 s (`caderno_turnkey._T_MEDIDO_SEG`)
   - estoura POR CONSTRUCAO em toda corrida; o portao passa porque a falta
   sai declarada. Achado, nao corrigido: e decisao de produto (prazo x o
   que o portao prova), levada ao usuario.
2. *Por que `-n N` nao ajudava.* Cada processo de teste pesado usa ~3,5-4,3
   nucleos (17-19 threads): o pool do OpenBLAS do scipy (0.3.30, padrao 8
   threads; o do numpy 0.3.23 tem MAX_THREADS=2). Corridas inteiras com o
   padrao: `-n 3` em 28 % aos 21 min e `-n 2` em 39 % aos 31 min (serial:
   48 min inteira) - MAIS lentas que a serial; mortas e registradas.
3. *O que preserva o numero e o que nao preserva* (hash do resultado inteiro
   do predio `run_edificio` e dos 3 checks G15 do galpao):
   - padrao x padrao: identico (deterministico);
   - afinidade 2 nucleos: identico, mas predio 4 -> 50 s (8 threads presas);
   - `OPENBLAS_THREAD_TIMEOUT`/`GOTO_THREAD_TIMEOUT=4`: identico e sem efeito
     nenhum (a build Windows nao le);
   - `OPENBLAS_NUM_THREADS=1` ou `=2`: **difere no ultimo ulp** - predio 148
     linhas do JSON (analise lateral: drift, gamma_z, H/u; ex.
     `H_sobre_u` 2402.782203727036 -> 2402.7822037269434, ~1e-13 relativo);
     galpao G15 identico. Com 1 thread cada worker usa 1,0 nucleo.

**Entregue.**
- `tools/suite_paralela.py`: `pytest -n 3 --dist loadgroup` com o
  interpretador 8.3 (D80), `--blas` (padrao do runner: 1, gravado no
  resumo), e tres portoes da CORRIDA alem do verde do pytest: (a) lista
  nominal `find tests -name 'test_*.py'` == arquivos coletados (convencao
  10); (b) censo do FreeCAD nos dois sentidos; (c) `git status` antes ==
  depois (D81: suite que muta o repo nao roda em paralelo). Memoria livre
  minima amostrada e gravada.
- `tests/censo_freecad.py` + hooks no `tests/conftest.py`: os arquivos que
  sobem freecad.exe/freecadcmd.exe (dois juntos = ~4 GB, maquina de 8 GB,
  e o portao de memoria do G102 soma todo freecad visivel) vao a um grupo
  xdist unico. O grupo e cobrado por medicao: sob xdist cada worker amostra
  a arvore de processos (Toolhelp32/ctypes, sem psutil) e anota o teste
  corrente no primeiro avistamento de um freecad descendente. Reprova:
  teste fora do grupo que subiu freecad (tambem no controlador de qualquer
  `pytest -n`), e arquivo do grupo que nao subiu em corrida inteira
  (isencao morta, no runner).
- `tests/test_suite_paralela_d164.py` (4): conferencia vermelha nos dois
  sentidos por injecao; arvore de processos so por descendencia (com ciclo);
  o amostrador enxerga um executavel de verdade (copia do ping com nome
  vigiado; outro nome nao entra) - medidor que nao dispara nao mede (G119);
  grupo com arquivo existente e motivo medido.

**O censo trabalhou nos dois sentidos antes de fechar.** 1a corrida: pegou
`branches/g8/test_g8_entregaveis_no_loop.py` subindo freecadcmd FORA do
grupo (o grep inicial nao via: o 3D vem de producao). Corrida inteira com o
grupo do grep (39 arquivos): 25 isencoes mortas - subprocesso Python,
FreeCAD simulado ou rota SVG. Grupo congelado nos 15 medidos, cada um com
processos e teste no motivo.

**Decisao escrita (e reversivel).** O runner roda com 1 thread de BLAS
porque e a unica configuracao medida em que o paralelo ganha. Isso NAO
passa pela prova bit a bit do D158: o ultimo ulp de contas do LAPACK muda
(o numero ja depende da contagem de nucleos da maquina, mas isso nao o
torna igual). O que sustenta: a suite inteira com 1 thread da o mesmo
verde (3837 passed, nenhum veredito muda) e `pytest tests` serial, sem o
runner, segue como referencia bit a bit. Rejeitado: afinidade (numero
igual, 12x mais lento), `-n` com o padrao (mais lento que a serial), e
mexer no prazo do caderno ou no portao do G102 sem o usuario.

**Suite inteira pelo runner (297 arquivos, lista nominal == coletados).**
Corrida 1 (grupo do grep, 39 arquivos): **3837 passed, 0 falhas, 29 min
07 s** (serial de referencia D163: 48 min 33 s), memoria livre minima
1056 MB; o runner reprovou pelas 25 isencoes mortas - o portao fazendo
seu trabalho, e o grupo foi congelado nos 15 medidos. Corrida 2 (grupo
medido): **3836 passed, 1 failed, 26 min 58 s**, memoria minima 890 MB,
censo sem violacao e sem isencao morta. As duas quebras, com causa:
(a) `git status` mudou - eu editei `wiki/03-phases.md` com a suite
rodando; o portao pegou o que devia; (b) **o G102 e sorteio de relogio
(classe D81), achado nao corrigido**: nesta corrida o executivo de aco
gravou `PE02_FUNDACOES.pdf` e `PE03_ELEVACOES.pdf` antes do corte, e os
dois nao tem codigo no mapa do galpao (o G112 ja os dava fora do recorte)
-> `extra_no_disco`. O executivo emite em sequencia (PE01 187,7 + PE02
58,8 + PE03 211,9 = 458,4 s medidos, D133) contra 459 s de prazo: quando
a maquina esta um pouco mais rapida, dois arquivos sem codigo chegam ao
disco; mais lenta, nada chega e o portao passa. Nao nasce do paralelo -
o prazo e a ordem sao os mesmos na serial - mas so apareceu agora. Pede
decisao: mapa/isencao das pranchas de aco emitidas, prazo do aco no
caderno, ou o portao rodar o galpao sem o executivo de aco, que hoje
nunca termina em rodada de teste.

## D165 - auditoria do lote G132-G136, e o G102 que deixa de apostar corrida com o executivo de aco (2026-09-13) - FECHADO

**Decisao do usuario (2026-09-13), sobre o D164.** Manter o runner com 1
thread de BLAS nos goals e a serial bit a bit na auditoria; separar o que o
G102 misturava; tratar o executivo de aco como defeito de produto (goal).

**Auditoria do lote por medicao (nao pelo verbete).**
- G136: as 12 sondas da fctd (`base_chumbador`, `estaca_profunda`,
  `fundacao_sapata`, `laje_concreto`, `pilar_concreto`, `viga_baldrame`,
  `viga_protendida`) em 8 fcks (C20-C90), rodadas no HEAD pre-G136
  extraido (`git archive`) e na arvore: **560 campos, 0 diferencas** (`==`).
- G133: `galpao_concreto.rodar` real, vao 15 m C30 sem chave: protendida
  com `lim_comp` -21000 e `protensao.fck_origem =
  fck_nao_declarado_usa_fck_projeto`, relatorio "fck 30 MPa ... sem piso de
  fabrica C40"; com `fck_protendida` 40: -28000, "fck declarado no
  projeto"; vao 20 m: 25x70, como o D159 diz.
- G135/G136/G134/G133: censos da arvore todos fechados
  (`edicao_nbr6118_g123.confere_copias/confere_rotulos/confere_uso_edicao`,
  `chaves_to_rodar_g134.confere_censo`, `fctd_nbr6118_g136.confere_copias/
  confere_uso_fctd`, `protensao_fck_g133.confere_defaults/
  confere_uso_protensao`); wizard sem a pergunta, `PS.novo()` sem a chave.
- G132: casa real com `norma_6118_edicao = 2023+Em1` em memoria: nenhum SVG
  com "2023"; "2023" so em `project-run.json` (eco da entrada, fontes e
  `caderno_encargos.normas_referenciadas`), `pacote-legal` e
  `caderno-encargos` (a composicao) - o que o D161 declara.
O lote se sustenta; nenhum defeito corrigido na auditoria.

**G102 sem o executivo de aco.** Nova opcao de politica
`ProjectLoopOptions.executivo_aco` (padrao True: producao identica) ->
`caderno_turnkey.montar_caderno(..., executivo_aco)` ->
`_dispatch_pranchas`: com False o aco roda calculo, memorial e 3D e o status
diz `nao_solicitado` (ok None, sem erro - ausencia, nao falha); o laco do
adaptador nomeia a causa em cada folha PE-ES pulada
(`MOTIVO_EXECUTIVO_ACO_FORA`, fonte unica no caderno). O G102 roda o galpao
com `executivo_aco=False`: o test_01 cobra a causa em cada folha de aco
pulada; o test_09 prova o repasse (monkeypatch do `rodar_tudo`), a causa nos
dois sentidos, o padrao de producao intacto e o portao sem voltar a esperar
o executivo. As 4 opcoes falsas de teste (G93/G101/G107/G114) passaram a
declarar `executivo_aco: True` explicito, em vez de um `getattr` com
default escondido no adaptador.

**O executivo completo, medido e com portao proprio.** `rodar_tudo` sobre
`turnkey.aco` do `galpao-tp-g95` com prazo folgado (3D 900 s, executivo
2400 s), freecad.exe sozinho: **1038,9 s**, `ok=True`, **15 PDFs** - e so
**3 com codigo** no indice (PE01_COBERTURA, PE04_PORTICO, PE07_DET_JOELHO).
As 12 outras (PE02, PE03, PE05, PE06, PE08-PE14, PE16) viram a baseline
`SEM_CODIGO_ACO` de `tests/test_executivo_aco_completo_d165.py` (nos dois
sentidos; test_01 prova o vermelho de cada lado). O test_02 roda o
executivo completo so com `GALPAO_AUDITORIA=1`, serial - fora disso sai
pulado com o motivo escrito. Defeito de produto medido e levado ao G137: em
producao (prazo 1200 s, 459 s para o aco) o caderno do galpao nunca tem
prancha de aco.

**O que falta para o objetivo (medido nas rodadas reais, vira o backlog
G137-G142).** Predio: 15 folhas, nenhuma pulada. Casa: PE-AR-01 e PE-AR-03
bloqueadas por dado (lote, niveis), PE-EL-03 sem emissor na casa (o do
predio existe), alvenaria nao calculada no spec. Galpao: 6 folhas prometidas
puladas - PE-ES-01/02/03 (executivo de aco), PE-CD-01 (o hook passa recorte e
o caderno so emite coordenacao com `disciplinas=None`), PE-CO-04 (sem
emissor), PE-IN-02 (emissor do predio existe, entrada com outra forma) - e o
mezanino calculado que evapora do indice (D121). Normas todas no acervo.

**G102 re-medido e re-congelado (corrida isolada com -s, maquina livre).**
`CUSTO_G102 casa=2.0s predio=6.3s galpao=536.3s total=544.6s`, 9 passed em
551,5 s; `MEM_G102 ... galpao=1616.8MB(proc=195.1,fc=1486.5,n=1)`. Antes:
galpao 1048,3 s e 1988,8 MB. O portao cai de ~18 min para ~9 min e deixa de
depender do relogio. `CUSTO_MEDIDO_SEG`/`CUSTO_MEDIDO_MEM_MB` re-congelados
com a data e a corrida escritas no teste.

**Lista nominal:** faixa `confere_cobertura`, asserts G97, orfas G124,
`test_alcancabilidade`, `test_guardas_d86_g69`, `test_indice_disco_g91`,
`test_galpao_indice_g93`, `test_suite_paralela_d164`, G102 test_02/05/09,
`test_executivo_aco_completo_d165` (test_01; test_02 pulado sem a variavel)
- 74 passed, 1 skipped; G114/G101/G93/G107 + `branches/project_loop` (as
opcoes falsas) - 262 passed.

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 298 arquivos
== coletados): 3839 passed, 1 skipped, 0 falhas, 22 min 04 s, `quebras`
vazio** (censo do FreeCAD fechado nos dois sentidos, `git status` igual,
memoria livre minima 594 MB). O skip e o portao de auditoria do aco, com o
motivo escrito. De 48 min 33 s (serial, D163) para 22 min 04 s.

**Portao de auditoria do aco rodado de verdade (depois do commit 6212192).**
`GALPAO_AUDITORIA=1 pytest -s tests/test_executivo_aco_completo_d165.py`:
**2 passed em 1187,2 s**, `CUSTO_D165 executivo_aco_completo=1186.4s`
(a medicao de referencia, fora do pytest, deu 1038,9 s). As 15 pranchas e as
12 sem codigo bateram com a baseline nos dois sentidos - o portao dispara e
fecha na rodada real, nao so no test_01 sintetico.

**Suite serial de referencia (auditoria do lote, `pytest tests` sem o
runner, BLAS no padrao - o numero bit a bit): 3839 passed, 1 skipped, 0
falhas, 35 min 13 s.** Mesmas contagens da corrida paralela com 1 thread de
BLAS (3839 passed, 1 skipped, 22 min 04 s): nenhum veredito depende do
ultimo ulp.

## D166 - G137: cada prancha de aco emitida tem codigo; o prazo sai do medido (2026-09-14) - FECHADO

**Pedido.** O caderno do galpao saia sem nenhuma prancha de aco: 459 s de
1200 s para um executivo medido em ~788 s + 3D ~210 s; 15 PDFs emitidos,
so 3 com codigo.

**Medido antes de mudar (2026-09-14, sem freecad salvo onde dito).**
1. Prazo do aco no caderno: `caderno_turnkey._dispatch_pranchas` dividia o
   stage meio a meio (3D/executivo); com global 1200 o executivo recebia
   ~459 s (`timeout 459.18 s aguardando pranchas`, D164) — estoura por
   construcao em toda rodada.
2. Tempo por prancha (`tools_harness_aco_por_prancha.MEDIDOS_G109`, G109 +
   G118): PE01 187,6; PE02 58,7; PE03 211,9; PE04 15,4; PE05 209,4; PE06 6,3;
   PE07 7,6; PE08 28,7; PE09 7,7; PE10 12,8; PE11 8,6; PE12 10,7; PE13 12,0;
   PE14_CROQUIS 4,9; PE16 5,4 (total 787,7 s); PE14_DET_CONSOLE e
   PE15_DET_BLOCO 0,0 (condicionais ausentes no modelo). 3D ~210 s (D164,
   ~3,5 min). D165: 1038,9 s total (referencia) / 1186,4 s no pytest.
3. 15 pranchas contra o mapa: `conferir_pranchas_aco` com as 15 do D165
   contra `galpao_adapter._PRANCHA_ARQUIVO_GALPAO` (3 entradas de aco) +
   `SEM_CODIGO_ACO` (12) — 12 sem codigo, baseline nos dois sentidos.

**Entregue.**
- `pacote_legal._PRANCHAS["aco"]`: 3 -> 17 titulos (PE-ES-01..17; os 3
  primeiros intactos; PE-ES-04..15 as 12 do D165; PE-ES-16/17 as
  condicionais console/bloco, com motivo de ausencia declarada no laco).
- `galpao_adapter._PRANCHA_ARQUIVO_GALPAO`: 19 -> 33 entradas, 1:1 medido
  contra o `techdraw_exec` (literais via AST + `LIGACOES` para as 5
  variaveis PE10-13/console, mesma fonte do harness G105).
- `pacote_legal.CORRESPONDENCIA_NUMERACAO_GALPAO`: as 8 com carimbo
  extraivel ganham `cobre` (PE-ES-04..09,14,15); as 4 de ligacao sem
  carimbo literal seguem fora da lente G112 (nao-coverture declarada).
- Prazo do medido: `_T_MEDIDO_SEG["aco"]` 578 -> 787,7 s (peso 7,0 ->
  9,5396 via `peso_medido`); split 3D/exec proporcional ao medido
  (210/787,7) em vez de meio a meio; global 1200 -> 2100 s (aco 1038,9 +
  resto 536,3 = 1575 s + folga ~33 % para variacao de maquina; COMO-RODAR
  ja pedia >= 1800 para o lote cheio; sem aco o rapido segue ~536 s).
- `tests/test_executivo_aco_completo_d165.py`: `SEM_CODIGO_ACO` vazia
  (portao nos dois sentidos segue acusando prancha nova sem codigo e nome
  morto).
- Novo `tests/test_executivo_aco_g137.py` (4): 1:1 medido contra o emissor,
  vermelho por injecao em tmp_path nos dois sentidos, tres aceites de
  PE02/PE03 (pagina+carimbo no fonte, codigo no mapa, titulo que diz o que
  desenha), prazo derivado do medido (o dispatch le `_T_MEDIDO_*`; meio a
  meio ausente; global 2100).

**Tres aceites por folha, olhando o PNG (rodada de auditoria D165,
freecad sozinho, 2026-09-14, `PE02_FUNDACOES.png` / `PE03_ELEVACOES.png`
em `Temp/pytest-of-joseh/pytest-2885/.../pranchas/`).**
- PE-ES-04 / PE02_FUNDACOES.pdf — (1) esta certa: PLANTA DE FUNDACOES
  1:150, 13 eixos x 3 linhas = 39 sapatas (90,00 m / 7,50 m / 44,00 m),
  QUADRO DE SAPATAS + cotas em metros (sapatas em cm), carimbo PE-02
  02/15, sem pagina em branco; (2) sai no manifesto: PDF em
  `aco/pranchas/`, registrado em `drawings` + `executive-dossier` (o
  portao D165 lista as 15 e fecha com a baseline vazia); (3) diz o que
  desenha: indice "Planta de fundacoes", carimbo "PLANTA DE FUNDACOES",
  anotacao "PLANTA DE FUNDACOES ESCALA 1:150".
- PE-ES-05 / PE03_ELEVACOES.pdf — (1) esta certa: ELEVACAO FRONTAL
  (OITAO) 44,00 m + ELEVACAO LATERAL 90,00 m, pe-direito 7,00 m /
  cumeeira 8,10 m, baias 7,50 m, ESC 1:300, carimbo PE-03 03/15; (2) sai
  no manifesto (mesma via do D165); (3) diz o que desenha: indice
  "Elevacoes", carimbo "ELEVACOES", anotacoes "ELEVACAO FRONTAL (OITAO)"
  / "ELEVACAO LATERAL".
- Conteudo das pranchas intacto (nenhuma geometria/cota/nota tocada; o
  diff e so mapa/indice/prazo/testes).

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
G93 `PROMETIDOS_ESPERADOS` 19 -> 33 (+`_paginas_techdraw` lendo `LIGACOES`
para as 5 variaveis); G112 `BASELINE_G112` (8 do aco de arquivo_sem_mapa
para fora_do_mapa com os esperados PE-ES-..; isentas seguem 22);
G91 `test_06` 19 -> 33 e comentario 19/19 -> 33/33; G108 `FRACAO_ACO`
0,8197 -> 0,8610 (antiga 0,5490 -> 0,6239 com o peso novo).

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_
sequencia.confere()`, `varredura_constantes_orfas.confere()` — OK, OK,
OK; `test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`, `test_galpao_indice_g93`,
`test_suite_paralela_d164` + `test_executivo_aco_completo_d165:test_01` +
`test_executivo_aco_g137` (4) — 147 passed.

**G102 isolado com -s (2026-09-14, maquina livre).**
`CUSTO_G102 casa=2.5s predio=7.0s galpao=579.2s total=588.7s`, 9 passed
em 594,8 s; `MEM_G102 ... galpao=2054.3MB(proc=205.9,fc=1911.9,n=1)`
(teto 2500). Congelado segue D165 (2,0/6,3/536,3; 112,5/207,5/1616,8):
a variacao (+8 % tempo, +27 % pico) e de maquina, nao do diff (o diff so
acrescenta 14 puladas nomeadas sem freecad; o `test_05` segue verde sob
o teto). Nao devolvido o executivo ao G102 (`executivo_aco=False` fica).

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 299 arquivos
== coletados): 3843 passed, 1 skipped, 0 falhas, 18 min 18 s, `quebras`
vazio** (censo do FreeCAD fechado, `git status` igual, memoria livre
minima 379 MB). O skip e o portao de auditoria do aco. +4 sobre os 3839
do D165 (o guarda novo G137).

**Portao de auditoria do aco (`GALPAO_AUDITORIA=1 pytest -s
tests/test_executivo_aco_completo_d165.py`): 2 passed em 1067,3 s**,
`CUSTO_D165 executivo_aco_completo=1066.4s` (referencia D165 1038,9 s;
pytest D165 1186,4 s). As 15 pranchas batem com o mapa 1:1 nos dois
sentidos — o portao dispara e fecha na rodada real.

**Nao feito (do goal).** Mudar geometria/calculo/conteudo das pranchas;
tirar `executivo_aco=False` do G102 (o rapido fica rapido).

## D167 - G139: a coordenacao que o hook nunca emitia passa a sair no recorte, com peso medido e codigo nas duas folhas (2026-09-14) - FECHADO

**Pedido.** PE-CD-01 saia pulada em toda rodada do galpao: `montar_caderno`
so emitia a prancha formal com `disciplinas=None` e o hook sempre passa o
recorte; peso da coordenacao literal (0,5/0,75); 2a folha sem codigo.

**Medido antes de mudar (2026-09-14, mocks sem freecad onde dito).**
1. Remeça com fakes (sem freecad): recorte de 2 disciplinas -> render 1,
   prancha formal 0; `disciplinas=None` -> render 1, prancha 1; recorte de
   1 -> render 1 (desperdicio), prancha 0. O hook (`_emit_drawings`) nunca
   passa None — PE-CD-01 nunca emitida, por construcao.
2. Tempos cronometrados (galpao-tp-g95, freecad.exe nesta maquina,
   processo reiniciado por amostra): clash puro 0,012 s (4 disc) / 0,184 s
   (5 disc, 767 membros); render federado 12,1 s (4 disc, 155 membros),
   20,0 s (5 disc), 73,6 + 95,6 s (6 disc com aco, 3012 membros, 2850
   solidos); prancha formal 13,0 s (4 disc), 15,2 s (5 disc), 34,8 (1a,
   freecad morno — fora) + 67,8 + 69,8 + 65,7 s (frias, ok=True, 2 PDFs).
   Pesos literais 0,5/0,75 lidos pela producao sem cronometro (convencao 8
   violada no estado inicial).

**Entregue.**
- `caderno_turnkey.montar_caderno`: a coordenacao e de quem RODOU (o
  alvo/recorte), nao de quem existe no R — com >= 2 disciplinas no alvo,
  render + prancha formal entram na reserva com peso medido; com 1, seguem
  fora com motivo escrito (`MOTIVO_COORDENACAO_RECORTE_1`, visivel em
  `status["coordenacao"]`). O render desperdicado no recorte de 1 sumiu.
- Prazo do medido: `_T_MEDIDO_SEG["coordenacao_render"]=95,6` (peso
  1,1578) e `["coordenacao"]=69,8` (peso 0,8453), via `peso_medido`
  (ancora 578 s) — os MAXIMOS das amostras. A 1a versao usou a media
  (73,6/34,8) e estourou por construcao (`timeout 62,4 s na prancha`,
  G102 sob carga): a licao do G137 vale para a coordenacao.
- Cada folha emitida tem codigo (regra do G137): PE-CD-02 para o quadro de
  clash (titulo em `PE_CD_02_GALPAO`, prometido so no laco do galpao pela
  fronteira — o vocabulario partilhado com o predio segue com 1 titulo
  para nao prometer ao predio (folha unica) um codigo sem cobertura).
  Sem isso, a emissao parcial medida (COORD01 sem COORD02 no timeout sob
  carga) era estado real irrepresentavel: nem codigo, nem isencao sem
  tripwire de `isencao morta`.
- `galpao_adapter`: motivo PE-CD-01 reescrito para a regra nova (>= 2; 1
  segue sem); motivo proprio PE-CD-02; mapa 33 -> 34 entradas 1:1 medidas
  contra o `techdraw_coordenacao` (AST); `CORRESPONDENCIA` com cobre
  1:1 nas duas folhas.
- Novo `tests/test_coordenacao_g139.py` (5): recorte >= 2 emite / 1 segue
  sem motivo (fakes com PDFs validos em tmp_path); vermelho por injecao
  nos dois sentidos (lente + motivo vivo, sem o texto do defeito);
  tres aceites PE-CD-01/02 (pagina no emissor, codigo no mapa, titulo que
  diz o que desenha); prazo deriva do medido (sem literais 0,5/0,75);
  emissao parcial fecha a lente sem extra nem buraco.
- Predio e casa intactos em producao (nenhuma linha): predio segue 15/15.

**Tres aceites por folha, olhando o PNG (rodada de medicao 6 disciplinas,
2026-09-14, `COORD01_PLANTA.png` / `COORD02_CLASH.png` em
`Temp/coord_6d_beh2wkk4_coord/pranchas/`; confirmados na rodada G102).**
- PE-CD-01 / COORD01_PLANTA.pdf — (1) esta certa: titulo COORDENACAO -
  MODELO FEDERADO, PLANTA (comprimento x largura) + ELEVACAO
  (comprimento x altura), legenda com as 6 disciplinas coloridas
  (Concreto/Eletrico/Incendio/Climatizacao/Hidraulica/Aco) + Clash a
  revisar, RESUMO DE CLASH (Membros 3012, Conflitos 970, A revisar 688,
  Esperados 282, por par acoX*), carimbo PE-COORD-01 01/02 PARA APROVACAO,
  sem pagina em branco; (2) sai no manifesto: PDF em
  `coordenacao/pranchas/`, registrado em `drawings` + `executive-dossier`,
  `disciplinas.coordenacao=2` no caderno; (3) diz o que desenha: indice
  "Modelo federado / compatibilizacao", carimbo "PLANTA DE COORDENACAO -
  MODELO FEDERADO".
- PE-CD-02 / COORD02_CLASH.pdf — (1) esta certa: QUADRO DE
  INTERFERENCIAS (CLASH) - COORDENACAO (22 A REVISAR + 8 esperados),
  NOTAS com frame comum X=comprimento e triagem NBR 5419 vs A REVISAR,
  carimbo PE-COORD-02 02/02 (texto legivel esq->dir; o suposto
  espelhamento do thumbnail nao se confirmou no zoom nem no render fitz
  independente); (2) sai no manifesto (mesma via); (3) diz o que desenha:
  indice "Quadro de clash e notas", carimbo "QUADRO DE CLASH E NOTAS".
- Rodada G102 final (adapter de verdade, abaixo): `coordenacao ok:true`,
  `timed_out:false`, `skipped` sem coordenacao, ambos os PDFs no disco e
  nos artifacts.

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
G93 `PROMETIDOS_ESPERADOS` 33 -> 34 (+PE-CD-02; `_prometidos_vivos` deriva
do vivo + o codigo de fronteira); G91 `_quadro_galpao` 33 -> 34 (predio
segue 15/15; `test_06` conta a mao 33 + 1 de fronteira, anti-tautologia
acusou e foi atualizado); G112 `BASELINE_G112` (COORD02 de
arquivo_sem_mapa para fora_do_mapa com esperado [PE-CD-02]; isentas
seguem 22 arquivos); G108 `FRACAO_ACO` inalterada 0,8610 (coordenacao ja
consumida nos pendentes do aco); G101 passa (motivo PE-CD-02 com
not_available + dado nomeado); G107 `CODIGOS_FREECAD` + PE-CD-02 (causa
freecad via disciplina dona); G102 `CUSTO_MEDIDO_*` abaixo.

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_
sequencia.confere()`, `varredura_constantes_orfas.confere()` — OK, OK,
OK; `test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`, `test_galpao_indice_g93`,
`test_suite_paralela_d164` + `test_coordenacao` + `test_coordenacao_g139`
(5) + `test_caderno_pesos_g108` + ramos rapidos do G102 — verdes.

**G102 isolado com -s, tres corridas (2026-09-14, maquina livre).**
1. `casa=2.3s predio=7.0s galpao=661.8s total=671.1s`, 1 passed em 671,3 s
   (com a isencao COORD02 provisoria: passou = COORD02 existia no disco).
2. `casa=2.3s predio=8.5s galpao=732.7s total=743.5s` — com PE-CD-02 e
   pesos medios: `status.coordenacao = timeout 62,4 s`, freecad morto com
   so COORD01 pronta (prova de que a media nao cobre a necessidade;
   PE-CD-01 reivindicada, PE-CD-02 pulada com motivo — o desenho que
   aguentou o estado parcial).
3. `casa=2.4s predio=8.3s galpao=729.9s total=740.6s`, 1 passed em 740,9 s
   (pesos maximos: `coordenacao ok:true`, `timed_out:false`, ambos os
   PDFs + PNGs + status no disco e nos artifacts).
Congelado: `CUSTO_G102 casa=2.4s predio=8.3s galpao=729.9s`
(total=740.6s); `MEM_G102 casa=108.8MB predio=207.4MB
galpao=2111.3MB(proc=206.0,fc=1968.4,n=1)` (teto 2500). O galpao sobe
+193,6 s / +~495 MB sobre o D165 pelo diff (federado com aco + prancha
formal); casa/predio e variacao de maquina. Executivo de aco segue fora
do G102 (`executivo_aco=False` fica).

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 300 arquivos
== coletados), tres corridas, `quebras` vazio nas tres.**
1. 22 min 36 s: **4 failed, 3843 passed, 1 skipped** — G102 com
   `isencao morta COORD02_CLASH.pdf` (emissao parcial sob carga, acima)
   + 3 G21. Decisao: PE-CD-02 (estado parcial vira pulada nomeada) e
   pesos pelos maximos (acima), em vez de reinspecionar a loteria.
2. 25 min 05 s: **3 failed, 3845 passed, 1 skipped** — G102 VERDE no
   paralelo (o desenho aguentou); restam 3 G21.
3. 25 min 02 s: **3 failed, 3845 passed, 1 skipped** — os mesmos 3 G21;
   `quebras` vazio; memoria livre minima 534 MB; censo fechado.
Os 3 G21 (`test_G21_C1/C2/C3_disco_*_fica_vermelho`) sao anteriores ao
goal e alheios as fontes que ele toca (mutam `galpao_concreto` /
`edificio_multipavimento` em copia e rodam pytest em subprocesso): nas
3 corridas o subprocesso morre sem nenhuma saida (`rc != 0` com
`saida == "\n"` — a 1a assercao, mutacao->vermelho, PASSOU nas 3; so a
conferencia do texto da saida cai). Serial passam em 4 s (medido agora,
com o diff aplicado); o proprio arquivo documenta a nao-determinacao
sob paralelo desde 2026-09-03. Sem relacao com este diff (falham igual
antes e depois do PE-CD-02; nenhum modulo tocado por eles foi tocado
aqui — `git status` na auditoria). Fica registrado para goal proprio;
nao e verde por edicao: `rc_pytest` ficou 1 nas tres corridas.

**Nao feito (do goal).** Mudar a checagem de clash; devolver o executivo
de aco ao G102; prometer PE-CD-02 ao predio (folha unica, sem cobertura
— seria numero inventado); consertar o flake de subprocesso do G21
(goal proprio).

## D168 - G138: PE-IN-02 do galpao sai do emissor existente, adaptado do calculo, com as ausencias declaradas (2026-09-14) - FECHADO

**Pedido.** PE-IN-02 saia pulada em toda rodada do galpao ("sem emissor
de detalhe de hidrantes e rotas nesta rodada"): o emissor existe e esta
provado (`desenho_incendio.detalhes_hidrantes_rotas_svg` /
`gerar_detalhes_hidrantes`, chamado so pelo predio), mas o resultado do
incendio do galpao tem outra forma (G101 mediu a fronteira e manteve a
folha ausente).

**Medido antes de mudar (2026-09-14, sem freecad).**
1. `galpao_seguranca_incendio.rodar` (spec real do galpao-tp-g95, com
   `hidrantes: {ocupacao: industrial_I2}`) devolve chaves de topo
   `ATENDE/deteccao_alarme/gates/hidrantes/iluminacao_emergencia/
   reprovados/sinalizacao/spec/sprinklers`; `gates.hidrantes =
   {tipo: 2, sistema: hidrante, N_hidrantes: 4, vazao_total_Lmin: 600.0,
   reserva_m3: 36.0, ...}` e `spec = {C: 40.0, L: 20.0, H: 6.0}`.
2. O emissor le no shape do predio: `inc.sistemas.hidrantes`
   (N_hidrantes/tipo/reserva_incendio_m3) + `inc.gates.rotas_verticais`
   (n_minimo/n_declarado) e `escada_largura` (largura_exigida_m) +
   `inc.estrategia_abandono/populacao_total/altura_edificacao_m` +
   `estrutura.pavimentos`. Remeça no `test_01` (fonte viva: o fonte do
   emissor + o `rodar()` do galpao, nunca o proprio mapa).
3. Faltam ao galpao 6 campos: `gates.rotas_verticais`,
   `gates.escada_largura`, `estrategia_abandono`, `populacao_total`,
   `altura_edificacao_m`, `estrutura.pavimentos` (galpao terreo, nivel
   unico) — constantes em `AUSENCIAS_GALPAO_DETALHES`, uma fonte so na
   producao. Sem hidrantes no spec, um 7o entra na frente (`hidrantes nao
   calculados`).

**Entregue.**
- `desenho_incendio.adaptar_galpao_para_detalhes(r)`: (inc, estrutura,
  ausentes) lidos do calculo — o `hidrantes` cru de `r["hidrantes"]`, com
  `reserva_incendio_m3` original (nunca o gate reescrito `reserva_m3`);
  nenhum recalculado.
- `detalhes_hidrantes_rotas_svg(..., ausencias=None, nivel_unico=False)`:
  defaults = caminho do predio byte-identico (provado contra o HEAD:
  2473 bytes iguais); `nivel_unico=True` desenha os N hidrantes lado a
  lado no nivel unico (EXATAMENTE N simbolos == N_hidrantes, nunca N
  pavimentos inventados) e declara as ausencias em caixa vermelha na
  folha; `gerar_detalhes_hidrantes` repassa; `gerar_detalhes_galpao`
  adapta + escreve (uma fonte so).
- Executivo do galpao com INC03_DETALHES nos dois backends: rota
  svg-direta em `galpao_seguranca_incendio.montar_pranchas` (A1 via
  `pagina_esquema_a1` + carimbo PE-INC-03 03/03) e `_pr_detalhes` no
  `techdraw_incendio` (FreeCAD); INC01/INC02 passam a 01/03 e 02/03 (o
  galpao muda de 2 para 3 folhas; o predio nao usa este executivo).
- Mapa ja apontava INC03 (1:1 sem mudar); motivo PE-IN-02 reescrito para
  a regra nova (emite com incendio executado; sem ele, segue sem com o
  arquivo e o dado nomeados); `CORRESPONDENCIA` com `cobre: [PE-IN-02]`
  1:1 (cada folha emitida tem codigo, regra do G137/G139) + intro e
  entradas INC01/INC02 atualizadas.
- Novo `tests/test_hidrantes_g138.py` (5): remeça dos 6 (+7o sem
  hidrantes); predio byte-identico + galpao sem recalculo (N simbolos ==
  N do calculo, reserva do calculo, ausencias na folha); INC03 no disco,
  parse, guarda e raster (PNG com bytes); vermelho por injecao nos dois
  sentidos (emissor morto -> erro nomeado; sem INC03 a lente acusa
  PE-IN-02 faltando; motivo vivo com codigo/arquivo/dado); tres aceites
  (pagina no emissor via AST, codigo no mapa, titulo/carimbo/cobertura).
- Predio intacto em producao (nenhuma linha no caminho do predio):
  `edificio_adapter` segue chamando com 3 args; predio 15/15 no G102.

**Tres aceites por folha, olhando o PNG (spec real do galpao-tp-g95,
2026-09-14, `C:/tmp/g138/INC03_DETALHES.png`, 1437x978, 11.797 px
vermelhos / 57.593 nao-brancos; SVG com 4 `HID-`).**
- PE-IN-02 / INC03_DETALHES.pdf — (1) esta certa: titulo DETALHES -
  HIDRANTES (GALPAO TERREO) E ROTAS DE FUGA, COLUNA DN65 (NBR 13714), 4
  hidrantes HID-1..HID-4 lado a lado no nivel unico ("nivel unico
  (terreo): 4 hidrante(s) no mesmo nivel"), QUADRO DE ROTAS com RESERVA
  DE INCENDIO 36.0 m3 do calculo, caixa vermelha DADOS NAO DECLARADOS
  PELO CALCULO DO GALPAO (G138) com os 6 campos, sem pagina em branco;
  (2) sai no manifesto: PDF em `incendio/pranchas/`, registrado em
  `drawings` + `executive-dossier` (a lente fecha PE-IN-01/02 com INC01 +
  INC03; o G102 abaixo lista INC03 sem pulada); (3) diz o que desenha:
  indice "Detalhes hidrantes/rotas", carimbo PE-INC-03 "DETALHES DE
  HIDRANTES E ROTAS", correspondencia cobre [PE-IN-02] 1:1.

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
G93 `DECLARADOS_SEM_EMISSOR` -PE-IN-02 (ganha emissor; ficam PE-CO-04 e
PE-IN-03); G112 `BASELINE_G112` fora_do_mapa 19 -> 20 (+INC03/PE-INC-03
[PE-IN-02]; `techdraw_incendio` entra na extracao viva) e isentas 22 ->
23; tabela 22 -> 23 entradas; G107 `FOLHAS_ESQUEMA` +INC03 (a rota SVG
emite 3 PDFs no incendio); G104 `test_rota_svg_incendio_emite_2_pdfs_a1`
3 arquivos/pranchas; `test_executivo_incendio` build 2 -> 3; G102
`CUSTO_MEDIDO_*` abaixo.

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_
sequencia.confere()`, `varredura_constantes_orfas.confere()` — OK, OK,
OK; `test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`, `test_galpao_indice_g93`,
`test_suite_paralela_d164` + `test_hidrantes_g138` (5) +
`test_rota_svg_g104` + `test_executivo_incendio` (puros) +
`test_galpao_escada_fronteira_g101` + `test_galpao_svg_sem_freecad_g107` +
`test_caderno_pesos_g108` + `test_coordenacao_g139` + predio
(`test_edificio_pranchas_g56`, `test_incendio_bim`,
`test_incendio_robustez`) — verdes.

**G102 isolado com -s (2026-09-14, maquina livre).**
`casa=2.4s predio=8.7s galpao=725.5s total=736.5s`, 9 passed em 742,6 s;
`MEM_G102 casa=108.2MB predio=207.7MB galpao=2076.6MB
(proc=212.8,fc=1938.4,n=1)` (teto 2500). Congelado com estes numeros
(variacao de maquina sobre o G139: +0,4 s predio, -4,4 s galpao; o diff
so acrescenta 1 PDF SVG de ~ms a rodada do galpao). Executivo de aco
segue fora do G102 (`executivo_aco=False` fica).

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 301 arquivos
== coletados): 1 failed, 3852 passed, 1 skipped, 23 min 54 s, `quebras`
vazio** (censo do FreeCAD fechado, memoria livre minima 767 MB). O skip
e o portao de auditoria do aco; +2 arquivos sobre os 299 do D166 (os
guardas novos G137/G138). O 1 failed era baseline do proprio diff
(`test_montar_caderno_vivo_incendio`: caderno so-incendio com 3
pranchas, nao 2 — corrigido com motivo para 3, verde isolado em
`test_caderno_turnkey.py`). Nenhum G21 falhou nesta corrida.

**Nao feito (do goal).** Recalcular hidrantes; mexer na rota SVG do G104
(a rota segue com 2 arquivos nas outras disciplinas; o INC03 sai do
`galpao_seguranca_incendio`, nao da `prancha_svg_direta`); prometer
PE-IN-03 ao galpao sem escada (fronteira G101 fica); devolver o
executivo de aco ao G102.

## D169 - G140: PE-CO-04 do galpao sai do emissor existente, adaptado do calculo, com cada sapata desenhada uma por uma (2026-09-14) - FECHADO

**Pedido.** PE-CO-04 saia pulada em toda rodada do galpao ("sem emissor
de locacao e formas da fundacao nesta rodada"): a fundacao do
pre-moldado sai dimensionada (`galpao_concreto`) sem folha de locacao.
A casa tem `desenho_casa_residencial.fundacao_locacao_formas_casa_svg`
(`:733`, que delega a mesma funcao do G80) e o predio tem
`desenho_fundacao_edificio` (PE-CO-04 do predio emitida — predio real
sem nenhuma folha pulada).

**Medido antes de mudar (2026-09-14, sem freecad).**
1. `galpao_concreto.rodar` (spec do galpao-tp-g95: vao 20, 7 porticos,
   sigma 250) devolve a sapata UNICA dimensionada (`sapata.aprovado =
   (B, L, h, rA, cA)`, ex. 3.0 x 3.0 x 0.90) + `spec {vao, comprimento,
   H, n_porticos, s}` + `tipo_fundacao`; sem `por_pilar`, sem
   `proveniencia_sigma`, sem `cota_apoio_m`.
2. O emissor le no shape do predio: `fundacao.{tipo, sigma_solo_adm,
   proveniencia_sigma, cota_apoio_m, por_pilar[{i, j,
   N_dimensionamento_kN, geometria}]}` + `estrutura.{vaos_x, vaos_y}`.
   Remeça no `test_01` (fonte viva: o fonte do emissor + o `rodar()`
   do galpao, nunca o proprio mapa).
3. Faltam ao galpao 2 campos: `cota_apoio_m` (sempre — o calculo usa
   h_reaterro=0,5 m) e a tensao sem sondagem (só quando o sigma é
   default 200 sem SPT nem spec) — constantes em
   `AUSENCIAS_GALPAO_LOCACAO`, uma fonte so na producao. O `por_pilar`
   (malha 2 x n_porticos, P<j><E|D> como no `membros_bim`) e os vaos
   ([vao] x [s]*(n-1)) sao construidos da sapata dimensionada, nunca
   redimensionados.

**Entregue.**
- `desenho_fundacao_edificio.adaptar_galpao_para_locacao(r, spec)`:
  (fundacao, estrutura, ausentes) lidos do calculo — cada pilar com a
  sapata (ou o grupo de estacas) DIMENSIONADA; sem sapata/estaca
  aprovada levanta ValueError com o codigo PE-CO-04 (nunca folha
  vazia). `gerar_locacao_galpao` adapta + escreve o SVG (uma fonte
  so).
- `planta_fundacao_svg(..., ausencias=None)`: defaults = caminho do
  predio/casa byte-identico (provado contra o HEAD: 8486 bytes
  iguais); com ausencias desenha a mesma planta (uma por pilar,
  `confere_desenho_fundacao` ok) e declara a caixa vermelha
  DADOS NAO DECLARADOS PELO CALCULO DO GALPAO (G140); o quadro
  encurta acima da caixa (sem ausencias, pixel a pixel como antes).
- Executivo do galpao com PE04_LOCACAO_FUNDACAO nos dois niveis:
  `_pr_locacao` no `techdraw_concreto` (carimbo PE-04 04/04, simbolo
  da locacao; PE01..PE03 passam a 01/04..03/04) + fallback puro-Python
  em `galpao_concreto.montar_pranchas` (`gerar_prancha_locacao`, A1
  via `pagina_esquema_a1` com o carimbo do concreto — mesma via do
  INC03 no G138; só entra se a PE04 caiu no FreeCAD).
- Mapa ja apontava PE04 (1:1 sem mudar); motivo PE-CO-04 reescrito
  para a regra nova (emite com concreto executado; sem ele, segue sem
  com o arquivo e o dado nomeados); `CORRESPONDENCIA` com
  `cobre: [PE-CO-04]` 1:1 (cada folha emitida tem codigo, regra do
  G137/G139) + intro (concreto PE-01..PE-04; PE-04 em dois arquivos,
  como o PE-01).
- Novo `tests/test_fundacao_locacao_g140.py` (5): remeça dos 2 (+caso
  sem sigma, +erro sem sapata); predio/casa byte-identicos + galpao
  sem recalculo (14 rects data-pilar == 2 x 7, B/L/Ndim ==
  dimensionados, adaptar nao muta o resultado); PE04 no disco, parse,
  guarda e raster (PNG com bytes); vermelho por injecao nos dois
  sentidos (emissor morto -> erro nomeado; sem PE04 a lente acusa
  PE-CO-04 faltando; motivo vivo com codigo/arquivo/dado); tres
  aceites (pagina no emissor via AST, codigo no mapa,
  titulo/carimbo/cobertura).
- Predio e casa intactos em producao (nenhuma linha no caminho com
  defaults): `edificio_adapter` e `desenho_casa_residencial:733`
  seguem chamando sem `ausencias`.

**Tres aceites por folha, olhando o PNG (spec real do galpao-tp-g95,
2026-09-14, `C:/tmp/g140/PE04_LOCACAO_FUNDACAO.png`, 2170x1559, 9.991
px vermelhos / 125.434 nao-brancos; SVG com 14 `data-pilar`).**
- PE-CO-04 / PE04_LOCACAO_FUNDACAO.pdf — (1) esta certa: titulo
  PE-CO-04 - LOCACAO E FORMAS DA FUNDACAO DO GALPAO (sapata ;
  14 pilares), malha 2 x 7 (eixos 1-2 x A-G, vaos 20,00 x 15,00),
  cada uma das 14 sapatas 3.00 x 3.00 com Ndim 174 kN do calculo,
  QUADRO DE FUNDACAO com tipo/sigma/proveniencia/cota e as 14 linhas
  3.00 x 3.00 x 0.90, caixa vermelha com a cota ausente, sem pagina
  em branco; (2) sai no manifesto: PDF em `concreto/pranchas/`
  (4a prancha do executivo, provada no `test_build_gera_pranchas_pdf`
  com freecad.exe: PE01..PE04), registrado em `drawings` (a lente
  fecha PE-CO-01/04; o G102 abaixo lista PE04 sem pulada); (3) diz o
  que desenha: indice "Locacao e formas da fundacao", carimbo PE-04
  "LOCACAO E FORMAS DA FUNDACAO", correspondencia cobre [PE-CO-04]
  1:1.
- Ressalva visual: a cota do vao (20,00) cruza entre as duas linhas
  de legenda da fileira P1 (sapata pequena em vao grande) — a mesma
  classe da linha de cota que atravessa a sapata no predio (emissor
  do G80, fora do escopo: refaze-lo mudaria o predio byte-identico).

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
G93 `DECLARADOS_SEM_EMISSOR` -PE-CO-04 (ganha emissor; fica PE-IN-03);
G112 `BASELINE_G112` fora_do_mapa 20 -> 21 (+PE04_LOCACAO_FUNDACAO/
PE-04 [PE-CO-04]; `techdraw_concreto` entra na extracao viva) e
isentas 23 -> 24; tabela 23 -> 24 entradas; `test_techdraw_concreto`
3 -> 4 pranchas (+`test_config_locacao_g140` puro); G102
`CUSTO_MEDIDO_*` abaixo (sem re-congelar: o portao passou no teto).

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.confere()` — OK, OK,
OK; `test_folhas_g77`, `test_alcancabilidade`, `test_guardas_d86_g69`,
`test_disciplina_prancha_g103`, `test_indice_disco_g91`,
`test_carimbo_mapa_g112`, `test_normas_catalogo`, `test_galpao_indice_g93`,
`test_suite_paralela_d164` + `test_fundacao_locacao_g140` (5) +
`test_techdraw_concreto` (puro) + `test_galpao_escada_fronteira_g101` +
`test_galpao_svg_sem_freecad_g107` + `test_caderno_pesos_g108` +
`test_coordenacao_g139` + `test_hidrantes_g138` + predio
(`test_edificio_pranchas_g56`, `test_fundacao_prancha_g80`) e casa
(`test_casa_concreto_g100`) — verdes.

**G102 isolado com -s (2026-09-14, maquina livre, 2 corridas).**
`casa=2.6s predio=7.9s galpao=619.9s total=630.4s`, 9 passed em
636,7 s (1a corrida: 9 passed em 652,6 s);
`MEM_G102 casa=104.0MB predio=206.8MB galpao=2068.7MB
(proc=211.6,fc=1926.3,n=1)` (teto 2500). Variacao de maquina sobre o
G138 (galpao 725,5 s la; a PE04 soma 1 pagina TechDraw ao concreto,
~s, sem freecad extra). Executivo de aco segue fora do G102
(`executivo_aco=False` fica).

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 302 arquivos
== coletados): `rc_pytest` 0, 3859 passed, 1 skipped, 20 min 52 s,
`quebras` vazio** (censo do FreeCAD fechado, memoria livre minima
329 MB). O skip e o portao de auditoria do aco; +1 arquivo sobre os
301 do D168 (o guarda novo G140). Tres corridas anteriores falharam
só nos 3 testes de subprocesso do G21-C (C1/C2/C3, saida vazia no
pipe) — flake de infra, nao do diff: os 3 passam isolados em ~4 s e
o mecanismo aninhado foi provado a mao (rc=1 com FAILED no stdout).
Causa medida: nesta maquina (console cp850, repo em caminho com
"Área") o spawn dos workers xdist quebra com `UnicodeEncodeError ...
surrogates not allowed` no bootstrap do execnet; com `PYTHONUTF8=1`
no ambiente o spawn cura e a suite fecha verde (o repo só abre
arquivo com encoding explícito, nada muda nos testes).

**Nao feito (do goal).** Redimensionar fundacao (a adaptacao só lê);
refazer o emissor do G80 (a cota que cruza a legenda/sapata e dele,
e o predio segue byte-identico); prometer PE-IN-03 ao galpao sem
escada (fronteira G101 fica).

## D170 - G141: o mezanino calculado ganha codigo (PE-MZ-01, ausencia declarada por codigo, sem mudar o calculo) (2026-09-14) - FECHADO

**Pedido.** `galpao_turnkey.DISCIPLINAS` inclui `mezanino` (despachado por
`_run_mezanino`, levado ao BIM); `pacote_legal._PRANCHAS` nao tinha a
disciplina, entao ela era executada e sumia no `continue` do indice (D89
do lado da promessa, D121). Travado por assert em
`tests/test_indice_disco_g91.py:304-305`, nao consertado. Nenhum
`projects/*/project-spec.json` declara mezanino (0 ocorrencias).

**Medido antes de mudar (2026-09-14, sem freecad).**
1. `tk.DISCIPLINAS` = 7 com `mezanino`; `mezanino in pl._PRANCHAS` = False;
   o indice vivo da rodada (executadas filtradas ao vocabulario +
   coordenacao) promete 34 sem o mezanino - a disciplina some por
   construcao. Remeça no `test_01` do guarda novo (fontes vivas + glob
   dos 8 project-specs, nunca o proprio mapa).
2. `galpao_mezanino.rodar` na amostra 6x5 a 3 m no galpao 40x20x6 ATENDE
   (laje+vigas+pilares+sapatas, membros 4 Beam + 4 Column + 4 Footing +
   1 Slab, marcas M- federadas sem transformar).

**Entregue (ausencia declarada por codigo, sem folha nova).**
- `pacote_legal._PRANCHAS["mezanino"]` = ("PE-MZ", ["Mezanino de concreto
  (laje/vigas/pilares)"]) + entrada em `_ORDEM_DISC` (apos o concreto) e
  no grupo de LOD da estrutura; sem `_ART`/O&M novos (o mezanino segue na
  responsabilidade do concreto). Sem mezanino executado o indice/pacote
  saem byte-identicos (a disciplina so entra quando executada).
- `galpao_adapter._PRANCHA_ARQUIVO_GALPAO["PE-MZ-01"]` = "MZ01_MEZANINO.pdf"
  + motivo nomeado (sem emissor TechDraw ligado; o dimensionamento sai no
  memorial/BIM com membros M-). Sem correspondencia nova (nenhum arquivo
  emitido; PE-IN-03 e o precedente).
- `caderno_turnkey`: ROTULO/ORDEM com mezanino + dispatch declarado (ok
  None com `MOTIVO_MEZANINO_SEM_PRANCHA`, nunca erro) + comentario do peso
  atualizado (antes "sem dispatch", isento no G103).
- `varredura_disciplina_prancha.ISENCOES_DISCIPLINA_PRANCHA` vazia (a cura
  matou a isencao); o assert do G91 vira o portao do comportamento novo
  (`mezanino in _PRANCHAS`, prefixo PE-MZ, PE-MZ-01 nos prometidos).
- Novo `tests/test_mezanino_indice_g141.py` (5): remeça; rodada com
  mezanino (PE-MZ-01 no indice e no pacote, laco fecha via pulada nomeada,
  M- no federado; spec em tmp_path); sem mezanino byte-identico (sem
  PE-MZ/MZ01/mezanino no indice/pacote/md, concreto bit a bit igual);
  vermelho por injecao nos dois sentidos (sem _PRANCHAS vira sem_prancha,
  sem mapa vira sem_mapa, sem motivo vira faltando; dispatch ok None);
  fontes independentes + calculo intacto (membros 4/4/4/1, ATENDE).

**Baselines atualizadas com motivo escrito (nao e verde por edicao).**
G91 `_quadro_galpao` 34 -> 35 e `test_06` conta a mao + `mezanino` com
portao novo; G103 `BASELINE_G103` galpao isentas ["mezanino"] -> [] +
`test_03` caso bom/isencao-curacao e `test_04` com disciplina sem prancha
(ancoragem_orbital) + `test_05` portao da cura; G93 `PROMETIDOS_ESPERADOS`
34 -> 35 (+PE-MZ-01) e `DECLARADOS_SEM_EMISSOR` +PE-MZ-01; G112
`test_05` mapa 34 -> 35 (MZ01 sem carimbo cai em sem_carimbo_informativo,
fora_do_mapa/isentas intactos, sem tabela nova).

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.confere()`
— OK, OK, OK; `test_folhas_g77`, `test_alcancabilidade`,
`test_guardas_d86_g69`, `test_disciplina_prancha_g103`,
`test_indice_disco_g91`, `test_carimbo_mapa_g112`, `test_normas_catalogo`,
`test_galpao_indice_g93`, `test_suite_paralela_d164` + guarda novo G141 (5)
+ `test_mezanino`/`test_turnkey`/`test_caderno_turnkey`/`test_caderno_pesos_g108`/
`test_pacote_legal` + G138/G139/G140 + fronteira G101 + SVG G107 — verdes.

**G102 isolado com -s (2026-09-14, maquina livre).**
`casa=2.7s predio=8.0s galpao=618.7s total=629.5s`, 9 passed em 636,1 s;
`MEM_G102 casa=114.9MB predio=206.2MB galpao=1770.5MB
(proc=214.7,fc=1627.6,n=1)` (teto 2500). Nao re-congelado: variacao de
maquina sobre o G140 (2.6/7.9/619.9/630.4); o diff so acrescenta 1 pulada
nomeada quando ha mezanino (nenhum spec do repo declara), e o portao
passou no teto. Executivo de aco segue fora do G102
(`executivo_aco=False` fica).

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 303 arquivos
== coletados), duas corridas, `quebras` vazio nas duas.**
1. 20 min 52 s: **3 failed, 3861 passed, 1 skipped** — os 3 G21-C
   (C1/C2/C3, subprocesso com saida vazia no pipe); serial passam em
   6 s (9 passed), alheios ao diff (nenhum modulo tocado por eles foi
   tocado aqui). `quebras` vazio; memoria livre minima 362 MB.
2. Com `PYTHONUTF8=1` (cura do D169 para o spawn xdist no caminho com
   "Area"): **`rc_pytest` 0, 3864 passed, 1 skipped, 21 min 55 s,
   `quebras` vazio** (censo do FreeCAD fechado, `git status` igual,
   memoria livre minima 436 MB). O skip e o portao de auditoria do aco;
   +1 arquivo sobre os 302 do D169 (o guarda novo G141).

**Nao feito (do goal).** Mudar o calculo do mezanino (a adaptacao so le;
concreto bit a bit igual com e sem o vizinho); desenhar folha dedicada
de mezanino (sem emissor ligado, a ausencia sai declarada por codigo);
inventar geometria de mezanino num project-spec do repo (o spec de teste
mora em tmp_path, dito); prometer ART/O&M novos ao mezanino (segue na
responsabilidade do concreto).

## D171 - G142: PE-EL-03 da casa segue pulada - nada desenhável sem malha/SPDA, medição registrada (2026-09-14) - FECHADO

**Pedido.** Casa real com PE-EL-03 pulada ("sem emissor de
infraestrutura/aterramento; malha de aterramento e SPDA nao declarados
e sem folha emitida"). O predio emite com
`desenho_eletrico.infra_aterramento_edificio_svg` (`desenho_eletrico.py:439`),
chamado so por `edificio_adapter.py:1114`. Entregar a infra que o calculo
da casa produz, declarando malha/SPDA ausentes na folha - ou, se nada for
desenhável sem esses dados, manter a pulada e registrar a medicao. Sem
dimensionar SPDA/malha; predio byte-identico.

**Medido antes de mudar (2026-09-14, sem freecad, fontes vivas).**
1. O que a conta da casa produz (`residencial_eletrica.
run_residential_electrical`, fixture fase 6B): padrao de entrada B1
(disjuntor geral 50 A, ramal `10 (10)`, eletroduto ø50 mm, condutor de
aterramento do padrao 10 mm2), 3 circuitos dimensionados (secao/protecao
por NBR 5410) e layout validado (6 comodos, 3 pontos, quadro QD-01 em
x=8,0/y=7,0/z=1,6). Nao produz: `pavimentos_servidos`, `prumada`, rotas
de eletrodutos (`circuits.routes == []`, aceitas mas nunca geradas),
malha (solo/resistividade/arranjo/eletrodo) nem SPDA (NP/descidas) -
`malha/spda/resistividade/solo/eletrodo` ausentes do JSON inteiro.
2. O que o emissor do predio consome (o fonte, nunca o mapa):
`ele.pavimentos_servidos >= 1` (senao ValueError "nada a desenhar") e
`prumada.secao_mm2` no corte vertical do shaft com calhas por pavimento.
Com `{}` levanta; com shape minimo de predio (2 pavimentos, prumada
50 mm2) emite "PRUMADA 50 mm2". Casa terrea sem shaft/prumada nao tem o
que alimentar.
3. A infra parcial que existe ja e declarada onde e devida: o unifilar
residencial mostra ATERRAMENTO 10 mm2 + DPS + curto "nao avaliado", a
planta mostra o QD-01 e diz que a ligacao ponto-quadro NAO e tracado de
eletroduto. Desenhar eletroduto sem rota declarada, ou malha/SPDA sem
dado, seria invencao - a ausencia se declara, nunca default silencioso.
Conclusao: nada da folha e desenhável sem os dados. Segundo ramo do goal.

**Entregue (folha segue pulada, medicao registrada).**
- Nenhuma linha de producao mudada (casa, predio e emissores intactos;
o motivo atual ja nomeia codigo + malha + SPDA; o mapa ja tem
`PE-EL-03 -> eletrica-infra-aterramento-casa.svg`).
- Novo `tests/test_infra_aterramento_casa_g142.py` (5): test_01 remeça a
conta contra o emissor (fonte viva dos dois lados); test_02 motivo vivo
+ lente fecha com a pulada nomeada; test_03 substring -> parse ->
guarda -> PNG nas 3 folhas emitidas (sem `malha de aterramento`,
`SPDA NP` ou `PRUMADA` inventados); test_04 vermelho por injecao nos
dois sentidos (emissor morto, sem motivo vira faltando, sem mapa vira
sem_mapa, tudo em tmp_path); test_05 predio byte-identico (casa nunca
chama o emissor do predio; emissor deterministico; nada dimensiona).

**Tres aceites olhando o PNG (fixture fase 6B, 2026-09-14,
`Temp/opencode/g142_png/`, `svg_para_png` via fitz).**
- unifilar.svg (7572 bytes -> PNG 64775): DIAGRAMA UNIFILAR - INSTALACAO
RESIDENCIAL, ENTRADA BT, padrao B1, DISJ. GERAL 50 A, QD - QUADRO DE
DISTRIBUICAO, ATERRAMENTO 10 mm2 do calculo; sem malha/SPDA/PRUMADA.
(1) esta certa: numeros do calculo, parse + guarda ok; (2) sai no
manifesto: `drawings/unifilar.svg` no disco e nos artifacts; (3) diz o
que desenha: unifilar + quadro de distribuicao, sem prometer infra.
- planta-eletrica.svg (10234 -> PNG 119193): PLANTA DE ILUMINACAO E
TOMADAS, comodos + QD-01 + legenda + "NAO e tracado de eletroduto".
(1)/(2)/(3) como acima: posicoes do layout validado, no manifesto e no
disco, sem tracar eletroduto inexistente.
- quadro-cargas.svg (7117 -> PNG 58913): QUADRO DE CARGAS com os 3
circuitos, secao/protecao e rodape do padrao; sem dimensionar malha/SPDA.
A PE-EL-03 segue em `skipped` com malha e SPDA nomeados - o dado que
falta, com nome, nunca "nao disponivel" sozinho.

**Baselines atualizadas: nenhuma (nao e verde por edicao).** Sem mudar
producao, G92/G99/G91/G112/G93/G103 seguem verdes como estao; o guarda
novo congela o segundo ramo (se um dia o calculo declarar rotas/malha/
SPDA, o test_01 acusa a mudanca de forma e o goal se reabre por dado,
nao por defeito).

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.
confere()` - OK, OK, OK; `test_folhas_g77`, `test_alcancabilidade`,
`test_guardas_d86_g69` (111 passed); `test_disciplina_prancha_g103`,
`test_indice_disco_g91`, `test_carimbo_mapa_g112`,
`test_normas_catalogo`, `test_galpao_indice_g93`,
`test_suite_paralela_d164` (31 passed); portoes das fontes tocadas
`test_casa_eletrica_g99`, `test_casa_indice_g92`,
`test_edificio_pranchas_g56` (29 passed); guarda novo G142 (5 passed).
G102 isolado nao se aplica (goal sem folha de galpao; regra do lote) e
nada foi re-congelado.

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 304 arquivos
== coletados): `rc_pytest` 0, 3869 passed, 1 skipped, 34 min 42 s,
`quebras` vazio** (censo do FreeCAD fechado, memoria livre minima
159 MB). O skip e o portao de auditoria do aco. +1 arquivo e +5 testes
sobre os 303/3864 do D170 (o guarda novo G142); 3864 + 5 = 3869 bate.

**Nao feito (do goal).** Dimensionar SPDA ou malha sem dado declarado
(a adaptacao nem existe: nada le `rho/A/L` ou `NP/descidas`); mexer no
caminho do predio (`edificio_adapter`/`desenho_eletrico` intactos);
emitir folha inventada (eletroduto sem rota, malha/SPDA sem solo/norma).

## D172 - auditoria do lote G137-G142: o hidrante que o `or 1` desenhava e a folha que derrubava a disciplina (2026-09-14) - FECHADO

**Pedido.** Auditar por medicao o lote G137-G142 (commit `f22dfe9`) e
tirar do shell o `PYTHONUTF8=1` de que a suite dependia (D169/D170).

**Medido (arvore `f22dfe9`, fontes vivas, leitura do diff inteiro do lote).**
1. **Hidrante inventado na PE-IN-02 do galpao (G138).**
`desenho_incendio.detalhes_hidrantes_rotas_svg(..., nivel_unico=True)`
herdava do predio `n = int(N_hidrantes or 0) or 1` e
`"RESERVA DE INCENDIO %.1f m3" % (reserva or 0)`. Com hidrantes nao
calculados (spec sem `hidrantes`, gate informativo) a folha desenhava
**1 simbolo "HID-1 (terreo)"**, escrevia "1 hidrante(s)" e "RESERVA DE
INCENDIO 0.0 m3" - ao lado da caixa que dizia "hidrantes nao calculados".
Com N=0 tambem 1 simbolo; N=3 dava 3 (o G138 so testou o caso com N).
Saturacao silenciosa: numero inventado na folha.
2. **A folha que caia derrubava a disciplina.** Na rota SVG (a de producao
do incendio, G104) `techdraw_incendio.config_de_spec` passou a chamar o
emissor de detalhes sem try, e `galpao_seguranca_incendio.montar_pranchas`
devolvia `{"erro"}` em qualquer excecao da INC03: INC01/INC02 saiam do
status e a disciplina virava `failed_disciplines`. O
`test_hidrantes_g138.test_04` congelava esse `erro` como esperado.
3. **A causa nunca chegava ao motivo.** `locacao_erro` (PE04, G140) era
gravado no status do concreto e ninguem lia; a pulada da PE-CO-04 saia
com o motivo generico.
4. **Default morto no carimbo da PE04 de reserva (G140).**
`int((r.get("spec") or {}).get("fck_MPa", 30))`; medido: o carimbo da
rota pura nao imprime o material (texto da pagina sem C30/C35), entao o
30 nunca chegou a folha - cosmetico, trocado por leitura direta como a
conta faz (`r["spec"]["fck_MPa"]`).
5. **`PYTHONUTF8` fora do runner.** Os 3 G21-C so fechavam verdes com a
variavel posta a mao no shell (D169/D170).
Sem achado nos demais pontos lidos: a tensao default 200 kN/m2 da
locacao (G140) e anterior ao lote e sai declarada na folha
(`AUSENCIAS_GALPAO_LOCACAO[1]`); G141/G142 nao mudaram producao.

**Entregue.**
- `desenho_incendio`: com `nivel_unico` e N ausente/0, nenhum simbolo e a
folha diz "hidrantes nao calculados: nenhum simbolo" / "0 hidrantes no
calculo: nenhum simbolo"; reserva ausente sai "nao calculada". Caminho do
predio byte-identico (`test_hidrantes_g138.test_02`).
- `techdraw_incendio.config_de_spec`: detalhes em try, `detalhes_erro` no
cfg; `_pr_detalhes` recusa nomeado sem SVG.
- `galpao_seguranca_incendio.montar_pranchas` (rota SVG): a INC03 que cai
grava `detalhes_erro` e devolve INC01/INC02.
- `galpao_adapter._causas_folhas_galpao(statuses)` + `causas=` no
`_conferir_indice_galpao` + `causa_erro=` no motivo: a causa medida
(`locacao_erro`/`detalhes_erro`) sai no motivo da pulada; sem ela, nada.
- `galpao_concreto.gerar_prancha_locacao`: `fck_MPa` sem default.
- `tools/suite_paralela.ambiente_suite`: `PYTHONUTF8=1` no ambiente do
pytest (sobrepoe um 0 herdado); `test_suite_paralela_d164.test_05`.
- Novo `tests/test_auditoria_g137_g142_d172.py` (4): hidrantes um por um
com vermelho por injecao numa copia do fonte com a guarda desligada;
INC03 caida sem derrubar INC01/INC02 + causa no motivo (e nenhuma causa
inventada sem ela); leitura das causas nos status; PE04 recusa sem fck.

**Baseline mudada com motivo.** `test_hidrantes_g138.test_04`: esperava
`erro` na disciplina com o emissor morto (o defeito 2); agora espera
`detalhes_erro` nomeado sem `erro`.

**Vermelho no codigo antigo.** Worktree de `f22dfe9` no scratchpad (repo
intocado) com o guarda D172 copiado: **4 failed** - "sem hidrantes: 1
simbolo(s) HID desenhado(s), calculo da 0", "reserva 0.0 m3 inventada",
"N=0: 1 simbolo(s)", INC03 derrubando a disciplina, causas ausentes,
"sem fck_MPa ... carimbou um default". Na arvore consertada: 4 passed.

**Portoes.** D172 + G138/G140/G107/G93/G91/G112/G103/G104/incendio/
techdraw_concreto/G77/alcancabilidade/guardas/D164/G141/G139/G137/G142:
**214 passed em 107 s.**

**Suite inteira pelo runner, antes dos consertos e sem `PYTHONUTF8` no
shell (so o runner com a variavel):** `rc_pytest` 0, 3870 passed,
1 skipped, 20 min 33 s, `quebras` vazio, memoria livre minima 308 MB
(304 arquivos == coletados; +1 teste: o `test_05`). Os 3 G21-C verdes sem
a variavel no shell.

**Suite inteira pelo runner, com os consertos (305 arquivos == coletados):
`rc_pytest` 0, 3874 passed, 1 skipped, 20 min 25 s, `quebras` vazio**
(censo do FreeCAD fechado, memoria livre minima 416 MB). 3870 + 4 (o
guarda D172) = 3874 bate; o skip e o portao de auditoria do aco.

**Serial de referencia (`pytest tests`, sem runner, BLAS no padrao - o
numero bit a bit): `rc` 0, 3874 passed, 1 skipped, 1 h 06 min 57 s** -
o mesmo total do runner, nenhum veredito depende do BLAS. Mais lenta que
os 35 min do D165 por memoria da maquina (1,1-1,6 GB livres com os
aplicativos do usuario abertos); a 1a tentativa foi morta pelo harness
por memoria baixa em 24 % e relancada destacada, sem sobra de processo.

**Portao de auditoria do aco (`GALPAO_AUDITORIA=1 pytest
tests/test_executivo_aco_completo_d165.py`, serial): 2 passed em
1937,2 s**, `CUSTO_D165 executivo_aco_completo=1936.1s` (1067,3 s no
D166; mesma causa da serial - freecad.exe vivo com 1136 s de CPU e 648 MB
livres na maquina, nao travado).

**Nao feito.** Mudar o calculo de hidrantes ou o predio; dar piso de
memoria ao runner (so registra o minimo; nao existe teto declarado).

## D173 - G146: PE-MZ-01, a folha do mezanino calculado (formas + armacao via primitivas do predio) (2026-09-15) - FECHADO

**Pedido.** `framework/galpao_fw/BACKLOG-GOALS-G143-G148.md` G146: a folha
PE-MZ-01 do mezanino calculado, adaptada do resultado de
`galpao_mezanino.rodar` para as primitivas do predio
(`desenho_pavimento`), com ausencias declaradas e cada viga, pilar e
sapata desenhados um por um. Comecar medindo a diferenca de forma no
test_01, aplicar a convencao 13 (dado ausente, zero, falha so na folha
nova), seguir as convencoes 1-13 e a regra do lote, rodar o G102 isolado
e a suite pelo runner ate `rc_pytest` 0 e `quebras` vazio, escrever o
verbete e fazer o commit.

**Medido (antes de mudar, fontes vivas).**
- `galpao_mezanino.rodar` (`:305-319`) devolve `laje` (com `armaduras`),
  `viga_X`/`viga_Y` simples, `pilar` unico, `sapatas[4]` com `aprovado` e
  a posicao x0/y0/Lx/Ly/h — sem `vaos_x`/`vaos_y`/`paineis`/`por_pilar`,
  sem `por_linha`/`tramos` e sem `lances`, que e o que
  `planta_formas_svg` (`desenho_pavimento.py:57`) e
  `prancha_armacao_vigas_pilares_svg` (`:797`) leem no shape do predio
  (`pavimento_tipo.monta`: `vaos_x`, `vaos_y`, `area_m2`,
  `paineis[i,j,lx,ly,caso]`, `pilares`). Remeça no
  `tests/test_mezanino_folha_g146.test_01`.
- D170/G141: com mezanino executado a PE-MZ-01 era prometida e saia
  pulada ("sem emissor ligado"); o arquivo `MZ01_MEZANINO.pdf` ja estava
  mapeado (`_PRANCHA_ARQUIVO_GALPAO["PE-MZ-01"]`).
- Rota sem freecad.exe: as primitivas sao SVG puro-Python (mesma via da
  INC03 no G138 e da PE04 no G140) — medida, a folha sai sem executavel.

**Entregue.**
- `desenho_pavimento.adaptar_galpao_mezanino(r)`: (pav, vigas_verificacao,
  pilares, sapatas, ausentes) lidos do calculo, sem redimensionar — 1
  painel Lx x Ly, 4 pilares M-P1..M-P4 nos cantos com o Nk calculado, 4
  linhas de viga de 1 tramo (M-VX1/M-VX2 do `viga_X`, M-VY1/M-VY2 do
  `viga_Y`), 4 lances unicos do `pilar`, 4 sapatas com B/L/h do
  `aprovado`; `ausentes` = `AUSENCIAS_GALPAO_MEZANINO` (engastamento entre
  paineis, M- de envoltorias, locacao x0/y0 no envelope) + armadura da
  laje quando o calculo nao a produz. Sem sapata aprovada levanta
  ValueError nomeando a PE-MZ-01 (nunca folha vazia); nao muta o
  resultado.
- `planta_formas_svg(..., ausencias=None)`: default = caminho do
  predio/casa byte-identico; com a lista desenha a mesma planta e declara
  a caixa vermelha na faixa extra (malha e legenda nao se movem). A
  combinada de armacao segue intocada (M- 0.0 e calculado de viga simples;
  arranjo do pilar sem bitola ja diz NAO DETALHADO).
- `techdraw_mezanino.py` (novo): `config_de_spec` (adapta em `try`
  proprio, `mezanino_erro`; fck lido da conta, sem default - D172),
  carimbo MZ-01 (material/norma/departamento de concreto), pagina
  `MZ01_MEZANINO`, executivo + bootstrap para o backend manual.
- `galpao_mezanino.gerar_prancha_mezanino` (PDF A1 puro de 3 paginas:
  formas, armacao, quadro de sapatas/laje) + `montar_pranchas`
  (backend svg default; a MZ01 que cai fica em `mezanino_erro` com
  `ok: False`, sem derrubar as demais).
- Ligacao: motivo da PE-MZ-01 reescrito (emite via desenho_pavimento
  adaptado, G146), `mezanino_erro` em `_causas_folhas_galpao`, dispatch do
  mezanino no caderno emitindo (aposenta o `MOTIVO_MEZANINO_SEM_PRANCHA`
  do G141), correspondencia G112 com a entrada MZ01/MZ-01 cobrindo
  PE-MZ-01 (25 entradas; carimbo distinto do codigo, mesma regra do aco).
- Novo `tests/test_mezanino_folha_g146.py` (5): diferenca de forma,
  predio byte-identico + 1-por-1 com guardas, rota emitindo MZ01 de 3
  paginas que rasteriza, convencao 13, tres aceites.

**Convencao 13 (um por um).** Sapatas sem a chave e com `aprovado` None:
erro nomeado (nunca folha vazia). Laje com `armaduras` None e `{}`:
declara "armadura nao dimensionada nesta rodada" no quadro (nunca numero;
`0.00 cm2/m` acusado se aparecer). `q_uso=0` calculado sai com q 0.00 (o
numero do calculo, nao inventado). Emissor morto por monkeypatch: a MZ01
cai com a causa e a PE-CO-04 segue no disco (1 pulada so); sem causa, o
motivo nao inventa "causa proxima" (mesma forma do D172).

**Tres aceites, olhando o PNG (amostra 6x5 a 3 m, q=2).** (1) Esta certa:
formas com M-P1..M-P4, L11, Nk 68.2 e a caixa de ausencias; armacao com
M-VX1/M-VX2/M-VY1/M-VY2, M-P1..M-P4, secao 30x30 e OK; quadro com M-SAP1..
M-SAP4 120x120x35 e LAJE m-x/m-y — PNGs de 98 kB e 166 kB, nao em branco,
guardas `confere_folha_svg`/`confere_armacao_*` verdes. (2) Sai no
manifesto: mapa 1:1 `PE-MZ-01 -> MZ01_MEZANINO.pdf`, dispatch emite e o
laco fecha com o PDF no disco. (3) Diz o que desenha: indice "Mezanino de
concreto (laje/vigas/pilares)", carimbo MZ-01, cobertura escrita na
tabela G112.

**Baseline mudada com motivo.** `test_mezanino_indice_g141.test_04`:
dispatch `ok None` (o defeito do G141: ausencia declarada) agora emite a
MZ01 e sem calculo cai nomeado. `DECLARADOS_SEM_EMISSOR` -PE-MZ-01 (so
PE-IN-03); `_paginas_techdraw` +techdraw_mezanino;
`BASELINE_G112.fora_do_mapa` +MZ01/MZ-01 e isentas 24->25; tabela G112
24->25; `SEM_FAIXA_DECLARADA` +techdraw_mezanino; G102 re-congelado
abaixo. Predio e casa byte-identicos (formas default e combinada
intocadas).

**Vermelho no codigo antigo.** Sem o adaptar, `test_01` acusa a diferenca
de forma (`por_linha`/`lances`/`vaos_x` ausentes no resultado); com o
emissor morto, `test_04` acusa a MZ01 caida com a causa; sem a entrada no
mapa vira `sem_mapa` e sem motivo vira `faltando` (test_05 nos dois
sentidos).

**Portoes.** G146 (5) + G141 (5) + G93/G91/G103/G112 + lote rapido
(faixa/asserts/orfas/fallback verdes; folhas/alcancabilidade/guardas/
normas/D164/D172: 123 passed) + vizinhos (mezanino/interferencia/
techdraw_concreto/fallback/estaca/edificio: 64 passed; caderno/
coordenacao/incendio/orfas/faixa: 56 passed).

**G102 isolado (`-s`): 9 passed em 730,5 s** (casa 2,7 s, predio 14,7 s,
galpao 706,6 s; MEM 107,9/207,4/1679,0 MB, 1 freecad). Re-congelado com o
medido (G146, 2026-09-15): predio +6,0 s e variacao de maquina, nao do
diff (a rota do predio passa pela primitiva com `ausencias=None`,
byte-identica); o galpao-tp-g95 nao tem mezanino, a MZ01 SVG nao sobe
freecad.

**Suite inteira pelo runner:** `rc_pytest` 0, **3904 passed, 1 skipped,
1504,9 s (309 arquivos == coletados), `quebras` vazio**, memoria livre
minima 460 MB (o skip e o portao de auditoria do aco).

**Nao feito.** Mudar o calculo do mezanino; por mezanino num
`projects/*/project-spec.json` (o spec de teste mora em tmp_path);
paralelizar pranchas; backend freecad da MZ01 alem da pagina (a rota de
producao e a SVG pura, medida).

## D174 - G147: o prazo do executivo de aco numa maquina carregada e os pesos de concreto e eletrico medidos (2026-09-15) - FECHADO

**Pedido.** `framework/galpao_fw/BACKLOG-GOALS-G143-G148.md` G147: o prazo
do executivo de aco numa maquina carregada (1067 s livre, 1937 s com
648 MB livres) e os pesos de concreto e eletrico sem medicao em
`caderno_turnkey.py`. Cronometrar os dois, rodar a producao do galpao com
`executivo_aco=True` com maquina livre e em uso normal, decidir o prazo so
com numeros, seguir as convencoes 1-13 e a regra do lote, rodar a suite
pelo runner ate `rc_pytest` 0 e `quebras` vazio, escrever o verbete e fazer
o commit. Nao fechar aplicativos do usuario.

**Medido (antes de mudar, fontes vivas).**
- `caderno_turnkey._STAGE_WEIGHTS`: concreto 2,0 e eletrico 1,5 literais
  "SEM MEDICAO" (G108), producao lendo sem cronometro (convencao 8
  violada no estado inicial).
- Portao do aco: 1038,9 s (D165), 1067,3 s (D166), 1937,2 s (D172, 648 MB
  livres; freecad.exe vivo com 1136 s de CPU — nao travado).
- Producao: `ProjectLoopOptions.timeout_seconds` = 2100, repartido por peso
  (aco 787,7 s + 3D 210 s, medidos com maquina livre).

**Cronometro G147 (mesmo protocolo do G139: processo reiniciado por
amostra, dispatch vivo 3D+pranchas, ok=True, 4 PDFs cada, galpao-tp-g95,
freecad.exe nesta maquina, aplicativos do usuario abertos).**
- concreto: 61,1 + 58,6 + 60,8 s -> MAXIMO 61,1 s -> peso 0,74;
- eletrico: 108,4 + 104,3 + 110,5 s -> MAXIMO 110,5 s -> peso 1,3382
  (regra `peso_medido`, ancora 578 s; maximos — a media estouraria por
  construcao, licao do G139).
- PNGs olhados (substring -> parse -> renderizar): concreto PE01 101725,
  PE02 101228, PE03 119515, PE04 276017 bytes; eletrico PE01 160886, PE02
  648365, PE03 133113, PE04 139811 bytes — nenhum em branco, 4 PDFs cada.

**Producao do galpao (`projects/galpao-tp-g95`, generate_ifc False,
generate_2d True, `executivo_aco=True`, timeout 2100, aplicativos abertos).**

| rodada | elapsed | caderno | pico | mem livre | status |
|---|---|---|---|---|---|
| livre | 1380,5 s | 1364,3 s | 2041,8 MB (proc 197,2 + fc 1948,9, n=1) | ~2500 MB antes | generated, timed_out False, 0 estouros |
| uso normal | 1733,4 s | 1716,4 s | 2019,2 MB (proc 161,5 + fc 1926,5, n=1) | min 260 MB | generated, timed_out False, 0 estouros |

**Decisao so com numeros.** 2100 cobre o livre com folga 719,5 s (52 %) e
o uso normal com folga 366,6 s (21 %); o carregado do D172 (aco sozinho
1937 s com 648 MB) cabe no mesmo teto quando somado ao resto medido sem aco
(536,3 s no D165) so no limite — a producao cheia medida aqui (1733 s com
260 MB livres) passa sem timeout. Prazo 2100 MANTIDO com a frequencia
medida (2/2 generated); nenhum palpite, nenhum numero novo arbitrado.

**Entregue.**
- `_T_MEDIDO_SEG["concreto"]=61,1` e `["eletrico"]=110,5` com a origem
  escrita; `_STAGE_WEIGHTS` deriva via `peso_medido` — nenhum "SEM MEDICAO"
  restante no fonte.
- `tests/test_caderno_pesos_g147.py` (4): prazo deriva do medido (sem
  literais 2,0/1,5); vermelho por injecao nos dois sentidos (literais
  antigos mudam a fracao do aco para 0,8610; constante nao medida lida pelo
  prazo acusa por parte); G102 intacto (`executivo_aco=False` fica);
  reserva usa os medidos (fracao do aco 0,8738; concreto < eletrico < aco).
- `tests/test_caderno_pesos_g108.py`: fracao do aco 0,8610 -> 0,8738
  (eletrico 1,5 -> 1,3382); test_02 fixa o eletrico/concreto antigos para
  reproduzir o regime; test_03 cobra o medido (G147) em vez da ausencia.

**Baselines mudadas com motivo (nao e verde por edicao).**
G108 `FRACAO_ACO_ESPERADA` 0,8610 -> 0,8738 (10,9178 = 9,5396 + 1,3382 +
0,01 x 4); injecao antiga fixa eletrico 1,5/concreto 2,0; ancora passa a
cobrar concreto/eletrico derivados. G102 NAO re-congelado (goal sem folha
de galpao; regra do lote): casa 3,1 / predio 11,5 / galpao 797,1 s (+90,5 s
no galpao e -3,2 s no predio sobre o G146: variacao de maquina com 260 MB
livres, nao do diff — o diff so troca a reserva, nao a geometria; o teste
cobra o teto, nao o numero exato).

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.
confere()` — OK, OK, OK; `test_folhas_g77`, `test_alcancabilidade`,
`test_guardas_d86_g69`, `test_disciplina_prancha_g103`,
`test_indice_disco_g91`, `test_carimbo_mapa_g112`,
`test_normas_catalogo`, `test_galpao_indice_g93`,
`test_suite_paralela_d164` + `test_auditoria_g137_g142_d172` (214 passed
no D172) + `test_caderno_pesos_g108` + `test_caderno_pesos_g147` (4) +
`test_coordenacao_g139` — 159 passed em 126,8 s.

**G102 isolado com -s (2026-09-15, aplicativos abertos).**
`casa=3,1s predio=11,5s galpao=797,1s total=811,7s`, 9 passed em 824,0 s;
`MEM_G102 casa=136,5MB predio=206,6MB galpao=1998,8MB
(proc=208,5,fc=1856,1,n=1)` (teto 2500). Executivo de aco segue fora do
G102 (`executivo_aco=False` fica).

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 310 arquivos
== coletados): `rc_pytest` 0, 3904 + 4 = 3908 passed, 1 skipped, 1735,1 s,
`quebras` vazio** (censo do FreeCAD fechado, memoria livre minima
258 MB). O skip e o portao de auditoria do aco. +1 arquivo e +4 testes
sobre os 309/3904 do G146 (o guarda novo G147).

**Nao feito (do goal).** Paralelizar pranchas dentro do freecad.exe;
fechar aplicativos do usuario para medir; mover o G102-galpao para a
auditoria (parte do G148, com decisao do usuario); dar piso de memoria ao
runner (so registra o minimo).

## D175 - G148 parte 1: piso de memoria livre no runner (200 MB derivados do medido) - FECHADO

**Pedido.** `framework/galpao_fw/BACKLOG-GOALS-G143-G148.md` G148 parte 1:
piso de memoria livre em `tools/suite_paralela.py` derivado do medido, que
grava os testes de cada worker e sai como quebra nomeada sem matar processo
do usuario, com vermelho por injecao. Medir quanto a suite ganharia sem o
galpao do G102 e so relatar (nao mover cobertura). Seguir as convencoes 1-13
e a regra do lote, rodar a suite pelo runner ate `rc_pytest` 0 e `quebras`
vazio, escrever o verbete e fazer o commit. Parte 2 (tirar o galpao do G102
da suite do goal) com decisao do usuario: nao executada.

**Medido (antes de mudar, fontes vivas, aplicativos do usuario abertos).**
- O runner so REGISTRAVA `memoria_livre_min_mb`; sem piso: 159 MB (G142),
  308/416 MB (D172), 460 MB (G146), 258 MB (G147). A serial de referencia foi
  morta pelo harness por memoria baixa em 24 % (D172; a relancada passou com
  1,1-1,6 GB livres) - 159 MB ja e zona de morte, nao folga.
- Pico do G102-galpao: 1679,0 MB no congelado (G146: proc 207,1 + fc 1535,4,
  teto 2500), maximo historico 2111,3 MB (G139: fc 1968,4); producao cheia
  G147 2019-2041 MB; freecad.exe sozinho 1535-1968 MB numa maquina de 8 GB
  (SO + fundo ~2 GB). Livre antes da suite deste goal: ~843 MB.

**Entregue.**
- `PISO_MEMORIA_LIVRE_MB = 200` em `tools/suite_paralela.py` (fonte unica, com
  o numero e o motivo escritos): acima da zona onde a morte ja ocorreu (159),
  abaixo das minimas normais (258+), com folga para o amostrador de 5 s
  abortar antes de o harness matar.
- `veredito_piso_memoria(livre, piso)` pura: abaixo acusa nomeando piso +
  livre + goal + garantia; no piso/acima passa; None declara (nunca gap).
- `testes_por_worker(censo_dir)`: o que o censo ja sabe
  (coletados-<worker>.json + freecad-<worker>.jsonl) agrupado por worker;
  vazio declara `{}`.
- `main()` com amostrador injetavel (`_amostra_fn`, `_piso_mb`,
  `_intervalo_s`; default le a maquina e o piso da producao): cruzado o piso,
  termina SO o proprio filho pytest (`Popen` + `terminate`, nunca taskkill) e
  o resumo sai com a quebra nomeada + `testes_por_worker` + `minimo` do falso
  + `piso_memoria_livre_mb` (opcao declarada, nunca silenciosa).
- Novo `tests/test_piso_memoria_g148.py` (4): piso 200 com a derivacao escrita
  e lido pela producao por default (convencao 8); veredito nos dois sentidos
  (ausente/zero/presente, piso custom); snapshot agrupa o censo e vazio
  declara; integracao com amostrador falso - brecha vira quebra nomeada com o
  minimo do falso e o processo "do usuario" segue vivo, folga fecha
  `rc` 0 e `quebras` vazio. Tudo em `tmp_path`; nenhum teste novo sobe
  freecad (fora do `GRUPO_FREECAD`).

**Baselines mudadas com motivo: nenhuma** (nao e verde por edicao). O resumo
ganha dois campos (`piso_memoria_livre_mb` sempre, `testes_por_worker` na
brecha); `threading` sai dos imports (a vigia virou o laco do `Popen`).

**Lista nominal do lote, lida inteira (convencao 10).**
`varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.
confere()` - OK, OK, OK; `test_folhas_g77`, `test_alcancabilidade`,
`test_guardas_d86_g69`, `test_disciplina_prancha_g103`,
`test_indice_disco_g91`, `test_carimbo_mapa_g112`, `test_normas_catalogo`,
`test_galpao_indice_g93`, `test_suite_paralela_d164`,
`test_auditoria_g137_g142_d172` + guarda novo G148 - 151 passed em 89,3 s.
G102 isolado nao se aplica (goal sem folha de galpao; regra do lote).

**Ganho sem o galpao do G102 (medido, so relatado; cobertura NAO movida).**
`test_01` nesta suite: 769,8 s; casa + predio remedidos aqui (mesma maquina,
aplicativos abertos): 3,4 + 14,2 = 17,6 s. Parte do galpao ~= 752 s
(~12,5 min, ~98 % do G102). Sem ela a suite de 1605 s cairia para ~853 s
(~14 min): ganho ~= 750 s (~47 %). Casa e predio ficam; a decisao da parte 2
e do usuario.

**Suite inteira pelo runner (`tools/suite_paralela.py -n 3`, 311 arquivos
== coletados): `rc_pytest` 0, 3908 + 4 = 3912 passed, 1 skipped, 1605,1 s,
`quebras` vazio** (censo do FreeCAD fechado, memoria livre minima 270 MB >
piso 200 - sem falso disparo; `piso_memoria_livre_mb` 200 no resumo). O skip
e o portao de auditoria do aco. +1 arquivo e +4 testes sobre os 310/3908 do
G147 (o guarda novo G148); 3908 + 4 = 3912 bate.

**Nao feito (do goal).** Tirar o galpao do G102 da suite do goal (parte 2,
com decisao do usuario); baixar `-n` sem medir; fechar aplicativos do
usuario para medir.

## D176 - auditoria do lote G143-G148: o worker que sobrevivia ao piso, a viga com duas marcas e os tres goals sem verbete (2026-09-15) - FECHADO

**Pedido.** "backlog executado, agora e a sua vez": auditar por medicao o lote
G143-G148 (`14ece99`..`9f112ce`), corrigir, rodar a suite inteira e ler o
resumo, commitar e escrever o proximo backlog.

**Medido (fontes vivas, antes de mudar).**
- **G148 - o piso terminava so o pai.** Sonda com o proprio `main` do runner,
  amostrador falso que seca quando os workers ja rodam um teste de 60 s
  (`-n 2`): no aborto havia 6 processos novos (launcher do venv 2920 ->
  pytest 14960 -> 2 workers xdist, cada um launcher + python); depois do
  `terminate` o pai sumiu e **4 processos dos workers seguiam vivos no
  instante 0 e 10 s depois**; so aos ~40 s sairam, quando o `sleep` do teste
  acabou. Num teste do `GRUPO_FREECAD` (G102-galpao ~700 s, freecad.exe
  1535-1968 MB) o "aborto" deixaria o freecad segurando justamente a memoria
  que o piso queria liberar. O `test_04` do G148 nao pegava: recorte rapido
  em `-n 1` que acaba antes do terminate.
- **G146 - a folha com duas marcas para a mesma viga.** Render da MZ01 (3
  paginas, PNG olhado): a planta de formas marcava `VX0/VX1/VY0/VY1` (rotulo
  fixo do predio, `desenho_pavimento.py:135,140`) e a armacao + o BIM marcavam
  `M-VX1/M-VX2/M-VY1/M-VY2` (`galpao_mezanino.membros_bim:431,444`). Os testes
  do G146 conferiam `M-VX1` so na armacao.
- **G146 - titulo cortado.** "MEZANINO DE CONCRETO - FORMAS E ARMACAO" (39)
  passa por `techdraw_exec._cap_titulo` (26) e sai "MEZANINO DE CONCRETO -
  FO…" no rodape das 3 paginas. Mesma classe em mais **22** titulos de
  carimbo de outros emissores (AST de todas as chamadas `_carimbo*` com
  literal): 23 cortados no total - anterior ao lote, vai para o backlog.
- **G143, G144 e G145 sem verbete.** O `04-decisions` do lote tem D173
  (G146), D174 (G147) e D175 (G148); os tres primeiros goals so tinham uma
  linha no `03-phases` e o commit de uma linha. O verbete e parte da entrega.
- **Conferido e sem defeito:** a recusa do G143 dentro do turnkey chega
  isolada com erro nomeado (`galpao_turnkey.py:181-183`); os 3
  `project-spec.json` do repo tem `"estaca": null` (nenhum dependia do
  default); o gate do G144 reprova com motivo e o relatorio declara; a MZ01
  com mezanino reprovado marca REPROVA por viga na armacao; `fyk` e `hx/hy`
  existem no resultado do mezanino (os `.get(..., 500e3)`/`0.0` do adaptador
  estao mortos hoje); "18.3 (viga)" no limite governante do pilar e o rotulo
  do `pilar_concreto` (D84), nao defeito; as NBR citadas nas linhas novas do
  lote (13714, 6118, 6122, 8800) estao no catalogo.

**Corrigido.**
- `tools/suite_paralela.py`: `arvore_descendentes(pares, raiz)` pura (so quem
  descende do proprio filho; ciclo de ppid nao trava), `_pares_processos()`
  (CIM), `processo_vivo(pid)` (OpenProcess + GetExitCodeProcess) e
  `terminar_arvore(proc)`: snapshot da arvore ANTES do terminate, taskkill /F
  por PID de cada descendente vivo, WMI Terminate para quem resistir. O resumo
  ganha `descendentes_terminados` e `descendentes_sobreviventes`; sobrevivente
  vira quebra nomeada. O texto do veredito diz "so a arvore do proprio filho
  pytest".
- `desenho_pavimento.planta_formas_svg(..., rotulo_viga=None)`: None mantem
  `VX%d/VY%d` do predio; `rotulo_viga_mezanino(eixo, k)` = `M-V<eixo><k+1>`
  (mesma ordem do `membros_bim`), passado pelo `techdraw_mezanino.config_de_spec`.
- `techdraw_mezanino.TITULO_CARIMBO_MZ01 = "MEZANINO - FORMAS/ARMACAO"` (25),
  fonte unica da rota SVG e do TechDraw.
- Novo `tests/test_auditoria_g143_g148_d176.py` (4): marcas de viga iguais
  nas formas, na armacao e no BIM (a regua acusa sem o rotulo e o predio
  segue `VX0`); todo `_carimbo_mz` com titulo que `_cap_titulo` nao corta e
  PDF sem reticencia; arvore pura (usuario fora, snapshot vazio declara);
  aborto real com amostrador falso que seca quando o teste lento grava o PID
  do worker - o worker nao pode estar vivo 10 s depois e o resumo tem de
  nomea-lo. **Vermelho provado no `9f112ce` (worktree): 4 failed** (formas
  `VX0..` != BIM `M-VX1..`; 2 titulos cortados; sem `arvore_descendentes`;
  worker 14504 vivo 10 s depois e resumo sem o nome).

**Os tres verbetes que faltaram (resumo medido dos fontes do proprio goal).**
- **G143 (`14ece99`)** - sem `D_estaca`/`L_estaca` a conta usava 0,30/8,0
  calados (`galpao_concreto.py:351`) e a PE-CO-04 desenhava "D30 L8". Medido:
  L 8->10 util 0,116->0,103; D 0,30->0,40 util 0,116->0,071; L=0 n 1->5 em
  silencio; D=0 TypeError cru; pre_moldada->escavada util 0,116->0,198 e, no
  perfil fraco com Q_roof 0,25/L 6, pre_moldada ATENDE (n=2) e escavada
  REPROVA (n=4) - o tipo inverte o veredito. cota_apoio/B_max decidem o tipo
  no auto (B_max 0,5->estaca, >=1,0->sapata); mu/sigma nao entram na estaca.
  Entregue (D102): D/L/tipo recusam nomeados; cota/B_max/mu/sigma com a origem
  dita no resultado (`fundacao_parametros`), memorial, PE-CO-04 e sinais
  `assumed_default` (`estaca_parametros_g143.py`, fonte unica). Wizard alimenta
  o metalico, nao o concreto: terceiro valor declarado. Fora: `wizard.py:321-323`
  e `fundacao_edificio.py:403-405` seguem com default (backlog).
- **G144 (`2a2dd3c`)** - `galpao_mezanino.py:321-329` com `except Exception:
  pass`: checagem de interferencia levantando devolvia ATENDE True, reprovados
  [] e `interferencia` None. Entregue: gate `{"OK": False, "erro", "motivo":
  "interferencia_nao_verificada"}`, "interferencia" em reprovados, ATENDE
  False, relatorio "NAO VERIFICADA (...) -> REVISAR". Varridos os outros
  `except` do caminho (bridge->headless, isolamento do turnkey, emitir_bim):
  todos declaram, nenhum apaga gate.
- **G145 (`88c0b33`)** - o grep contava 47 linhas; o AST achou 50 ocorrencias
  `or 0/or 1` nos 10 emissores (2 linhas com duas). 3 VIVOS curados (reserva,
  populacao dos detalhes, N_hidrantes da planta do pavimento: declaram em
  texto); 47 restantes triados MORTOS contra o produtor com baseline nos dois
  sentidos (`varredura_fallback_folha.py`). Fronteira medida aqui: a lente so
  ve `BoolOp Or`; `.get(chave, 0/1)` nos mesmos emissores + techdraw do
  mezanino/incendio/concreto soma **64** (backlog).

**Baselines mudadas com motivo: nenhuma.** O resumo do runner ganha 2 campos.

**Portoes tocados.** `test_auditoria_g143_g148_d176` + G148 + G146 + G141 +
G112 + G93 + D164 + G145: 47 passed em 39,7 s. Regra do lote: 165 passed, varreduras
True.

**Suite inteira (lida inteira).** Runner `-n 3`: rc_pytest 0, **3916 passed, 1 skipped
em 1574,4 s** (26 min), 312/312 arquivos, memoria livre minima 251 MB (piso nao
disparou), `descendentes_terminados` [] e `descendentes_sobreviventes` [], quebras [].
Referencia serial: **3916 passed, 1 skipped em 3398,1 s** (56 min). Portao do aco
(`GALPAO_AUDITORIA=1`, D165): **2 passed em 1909,2 s**. +4 testes sobre o G148
(3912), os 4 deste verbete.

## D177 - G148 parte 2: o galpao do G102 sai da suite do goal para a auditoria do lote (2026-09-15) - FECHADO

**Pedido.** Decisao do usuario sobre a parte 2 do G148 ("Pode fazer assim"):
tirar a rodada real do galpao do G102 da suite de cada goal e roda-la so na
auditoria do lote, como o executivo de aco (D165). Casa e predio ficam.

**Medido antes (D175/D176).** Na suite pelo runner o `test_01` levava 769,8 s
(D175) e 838,8 s (D176), dos quais casa + predio 17,6 s. O pico do galpao e o
freecad.exe (1369-1968 MB); casa e predio nao sobem freecad
(`CUSTO_MEDIDO_N_FREECAD` 0/0).

**Entregue.**
- `tests/test_indice_disco_rodada_g102.py`: o corpo do `test_01` virou
  `_portao_rodada_real(nomes, tmp_path)` (mesma lente, mesmos tetos de tempo e
  memoria, mesma cobranca de freecad mensuravel, folhas de aco puladas com a
  causa, fronteira PE-IN-03), devolvendo `(gaps, relatorio)`. `test_01` roda
  `TIPOLOGIAS_GOAL = ("casa", "predio")`; o novo `test_10` roda
  `TIPOLOGIAS_AUDITORIA = ("galpao",)` com `skipif` em `GALPAO_AUDITORIA != "1"`
  e o motivo escrito. Nome do `test_01` mantido (citado no G91/G97).
- `ISENCOES_TIPOLOGIA` + `isencoes_mortas(vistos, nomes)`: a isencao morta so
  se cobra da tipologia que rodou (a rodada do goal nao emite HID02/INC02/CLI02
  do galpao, e isso nao e isencao morta); isencao sem dona e cobrada sempre.
- `test_11` (puro): as duas rodadas particionam as tres tipologias; auditoria
  == galpao; `test_10` com um `skipif` so, preso a `GALPAO_AUDITORIA=1`;
  `ISENCOES_TIPOLOGIA` cobre `ISENCOES_EXTRA`; `isencoes_mortas` nos dois
  sentidos (so casa vista: nada no goal, as 3 do galpao com tudo; nada visto:
  as 2 da casa no goal, as 3 do galpao na auditoria) e a sem dona nao some.
- `tests/censo_freecad.GRUPO_FREECAD`: a entrada do G102 saiu com o motivo
  escrito no lugar. Os 7 processos do D164 eram do galpao; ficar no grupo seria
  isencao morta na corrida do goal (o runner reprova isso em corrida inteira).

**Baselines mudadas com motivo.** `GRUPO_FREECAD` perde o G102 (acima).
`CUSTO_MEDIDO_SEG`/`CUSTO_MEDIDO_MEM_MB` ficam como estao: sao o registro da
auditoria, e o `test_05` segue cobrando as tres tipologias.

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK; os 15
arquivos da regra do lote + G102 + G147 + G107 + G97: 182 passed, 1 skipped
(o `test_10`) em 208,1 s. No goal: `CUSTO_G102 casa=7.1s predio=22.5s
total=29.6s`, `MEM_G102 casa=138.4MB predio=208.6MB`, n_freecad 0.

**Portao do galpao na auditoria (`GALPAO_AUDITORIA=1`, serial, -s).** `test_10`:
1 passed em 771,7 s; `CUSTO_G102 galpao=770.8s` (teto 1800),
`MEM_G102 galpao=1470.9MB(proc=184.2,fc=1369.1,n=1)` (teto 2500, freecad
mensuravel e visto). Mesma ordem dos registros (706,6 s / 1679,0 MB no G146):
variacao de maquina, sem re-congelar.

**Suite inteira pelo runner (`-n 3`).** `rc_pytest` 0, **3917 passed, 2 skipped
em 1664,6 s** (27,7 min), 312/312 arquivos, memoria livre minima 300 MB,
descendentes [] / [], `quebras` [] - censo do FreeCAD fechado com o G102 fora
do grupo (sem violacao, sem isencao morta). +1 passed (`test_11`) e +1 skipped
(`test_10`) sobre o D176 (3916/1). O `test_01` caiu de 838,8 s para 31,8 s.

**Ganho de parede NAO demonstrado.** A corrida levou 1664,6 s contra 1574,4 s
do D176. Nao e o diff: os testes do grupo FreeCAD, intocados, ficaram
1,4-2,3x mais lentos (coluna_tapered 81,6->144,1 s; tesoura 79,8->124,6;
estaca_bloco 53,1->119,6; g19_quarto_caso 56,8->88,8), e o Cursor do usuario,
aberto as 16:33 (depois da corrida do D176), somava ~3,3 mil s de CPU ao fim
(CPU em 51 % com a suite ja parada). A estimativa do D175 (1605 -> ~853 s,
-47 %) subtraia o teste do total, e isso nao vale sob xdist: a parede depende
da CPU disputada pelos 3 workers + freecad, nao so da fila de um worker.
Ganho medido com certeza: ~807 s de tempo de teste e o freecad.exe de
1,4-2 GB fora da corrida do goal. A parede em corrida comparavel vai para o
G153 (com a carga da maquina registrada, sem fechar aplicativo do usuario).

**Como rodar a auditoria do lote agora.** Serial `pytest tests` +
`GALPAO_AUDITORIA=1 pytest tests/test_executivo_aco_completo_d165.py
tests/test_indice_disco_rodada_g102.py::test_10_portao_rodada_real_galpao_na_auditoria`
(uma rodada pesada por vez). Goal que muda folha do galpao roda o `test_10`.

**Nao feito.** Mover qualquer outra cobertura; baixar `-n`; mexer nos tetos;
fechar aplicativo do usuario para medir.

## D183 - G149: A estaca calada nas outras tres portas (metalico, wizard, predio) - FECHADO

**Medido por injecao (antes de mudar).**
- **Nucleo** (`verifica_estaca`, N=500, argila N5/3 m + areia N25/8 m):
  D 0,30->0,40 P_adm 572,7->913,2 kN (util 0,873->0,548); L 10->8 m P_adm
  572,7->509,8 (util 0,873->0,981); pre_moldada->escavada P_adm 572,7->334,1
  (n 1->2); FS 3->2 P_adm 572,7->859,0 (N=850: n 2->1, util 0,742->0,990);
  no perfil fraco (L6, N400) pre n=11 x esc n=19. Sem `tipo_estaca` a conta
  usava "pre_moldada" calada; sem `FS`, 3,0 calado.
- **Bloco** (n=2, bielas-e-tirantes): fck 25->15 MPa em N=600 OK->REPROVA
  (biela); a_pilar 0,30->0,50 m em N=700/800 REPROVA->OK. O bloco decide o
  veredito — o dict inteiro calado escondia fck e a_pilar juntos.
- **Predio isolado** (N=800): D 0,30->0,40 n 2->1; tipo pre->esc n 2->3; sem
  D_m/tipo a conta calava 0,30/"pre_moldada" (o numero coincidia com o
  declarado — o defeito era o silencio). L ausente ja avisava
  (`comprimento_de_estaca_lido_da_sondagem`).
- **Predio divisa** (`:666-678`): mesmos defaults de D/tipo + `P_adm = 700,0`
  de fallback; perfil sem tipo de solo caia no 700 em silencio (o `except`
  engolia o erro do `verifica_estaca`).
- **Metalico**: `to_rodar_params` com `.get(D,0,30)/.get(L,10,)/
  .get(tipo_estaca,"pre_moldada")/.get(FS,3,0)` + `rodar_galpao` com
  `setdefault` D/L/bloco `{a_pilar 0,30, fck 25 MPa}`. O fck do bloco se le
  do material declarado do projeto (spec `fundacao.fck` -> params
  `fundacao.fck`; `PARAMS_REF` traz 25e3) — o divisa do predio ja herdava
  assim (`spec_fundacao.get("fck", materiais["fck"])`), precedente, nao
  invencao. O default do template (`PS.novo` fundacao.fck 25e3, nunca
  perguntado no wizard) e fronteira medida aqui, fora do escopo: a heranca
  le o valor vigente do projeto com a origem dita.
- **Wizard**: `construir_spec` gravava o default no spec (`r.get` com
  default) — a origem se perdia ali, nao na conta. O laco interativo mostra
  o default (`[0,30]`, Enter aceita = declarado pelo usuario); o dict
  programatico sem a chave ganhava default silencioso.

**Entregue (D102, fonte unica `estaca_parametros_g143.py`, nunca copia por
modulo; sem arbitrar valor, sem trocar o FS).**
- D, L, tipo (metalico, predio), bloco e a_pilar (metalico): **recusa
  nomeada** (`d/l/tipo_estaca_nao_declarada`, `*_invalida`,
  `bloco_nao_declarado`, `a_pilar_nao_declarado`) — geometria sem piso
  universal que decide capacidade, n e veredito (medido acima). No metalico
  a recusa mora nas duas portas (spec: `validar` com as marcas +
  `to_rodar_params`; params direto: `rodar_galpao` antes do `verifica`).
  No predio mora na entrada do `dimensiona` (vira `EntradaFundacao`, o
  contrato do modulo), na isolada e na divisa.
- fck/fyk do bloco ausentes: **herdam o material do projeto**
  (`material_do_projeto`) com a origem dita — declaracao, nao default. Sem
  material de onde herdar: recusa (`fck/fyk_bloco_nao_declarado`).
- FS ausente: **mantem 3,0 com a origem dita** (`default_normativo_NBR6122`)
  em `verifica_estaca` (out + capacidades), no `gate7-estaca.txt`, no
  `res["estaca"]` do metalico e no memorial/resultado do predio
  (`estaca_parametros` + `relatorio_pt`). FS invalido recusa
  (`fs_invalida`); FS<3 sem prova continua bloqueado no `validar`.
- L do predio ausente: segue o aviso existente (nao se recusa caminho que
  ja declara). `P_adm = 700,0` removido da divisa (o erro sobe ao `except`
  externo e cai na isolada honesta); perfil sem tipo de solo recusa com
  motivo nos dois caminhos.
- Folhas: predio com estaca carimba `proveniencias_g149` (D/L/tipo/FS com
  origem; caminho rasa/casa sem a chave segue byte-identico); PE-CO-04 do
  metalico (`_callout_bloco`) le o fck do `bloco_adotado` com origem (sem
  proveniencia: "origem nao registrada, confirmar", nunca literal calado).
- Wizard: `construir_spec` so escreve o que a resposta trouxe (tipo/D/L/FS/
  bloco via `est_a_pilar`, pergunta nova em `PERGUNTAS_ESTACA`); ausente
  bloqueia no `validar`. Preset 3 declara `est_a_pilar`.

**Testes.** Novo `tests/test_estaca_g149.py` (9): vermelho por injecao em
cada porta (nucleo tipo/FS; spec metalico ausente-e-zero um por um;
rodar direto sem D/bloco; wizard sem `est_*`; predio isolado e divisa;
perfil sem tipo); tabela antes/depois (D/L/tipo/FS/bloco mudam
capacidade/n/veredito); FS 3,0 com origem no resultado e nos tres
memoriais; casa e rasa byte-identicas; os tres aceites da folha de
fundacao do predio com estaca (parse por pilar + G149 + `confere` +
PNG rasterizado + mapa 1:1 + indice). `test_estaca_g143` segue verde.
Vizinhos que congelavam o default antigo passaram a declarar:
`test_validacao` (wizard), `test_crashes_wiki07`, `test_validacao_coerencia`
(`_base_estaca` + marcas `*_invalida` no `validar` + `a_pilar` sem declaracao
bloqueia), `branches/g9/test_fundacao_edificio` (5), `test_g9_fundacao_no_loop`
(IfcPile), `branches/g14/test_gestao_edificio` (insumo estaca).

**Baselines mudadas com motivo: nenhuma** (censo de chaves G134 intacto:
29 de topo; lente G145 sem ocorrencia nova).

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK;
os 15 arquivos da regra + G143 + validacao/coerencia + fundacao: verdes.
Portao do galpao (`GALPAO_AUDITORIA=1`, serial, `-s`, folha do executivo
tocada): `test_10` 1 passed em 683,2 s; `CUSTO_G102 galpao=678,9s`
(teto 1800), `MEM_G102 galpao=1669,8MB` (teto 2500, freecad mensuravel).

**Suite inteira pelo runner (`-n 3`, lida inteira).** `rc_pytest` 0,
**3926 passed, 2 skipped em 1270,4 s** (21 min), 313/313 arquivos (+1 sobre
o D177: `test_estaca_g149`), memoria livre minima 217 MB (piso 200 nao
disparou), descendentes [] / [], `quebras` []. Duas tentativas abortadas
pelo piso antes (190/149/165 MB, maquina carregada; so a arvore do proprio
filho, nenhum app do usuario tocado) — artefato de carga, nao do diff: as
quebras de censo que as acompanham somem na corrida completa. O piso que
aborta na primeira amostra e o objeto do G153.

## D184 - G150: O `or 0` que a lente nao ve (`.get(chave, 0/1)` nos emissores) - FECHADO

**Medido (AST, antes de triar).** A lente do G145 so acha `BoolOp Or`; o mesmo
fallback como `.get(chave, 0|0.0|1|1.0)` nao entra. AST nos 10 emissores do
G145 + `techdraw_mezanino`, `techdraw_incendio`, `techdraw_concreto`: **64**
ocorrencias — `desenho_pavimento` 24, `desenho_casa_residencial` 16,
`desenho_fundacao_edificio` 8, `desenho_alvenaria` 8, `desenho_escada_edificio`
3, `desenho_eletrico` 2, `techdraw_concreto` 2, `desenho_hidraulica` 1
(`desenho_incendio`, `desenho_coordenacao`, `techdraw_eletrico`,
`techdraw_mezanino`, `techdraw_incendio`: 0, congelados no alvo). Fora do AST
numerico, os 3 do adaptador novo pelo nome: `rp.get("hy"|"hx", mz.get(...))`
(`desenho_pavimento.py:1027-1028`, default externo e outra Call) e
`mz.get("fyk", 500e3)` (`techdraw_mezanino.config_de_spec:242`, fora de 0/1).

**Triagem contra o produtor (convencao 9): 64 + 3 MORTOS, 0 VIVOS.** Nenhum
dado pode faltar em rodada real: tramo/linha/lance/base do pavimento
(`viga_concreto.verifica_viga`, `adaptar_galpao_mezanino:1007-1014,1034-1038`,
`galpao_mezanino`), telhado/pecas/contraventamento/arrancamento
(`telhado_casa_madeira.rodar`, chave `contraventamento_6_6` com underscore),
carga_total (`eletrica_edificio.dimensiona` via spec do predio + contexto),
blondel/h_laje (`escada_concreto.geometria/dimensiona`), N_dimensionamento
(`fundacao_edificio.py:797`), ventilacao (`galpao_hidraulica.py:159`, ramo
guardado pela coluna), N_wall/H_total/comprimentos
(`estrutura_casa`, `alvenaria_estrutural`), As_inf (`galpao_concreto.py:280`),
conferencias (`confere_*`, diagnostico, nao desenho). Correcao antes de
fechar: `rp` **tem** `hx/hy` (echo do `dimensiona_pilar`, medido 0,30/0,30) —
o motivo inicial "rp nunca tem" foi reescrito; o externo nunca cai no `mz` e
o interno nunca cai no `0.0`. Com 0 vivos, nenhuma folha declara ausencia
nova: **nenhum emissor tocado, predio e casa byte-identicos por construcao,
sem PNG de cura** (o teste regenera os SVGs da MZ01 em memoria e confere
`CA-50` + formas/armacao presentes, sem escrever no disco).

**Entregue (uma fonte so, a do G145).** `varredura_fallback_folha.py`:
`ALVOS_GET` (13), `varredura_get`/`chaves_get` (mesma chave estavel + `#k`),
`GETS_TRIADOS` (64), `ADAPTADOR_MEZANINO_TRIADOS` (3, presenca textual +
`confere_get`/`relatorio_get` com `adp_resolvidas` fails closed). A lente do
G145 (`varredura`/`chaves`/`confere`, 47) segue intacta e verde.

**Testes.** Novo `tests/test_fallback_get_g150.py` (6): baseline (64/64/3,
0 vivos); vermelho por injecao de `.get` novo em `tmp_path` (convencoes
1/2/7); resolvida nos dois sentidos; motivo/produtor vazio reprova;
mortos-produzem (mezanino + escada + viga + telhado + eletrica/H_total do
predio + hidraulica do galpao + prova textual por produtor para
fundacao/alvenaria/concreto); adaptador-morto (fyk/hx/hy no resultado,
`CA-50`, SVGs presentes, presenca textual). Censo de guardas D86: item 46
(`confere_get`, INDEPENDENTE codigo x declaracao), 39 defs.

**Baselines mudadas com motivo:** `GETS_TRIADOS` 64 (nova), adaptador 3
(novo), `TRIADAS_G69` +1 (`confere_get`). `FALLBACKS_TRIADOS` intacta (47).

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK; os
13 arquivos da regra (12 do lote + `test_fallback_get_g150`; `guardas` com o
item 46) + `test_fallback_folha_g145`: **168 passed**. Portao do galpao
(`test_10`) nao correu: o goal nao muda folha do galpao (so lente + teste).

**Suite inteira pelo runner (`-n 3`, lida inteira).** `rc_pytest` 0,
**3932 passed, 2 skipped em 939,7 s** (15,6 min), 314/314 arquivos (+1 sobre
o G149: `test_fallback_get_g150`; +6 passed sobre os 3926), memoria livre
minima 402 MB (piso 200 nao disparou), descendentes [] / [], `quebras` [].


## D185 - G151: O titulo que o carimbo corta em 26 caracteres - FECHADO

**Pedido.** BACKLOG-GOALS-G149-G153.md G151: os 23 titulos de carimbo cortados
por `techdraw_exec._cap_titulo` (26) e o `sheet_number` fora da contagem.
Lente AST com baseline nos dois sentidos, titulos corrigidos sem mudar
`drawing_number` nem codigo de prancha, abreviacoes declaradas com motivo,
PNG olhado de cada folha tocada, convencoes 1-14 e regra do lote, portao do
galpao se folha do galpao mudar, suite pelo runner ate `rc_pytest` 0 e
`quebras` vazio, verbete e commit.

**Medido (AST, antes de mudar).** `varredura_titulo_carimbo_g151.py` (nova,
mesmo molde da do G145): toda chamada `_carimbo*` com titulo literal +
tabela `LIGACOES` + `TITULOS` da rota SVG + `TITULO_CARIMBO_MZ01`: **20
cortados** (15 literais em 9 arquivos + 5 `TITULOS` espelho em
`prancha_svg_direta`) - o backlog contava 23 incluindo as limpas. Os 20:
`techdraw_exec` 2 (CROQUIS 40->"CROQUIS DE FABRICACAO (pe…", PLANO 31->"…ESCOR…"),
`techdraw_eletrico` 3, `techdraw_hidraulica` 2, `techdraw_incendio` 2,
`techdraw_climatizacao` 2, `techdraw_concreto` 1, `techdraw_coordenacao` 1,
`galpao_concreto` 1, `galpao_seguranca_incendio` 1, `TITULOS` 5. MZ01 curada
na D176 (25, sem corte). `sheet_number`: a MZ01 tem 3 paginas e carimbava
"01/01" nas tres (D176, reproduzido aqui: `Folha 01/01` x3); rota SVG com 1
pagina por PDF (01/02, 02/02 coerentes) e quadro de 1 pagina na rodada real.

**Corrigido (titulo curto, `drawing_number` e codigo de prancha intactos).**
13 titulos unicos, todos <=26 e com `_cap_titulo(t)==t`:

| original (n) | novo (n) | motivo |
|---|---|---|
| CROQUIS DE FABRICACAO (pecas principais) (40) | CROQUIS DE FABRICACAO (21) | parentese lista C1/V1/MI1 ja no corpo |
| PLANO DE MONTAGEM E ESCORAMENTO (31) | MONTAGEM E ESCORAMENTO (22) | PLANO redundante; corpo diz NBR 8800 12.3 |
| PLANTA DE ILUMINACAO E TOMADAS (30) | ILUMINACAO E TOMADAS (20) | PLANTA redundante |
| PLANTA - ELETROCALHAS E ATERRAMENTO (35) | ELETROCALHAS E ATERRAMENTO (26) | PLANTA - redundante |
| QUADRO DE CARGAS E ESPECIFICACOES (33) | CARGAS E ESPECIFICACOES (23) | QUADRO DE redundante (prancha ja e quadro) |
| ESQUEMA DA REDE HIDRAULICA PREDIAL (34) | ESQUEMA REDE HIDRAULICA (23) | DA/PREDIAL redundantes (disciplina ja diz) |
| QUADRO DE DIMENSIONAMENTO E MEMORIAL (36) | DIMENSIONAMENTO E MEMORIAL (25) | QUADRO DE redundante |
| PLANTA DE SEGURANCA CONTRA INCENDIO (35) | SEGURANCA CONTRA INCENDIO (25) | PLANTA DE redundante |
| DETALHES DE HIDRANTES E ROTAS (29) | HIDRANTES E ROTAS (17) | DETALHES DE redundante |
| ESQUEMA DA REDE DE CLIMATIZACAO (HVAC) (38) | ESQUEMA REDE HVAC (17) | HVAC ja diz climatizacao |
| QUADRO DE CAPACIDADE E MEMORIAL (31) | QUADRO CAPACIDADE/MEMORIAL (26) | DE->vazio, E->/ compacto |
| LOCACAO E FORMAS DA FUNDACAO (28) | LOCACAO E FORMAS FUNDACAO (25) | artigo DA |
| PLANTA DE COORDENACAO - MODELO FEDERADO (39) | COORDENACAO - FEDERADO (22) | PLANTA/MODELO redundantes |

Arquivos: `techdraw_exec` (PE-14, PE-16), `techdraw_eletrico` (PE-EL-02/03/04),
`techdraw_hidraulica` (PE-HID-01/02), `techdraw_incendio` (PE-INC-01/03),
`techdraw_climatizacao` (PE-CLI-01/02), `techdraw_concreto` + `galpao_concreto`
(PE-04), `techdraw_coordenacao` (PE-COORD-01), `galpao_seguranca_incendio`
(PE-INC-03), `prancha_svg_direta.TITULOS` (5, mesmos textos). Nenhum
`drawing_number` (PE-14, PE-16, PE-EL-02/03/04, PE-HID-01/02, PE-INC-01/03,
PE-CLI-01/02, PE-04, PE-COORD-01, PE-INC-03) e nenhum codigo de prancha
(PE14_CROQUIS, PE16_MONTAGEM, PE02_PLANTA_INST, PE03_PLANTA_INFRA,
PE04_QUADROS, HID01_ESQUEMA, HID02_QUADRO, INC01_PLANTA, INC03_DETALHES,
CLI01_ESQUEMA, CLI02_QUADRO, PE04_LOCACAO_FUNDACAO, COORD01_PLANTA) mudou.

**Abreviacoes limpas declaradas (10, sem reticencia, cap conferido).**
`ABREVIACOES_LIMPAS` na lente, uma fonte so: DETALHE-BASE/COLUNA,
BLOCO/COROAMENTO, LIGACAO/JOELHO (2 formas), FECHAMENTO/TERCAS/MAO-FRANCESA
e as 5 da tabela `LIGACOES` (CUMEEIRA, GUSSET_COB/PAR, GIRT, CONSOLE) -
motivo escrito em cada uma (DETALHE redundante; complemento no corpo/vista).
Motivo vazio, cap divergente, limpa nova sem entrada e abreviacao que some
reprovam (fails closed).

**`sheet_number` coerente.** `galpao_mezanino.gerar_prancha_mezanino`: 3
carimbos 01/03, 02/03, 03/03 (antes um so "01/01" nas 3); o quadro e 1 pagina
na rodada real e, se derramar (N>1), o total vira 2+N com um carimbo por
pagina do quadro (`prancha_svg_direta.pagina_quadro_a1(..., carimbos=)` novo
parametro opcional, comportamento historico sem ele).

**Testes.** Novo `tests/test_titulo_carimbo_g151.py` (6): baseline (0
cortados, 10 abreviacoes, todo titulo <=26 sem "…"); vermelho por injecao de
titulo longo em `tmp_path` nomeando arquivo:linha; resolvida nos dois
sentidos; limpa sem motivo/nao declarada reprova; MZ01 com 3 paginas
01/03..03/03 sem "…" no PDF; rota SVG 01/02+02/02 sem "…". Vermelho provado:
antes da correcao a lente achava 20 cortados (test_01 falharia); injecao nova
reprova (test_02).

**PNG olhado (convencoes 3/6).** MZ01 3p (formas M-VX/VY=BIM, armacao,
quadro; rodape 01/03..03/03, titulo inteiro); HID01/HID02, INC01 (+INC03
HIDRANTES E ROTAS via `montar_pranchas`, PE-INC-03 intacto), CLI01/CLI02 e
PE04_LOCACAO_FUNDACAO (PE-04 | LOCACAO E FORMAS FUNDACAO | 04/04) - titulos
inteiros, sem "…", sem "-" da fonte helv, `drawing_number` no rodape.
PE-14/PE-16/PE-EL/PE-COORD: mudanca so de literal de titulo (mesmo padrao
das demais, sem conta); cobertas pelo portao do galpao abaixo.

**Baselines mudadas com motivo.** `ABREVIACOES_LIMPAS` 10 (nova);
`SCRIPTS_AVULSOS` +1 (`varredura_titulo_carimbo_g151`);
`SEM_FAIXA_DECLARADA` +1 (lente sem numero de norma). Nenhuma outra baseline.

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK;
13 arquivos da regra + `test_titulo_carimbo_g151`: **168 passed**.
`test_carimbo_mapa_g112` e `test_galpao_indice_g93` verdes (codigo intacto).
Portao do galpao (`GALPAO_AUDITORIA=1`, serial, isolado): **1 passed em
656,9 s** (CUSTO_G102 galpao 656,4 s, MEM 1583,1 MB).

**Suite inteira pelo runner (`-n 3`, lida inteira).** `rc_pytest` 0,
**3938 passed, 2 skipped em 976,6 s** (16,3 min), 315/315 arquivos (+1 sobre
o G150: `test_titulo_carimbo_g151`; +6 passed sobre os 3932), memoria livre
minima 599 MB (piso 200 nao disparou), descendentes [] / [], `quebras` [].
Os 2 skipped sao os portoes de auditoria (galpao `test_10` + aco D165),
pulados sem a variavel (D177).

**Nao feito.** Aumentar a celula do template ISO 5457; mudar codigo de
prancha; trocar numero do FS ou qualquer conta (titulo, nao conta).

## D186 - G152: A folha de disciplina reprovada que nao dizia que reprovou - FECHADO

**Pedido.** BACKLOG-GOALS-G149-G153.md G152: a folha reprovada saia com
carimbo PARA APROVACAO e sem nenhum REPROVAD no corpo. Medir disciplina por
disciplina com o veredito reprovado injetado; a folha reprovada declara o
veredito no carimbo e no corpo, nomeando os gates - texto, nunca omissao,
lido do resultado (fonte unica). ATENDE byte-identica, PNG olhado,
convencoes 1-14 e regra do lote, suite pelo runner ate `rc_pytest` 0 e
`quebras` vazio, verbete e commit.

**Medido (resultado real na mao, conta intacta, antes de mudar).**
`grep REPROVAD|NAO ATENDE` em `techdraw_*.py` + `prancha_svg_direta.py`: 0;
`_carimbo` sempre PARA APROVACAO; o veredito morava fora da folha (capa do
caderno, `native_atende`/`reprovados` do adaptador). Por disciplina:

| disciplina | resultado real | folha dizia |
|---|---|---|
| hidraulica | ATENDE [] | nada; inj. reprovada -> nada |
| incendio | ATENDE [] | nada; inj. reprovada -> nada |
| climatizacao | ATENDE [] | nada; inj. reprovada -> nada |
| mezanino | ATENDE [] | nada; inj. (viga_X/viga_Y/vigas) -> so a armacao marca por viga, formas e quadro nada |
| eletrico | REPROVA ['cargas'] de verdade no spec minimo | nada (prova viva) |
| concreto | REPROVA ['pilar'] de verdade no spec minimo | nada (prova viva) |
| aco | `config_de_spec(spec)` nem recebia o veredito (o memorial ja imprime VEREDITO, a folha nao) | nada |

Coordenacao: N/A declarado - clash e triagem (A REVISAR/esperados), nao
veredito de calculo; o global ja vai na capa do caderno.

**Entregue (fonte unica `veredito_folha_g152.py`, lida do resultado, nunca
decidida na folha).** `extrair_veredito` le os dois dialetos (ATENDE/
reprovados e atende_global/atende/falhas_verificacao); sem a chave, o
veredito e DESCONHECIDO e a folha sai como antes. `aplicar_a_cfg` em todo
`config_de_spec` (7 disciplinas) carrega `veredito_atende/reprovados/linha/
status`; o aco viaja carimbado no spec pelo `calcular`
(`estrutura.veredito_aco`, escrito do `res`). Carimbo: REPROVADO - VER
MEMORIAL so na REPROVA (lido da chave precomputada, sem import de irmao
dentro do freecad). Corpo, nomeando os gates: notas do quadro + titulo das
vistas (13 paginas do aco, 3 do eletrico, 3 do concreto, 1 da MZ01 FreeCAD,
7 simbolo com vista V152 nova) + subtitulo e rodape STATUS em CADA pagina
da rota SVG (hid/inc/cli default + MZ01 3p). A folha reprovada continua
saindo (o engenheiro precisa dela para revisar).

**Testes.** Novo `tests/test_veredito_folha_g152.py` (5): baseline ATENDE/
DESCONHECIDO sem REPROVAD e com carimbo historico; vermelho por injecao em
cada uma das 7 disciplinas (carimbo + linha com todos os gates + linha nas
notas); fonte unica le-sem-decidir (tabela verdade, literais a mao);
rota SVG declara por pagina e ATENDE sem REPROVAD; MZ01 3p declara e ATENDE
sem REPROVAD. Vermelho provado: com a producao em `stash`, o test_01 falha
(sem `veredito_atende`); com o fix, 5 passed em 23,3 s.

**PNG olhado (convencoes 3/6).** HID01/HID02 e MZ01 (3p) reprovadas: subtitulo
com o veredito e os gates, rodape STATUS, notas com a linha, sem colisao;
ATENDE sem VEREDITO e sem STATUS (byte-identica no pixel). INC/CLI
reprovadas: texto por pagina confere (mesmo renderizador). FreeCAD real
(eletrico que REPROVA cargas de verdade, 3D headless + freecad.exe):
PE-EL-01/02/03/04 com carimbo REPROVADO - VER MEMORIAL, linha no corpo e
`drawing_number`/folha intactos; a vista V152 a y=45 encostava na moldura e
subiu para y=58 (re-render PE-EL-01 confere: legivel, sem colisao).

**Baselines mudadas com motivo.** `SEM_FAIXA_DECLARADA` +1 (fonte pura sem
numero de norma). Nenhuma outra baseline.

**Portoes tocados + regra do lote.** Faixa/sequencia/orfas OK; 13 arquivos
da regra + faixa-guard + `test_veredito_folha_g152`: **189 passed**.
`test_carimbo_mapa_g112` e `test_galpao_indice_g93` verdes (nenhum codigo
de prancha muda aqui). Portao do galpao (`GALPAO_AUDITORIA=1`, serial,
isolado): **1 passed em 623,9 s** (CUSTO_G102 galpao 623,7 s, MEM 1587,8 MB).

**Suite inteira pelo runner (`-n 3`, lida inteira).** `rc_pytest` 0,
**3943 passed, 2 skipped em 1009,7 s** (16,8 min), 316/316 arquivos (+1
sobre o G151: `test_veredito_folha_g152`; +5 passed sobre os 3938), memoria
livre minima 365 MB (piso 200 nao disparou), descendentes [] / [],
`quebras` []. Os 2 skipped sao os portoes de auditoria (galpao `test_10` +
aco D165), pulados sem a variavel (D177); o `test_10` rodou isolado acima.

**Nao feito.** Parar de emitir a folha reprovada; decidir gate na folha;
coordenacao com veredito (clash e triagem, nao conta); numero novo no
carimbo (`drawing_number`/titulo intactos, G151 segue verde).

## D178 - G153: o piso que abortava por uma amostra confirma em 3, com serie e carga no resumo (2026-09-16) - FECHADO

**Pedido.** O piso do runner abortava na primeira amostra abaixo de 200 MB e o
G142 passou com minimo de 159 MB numa unica amostra (sem serie, sem duracao):
com o piso de hoje teria sido abortado. Entregar: serie de amostras no resumo;
duracao das quedas em duas corridas reais com a maquina em uso normal; regra de
confirmacao decidida so com os numeros, com vermelho por injecao nos dois
sentidos; tempo ate a memoria voltar com processo ocupado; carga da maquina no
resumo e ganho de parede do D177 contra o D176 em corrida comparavel. Sem
fechar aplicativo do usuario, sem mover cobertura.

**Medido (fontes vivas, antes de decidir).**
- Duas corridas reais pelo runner (`-n 3`, maquina em uso normal, aplicativos
  do usuario abertos; resumos em
  `C:/Users/joseh/AppData/Local/Temp/opencode/g153-A/resumo.json` e `.../g153-B/resumo.json`):
  A = 3948 passed/2 skipped em 1031,6 s, serie de 1032 amostras de 1 s,
  quedas abaixo de 200 MB = 0, duracao 0 s, minimo 374 MB (livre_inicial 1283 MB);
  B = 3948 passed/2 skipped em 1061,7 s, 1062 amostras, quedas = 0, duracao 0 s,
  minimo 419 MB (livre_inicial 1794 MB). Em ~2094 amostras reais, nenhuma queda:
  a unica queda historica (G142 159 MB) foi de 1 amostra sem duracao.
- Volta da memoria com processo ocupado (sonda propria, sem fechar nada do
  usuario): filho python com 400 MB + sleep, terminate da arvore propria -
  morte em ~0,0 s e livre 827 -> 1215 MB (+388) em 0,5 s. O freecad.exe real
  (1535-1968 MB, D176) sai pela mesma `terminar_arvore` (D176 provou worker
  morto < 10 s); em brecha real o runner grava `tempo_memoria_volta_s` e a
  `memoria_serie_recuperacao` (nas duas corridas: None declarado, sem brecha).
- Carga como regua (testes intocados do grupo FreeCAD, `--durations=40`):
  D176 = coluna_tapered 81,6 / tesoura 79,8 / estaca_bloco 53,1 / g19 56,8 s;
  D177 (carregada, Cursor ~3,3 mil s CPU) = 144,1 / 124,6 / 119,6 / 88,8 s;
  G153-A = 76,5 / 70,4 / 52,3 / 60,9 s; G153-B = 78,3 / 69,7 / 51,1 / 61,0 s.
  A/B andam com o D176, nao com o D177: a comparacao de parede vale contra o D176.
- Ganho de parede do D177 (galpao do G102 fora da suite do goal) em corrida
  comparavel: D176 1574,4 s -> G153-A 1031,6 s = -542,8 s (-34 %); o `test_01`
  838,8 s (D176) -> 16,1 s (A). O D177 mediu 1664,6 s so porque a maquina
  estava carregada (regua acima); o diff em si entrega ~807 s de tempo de teste
  e o freecad.exe de 1,4-2 GB fora da corrida do goal.

**Decidido so com os numeros.** Aborta so com K = 3 amostras CONSECUTIVAS
abaixo do piso (~3 s no amostrador de 1 s). Derivacao: 2094 amostras reais com
0 quedas + 1 queda historica de 1 amostra (G142) = transitoria de 1-2 s nunca
pode abortar; nada medido dura 3 s+, entao 3 confirma sem nenhum falso-aborto
observado e sem afrouxar para rajadinha. Amostra None quebra a sequencia.

**Entregue.**
- `tools/suite_paralela.py`: `CONFIRMACAO_PISO_AMOSTRAS = 3` (fonte unica, motivo
  com os numeros acima); `confirma_queda_consecutiva` + `quedas_abaixo_piso`
  puras; `carga_maquina_dict` (cpu_logicos, total_phys_mb, livre_inicial/min,
  n_amostras); o `main` grava `memoria_serie_amostras`, `memoria_quedas_abaixo_piso`,
  `memoria_confirmacao_amostras`, `carga_maquina`, `tempo_memoria_volta_s` e
  `memoria_serie_recuperacao`, e so aborta com 3 seguidas (quebra diz
  "confirmado em 3 amostras seguidas < piso, G153").
- `tests/censo_freecad.py`: `ler_coletados`/`ler_registros` declaram ausencia
  em arquivo vazio/linha ruim (vermelho do G153: no aborto o worker morre no
  meio da escrita e o `json.load('')` matava o proprio resumo com
  JSONDecodeError).
- `tests/test_piso_memoria_g153.py` (6): K derivado e lido pela producao;
  puras nos dois sentidos + quedas com duracao/minimo; transitoria nao aborta e
  sustentada aborta pelo `main` (usuario vivo nos dois); aborto com teste lento
  mata a arvore < 10 s e nomeia o worker (conv. 14); serie/carga/volta
  declaradas; censo com coletados vazio nao levanta.
- `tests/test_piso_memoria_g148.py::test_04`: baseline recomposta com motivo
  (sequencia 50/40/30 confirma na 3a: minimo 30, quebra "confirmado em 3").

**Baselines mudadas com motivo.** `test_04` do G148 (acima). `GRUPO_FREECAD`
intocado; piso 200 MB intocado; nenhum teto mexido.

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK;
lote (g77, alcancabilidade, guardas, disciplina, indice_g91, carimbo,
normas, galpao_indice, fallback, g148, g153): 159 passed em 105,5 s; D164 +
auditorias g137-g142/g143-g148: 13 passed em 43,3 s.

**Suite inteira (lida inteira).** Corrida A pelo runner: rc_pytest 0,
3948 passed, 2 skipped em 1031,6 s, 317/317 arquivos, minimo 374 MB,
quedas [], `tempo_memoria_volta_s` None (declarado, sem brecha),
descendentes [] / [], `quebras` []. Corrida B: mesmos 3948/2 em 1061,7 s com
1 quebra flaky de censo (`test_ifc_secundarios_xcheck` no grupo e sem avistamento
na B, avistado na A com 78,18 s de teste) - amostrador de 0,5 s perdeu o processo
curto, isencao viva, nao morta. Fechamento pela A (rc 0 e quebras vazio); o fix
do censo e o comentario de derivacao entraram depois sem mudar comportamento do
caminho verde (lote re-rodado verde acima).

**Nao feito.** Baixar o piso; mover cobertura para a auditoria; fechar
aplicativo do usuario para medir; trocar K sem numero novo.

## D179 - auditoria do lote G149-G153: o FS "normativo" que a norma nao diz, o PID reusado e o censo herdado (2026-09-16) - FECHADO

**Pedido.** "goals encerrados, sua vez agora": auditar por medicao o lote
G149-G153 (`86b981c`..`0083568`), corrigir, rodar a suite inteira (runner,
serial, portoes de auditoria) e ler o resumo, commitar e escrever o proximo
backlog.

**Medido (fontes vivas, antes de mudar).**
- **G149 - o FS 3,0 carimbado como "default normativo NBR 6122".** O G149
  passou a escrever essa origem no resultado (`FS_origem`), no memorial do
  metalico e do predio e na folha de fundacao do predio. O acervo diz outra
  coisa: NBR 6122:2022 **p.18 (imagem do PDF, F038)**, 6.2.1.2.1 - "O fator de
  seguranca global a ser utilizado para determinacao da carga admissivel e
  **2,0**" (semiempirico); 6.2.1.2.2 - **1,6** com prova de carga estatica. O
  **3,00** e da Tabela 1 (fundacao **rasa**, 6.2.1.1.1). O 3,0 veio do D38
  (parecer de 2026-07-11, "sem citar o PDF 6122 escaneado"; antes era 2,0). O
  G149 so repetiu o que o **backlog G149-G153 afirmava** ("valor normativo
  (NBR 6122, no acervo)", escrito na auditoria D176 sem ler a pagina) - o erro
  de origem e da auditoria anterior, nao do goal. A lente do teste novo achou
  mais dois textos com a mesma atribuicao: a pergunta do wizard
  (`wizard.py:222`) e o memorial do nucleo (`estaca_profunda.py:662`).
- **G149 - fck do bloco "herdado do material do projeto".** `projeto_spec.novo()`
  (`:125`) escreve `fundacao.fck = 25e3` em todo spec e o wizard nunca pergunta:
  a origem "material do projeto" pode ser o valor do modelo. O G149 mediu que
  fck 25->15 vira a biela (OK->REPROVA). `fundacao_sapata_corrida.py:173` ainda
  cala `.get("fck", 25e3)`. Vai para o G154.
- **G153 - a quebra "flaky" do censo nao era processo curto.** O freecadcmd do
  `test_ifc_secundarios_xcheck` vive **~40 s** (sonda a 50 ms: de 10,8 a 51,0
  s) - um amostrador de 0,5 s nao o perde. Duas causas medidas nos arquivos do
  censo das corridas A/B e por injecao:
  1. `Amostrador.amostra` descartava por **PID ja visto**; o Windows reusa PID
     (3612 e 5796 aparecem em testes diferentes nas duas corridas). Injecao:
     freecad do segundo teste com PID reusado -> sem registro -> "isencao morta"
     falsa (a mesma quebra da corrida B).
  2. O pytest aninhado do `test_G21_prova_fronteiras` (subprocesso sem `-n`)
     herdava `GALPAO_CENSO_FREECAD` e `PYTEST_XDIST_WORKER`, ligava um
     amostrador proprio e **sobrescrevia `coletados-gw1/gw2.json`** da corrida de
     fora com `["tests/test_fronteiras.py"]` (A e B).
  O D178 fechou pela corrida A e **mudou codigo depois** (fix do censo) sem
  rodar de novo; esta auditoria rodou.
- **G152 - veredito DESCONHECIDO sai "PARA APROVACAO".** Medido: os seis
  `config_de_spec` das disciplinas recebem o resultado `r`; o aco le o carimbo
  do `calcular`, e os quatro chamadores de `rodar_executivo` (`rodar_tudo`,
  `build_final`, `smoke_executivo`, turnkey) calculam antes. Nao alcancavel em
  rodada real hoje: sem defeito.
- **G151 - a lente dos titulos.** 29 chamadas `_carimbo*` com titulo nao
  literal: todas repasse de wrapper (`titulo`) ou a constante da MZ01 (coberta).
  Nenhum titulo montado por conta escapa: sem defeito.
- **G150.** Nao re-triado nesta auditoria (64+3 mortos): a lente e o teste
  mortos-produzem do goal seguem verdes na regra do lote. Nao medido aqui.
- **Processo.** Os verbetes G149-G152 fecharam sem numero D (so o G153 virou
  D178) e nenhum dos cinco escreveu no `03-phases` (escrito aqui). Vai para o
  G157 como guarda.

**Corrigido.**
- Atribuicao do FS (numero e trava **intocados**, decisao do usuario):
  `estaca_parametros_g143.ORIGEM_FS_ADOTADO = "fs_adotado_D38"` (era
  `default_normativo_NBR6122`) + `NOTA_FS_NBR6122`; `_fmt_origem` diz "adotado no
  framework (D38); NBR 6122:2022 6.2.1.2.1 fixa 2,0 no semiempirico (1,6 com
  prova de carga, 6.2.1.2.2) - confirmar com o responsavel". Mesma correcao em
  `estaca_profunda` (comentarios, fallback do memorial, texto A CONFIRMAR),
  `fundacao_edificio` (origem + comentario), `projeto_spec.validar` (mensagem
  do bloqueio e do aviso com prova: "regra adotada no D38"), `wizard.py` (aviso e
  pergunta do FS) e o comentario do `test_fase3`.
- Texto do material herdado: "fundacao.fck/fyk do spec (o wizard nao pergunta:
  pode ser o valor do modelo PS.novo) - confirmar".
- `tests/censo_freecad.Amostrador.amostra`: PID que sai da arvore deixa de
  contar como visto (reuso volta a ser avistamento).
- `tests/conftest.py`: `_worker_xdist(config)` - so worker de verdade
  (`workerinput`) ou `-n 0` explicito liga o amostrador e escreve `coletados`;
  o pytest aninhado fica de fora.
- Novo `tests/test_auditoria_g149_g153_d179.py` (6, o `test_05` descrito nas
  suites abaixo): PID reusado volta a ser
  avistado e nao gera isencao morta; pytest aninhado nao escreve no censo de
  fora e `-n 0` segue escrevendo; nenhum texto de producao atribui 3,0 a NBR
  6122 sem o item (AST), a linha do FS cita 6.2.1.2.1 e 2,0, `FS_GLOBAL` segue
  3,0 e a mensagem do `validar` tem a atribuicao corrigida, com o trecho do
  acervo conferido quando presente; acervo presente ou pulo declarado; texto do
  fck diz "pode ser o valor do modelo". **Vermelho provado no `0083568`
  (worktree, os 5 primeiros): 4 failed, 1 skipped** (sem o acervo na copia);
  o `test_05` acusa os dois arquivos do `0083568`.
- `tests/test_estaca_g149.py`: 4 literais da origem acompanham o nome novo.

**Baselines mudadas com motivo.** Valor da origem do FS
(`default_normativo_NBR6122` -> `fs_adotado_D38`), pelo motivo acima. Nenhum
numero, teto, piso ou gate.

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK;
auditoria + estaca G143/G149 + fase3 + validacao/coerencia + crashes + g9 +
wizard: 157 passed em 106,9 s; regra do lote (15 + G149-G153 + D179 + G102):
**204 passed, 1 skipped** (o `test_10`) em 188,2 s.

**Suites da auditoria (lidas inteiras).**
- Runner `-n 3`: `rc_pytest` 0, **3954 passed, 2 skipped em 896,4 s** (15 min),
  318/318, memoria livre minima 614 MB, quedas [], descendentes [] / [],
  `quebras` []. Os tres `coletados-gwN.json` com a lista inteira (12 356 bytes
  cada; nas corridas do G153 gw1/gw2 tinham 28 bytes). +6 sobre os 3948 do
  G153-A: 5 deste verbete + o `test_06` do G153, que entrou depois da corrida A.
- Serial `pytest tests`: **1 failed, 3953 passed, 2 skipped em 3034,4 s**. A
  falha: `test_piso_memoria_g153::test_04` - o runner aninhado saiu com rc 1 e
  quebras [] porque a coleta deu `FileNotFoundError` em
  `Temp\playwright_chromiumdev_profile-...` (pasta de outro aplicativo apagada
  no meio). Medido: o arquivo lento mora no `tmp_path` sem ini e a raiz do
  pytest aninhado vira `C:\Users\joseh` (coleta 1,67 s varrendo o Temp); com um
  `pytest.ini` ao lado a raiz e o proprio tmp (0,01 s). Mesmo desenho no
  `test_04` do D176 (escrito na auditoria anterior). **Corrigido:** os dois
  poem `pytest.ini` ao lado; `test_05` novo (guarda: todo teste que gera
  arquivo para o runner aninhado poe o ini; acusa os dois arquivos como estavam
  no `0083568`; injecao nos dois sentidos). Os dois testes + vizinhos: 20
  passed; o arquivo da auditoria: 6 passed.
- Portao do aco (`GALPAO_AUDITORIA=1`, D165): **2 passed em 1780,7 s**
  (`CUSTO_D165 executivo_aco_completo=1779.6s`).
- Portao do galpao (`test_10`, D177): **1 passed em 884,4 s**;
  `CUSTO_G102 galpao=884.0s` (teto 1800), `MEM_G102
  galpao=1864.1MB(proc=171.0,fc=1761.8,n=1)` (teto 2500).
- Runner de novo no codigo final (convencao 16: a correcao dos testes veio
  depois): `rc_pytest` 0, **3955 passed, 2 skipped em 1777,4 s**, 318/318,
  memoria livre minima 252 MB, quedas [], descendentes [] / [], `quebras` []
  (+1 = o `test_05`). Mais lenta que a primeira (896 s) por carga da maquina,
  nao do diff: a regua dos testes intocados do FreeCAD subiu junto
  (coluna_tapered 136,7 s, tesoura 120,0, estaca_bloco 78,5, g19 101,3).

**Decisao do usuario (backlog G154-G157).** FS da estaca: (a) manter 3,0 como
adotado e declarado; (b) alinhar a 2,0 / 1,6 com prova (vira goal, muda
capacidade, n e veredito).

**Nao feito.** Trocar o FS ou a trava; mudar o fck do modelo; numerar os
verbetes G149-G152 (G157).

## D180 - G154: o material da fundacao que vinha do modelo sem ninguem declarar (2026-09-17) - FECHADO

**Pedido.** BACKLOG-GOALS-G154-G157.md G154: o `fundacao.fck = 25e3` /
`fyk = 500e3` que o `projeto_spec.novo()` (`:125`) escreve em todo spec e o
wizard nunca pergunta, e que decide veredito — bloco do metalico
(`estaca_parametros_g143`), predio (`fundacao_edificio.py:352,427,666,747,756`)
e sapata corrida (`fundacao_sapata_corrida.py:173`, 25 MPa calado).

**Medido por injecao (antes de mudar).**
- Bloco metalico n=2 N=600: **fck 25->15 MPa OK->REPROVA** (biela, sig 13,33 vs
  fcd1 13,66->8,56); fyk 500->250 MPa OK segue OK, As 6,9->13,8 cm2
  (quantidade, nao veredito); cobrimento 0,05->0,10 m: h 0,445->0,495 m com
  d 0,375 inalterado (h = d+cob+emb do bloco rigido) — OK igual, muda
  geometria; phi_barra nao lido no bloco (bitola do tirante e detalhada).
- Sapata isolada Parte B (B=2 L=2,5 h=0,5): **fck 25->15 em N=1500 OK->REPROVA**
  (u_cd 0,691->1,103); **cob 0,05->0,10 em N=2000 OK->REPROVA**
  (u_cd 0,922->1,041, d 0,438->0,388); **phi 12,5->25 mm em N=2120 OK->REPROVA**
  (u_cd 0,977->1,006); fyk 500->250 MPa OK segue OK em M=100..400 (As sobe,
  puncao melhora 0,133->0,112) — quantidade, nao veredito.
- Sapata corrida: mesma Parte B (VIVO por construcao); no aprovado tipico o
  SOLO governa (q=150/sigma=120: B 2,0 passa solo, concreto passa nos dois
  fck) — o silencio continua defeito (D102) e sai do mesmo jeito.
- Portas: spec metalico (PS.novo escreve antes de qualquer resposta; comparar
  valor com 25e3 nao distingue — o usuario pode declarar 25); wizard
  (`:317-343` nunca pergunta); predio (herda do material declarado do predio);
  corrida (`.get("fck", 25e3)` calado).

**Entregue (D102, fonte unica `material_fundacao_g154.py`, nunca copia por
modulo; sem arbitrar valor, sem trocar classe de agressividade, sem quebrar o
caminho do usuario).**
- O spec distingue desde onde o numero nasce: `PS.novo()` escreve
  `fundacao._origem_material` modelo; `wizard.construir_spec` (4 perguntas
  novas `fund_fck/fyk/cobrimento/phi`, com FAIXAS e conversao MPa/cm/mm) so
  escreve o que a resposta trouxe e marca declarado; `declarar_material_fundacao`
  marca no spec-direto. Sem aviso no `validar` (o aviso virava needs_review no
  G15/G19 e quebrava a proposta 36x24 ready sem mudar numero — a declaracao
  mora na entrega, nao no gate, mesmo desenho do G143 para cota/B_max).
- Por item, com motivo: fck/cobrimento/phi DECLARAM com origem (decidem
  veredito, medido acima; numero mantido); fyk DECLARA com origem (muda As,
  nao veredito); phi no bloco e TERCEIRO VALOR (nao se aplica, declarado).
  A corrida deixa de calar 25 MPa (resolver); o bloco herda cobrimento com
  origem (antes calava 0,05); o predio herda do predio declarado com origem
  dita (antes heranca calada).
- Memorial sempre diz a origem (`MATERIAL DA FUNDACAO (G154)` em
  gate7-fundacao.txt, gate7-estaca.txt, relatorio do predio e tabela da
  corrida); folha carimba `G154 material: ... modelo (confirmar)` so no modelo
  a confirmar (declarado puro segue sem linha nova, byte-identico).

**Testes.** Novo `tests/test_material_fundacao_g154.py` (8): tabela antes/depois
(fck/cob/phi viram, fyk nao); spec modelo vs declarado (declarar 25 segue
declarado); wizard sem/com `fund_*`; metalico modelo/declarado no memorial e
na folha (rodar de verdade); predio heranca/declarado no memorial; corrida sem
25 MPa calado; folha do predio tres aceites com modelo (parse por pilar +
`confere` + PNG rasterizado + mapa 1:1 + indice); baseline nos dois sentidos.
Vizinhos com baseline mudada com motivo: `test_estaca_g149` (heranca de modelo
diz `modelo_PS_novo`, antes `material_do_projeto` generico) e
`test_auditoria_g149_g153_d179::test_04` (o wizard agora pergunta; o texto
"nao pergunta" saiu). Lente G75 sem ocorrencia nova (a leitura do memorial usa
`[]`, nao `.get("material")`).

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK;
G75/G145/G150/G151/G152/G149/D179 + validacao/coerencia/crashes + fundacao G9
+ G102 casa/predio (`test_01`) + colisoes: verdes. G102 casa/predio seguem
rodando; o galpao vai no portao de auditoria (folha do galpao tocada no
callout do bloco).

**Suite inteira pelo runner (`-n 3`, lida inteira, worktree so com o G154).**
`rc_pytest` 0, **3958 passed, 7 skipped em 1399,7 s** (23 min), 319/319
arquivos, memoria livre minima 368 MB (piso 200 nao disparou), quedas [],
descendentes [] / [], `quebras` []. (Na arvore com o WIP do G155 em progresso
a suite nao fecha — o G155 toca o mesmo emissor e ainda nao triou o
`BASELINE_G83`; ver G155.)

**Nao feito.** Escolher outro fck; mudar classe de agressividade; tirar o valor
do modelo sem a pergunta no wizard; numerar os verbetes G149-G152 (G157).

## D181 - G155: as folhas do predio e da casa que nao diziam que reprovaram (2026-09-17) - FECHADO

**Pedido.** BACKLOG-GOALS-G154-G157.md G155, pelo protocolo de execucao em
sequencia e as decisoes do topo (retomar o WIP, sem recomeçar; sem perguntas;
imprevisto pela regra conservadora). Checagem de entrada OK antes de editar:
`git log` com `4018471` (G154/D180); `git status` so com os 17 caminhos do WIP
do "Estado de partida"; nenhum pytest/suite_paralela/freecad rodando.

**Medido por injecao (antes de completar; conta intacta).**
- Predio (edificio-multipavimento real): eletrica REPROVA de verdade e a
  prumada nao dizia nada (prova viva); hidraulica/incendio ATENDEM e com o
  reprovado injetado seguiam sem dizer nada; fundacao (`gate.OK`) idem; R
  traz `ATENDE=True`; memorial com `atende_global=False` (a eletrica reprova).
  Marcas parciais (escada 13, pavimento 4, casa 7/6) nomeiam a peca, nao o
  veredito da disciplina com os gates.
- Casa (casa-residencial real): arquitetura/hidraulica/estrutura/telhado com
  ATENDE; conferencia_nbr5410 com `ok=True`; fundacao com `gate.OK=True`;
  `circuits` com `ok=True` produzido pelo dimensionamento (erros por
  `design_id` quando falha); planta-baixa sobre arquitetura com ATENDE.
  Nenhuma disciplina com dado real esta sem veredito (o caminho
  "indisponivel" abaixo e provado por injecao).
- `BASELINE_G83`: intacto e verde — o WIP nao o tocou
  (`test_guardas_um_eixo_g83.py` fora do diff) e o G155 nao cria guarda de
  um eixo em teste (asserts de substring/parse/hash; o veredito usa
  coordenadas absolutas na producao). O "quebrava antes" do D180 era a
  execucao sobreposta G154+G155 na mesma copia, nao um triado pendente.

**Entregue (fonte unica `veredito_folha_g152`, estendida, nunca copiada).**
- `extrair_veredito` le ATENDE > atende_* > `gate.OK` (fundacao) > `OK`
  (piso/escada/peca) > `ok` (conferencia) > `circuits.ok` com erros por
  `design_id` + designs com conductor/protection OK False (eletrica
  residencial, tudo produzido pelo calculo). Sem chave: DESCONHECIDO.
- Decisao do backlog: disciplina sem veredito no resultado nao ganha
  veredito na folha — a folha declara `VEREDITO NAO DISPONIVEL NO
  RESULTADO - VER MEMORIAL`, sem STATUS (carimbar seria decidir); so o
  parametro ausente (None) sai byte-identico. O caso vai ao verbete (abaixo:
  nenhum com dado real).
- Cada folha do predio/casa aceita `veredito=` e declara na REPROVA a linha
  com todos os gates + `STATUS: REPROVADO - VER MEMORIAL`, so posicionando
  as strings da fonte unica; ATENDE = byte-identico (hash). Posicoes
  conferidas no PNG + estimador `colisoes_de_rotulo_svg` (zero pares
  VEREDITO/STATUS): formas abre faixa propria de 48 px no rodape (a malha
  ocupa a folha toda); coordenacao no vao entre as caixas; fundacao y=100
  (fora dos numeros de eixo); hidraulica y=75; escada y=76; vigas y=75;
  laje abaixo do RESULTADO da peca (y=678). `gerar_*` repassam o veredito
  (ausente = historico silencioso, byte-identico com G143/G149/G138); o
  adapter passa a disciplina explicitamente em todas as pranchas; a casa
  injeta no gerar (primeira faixa livre: 20/56/92 + rodape).
- Completado alem do WIP: as 6 posicoes acima (o WIP colidia em CD-01,
  CO-01, CO-04, HI, IN-03, CO-02 — visto no PNG); a eletrica residencial
  lia por agregacao manual no emissor, agora le o `circuits` pela fonte
  unica; a laje no caminho `paineis` (predio e casa) perdia o veredito —
  `planta_lajes_todos_paineis_svg`/`gerar_planta_laje` repassam; a decisao
  "sem veredito declara indisponivel" nao existia no WIP; isencao com
  motivo para `veredito_folha_g152._altura_svg` no censo G77.
- Primeira corrida do goal (3 failed) acusou o conflito real: o default
  "gerar passa a disciplina" quebrava o byte-identico de
  G143/G149/G138 — voltado a pass-through com o adapter explicito
  (regra conservadora: teste de goal antigo nao se reescreve).

**Testes.** `tests/test_veredito_folha_g155.py` (7): baseline ATENDE
byte-identica; vermelho por injecao em cada disciplina (14 folhas do
predio + casa); fonte unica estendida (literais, com precedencia);
casa por folha; PNG reprovado rasterizado (fitz); zero colisao da marca;
eletrica residencial (`circuits` real: ok byte-identico, reprovado com
design_id, sem circuits indisponivel). Vizinhos: G152, G77 (+1 isencao
motivada), guardas G83, laje, casa-concreto G100, alvenaria G62,
planta-baixa G78, eletrica G99/fase6B, G142, G143/G149/G138/G140, adapter
do predio (21), G102 casa/predio na suite.

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK;
G77, alcancabilidade, guardas D86/G69, disciplina-prancha G103, indice
G91, carimbo-mapa G112, normas-catalogo, galpao-indice G93, suite D164,
auditorias D172/D176/D179, fallbacks G145/G150, titulo G151, veredito
G152, piso G153, estaca G149: verdes. Folha do galpao intocada (sem
portao de auditoria; carimbo do galpao fechado). G102 casa/predio verdes
na suite.

**Suite inteira pelo runner (`-n 3`, codigo final, lida inteira).**
`rc_pytest` 0, **3970 passed, 2 skipped em 1477,4 s** (24 min), 320/320
arquivos, memoria livre minima 207 MB (piso 200 confirmado em 3
amostras, 0 quedas), descendentes [] / [], `quebras` [].

**PNG olhado (reprovada declara, ATENDE limpa):** EL-01/02/03/04,
HI-agua/esgoto/pluvial, IN-01/02/03, CO-04, CO-01 (faixa no rodape),
CO-02, CD-01, quadro-ambientes da casa. G154 visivel na CO-04
(`cob modelo (confirmar)`), intacto.

**Pendencia ao usuario:** nenhuma — toda disciplina com dado real
carrega veredito (medido acima); o caminho indisponivel existe so por
injecao. **Nao feito.** Parar de emitir folha reprovada; decidir gate na
folha; mudar o carimbo do galpao. Nao comecar o G156.

## D182 - G156: a citacao normativa com numero e sem item (2026-09-18) - FECHADO

**Pedido.** BACKLOG-GOALS-G154-G157.md G156, pelo protocolo de execucao em
sequencia (checagem de entrada: `4432af0 G155:` no log, arvore limpa, nenhum
pytest/suite_paralela/freecad rodando). Lente AST das frases que atribuem
numero a NBR, baseline nos dois sentidos, triagem de cada frase contra a
imagem da pagina do acervo; divergencia corrige so a atribuicao (numero
nunca muda) e vai ao verbete como pendencia; sem perguntas no meio.

**Decidido para este goal (backlog):** frase nao conferivel (norma fora do
acervo ou pagina ilegivel) fica como esta, com o motivo; frase de fonte que
nao e NBR (livro, catalogo) fica fora da lente, com a regra escrita no teste.

**Medido.** Heuristica do backlog (literais com `NBR nnnn` + numero, sem
`n.n`/Tabela/Anexo): 25 literais em 21 arquivos na arvore do D179. Na arvore
do G156 (pos-G154/G155) a mesma classe, estendida a comentarios (o achado
F152 e comentario) e a inteiros com unidade, da 70 frases em 43 arquivos +
1 comentario NM 280 (+2 fragmentos multi-linha triados pela lente: 73
itens). A maioria e remissao/titulo/dado de projeto; 20 sao atribuicao de
valor normativo e 2 nao conferiveis (NBR 16401-2 e 16401-3 fora do acervo;
so a parte 1 F077).

**Entregue (lente `tests/test_citacao_norma_g156.py`, 3 testes).** Regra:
literal/comentario com NBR (inclui NM) + valor + sem item reprova, salvo
triado na BASELINE (73 itens: CONFERE/NAO_CONFERIVEL com item+pagina;
DIVERGE com a atribuicao corrigida; REMISSAO/FONTE_NAO_NBR/D179 com motivo
escrito). Sentido 1: frase sem triagem reprova; sentido 2: triagem sem
frase reprova. Vermelho por injecao em tmp_path (literal e comentario,
nomeando arquivo:linha; caso com item passa). `Cap.N` conta como item
(item de livro-fonte: Negrisoli/Mamede).

**Triagem contra a imagem (18 paginas conferidas; numeros identicos).**
CONFERE (item acrescentado): 6123:1988 4.2 c) p.4 (0,613, validacao x3 +
relatorio); 15575-2:2013 7.3.1 p.7 (0,6 mm); 14323:2013 6.3.1 Tab.3 p.13
(gama 1,0/1,10-1,30); 5410:2004 5.3.4.1 p.63 (1,45); 8800:2008 Tab.C.1
p.117 (L/600-800-1000) e Tab.3 p.23 (gama2 1,35); 5626:2020 6.8.3 NOTA
p.21 (3 m/s); 8160:1999 5.1.4.1 p.17 (DN100) e 4.2.3.2 p.4 (2%/1%);
7480:2024 4.1.2 p.3 (CA-25/50/60); 5419-2:2026 5.3 Tab.4 p.27 (RT=1e-5);
7483:2021 4.1.2 p.3 (CP-190); 8681:2025 Tab.1 p.14 + Tab.4 p.15 (vento 1,4)
+ Tab.6 (psi0 vento 0,6) + 5.1.4.2 p.15 (portico 1,40x0,60; fav nao entra).
DIVERGE (so atribuicao; numero e trava intactos): NM 280 -> NM 247-3
Tab.1 p.5 (2,5 mm2 = 3,2-3,9 mm; a 280 Tab.1 p.9 e resistencia 7,41 ohm/km;
_ELETRODUTO_POR_SECAO inalterado); Wenner sai da 15749 (escopo 1.1 nao
cobre; re-atribuido a Negrisoli Cap.11; 7117-1 fora do acervo, ref. na
5419-3:2026); 10 ohm adotado (5419-3:2026 7.1.4 nao exige medicao);
Rippl (15527:2019 4.4.10 nao prescreve metodo; pode ser da ed. 2007);
theta 550/mu 0,6 (14323 Tab.B.6 p.42: 550 C e theta-o,t p/ TRRF 30);
faixa 3,0-5,0 m do incendio (grupo 1 existe no Anexo A Tab.A.1 p.92 da
10897; faixa nao localizada nem na 16981); gama 0,9/1,4 adotados ante
8681 Tab.1 (fav 1,0); psi2 0,2/0,4/0,6 ante 14323 6.3.1 (0,21/0,28/0,42);
10% da cinta (fonte mista 6122/Alonso). NAO_CONFERIVEL: 16401-3 (27n+1,5A)
e 16401-2 (0,335) - partes fora do acervo. Corrigido de quebra o typo
`psic2 * psic2` -> `psi2` no docstring (texto igual ao codigo).

**Testes.** Lente (3, baseline 73 + injecao literal/comentario). Vizinhos:
G65 lastro acusou o `7117` novo sem acervo - re-atribuido via 5419-3 (com
lastro), registro cheio na baseline/aqui; G65 verde sem tocar LACUNAS.
Regra do lote inteira verde (faixa/sequencia/orfas OK; G77, alcancabilidade,
guardas, disciplina-prancha, indice, carimbo-mapa, normas-catalogo,
galpao-indice, suite D164, auditorias D172/D176/D179, fallbacks, titulo
G151, veredito G152, piso G153, estaca G149).

**Suite inteira pelo runner (`-n 3`, codigo final, lida inteira).**
`rc_pytest` 0, **3973 passed, 2 skipped em 1718,9 s** (28 min), 321/321
arquivos, memoria livre minima 94 MB (3 quedas abaixo do piso 200;
`memoria_confirmacao_amostras` 3), descendentes [] / [], `quebras` [].
Primeira corrida do goal (rc 0, mesmos 3973) caiu numa quebra alheia ao
codigo (`.ai-memory.toml`, scaffolding da sessao criado no meio da corrida);
removido o arquivo e rodada de novo, limpa.

**PNG olhado:** PE-HID-02 (quadro com `NBR 5626:2020 6.8.3` e nota
`NBR 8160:1999 5.1.4.1/4.2.3.2`) - texto dentro da folha, carimbo intacto.
Prancha eletrica (nota 6, freecad-only): gerada e verde na suite; mudanca
e so linha de nota, mesmo emissor. 18 paginas de norma vistas na imagem
(F038 p.18 ja conferida no D179, nao relida).

**Pendencia ao usuario:** (1) confirmar 1,4 ante o 1,30 da madeira
(Tab.1) e o par 0,9/1,4 da tesoura/tercas ante Tab.1 (adotados,
conservadores); (2) confirmar o item da faixa 3,0-5,0 m do incendio
(grupo 1 OK no Anexo A); (3) confirmar theta-critica 550/mu 0,6 ante
14323 Tab.B.6; (4) confirmar Rippl ante 15527 (pode ser ed. 2007);
(5) confirmar Wenner ante 7117-1/Negrisoli e o 10 ohm ante 5419-3:2026;
(6) confirmar psi2 0,2/0,4/0,6 ante 14323 6.3.1 e os 10% da cinta
(6122/Alonso). Nenhum numero mudou; as seis seguem declaradas no codigo.
**Nao feito.** Trocar numero para bater com a norma; confiar no OCR sem a
imagem; citar de memoria; renumerar D existentes. Nao comecar o G157.

## D187 - G157: o verbete sem numero e a fase sem linha (2026-09-18) - FECHADO

**Pedido.** BACKLOG-GOALS-G154-G157.md G157, pelo protocolo de execucao em
sequencia (checagem de entrada: `6d3b16d G156:` no log, arvore limpa,
nenhum pytest/suite_paralela/freecad rodando - so uvicorn do Projetor e o
notebooklm-mcp, alheios a este repo). Guarda que confere, para todo goal
fechado no git log desde o G149 (incluindo G154-G157), verbete com numero D
em `04-decisions` e bullet com link em `03-phases`; baseline nos dois
sentidos, vermelho por injecao em `tmp_path`; numerar os verbetes do G149
ao G152 com os proximos D livres, nessa ordem, sem reescrever o conteudo;
conferir os links da wiki; sem perguntas no meio.

**Decidido para este goal (topo do backlog):** os quatro verbetes recebem os
proximos D livres depois do ultimo D existente no momento do G157, na ordem
G149, G150, G151, G152. Imprevisto segue a regra conservadora do protocolo
(segur e registrar, nao parar; escolha vai ao verbete como pendencia).

**Medido (antes de mudar).** `## G149/G150/G151/G152 - ...` sem numero D
(so o G153 virou D178); nenhum dos cinco escreveu no `03-phases` (o D179
escreveu as linhas na auditoria); ultimo D existente: D182 (G156). Nao ha
guarda que cubra isso: o D176 e o D179 acharam a falta lendo o arquivo.
Links `[[04-decisions#D152]]`, `[[04-decisions#D153]]` e
`[[04-decisions#D154]]` nos bullets do G126/G127/G128 sem header `## D`
correspondente (lote G126-G130, fora do escopo desde-G149: vai a pendencia,
nao se renumera nem se reescreve sem decisao).

**Entregue (guarda no teste, precedente G156).** `tests/test_verbete_fase_g157.py`
(3 testes + `confere_verbete_fase` pura): MAPA_GOAL_D (G149:D183, G150:D184,
G151:D185, G152:D186, G153:D178, G154:D180, G155:D181, G156:D182, G157:D187)
com `goals_no_git_log` (parse de `^<hash> G<num>:`); sentido 1 (goal no log
sem MAPA/verbete/bullet+link reprova, nomeando o goal); sentido 2 (MAPA sem
commit - salvo o goal em progresso -, verbete `## D - G>=149` fora do MAPA,
header `## G<num>` sem D, link do bullet sem `## D` reprova). Sem modulo novo
na producao de proposito: modulo so consumido pelo teste seria ilha no
`test_nenhuma_ilha_fora_do_declarado` (precedente G156: a lente mora no
teste); por isso nenhuma baseline de producao muda (sem ilha, sem censo D86,
sem SCRIPTS_AVULSOS, G156/G65/faixa/orfas verdes sem triagem nova).
Numerados os headers (`## D183 - G149:` .. `## D186 - G152:`, resto do titulo
intacto) e linkados os bullets (`([[04-decisions#D183]])` ..
`([[04-decisions#D186]])`); nota do `03-phases` e do `00-index` atualizadas
no passado (eram "sem numero D"). Nenhum `[[04-decisions#G1xx]]` existia,
nenhum link quebrou na renumeracao.

**Testes.** Baseline verde no repo real; vermelho por injecao em `tmp_path`
(header sem D, bullet removido, MAPA com goal inexistente, goal sem MAPA,
verbete orfao, link trocado por D999, carve-out do goal corrente exato nos
dois mundos) + copia limpa sem falso-positivo. Vermelho provado no defeito
real antes de numerar (10 gaps: 8 do G149-G152 + 2 do G157 ainda nao
escrito). Um assert por teste (G97).

**Baselines mudadas com motivo: nenhuma.**

**Portoes tocados + regra do lote.** Varreduras faixa/sequencia/orfas OK;
lote (g77, alcancabilidade, guardas, disciplina-prancha, indice_g91,
carimbo-mapa, normas-catalogo, galpao-indice, suite D164, auditorias
D172/D176/D179, fallbacks, titulo G151, veredito G152, piso G153, estaca
G149, material G154, veredito G155, citacao G156): **218 passed** (serial).
Sem portao do galpao (nenhuma folha tocada) e sem GRUPO_FREECAD (nenhum
freecad subido pelo teste novo).

**Suite inteira pelo runner (`-n 3`, codigo final, lida inteira).**
`rc_pytest` 0, **3976 passed, 2 skipped em 2067,9 s** (34,5 min), 322/322
arquivos, memoria livre minima 173 MB (1 queda de 1 amostra < 200, sem
disparo - G153), descendentes [] / [], `quebras` []. A corrida anterior
(rc 1, 3974 passed + os 2 failed) tinha como unicos fails a guarda nova
acusando este verbete ainda nao escrito; com o verbete e o bullet no lugar
- a arvore que esta corrida viu -, tudo verde. Codigo identico nas duas
corridas (so wiki/prosa mudou entre elas, precedente D178).

**Pendencia ao usuario:** (1) os links `[[04-decisions#D152]]`,
`[[04-decisions#D153]]` e `[[04-decisions#D154]]` nos bullets do G126, G127
e G128 nao tem verbete `## D152/D153/D154` (o lote G126-G130 registrou
D152-D157 no indice mas os verbetes do G126-G128 nao levaram esses
numeros); fora do escopo deste goal (desde o G149) - confirmar se ganham
numeracao nova ou se os links caem. Nenhum numero mudou neste goal.

**Nao feito.** Reescrever verbete antigo; renumerar D ja existentes; tocar
folha ou codigo de producao; mudar numero, veredito, default ou trava;
criar backlog novo. Nao comecar goal novo (a fila G154-G157 fecha aqui).

## D188 - G159: o codigo de producao que entra sem deixar registro (2026-09-21) - FECHADO

**Pedido.** BACKLOG-GOALS-G158-G163.md G159. Desvio de entrada registrado: o
backlog manda partir do commit do G158, mas o `git log` nao tem commit
`G158:` (o HEAD e `23a23a9` docs-backlog da fila G158-G163, arvore limpa) -
ou seja, a auditoria G158 ainda nao fechou quando este goal executou. Pela
regra do backlog ("D livres na ordem em que os goals fecharem", ultimo D
D187), o verbete deste goal leva o D188. Nada da auditoria pendente foi
assumido aqui: o que e auditoria segue no G158.

**Medido (antes de mudar).** Quatro commits de 2026-09-19 sem prefixo
`G1xx:` entregaram conta normativa viva: `dc686af` feat(p70, tabelas de
motores completa), `700afd8` feat(p71, rendimento do motor), `6734fc8`
fix(revisao, consolida motores de mesma potencia), `a85bdbe` fix(demand,
cozinha via tabela transcrita). `demanda_residencial_enel.py` tem 600
linhas; `residencial_eletrica.py:16` importa, `:313` e `:355` chamam
`calculate_residential_demand`; o numero chega a folha em
`desenho_eletrico_residencial.py:273-276` (`demanda %s kVA` de
`calculation.demand.final_kva`). Grep por `wki`/`enel`/`demanda_residencial`
em `wiki/*.md`: zero. A guarda do G157 estava verde (casa so prefixo
`G1xx:`); a lente do G156 nao ve (casa so `NBR`, e o modulo cita "WKI").
Censo completo desde o G149 (parte da entrega): 18 commits no intervalo,
11 tocaram producao - 6 goals (G149, G151, G152, G154, G155, G156), 1
auditoria (`6d94510` fix d179) e os 4 WKI. G150, G153, G157 e os 4
docs-backlog nao tocam producao (so teste/lente/wiki), por isso nao entram
no censo. Nenhum outro commit do intervalo entregou numero ao cliente: so
os 4 WKI poem numero na folha.

**O que a conta faz.** `calculate_residential_demand(payload)` (modulo puro,
sem FreeCAD): (a) comodos x modulos kVA (`ROOM_MODULES_KVA`: quarto 1,50,
sala 1,60, banheiro 2,30, cozinha_1 1,50 / cozinha_2 2,10, area_servico 1,90,
outros 0,35; divisor 1,40 com 1 quarto senao 1,20) x fator locacional
(1,00/0,88/0,75/0,55); (b) aquecimento pela TABELA 1 (quantidade x potencia
x fator da faixa); (c) motores pelas TABELAS 2 e 3 por grupo de mesma
potencia, com o maior grupo a 1,0 e os demais a 0,70; (d) iluminacao
especial (kW / fator: incandescente 1,0, vapores 0,9); final = a + maior de
(b,c,d) + 0,70 x demais. **De onde vem (F131,
WKI-OMBR-MAT-18-0263-INBR-R01):** item 6.1 (potencia instalada e rendimento
da placa), 6.2.3.2 (motores de mesma potencia nas TABELAS 2 e 3, PDF p. 14),
6.2.3.3 (iluminacao especial), notes 1 e 2 p. 7 (COZINHA 1 ate 2 quartos,
COZINHA 2 com 3+), TABELA 1 de aquecimento. **O que ela recusa** (erro
estruturado, nunca default): motor bifasico; CV fora da grafia da fonte
(sem interpolar); quantidade nao-inteira ou < 1; consolidado > 10 colunas;
payload sem network/rooms/loads; fator locacional fora da tabela; comodo
fora do contrato; rendimento fora de (0,1]; `factor` arbitrario na
iluminacao especial; rede nao-aerea para o padrao de entrada e
`installed_load_kw` nao-positivo (na `residencial_eletrica`).

**O erro entregue e corrigido.** Antes do `6734fc8`, cada declaracao de
motor virava um grupo proprio na consulta: dois motores de 1 CV trifasicos
em duas linhas somavam 1,52 + 1,06 ~= **2,584 kVA**, onde a coluna de
quantidade 2 da TABELA 2 imprime **2,28 kVA**. A correcao consolida por par
(ligacao, potencia) antes da consulta; a potencia instalada continua por
declaracao (item 6.1: cada motor traz o rendimento da propria placa).
`p70` tirou a tabela de `limited` (1 celula) para completa (370 celulas);
`p71` separou sem-placa (1500 W/CV) de rendimento-da-placa
(CV x 0,736 / rendimento); `a85bdbe` tirou o segundo literal 1,50/2,10 e le
o modulo da cozinha so de `ROOM_MODULES_KVA`. Erro entregue e corrigido sem
D e exatamente o que o registro existe para guardar - por isso vai aqui, e
a afericao celula-a-celula na imagem fica no G161 (nao conferida neste
goal, convencao 17).

**Entregue (guarda no teste, precedente G156/G157).**
`tests/test_censo_producao_g159.py` (5 testes + `censo_de_git` e
`confere_censo` puras): parada fixa `COMMIT_BASE_G149` (hash cheio do commit
do G149, sem "desde sempre"); predicado unico `_e_arquivo_producao` (a regra
do G156, com o test_05 provando a equivalencia e travando que os emissores
G145/G150 nao veem os 3 arquivos WKI - anti-padrao G131); sentido 1 (commit
sem cobertura/isencao reprova nomeando commit+arquivo), isencao sem motivo
reprova, sentido 2 (cobertura de commit inexistente e D sem `## D`
reprovam); cobertura dos 10 (6 goals nos D que o G157 numerou + 4 WKI no
D188) e isencao do `6d94510` com motivo (auditoria D179, nao entrega nova).
Anti-tautologia G91: o censo vem do git e a cobertura do literal, por
argumentos separados. Segui o contrato de manutencao do G157 no mesmo
commit (MAPA ganha `G159: D188`, GOAL_CORRENTE avanca, sem mudar regra de
conteudo). Sem modulo novo na producao (precedente G156/G157: nada de ilha,
nenhuma baseline de producao muda).

**Testes.** Guarda nova (5, baseline + 3 injecoes em repo git de verdade em
`tmp_path` + fonte unica). Vermelho provado no defeito real antes do
verbete (test_01 acusou so o D188 ausente: censo 11/11, WKI 4/4). Regra do
lote verde no codigo final, serial: 198 passed em 265 s (folhas, alcance,
guardas, disciplina, indice, carimbo, normas, galpao-indice, suite D164,
fallbacks, titulo G151, vereditos, citacao G156, verbete G157, censo G159,
estaca G149) + 28 passed em 88 s (auditorias D172/D176/D179, piso G153,
material G154); 3 varreduras (faixa/sequencia/orfas) OK. Sem GRUPO_FREECAD (nenhum
freecad subido pelo teste novo) e sem portao do galpao (nenhuma folha
tocada). Runner integral nao rodado neste goal (nenhum `.py` de producao
mudou - so teste e wiki; a corrida que vale para o codigo commitado segue a
do G158 quando ele fechar).

**Pendencia ao usuario:** (1) o G158 (auditoria do lote G154-G157) ainda nao
fechou - este goal nao auditou os goals, so registrou os commits; (2) as
~476 celulas WKI transcritas seguem sem conferencia na imagem (G161);
(3) a lente do G156 segue so-NBR, as citacoes WKI seguem sem triagem
(G160); (4) a vigencia da WKI R01/2018 (listada Enel-Rio 2026, revisao
posterior nao conferida) segue no G163. Nenhum numero mudou neste goal.

**Nao feito.** Reescrever os verbetes antigos; renumerar D existentes; mudar
a producao do modulo WKI (G160/G161/G162); transformar a isencao em lista
de nomes sem motivo; rodar a auditoria do lote (G158).

## D189 - G160: a lente de citacao que so enxergava NBR (2026-09-21) - FECHADO

**Pedido.** BACKLOG-GOALS-G158-G163.md G160. Estado de partida: `ed13be6`
(G159) no `git log`, arvore limpa.

**Medido (antes de mudar).** `tests/test_citacao_norma_g156.py:42` casava so
`NBR`: as 13 citacoes WKI de `demanda_residencial_enel.py` (`:29`, `:74`,
`:106`, `:146`, `:164`, `:380`, `:431`, `:450`, `:462`, `:473`, `:511`,
`:523`, mais a docstring `:1`) trazem item e pagina e nenhuma estava na
BASELINE. Censo da producao (entrega do goal): 32 frases citam fonte de
conta nao-NBR - 15 WKI (13 no modulo + 2 no `validacao_sistema_g15.py`),
5 CNC/ET-Enel, 5 IEC, 7 ISO/CIE-8995 (5 na `luminotecnica_nbr8995.py` + 1
na folha `techdraw_eletrico.py` + 1 `NBR 8995-1` na docstring; `ISO 5457`
de prancha, `ISO-8601` de data e `piso`/`aviso`/`piece` nunca casam).

**Entregue (mesma lente, nunca copia).** `PAT_FONTE` = `PAT_NBR` + `PAT_CONTA`
(`PAT_WKI` casa `WKI` E `WKI-OMBR-MAT-18-0263-INBR-R01`; `PAT_CNC_ET` casa
qualquer `CNC-...` com ou sem revisao + `ET-123-R01`; `PAT_IEC`; `PAT_ISO_CIE`
exige `8995` ou `CIE` ao lado); `_candidatos_em_texto` continua um so (Tier A:
fonte sem item com valor reprova); `_citacoes_conta_em_texto` + teste novo
(Tier B: TODA frase de conta tem veredicto na BASELINE, mesmo com item);
teste de padrao-vivo (abreviacao E codigo casam; ISO de prancha/data nao)
+ injecao nos dois tiers + isencao livro/catalogo intacta em `tmp_path`.
WKI nunca vai para `FONTE_NAO_NBR`. Pagina do arquivo = pagina da norma no
F131 e no F128 (o rodape numerado coincide com a pagina do viewer).

**Triagem na imagem (todas as 32 vistas; numero nenhum mudou).**

| frase | arquivo:linha | item | pag. arq. | pag. norma | veredicto |
|---|---|---|---|---|---|
| base WKI/Enel (docstring) | demanda_residencial_enel.py:1 | - | - | - | REMISSAO (nomeia a base, sem valor) |
| WKI Tabela 1 (3,5 kW) | demanda_residencial_enel.py:29 | Tabela 1 | 13 | F131 p.13 | CONFERE (limite 3,5 kW; celulas ao G161) |
| WKI TABELA 2 three-phase | demanda_residencial_enel.py:74 | TABELA 2 | 14 | F131 p.14 | REMISSAO (nota de transcricao; celulas ao G161) |
| WKI TABELA 3 single-phase | demanda_residencial_enel.py:106 | TABELA 3 | 14 | F131 p.14 | REMISSAO idem |
| WKI Enel item 6.1 | demanda_residencial_enel.py:146 | 6.1 | 5 | F131 p.5 | CONFERE (Pn x 0,736/eta; sem placa 1500 W) |
| WKI 6.2.3.3 vapor/incand. | demanda_residencial_enel.py:164 | 6.2.3.3 | 8 | F131 p.8 | CONFERE (vapor/0,9; incand. kW=kVA) |
| WKI notes 1 and 2 | demanda_residencial_enel.py:380 | notes 1-2 | 7 | F131 p.7 | CONFERE (COZINHA 1 ate 2 quartos, 2 com 3+) |
| item 6.2.3.2 TABELAS 2-3 | demanda_residencial_enel.py:431 | 6.2.3.2 | 8 | F131 p.8 | CONFERE (100% maior + 70% demais) |
| recusa bifasico | demanda_residencial_enel.py:450 | TABELAS 2-3 | 14 | F131 p.14 | REMISSAO (texto de recusa, sem valor) |
| recusa sem linha exata | demanda_residencial_enel.py:462 | TABELAS 2-3 | 14 | F131 p.14 | REMISSAO idem |
| quantidade >= 1 | demanda_residencial_enel.py:473 | TABELAS 2-3 | 14 | F131 p.14 | CONFERE (colunas 1 a 10) |
| acima de 10 recusada | demanda_residencial_enel.py:511 | TABELAS 2-3 | 14 | F131 p.14 | CONFERE (so colunas 1-10) |
| recusa sem linha (grupo) | demanda_residencial_enel.py:523 | TABELAS 2-3 | 14 | F131 p.14 | REMISSAO idem :462 |
| caso Enel WKI (6 comodos) | validacao_sistema_g15.py:404 | - | 7 | F131 p.7 | REMISSAO (definicao do caso; 1,9 kVA computado) |
| oraculo 8.875 kVA | validacao_sistema_g15.py:413 | - | - | - | REMISSAO (numero do teste, nao da norma) |
| CNC 25-1580 7.8.3 | eletrica_edificio.py:84 | 7.8.3 | 25 | F128 p.25 | CONFERE (7.8.2 a/b: <=75 kW BT, >75 MT) |
| referencia conexao coletiva | eletrica_edificio.py:657 | - | - | - | REMISSAO (referencia, sem valor; 75 kW no :84) |
| aviso sem fator | eletrica_edificio.py:759 | - | - | - | REMISSAO (declara a fonte, sem valor) |
| dado da CONCESSIONARIA | eletrica_edificio.py:25 | - | - | - | REMISSAO (fonte declarada, sem valor) |
| CNC-24-1569-EDBR | entrada_enel_bt.py:14 | Anexos A/C | - | - | REMISSAO (identificador do documento) |
| IEC 60364 (x3) | comissionamento_fv.py:62,90,98 | - | - | - | NAO_CONFERIVEL (60364 fora do acervo; F148=60617) |
| NBR 5444/IEC (x2) | desenho_eletrico.py:9, desenho_svg_base.py:3 | - | - | - | REMISSAO (pratica citada, sem valor) |
| NBR IEC 60898 (x2) | protecao_nbr5410.py:8,25 | - | - | - | REMISSAO (serie citada como input, sem valor) |
| NBR (ISO/CIE) 8995-1 (x5) | luminotecnica_nbr8995.py:5,20,28,67; techdraw_eletrico.py:319 | - | - | - | REMISSAO (base citada, sem valor; F102) |

Celulas impares da fonte preservadas como impresso (vistas p.14):
TABELA 2 15 CV/4 motores = 33,29; TABELA 3 1 1/2 CV/2 motores = 2,53 e
10 CV/7 motores = 33,41 (o codigo as mantem de proposito; afericao ao G161).

**Testes.** Lente 5 passed (3 do G156 intactos + Tier B + padrao-vivo/injecao).
Regra do lote verde no codigo final (so teste + wiki mudaram; producao
intacta, censo G159 inafetado). Segui o contrato do G157 no mesmo commit
(MAPA ganha `G160: D189`, GOAL_CORRENTE avanca, sem mudar regra de conteudo).

**Pendencia ao usuario:** (1) as ~476 celulas seguem transcritas sem
conferencia celula a celula (G161); (2) IEC 60364 citado e fora do acervo -
manter NAO_CONFERIVEL ou adquirir a norma; (3) vigencia da WKI R01/2018
(listada 2026, revisao posterior nao conferida) segue no G163; (4) a tabela
acima entra na decisao do G163. Nenhum numero de conta mudou neste goal.

**Nao feito.** Trocar numero para bater com a norma; extracao de texto no
lugar da imagem; citar de memoria; mandar WKI para FONTE_NAO_NBR.

## D190 - G161: as 476 celulas WKI conferidas na imagem (2026-09-21) - FECHADO

**Pedido.** BACKLOG-GOALS-G158-G163.md G161. Estado de partida: `25b33b5`
(G160) no `git log`, arvore limpa.

**Medido (antes de mudar).** `demanda_residencial_enel.py`: `_MOTOR_TABLE_KVA`
370 celulas, `_HEATING_TABLE` 90, `ROOM_MODULES_KVA` 7, `LOCATION_FACTORS` 4,
`_SPECIAL_LIGHTING_POWER_FACTORS` 4, `_MOTOR_TABLE_MAX_QUANTITY` 1,
`_MOTOR_NO_PLATE_KW_PER_CV` 1 = ~476, com comentarios "complete source
transcription" (`:74`, `:106`) - transcricao, nao conferencia. `6734fc8`
prova o segundo modo de erro (leitura por quantidade consolidada, 2,584 kVA
onde a coluna qtd 2 imprime 2,28). Zero afericao contra exemplo resolvido
(grep `exemplo`/`anexo`/`worked` no teste de demanda = 0). F131 e PDF digital
mas a conferencia e na imagem (extracao de tabela embaralha coluna).

**Censo na imagem (F131, paginas abertas como imagem).** 476/476 conferidas,
0 divergencias:
- TABELA 2 + TABELA 3, p.14: 370/370. Coluna de quantidade 1..10 conferida
  primeiro (onde morava o `6734fc8`). Anomalias SÃO DA FONTE e foram mantidas:
  tri 15 CV/qtd 4 = 33,29; mono 1 1/2 CV/qtd 2 = 2,53; mono 10 CV/qtd 7 = 33,41;
  mais tri 3 CV/qtd 7 = 13,13; tri 5 CV/qtd 6 = 18,86; tri 150 CV/qtd 3 = 263,45;
  mono 12 1/2 CV/qtd 4 = 34,03 (todas como impresso).
- TABELA 1, p.13: 90/90 (30 linhas x minimo + 2 fatores). Faixas "26 A 30",
  "31 A 40", "41 A 50", "51 A 60", "61 OU MAIS" = minimos 26/31/41/51/61.
- Soltas: comodos p.6-7 (1,50/1,60/2,30/1,50/2,10/1,90/0,35); localizacao
  6.2.2.2 p.7 (1/0,88/0,75/0,55); iluminacao 6.2.3.3 p.8 (vapor /0,9,
  incandescente kW=kVA); item 6.1 p.5 (sem placa 1500 W/CV).
- Leitura: motores 6.2.3.2 p.8 consolidam mesma potencia (100% maior + 70%
  demais); aquecimento Nota 1 p.13 NÃO consolida (cada tipo separado, soma) -
  o Exemplo 1 prova (3,52 + 1,20).
- Exemplo resolvido EXISTE (o backlog marcou "nao medido"): 6.6.1 EXEMPLO 1,
  p.28-30 (casa Santa Rosa/Niterói, Dc = 23,69 kVA). Nao inventado.

**Entregue.** `tests/test_wki_transcricao_g161.py` (convencao 17: a proxima
edicao nao apaga): literais ESPERADO_* independentes vistos na imagem
(convencao 5: nada importado do modulo); `confere_transcricao` acusa por parte
(convencao 7); test_01 baseline 476 verde; test_02 injecao em `tmp_path` por
parte (tri/mono/aquecimento/comodos/localizacao/iluminacao/escalares) + copia
limpa sem falso-positivo; test_03 fixture EXEMPLO 1 (a=14,67 b=4,72 c=4,48
d=1,67 final=23,69); test_04 leitura consolidada (motor 1+1 CV = 2,28) e recusa
(consolidado >10), aquecimento soma sem consolidar (2x4,4 = 2x3,52) e recusa
(qtd 0). Nenhum numero de producao mudou (0 divergencias, nada a trocar).
Contrato do G157 no mesmo commit (MAPA ganha `G161: D190`, GOAL_CORRENTE
avanca, sem mudar regra de conteudo).

**Pendencia ao usuario:** nenhuma linha de divergencia vai a tabela do G163
(0 divergencias). Ficam registradas as 7 celulas anomalas impressas pela fonte
e mantidas acima - sao CONFERE com a pagina, nao pendencia de numero. Demais
pendencias (vigencia WKI R01/2018, IEC 60364) seguem no G163.

**Nao feito.** Interpolar valor nao impresso (`:462`/`:523` mantidos);
arredondar para bater; conferir por extracao de texto; aceitar a tabela porque
os testes passam (os testes vinham da mesma transcricao).

## D191 - G162: a demanda que chegava a folha como um numero sem origem (2026-09-21) - FECHADO

**Pedido.** BACKLOG-GOALS-G158-G163.md G162. Estado de partida: `f093b4b`
(G161) no `git log`, arvore limpa.

**Medido (antes de mudar, por injecao, conta intacta).**
`desenho_eletrico_residencial.py:273-276` imprimia so
`"demanda %s kVA" % final_kva`, sem fonte (WKI/F131), item, fator locacional
ou composicao. O `_num` (`:175-178`) declara a ausencia (certo, intocado).
A folha sabia reprovar circuitos (`_reprovado` `:181`, REPROVA em `:308`,
`:367`, `:412`, `:593`, fonte unica em `:630`). As recusas da demanda
morriam no resultado: motor bifasico / sem linha exata / qtd > 10 davam
ok=False com `calculation` PRESENTE (numero so-dos-comodos) e a folha
imprimia o numero como se ATENDESSE (`extrair_veredito(circuits)` =
(True, []), silencio); fator locacional fora da tabela dava `calculation`
vazio e a folha saia `demanda A CONFIRMAR kVA` sem dizer por que (G106).

**Entregue (fonte unica, nunca copia).**
`demanda_residencial_enel.fonte_demanda/linha_fonte_demanda` +
`calculation["fonte"]` (codigo, acervo F131, itens 6.1/6.2.3.2/6.2.3.3,
notas 1-2 p.7/TABELA 1, fator usado - G154/G131); `residencial_eletrica`
grava `calculation["demand_errors"]` (vale quando o numero falta; a segunda
chamada le do mesmo modulo puro, sem divergir); `veredito_folha_g152`
ganha `gates_demanda` lido em `extrair_veredito`
(`demanda-motor-bifasico`, `demanda-motor-sem-linha`,
`demanda-motor-qtd-acima-10`, `demanda-fator-locacional`,
`demanda-<code>`); o unifilar declara a fonte em faixa propria (ybus-32,
sem colisao no estimador G129) e a recusa pelo veredito. A folha nunca
para de sair, nunca decide gate, o numero nao muda e o carimbo nao e
tocado. Lente G160: +1 triagem (o codigo do documento, CONFERE catalogo
F131); comentario novo sem token de fonte.

**Testes.** `tests/test_demanda_folha_g162.py` (7): ok byte-identica (hash
cru == gerado) com fonte; vermelho por injecao nas 4 recusas pela porta do
adaptador (gates distintos) + bifasico pela porta da casa composta
(convencao 11); fonte unica em literais a mao; numero intocado e mesma
composicao nas duas chamadas; manifesto com unifilar+quadro e titulo;
PNG das duas folhas (artefato em tmp_path). Regra do lote verde no codigo
final (folhas, alcance, guardas, disciplina, indice, carimbo, normas,
galpao-indice, fallbacks, titulo, vereditos, citacao, verbete, censo,
estaca, piso, auditorias D172/D176/D179; 3 varreduras OK) + G102 casa
verde (10 passed, menos o portao do galpao, so na auditoria). Runner
integral: `rc_pytest` 0 e `quebras` vazio (resumo.json).

**PNG olhado.** `unifilar-com-demanda.png` (63 901 bytes) e
`unifilar-demanda-recusada.png` (75 234 bytes): as duas renderizam; a
recusada declara `VEREDITO: REPROVADO em demanda-motor-bifasico` + STATUS
na faixa de fallback do G155 (o estimador acusa encosto no titulo
centrado - comportamento pre-existente das folhas residenciais reprovadas,
igual aos gates de circuito; ficou registrado e visivel para o olho).

**Pendencia ao usuario:** nenhuma linha nova vai a tabela do G163 (nenhum
numero mudou). Fica o convite de olhar os dois PNG acima e dizer se a
faixa de fallback do veredito nas folhas residenciais deve ganhar faixa
propria (como a planta de formas) em goal futuro - sem mudar nada aqui.

**Nao feito.** Parar a folha na recusa; decidir gate na folha; mudar o
numero; tocar o carimbo (G151); interpolar valor nao impresso.

## D192 - G163: a tabela de decisao das sete pendencias e dos links sem verbete (2026-09-21) - FECHADO

**Pedido.** BACKLOG-GOALS-G158-G163.md G163. Estado de partida: `8123f70`
(G162) no `git log`, arvore limpa. Entregar a tabela unica de decisao das
pendencias empilhadas nos verbetes (D182 seis, D187 links, D179 FS 3,0,
G160/G161, vigencia WKI), cada linha conferida na imagem da pagina, com a
recomendacao conservadora ao lado. Nenhum numero, veredito, default ou
trava muda neste goal.

**Medido (antes de mudar).** D182 (`:5517-5523`): seis pendencias, todas
declaradas no codigo com "adotado"/"confirmar"/"CONFIRMAR", nenhuma trava
nada (a lente `test_citacao_norma_g156.py` as carrega como
CONFERE-parcial/DIVERGE com o motivo escrito). D187 (`:5597-5602`): os
links `[[04-decisions#D152]]`, `[[04-decisions#D153]]` e
`[[04-decisions#D154]]` nos bullets do G126/G127/G128 (`03-phases.md`
`:753,:755,:757`) nao resolvem: os verbetes existem mas como headers
compostos `## D152/G126` (`:2266`), `## D153/G127` (`:2354`) e
`## D154/G128` (`:2421`), cuja ancora nao e `#D152/#D153/#D154`. D179
(`:5265-5267`): FS 3,0 decisao (a) manter adotado e declarado
(2026-09-17). G160 (D189): 0 divergencias; IEC 60364 NAO_CONFERIVEL.
G161 (D190): 0 divergencias; 7 celulas anomalas CONFERE-como-impresso.
Fontes: catalogo F131 = `listada_enel_rio_2026` (listada, nao vigencia
conferida); 7117-1 e 60364 ausentes do catalogo; 16401-2/3 ausentes (so
F077 parte 1); 15527 no acervo e ed. 2019; 5419-3 no acervo e ed. 2026
(igual a citada).

**Entregue (tabela unica, 9 paginas vistas na imagem neste goal + F038
p.18 vista no D179).** Legenda: DIVERGE-adotado = numero do codigo difere
da pagina e esta MAIS seguro (nao e erro); DIVERGE-parcial = parte confere,
parte nao localizada; NAO_CONFERIVEL = fica como esta, com o motivo.

| # | frase (arquivo:linha) | norma / item | pag. acervo (imagem vista) | o que o codigo usa | o que a pagina diz | veredito | recomendacao conservadora |
|---|---|---|---|---|---|---|---|
| 1a | `1,4.(G+Q) (NBR 8681:2025 Tab.1: madeira desf 1,30 - adotado 1,4; confirmar)` (telhado_casa_madeira.py:1195) | NBR 8681:2025 Tab.1 | p.14 (F101) | 1,4 desf na madeira | Tab.1 Normal: pre-moldada/madeira desf 1,30, fav 1,0 | DIVERGE-adotado (1,4 > 1,30, mais seguro) | manter 1,4 declarado; confirmar item |
| 1b | `gamma_g do peso permanente (NBR 8681:2025 Tab.1: fav 1,0, adotado 0,9 conservador p/ uplift; desf 1,25-1,50, adotado 1,4)` (tesoura.py:152-158); `gamma_g FAVORAVEL: adotado 0,90` (tercas_nbr14762.py:24,220) | NBR 8681:2025 Tab.1 | p.14 (F101) | 0,9 fav / 1,4 desf por sentido do vento | Tab.1 Normal: fav 1,0 (todas); desf 1,25-1,50 conforme tipo | DIVERGE-adotado no fav (0,9 < 1,0, mais seguro p/ uplift); desf 1,4 CONFERE na faixa | manter 0,9/1,4 declarados; confirmar item |
| 2 | `plasticos/texteis sinteticos empilhados, 3,0 m < H <= 5,0 m, risco extraordinario grupo 1 (NBR 10897:2014 Anexo A Tab.A.1: o grupo; faixa de altura a confirmar - ver NBR 16981)` (incendio_edificio.py:120-122) | NBR 10897:2014 Anexo A Tab.A.1; NBR 16981:2021 (busca) | p.92 (F070, grupo 1 existe); 16981: 5 ocorrencias de "3,0 m" (Anexo B), nenhuma e o criterio de velocidade | grupo 1 + faixa 3,0-5,0 m p/ velocidade rapida | Tab.A.1 p.92: "Risco extraordinario - Grupo 1" existe; a faixa 3,0-5,0 m NAO foi localizada na 10897 nem na 16981 | DIVERGE-parcial (grupo CONFERE, faixa nao localizada) | manter declarado "a confirmar"; confirmar item da faixa |
| 3 | `theta_critica ausente -> assumindo 550 C (mu~0,6; NBR 14323:2013 Tab.B.6: 550 C e o theta-o,t p/ TRRF 30, nao theta-critica - confirmar)` (projeto_spec.py:489-493); `[DEFAULT - CONFIRMAR: theta_critica = 550 C (mu~0,6; ...)]` (rodar_galpao.py:1547-1550, comentario :1533-1535) | NBR 14323:2013 Tab.B.6 | p.42 (F116): Tab.B.6, TRRF 30 -> theta-o,t 550 C | 550 C como theta-critica default (mu~0,6), flagado CONFIRMAR | 550 C e o theta-o,t p/ TRRF 30 (parametro da formula de B.3.2.2.1), nao theta-critica p/ mu 0,6 | DIVERGE-parcial (numero certo na tabela errada) | manter default flagado; confirmar com o responsavel |
| 4 | `Dimensiona a cisterna de reuso pelo METODO DE RIPPL (balanco de massa; NBR 15527:2019 4.4.10 nao prescreve metodo - pode ser da ed. 2007; confirmar)` (esgoto_reuso.py:93-94; metodo :126) | NBR 15527 4.4.10 | p.6 arq (F069, ed. 2019 no acervo): 4.4.10 sem prescrever metodo | Rippl (balanco de massa) atribuido a 15527 | 4.4.10: "dimensionado com base em criterios tecnicos, economicos e ambientais" - nenhum metodo prescrito; Rippl pode ser da ed. 2007 | DIVERGE-atribuicao (edicao a confirmar) | manter metodo declarado; confirmar se Rippl e da ed. 2007 |
| 5a | `RESISTIVIDADE aparente pelo metodo de WENNER (norma de resistividade do solo fora do acervo - a NBR 5419-3:2026 referencia a 7117-1; base: Negrisoli Cap.11 - confirmar)` (aterramento_nbr15749.py:6-11, docstring :39-43) | NBR 15749:2009 1.1; NBR 7117-1 (fora do acervo); Negrisoli Cap.11 | p.1 (F059, escopo 1.1); catalogo: 7117 ausente | Wenner re-atribuido a Negrisoli Cap.11 | 1.1: escopo = medicao de resistencia de aterramento e de potenciais - NAO cobre resistividade Wenner | DIVERGE re-atribuido (saiu da 15749; 7117-1 fora do acervo) | manter base Negrisoli declarada; confirmar 7117-1 ou adquirir a norma |
| 5b | `LIMITE recomendado: R <= 10 ohm adotado (SPDA/subestacao); ... A NBR 5419-3:2026 7.1.4 nao exige medicao de resistencia - confirmar o 10 ohm` (aterramento_nbr15749.py:17-19,27-28; `R_MAX_SPDA = 10.0` :34; techdraw_eletrico.py:324; desenho_eletrico.py:115) | NBR 5419-3:2026 7.1.4 | p.45 (F062, ed. 2026 = citada) | 10 ohm adotado como limite | 7.1.4: "Nao e necessaria a realizacao de medicao de resistencia de aterramento para a verificacao da eficacia do SPDA" - nenhum 10 ohm exigido (era da edicao anterior/pratica) | DIVERGE-adotado | manter 10 ohm adotado; confirmar item |
| 6a | `psi2 = 0,2 (sem predominancia), 0,4 (concentracao), 0,6 (arquivos)` (fogo_nbr14323.py:79-83, default 0.4) | NBR 14323:2013 6.3.1; NBR 8681:2025 Tab.6 nota c | p.13 (F116): 6.3.1 traz 0,21/0,28/0,42; p.16 (F101): Tab.6 psi2 0,3/0,4/0,6 com nota c (x0,7 no fogo) | 0,2/0,4/0,6 sem a reducao x0,7 | 6.3.1 ja embute a reducao (0,3x0,7=0,21; 0,4x0,7=0,28; 0,6x0,7=0,42) | DIVERGE-adotado (sem reduzir = mais carga = mais seguro) | manter 0,2/0,4/0,6 declarados; confirmar item |
| 6b | `dimensiona-se a CINTA TRANSVERSAL, para a excentricidade executiva acidental (>= 10% da carga vertical, NBR 6122 / Alonso)` (rodar_galpao.py:937; `N_cinta = 0.10 * N_pilar` :942) | NBR 6122 / Alonso (livro) | OCR F038: as ocorrencias de "10 %" sao outras (majoracao, diagramas); item nao localizado; Alonso fora da lente (livro) | 0,10 x N_pilar | item da norma nao localizado | DIVERGE-fonte-mista (norma + livro, sem item) | manter 0,10 declarado; confirmar fonte |
| 7 | FS 3,0 da estaca (`estaca_parametros_g143.ORIGEM_FS_ADOTADO = "fs_adotado_D38"`, `projeto_spec.validar`) | NBR 6122:2022 6.2.1.2.1 | p.18 (F038, vista na imagem no D179; OCR: FS 2,0 semiempirico) | 3,0 adotado (D38), trava do `validar` intacta | 6.2.1.2.1: FS 2,0 no semiempirico (1,6 com prova, 6.2.1.2.2); 3,00 e da Tab.1 de fundacao rasa | DECIDIDO (a) manter adotado e declarado, 2026-09-17 (D179 :5265-5267) | registro; nenhum goal deste arco muda o numero ou a trava |
| 8 | links `[[04-decisions#D152]]`, `[[04-decisions#D153]]`, `[[04-decisions#D154]]` (03-phases.md :753,:755,:757, bullets G126/G127/G128) | indice do lote G126-G130 (D152-D157) | - (link quebrado, nao pagina) | links apontam `#D152/#D153/#D154` | verbetes existem como `## D152/G126` (:2266), `## D153/G127` (:2354), `## D154/G128` (:2421): a ancora `#D152` nao resolve (header composto) | link sem verbete correspondente | (a) criar D novos e renomear os links; (b) corrigir os 3 links para as ancoras existentes; (c) deixar como esta |
| 9 | G160 (D189): 32 frases triadas; IEC 60364 x3 (comissionamento_fv.py:62,90,98) | IEC 60364 | NAO_CONFERIVEL: fora do acervo (F148 = 60617, F149 = 60417; catalogo) | citado sem valor | norma ausente | NAO_CONFERIVEL com motivo | manter NAO_CONFERIVEL ou adquirir a norma |
| 10 | G161 (D190): 476/476 celulas vistas; 7 anomalas (tri 15 CV/qtd 4 = 33,29; mono 1 1/2 CV/qtd 2 = 2,53; mono 10 CV/qtd 7 = 33,41; tri 3 CV/qtd 7 = 13,13; tri 5 CV/qtd 6 = 18,86; tri 150 CV/qtd 3 = 263,45; mono 12 1/2 CV/qtd 4 = 34,03) + EXEMPLO 1 (6.6.1 p.28-30, Dc 23,69 kVA) | WKI F131 p.5-8,13-14,28-30 | vistas na imagem no G161 | mantidas como impresso | sao DA FONTE | 0 divergencias (CONFERE-como-impresso, nao pendencia de numero) | registro; nada a decidir |
| 11 | vigencia da WKI-OMBR-MAT-18-0263-INBR-R01 | catalogo F131 | capa vista: Instrucao de Trabalho no. 263, Versao no.01, data 02/03/2018; catalogo = `listada_enel_rio_2026` | R01/2018 em uso | "listada em 2026", nao "vigencia conferida" | NAO_CONFERIVEL no acervo (depende de consulta externa a listagem Enel-Rio) | confirmar se substituida por revisao posterior |

**Testes.** Contrato do G157 no mesmo commit (MAPA ganha `G163: D192`,
GOAL_CORRENTE avanca, sem mudar regra de conteudo). Regra do lote verde
no codigo final + lente G156/G160 (nenhuma frase nova: nenhum `.py` de
producao mudou). Runner integral nao rodado neste goal (nenhum `.py` de
producao mudou - so teste-guarda e wiki; precedente G159).

**Suite.** Nenhum numero de conta mudou: nenhum `.py` de producao tocado
neste goal (`git status` so wiki + MAPA). A corrida que vale para o codigo
commitado segue a do G162.

**PNG olhado (9 paginas, rendidas do PDF a 130 dpi e vistas na imagem):**
8681 Tab.1 p.14 (madeira desf 1,30 / fav 1,0); 8681 Tab.6 p.16 (psi2
0,3/0,4/0,6); 14323 6.3.1 p.13 (0,21/0,28/0,42); 14323 Tab.B.6 p.42
(theta-o,t 550 p/ TRRF 30); 10897 Tab.A.1 p.92 (Grupo 1 existe); 15749
1.1 p.1 (escopo sem Wenner); 5419-3 7.1.4 p.45 (sem exigir medicao);
15527 4.4.10 p.6 arq (sem prescrever metodo); WKI capa (R01 02/03/2018).
F038 p.18 (FS 2,0) vista na imagem no D179, nao relida. 16981: busca por
"3,0 m" (5 ocorrencias no Anexo B, nenhuma e o criterio de velocidade) -
a ausencia da faixa e corroborada por busca, nao por imagem pagina a
pagina.

**Pendencia ao usuario (lista fechada, item a item - a entrega deste
goal):** (1a) manter 1,4 ante o 1,30 da madeira; (1b) manter 0,9/1,4 ante
Tab.1 (fav 1,0); (2) o item da faixa 3,0-5,0 m (grupo 1 OK, faixa nao
localizada); (3) o default 550/mu 0,6 ante Tab.B.6 (e theta-o,t p/ TRRF
30); (4) o Rippl ante a 15527:2019 (pode ser ed. 2007); (5a) o Wenner ante
Negrisoli Cap.11 (7117-1 fora do acervo); (5b) o 10 ohm ante 5419-3:2026
7.1.4 (nao exige); (6a) o psi2 0,2/0,4/0,6 ante 6.3.1 (0,21/0,28/0,42 sem
o x0,7); (6b) os 10% da cinta (item nao localizado, fonte mista
6122/Alonso); (7) FS 3,0: ja decidido (a), so registro; (8) links
D152/D153/D154: (a) numeracao nova, (b) corrigir para as ancoras
existentes, ou (c) deixar como esta; (9) IEC 60364: manter
NAO_CONFERIVEL ou adquirir; (10) 7 celulas anomalas: registro, nada a
decidir; (11) WKI R01/2018: confirmar se substituida.

**Nao feito.** Decidir qualquer linha pelo usuario; trocar numero para
bater com a norma; reescrever verbete antigo; renumerar D existentes;
abrir goal novo a partir da tabela.

## D193 - Plano de 2026-10-08, Fases 1 e 2: o motor sem FreeCAD provado e o calculo gravado no IFC (2026-10-08) - FECHADO

**Pedido.** `decisoes-arquitetura-projetos.md` (raiz do repo, decisao do
usuario em 2026-10-08): o sistema passa a ser ferramenta interna para vender
o PROJETO; o motor de calculo nao pode importar FreeCAD (Fase 1) e o galpao
sai em IFC direto dos dados do motor, com classes, perfis reais, materiais e
resultados de calculo em property sets (Fase 2). Este verbete nao e de goal
`G<num>`: o arco de goals G/D fica congelado ate a entrega do galpao.

**Medido (antes de mudar).** Fase 1: por AST, 12 dos 233 modulos de
`galpao_fw` citam o FreeCAD (`build_galpao`, `build_concreto`,
`build_eletrico`, `build_federado` e os oito `techdraw_*`), e so
`build_galpao` importa no topo; nenhum modulo de calculo importa um deles ao
carregar. Sonda viva (subprocesso com FreeCAD/Part/TechDraw/PySide bloqueados
no `sys.meta_path`): 231 de 233 importam; as duas excecoes sao
`build_galpao` (esperada) e `casa_residencial_sintetica`, que so importa
depois de `project_loop` (import circular ja existente, sem relacao com o
FreeCAD). `tools_probe_pe13` sobe um `freecad.exe` ao ser importado (script
sem guarda `__main__`, ja declarado SCRIPT AVULSO). Fase 2: `rodar_tudo` com
`com_3d=False` no spec de teste `projects/galpao-sjb/project-spec-framework-
teste.json` (dados sinteticos, `not_real_engineering_input`) gerou os dois
IFC em 40,5 s sem FreeCAD carregado: fisico com 16 IfcColumn, 37 IfcBeam,
166 IfcMember, 184 IfcPlate, 16 IfcFooting, 480 IfcMechanicalFastener, perfis
`IfcIShapeProfileDef` (HEA240/IPE330/HEA160), 0 apontamento no
`ifcopenshell.validate` - e **0 IfcMaterial, 0 IfcPropertySet**. Analitico:
4 apontamentos `Attribute not optional` (um por `IfcStructuralCurveMember`,
faltava `Axis`, obrigatorio no IFC4).

**Entregue.**
- `tests/test_motor_sem_freecad.py` (so teste): medida estatica (quem cita o
  FreeCAD tem de estar em `SAIDA_FREECAD`, nos dois sentidos) e medida viva
  (todo modulo nao-avulso importa com o FreeCAD bloqueado, menos
  `IMPORTA_NO_TOPO`); vermelho por injecao dos dois medidores (import tardio
  em funcao para a AST; import de topo, em cadeia e dinamico via `importlib`
  para a sonda - o dinamico a AST nao ve).
- `ifc_emit.py`: `membros_do_spec` chama `_anotar_calculo`, que grava em
  coluna (`C<n>`), viga do portico (`V<n>`) e fundacao o material declarado
  e o pset `Calc_VerificacaoEstrutural` (perfil adotado e inicial, classe do
  aco com o par fy/fu de `acos.propriedades`, Nsd/Vsd/Msd e combinacao
  governante, utilizacao, veredito do aco; na fundacao: tipo, utilizacao,
  fck). So copia o que o calculo deixou em `spec.estrutura`: chave ausente
  fica fora do pset; sapata sem `fundacao.fck` nao ganha concreto.
  `emitir_ifc` ganha `_pset`/`_assoc_calculo` (chave `propriedades` do
  membro; `Pset_Armadura` passa pelo mesmo `_pset`, mesmo resultado).
  `emitir_ifc_analitico` grava `Axis` (0,0,1: portico no plano XY).
- Depois: no mesmo spec de teste, 32 elementos com `Aco MR250`, 16 com
  `Concreto C25`, 48 psets (16 coluna + 16 viga + 16 fundacao), 0
  apontamento de validacao nos dois arquivos.
- `tests/test_ifc_emit.py`: quatro testes (calculo e material no portico;
  so portico e fundacao levam o pset; dado ausente fica fora; os dois
  arquivos validam e toda barra analitica tem `Axis`).

**Decisoes tomadas sem o usuario (reversiveis).** (1) Nome do pset sem o
prefixo `Pset_`, que o buildingSMART reserva aos psets padronizados (os
`Pset_Armadura`/`Pset_SecaoAnalitica` antigos ficam como estao). (2)
Escoras, cumeeiras, tercas, tirantes e chapas seguem sem material e sem
pset: o spec nao guarda esforco proprio deles, e a classe do aco do portico
nao vale para chumbador nem para perfil formado a frio. (3) Nenhuma citacao
de norma entra no pset (a lente de citacao cobra conferencia de cada uma).

**Nao feito.** Empacotar o motor (`pyproject`, imports com nome de pacote):
os 233 modulos usam import plano, e renomear tudo nao aproxima a entrega do
galpao. Entradas e saidas tipadas (dataclass/pydantic). Abrir o IFC num
visualizador externo (so `ifcopenshell.validate`). **O criterio de pronto da
Fase 2 fala do galpao do cliente: `projects/galpao-sjb/project-spec.json`
segue bloqueado por 9 campos sem dado real (comprimento, vao, pe-direito e
as seis disciplinas); o IFC entregue aqui e o do spec de teste.**

## D194 - Plano de 2026-10-08, Fases 1, 3 e 4: camada rapida medida, teste do Bonsai e prancha DXF (2026-10-08) - FECHADO

**Pedido.** `decisoes-arquitetura-projetos.md`: separar a suite em camada
rapida (motores e modelo, poucos minutos na maquina de 8 GB) e lenta (Fase
1); testar o Blender + Bonsai com seis criterios e entregar relatorio (Fase
3); exportar DXF editavel em espaco de papel, com escala e folha escolhidas
sozinhas, viewport, carimbo como bloco, camadas por disciplina e estilo fixo
de cota (Fase 4).

**Medido (antes de mudar).** Suite inteira no commit do D193
(`tools/suite_paralela.py -n 2`, com junit): 4020 testes, 0 falha, 2
pulados, 1535 s de parede, 3044 s somados em 326 arquivos (maquina
carregada: o teste do Bonsai rodou junto e a memoria livre desceu a 61 MB,
sem quebra). 61 arquivos somam 10 s ou mais e concentram 2676 s; os 263
restantes fora do grupo do FreeCAD somam 368 s. Linha de base antes de
qualquer mudanca (commit `a1e8f0e`): rc 0 em 1512 s. Bonsai: nao instalado;
Blender 5.2.1 LTS instalado; sem Inkscape; sem ODA File Converter. O
`requirements.txt` citava um `dxf_vistas.py` que nao existe; nenhum modulo
de `galpao_fw` importava `ezdxf`.

**Entregue.**
- Fase 1: `tests/camada_lenta.py` (61 arquivos com o tempo medido, corte de
  10 s; quem sobe o FreeCAD entra por `censo_freecad.GRUPO_FREECAD`, fonte
  unica); `tests/conftest.py` marca `slow`; `pytest.ini` declara o marcador;
  `tools/suite_rapida.py` roda `-m "not slow"` e reprova por orcamento de
  parede (600 s) ou por arquivo que dobra o corte;
  `tests/test_camada_rapida.py` cobra a lista (isencao morta, FreeCAD dentro,
  guardas da fase na camada rapida) e injeta os dois defeitos no medidor do
  runner. Medido: camada rapida = 3173 testes em 265 arquivos, **212 s de
  parede** (`-n 2`); lenta = 862 testes.
- Fase 3: `docs/fase3-bonsai/` (relatorio com os seis criterios, dois
  scripts, tres folhas A1 em PDF e PNG, render). Bonsai, Inkscape 1.4.4 e
  ODA File Converter instalados na maquina para o teste.
- Fase 4: `dxf_prancha.py` (SCRIPT AVULSO, declarado em
  `test_alcancabilidade.SCRIPTS_AVULSOS`): le o SVG de desenho que o
  `ifcopenshell.draw` escreve, leva a geometria ao espaco do modelo em mm
  reais por camada de disciplina (corte em 0,50 mm), grava cada cota como
  entidade DIMENSION que mede a geometria, e cria uma folha por vista no
  espaco de papel com a maior escala entre 1:50, 1:75 e 1:100 que cabe na
  menor folha entre A3, A2 e A1, viewport nessa escala e carimbo como bloco
  com oito atributos. `tests/test_dxf_prancha.py`: 15 testes com SVG escrito
  a mao (sem Blender). No galpao do spec de teste: 6 folhas (corte e
  elevacao frontal 1:50 A1; plantas e elevacao lateral 1:75 A1), 7091 linhas,
  30 cotas, auditoria do ezdxf sem erro, cota = distancia entre os pontos
  medidos nas 30. DWG pelo ODA File Converter 27.9.0 (AutoCAD 2018, auditoria
  ligada, sem arquivo de erro); convertido de volta, as 6 folhas, as 7091
  linhas, as 30 cotas, a viewport 1:75 e o carimbo estao la.

**Decisoes tomadas sem o usuario (reversiveis).** (1) Corte da camada lenta
em 10 s por arquivo, medido com a maquina carregada. (2) Folga de 2x no
runner: cinco arquivos de 6 a 9 s numa corrida somaram de 11 a 14 s na
seguinte, e sem folga o runner reprovava por ruido. (3) Vista que nao cabe
em A1 a 1:100 cai em escala de escape (1:125 a 1:500) e o resumo diz
`escala_de_escape`. (4) Margens, carimbo, altura de texto e espessuras do
DXF sao ADOTADOS e estao declarados no cabecalho do modulo: a norma de
desenho tecnico nao esta na biblioteca de normas.

**Nao feito.** Trocar o FreeCAD por Bonsai em qualquer entregavel (a decisao
de migrar e do usuario; o relatorio recomenda). Carimbo proprio no Bonsai,
eixos nomeados, niveis, detalhes de ligacao. Abrir o DXF no AutoCAD (so
auditoria e render pelo ezdxf). Ligar `dxf_prancha` ao `rodar_tudo`: a
entrada dele sao os SVG do Bonsai, que ainda nao e' saida do pipeline. Fase
5 (eletrico sobre planta de terceiros): o plano a poe depois do galpao.
**O galpao do cliente segue sem dado real (D193); tudo aqui foi medido no
spec de teste.**

## D195 - Plano de 2026-10-08, Fase 2 no galpao 20 x 28,5 m: o marcador PENDENTE vazava para o IFC (2026-10-08) - FECHADO

**Pedido.** Fechar o criterio de pronto da Fase 2 num galpao que nao seja o
spec de teste. `projects/galpao-sjb/project-spec.json` segue sem dado real
(D193). Busca feita antes de pedir ao usuario: das quatro fichas de galpao
em `projects/`, a do `galpao-sjb` esta bloqueada e as outras tres
(`galpao-25x54-trelicado`, `galpao-ufpe`, `galpao-tp-g95`) se declaram
`not_real_engineering_input`; a ficha completa e sem essa marca e
`spec_amostra_engenheiro.json` (20 x 28,5 m, pe-direito 8 m, V0 45, lote de
957 m2 com recuos e taxa de ocupacao), a mesma que o usuario levou ao
Blender em `dev/3Dblender/galpao`. **Se ela e' o galpao do cliente atual so
o usuario confirma.**

**Medido.** `rodar_tudo(spec, com_3d=False, com_executivo=False)` na ficha,
saida em `projects/amostra_engenheiro/saida/plano-2026-10/` (ignorada pelo
git): `exigir_completo` passa; calculo ATENDE sem falha de verificacao
(pilar e viga IPE500, utilizacao maxima 0,84; contraventamento 1,00 e
flecha do portico 0,99 no limite); memorial em PDF; IFC fisico (12
IfcColumn, 27 IfcBeam, 130 IfcMember, 156 IfcPlate, 12 IfcFooting, 360
IfcMechanicalFastener, perfis IPE500 e HEA160, 24 elementos em `Aco MR250`
e 12 em `Concreto C25`) e analitico, os dois com 0 apontamento no validador
de esquema e sem FreeCAD carregado. **Defeito achado na leitura do pset:**
`PerfilInicial = "__PENDENTE__"` - a ficha deixa o perfil para o calculo
escolher e o `_anotar_calculo` do D193 copiava o marcador como se fosse
dado.

**Entregue.** `ifc_emit._anotar_calculo`: valor igual a
`projeto_spec.PENDENTE` fica fora do pset (mesmo tratamento de chave
ausente). `tests/test_ifc_emit.py`: um teste com o marcador nos dois
perfis. Na pasta de saida, geradas pelo fluxo do D194: tres folhas A1 pelo
Bonsai (PDF e PNG; eixos lidos do IFC a cada 5,7 m, cotas 5 x 5700, 28500,
20000 e 8000), DXF de seis folhas (cortes e elevacoes a 1:50, plantas a
1:75, todas A1) e o DWG pelo ODA.

**Nao feito.** Confirmar que esta ficha e' o galpao do cliente (decisao do
usuario). Abrir o IFC em visualizador com interface (aberto no Bonsai sem
janela e validado no esquema). A elevacao frontal ainda invade o carimbo na
folha do Bonsai (pe-direito de 8 m); no DXF cada vista tem a sua folha.

## D196 - Plano de 2026-10-08: decisoes do usuario e as ressalvas das folhas do galpao 20 x 28,5 m (2026-10-09) - FECHADO

**Decisoes do usuario (2026-10-08, perguntadas uma a uma).** (1) O galpao
do cliente atual e' o de 20 x 28,5 m da ficha `spec_amostra_engenheiro.json`
- com isso o criterio de pronto da Fase 2 fecha com o que o D195 gerou. (2)
A Fase 5 (eletrico sobre planta de terceiros) segue congelada ate a entrega
do galpao. (3) Bonsai entra aos poucos como saida de pranchas e render; o
FreeCAD fica ate o Bonsai cobrir o que o executivo de aco entrega hoje.

**Medido (antes de mudar).** Nas folhas do Bonsai do galpao do cliente: a
elevacao frontal (pe-direito de 8 m) invadia o carimbo; o titulo da segunda
vista caia sobre a tabela de revisoes; carimbo em ingles com `UNTITLED`;
plantas sem eixo nomeado. O Bonsai grava a posicao de cada desenho num SVG
de disposicao por folha (`layouts/*.svg`, um `<image x y>` por vista) e
ordena a lista de folhas pela identificacao - renomear a primeira muda o
indice das seguintes.

**Entregue.**
- `docs/fase3-bonsai/scripts/pranchas_bonsai.py`: `distribuir` reparte as
  vistas em prateleiras dentro da area util acima do carimbo e abre folha
  nova quando a vista nao cabe (o galpao do cliente passou de 3 para 4
  folhas, nenhuma vista sobre o carimbo); as posicoes sao gravadas no SVG de
  disposicao antes de gerar; carimbo com rotulos em portugues, folha
  `EST-0n` e titulo curto por vista; a folha recem-criada e' achada pela
  diferenca de ids (o bug do indice renomeava sempre a mesma folha); o
  enquadramento usa so os elementos, sem a grade.
- `ifc_emit.py`: `emitir_ifc(..., eixos=)` grava um `IfcGrid` com um eixo
  numerado por portico e um eixo com letra por linha de pilares, 2,5 m alem
  da ultima linha; `emitir_ifc_do_spec` le as posicoes dos proprios pilares
  (`eixos_dos_pilares`). As outras tipologias chamam `emitir_ifc` sem
  `eixos` e seguem sem grade. `tests/test_ifc_emit.py`: tres testes (grade
  com rotulos e posicoes, so entra quando pedida, letra depois do Z). No
  galpao do cliente: 6 eixos numerados e 2 com letra, IFC com 0 apontamento.
- Pacote em `projects/amostra_engenheiro/saida/plano-2026-10/` (ignorado
  pelo git): memorial em PDF, IFC fisico e analitico, quatro folhas A1 em
  PDF, DXF de seis folhas e DWG.

**Nao feito.** **Os eixos estao no IFC e o Bonsai cria as 25 anotacoes de
referencia, mas sem janela elas nao chegam ao SVG** (nem com `sync=True`,
nem gerando o desenho duas vezes): as plantas seguem sem eixo desenhado e o
DXF tambem. A cota de altura do corte ainda e' o topo do envelope (9750),
nao a cumeeira do portico. `REV` sai `None` no carimbo. Detalhes de
ligacao, lista de material e simbolos de solda continuam so no executivo do
FreeCAD. O DWG nao foi aberto no AutoCAD.

## D197 - Plano de 2026-10-08: eixos desenhados, cota de cumeeira e revisao no carimbo (2026-10-09) - FECHADO

**Pedido.** Fechar o que o D196 deixou aberto nas folhas do galpao do
cliente: eixos da grade que nao chegavam ao desenho, cota de altura do
corte no topo do envelope e `REV None` no carimbo.

**Medido (antes de mudar).** Recarregando o IFC que a primeira geracao
salvou, as 8 anotacoes GRID do grupo da planta estao na cena, visiveis e
dentro de `get_drawing_elements`; gerar o desenho NESSA sessao poe as 24
marcas de eixo no SVG. Na sessao que as criou (`create_drawing(sync=True)`)
elas nao entram, nem gerando duas vezes. O desenho grava cada eixo como
`<line class="... PredefinedType-GRID">` com um `<text class="GRID">` em
cada ponta. A ponta da extrusao das vigas `V<n>` no IFC da 9,5 m (a
cumeeira da ficha); o topo do envelope dava 9,75 m (terca).

**Entregue.**
- `docs/fase3-bonsai/scripts/pranchas_bonsai.py`: segunda passada (recarrega
  o IFC salvo e gera de novo desenhos e folhas); cota de cumeeira lida do
  eixo das vigas do portico no IFC (`_cumeeira`); cotas da planta afastadas
  das bolhas dos eixos; `Revision` gravada na folha (padrao `00`). No galpao
  do cliente: 24 marcas de eixo em cada planta e 6 no corte, cotas 5 x 5700,
  28500, 20000, 8000 e **9500**, carimbo com `REV 00`; 62 s as seis vistas
  e as quatro folhas com as duas passadas.
- `dxf_prancha.py`: le os eixos do desenho (linha + rotulo das pontas; eixo
  sem rotulo unico reprova) e grava no DXF linha em tipo CENTER, bolha e
  rotulo na camada `ANOT-EIXO`, no tamanho de papel vezes a escala da folha.
  `tests/test_dxf_prancha.py`: tres testes (eixo com linha, bolha e rotulo
  nas duas coordenadas; desenho sem grade; eixo sem rotulo). No galpao do
  cliente: 8 eixos em cada planta e 2 no corte, auditoria sem erro, 24
  cotas iguais a distancia medida; DWG pelo ODA.

**Nao feito.** No corte do Bonsai as bolhas dos eixos A e B saem cortadas
pela borda da vista (a linha do eixo ocupa a altura toda) e a marca de
elevacao cai sobre a cota de 8000; na planta a marca de corte cai sobre uma
cota de vao. Detalhes de ligacao, lista de material e simbolos de solda
continuam so no executivo do FreeCAD. **Nenhum programa CAD esta instalado
nesta maquina (procurado em `C:/Program Files`): o DWG foi conferido so
pelo ODA e pelo ezdxf, nunca aberto no AutoCAD.**

## D198 - Plano de 2026-10-08: acabamento das pranchas do galpao do cliente e lista de material (2026-10-09) - FECHADO

**Pedido.** Decisao do usuario (2026-10-09, perguntada): enquanto a
entrega espera a abertura do DWG no AutoCAD e a revisao do engenheiro
parceiro, trabalhar no acabamento das pranchas do galpao de 20 x 28,5 m -
bolhas de eixo cortadas no corte, marca de corte sobre cota e a lista de
material numa folha do DXF. Fase 5 segue congelada.

**Medido (antes de mudar).** O Bonsai leva a linha de cada eixo e de cada
corte ate a borda da vista (`<line>` com y de 0,001 a 319,7 numa vista de
319,7 mm), e a bolha ou a seta da ponta sai pela metade. A marca de corte
ficava a 5,2 m da linha de pilares, sobre a cota total (5,4 m). O romaneio
do calculo so existia em texto (`romaneio-preliminar.txt`, pecas
primarias); o IFC nao guardava peso.

**Entregue.**
- `docs/fase3-bonsai/scripts/pranchas_bonsai.py`: `puxar_para_dentro`
  encurta as linhas de eixo e de corte para 8 mm dentro da vista e leva
  junto o rotulo e o simbolo da ponta (4 pontas no corte, 2 em cada
  planta); margem do enquadramento de 9 para 11 m e cota total a 5,2 m,
  para a marca de corte ficar abaixo das cotas.
- `ifc_emit._anotar_calculo`: `Comprimento_m` e `Peso_kg` do romaneio do
  calculo no pset da peca primaria (marca C1 e V1); sem romaneio as duas
  chaves ficam fora.
- `dxf_prancha.py`: `lista_do_ifc` conta as pecas no proprio modelo (uma
  linha por classe, marca, perfil e comprimento; comprimento so para peca
  linear; peso so onde o pset traz) e `gerar_dxf(..., lista=)` grava a
  folha A3 `NN-LISTA-DE-MATERIAL` com a tabela, o total pesado e o aviso
  de quantas linhas estao sem peso. Lista que nao cabe na folha reprova.
- Testes: um em `tests/test_ifc_emit.py` (peso e comprimento no pset; fora
  sem romaneio) e tres em `tests/test_dxf_prancha.py` (lista contada no
  modelo; folha no DXF com aviso de peso parcial; lista que nao cabe).
- No galpao do cliente: 29 linhas, 2 com peso (12 pilares IPE500 de 8,000
  m = 8703,6 kg; 12 vigas IPE500 de 10,112 m = 11001,6 kg), **total pesado
  19705,2 kg** contra 19705,9 kg do romaneio do calculo (a lista soma o
  peso unitario arredondado a 0,1 kg); DXF de sete folhas com auditoria
  sem erro, DWG pelo ODA.

**Nao feito.** Peso das 27 linhas secundarias (tercas, longarinas, chapas,
fixadores, bloco): o calculo nao as pesa, e a folha diz que o total nao e'
o peso da obra. Lista de material tambem como folha do Bonsai (so no DXF).
Detalhes de ligacao e simbolos de solda continuam so no executivo do
FreeCAD. DWG nunca aberto no AutoCAD (nenhum CAD nesta maquina).

## D199 - Plano de 2026-10-08: detalhes de ligacao no Bonsai (1a etapa) e o graute que o modelo neutro nao realizava (2026-10-09) - FECHADO

**Pedido.** Decisao do usuario (2026-10-09, perguntada): levar para o
Bonsai o que hoje so o executivo do FreeCAD entrega em detalhes de ligacao,
base e simbolos de solda. Trabalho em etapas; esta e' a primeira.

**Medido (antes de mudar).** O executivo do FreeCAD (`techdraw_exec.py`)
entrega PE06 (base de coluna, com o toco do pilar), PE07 (joelho, recorte
em torno do no), PE10+ (uma prancha por tipo de ligacao) e o glifo de solda
de filete. O IFC do galpao do cliente ja traz placa de base, enrijecedores,
chumbadores, porcas, arruelas e a misula; nao traz chapa de topo nem
parafusos do joelho, nem solda. Ao olhar o primeiro detalhe da base gerado
do IFC: placa de base de z = -70 a +30 mm e bloco com o topo em 0 - **a
placa 70 mm dentro do concreto e a porca de nivel (-98 a -70) enterrada,
sem a folga de graute**. O `build_galpao` ja realizava o gap
(`z_conc_top = pbot - GROUT_GAP`, com o comentario do mesmo defeito) e
`fundacoes_profundas` tambem; so `modelo_neutro.fundacoes` (fundacao rasa,
o caminho do IFC) nao.

**Entregue.**
- `modelo_neutro.fundacoes(..., base_t=)`: com placa de base, o topo do
  concreto fica em `z0 - t - grout` (-100 mm para placa de 100 mm);
  `frame_completo` passa a espessura da placa. Sem placa, topo na cota 0
  como antes. Dois testes em `tests/test_modelo_neutro.py` (gap de 30 mm
  realizado; sem placa nada muda). 504 testes que tocam o modelo neutro, o
  IFC e as fundacoes passaram antes da suite inteira.
- `docs/fase3-bonsai/scripts/pranchas_bonsai.py`: tres detalhes a 1:10 do
  MESMO modelo, numa folha propria (`EST-05 DETALHES DE LIGACAO`): base em
  elevacao e em planta (cotas 600, 800 e 100 lidas do envelope da placa no
  modelo) e o no do joelho. Vista em ELEVACAO, com a camera fora do bloco:
  o corte pelo eixo do pilar preenchia de preto a alma e o bloco. A primeira
  passada so grava no IFC e tolera falha de desenho (as marcas de referencia
  nascem com geometria de comprimento zero e o Bonsai quebra ao desenha-las
  num corte); desenhos e folhas saem todos da segunda passada. O ajuste das
  bolhas passou a encurtar a linha so ao longo dela e a remover o eixo que
  nao cruza a vista (trazia o eixo B para dentro de um detalhe do eixo A).
- `dxf_prancha.py`: desenho com escala de origem maior que 1:50 mantem essa
  escala na folha (os detalhes saem a 1:10 em A3). Dois testes.
- Galpao do cliente: cinco folhas A1 do Bonsai e DXF/DWG de dez folhas (seis
  vistas, tres detalhes e a lista de material), auditoria sem erro, 28 cotas
  iguais a distancia medida.

**Nao feito (proximas etapas).** Simbolo de solda (o IFC nao tem solda;
falta decidir de onde sai a perna e o tipo). Chapa de topo e parafusos do
joelho no modelo neutro. Pedestal da fundacao rasa, que o `build_galpao`
desenha e o modelo neutro nao. **O pilar no modelo neutro comeca em z = 0 e
o topo da placa esta em +30: 30 mm de sobreposicao** (o `build_galpao`
comeca o pilar em Z0); mexer nisso muda o comprimento do pilar no IFC
(8,000 m, igual ao do romaneio) e ficou para decisao. Textos de chamada nos
detalhes (bitola do chumbador, perfil, utilizacao). Detalhes de cumeeira,
contraventamento e demais ligacoes do PE10+.

## D200 - Plano de 2026-10-08: pilar no topo da placa e textos de chamada nos detalhes (2026-10-09) - FECHADO

**Decisoes do usuario (2026-10-09, perguntadas).** (1) Alinhar o pilar com
o FreeCAD: no modelo do IFC ele passa a nascer no topo da placa de base
(+30 mm), nao na cota 0. (2) Etapa 2 das ligacoes no Bonsai = textos de
chamada lidos do modelo.

**Medido (antes de mudar).** IFC do galpao do cliente: pilar de z = 0 a
8000 e placa de base de -70 a +30 - 30 mm do pilar dentro da placa. O
`build_galpao` comeca o pilar em `Z0` (30 mm). A placa de base, os
chumbadores e a misula nao tinham propriedade nenhuma no IFC; o que o
calculo adotou para a base e para o joelho so existia em `spec.estrutura`.
As chapas poligonais (misula, nervura) passavam por `_painel_ifc` e nunca
recebiam pset. O Bonsai resolve `{{Pset.Propriedade}}` no texto de uma
anotacao a partir do elemento associado a ela.

**Entregue.**
- `modelo_neutro.frame_completo`: com placa de base, o pilar nasce em
  `Z0_PLACA_MM` (30); sem placa, na cota 0 como antes. No galpao do cliente
  a peca passa a 7970 mm no IFC.
- `ifc_emit`: a placa de base leva `Descricao` (B x L x t), `Chumbadores`
  (quantidade e bitola) e `Utilizacao`; a misula leva a ligacao do joelho
  (`n parafusos, chapa t`) e a utilizacao - so quando o calculo deixou
  todas as medidas. Chapa poligonal passa a receber o pset.
- `dxf_prancha`: a linha da peca pesada usa o comprimento do calculo (o que
  gerou o peso), com a nota na folha; os textos de chamada do desenho vao
  ao DXF no tamanho de papel vezes a escala.
- `docs/fase3-bonsai/scripts/pranchas_bonsai.py`: `_texto` cria a anotacao
  TEXT ligada ao elemento mais proximo do eixo do detalhe; oito chamadas
  nos tres detalhes.
- Testes: um em `test_modelo_neutro.py`, dois em `test_ifc_emit.py`, dois
  em `test_dxf_prancha.py`.
- No galpao do cliente (texto lido do SVG gerado): "PILAR IPE500 - ACO
  MR250", "PLACA DE BASE 600 x 800 x 100 mm", "CHUMBADORES 6 O32", "VIGA
  IPE500", "JOELHO: 4 parafusos O24, chapa 12.5 mm" (O = simbolo de
  diametro). Lista de material: pilar com 8,000 m e 725,3 kg (calculo).
  DXF de dez folhas com auditoria sem erro.

**Nao feito.** Simbolo de solda; chapa de topo e parafusos do joelho como
geometria (hoje so a descricao em texto); pedestal da fundacao rasa;
detalhes de cumeeira, contraventamento e demais ligacoes. O texto da
utilizacao nao foi posto na prancha (esta no pset). A descricao do joelho
sai com ponto decimal ("12.5 mm").

## D201 - Plano de 2026-10-08: chapa de topo, parafusos e enrijecedores do joelho no modelo (2026-10-09) - FECHADO

**Pedido.** Terceira etapa das ligacoes no Bonsai: levar ao modelo que gera
o IFC a ligacao do joelho que so o `build_galpao` desenhava, para o detalhe
mostrar a peca e nao so o texto.

**Medido (antes de mudar).** `build_galpao.joelho` desenha, por no: misula,
chapa de topo (espessura do calculo x 220 x 250 mm, perpendicular a viga, a
820 mm do no), 4 parafusos pela chapa (+-70 mm no comprimento, +-90 mm na
altura, 120 mm de comprimento) e dois enrijecedores de continuidade no
pilar (bf x d x 12 mm, a -95 e -15 mm do beiral). O docstring diz
"conceitual - dimensoes/parafusamento definitivos sao detalhe do eng.
responsavel". `modelo_neutro.misulas_joelho` so levava a misula e dizia que
o resto era detalhe de fabricacao fora do intercambio.

**Entregue.** `modelo_neutro.ligacoes_joelho`: as mesmas pecas, medidas e
posicoes do build (chapa `CJ1`, parafusos `PJ1`, enrijecedores `EJ1`), so
quando o calculo deixou `joelho_adotado` com n, db e t, e so no portico
prismatico; a chapa e' extrudada para +viga e fica centrada no ponto do
build. `frame_completo(..., joelho_lig=)` e `ifc_emit.membros_do_spec`
passam o adotado. Quatro testes em `tests/test_modelo_neutro.py`
(contagens; chapa centrada, plana e perpendicular a viga, parafusos de 120
mm paralelos a ela; seis parafusos em tres fileiras; sem adotado so a
misula). 1029 testes que tocam o modelo, o IFC, os fixadores e o orcamento
passaram antes da suite inteira. No galpao do cliente: +12 chapas de topo,
+24 enrijecedores e +48 parafusos no IFC (validacao sem apontamento),
detalhe do joelho com a chapa e os parafusos, lista de material com 32
linhas.

**Achado ao olhar o detalhe, NAO corrigido.** A chapa de topo de 250 mm de
altura fica no meio de uma viga IPE500 de 500 mm: o build fixa 220 x 250
(medida da referencia antiga, viga de 171 mm) e nao escala com o perfil
adotado. Espelhei o build; dimensionar a chapa e o parafusamento para o
perfil e' projeto de ligacao, do engenheiro. O mesmo vale para a posicao
dos enrijecedores (-95 e -15 mm). **O detalhe do joelho mostra a ligacao
conceitual do build, nao uma ligacao detalhada.**

**Nao feito.** Simbolo de solda; pedestal da fundacao rasa; cumeeira,
contraventamento e demais ligacoes; chapa de reforco de alma (doubler) do
joelho, que o build desenha quando a zona de painel exige.

## D202 - Plano de 2026-10-08: o pedestal do build e' menor que a placa de base (2026-10-09) - REGISTRADO, SEM MUDANCA DE CODIGO

**Pedido.** Quarta etapa das ligacoes no Bonsai: levar ao modelo do IFC o
pedestal da fundacao rasa que o `build_galpao` desenha.

**Medido.** A altura do pedestal tem origem declarada (`fundacao.h_ped`,
0,5 m quando a ficha nao declara; `projeto_spec.to_build_kwargs` e o
quantitativo do calculo a usam). O lado, nao: o `build_galpao` fixa
`pdim = max(d + 120, bf + 120, 300)` mm a partir do pilar. No galpao do
cliente (pilar IPE500, placa de base 600 x 800 x 100 mm, chumbadores a 60
mm da borda da placa) isso da **620 mm de lado contra 800 mm de placa: os
chumbadores ficam a 340 mm do eixo e a face do pedestal a 310 mm - fora do
concreto**. Vi isso no detalhe da base gerado do IFC com o pedestal
espelhado (implementado, 1308 testes verdes, e desfeito).

**Decisao do usuario (2026-10-09, perguntada).** Sem pedestal no IFC por
enquanto: o bloco fica direto sob a placa, com o gap de graute (D199), que
e' o detalhe que sai coerente. O codigo do pedestal no modelo neutro foi
revertido antes de qualquer commit.

**Fica aberto.** O defeito esta no `build_galpao` (PEDESTAL_* menor que a
placa sempre que a placa passa de `pilar + 120 mm`) e portanto na prancha
PE06 do executivo do FreeCAD. A regra do lado do pedestal (placa + folga,
cobrimento do chumbador) e' definicao do engenheiro; nada foi mudado no
build. A chapa de reforco de alma do joelho (doubler) tambem nao foi levada
ao modelo: no galpao do cliente a zona de painel da 0,87 e nao a exige.

## D203 - Plano de 2026-10-08: ligacao da cumeeira no modelo e detalhes de cumeeira e contraventamento (2026-10-09) - FECHADO

**Pedido.** Quinta etapa das ligacoes no Bonsai: cumeeira e contraventamento.

**Medido (antes de mudar).** `build_galpao.cumeeira_conn` desenha no apice
uma chapa de topo (largura = mesa da viga, espessura do `joelho_adotado`,
altura = d + 140 mm, normal em Y) e 4 parafusos de 140 mm (a bf/2 - 35 e
d/2 - 25 do centro) - aqui a chapa ESCALA com o perfil, ao contrario da do
joelho (D201). O modelo neutro nao tinha a ligacao do apice. Os gussets do
contraventamento ja estavam no modelo (`gussets_contrav`).

**Entregue.** `modelo_neutro.ligacoes_cumeeira` (chapa `CC1` e parafusos
`PM1`, mesmas medidas e posicoes do build), chamada junto com a do joelho;
dois testes em `tests/test_modelo_neutro.py`. No script de pranchas: detalhe
`DET-CUMEEIRA` (vista do apice a 1:10, com o perfil da viga e a descricao da
ligacao lidos do modelo) e `DET-CONTRAVENTAMENTO` (planta do canto do
primeiro portico, filtrada para a estrutura). No galpao do cliente: +6
chapas e +24 parafusos no IFC, seis folhas A1 do Bonsai, DXF de doze
folhas.

**Nao feito.** No detalhe do contraventamento a chapa de gusset fica
escondida sob a viga na planta (so aparecem a barra, a viga e a escora): a
vista certa e' de baixo para cima, nao tentada. Simbolo de solda. Chapa de
reforco de alma do joelho. As ligacoes de terca, longarina e mao-francesa
nao tem detalhe proprio.

## D204 - Plano de 2026-10-08: detalhes de contraventamento, terca e longarina (2026-10-09) - FECHADO, SO SCRIPT

**Entregue.** `docs/fase3-bonsai/scripts/pranchas_bonsai.py`: o detalhe do
contraventamento passou a ser a vista da PAREDE no canto inferior do
primeiro vao (na planta da cobertura a chapa de gusset ficava escondida sob
a viga); dois detalhes novos, de terca e de longarina, com a camera posta
no centro da peca lido do modelo (`_apoio_secundario`). Nenhum modulo de
producao mudou. Galpao do cliente: seis folhas A1 do Bonsai (a sexta com
cumeeira, contraventamento, terca e longarina), DXF de catorze folhas com
auditoria sem erro, DWG pelo ODA.

**Visto na folha e nao resolvido.** Os tres detalhes novos sao pobres: no
do contraventamento aparecem a base do pilar e a chapa de gusset, mas a
barra nao; no da terca e no da longarina aparecem a peca em secao e o
clipe, sem cota nem fixador (o modelo nao tem os parafusos do clipe). Servem
de localizacao, nao de detalhe de fabricacao.

**Nao feito.** Simbolo de solda (falta o usuario dizer de onde saem tipo e
perna). Chapa de reforco de alma do joelho. Mao-francesa sem detalhe.

## D205 - Plano de 2026-10-08: Fase 5 liberada (primeiro passo) e simbolo de solda do gusset (2026-10-09) - FECHADO

**Decisoes do usuario (2026-10-09, perguntadas).** (1) LIBERAR a Fase 5,
suspendendo o congelamento registrado no D196: fazer o primeiro passo do
plano (ler ambientes num DXF e gerar a previsao de cargas). (2) Solda: usar
a que o executivo do FreeCAD ja usa, marcada como conceitual.

**Medido (antes de mudar).** Motor: `arquitetura_residencial.rodar` aceita
ambientes por `{nome, tipo, area_m2, perimetro_m}` e ja entrega a previsao
(pontos minimos e cargas). Nao havia leitor de planta no `galpao_fw`. Solda
no executivo do FreeCAD: so o gusset (e o console) tem solda com dado - a
perna vem de `gusset_adotado.perna_solda_mm` (solda de filete minima do
calculo) e sai como glifo de filete em todo o contorno; base, joelho e
cumeeira nao tem solda nenhuma no codigo dele.

**Entregue.**
- `ambientes_dxf.py` (SCRIPT AVULSO, declarado em
  `test_alcancabilidade.SCRIPTS_AVULSOS` e em `SEM_FAIXA_DECLARADA`): le
  polilinhas fechadas e o texto de dentro de cada uma numa camada (padrao
  `AMBIENTES`), devolve tipo, area e perimetro em metros pela unidade do
  cabecalho do DXF e chama o motor. Desenho sem unidade declarada e'
  recusado ate a unidade ser informada; polilinha aberta, com arco, sem
  texto, com dois textos e texto solto viram erro nomeado e derrubam o
  veredito. Nenhum valor de norma no modulo.
- `tests/test_ambientes_dxf.py`: 14 testes com a planta escrita pelo ezdxf
  (area e perimetro; mm, cm e m; sem unidade; previsao igual a do motor para
  os mesmos numeros digitados; planta mal marcada; outra camada; tipos com
  acento e preposicao).
- `ifc_emit`: a chapa de gusset leva a espessura, a perna da solda de filete
  e a utilizacao do calculo. Um teste.
- `docs/fase3-bonsai/scripts/pranchas_bonsai.py`: simbolo de solda de filete
  em todo o contorno acrescentado ao `symbols.svg` do projeto e posto no
  detalhe do contraventamento, com a perna lida do elemento; texto de
  chamada com espessura e perna. No galpao do cliente: "GUSSET: chapa 12 mm
  - SOLDA DE FILETE, PERNA 5.0 mm, TODO O CONTORNO" e o simbolo com 5.0.

**Nao feito.** Fase 5 alem do primeiro passo: entrada por IFC (`IfcSpace`),
divisao de circuitos, quadro, unifilar e saida do eletrico em DXF sobre a
planta; gabarito contra projeto ja entregue (nenhuma planta real de cliente
foi lida, so plantas de teste). Solda de base, joelho e cumeeira: o FreeCAD
nao tem dado para elas. O simbolo de solda nao vai ao DXF (so o texto).

## D206 - Plano de 2026-10-08: Fase 5, segundo passo - pontos, divisao em circuitos e quadro de cargas (2026-10-09) - FECHADO

**Medido (antes de escrever).** O motor de dimensionamento
(`dimensionamento_eletrico_residencial`) so aceita pontos e circuitos
EXPLICITOS; `residencial_eletrica` diz no proprio cabecalho que nao cria
pontos a partir de comodos. Nao havia divisao em circuitos em Python (no
Projetor-eletrico ela so existe em TypeScript). Regras lidas no acervo
(edicao 2004, paginas 18-19 e 184): 4.2.5.5, 4.2.5.6, 9.5.3.1, 9.5.3.2 e
9.5.3.3. A norma NAO fixa potencia maxima por circuito.

**Entregue.**
- `circuitos_planta.py` (biblioteca sem FreeCAD, chamada pela linha de
  comando do `ambientes_dxf` com `criterios=<json>`; declarada em
  `SEM_FAIXA_DECLARADA`): da
  previsao por ambiente tira um ponto de luz com a carga minima e os pontos
  de tomada minimos, cada um com a potencia do motor (a soma e' conferida
  contra a previsao); separa iluminacao, tomadas e tomadas dos locais de
  9.5.3.2; enche os circuitos na ordem da planta ate o limite declarado;
  cada equipamento declarado ganha circuito proprio, com a exigencia de
  9.5.3.1 dita (acima de 10 A); distribui os circuitos nas fases, maior
  primeiro na menos carregada. Os pontos saem no formato do motor de
  dimensionamento.
- Criterio de projeto e' DECLARADO, sem padrao: tensao, numero de fases,
  limite de VA por classe e lista de equipamentos (vazia se nao ha). Faltando
  um, nenhum circuito sai e o campo e' nomeado.
- `tests/test_circuitos_planta.py`: 13 testes (soma por ambiente; classes que
  nao se misturam; corte no ponto certo com dois limites; quadro e fases
  fechando com a previsao; 10 A exatos nao exige e 10,01 A exige; criterio
  ausente; ponto maior que o limite; equipamento mal declarado; da planta DXF
  ao quadro).

**Camada rapida.** `tests/test_ifc_emit.py` somou 20,6 s na camada rapida
(limite de 20 s por arquivo) por causa dos testes de ligacao do D198 ao D205;
foi declarado em `camada_lenta.LENTOS_MEDIDOS` com o tempo medido. Segue na
suite inteira; saiu da rapida (3197 testes, 197 s de parede).

**Limites ditos.** O quadro e' de CARGA INSTALADA: sem demanda, sem
comprimento, sem condutor e sem disjuntor. A excecao de 9.5.3.3 (circuito
comum) nao e' usada. A distribuicao de fases e' heuristica, nao o otimo. O
ponto de luz e' um por ambiente, com a carga inteira. Nenhuma planta real de
cliente passou por aqui.

**Nao feito.** Comprimento dos circuitos (precisa da posicao do quadro na
planta), dimensionamento, unifilar, saida em DXF, entrada por IFC e gabarito
contra projeto entregue.

## D207 - Plano de 2026-10-08: Fase 5, terceiro passo - comprimento, dimensionamento, unifilar e quadro (2026-10-09) - FECHADO

**Medido (antes de escrever).** O motor `dimensionamento_eletrico_residencial`
ja dimensiona condutor e protecao de circuito explicito, e
`desenho_eletrico_residencial` ja desenha unifilar e quadro de cargas a
partir do resultado dele. Faltava so a ponte: a divisao do D206 nao tinha
comprimento nem os dados de instalacao que o motor exige. Nenhuma tabela foi
reescrita.

**Entregue.**
- `ambientes_dxf`: o leitor devolve tambem o poligono de cada ambiente em
  metros e a posicao do quadro, lida de UMA entidade na camada `QUADRO`
  (duas ou mais: erro nomeado; nenhuma: posicao nao informada, sem erro).
- `circuitos_planta.comprimentos_pela_planta`: comprimento ESTIMADO = fator
  de tracado x distancia ortogonal do quadro ao vertice mais distante do
  ambiente mais distante do circuito + acrescimo vertical. Fator e acrescimo
  sao declarados, sem padrao; a origem ("estimado" ou "declarado") vai ao
  resumo. Comprimento declarado por circuito vence a estimativa.
- `circuitos_planta.dimensionar`: monta os circuitos no contrato do motor e o
  chama. Isolacao, metodo, temperatura, agrupamento, fator de potencia por
  classe, limite de queda e exposicao sao declarados; faltando um, nada e'
  dimensionado e o campo e' nomeado. O local do circuito (banheiro, molhado,
  externo, seco) e' o mais restritivo dos ambientes que ele serve.
- `circuitos_planta.desenhos`: unifilar e quadro de cargas em SVG pelo
  emissor que ja existia.
- Linha de comando: `criterios=<json>` com `instalacao` dimensiona;
  `saida=<pasta>` grava os dois SVG.
- Testes: 10 funcoes novas em `test_circuitos_planta.py` e 2 em
  `test_ambientes_dxf.py` (51 casos nos dois arquivos; comprimento conferido a mao com o quadro andando
  em cada eixo; resultado igual ao do motor chamado a mao; comprimento maior
  engrossa o condutor; circuito recusado some do resumo e derruba o veredito;
  iluminacao de local seco sem diferencial e com banheiro no circuito com).

**Visto no desenho.** Unifilar e quadro abertos em imagem na planta de teste
de cinco ambientes: cinco circuitos, secao, disjuntor e diferencial de cada
um; entrada, disjuntor geral, aterramento e demanda saem "A CONFIRMAR"
(nao foram calculados). No unifilar o texto da corrente do disjuntor fica
cortado pela linha do circuito - defeito do emissor que ja existia, nao
corrigido aqui.

**Limites ditos.** O comprimento estimado e' de anteprojeto: nao segue
parede nem eletroduto. Sem demanda, sem ramal e padrao de entrada, sem
curto-circuito. O motor responde `KeyError` (sem dizer o motivo) quando o
comprimento passa do que as tabelas dele cobrem; o circuito e' recusado, mas
o motivo fica opaco.

## D208 - Plano de 2026-10-08: Fase 5, quarto passo - o eletrico desenhado sobre a planta DXF recebida (2026-10-09) - FECHADO

**Entregue.**
- `planta_eletrica_dxf.py` (biblioteca sem FreeCAD, chamada pela linha de
  comando do `ambientes_dxf` com `dxf=<saida.dxf>`; declarada em
  `SEM_FAIXA_DECLARADA`): abre o DXF recebido, acrescenta camadas `ELE-` e
  grava em OUTRO arquivo. Vao ao desenho o quadro (onde o cliente marcou), um
  ponto de luz no centro de cada ambiente, as tomadas repartidas pelo
  perimetro e afastadas para dentro do ambiente, os equipamentos ao lado do
  ponto de luz, o circuito ao lado de cada ponto, a tabela dos circuitos
  (com condutor, disjuntor e diferencial quando ha dimensionamento), a
  legenda e a nota de que as posicoes sao sugestao.
- `tests/test_planta_eletrica_dxf.py`: 11 testes que RELEEM o arquivo
  gravado (o original nao muda, byte a byte; cada ponto vira um simbolo no
  ambiente certo, nos dois eixos; rotulo = circuito que alimenta; tabela com
  uma linha por circuito; mm, cm e m; ambiente em U sem ponto inventado;
  circuito recusado escrito "NAO DIMENSIONADO").

**Achado ao olhar o desenho (corrigido antes do commit).** (1) A tomada que
caia exatamente no canto do ambiente saia desenhada do lado de FORA: no
vertice nao ha um "lado de dentro" de uma parede so; agora ela e' puxada
para fora do canto antes de ser afastada. (2) Os simbolos da legenda estavam
nas mesmas camadas dos pontos: quem contasse pontos por camada contaria a
legenda; foram para a camada da tabela.

**Limites ditos.** As posicoes sao sugestao de partida, nao projeto: a
planta nao diz onde ficam portas, bancadas e moveis. Nao ha eletroduto
tracado. Os simbolos sao ADOTADOS (o acervo nao tem norma de simbologia) e
explicados na legenda. Ambiente cujo centro cai fora do proprio poligono
(L fino, U) nao recebe ponto: erro nomeado e veredito reprovado. Rotulos de
tomadas de ambientes vizinhos podem se sobrepor perto de um encontro de
paredes. O DXF nao foi aberto num CAD de verdade, so relido pelo ezdxf e
visto em imagem.

## D209 - Plano de 2026-10-08: Fase 5, quinto passo - ambientes lidos de um modelo IFC (2026-10-09) - FECHADO

**Entregue.**
- `ambientes_ifc.py` (biblioteca sem FreeCAD, chamada pela linha de comando
  do `ambientes_dxf` quando o arquivo e' `.ifc`; declarada em
  `SEM_FAIXA_DECLARADA`): cada `IfcSpace` do pavimento vira um ambiente com
  o mesmo contrato do leitor de DXF. Area, perimetro e poligono saem da
  GEOMETRIA (face de baixo do solido, pelo nucleo geometrico do
  ifcopenshell), em metros qualquer que seja a unidade do arquivo. O tipo
  vem de `ObjectType`, senao `LongName`, senao `Name`. O quadro e' o unico
  `IfcElectricDistributionBoard`.
- Erro nomeado em vez de palpite: ambiente sem nome, sem geometria, com
  vazio no piso, quantidade de area do arquivo divergindo da geometria em
  mais de 1 %, ambientes em mais de um pavimento sem o pavimento escolhido,
  pavimento que nao existe, mais de um quadro.
- `tests/test_ambientes_ifc.py`: 8 testes com o modelo escrito pelo
  ifcopenshell (mm e m; ambientes fora da origem; ambiente em L; previsao,
  divisao e comprimento iguais aos da planta DXF equivalente; rotulo x
  geometria; modelo mal formado; dois pavimentos).

**Limites ditos.** A tolerancia de 1 % entre a area escrita e a da geometria
e' ADOTADA (conferencia de rotulo, nao criterio de norma). Nao ha saida
desenhada para entrada em IFC: o desenho do D208 precisa de uma planta DXF
de base. Nenhum IFC de cliente (Revit, ArchiCAD) foi lido: so modelos
escritos pelo proprio teste. Os `IfcSpace` que o proprio projeto emite para
a casa nao trazem tipo (so o nome do ambiente).

**Fase 5: o que continua aberto.** Demanda, ramal e padrao de entrada na
ponte da planta (os motores existem, a ponte nao); eletroduto tracado;
gabarito contra um projeto ja entregue - depende de o usuario trazer uma
planta real e o projeto correspondente.

## D210 - Plano de 2026-10-08: Fase 5, sexto passo - demanda e padrao de entrada na ponte da planta (2026-10-09) - FECHADO

**Medido (antes de escrever).** Os motores `demanda_residencial_enel` e
`entrada_enel_bt` ja existiam e o unifilar ja sabia desenhar o que eles
devolvem; na ponte da planta (D207) entrada, disjuntor geral, aterramento e
demanda saiam "A CONFIRMAR". As fontes da distribuidora NAO estao no acervo
novo de texto nativo (so no antigo, F131): por isso a ponte nao interpreta
regra nenhuma delas.

**Entregue.**
- `circuitos_planta.demanda_e_entrada`: monta a entrada dos dois motores e os
  chama. Conta os ambientes por modulo de demanda: tipo que e' exatamente um
  modulo do motor entra direto; qualquer outro (suite, varanda, lavabo...) so
  entra com o modulo DECLARADO em `demanda.modulo_por_tipo`, senao e' erro
  nomeado. Equipamento so entra com `grupo_demanda` declarado, e so o grupo
  de aquecimento esta ligado (iguais em potencia viram um item com a
  quantidade). Carga instalada em kW = soma dos circuitos pela potencia vezes
  o fator de potencia declarado da classe. Rede (fator locacional, tensao,
  tipo de fornecimento, aerea ou nao) declarada.
- Conferencia cruzada: o numero de fases em que o quadro foi repartido tem de
  ser o que o ramal da linha escolhida entrega (lido da propria tabela do
  motor, "2x10 (10)"); diferente, reprova.
- `desenhos(..., entrada)` leva demanda e padrao de entrada ao unifilar e ao
  quadro; linha de comando: `rede` no arquivo de criterios.
- 7 funcoes de teste novas em `test_circuitos_planta.py` (resultado igual ao
  dos dois motores chamados a mao; tipo sem modulo; equipamento sem grupo;
  cada dado de rede ausente; rede que os motores recusam; fases; unifilar com
  e sem entrada).

**Visto no desenho.** Unifilar da planta de teste com a rede declarada:
"ENTRADA BT 127/220 V", "Padrao B1 - ramal 10 (10) mm2", "DISJ. GERAL 50 A",
aterramento 10 mm2 e demanda 10,69 kVA com a fonte escrita. Conta refeita a
mao: modulos 8,8 kVA / 1,40 + chuveiro 5,5 kW x 80 % = 10,69 kVA.

**Limites ditos.** Vale so para a distribuidora cujas tabelas o motor tem
(rede aerea, 127/220 e 120/240 V). Motores e iluminacao especial nao sao
montados pela ponte. Curto-circuito segue nao avaliado. A correspondencia
entre tipo de ambiente e modulo de demanda e' de quem projeta.

**Fase 5: o que continua aberto.** Eletroduto tracado; gabarito contra um
projeto ja entregue (depende de planta real e projeto correspondente
trazidos pelo usuario).

## D211 - Plano de 2026-10-08: Fase 5 - gabarito da demanda contra um projeto entregue; motores, iluminacao especial e grupo "nenhum" na ponte (2026-10-09) - FECHADO

**Gabarito (medido).** Na pasta de clientes (fora do repositorio, nao
versionada) ha um calculo de demanda residencial ja entregue a distribuidora,
feito por um script proprio daquela entrega, que nao importa o motor daqui.
Os mesmos dados passados a `demanda_residencial_enel` e a `entrada_enel_bt`
deram o MESMO resultado: parcelas a, b, c e d iguais, demanda final
31,682567 kVA nos dois, e a mesma linha do padrao de entrada (C8, 175 A).
Limite do gabarito: os dois calculos sao do mesmo autor e da mesma leitura
da fonte; concordarem prova que o motor reproduz o que foi entregue, nao que
a leitura da fonte esteja certa. Os dados do cliente nao entraram em teste
nem em arquivo do repositorio.

**Achado do gabarito.** No projeto entregue, o grupo de aquecimento levou so
forno e cooktop; chuveiros, ar-condicionado e lavadora nao entraram em grupo
acessorio nenhum, e havia tres motores e iluminacao especial. A ponte do
D210 nao conseguia representar isso: so conhecia o grupo de aquecimento e
recusava o resto. O exemplo que eu usei no D210 (chuveiro como aquecimento)
e' escolha de quem declara, nao regra - e o projeto entregue escolheu
diferente.

**Entregue.**
- `grupo_demanda` de cada equipamento passa a ser um de: `aquecimento` (a
  ponte monta o item), `motor` (o motor vem descrito em `demanda.motores`) ou
  `nenhum` (nao entra em grupo acessorio). Outro valor: erro nomeado.
- `demanda.motores` e `demanda.iluminacao_especial` sao listas declaradas no
  contrato do calculador e vao a ele como estao; ausentes, e' erro nomeado
  (lista vazia tem de ser dita). Equipamento declarado como motor com
  `demanda.motores` vazia reprova.
- 2 funcoes de teste novas e 3 ajustadas em `test_circuitos_planta.py`.

**Nao feito.** Nao ha planta de ambientes desse projeto (os DXF da pasta sao
desenhos de rede da distribuidora), entao a ponte inteira - planta ate o
quadro - segue sem gabarito real. Eletroduto tracado segue fora.

## D212 - Plano de 2026-10-08: Fase 5 - esboco de eletroduto no DXF do eletrico (2026-10-09) - FECHADO

**O que o plano pede.** "Roteamento automatico de cabos fica para versao
posterior; no inicio, tracado simplificado e ajuste manual." O D208 nao
tracava nada.

**Entregue.**
- `planta_eletrica_dxf.esboco_de_eletroduto`: com o quadro marcado, o ponto
  de luz de cada ambiente e' o no do ambiente; os nos se ligam ao quadro pela
  arvore de menor comprimento (cada no se liga ao ja ligado mais proximo, a
  comecar do quadro) e cada tomada ou equipamento se liga ao no do seu
  ambiente. Retas na camada `ELE-ELETRODUTO-ESBOCO`, que se desliga sozinha,
  com a nota escrita no desenho. Sem quadro marcado nao ha esboco nem nota.
- 3 funcoes de teste novas em `test_planta_eletrica_dxf.py`, relendo o
  arquivo: arvore conferida a mao na casa de teste; todo simbolo desenhado
  alcanca o quadro pelos trechos; o primeiro trecho muda quando o quadro anda
  em x e quando anda em y.

**Visto no desenho.** Imagem da planta de teste de cinco ambientes: 5 trechos
de arvore e 18 ramais, todos chegando ao quadro.

**Limites ditos.** E' esboco de LIGACAO, nao tracado: as retas atravessam
parede, nao dizem por onde o eletroduto passa, quantos condutores leva nem o
diametro. O comprimento dos circuitos NAO sai dele (segue o criterio
declarado do D207). Em planta cheia as retas se cruzam e poluem o desenho;
por isso a camada propria.

**Fase 5: o que continua aberto.** Gabarito da ponte inteira (planta ate o
quadro) contra um projeto entregue: depende de planta de ambientes real e do
projeto correspondente, que nao existem na maquina.

## D213 - Plano de 2026-10-08: Fase 4 - o DWG do galpao conferido por ida e volta, sem AutoCAD (2026-10-09) - FECHADO (so medicao)

**Por que.** O DWG da entrega nunca foi aberto num AutoCAD (nao ha CAD na
maquina) e isso segue dependendo do usuario. O que da para medir sem ele: se
o DWG guarda tudo o que o DXF tinha.

**Medido.** `galpao-20x28_5.dwg` convertido de volta a DXF pelo ODA File
Converter 27.9.0 e relido com o ezdxf em modo de recuperacao, ao lado do DXF
de origem:
- auditoria do ezdxf: 0 erros e 0 correcoes nos dois arquivos;
- espaco do modelo: 8702 entidades nos dois, mesma contagem por tipo e por
  camada;
- 14 folhas com os mesmos nomes; mesmos blocos; mesma unidade;
- todos os textos iguais;
- 28 cotas com a mesma medida pela geometria e o mesmo texto.

**Erro meu no caminho.** A primeira comparacao acusou as 28 cotas como
diferentes: eu lia o campo de medida gravada, que o DXF de origem nao traz e
o ODA devolve como -1 (a recalcular). Medindo pela geometria nos dois lados,
sao iguais. Nao era defeito do arquivo.

**Limite.** Isto prova que o DWG nao perdeu entidade, camada, folha, texto
nem cota em relacao ao DXF. NAO prova que o AutoCAD o abre sem aviso nem que
o desenho aparece como esperado na tela (fontes, espessuras, viewport): isso
so abrindo num CAD de verdade, e continua com o usuario. Nenhum codigo mudou.

## D214 - Plano de 2026-10-08: Fases 3 e 4 - as pranchas do IFC saem do `rodar_tudo` (2026-10-09) - FECHADO

**Por que.** O D194 deixou aberto: "ligar `dxf_prancha` ao `rodar_tudo`: a
entrada dele sao os SVG do Bonsai, que ainda nao e' saida do pipeline". O
pacote do galpao do cliente (D195 a D204) foi montado por quatro comandos
dados a mao, um depois do outro (Blender, `dxf_prancha`, ODA, Inkscape).

**Entregue.**
- `pranchas_ifc.py` (modulo novo): `gerar(ifc, pasta, titulo, revisao,
  carimbo)` copia o IFC do motor para a pasta de trabalho (o Bonsai grava no
  arquivo que abre; o original nao e' tocado), roda o script do Bonsai sem
  janela, converte os desenhos em DXF com a lista de material do proprio IFC
  (`dxf_prancha.gerar_de_pasta`), gera o DWG pelo ODA e o PDF de cada folha
  pelo Inkscape. Cada programa de fora e' procurado na maquina (variavel de
  ambiente `BLENDER_EXE` / `ODA_EXE` / `INKSCAPE_EXE`, pasta de instalacao,
  PATH); o que faltar ou falhar fica em `nao_gerado` com o motivo, e uma
  entrega so aparece no resultado com o arquivo gravado e nao vazio. Vista
  que o Bonsai nao conseguiu gerar aparece como INCOMPLETO. Pasta de
  trabalho de corrida anterior e' renomeada (`.anterior-<data>`), nunca
  apagada nem reaproveitada.
- `rodar_projeto.rodar_tudo(..., com_pranchas_ifc=False,
  carimbo_pranchas=None, revisao_pranchas="00")`: passo 2c, depois do IFC.
  Pedido, nao padrao: leva minutos e depende de programas de fora. O
  resultado vai em `r["pranchas_ifc"]` e em `spec["estrutura"]`. Campo do
  carimbo nao declarado sai em branco (a ficha nao traz cliente nem
  responsavel).
- `dxf_prancha.py` deixou de ser script avulso (o `pranchas_ifc` o importa);
  saiu de `SCRIPTS_AVULSOS` e o cabecalho mudou. O uso pela linha de comando
  continua.
- 8 funcoes de teste em `tests/test_pranchas_ifc.py`, com o executor dos
  programas trocado por um que escreve os arquivos que cada um escreveria, e
  1 em `tests/test_pipeline_bim.py` (o `rodar_tudo` passa o IFC do passo 2b,
  a pasta, a revisao e o carimbo declarados, e so quando pedido).

**Medido no galpao do cliente (20 x 28,5 m), com os programas de verdade.**
`rodar_tudo(spec, com_3d=False, com_executivo=False, gerar_dossie=False,
com_pranchas_ifc=True)` em pasta nova (`plano-2026-10-d214`, ignorada pelo
git): 163 s ao todo, 141 s nas pranchas; 13 desenhos, nenhum passo do Bonsai
com erro; 6 folhas A1 em PDF; DXF de 14 folhas e DWG de 264 kB. O DXF que
saiu do pipeline, ao lado do que tinha sido montado a mao e conferido no
D213: mesma contagem por tipo e por camada (8702 entidades), mesmas 14
folhas, mesmos blocos, textos e cotas. Folha EST-01 vista em imagem.

**Limites.** Os testes nao sobem Blender, ODA nem Inkscape: a costura e'
testada, os programas so foram exercitados na corrida medida acima. O script
do Bonsai segue em `docs/fase3-bonsai/scripts/` e so conhece o galpao. O
titulo passado ao script nao aparece no carimbo das folhas do Bonsai (a
celula mostra o titulo curto das vistas). DWG ainda nao aberto no AutoCAD.
O `relatorio_consolidado` nao lista as pranchas do IFC.
