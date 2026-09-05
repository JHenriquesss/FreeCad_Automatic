# ============================================================================
# varredura_faixa_validade.py - G51: A FAIXA DE VALIDADE DECLARADA VIRA GUARDA.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_faixa_validade.py) e pelo teste-guarda
# tests/test_varredura_faixa_validade_g51.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_descoberta.
#
# Motivacao (G51): terceira vez que a mesma assinatura paga (lambda<=90 no G3,
# C50 no G49/G50): o limite do metodo esta no comentario, o autor sabia, e nao
# virou if. A maquina de AST e a do G48 (varredura_descoberta): percorre as
# funcoes, casa comentarios/docstrings que declaram faixa de validade com a
# funcao onde moram, e classifica em tres baldes:
#   - guardada: existe comparacao contra aquele limite no corpo (ou min/max
#     que satura nele);
#   - desguardada: a grandeza e parametro da funcao e ninguem a compara ->
#     candidato a bug (so entra como correcao depois de MEDIDO, rigor G10);
#   - inverificavel: a grandeza nem e entrada da funcao (caso Wenner: a>>b
#     no cabecalho do modulo, b nao e parametro de resistividade_wenner) ->
#     nao e bug, mas tem de ser declarado, nao silenciado.
# O balde inverificavel e o que impede a ferramenta de virar um gerador de
# falso-positivo; sem ele a varredura vira ruido e e abandonada.
# ============================================================================
"""Varredura G51: faixa de validade declarada em comentario vira guarda."""

from __future__ import annotations

import ast
import pathlib
import re

GALPAO = pathlib.Path(__file__).resolve().parent

# Declaracao de faixa de validade: os vocabulos do G51 + intervalo numerico.
# So casa COMENTARIO/DOCSTRING (nunca codigo): _linhas_validade filtra.
# "faixa" sozinha nao casa (faixa tributaria, faixa de 1 m); exige o
# qualificador de validade/calibracao - sem isso a varredura vira ruido.
VALIDADE_RE = re.compile(
    r"s[o\xf3] vale"                       # so vale / só vale
    r"|v[áa]lid[oa]s?\s+(para|at[ée]|quando|se|em)"  # valido para/ate
    r"|restrito\s+a"
    r"|limitad[oa]s?\s+a"
    r"|no\s+intervalo"
    # "entre X e Y" so conta com numeros nos dois lados (entre 0,15 e 2,0):
    # sem isso, "fronteira entre A e B" / "menor entre X e Y" viram ruido.
    r"|entre\s+[\d.,°]+\s+e\s+[\-\d.,°]+"
    r"|arbitrado\s+em"
    r"|faixa\s+de\s+validade|faixa\s+calibrada|foge\s+da\s+faixa"
    r"|fck\s*<=|C55[\u2013\-]C90|\(fck<=|<= ?50|\(G49\)",
    re.I,
)

# Intervalo numerico explicito (30..45, [0,35 ; 0,76]) conta como
# declaracao mesmo sem vocabulo: e a forma curta de dizer a faixa.
# Nao casa ref de equacao (5.4-13..5.4-21: o ".." ali e' numero de
# formula, nao faixa de validade) nem interpolacao (3/2..2).
INTERVALO_RE = re.compile(
    r"(?<![\d.\-/])\d+\s*(?:\.\.|\u2026)\s*\d+(?![\d]|\.\d)"
    r"|\[\s*[\d.,]+\s*;\s*[\d.,]+\s*\]")

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")

_SUFIXOS = ("_mpa", "_deg", "_mm", "_m2", "_cm", "_m", "_k", "_sd")


def _base(nome):
    n = nome.lower()
    for s in _SUFIXOS:
        if n.endswith(s):
            n = n[: -len(s)]
            break
    return n


def _numeros(texto):
    vals = []
    for m in NUM_RE.finditer(texto.replace(",", ".")):
        try:
            vals.append(float(m.group(0)))
        except ValueError:
            pass
    if re.search(r"C55[\u2013\-]C90", texto):
        # "C55-C90" diz a faixa alta: o limiar que a separa e' 50, mesmo
        # quando a linha nao o escreve (ex. docstring do ramo alto). Sem
        # isso, `if fck <= 50` no corpo nunca casaria com a linha do C55-C90.
        vals.append(50.0)
    return vals


def _e_declaracao(linha):
    return bool(VALIDADE_RE.search(linha) or INTERVALO_RE.search(linha))


def _parametro_na_linha(params, linha):
    """A grandeza declarada e entrada da funcao? Casa por base (theta_deg~theta,
    fck_MPa~fck).     Nomes curtos (a, b, K) casam CASE-SENSITIVE por palavra
    inteira (licao do G43: re.I casava N_ com n_cond); longos, insensitive.
    Casa o MAIS LONGO primeiro: na linha "W = ... ; zona = ... (0..4)" o
    W (1 letra) nao pode roubar a declaracao da zona. Desempate final por
    PROXIMIDADE ao primeiro numero: a grandeza rangida mora ao lado da
    faixa ("zona = zona sismica (0..4)" -> zona, nao pesos_niveis)."""
    cand = []
    for p in params:
        b = _base(p)
        if len(b) <= 2:
            # Curto e case-sensitive (A != a): sem isso o "a >> b" do Wenner
            # casa com o A de resistencia_malha(rho, A, L).
            if re.search(r"\b%s\b" % re.escape(p), linha):
                cand.append(p)
            continue
        if b in linha.lower() or p.lower() in linha.lower():
            cand.append(p)
    if not cand:
        return None
    if len(cand) == 1:
        return cand[0]
    # A grandeza rangida PRECEDE a faixa em prosa ("zona ... (0..4)"):
    # prefere o candidato mais proximo ANTES do intervalo/numero; so sem
    # ninguem antes vale o mais proximo depois. Sem isso, em
    # "zona = zona sismica (0..4) ; classe = ..." o casador pegava "classe".
    m = INTERVALO_RE.search(linha)
    if m is None:
        m = NUM_RE.search(linha.replace(",", "."))
    if m is None:
        return max(cand, key=len)
    pos = m.start()
    low = linha.lower()

    def _occs(p):
        return [mm.start() for mm in re.finditer(re.escape(_base(p)), low)]

    antes = [(p, max((o for o in _occs(p) if o <= pos), default=None))
             for p in cand]
    antes = [(p, o) for p, o in antes if o is not None]
    if antes:
        return max(antes, key=lambda t: t[1])[0]
    return min(cand, key=lambda p: min(_occs(p)))


_COMP_OP_RE = re.compile(r"([A-Za-z_][\w.]*)\s*(>>|<<|<=|>=|<|>)\s*([A-Za-z_][\w./]*)")


def _grandezas_externas(linha, params):
    """Nomes do outro lado da comparacao que NAO sao entrada (caso Wenner:
    'valido para a >> b' com b fora da assinatura). Curto: case-sensitive."""
    bases = {_base(p) for p in params} | set(params)
    externas = []
    for a, _op, c in _COMP_OP_RE.findall(linha):
        for nome in (a, c.split("/")[0]):
            nb = nome.strip()
            if not nb or nb.replace(".", "").replace("/", "").isdigit():
                continue
            if len(nb) <= 2:
                if nb not in params and nb not in bases:
                    externas.append(nb)
            elif _base(nb) not in {_base(p) for p in params}:
                externas.append(nb)
    return sorted(set(externas))


def _aliases(no_func, param, base):
    """Locais derivados do parametro (fck_MPa = fck/1000): guarda neles vale
    como guarda do parametro. Sem isso, 'if fck_MPa <= 50' (G49/G50) viraria
    desguardada embora guarde fck."""
    der = set()
    for no in ast.walk(no_func):
        if isinstance(no, (ast.Assign, ast.AnnAssign)):
            tgts = no.targets if isinstance(no, ast.Assign) else [no.target]
            val = no.value
            rhs = {n.id for n in ast.walk(val)
                   if isinstance(n, ast.Name)}
            if param in rhs or base in rhs:
                for t in tgts:
                    for n in ast.walk(t):
                        if (isinstance(n, ast.Name)
                                and isinstance(n.ctx, ast.Store)):
                            der.add(n.id)
    return der


def _constantes_modulo(arvore):
    """Nome -> valor para atribuicoes numericas de topo (THETA_MIN = 30.0).
    A guarda idiomatica compara contra a constante nomeada, nao contra o
    literal: sem resolver o nome, toda guarda bem escrita viraria
    'desguardada' (foi o que quase aconteceu com o proprio fix do G51)."""
    consts = {}
    for no in arvore.body:
        if isinstance(no, (ast.Assign, ast.AnnAssign)):
            tgts = (no.targets if isinstance(no, ast.Assign) else [no.target])
            val = no.value
            if (isinstance(val, ast.Constant)
                    and isinstance(val.value, (int, float))):
                for t in tgts:
                    if isinstance(t, ast.Name):
                        consts[t.id] = float(val.value)
    return consts


def _comparados_com_param(no_func, param, consts_mod=None):
    """Constantes comparadas contra o parametro no corpo (Compare) + alvos de
    min/max que o saturam. Inclui locais derivados (fck_MPa de fck) e
    constantes nomeadas do modulo (THETA_MIN). Retorna a lista de constantes."""
    consts = []
    base = _base(param)
    nomes = {param, base} | _aliases(no_func, param, base)
    consts_mod = consts_mod or {}
    for no in ast.walk(no_func):
        if isinstance(no, ast.Compare):
            envolvidos = {n.id for n in ast.walk(no)
                          if isinstance(n, ast.Name)}
            if envolvidos & nomes:
                for comp in [no.left] + list(no.comparators):
                    for n in ast.walk(comp):
                        if isinstance(n, ast.Constant) and isinstance(
                                n.value, (int, float)):
                            consts.append(float(n.value))
                        elif (isinstance(n, ast.Name)
                                and n.id in consts_mod):
                            consts.append(consts_mod[n.id])
        elif isinstance(no, ast.Call):
            fn = no.func
            fname = (fn.id if isinstance(fn, ast.Name)
                     else (fn.attr if isinstance(fn, ast.Attribute) else ""))
            if fname in ("min", "max"):
                args_nomes = {n.id for n in ast.walk(no)
                              if isinstance(n, ast.Name)}
                if args_nomes & nomes:
                    for a in no.args:
                        if (isinstance(a, ast.Constant)
                                and isinstance(a.value, (int, float))):
                            consts.append(float(a.value))
                        elif (isinstance(a, ast.Name)
                                and a.id in consts_mod):
                            consts.append(consts_mod[a.id])
    return consts


def _tem_guarda(no_func, param, numeros_decl, consts_mod=None):
    """Ha comparacao do parametro contra (aprox.) o limite declarado? Se a
    declaracao nao traz numero (ex. 'restrito a pilar'), qualquer comparacao
    do parametro conta; se traz, exige constante proxima (tolerancia 2%)."""
    consts = _comparados_com_param(no_func, param, consts_mod)
    if not consts:
        return False, []
    if not numeros_decl:
        return True, consts
    for c in consts:
        for d in numeros_decl:
            if abs(d) < 1e-12:
                if abs(c) < 1e-12:
                    return True, consts
            elif abs(c - d) <= max(0.02 * abs(d), 1e-9):
                return True, consts
    return False, consts


def _funcoes_da_arvore(arvore):
    return [n for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef)]


def _linhas_validade(caminho, arvore):
    """Linhas que declaram faixa em COMENTARIO ou DOCSTRING: [(n, texto)].

    Codigo nunca conta (ex. 'if fck_MPa <= 50' e a guarda, nao a declaracao):
    sem esse filtro, a propria guarda viraria 'candidata' e a varredura
    viraria ruido. Docstrings entram com o numero da linha do `def`."""
    try:
        texto = caminho.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [], []
    linhas = texto.splitlines()
    doc_linhas = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(no, clean=False)
            if doc:
                for sub in doc.splitlines():
                    s = sub.strip()
                    if s and _e_declaracao(s):
                        if isinstance(no, ast.Module):
                            doc_linhas.add((1, s[:220]))
                        else:
                            doc_linhas.add((no.lineno, s[:220]))
    achadas = list(doc_linhas)
    for i, ln in enumerate(linhas):
        s = ln.strip()
        if s.startswith("#") and _e_declaracao(ln):
            achadas.append((i + 1, s[:220]))
    # comentarios trailing (codigo + # limite): a parte comentario conta
    for i, ln in enumerate(linhas):
        if "#" in ln and not ln.strip().startswith("#"):
            parte = ln.split("#", 1)[1]
            if _e_declaracao(parte):
                achadas.append((i + 1, ("# " + parte.strip())[:220]))
    achadas.sort()
    return linhas, achadas


def _classifica(dona, texto, numeros, arquivo, consts_mod=None):
    params = [a.arg for a in dona.args.args
              if a.arg not in ("self", "cls")]
    casado = _parametro_na_linha(params, texto)
    if casado is None:
        return {"arquivo": arquivo, "funcao": dona.name,
                "parametro": None, "numeros": numeros,
                "balde": "inverificavel",
                "motivo": "grandeza declarada nao e parametro de %s(%s)"
                          % (dona.name, ",".join(params[:6]))}
    # Caso Wenner: a condicao envolve grandeza fora da assinatura
    # (a>>b com b ausente) -> inverificavel, nao bug. Declarar, nao silenciar.
    ext = _grandezas_externas(texto, params)
    if ext:
        return {"arquivo": arquivo, "funcao": dona.name,
                "parametro": casado, "numeros": numeros,
                "balde": "inverificavel",
                "motivo": "%s fora da assinatura de %s(%s): condicao %r" % (
                    ",".join(ext), dona.name, ",".join(params[:6]),
                    texto[:90])}
    ok, consts = _tem_guarda(dona, casado, numeros, consts_mod)
    if ok:
        return {"arquivo": arquivo, "funcao": dona.name,
                "parametro": casado, "numeros": numeros,
                "balde": "guardada",
                "motivo": "compara %s contra %r" % (casado, consts[:4])}
    return {"arquivo": arquivo, "funcao": dona.name,
            "parametro": casado, "numeros": numeros,
            "balde": "desguardada",
            "motivo": "parametro %s sem comparacao contra %r no corpo"
                      % (casado, numeros)}


def varredura(raiz=None):
    """Toda declaracao de faixa casada com a funcao dona e classificada.

    [{arquivo, funcao|None, linha, declaracao, parametro|None, numeros,
      balde, motivo}]. Ordem estavel por (arquivo, linha).

    `raiz` (G51-rev): diretorio a varrer, default o proprio galpao_fw. Existe
    para o teste-guarda provar o VERMELHO num diretorio temporario, em vez de
    escrever um modulo falso dentro do repo vivo (licao do D81: teste que muta
    o repo)."""
    achados = []
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "varredura_faixa_validade.py":
            continue
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        funcoes = _funcoes_da_arvore(arvore)
        consts_mod = _constantes_modulo(arvore)
        try:
            linhas, decls = _linhas_validade(caminho, arvore)
        except (OSError, UnicodeError):
            continue
        for nlinha, texto in decls:
            # funcao dona: a de menor escopo que contem a linha
            dona = None
            for f in funcoes:
                fim = getattr(f, "end_lineno", f.lineno)
                if f.lineno <= nlinha <= fim:
                    if dona is None or f.lineno >= dona.lineno:
                        dona = f
            numeros = _numeros(texto)
            if dona is None:
                # cabecalho do modulo: resolve para as funcoes cujos
                # parametros casam a grandeza (ex. theta do header ->
                # verifica_torcao(theta_deg)). Sem isso o gap do G51
                # (declarado no header, pago na funcao) seria "inverificavel"
                # e a ferramenta perderia exatamente o que a motivou.
                alvos = [f for f in funcoes
                         if _parametro_na_linha(
                             [a.arg for a in f.args.args
                              if a.arg not in ("self", "cls")], texto)]
                if not alvos:
                    achados.append({
                        "arquivo": caminho.name, "funcao": None,
                        "linha": nlinha, "declaracao": texto[:220],
                        "parametro": None, "numeros": numeros,
                        "balde": "inverificavel",
                        "motivo": "declaracao em escopo de modulo, sem funcao dona",
                    })
                    continue
                for f in alvos:
                    r = _classifica(f, texto, numeros, caminho.name,
                                    consts_mod)
                    r["linha"] = nlinha
                    r["declaracao"] = texto[:220]
                    if r["balde"] != "inverificavel":
                        r["motivo"] = ("cabecalho do modulo -> %s: "
                                       % f.name) + r["motivo"]
                    achados.append(r)
                continue
            r = _classifica(dona, texto, numeros, caminho.name, consts_mod)
            r["linha"] = nlinha
            r["declaracao"] = texto[:220]
            achados.append(r)
    achados.sort(key=lambda d: (d["arquivo"], d["linha"]))
    return achados


def chaves_varridas(raiz=None):
    return sorted((d["arquivo"], d["funcao"] or "<modulo>", d["linha"])
                  for d in varredura(raiz))


# ---------------------------------------------------------------------------
# BASELINE (G51-rev). A varredura nao pode crescer sozinha - mesma regra do
# G33 (varredura_nao_verificados) e do G40/G42/G43/G48. Sem isto a ferramenta
# e' RELATORIO, nao guarda: uma faixa nova declarada e nao guardada cai no meio
# das desguardadas ja triadas e a suite fica verde (medido na revisao do G51).
#
# A chave e' (arquivo, declaracao[:70]) e NAO inclui a linha: linha muda a cada
# edicao e o baseline viraria ruido. Tambem nao inclui a funcao: uma so linha de
# cabecalho rende ate 14 registros por fan-out (pilar_concreto:36/41/42) - o que
# se declara e' a DECLARACAO, nao cada funcao que ela alcanca. 106 declaracoes
# distintas hoje, 21 com alguma desguardada.
#
# Entrada nova aqui = ou vira guarda (if que compara), ou entra declarada com o
# motivo pelo qual NAO e' bug. Os motivos de cada uma estao medidos nos
# test_06* de tests/test_varredura_faixa_validade_g51.py.
# ---------------------------------------------------------------------------
DESGUARDADAS_TRIADAS = [   (   'cargas_nbr6120.py',
        'a lista de chaves validas se o ambiente nao existir - NUNCA '
        'devolve um'),
    (   'desempenho_nbr15575.py',
        '# edificio deve ser limitado a H_total/500 ou 3 cm, '
        'respeitando-se o M'),
    (   'escada_concreto.py',
        'p = blondel - 2e. Gate: piso fora de [0,25 ; 0,32] m reprova em '
        'vez de'),
    (   'estabilidade_edificio.py',
        'theta_1 = 1/(100 raiz(H)), limitado a [1/300, 1/200];'),
    (   'fundacao_sapata.py',
        '#   - 17.2.2  : bloco retangular de tensoes; fck<=50 MPa -> '
        'lambda=0,8'),
    (   'fundacao_sapata.py',
        'fck<=50: lambda=0,80 alpha_c=0,85 xd_lim=0,45 ; C55-C90: '
        'lambda/alpha_'),
    (   'iluminacao_externa_nbr5101.py',
        'Espacamento entre postes S = k*H (m), limitado a [3H, 5H].'),
    (   'incendio_edificio.py',
        '# nota e) da Tab.11: escadas externas limitadas a edificios de '
        'ate 45 '),
    (   'nbr8400.py',
        'e Psi_min da Tabela 12 pela classe de elevacao HC1..HC4. Vh '
        '(m/s) limi'),
    (   'perdas_protensao_nbr6118.py',
        '# Valores tipicos (Tab.A.1, ao ar livre ~70% UR): phi 1,5..2,5 '
        '; retra'),
    (   'pilar_concreto.py',
        '# --- diagrama de deformacoes (fck <= 50 MPa), NBR 6118 8.2.10 '
        '/ 17.2.'),
    (   'pilar_concreto.py',
        '# consumidores e o comentario "(fck<=50)" a fazia parecer '
        'valida em C5'),
    (   'pilar_concreto.py',
        '# tensao do bloco = 0,85*fcd, 17.2.2 (fck<=50)'),
    (   'premoldado_nbr9062.py',
        '# tensao da armadura longitudinal limitada a 0,50 fyk '
        '(5.3.2.2)'),
    (   'pycufsm_compat.py',
        '# Escopo restrito a esses 2 modulos (nao mexe no numpy global). '
        'Idempo'),
    (   'secundarios_nbr8800.py',
        'e valida se o tapamento (telha parafusada) TRAVAR O GIRO da '
        'secao; sen'),
    (   'sismo_nbr15421.py',
        '#     normalizada, em fracao de g). Zona 0..4.'),
    (   'sismo_nbr15421.py',
        '# (interpolar linear entre 0,10 e 0,15). Classe F exige estudo '
        'especif'),
    (   'subestacao_nbr14039.py',
        '#      Fusivel HH: Inf ~ 1,5*Inp -> proximo padrao. Rele 51 '
        '(tape): (1'),
    (   'subestacao_nbr14039.py',
        '# tape do 51: 1,20*Inp (faixa 1,15..1,30)'),
    (   'varredura_descoberta.py',
        '# um zero so vale depois do vermelho injetado naquela '
        'linguagem).')]


def chaves_desguardadas(raiz=None):
    """(arquivo, declaracao[:70]) das declaracoes com alguma desguardada."""
    return sorted({(d["arquivo"], d["declaracao"][:70])
                   for d in varredura(raiz) if d["balde"] == "desguardada"})


def relatorio_pt():
    linhas = ["VARREDURA G51 - FAIXA DE VALIDADE DECLARADA",
               "arquivo/funcao | balde | linha -> declaracao"]
    baldes = {"guardada": 0, "desguardada": 0, "inverificavel": 0}
    for d in varredura():
        baldes[d["balde"]] += 1
        fun = d["funcao"] or "<modulo>"
        linhas.append("  %-26s/%-28s | %-13s @%d :: %s" % (
            d["arquivo"], fun, d["balde"], d["linha"], d["declaracao"][:110]))
    linhas.append("  total=%d guardada=%d desguardada=%d inverificavel=%d" % (
        sum(baldes.values()), baldes["guardada"], baldes["desguardada"],
        baldes["inverificavel"]))
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print(relatorio_pt())
