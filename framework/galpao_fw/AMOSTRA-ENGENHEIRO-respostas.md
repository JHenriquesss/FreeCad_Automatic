# Amostra para o engenheiro responsável — respostas do wizard

**Data:** 2026-07-16
**Slug:** `amostra_engenheiro` · spec salvo em `spec_amostra_engenheiro.json`
**Objetivo da amostra:** rodar o framework guiado por perguntas (aqui no chat) e gerar
**apenas a imagem 3D** (pranchas 2D puladas — passo lento).

## Respostas coletadas (gate a gate)

### Módulo 1 — Geometria
| Campo | Resposta |
|---|---|
| Vão transversal (largura de cada vão) | **20 m** |
| Comprimento total | **28,5 m** |
| Pé-direito / beiral | **8 m** |
| Vinculação da base | **Engastada** |
| Nº de vãos transversais | 1 (default) |
| Espaçamento entre pórticos (bay) | *(pendente — ver Módulo 6)* |

### Módulo 2 — Cobertura
| Campo | Resposta |
|---|---|
| Nº de águas | **2 águas** |
| Inclinação | **15%** |
| Tipo de telha | **Trapezoidal** |
| Calha de água pluvial | **Sim** |

### Módulo 3 — Vento (NBR 6123)
| Campo | Resposta |
|---|---|
| V0 (velocidade básica) | **45 m/s** |
| Categoria de rugosidade | **II** |
| Abertura dominante (Cpi) | **Vedada** |

### Módulo 4 — Cargas (NBR 8800)
| Campo | Resposta |
|---|---|
| Permanente G | **0,27 kN/m²** |
| Sobrecarga Q | **0,50 kN/m²** |
| Neve sk | **0 (sem neve)** |

### Módulo 5 — Terreno & Fundação
| Campo | Resposta |
|---|---|
| Área do lote | **957 m²** |
| Tensão admissível do solo σ | **150 kN/m²** |
| Tipo de fundação | **"Bloco de fundação (médio)"** → ver GAP abaixo; amostra usa **sapata** |

### Módulo 6 — Geometria complementar & Fechamento
| Campo | Resposta |
|---|---|
| Espaçamento entre pórticos (bay) | **5,7 m** (5 vãos iguais → 6 pórticos; divisão exata de 28,5 m) |
| Tipo de fechamento | **Alvenaria** |
| Mão-francesa travando mesa interna | **Sim** (mesa_interna_travada = True) |

### Módulo 7 — Mão-francesa, peso do fechamento & Aberturas
| Campo | Resposta |
|---|---|
| Nº de mãos-francesas por água | **9** (incomum > típico 6 — aceito com aviso) |
| Peso do fechamento (alvenaria) | **1,5 kN/m²** |
| Portão frontal (L×H) | **4500 × 2500 mm** |
| Janelas laterais (L×H) | **3000 × 1000 mm** (5 por vão em cada lateral — quantidade não modelada no schema simplificado de aberturas) |

### Módulo 8 — Terreno & Legislação urbana
| Campo | Resposta |
|---|---|
| Taxa de ocupação máxima | **0,60** (galpão ocupa ~570/957 ≈ 0,60 — no limite) |
| Recuo frontal | **8 m** |
| Recuos laterais | **1,5 m** |
| Recuo de fundos | **0 (na divisa)** |

### Defaults aceitos (não perguntados nesta amostra)
C.A. máx 1,0 · taxa permeabilidade 0,2 · peso telha 0,10 kN/m² · chuva 150 mm/h ·
classe B · S3 0,95 · peso próprio estrutural 0,35 kN/m² · tapamento 0,10 kN/m² · 1 vão transversal.

## GAPs registrados

### GAP 1 — Tipo de fundação "bloco de fundação" não previsto
O framework aceita hoje só `sapata` (rasa) e `estaca` (profunda) — `projeto_spec.TIPOS_FUNDACAO`.
O "bloco de fundação" raso isolado **não é um tipo próprio**. Para a amostra usou-se `sapata`
(fundação direta, coerente com σ=150). Salvo para implementação futura na memória
`bloco-fundacao-tipo-futuro`.

### GAP 4 — Peso do fechamento/revestimento das paredes NÃO entra na carga — CONTRA-SEGURANÇA
Levantado pelo engenheiro ao encerrar a amostra. (a) O wizard não pergunta o **revestimento**
das paredes como carga; (b) mesmo o `fech_peso` que é perguntado **nunca é aplicado**:
`to_rodar_params` (linha ~308) só passa `{G, self, Q}`; `fechamento` só entrega travamento
(`mesa_interna_travada`, `n_maos_francesas`). O peso da parede (alvenaria 1,5 kN/m² × ~8 m) fica
**ignorado** no pilar e na fundação → subdimensionamento. A corrigir: aplicar o peso da parede
como ação vertical (pendurada nas longarinas → pilar) e/ou no baldrame (`q_parede`) conforme o
tipo de fechamento. Memória: `carga-fechamento-parede-nao-aplicada`.

### ERRO DE ENUNCIADO (não pode repetir)
Na opção de bay 5,7 m escrevi "6 vãos → 7 pórticos"; o correto é **5 vãos → 6 pórticos**
(28,5 ÷ 5,7 = 5). Número derivado errado num enunciado de pergunta. Regra registrada em
`perguntas-numeros-derivados-corretos`: conferir toda aritmética antes de mostrar a pergunta.

### GAP 3 — Convenção de `janelas_laterais` incompatível (wizard × build) — BUG REAL
`build_galpao._parede_lateral` (linha ~1078) usa `janelas_laterais` como **faixa de elevação
`(z_base, z_topo)`** (default do módulo: `(4300, 5300)`). Já o wizard/`construir_spec` entrega
`(largura, altura)` — ex. `(3000, 1000)`. Resultado: o box de recorte fica com altura
`1000 − 3000 = −2000` → `ValueError: height of box too small`, **quebrando o build inteiro**.
O portão (`portao_frente`) usa `(L, H)` corretamente (linha 1111), então a inconsistência é só
das janelas. **A corrigir:** reconciliar a convenção — o mapper deveria converter as janelas do
usuário (L×H + peitoril) numa faixa `(z_base, z_topo)`, ou o build aceitar `(L,H)` e posicionar.
Além disso o schema de aberturas do wizard **não modela quantidade** (ex. "5 janelas por vão"):
desenha uma faixa contínua. **Contorno na amostra:** janela enviada como faixa `(2000, 3000)`
(tira de 1 m a 2 m de altura) — proxy visual; e `porta_lateral` forçada a `None` (o default do
build desenharia uma porta não pedida).

### GAP 2 — Bridge do FreeCAD (porta 9875) não sobe sozinho → 3D bloqueado nesta sessão
Ao lançar o `freecad.exe`, o addon RobustMCPBridge (AutoStart=True por padrão) **não respondeu
na porta 9875** dentro de vários minutos de polling. Processos `freecad.exe` estavam vivos, mas
o XML-RPC recusava conexão. Sem o bridge, `rodar_projeto.montar_modelo` não monta o 3D.
**A resolver depois** (fora do escopo desta amostra, por decisão do usuário): investigar por que
o auto-start do bridge não firma o socket (possível diálogo de startup bloqueando a GUI, falha
silenciosa no QTimer de auto-start, ou porta ocupada). Alternativa robusta a avaliar: render 3D
por `freecad.exe` **destacado** com bootstrap próprio (como o `rodar_executivo` faz p/ pranchas),
sem depender do bridge.

### Coerência a revisar (não bloqueante)
- **Cpi × portão frontal:** o Módulo 3 marcou abertura dominante **"vedada"**, mas o Módulo 7
  informou **portão frontal 4,5×2,5 m** (11,25 m²). Com abertura grande na fachada, o Cpi
  deveria provavelmente ser tratado como **portão no oitão** (não vedada). Registrar para o
  engenheiro decidir — impacta a pressão interna de vento.

## Modelo 3D gerado (sem fundação) — OK
Contornado o bridge (GAP 2) via **freecad.exe destacado + bootstrap** (`tmp/boot_build3d.py`),
sem usar a porta 9875. Fundação suprimida (sapata/estaca/bloco/baldrame = None) a pedido.

| Métrica | Valor |
|---|---|
| Elementos | 645 |
| Pórticos | 6 (bay 5,7 m em 28,5 m) |
| Interferências | 0 |
| Massa de aço | 28.192 kg (~28,2 t) |
| Altura da cumeeira | 9.500 mm (beiral 8.000 + 15%·10.000/... = +1.500) |
| Arquivos | `saida_amostra/freecad/amostra_engenheiro.FCStd` · `.../step/*.step` · `vistas/*.png` (4) |

Vistas capturadas não-brancas (recipe showNormal+Visibility+ViewFit): isométrica, frontal,
lateral direita, superior. **Modelo deixado ABERTO no FreeCAD** para o engenheiro inspecionar
(pode ligar/desligar visibilidade do fechamento p/ ver o esqueleto estrutural).

## Correções aplicadas (2026-07-16)
Depois da amostra, corrigidos com teste de regressão cada um:

1. **Peso da parede/revestimento na carga** (era ignorado — contra-segurança). Agora
   `projeto_spec.cargas_parede` distribui o peso; entra como **UDL vertical nas colunas
   externas** (`galpao_portico.case_G`, via `W_WALL_COL`) → chega à coluna e à fundação;
   a parcela de alvenaria alimenta a **viga de baldrame** (`q_parede`). Wizard passou a
   perguntar "peso do fechamento + revestimento" e a altura da alvenaria.
   Testes: `tests/test_carga_parede.py`.
2. **Convenção das janelas** (quebrava o 3D). `to_build_kwargs` converte a janela do
   wizard `(L,H)` na faixa `(z_base, z_topo)` do build (`_janela_band`, peitoril default
   1,10 m). Build 3D da amostra passou a rodar direto (645 elementos, 0 interferências).
   Testes: `tests/test_aberturas_janela.py`.
3. **Viabilidade urbanística (TO/CA/TP + recuos)** (gate sempre pulado — o mapper não
   passava `params[terreno]`). Agora mapeado; `terreno.analisa_terreno` ganhou modo
   **área-only** (TO/CA/TP pela área; recuos ficam PENDENTES sem o polígono do lote).
   Na amostra: footprint 570 ≤ TO_max 574 m² → OK (no limite, como sinalizado).
   Testes: `tests/test_terreno_mapper.py`.

### Achados da varredura NÃO corrigidos (aguardam decisão)
- **cargas.tapamento**: campo morto e redundante com `fechamento.peso` — corrigir arrisca
  dupla contagem. Recomendo consolidar os dois campos num só.
- **vento.abertura_dominante**: `vento` usa envelope fixo de Cpi (barlavento+sotavento),
  ignora a escolha do usuário. Conservador/seguro, mas "vedada" não reduz a carga interna.
- **cobertura.aguas**: geometria é sempre 2 águas; **1 água (shed) não é suportado** —
  limitação, não só campo morto.
- **cobertura.telha_tipo**: só rótulo/take-off (não dimensiona o perfil da telha).

### BUG pré-existente descoberto (alta prioridade, fora do escopo desta rodada)
**Sinal da reação na fundação.** `frame2d.reactions()` dá sinais opostos para carga UDL
vs nodal; e `casos_base` entrega a compressão de gravidade como **N negativo**, enquanto a
sapata espera N>0 para compressão. Efeito: a sapata trata a gravidade como uplift e só
"passa" quando o peso próprio da sapata supera — **footings sistematicamente
superdimensionadas** (a ref adota 2,5×3,0×0,90 m para um pilar de ~66 kN). Afeta também a
carga de cobertura. Precisa de tarefa própria + revalidação contra sapata calculada à mão.
Memória: `bug-sinal-reacao-fundacao`.

## Status
- [x] Perguntas Módulos 1–8 coletadas (wizard completo)
- [x] Spec montado e **VÁLIDO** → `spec_amostra_engenheiro.json`
- [x] **Modelo 3D gerado sem fundação** (645 elementos, 0 interferências) + 4 vistas PNG
- [ ] Cálculo/veredito NBR (`rodar_tudo` com `com_3d=False`) — disponível a qualquer momento
- [ ] Corrigir GAP 3 (convenção janelas) e GAP 2 (bridge) e GAP 1 (tipo bloco) — pós-amostra
