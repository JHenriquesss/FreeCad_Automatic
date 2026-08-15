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
