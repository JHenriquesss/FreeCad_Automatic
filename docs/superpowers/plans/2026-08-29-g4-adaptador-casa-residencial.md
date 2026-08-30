# Plano G4 — Adaptador de casa residencial real

**Design:** `docs/superpowers/specs/2026-08-29-g4-adaptador-casa-residencial-real.md`
**Data:** 2026-08-29

## Sequência executada (TDD)

1. **Transcrição normativa (AR300).** Consulta ao notebook elétrico
   `78cd2efd`, fonte `d213019d` (NBR 5410:2004), com `cited_text` literal dos
   itens 9.5.2.1.1, 9.5.2.1.2, 9.5.2.2.1 (a–e), 9.5.2.2.2 (a–b), 9.5.3.1 e
   9.5.3.2. Nada foi escrito de memória.
2. **`arquitetura_residencial.py` + 34 testes.** Previsão de carga por
   ambiente, degraus da norma parametrizados (6 m², 4 m² inteiros, 3,5 m,
   5 m, 2,25 m², 600/100 VA) e a checagem isoperimétrica de rótulo ×
   geometria.
3. **Saturação das tabelas da NBR 8160.** `hidraulica_predial` já tinha
   `_menor_dn_sat`, mas quatro funções descartavam a flag. Criados
   `diametro_ramal_esgoto_sat`, `diametro_tubo_queda_sat`,
   `diametro_coletor_sat` e `diametro_ramal_ventilacao_sat`; as funções
   antigas passaram a delegar (compatibilidade com o galpão). `galpao_hidraulica`
   ganhou o gate `esgoto_saturacao`.
4. **`hidraulica_residencial.py` + 26 testes.** Água fria, esgoto/ventilação e
   pluvial da casa, sem DN default: casa sem aparelhos fica bloqueada.
5. **`casa_residencial.py` + `desenho_casa_residencial.py` + 26 testes.**
   Adaptador com as três disciplinas e a conferência ponto declarado × mínimo
   normativo, mais três pranchas SVG.
6. **`projects/casa-residencial/`.** Spec real de casa térrea de dois
   dormitórios: 7 ambientes, 27 pontos, 6 circuitos, rede hidráulica completa.
7. **Renderizar-e-olhar.** As três pranchas foram rasterizadas e inspecionadas.

## Achados durante o loop

- **Saturação silenciosa (NBR 8160).** Quatro funções de diâmetro devolviam o
  maior DN tabelado sem dizer que a tabela havia estourado. `DN75` saía igual
  para 60 e para 600 UHC de ventilação, com `OK=True`. Corrigido com flag e
  gate efetivo, nos dois orquestradores (casa e galpão).
- **Dupla escapa no SVG.** A primeira versão de `desenho_casa_residencial`
  chamava `esc()` antes de `texto()`, que já escapa: um nome de ambiente com
  `<` ou `&` imprimiria `&amp;lt;` literal na prancha. Só o teste que
  **parseia** o SVG e lê o texto do nó pegou; teste por substring não pegaria.
- **`i_default` por coincidência de valor.** `diametro_pluvial` marcava a
  intensidade como assumida sempre que ela igualava 150 mm/h, mesmo quando o
  projeto a tinha confirmado. O módulo residencial deriva a flag de o spec ter
  declarado ou não o valor.
- **Filtro de nome morto (prevenido).** A conferência casa `points[].room` com
  o nome do ambiente. Nome normalizado (acento, caixa, espaço) e ponto órfão
  vira erro `ambiente_desconhecido_no_circuito` — sem isso, um `room` que não
  casa devolveria zero pontos em silêncio.

## Fora do escopo (registrado para as próximas fases)

- estrutura da casa (fundação, laje, alvenaria — alvenaria segue bloqueada por
  falta da NBR 16868 no acervo);
- código de obras municipal, NBR 15575 e NBR 9050;
- água quente residencial, reservatório e recalque;
- IFC/3D da casa (o adaptador declara apenas `report` e `drawings`).
