# Validador de compatibilidade elétrica de strings FV

**Status:** aprovado para especificação da fase 19

## Objetivo

Criar uma validação pura e determinística para a compatibilidade elétrica básica
de um arranjo fotovoltaico em corrente contínua. A função bloqueia entradas
incompletas ou incompatíveis e devolve valores calculados e referências
normativas para cada decisão.

O módulo atual fotovoltaico.py calcula potência e geração com valores de
catálogo marcados como “A CONFIRMAR”, mas não verifica tensão, corrente,
proteção ou conectores. O novo validador será uma camada independente: não
altera dimensiona_fv nesta fase e não inventa dados de fabricante, temperatura
ou distribuidora.

## Evidência normativa autorizada

| Fonte | Trechos usados | Aplicação |
| --- | --- | --- |
| ABNT NBR 16690:2019, source ID 1d06923f-04d7-4b39-afbd-da6ab91567a9 | 3.1.42; 5.3.9; 5.3.11.1; 6.1.1; 6.1.3; 6.2.5; 6.2.8.1; 6.2.8.2 | tensão máxima, corrente mínima, proteção CC, componentes e conectores |
| ABNT NBR 16149:2013, source ID 7f85f8f0-9ff2-492a-9188-bf345529f2b6 | 5.5–5.7 | delimitação da interface com a rede; não será usada para inventar regras internas do lado CC |

Trechos auditados no NotebookLM:

- 3.1.42: VOC_ARRANJO = VOC_MOD × M.
- 6.1.3: a tensão máxima é VOC_ARRANJO corrigida para a menor temperatura de
  operação; sem instrução do fabricante para silício mono/policristalino,
  aplica-se o fator da Tabela 4.
- 6.1.1: componentes devem ser apropriados para c.c., ter tensão nominal maior
  ou igual à tensão máxima e corrente nominal maior ou igual à Tabela 5.
- Tabela 5: para o arranjo sem proteção contra sobrecorrente, a corrente mínima
  é 1,25 × ISC_ARRANJO; com proteção, o valor de referência é o valor nominal
  do dispositivo de proteção do arranjo.
- 5.3.9: proteção de séries é requerida quando
  ((SA - 1) × ISC_MOD) > IMOD_MÁX_OCPR; são aceitos gPV, ABNT NBR IEC
  60947-2 ou IEC 60898-2, e não ABNT NBR NM 60898.
- 5.3.11.1: proteção individual exige 1,5 × ISC_MOD < In < 2,4 × ISC_MOD e
  In ≤ IMOD_MÁX_OCPR; proteção agrupada exige In > 1,5 × SG × ISC_MOD e
  In < IMOD_MÁX_OCPR - ((SG - 1) × ISC_MOD).
- 6.2.8.1 e 6.2.8.2: conectores da mesma conexão devem ser do mesmo tipo e
  fabricante e devem atender aos requisitos de c.c., tensão e corrente.

## Escopo da fase

Incluído:

1. cálculo de VOC_ARRANJO, V_MAX_ARRANJO, ISC_ARRANJO e corrente mínima;
2. verificação de componentes CC;
3. decisão e verificação de proteção de séries individual ou agrupada;
4. verificação de conectores quando o caso declarar que os utiliza;
5. retorno estruturado com falhas, avisos, valores e referências;
6. candidato atômico do scheduler com as duas fontes FV locais declaradas.

Fora desta fase:

- seccionamento e isolação da UCP;
- aterramento, equipotencialização e SPDA;
- anti-ilhamento, tensão/frequência CA e reconexão;
- dimensionamento térmico completo de cabos segundo NBR 16612/NBR 5410;
- regras da distribuidora, PRODIST, ANEEL e aprovação de acesso;
- escolha automática de módulo, inversor, HSP, fator de correção ou catálogo.

Esses itens permanecem lacunas explícitas para candidatos posteriores.

## Contrato da função

Adicionar a função pura:

    validar_compatibilidade_arranjo_fv(caso: dict) -> dict

O retorno sempre terá:

    {
        "ok": bool,
        "falhas": [
            {
                "codigo": str,
                "mensagem": str,
                "referencia": {
                    "norma": "ABNT NBR 16690:2019",
                    "secao": str,
                    "source_id": "1d06923f-04d7-4b39-afbd-da6ab91567a9",
                },
            },
        ],
        "avisos": [],
        "valores_calculados": {
            "voc_arranjo_v": float,
            "v_max_arranjo_v": float,
            "isc_arranjo_a": float,
            "corrente_minima_arranjo_a": float,
            "corrente_referencia_componentes_a": float,
            "protecao_series_requerida": bool,
        },
        "referencias": [],
    }

Entradas obrigatórias:

    {
        "voc_modulo_v": float > 0,
        "modulos_serie": int >= 1,
        "isc_modulo_a": float > 0,
        "series_paralelo": int >= 1,
        "componentes_cc": [
            {
                "nome": str não vazia,
                "tensao_nominal_v": float > 0,
                "corrente_nominal_a": float > 0,
                "adequado_cc": bool,
            },
        ],
        "usa_conectores": bool,
    }

Para a tensão máxima, o caso deve fornecer exatamente uma destas entradas:

- fator_correcao_tensao: número finito maior que zero; calcula
  v_max = voc_modulo_v × modulos_serie × fator;
- v_max_arranjo_v: número finito maior que zero já calculado segundo as
  instruções do fabricante; o validador não recalcula nem valida a origem.

Quando series_paralelo > 1, imod_max_ocpr_a também é obrigatório, pois sem ele
não é possível decidir a necessidade de proteção da série conforme 5.3.9.

Quando a proteção do arranjo for declarada, seu formato será:

    {
        "corrente_nominal_a": float > 0,
        "tipo": "gPV" | "disjuntor_cc_60947-2" | "disjuntor_cc_60898-2",
    }

Sua corrente nominal será a referência da Tabela 5 para os componentes do
arranjo; sem essa proteção, a referência será 1,25 × ISC_ARRANJO. A proteção
do arranjo é distinta da proteção de séries: a primeira define a corrente de
referência dos componentes do arranjo; a segunda atende à decisão de 5.3.9 e
às desigualdades de 5.3.11.1.

Quando protecao_series existir:

    {
        "modo": "individual" | "grupo",
        "corrente_nominal_a": float > 0,
        "tipo": "gPV" | "disjuntor_cc_60947-2" | "disjuntor_cc_60898-2",
        "series_grupo": int >= 1,
    }

Quando usa_conectores for True, conectores será obrigatório:

    {
        "macho": {"fabricante": str, "tipo": str},
        "femea": {"fabricante": str, "tipo": str},
    }

A fase 19 garante a compatibilidade de fabricante e tipo da conexão. As
propriedades elétricas de conectores são verificadas pelos itens declarados em
componentes_cc; propriedades ausentes serão lacuna para a unidade de catálogo.

## Regras de decisão

Todas as entradas numéricas devem ser finitas; bool não é número válido. Inteiros
grandes que não possam ser representados finitamente e qualquer overflow de
intermediário geram `NUMERO_INVALIDO`; nenhum `NaN`, `inf`, `TypeError` ou
`OverflowError` escapa da função.
Entrada ausente, tipo inválido ou valor não positivo gera falha e nunca aprova
parcialmente o caso.

    voc_arranjo_v = voc_modulo_v * modulos_serie
    v_max_arranjo_v = voc_arranjo_v * fator_correcao_tensao
                       ou v_max_arranjo_v fornecido pelo fabricante
    isc_arranjo_a = isc_modulo_a * series_paralelo
    protecao_series_requerida =
        (series_paralelo - 1) * isc_modulo_a > imod_max_ocpr_a
    corrente_minima_arranjo_a = 1.25 * isc_arranjo_a
    corrente_referencia_componentes_a = (
        corrente_minima_arranjo_a
        quando não houver proteção do arranjo
        ou corrente nominal da proteção do arranjo
    )

Falhas normativas:

- componente CC com adequado_cc diferente de True;
- tensão nominal abaixo de v_max_arranjo_v;
- corrente nominal abaixo da corrente_referencia_componentes_a;
- proteção do arranjo com tipo não autorizado ou corrente inválida;
- proteção de série necessária ausente;
- tipo de dispositivo fora da lista autorizada;
- proteção individual fora das desigualdades de 5.3.11.1;
- proteção agrupada com series_grupo > series_paralelo ou fora das desigualdades;
- conectores declarados com fabricante ou tipo diferente.

As desigualdades de proteção são estritas. A implementação compara diretamente
os limites representáveis e os testes cobrem o valor no limite e o próximo
`float` representável em cada lado; não há tolerância artificial via `isclose`.

Códigos de falha estáveis. Também é falha fornecer simultaneamente
fator_correcao_tensao e v_max_arranjo_v, ou não fornecer nenhum dos dois:
ENTRADA_AUSENTE, NUMERO_INVALIDO, COMPONENTE_NAO_CC,
TENSAO_COMPONENTE_INSUFICIENTE, CORRENTE_COMPONENTE_INSUFICIENTE,
PROTECAO_SERIE_AUSENTE, TIPO_PROTECAO_CC_INVALIDO,
PROTECAO_INDIVIDUAL_FORA_DA_FAIXA, PROTECAO_GRUPO_FORA_DA_FAIXA,
CONECTOR_FABRICANTE_INCOMPATIVEL, CONECTOR_TIPO_INCOMPATIVEL e
TENSAO_MAXIMA_AMBIGUA.

## Tratamento de fontes e scheduler

Adicionar à descoberta uma unidade atômica para a pendência de fotovoltaico:

- tópico: fotovoltaico;
- disciplina: eletrica;
- prioridade acima da pendência ampla de vigência;
- teste sugerido: framework/galpao_fw/tests/test_fotovoltaico.py;
- fontes:
  - 05_ELETRICA/ELETRICA__NBR__NBR-16690-2019__instalacoes-arranjos-fotovoltaicos.pdf;
  - 05_ELETRICA/ELETRICA__NBR__NBR-16149-2013__interface-fv-rede-distribuicao.pdf.

A pendência ampla sobre ANEEL/distribuidora continuará visível como tarefa
separada e não será considerada resolvida por esta unidade.

## Testes e critérios de aceite

Positivos:

- caso completo com uma série e componentes compatíveis retorna ok=True;
- tensão máxima calculada por fator e fornecida diretamente produz valores
  equivalentes;
- proteção individual válida é aceita;
- proteção agrupada válida é aceita;
- conectores do mesmo fabricante e tipo são aceitos.

Negativos:

- campo obrigatório ausente, número não finito, zero, negativo ou bool;
- tensão ou corrente de componente abaixo do limite;
- componente não apropriado para c.c.;
- proteção necessária ausente;
- dispositivo CA ou tipo não autorizado;
- desigualdade individual ou agrupada violada;
- conectores de fabricante ou tipo diferentes;
- usa_conectores=True sem par macho/fêmea.

O teste de integração da descoberta confirma que a unidade possui somente os
dois caminhos locais de fonte e é ordenada antes da pendência ampla.

O retorno também inclui as seções de proteção e conectores efetivamente
avaliadas (5.3.9, 5.3.11.1, 6.2.8.1 e 6.2.8.2), além da delimitação de
interface 5.5–5.7 da NBR 16149 com seu `source_id`; essa fonte não é usada
para inventar regras internas do lado CC.

## Não objetivos

- não alterar as fórmulas existentes de área, geração, módulos ou inversores;
- não incorporar valores de catálogo marcados como “A CONFIRMAR”;
- não consultar a web ou criar fontes durante a implementação;
- não declarar conformidade integral do sistema FV;
- não apagar a pendência ampla de ANEEL/distribuidora.
