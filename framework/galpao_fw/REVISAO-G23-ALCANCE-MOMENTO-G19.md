# REVISAO — G23: alcance do momento na base + G19 sem inventar obra

O momento na base que o G17 ligou à fundação se espalhou para consumidores que
ninguém tinha auditado. O G17 já havia provado o risco uma vez, roteando o
BLOCO de concreto simples pelo caminho de divisa (corrigido em `29acc18`); a
pergunta do G23 era quantos outros não pegamos. Em paralelo, o G19 ganha o
cabeamento do 4º caso sem destravar validação com dado sintético.

## 1. Vereditos de alcance do M_base (sem terceira opção)

Cada consumidor de `M_base`/`M_portico` usa ou ignora COM razão declarada —
nenhum caminho onde excentricidade chegue por acidente
(`fundacao_edificio.py:47-70`):

| Consumidor | Veredito |
|---|---|
| Sapata isolada (`fundacao_sapata.dimensiona_sapata_env`) | USA M via Parte A (`tensoes_solo` N+M, núcleo/borda, FS tomb/desl com e=M/N) |
| Bloco simples (`dimensiona_bloco_env`) | USA M para bearing (mesma Parte A) mas NÃO gera armadura de flexão (β≥60° NBR 6122 7.8.2, bielas comprimidas). Sempre isolado, nunca divisa (guarda de `29acc18`) |
| Estaca isolada (`estaca_profunda.verifica_estaca`) | USA M quando o GRUPO tem braço (n=4, Sxx/Syy>0, Navier); para n=1-2 o grupo NÃO resiste e o momento vai para TIRANTES DE BALDRAME (fronteira nomeada). V sempre ignorado (Broms/Matlock-Reese não existe) |
| Sapata de divisa (`sapata_divisa.py:10`) e viga de equilíbrio (`viga_equilibrio.py:27`) | IGNORAM `M_portico` com razão declarada: a excentricidade GEOMÉTRICA da divisa (e=(B−b)/2 ~0,6-0,8 m, P·e ~800-1500 kNm) domina M típico 10-40 kNm (2-5%); modelo de divisa com M fletor adicional não existe na NBR 6122/Velloso-Lopes e não é inventado |
| `bim_edificio.py:341`, `gestao_edificio.py:354`, `orcamento.py`, `galpao_turnkey.py`, `build_federado` | Varridos com veredito (usa corretamente ou ignora com razão — ver commit `2b52e73`) |
| Gate ATENDE (`fundacao_edificio.py:741`) | Reflete M via Parte A (rasa) e via `grupo_momento` (estaca) |

Ação horizontal completa em `fundacao_edificio.py:29-45`: tombamento global
como binário entre prumadas, cortante dividido igualmente (rasa; na estaca,
`esforco_horizontal_na_estaca: not_available` com razão, não silêncio), M por
pilar do pórtico heterogêneo (G17).

## 2. Infraestrutura ≠ divergência numérica (item pequeno, bug real de leitura)

`validacao_sistema_g15.py:249` passa a separar falha de INFRAESTRUTURA
(arquivo/caminho) de divergência numérica, com `[INFRA]` no NOME do check, não
escondido na mensagem. Antes as duas saíam como `err=nan%` — foi assim que um
bug de caminho relativo pareceu engenharia por um instante.

## 3. G19 sem inventar obra

O gargalo não é código, são os 9 campos de `ENTRADAS-PENDENTES.md`, e eles
CONTINUAM pendentes: o `project-spec.json` canônico segue com 9 `__PENDENTE__`
e o G19 não foi destravado. A proposta 36×24 está rotulada como hipótese em
quatro lugares independentes (nome do arquivo, description,
`test_assumptions.status=not_real_engineering_input`, README) e serve para
exercitar o pipeline, não para validar engenharia:

- Cabeamento: `docs/validacao_g15/` (CHECKLIST, ESQUEMA, FLUXO, QUARTO-CASO,
  README, sidecar exemplo + template), `tools/gerar_sidecar.py`,
  `tools/ingestao_sjb.py`, `tools/validar_9_campos.py`,
  `tools/demo_g19_4o_caso.py`, `validacao_sistema_g15.py` (preflight + memorial
  + obra conhecida agente 36×24 + obras genéricas).
- RESSALVA (dívida paga no G36): `tools/demo_g19_4o_caso.py` comparava o
  framework contra um sidecar gerado PELO PRÓPRIO framework e imprimia `0.00%`
  PASS — circular por construção: prova que o harness compara, não que o
  cálculo está certo. O README avisava; o aviso agora sai junto do número no
  terminal (ver `demo_g19_4o_caso.py`).

Commit: `2b52e73 feat(g23)` — 31 arquivos, +2821/−50. Verificação dirigida ao
código novo: `test_[m-z]*` 759 + fronteiras/G21/mezanino/tools 268 +
`branches/g15`+`branches/g9` 77 = 1104 verificados, 0 falhas (suite completa
3082 com `-n 4` pendente de ambiente com xdist).

## 4. O que este G23 NÃO fez

- Não destravou o G19 (9 campos seguem pendentes; proposta ≠ obra real).
- Não criou modelo de divisa com M fletor adicional nem Broms/Matlock-Reese
  para estaca transversal — limitações nomeadas, não verificações esquecidas.
- Não rodou a suite completa de 3082 (ver acima).
