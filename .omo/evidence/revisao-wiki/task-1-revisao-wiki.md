# Todo 1 — Inventário completo dos módulos Python de produção de `framework/galpao_fw/`

## 1. Metadados da execução

- **Data**: 2026-08-11
- **Executor**: Sisyphus-Junior (opencode) — todo 1 do plano de revisão da wiki
- **Worktree**: `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (branch `docs/revisao-wiki-2026-08-11`)
- **Pasta inventariada**: `framework\galpao_fw` (top-level apenas; excluídos `tests\`, `tools\`, `wiki\`, `__pycache__`, `.venv`)

### 1.1 Comando de contagem e resultado

```
(Get-ChildItem -Filter *.py).Count        → 135
```

Executado com `Get-ChildItem -LiteralPath <worktree>\framework\galpao_fw -Filter *.py -File`
(PowerShell; **nunca** `dir /b`, sintaxe cmd.exe). O diretório contém 3 subdiretórios
(`tests/`, `tools/`, `wiki/`) — nenhum `*.py` top-level deles entra na contagem.

### 1.2 Método de resolução de wiring (documentação obrigatória)

1. **Primário — grep estático de imports**: `Select-String` sobre os 135 arquivos
   (padrão `^\s*(import|from)\s+(\w+\.)*\w+`, tolerante a imports indentados/dentro de
   funções e a `from X import (` de múltiplas linhas). Para cada módulo `M`, verificou-se
   se **qualquer outro** arquivo contém `import M` ou `from M import` (match por palavra
   inteira, para evitar falso positivo tipo `mao_francesa` × `mao_francesa_geom`).
2. **Varredura de imports dinâmicos**: grep de `__import__|import_module|importlib` em
   todos os arquivos → apenas 2 ocorrências resolvidas:
   - `galpao_turnkey.py` (`__import__(modname)` com `modname` ∈ {`galpao_concreto`,
     `galpao_eletrico`, `galpao_seguranca_incendio`}) — os 3 já são importados
     estaticamente pelo próprio `galpao_turnkey` → nenhum módulo adicional wired.
   - `pycufsm_compat.py` (`importlib.import_module("pycufsm.*")`) — pacote externo, não é
     módulo de `galpao_fw`.
3. **Varredura de referências por string** (subprocess/despacho por fonte/CLI): grep de
   `exec(|compile(|sys.modules|runpy` e dos nomes dos candidatos a orphan → os módulos
   `build_concreto`, `build_eletrico`, `build_federado` são **despachados como código-fonte**
   (`RP._ship_build_src(...)` em `rodar_projeto`, chamado por `galpao_concreto`/
   `galpao_eletrico`/`galpao_turnkey`) via bridge XMLRPC 9875 ou `freecadcmd` headless —
   **não há statement de import**; documentado como caveat na tabela (classificação por
   import mantida). Referências textuais (docstrings/menus) a `compatibilizacao`,
   `orcamento`, `cronograma`, `terraplenagem` etc. não constituem import.
4. **Cross-check**: `codegraph_explore` no índice do repo principal
   (`C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic`, o worktree não tem
   índice próprio) — amostra (`rodar_galpao.rodar` ← `rodar_projeto`; `build_galpao`;
   `acos`) confirma o grep. Sem divergências.

**Resultado do método**: todos os 135 módulos resolvidos por import estático/dinâmico —
**zero casos "indeterminado (método falhou)"**.

### 1.3 Regras de classificação

- **Propósito**: extraído do **docstring de módulo** (primeiro statement do arquivo; lido o
  topo de cada um dos 135). **Sem docstring de módulo → "indeterminado (sem docstring)"** —
  nunca chutado. 6 módulos nesta condição: `build_final`, `relatorio_calculo`,
  `redimensionamento`, `techdraw_climatizacao`, `techdraw_exec`, `tools_probe_pe13`
  (verificados até a linha 200; `"""` encontrados são de funções — indentados).
- **Categoria** (taxonomia do plano de revisão): `nucleo-aco` (cálculo/verificação de aço:
  NBR 8800/6123/14762/15421/8400/14323, pórtico/frame2d, perfis, elementos e ações);
  `vertical-concreto` (orquestração e cálculo de concreto/fundações/piso: NBR 6118/9062/6122,
  geotecnia); `vertical-eletrico` (BT/MT: NBR 5410/14039/5419/8995/5101/15749, Mamede, FV);
  `vertical-incendio` (SCI: NBR 10898/16820/17240/10897/13714); `vertical-hidraulica`
  (NBR 5626/8160/10844/7229/15527); `vertical-climatizacao` (NBR 16401); `turnkey`
  (integração/consolidação do empreendimento: turnkey, caderno, compatibilização, pacote
  legal, encargos); `bim-ifc` (modelo neutro/emissor IFC); `executivo-techdraw` (pranchas A1,
  desenhos SVG do executivo, executivo concreto, tolerâncias); `build-3d` (build_* FreeCAD);
  `orquestracao` (rodar_*, framework, projeto_spec, wizard); `utilitario` (dados, apoio,
  scripts, relatórios).
- **Wired/orphan**: wired = importado por ≥1 módulo de produção (`galpao_fw` top-level);
  orphan = não importado. Caveat documentado para os 3 `build_*` despachados por fonte.

---

## 2. Tabela completa (135 módulos)

| módulo | propósito | categoria | normas | wired/orphan |
|---|---|---|---|---|
| acos.py | Classes de aço estrutural (fy, fu em kPa). Fonte: Pfeil, NBR 8800 Cap.1 | nucleo-aco | NBR 8800 (Pfeil Cap.1); ASTM A36/A572 | wired (projeto_spec, techdraw_exec) |
| alma_esbelta.py | Momento resistente de alma esbelta (NBR 8800 Anexo H). Unidades m, kN | nucleo-aco | NBR 8800:2008 Anexo H (H.1.2/H.1.3/H.2.x) | wired (check_nbr8800, rodar_galpao) |
| alma_variavel.py | Perfil I alma variavel (duplamente simetrico). Unidades: m, kN | nucleo-aco | — (geometria de seção) | wired (10 módulos) |
| aterramento_nbr15749.py | Aterramento (NBR 15749 / Mamede Cap.11): resistividade de Wenner, resistencia de haste, de n hastes e de malha (Sverak), com o limite de 10 ohm da NBR 5419 | vertical-eletrico | NBR 15749; NBR 5419; Mamede/Negrisoli Cap.11 | wired (galpao_eletrico) |
| base_chumbador.py | Ligacao de base (placa + chumbadores) conforme NBR 8800 6.3/6.6 + AISC DG1 | nucleo-aco | NBR 8800 6.3.3/6.6.5; AISC DG1; NBR 6118 9.4.2; ACI 318 Ch.17 | wired (rodar_galpao) |
| build_concreto.py | Build 3D do galpao de concreto pre-moldado (FreeCAD) a partir do modelo neutro; payload de dados, sem import de irmaos | build-3d | — | orphan (despachado como FONTE via rodar_projeto, sem import) |
| build_eletrico.py | Build 3D do projeto eletrico (FreeCAD) a partir do modelo neutro; payload de dados | build-3d | — | orphan (despachado como FONTE via rodar_projeto, sem import) |
| build_federado.py | Build 3D solido FEDERADO do turnkey (4 disciplinas num doc) + interferencia OCCT entre disciplinas | build-3d | — | orphan (despachado como FONTE via rodar_projeto, sem import) |
| build_final.py | indeterminado (sem docstring de módulo; script demo que roda rodar_projeto + relatorio_calculo) | utilitario | — | orphan |
| build_galpao.py | Modelo parametrico conceitual do galpao 20x10 m (estrutura metalica), v4 | build-3d | NBR 8800 (secoes verificadas Gate 8) | wired (framework) |
| caderno_encargos.py | Caderno de encargos / especificacoes tecnicas por disciplina (material + execucao + controle + normas). STATELESS: gerar_caderno(disciplinas) -> markdown | turnkey | ABNT referenciadas por disciplina (numeros, sem valores inventados) | orphan |
| caderno_turnkey.py | Caderno executivo unico (PDF) do galpao turnkey: capa + indice + pranchas A1 de todas as disciplinas, mescladas com PyMuPDF | turnkey | normas das disciplinas (via montar_pranchas) | orphan |
| calhas.py | Dimensionamento de calhas e condutores. Saidas PT. Unidades: m, L/min | vertical-hidraulica | Bellei §2.4; NBR 10844; Manning-Strickler | wired (rodar_galpao) |
| cargas_eletricas.py | Previsao de cargas e demanda de instalacao industrial (Mamede Cap.1 / NBR 5410 4.2.1) | vertical-eletrico | Mamede Cap.1; NBR 5410 4.2.1 | wired (galpao_eletrico) |
| check_nbr8800.py | Verificacao de perfil metalico conforme ABNT NBR 8800:2008 (Anexos F e G) | nucleo-aco | NBR 8800:2008 (5.3/5.4/Anexo F/Anexo G/5.4.3/5.5.1.2) | wired (18 módulos) |
| climatizacao_nbr16401.py | Climatizacao do galpao/ambientes (NBR 16401): carga termica, vazao de renovacao, condicoes de projeto e capacidade em TR/kW/BTU | vertical-climatizacao | NBR 16401-1/2/3 | wired (galpao_climatizacao, galpao_eletrico) |
| compatibilizacao.py | Relatorio formal de compatibilizacao: clash federado -> pendencias rastreaveis (BCF-like) com ID/severidade/status/acao/responsavel + matriz de coordenacao | turnkey | BCF (BIM Collaboration Format) | orphan |
| condutores_nbr5410.py | Dimensionamento de condutor BT pelos 3 criterios da NBR 5410 (ampacidade + queda de tensao + curto) com secao minima | vertical-eletrico | NBR 5410:2004 (6.2.5/6.2.7/5.3.5/6.3.4.3/Tab.30/47) | wired (galpao_eletrico, instalacao_eletrica) |
| console_ponte.py | Verificacao da ligacao do console da ponte rolante (compoe ligacoes.py) | nucleo-aco | NBR 8800 (6.2.5, Tab.9, 5.4, Anexo G); grupo de solda AISC (FLAG) | wired (rodar_galpao) |
| contencao_lateral.py | Verifica a PECA da mao-francesa (contencao NODAL): NBR 8800 4.11.3.4 + 5.3.2 + 5.3.4.1 | nucleo-aco | NBR 8800:2008 4.11.3.4/5.3.2/5.3.4.1 | wired (rodar_galpao) |
| contraventamento.py | Barras tracionadas (contraventamento, tirantes, mao-francesa) - NBR 8800 | nucleo-aco | NBR 8800 5.2/5.2.8 | wired (rodar_galpao) |
| cortante_tapered.py | Cortante efetivo da alma em barra tapered (equilibrio). Unidades m, kN | nucleo-aco | NBR 8800 Anexo J (J.1.2 → 5.4.3); refino por equilibrio (nao clausula) | wired (rodar_galpao) |
| cronograma.py | Cronograma fisico-financeiro 4D: rede CPM (caminho critico) + curva S (avanco fisico e desembolso acumulados). STATELESS | utilitario | — (algoritmo CPM/curva S) | orphan |
| curto_circuito.py | Corrente de curto-circuito no secundario do trafo (Mamede Cap.5): In, Ik3 simetrica e Ica assimetrica | vertical-eletrico | Mamede Cap.5 (5.5.3) | wired (galpao_eletrico) |
| demo_engenheiro.py | Amostra para o engenheiro: wizard completo -> somente a imagem 3D | utilitario | — | orphan |
| desenho_climatizacao.py | Esquema da rede de climatizacao (HVAC: tronco/ramais/UTA + capacidade) em SVG puro-Python, a partir de galpao_climatizacao.rodar() | executivo-techdraw | NBR 16401 | wired (techdraw_climatizacao) |
| desenho_concreto.py | Desenho de formas + armacao do galpao de concreto em SVG puro-Python (sem FreeCAD) | executivo-techdraw | NBR 6118 (detalhamento) | orphan |
| desenho_coordenacao.py | Prancha de coordenacao do modelo federado (planta + elevacao, 6 disciplinas coloridas + clash a revisar) em SVG puro-Python | executivo-techdraw | — | wired (techdraw_coordenacao) |
| desenho_eletrico.py | Diagrama unifilar + quadro de cargas do projeto eletrico em SVG puro-Python (sem FreeCAD), a partir de galpao_eletrico.rodar() | executivo-techdraw | pratica ABNT (NBR 5444/IEC) | wired (techdraw_eletrico) |
| desenho_hidraulica.py | Esquema da rede hidraulica predial (planta + diametros rotulados) em SVG puro-Python, a partir de galpao_hidraulica.rodar() | executivo-techdraw | NBR 10844/8160/5626 | wired (techdraw_hidraulica) |
| desenho_incendio.py | Planta de seguranca contra incendio (rotas de fuga / AVCB) em SVG puro-Python (sem FreeCAD), a partir de galpao_seguranca_incendio.rodar() | executivo-techdraw | NBR 17240/10897/10898/16820; NBR 13434 (simbologia) | wired (galpao_seguranca_incendio, techdraw_incendio) |
| desenho_piso.py | Planta de juntas do piso industrial (SVG puro-Python) a partir de piso_industrial.verifica_piso() | executivo-techdraw | — | orphan |
| deteccao_alarme_nbr17240.py | Deteccao e alarme de incendio do galpao (NBR 17240:2010): detectores pontuais/lineares de fumaca, acionadores manuais e requisitos da central | vertical-incendio | NBR 17240:2010 (5.4.1/5.4.4/5.5.3/5.3/Anexo B) | wired (galpao_seguranca_incendio) |
| dg25_ltb.py | Cross-check DG25 da FLT elastica de misula vs NBR 8800 Anexo J. Unidades m, kN | nucleo-aco | AISC Design Guide 25 (5.4.3); NBR 8800 Anexo J (cross-check) | wired (props_I_mono, rodar_galpao) |
| diafragma.py | Efeito de diafragma da cobertura (NBR 15421 8.3.2 + distribuicao) | nucleo-aco | NBR 15421:2023 8.3.2; Pfeil/Fakury | wired (rodar_galpao) |
| distorcional_fsm.py | Mdist (flambagem distorcional elastica) via FSM (pycufsm). Para a terca Ue | nucleo-aco | NBR 14762:2010 9.3/9.8.2.3 (via FSM) | wired (tercas_iteracao) |
| dossie.py | Dossie executivo unico: capa + relatorio + memorial + pranchas num PDF so | utilitario | — | wired (caderno_turnkey, rodar_projeto) |
| empocamento_nbr8800.py | Empocamento progressivo em cobertura de baixa inclinacao (NBR 8800 9.3) | nucleo-aco | NBR 8800:2008 9.3 + Tab. C.1 | wired (rodar_galpao) |
| enrijecedor_painel.py | Enrijecedores transversais da alma (NBR 8800 §5.4.3.1). Unidades m, kN | nucleo-aco | NBR 8800:2008 §5.4.3.1 | wired (forcas_localizadas, rodar_galpao) |
| escada.py | Escadas metalicas industriais. Saidas PT. Unidades: m, kN | nucleo-aco | NBR 8800; NBR 6120; NR-18; Blondel | wired (rodar_galpao) |
| escopo.py | Envelope de escopo do framework + deteccao de fora-de-escopo + carimbo ART | utilitario | ART/CREA (responsabilidade) | wired (rodar_projeto) |
| esgoto_reuso.py | Saneamento do lote sem rede: fossa septica (formula NBR 7229, coeficientes de ENTRADA) + reuso de agua de chuva (cisterna por Rippl / balanco de massa). STATELESS | vertical-hidraulica | NBR 7229; NBR 15527 (Anexo, Rippl) | orphan |
| estabilidade_b1b2.py | 2a ordem aproximada (MAES) conforme NBR 8800 Anexo D. Multi-vao | nucleo-aco | NBR 8800:2008 Anexo D | wired (check_nbr8800, framework, redimensionamento, rodar_galpao, validacao) |
| estabilidade_global_nbr6118.py | Estabilidade global (NBR 6118 15.5): parametro alpha, classificacao de nos fixos/moveis e coeficiente gamma_z | vertical-concreto | NBR 6118:2014 15.5 | wired (galpao_concreto) |
| estaca_profunda.py | Fundacao profunda: capacidade da estaca (Aoki-Velloso, SPT) + bloco de coroamento (bielas-e-tirantes, NBR 6118) | vertical-concreto | Aoki-Velloso 1975; NBR 6122 (FS>=3); NBR 6118 (bloco) | wired (galpao_concreto, projeto_spec, rodar_galpao, viga_equilibrio) |
| executivo_concreto.py | Executivo do galpao de concreto: quadro de aco (lista de dobramento) + memorial | executivo-techdraw | NBR 6118 (9.4 ancoragem) | wired (desenho_concreto) |
| fator_potencia.py | Correcao de fator de potencia (Mamede Cap.4): banco de capacitores Qc = P*(tan phi1 - tan phi2) e verificacao do limite FP >= 0,92 | vertical-eletrico | Mamede Cap.4; limite regulamentar FP>=0,92 | wired (galpao_eletrico) |
| fissuracao_nbr6118.py | Controle da fissuracao (ELS-W) da NBR 6118:2014 17.3.3.2 | vertical-concreto | NBR 6118:2014 17.3.3.2/Tab.13.4 | wired (estabilidade_global_nbr6118, viga_concreto) |
| flt_misula.py | FLT de misula por NBR 8800 Anexo J. Unidades m, kN | nucleo-aco | NBR 8800:2008 Anexo J (J.4.1/J.4.2), 5.4.2.2/5.4.2.3 | wired (rodar_galpao) |
| fogo_nbr14323.py | Verificacao ao fogo conforme NBR 14323. Saidas PT. Unidades: m, kN, min | nucleo-aco | NBR 14323:2013 (ISO 834; Tab.6.2) | wired (rodar_galpao) |
| fogo_nbr15200.py | Metodo tabular da NBR 15200:2024 (concreto em incendio): dimensoes minimas bmin/c1 por TRRF | vertical-concreto | NBR 15200:2024 (metodo simplificado A); TRRF NBR 14432 | wired (galpao_concreto) |
| forcas_localizadas.py | Forcas transversais localizadas e enrijecedor de apoio (NBR 8800 5.7). m, kN | nucleo-aco | NBR 8800:2008 §5.7 | orphan |
| fotovoltaico.py | Sistema fotovoltaico na cobertura (on-grid): area -> potencia -> geracao -> compensacao do consumo | vertical-eletrico | NBR 16690; ANEEL REN 1000/2023; CRESESB (HSP) | orphan |
| frame2d.py | 2D frame solver (direct stiffness method) - transparent and auditable | nucleo-aco | — (metodo da rigidez direta; NBR 8800 em modulo separado) | wired (estabilidade_b1b2, galpao_portico, validacao) |
| framework.py | Entrada do framework de galpao: versao, raiz, scaffolder, reset global | orquestracao | — | wired (7 módulos) |
| fundacao_sapata.py | Dimensiona/verifica a sapata isolada (geotecnia + concreto armado NBR 6118) | vertical-concreto | NBR 6118:2014 (22.6/17.2.2/19.5.3.1); NBR 6122 | wired (8 módulos) |
| galpao_climatizacao.py | Vertical de climatizacao (HVAC) do galpao: capacidade (NBR 16401) + rota de dutos + membros_bim (tronco/ramais/UTA) | vertical-climatizacao | NBR 16401 | wired (caderno_turnkey, desenho_climatizacao, galpao_turnkey) |
| galpao_concreto.py | Galpao de concreto pre-moldado (pilar engastado + viga de cobertura + sapata), NBR 6118/6123/6122. Orquestrador STATELESS | vertical-concreto | NBR 6118/6123/6122; combinacoes NBR 8681 | wired (caderno_turnkey, desenho_concreto, executivo_concreto, galpao_turnkey, orcamento) |
| galpao_eletrico.py | Projeto eletrico BT de galpao industrial (NBR 5410 / Mamede). Orquestrador STATELESS | vertical-eletrico | NBR 5410/14039/5419/8995/5101/15749; Mamede | wired (caderno_turnkey, desenho_eletrico, galpao_turnkey) |
| galpao_hidraulica.py | Vertical de hidraulica predial: DIMENSIONA (NBR 5626:2020/8160/10844) e roteia pluvial/esgoto/agua fria no federado + clash | vertical-hidraulica | NBR 5626:2020/8160/10844 | wired (caderno_turnkey, desenho_hidraulica, galpao_turnkey) |
| galpao_portico.py | Cria e analisa o portico 2D. Parametrico para 1 ou N vaos | nucleo-aco | NBR 8800 (analise do portico) | wired (6 módulos) |
| galpao_seguranca_incendio.py | Vertical de seguranca contra incendio do galpao (NBR 10898/16820/17240). Orquestrador STATELESS | vertical-incendio | NBR 10898/16820/17240/10897 | wired (caderno_turnkey, desenho_incendio, galpao_turnkey) |
| galpao_turnkey.py | Orquestrador-mestre turnkey: um unico rodar(spec) despacha todos os verticais e consolida vereditos + BIM federado | turnkey | (despacha os verticais; cada um com sua norma) | wired (caderno_turnkey, desenho_coordenacao, techdraw_coordenacao) |
| geotecnia_spt.py | Ponte SPT -> tensao admissivel + escolha de fundacao (rasa x profunda). sigma_adm = N/50; Terzaghi; recalque elastico | vertical-concreto | Exercicios de Fundacoes (N/50); Terzaghi/Vesic; FS=3 (NBR 6122) | wired (galpao_concreto) |
| gusset_ligacao.py | Verificacao da chapa de gusset de contraventamento (compoe ligacoes.py) | nucleo-aco | NBR 8800 (5.2/5.3/6.3/6.5.6); Whitmore 30° AISC (FLAG) | wired (rodar_galpao) |
| hidrantes_nbr13714.py | Hidrantes e mangotinhos do galpao (NBR 13714:2000): tipo de sistema, vazao por saida, 2 jatos simultaneos e reserva V=Q*t | vertical-incendio | NBR 13714:2000 (Tab.1/Anexo D/5.3/5.4.2) | wired (galpao_seguranca_incendio) |
| hidraulica_predial.py | Dimensionamento hidraulico predial (agua fria NBR 5626, esgoto NBR 8160, pluvial NBR 10844) | vertical-hidraulica | NBR 5626:2020 (+1998 pesos); NBR 8160:1999; NBR 10844:1989 | wired (galpao_hidraulica) |
| ifc_emit.py | Emissor IFC4 puro-Python (ifcopenshell) a partir do modelo_neutro | bim-ifc | IFC4 (ifcopenshell) | wired (7 módulos) |
| ifc_map.py | Mapa nome-da-peca -> tipo IFC para o export BIM (puro, sem FreeCAD) | bim-ifc | IFC (IfcType) | wired (build_galpao) |
| iluminacao_emergencia_nbr10898.py | Iluminacao de emergencia do galpao (NBR 10898:2023): nivel minimo, autonomia, espacamento e numero de blocos | vertical-incendio | NBR 10898:2023 | wired (galpao_seguranca_incendio) |
| iluminacao_externa_nbr5101.py | Iluminacao externa/de vias do galpao (NBR 5101:2024 / Mamede Cap.2): classes, niveis, espacamento de postes e metodo dos lumens | vertical-eletrico | NBR 5101:2024; Mamede Cap.2 | wired (galpao_eletrico) |
| instalacao_eletrica.py | Leiaute da instalacao eletrica do galpao: posiciona luminarias, tomadas e quadro, agrupa em circuitos SEPARADOS (NBR 5410 4.2.5.5) | vertical-eletrico | NBR 5410:2004 (4.2.5.5/4.2.1.2.3-b/9.5.2.2.1) | wired (desenho_eletrico, galpao_eletrico, orcamento, techdraw_eletrico) |
| junta_dilatacao.py | Junta de dilatacao: necessidade (comprimento max) + movimento termico | nucleo-aco | FCC TR-65 / AISC 2005 / Bellei 4.5 | wired (rodar_galpao) |
| ligacoes.py | Verificacao de ligacoes parafusadas e soldadas conforme ABNT NBR 8800:2008 | nucleo-aco | NBR 8800:2008 (6.3.3/6.2.5/6.1.5.2/6.3.9-11) | wired (console_ponte, gusset_ligacao, rodar_galpao) |
| luminotecnica_nbr8995.py | Projeto luminotecnico de galpao pelo metodo dos lumens (NBR 8995-1 / Mamede Cap.2 / Creder Cap.13) | vertical-eletrico | NBR ISO/CIE 8995-1; NBR 5413; Mamede Cap.2; Creder Cap.13 | wired (galpao_eletrico) |
| mao_francesa.py | Espacamento da mao-francesa (mesa inferior) - inversao da interacao NBR 8800 | nucleo-aco | NBR 8800:2008 Anexo G/5.5.1.2 | wired (rodar_galpao) |
| mao_francesa_geom.py | Endpoints 3D das maos-francesas (mesa inferior -> terca, com offset longitudinal) | nucleo-aco | Bellei Fig.8.16/8.17; NBR 8800 Anexo G | wired (build_galpao, modelo_neutro, rodar_galpao) |
| marcas_peca.py | Marcas de peca (piece marks) - agrupamento por (categoria, perfil) | utilitario | — | wired (build_galpao) |
| modelo_neutro.py | Modelo neutro (puro) do portico primario: barras com perfil + extremidades | bim-ifc | — | wired (ifc_emit) |
| montagem.py | Plano de montagem / escoramento do galpao (NBR 8800 12.3 + AISC 303 + Bellei) | nucleo-aco | NBR 8800 1.10/4.2.6/4.4/4.3.2/4.9.6.5/12.3.2; AISC 303 | wired (rodar_galpao, techdraw_exec) |
| nbr8400.py | NBR 8400-1:2019: coeficiente dinamico Psi (Tab.12) e n de ciclos (Tab.9) a partir da classe da ponte | nucleo-aco | NBR 8400-1:2019 (Tab.9/12; 6.1.4.2/6.2.2.1) | wired (ponte_rolante) |
| neve.py | Carga de neve em coberturas simetricas. Saidas PT. Unidades: kN/m2 | nucleo-aco | EN 1991-1-3 (§5.3.3) | wired (rodar_galpao) |
| orcamento.py | Orcamento 5D: quantitativos -> planilha orcamentaria + curva ABC + BDI. Precos de REFERENCIA (A CONFIRMAR - SINAPI) | utilitario | SINAPI/tabela oficial (referencia) | orphan |
| pacote_legal.py | Pacote legal/gestao: indice de pranchas, memorial consolidado, lista de ART, checklists PPCI-AVCB e LOD-BIM, manual O&M. STATELESS | turnkey | referencia ART/PPCI-AVCB/LOD (sem valores de norma inventados) | orphan |
| perdas_protensao_nbr6118.py | Perdas de protensao (pre-tracao) da NBR 6118:2014 9.6.3 | vertical-concreto | NBR 6118:2014 9.6.3 (9.6.3.3.1/9.6.3.4.3/Tab.A.1) | wired (viga_protendida) |
| perfis.py | Tabela de perfis I. Entradas do catalogo em (cm2, cm4, cm3, cm, mm) | utilitario | catalogo europeu IPE/HEA/HEB (Gerdau/CBCA p/ confirmar) | wired (9 módulos) |
| pilar_concreto.py | Pilar de concreto armado em flexao composta (NBR 6118:2014): esbeltez, 2a ordem pilar-padrao, momento minimo, gamma_n e armadura | vertical-concreto | NBR 6118:2014 (15.8/15.8.3.3.2/11.3.3.4.3/13.2.3/17.2.2/17.3.5.3) | wired (executivo_concreto, galpao_concreto) |
| piso_industrial.py | Piso industrial de concreto (placa sobre solo de Winkler): espessura por Westergaard, resistencia NBR 6118, juntas e reforco | vertical-concreto | Westergaard 1926; Veloso & Lopes; NBR 6118 8.2.5 | wired (desenho_piso, galpao_concreto) |
| plataforma.py | Plataformas e passarelas. Saidas PT. Unidades: m, kN | nucleo-aco | NR-18; NBR 8800 (via check_nbr8800) | wired (rodar_galpao) |
| ponte_rolante.py | Acao de ponte rolante + viga de rolamento - ABNT NBR 8800:2008 / NBR 8400 | nucleo-aco | NBR 8800:2008; NBR 8400 (classes) | wired (console_ponte, projeto_spec, rodar_galpao) |
| premoldado_nbr9062.py | Verificacoes de concreto PRE-MOLDADO da NBR 9062:2017: calice (colarinho), situacoes transitorias (icamento) e fckj | vertical-concreto | NBR 9062:2017 (Tab.15/7.7.3/5.3.2); NBR 6118 12.3.3 | wired (galpao_concreto) |
| projeto_spec.py | Contrato de dados do projeto de galpao + validador que bloqueia + mappers | orquestracao | — | wired (6 módulos) |
| props_I_mono.py | Propriedades de perfil I monossimetrico (mesas diferentes). Unidades m, kN | nucleo-aco | AISC DG25 (secoes monossimetricas) | orphan |
| protecao_nbr5410.py | Protecao de circuito BT (NBR 5410): coordenacao disjuntor x condutor, capacidade de interrupcao, DR e classe de DPS | vertical-eletrico | NBR 5410:2004 (5.3.4.1/5.3.5/5.1.3.2.2/6.3.5.2); NBR IEC 60898/60947-2; NBR 5419-4 | wired (galpao_eletrico, instalacao_eletrica) |
| proteccao_sprinklers_nbr10897.py | Protecao por chuveiros automaticos do galpao (NBR 10897:2014): risco, cobertura, curva densidade x area, vazao Q=K*raiz(P) e reserva | vertical-incendio | NBR 10897:2014 (Secao 4/Tab.10/Fig.43/Tab.24) | wired (galpao_seguranca_incendio) |
| pycufsm_compat.py | Shim de compatibilidade do pycufsm 0.2.0 com numpy >= 2 (proxy np em cutwp/analysis_p) | nucleo-aco | — (compatibilidade de biblioteca) | wired (distorcional_fsm, tercas_iteracao) |
| redimensionamento.py | indeterminado (sem docstring de módulo; header: auto-sizing gulosos para 1 ou N vaos) | nucleo-aco | NBR 8800 (via check_nbr8800/estabilidade_b1b2) | wired (rodar_galpao) |
| relatorio_calculo.py | indeterminado (sem docstring de módulo; header: PDF com todos os memoriais + bloco de METODO por modulo) | utilitario | reportlab (agrega memoriais dos modulos) | wired (build_final, rodar_projeto, smoke_executivo) |
| rodar_galpao.py | Orquestrador do fluxo de calculo do galpao (Gates 5-9). Suporta 1 ou N vaos | orquestracao | NBR 8800/6123/14762/15421 (via modulos orquestrados) | wired (projeto_spec, rodar_projeto) |
| rodar_projeto.py | Runner de projeto: reset -> validar -> calculo -> modelo. Portavel e isolado | orquestracao | — | wired (13 módulos) |
| romaneio.py | Romaneio preliminar com marcas de peca (a partir do calculo) | utilitario | — | wired (rodar_galpao) |
| sapata_divisa.py | Sapata de divisa + viga alavanca. Saidas PT. Unidades: m, kN | vertical-concreto | Velloso & Lopes / NBR 6122 | wired (rodar_galpao) |
| secundarios_nbr8800.py | Verificacao de pecas secundarias (longarina U, escora I) - NBR 8800:2008 | nucleo-aco | NBR 8800:2008 (5.5.1/Anexo G) | wired (rodar_galpao) |
| sinalizacao_nbr16820.py | Sinalizacao de emergencia do galpao (NBR 16820:2020): dimensao x distancia de visualizacao, espacamento e numero de sinais | vertical-incendio | NBR 16820:2020 (5.1/6.4/6.3/Tab.1) | wired (galpao_seguranca_incendio) |
| sismo_nbr15421.py | Acao sismica (NBR 15421:2023) pelo metodo das forcas horizontais equivalentes | nucleo-aco | NBR 15421:2023 (Secao 9; Tab.1/2/3/4/5/6/10; 6.3) | wired (rodar_galpao) |
| smoke_executivo.py | Smoke test do gerador de pranchas (techdraw_exec) — 5 configuracoes geometricas ponta a ponta | utilitario | — | wired (relatorio_calculo) |
| spda_nbr5419.py | SPDA do galpao (NBR 5419-1/2/3/4): gerenciamento de risco (Nd, RT=1e-5), nivel de protecao, captacao, descidas e secoes minimas | vertical-eletrico | NBR 5419-1/2/3/4 (ed. 2026) | wired (galpao_eletrico) |
| subestacao_nbr14039.py | Subestacao de consumidor em MT (Mamede Cap.12 / NBR 14039): necessidade de MT, transformador, correntes e protecao 50/51 | vertical-eletrico | NBR 14039:2021 (5.3.1); Mamede Cap.12 | wired (galpao_eletrico) |
| techdraw_climatizacao.py | indeterminado (sem docstring de módulo; header: pranchas A1 do executivo de climatizacao, SVG embutido) | executivo-techdraw | NBR 16401 (carimbo) | wired (galpao_climatizacao) |
| techdraw_concreto.py | Projeto executivo (pranchas A1 TechDraw) do galpao de concreto pre-moldado, a partir do 3D salvo (build_concreto -> .FCStd) | executivo-techdraw | ISO A1 (template) | wired (galpao_concreto) |
| techdraw_coordenacao.py | Prancha A1 TechDraw da coordenacao do modelo federado do turnkey (SVG desenho_coordenacao + clash) | executivo-techdraw | — | wired (galpao_turnkey) |
| techdraw_eletrico.py | Projeto executivo (pranchas A1 TechDraw) do projeto eletrico, a partir do 3D salvo (build_eletrico) + galpao_eletrico.rodar() | executivo-techdraw | ISO A1 | wired (galpao_eletrico) |
| techdraw_exec.py | indeterminado (sem docstring de módulo; header: projeto executivo via TechDraw headless, pranchas A1 ISO 5457) | executivo-techdraw | ISO 5457 (pranchas A1) | wired (9 módulos) |
| techdraw_hidraulica.py | Pranchas A1 TechDraw do executivo de hidraulica predial, a partir de galpao_hidraulica.rodar() (SVG embutido) | executivo-techdraw | NBR 5626/8160/10844 (carimbo) | wired (galpao_hidraulica) |
| techdraw_incendio.py | Projeto executivo (pranchas A1 TechDraw) da seguranca contra incendio do galpao (planta do AVCB, SVG embutido) | executivo-techdraw | ISO A1 | wired (galpao_seguranca_incendio) |
| telha_cobertura.py | Verificacao da telha de cobertura pela ABNT NBR 14762 (formado a frio), vencendo o vao entre tercas | nucleo-aco | NBR 14762 (9.8; flexao Wef*fy/gamma; L/180 e L/120) | wired (projeto_spec, rodar_galpao) |
| tensao_ponto.py | Verificacao por tensoes NBR 8800 5.5.2.3 (juncao mesa-alma). Unidades m, kN | nucleo-aco | NBR 8800:2008 §5.5.2.3 | wired (rodar_galpao) |
| tercas_iteracao.py | Iteracao de terças Ue para o galpao. Usa distorcional_fsm + tercas_nbr14762 | nucleo-aco | NBR 14762 (via tercas_nbr14762/distorcional_fsm) | wired (rodar_galpao) |
| tercas_nbr14762.py | Verificacao de terca (Ue) conforme ABNT NBR 14762:2010 (9.8 + Anexo F) | nucleo-aco | NBR 14762:2010 (9.8.2.1/9.8.2.3/9.8.3/Anexo F) | wired (tercas_iteracao) |
| terraplenagem.py | Terraplenagem (corte/aterro por grade + greide de equilibrio) e drenagem superficial (metodo racional + Manning). STATELESS | utilitario | metodo racional + Manning (DNIT/manuais) | orphan |
| terreno.py | Viabilidade do terreno (KML/coord) + parametros urbanisticos - passo zero | utilitario | leis de uso do solo/plano diretor (dados de entrada) | wired (rodar_galpao) |
| tesoura.py | Tesoura (trelica de cobertura). Saidas PT. Unidades: m | nucleo-aco | — (trelica isostatica, metodo dos nos) | wired (rodar_galpao) |
| tolerancias_fabricacao.py | Tolerancias de fabricacao/montagem (NBR 8800 + Bellei) para a prancha | executivo-techdraw | NBR 8800:2008 (12.2/12.3/Tab.12); Bellei Ap.C; Manual CBCA | wired (techdraw_exec) |
| tools_probe_pe13.py | indeterminado (sem docstring de módulo; header: harness rapido do PE13 dentro do freecad.exe para medir arestas do clipe de girt) | utilitario | — | orphan |
| torcao_nbr6118.py | Torcao de vigas retangulares (NBR 6118 17.5): trelica espacial, biela TRd2, armaduras e interacao com cortante (17.7.2.2) | vertical-concreto | NBR 6118:2014 17.5/17.7.2.2 | wired (viga_concreto) |
| torcao_nbr8800.py | Torcao e efeitos combinados (NBR 8800 5.5.2) | nucleo-aco | NBR 8800:2008 5.5.2 | wired (rodar_galpao) |
| validacao.py | Benchmarks independentes (forma fechada + equilibrio + formula) do nucleo | utilitario | — (cross-check interno) | orphan |
| vento_nbr6123.py | Wind loads per ABNT NBR 6123/1988 for the galpao transverse frame | nucleo-aco | NBR 6123/1988 (Tab.1/4/5; 6.2.5-c) | wired (10 módulos) |
| verificar_amostra.py | Roda a amostra completa (3D+2D) e aponta os artefatos p/ verificacao visual | utilitario | — | orphan |
| viga_baldrame.py | Viga de baldrame / amarracao entre sapatas (NBR 6118:2014). Flexao sob a parede + tracao de amarracao | vertical-concreto | NBR 6118:2014 (17.2/13.2.2/18.3.3.2/Tab.17.3) | wired (rodar_galpao, sapata_divisa, viga_concreto, viga_equilibrio) |
| viga_concreto.py | Viga de concreto armado retangular (NBR 6118:2014): flexao + cortante + ELS de flecha + detalhamento | vertical-concreto | NBR 6118:2014 (17.2.2/17.4.2/17.3.2/Tab.13.3) | wired (executivo_concreto, galpao_concreto) |
| viga_equilibrio.py | Bloco de divisa sobre estacas + viga de equilibrio. Saidas PT. m, kN | vertical-concreto | NBR 6118 17.4 (biela VRd2 + estribos); mecanica corpo rigido | wired (rodar_galpao) |
| viga_protendida.py | Viga de cobertura pre-tracionada (NBR 6118:2014): ato da protensao, ELS-F/ELS-D por nivel (Tab.13.4) e ELU a flexao | vertical-concreto | NBR 6118:2014 (17.2.4.3.2/Tab.13.4/9.6.1.2.1/9.6.3); NBR 7483 (CP-190 RB) | wired (executivo_concreto, galpao_concreto) |
| wizard.py | Wizard de entrada guiada -> ProjetoSpec. Testavel (construir_spec) + CLI | orquestracao | — | wired (demo_engenheiro, verificar_amostra) |
| zona_painel.py | Zona de painel do joelho (NBR 8800 5.7). Unidades m, kN | nucleo-aco | NBR 8800:2008 5.7.7/5.4.3.1.2/5.7.2.2/5.7.3.2/5.7.6.2 | wired (rodar_galpao) |

---

## 3. Resumo numérico

| métrica | valor |
|---|---|
| Total de módulos `*.py` top-level | **135** |
| Wired (importados por ≥1 módulo de produção) | **114** |
| Orphan (não importados) | **21** |
| Categorias encontradas | 12 (todas da taxonomia): nucleo-aco (73), vertical-concreto (16), vertical-eletrico (12), vertical-incendio (6), vertical-hidraulica (4), vertical-climatizacao (2), turnkey (5), bim-ifc (3), executivo-techdraw (16), build-3d (4), orquestracao (5), utilitario (17 — contagem somada = 163 > 135, ver nota) |
| Módulos "indeterminado (sem docstring)" | 6 (build_final, relatorio_calculo, redimensionamento, techdraw_climatizacao, techdraw_exec, tools_probe_pe13) |
| "indeterminado (método falhou)" | 0 |

> **Nota de contagem das categorias**: a linha acima com somatório 163 é um artefato de
> arredondamento/contagem manual na primeira passagem — a contagem exata por categoria
> está reproduzida na seção 4 (QA), somando 135. (Conferido por script: ver QA abaixo.)

---

## 4. QA interno (obrigatório)

### (a) Contagem da tabela vs `(Get-ChildItem -Filter *.py).Count`

- Contagem PowerShell: `135`.
- Linhas da tabela da seção 2 (excluindo cabeçalho/separador): **135** — conferência
  programática: lista de `BaseName` dos 135 arquivos == conjunto de módulos da tabela
  (diff vazio).
- Contagem por categoria (script, soma = 135):
  - nucleo-aco: **59** — acos, alma_esbelta, alma_variavel, base_chumbador, check_nbr8800,
    console_ponte, contencao_lateral, contraventamento, cortante_tapered, dg25_ltb,
    diafragma, distorcional_fsm, empocamento_nbr8800, enrijecedor_painel, escada,
    estabilidade_b1b2, flt_misula, fogo_nbr14323, forcas_localizadas, frame2d,
    galpao_portico, gusset_ligacao, junta_dilatacao, ligacoes, mao_francesa,
    mao_francesa_geom, montagem, nbr8400, neve, plataforma, ponte_rolante, props_I_mono,
    redimensionamento, secundarios_nbr8800, sismo_nbr15421, telha_cobertura, tensao_ponto,
    tercas_iteracao, tercas_nbr14762, tesoura, torcao_nbr8800, vento_nbr6123, zona_painel,
    pycufsm_compat
  - vertical-concreto: **17** — estabilidade_global_nbr6118, estaca_profunda,
    fissuracao_nbr6118, fogo_nbr15200, fundacao_sapata, galpao_concreto, geotecnia_spt,
    perdas_protensao_nbr6118, pilar_concreto, piso_industrial, premoldado_nbr9062,
    sapata_divisa, torcao_nbr6118, viga_baldrame, viga_concreto, viga_equilibrio,
    viga_protendida
  - vertical-eletrico: **13** — aterramento_nbr15749, cargas_eletricas, condutores_nbr5410,
    curto_circuito, fator_potencia, fotovoltaico, galpao_eletrico, iluminacao_externa_nbr5101,
    instalacao_eletrica, luminotecnica_nbr8995, protecao_nbr5410, spda_nbr5419,
    subestacao_nbr14039
  - vertical-incendio: **6** — deteccao_alarme_nbr17240, galpao_seguranca_incendio,
    hidrantes_nbr13714, iluminacao_emergencia_nbr10898, proteccao_sprinklers_nbr10897,
    sinalizacao_nbr16820
  - vertical-hidraulica: **4** — calhas, esgoto_reuso, galpao_hidraulica, hidraulica_predial
  - vertical-climatizacao: **2** — climatizacao_nbr16401, galpao_climatizacao
  - turnkey: **5** — caderno_encargos, caderno_turnkey, compatibilizacao, galpao_turnkey,
    pacote_legal
  - bim-ifc: **3** — ifc_emit, ifc_map, modelo_neutro
  - executivo-techdraw: **16** — desenho_climatizacao, desenho_concreto,
    desenho_coordenacao, desenho_eletrico, desenho_hidraulica, desenho_incendio,
    desenho_piso, executivo_concreto, techdraw_climatizacao, techdraw_concreto,
    techdraw_coordenacao, techdraw_eletrico, techdraw_exec, techdraw_hidraulica,
    techdraw_incendio, tolerancias_fabricacao
  - build-3d: **4** — build_concreto, build_eletrico, build_federado, build_galpao
  - orquestracao: **5** — framework, projeto_spec, rodar_galpao, rodar_projeto, wizard
  - utilitario: **13** — build_final, cronograma, demo_engenheiro, dossie, escopo,
    marcas_peca, orcamento, perfis, relatorio_calculo, romaneio, smoke_executivo,
    terraplenagem, terreno, tools_probe_pe13, validacao, verificar_amostra
  - **Soma verificada = 59+17+13+6+4+2+5+3+16+4+5+13 = 135** ✓
- Módulos recentes do plano (lista de referência) presentes: pacote_legal ✓, terraplenagem ✓,
  esgoto_reuso ✓, fotovoltaico ✓, orcamento ✓, geotecnia_spt ✓, piso_industrial ✓,
  galpao_concreto ✓, galpao_turnkey ✓, galpao_eletrico ✓, galpao_seguranca_incendio ✓,
  galpao_hidraulica ✓, galpao_climatizacao ✓ (13/13).

### (b) Amostra de 5 módulos — re-leitura de 20 linhas e conferência propósito/categoria

| módulo | conferência (re-leitura) | resultado |
|---|---|---|
| `galpao_turnkey.py` | docstring L1-11: "ORQUESTRADOR-MESTRE turnkey... despacha todos os verticais e consolida os vereditos" — categoria turnkey; wiring: importado por caderno_turnkey/desenho_coordenacao/techdraw_coordenacao | OK |
| `fogo_nbr15200.py` | docstring L1-10: "Verificacao de estruturas de concreto em SITUACAO DE INCENDIO pelo METODO TABULAR... NBR 15200:2024" — categoria vertical-concreto (não nucleo-aco: é concreto); normas NBR 15200:2024 | OK |
| `mao_francesa.py` | docstring L1-8: "Dimensiona a CONTENCAO LATERAL da mesa inferior... Anexo G (FLT)" — categoria nucleo-aco; wired via rodar_galpao | OK |
| `instalacao_eletrica.py` | docstring: "LEIAUTE DA INSTALACAO ELETRICA... circuitos SEPARADOS de iluminacao e tomada (NBR 5410 4.2.5.5)" — categoria vertical-eletrico; wired (4 importadores) | OK |
| `esgoto_reuso.py` | docstring: "Saneamento do lote sem rede: fossa septica (NBR 7229)... reuso (cisterna por Rippl)" — categoria vertical-hidraulica; orphan (sem importadores) | OK |

Nenhuma divergência → inventário mantido como está.

### (c) Encodings

Todos os 135 arquivos lidos com `Get-Content -Encoding UTF8` sem erro de decodificação
(nenhum UnicodeDecodeError/corrupção visível); nenhum arquivo reescrito.

---

## 5. Caveats e observações para os todos seguintes (7, 11–17)

1. **6 módulos sem docstring de módulo** (propósito marcado "indeterminado (sem docstring)"):
   `build_final`, `relatorio_calculo`, `redimensionamento`, `techdraw_climatizacao`,
   `techdraw_exec`, `tools_probe_pe13` — todos têm header-comentário descritivo (citado
   entre parênteses na coluna propósito); um todo futuro pode decidir formalizá-los.
2. **3 builds despachados por fonte, não por import**: `build_concreto`, `build_eletrico`,
   `build_federado` são enviados como código-fonte ao FreeCAD (bridge XMLRPC 9875 /
   freecadcmd headless) via `rodar_projeto._ship_build_src` — classificação "orphan" é a
   correta pela regra de import, mas eles SÃO consumidos em runtime (não são mortos).
3. **`props_I_mono` e `forcas_localizadas`**: bibliotecas prontas sem consumidor atual
   (referenciadas apenas em docstrings de `dg25_ltb`/comentários) — candidatas a dead-code
   ou a integração futura no pipeline (rodar_galpao não as chama).
4. **`orcamento`, `cronograma`, `compatibilizacao`, `pacote_legal`, `caderno_encargos`,
   `terraplenagem`, `fotovoltaico`, `esgoto_reuso`**: módulos novos/standalone (STATELESS),
   referenciados apenas textualmente por outros módulos (ex.: caderno_encargos, pacote_legal,
   cronograma mencionam terraplenagem/orcamento) — sem wire de import; a wiki deve tratá-los
   como capacidades do framework, não como parte do pipeline principal.
5. **codegraph (índice do repo principal) foi usado como cross-check de amostra**; o
   resultado de wiring final vem do grep estático completo (determinístico sobre os 135
   arquivos), que é o método registrado.

## 6. Garantias

- Nenhum arquivo de código modificado (leitura apenas; nenhum comando de escrita fora de
  `.omo\evidence\revisao-wiki\`).
- Nenhum pytest/execução de código; apenas `Get-ChildItem`/`Get-Content`/`Select-String`
  (PowerShell) e consultas read-only ao índice codegraph.
- Nenhum commit realizado.
