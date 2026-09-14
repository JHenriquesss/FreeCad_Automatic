# ============================================================================
# protensao_fck_g133.py - G133: A VIGA PROTENDIDA NUM CONCRETO QUE O PROJETO
# NAO DECLAROU. IDENTIDADE + PISO DECLARADO + PORTAO. NAO ESCOLHE O FCK DE
# FABRICA NEM A IDADE DE PROTENSAO.
# MODULO DE PRODUCAO (fonte unica): o concreto que a viga protendida usou
# mora aqui; a lente e o teste importam daqui. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python protensao_fck_g133.py) e pelo teste-guarda
# tests/test_protensao_fck_g133.py. IMPORTADO pela producao (viga_protendida,
# galpao_concreto, desenho_concreto, techdraw_concreto, pacote_legal,
# galpao_adapter, entregaveis_projeto) - por isso NAO e script avulso (ver
# test_alcancabilidade).
#
# O que foi MEDIDO (G131 + remedicao G133 na funcao real):
#   - `galpao_concreto.py:223` passava `max(fck, 40e3)` a viga protendida:
#     com o projeto em C30, a viga era calculada em C40.
#   - `viga_protendida.py:154` fazia `fckj = cfg.get("fckj", fck)`: a
#     verificacao no ato da protensao usava o fck de 28 dias. O
#     galpao_concreto nao passava `fckj`.
#   - Funcao real, galpao de concreto de vao 15 m em C30: tipo_viga =
#     "protendida"; no ato, lim_comp = -28000 kN/m2 (= 0,70 x 40 MPa: fck e
#     fckj = 40 MPa). O relatorio_pt dizia "C30" e "VIGA DE COBERTURA
#     (protendida): secao 20x60 cm ; 4 cordoalhas Ø12,7 -> ATENDE"; o
#     executivo_concreto.memorial nao mencionava C40.
#   - O relatorio proprio da viga diz "[A CONFIRMAR: fckj na idade da
#     protensao, ...]" (viga_protendida.py:233): o aviso existia na peca da
#     viga e chegava ao memorial pelo executivo_concreto (que compoe o
#     relatorio da viga), mas NAO chegava as folhas (desenho_concreto,
#     techdraw_concreto) nem ao relatorio_pt do galpao, que so dizia "C30".
#
# Maquina: CHAVES ("fck_protendida", "fckj_protensao") + _parse_fck (kN/m2,
# com atalho MPa) + fck_protendida_de_spec/fckj_protensao_de_spec (sem
# default silencioso; invalido LEVANTA) + resolver_entrada (ausente = fck
# do projeto / fckj = fck usado, com a origem dita) +
# protensao_do_turnkey/protensao_da_entrega (G131: o que a conta USOU vence;
# divergencia entre declarado e usado LEVANTA) + linha_protensao (o que a
# folha e o memorial dizem) + contem_declaracao_protensao/confere_pecas
# (peca sem declaracao reprova) + defaults_de_protensao/confere_defaults
# (nenhum `max(fck, ...)` e nenhum default numerico de fck/fckj sobrando,
# por AST) + arquivos_que_importam_protensao/confere_uso_protensao
# (ninguem le por conta propria fora do esperado).
#
# Escolha escrita (exigida pelo goal): PISO DECLARADO = FCK DO PROJETO, nao
# bloqueio e nao C40 de fabrica. Motivo: o C40 e o default MAIS FAVORAVEL
# (resistencia maior aprova onde o C30 reprovaria ou aliviaria a armadura);
# usa-lo sem declaracao e a classe do G125 (o documento declara um valor e
# a conta usa outro), agora do lado do veredito. Travar todo spec antigo
# do repo por um dado que nunca foi pedido puniria o usuario pela omissao
# do framework (a mesma razao do G126). E calcular o fckj pela 12.3.3 com
# uma idade inventada seria escolher a idade de protensao do projeto (Nao
# fazer do goal). Piso nao e "o concreto provavel": e o fck do projeto
# para o fck, e o fck usado para o fckj, e a folha e o memorial dizem que
# foram usados PORQUE nada foi declarado - com o [A CONFIRMAR] da idade
# mantido na peca da viga.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - os VALORES de `s`/beta1 da 12.3.3 (moram em `edicao_nbr6118_g123` e
#     `premoldado_nbr9062.fckj_idade`; este modulo nunca converte idade em
#     resistencia - e por isso que nao escolhe idade);
#   - o cimento do icamento (mora em `cimento_nbr6118_g126`; aqui e so o
#     fck da viga protendida e o fckj da transferencia);
#   - o campo ProjetoSpec/wizard do galpao METALICO (to_rodar_params ->
#     rodar_galpao), que nao tem viga protendida de concreto: as entradas
#     que o produto aceita para este dado sao o spec do galpao_concreto, o
#     payload turnkey.concreto e o topo do project-spec (via galpao_adapter)
#     - a convencao 11 sem repetir o erro do G134;
#   - PDF do memorial (relatorio_calculo.gerar_pdf): a declaracao mora no
#     memorial em texto (galpao_concreto.relatorio_pt +
#     executivo_concreto.memorial + viga_protendida.relatorio_pt), que e o
#     que o portao confere; o PDF so o reimprime.
# ============================================================================
"""Fck da viga protendida e fckj da transferencia (G133): declarados, com
portao. Nunca escolhe o fck de fabrica (C40) nem a idade de protensao."""

from __future__ import annotations

import ast
import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

# Chaves de entrada que o produto aceita (spec do galpao_concreto, payload
# turnkey.concreto e topo do project-spec via galpao_adapter).
CHAVE_FCK = "fck_protendida"
CHAVE_FCKJ = "fckj_protensao"

ORIGEM_FCK_DECLARADO = "declarado_no_projeto"
ORIGEM_FCK_PISO = "fck_nao_declarado_usa_fck_projeto"
ORIGEM_FCKJ_DECLARADO = "fckj_declarado_no_projeto"
ORIGEM_FCKJ_PISO = "fckj_nao_declarado_adotado_fck"
# G131 (terceiro valor declarado): peca sem viga protendida calculada (viga
# de concreto armado, casa, predio). Nenhum fck/fckj de protensao foi usado;
# a linha diz isso em vez de afirmar um piso.
ORIGEM_SEM_PROTENSAO = "sem_viga_protendida"
ORIGENS = (ORIGEM_FCK_DECLARADO, ORIGEM_FCK_PISO, ORIGEM_FCKJ_DECLARADO,
           ORIGEM_FCKJ_PISO, ORIGEM_SEM_PROTENSAO)

# Tipologias cujo pacote nao calcula viga protendida (galpao de concreto
# armado com vao curto tambem cai aqui, via tem_protensao=False).
TIPOLOGIAS_SEM_PROTENSAO = ("casa", "predio", "edificio")

# Prefixo estavel que o portao confere por substring (nunca regex sobre a
# folha: a declaracao e texto corrido, mesmo molde do G123/G126).
PREFIXO_LINHA = "Protensao (fck da viga e fckj"
MARCA_FCK_DECLARADO = "fck declarado no projeto"
MARCA_FCK_PISO = "fck nao declarado"
MARCA_FCKJ_DECLARADO = "fckj declarado no projeto"
MARCA_FCKJ_PISO = "fckj nao declarado"
MARCA_SEM_PROTENSAO = "sem viga protendida"
MARCA_FABRICA = "sem piso de fabrica C40"

# Arquivos de producao que podem importar esta fonte unica (baseline nos
# dois sentidos: import novo sem triagem = leitura por conta propria;
# import que some = nome morto). So raiz *.py (nao tests/): teste que
# importa a lente nao e conta de producao. O executivo_concreto NAO importa:
# o memorial dele compoe o relatorio_pt do galpao e o relatorio da viga, e
# a declaracao chega por ali (dito aqui para a ausencia nao parecer
# esquecimento - mesmo molde do G126).
LEITORES_ESPERADOS = frozenset({
    "protensao_fck_g133.py",
    "viga_protendida.py",
    "galpao_concreto.py",
    "desenho_concreto.py",
    "techdraw_concreto.py",
    "pacote_legal.py",
    "galpao_adapter.py",
    "entregaveis_projeto.py",
})


def _parse_fck(valor, nome="fck"):
    """Canoniza um fck em kN/m2 (mesma unidade do `fck` do spec).

    Aceita numero em kN/m2 (ex. 30000, 40e3) ou atalho em MPa (ex. 30, 40,
    "40 MPa", "C40"): valor numerico < 1000 e lido como MPa e convertido
    (x1000). String vazia/branca = ausente (devolve None, nao levanta:
    parametro ausente nao e valor invalido, e piso declarado). Qualquer
    outra coisa (<= 0, nao numerico) LEVANTA ValueError (nunca vira C40 em
    silencio).
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        t = valor.strip()
        if not t:
            return None
        u = t.upper().replace("KN/M2", "").replace("KPA", "").strip()
        u = u.replace("MPA", "").replace("C", "", 1) if u.lstrip().startswith("C") and len(u.strip()) <= 6 else u.replace("MPA", "")
        u = u.strip()
        try:
            num = float(u.replace(",", "."))
        except ValueError:
            raise ValueError("%s invalido %r (use kN/m2, ex. 30000, ou MPa, "
                             "ex. 30)" % (nome, valor))
        valor = num
    try:
        num = float(valor)
    except (TypeError, ValueError):
        raise ValueError("%s invalido %r (use kN/m2, ex. 30000, ou MPa, "
                         "ex. 30)" % (nome, valor))
    if num < 1000.0:
        # atalho MPa (o fck em kN/m2 e sempre >= 20000 para C20+).
        if num <= 0:
            raise ValueError("%s invalido %r (tem de ser > 0)" % (nome, valor))
        num = num * 1000.0
    if num <= 0:
        raise ValueError("%s invalido %r (tem de ser > 0)" % (nome, valor))
    return float(num)


def fck_protendida_de_spec(spec):
    """Fck declarado da viga protendida num spec dict.

    Ausente/None/"" -> None (piso = fck do projeto, declarado; nunca C40).
    Valor invalido -> ValueError (nao vira numero em silencio).
    """
    if not isinstance(spec, dict):
        return None
    if CHAVE_FCK not in spec or spec[CHAVE_FCK] in (None, ""):
        return None
    return _parse_fck(spec[CHAVE_FCK], CHAVE_FCK)


def fckj_protensao_de_spec(spec):
    """Fckj declarado da transferencia num spec dict (mesmo contrato)."""
    if not isinstance(spec, dict):
        return None
    if CHAVE_FCKJ not in spec or spec[CHAVE_FCKJ] in (None, ""):
        return None
    return _parse_fck(spec[CHAVE_FCKJ], CHAVE_FCKJ)


def resolver_entrada(spec=None, fck_projeto=None):
    """Resolve o fck da protendida e o fckj sem default silencioso.

    `spec`: dict com as chaves opcionais (ausente = piso declarado).
    `fck_projeto`: o fck do projeto em kN/m2 (o `fck` do spec do galpao;
    obrigatorio - sem ele nao ha piso honesto e a funcao levanta).
    Devolve {"fck_usado", "fck_origem", "fck_explicito", "fckj_usado",
    "fckj_origem", "fckj_explicito"}.
    """
    try:
        fp = float(fck_projeto)
    except (TypeError, ValueError):
        raise ValueError("resolver_entrada exige o fck do projeto em kN/m2 "
                         "(recebido %r): sem ele nao ha piso declarado"
                         % (fck_projeto,))
    if fp <= 0:
        raise ValueError("fck do projeto invalido %r" % (fck_projeto,))
    fck_decl = fck_protendida_de_spec(spec)
    if fck_decl is not None:
        fck_usado, fck_origem, fck_exp = fck_decl, ORIGEM_FCK_DECLARADO, True
    else:
        fck_usado, fck_origem, fck_exp = float(fp), ORIGEM_FCK_PISO, False
    fckj_decl = fckj_protensao_de_spec(spec)
    if fckj_decl is not None:
        fckj_usado, fckj_origem, fckj_exp = (fckj_decl, ORIGEM_FCKJ_DECLARADO,
                                            True)
    else:
        fckj_usado, fckj_origem, fckj_exp = (float(fck_usado),
                                            ORIGEM_FCKJ_PISO, False)
    return {"fck_usado": float(fck_usado), "fck_origem": fck_origem,
            "fck_explicito": fck_exp, "fckj_usado": float(fckj_usado),
            "fckj_origem": fckj_origem, "fckj_explicito": fckj_exp}


def protensao_do_turnkey(R):
    """Protensao que o CALCULO usou no resultado do galpao_turnkey (G131).

    Parte de onde o dado e produzido (convencao 9): galpao_concreto.rodar
    grava o resolvido em `raw["protensao"]`. Concreto nao executado, ou
    executado sem viga protendida (viga de concreto armado) -> origem
    ORIGEM_SEM_PROTENSAO (nenhum fck/fckj de protensao usado). Concreto
    com protendida mas sem o resolvido no resultado -> ValueError (a
    entrega nao declara o que a conta nao registrou).
    """
    if not isinstance(R, dict):
        raise TypeError("R tem de ser o dict do galpao_turnkey.rodar")
    if "concreto" not in (R.get("executadas") or []):
        return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                "fck_usado": None, "fckj_usado": None}
    conc = (R.get("disciplinas") or {}).get("concreto")
    raw = conc.get("raw") if isinstance(conc, dict) else None
    if not isinstance(raw, dict):
        raise ValueError("concreto executado sem resultado no turnkey (G133)")
    if raw.get("tipo_viga") != "protendida" or not raw.get("viga_prot"):
        prot = raw.get("protensao") if isinstance(raw.get("protensao"), dict) else None
        return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                "fck_usado": None, "fckj_usado": None,
                "declarado": prot}
    prot = raw.get("protensao")
    if not isinstance(prot, dict) or prot.get("fck_usado") in (None, ""):
        raise ValueError("concreto com protendida sem a protensao resolvida "
                         "no resultado (G133): a entrega nao declara o que "
                         "a conta nao registrou")
    return _resolve_fonte(prot)


def protensao_da_entrega(calculado=None, spec=None, tipologia=None,
                         tem_protensao=None):
    """A protensao que a ENTREGA declara (pacote), sem duas fontes (G131).

    `calculado` (o que a conta usou, ex. protensao_do_turnkey) vence; se o
    `spec` declarar outro fck/fckj, LEVANTA (a entrega nao escreve os dois).
    Sem `calculado`: tipologia casa/predio/edificio, ou tem_protensao=False
    -> sem viga protendida; senao o spec (ausente = piso dito). Valor
    declarado sem conta que o use viaja com origem ORIGEM_SEM_PROTENSAO (a
    linha diz "sem uso em conta").
    """
    fck_decl = fck_protendida_de_spec(spec)
    fckj_decl = fckj_protensao_de_spec(spec)
    if calculado is not None:
        res = _resolve_fonte(calculado)
        if res["origem"] == ORIGEM_SEM_PROTENSAO:
            extra = {}
            if fck_decl is not None:
                extra["fck_declarado_sem_uso"] = fck_decl
            if fckj_decl is not None:
                extra["fckj_declarado_sem_uso"] = fckj_decl
            out = dict(res)
            out.update(extra)
            return out
        for chave, decl in ((CHAVE_FCK, fck_decl), (CHAVE_FCKJ, fckj_decl)):
            usado = res["fck_usado"] if chave == CHAVE_FCK else res["fckj_usado"]
            if decl is not None and abs(decl - usado) > 1e-6:
                raise ValueError(
                    "%s declarado no projeto %.0f kN/m2, mas o calculo usou "
                    "%.0f kN/m2: a entrega nao declara os dois (G133)"
                    % (chave, decl, usado))
        return res
    tip = str(tipologia).strip().lower() if tipologia is not None else None
    if tip in TIPOLOGIAS_SEM_PROTENSAO or tem_protensao is False:
        out = {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
               "fck_usado": None, "fckj_usado": None}
        if fck_decl is not None:
            out["fck_declarado_sem_uso"] = fck_decl
        if fckj_decl is not None:
            out["fckj_declarado_sem_uso"] = fckj_decl
        return out
    if tem_protensao is True or fck_decl is not None or fckj_decl is not None:
        fck_proj = None
        if isinstance(spec, dict):
            try:
                fck_proj = float(spec.get("fck", 0) or 0)
            except (TypeError, ValueError):
                fck_proj = None
        if not fck_proj:
            # sem fck do projeto nao ha piso honesto: a entrega nao inventa.
            raise ValueError("sem o fck do projeto nao ha como declarar a "
                             "protensao (G133): informe o fck ou o "
                             "fck_protendida")
        r = resolver_entrada(spec, fck_proj)
        return {"origem": "resolvido_do_spec", "tem_protensao": True,
                "fck_usado": r["fck_usado"], "fck_origem": r["fck_origem"],
                "fck_explicito": r["fck_explicito"],
                "fckj_usado": r["fckj_usado"],
                "fckj_origem": r["fckj_origem"],
                "fckj_explicito": r["fckj_explicito"]}
    return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
            "fck_usado": None, "fckj_usado": None}


def _mpa(kNm2):
    return "%.0f MPa" % (float(kNm2) / 1000.0,)


def linha_protensao(fonte=None):
    """Linha que a folha e o memorial carimbam (vem desta fonte so).

    `fonte`: dict resolvido (resolver_entrada/protensao_da_entrega), dict
    com "protensao", resultado do galpao/viga (com "viga_prot"/"fckj"), spec
    dict, ou None. Sem viga protendida, a linha diz isso (terceiro valor
    declarado, nunca o piso de uma conta que nao existe). Sem declaracao,
    a linha diz que o fck do projeto e o fck foram usados PORQUE nada foi
    declarado (sem default silencioso: a ausencia fica escrita; sem piso
    de fabrica C40).
    """
    res = _resolve_fonte(fonte)
    if res["origem"] == ORIGEM_SEM_PROTENSAO:
        extra = ""
        if res.get("fck_declarado_sem_uso") is not None:
            extra += ("; fck_protendida declarado %s sem uso em conta"
                      % _mpa(res["fck_declarado_sem_uso"]))
        if res.get("fckj_declarado_sem_uso") is not None:
            extra += ("; fckj_protensao declarado %s sem uso em conta"
                      % _mpa(res["fckj_declarado_sem_uso"]))
        return ("Protensao (fck da viga e fckj na transferencia): sem viga "
                "protendida nesta entrega — nenhum fck/fckj de protensao "
                "usado%s (G133)" % extra)
    fck_usado = res["fck_usado"]
    fckj_usado = res["fckj_usado"]
    if res.get("fck_origem") == ORIGEM_FCK_DECLARADO:
        parte_fck = ("fck %s (fck declarado no projeto)" % _mpa(fck_usado))
    else:
        parte_fck = ("fck %s (fck nao declarado — usado fck do projeto, %s)"
                     % (_mpa(fck_usado), MARCA_FABRICA))
    if res.get("fckj_origem") == ORIGEM_FCKJ_DECLARADO:
        parte_fckj = ("fckj %s (fckj declarado no projeto)"
                      % _mpa(fckj_usado))
    else:
        parte_fckj = ("fckj %s (fckj nao declarado — adotado fck, confirmar "
                      "na idade da protensao)" % _mpa(fckj_usado))
    return ("Protensao (fck da viga e fckj na transferencia): %s; %s (G133)"
            % (parte_fck, parte_fckj))


def _resolve_fonte(fonte):
    """Normaliza qualquer portador de protensao para o dict resolvido."""
    if fonte is None:
        return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                "fck_usado": None, "fckj_usado": None}
    if isinstance(fonte, dict):
        if fonte.get("origem") == ORIGEM_SEM_PROTENSAO:
            out = {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                   "fck_usado": None, "fckj_usado": None}
            for k in ("fck_declarado_sem_uso", "fckj_declarado_sem_uso"):
                if fonte.get(k) is not None:
                    out[k] = float(fonte[k])
            return out
        if fonte.get("origem") == "resolvido_do_spec":
            return dict(fonte)
        if "fck_usado" in fonte and "fckj_usado" in fonte:
            fck_o = fonte.get("fck_origem")
            fckj_o = fonte.get("fckj_origem")
            if fck_o is None:
                fck_o = (ORIGEM_FCK_DECLARADO if fonte.get("fck_explicito")
                         else ORIGEM_FCK_PISO)
            if fckj_o is None:
                fckj_o = (ORIGEM_FCKJ_DECLARADO if fonte.get("fckj_explicito")
                          else ORIGEM_FCKJ_PISO)
            return {"origem": "resolvido_do_spec", "tem_protensao": True,
                    "fck_usado": float(fonte["fck_usado"]),
                    "fck_origem": fck_o,
                    "fck_explicito": bool(fonte.get("fck_explicito", False)),
                    "fckj_usado": float(fonte["fckj_usado"]),
                    "fckj_origem": fckj_o,
                    "fckj_explicito": bool(fonte.get("fckj_explicito", False))}
        if isinstance(fonte.get("protensao"), dict):
            return _resolve_fonte(fonte["protensao"])
        # resultado do galpao_concreto (tem viga_prot/tipo_viga) ou da viga
        # (tem fck/fckj): a conta gravou o que usou (convencao 9).
        if "viga_prot" in fonte or "tipo_viga" in fonte:
            if fonte.get("tipo_viga") == "protendida" and fonte.get("viga_prot"):
                vp = fonte["viga_prot"]
                prot = fonte.get("protensao")
                if isinstance(prot, dict) and prot.get("fck_usado"):
                    return _resolve_fonte(prot)
                fck_usado = vp.get("fck") if isinstance(vp, dict) else None
                fckj_usado = vp.get("fckj") if isinstance(vp, dict) else None
                if fck_usado is None:
                    raise ValueError("resultado com protendida sem o fck "
                                     "usado gravado (G133)")
                fckj_o = (vp.get("fckj_origem") if isinstance(vp, dict)
                          else None)
                return {"origem": "resolvido_do_spec", "tem_protensao": True,
                        "fck_usado": float(fck_usado),
                        "fck_origem": (ORIGEM_FCK_DECLARADO
                                       if fonte.get("protensao", {}).get("fck_explicito")
                                       else ORIGEM_FCK_PISO) if isinstance(
                                           fonte.get("protensao"), dict)
                        else ORIGEM_FCK_PISO,
                        "fck_explicito": bool((fonte.get("protensao") or {}).get("fck_explicito", False)) if isinstance(fonte.get("protensao"), dict) else False,
                        "fckj_usado": float(fckj_usado if fckj_usado is not None else fck_usado),
                        "fckj_origem": (fckj_o if fckj_o in (ORIGEM_FCKJ_DECLARADO, ORIGEM_FCKJ_PISO)
                                        else ORIGEM_FCKJ_PISO),
                        "fckj_explicito": bool(fckj_o == ORIGEM_FCKJ_DECLARADO)}
            return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                    "fck_usado": None, "fckj_usado": None}
        if "fck" in fonte and ("fckj" in fonte or "vao" in fonte):
            # resultado/cfg da viga protendida isolada (ausencia dita: sem a
            # chave, vale o fck - o mesmo mecanismo de verifica_viga).
            fck_usado = float(fonte["fck"])
            fckj_usado = float(fonte["fckj"]) if fonte.get("fckj") not in (None, "") else float(fck_usado)
            fck_o = fonte.get("fck_origem")
            fckj_o = fonte.get("fckj_origem")
            return {"origem": "resolvido_do_spec", "tem_protensao": True,
                    "fck_usado": fck_usado,
                    "fck_origem": (fck_o if fck_o in (ORIGEM_FCK_DECLARADO, ORIGEM_FCK_PISO)
                                   else (ORIGEM_FCK_DECLARADO if fonte.get("fck_explicito", True)
                                         else ORIGEM_FCK_PISO)),
                    "fck_explicito": bool(fonte.get("fck_explicito", True)),
                    "fckj_usado": fckj_usado,
                    "fckj_origem": (fckj_o if fckj_o in (ORIGEM_FCKJ_DECLARADO, ORIGEM_FCKJ_PISO)
                                    else ORIGEM_FCKJ_PISO),
                    "fckj_explicito": bool(fckj_o == ORIGEM_FCKJ_DECLARADO)}
        # spec dict: precisa do fck do projeto para o piso honesto.
        if CHAVE_FCK in fonte or CHAVE_FCKJ in fonte or "fck" in fonte:
            fck_proj = fonte.get("fck")
            if fck_proj in (None, ""):
                return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                        "fck_usado": None, "fckj_usado": None}
            r = resolver_entrada(fonte, float(fck_proj))
            return {"origem": "resolvido_do_spec", "tem_protensao": True,
                    "fck_usado": r["fck_usado"], "fck_origem": r["fck_origem"],
                    "fck_explicito": r["fck_explicito"],
                    "fckj_usado": r["fckj_usado"],
                    "fckj_origem": r["fckj_origem"],
                    "fckj_explicito": r["fckj_explicito"]}
        return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                "fck_usado": None, "fckj_usado": None}
    if isinstance(fonte, str):
        if MARCA_SEM_PROTENSAO in fonte or "sem viga protendida" in fonte:
            return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                    "fck_usado": None, "fckj_usado": None}
        return {"origem": ORIGEM_SEM_PROTENSAO, "tem_protensao": False,
                "fck_usado": None, "fckj_usado": None}
    raise TypeError("fonte de protensao invalida: %r" % (fonte,))


def contem_declaracao_protensao(texto):
    """A peca declara o fck da protendida e o fckj? (portao por substring).

    True quando o texto contem o prefixo E as marcas do fck e do fckj
    (declarado ou nao-declarado), ou a marca de sem-protendida. Devolve
    {'tem', 'origem'}; origem=None quando nao tem.
    """
    t = str(texto or "")
    if PREFIXO_LINHA not in t:
        return {"tem": False, "origem": None}
    if MARCA_SEM_PROTENSAO in t:
        return {"tem": True, "origem": ORIGEM_SEM_PROTENSAO}
    tem_fck = (MARCA_FCK_DECLARADO in t or MARCA_FCK_PISO in t)
    tem_fckj = (MARCA_FCKJ_DECLARADO in t or MARCA_FCKJ_PISO in t)
    if tem_fck and tem_fckj:
        if MARCA_FCK_DECLARADO in t and MARCA_FCKJ_DECLARADO in t:
            return {"tem": True, "origem": "declarado"}
        return {"tem": True, "origem": "piso_declarado"}
    return {"tem": False, "origem": None}


def confere_pecas(pecas):
    """Portao das pecas: OK quando TODA peca declara a protensao.

    OK global so quando toda peca declara (cada OK chega ao veredito
    global, contra a saturacao silenciosa do G113). 'sem_declaracao' e o
    acumulador que o teste faz disparar (convencao 7).
    """
    if pecas is None or not isinstance(pecas, dict):
        raise TypeError("pecas tem de ser dict nome->texto")
    por_peca = {}
    sem = []
    for nome, texto in pecas.items():
        c = contem_declaracao_protensao(texto)
        if c["tem"]:
            por_peca[str(nome)] = {"OK": True, "origem": c["origem"],
                                   "motivo": ""}
        else:
            por_peca[str(nome)] = {
                "OK": False, "origem": None,
                "motivo": "peca sem declaracao do fck da protendida e do "
                          "fckj (exigido G133: '%s ...' com as marcas do fck "
                          "e do fckj, ou '%s ... %s')"
                          % (PREFIXO_LINHA, PREFIXO_LINHA,
                             MARCA_SEM_PROTENSAO)}
            sem.append(str(nome))
    sem.sort()
    return {"por_peca": por_peca, "sem_declaracao": sem,
            "OK": not sem}


def _e_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def defaults_de_protensao(raiz=None):
    """Defaults silenciosos da protensao no codigo (por AST, nunca substring).

    Acha (a) `max(fck, <numero>)` / `max(<numero>, fck)` - o piso de fabrica
    C40 que virava numero sem declaracao; (b) `.get("fck_protendida",
    <numero>)` / `.get("fckj_protensao", <numero>)` - default numerico nas
    chaves novas; (c) `.get("fckj", <default>)` onde o default NAO e o nome
    `fck` (o mecanismo da ausencia dita e `cfg.get("fckj", fck)` com a
    origem gravada; numero ou outra expressao calada e default silencioso).
    Mencao em string, chamada com valor explicito e `resolver_entrada` NAO
    sao default. `raiz` (molde G51-rev): diretorio a varrer, default o
    proprio galpao_fw; existe para o teste-guarda provar o VERMELHO num
    diretorio temporario. Devolve [{"arquivo", "linha", "forma"}] estavel.
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
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) \
                    and no.func.id == "max":
                tem_fck = any(isinstance(a, ast.Name) and a.id == "fck"
                              for a in no.args)
                tem_num = any(isinstance(a, ast.Constant) and _e_numero(a.value)
                              and a.value >= 20000 for a in no.args)
                if tem_fck and tem_num:
                    achados.append({"arquivo": rel, "linha": no.lineno,
                                    "forma": "max(fck, <piso C40>)"})
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
                    and no.func.attr == "get" and len(no.args) >= 2:
                chave, padrao = no.args[0], no.args[1]
                if isinstance(chave, ast.Constant) and chave.value in (
                        CHAVE_FCK, CHAVE_FCKJ):
                    if isinstance(padrao, ast.Constant) and _e_numero(padrao.value):
                        achados.append({"arquivo": rel, "linha": no.lineno,
                                        "forma": 'get("%s", <numero>)'
                                                 % (chave.value,)})
                if isinstance(chave, ast.Constant) and chave.value == "fckj":
                    if isinstance(padrao, ast.Name) and padrao.id == "fck":
                        continue
                    if isinstance(padrao, ast.Constant) and padrao.value is None:
                        continue
                    achados.append({"arquivo": rel, "linha": no.lineno,
                                    "forma": 'get("fckj", <nao-fck>)'})
    achados.sort(key=lambda d: (d["arquivo"], d["linha"], d["forma"]))
    return achados


def confere_defaults(raiz=None):
    """Portao 'nenhum default de protensao sobrando'.

    OK so quando o scan acha ZERO defaults (o baseline e vazio nos dois
    sentidos: default novo sem triagem = vermelho; nao ha "resolvido" -
    remover default e o estado final, nao divida). 'defaults' e o
    acumulador que o teste faz disparar.
    """
    achados = defaults_de_protensao(raiz)
    return {"OK": not achados, "defaults": achados}


def arquivos_que_importam_protensao(raiz=None):
    """Arquivos *.py da raiz que importam esta fonte unica (por AST, nunca
    substring: o nome em string de mensagem de erro nao e dependencia).

    Le por ast.parse (nunca substring): `import protensao_fck_g133` ou
    `from protensao_fck_g133 import ...`, em qualquer nivel. O proprio
    modulo conta (fonte unica). So raiz (nao tests/): teste que importa a
    lente nao e conta de producao.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = set()
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "protensao_fck_g133.py":
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
                if any((a.name or "").split(".")[0] == "protensao_fck_g133"
                       for a in no.names):
                    achados.add(caminho.name)
                    break
            elif isinstance(no, ast.ImportFrom):
                if (no.module or "").split(".")[0] == "protensao_fck_g133":
                    achados.add(caminho.name)
                    break
    return achados


def confere_uso_protensao(raiz=None, esperado=None):
    """Portao 'nenhum modulo le por conta propria' (lado dos imports).

    Compara quem importa a fonte unica com o baseline LEITORES_ESPERADOS
    nos dois sentidos: extra (import novo sem triagem) e faltando (nome
    morto) = vermelho. 'extras'/'faltando' sao os acumuladores que o teste
    faz disparar.
    """
    esp = set(LEITORES_ESPERADOS) if esperado is None else set(esperado)
    tem = set(arquivos_que_importam_protensao(raiz))
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
    res = resolver_entrada({"fck": 30e3}, 30e3)
    print("chaves=%s piso=fck-do-projeto leitores=%d"
          % ([CHAVE_FCK, CHAVE_FCKJ], len(LEITORES_ESPERADOS)))
    print("linha (sem nada, C30): %s" % linha_protensao(
        {"fck_usado": 30e3, "fck_origem": ORIGEM_FCK_PISO,
         "fck_explicito": False, "fckj_usado": 30e3,
         "fckj_origem": ORIGEM_FCKJ_PISO, "fckj_explicito": False}))
    print("linha (declarado C40/C40): %s" % linha_protensao(
        {"fck_usado": 40e3, "fck_origem": ORIGEM_FCK_DECLARADO,
         "fck_explicito": True, "fckj_usado": 40e3,
         "fckj_origem": ORIGEM_FCKJ_DECLARADO, "fckj_explicito": True}))
    print("linha (sem protendida): %s" % linha_protensao(None))
    print("resolver(C30 sem chaves)=%r" % (res,))
    d = confere_defaults()
    print("defaults restantes=%d (esperado 0)" % len(d["defaults"]))
    u = confere_uso_protensao()
    print("uso OK=%s extras=%r faltando=%r" % (u["OK"], u["extras"],
                                               u["faltando"]))
    return 0 if (d["OK"] and u["OK"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
