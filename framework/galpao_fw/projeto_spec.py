# ============================================================================
# projeto_spec.py - CONTRATO DE DADOS DO PROJETO (framework fino)
# Fonte UNICA da verdade de um projeto de galpao. A skill preenche o spec gate a
# gate; validar() BLOQUEIA o calculo e o desenho enquanto houver campo nao
# decidido. Os mappers (to_rodar_params / to_build_kwargs) traduzem o spec para
# os modulos - o builder e o orquestrador leem SO do spec, sem cair em default
# hardcoded (mata a copia de projetos anteriores).
#
# Estados de um campo:
#   PENDENTE  -> nao decidido: BLOQUEIA (template comeca tudo PENDENTE).
#   <valor>   -> decidido.
#   None      -> decidido "nenhum/nao" (ex: sem porta lateral, sem ponte).
#   valor + path em spec["_a_confirmar"] -> decidido provisorio (confirmar depois).
# ============================================================================
"""Contrato de dados do projeto de galpao + validador que bloqueia + mappers."""

from __future__ import annotations

import copy

PENDENTE = "__PENDENTE__"       # nao decidido -> bloqueia
P = PENDENTE

# Campos OBRIGATORIOS (dotted path -> descricao). Se == PENDENTE, faltando.
REQUERIDOS = [
    ("terreno.area_lote_m2", "area do lote (KML/coord)"),
    ("terreno.to_max", "taxa de ocupacao"),
    ("terreno.ca_max", "coef. de aproveitamento"),
    ("terreno.tp_min", "taxa de permeabilidade"),
    ("terreno.recuos", "recuos frente/lateral/fundos"),
    ("geometria.span", "vao transversal"),
    ("geometria.comprimento", "comprimento"),
    ("geometria.eave", "pe-direito"),
    ("geometria.bay", "espacamento de porticos"),
    ("geometria.base_fixed", "base rotulada/engastada"),
    ("cobertura.aguas", "numero de aguas"),
    ("cobertura.slope", "inclinacao"),
    ("cobertura.telha_tipo", "tipo de telha"),
    ("fechamento.tipo", "fechamento das paredes"),
    ("aberturas", "aberturas (Gate 4)"),
    ("vento.v0", "velocidade basica do vento"),
    ("vento.cat", "categoria de rugosidade"),
    ("vento.abertura_dominante", "abertura dominante (Cpi)"),
    ("ponte", "ponte rolante (dict ou None)"),
    ("cargas.G", "carga permanente de cobertura"),
    ("cargas.Q", "sobrecarga"),
    ("fundacao.sigma_solo_adm", "tensao admissivel do solo (sondagem/geotecnia)"),
    ("fundacao.tipo", "tipo de fundacao (sapata=rasa / estaca=profunda)"),
]

# Fundacao PROFUNDA (estaca): campos requeridos SO quando fundacao.tipo=="estaca".
# O perfil SPT e o tipo de estaca vem da SONDAGEM (Ask, Do Not Invent) -> sem
# default; PENDENTE/ausente bloqueia. D, L, FS tem default (A CONFIRMAR).
REQUERIDOS_ESTACA = [
    ("fundacao.estaca.perfil_spt", "perfil SPT da sondagem (camadas tipo/N/dz)"),
    ("fundacao.estaca.tipo_estaca", "tipo de estaca (pre_moldada/metalica/escavada/...)"),
]
TIPOS_FUNDACAO = ("sapata", "estaca", "bloco")
TIPOS_PORTICO = ("prismatico", "alma_variavel", "tesoura")

# Ponte rolante: campos do FABRICANTE requeridos SO quando spec["ponte"] != None.
# Sao dado de catalogo/projeto (Ask, Do Not Invent) - PENDENTE/ausente bloqueia.
# phi/n_ciclos podem vir das classes NBR 8400 (classe_hc/classe_b) OU direto.
REQUERIDOS_PONTE = [
    ("Q", "capacidade icada (kN)"),
    ("peso_ponte", "peso proprio da ponte (kN)"),
    ("peso_trole", "peso do trole/carro (kN)"),
    ("aprox_min", "aproximacao minima do gancho ao trilho (m)"),
    ("n_rodas_lado", "numero de rodas por lado (trilho)"),
    ("n_rodas_motoras", "numero de rodas MOTORAS por lado (frenagem)"),
    ("frac_lateral", "fracao do surto transversal (A CONFIRMAR)"),
    ("frac_long", "fracao da frenagem longitudinal (A CONFIRMAR)"),
]


def novo():
    """Template de spec: tudo PENDENTE. A skill preenche gate a gate."""
    return {
        "slug": P, "descricao": P,
        "terreno": {"kml": P, "area_lote_m2": P, "to_max": P, "ca_max": P,
                    "tp_min": P, "recuos": P, "n_pav": 1, "pts_xy_mm": None},
        # span = vao transversal (1 vao). Multi-vao: 'spans' = lista de larguras
        # de vao (m); None/1 item = 1 vao (retro). Cada vao com a mesma inclinacao.
        "geometria": {"span": P, "spans": None, "comprimento": P, "eave": P,
                      "ridge": P, "bay": P, "base_fixed": P},
        # chuva_I_mm_h: intensidade pluviometrica local (NBR 10844) p/ dimensionar
        # a calha. Default 150 (A CONFIRMAR regional); nao bloqueia.
        "cobertura": {"aguas": P, "slope": P, "telha_tipo": P, "telha_peso": P,
                      "calha": P, "chuva_I_mm_h": 150.0},
        # mesa_interna_travada: longarina sob succao. False (default seguro) =
        # mesa interna livre, Lb=vao cheio no FLT. True = mao-francesa trava a
        # mesa interna -> Lb menor (exige o detalhe). Nao bloqueia (tem default).
        "fechamento": {"tipo": P, "altura_alvenaria": None, "peso": P,
                       "mesa_interna_travada": False, "n_maos_francesas": None},
        "aberturas": P,     # dict {portao_frente, portao_fundo, porta_*, janelas_*}
        # tipo_portico: prismatico (default) | alma_variavel (misula tapered).
        # tapered = None p/ prismatico; dict {h_joelho,h_cumeeira,bf,tw,tf} (m).
        "estrutura": {"perfil_col": P, "perfil_raf": P, "contraventamento": P,
                      "tipo_portico": "prismatico", "tapered": None,
                      # trelica: None p/ nao-tesoura; dict {h,n_paineis,tipo,
                      # perfil_banzo,perfil_diagonal} quando tipo_portico=tesoura.
                      "trelica": None},
        "vento": {"v0": P, "cat": P, "classe": P, "s1": 1.0, "s3": P, "z": P,
                  "abertura_dominante": P},
        "ponte": P,         # None (sem ponte) ou dict de dados
        "cargas": {"G": P, "Q": P, "self": P, "tapamento": P},
        # Fundacao. tipo (sapata=rasa / estaca=profunda) BLOQUEIA. sigma_solo_adm
        # (kN/m2) BLOQUEIA - vem da sondagem, nao se inventa. Demais parametros da
        # sapata tem default (A CONFIRMAR). estaca=None ate tipo=="estaca": ai vira
        # dict {perfil_spt (sondagem), tipo_estaca, D, L, FS, bloco}.
        "fundacao": {"tipo": P, "sigma_solo_adm": P, "mu": 0.5, "coesao": 0.0,
                     "h_reaterro": 0.5, "fck": 25e3, "fyk": 500e3,
                     "cobrimento": 0.05, "phi_barra": 0.0125, "gamma_f": 1.4,
                     "estaca": None,
                     # divisa: None (sem pilar de divisa) OU dict {dist_divisa (m):
                     # distancia do eixo do pilar de divisa a linha do lote}. Dispara
                     # a sapata de divisa excentrica + viga alavanca (Alonso).
                     "divisa": None},
        # Viga de baldrame / amarracao entre fundacoes (NBR 6118). None = nao ha;
        # dict {b, h, q_parede, continuidade} = dimensiona (vao e N_amarracao do modelo).
        "baldrame": None,
        "fogo": None,         # None (sem verificacao) ou dict {TRRF_min, protecao,
                              # theta_critica_C (opc; default 550 flagado),
                              # protecao={tipo, espessura, lambda_p? c_p? rho_p?}
                              # (props termicas opc do BOLETIM; default calibrado flagado)}
        # neve: None (sem neve, default BR) OU dict {sk (carga no solo kN/m2,
        # regional - Ask-Do-Not-Invent), Ce, Ct, deslizamento_livre}. So relevante
        # em regioes serranas do Sul (SC/RS). EN 1991-1-3.
        "neve": None,
        "escada": None,       # None (sem escada) ou dict {desnivel, projecao, largura}
        "plataforma": None,   # None (sem plataforma) ou dict {L, b_trib, q_perm, q_acidental}
        "_a_confirmar": [],
    }


def _get(spec, path):
    o = spec
    for k in path.split("."):
        if not isinstance(o, dict) or k not in o:
            return KeyError
        o = o[k]
    return o


def validar(spec):
    """Retorna {faltando, a_confirmar, avisos, ok}. ok=False BLOQUEIA calculo/desenho.
    `avisos` = excecoes normativas ativas (nao bloqueiam, mas ficam na memoria de
    calculo para auditoria/ART)."""
    faltando = []
    avisos = []
    for path, desc in REQUERIDOS:
        v = _get(spec, path)
        if v is KeyError or v == PENDENTE:
            faltando.append((path, desc))
    # tipo de fundacao invalido bloqueia (so sapata|estaca)
    tipo = _get(spec, "fundacao.tipo")
    if tipo not in (KeyError, PENDENTE) and tipo not in TIPOS_FUNDACAO:
        faltando.append(("fundacao.tipo",
                         "valor invalido '%s' (use %s)" % (tipo, "/".join(TIPOS_FUNDACAO))))
    # fundacao profunda: perfil SPT + tipo de estaca sao da sondagem (bloqueiam)
    if tipo == "estaca":
        est = _get(spec, "fundacao.estaca")
        if est in (KeyError, None, PENDENTE) or not isinstance(est, dict):
            faltando.append(("fundacao.estaca", "bloco de estaca ausente (sondagem)"))
        else:
            for path, desc in REQUERIDOS_ESTACA:
                v = _get(spec, path)
                if v in (KeyError, None, PENDENTE, [], "") or v == PENDENTE:
                    faltando.append((path, desc))
            # Fator de seguranca global (NBR 6122): metodo semi-empirico SEM prova
            # de carga estatica -> FS >= 3,0. FS < 3,0 (ate 2,0) so e admitido COM
            # prova de carga na obra (fundacao.estaca.prova_de_carga = True). Sem a
            # flag, FS<3,0 BLOQUEIA (evita relatorio contra a norma).
            fs_est = _get(spec, "fundacao.estaca.FS")
            prova = _get(spec, "fundacao.estaca.prova_de_carga")
            if isinstance(fs_est, (int, float)) and fs_est < 3.0:
                if prova is not True:
                    faltando.append(
                        ("fundacao.estaca.FS",
                         "FS=%.2f < 3,0 exige prova de carga estatica (NBR 6122): "
                         "marque fundacao.estaca.prova_de_carga=True ou use FS>=3,0" % fs_est))
                else:
                    # excecao normativa ATIVA: fica na memoria de calculo (auditoria).
                    avisos.append(
                        ("fundacao.estaca.FS",
                         "FS=%.2f < 3,0 liberado por PROVA DE CARGA estatica (NBR 6122). "
                         "Validade do dimensionamento condicionada a execucao das provas "
                         "na obra - responsabilidade do engenheiro." % fs_est))
            # tipo de solo da sondagem: o motor (Aoki-Velloso) so aceita a lista
            # fechada NBR 6122. String invalida passava no validar e so quebrava no
            # meio da orquestracao (ValueError). Bloqueia aqui. Ver wiki 07 item D.
            perfil = _get(spec, "fundacao.estaca.perfil_spt")
            if isinstance(perfil, list):
                import estaca_profunda as _ep
                for camada in perfil:
                    t = isinstance(camada, dict) and camada.get("tipo")
                    if t and t not in _ep.TIPOS_SOLO:
                        faltando.append(
                            ("fundacao.estaca.perfil_spt",
                             "tipo de solo '%s' invalido; use um de: %s"
                             % (t, ", ".join(sorted(_ep.TIPOS_SOLO)))))
    # tipo de portico invalido bloqueia (prismatico|alma_variavel)
    tp = _get(spec, "estrutura.tipo_portico")
    if tp not in (KeyError, None, PENDENTE) and tp not in TIPOS_PORTICO:
        faltando.append(("estrutura.tipo_portico",
                         "valor invalido '%s' (use %s)" % (tp, "/".join(TIPOS_PORTICO))))
    # tesoura: n_paineis deve ser PAR (cumeeira em no; impar poe o apice no meio da
    # barra do banzo superior e reintroduz flexao -> invalida o metodo dos nos).
    if tp == "tesoura":
        tr = _get(spec, "estrutura.trelica")
        if isinstance(tr, dict):
            npn = tr.get("n_paineis", 8)
            if isinstance(npn, int) and npn % 2 != 0:
                faltando.append(("estrutura.trelica.n_paineis",
                                 "n_paineis=%d deve ser PAR (cumeeira em no; impar "
                                 "reintroduz flexao na tesoura)" % npn))
    # coluna de alma variavel (tapered): h_col_base opcional (rasa na base, funda
    # no joelho). Deve ser < h_joelho (senao a coluna nao afina) e > 2*tf (secao I
    # valida). Fora disso -> AVISO (nao bloqueia; alerta de geometria incoerente).
    if tp == "alma_variavel":
        tap = _get(spec, "estrutura.tapered")
        if isinstance(tap, dict) and tap.get("h_col_base") is not None:
            hcb = tap["h_col_base"]; hj = tap.get("h_joelho")
            tf = tap.get("tf", 0.0125)
            if isinstance(hcb, (int, float)):
                if isinstance(hj, (int, float)) and hcb >= hj:
                    avisos.append(("estrutura.tapered.h_col_base",
                                   "h_col_base=%.3f >= h_joelho=%.3f: coluna nao afina "
                                   "(base deve ser mais rasa que o joelho)" % (hcb, hj)))
                if hcb <= 2.0 * tf:
                    avisos.append(("estrutura.tapered.h_col_base",
                                   "h_col_base=%.3f <= 2*tf=%.4f: secao I invalida" % (hcb, 2.0 * tf)))
    # ponte rolante: se ha ponte (dict), os dados do fabricante bloqueiam. phi
    # exige classe_hc OU phi direto; n de ciclos exige classe_b OU n_ciclos.
    ponte = spec.get("ponte")
    if isinstance(ponte, dict):
        for k, desc in REQUERIDOS_PONTE:
            v = ponte.get(k)
            if v in (None, PENDENTE):
                faltando.append(("ponte." + k, desc))
        if ponte.get("phi") in (None, PENDENTE) and not ponte.get("classe_hc"):
            faltando.append(("ponte.phi", "impacto phi OU classe de elevacao HC (NBR 8400)"))
    # fogo: theta_critica (nivel de carregamento a quente) e as propriedades
    # termicas da protecao (lambda_p) sao de CATALOGO/BOLETIM do fabricante.
    # Ausentes -> default calibrado + AVISO (nao bloqueia, mas fica na memoria
    # p/ o eng. confirmar/ART). Ask-Do-Not-Invent, padrao dos demais gates.
    fogo = spec.get("fogo")
    if isinstance(fogo, dict):
        if fogo.get("theta_critica_C") in (None, PENDENTE):
            avisos.append(("fogo.theta_critica_C",
                           "theta_critica ausente -> assumindo 550 C (mu~0,6, NBR "
                           "14323). CONFIRMAR: depende do nivel de carregamento a "
                           "quente do perfil."))
        prot = fogo.get("protecao")
        if isinstance(prot, dict) and prot.get("tipo") in ("intumescente", "spray"):
            if prot.get("lambda_p") in (None, PENDENTE):
                avisos.append(("fogo.protecao.lambda_p",
                               "condutividade lambda_p da protecao '%s' ausente -> "
                               "usando valor TIPICO calibrado. CONFIRMAR com o "
                               "BOLETIM tecnico do fabricante." % prot["tipo"]))
    # neve: carga no solo sk e regional (Ask-Do-Not-Invent). Se ha bloco de neve
    # sem sk, avisa (nao bloqueia; default = sem neve).
    nv = spec.get("neve")
    if isinstance(nv, dict) and not nv.get("sk"):
        avisos.append(("neve.sk", "bloco de neve sem 'sk' (carga no solo kN/m2) - "
                       "dado REGIONAL (EN 1991-1-3 / mapa local). Sem sk = sem neve."))
    # cobertura de 1 agua (shed): suportada para 1 VAO (portico assimetrico, colunas
    # de alturas diferentes). Multi-vao de 1 agua (dente-de-serra) ainda NAO -> so
    # esse caso bloqueia (evita modelo errado).
    aguas = _get(spec, "cobertura.aguas")
    _sp = _get(spec, "geometria.spans")
    _nv = len(_sp) if isinstance(_sp, (list, tuple)) else 1
    if aguas == 1 and _nv > 1:
        faltando.append(("cobertura.aguas",
                         "telhado de 1 agua (shed) MULTI-VAO (dente-de-serra) ainda "
                         "nao suportado; use 1 vao ou 2 aguas."))
    # --- COERENCIA geometrica / fisica. O wizard deriva e faz faixa (caminho
    # guiado seguro), mas o caminho SPEC-DIRETO (carregar_spec/JSON editado) so
    # checava PENDENTE: geometria degenerada (span<0, ridge<=eave, slope<=0,
    # V0=0, aguas invalido, abertura > fachada) era CERTIFICADA como ATENDE - o
    # pior modo de falha de uma ferramenta de certificacao. Bloqueia aqui. So
    # valida valores JA decididos (concretos); PENDENTE fica com a checagem acima.
    def _num(path):
        v = _get(spec, path)
        return v if (isinstance(v, (int, float)) and not isinstance(v, bool)) else None
    for path, desc in (("geometria.span", "vao transversal"),
                       ("geometria.comprimento", "comprimento"),
                       ("geometria.eave", "pe-direito/beiral"),
                       ("geometria.bay", "espacamento de porticos")):
        v = _num(path)
        if v is not None and v <= 0:
            faltando.append((path, "%s deve ser > 0 (recebido %g)" % (desc, v)))
    if isinstance(_sp, (list, tuple)):
        for i, sv in enumerate(_sp):
            if not (isinstance(sv, (int, float)) and not isinstance(sv, bool)) or sv <= 0:
                faltando.append(("geometria.spans[%d]" % i,
                                 "largura de cada vao deve ser > 0 (recebido %r)" % (sv,)))
    _slope = _num("cobertura.slope")
    if _slope is not None and _slope <= 0:
        faltando.append(("cobertura.slope",
                         "inclinacao deve ser > 0: telhado plano nao drena e invalida "
                         "o vento de cobertura NBR 6123 (recebido %g)" % _slope))
    _ridge = _num("geometria.ridge"); _eave = _num("geometria.eave")
    if _ridge is not None and _eave is not None and _ridge <= _eave:
        faltando.append(("geometria.ridge",
                         "cumeeira (%.2f m) deve ser > beiral (%.2f m); ridge<=eave = "
                         "telhado plano/invertido (geometria impossivel)" % (_ridge, _eave)))
    if isinstance(aguas, int) and aguas not in (1, 2):
        faltando.append(("cobertura.aguas",
                         "numero de aguas=%d invalido (use 1=shed ou 2=simetrico)" % aguas))
    _v0 = _num("vento.v0")
    if _v0 is not None and _v0 < 30.0:
        faltando.append(("vento.v0",
                         "V0=%g m/s abaixo do minimo do mapa de isopletas NBR 6123 "
                         "(~30 m/s); confira o dado de sitio" % _v0))
    # aberturas nao podem exceder a envoltoria (portao/janela > fachada e Cpi de
    # abertura dominante sem sentido fisico). Dims em mm; envelope generoso
    # (largura <= maior dim em planta; altura <= cumeeira) p/ nao vetar projeto real.
    _ab = spec.get("aberturas")
    if isinstance(_ab, dict) and _ridge and (_eave or _num("geometria.span")):
        _wmax_mm = max(_num("geometria.span") or 0.0,
                       _num("geometria.comprimento") or 0.0) * 1000.0
        _hmax_mm = _ridge * 1000.0
        for _k, _v in _ab.items():
            if isinstance(_v, (list, tuple)) and len(_v) >= 2 \
                    and all(isinstance(x, (int, float)) for x in _v[:2]):
                _w, _h = _v[0], _v[1]
                if _wmax_mm and _w > _wmax_mm:
                    faltando.append(("aberturas." + _k,
                                     "largura %.0f mm excede a fachada (%.0f mm)" % (_w, _wmax_mm)))
                if _hmax_mm and _h > _hmax_mm:
                    faltando.append(("aberturas." + _k,
                                     "altura %.0f mm excede a cumeeira (%.0f mm)" % (_h, _hmax_mm)))
    return {"faltando": faltando, "a_confirmar": list(spec.get("_a_confirmar", [])),
            "avisos": avisos, "ok": not faltando}


def exigir_completo(spec):
    """Levanta se o spec nao estiver completo (para o builder/orquestrador)."""
    r = validar(spec)
    if not r["ok"]:
        itens = "; ".join(f"{p} ({d})" for p, d in r["faltando"])
        raise ValueError("ProjetoSpec incompleto - decida antes de prosseguir: "
                         + itens)
    return True


def resumo_pt(spec):
    r = validar(spec)
    L = ["=" * 68, f"PROJETO SPEC - {spec.get('slug')}", "=" * 68]
    if r["faltando"]:
        L.append(f"  PENDENTE ({len(r['faltando'])}): BLOQUEIA calculo/desenho")
        for p, d in r["faltando"]:
            L.append(f"    - {p} : {d}")
    else:
        L.append("  COMPLETO: todos os campos obrigatorios decididos.")
    if r["a_confirmar"]:
        L.append(f"  A CONFIRMAR ({len(r['a_confirmar'])}): valor provisorio")
        for p in r["a_confirmar"]:
            L.append(f"    - {p}")
    L.append("=" * 68)
    return "\n".join(L)


# ---- carga de parede (caminho de carga fisico) ------------------------------
def cargas_parede(fechamento, eave, bay, telha_peso=0.10):
    """Peso da parede de fechamento no caminho de carga FISICO. Pura (testavel).
    eave/bay em m; peso em kN/m2. Retorna kN:
      w_col_kN_m        fechamento LEVE (telha/painel) pendurado nas longarinas ->
                        UDL vertical na coluna externa [kN/m de altura de coluna]
      w_masonry_kN_m    ALVENARIA autoportante -> carga linear no baldrame [kN/m]
      N_masonry_ext_kN  ALVENARIA -> reacao vertical na fundacao por coluna externa [kN]

    Caminhos SEPARADOS (fisicamente corretos):
    - telha/painel leve: pendura na estrutura -> coluna de aco -> base -> fundacao.
    - alvenaria autoportante: desce pela viga de BALDRAME -> sapatas; NAO carrega a
      coluna de aco (so estabiliza a fundacao contra uplift).
    - alvenaria_telha: alvenaria (ate altura_alvenaria) -> baldrame/fundacao; telha
      acima -> coluna.
    As paredes longitudinais descarregam nos DOIS pilares externos (tributaria =
    'bay'). Antes o peso era coletado e IGNORADO (contra-seguranca); o passo anterior
    somava tudo na coluna (conservador); aqui rota-se corretamente, ja que o sinal
    de reacao do frame2d foi consertado."""
    fe = fechamento or {}
    tipo = fe.get("tipo", "telha")
    peso = fe.get("peso") or 0.0
    h_alv = fe.get("altura_alvenaria") or 0.0
    P_light = 0.0                                     # leve por coluna externa [kN]
    w_mas = 0.0                                       # alvenaria linear [kN/m]
    if tipo in ("telha", "aberto", None):
        P_light = (peso * eave) * bay                 # leve em toda a altura -> coluna
    elif tipo == "alvenaria":
        h = h_alv if h_alv > 0 else eave              # alvenaria cheia ate o beiral
        w_mas = peso * h                              # -> baldrame/fundacao (nao coluna)
    elif tipo == "alvenaria_telha":
        h = h_alv if h_alv > 0 else eave / 2.0        # meia-parede (default)
        w_mas = peso * h                              # alvenaria -> fundacao
        h_telha = max(0.0, eave - h)
        P_light = (telha_peso * h_telha) * bay        # telha acima -> coluna
    else:
        P_light = (peso * eave) * bay                 # tipo desconhecido: conservador
    w_col = (P_light / eave) if eave > 0 else 0.0
    return {"w_col_kN_m": round(w_col, 4),
            "w_masonry_kN_m": round(w_mas, 3),
            "N_masonry_ext_kN": round(w_mas * bay, 3)}


# ---- aberturas: convencao do spec (L,H) -> convencao do build 3D ------------
def _janela_band(janela, eave_mm, peitoril_mm=1100.0):
    """Converte a janela do wizard (largura, altura[, peitoril]) em mm para a
    FAIXA de elevacao (z_base, z_topo) que o build_galpao espera para
    'janelas_laterais'. Pura. Sem a conversao o build recebia (L,H) e montava um
    box de altura negativa -> 'height of box too small' (ver bug-janela-lateral)."""
    if not janela:
        return None
    vals = list(janela)
    H = vals[1] if len(vals) >= 2 else 0.0
    peit = vals[2] if len(vals) >= 3 else peitoril_mm
    z_base = max(0.0, peit)
    z_topo = z_base + max(0.0, H)
    if eave_mm:                                   # nao atravessar o beiral
        z_topo = min(z_topo, eave_mm - 100.0)
        z_base = min(z_base, max(0.0, z_topo - 100.0))
    return (round(z_base, 1), round(z_topo, 1))


def aberturas_para_build(aberturas, eave_mm):
    """Traduz o dict de aberturas do spec (janela = L,H) para a convencao do
    build_galpao (janela = faixa z_base,z_topo). Portao/porta ficam (L,H). Pura."""
    ab = dict(aberturas or {})
    for chave in ("janelas_laterais", "janelas_frontais"):
        if ab.get(chave):
            ab[chave] = _janela_band(ab[chave], eave_mm)
    return ab


# ---- mappers: spec -> modulos ----------------------------------------------
def to_rodar_params(spec):
    """Traduz o spec para os params do orquestrador (rodar_galpao). Parte do
    PARAMS_REF (perfis placeholder + ligacoes que o redimensionamento refina) e
    SOBRESCREVE tudo que e decisao do projeto (geometria, vento, cargas, ponte)."""
    exigir_completo(spec)
    import rodar_galpao as R
    p = copy.deepcopy(R.PARAMS_REF)
    g = spec["geometria"]
    # multi-vao: geometria.spans (lista de larguras de vao, m). span0 = 1o vao
    # (define a inclinacao/ridge, iguais por vao); span "total" = soma (largura
    # transversal do galpao, p/ vento etc.). Sem spans -> 1 vao (retro).
    spans = g.get("spans") if isinstance(g.get("spans"), (list, tuple)) else None
    span0 = spans[0] if spans else g["span"]
    ridge = g["ridge"] if g.get("ridge") not in (None, PENDENTE) else \
        g["eave"] + spec["cobertura"]["slope"] * span0 / 2.0
    p["geometria"] = {"span": (sum(spans) if spans else g["span"]),
                      "comprimento": g["comprimento"],
                      "eave": g["eave"], "ridge": ridge, "bay": g["bay"]}
    if spans and len(spans) > 1:
        p["geometria"]["spans"] = list(spans)
    p["base_fixed"] = g["base_fixed"]
    c = spec["cargas"]
    p["cargas"] = {"G": c["G"], "self": c.get("self", 0.35), "Q": c["Q"]}
    v = spec["vento"]
    p["vento"] = {"v0": v["v0"], "cat": v["cat"], "classe": v.get("classe", "B"),
                  "s1": v.get("s1", 1.0), "s3": v["s3"], "z": v.get("z", ridge),
                  "abertura_dominante": v.get("abertura_dominante", "portao_oitao")}
    p["aguas"] = spec.get("cobertura", {}).get("aguas", 2)   # 1=shed, 2=simetrico
    fe = spec.get("fechamento", {})     # longarina: travamento da mesa interna
    lg = p.setdefault("secundarios", {}).setdefault("longarina", {})
    lg["mesa_interna_travada"] = bool(fe.get("mesa_interna_travada", False))
    if fe.get("n_maos_francesas") not in (None, PENDENTE):
        lg["n_maos_francesas"] = fe["n_maos_francesas"]
    # peso da parede de fechamento no caminho de carga (antes: coletado e ignorado).
    p["parede"] = cargas_parede(fe, g["eave"], g["bay"],
                                telha_peso=spec.get("cobertura", {}).get("telha_peso", 0.10))
    # viabilidade urbanistica (TO/CA/TP + recuos): mapeia o terreno p/ o gate rodar
    # (antes: coletado no wizard e IGNORADO - o gate nunca recebia params[terreno]).
    tr = spec.get("terreno") or {}
    if tr.get("area_lote_m2") not in (None, PENDENTE):
        rc = tr.get("recuos") or {}
        p["terreno"] = {"area_lote_m2": tr["area_lote_m2"],
                        "to_max": tr.get("to_max", 0.6), "ca_max": tr.get("ca_max", 1.0),
                        "tp_min": tr.get("tp_min", 0.2),
                        "recuo_frente": rc.get("frente", 0.0),
                        "recuo_lateral": rc.get("lateral", 0.0),
                        "recuo_fundos": rc.get("fundos", 0.0),
                        "n_pav": tr.get("n_pav", 1)}
        if tr.get("pts_xy_mm"):     # com o poligono do lote, checa tambem os recuos
            p["terreno"]["pts_xy"] = [(x / 1000.0, y / 1000.0)
                                      for x, y in tr["pts_xy_mm"]]
    fu = spec.get("fundacao") or {}     # sapata: sobrescreve os defaults do solo
    if fu:
        p.setdefault("fundacao", {}).update(
            {k: v for k, v in fu.items()
             if k not in ("tipo", "estaca") and v not in (None, PENDENTE)})
        # tipo de fundacao rasa: sapata (armada) x bloco (concreto simples, NBR 6122
        # 7.8.2). O rodar_galpao escolhe dimensiona_sapata_env vs dimensiona_bloco_env.
        p.setdefault("fundacao", {})["tipo"] = fu.get("tipo", "sapata")
    # fundacao PROFUNDA: monta o cfg da estaca (perfil SPT da sondagem) que o
    # rodar_galpao consome (verifica_estaca). SO quando tipo=="estaca" (exclusivo
    # da sapata). Nada de dado geometrico inventado: tudo vem do bloco 'estaca'.
    if fu.get("tipo") == "estaca" and isinstance(fu.get("estaca"), dict):
        e = fu["estaca"]
        # FS default 3,0 (NBR 6122 semi-empirico s/ prova de carga); 2,0 so com
        # prova de carga (barrado no validar()).
        ec = {"perfil": e["perfil_spt"], "D": e.get("D", 0.30),
              "L": e.get("L", 10.0), "tipo_estaca": e.get("tipo_estaca", "pre_moldada"),
              "FS": e.get("FS", 3.0)}
        for opt in ("N_ponta", "bloco", "grupo", "camadas_neg", "recalque_grupo",
                    "FS_tracao"):
            if e.get(opt) is not None:
                ec[opt] = e[opt]
        p["estaca"] = ec
    else:
        p.pop("estaca", None)           # tipo=sapata: garante que nao ha estaca
    # viga de baldrame: opt-in pelo spec (sobrescreve o default do PARAMS_REF).
    bal = spec.get("baldrame")
    if isinstance(bal, dict):
        p.setdefault("baldrame", {}).update(
            {k: v for k, v in bal.items() if v not in (None, PENDENTE)})
    # calha (dimensionamento hidraulico): roda quando ha calha na cobertura;
    # intensidade pluviometrica local (NBR 10844).
    cob = spec.get("cobertura", {})
    p["calha"] = bool(cob.get("calha")) and cob.get("calha") != PENDENTE
    ci = cob.get("chuva_I_mm_h")
    if ci not in (None, PENDENTE):
        p["chuva_I_mm_h"] = ci
    # sapata de divisa: so quando o gate fundacao.divisa e informado.
    dv = fu.get("divisa")
    if isinstance(dv, dict):
        p["divisa"] = dv
    # tipo de portico (prismatico|alma_variavel) + misula tapered.
    est0 = spec.get("estrutura", {})
    p["tipo_portico"] = est0.get("tipo_portico", "prismatico")
    if est0.get("tipo_portico") == "alma_variavel" and isinstance(est0.get("tapered"), dict):
        p["tapered"] = est0["tapered"]
    # opt-in: creditar o alivio de cortante das mesas inclinadas (equilibrio; refino
    # nao-normativo). Default False (conservador). Ver cortante_tapered.py.
    p["creditar_cortante_mesa_inclinada"] = bool(
        est0.get("creditar_cortante_mesa_inclinada", False))
    if est0.get("tipo_portico") == "tesoura" and isinstance(est0.get("trelica"), dict):
        p["trelica"] = est0["trelica"]
    p["ponte"] = spec["ponte"] if spec["ponte"] else None
    if spec["ponte"]:
        import ponte_rolante as pr
        p["ponte"].setdefault("perfil_viga", pr.VS500)
        p["ponte"].setdefault("fy", 250e3)
        p["ponte"].setdefault("E_Ix", pr.ck.E * pr.VS500["Ix"])
    p["fogo"] = spec.get("fogo") if spec.get("fogo") else None
    p["neve"] = spec.get("neve") if spec.get("neve") else None
    p["escada"] = spec.get("escada") if spec.get("escada") else None
    p["plataforma"] = spec.get("plataforma") if spec.get("plataforma") else None
    return p


def to_build_kwargs(spec):
    """Traduz o spec para os kwargs de build_galpao.configurar (geometria +
    aberturas + fechamento + terreno). NADA vem de default hardcoded."""
    exigir_completo(spec)
    g = spec["geometria"]
    # perfil ADOTADO (redimensionamento) -> secao do modelo (h,b,tw,tf em mm).
    import perfis
    est = spec.get("estrutura", {})

    def _sec(nome):
        p = perfis.PERFIS.get(nome) if nome else None
        return (p["d"] * 1000, p["bf"] * 1000, p["tw"] * 1000, p["tf"] * 1000) if p else None
    col_nome = est.get("perfil_col_adotado")
    raf_nome = est.get("perfil_raf_adotado")

    def _maior(a, b):
        pa, pb = perfis.PERFIS.get(a), perfis.PERFIS.get(b)
        if pa and pb:
            return a if pa["d"] >= pb["d"] else b
        return a or b
    esc_nome = _maior(est.get("perfil_escora"), est.get("perfil_montante"))
    jo = est.get("joelho_adotado")
    tipo_fund = spec.get("fundacao", {}).get("tipo")
    profunda = tipo_fund == "estaca"
    ea = est.get("estaca_adotada"); bo = est.get("bloco_adotado")
    bl = est.get("baldrame_adotado")
    _spans = g.get("spans") if isinstance(g.get("spans"), (list, tuple)) else None
    return {
        "length": g["comprimento"] * 1000.0, "span": g["span"] * 1000.0,
        # multi-vao: passa a lista de vaos (mm) ao build 3D; None -> 1 vao.
        "spans": ([s * 1000.0 for s in _spans] if _spans and len(_spans) > 1 else None),
        "eave_h": g["eave"] * 1000.0, "slope": spec["cobertura"]["slope"],
        "bay": g["bay"] * 1000.0, "aguas": spec.get("cobertura", {}).get("aguas", 2),
        "aberturas": aberturas_para_build(spec["aberturas"], g["eave"] * 1000.0),
        "fechamento": spec["fechamento"],
        "terreno_pts": spec["terreno"].get("pts_xy_mm"),
        "perfil_col": _sec(col_nome), "perfil_raf": _sec(raf_nome),
        "perfil_col_nome": col_nome, "perfil_raf_nome": raf_nome,
        "perfil_esc": _sec(esc_nome), "perfil_esc_nome": esc_nome,
        "terca": est.get("terca_dims"),
        "longarina": est.get("longarina_dims"),
        "longarina_nome": est.get("longarina_perfil"),
        "n_tirante_parede": est.get("n_tirante_parede"),
        "joelho": ({"t": jo["t"] * 1000, "db": jo["db"] * 1000, "n": jo["n"]}
                   if jo else None),
        "base": ({"B": ba["B"] * 1000, "L": ba["L"] * 1000, "t": ba["t"] * 1000,
                  "db": ba["db"] * 1000, "n": ba["n"]}
                 if (ba := est.get("base_adotada")) else None),
        # fundacao RASA (sapata): so quando tipo!=estaca (exclusivo - mne-2).
        "sapata": ({"B": sa["B"] * 1000, "L": sa["L"] * 1000, "h": sa["h"] * 1000,
                    "ped": spec.get("fundacao", {}).get("h_ped", 0.5) * 1000}
                   if (not profunda and (sa := est.get("sapata_adotada"))) else None),
        # fundacao PROFUNDA (estaca + bloco + baldrame): dims do CALCULO em mm.
        "estaca": ({"D": ea["D"] * 1000, "L": ea["L"] * 1000, "n": ea["n"],
                    "espacamento": ea.get("espacamento", 3.0 * ea["D"]) * 1000,
                    "tipo": ea.get("tipo")}
                   if (profunda and ea) else None),
        "bloco": ({"h": bo["h"] * 1000, "a": bo.get("a", 0.30) * 1000,
                   "B": bo.get("B", bo.get("a", 0.30)) * 1000,
                   "L": bo.get("L", bo.get("a", 0.30)) * 1000}
                  if (profunda and bo) else None),
        "baldrame": ({"b": bl["b"] * 1000, "h": bl["h"] * 1000,
                      "vao": bl.get("vao", g["bay"]) * 1000}
                     if (profunda and bl) else None),
        # portico de alma variavel: tipo + misula tapered (alturas em mm p/ o loft).
        "tipo_portico": est.get("tipo_portico", "prismatico"),
        "tapered": ({"h_joelho": tap["h_joelho"] * 1000, "h_cumeeira": tap["h_cumeeira"] * 1000,
                     "bf": tap.get("bf", 0.20) * 1000, "tw": tap.get("tw", 0.008) * 1000,
                     "tf": tap.get("tf", 0.0125) * 1000,
                     **({"h_col_base": tap["h_col_base"] * 1000}
                        if tap.get("h_col_base") is not None else {})}
                    if (est.get("tipo_portico") == "alma_variavel"
                        and isinstance(tap := est.get("tapered"), dict)) else None),
        # portico trelicado (tesoura): geometria (m) + perfis (mm) p/ desenhar as barras.
        "trelica": ({"h": tr["h"], "n_paineis": tr.get("n_paineis", 8),
                     "tipo": tr.get("tipo", "warren"),
                     "d_banzo": max(tr["perfil_banzo"][0], tr["perfil_banzo"][1]) * 1000,
                     "d_diag": max(tr["perfil_diagonal"][0], tr["perfil_diagonal"][1]) * 1000}
                    if (est.get("tipo_portico") == "tesoura"
                        and isinstance(tr := est.get("trelica"), dict)) else None),
        "ponte_modelo": ({"Hvr": spec["ponte"].get("Hvr", 4.5) * 1000.0,
                          "excentricidade": spec["ponte"].get("excentricidade", 0.3) * 1000.0}
                         if spec["ponte"] else None),
        # reforco da zona de painel do joelho (doubler/enrijecedor) - so quando o
        # calculo exigiu (zona_painel_adotado.precisa_*). Espessuras em mm.
        "reforco_joelho": ({"t_doubler": zp.get("t_doubler_mm", 0.0),
                            "enrijecedor": bool(zp.get("precisa_enrijecedor"))}
                           if (isinstance(zp := est.get("zona_painel_adotado"), dict)
                               and (zp.get("precisa_reforco") or zp.get("precisa_enrijecedor")))
                           else None),
    }


def marcar_a_confirmar(spec, *paths):
    for p in paths:
        if p not in spec["_a_confirmar"]:
            spec["_a_confirmar"].append(p)


def _selftest():
    s = novo()
    r = validar(s)
    assert not r["ok"] and len(r["faltando"]) == len(REQUERIDOS)   # template bloqueia
    # preenche o minimo
    s["slug"] = "teste"
    s["terreno"].update(area_lote_m2=982.0, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={"frente": 5, "lateral": 1.5, "fundos": 3})
    s["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                         bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal", calha=True)
    s["fechamento"].update(tipo="alvenaria_telha", altura_alvenaria=2.5, peso=0.12)
    s["aberturas"] = {"portao_frente": (4000, 4500), "porta_fundo": (900, 2130),
                      "janelas_laterais": (4300, 5300), "porta_lateral": None,
                      "portao_fundo": None, "porta_frente": None}
    s["vento"].update(v0=35.0, cat="II", classe="B", s3=0.95, z=6.5,
                      abertura_dominante="portao_oitao")
    marcar_a_confirmar(s, "vento.v0", "terreno.to_max")
    s["ponte"] = None
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.10)
    s["fundacao"]["sigma_solo_adm"] = 200.0        # kN/m2 (sondagem)
    s["fundacao"]["tipo"] = "sapata"
    r = validar(s)
    print(resumo_pt(s))
    assert r["ok"], r["faltando"]
    # fundacao profunda: tipo=estaca exige perfil SPT + tipo de estaca (sondagem)
    s2 = copy.deepcopy(s)
    s2["fundacao"]["tipo"] = "estaca"
    assert validar(s2)["ok"] is False                # falta o bloco de estaca
    s2["fundacao"]["estaca"] = {
        "perfil_spt": [{"tipo": "areia_siltosa", "N": 20, "dz": 8.0}],
        "tipo_estaca": "pre_moldada", "D": 0.30, "L": 8.0, "FS": 3.0}
    assert validar(s2)["ok"], validar(s2)["faltando"]
    # FS < 3,0 SEM prova de carga BLOQUEIA (NBR 6122 semi-empirico)
    s3 = copy.deepcopy(s2)
    s3["fundacao"]["estaca"]["FS"] = 2.0
    r3 = validar(s3)
    assert r3["ok"] is False and any("FS" in p for p, _ in r3["faltando"]), r3
    # com prova de carga, FS=2,0 e liberado E registra aviso de auditoria
    s3["fundacao"]["estaca"]["prova_de_carga"] = True
    r3b = validar(s3)
    assert r3b["ok"], r3b["faltando"]
    assert any("FS" in p for p, _ in r3b["avisos"]), r3b   # excecao normativa auditada
    # remover um obrigatorio volta a bloquear
    s["geometria"]["bay"] = PENDENTE
    assert validar(s)["ok"] is False
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
