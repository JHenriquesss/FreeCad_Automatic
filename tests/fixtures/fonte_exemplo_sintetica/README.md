# G35 — Fonte-exemplo sintética (NÃO é fonte externa real)

> **CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA**
> Este diretório NÃO é fonte externa. É material de demonstração do protocolo
> G24 / guarda G30: PDF mínimo gerado localmente (1 página, 4 trechos) com
> `pagina` + `trecho_literal` que passam na guarda local **por construção**.
> Nunca foi coleta real e nunca deve voltar para `fontes_externas/registro.json`.

Movido de `fontes_externas/` em G35 (resíduo do lote G24–G32, corpo do commit
`a3e8e4d`, item ABERTO G33). Motivo: a entrada usava URL
`https://example.com/tcc-exemplo-ufmg-2023-galpao-24x36.pdf`, que **dá 404** —
não há servidor de origem — e mesmo assim **passava** na guarda G30, porque o
G30 confere o fixture contra o PDF **local** e nunca verifica que o PDF local
é o que a URL serve. É o limite documentado do G30, agora fechado pelo
`--check-remote` do extrator (`tools/extrai_fonte_externa.py`), que rebusca a
URL ao vivo e compara o SHA-256.

Conteúdo:

- `tcc-exemplo-ufmg-2023-galpao-24x36__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/`
  — diretório da obra movido intacto (`fonte.json`, `fixture.json`,
  `comparacao.json`, `relatorio.txt`, `original.pdf`, `README.md`).
  Notas de arqueologia, preservadas de propósito, sem reescrita:
  - `relatorio.txt` ainda declara `URL: file://fontes_externas/exemplo_dummy.pdf`
    e o SHA antigo `dba5e05e…` — resíduo da época `file://`, anterior à
    reescrita para `https://example.com` + SHA `72b9fb06…`.
  - `fonte.json:observacao_coleta` e `comparacao.json:relatorio_txt` tiveram só
    os caminhos `fontes_externas/…` atualizados para este diretório na mudança;
    valores e trechos, intocados.
- `exemplo_dummy.pdf` — o PDF mínimo (1 página, 1064 bytes, SHA-256 `72b9fb06…`,
  idêntico ao `original.pdf` da obra) antes guardado na raiz de
  `fontes_externas/`.
- `registro_entry.json` — cópia exata da entrada removida de
  `fontes_externas/registro.json` (para auditoria; a fonte de verdade agora tem
  só as 3 fontes reais).

Uso em testes: `test_g30_dummy_sintetico_pass` (agora ancorado aqui) prova que
o G30 local passa por construção; `test_g35_check_remote_*` prova que o
`--check-remote` falha para esta URL (404 / hash incompatível) e passa quando
URL e hash batem (servidor local de teste).
