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
fixture é `needs_review`: a vertical ainda não dimensiona condutores e
proteções nem emite entregáveis executivos.
