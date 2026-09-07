# ============================================================================
# compatibilizacao.py - O QUE ESTE SCRIPT FAZ / PRODUZ
# Transforma o CLASH FEDERADO (galpao_turnkey.checa_interferencia_federada) num
# DOCUMENTO DE COORDENACAO com pendencias RASTREAVEIS - o passo que faltava: hoje o
# clash sai como lista/apendice de texto; aqui vira registro formal com ID estavel,
# severidade, status, acao sugerida e disciplina responsavel, exportavel em formato
# BCF-like (BIM Collaboration Format: um "topic" por conflito, com guid/titulo/
# status/prioridade/rotulos/responsavel). Assim a coordenacao vira um ciclo
# fechado (abrir -> analisar -> resolver -> aprovar), nao uma foto.
#   - gerar_pendencias(rep_clash): 1 pendencia por clash, ID CLH-NNN estavel, com
#     severidade (por volume + se e' montagem esperada), status inicial e acao.
#   - matriz_coordenacao(rep): matriz disciplina x disciplina (n de conflitos).
#   - bcf_topics(pendencias): estrutura BCF-like (topics) para intercambio.
# STATELESS: funcoes puras sobre o dict de clash; nenhuma dependencia pesada.
# ============================================================================
"""Relatorio formal de compatibilizacao: clash federado -> pendencias rastreaveis
(BCF-like) com ID/severidade/status/acao/responsavel + matriz de coordenacao."""

from __future__ import annotations

import hashlib

# disciplinas que sao ESTRUTURA (nao se movem; a instalacao e' que se compatibiliza)
# G54-rev: "estrutura" e o nome que o federado do EDIFICIO emite (o do galpao
# separa concreto/aco). Sem ele no conjunto, `_acao_e_responsavel` caia no
# ramo "ambas sao instalacoes" e TODA pendencia estrutura x instalacao saia
# com "remanejar o tracado ... reuniao de coordenacao" e responsavel
# "coordenacao" - some justamente a frase que e o proposito do entregavel:
# "prever passagem (furacao/embutido) na estrutura". Filtro de nome morto.
_ESTRUTURA = {"concreto", "aco", "estrutura"}
# nome de exibicao
_NOME = {"concreto": "Estrutura de concreto", "aco": "Estrutura metalica",
         "estrutura": "Estrutura",
         "eletrico": "Eletrica", "hidraulica": "Hidraulica",
         "incendio": "Incendio", "climatizacao": "Climatizacao (HVAC)"}

STATUS_ABERTO = "Aberto"
STATUS_APROVADO = "Aprovado"        # montagem intencional (clash esperado)
STATUS_RESOLVIDA = "Resolvida"      # G55: furo previsto fechado por decisao registrada

# G55: terceira categoria. O clash esperado=False era sempre "conflito a
# remanejar"; agora ha o furo previsto (cruzamento inevitavel e legitimo cuja
# acao e' prever a passagem e verificar admissibilidade) e o conflito real.
CAT_MONTAGEM = "montagem"           # esperado=True (contato de montagem)
CAT_FURO = "furo_previsto"          # estrutura x instalacao, passagem transversal
CAT_CONFLITO = "conflito"           # todo o resto (remanejar / coordenacao)

# Vereditos da regra normativa (NBR 6118:2014). "admissivel" NAO fecha a
# pendencia sozinho: o fechamento exige resolucao registrada (quem + porque).
VER_ADMISSIVEL = "admissivel"       # dispensa de 13.2.5.1/13.2.5.2 atendida
VER_ACONFIRMAR = "a_confirmar"      # sem dado ou fora da dispensa: exige verificacao
VER_REPROVADO = "reprovado"         # viola limite duro: nao pode ser aprovado

_FONTE_6118 = "NBR 6118:2014"


def _disciplinas_do_par(par):
    """'concretoxeletrico' -> ('concreto','eletrico'). Nomes nao contem 'x'."""
    ps = par.split("x")
    return (ps[0], ps[1]) if len(ps) == 2 else (par, "")


def _severidade(vol_mm3, esperado):
    """Severidade da pendencia. Esperado (montagem) -> Informativa. Senao por volume
    de interpenetracao: >5e6 mm3 (~5 L) Alta ; >5e5 Media ; senao Baixa."""
    if esperado:
        return "Informativa"
    if vol_mm3 > 5e6:
        return "Alta"
    if vol_mm3 > 5e5:
        return "Media"
    return "Baixa"


def _acao_e_responsavel(da, db, esperado):
    """Acao sugerida + disciplina responsavel pela adequacao. Regra de coordenacao:
    a INSTALACAO cede a ESTRUTURA (reposiciona/preve passagem); estrutura so muda em
    ultimo caso. Instalacao x instalacao -> coordenacao (remanejar tracado)."""
    if esperado:
        return ("Nenhuma - contato de montagem intencional (fixacao/aterramento); "
                "verificar apenas a fixacao.", "-")
    da_e = da in _ESTRUTURA; db_e = db in _ESTRUTURA
    if da_e and db_e:
        return ("Conflito estrutura x estrutura - revisar geometria/modelo (nao "
                "deveria ocorrer entre disciplinas).", "coordenacao")
    if da_e ^ db_e:                                 # uma e' estrutura, a outra instalacao
        inst = db if da_e else da
        return ("Reposicionar/remanejar o tracado da %s ou prever passagem "
                "(furacao/embutido) na estrutura, com verificacao estrutural." %
                _NOME.get(inst, inst), inst)
    # ambas instalacoes
    return ("Remanejar o tracado de uma das instalacoes (reservar prumadas/shafts); "
            "definir prioridade em reuniao de coordenacao.", "coordenacao")


def _num(v):
    """float(v) ou None quando ausente/nao-numerico (dado nao declarado)."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def avalia_furo_viga(d_furo_mm=None, h_viga_mm=None, dist_apoio_mm=None,
                     zona_tracao=None, dist_face_mm=None, cobrimento_mm=None,
                     dist_entre_furos_mm=None, furo_unico=False,
                     armadura_seccionada=None, sob_torcao=False):
    """Admissibilidade de furo transversal em viga de concreto (G55).

    Fonte: NBR 6118:2014 13.2.5/13.2.5.1 (+ 21.3.1 armadura de contorno).
    Dispensa de verificacao adicional exige SIMULTANEAMENTE (13.2.5.1 a-d):
      a) furo em zona de tracao e a >= 2h da face do apoio;
      b) dimensao do furo <= 12 cm e <= h/3;
      c) distancia entre faces de furos no mesmo tramo >= 2h;
      d) cobrimentos suficientes e nenhum seccionamento de armadura (Secao 7).
    Base "em qualquer caso": dist a face mais proxima >= 5 cm e 2x cobrimento.
    Sem o dado, o veredito e' a_confirmar com o motivo nomeado - nunca um passe.
    Retorna {"veredito","motivos","clausulas"}.
    """
    motivos = []
    clausulas = [_FONTE_6118 + " 13.2.5", _FONTE_6118 + " 13.2.5.1",
                 _FONTE_6118 + " 21.3.1"]
    d = _num(d_furo_mm); h = _num(h_viga_mm)
    dist_ap = _num(dist_apoio_mm); dist_face = _num(dist_face_mm)
    cob = _num(cobrimento_mm); dist_ff = _num(dist_entre_furos_mm)

    ausentes = []
    if d is None:
        ausentes.append("d_furo_mm")
    if h is None:
        ausentes.append("h_viga_mm")
    if dist_ap is None:
        ausentes.append("dist_apoio_mm")
    if zona_tracao is None:
        ausentes.append("zona_tracao")
    if dist_face is None:
        ausentes.append("dist_face_mm")
    if cob is None:
        ausentes.append("cobrimento_mm")
    if armadura_seccionada is None:
        ausentes.append("armadura_seccionada")
    if not furo_unico and dist_ff is None:
        ausentes.append("dist_entre_furos_mm")
    if ausentes:
        return {"veredito": VER_ACONFIRMAR,
                "motivos": ["dado ausente: %s - sem ele nao ha dispensa "
                            "(13.2.5.1) nem passe" % ", ".join(ausentes)],
                "clausulas": list(clausulas)}

    # --- limites duros ("em qualquer caso"): violacao reprova ---------------
    face_min = max(50.0, 2.0 * cob)
    if dist_face < face_min:
        return {"veredito": VER_REPROVADO,
                "motivos": ["distancia a face %.0f mm < minimo %.0f mm "
                            "(5 cm e 2x cobrimento, 13.2.5.1)" % (dist_face,
                                                                  face_min)],
                "clausulas": list(clausulas)}
    if armadura_seccionada is True:
        return {"veredito": VER_REPROVADO,
                "motivos": ["secciona armadura sem reposicao declarada "
                            "(13.2.5.1(d))"],
                "clausulas": list(clausulas)}
    if sob_torcao:
        motivos.append("elemento sob torcao: limites devem ser ajustados de "
                       "forma a permitir funcionamento adequado (13.2.5.1, "
                       "21.3.3) - verificacao especifica exigida")

    # --- dispensa (a-d simultaneas) ------------------------------------------
    pend = []
    if not (zona_tracao is True and dist_ap >= 2.0 * h):
        pend.append("fora da zona de tracao a >= 2h do apoio (13.2.5.1(a))")
    if not (d <= 120.0 and d <= h / 3.0):
        pend.append("dimensao %.0f mm excede o limite de dispensa "
                    "(12 cm e h/3, 13.2.5.1(b))" % d)
    if not furo_unico and dist_ff < 2.0 * h:
        pend.append("espacamento entre furos %.0f mm < 2h (13.2.5.1(c))" % dist_ff)
    if motivos or pend:
        return {"veredito": VER_ACONFIRMAR,
                "motivos": motivos + [
                    ("dispensa nao atendida: %s - requer verificacao "
                     "estrutural (reducao ao cisalhamento/flexao, 13.2.5; "
                     "bielas e tirantes, Secao 22)") % "; ".join(pend)] if pend
                else motivos,
                "clausulas": list(clausulas)}
    return {"veredito": VER_ADMISSIVEL,
            "motivos": ["dispensa de verificacao adicional atendida "
                        "(13.2.5.1 a-d); manter armadura de contorno/cantos "
                        "(21.3.1) e boa concretagem"],
            "clausulas": list(clausulas)}


def avalia_abertura_laje(dim_abertura_mm=None, vao_menor_mm=None,
                         dist_apoio_mm=None, dist_adjacente_mm=None,
                         laje_lisa=None, armadura_seccionada=None):
    """Admissibilidade de abertura que atravessa laje na sua espessura (G55).

    Fonte: NBR 6118:2014 13.2.5.2 (+ 20.2 bordas/aberturas, 21.3.4). Laje
    lisa/cogumelo exige verificacao sempre. Demais lajes armadas em duas
    direcoes dispensam quando SIMULTANEAMENTE: (a) dim <= vao_menor/10;
    (b) dist face-eixo de apoio >= vao/4; (c) dist entre faces adjacentes >
    vao_menor/2. Secao remanescente deve equilibrar o ELU sem a abertura.
    """
    clausulas = [_FONTE_6118 + " 13.2.5", _FONTE_6118 + " 13.2.5.2",
                 _FONTE_6118 + " 20.2", _FONTE_6118 + " 21.3.4"]
    dim = _num(dim_abertura_mm); vao = _num(vao_menor_mm)
    dist_ap = _num(dist_apoio_mm); dist_adj = _num(dist_adjacente_mm)

    if laje_lisa is True:
        return {"veredito": VER_ACONFIRMAR,
                "motivos": ["laje lisa/cogumelo: verificacao de resistencia e "
                            "deformacao sempre exigida (13.2.5.2)"],
                "clausulas": list(clausulas)}
    if armadura_seccionada is True:
        return {"veredito": VER_REPROVADO,
                "motivos": ["interrompe armadura sem reposicao declarada "
                            "(20.2/21.3.4: proteger bordas com armadura "
                            "transversal e longitudinal)"],
                "clausulas": list(clausulas)}
    ausentes = []
    if dim is None:
        ausentes.append("dim_abertura_mm")
    if vao is None:
        ausentes.append("vao_menor_mm")
    if dist_ap is None:
        ausentes.append("dist_apoio_mm")
    if dist_adj is None:
        ausentes.append("dist_adjacente_mm")
    if laje_lisa is None:
        ausentes.append("laje_lisa")
    if armadura_seccionada is None:
        ausentes.append("armadura_seccionada")
    if ausentes:
        return {"veredito": VER_ACONFIRMAR,
                "motivos": ["dado ausente: %s - sem ele nao ha dispensa "
                            "(13.2.5.2) nem passe" % ", ".join(ausentes)],
                "clausulas": list(clausulas)}
    pend = []
    if not (dim <= vao / 10.0):
        pend.append("dimensao %.0f mm > vao_menor/10 (13.2.5.2(a))" % dim)
    if not (dist_ap >= vao / 4.0):
        pend.append("distancia ao apoio %.0f mm < vao/4 (13.2.5.2(b))" % dist_ap)
    if not (dist_adj > vao / 2.0):
        pend.append("distancia entre aberturas %.0f mm <= vao_menor/2 "
                    "(13.2.5.2(c))" % dist_adj)
    if pend:
        return {"veredito": VER_ACONFIRMAR,
                "motivos": ["dispensa nao atendida: %s - requer verificacao "
                            "de resistencia/deformacao da secao remanescente "
                            "no ELU (13.2.5/21.3.4)" % "; ".join(pend)],
                "clausulas": list(clausulas)}
    return {"veredito": VER_ADMISSIVEL,
            "motivos": ["dispensa atendida (13.2.5.2 a-c); proteger bordas com "
                        "armadura transversal e longitudinal (20.2)"],
            "clausulas": list(clausulas)}


def avalia_furo_vertical_viga(d_furo_mm=None, b_viga_mm=None, dist_face_mm=None,
                              cobrimento_mm=None, dist_entre_faces_mm=None,
                              estribo_por_intervalo=None):
    """Furo que atravessa a viga na direcao da altura - prumada vertical (G55).

    Fonte: NBR 6118:2014 21.3.3 (Figura 21.5): diametro <= b/3 (duro);
    distancia minima a face >= 5 cm e 2x cobrimento; furos alinhados com faces
    a >= 5 cm e cada intervalo com >= 1 estribo; secao remanescente deve
    resistir ao cisalhamento/flexao e permitir boa concretagem.
    """
    clausulas = [_FONTE_6118 + " 13.2.5", _FONTE_6118 + " 21.3.3"]
    d = _num(d_furo_mm); b = _num(b_viga_mm)
    dist_face = _num(dist_face_mm); cob = _num(cobrimento_mm)
    dist_ff = _num(dist_entre_faces_mm)

    ausentes = []
    if d is None:
        ausentes.append("d_furo_mm")
    if b is None:
        ausentes.append("b_viga_mm")
    if dist_face is None:
        ausentes.append("dist_face_mm")
    if cob is None:
        ausentes.append("cobrimento_mm")
    if ausentes:
        return {"veredito": VER_ACONFIRMAR,
                "motivos": ["dado ausente: %s - sem ele nao ha juizo "
                            "(21.3.3) nem passe" % ", ".join(ausentes)],
                "clausulas": list(clausulas)}
    if d > b / 3.0:
        return {"veredito": VER_REPROVADO,
                "motivos": ["diametro %.0f mm > b/3 (%.0f mm) - 21.3.3 veda" % (d,
                                                                              b / 3.0)],
                "clausulas": list(clausulas)}
    face_min = max(50.0, 2.0 * cob)
    if dist_face < face_min:
        return {"veredito": VER_REPROVADO,
                "motivos": ["distancia a face %.0f mm < minimo %.0f mm "
                            "(21.3.3)" % (dist_face, face_min)],
                "clausulas": list(clausulas)}
    pend = []
    if dist_ff is not None and dist_ff < max(50.0, d):
        pend.append("faces de furos a %.0f mm < max(5 cm, diametro) (21.3.3)"
                    % dist_ff)
    if estribo_por_intervalo is False:
        pend.append("intervalo sem estribo (21.3.3 exige >= 1 por intervalo)")
    if estribo_por_intervalo is None or dist_ff is None:
        pend.append("espaçamento/estribo entre furos nao declarado (21.3.3)")
    if pend:
        return {"veredito": VER_ACONFIRMAR,
                "motivos": ["atende b/3 e face minima, mas: %s - verificar "
                            "reducao ao cisalhamento/flexao" % "; ".join(pend)],
                "clausulas": list(clausulas)}
    return {"veredito": VER_ADMISSIVEL,
            "motivos": ["atende 21.3.3 (d <= b/3, face minima, furos alinhados "
                        "com estribo por intervalo); verificar secao "
                        "remanescente ao cisalhamento/flexao"],
            "clausulas": list(clausulas)}


def _guid(a, b, tipos, ocorrencia=1):
    """GUID determinístico e único para ocorrências repetidas do mesmo clash."""
    h = hashlib.sha1(("%s|%s|%s" % (a, b, tipos)).encode("utf-8")).hexdigest()
    guid = "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:32])
    return guid if ocorrencia == 1 else "%s~%d" % (guid, ocorrencia)


def _hint_do_clash(clash, cruzamentos):
    """Geometria declarada do cruzamento de um clash (G55).

    O tipo de peca NAO classifica furo: BeamxPipe existe nos dois mundos. So
    vira furo_previsto o clash que traz geometria declarada - no proprio dict
    ("cruzamento") ou no mapa cruzamentos[(a, b, tipos)]. Sem isso, e'
    conflito (comportamento anterior preservado).
    """
    hint = clash.get("cruzamento")
    if isinstance(hint, dict):
        return hint
    if isinstance(cruzamentos, dict):
        chave = (clash.get("a"), clash.get("b"), clash.get("tipos"))
        hint = cruzamentos.get(chave)
        if isinstance(hint, dict):
            return hint
    return None


def classifica_cruzamento(clash, cruzamento=None):
    """Categoria + veredito normativo de um clash (G55, criterio declarado).

    - esperado=True -> montagem (contato intencional, sem veredito).
    - sem geometria declarada -> conflito ("tipo de peca nao classifica furo").
    - direcao longitudinal (ou indefinida) -> conflito (embutido 13.2.6, nao furo).
    - transversal estrutura x instalacao em Beam -> furo (regra 13.2.5.1);
      em Slab -> furo (regra 13.2.5.2); em Column/Footing/Pile -> conflito
      (pilar/fundacao nao admite furo dispensado).
    - transversal fora de estrutura x instalacao -> conflito.
    Retorna {"categoria","veredito","motivos","clausulas"}.
    """
    esperado = bool(clash.get("esperado"))
    if esperado:
        return {"categoria": CAT_MONTAGEM, "veredito": None, "motivos": [],
                "clausulas": []}
    hint = cruzamento if isinstance(cruzamento, dict) else None
    if hint is None:
        hint = _hint_do_clash(clash, None)
    if not isinstance(hint, dict):
        return {"categoria": CAT_CONFLITO, "veredito": None,
                "motivos": ["sem geometria declarada do cruzamento: o tipo de "
                            "peca nao distingue furo previsto de conflito real"],
                "clausulas": []}
    direcao = hint.get("direcao")
    if direcao == "longitudinal":
        return {"categoria": CAT_CONFLITO, "veredito": None,
                "motivos": ["sobreposicao longitudinal: canalizacao embutida "
                            "segundo o eixo do elemento (13.2.6), nao furo "
                            "transversal - remanejar o tracado"],
                "clausulas": [_FONTE_6118 + " 13.2.6"]}
    if direcao != "transversal":
        return {"categoria": CAT_CONFLITO, "veredito": None,
                "motivos": ["direcao do cruzamento indefinida: sem passagem "
                            "transversal declarada nao ha furo previsto"],
                "clausulas": []}
    da, db = _disciplinas_do_par(clash.get("disciplinas", ""))
    if not ((da in _ESTRUTURA) ^ (db in _ESTRUTURA)):
        return {"categoria": CAT_CONFLITO, "veredito": None,
                "motivos": ["passagem transversal fora de estrutura x "
                            "instalacao: sem elemento estrutural que receba o "
                            "furo"],
                "clausulas": []}
    tipos = str(clash.get("tipos") or "")
    if "Slab" in tipos:
        v = avalia_abertura_laje(
            dim_abertura_mm=hint.get("d_furo_mm", hint.get("dim_abertura_mm")),
            vao_menor_mm=hint.get("vao_menor_mm"),
            dist_apoio_mm=hint.get("dist_apoio_mm"),
            dist_adjacente_mm=hint.get("dist_adjacente_mm"),
            laje_lisa=hint.get("laje_lisa"),
            armadura_seccionada=hint.get("armadura_seccionada"))
        return {"categoria": CAT_FURO, "veredito": v["veredito"],
                "motivos": v["motivos"], "clausulas": v["clausulas"]}
    if "Beam" in tipos:
        if hint.get("vertical") is True:
            v = avalia_furo_vertical_viga(
                d_furo_mm=hint.get("d_furo_mm"),
                b_viga_mm=hint.get("b_viga_mm"),
                dist_face_mm=hint.get("dist_face_mm"),
                cobrimento_mm=hint.get("cobrimento_mm"),
                dist_entre_faces_mm=hint.get("dist_entre_furos_mm"),
                estribo_por_intervalo=hint.get("estribo_por_intervalo"))
        else:
            v = avalia_furo_viga(
                d_furo_mm=hint.get("d_furo_mm"),
                h_viga_mm=hint.get("h_viga_mm"),
                dist_apoio_mm=hint.get("dist_apoio_mm"),
                zona_tracao=hint.get("zona_tracao"),
                dist_face_mm=hint.get("dist_face_mm"),
                cobrimento_mm=hint.get("cobrimento_mm"),
                dist_entre_furos_mm=hint.get("dist_entre_furos_mm"),
                furo_unico=bool(hint.get("furo_unico", False)),
                armadura_seccionada=hint.get("armadura_seccionada"),
                sob_torcao=bool(hint.get("sob_torcao", False)))
        return {"categoria": CAT_FURO, "veredito": v["veredito"],
                "motivos": v["motivos"], "clausulas": v["clausulas"]}
    return {"categoria": CAT_CONFLITO, "veredito": None,
            "motivos": ["elemento estrutural %s nao admite furo dispensado "
                        "(13.2.5.1 e' de vigas, 13.2.5.2 e' de lajes) - "
                        "remanejar o tracado" % tipos],
            "clausulas": [_FONTE_6118 + " 13.2.5"]}


def _acao_furo(da, db, veredito, motivos):
    """Acao do furo previsto: prever a passagem + verificar admissibilidade.

    Nunca "remanejar" e nunca passe automatico: admissivel ainda exige decisao
    registrada; a_confirmar nomeia o que falta; reprovado veda a aprovacao.
    """
    inst = db if da in _ESTRUTURA and db not in _ESTRUTURA else (
        da if db in _ESTRUTURA and da not in _ESTRUTURA else "coordenacao")
    det = "; ".join(motivos) if motivos else ""
    if veredito == VER_ADMISSIVEL:
        acao = ("Prever passagem (furo) na estrutura e detalhar armadura de "
                "contorno/cantos (21.3.1), com boa concretagem. Veredito "
                "admissivel - o fechamento exige decisao registrada "
                "(aprovador + justificativa). %s" % det)
    elif veredito == VER_REPROVADO:
        acao = ("Furo previsto REPROVADO pela regra (NBR 6118 13.2.5/21.3): "
                "%s Redimensionar a passagem ou remanejar o tracado - NAO "
                "pode ser aprovado como esta." % det)
    else:
        acao = ("Prever passagem (furo) na estrutura e verificar "
                "admissibilidade (NBR 6118 13.2.5/21.3, bielas e tirantes "
                "Secao 22 quando fora da dispensa): %s" % det)
    return (acao, inst)


def gerar_pendencias(rep_clash, prefixo="CLH", cruzamentos=None):
    """Uma pendencia rastreavel por clash. rep_clash = saida de
    checa_interferencia_federada. Ordena A REVISAR (por volume desc) antes dos
    esperados; ID CLH-NNN estavel pela ordem. Retorna lista de dicts.

    G55: cruzamentos (opcional) declara a geometria por clash
    {(a, b, tipos): {"direcao": "transversal"|"longitudinal", ...dims...}} -
    so com ela um clash vira furo_previsto; sem ela, o comportamento e'
    identico ao anterior (montagem x conflito).
    """
    clashes = rep_clash.get("clashes", [])
    # a revisar primeiro (por volume desc), depois esperados (por volume desc)
    ordenados = sorted(clashes, key=lambda c: (c.get("esperado", False),
                                               -c.get("vol_mm3", 0)))
    pend = []
    ocorrencias = {}
    for i, c in enumerate(ordenados, start=1):
        da, db = _disciplinas_do_par(c.get("disciplinas", ""))
        esperado = bool(c.get("esperado"))
        hint = _hint_do_clash(c, cruzamentos)
        cls = classifica_cruzamento(c, hint)
        categoria = cls["categoria"]
        veredito = cls["veredito"]
        if categoria == CAT_FURO:
            acao, resp = _acao_furo(da, db, veredito, cls["motivos"])
        else:
            acao, resp = _acao_e_responsavel(da, db, esperado)
        base_guid = _guid(c.get("a"), c.get("b"), c.get("tipos"))
        ocorrencia = ocorrencias.get(base_guid, 0) + 1
        ocorrencias[base_guid] = ocorrencia
        pend.append({
            "id": "%s-%03d" % (prefixo, i),
            "guid": _guid(c.get("a"), c.get("b"), c.get("tipos"), ocorrencia),
            "titulo": "Interferencia %s x %s" % (_NOME.get(da, da), _NOME.get(db, db)),
            "disciplina_a": da, "disciplina_b": db,
            "elemento_a": c.get("a"), "elemento_b": c.get("b"),
            "tipos": c.get("tipos"), "volume_mm3": c.get("vol_mm3"),
            "severidade": _severidade(c.get("vol_mm3", 0), esperado),
            "status": STATUS_APROVADO if esperado else STATUS_ABERTO,
            "esperado": esperado,
            "categoria": categoria,
            "veredito": veredito,
            "motivos": list(cls["motivos"]),
            "clausulas": list(cls["clausulas"]),
            "resolucao": None,
            "acao_sugerida": acao, "responsavel": resp,
        })
    return pend


def resumo(pendencias):
    """Contagens por status, severidade, par, categoria e veredito.

    G55: "abertas" exclui as Resolvidas - o gate e' "zero pendencias abertas
    nao resolvidas", nao "zero clashes".
    """
    por_status = {}; por_sev = {}; por_par = {}
    por_cat = {}; por_ver = {}
    for p in pendencias:
        por_status[p["status"]] = por_status.get(p["status"], 0) + 1
        por_sev[p["severidade"]] = por_sev.get(p["severidade"], 0) + 1
        par = "x".join(sorted((p["disciplina_a"], p["disciplina_b"])))
        por_par[par] = por_par.get(par, 0) + 1
        por_cat[p.get("categoria", CAT_CONFLITO)] = por_cat.get(
            p.get("categoria", CAT_CONFLITO), 0) + 1
        por_ver[str(p.get("veredito"))] = por_ver.get(str(p.get("veredito")), 0) + 1
    abertas = sum(1 for p in pendencias if p["status"] == STATUS_ABERTO)
    resolvidas = sum(1 for p in pendencias if p["status"] == STATUS_RESOLVIDA)
    return {"total": len(pendencias), "abertas": abertas,
            "resolvidas": resolvidas,
            "por_status": por_status, "por_severidade": por_sev, "por_par": por_par,
            "por_categoria": por_cat, "por_veredito": por_ver}


def pendencias_em_aberto(pendencias):
    """As pendencias que ainda prendem o gate (status Aberto)."""
    return [p for p in (pendencias or []) if p.get("status") == STATUS_ABERTO]


def gate_ok(pendencias):
    """Gate G55: True quando nao ha pendencia aberta nao resolvida."""
    return not pendencias_em_aberto(pendencias)


def _alvo_resolucao(req):
    for chave in ("id", "issue_id", "pendencia_id", "pendencia", "guid"):
        alvo = req.get(chave)
        if isinstance(alvo, str) and alvo.strip():
            return chave, alvo.strip()
    return None, None


def _aprovador_resolucao(req):
    for chave in ("aprovador", "approved_by", "autor", "responsavel_tecnico"):
        valor = req.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return None


def _justificativa_resolucao(req):
    for chave in ("justificativa", "justificacao", "justification", "motivo_aprovacao"):
        valor = req.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return None


def _eh_aprovacao_g55(req):
    """So e' aprovacao G55 (fecha o gate) o request que declara intento de
    aprovar: campos de aprovador/justificativa ou decisao explicita de
    aprovar. Nota legada de revisao (issue_id + status + note) e' so nota:
    registrada no manifesto, sem efeito no gate (texto nao fecha conflito)."""
    for chave in ("aprovador", "approved_by", "autor", "responsavel_tecnico",
                  "justificativa", "justificacao", "justification",
                  "motivo_aprovacao"):
        valor = req.get(chave)
        if isinstance(valor, str) and valor.strip():
            return True
    decisao = req.get("decisao", req.get("decision"))
    return (isinstance(decisao, str)
            and decisao.strip().lower() in ("aprovar", "aprovado", "approved",
                                            "aprovar_furo", "aprovar_furo_previsto"))


def aplicar_resolucoes(pendencias, resolution_requests):
    """Fecha pendencias por decisao registrada (G55).

    So o request com intento de aprovar (aprovador/justificativa ou decisao
    explicita) entra na via estrita: precisa de alvo (id/guid) + aprovador +
    justificativa, e o alvo precisa ser furo_previsto com veredito !=
    reprovado. Aprovacao sem justificativa, sem aprovador, de pendencia
    reprovada, de conflito ou de montagem FALHA (ValueError) - sem isso o
    mecanismo vira o botao de silenciar tudo. Nota legada de revisao
    (issue_id + status + note) nao fecha nem falha: e' so nota.
    Retorna NOVA lista (a de entrada nao e' mutada).
    """
    import copy as _copy

    novas = _copy.deepcopy(list(pendencias or []))
    reqs = list(resolution_requests or [])
    if not reqs:
        return novas
    por_id = {p.get("id"): p for p in novas}
    por_guid = {}
    for p in novas:
        por_guid.setdefault(p.get("guid"), p)
    vistas = set()
    for req in reqs:
        if not isinstance(req, dict):
            raise ValueError("resolucao_invalida: cada resolucao deve ser um objeto")
        if not _eh_aprovacao_g55(req):
            continue                      # nota de revisao: sem efeito no gate
        chave_alvo, alvo = _alvo_resolucao(req)
        if alvo is None:
            raise ValueError("resolucao_sem_alvo: toda aprovacao requer "
                             "id/guid da pendencia")
        pend = por_id.get(alvo)
        if pend is None and chave_alvo == "guid":
            pend = por_guid.get(alvo)
        if pend is None:
            raise ValueError("resolucao_alvo_inexistente: %s" % alvo)
        if pend["id"] in vistas:
            raise ValueError("resolucao_duplicada: %s" % pend["id"])
        vistas.add(pend["id"])
        aprovador = _aprovador_resolucao(req)
        if aprovador is None:
            raise ValueError("resolucao_sem_aprovador: %s (quem aprovou?)"
                             % pend["id"])
        justificativa = _justificativa_resolucao(req)
        if justificativa is None:
            raise ValueError("resolucao_sem_justificativa: %s (aprovacao sem "
                             "justificativa e' silenciamento, nao governanca)"
                             % pend["id"])
        if pend.get("categoria") != CAT_FURO:
            raise ValueError("resolucao_categoria_invalida: %s e' %s - so "
                             "furo_previsto fecha por decisao (conflito fecha "
                             "com remanejo, montagem ja e' aprovada)"
                             % (pend["id"], pend.get("categoria")))
        if pend.get("veredito") == VER_REPROVADO:
            raise ValueError("resolucao_veredito_reprovado: %s foi reprovado "
                             "pela regra (%s) - redimensionar ou remanejar, "
                             "nao aprovar" % (pend["id"],
                                              "; ".join(pend.get("motivos") or [])))
        pend["status"] = STATUS_RESOLVIDA
        pend["resolucao"] = {"aprovador": aprovador,
                             "justificativa": justificativa,
                             "veredito_na_aprovacao": pend.get("veredito")}
    return novas


def matriz_coordenacao(rep_clash):
    """Matriz disciplina x disciplina com o n de conflitos (por_par do clash).
    Retorna {disciplinas:[...ordenadas...], matriz:{da:{db:n}}}."""
    discs = set()
    m = {}
    for par, n in rep_clash.get("por_par", {}).items():
        da, db = _disciplinas_do_par(par)
        discs.add(da); discs.add(db)
        m.setdefault(da, {})[db] = n
        m.setdefault(db, {})[da] = n
    return {"disciplinas": sorted(discs), "matriz": m}


def bcf_topics(pendencias, autor="galpao_turnkey"):
    """Estrutura BCF-like (BIM Collaboration Format) - 1 topic por pendencia, com
    os campos do markup BCF (guid, title, topic_status, priority, labels,
    assigned_to). Serializavel em JSON para intercambio com plataformas BIM."""
    _PRIOR = {"Alta": "High", "Media": "Normal", "Baixa": "Low",
              "Informativa": "Low"}
    topics = []
    for p in pendencias:
        resolvida = p.get("status") == STATUS_RESOLVIDA
        labels = [p["disciplina_a"], p["disciplina_b"], p["severidade"]]
        if p.get("categoria") == CAT_FURO:
            labels.append(CAT_FURO)
        desc = "%s | %s : %s mm3 | Acao: %s" % (
            p["tipos"], "%s x %s" % (p["elemento_a"], p["elemento_b"]),
            p["volume_mm3"], p["acao_sugerida"])
        if p.get("veredito") is not None:
            desc += " | Veredito: %s (%s)" % (
                p["veredito"], "; ".join(p.get("motivos") or []))
        if isinstance(p.get("resolucao"), dict):
            desc += " | Resolucao: %s - %s (veredito: %s)" % (
                p["resolucao"].get("aprovador"),
                p["resolucao"].get("justificativa"),
                p["resolucao"].get("veredito_na_aprovacao"))
        topics.append({
            "guid": p["guid"],
            "title": "%s: %s" % (p["id"], p["titulo"]),
            "topic_type": "Clash",
            "topic_status": "Closed" if (p["esperado"] or resolvida) else "Open",
            "priority": _PRIOR.get(p["severidade"], "Normal"),
            "labels": labels,
            "assigned_to": p["responsavel"],
            "description": desc,
            "author": autor,
        })
    return {"bcf_version": "2.1-like", "topics": topics, "n": len(topics)}


def relatorio_pt(pendencias, res=None):
    """Relatorio-texto do documento de compatibilizacao."""
    res = res or resumo(pendencias)
    if res.get("resolvidas"):
        cab = ("Total: %d pendencias (%d ABERTAS nao resolvidas, %d resolvidas "
               "por decisao, %d aprovadas/montagem)" %
               (res["total"], res["abertas"], res["resolvidas"],
                res["total"] - res["abertas"] - res["resolvidas"]))
    else:
        cab = ("Total: %d pendencias (%d ABERTAS, %d aprovadas/montagem)" %
               (res["total"], res["abertas"], res["total"] - res["abertas"]))
    L = ["RELATORIO DE COMPATIBILIZACAO - PENDENCIAS DE COORDENACAO",
         "=" * 58,
         cab,
         "Severidade: " + " ; ".join("%s=%d" % (k, v)
                                     for k, v in sorted(res["por_severidade"].items())),
         "-" * 58]
    for p in pendencias:
        L.append("%-8s [%-11s] %-9s %s" %
                 (p["id"], p["severidade"], p["status"], p["titulo"]))
        L.append("         %s x %s (%s)  vol=%s mm3" %
                 (p["elemento_a"], p["elemento_b"], p["tipos"], p["volume_mm3"]))
        if p.get("categoria") == CAT_FURO:
            L.append("         [furo_previsto:%s] %s" %
                     (p.get("veredito"), "; ".join(p.get("motivos") or [])))
        L.append("         -> %s [resp: %s]" % (p["acao_sugerida"], p["responsavel"]))
        if isinstance(p.get("resolucao"), dict):
            L.append("         Resolvida por %s: %s [veredito: %s]" % (
                p["resolucao"].get("aprovador"),
                p["resolucao"].get("justificativa"),
                p["resolucao"].get("veredito_na_aprovacao")))
    if not pendencias:
        L.append("Nenhum conflito no modelo federado.")
    return "\n".join(L)


def _esc(txt):
    return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def matriz_svg(rep_clash, pendencias=None):
    """Matriz de coordenacao disciplina x disciplina (heatmap do n de conflitos) +
    resumo de severidade. SVG puro-Python, XML-valido (parse)."""
    mat = matriz_coordenacao(rep_clash)
    discs = mat["disciplinas"]
    pend = pendencias if pendencias is not None else gerar_pendencias(rep_clash)
    res = resumo(pend)
    n = len(discs)
    cell = 74
    x0, y0 = 240, 130
    W = max(880, x0 + n * cell + 60)
    H = max(520, y0 + n * cell + 190)

    def _t(x, y, s, size=13, anchor="middle", weight="normal", color="#111"):
        return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="Arial" font-size="{size}"'
                f' text-anchor="{anchor}" font-weight="{weight}" fill="{color}">'
                f'{_esc(s)}</text>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Arial">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           _t(W / 2, 46, "MATRIZ DE COMPATIBILIZACAO - CONFLITOS ENTRE DISCIPLINAS",
              20, weight="bold")]
    if n == 0:
        out.append(_t(W / 2, H / 2, "Nenhum conflito no modelo federado.", 15,
                      color="#0a0"))
        out.append("</svg>")
        return "\n".join(out)

    vmax = max((v for row in mat["matriz"].values() for v in row.values()), default=1)
    for j, dj in enumerate(discs):                 # colunas (cabecalho girado)
        cx = x0 + j * cell + cell / 2
        out.append(_t(cx, y0 - 12, _NOME.get(dj, dj)[:12], 11, anchor="middle",
                      color="#333"))
    for i, di in enumerate(discs):                 # linhas
        cy = y0 + i * cell + cell / 2
        out.append(_t(x0 - 12, cy + 4, _NOME.get(di, di)[:16], 11, anchor="end",
                      color="#333"))
        for j, dj in enumerate(discs):
            x = x0 + j * cell; y = y0 + i * cell
            v = mat["matriz"].get(di, {}).get(dj, 0) if di != dj else None
            if v is None:
                fill = "#e8e8e8"                    # diagonal (mesma disciplina)
            elif v == 0:
                fill = "#f4faf4"
            else:
                t = v / vmax
                fill = "#%02x%02x%02x" % (int(220 - 120 * t), int(90 + 40 * (1 - t)),
                                          int(70 + 30 * (1 - t)))
            out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                       f'fill="{fill}" stroke="#fff" stroke-width="2"/>')
            if v:
                out.append(_t(x + cell / 2, y + cell / 2 + 6, str(v), 20,
                              weight="bold", color="#fff"))

    # resumo por severidade
    ry = y0 + n * cell + 46
    out.append(_t(x0, ry, "PENDENCIAS: %d total ; %d ABERTAS" %
                  (res["total"], res["abertas"]), 14, anchor="start", weight="bold"))
    sev = res["por_severidade"]
    out.append(_t(x0, ry + 28, "Severidade  ->  " + " ; ".join(
        "%s: %d" % (k, sev[k]) for k in ("Alta", "Media", "Baixa", "Informativa")
        if k in sev), 12, anchor="start", color="#333"))
    out.append(_t(x0, ry + 54, "Numero na celula = conflitos entre o par (a instalacao "
                  "cede a estrutura; ver acao por pendencia).", 11, anchor="start",
                  color="#666"))
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------- selftest --------------------------------
def _selftest():
    rep = {"por_par": {"concretoxeletrico": 2, "concretoxhidraulica": 1},
           "clashes": [
               {"a": "C-P1E", "b": "E-CALHA", "disciplinas": "concretoxeletrico",
                "tipos": "ColumnxCableCarrier", "vol_mm3": 8.0e6, "esperado": False},
               {"a": "C-V1", "b": "H-TUBO", "disciplinas": "concretoxhidraulica",
                "tipos": "BeamxPipe", "vol_mm3": 6.0e5, "esperado": False},
               {"a": "C-P2D", "b": "E-DESC", "disciplinas": "concretoxeletrico",
                "tipos": "ColumnxCable", "vol_mm3": 3.0e5, "esperado": True}]}
    pend = gerar_pendencias(rep)
    # 3 pendencias, IDs sequenciais estaveis; a revisar antes do esperado
    assert [p["id"] for p in pend] == ["CLH-001", "CLH-002", "CLH-003"]
    assert pend[0]["severidade"] == "Alta" and pend[0]["volume_mm3"] == 8.0e6
    assert pend[1]["severidade"] == "Media"
    # o esperado vem por ultimo, Informativa/Aprovado
    assert pend[2]["esperado"] and pend[2]["status"] == STATUS_APROVADO
    assert pend[2]["severidade"] == "Informativa"
    # responsavel: estrutura x eletrica -> eletrica se adequa
    assert pend[0]["responsavel"] == "eletrico"
    # guid estavel (mesmo input -> mesmo guid)
    assert gerar_pendencias(rep)[0]["guid"] == pend[0]["guid"]

    r = resumo(pend)
    assert r["total"] == 3 and r["abertas"] == 2
    assert r["por_status"][STATUS_ABERTO] == 2 and r["por_status"][STATUS_APROVADO] == 1

    mat = matriz_coordenacao(rep)
    assert mat["matriz"]["concreto"]["eletrico"] == 2
    assert mat["matriz"]["eletrico"]["concreto"] == 2

    bcf = bcf_topics(pend)
    assert bcf["n"] == 3
    assert bcf["topics"][0]["topic_status"] == "Open"
    assert bcf["topics"][0]["priority"] == "High"
    assert bcf["topics"][2]["topic_status"] == "Closed"      # esperado

    # sem conflitos -> lista vazia, relatorio informa
    assert gerar_pendencias({"clashes": []}) == []
    assert "Nenhum conflito" in relatorio_pt([])

    # matriz SVG e' XML valido (parse, nao substring)
    from xml.dom.minidom import parseString
    svg = matriz_svg(rep, pend)
    assert svg.startswith("<svg") and "MATRIZ DE COMPATIBILIZACAO" in svg
    parseString(svg.encode("utf-8"))
    parseString(matriz_svg({"por_par": {}, "clashes": []}).encode("utf-8"))  # vazio
    return True


if __name__ == "__main__":
    _selftest()
    print("selftest OK")
