# G8 — IFC e 3D das tipologias novas

**Problema.** Só o galpão entregava `ifc` e `model_3d`. `casa-residencial` e
`edificio-multipavimento` declaravam apenas `report` e `drawings`: o resultado do
cálculo existia como número no relatório e como prancha 2D, nunca como **modelo**.

**Escopo entregue.** As duas tipologias passam a declarar e produzir `ifc` e
`model_3d`. O edifício saiu pelo caminho barato previsto no roteiro de
interoperabilidade — `ifc_emit` puro-Python, sem FreeCAD, porque a malha do
pavimento-tipo é regular e já está calculada — com o caminho FreeCAD em paralelo
servindo de cross-check.

**Achado colateral: três defeitos reais, todos pré-existentes**, encontrados
*medindo* a geometria emitida antes de construir em cima dela.

---

## 1. A sapata do galpão de concreto saía 1000× menor no IFC

`galpao_concreto.membros_bim` emitia `dims` da sapata em **metros**; o
`ifc_emit` passa `dims` cru para o `IfcRectangleProfileDef`, que está em
**milímetros**. Uma sapata de 2,00 × 2,50 × 0,55 m chegava ao IFC como
**2,0 × 2,5 × 0,55 mm**.

Medido, não deduzido — a bbox real do `IfcFooting` no arquivo emitido:

```
antes:  IfcFooting [0.002  0.0025  0.00055]   (m)
depois: IfcFooting [2.0    2.5     0.55   ]   (m)
```

Ninguém tinha percebido porque `build_concreto` (o 3D) e `_aabb` (o clash) faziam
a conversão m→mm e viam a sapata certa; **só o IFC**, o entregável que sai da
casa, estava errado. Consertado na origem: `dims` é milímetro em toda parte, e a
conversão desapareceu dos três leitores.

**A divergência já tinha sido "consertada" pela metade.** Dois testes-guarda
(`test_aabb_caixa_aco_em_mm_nao_metros`, `test_caixa_aco_em_mm_nao_metros`)
documentavam um bug anterior: *"o bug x1000 inflava a sapata/bloco p/ ~km e
inundava o clash"*. Alguém já tinha topado com a mesma inconsistência, corrigiu
só a metade do **aço** — e cristalizou a outra metade num `assert`
("concreto continua em metros"). Os dois testes continuam existindo, agora
travando as **duas** metades contra uma unidade só.

**Efeito colateral do defeito 1, também corrigido:** com a sapata finalmente
existindo em tamanho real, apareceu um mapa de escala por disciplina
(`_ESCALA_M`, com `"concreto": 1000.0`) em `galpao_turnkey` e `build_federado` —
a indireção que existia justamente porque o concreto emitia em metros. Ele
multiplicava a sapata já corrigida por mil de novo: o clash federado saltou para
**2 289** conflitos, com volume comum de até 64 m³ numa peça de 2,75 m³.
Removido o mapa, **157**. E `orcamento._vol_membros_concreto`, que lia a mesma
caixa em metros, voltou a fechar.

## 2. O IFC e o 3D do mesmo galpão discordavam em meia altura de viga

O `build_concreto` sempre desenhou a viga a partir da **face inferior**
("apoia no topo do pilar"); o `ifc_emit` sempre centrou o perfil no **eixo**.
Duas descrições da mesma viga de cobertura, com d/2 de diferença:

```
FreeCAD : viga z 6,00 → 6,70 m   (apoiada no topo do pilar, que termina em 6,00)
IFC     : viga z 5,65 → 6,35 m   (35 cm enterrados dentro do pilar)
```

O IFC entregava o telhado 35 cm mais baixo do que o modelo 3D do mesmo projeto.
A ancoragem deixou de ser implícita e diferente em cada emissor: virou a chave
`ancoragem` (`"eixo"` — padrão, o que o galpão de aço sempre usou — ou `"base"`)
**declarada pelo membro** e lida pelos dois. O galpão de concreto declara
`"base"`; o 3D não mudou e o IFC passou a concordar com ele.

Este é o defeito que o cross-check do G8 expôs: montar o edifício pelos dois
caminhos e comparar cota a cota.

## 3. A laje engrossava e a carga não sabia

`laje_concreto.dimensiona_laje` adota a **menor espessura que atende**, que pode
ser maior que a declarada. No projeto persistido do edifício ela subia de 10 para
**12 cm** — e ninguém realimentava a carga. Vigas, pilares e a descida inteira
eram dimensionados com o peso próprio de uma laje que não seria construída:

| | antes | depois |
|---|---|---|
| espessura na carga | 10 cm | 12 cm |
| g do pavimento | 3,50 kN/m² | 4,00 kN/m² |
| gate da laje | `OK: True, h_cm: 12.0` | idem, **e compatibilizado** |

Meio kN/m² sobre 126 m² × 9 pavimentos, com todos os gates dizendo OK — a família
da *saturação silenciosa*, desta vez entre dois módulos em vez de dentro de um.

`edificio_multipavimento.rodar` passou a iterar um **ponto fixo** em h: a
espessura adotada realimenta a carga e o laço repete até parar de crescer
(converge em 2 iterações no projeto persistido). Não convergir vira gate
reprovado, nunca resultado dado por bom. O gate novo `laje_compatibilizada`
publica as três espessuras lado a lado — declarada, adotada e a que de fato pesou.

---

## O que ficou construído

### Edifício multipavimento — `bim_edificio.py`

Pilares (um membro por **lance**, com a seção que aquele lance adotou), vigas
(nervura abaixo da laje) e lajes de todos os pavimentos, com um
`IfcBuildingStorey` por pavimento — sem isso um prédio de 9 pavimentos abriria no
visualizador como um único "Térreo" com tudo dentro.

O empilhamento é o que faz as peças não se interpenetrarem:

```
laje  : z_k − h_laje  ..  z_k
viga  : z_k − h_viga  ..  z_k − h_laje   (nervura, sob a laje)
pilar : z_(k−1)       ..  z_k − h_viga   (encosta na face inferior da viga)
```

Cada par compartilha **face**, não volume. As vigas em Y são recuadas de b/2 nas
pontas onde encontram as vigas em X — sem esse recorte as duas se cruzariam no nó
e o mesmo concreto entraria duas vezes no quantitativo.

### Casa residencial — `bim_casa_residencial.py`

`desenho_casa_residencial` diz, na própria abertura, que não há planta baixa
porque "o programa declara área e perímetro, não posições". O BIM herdou a regra:
o que destrava o modelo é o **layout declarado** — o mesmo contrato de retângulos
que a elétrica já exigia, agora numa primitiva compartilhada
(`layout_ambientes.py`, com `layout_eletrico_residencial` delegando a ela).

Emite `IfcSpace` por ambiente, `IfcSlab` de piso e `IfcWall` **apenas** onde há
parede declarada. Não deduz paredes do contorno dos cômodos: espessura, material
e vão de esquadria não são declarados em lugar nenhum do spec, e um IFC com
paredes de espessura arbitrada seria lido como projeto sem que ninguém o tenha
projetado. O que o layout não declarou aparece no manifesto como `not_declared`.

A costura rótulo × geometria: o retângulo tem de reproduzir a **área e o
perímetro** que a arquitetura calculou — foi sobre esses dois números que a
previsão de carga da NBR 5410 9.5.2 foi feita. Divergiu, o entregável fica
`blocked` com o ambiente nomeado.

O projeto persistido já tem layout (declarado na seção elétrica), então ele
entrega IFC hoje — e a **procedência viaja no manifesto**
(`layout_origem: "eletrico.circuits.layout"`), porque um layout que a arquitetura
não declarou não pode ser lido como se ela o tivesse declarado.

---

## Aceite

**IFC4 que abre em visualizador externo.** "Abre" não é "o arquivo existe": é a
geometria ser construível. Um IFC com perfil degenerado ou representação órfã
carrega sem erro e mostra tela vazia. Duas provas, as que um visualizador faz:

| | edifício | casa |
|---|---|---|
| entidades com representação | 315 | 7 |
| triangulações geradas (`geom.iterator`) | **315** | **7** |
| `validate` com regras EXPRESS | **0 erros** | **0 erros** |
| elementos fora da árvore espacial | 0 | 0 |

**Cross-check contra o caminho FreeCAD** (o análogo do 12+12 do galpão), rodado
ao vivo com `freecadcmd` headless sobre o projeto persistido:

| | modelo puro (IFC) | FreeCAD (sólidos) |
|---|---|---|
| peças | 315 | **315** |
| volume de concreto | 203,822 m³ | **203,822 m³** |
| interpenetração (OCCT `common()`) | — | **0** |
| IfcColumn / IfcBeam / IfcSlab | 108 / 153 / 54 | **108 / 153 / 54** |

O cross-check é permanente: `_cruzar_puro_com_freecad` roda dentro do hook
`model_3d` e **reprova o entregável** se os dois caminhos divergirem — não é só
um teste, é um gate do manifesto.

**Nota de ambiente.** O importador IFC do FreeCAD 1.1.1 desta máquina está
quebrado (`'Settings' object has no attribute 'USE_BREP_DATA'` — o `importIFC`
ainda chama uma API que o ifcopenshell 0.8 removeu). Conferido que ele falha
igual com um IFC **exportado pelo próprio FreeCAD**, então é defeito da
instalação e não dos arquivos daqui. Por isso a prova de renderização usa o
iterador de geometria do ifcopenshell — o mesmo motor dos visualizadores
IfcOpenShell/BlenderBIM — e o caminho FreeCAD é cruzado pela via do build sólido.

---

## Testes

`tests/branches/g8/`, 48 testes (mais 5 marcados `build`, que exigem freecadcmd):

- **medem a geometria emitida**, não leem a string do perfil: o pilar não pode
  estar girado 90° (a dimensão `h` tem de cair na direção X com que a esbeltez
  foi calculada), a viga não pode estar deitada de lado, a parede tem de estar em
  pé, e a cadeia pilar → nervura → laje tem de fechar sem folga e sem embutir;
- **recusam o que não pode ser modelado**: viga mais rasa que a laje, seção que
  não reproduz o peso próprio da análise, layout que não bate com o programa,
  cômodo sobrando, parede oblíqua;
- **provam a ausência honesta**: sem layout não há modelo — `not_available` com
  motivo escrito, nunca um IFC vazio.
