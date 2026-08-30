# G9 — Fundação do edifício

**Problema.** A descida de cargas do G3 sempre entregou `N_base` por pilar — e a
carga parava ali. O `edificio_adapter` declarava `fundacao: not_available`, num
prédio de 9 pavimentos cuja base recebe 1 542 kN no pilar central.

**Por que era barato.** Nada precisava ser criado: `fundacao_sapata` (sapata
armada + bloco de concreto simples), `estaca_profunda` (Aoki-Velloso sobre o SPT,
com Décourt-Quaresma e Teixeira de cross-check) e `geotecnia_spt` (a ponte
sondagem → tensão admissível) já existiam, aferidos e testados. O que faltava era
a **fronteira** entre a descida e eles: `fundacao_edificio.py`.

```
descida (N_base por pilar) + SPT declarado
     -> geotecnia_spt.recomenda_fundacao          (sapata x estaca)
     -> fundacao_sapata.dimensiona_sapata_env / dimensiona_bloco_env
        ou estaca_profunda.verifica_estaca                   (por pilar)
     -> gate  ->  IFC/3D
```

---

## As três decisões de projeto

### 1. A sondagem é entrada declarada — sem ela não há fundação

`fundacao_edificio` não tem `SIGMA_SOLO_DEFAULT`. A tensão admissível vem do SPT
(σ = N/50 no bulbo, `geotecnia_spt`) ou de um valor que o projetista assume
explicitamente; **não existe caminho em que ela seja arbitrada**. Sem
`estrutura.fundacao`, o escopo volta a dizer `not_available` e um aviso nomeado
(`fundacao_nao_declarada`) explica que a carga desce até `N_base` e para ali.

Arbitrar a tensão do solo decidiria a fundação inteira a partir de um número que
ninguém mediu — é o padrão que este repositório trata como bug, não como default.

### 2. Um tipo para a obra, uma geometria por pilar

O tipo (sapata / bloco / estaca) é escolhido **uma vez**, pela sondagem sob o
pilar mais carregado: obra não mistura fundação rasa e profunda sem decisão
explícita. Já a geometria é dimensionada **pilar a pilar** — no projeto
persistido isso dá três famílias em vez de doze sapatas de 2,50 × 2,50:

| posição | N de dimensionamento | sapata adotada |
|---|---|---|
| canto (4×) | 367,7 kN | 1,20 × 1,20 × 0,35 m |
| extremidade (6×) | 661–746 kN | 1,50 × 2,00 × 0,60 m |
| interno (2×) | 1 542,0 kN | 2,50 × 2,50 × 0,80 m |

O tipo declarado vence a sondagem, mas a divergência é publicada
(`tipo_diverge_da_sondagem`) em vez de a recomendação sumir.

### 3. A ação horizontal entra — e o que não entra é dito

O que **entra**: o momento global de tombamento (vento/desaprumo, o mesmo número
que alimentou γz) repartido entre as prumadas como um binário pelo módulo de
resistência da malha de fundações, `dN_i = M·x_i / Σx_j²`. É a mesma conta que
`estaca_profunda.carga_estaca_grupo` faz dentro de um bloco, aplicada aqui ao
conjunto de pilares — o edifício visto como uma fundação só, que é o que resiste
ao tombamento. O cortante da base entra dividido entre as prumadas, alimentando o
FS ao deslizamento.

Isso não é decoração: no pilar de canto o `N` de dimensionamento sai de 235 kN
(gravitacional) para **367,7 kN**. E cada pilar é verificado nos **dois** casos —
sotavento (que dimensiona o solo) e barlavento, que *alivia* o peso estabilizante
e é quem dimensiona tombamento e deslizamento. Verificar só o maior `N` deixaria
o segundo passar despercebido; é o mesmo motivo pelo qual `dimensiona_sapata_env`
existe.

Momento e normal entram **ambos característicos** — `M_base_kNm` sai de
`Fa = Ca·q·Ae` sem γf, igual ao `N_base_k` da descida. Misturar um de cálculo com
o outro característico é o tipo de erro que passa despercebido e sobredimensiona
a obra inteira.

O que **não entra**: o momento fletor na base de *cada* pilar. O modelo de
estabilidade é um pórtico plano **global** para γz e ELS e não devolve esforço
por barra. As combinações vão com M = 0 no topo da sapata, e o escopo publica
`momento_base_pilar: not_available`. Dimensionar uma sapata para um momento que
ninguém calculou seria pior que dizer que ele falta.

---

## O aceite

`fundacao` saiu de `not_available` no escopo do `edificio_adapter`:

```json
"scope": {
  "fundacao": "implemented",
  "momento_base_pilar": "not_available",
  "viga_baldrame": "not_available",
  "recalque_diferencial": "not_available"
}
```

Os três `not_available` que sobraram são as fronteiras **dentro** da fundação,
nomeadas em vez de omitidas — capacidade não declarada é capacidade que não
existe, mas capacidade declarada que não entrega faz o manifesto mentir.

O projeto persistido passou a declarar o perfil SPT, com a proveniência escrita
no próprio spec: *"A CONFIRMAR — perfil de sondagem SPT do terreno; sem laudo
real este é o dado que o projetista tem de substituir"*.

### A fundação virou peça do modelo

Agora que existe, ela entra no BIM: `IfcFooting` sob cada pilar com o **topo na
cota de apoio** (enterrada, não a céu aberto), num `IfcBuildingStorey` "Fundacao"
próprio — sem ele as sapatas cairiam dentro do Tipo 1 no navegador do
visualizador. A estaca vira `IfcPile` **cilíndrica**: um prisma D×D daria 27 % a
mais de concreto no quantitativo e faria o cross-check reprovar, então
`build_concreto` ganhou `Part.makeCylinder` e `geometria_membros` ganhou o volume
πD²/4.

Cross-check puro × FreeCAD headless, nos dois caminhos:

| | peças (puro = FreeCAD) | concreto | interpenetração OCCT |
|---|---|---|---|
| sapata | 327 = 327 | 226,638 = 226,638 m³ | 0 |
| estaca | 343 = 343 | 235,800 = 235,800 m³ | 0 |

---

## Fronteiras que o G9 nomeou em vez de esconder

- **momento na base do pilar** — o modelo global não o produz (acima);
- **bloco de coroamento fora de 2 ou 4 estacas** — `estaca_profunda` só tem o
  modelo de bielas para esses dois números. Com 3 estacas o bloco **não** é
  dimensionado nem modelado, e o resultado diz quais pilares ficaram assim
  (`bloco_de_coroamento_nao_dimensionado`, escopo `partial`) em vez de o bloco
  desaparecer do quadro;
- **comprimento da estaca** — sem `estaca.L_m` declarado, a ponta para na **base**
  da primeira camada competente (N ≥ 20), não no topo. É a escolha conservadora
  que não exige arbitrar um embutimento ("3D", "1 m") que dado nenhum fornece;
- **viga baldrame** e **recalque diferencial** — abertos.

---

## Testes

`tests/branches/g9/`, 36 testes. Eles prendem a **ligação**, não os cálculos —
que têm os seus próprios arquivos:

- a sondagem como entrada declarada: sem ela não há fundação; perfil malformado,
  tipo inválido e estaca sem SPT são recusados **com motivo**; entrada declarada
  que não fecha (sem camada competente) vira **gate reprovado**, nunca uma
  fundação que some do resultado em silêncio;
- geometria por pilar **medida**: a área da sapata de canto tem de ser menor que
  a do pilar interno, e a altura tem de satisfazer a rigidez de 22.6.1 contra a
  seção do lance da **base** — não a do topo;
- o binário do tombamento **soma zero** e cresce com o braço; o caso de
  barlavento existe e tem cortante;
- solo fraco demais **reprova** em vez de adotar a maior geometria da escada e
  devolver OK — o padrão de saturação silenciosa que este projeto persegue;
- no IFC: a sapata está sob o pilar que ela recebe (rótulo × geometria, medindo
  os dois centros), com o topo na cota de apoio, e a estaca tem seção circular.
