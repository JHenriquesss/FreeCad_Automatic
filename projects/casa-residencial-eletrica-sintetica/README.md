# Casa residencial elétrica sintética

Fixture de integração da vertical elétrica residencial BT/Enel. Ela registra
um caso sintético para o loop universal; não representa aprovação da Enel,
ART, vistoria ou liberação para construção.

Os campos locais `status: 2` são um snapshot das fontes. Depois de autenticar,
o primeiro comando abaixo produz a verificação viva das fontes antes da
execução; o segundo usa o readiness aprovado.

```powershell
nlm login
python framework/galpao_fw/project_loop_cli.py --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/readiness --verify-source-refs --preflight-only --require-source-refs
python framework/galpao_fw/project_loop_cli.py --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/run --readiness projects/casa-residencial-eletrica-sintetica/readiness --require-source-refs --no-ifc
```

A cobertura de motores desta fase é deliberadamente limitada à combinação
`1 CV trifásico, quantidade 1`. O resultado usa o campo `demand_kva`; motores
fora dessa linha exigem revisão explícita e não são interpolados.

Use uma pasta de saída nova para cada execução. O resultado esperado da
fixture é `needs_review`: `circuits.points` declara as cargas e
`circuits.designs` declara as entradas de engenharia sem defaults.
`circuits.designs` é obrigatório para executar o dimensionamento; quando
faltar, a disciplina fica `blocked` com `missing_circuit_designs`. Nesta fase
a vertical dimensiona condutor/proteção e indica DR/DPS, mas a ausência de
`short_circuit` mantém `short_circuit_evaluation: not_evaluated` e o status
geral em `needs_review`. Ainda não há IFC, FCStd, DXF, SVG, PDF, unifilar ou
prancha executiva. O fixture continua sendo apenas integração; não representa
aprovação da Enel, ART, vistoria ou liberação para obra.
