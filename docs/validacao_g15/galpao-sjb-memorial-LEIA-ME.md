# Placeholder do memorial SJB

Este diretorio aguarda o memorial de obra construida do galpao SJB/ENEL.

- Arquivo esperado: `galpao-sjb-memorial.pdf` (PDF original do escritorio, nao gerado pelo framework).
- Sidecar esperado: `galpao-sjb-valores-referencia.json` (preenchido a partir de `galpao-sjb-valores-referencia.json.template`).

Enquanto nao houver obra real doada, o harness G15 roda em modo guard:

```
python -m validacao_sistema_g15  # 21/21 PASS — 2 checks SJB em SKIP (AGUARDANDO OBRA REAL)
```

Nao commitar PDF com dados sensiveis sem autorizacao do responsavel tecnico.

Se voce tem uma obra que conhece (galpao, casa, estrutura), doe o memorial aqui e abra um `project-spec.json` em `projects/galpao-sjb/` (ou novo `projects/<slug>/`) com os 9 campos de `ENTRADAS-PENDENTES.md`. O harness reaplica-se como 4o caso em um comando.

Ver `README.md` neste diretorio para formato do sidecar e passos de ingestao.
