# Design — primeira vertical real: elétrica residencial BT/Enel

**Status:** proposta de execução baseada na autorização anterior para continuar
o framework; esta fase não substitui a revisão técnica do responsável pelo
projeto.

## Objetivo

Transformar a casa residencial de uma fixture puramente sintética em uma
segunda prova do framework com uma disciplina elétrica real, porém limitada e
honestamente auditável: previsão de demanda residencial da Enel Rio, seleção
do padrão de entrada individual e contrato mínimo para circuitos internos.

O galpão continua sendo apenas o adaptador de integração. Nenhum módulo
residencial deverá importar `galpao_eletrico`, `galpao_hidraulica`,
`galpao_turnkey` ou depender de geometria industrial.

## Evidência normativa disponível

A reautenticação do NotebookLM foi executada antes desta proposta. O notebook
elétrico é `78cd2efd-0652-484e-b312-c5c5a7648962`; a listagem remota confirmou
39 fontes, todas com `status=2` e `is_stale=false`. A consulta auditável de
escopo residencial retornou citações estruturadas para:

| Fonte | Source ID | Uso nesta fase |
| --- | --- | --- |
| ABNT NBR 5410:2004 | `d213019d-6e5c-4f18-8151-bf5a74c11b5d` | documentação mínima, circuitos, proteção e parâmetros do projeto |
| Enel BT individual R02/2025 | `5129118d-2ff6-4187-a9d2-d1828d61afdf` | tensão, entrada individual, tabelas A/C, medição e requisitos Enel |
| Enel Rio WKI demanda BT R01/2018 | `5bc6c2f1-c8b8-4a04-8b82-be0e937b4749` | módulos de demanda residencial e potências especiais |
| ANEEL PRODIST Módulo 3 | `4c71daf6-ff91-44d1-a5e7-d7f881ab66f8` | contexto de conexão e dados de crescimento/atendimento |

O WKI local confirma: módulos de cômodos, divisor `1,4` para um quarto e
`1,2` para dois ou mais, fator de localização entre `1,00`, `0,88`, `0,75` e
`0,55`, e fórmula de demanda final `a + maior(b,c,d) + 0,70 * restantes`
(PDF local, páginas 6–9). A tabela Enel BT local confirma as linhas do Anexo
A para 127/220 V (página 72) e do Anexo C para 120/240 V (página 77).

O fator de localização específico de São João da Barra não foi encontrado nas
fontes consultadas. Portanto ele será entrada obrigatória, nunca default
regional inventado. Tensão da rede, tipo de fornecimento, rede aérea ou
subterrânea e viabilidade local também permanecem dados do imóvel/consulta à
concessionária.

## Decisão de arquitetura

Criar um adaptador explícito `casa-residencial-eletrica`, separado do
`casa-residencial-sintetica`, e dois módulos puros específicos da vertical:

- `framework/galpao_fw/demanda_residencial_enel.py`: cálculo determinístico
  dos módulos de cômodos, potências de aquecimento, iluminação especial e
  demanda final, com tabelas e referências de edição declaradas;
- `framework/galpao_fw/entrada_enel_bt.py`: seleção dos dados mínimos das
  tabelas Enel Rio 127/220 V e 120/240 V, sem inferir tipo de ligação quando
  as faixas permitirem mais de uma escolha;
- `framework/galpao_fw/residencial_eletrica.py`: runner registrado no loader,
  validação do payload, composição dos módulos e produção do relatório JSON.

Os calculadores não importarão FreeCAD. O runner não fornecerá hooks IFC, 3D,
desenho ou caderno nesta fase; o núcleo universal registrará esses estados
como `not_available` ou `not_requested`. A fase seguinte poderá consumir o
resultado neutro para 2D/BIM.

## Contrato de entrada

O adaptador aceitará um envelope `freecad-automatic/project-spec` com este
recorte mínimo em `turnkey.eletrico`:

```json
{
  "network": {
    "voltage_system": "127/220",
    "supply_type": "B",
    "network_kind": "aerea",
    "location_factor": 1.0
  },
  "rooms": {
    "quarto": 2,
    "sala": 1,
    "banheiro": 1,
    "cozinha": 1,
    "area_servico": 1,
    "outros": 0
  },
  "loads": {
    "installed_load_kw": 7.5,
    "heating": [],
    "motors": [],
    "special_lighting": []
  },
  "circuits": {
    "points": [
      {"id": "L-01", "room": "sala", "kind": "lighting", "power_va": 100,
       "voltage_v": 127},
      {"id": "T-01", "room": "cozinha", "kind": "tug", "power_va": 600,
       "voltage_v": 127},
      {"id": "TUE-01", "room": "banheiro", "kind": "tue", "power_va": 4400,
       "voltage_v": 220}
    ],
    "routes": []
  }
}
```

`location_factor`, `voltage_system`, `supply_type` e `network_kind` podem ser
omitidos somente para produzir um estado bloqueado/`needs_review`; o cálculo
não preencherá esses dados. A lista de pontos é explícita: a fase não cria
pontos arquitetônicos por heurística.

`loads.installed_load_kw` é obrigatório para selecionar uma linha dos Anexos A
ou C. Ele representa a carga instalada informada para o imóvel e não será
substituído silenciosamente pela demanda calculada, pois as tabelas e as
premissas têm naturezas diferentes. Sem esse valor, a demanda residencial
pode ser calculada, mas o resultado do padrão de entrada fica bloqueado.

Cada ponto deve declarar `voltage_v`; a fase não inventará tensão para
iluminação ou tomadas. As referências no spec devem conter `notebook_id`, `source_id`, título, edição
e `status` observado. A validação ao vivo continuará externa ao cálculo,
através de `project_source_gate.py` e do readiness aprovado. Um `status=2`
gravado no spec não será tratado como prova viva sem o relatório de readiness.

## Estados e entregáveis

- `blocked`: payload ausente, tipo de tensão não suportado, quantidade inválida,
  ponto sem potência/tensão, fator de localização ausente quando a demanda é
  solicitada ou fonte obrigatória não declarada sob `require_source_refs`;
- `needs_review`: cálculo determinístico produzido, mas há premissa explícita,
  fonte não revalidada no readiness, padrão que depende da concessionária ou
  ausência de hooks executivos;
- `passed` não será emitido nesta fase para uma instalação residencial. O
  resultado deve preservar `native_atende`, `gates`, `warnings`, `errors`,
  `source_refs`, `calculation` e `service_entry`.

O relatório do adaptador será `reports/adapter-result.json`, acompanhado de
`reports/disciplinas.json` e do manifesto universal. Não serão criados IFC,
FCStd, PDF, SVG ou DXF.

## Regras de cálculo

1. A demanda dos cômodos usa a tabela do WKI: quarto 1,50 kVA, sala 1,60,
   banheiro 2,30, cozinha 1 1,50, cozinha 2 2,10, área de serviço 1,90 e
   outros 0,35 por cômodo. Até dois quartos usa cozinha 1; três ou mais usa
   cozinha 2. O subtotal é dividido por 1,4 para um quarto ou 1,2 para dois ou
   mais e multiplicado pelo fator de localização informado.
2. Aquecimento usa a Tabela 1 do WKI por grupo de potência e quantidade;
   iluminação especial usa 100% e fator de potência explícito conforme a
   espécie. O cálculo da demanda final aplica a combinação `a,b,c,d` do item
   6.2.4.
3. Motores só serão calculados para a combinação atualmente liberada na tabela
   do WKI: `1 CV trifásico, quantidade 1`. Motor fora dessa linha produz erro
   auditável, não interpolação silenciosa. Os resultados de demanda usam o
   campo unitário `demand_kva`.
4. A seleção de entrada usa somente as linhas reproduzidas da edição Enel BT
   declarada. Para 127/220 V usa Anexo A; para 120/240 V usa Anexo C. Tipo de
   fornecimento ausente ou incompatível gera gate explícito. As linhas e notas
   preservam referência à página/tabela, não apenas um número solto.
5. O cálculo de circuitos internos nesta fase valida pontos e separação de
   funções e delega condutor/proteção aos módulos NBR 5410 já existentes apenas
   com parâmetros explícitos. Não reutilizará o layout automático de perímetro
   do galpão.

## Fora de escopo desta fase

- plantas, unifilares renderizados, IFC, 3D, DXF, PDF ou caderno;
- SPDA, fotovoltaica, recarga de veículos, média tensão e geração distribuída;
- aprovação da Enel, ART/RT, vistoria ou declaração de atendimento para obra;
- alteração dos defaults ou do runner industrial do galpão;
- implementação hidráulica ou arquitetônica real.

## Critério de aceitação

Uma fixture residencial elétrica com fontes declaradas e dados explícitos deve
percorrer o mesmo `run_project_file()` universal, produzir cálculo e padrão
Enel rastreáveis, permanecer `needs_review`, verificar hashes e não importar
qualquer módulo do galpão. Fixtures negativas devem bloquear falta de fator de
localização, tensão/tipo incompatível, ponto inválido, fonte ausente e tabela
sem correspondência. A suíte existente do galpão deve continuar verde.
