# Glossario de Elementos (PT-BR)

Nomenclatura dos elementos no modelo FreeCAD e no levantamento de material.
Todo o projeto e registrado em portugues. Lados: E = esquerda, D = direita.
Frente/fundo = oitoes. Numeracao com dois digitos (01, 02, ...).

## Estrutura principal

| Nome | O que e |
| --- | --- |
| `PORTICO_NN_COLUNA_E/D` | Coluna (pilar) do portico, lado esquerdo/direito |
| `PORTICO_NN_VIGA_E/D` | Viga inclinada do portico (agua esquerda/direita) |
| `VAO_NN_CUMEEIRA` | Viga de cumeeira (longitudinal, por vao) |
| `VAO_NN_ESCORA_BEIRAL_E/D` | Escora de beiral (longitudinal no no beiral) |
| `MONTANTE_OITAO_FRENTE/FUNDO_NN` | Montante de oitao (tapamento frontal) |

## Sistema secundario

| Nome | O que e |
| --- | --- |
| `TERCA_E/D_NN`, `TERCA_BEIRAL_E/D` | Terca de cobertura (perfil U, face aberta p/ beiral) |
| `TERCA_PAREDE_E/D_NN` | Terca de parede (girt) do tapamento lateral |
| `TIRANTE_E/D_VAO_NN_SS` | Tirante (linha de corrente) das tercas |
| `MAO_FRANCESA_XX_NN` | Mao-francesa (contencao da mesa inferior) |
| `CONTRAV_COBERTURA_NN_A/B` | Contraventamento da cobertura (so-tracao) |
| `CONTRAV_PAREDE_E/D_NN_A/B` | Contraventamento vertical de parede (so-tracao) |

## Bases e ligacoes

| Nome | O que e |
| --- | --- |
| `PLACA_BASE_E/D_NN` | Placa de base |
| `CHUMBADOR_E/D_NN_a/b` | Chumbador (barra de ancoragem) |
| `CHUMBADOR_GANCHO_E/D_NN_a/b` | Gancho (perna 90 graus) do chumbador |
| `ARRUELA_E/D_NN_a/b` | Arruela de chapa (sobre furo alargado) |
| `VERGA_PORTA_E` | Verga sobre a porta (interrompe a terca de parede) |

## Envelope, drenagem e aberturas

| Nome | O que e |
| --- | --- |
| `TELHA_E/D` | Telha de cobertura (agua esquerda/direita) |
| `TAPAMENTO_LATERAL_E/D` | Tapamento (fechamento) lateral |
| `TAPAMENTO_OITAO_FRENTE/FUNDO` | Tapamento do oitao |
| `CALHA_E/D` | Calha de beiral |
| `CONDUTOR_E/D_NN` | Condutor (tubo de descida) |

Aberturas recortadas no tapamento: portao (oitao frente), porta (lateral E),
janelas (faixa alta nas laterais).

## Verificacoes automaticas (saida do script)

| Chave | Significado |
| --- | --- |
| `interferencias` | pares estrutura x estrutura que se cruzam indevidamente (deve ser 0) |
| `conflito_abertura_contrav` | aberturas de parede sobre vao contraventado (deve ser vazio) |
| `estrutura_em_aberturas` | estrutura dentro de portao/porta (deve ser vazio) |
| `massa_total_kg` | massa total (aco + envelope), calculada do volume dos solidos |
