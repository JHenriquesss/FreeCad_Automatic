# Catalogação e organização das fontes — Implementation Plan

> **For agentic workers:** Execute este plano em tarefas sequenciais com verificação após cada etapa. Os arquivos de fontes não serão apagados; somente serão movidos e renomeados com mapa explícito.

**Goal:** Organizar os 75 documentos da pasta `fontes/` em subpastas disciplinares, normalizar seus nomes e gerar um catálogo auditável para uso no NotebookLM e no framework.

**Architecture:** A organização física será por disciplina. O catálogo CSV será a fonte de rastreabilidade entre nome original, nome normalizado, tipo, norma/autor, edição, hash e observações. Possíveis duplicatas semânticas serão preservadas e marcadas para revisão.

**Tech Stack:** PowerShell, SHA-256, `fitz`/PyMuPDF para leitura de metadados PDF, `apply_patch` para documentação.

## Global Constraints

- Não excluir nenhum documento.
- Preservar o conteúdo byte a byte; hashes SHA-256 antes/depois devem coincidir.
- Usar nomes portáveis, sem acentos, espaços, hashes de sites ou caracteres especiais.
- Manter a edição/ano quando identificados.
- Não inventar autor, edição ou título; usar `99_REVISAR` quando a identificação for insuficiente.
- Manter `README.md`, catálogo e relatórios na raiz de `fontes/`.

---

### Task 1: Validar inventário pré-movimentação

**Files:**
- Read: `fontes/*`
- Produce: hash map in memory for `fontes/catalogo.csv`

- [ ] Contar os 75 documentos, separar `README.md` e calcular SHA-256 de cada documento.
- [ ] Verificar colisões de nomes e hashes antes de criar destinos.
- [ ] Abortar se houver destino já ocupado ou fonte ausente no mapa.

### Task 2: Criar taxonomia e mapa de nomes

**Files:**
- Create: subpastas `fontes/00_FRAMEWORK` até `fontes/99_REVISAR`
- Create: `fontes/catalogo.csv`

- [ ] Classificar todos os documentos nas disciplinas aprovadas.
- [ ] Aplicar o padrão `DISCIPLINA__TIPO__NORMA-O-AUTOR__TITULO-CURTO.ext`.
- [ ] Marcar candidatos semânticos, como versões históricas e scans alternativos, sem eliminá-los.

### Task 3: Mover e renomear preservando bytes

**Files:**
- Modify: localização dos 75 documentos sob `fontes/`

- [ ] Criar destinos somente após validar que todos os nomes finais são únicos.
- [ ] Mover cada arquivo pelo mapa explícito.
- [ ] Não sobrescrever destino existente; interromper se surgir colisão.

### Task 4: Gerar documentação da coleção

**Files:**
- Modify: `fontes/README.md`
- Create: `fontes/duplicatas-semanticas.md`
- Create: `fontes/fontes-faltantes.md`

- [ ] Registrar contagens por pasta e por extensão.
- [ ] Documentar fontes prioritárias ainda ausentes para os módulos atuais.
- [ ] Separar fontes bloqueadoras, complementares e futuras.

### Task 5: Verificação final

**Files:**
- Read: `fontes/catalogo.csv`
- Read: `fontes/*`

- [ ] Confirmar 75 documentos após a movimentação.
- [ ] Confirmar que cada hash pós-movimento existe exatamente uma vez.
- [ ] Confirmar que não restaram documentos soltos fora das subpastas.
- [ ] Confirmar que `README.md`, `catalogo.csv`, `duplicatas-semanticas.md` e `fontes-faltantes.md` existem.
- [ ] Reportar qualquer item que precise de revisão humana.
