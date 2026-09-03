# G29 — Fontes Fabricadas (backup negativo para G30)

> **CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA**
> Este diretório contém cópia dos três diretórios fabricados que estavam em `fontes_externas/` antes do G29.
> São **material negativo** para o G30: fixtures que **devem falhar** em validação de procedência/página, URL https, e classe de autoridade.
> Não são lixo — são o conjunto de teste que prova que o protocolo detecta fabricação.

- `licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/` — PDF 2959 bytes sintético, autor Quitandinha 014/2023, file://, sha f9a260c704b6...
- `tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/` — PDF 1393 bytes sintético, autor Lab. Recife 2018, file://, sha 1c7334f60d81...
- `tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL/` — PDF 7083 bytes sintético, autor UFSM 2021 tcc_academico, file://, sha 1fe6f59af568...

Cada um com `fixture.json` com `pagina` inventada (45,46,48...) e `trecho_literal` sintético, `url=file://` e `classe` errada para o 25x54 (tcc_academico em vez de material_comercial).

G30 usará estes para provar que o detector de fabricação fica **vermelho** com eles e **verde** com as fontes reais em `fontes_externas/` (https, attena.ufpe.br, calculistadeaco.com.br, Petropolis Celina Schechner 2ª licitação).

Copiado em G29 via `Copy-Item` antes da substituição pelos PDFs reais via `tools/extrai_fonte_externa.py` (urllib, https).
