# Casa residencial elétrica sintética

Fixture de integração da vertical elétrica residencial BT/Enel. Ela registra
um caso sintético para o loop universal; não representa aprovação da Enel,
ART, vistoria ou liberação para construção.

Os campos locais `status: 2` são um snapshot das fontes. Depois de autenticar,
o primeiro comando abaixo executa o gate ao vivo das fontes antes da execução.

```powershell
nlm login
python -m framework.galpao_fw.project_loop_cli --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/readiness --preflight-only --require-source-refs
python -m framework.galpao_fw.project_loop_cli --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/run --readiness projects/casa-residencial-eletrica-sintetica/readiness --require-source-refs --no-ifc
```

Use uma pasta de saída nova para cada execução. O resultado esperado da
fixture é `needs_review`: a vertical ainda não dimensiona condutores e
proteções nem emite entregáveis executivos.
