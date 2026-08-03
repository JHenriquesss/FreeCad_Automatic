# tools/

## run_tests.py — regressão non-build confiável

Roda a suíte `-m "not build"` (~1281 testes) de forma reproduzível e dentro do
limite de tempo do ambiente.

```bash
python tools/run_tests.py            # suíte inteira
python tools/run_tests.py -x -k terca   # args extras vão pro pytest
```

- **Rápido (recomendado):** com `pytest-xdist` instalado, paraleliza tudo num só
  comando — **~5 min** em 8 núcleos (vs ~15 min sequencial). A suíte é **xdist-safe**
  (verificado S40: 1281 passed com `-n auto`).
- **Fallback (sem xdist):** 2 lanes sequenciais — os pesados `test_fase*` +
  `test_crashes_wiki07` (243 testes, ~20 s cada, rodam o `rodar_projeto.calcular`
  completo) isolados dos 1038 rápidos, para a lane rápida sempre fechar sob o limite.

Instale o toolchain de teste com:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Os testes de build 3D (`-m build`, exigem FreeCAD) ficam de fora — rodam à parte.
