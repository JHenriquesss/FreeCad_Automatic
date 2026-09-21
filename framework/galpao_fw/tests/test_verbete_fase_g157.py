"""G157 - o verbete sem numero e a fase sem linha (D187).

Defeito (o D176 e o D179 acharam lendo o arquivo): os verbetes do G149, do
G150, do G151 e do G152 fecharam com cabecalho `## G1xx` sem numero D (so o
G153 virou D178) e nenhum dos cinco goals escreveu em `wiki/03-phases.md`
(o D179 escreveu as linhas na auditoria). Nenhuma guarda cobria isso.

Guarda (neste arquivo, sem modulo novo na producao: nada do produto a
consome, e a lente do G156 mora no teste pelo mesmo motivo). Regra: todo
goal fechado no `git log` desde o G149 (incluindo G154-G157) tem verbete
COM numero D em `wiki/04-decisions.md` e bullet `- **G<num>**` com o link
`[[04-decisions#D...]]` em `wiki/03-phases.md`.

Baseline nos dois sentidos (convencao 1), via MAPA_GOAL_D:
- sentido 1: goal no git log sem entrada no MAPA, ou sem `## D - G` no
  decisions, ou sem bullet+link na fase, reprova;
- sentido 2: entrada no MAPA sem goal no git log (salvo o goal em
  progresso), verbete `## D - G<num>=149` fora do MAPA, header `## G<num>`
  sem D, ou link do bullet sem `## D` no decisions, reprova.
Injecao em tmp_path (convencao 2), nunca mutando o repo: os testes copiam
os arquivos reais para tmp_path e injetam cada defeito. Acusa por parte
(convencao 7/G125): cada gap nomeia o goal/D. Um assert por teste (G97).

Contrato de manutencao (o goal seguinte atualiza os tres juntos, no mesmo
commit): MAPA_GOAL_D ganha a entrada do goal novo, o verbete `## D - G`
entra no decisions, o bullet com o link entra no phases, e GOAL_CORRENTE
avanca. Goal futuro com commit e sem entrada no MAPA reprova (sentido 1).
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
REPO = os.path.dirname(os.path.dirname(GALPAO))

DECISIONS = os.path.join(GALPAO, "wiki", "04-decisions.md")
PHASES = os.path.join(GALPAO, "wiki", "03-phases.md")

#: Goals cobertos pela guarda (o arco que fechou sem numero D + o atual).
GOAL_MINIMO = 149

#: Goal corrente: entra no git log no commit deste arquivo, ate la vai em
#: `em_progresso` no test_01 (o resto da checagem - verbete+linha - ja vale
#: para ele; o test_03 prova que o carve-out so libera este goal).
#: (G159: avancado pelo contrato de manutencao - MAPA ganha a entrada nova,
#: GOAL_CORRENTE avanca - sem mudar nenhuma regra de conteudo.)
#: (G160: idem - MAPA ganha G160/D189, GOAL_CORRENTE avanca.)
GOAL_CORRENTE = "G160"

#: Baseline nos dois sentidos: goal -> D do verbete. Os quatro verbetes sem
#: D ganharam os proximos D livres depois do ultimo D existente no momento
#: do G157 (D182), na ordem G149, G150, G151, G152 (decisao do usuario no
#: topo do backlog G154-G157); o G157 ganha o D187; o G159 ganha o D188;
#: o G160 ganha o D189
#: (contrato de manutencao: o goal seguinte atualiza os tres juntos).
MAPA_GOAL_D = {
    "G149": "D183",
    "G150": "D184",
    "G151": "D185",
    "G152": "D186",
    "G153": "D178",
    "G154": "D180",
    "G155": "D181",
    "G156": "D182",
    "G157": "D187",
    "G159": "D188",
    "G160": "D189",
}

#: `## G149 - ...` (sem D) ou `## D183 - G149: ...` (numerado). A forma
#: `## D150/G124 - ...` (auditoria antiga, com barra) nunca casa aqui de
#: proposito: nao e verbete de goal simples e mora fora do arco G149+.
PAT_Verbete = re.compile(r"^## (?:(D\d+) - )?G(\d+)\b\s*[-:]")

#: Bullet de fase: `- **G149** ...` (o bloco vai ate o proximo bullet,
#: cabecalho ou linha em branco; continuacoes tem espaco na frente).
PAT_BULLET = re.compile(r"^- \*\*G(\d+)\*\*")

#: Header de verbete numerado: `## D183 ...` (alvo dos links da fase).
PAT_HEADER_D = re.compile(r"^## (D\d+)\b", re.M)

#: Linha de `git log --oneline` com commit de goal: `<hash> G149: ...`.
PAT_GOAL_NO_LOG = re.compile(r"^[0-9a-f]+ G(\d+):")


def _goals_no_git_log():
    """Goals com commit `G<num>:` no `git log` (conjunto de "G149", ...)."""
    r = subprocess.run(["git", "log", "--oneline"], cwd=REPO,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("git log falhou: %s" % r.stderr)
    goals = set()
    for linha in r.stdout.splitlines():
        m = PAT_GOAL_NO_LOG.match(linha.strip())
        if m:
            goals.add("G%s" % m.group(1))
    return goals


def _verbetes_de(texto_decisions):
    """Cabecalhos de goal no decisions: {goal: (D|None, linha)}. """
    verbetes = {}
    for linha in texto_decisions.splitlines():
        m = PAT_Verbete.match(linha)
        if m:
            verbetes["G%s" % m.group(2)] = (m.group(1), linha)
    return verbetes


def _bullets_fase_de(texto_phases):
    """Bullets `- **G<num>**` da fase: {goal: bloco_de_texto}."""
    bullets = {}
    atual = None
    for linha in texto_phases.splitlines():
        m = PAT_BULLET.match(linha)
        if m:
            atual = "G%s" % m.group(1)
            bullets[atual] = [linha]
        elif atual is not None:
            if (linha.startswith("- **") or linha.startswith("#")
                    or not linha.strip()):
                atual = None
            else:
                bullets[atual].append(linha)
    return {g: "\n".join(bloco) for g, bloco in bullets.items()}


def confere_verbete_fase(texto_decisions, texto_phases, goals_log,
                         mapa=None, em_progresso=()):
    """Guarda G157: cada goal fechado tem verbete com D e bullet com link.

    Devolve a lista de gaps (vazia = verde); cada gap nomeia o goal/D.
    """
    if mapa is None:
        mapa = MAPA_GOAL_D
    em_progresso = set(em_progresso)
    verbetes = _verbetes_de(texto_decisions)
    bullets = _bullets_fase_de(texto_phases)
    headers_d = set(PAT_HEADER_D.findall(texto_decisions))
    gaps = []

    for goal in sorted(goals_log):
        try:
            num = int(goal[1:])
        except (ValueError, IndexError):
            continue
        if num < GOAL_MINIMO:
            continue
        if goal not in mapa:
            gaps.append("%s: fechado no git log sem entrada no MAPA_GOAL_D "
                        "(goal sem verbete mapeado)" % goal)

    for goal in sorted(mapa):
        d = mapa[goal]
        if goal not in goals_log and goal not in em_progresso:
            gaps.append("%s: no MAPA como %s mas sem commit no git log "
                        "(mapeamento de goal inexistente)" % (goal, d))
        verbete = verbetes.get(goal)
        if verbete is None or verbete[0] != d:
            if verbete is not None and verbete[0] is None:
                gaps.append("%s: cabecalho '## %s' sem numero D em "
                            "wiki/04-decisions.md (esperado '## %s - %s')"
                            % (goal, goal, d, goal))
            else:
                gaps.append("%s: sem verbete '## %s - %s' em "
                            "wiki/04-decisions.md" % (goal, d, goal))
        bloco = bullets.get(goal)
        link = "[[04-decisions#%s]]" % d
        if bloco is None or link not in bloco:
            gaps.append("%s: sem bullet '- **%s**' com '%s' em "
                        "wiki/03-phases.md" % (goal, goal, link))
        for link_d in sorted(set(re.findall(r"\[\[04-decisions#(D\d+)\]\]",
                                            bloco or ""))):
            if link_d not in headers_d:
                gaps.append("%s: bullet linka '[[04-decisions#%s]]' mas "
                            "wiki/04-decisions.md nao tem '## %s' (link "
                            "quebrado)" % (goal, link_d, link_d))

    for goal in sorted(verbetes):
        try:
            num = int(goal[1:])
        except (ValueError, IndexError):
            continue
        if num < GOAL_MINIMO:
            continue
        if goal not in mapa:
            d, _titulo = verbetes[goal]
            gaps.append("%s: verbete '## %s' fora do MAPA_GOAL_D (verbete "
                        "de goal inexistente ou renumerado)" % (goal, d))

    return gaps


def _textos():
    with open(DECISIONS, encoding="utf-8") as fh:
        dec = fh.read()
    with open(PHASES, encoding="utf-8") as fh:
        ph = fh.read()
    return dec, ph


def _sem_bullet(texto, goal):
    """Copia do phases sem o bloco `- **G<num>**` (injetor do test_02)."""
    fora, pulando = [], False
    for linha in texto.splitlines():
        if PAT_BULLET.match(linha):
            pulando = ("**%s**" % goal) in linha
            if pulando:
                continue
        elif pulando and (linha.startswith("- **")
                          or linha.startswith("#") or not linha.strip()):
            pulando = False
        if pulando:
            continue
        fora.append(linha)
    return "\n".join(fora) + "\n"


def test_01_baseline_verde_no_repo():
    """Sentidos 1+2 no repo real: todo goal fechado tem verbete com D e
    bullet com link, e todo mapeado tem goal (o corrente, em progresso)."""
    dec, ph = _textos()
    gaps = confere_verbete_fase(dec, ph, _goals_no_git_log(),
                                em_progresso=(GOAL_CORRENTE,))
    lados = ["baseline G157 reprova: %s" % g for g in gaps]
    assert not lados, "guarda do verbete/fase:\n" + "\n".join(lados)


def test_02_sentido_1_vermelho_por_injecao(tmp_path):
    """Goal sem verbete com D / sem bullet com link reprova, nomeando o
    goal - e a copia limpa passa (sem falso-positivo do mecanismo)."""
    dec, ph = _textos()
    p_dec = tmp_path / "04-decisions.md"
    p_ph = tmp_path / "03-phases.md"
    p_dec.write_text(dec, encoding="utf-8")
    p_ph.write_text(ph, encoding="utf-8")
    log = _goals_no_git_log()
    lados = []

    sem_d = p_dec.read_text(encoding="utf-8").replace(
        "## D183 - G149:", "## G149:", 1)
    gaps_d = confere_verbete_fase(sem_d, ph, log,
                                  em_progresso=(GOAL_CORRENTE,))
    if not [g for g in gaps_d if "G149" in g and "sem numero D" in g]:
        lados.append("header '## G149' sem D nao acusou: %r" % (gaps_d,))

    sem_bullet = _sem_bullet(p_ph.read_text(encoding="utf-8"), "G150")
    gaps_b = confere_verbete_fase(dec, sem_bullet, log,
                                  em_progresso=(GOAL_CORRENTE,))
    if not [g for g in gaps_b if "G150" in g and "03-phases" in g]:
        lados.append("fase sem bullet da G150 nao acusou: %r" % (gaps_b,))

    gaps_limpa = confere_verbete_fase(
        p_dec.read_text(encoding="utf-8"), p_ph.read_text(encoding="utf-8"),
        log, em_progresso=(GOAL_CORRENTE,))
    if gaps_limpa:
        lados.append("copia limpa acusou (falso-positivo): %r"
                     % (gaps_limpa,))

    assert not lados, "sentido 1 G157:\n" + "\n".join(lados)


def test_03_sentido_2_vermelho_por_injecao(tmp_path):
    """Mapeamento sem goal, goal sem mapeamento, verbete orfao e link
    quebrado reprovam - e o carve-out so libera o goal corrente."""
    dec, ph = _textos()
    log = _goals_no_git_log()
    lados = []

    mapa_orfao = dict(MAPA_GOAL_D, G997="D997")
    gaps_m = confere_verbete_fase(dec, ph, log, mapa=mapa_orfao,
                                  em_progresso=(GOAL_CORRENTE,))
    if not [g for g in gaps_m if "G997" in g and "sem commit" in g]:
        lados.append("MAPA com goal inexistente nao acusou: %r" % (gaps_m,))

    gaps_g = confere_verbete_fase(dec, ph, log | {"G998"},
                                  em_progresso=(GOAL_CORRENTE,))
    if not [g for g in gaps_g if "G998" in g and "MAPA_GOAL_D" in g]:
        lados.append("goal sem mapeamento nao acusou: %r" % (gaps_g,))

    dec_orfa = dec + "\n## D999 - G998: verbete de goal inexistente " \
        "(injetado G157)\n"
    gaps_o = confere_verbete_fase(dec_orfa, ph, log,
                                  em_progresso=(GOAL_CORRENTE,))
    if not [g for g in gaps_o if "G998" in g and "fora do MAPA" in g]:
        lados.append("verbete orfao nao acusou: %r" % (gaps_o,))

    ph_quebrada = ph.replace("[[04-decisions#D178]]",
                             "[[04-decisions#D999]]", 1)
    gaps_q = confere_verbete_fase(dec, ph_quebrada, log,
                                  em_progresso=(GOAL_CORRENTE,))
    if not [g for g in gaps_q if "D999" in g and "link quebrado" in g]:
        lados.append("link quebrado nao acusou: %r" % (gaps_q,))

    sem = confere_verbete_fase(dec, ph, log, em_progresso=())
    com = confere_verbete_fase(dec, ph, log,
                               em_progresso=(GOAL_CORRENTE,))
    tem_sem = [g for g in sem if GOAL_CORRENTE in g and "sem commit" in g]
    tem_com = [g for g in com if GOAL_CORRENTE in g and "sem commit" in g]
    if GOAL_CORRENTE in log:
        if tem_sem or tem_com:
            lados.append("goal commitado ainda acusado: %r / %r"
                         % (sem, com))
    elif not tem_sem or tem_com:
        lados.append("carve-out do goal corrente furado: sem=%r com=%r"
                     % (sem, com))

    assert not lados, "sentido 2 G157:\n" + "\n".join(lados)
