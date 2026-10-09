# Decisões de arquitetura — sistema de produção de projetos de engenharia

**Data da decisão:** 08/10/2026
**Para:** orquestrador do projeto (contexto: FreeCad_Automatic, Projetor-eletrico, motores NBR em Python)
**Autor das decisões:** Henriques, após revisão de arquitetura

---

## 1. Objetivo de negócio (ler antes de tudo)

O objetivo **não é vender software**. É **vender o projeto final como serviço**.

- O mercado de software de projeto já tem concorrentes fortes e bem financiados (AltoQi Builder, Endra etc.). Não vamos competir com eles.
- O sistema é uma **ferramenta interna de produção**: serve para entregar projetos mais rápido, mais barato e com mais consistência do que o método manual.
- Fluxo comercial: o sistema produz o projeto calculado e desenhado (pranchas, memoriais, planilhas) → um engenheiro civil experiente revisa e assina a parte estrutural → Henriques assina a parte elétrica. A revisão deve ser **leitura e correções mínimas**, não um retrabalho.
- Consequência para o desenvolvimento: toda decisão técnica deve ser julgada por **"isso melhora a qualidade, a velocidade ou a confiabilidade do projeto entregue?"**, não por "isso deixa o software mais completo".

---

## 2. Decisões tomadas

1. **O ativo de valor é o motor determinístico em Python** (cálculos e verificações normativas). Ele será preservado, revisado e melhorado.
2. **O motor será desacoplado do FreeCAD.** Nenhum módulo de cálculo pode importar FreeCAD. O motor recebe dados e devolve dados.
3. **O modelo de projeto passa a ser a única fonte de verdade.** Desenhos, pranchas, DXF e renders são sempre **derivados** do modelo, nunca editados diretamente.
4. **Formato-alvo do modelo: IFC**, gerado e editado com **IfcOpenShell** (Python).
5. **Será testado o Blender + Bonsai** (antigo BlenderBIM) como saída para BIM, pranchas e render de apresentação. Se o teste passar, o Bonsai substitui o FreeCAD como saída.
6. **O FreeCAD sai gradualmente**, só quando nada mais depender dele. Até lá, continua como saída provisória.
7. **Entregável editável para engenheiros que usam AutoCAD:** exportador próprio modelo/IFC → DXF com **ezdxf** (DWG via ODA File Converter).
8. **O Projetor-eletrico é descartado como produto** (a interface tipo Miro). Ficam apenas os motores. Ver regra de preservação na Fase 0.
9. **AltoQi Builder e Revit foram avaliados e descartados como núcleo:** AltoQi não tem API pública para a IA operar; Revit é pesado, fechado e caro. Nenhum dos dois conhece a NBR por conta própria — o cálculo continuaria sendo nosso.
10. **Escopo congelado:** prioridade é entregar o galpão do cliente atual. Nenhuma tipologia ou disciplina nova entra antes disso.

---

## 3. Arquitetura-alvo

```
Dados de entrada (especificação, terreno, planta do cliente)
            │
            ▼
   ┌───────────────────────┐
   │  MOTORES (Python puro) │  NBR 5410, NBR 8800, cargas, ligações, fundações...
   │  sem FreeCAD, sem CAD  │  entrada: dados → saída: dados
   └──────────┬────────────┘
              ▼
   ┌───────────────────────┐
   │  MODELO DE PROJETO     │  IFC (IfcOpenShell) = fonte única de verdade
   └──────────┬────────────┘
     ┌────────┼─────────────────┬──────────────────┐
     ▼        ▼                 ▼                  ▼
  Bonsai   Bonsai/Blender    Exportador DXF     Memoriais /
  pranchas render 3D         (ezdxf) p/ AutoCAD  planilhas
  (SVG/PDF) apresentação
```

**Estrutura de produto:** núcleo comum + verticais finas.
- **Núcleo:** motores, modelo de dados, geradores de prancha/DXF/memorial.
- **Verticais:** "galpão" agora; "residência" e outras depois. Cada vertical só decide quais motores usar, em que ordem e com quais regras da tipologia.
- **Não generalizar antes da hora:** o núcleo genérico só é extraído quando houver uma segunda tipologia real. O motor NBR 5410 já é candidato, pois é compartilhado hoje.

---

## 4. Princípios obrigatórios

1. **O modelo é a verdade; o desenho é derivado.** Nunca editar prancha/DXF à mão como forma de corrigir o projeto. Corrige-se o modelo e regenera-se.
2. **A IA lê o projeto consultando, não fotografando.** Expor o modelo por operações (ex.: `listar_circuitos`, `adicionar_circuito`, `mover_ponto`, `validar`). Captura de tela só para conferência visual final, nunca para descobrir o estado do projeto.
3. **Para criar, a IA escreve código contra bibliotecas bem documentadas** (IfcOpenShell, bpy/Bonsai, ezdxf). **Para editar, consulta e altera o modelo** por operações pequenas. Evitar longas cadeias de chamadas MCP para tarefas que um script resolve.
4. **Determinismo:** cálculo e verificação normativa são código testado, nunca texto gerado por LLM.
5. **Valores normativos vêm da biblioteca de normas (MCP_Fontes), nunca da memória do modelo.**
6. **Correção se mede por teste, não por inspeção visual:** cotas batem com a geometria; todo circuito do quadro aparece na planta; resultados comparados com projetos reais já entregues (gabaritos).
7. **Escopo congelado** até a entrega do galpão.

---

## 5. Plano de execução

### Fase 0 — Limpeza segura (antes de qualquer refatoração)

- Fazer commit de todo trabalho pendente em todos os repositórios envolvidos e enviar ao GitHub (o FreeCad_Automatic local está à frente do remoto; o Projetor-eletrico não tem remoto).
- **Não apagar nada. Arquivar** (tag ou branch de arquivo) o que for descartado.
- **Preservar obrigatoriamente** a subpasta `Projetor-eletrico/asdasd`: contém trabalho real de cliente (pacote de pedido de ligação Enel-Rio). Mover para local próprio de projetos de clientes, fora do código.
- Identificar e listar quais partes do Projetor-eletrico são motor (manter) e quais são interface (arquivar).
- Corrigir o teste que falha hoje (`test_dossie_unico`, dependência `fitz` ausente).
- **Pronto quando:** tudo commitado e com backup remoto; lista de manter/arquivar aprovada por Henriques; nenhum arquivo apagado.

### Fase 1 — Desacoplar o motor do FreeCAD

- Extrair os motores para pacote(s) Python independentes (ex.: `motor_nbr5410`, `motor_estrutural`), sem nenhum `import FreeCAD`.
- Entradas e saídas como estruturas de dados tipadas (dataclasses ou pydantic).
- O Projetor-eletrico deixa de depender da pasta irmã do FreeCad_Automatic.
- **Separar os testes em duas camadas:**
  - **Rápida:** motores e modelo, sem FreeCAD; deve rodar em poucos minutos e ser executada a cada alteração.
  - **Lenta:** integração, geração de pranchas e comparação de arquivos de saída; roda só antes de entregas.
  - Usar marcadores do pytest (ex.: `@pytest.mark.slow`).
- Aproveitar a refatoração para revisar os motores: erros, cobertura de casos, rastreabilidade de cada valor normativo até a fonte.
- **Pronto quando:** motores importáveis sem FreeCAD instalado; suíte rápida passando em poucos minutos na máquina de 8 GB; pipeline atual do galpão ainda gera o mesmo resultado (teste de regressão).

### Fase 2 — Galpão em IFC

Duas rotas, nesta ordem:

1. **Teste rápido (opcional, só para destravar o Bonsai):** exportar o modelo atual do FreeCAD para IFC. Atenção: sólidos genéricos tendem a sair como `IfcBuildingElementProxy`, sem semântica. Serve só para abrir no Bonsai e conhecer a ferramenta.
2. **Rota correta:** gerar o IFC **direto dos dados do motor** com `ifcopenshell.api`:
   - Hierarquia `IfcProject` → `IfcSite` → `IfcBuilding` → `IfcBuildingStorey`.
   - Pilares e vigas como `IfcColumn` / `IfcBeam` com perfis reais (`IfcIShapeProfileDef` etc.) e materiais.
   - Resultados de cálculo gravados em property sets dos elementos (esforços, verificações, perfil adotado).
- **Pronto quando:** o IFC do galpão do cliente atual é gerado a partir do motor, abre sem erros em visualizador IFC e contém elementos com classes e perfis corretos.

### Fase 3 — Teste do Blender + Bonsai

Testar com o galpão real. **Critérios de aprovação (todos obrigatórios):**

- [ ] O IFC da Fase 2 abre corretamente no Bonsai.
- [ ] Gera planta, corte e elevação com qualidade de prancha executiva: escala correta, carimbo, espessuras de linha, cotas, enquadramento limpo.
- [ ] Pranchas por disciplina como **filtros de visualização do mesmo modelo** (ex.: só estrutura; arquitetura limpa; completa).
- [ ] Render de apresentação a partir do mesmo modelo, sem remodelar.
- [ ] A IA consegue alterar o modelo (ex.: mudar um perfil ou um vão) e regenerar as pranchas sem refazer o projeto do zero.
- [ ] Tempo de geração aceitável na máquina disponível.

**Observações conhecidas:** Bonsai é código aberto mantido pela comunidade, ainda com arestas; exige Inkscape para composição de folhas e exportação PDF; pranchas saem em SVG/PDF (não DWG). Existem pacotes de skills prontos para Bonsai/IfcOpenShell que podem ajudar os agentes.

- **Resultado esperado:** relatório curto com cada critério marcado como aprovado/reprovado, evidências (arquivos gerados) e recomendação. **A decisão final de migrar é de Henriques.** Se reprovar, o FreeCAD continua como saída e nada se perde, pois o motor já estará livre.

### Fase 4 — Exportador DXF editável

- Gerar DXF a partir do modelo/IFC com `ezdxf`, montado em **espaço de papel**:
  - escolha automática de escala padrão (1:50, 1:75, 1:100) e formato de folha (A3, A2, A1) conforme o tamanho da vista;
  - viewport na escala correta, carimbo como bloco, margens e legenda;
  - camadas por disciplina com pesos de linha definidos;
  - estilos fixos de cota e texto.
- Regras de formato, margem, carimbo e tipos de linha: conferir as normas ABNT de desenho técnico na biblioteca de normas (verificar qual norma vigente consolida esses requisitos).
- DWG via ODA File Converter.
- **Pronto quando:** o engenheiro abre o arquivo no AutoCAD e as pranchas estão enquadradas, em escala e editáveis.

### Fase 5 (depois do galpão) — Caminho do projeto elétrico sobre planta de terceiros

Serviço frequente: o cliente envia a planta e quer só o elétrico.

- O motor elétrico trabalha com o conceito abstrato de **ambiente** (tipo, área, perímetro), independente da origem:
  - **Entrada DWG 2D (maioria dos casos):** DWG → DXF; ambientes marcados como polilinhas fechadas numa camada (ex.: `AMBIENTES`) com texto do tipo; `ezdxf` lê área e perímetro.
  - **Entrada IFC:** ambientes lidos de `IfcSpace`.
- Motor aplica a NBR 5410: previsão de tomadas e iluminação, divisão de circuitos, posição do quadro, quadro de cargas, unifilar, memorial.
- Saída: DXF com o elétrico em camadas próprias sobre a planta original (e/ou elementos no IFC).
- Roteamento automático de cabos fica para versão posterior; no início, traçado simplificado e ajuste manual.
- **Gabaritos:** projetos elétricos já entregues por Henriques. Mesma planta de entrada → resultado do sistema comparado com o projeto real.
- Primeiro passo pequeno: ler polilinhas de ambientes num DXF e gerar a previsão de cargas.

---

## 6. Fora de escopo agora (registrado para o futuro)

- Novas tipologias além do galpão.
- Disciplina hidráulica (NBR 5626, NBR 8160) e outras.
- Interface gráfica própria (tipo Miro / Lumine).
- Venda do software.
- Revit e AltoQi como núcleo.

### Visão de longo prazo (não implementar agora)

- Entrada: DXF do levantamento topográfico → terreno no modelo.
- A IA pergunta as regras municipais (taxa de ocupação, recuos, gabarito, área aproveitável — ex.: limite de 60% comum na região) e o motor verifica tudo de forma determinística.
- Projeto multidisciplinar (arquitetura, estrutura, elétrico, hidráulico) no mesmo modelo IFC, com pranchas por disciplina e de compatibilização como vistas filtradas.

---

## 7. Riscos e restrições

- **Máquina com 8 GB de RAM** até o upgrade previsto (~20 GB). A Fase 1 deve reduzir esse gargalo, pois tira o FreeCAD da maior parte dos testes.
- **Maturidade do Bonsai:** pode exigir contornos; por isso a migração depende do teste da Fase 3.
- **Responsabilidade técnica:** estrutural assinado pelo engenheiro civil parceiro; elétrico por Henriques. O sistema deve produzir rastreabilidade suficiente para a revisão ser rápida.
- **Custo de IA:** evitar sessões longas de desenvolvimento sem objetivo de entrega. Cada fase tem critério de pronto; não avançar para a seguinte sem cumpri-lo.

---

## 8. Regras de trabalho para o orquestrador

1. Seguir as fases em ordem; não iniciar a seguinte sem cumprir o critério de pronto da atual.
2. Commit pequeno e descritivo a cada passo concluído; push frequente.
3. **Nunca apagar arquivos** sem aprovação explícita de Henriques; arquivar em vez de apagar.
4. Não adicionar funcionalidades fora do escopo desta fase, mesmo que pareçam úteis. Registrar a ideia num backlog e seguir.
5. Ao fim de cada fase, entregar um resumo curto: o que foi feito, critérios atendidos, problemas encontrados e próxima ação proposta.
6. Em dúvida entre "mais completo" e "entrega o galpão mais cedo", escolher o segundo.
