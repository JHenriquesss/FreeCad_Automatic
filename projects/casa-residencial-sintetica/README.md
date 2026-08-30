# Casa residencial sintética

Esta pasta contém uma fixture de contrato para validar a generalização do
Loop de projeto. Ela testa entrada por arquivo, seleção de adaptador,
manifesto, estados de disciplinas e verificação de artefatos.

Não é um projeto residencial para obra. A fixture não faz cálculo,
dimensionamento ou validação normativa e não gera IFC, modelo 3D, desenhos ou
caderno de obra. As disciplinas presentes devem retornar `needs_review`, que é
o estado correto para este caso sintético.

Os `source_refs` vazios são deliberados: não há alegação de consulta normativa
ao vivo. A cidade e a concessionária são apenas dados de contexto da fixture.
O resultado `ok: true` do verificador significa somente que os artefatos
persistidos estão íntegros e seus hashes conferem; não significa aprovação
técnica ou autorização para construção.

## Onde fica o projeto residencial que calcula

Esta fixture continua existindo porque é o caso de contrato do núcleo: ela
prova que o Loop aceita outra tipologia sem conhecer a geometria do galpão.
O projeto residencial que **dimensiona de verdade** (arquitetura, elétrica e
hidráulica) é [`casa-residencial`](../casa-residencial/README.md), executado
pelo adaptador `casa-residencial`. Os dois convivem: a fixture testa o
contrato, o outro exerce as disciplinas.
