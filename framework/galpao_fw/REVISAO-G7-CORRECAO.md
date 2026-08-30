# G7 — Auditoria de correção da camada religada

**Problema.** G6 provou que os sete entregáveis de gestão/sítio/desenho **rodam**.
Não provou que estão **certos**. Esses módulos nunca tinham passado por revisão
porque nunca produziram artefato que alguém olhasse.

**Método.** As três técnicas que este repositório já validou:
*renderizar-e-olhar* (rasterizar os SVG com `svglib`+`reportlab` e abrir a imagem),
*rótulo × geometria* (o quantitativo contra a geometria real do modelo) e
*saturação silenciosa* (o resultado satura num teto e devolve OK?).

**Resultado: nove defeitos reais.** Sete na camada de gestão, dois nas pranchas.

---

## 1. O orçamento ignorava o aço (o maior)

`orcamento.quantitativos_de_turnkey` derivava **3 dos 11** códigos da tabela de
preços — e nenhum deles era o aço. Um galpão **metálico** de 28,5 × 20 m saía
orçado em **R$ 72 mil**, só concreto.

O peso real já estava no resultado do próprio vertical:
`R["disciplinas"]["aco"]["raw"]["romaneio_peso_primario_kg"]` = **19.705,9 kg**
(≈ R$ 355 mil a 18 R$/kg) — **uma chave de distância**, nunca lida. Mesmo formato
do `filtro-de-nome-morto`: o código existe, o preço existe, o mapeamento não
acontece e nada avisa.

O peso do romaneio cobre só as peças **primárias** (colunas + rafters). Terças,
longarinas, contraventamento, ligações e chapas ficam de fora — dito junto com o
número, em `orcamento.NOTA_ACO_PRIMARIO`, não numa nota de rodapé.

## 2. Sapata cobrada como superestrutura (rótulo × geometria)

`_vol_membros_concreto` somava **todos** os membros em `concreto_estrut`. Dos
76,3 m³ de um galpão 40 × 20, **49 m³ eram sapata** — cobrados a 620 R$/m³
(concreto estrutural) em vez de 780 R$/m³ (fundação: concreto + forma + armadura +
escavação), com a linha de fundação zerada na planilha. A geometria estava certa;
o rótulo, não. Agora `membros_bim` é separado por `tipo == "Footing"`.

## 3. Orçamento parcial se apresentando como fechado

Com uma linha só, a saída era `sem_preco: []` e curva ABC "A = 1 item = 100 %" —
nenhum sinal de que faltava obra. `compor_orcamento` passa a devolver
`sem_quantidade` + `cobertura_pct`, e `relatorio_pt` imprime
`ORCAMENTO PARCIAL - N insumo(s) da tabela SEM quantitativo`. Custo omitido não é
custo zero.

## 4. Curva S saturada avisando só no manifesto

A curva S pondera o avanço físico pelo custo. Com custo em 2 de 8 atividades ela
atinge **100 % no dia 58 de 103** — verdade sobre o dinheiro conhecido, mentira
sobre o cronograma físico. O aviso existia no `manifest`, e **não** no
`relatorio.txt` nem no `curva-s.svg`, que são o que a pessoa lê. Novo
`cronograma.aviso_custeio(crono)` alimenta os dois artefatos.

## 5. Caderno especificando piso que ninguém dimensionou

`caderno_de_turnkey` acrescentava a seção PISO INDUSTRIAL sempre que o concreto
rodava — com `raw["piso"] is None`. O caderno prescrevia planicidade FF/FL,
espessura e módulo de reação do subleito de uma laje inexistente. É o **espelho
exato** do item 3: na mesma rodada, o orçamento sub-declarava e o caderno
super-declarava.

## 6. Pacote legal prometendo LOD de disciplina que não rodou

`checklist_lod_bim()` era estático: um projeto só de concreto entregava, num
documento de aprovação, a promessa de LOD 300 de instalações elétricas,
hidrossanitárias e incêndio. Agora filtra por disciplina executada
(`_LOD_DISCIPLINA`); coordenação/federado permanece sempre.

## 7. Uma frente do sítio derrubava as outras

`emitir_obras_sitio` calculava as quatro frentes em sequência e gravava no fim:
uma entrada faltando no esgoto **descartava o corte/aterro já calculado**, e o
manifesto dizia apenas `KeyError: 'N'` — sem nomear frente nem entrada. Novo
`_frente()` isola cada uma (mesmo princípio do `galpao_turnkey`), o status vira
`partial` e a falha nomeia frente + entrada ausente.

---

## 8. Pilar girado 90° — na planta **e** no BIM

Abrindo o PNG da planta de formas: o pilar 25 × 50 aparecia com **25 cm na
direção do vão**. `hx` é a dimensão no **plano do pórtico** (// vento, o eixo em
que o pilar é dimensionado como balanço engastado) e o papel/frame BIM tem
X = vão. Tanto `desenho_concreto.planta_formas_svg` quanto
`galpao_concreto.membros_bim` (`sec_pil = {"bf": hy, "d": hx}`) punham `hy` em X.

Construído como desenhado, o pilar fica com o **eixo fraco no plano do pórtico** —
Ix/Iy = (50/25)² = 4×. O **cálculo estava certo** (`dimensiona_pilar` recebe
`h = hx` como a direção do momento): errava o que a obra lê e o que o BIM entrega.
Mesma família do bug #35 (coluna de aço) e do giro de barra retangular do federado
achado em G3.

**Efeito colateral que confirma o achado:** com o pilar na largura real, o clash
federado passou a acusar `C-P4E × I-ACN1` (acionador manual de alarme penetrando o
pilar, 0,8 L) — coordenação real que a seção estreita demais escondia. Fica
classificado como **A REVISAR**, que é o correto.

## 9. A prancha de armação inventava aço

Vão de 20 m ⇒ viga de cobertura sai **protendida** (8 cordoalhas ø12,7), então
`arr_inf`/`arr_sup` ficam `None`. A prancha rotulava **`VIGA COB. 20x60 - inf 0
f0.0`** e caía num fallback `barras_v or [(10.0, 2)]` que desenhava **2 ø10 que o
cálculo nunca produziu**. Pior que omitir: mostrava armadura inexistente e
escondia a protensão inteira. Irmão do quadro de materiais que sumia em silêncio.

---

## Testes-guarda

`tests/test_orcamento_cobertura.py` (15) e `tests/test_pilar_orientacao_concreto.py`
(7). Os das pranchas são **geométricos**, não de substring: parseiam o SVG, medem
`width`/`height` do retângulo do pilar e **contam os círculos** contra o número do
rótulo. Nenhum dos ~1.400 testes existentes olhava o desenho.

Três testes em `test_turnkey_clash.py` foram corrigidos: cristalizavam o estado
anterior (`n_revisar == 0`, ordenação global por volume). A ordenação do módulo é
`(esperado, -volume)` — revisar primeiro — e o teste antigo só passava porque este
fixture nunca tinha item a revisar.

## Aberto

O adaptador `edificio-multipavimento` tem `DELIVERABLES = ("report", "drawings")`:
**não tem orçamento, cronograma, caderno nem pacote legal**. É gap de
*alcançabilidade* (classe G6) noutra tipologia, não de correção. Adicionar só a
função de derivação de quantitativos criaria mais uma ilha inalcançável — que é
exatamente o defeito que G6 fechou. Decisão do usuário.
