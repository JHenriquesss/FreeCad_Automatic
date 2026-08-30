# Readiness gate implementation plan

**Goal:** Expor o preflight como um gate auditável entre o Loop de
desenvolvimento e o Loop de projeto, sem executar disciplinas no modo de
homologação.

**Constraints:** reutilizar `normalize_spec`/`_preflight`; não duplicar regras
de engenharia; não alterar o comportamento padrão de `run_project`; preservar
o contrato de entrada por arquivo e os manifestos existentes.

## Tasks

1. **Contrato e testes RED**
   - adicionar testes para API, persistência, ausência de execução e estados
     `ready`/`needs_review`/`blocked`;
   - adicionar teste CLI para `--preflight-only` e códigos de saída.
2. **Implementar API**
   - criar `preflight_project` em `project_loop.py`;
   - criar `preflight_project_file` em `project_io.py` e reexportar.
3. **Implementar CLI**
   - adicionar flag sem alterar a jornada normal;
   - persistir resumo de prontidão e mapear códigos.
4. **Documentar e integrar**
   - atualizar `COMO-RODAR.md` e o registro da sessão;
   - ligar a etapa ao spec SJB/ENEL e aos critérios do Loop 2.
5. **Verificar**
   - testes focados, branches/trunk do Loop, regressão afetada,
   `compileall` e `git diff --check`.

## Evidence

- Readiness focused: 15 testes aprovados após as correções de autoridade.
- Branches do Loop + trunk: 43 testes aprovados.
- Regressão turnkey/BIM/clash/validação: 76 aprovados, 1 desmarcado.
- `tools/loops/tests`: 228 aprovados.
- `compileall` e `git diff --check`: aprovados.
- Gate real do template SJB/ENEL: `blocked`, 9 erros e seis disciplinas com
  pendências de dados; as seis têm referências de fonte válidas e nenhum
  `project-run.json` foi criado.
