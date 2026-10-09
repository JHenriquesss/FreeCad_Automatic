"""G159 - o codigo de producao que entra sem deixar registro (D188).

Defeito (medido no BACKLOG-GOALS-G158-G163.md, 2026-09-21): quatro commits de
2026-09-19 (`dc686af`, `700afd8`, `6734fc8`, `a85bdbe`) entregaram 600 linhas
de conta normativa viva (`demanda_residencial_enel.py`, chamado em
`residencial_eletrica.py:313`, impresso em `desenho_eletrico_residencial.py:
273`) sem verbete, sem D e sem linha de fase - e a guarda do G157 ficou verde,
porque ela casa goals por prefixo de commit `G1xx:` e esses commits nao tem o
prefixo. E a lente do G156 nao viu porque so enxerga `NBR` (convencao 7/G125:
instrumento que nao consegue acusar).

Guarda (neste arquivo, sem modulo novo na producao: nada do produto a
consome, precedente G156/G157 - modulo so consumido pelo teste seria ilha).
Regra: todo commit desde o G149 que tocou arquivo de producao tem cobertura
com D em `wiki/04-decisions.md` ou isencao declarada com motivo medido
(padrao G98: isencao com motivo, nunca renomear).

Fonte unica (armadilha G131): "arquivo de producao" e o predicado
`_e_arquivo_producao`, que e a mesma regra da lente do G156
(`test_citacao_norma_g156._modulos_fonte`: `*.py` do `galpao_fw` que nao
comeca com `test_` nem `varredura_`) - o censo e a checagem usam esse
predicado, nunca uma lista copiada. As listas de emissores do G145/G150
(`varredura_fallback_folha.ALVOS`/`ALVOS_GET`) sao subconjunto para folhas e
NAO servem aqui: nenhum dos tres arquivos WKI esta nelas (o test_05 trava
isso). O test_05 prova que o predicado casa exatamente com `_modulos_fonte`
no repo real; se uma das duas definicoes mudar, ele fica vermelho.

Censo com parada fixa (armadilha do "desde sempre"): `censo_de_git` lista
`COMMIT_BASE_G149^..HEAD` (o commit do G149, hash cheio fixo). Historia mais
antiga nunca entra, mesmo que tenha tocado producao sem verbete.

Anti-tautologia (licao do G91): `confere_censo` recebe o censo (vindo do git,
fonte independente) e a cobertura/isencoes (literais deste arquivo, fonte
independente) como argumentos separados - nunca deriva um do outro.

Baseline nos dois sentidos (convencao 1), via COBERTURA_COMMIT_D e
ISENCOES_COMMIT:
- sentido 1: commit do censo sem cobertura nem isencao reprova, nomeando o
  commit curto e cada arquivo de producao que ele tocou;
- sentido 1b: isencao sem motivo (vazio/branco) reprova;
- sentido 2: cobertura ou isencao para commit fora do censo reprova
  (verbete de commit inexistente); cobertura com D sem `## D` no decisions
  reprova (D tem de existir).
Injecao em tmp_path (convencao 2): os testes 02/03/04 criam um repo git de
verdade no diretorio temporario e exercem a MESMA `censo_de_git`/`confere`
do repo real. Acusa por parte (convencao 7/G125). Um assert por teste (G97).

Contrato de manutencao (o goal seguinte atualiza os dois juntos, no mesmo
commit que tocar producao): o commit novo ganha entrada em COBERTURA_COMMIT_D
(com o D do verbete novo) ou em ISENCOES_COMMIT (com motivo medido); commit
novo sem entrada reprova (sentido 1, fails closed).
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(GALPAO))

import test_citacao_norma_g156 as g156
import varredura_fallback_folha as vff

DECISIONS = os.path.join(GALPAO, "wiki", "04-decisions.md")

#: Parada fixa do censo: o commit do G149 (hash cheio). O `git log` vai de
#: `COMMIT_BASE_G149^..HEAD`, incluindo o proprio G149 e nunca a historia
#: anterior a ele.
COMMIT_BASE_G149 = "86b981c5c982cd102d624afa81261a9e953cd17a"

#: Cobertura: commit (hash cheio) -> D do verbete que o registra. Os seis goals
#: usam os verbetes que o G157 ja numerou; os quatro commits WKI usam o D188
#: (verbete deste goal); o G162 usa o D191 (contrato de manutencao: o hash
#: so existe depois do commit, entao a entrada entra no commit seguinte,
#: que toca so teste e nao entra no censo).
COBERTURA_COMMIT_D = {
    "86b981c5c982cd102d624afa81261a9e953cd17a": "D183",  # G149
    "94d00b6e8bb65890f8fe9141c4080e92878756ce": "D185",  # G151
    "11ee39fffeb2cff3e9426ca4bd6e9b383880c5dd": "D186",  # G152
    "401847181971732e1846e4b88df0199425ca535b": "D180",  # G154
    "4432af0aa0b0ac63bbac816151670e126c543e04": "D181",  # G155
    "6d3b16d9fd92db61150437d0a51d1f35a5d30b8b": "D182",  # G156
    "dc686af44a89282405edf106783cba04d831f23b": "D188",  # WKI p70
    "700afd85bd80660ebea1763067cdb6e6053ea3d4": "D188",  # WKI p71
    "6734fc8c89e427cb9958b1906409974607a4dc73": "D188",  # WKI revisao
    "a85bdbec0a31ccc83d183a9c83ec4a1ceb307a49": "D188",  # WKI cozinha
    "e4779b8d3b15a60b36b6d49b0e0def5d3d6dfa8f": "D191",  # G162
    "a51da6c7db7723247de5d121f58bdb34a4754c74": "D193",  # Fases 1-2 (plano 2026-10-08)
    "d1d19f4b8dedb4eb020e738912ae44100a980601": "D194",  # Fases 1, 3 e 4 (plano 2026-10-08)
    "f0c604e15326cea905f178ef5841834d43b030fb": "D195",  # Fase 2, galpao 20 x 28,5 m
    "145e1e95c4756144b4ab78f67c12417cb31013a4": "D196",  # grade de eixos no IFC
}

#: Isencoes: commit (hash cheio) -> motivo medido. Isencao sem motivo reprova
#: (padrao G98: isencao com motivo, nunca renomear; nunca lista de nomes).
ISENCOES_COMMIT = {
    "6d945108c7bf63a05532429d5a12fa044143459c":
        "auditoria D179 do lote G149-G153 (commit de auditoria, nao entrega "
        "nova: FS 3,0 da estaca deixa de se dizer normativo, NBR 6122:2022 "
        "6.2.1.2.1 = 2,0; verbete D179 cobre; censo com PID reusado e pytest "
        "aninhado)",
}

#: Header de verbete numerado: `## D188 ...` (o D da cobertura tem de existir).
PAT_HEADER_D = re.compile(r"^## (D\d+)\b", re.M)


def _e_arquivo_producao(nome):
    """A definicao de "arquivo de producao" (fonte unica deste goal).

    Mesma regra da lente do G156 (`test_citacao_norma_g156._modulos_fonte`):
    `*.py` direto do `galpao_fw`, excluindo `test_*` e `varredura_*`. O
    test_05 prova a equivalencia no repo real; censo e checagem usam so este
    predicado (nunca uma segunda lista - armadilha G131).
    """
    return (nome.endswith(".py")
            and not nome.startswith("test_")
            and not nome.startswith("varredura_"))


def _git(repo, *args):
    r = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True,
                       text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("git %s falhou em %s: %s"
                           % (" ".join(args), repo, r.stderr))
    return r.stdout


def censo_de_git(repo=None, base=None):
    """Censo: {hash_cheio: [arquivos de producao]} da base ate o HEAD.

    A mesma funcao serve o repo real e os repos de injecao em tmp_path (sem
    caminho especial para teste: o que a entrega declara e o que a conta usa
    e a mesma funcao - anti-padrao G131).
    """
    repo = REPO if repo is None else str(repo)
    base = COMMIT_BASE_G149 if base is None else base
    todos = [ln.strip() for ln in
             _git(repo, "log", "--format=%H", "HEAD").splitlines()
             if ln.strip()]
    if base not in todos:
        raise RuntimeError("base %s fora do HEAD em %s" % (base[:7], repo))
    hashes = todos[:todos.index(base) + 1]
    censo = {}
    for h in hashes:
        nomes = [ln.strip() for ln in
                 _git(repo, "show", "--name-only", "--format=", h).splitlines()
                 if ln.strip()]
        prod = sorted({p.split("framework/galpao_fw/")[-1]
                       for p in nomes
                       if p.startswith("framework/galpao_fw/")
                       and "/" not in p.split("framework/galpao_fw/")[-1]
                       and _e_arquivo_producao(
                           p.split("framework/galpao_fw/")[-1])})
        if prod:
            censo[h] = prod
    return censo


def confere_censo(censo, cobertura=None, isencoes=None, texto_decisions=""):
    """Guarda G159 em forma pura: cada commit do censo esta coberto ou isento.

    Devolve a lista de gaps (vazia = verde); cada gap nomeia commit e arquivo.
    O censo vem do git e a cobertura deste arquivo (fontes independentes -
    anti-tautologia G91).
    """
    cobertura = COBERTURA_COMMIT_D if cobertura is None else cobertura
    isencoes = ISENCOES_COMMIT if isencoes is None else isencoes
    headers_d = set(PAT_HEADER_D.findall(texto_decisions or ""))
    gaps = []

    for commit in sorted(censo):
        curto = commit[:7]
        if commit not in cobertura and commit not in isencoes:
            for arq in censo[commit]:
                gaps.append("%s: toca producao (%s) sem verbete nem isencao "
                            "(commit sem cobertura)" % (curto, arq))
        if commit in isencoes and not (isencoes[commit] or "").strip():
            gaps.append("%s: isencao sem motivo (padrao G98: isencao com "
                        "motivo, nunca renomear)" % curto)
        if commit in cobertura and cobertura[commit] not in headers_d:
            gaps.append("%s: cobertura '%s' sem '## %s' em "
                        "wiki/04-decisions.md (D tem de existir)"
                        % (curto, cobertura[commit], cobertura[commit]))

    for commit in sorted(set(cobertura) | set(isencoes)):
        if commit not in censo:
            gaps.append("%s: cobertura de commit inexistente no censo "
                        "(verbete de commit inexistente)" % commit[:7])

    return gaps


def _repo_git_tmp(tmp_path, arquivos_por_commit):
    """Repo git de verdade em tmp_path: [(arquivo, conteudo)] por commit."""
    _git(str(tmp_path), "init", "-q")
    _git(str(tmp_path), "config", "user.email", "g159@invalido")
    _git(str(tmp_path), "config", "user.name", "G159")
    _git(str(tmp_path), "config", "commit.gpgsign", "false")
    for i, arquivos in enumerate(arquivos_por_commit):
        for nome, conteudo in arquivos:
            p = tmp_path / nome
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(conteudo, encoding="utf-8")
            _git(str(tmp_path), "add", nome)
        _git(str(tmp_path), "-c", "user.email=g159@invalido",
             "-c", "user.name=G159", "commit", "-qm", "c%d" % i)
    base = _git(str(tmp_path), "rev-list", "--max-parents=0",
                "HEAD").splitlines()[0].strip()
    return base


def test_01_baseline_verde_e_censo_real_no_repo():
    """O repo real: o censo lista os 16 commits que tocaram producao desde o
    G149, cada um coberto (verbete) ou isento com motivo - e nada mais."""
    censo = censo_de_git()
    with open(DECISIONS, encoding="utf-8") as fh:
        dec = fh.read()
    gaps = confere_censo(censo, texto_decisions=dec)
    lados = ["baseline G159 reprova: %s" % g for g in gaps]
    esperado = set(COBERTURA_COMMIT_D) | set(ISENCOES_COMMIT)
    if set(censo) != esperado:
        lados.append("censo divergente: faltam=%r sobram=%r"
                     % (sorted(esperado - set(censo)),
                        sorted(set(censo) - esperado)))
    if len(censo) != 16:
        lados.append("censo=%d, esperado 16 (7 goals + 1 auditoria + 4 WKI "
                     "+ 4 do plano de 2026-10-08)"
                     % len(censo))
    curtos = {h[:7] for h in censo}
    if not {"dc686af", "700afd8", "6734fc8", "a85bdbe"} <= curtos:
        lados.append("os 4 commits WKI nao estao no censo: %r"
                     % sorted(curtos))
    assert not lados, "censo de producao G159:\n" + "\n".join(lados)


def test_02_sentido_1_vermelho_por_injecao(tmp_path):
    """Commit que toca producao sem cobertura reprova nomeando commit e
    arquivo - e o mesmo commit coberto passa (sem falso-positivo)."""
    base = _repo_git_tmp(tmp_path, [
        [("framework/galpao_fw/mod_a.py", "X = 1\n")],
        [("framework/galpao_fw/mod_a.py", "X = 2\n")],
    ])
    censo = censo_de_git(repo=tmp_path, base=base)
    p_dec = tmp_path / "04-decisions.md"
    p_dec.write_text("## D990 - G990: injetado\n", encoding="utf-8")
    dec = p_dec.read_text(encoding="utf-8")
    lados = []
    gaps_nu = confere_censo(censo, cobertura={}, isencoes={}, texto_decisions=dec)
    novos = [h for h in censo if h != base]
    if len(novos) != 1 or not [
            g for g in gaps_nu
            if novos[0][:7] in g and "mod_a.py" in g and "sem cobertura" in g]:
        lados.append("commit sem cobertura nao acusou commit+arquivo: %r / %r"
                     % (gaps_nu, censo))
    gaps_ok = confere_censo(censo, cobertura={base: "D990", novos[0]: "D990"},
                            isencoes={}, texto_decisions=dec)
    if gaps_ok:
        lados.append("commit coberto acusou (falso-positivo): %r" % (gaps_ok,))
    assert not lados, "sentido 1 G159:\n" + "\n".join(lados)


def test_03_isencao_sem_motivo_reprova(tmp_path):
    """Isencao sem motivo reprova; com motivo medido passa."""
    base = _repo_git_tmp(tmp_path, [
        [("framework/galpao_fw/mod_b.py", "Y = 1\n")],
    ])
    censo = censo_de_git(repo=tmp_path, base=base)
    lados = []
    gaps_vazia = confere_censo(censo, cobertura={}, isencoes={base: "  "},
                               texto_decisions="")
    if not [g for g in gaps_vazia if base[:7] in g and "sem motivo" in g]:
        lados.append("isencao sem motivo nao acusou: %r" % (gaps_vazia,))
    gaps_cheia = confere_censo(
        censo, cobertura={},
        isencoes={base: "auditoria injetada, motivo medido em tmp_path"},
        texto_decisions="")
    if gaps_cheia:
        lados.append("isencao com motivo acusou (falso-positivo): %r"
                     % (gaps_cheia,))
    assert not lados, "isencao G159:\n" + "\n".join(lados)


def test_04_sentido_2_cobertura_fantasma_reprova(tmp_path):
    """Cobertura/isencao de commit fora do censo reprova (verbete de commit
    inexistente) - e D sem header reprova."""
    base = _repo_git_tmp(tmp_path, [
        [("framework/galpao_fw/mod_c.py", "Z = 1\n")],
    ])
    censo = censo_de_git(repo=tmp_path, base=base)
    p_dec = tmp_path / "04-decisions.md"
    p_dec.write_text("## D991 - G991: injetado\n", encoding="utf-8")
    dec = p_dec.read_text(encoding="utf-8")
    lados = []
    fantasma = "0123456789abcdef0123456789abcdef01234567"
    gaps_f = confere_censo(censo, cobertura={fantasma: "D991"}, isencoes={},
                           texto_decisions=dec)
    if not [g for g in gaps_f if fantasma[:7] in g and "inexistente" in g]:
        lados.append("cobertura fantasma nao acusou: %r" % (gaps_f,))
    gaps_d = confere_censo(censo, cobertura={base: "D992"}, isencoes={},
                           texto_decisions=dec)
    if not [g for g in gaps_d if base[:7] in g and "D992" in g]:
        lados.append("D sem header nao acusou: %r" % (gaps_d,))
    assert not lados, "sentido 2 G159:\n" + "\n".join(lados)


def test_05_fonte_unica_casa_com_g156_e_wki_e_producao():
    """A definicao de producao e uma so: o predicado casa com `_modulos_fonte`
    do G156 no repo real - e os 3 arquivos WKI sao producao (as listas de
    emissores G145/G150 nao os veem: e por isso o censo nao podia usa-las)."""
    vivos = sorted(p for p in os.listdir(GALPAO)
                   if os.path.isfile(os.path.join(GALPAO, p))
                   and _e_arquivo_producao(p))
    lados = []
    if vivos != sorted(g156._modulos_fonte()):
        lados.append("predicado diverge de test_citacao_norma_g156 "
                     "(fonte unica quebrada)")
    for arq in ("demanda_residencial_enel.py", "residencial_eletrica.py",
                "desenho_eletrico_residencial.py"):
        if not _e_arquivo_producao(arq):
            lados.append("%s devia ser producao" % arq)
        if arq in vff.ALVOS or arq in vff.ALVOS_GET:
            lados.append("%s esta nos emissores G145/G150 (nao devia)" % arq)
    assert not lados, "fonte unica G159:\n" + "\n".join(lados)
