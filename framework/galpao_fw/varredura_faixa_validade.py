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
#
# G64 - vocabulario de tabela (alvenaria_estrutural era invisivel: 0 chaves
# em 161/50). Cada termo novo entra com a contagem de falsos-positivos
# medida em ~19 mil linhas de comentario/docstring do galpao_fw, porque a
# lente foi deliberadamente estreita e cada alargamento custa ruido:
#   - "tetos? (da|de|do) Tab.": 5 ocorrencias, 0 FP (4 alvenaria + 1
#     estrutura_casa, o mesmo teto da Tab.9). "teto" sozinho tem 78
#     ocorrencias (forro arquitetonico, teto de ductilidade) e NAO entra.
#   - "patamar de fpk": 3 ocorrencias, 0 FP. "patamar" sozinho tem 26
#     (23 sao patamar de escada = descanso) e NAO entra.
#   - "fora dos? tabelados?": 1 ocorrencia, 0 FP.
#   - "a partir de <digito>": 1 ocorrencia, 0 FP. Sem o digito sao 42
#     ("a partir de um payload", "a partir de z0"...) e NAO entra.
#   - "acima do teto": 6 ocorrencias, 0 FP (4 alvenaria + estrutura_casa
#     no mesmo teto + pilar_concreto "teto de 6R", que devolve o teto e o
#     chamador reprova - guarda relevante, nao ruido).
# PROIBIDO (G64): reescrever comentario de modulo para agradar a esta
# expressao - a lente se adapta ao codigo, nunca o contrario.
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
    r"|fck\s*<=|C55[\u2013\-]C90|\(fck<=|<= ?50|\(G49\)"
    r"|tetos?\s+(da|de|do)\s+Tab\."      # G64: tetos da Tab.9 (5 hits, 0 FP)
    r"|patamar\s+de\s+fpk"               # G64: patamar de fpk (3 hits, 0 FP)
    r"|fora\s+dos?\s+tabelados?"         # G64: fora dos tabelados (1, 0 FP)
    r"|a\s+partir\s+de\s+\d"             # G64: a partir de 26 (1 hit, 0 FP)
    r"|acima\s+do\s+teto",               # G64: acima do teto (6 hits, 0 FP)
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
# se declara e' a DECLARACAO, nao cada funcao que ela alcanca. 124 declaracoes
# distintas hoje (G64: era 106), 27 com alguma desguardada (era 21).
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
        'linguagem).'),
    # G64 - alvenaria_estrutural sai da invisibilidade (0 chaves em 161/50
    # -> 37 chaves). O modulo esta GUARDADO (lambda acima do teto reprova,
    # patamar de fpk fora da Tab.1 recusa - medido nos test_06g/06h); o que
    # segue desguardado e fan-out do cabecalho para funcoes que DELEGAM a
    # guarda (modulo_deformacao, teto_esbeltez + `if lam > teto: reprova`),
    # a mesma fronteira de 1 nivel ja triada no pilar (test_06c). Cada uma
    # com o motivo medido pelo qual NAO e bug (rigor G10).
    (   'alvenaria_estrutural.py',
        '#     ceramicos 600 x fpk. Patamar de fpk fora dos tabelados recusa'),
    (   'alvenaria_estrutural.py',
        '#     concreto 800/750/700 x fpk por patamar de fpk; bloco e tijolo'),
    (   'alvenaria_estrutural.py',
        '#   - Esbeltez, 10.1.2: lambda = he / te. Tetos da Tab.9: 24 sem armad'),
    (   'alvenaria_estrutural.py',
        'R = [1-(lambda/40)^3] com lambda = he/te (10.1.2); teto da Tab.9'),
    (   'alvenaria_estrutural.py',
        'default; lambda acima do teto reprova; Qh avulsa recusa com motivo (a'),
    (   'alvenaria_estrutural.py',
        'no momento). Tracao: limitada a 10 % de fpk/gamma_m (C.1-f, leitura do'),]


def chaves_desguardadas(raiz=None):
    """(arquivo, declaracao[:70]) das declaracoes com alguma desguardada."""
    return sorted({(d["arquivo"], d["declaracao"][:70])
                   for d in varredura(raiz) if d["balde"] == "desguardada"})


# ---------------------------------------------------------------------------
# COBERTURA (G64, D87). A lente do G51 enxergava o que entrou depois dela:
# alvenaria_estrutural (vertical novo, cheio de faixas) produzia ZERO chaves
# e a suite ficava verde. Relatorio vira portao aqui: todo *.py do diretorio
# ou produz >= 1 chave na varredura, ou consta de SEM_FAIXA_DECLARADA com o
# motivo pelo qual zero chaves e o esperado. Modulo novo que nao esteja em
# nenhum dos dois deixa a suite vermelha (test_09*).
#
# "Sem faixa" e lido no nivel da LENTE: arquivos que declaram limites em
# vocabulario que a lente ainda nao cobre levam o prefixo DIVIDA-LENTE com
# a descricao do vocabulario cego - decisao explicita, nao silencio. Isencao
# com motivo apagado/vazio reprova; isencao de arquivo que passou a produzir
# chave reprova (nome morto, mesma regra do baseline); arquivo isento que
# some do disco reprova (pede a remocao da entrada junto).
# ---------------------------------------------------------------------------
SEM_FAIXA_DECLARADA = {
    "acos.py": "catalogo de acos (fy/fu); sem faixa declarada.",
    "alma_variavel.py": "gerador de secoes tapered; sem faixa no vocabulario da lente.",
    "armazenamento_nbr16981.py": "gate de dados (nao dimensiona); limites de contrato, nao faixa de metodo.",
    "bim_casa_residencial.py": "BIM/IFC sem formula; sem faixa.",
    "bim_edificio.py": "BIM/IFC sem formula; sem faixa.",
    "bim_eletrico_residencial.py": "BIM posiciona o ja dimensionado; sem faixa.",
    "bim_instalacoes_casa.py": "geometria no frame; 'teto' ali e forro arquitetonico (FP do teto generico).",
    "bim_instalacoes_edificio.py": "geometria no frame; sem faixa.",
    "build_concreto.py": "build 3D a partir do neutro calculado; sem faixa.",
    "build_eletrico.py": "build 3D a partir do neutro calculado; sem faixa.",
    "build_federado.py": "build federado; sem faixa.",
    "build_final.py": "script avulso de demo legada; sem faixa.",
    "builtin_adapters.py": "registro de adaptadores; sem faixa.",
    "caderno_encargos.py": "documento contratual; remete limites a norma, sem faixa propria.",
    "caderno_turnkey.py": "junta PDFs de pranchas; sem faixa.",
    "calhas.py": "DIVIDA-LENTE: 'H_max fora de faixa fisica' em vocabulario fora da lente.",
    "cargas_eletricas.py": "DIVIDA-LENTE: faixas de demanda por ocupacao/potencia (Tab.1.8) fora da lente.",
    "casa_residencial.py": "adaptador; faixas vivem nos modulos de calculo chamados.",
    "casa_residencial_sintetica.py": "fixture sintetica; nao calcula.",
    "check_nbr8800.py": "verificacao por estados-limite; sem faixa no vocabulario da lente.",
    "climatizacao_nbr16401.py": "DIVIDA-LENTE: limites de velocidade (Tab.1) e tabelas C.1/3.5 fora da lente.",
    "comissionamento_fv.py": "checklist de evidencias; sem faixa.",
    "compatibilizacao.py": "documento de coordenacao; 'limite duro' e de processo.",
    "condutores_nbr5410.py": "DIVIDA-LENTE: limites de queda de tensao e secoes minimas (Tab.30/47) fora da lente.",
    "console_ponte.py": "DIVIDA-LENTE: perna minima (Tab.9) e faixa de fadiga fora da lente.",
    "contencao_lateral.py": "verificacao NBR 8800; sem faixa no vocabulario da lente.",
    "contraventamento.py": "barras tracionadas; 'dispensada do limite' nao declara faixa.",
    "coordination_review.py": "contrato de revisao; sem faixa.",
    "cortante_tapered.py": "cortante de alma variavel; sem faixa declarada.",
    "cronograma.py": "cronograma/curva S; 'faixa' ali e area de desenho.",
    "curto_circuito.py": "limite matematico interno raiz(3); nao faixa de metodo.",
    "demanda_residencial_enel.py": "demanda por tabelas Enel; sem faixa no vocabulario da lente.",
    "demo_engenheiro.py": "script avulso de demonstracao; sem faixa.",
    "desenho_alvenaria.py": "prancha SVG; 'faixa de ajuste' e geometria de fiada.",
    "desenho_casa_residencial.py": "prancha SVG; sem faixa.",
    "desenho_climatizacao.py": "esquema SVG; sem faixa.",
    "desenho_coordenacao.py": "prancha de coordenacao; 'faixa p/ titulo' e layout.",
    "desenho_eletrico.py": "unifilar SVG; 'FAIXA DE CIRCUITOS' e legenda.",
    "desenho_eletrico_residencial.py": "prancha SVG; sem faixa.",
    "desenho_hidraulica.py": "esquema SVG; sem faixa.",
    "desenho_incendio.py": "planta AVCB; 'faixa lateral' e layout, 'teto' e posicao.",
    "desenho_pavimento.py": "planta de formas; sem faixa.",
    "desenho_piso.py": "planta de juntas; sem faixa.",
    "desenho_svg_base.py": "primitivas SVG; sem faixa.",
    "deteccao_alarme_nbr17240.py": "DIVIDA-LENTE: cobertura 81m2 (teto<=8m) e teto>8m em vocabulario 'teto' generico (ruido: 78 hits).",
    "dimensionamento_eletrico_residencial.py": "delega tabelas a condutores/protecao; sem faixa propria.",
    "distorcional_fsm.py": "'FAIXAS FINITAS' e nome de metodo numerico; sem faixa.",
    "dossie.py": "junta PDFs; sem faixa.",
    "edificio_adapter.py": "adaptador; menciona tetos da Tab.9 com quebra de linha (fora da lente); faixas vivem em alvenaria_estrutural.",
    "eletrica_edificio.py": "orquestra vertical; limites vivem nos modulos de calculo.",
    "empocamento_nbr8800.py": "'dispensado (limite inclusivo)' e criterio, nao faixa declarada.",
    "enrijecedor_painel.py": "enrijecedores de alma; sem faixa declarada.",
    "entrada_enel_bt.py": "transcricao de tabelas Enel; sem faixa no vocabulario da lente.",
    "entregaveis_projeto.py": "hooks de entrega; sem faixa.",
    "escopo.py": "envelope de escopo; sem faixa de metodo.",
    "esgoto_reuso.py": "reuso de tabelas NBR 17076:2024; sem faixa propria.",
    "estabilidade_b1b2.py": "DIVIDA-LENTE: 'Limite de validade do MAES (B2<=1.40)' em vocabulario fora da lente.",
    "estabilidade_global_nbr6118.py": "DIVIDA-LENTE: dispensa de 2a ordem (gamma_z) com 'valido' fora da lente.",
    "fator_potencia.py": "DIVIDA-LENTE: FP>=0,92 em vocabulario 'limite regulamentar' fora da lente.",
    "flt_misula.py": "DIVIDA-LENTE: tetos de M_Rd/Cb em vocabulario 'teto' generico fora da lente.",
    "fogo_nbr14323.py": "DIVIDA-LENTE: temperaturas-limite e carta de cobertura (Tab.6.13) fora da lente.",
    "fontes_externas_protocolo.py": "protocolo de fontes; sem faixa.",
    "forcas_localizadas.py": "DIVIDA-LENTE: faixa de Whitmore (12tw/25tw) sem qualificador de validade, fora da lente.",
    "fotovoltaico.py": "DIVIDA-LENTE: tetos de area/consumo em vocabulario generico fora da lente.",
    "frame2d.py": "solver de rigidez; sem faixa de metodo.",
    "framework.py": "ponto de entrada/versao; sem faixa.",
    "fundacao_edificio.py": "'M=0 na faixa de 1m' e hipotese de modelagem; sem faixa de validade.",
    "fundacao_sapata_corrida.py": "hipotese da faixa de 1m; verificacao delegada a fundacao_sapata.",
    "galpao_adapter.py": "adaptador nativo; sem faixa.",
    "galpao_climatizacao.py": "orquestra disciplina; limites vivem em climatizacao_nbr16401.",
    "galpao_eletrico.py": "orquestra BT; sem faixa propria.",
    "galpao_hidraulica.py": "orquestra e roteia; faixas vivem em hidraulica_predial.",
    "galpao_portico.py": "analise de portico; sem faixa no vocabulario da lente.",
    "galpao_seguranca_incendio.py": "orquestra vertical; sem faixa propria.",
    "galpao_turnkey.py": "orquestrador-mestre; sem faixa propria.",
    "geometria_membros.py": "primitiva geometrica (caixa); sem faixa.",
    "geotecnia_spt.py": "ponte SPT-tensao; fatores de forma, sem faixa declarada.",
    "gestao_casa.py": "camada de gestao; sem faixa.",
    "gestao_edificio.py": "camada de gestao; sem faixa.",
    "gusset_ligacao.py": "DIVIDA-LENTE: faixa de Whitmore fora da lente (como forcas_localizadas).",
    "hidrantes_nbr13714.py": "DIVIDA-LENTE: limiares de aplicabilidade (area>750m2, Tab.D.1/Tab.1) fora da lente.",
    "hidraulica_edificio.py": "DIVIDA-LENTE: teto de 400 kPa em vocabulario generico; calculo nas primitivas.",
    "hidraulica_predial.py": "DIVIDA-LENTE: tabelas UHC/DN/velocidade sem vocabulario de validade.",
    "hidraulica_residencial.py": "reuso de primitivas; faixas vivem em hidraulica_predial.",
    "ifc_emit.py": "emissor IFC; sem faixa.",
    "ifc_map.py": "mapa peca-IFC; sem faixa.",
    "iluminacao_emergencia_nbr10898.py": "DIVIDA-LENTE: limites absolutos (20m, 0,5m do teto) fora da lente.",
    "instalacao_eletrica.py": "DIVIDA-LENTE: faixas de secao e limites de circuito fora da lente.",
    "junta_dilatacao.py": "verificacao de necessidade; sem faixa declarada.",
    "layout_ambientes.py": "primitiva de retangulos; sem faixa.",
    "layout_eletrico_residencial.py": "contrato de layout; sem faixa.",
    "ligacoes.py": "verificacao de ligacoes; sem faixa declarada.",
    "luminotecnica_nbr8995.py": "DIVIDA-LENTE: faixas de eficiencia e Fu tabelado fora da lente.",
    "mao_francesa.py": "dimensionamento Anexo G; sem faixa declarada.",
    "mao_francesa_geom.py": "geometria pura; sem faixa.",
    "marcas_peca.py": "marcas de fabricacao; sem faixa.",
    "modelo_neutro.py": "dados de modelo; sem faixa.",
    "neve.py": "carga de neve EN 1991; sem faixa declarada.",
    "pacote_legal.py": "pacote documental; 'VALIDO/ENTREGAVEL' e de processo.",
    "perfis.py": "catalogo de perfis; sem faixa.",
    "plataforma.py": "DIVIDA-LENTE: limites de flecha L/350 e frequencia fora da lente.",
    "ponte_rolante.py": "DIVIDA-LENTE: faixas de fadiga (Anexo K) e tabelas fora da lente.",
    "populacao_nbr9077.py": "populacao exata sem arredondamento; sem faixa.",
    "project_io.py": "envelope de transporte; sem faixa.",
    "project_loop.py": "orquestrador; regras vivem nos calculadores.",
    "project_loop_cli.py": "CLI fina; sem faixa.",
    "project_source_gate.py": "gate de fontes; sem faixa de metodo.",
    "projeto_spec.py": "contrato de dados; validacao de entrada nao e faixa de metodo.",
    "props_I_mono.py": "DIVIDA-LENTE: razao em faixa (0.5,0.7) fora da lente (INTERVALO_RE nao cobre parenteses com virgula).",
    "protecao_nbr5410.py": "criterio I2<=1,45IZ; sem faixa declarada.",
    "proteccao_sprinklers_nbr10897.py": "DIVIDA-LENTE: cobertura/espacamento (Tab.10) e teto absoluto 21m2 fora da lente.",
    "recalque_edificio.py": "DIVIDA-LENTE: limites default (Tabela C.1) fora da lente.",
    "redimensionamento.py": "otimizador guloso; verificacoes vivem nos modulos chamados.",
    "relatorio_calculo.py": "memorial PDF; sem faixa.",
    "residencial_eletrica.py": "runner que compoe calculadores; sem faixa propria.",
    "rodar_galpao.py": "orquestrador parametrico; 'TETO'/'patamar' ali sao de outros dominios.",
    "rodar_projeto.py": "runner spec-calculo; sem faixa.",
    "romaneio.py": "lista de materiais; sem faixa.",
    "sapata_divisa.py": "viga alavanca NBR 6122; sem faixa declarada.",
    "sinalizacao_nbr16820.py": "DIVIDA-LENTE: 'valido L<50m, minimo 4m' (Tab.1) fora da lente.",
    "smoke_executivo.py": "smoke test; sem faixa.",
    "spda_nbr5419.py": "DIVIDA-LENTE: criterios/tabelas (R1>RT, malha, secoes) sem vocabulario de validade.",
    "techdraw_climatizacao.py": "prancha TechDraw; sem faixa.",
    "techdraw_concreto.py": "prancha TechDraw; sem faixa.",
    "techdraw_coordenacao.py": "prancha TechDraw; sem faixa.",
    "techdraw_eletrico.py": "prancha TechDraw; sem faixa.",
    "techdraw_exec.py": "prancha TechDraw; 'valido' ali e sobre SVG.",
    "techdraw_hidraulica.py": "prancha TechDraw; sem faixa.",
    "techdraw_incendio.py": "prancha TechDraw; sem faixa.",
    "telha_cobertura.py": "hipotese da faixa de 1m; 'no limite' e criterio, sem faixa declarada.",
    "tensao_ponto.py": "verificacao por tensoes; sem faixa declarada.",
    "tercas_iteracao.py": "iterador ('escada' = degraus de perfil); verificacao vive em tercas_nbr14762.",
    "tercas_nbr14762.py": "DIVIDA-LENTE: dispensa (Tab.14) e limites L/180-L/120 fora da lente.",
    "terraplenagem.py": "movimento de terra; 'acima do greide' e geometria.",
    "tesoura.py": "DIVIDA-LENTE: 'metodo dos nos valido' (trelica isostatica) fora da lente.",
    "tolerancias_fabricacao.py": "DIVIDA-LENTE: quadro de tolerancias (Tab.12) fora da lente.",
    "tools_probe_pe13.py": "script avulso de medicao; sem faixa.",
    "torcao_nbr8800.py": "torcao 5.5.2; sem faixa no vocabulario da lente.",
    "validacao.py": "harness de afericao; sem faixa.",
    "validacao_sistema_g15.py": "harness G15; 'fora do intervalo' ali e de URL/pagina.",
    "varredura_nao_verificados.py": "ferramenta G33; nao declara faixa de metodo.",
    "verificar_amostra.py": "script avulso visual; sem faixa.",
    "vibracao_piso.py": "escopo ilimitado ('vale para toda classe') fora da lente; 'restrito' e de acesso.",
    "viga_baldrame_edificio.py": "fronteira sem faixa declarada.",
    "viga_equilibrio.py": "DIVIDA-LENTE: teto de armadura (5cm2/m) em vocabulario generico fora da lente.",
    "wizard.py": "formulario de entrada; validacao de entrada nao e faixa de metodo.",
    "zona_painel.py": "DIVIDA-LENTE: limite b/t (Tab.F.1) fora da lente.",
}


def arquivos_varridos(raiz=None):
    """Arquivos com >= 1 chave na varredura (a cobertura existe)."""
    return sorted({d["arquivo"] for d in varredura(raiz)})


def arquivos_sem_chave(raiz=None):
    """Arquivos *.py sem nenhuma chave: ou entram em SEM_FAIXA_DECLARADA
    com motivo, ou a suite fica vermelha (D87). A propria lente nunca entra
    (ela e o instrumento, nao o objeto)."""
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    varridos = set(arquivos_varridos(raiz))
    return sorted(p.name for p in base.glob("*.py")
                  if p.name != "varredura_faixa_validade.py"
                  and p.name not in varridos)


def confere_cobertura(raiz=None, isentos=None):
    """Guarda D87 em forma chamavel (para o teste provar o vermelho sem
    mutar o repo): faltando = invisivel a lente e sem isencao; sobrando =
    isento que agora produz chave (nome morto); sem_motivo = isencao com
    motivo apagado/vazio; ausentes = isento que sumiu do disco."""
    iso = SEM_FAIXA_DECLARADA if isentos is None else isentos
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    no_disco = {p.name for p in base.glob("*.py")}
    sem = arquivos_sem_chave(raiz)
    faltando = sorted(a for a in sem if a not in iso)
    sobrando = sorted(a for a in iso if a in no_disco and a not in sem)
    sem_motivo = sorted(a for a, m in iso.items() if not (m or "").strip())
    ausentes = sorted(a for a in iso if a not in no_disco)
    return {"OK": not (faltando or sobrando or sem_motivo or ausentes),
            "faltando": faltando, "sobrando": sobrando,
            "sem_motivo": sem_motivo, "ausentes": ausentes}


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
