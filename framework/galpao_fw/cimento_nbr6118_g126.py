# ============================================================================
# cimento_nbr6118_g126.py - G126: O CIMENTO QUE NINGUEM DECLAROU. IDENTIDADE +
# PISO CONSERVADOR + PORTAO. NAO ESCOLHE O CIMENTO DO PROJETO.
# MODULO DE PRODUCAO (fonte unica): o cimento que o cliente recebe mora
# aqui; a lente e o teste importam daqui. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python cimento_nbr6118_g126.py) e pelo teste-guarda
# tests/test_cimento_nbr6118_g126.py. IMPORTADO pela producao (premoldado,
# galpao_concreto, desenho_concreto, executivo_concreto, techdraw_concreto,
# pacote_legal, projeto_spec) - por isso NAO e script avulso (ver
# test_alcancabilidade).
#
# O que foi MEDIDO (G125, enderecos verificados naquela entrega + remedicao
# G126 na funcao real):
#   - `galpao_concreto.py:262` passava `spec.get("cimento", "CPV")` ao
#     icamento, e `premoldado_nbr9062.py:255` repetia
#     `caso.get("cimento", "CPV")`. Nem o ProjetoSpec nem o wizard tinham
#     campo de cimento - pelo caminho do produto, o galpao de concreto
#     SEMPRE calculava o icamento com CPV.
#   - O CPV tem o menor `s` da 12.3.3 (0,20): e o default MAIS FAVORAVEL.
#     Medido na funcao real, `fckj_idade(30e3, 7, cimento)`: CPV 24562,
#     CPII 23364, CPIII 20516 kN/m2. O default dava +19,7 % de resistencia
#     aos 7 dias sobre um CPIII que ninguem excluiu.
#   - `premoldado_nbr9062.fckj_idade` tinha OUTRO default, `cimento="CPII"`.
#   - Cimento DESCONHECIDO (qualquer string fora da tabela) virava s = 0,25
#     em silencio (`edicao_nbr6118_g123.S_PADRAO_DESCONHECIDO`): "XYZ" dava
#     o mesmo numero do CPII.
#
# G131 (auditoria do G126, rodada real do galpao, medido): o calculo lia o
# cimento do payload `turnkey.concreto` e o pacote lia do TOPO do projeto.
# Com "cimento": "CPII" no topo, o pacote dizia "CPII (declarado)" e o
# calculo usava o piso s=0,38; com CPII no payload, o calculo usava 0,25 e o
# pacote dizia "nao declarado - piso". E o pacote da casa e do predio
# afirmava "piso conservador no icamento" sem icamento nenhum calculado.
# Agora a entrega declara a partir do resultado (cimento_do_turnkey +
# cimento_da_entrega), o topo chega ao payload (galpao_adapter) e a
# divergencia entre declarado e usado LEVANTA.
#
# Maquina: CIMENTOS_VALIDOS (a tabela da 12.3.3, so identidade - os valores
# de `s` continuam na fonte unica `edicao_nbr6118_g123.S_CIMENTO_2014`) +
# PISO_S = 0,38 (o MAIOR `s` da tabela, regra G6 para dado ausente) +
# normaliza_cimento (desconhecido LEVANTA com a lista dos validos, nunca
# vira 0,25) + resolver_cimento (ausente = piso, com a origem dita) +
# cimento_de_spec (le a chave "cimento" do spec, sem default silencioso) +
# cimento_do_turnkey/cimento_da_entrega (G131: o que a conta USOU) +
# linha_cimento (o que a folha e o memorial dizem) +
# contem_declaracao_cimento/confere_pecas (peca sem declaracao reprova) +
# defaults_de_cimento/confere_defaults (nenhum default CPV/CPII sobrando,
# por AST: `.get("cimento", "<valido>")` ou parametro `cimento="<valido>"`)
# + arquivos_que_importam_cimento/confere_uso_cimento (ninguem le por conta
# propria fora do esperado).
#
# Escolha escrita (exigida pelo goal): PISO CONSERVADOR DECLARADO, nao
# bloqueio. Motivo: o G123 (chave da edicao, mesma familia de "dado que o
# projeto nao declarou") ja decidiu pela chave DESLIGADA - ausente =
# comportamento de hoje declarado na folha, sem travar o pipeline; o goal
# manda o campo de ProjetoSpec/wizard OPCIONAL ("com a ausencia dita"), o
# que e incompativel com bloqueio; e travar todo spec antigo do repo por um
# dado que nunca foi pedido seria punir o usuario pela omissao do
# framework. Piso nao e "o cimento provavel" (Nao fazer do goal): e o MAIOR
# `s` (menor resistencia jovem), e a folha e o memorial dizem que ele foi
# usado PORQUE o cimento nao foi declarado.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - os VALORES de `s` (moram em `edicao_nbr6118_g123.S_CIMENTO_2014`; este
#     modulo so carrega a identidade; numero que ninguem le e comentario);
#   - a REGRA C60+ da 2023+Em1 (mora em `edicao_nbr6118_g123.s_cimento, que
#     agora levanta para desconhecido e aplica o piso para ausente);
#   - o cimento do ACO, da argamassa ou de qualquer outro vertical (aqui e
#     so o `s` da 12.3.3 para o fckj do icamento do pre-moldado);
#   - o fckj da PROTENSAO (viga_protendida le `cfg["fckj"]`, default fck,
#     com A CONFIRMAR no relatorio): nao passa pela 12.3.3 nem pelo cimento;
#   - o campo ProjetoSpec/wizard do galpao METALICO (to_rodar_params ->
#     rodar_galpao), que nao tem icamento de pre-moldado: o caminho que
#     calcula e o project-spec do turnkey (topo ou payload concreto);
#   - PDF do memorial (relatorio_calculo.gerar_pdf): a declaracao mora no
#     memorial em texto (executivo_concreto.memorial + relatorio_pt), que e
#     o que o portao confere; o PDF so o reimprime.
# ============================================================================
"""Cimento da NBR 6118 12.3.3 (G126): identidade, piso conservador e portao."""

from __future__ import annotations

import ast
import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

# A tabela da 12.3.3, so identidade (os `s` moram na fonte unica da edicao).
# "CPV-ARI" e o nome da norma; "CPV ARI" (com espaco) e aceito como alias.
CIMENTOS_VALIDOS = ("CPI", "CPII", "CPIII", "CPIV", "CPV", "CPV-ARI")

# Piso conservador para dado ausente (G6: o MAIOR `s` da tabela = a MENOR
# resistencia jovem). Nao e palpite de cimento: e o teto do `s`.
PISO_S = 0.38
PISO_ROTULO = "CPIII/CPIV"

ORIGEM_DECLARADO = "declarado_no_projeto"
ORIGEM_PISO = "piso_conservador_sem_declaracao"
# G131: entrega sem icamento de pre-moldado calculado (casa, predio, galpao
# sem a disciplina concreto). Nenhum fckj depende do cimento; a linha diz
# isso em vez de afirmar um piso que nenhuma conta usou.
ORIGEM_SEM_ICAMENTO = "sem_icamento_calculado"
ORIGENS = (ORIGEM_DECLARADO, ORIGEM_PISO, ORIGEM_SEM_ICAMENTO)

# Tipologias cujo pacote nao calcula icamento de pre-moldado (G131).
TIPOLOGIAS_SEM_ICAMENTO = ("casa", "predio", "edificio")

# Prefixo estavel que o portao confere por substring (nunca regex sobre a
# folha: o carimbo e texto corrido, mesmo molde do G123).
PREFIXO_LINHA = "Cimento (NBR 6118 12.3.3"
MARCA_DECLARADO = "(declarado no projeto)"
MARCA_PISO = "piso conservador s=0,38"
MARCA_SEM_ICAMENTO = "sem icamento de pre-moldado calculado"

# Arquivos de producao que podem importar esta fonte unica (baseline nos
# dois sentidos: import novo sem triagem = leitura por conta propria;
# import que some = nome morto). So raiz *.py (nao tests/): teste que
# importa a lente nao e conta de producao. O executivo_concreto NAO importa:
# o memorial dele compoe o relatorio_pt do galpao, e a declaracao chega por
# ali (dito aqui para a ausencia nao parecer esquecimento).
LEITORES_ESPERADOS = frozenset({
    "cimento_nbr6118_g126.py",
    "edicao_nbr6118_g123.py",
    "premoldado_nbr9062.py",
    "galpao_concreto.py",
    "desenho_concreto.py",
    "techdraw_concreto.py",
    "pacote_legal.py",
    "projeto_spec.py",
    # G131: o topo do projeto chega ao payload do concreto (galpao_adapter)
    # e o pacote do galpao declara o cimento do resultado (entregaveis).
    "galpao_adapter.py",
    "entregaveis_projeto.py",
})


def normaliza_cimento(cimento):
    """Canoniza um tipo de cimento da 12.3.3 (NBR 6118 Tab. 12.3.3).

    Aceita variacao de caixa e de espaco ("cpii", "CPV ARI"); qualquer outra
    coisa LEVANTA ValueError com a lista dos validos (nunca vira 0,25 em
    silencio). None nunca chega aqui (ver resolver_cimento): parametro
    ausente nao e cimento invalido, e piso conservador declarado.
    """
    if not isinstance(cimento, str):
        raise ValueError("cimento deve ser um de %s (recebido %r)"
                         % (", ".join(CIMENTOS_VALIDOS), cimento))
    t = cimento.strip().upper()
    if t == "CPV ARI":
        t = "CPV-ARI"
    if t not in CIMENTOS_VALIDOS:
        raise ValueError("cimento desconhecido %r (NBR 6118 12.3.3; use um "
                         "de: %s)" % (cimento, ", ".join(CIMENTOS_VALIDOS)))
    return t


def resolver_cimento(valor=None):
    """Resolve o cimento sem default silencioso.

    valor=None/""/branco (parametro ausente) -> piso conservador
    (PISO_S), com origem declarada ORIGEM_PISO (a folha diz que o cimento
    nao foi declarado). String valida -> o cimento, com origem
    ORIGEM_DECLARADO. Qualquer outra coisa -> ValueError (nao vira CPV,
    nem CPII, nem 0,25).
    """
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return {"cimento": None, "origem": ORIGEM_PISO, "explicito": False}
    can = normaliza_cimento(valor)
    return {"cimento": can, "origem": ORIGEM_DECLARADO, "explicito": True}


def cimento_de_spec(spec):
    """Cimento declarado num spec dict (galpao_concreto ou ProjetoSpec).

    Procura a chave "cimento". Ausente/None/"" -> None (piso conservador
    declarado, nao CPV). Valor invalido -> ValueError (nao vira cimento em
    silencio; o ProjetoSpec converte em campo faltante).
    """
    if not isinstance(spec, dict):
        return None
    if "cimento" not in spec or spec["cimento"] in (None, ""):
        return None
    return normaliza_cimento(spec["cimento"])


def cimento_do_turnkey(R):
    """Cimento que o CALCULO usou no resultado do galpao_turnkey (G131).

    Parte de onde o dado e produzido (convencao 9): galpao_concreto.rodar
    grava o resolvido em `raw["cimento"]`. Concreto nao executado -> origem
    ORIGEM_SEM_ICAMENTO (nenhum fckj calculado). Concreto executado sem o
    resolvido no resultado -> ValueError (a entrega nao declara um cimento
    que a conta nao registrou).
    """
    if not isinstance(R, dict):
        raise TypeError("R tem de ser o dict do galpao_turnkey.rodar")
    if "concreto" not in (R.get("executadas") or []):
        return {"cimento": None, "origem": ORIGEM_SEM_ICAMENTO,
                "explicito": False}
    conc = (R.get("disciplinas") or {}).get("concreto")
    raw = conc.get("raw") if isinstance(conc, dict) else None
    cim = raw.get("cimento") if isinstance(raw, dict) else None
    if not isinstance(cim, dict) or cim.get("origem") not in (ORIGEM_DECLARADO,
                                                              ORIGEM_PISO):
        raise ValueError("concreto executado sem o cimento resolvido no "
                         "resultado (G126/G131): a entrega nao declara o "
                         "que a conta nao registrou")
    return _resolve_fonte(raw)


def cimento_da_entrega(calculado=None, spec=None, tipologia=None):
    """O cimento que a ENTREGA declara (pacote), sem duas fontes (G131).

    `calculado` (o que a conta usou, ex. cimento_do_turnkey) vence; se o
    `spec` declarar outro cimento, LEVANTA (a entrega nao escreve os dois).
    Sem `calculado`: tipologia casa/predio -> sem icamento calculado;
    senao o spec (ausente = piso declarado). Cimento declarado sem conta que
    o use viaja em `cimento` com a origem ORIGEM_SEM_ICAMENTO (a linha diz
    "sem uso em conta").
    """
    declarado = cimento_de_spec(spec)
    if calculado is not None:
        res = _resolve_fonte(calculado)
        if res["origem"] == ORIGEM_SEM_ICAMENTO:
            return {"cimento": declarado, "origem": ORIGEM_SEM_ICAMENTO,
                    "explicito": declarado is not None}
        if declarado is not None and res["cimento"] != declarado:
            raise ValueError(
                "cimento declarado no projeto %s, mas o calculo usou %s "
                "(NBR 6118 12.3.3): a entrega nao declara os dois (G131)"
                % (declarado, res["cimento"] or "o piso conservador s=0,38"))
        return res
    tip = str(tipologia).strip().lower() if tipologia is not None else None
    if tip in TIPOLOGIAS_SEM_ICAMENTO:
        return {"cimento": declarado, "origem": ORIGEM_SEM_ICAMENTO,
                "explicito": declarado is not None}
    return resolver_cimento(declarado)


def linha_cimento(fonte=None):
    """Linha que a folha e o memorial carimbam (vem desta fonte so).

    `fonte`: dict resolvido (com "cimento"+"origem"), resultado do
    galpao/icamento (com "cimento"), spec dict, string de cimento ou None.
    Sem o cimento, a linha diz que o piso foi usado PORQUE nada foi
    declarado (sem default silencioso: a ausencia fica escrita). Sem
    icamento calculado (G131), a linha diz isso - nao afirma um piso.
    """
    res = _resolve_fonte(fonte)
    if res["origem"] == ORIGEM_SEM_ICAMENTO:
        extra = ("; cimento declarado %s sem uso em conta" % res["cimento"]
                 if res.get("cimento") else "")
        return ("Cimento (NBR 6118 12.3.3, fckj no icamento): %s nesta "
                "entrega — nenhum fckj depende do cimento%s (G126)"
                % (MARCA_SEM_ICAMENTO, extra))
    if res["origem"] == ORIGEM_DECLARADO:
        return ("Cimento (NBR 6118 12.3.3, fckj no icamento): %s "
                "(declarado no projeto)" % res["cimento"])
    return ("Cimento (NBR 6118 12.3.3, fckj no icamento): nao declarado "
            "— piso conservador s=0,38 (CPIII/CPIV) (G126)")


def _resolve_fonte(fonte):
    """Normaliza qualquer portador de cimento para o dict resolvido."""
    if isinstance(fonte, dict):
        # dict ja resolvido (resolver_cimento/cimento_da_entrega)
        if fonte.get("origem") in ORIGENS and \
                not isinstance(fonte.get("cimento"), dict):
            c = fonte.get("cimento")
            can = normaliza_cimento(c) if c not in (None, "") else None
            if fonte["origem"] == ORIGEM_DECLARADO and can is None:
                raise ValueError("origem declarada sem cimento (G126)")
            return {"cimento": can, "origem": fonte["origem"],
                    "explicito": (fonte["origem"] == ORIGEM_DECLARADO
                                  or (fonte["origem"] == ORIGEM_SEM_ICAMENTO
                                      and can is not None))}
        if isinstance(fonte.get("cimento"), dict) and \
                fonte["cimento"].get("origem") in ORIGENS:
            return _resolve_fonte(fonte["cimento"])
        if fonte.get("cimento_origem") in (ORIGEM_DECLARADO, ORIGEM_PISO):
            c = fonte.get("cimento")
            if c is None:
                return resolver_cimento(None)
            return {"cimento": normaliza_cimento(c),
                    "origem": fonte["cimento_origem"],
                    "explicito": fonte["cimento_origem"] == ORIGEM_DECLARADO}
        return resolver_cimento(cimento_de_spec(fonte))
    return resolver_cimento(fonte)


def contem_declaracao_cimento(texto):
    """A peca declara o cimento do fckj? (portao por substring).

    True quando o texto contem o prefixo E uma das tres marcas (declarado,
    piso ou sem icamento calculado). Devolve {'tem', 'origem'}; origem=None
    quando nao tem; 'ambas' quando ha mais de uma marca.
    """
    t = str(texto or "")
    if PREFIXO_LINHA not in t:
        return {"tem": False, "origem": None}
    achadas = [origem for origem, marca in (
        (ORIGEM_DECLARADO, MARCA_DECLARADO),
        (ORIGEM_PISO, MARCA_PISO),
        (ORIGEM_SEM_ICAMENTO, MARCA_SEM_ICAMENTO)) if marca in t]
    if not achadas:
        return {"tem": False, "origem": None}
    if len(achadas) > 1:
        return {"tem": True, "origem": "ambas"}
    return {"tem": True, "origem": achadas[0]}


def confere_pecas(pecas):
    """Portao das pecas: OK quando TODA peca declara o cimento do fckj.

    OK global so quando toda peca declara (cada OK chega ao veredito
    global, contra a saturacao silenciosa do G113). 'sem_declaracao' e o
    acumulador que o teste faz disparar (convencao 7).
    """
    if pecas is None or not isinstance(pecas, dict):
        raise TypeError("pecas tem de ser dict nome->texto")
    por_peca = {}
    sem = []
    for nome, texto in pecas.items():
        c = contem_declaracao_cimento(texto)
        if c["tem"]:
            por_peca[str(nome)] = {"OK": True, "origem": c["origem"],
                                   "motivo": ""}
        else:
            por_peca[str(nome)] = {
                "OK": False, "origem": None,
                "motivo": "peca sem declaracao do cimento do fckj "
                          "(exigido G126: '%s ... %s' ou '%s ... %s')"
                          % (PREFIXO_LINHA, MARCA_DECLARADO,
                             PREFIXO_LINHA, MARCA_PISO)}
            sem.append(str(nome))
    sem.sort()
    return {"por_peca": por_peca, "sem_declaracao": sem,
            "OK": not sem}


def _e_cimento_valido_literal(valor):
    """String literal que e um tipo de cimento valido (para o scan)."""
    return (isinstance(valor, str)
            and valor.strip().upper().replace(" ", "") in
            {c.replace("-", "") for c in CIMENTOS_VALIDOS})


def defaults_de_cimento(raiz=None):
    """Defaults silenciosos de cimento no codigo (por AST, nunca substring).

    Acha (a) `.get("cimento", "<valido>")` - o default que virava CPV - e
    (b) parametro `cimento="<valido>"` em `def` - o default que virava
    CPII. Mencao em string, chamada com cimento explicito e alias em
    mensagem de erro NAO sao default. `raiz` (molde G51-rev): diretorio a
    varrer, default o proprio galpao_fw (raiz *.py + tests/ recursivo);
    existe para o teste-guarda provar o VERMELHO num diretorio temporario.
    Devolve [{"arquivo", "linha", "forma"}] em ordem estavel.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    if raiz is None:
        alvos = sorted(base.glob("*.py"))
        testes = base / "tests"
        if testes.is_dir():
            alvos += sorted(p for p in testes.rglob("*.py")
                            if p.is_file())
    else:
        alvos = sorted(p for p in base.rglob("*.py") if p.is_file())
    achados = []
    for caminho in alvos:
        try:
            rel = caminho.relative_to(base).as_posix()
        except ValueError:
            rel = caminho.name
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            arvore = ast.parse(texto, filename=str(caminho))
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
                    and no.func.attr == "get" and len(no.args) >= 2:
                chave, padrao = no.args[0], no.args[1]
                if isinstance(chave, ast.Constant) and chave.value == "cimento" \
                        and isinstance(padrao, ast.Constant) \
                        and _e_cimento_valido_literal(padrao.value):
                    achados.append({"arquivo": rel, "linha": no.lineno,
                                    "forma": 'get("cimento", "%s")'
                                             % (padrao.value,)})
            elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                todos = (list(no.args.posonlyargs) + list(no.args.args)
                         + list(no.args.kwonlyargs))
                pares = list(no.args.defaults)
                simples = todos[len(todos) - len(pares):] if pares else []
                for arg, val in zip(simples, pares):
                    if arg.arg == "cimento" and isinstance(val, ast.Constant) \
                            and _e_cimento_valido_literal(val.value):
                        achados.append({"arquivo": rel, "linha": no.lineno,
                                        "forma": 'param cimento="%s"'
                                                 % (val.value,)})
                for arg, val in zip(no.args.kwonlyargs, no.args.kw_defaults):
                    if arg.arg == "cimento" and isinstance(val, ast.Constant) \
                            and _e_cimento_valido_literal(val.value):
                        achados.append({"arquivo": rel, "linha": no.lineno,
                                        "forma": 'param cimento="%s"'
                                                 % (val.value,)})
    achados.sort(key=lambda d: (d["arquivo"], d["linha"], d["forma"]))
    return achados


def confere_defaults(raiz=None):
    """Portao 'nenhum default de cimento sobrando'.

    OK so quando o scan acha ZERO defaults (o baseline e vazio nos dois
    sentidos: default novo sem triagem = vermelho; nao ha "resolvido" -
    remover default e o estado final, nao divida). 'defaults' e o
    acumulador que o teste faz disparar.
    """
    achados = defaults_de_cimento(raiz)
    return {"OK": not achados, "defaults": achados}


def arquivos_que_importam_cimento(raiz=None):
    """Arquivos *.py da raiz que importam esta fonte unica (por AST, nunca
    substring: o nome em string de mensagem de erro nao e dependencia).

    Le por ast.parse (nunca substring): `import cimento_nbr6118_g126` ou
    `from cimento_nbr6118_g126 import ...`, em qualquer nivel. O proprio
    modulo conta (fonte unica). So raiz (nao tests/): teste que importa a
    lente nao e conta de producao.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = set()
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "cimento_nbr6118_g126.py":
            achados.add(caminho.name)
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            arvore = ast.parse(texto, filename=str(caminho))
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                if any((a.name or "").split(".")[0] == "cimento_nbr6118_g126"
                       for a in no.names):
                    achados.add(caminho.name)
                    break
            elif isinstance(no, ast.ImportFrom):
                if (no.module or "").split(".")[0] == "cimento_nbr6118_g126":
                    achados.add(caminho.name)
                    break
    return achados


def confere_uso_cimento(raiz=None, esperado=None):
    """Portao 'nenhum modulo le por conta propria' (lado dos imports).

    Compara quem importa a fonte unica com o baseline LEITORES_ESPERADOS
    nos dois sentidos: extra (import novo sem triagem) e faltando (nome
    morto) = vermelho. 'extras'/'faltando' sao os acumuladores que o teste
    faz disparar.
    """
    esp = set(LEITORES_ESPERADOS) if esperado is None else set(esperado)
    tem = set(arquivos_que_importam_cimento(raiz))
    extras = sorted(tem - esp)
    faltando = sorted(esp - tem)
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    try:
        no_disco = {p.name for p in base.glob("*.py")}
    except OSError:
        no_disco = set(tem) | esp
    ausentes = sorted(a for a in esp if a not in no_disco)
    faltando = sorted(a for a in faltando if a not in ausentes)
    return {"OK": not (extras or faltando or ausentes),
            "extras": extras, "faltando": faltando, "ausentes": ausentes,
            "tem": sorted(tem)}


def main() -> int:
    res = resolver_cimento(None)
    print("cimentos=%s piso_s=%.2f (%s) leitores=%d"
          % (list(CIMENTOS_VALIDOS), PISO_S, PISO_ROTULO,
             len(LEITORES_ESPERADOS)))
    print("linha (sem cimento): %s" % linha_cimento(None))
    print("linha (CPII): %s" % linha_cimento("CPII"))
    print("linha (casa): %s" % linha_cimento(
        cimento_da_entrega(tipologia="casa")))
    print("resolver(None)=%r" % (res,))
    d = confere_defaults()
    print("defaults restantes=%d (esperado 0)" % len(d["defaults"]))
    u = confere_uso_cimento()
    print("uso OK=%s extras=%r faltando=%r" % (u["OK"], u["extras"],
                                               u["faltando"]))
    return 0 if (d["OK"] and u["OK"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
