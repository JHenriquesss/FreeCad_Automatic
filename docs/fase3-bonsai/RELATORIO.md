# Fase 3 — teste do Blender + Bonsai

**Data:** 2026-10-08 · **Plano:** `decisoes-arquitetura-projetos.md`, Fase 3
**A decisão de migrar é de Henriques.** Este relatório só mede.

## Recomendação

**Migrar a saída de pranchas e de render para o Bonsai, mantendo o FreeCAD até
as pranchas do Bonsai cobrirem o que o executivo de aço entrega hoje.** Os seis
critérios passaram no que dependia da ferramenta; o que falta é automação nossa
(camada de pranchas), não limite do Bonsai. Nada precisa ser decidido às cegas:
as três folhas e o render estão em `evidencias/`.

O teste foi feito com a **especificação de teste** do galpão SJB
(`projects/galpao-sjb/project-spec-framework-teste.json`, dados sintéticos). O
galpão do cliente segue sem os dados reais de entrada.

## Ambiente medido

| Item | Valor |
|---|---|
| Blender | 5.2.1 LTS (já instalado) |
| Bonsai | extensão de `extensions.blender.org`, instalada neste teste |
| Inkscape | 1.4.4, instalado neste teste (PDF e PNG das folhas) |
| Modo | tudo sem janela (`blender -b --python`), dirigido por script |
| Máquina | 8 GB, com a suíte de testes rodando em paralelo durante as medições |

## Critérios

| # | Critério do plano | Resultado | Medida |
|---|---|---|---|
| 1 | O IFC da Fase 2 abre no Bonsai | **Aprovado** | 2,2 s; 905 de 905 elementos com geometria; envelope 40 × 20 × 7,2 m; nenhum elemento sem objeto |
| 2 | Planta, corte e elevação com qualidade de prancha | **Aprovado com ressalvas** | escala 1:100 gravada no desenho; cotas lidas do modelo; folha A1 com carimbo; ressalvas abaixo |
| 3 | Pranchas por disciplina como filtro do mesmo modelo | **Aprovado** | planta de fundação (`IfcFooting, IfcColumn`) e de cobertura (`IfcBeam, IfcMember`) saem do mesmo IFC por consulta no desenho |
| 4 | Render de apresentação do mesmo modelo | **Aprovado com ressalvas** | EEVEE sem janela em 41,7 s (1920 × 1080), materiais por classe IFC; iluminação ainda crua |
| 5 | A IA altera o modelo e regenera sem refazer | **Aprovado** | vão 20 → 24 m e comprimento 40 → 30 m na especificação: o motor redimensionou (HEB240 / IPE400), o IFC e as pranchas saíram de novo com cotas 24000, 30000 e 6 × 5000 |
| 6 | Tempo de geração aceitável | **Aprovado** | 6 vistas + 3 folhas em 51 s; ciclo completo cálculo → IFC → planta e corte em 94 s |

### Ressalvas do critério 2 (o que ainda não é prancha executiva)

- **Carimbo:** é o modelo padrão do Bonsai, em inglês. Trocar por um carimbo
  nosso é editar um SVG de modelo; não foi feito.
- **Disposição na folha:** o Bonsai empilha os desenhos sem conferir se cabem.
  Seis vistas numa A1 transbordam; o script separa em três folhas. O título da
  segunda vista de cada folha ainda cai sobre a tabela de revisões.
- **Cotas:** só eixos, vão, comprimento e alturas. Faltam cotas de detalhe,
  eixos nomeados (A, B, 1, 2…), níveis e textos.
- **Altura do corte:** a cota 7215 é o topo do envelope (terça), não a cumeeira
  do pórtico. Cota de engenharia tem de vir de um ponto nomeado do modelo.
- **Espessuras de linha:** vêm de uma folha de estilo por classe e por material
  (os materiais gravados na Fase 2 aparecem como `material-AcoMR250`). O padrão
  serve; não foi ajustado à norma de desenho.
- **Marcas de corte:** o Bonsai desenha sozinho as marcas dos cortes e
  elevações nas plantas, mas elas caem sobre as cotas.
- **Detalhes de ligação, lista de material e símbolos de solda** que o
  executivo atual do FreeCAD entrega não foram tentados.

### Ressalva do critério 4

O render sai, mas claro demais e sem sombra marcada. Falta ajustar sol,
exposição e câmera; é trabalho de cena, não de modelagem.

## O que o Bonsai não faz sozinho (resolvido no script)

1. A câmera de todo desenho nasce na origem com quadro de 50 × 50 m: o modelo
   sai cortado. Posição, largura, altura e profundidade passam a vir do envelope.
2. Depois de mudar largura e altura, as cotas saem deslocadas de
   (largura − altura) / 2, porque a resolução da cena só é atualizada ao ativar
   o desenho. O script reatribui a resolução.
3. O arquivo SVG herda o nome dado na criação; renomear depois não renomeia o
   arquivo, e dois desenhos com o mesmo nome se sobrescrevem. O script renomeia
   pelo núcleo do Bonsai antes de gerar.
4. A profundidade da elevação precisa passar da linha dos pilares, senão a
   fachada sai só com os condutores e os blocos.

## Riscos

- O script usa funções internas do Bonsai (`bonsai.tool`, `bonsai.core`), sem
  garantia de estabilidade entre versões. Convém fixar a versão da extensão.
- Só PDF e SVG. O entregável em DWG para quem usa AutoCAD continua sendo a
  Fase 4.
- O rasterizador do PyMuPDF não respeita a folha de estilo destes SVG (saiu em
  branco); conferência visual só com Inkscape ou navegador.

## Evidências (`evidencias/`)

- `folha-A01.pdf` / `.png` — planta baixa cotada, corte transversal, elevação frontal.
- `folha-A02.pdf` / `.png` — planta de fundação (filtro) e elevação lateral.
- `folha-A03.pdf` / `.png` — planta de cobertura (filtro).
- `render-apresentacao.jpg` — render EEVEE do mesmo IFC.

## Como reproduzir

```
# 1. IFC pelo motor (sem FreeCAD): rodar_projeto.rodar_tudo(spec_aco, com_3d=False, ...)
# 2. copiar o .ifc para uma pasta de trabalho (o Bonsai grava nele)
blender -b --python docs/fase3-bonsai/scripts/pranchas_bonsai.py -- <pasta>/galpao.ifc
blender -b --python docs/fase3-bonsai/scripts/render_apresentacao.py -- <pasta>/galpao.ifc saida.png BLENDER_EEVEE
inkscape "<pasta>/sheets/A01 - UNTITLED.svg" --export-type=pdf --export-filename=folha-A01.pdf
```
