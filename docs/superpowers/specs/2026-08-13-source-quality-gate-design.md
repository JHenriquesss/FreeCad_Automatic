# Gate local de qualidade das fontes — Especificação de Design

**Data:** 2026-08-13  
**Status:** aprovado para implementação nesta sessão  
**Escopo:** Fase 26 do loop de desenvolvimento

## Objetivo

Evitar consultas remotas inúteis quando uma fonte PDF declarada não possui texto
extraível suficiente para produzir citações auditáveis. O gate deve diagnosticar o
arquivo local, registrar a pendência e estacionar a tarefa antes de executar
`nlm notebook query`.

## Contexto observado

- O adaptador `NlmCliAdapter` já recebe exatamente os `source_paths` declarados
  pela candidata e só seleciona fontes remotas com status `2`.
- `fontes/03_FUNDACOES_GEOTECNIA/FUNDACOES__NBR__NBR-6122-2022__projeto-fundacoes.pdf`
  possui 120 páginas, 0 páginas com texto e 0 caracteres extraídos.
- `fontes/09_INCENDIO/INCENDIO__NBR__NBR-9077-2025__saidas-emergencia.pdf`
  possui 59 páginas com texto e 127.447 caracteres extraídos.
- PyMuPDF está disponível no ambiente e já é dependência declarada do projeto.

## Decisão de arquitetura

Criar `tools/loops/source_quality.py` como módulo pequeno e independente. Ele
expõe uma função de inspeção PDF que retorna um relatório imutável com número de
páginas, páginas com texto, total de caracteres, maior página e diagnóstico de
usabilidade. A regra mínima de texto utilizável é:

```text
total_chars > 0 e pages_with_text > 0
```

O `NlmCliAdapter` receberá `source_root`, resolverá com segurança o caminho local
catalogado e chamará o inspetor para cada fonte PDF selecionada antes da consulta.
Fontes não-PDF passam sem esta inspeção nesta fase; elas terão um gate específico
quando houver necessidade real.

## Fluxo de falha

1. O NotebookLM lista a fonte e confirma status `2`.
2. O adaptador verifica se o arquivo local existe dentro de `fontes/`.
3. Para PDF, o inspetor mede o texto extraível sem modificar o arquivo.
4. Se o arquivo não existir, for inválido ou não tiver texto, o adaptador escreve
   uma solicitação manual contendo notebook, source ID, caminho, hash e relatório.
5. O adaptador lança `NlmEvidenceRequired`; o supervisor estaciona como
   `manual_source_required` e não cria `evidence.json`.
6. Nenhum comando `nlm notebook query` é executado nesse caminho.

## Não objetivos

- Não executar OCR automaticamente.
- Não criar PDF derivado ou alterar a fonte original.
- Não aceitar resposta textual do NotebookLM sem `cited_text`.
- Não ampliar a pesquisa para outras fontes do notebook.
- Não validar EPUB, CSV ou outros formatos nesta fase.

## Contrato de inspeção

O módulo deve fornecer:

```python
@dataclass(frozen=True)
class PdfTextReport:
    path: str
    pages: int
    pages_with_text: int
    total_chars: int
    max_page_chars: int

    @property
    def usable(self) -> bool: ...

    def summary(self) -> str: ...

def inspect_pdf_text(path: Path) -> PdfTextReport: ...
```

`inspect_pdf_text` deve transformar arquivo ausente, PDF inválido e falha de
leitura em erro explícito com diagnóstico; não deve ocultar exceções como fonte
válida.

## Testes e verificação

- PDF sintético textual: relatório utilizável e consulta segue normalmente.
- PDF sintético formado por imagem: relatório não utilizável.
- Fonte PDF sem texto: pendência manual inclui métricas e o runner não recebe
  chamada `nlm notebook query`.
- Fonte ausente: pendência manual continua funcionando.
- Resposta sem `cited_text`: permanece rejeitada pelo parser atual.
- Diagnóstico real da NBR 6122 confirma 120 páginas e 0 caracteres.

## Critério de aceite

A Fase 26 só estará concluída quando uma fonte textual continuar funcionando, a
NBR 6122 for estacionada antes da consulta remota por diagnóstico local, a suíte
do loop estiver verde e o comportamento estiver documentado no README e no log da
sessão.
