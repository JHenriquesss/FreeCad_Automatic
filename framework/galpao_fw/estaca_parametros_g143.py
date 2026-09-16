# ============================================================================
# estaca_parametros_g143.py - G143: OS PARAMETROS DA FUNDACAO DO GALPAO SEM
# DEFAULT SILENCIOSO (D102: default que decide veredito — declarar ou recusar).
#
# Medido (2026-09-15, antes de mudar, galpao 10x40x6, tipo_fundacao="estaca",
# perfil SPT de tests/test_build_concreto.py:114):
# - sem D_estaca/L_estaca a conta usava D=0,30 m / L=8,0 m calados
#   (galpao_concreto.py:351) e a PE-CO-04 desenhava "D30 L8" como projeto;
# - L 8->10 m: util 0,116->0,103 e geometria "L8"->"L10"; D 0,30->0,40 m:
#   util 0,116->0,071; L=0: n 1->5 em silencio; D=0: TypeError cru;
# - tipo_estaca pre_moldada->escavada: util 0,116->0,198; com Q_roof=0,25 e
#   L=6 no perfil fraco a pre_moldada ATENDE (n=2) e a escavada REPROVA
#   (n=4) — o tipo INVERTE o veredito; com Q_roof=2,0 inverte de novo;
# - cota_apoio/B_max_sapata nao mudam o caminho com tipo explicito, mas com
#   tipo ausente (auto) B_max 0,5->estaca e >=1,0->sapata em carga alta;
# - mu_solo/sigma_solo_adm ignorados no caminho estaca (0,9/500 -> identico).
#
# Regra por item (motivo escrito, sem valor novo arbitrado):
# - D_estaca, L_estaca, tipo_estaca: RECUSA NOMEADA quando tipo_fundacao e
#   "estaca" (como a estaca sem SPT ja faz). Motivo: geometria comercial
#   sem piso universal — o default 0,30/8,0/"pre_moldada" decidia
#   geometria, capacidade e veredito sem ninguem declarar.
# - cota_apoio, B_max_sapata: DECLARACAO (defaults 0,5/2,5 mantidos para a
#   recomendacao SPT, com a origem dita no resultado, no memorial, na folha
#   e nos sinais de revisao). Motivo: parametro de modelo da recomendacao
#   geotecnica, nao geometria final; recusar quebraria o caminho
#   automatico legitimo (sapata que fecha sozinha).
# - mu_solo, sigma_solo_adm: TERCEIRO VALOR no caminho estaca ("nao se
#   aplica", declarado no memorial); no caminho sapata seguem com a origem
#   dita (a folha PE-CO-04 do G140 ja declarava; o memorial e os sinais
#   passam a declarar). Motivo: medido que a conta da estaca nao os le.
#
# Portas de entrada (convencao 11): o spec direto de galpao_concreto.rodar
# e o sub-spec "concreto" do galpao_turnkey (via project-spec.json ->
# turnkey.concreto) passam pelo mesmo `spec` — uma fonte so aqui. O
# wizard (wizard.py/PERGUNTAS_ESTACA) alimenta o ProjetoSpec METALICO
# (rodar_galpao), nunca o galpao_concreto: terceiro valor declarado
# (nao se aplica ao concreto), dito no verbete.
# ============================================================================
"""Parametros da fundacao do galpao de concreto sem default silencioso.

Fonte unica das recusas nomeadas (D/L/tipo da estaca) e das proveniencias
declaradas (cota/B_max/mu/sigma). O memorial e a folha leem daqui.
STATELESS: funcoes puras.
"""

from __future__ import annotations

# Defaults NUMERICOS mantidos onde a recusa quebraria caminho legitimo —
# agora com a origem dita (nunca calados). Nenhum numero novo arbitrado:
# sao os mesmos que o codigo ja usava.
COTA_APOIO_DEFAULT = 0.5
B_MAX_SAPATA_DEFAULT = 2.5
MU_SOLO_DEFAULT = 0.5
SIGMA_SOLO_DEFAULT = 200.0

ORIGEM_DECLARADO = "declarado_no_spec"
ORIGEM_DEFAULT = "default"
ORIGEM_NAO_SE_APLICA = "nao_se_aplica"
# G149/D179: o FS global defaultado (3,0) e o valor ADOTADO no framework pelo
# parecer do D38 (2026-07-11, adotado sem ler o PDF da 6122). Medido no
# D179 contra o acervo (fontes/03_FUNDACOES_GEOTECNIA, NBR 6122:2022 p.18):
# 6.2.1.2.1 fixa FS global 2,0 para estaca por metodo semiempirico e
# 6.2.1.2.2 fixa 1,6 com prova de carga estatica; o 3,00 e da Tabela 1
# (fundacao RASA). A origem NAO pode se dizer normativa. O NUMERO nao muda
# aqui (decisao do responsavel, nunca arbitrada no codigo).
ORIGEM_FS_ADOTADO = "fs_adotado_D38"
NOTA_FS_NBR6122 = ("NBR 6122:2022 6.2.1.2.1 fixa 2,0 no semiempirico "
                   "(1,6 com prova de carga, 6.2.1.2.2)")
# G149: fck/fyk do bloco de coroamento herdados do material declarado do
# projeto (spec fundacao.fck/fyk, via params), nunca arbitrados aqui.
ORIGEM_MATERIAL_PROJETO = "material_do_projeto"


def _e_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def resolver_estaca_de_spec(spec):
    """Exige D/L/tipo da estaca declarados quando tipo_fundacao="estaca".

    Ausente/invalido -> ValueError NOMEADO (d_estaca_nao_declarada,
    l_estaca_nao_declarada, tipo_estaca_nao_declarada, *_invalida) — nunca
    0,30/8,0/"pre_moldada" calados. Declarado -> o numero do spec, com a
    origem declarada.
    """
    if not isinstance(spec, dict):
        raise ValueError("d_estaca_nao_declarada: spec nao e dict "
                         "(sem geometria de estaca declarada)")
    if "D_estaca" not in spec or spec["D_estaca"] is None:
        raise ValueError(
            "d_estaca_nao_declarada: tipo_fundacao='estaca' exige 'D_estaca' "
            "(diametro da estaca, m) declarado no spec — sem default")
    if "L_estaca" not in spec or spec["L_estaca"] is None:
        raise ValueError(
            "l_estaca_nao_declarada: tipo_fundacao='estaca' exige 'L_estaca' "
            "(comprimento da estaca, m) declarado no spec — sem default")
    if "tipo_estaca" not in spec or spec["tipo_estaca"] is None:
        raise ValueError(
            "tipo_estaca_nao_declarada: tipo_fundacao='estaca' exige "
            "'tipo_estaca' declarado no spec (pre_moldada/metalica/escavada/"
            "helice/raiz/franki/omega) — sem default")
    D_e = spec["D_estaca"]
    L_e = spec["L_estaca"]
    tipo = spec["tipo_estaca"]
    if not _e_numero(D_e) or not D_e > 0:
        raise ValueError(
            "d_estaca_invalida: D_estaca deve ser numero > 0 (m, recebido %r)"
            % (D_e,))
    if not _e_numero(L_e) or not L_e > 0:
        raise ValueError(
            "l_estaca_invalida: L_estaca deve ser numero > 0 (m, recebido %r)"
            % (L_e,))
    try:
        import estaca_profunda as _ep
        validos = sorted(_ep._F1_F2)
    except ImportError:
        validos = ["pre_moldada", "metalica", "escavada", "helice", "raiz",
                   "franki", "omega"]
    if not isinstance(tipo, str) or tipo not in validos:
        raise ValueError(
            "tipo_estaca_invalida: %r (use um de: %s)"
            % (tipo, ", ".join(validos)))
    return {"D": float(D_e), "L": float(L_e), "tipo_estaca": tipo,
            "origem": ORIGEM_DECLARADO, "explicito": True}


def resolver_recomendacao_de_spec(spec):
    """cota_apoio/B_max com a origem dita (declarado ou default mantido).

    Os numeros sao os que a recomendacao SPT sempre usou (0,5/2,5); a
    novidade e a proveniencia viajar no resultado (memorial, folha e
    sinais leem daqui). Nao numerico -> ValueError nomeado.
    """
    spec = spec if isinstance(spec, dict) else {}
    if spec.get("cota_apoio") is None:
        cota, cota_origem = COTA_APOIO_DEFAULT, ORIGEM_DEFAULT
    else:
        cota = spec["cota_apoio"]
        if not _e_numero(cota) or not cota >= 0:
            raise ValueError(
                "cota_apoio_invalida: cota_apoio deve ser numero >= 0 (m, "
                "recebido %r)" % (cota,))
        cota, cota_origem = float(cota), ORIGEM_DECLARADO
    if spec.get("B_max_sapata") is None:
        bmax, bmax_origem = B_MAX_SAPATA_DEFAULT, ORIGEM_DEFAULT
    else:
        bmax = spec["B_max_sapata"]
        if not _e_numero(bmax) or not bmax > 0:
            raise ValueError(
                "b_max_sapata_invalida: B_max_sapata deve ser numero > 0 (m, "
                "recebido %r)" % (bmax,))
        bmax, bmax_origem = float(bmax), ORIGEM_DECLARADO
    return {"cota_apoio": cota, "cota_origem": cota_origem,
            "B_max_sapata": bmax, "B_max_origem": bmax_origem}


def resolver_solo_sapata_de_spec(spec, tem_spt_ou_geo):
    """sigma/mu com a origem dita (declarado, derivado da sondagem, default).

    Os numeros sao os que o ramo sapata sempre usou (explicito > SPT >
    200; mu 0,5). Nao numerico -> ValueError nomeado.
    """
    spec = spec if isinstance(spec, dict) else {}
    if spec.get("sigma_solo_adm") is not None:
        sig = spec["sigma_solo_adm"]
        if not _e_numero(sig) or not sig > 0:
            raise ValueError(
                "sigma_solo_adm_invalida: deve ser numero > 0 (kN/m2, "
                "recebido %r)" % (sig,))
        sigma, sigma_origem = float(sig), ORIGEM_DECLARADO
    elif tem_spt_ou_geo:
        sigma, sigma_origem = None, "derivada_sondagem"
    else:
        sigma, sigma_origem = SIGMA_SOLO_DEFAULT, ORIGEM_DEFAULT
    if spec.get("mu_solo") is None:
        mu, mu_origem = MU_SOLO_DEFAULT, ORIGEM_DEFAULT
    else:
        mu = spec["mu_solo"]
        if not _e_numero(mu) or not mu > 0:
            raise ValueError(
                "mu_solo_invalido: deve ser numero > 0 (recebido %r)" % (mu,))
        mu, mu_origem = float(mu), ORIGEM_DECLARADO
    return {"sigma_solo_adm": sigma, "sigma_origem": sigma_origem,
            "mu_solo": mu, "mu_origem": mu_origem}


def parametros_de_spec(spec, tipo_fund, tem_spt_ou_geo):
    """Proveniencia completa dos 7 valores do bloco de fundacao (G143).

    No caminho estaca exige D/L/tipo (recusa nomeada) e marca mu/sigma
    como nao-se-aplica. Fora dele, D/L/tipo sao nao-se-aplica. Os
    dicionarios aninhados com {"default": True} sao lidos pelo
    _review_signals do adaptador (codigo assumed_default) — a declaracao
    chega aos sinais sem reinterpretar gate nenhum.
    """
    spec = spec if isinstance(spec, dict) else {}
    rec = resolver_recomendacao_de_spec(spec)
    if tipo_fund == "estaca":
        est = resolver_estaca_de_spec(spec)
        bloco = {
            "D_estaca": {"valor": est["D"], "origem": ORIGEM_DECLARADO},
            "L_estaca": {"valor": est["L"], "origem": ORIGEM_DECLARADO},
            "tipo_estaca": {"valor": est["tipo_estaca"],
                            "origem": ORIGEM_DECLARADO},
            "mu_solo": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                        "nota": "fundacao profunda: atrito solo-sapata nao "
                                "usado na conta da estaca"},
            "sigma_solo_adm": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                               "nota": "fundacao profunda: tensao de sapata "
                                       "nao usada na conta da estaca"},
        }
    else:
        solo = resolver_solo_sapata_de_spec(spec, tem_spt_ou_geo)
        bloco = {
            "D_estaca": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                         "nota": "fundacao rasa: sem estaca"},
            "L_estaca": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                         "nota": "fundacao rasa: sem estaca"},
            "tipo_estaca": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                            "nota": "fundacao rasa: sem estaca"},
            "mu_solo": {"valor": solo["mu_solo"],
                        "origem": solo["mu_origem"]},
            "sigma_solo_adm": {"valor": solo["sigma_solo_adm"],
                               "origem": solo["sigma_origem"]},
        }
        if solo["mu_origem"] == ORIGEM_DEFAULT:
            bloco["mu_solo"]["default"] = True
        if solo["sigma_origem"] == ORIGEM_DEFAULT:
            bloco["sigma_solo_adm"]["default"] = True
    bloco["cota_apoio"] = {"valor": rec["cota_apoio"],
                           "origem": rec["cota_origem"]}
    bloco["B_max_sapata"] = {"valor": rec["B_max_sapata"],
                             "origem": rec["B_max_origem"]}
    if rec["cota_origem"] == ORIGEM_DEFAULT:
        bloco["cota_apoio"]["default"] = True
    if rec["B_max_origem"] == ORIGEM_DEFAULT:
        bloco["B_max_sapata"]["default"] = True
    return {"tipo_fundacao": tipo_fund, "parametros": bloco,
            "estaca": ({"D": est["D"], "L": est["L"],
                        "tipo_estaca": est["tipo_estaca"],
                        "origem": ORIGEM_DECLARADO}
                       if tipo_fund == "estaca" else None)}


def _fmt_origem(origem):
    return {"declarado_no_spec": "declarado no spec",
            "default": "default (confirmar com sondagem/projeto)",
            "nao_se_aplica": "nao se aplica",
            "derivada_sondagem": "derivada da sondagem SPT",
            "fs_adotado_D38":
                "adotado no framework (D38); " + NOTA_FS_NBR6122 +
                " - confirmar com o responsavel",
            "material_do_projeto":
                "fundacao.fck/fyk do spec (o wizard nao pergunta: pode ser "
                "o valor do modelo PS.novo) - confirmar"}.get(
                origem, str(origem))


# ============================================================================
# G149: a estaca calada nas outras tres portas (galpao metalico, wizard,
# predio) + tipo e FS default do nucleo. Mesma regra D102, mesma fonte unica
# (nunca uma copia por modulo).
#
# Medido por injecao (2026-09-15, antes de mudar):
# - nucleo (verifica_estaca, N=500, argila N5/3m + areia N25/8m): D 0,30->0,40
#   P_adm 572,7->913,2 kN (n 1, util 0,873->0,548); L 10->8 m P_adm
#   572,7->509,8 (util 0,873->0,981); pre_moldada->escavada P_adm 572,7->334,1
#   (n 1->2); FS 3->2 P_adm 572,7->859,0 (N=850: n 2->1, util 0,742->0,990);
#   no perfil fraco (L6, N400) pre n=11 x esc n=19. Sem tipo -> "pre_moldada"
#   calada; sem FS -> 3,0 calado.
# - bloco (n=2): fck 25->15 MPa em N=600 OK->REPROVA (biela); a_pilar
#   0,30->0,50 m em N=700/800 REPROVA->OK. fck e a_pilar DECIDEM veredito.
# - predio isolado (N=800): D 0,30->0,40 n 2->1; tipo pre->esc n 2->3; sem
#   D_m/sem tipo a conta usava 0,30/"pre_moldada" calados (mesmo numero do
#   declarado — o silencio, nao o numero, e o defeito). L ausente ja avisa
#   (comprimento_de_estaca_lido_da_sondagem) — caminho que declara nao se
#   recusa. Divisa (:666): mesmos defaults + P_adm=700,0 de fallback e
#   perfil sem tipo de solo caindo no 700 em silencio.
# - metalico (spec->params->rodar): to_rodar_params .get(D,0,30)/.get(L,10,)/
#   .get(tipo,"pre_moldada")/.get(FS,3,0) + rodar setdefault D/L/bloco
#   {a_pilar 0,30, fck 25 MPa}. O fck do bloco deve ser lido do material
#   declarado do projeto (spec fundacao.fck, que viaja a params fundacao.fck;
#   PARAMS_REF traz 25e3): o divisa do predio ja herda assim
#   (spec_fundacao.get("fck", materiais["fck"])) — precedente, nao invencao.
# - wizard: construir_spec gravava o default no spec (r.get com default) e a
#   origem se perdia ali, nao na conta.
#
# Regra por item (motivo escrito, sem valor novo arbitrado, sem trocar o FS):
# - D, L, tipo (metalico, predio), a_pilar (bloco metalico): RECUSA NOMEADA.
#   Motivo: geometria sem piso universal que decide capacidade, n e veredito
#   (medido acima) — mesmo motivo do G143.
# - bloco ausente (metalico, com estaca): RECUSA NOMEADA (bloco_nao_declarado).
#   Motivo: o bloco decide o veredito da biela e a geometria 3D (h); o dict
#   inteiro calado escondia fck/a_pilar juntos.
# - fck/fyk do bloco ausentes: HERDAM o material do projeto com a origem dita
#   (declaracao, nao default). Motivo: o material do projeto ja esta declarado
#   no spec (fundacao.fck/fyk); repetir o numero com a origem e declarar, nao
#   arbitrar. Sem material de onde herdar: recusa (nunca inventar).
# - FS ausente: MANTEM 3,0 com a origem dita (adotado no D38) no resultado e
#   no memorial; nunca outro numero. D179: o acervo NAO diz 3,0 para estaca
#   (NBR 6122:2022 6.2.1.2.1 = 2,0); o numero e decisao do responsavel.
#   FS invalido recusa.
# - L do predio ausente: segue o aviso existente (nao se recusa caminho que
#   ja declara).
# ============================================================================

def _fs_global_g149():
    try:
        import estaca_profunda as _ep
        return float(_ep.FS_GLOBAL)
    except ImportError:
        return 3.0


def _tipos_estaca_g149():
    try:
        import estaca_profunda as _ep
        return sorted(_ep._F1_F2)
    except ImportError:
        return ["pre_moldada", "metalica", "escavada", "helice", "raiz",
                "franki", "omega"]


def _e_numero_pos(valor):
    import math
    return (_e_numero(valor) and math.isfinite(valor) and valor > 0)


def _resolver_tipo(tipo):
    """tipo da estaca sem default silencioso (nucleo, metalico, predio)."""
    if tipo is None:
        raise ValueError(
            "tipo_estaca_nao_declarada: tipo da estaca nao declarado — "
            "sem default (pre_moldada calada decidia capacidade, n e "
            "veredito, G149)")
    validos = _tipos_estaca_g149()
    if not isinstance(tipo, str) or tipo not in validos:
        raise ValueError(
            "tipo_estaca_invalida: %r (use um de: %s)"
            % (tipo, ", ".join(validos)))
    return tipo


def _resolver_fs(fs):
    """FS global: ausente -> (3,0 adotado no D38, origem dita); nunca outro
    numero.

    O numero e o FS_GLOBAL do nucleo (adotado; ver NOTA_FS_NBR6122). Nao
    valida faixa contra
    prova de carga aqui: a flag mora no spec e o gate projeto_spec.validar()
    barra FS<3,0 sem prova; o nucleo so registra a origem.
    """
    if fs is None:
        return _fs_global_g149(), ORIGEM_FS_ADOTADO
    if not _e_numero(fs) or not fs > 0:
        raise ValueError(
            "fs_invalida: FS deve ser numero > 0 (recebido %r)" % (fs,))
    return float(fs), ORIGEM_DECLARADO


def resolver_tipo_fs_nucleo(cfg):
    """Tipo e FS para estaca_profunda.verifica_estaca (G149, fonte unica).

    Tipo ausente/invalido -> recusa nomeada. FS ausente -> 3,0 adotado com
    a origem dita (o numero nao muda). D/L continuam leitura direta do cfg
    (KeyError sem eles) — fora do escopo medido do nucleo.
    """
    cfg = cfg if isinstance(cfg, dict) else {}
    tipo = _resolver_tipo(cfg.get("tipo_estaca"))
    fs, fs_origem = _resolver_fs(cfg.get("FS"))
    return {"tipo_estaca": tipo, "tipo_origem": ORIGEM_DECLARADO,
            "FS": fs, "FS_origem": fs_origem}


def _resolver_dimensao(valor, nome, marca_nao, marca_inv, unidade):
    if valor is None:
        raise ValueError(
            "%s: %s nao declarado (%s) — sem default" % (marca_nao, nome,
                                                         unidade))
    if not _e_numero_pos(valor):
        raise ValueError(
            "%s: %s deve ser numero > 0 (%s, recebido %r)"
            % (marca_inv, nome, unidade, valor))
    return float(valor)


def resolver_estaca_metalica(e, material=None):
    """D/L/tipo/FS/bloco da estaca do galpao METALICO sem default silencioso.

    `e`: fundacao.estaca do spec ou params["estaca"] (chaves D, L,
    tipo_estaca, FS, bloco{a_pilar, fck, fyk}). `material`: projeto
    declarado (fundacao com fck/fyk) de onde o bloco herda fck/fyk com a
    origem dita. Ausente/invalido -> ValueError NOMEADO; nunca 0,30/10,0/
    "pre_moldada"/bloco cheio calados.
    """
    e = e if isinstance(e, dict) else {}
    D = _resolver_dimensao(e.get("D"), "D (diametro da estaca)",
                           "d_estaca_nao_declarada", "d_estaca_invalida",
                           "m")
    L = _resolver_dimensao(e.get("L"), "L (comprimento da estaca)",
                           "l_estaca_nao_declarada", "l_estaca_invalida",
                           "m")
    tipo = _resolver_tipo(e.get("tipo_estaca"))
    fs, fs_origem = _resolver_fs(e.get("FS"))
    bloco = e.get("bloco")
    if bloco is None:
        raise ValueError(
            "bloco_nao_declarado: fundacao profunda exige 'bloco' "
            "(a_pilar, fck, fyk) declarado — o dict inteiro calado "
            "{a_pilar 0,30, fck 25 MPa} decidia o veredito da biela e a "
            "geometria 3D sem ninguem declarar (G149)")
    if not isinstance(bloco, dict):
        raise ValueError(
            "bloco_invalido: 'bloco' deve ser dict {a_pilar, fck, fyk} "
            "(recebido %r)" % (bloco,))
    a_pilar = _resolver_dimensao(bloco.get("a_pilar"),
                                 "a_pilar (lado do pilar no bloco)",
                                 "a_pilar_nao_declarado",
                                 "a_pilar_invalida", "m")
    mat = material if isinstance(material, dict) else {}
    origens = {"a_pilar": ORIGEM_DECLARADO}
    if bloco.get("fck") is None:
        fck = mat.get("fck")
        if not _e_numero_pos(fck):
            raise ValueError(
                "fck_bloco_nao_declarado: bloco sem 'fck' e sem material "
                "do projeto (fundacao.fck) de onde herdar — sem default")
        fck, origens["fck"] = float(fck), ORIGEM_MATERIAL_PROJETO
    else:
        if not _e_numero_pos(bloco.get("fck")):
            raise ValueError(
                "fck_bloco_invalido: fck deve ser numero > 0 (kN/m2, "
                "recebido %r)" % (bloco.get("fck"),))
        fck, origens["fck"] = float(bloco["fck"]), ORIGEM_DECLARADO
    if bloco.get("fyk") is None:
        fyk = mat.get("fyk")
        if not _e_numero_pos(fyk):
            raise ValueError(
                "fyk_bloco_nao_declarado: bloco sem 'fyk' e sem material "
                "do projeto (fundacao.fyk) de onde herdar — sem default")
        fyk, origens["fyk"] = float(fyk), ORIGEM_MATERIAL_PROJETO
    else:
        if not _e_numero_pos(bloco.get("fyk")):
            raise ValueError(
                "fyk_bloco_invalido: fyk deve ser numero > 0 (kN/m2, "
                "recebido %r)" % (bloco.get("fyk"),))
        fyk, origens["fyk"] = float(bloco["fyk"]), ORIGEM_DECLARADO
    return {"D": D, "L": L, "tipo_estaca": tipo,
            "tipo_origem": ORIGEM_DECLARADO,
            "FS": fs, "FS_origem": fs_origem,
            "bloco": {"a_pilar": a_pilar, "fck": fck, "fyk": fyk,
                      "origens": origens}}


def resolver_estaca_predio(estaca_cfg):
    """D_m/tipo da estaca do PREDIO sem default silencioso (G149, fonte unica).

    L_m ausente NAO recusa: o caminho existente ja declara (aviso
    comprimento_de_estaca_lido_da_sondagem, fundacao_edificio.py:959-964) —
    e caminho que declara nao se recusa. Devolve L_m None com a origem
    derivada-da-sondagem nesse caso.
    """
    cfg = estaca_cfg if isinstance(estaca_cfg, dict) else {}
    D = _resolver_dimensao(cfg.get("D_m"), "D_m (diametro da estaca)",
                           "d_estaca_nao_declarada", "d_estaca_invalida",
                           "m")
    tipo = _resolver_tipo(cfg.get("tipo_estaca"))
    if cfg.get("L_m") is None:
        L, L_origem = None, "derivada_sondagem"
    else:
        L = _resolver_dimensao(cfg.get("L_m"),
                               "L_m (comprimento da estaca)",
                               "l_estaca_nao_declarada",
                               "l_estaca_invalida", "m")
        L_origem = ORIGEM_DECLARADO
    return {"D_m": D, "L_m": L, "L_origem": L_origem,
            "tipo_estaca": tipo, "tipo_origem": ORIGEM_DECLARADO}


def linha_fs_g149(fs, origem):
    """Linha do memorial com a origem do FS global (vem desta fonte so).

    O numero nao muda: ausente na entrada -> 3,0 adotado no D38 (a linha
    cita a NBR 6122:2022 6.2.1.2.1, que fixa 2,0).
    """
    return ("FS global = %.1f (%s)"
            % (float(fs), _fmt_origem(origem)))


def linha_bloco_g149(bloco):
    """Linha curta do bloco do metalico com a origem de cada item."""
    if not isinstance(bloco, dict):
        raise ValueError("resultado sem bloco resolvido (G149)")
    org = (bloco.get("origens") or {}) if isinstance(bloco, dict) else {}
    return ("bloco a_pilar=%.2f m (%s) ; fck=%.0f kN/m2 (%s) ; fyk=%.0f kN/m2 (%s)"
            % (bloco.get("a_pilar", 0.0),
               _fmt_origem(org.get("a_pilar")),
               bloco.get("fck", 0.0), _fmt_origem(org.get("fck")),
               bloco.get("fyk", 0.0), _fmt_origem(org.get("fyk"))))


def linha_folha_g149(estaca_parametros):
    """Linha curta que a folha de fundacao do predio carimba (fonte unica).

    None quando nao ha o que declarar (caminho rasa, resultado antigo).
    """
    if not isinstance(estaca_parametros, dict):
        return None
    if estaca_parametros.get("tipo_fundacao") != "estaca":
        return None
    par = estaca_parametros.get("parametros") or {}
    d = (par.get("D_m") or {})
    t = (par.get("tipo_estaca") or {})
    f = (par.get("FS") or {})
    base = ("estaca D%.0f %s (%s)"
            % (float(d.get("valor", 0.0)) * 100,
               t.get("valor", "?"),
               _fmt_origem(t.get("origem"))))
    l = (par.get("L_m") or {})
    if l.get("origem") == ORIGEM_DECLARADO:
        base += " L%.0f (declarado)" % float(l.get("valor", 0.0))
    else:
        base += " L da sondagem (ver aviso)"
    base += " ; FS %s (%s)" % (str(f.get("valor", "?")),
                               _fmt_origem(f.get("origem")))
    return "G149: " + base


def linha_memorial(parametros):
    """Linha que o memorial carimba (vem desta fonte so)."""
    if not isinstance(parametros, dict):
        raise ValueError("resultado sem fundacao_parametros (G143): a "
                         "entrega nao declara o que a conta nao registrou")
    bloco = parametros.get("parametros") or {}
    tipo = parametros.get("tipo_fundacao")
    partes = []
    if tipo == "estaca":
        est = parametros.get("estaca") or {}
        partes.append("estaca D=%.2f m L=%.1f m tipo=%s (%s)"
                      % (est.get("D", 0.0), est.get("L", 0.0),
                         est.get("tipo_estaca", "?"),
                         _fmt_origem((est.get("origem")))))
        partes.append("mu_solo/sigma_solo_adm nao se aplicam "
                      "(fundacao profunda)")
    else:
        for chave, rot in (("mu_solo", "mu_solo"),
                           ("sigma_solo_adm", "sigma_solo_adm")):
            item = bloco.get(chave) or {}
            val = item.get("valor")
            txt = ("%.3g" % val) if val is not None else "derivada"
            partes.append("%s=%s (%s)" % (rot, txt,
                                          _fmt_origem(item.get("origem"))))
    for chave, rot in (("cota_apoio", "cota_apoio"),
                       ("B_max_sapata", "B_max_sapata")):
        item = bloco.get(chave) or {}
        val = item.get("valor")
        txt = ("%.3g m" % val) if val is not None else "?"
        partes.append("%s=%s (%s)" % (rot, txt,
                                      _fmt_origem(item.get("origem"))))
    return ("PARAMETROS DA FUNDACAO (G143): " + " ; ".join(partes))


def linha_folha(parametros):
    """Linha curta que a PE-CO-04 carimba no quadro (vem desta fonte so)."""
    if not isinstance(parametros, dict):
        return None
    bloco = parametros.get("parametros") or {}
    tipo = parametros.get("tipo_fundacao")
    if tipo == "estaca":
        est = parametros.get("estaca") or {}
        base = ("estaca D%.0f L%.0f %s (declarado no spec)"
                % (float(est.get("D", 0.0)) * 100,
                   float(est.get("L", 0.0)),
                   est.get("tipo_estaca", "?")))
        c = bloco.get("cota_apoio") or {}
        if c.get("origem") == ORIGEM_DEFAULT:
            base += " ; cota_apoio default (confirmar)"
        b = bloco.get("B_max_sapata") or {}
        if b.get("origem") == ORIGEM_DEFAULT:
            base += " ; B_max default (confirmar)"
        return base + " ; mu/sigma N/A (profunda)"
    c = bloco.get("cota_apoio") or {}
    b = bloco.get("B_max_sapata") or {}
    m = bloco.get("mu_solo") or {}
    s = bloco.get("sigma_solo_adm") or {}
    marc = []
    if c.get("origem") == ORIGEM_DEFAULT:
        marc.append("cota_apoio default (confirmar)")
    if b.get("origem") == ORIGEM_DEFAULT:
        marc.append("B_max default (confirmar)")
    if m.get("origem") == ORIGEM_DEFAULT:
        marc.append("mu default (confirmar)")
    if s.get("origem") == ORIGEM_DEFAULT:
        marc.append("sigma default (confirmar)")
    if not marc:
        return None
    return "parametros: " + " ; ".join(marc)


def _selftest():
    perfil = [{"tipo": "argila", "N": 5, "dz": 3.0}]
    # recusa nomeada, uma por uma
    for spec, marca in [
            ({"tipo_fundacao": "estaca", "perfil_spt": perfil},
             "d_estaca_nao_declarada"),
            ({"tipo_fundacao": "estaca", "perfil_spt": perfil,
              "D_estaca": 0.30}, "l_estaca_nao_declarada"),
            ({"tipo_fundacao": "estaca", "perfil_spt": perfil,
              "D_estaca": 0.30, "L_estaca": 8.0},
             "tipo_estaca_nao_declarada"),
            ({"tipo_fundacao": "estaca", "D_estaca": 0, "L_estaca": 8.0,
              "tipo_estaca": "pre_moldada"}, "d_estaca_invalida"),
            ({"tipo_fundacao": "estaca", "D_estaca": 0.30, "L_estaca": 0,
              "tipo_estaca": "pre_moldada"}, "l_estaca_invalida"),
            ({"tipo_fundacao": "estaca", "D_estaca": 0.30, "L_estaca": 8.0,
              "tipo_estaca": "tubarole"}, "tipo_estaca_invalida")]:
        try:
            resolver_estaca_de_spec(spec)
            raise AssertionError("devia recusar: %s" % marca)
        except ValueError as exc:
            assert marca in str(exc), (marca, exc)
    ok = resolver_estaca_de_spec({"tipo_fundacao": "estaca",
                                  "D_estaca": 0.30, "L_estaca": 10.0,
                                  "tipo_estaca": "escavada"})
    assert ok["D"] == 0.30 and ok["L"] == 10.0
    assert ok["tipo_estaca"] == "escavada"
    # recomendacao: mesmos numeros, origem dita
    rec = resolver_recomendacao_de_spec({})
    assert rec["cota_apoio"] == 0.5 and rec["cota_origem"] == "default"
    assert rec["B_max_sapata"] == 2.5 and rec["B_max_origem"] == "default"
    rec2 = resolver_recomendacao_de_spec({"cota_apoio": 1.5,
                                          "B_max_sapata": 4.0})
    assert rec2["cota_origem"] == "declarado_no_spec"
    # bloco completo: estaca marca mu/sigma N/A; sapata marca defaults
    p_est = parametros_de_spec({"tipo_fundacao": "estaca", "D_estaca": 0.30,
                                "L_estaca": 8.0,
                                "tipo_estaca": "pre_moldada"}, "estaca",
                               True)
    assert p_est["parametros"]["mu_solo"]["origem"] == "nao_se_aplica"
    assert p_est["parametros"]["cota_apoio"]["default"] is True
    p_sap = parametros_de_spec({}, "sapata", False)
    assert p_sap["parametros"]["sigma_solo_adm"]["default"] is True
    assert p_sap["parametros"]["D_estaca"]["origem"] == "nao_se_aplica"
    assert "PARAMETROS DA FUNDACAO (G143)" in linha_memorial(p_est)
    assert "declarado no spec" in (linha_folha(p_est) or "")
    # G149: nucleo — tipo recusa, FS ausente vira 3,0 normativo com origem
    tfs = resolver_tipo_fs_nucleo({"tipo_estaca": "pre_moldada"})
    assert tfs["FS"] == 3.0 and tfs["FS_origem"] == ORIGEM_FS_ADOTADO
    tfs2 = resolver_tipo_fs_nucleo({"tipo_estaca": "escavada", "FS": 2.0})
    assert tfs2["FS"] == 2.0 and tfs2["FS_origem"] == ORIGEM_DECLARADO
    for bad, marca in [({}, "tipo_estaca_nao_declarada"),
                       ({"tipo_estaca": "tubarole"}, "tipo_estaca_invalida"),
                       ({"tipo_estaca": "pre_moldada", "FS": 0},
                        "fs_invalida")]:
        try:
            resolver_tipo_fs_nucleo(bad)
            raise AssertionError("devia recusar: %s" % marca)
        except ValueError as exc:
            assert marca in str(exc), (marca, exc)
    # G149: metalico — D/L/tipo/bloco/a_pilar recusam; FS e fck/fyk declaram
    mat = {"fck": 25e3, "fyk": 500e3}
    m = resolver_estaca_metalica(
        {"D": 0.30, "L": 10.0, "tipo_estaca": "pre_moldada",
         "bloco": {"a_pilar": 0.30}}, mat)
    assert m["FS"] == 3.0 and m["FS_origem"] == ORIGEM_FS_ADOTADO
    assert m["bloco"]["fck"] == 25e3
    assert m["bloco"]["origens"]["fck"] == ORIGEM_MATERIAL_PROJETO
    for bad, marca in [
            ({}, "d_estaca_nao_declarada"),
            ({"D": 0.30}, "l_estaca_nao_declarada"),
            ({"D": 0.30, "L": 10.0}, "tipo_estaca_nao_declarada"),
            ({"D": 0, "L": 10.0, "tipo_estaca": "pre_moldada",
              "bloco": {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3}},
             "d_estaca_invalida"),
            ({"D": 0.30, "L": 10.0, "tipo_estaca": "pre_moldada"},
             "bloco_nao_declarado"),
            ({"D": 0.30, "L": 10.0, "tipo_estaca": "pre_moldada",
              "bloco": {"fck": 25e3, "fyk": 500e3}},
             "a_pilar_nao_declarado"),
            ({"D": 0.30, "L": 10.0, "tipo_estaca": "pre_moldada",
              "bloco": {"a_pilar": 0.30}}, "fck_bloco_nao_declarado")]:
        try:
            resolver_estaca_metalica(bad, None if marca == "fck_bloco_nao_declarado" else mat)
            raise AssertionError("devia recusar: %s" % marca)
        except ValueError as exc:
            assert marca in str(exc), (marca, exc)
    # G149: predio — D_m/tipo recusam; L_m ausente declara (sondagem)
    p = resolver_estaca_predio({"D_m": 0.30, "tipo_estaca": "pre_moldada"})
    assert p["L_m"] is None and p["L_origem"] == "derivada_sondagem"
    p2 = resolver_estaca_predio({"D_m": 0.30, "L_m": 10.0,
                                 "tipo_estaca": "escavada"})
    assert p2["L_m"] == 10.0 and p2["L_origem"] == ORIGEM_DECLARADO
    for bad, marca in [({}, "d_estaca_nao_declarada"),
                       ({"D_m": 0.30}, "tipo_estaca_nao_declarada"),
                       ({"D_m": 0, "L_m": 10.0,
                         "tipo_estaca": "pre_moldada"},
                        "d_estaca_invalida")]:
        try:
            resolver_estaca_predio(bad)
            raise AssertionError("devia recusar: %s" % marca)
        except ValueError as exc:
            assert marca in str(exc), (marca, exc)
    assert "NBR 6122" in linha_fs_g149(3.0, ORIGEM_FS_ADOTADO)
    assert "declarado no spec" in linha_fs_g149(2.0, ORIGEM_DECLARADO)
    assert "material do projeto" in linha_bloco_g149(m["bloco"])
    print("estaca_parametros_g143 self-test PASSED")


if __name__ == "__main__":
    _selftest()
