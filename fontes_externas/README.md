# G24 — Protocolo de Fonte Externa (bloqueia todos os outros)

> **CONCORDANCIA ENTRE CALCULISTAS — NAO E OBRA CONSTRUIDA**
> Nenhum número neste diretório valida o framework contra obra edificada.
> Toda comparação aqui é concordância entre calculistas com premissas
> possivelmente diferentes. Não rotular como “validado contra obra real”
> em nenhum artefato derivado. Daqui a seis meses alguém vai ler
> “validado contra obra real” se você deixar — este aviso existe para impedir.
>
> Este aviso replica-se obrigatoriamente em **quatro lugares**:
> 1. **Nome do diretório** da obra — sufixo `__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL`
> 2. **JSON** — campo `_aviso` / `rotulo` em `registro.json` e em cada `fonte.json` / `fixture.json` / `comparacao.json`
> 3. **README** — este arquivo (sec. Rotulagem)
> 4. **Relatório** — cabeçalho de todo relatório gerado em `fontes_externas/<obra>/relatorio*.txt` ou `comparacao.json`

Sem este protocolo, a primeira divergência vira decisão ad hoc e o
framework acaba calibrado para reproduzir o TCC de um aluno — pior do
que não ter validação externa nenhuma. **Nada de comparar número antes
disto existir.**

---

## 1. Registro — `fontes_externas/registro.json`

Uma entrada por obra. Cada entrada contém obrigatoriamente:

| Campo | Tipo | Regra |
|---|---|---|
| `id` | string | slug único, terminado em `__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL` |
| `url` | string | URL canônica do PDF (https ou file:// para coleta local) |
| `sha256` | string | hex de 64 chars do PDF baixado (verificado pelo extrator) |
| `data_coleta` | string | ISO 8601 `YYYY-MM-DD` da coleta |
| `autor` | string | nome + instituição + ano da obra |
| `classe_autoridade` | enum | ver §2 |
| `titulo_obra` | string | título literal da obra |
| `rotulo` | string | = `CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA` |
| `observacao_coleta` | string | notas da coleta (opcional) |

Exemplo mínimo em `registro.json`:

```json
{
  "id": "licitacao-pm-sjb-2024-galpao-30x60__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL",
  "url": "https://transparencia.sjb.rj.gov.br/licitacoes/edital123_galpao.pdf",
  "sha256": "a3f5c9e…64hex…",
  "data_coleta": "2026-09-03",
  "autor": "Prefeitura SJB - Edital 123/2024 - Eng. Resp. CREA 123456",
  "classe_autoridade": "licitacao_executada",
  "titulo_obra": "Galpão 30x60m - Memorial e quantitativos",
  "rotulo": "CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA"
}
```

O arquivo `registro.json` também carrega na raiz os campos de rótulo
`_aviso` e `_rotulo_quatro_lugares` idênticos ao cabeçalho deste README.

Per-obra o registro espelha-se em `fontes_externas/<id>/fonte.json`
(cópia da entrada + `pagina_exemplo_referencia` e `trecho_literal_exemplo`
para auditoria humana rápida). A fonte de verdade é `registro.json`.

---

## 2. Hierarquia de autoridade declarada

Ordenada decrescentemente (maior autoridade primeiro). Usada para
ponderar divergências e para ordenar o registro:

```
licitacao_executada  >  projeto_licitado  >  livro_exemplo_resolvido
                     >  tcc_academico     >  material_comercial
```

- `licitacao_executada` — edital + memorial de obra licitada e executada (maior peso)
- `projeto_licitado` — projeto licitado ainda não executado
- `livro_exemplo_resolvido` — exemplo resolvido em livro técnico (ex. Bellei, Pfeil)
- `tcc_academico` — TCC/dissertação acadêmica
- `material_comercial` — catálogo / material comercial (menor peso)

Toda entrada deve declarar sua classe. Um `tcc_academico` nunca
sobrepõe `licitacao_executada` em caso de divergência — calibrar o
framework para reproduzir TCC é a falha que este protocolo bloqueia.

---

## 3. Veredito de divergência — enum fechado

Escrito **antes** de ver qualquer resultado. Toda comparação em
`fontes_externas/<id>/comparacao.json` deve usar exatamente um destes
valores em `veredito`:

| Veredito | Significado | Consequência |
|---|---|---|
| `concorda` | Concordância entre calculistas dentro da tolerância numérica declarada (G31) | Não mexe; valida a entrada/cálculo |
| `framework_errado` | Framework diverge da norma / física; fonte defensável | Único que autoriza mexer no framework, **exige** `citacao_normativa` (ex. `NBR 8800:2024 §5.4.3 p.60 eq.5.4-10`) |
| `fonte_errada` | Fonte contém erro demonstrável | Não mexe no framework; documentar prova |
| `hipotese_divergente` | Ambas defensáveis, premissas diferentes (ex. base rotulada vs engastada) OU erro acima da tolerância `concorda` mas ainda defensável | Não mexe; registrar hipóteses lado a lado |
| `nao_comparavel` | Definições diferentes — guarda do `d·sen(45)` | Não comparar; explicitar `d` vs `d·sen45`, `L_rafter inclinado` vs `projeção`, `vão livre` vs `eixo` etc. |
| `nao_conclusivo` | Dados insuficientes para decidir | Não mexe; coletar mais páginas/trechos |

Fechado = nenhum outro string é aceito. Teste reprova veredito fora do enum.

### 3.1 G31 — Tolerância que separa `concorda` de `hipotese_divergente`

Regra escrita **antes** de reclassificar — senão vira calibração pelo resultado.
Valores derivados das tolerâncias G15 já existentes, não inventados para o caso.

| Grandeza | Tolerância | Origem G15 | Exemplo |
|---|---|---|---|
| Geometria (m, mm) — bay, vão, altura, L_rafter | **2 %** | G15 elétrica 2 % | bay 7,5 vs 7,5 = 0 % → `concorda` |
| Massa linear / peso (kg/m, kg) — perfil, romaneio | **10 %** | G15 peso 10 % | tapamento 13 vs 14 = 7,7 % → `concorda` (≤10 %) |
| Diâmetro contraventamento (mm) | **10 %** | peso-like 10 % | — |
| Esforço (kN, kNm) — M, N, V | **15 %** | G15 M/H 15 % | — |
| Índice (m³/m², kg/m³) — banda magnitude | **10 %** | quantitativo 10 % | 0,194 vs 0,206 = 6,2 % → `concorda` (se mesma definição) |
| default | **10 %** | — | fallback |

Implementado em `framework/galpao_fw/fontes_externas_protocolo.py:TOLERANCIA_CONCORDA_PCT`,
`erro_relativo_pct()` e `classifica_concorda_ou_hipotese()`.

- `erro_relativo_pct = |fonte - framework| / |framework| × 100`
- `erro ≤ tolerância[grandeza]` → `concorda`
- `erro > tolerância` mas defensável → `hipotese_divergente`

> Antes de G31, `bay_porticos` 7,5 vs 7,5 exato era `hipotese_divergente` com
> observação "CONCORDÂNCIA EXATA… não é erro" — sintoma de enum incompleto.
> Após G31, mesma entrada vira `concorda` porque 0 % ≤ 2 %. A viga de
> tapamento 13 vs 14 (7,7 %) já estava descrita como "Concordância próxima"
> mas classificada como `hipotese_divergente` leve; com a regra 10 % ela é
> `concorda` — decisão tomada pela regra, não pelo resultado desejado.

### Regra que dá sentido ao resto

> Uma divergência só pode ser **fechada mexendo no framework** quando o
> veredito for `framework_errado` **com citação normativa**.
> Concordar com a fonte nunca é justificativa suficiente.

Implementado em `framework/galpao_fw/fontes_externas_protocolo.py:fechar_divergencia()`:
- `mudou_framework == True` exige `veredito == "framework_errado"` e `citacao_normativa.strip() != ""`
- `veredito != "framework_errado"` + `mudou_framework` → exceção / FAIL
- `framework_errado` sem citação → exceção / FAIL

---

## 4. Guarda contra fabricação — procedência por número

Todo número em `fontes_externas/<id>/fixture.json` carrega **pagina + trecho_literal**:

```json
{
  "_aviso": "CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA",
  "fonte_id": "tcc-ufmg-2023-galpao-24x36__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL",
  "valores": {
    "Mcol_kNm": {
      "valor": 235.9,
      "pagina": 42,
      "trecho_literal": "Momento fletor máximo no topo do pilar: 235,9 kNm (Tab. 4.2, combinação Fd1)",
      "unidade": "kN.m",
      "definicao": "M no topo da coluna, combinação Fd1 1.25G+1.5Q, portico 24m"
    }
  }
}
```

- `pagina` : int >0 (página do PDF onde o número aparece)
- `trecho_literal` : string ≥10 chars, cópia literal do trecho do PDF que contém o número

Valor sem `pagina` ou sem `trecho_literal` **reprova em teste**
(`framework/galpao_fw/tests/test_fontes_externas_protocolo.py`).
É a mesma doença de sempre — número que aparece e ninguém sabe de onde veio.

O extrator `tools/extrai_fonte_externa.py` grava o esqueleto já com esses
campos obrigatórios; deixar em branco mantém o fixture em estado
`BLOQUEADO - sem proveniência` até preenchimento manual auditável.

---

## 5. Rotulagem obrigatória (4 lugares) — padrão 36×24

A proposta `36×24` já usa o padrão: `PROPOSTA NAO E OBRA REAL` aparece em
`projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json`,
`docs/validacao_g15/proposta-36x24-exemplo-valores-referencia.json`,
`projects/galpao-sjb/PROPOSTA-README.md` e nos relatórios.
Para fontes externas replica-se idêntico, mas com o rótulo

```
CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA
```

nos quatro lugares:

1. **Diretório**: `fontes_externas/<id__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL>/`
2. **JSON**: `_aviso` / `rotulo` em `registro.json`, `fonte.json`, `fixture.json`, `comparacao.json`
3. **README**: este arquivo + `fontes_externas/<id>/README.md` (se existir)
4. **Relatório**: cabeçalho de `comparacao.json` / `relatorio*.txt` gerado pelo harness

Qualquer comparação que omita o rótulo em um dos quatro lugares é
considerada `BLOQUEADO - rotulagem incompleta`.

---

## 6. Workflow — extrator `tools/extrai_fonte_externa.py`

```powershell
# coleta por URL (ou --pdf-local para arquivo já baixado)
python tools/extrai_fonte_externa.py --url https://repositorio.universidade.br/tcc-galpao.pdf --autor "Silva, J. - UFMG 2023" --classe tcc_academico --id tcc-ufmg-2023-galpao-24x36 --titulo "Galpão 24x36 - TCC UFMG 2023"

# saídas:
# - fontes_externas/registro.json  (entrada acrescentada/atualizada)
# - fontes_externas/<id__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL>/fonte.json
# - fontes_externas/<id>/fixture.json  (esqueleto com pagina+trecho obrigatórios)
# - fontes_externas/<id>/comparacao.json  (esqueleto veredito = nao_conclusivo)
# - PDF salvo em fontes_externas/<id>/original.pdf  (para auditoria, .gitignore opcional)

# verificar (só arquivo local, sem rede)
python tools/extrai_fonte_externa.py --check --id tcc-ufpe-galpao-44x90

# G35: rebuscar a URL ao vivo e comparar SHA-256 com o registrado (prova que o
# PDF guardado é o que a URL serve; o --check só confere o arquivo local)
python tools/extrai_fonte_externa.py --check-remote --id tcc-ufpe-galpao-44x90

# validar procedência de um fixture
python -m pytest framework/galpao_fw/tests/test_fontes_externas_protocolo.py -v
```

O extrator calcula `SHA-256` do PDF, registra `data_coleta` (hoje),
e **nunca inventa** `pagina`/`trecho_literal` — deixa `null` para
preenchimento manual com cópia literal do PDF.

---

## 7. Validação

```powershell
# harness do protocolo (não compara número, valida o protocolo)
python -m pytest framework/galpao_fw/tests/test_fontes_externas_protocolo.py -v

# deve PASS: registro existe, enum fechado, guarda pagina+trecho, rótulo 4 lugares,
# e reprovar fixture sem página (teste negativo incluído)
```

Enquanto `fontes_externas/registro.json` não existir, qualquer
comparação numérica contra fonte externa é considerada `BLOQUEADO - protocolo G24 ausente`.

---

## 8. Referências

- Proposta 36×24: `projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json` + `PROPOSTA-README.md` + `docs/validacao_g15/proposta-36x24-exemplo-valores-referencia.json` (padrão de 4 lugares)
- Guarda `d·sen(45)`: `framework/galpao_fw/validacao_sistema_g15.py:check_armadilha_d_sen45` + `docs/validacao_g15/README.md` (“declare sempre se o memorial mede comprimento inclinado ou projeção”)
- Protocolo em código: `framework/galpao_fw/fontes_externas_protocolo.py`
- Extrator: `tools/extrai_fonte_externa.py`
- Testes: `framework/galpao_fw/tests/test_fontes_externas_protocolo.py`
