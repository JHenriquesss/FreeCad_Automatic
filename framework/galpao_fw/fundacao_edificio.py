# ============================================================================
# fundacao_edificio.py - FUNDACAO DO EDIFICIO MULTIPAVIMENTO, PILAR A PILAR
#
# A descida de cargas (G3) entrega N_base por pilar desde o inicio, e o
# adaptador declarava 'fundacao': not_available - a carga chegava ao chao e
# parava ali. Os modulos de calculo ja existiam e ja estavam aferidos
# (fundacao_sapata contra Alonso, estaca_profunda por Aoki-Velloso lido do PDF,
# geotecnia_spt pela ponte SPT -> tensao admissivel). Este modulo LIGA os dois
# lados; nao inventa metodo novo.
#
#     descida (N_base por pilar) + SPT declarado
#          -> geotecnia_spt.recomenda_fundacao  (sapata x estaca)
#          -> fundacao_sapata.dimensiona_sapata_env / dimensiona_bloco_env
#             ou estaca_profunda.verifica_estaca                (por pilar)
#          -> gate
#
# ASK, DO NOT INVENT. A sondagem e' ENTRADA DECLARADA: sem `perfil_spt` (ou uma
# `sigma_solo_adm` que o projetista assuma), nao ha fundacao - o modulo devolve
# 'nao_declarada' e o escopo continua dizendo not_available. Tensao admissivel
# arbitrada e' o erro que este framework trata como bug, nao como default.
#
# UM TIPO PARA A OBRA, UMA GEOMETRIA POR PILAR. O tipo (sapata / bloco / estaca)
# e' escolhido UMA vez, pela sondagem sob o pilar MAIS CARREGADO - obra nao mistura
# fundacao rasa e profunda sem decisao explicita. Ja a geometria e' dimensionada
# PILAR A PILAR: o pilar de canto de um edificio recebe uma fracao da carga do
# interno, e uma sapata unica dimensionada pelo pior caso seria desperdicio em
# 8 das 12 posicoes.
#
# ACAO HORIZONTAL - o que entra e o que NAO entra:
#   ENTRA  o momento GLOBAL de tombamento (vento/desaprumo, de
#          estabilidade_edificio), distribuido entre as prumadas como um binario:
#          dN_i = M * x_i / sum(x_j^2), pelo modulo de resistencia da malha de
#          fundacoes. O pilar de sotavento sobrecarrega, o de barlavento alivia.
#   ENTRA  o cortante da base, dividido igualmente entre as prumadas (hipotese
#          usual de uma primeira aproximacao), que alimenta o FS ao deslizamento
#          da fundacao RASA. Na ESTACA ele nao e' verificado: estaca carregada
#          transversalmente (Broms / Matlock-Reese) nao existe neste framework,
#          e o escopo diz `esforco_horizontal_na_estaca: not_available`.
#   NAO ENTRA o MOMENTO FLETOR na base de CADA pilar: o modelo de estabilidade e'
#          um portico plano GLOBAL para gamma_z e ELS, e nao devolve esforco por
#          barra. As combinacoes vao com M=0 no topo da sapata, e o escopo
#          publica `momento_base_pilar: not_available` em vez de calar. Dimensionar
#          uma sapata para um momento que ninguem calculou seria pior que dizer
#          que ele falta.
#
# Unidades: m, kN (fck/fyk/sigma em kN/m2). STATELESS.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Fundacao do edificio multipavimento: tipo pela sondagem, geometria por pilar."""

from __future__ import annotations

import copy
import math

import estaca_profunda as ep
import fundacao_sapata as fsap
import geotecnia_spt as gspt

TIPOS = ("sapata", "bloco", "estaca")

# tensao admissivel default: NAO EXISTE. A ausencia e' o comportamento correto.
SIGMA_SOLO_DEFAULT = None


class EntradaFundacao(ValueError):
    """A entrada declarada nao permite dimensionar a fundacao."""


def declarada(spec_fundacao) -> bool:
    """True se ha o minimo para dimensionar: sondagem OU tensao assumida."""
    if not isinstance(spec_fundacao, dict):
        return False
    return bool(spec_fundacao.get("perfil_spt")
                or spec_fundacao.get("sigma_solo_adm"))


def _valida(spec_fundacao):
    """Recusa a entrada malformada em vez de deixar o solver estourar fundo."""
    erros = []
    perfil = spec_fundacao.get("perfil_spt")
    if perfil is not None:
        if not isinstance(perfil, list) or not perfil:
            erros.append("perfil_spt deve ser uma lista nao vazia de camadas")
        else:
            for i, camada in enumerate(perfil):
                if not isinstance(camada, dict):
                    erros.append("perfil_spt[%d] deve ser um objeto" % i)
                    continue
                if not _positivo(camada.get("dz")):
                    erros.append("perfil_spt[%d].dz deve ser > 0" % i)
                n_spt = camada.get("N")
                if not isinstance(n_spt, (int, float)) or isinstance(n_spt, bool) \
                        or n_spt < 0:
                    erros.append("perfil_spt[%d].N deve ser numerico >= 0" % i)
                if camada.get("tipo") is not None \
                        and camada["tipo"] not in ep.TIPOS_SOLO:
                    erros.append("perfil_spt[%d].tipo de solo desconhecido: %r"
                                 % (i, camada["tipo"]))
    sigma = spec_fundacao.get("sigma_solo_adm")
    if sigma is not None and not _positivo(sigma):
        erros.append("sigma_solo_adm deve ser numerico > 0 (kN/m2)")
    tipo = spec_fundacao.get("tipo")
    if tipo is not None and tipo not in TIPOS:
        erros.append("tipo de fundacao invalido: %r (use %s)"
                     % (tipo, ", ".join(TIPOS)))
    if tipo == "estaca" and not spec_fundacao.get("perfil_spt"):
        # Aoki-Velloso e' um metodo SEMI-EMPIRICO sobre o SPT: sem sondagem nao
        # ha capacidade a calcular, e um P_adm arbitrado nao e' fundacao.
        erros.append("tipo='estaca' exige perfil_spt (sondagem): a capacidade "
                     "vem do SPT, nao de um valor assumido")
    if erros:
        raise EntradaFundacao("; ".join(erros))


def _positivo(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


# ---------------------------------------------------------------------------
# acao horizontal: do momento GLOBAL para o dN de cada prumada
# ---------------------------------------------------------------------------
def esforcos_horizontais(estabilidade, pilares, eixos_x, eixos_y):
    """Distribui o tombamento global entre as prumadas (binario) e o cortante.

    `estabilidade` e' o retorno de `estabilidade_edificio.verifica` (ou None).
    Devolve {direcao: {pilar: {'dN_kN', 'V_kN'}}} - dN POSITIVO sobrecarrega.

    O momento e' repartido pelo modulo de resistencia da malha de fundacoes,
    dN_i = M * x_i / sum(x_j^2), com x medido do CENTROIDE das prumadas. E' a
    mesma conta que `estaca_profunda.carga_estaca_grupo` faz dentro de um bloco,
    aplicada aqui ao conjunto de pilares - o edificio inteiro visto como uma
    fundacao so, que e' o que resiste ao tombamento.
    """
    if not estabilidade:
        return {}
    xs = [eixos_x[p["i"]] for p in pilares]
    ys = [eixos_y[p["j"]] for p in pilares]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    sxx = sum((x - cx) ** 2 for x in xs)              # em torno do eixo Y (vento X)
    syy = sum((y - cy) ** 2 for y in ys)
    n = len(pilares)
    out = {}
    for direcao in ("x", "y"):
        registro = (estabilidade.get("por_direcao") or {}).get(direcao)
        if not registro:
            continue
        # o momento que governa a estabilidade e' o da COMBINACAO adotada
        # (vento, desaprumo ou os dois) - o mesmo numero que alimentou gamma_z.
        # E' CARACTERISTICO (Fa = Ca.q.Ae, sem gamma_f), igual ao N_base_k que
        # vem da descida. Misturar um de calculo com o outro caracteristico e' o
        # tipo de erro que passa despercebido e sobredimensiona a obra inteira.
        m_base = float(registro["combinacao"]["M_kNm"])
        v_base = float(sum(registro["forcas_horizontais_kN"]))
        soma = sxx if direcao == "x" else syy
        por_pilar = {}
        for p, x, y in zip(pilares, xs, ys):
            braco = (x - cx) if direcao == "x" else (y - cy)
            dn = (m_base * braco / soma) if soma > 1e-9 else 0.0
            por_pilar[p["nome"]] = {"dN_kN": round(dn, 2),
                                    "V_kN": round(v_base / n, 2),
                                    "braco_m": round(braco, 3)}
        out[direcao] = {"M_base_kNm": round(m_base, 1),
                        "V_base_kN": round(v_base, 1),
                        "soma_x2_m2": round(soma, 3),
                        "por_pilar": por_pilar}
    return out


def combinacoes_do_pilar(nome, N_base_k, horizontais):
    """Casos (nome, N, V, M) que a fundacao deste pilar tem de atender.

    Sempre ha o caso GRAVITACIONAL puro. Com acao horizontal declarada entram,
    por direcao, o caso de SOTAVENTO (N + dN, o que dimensiona o solo) e o de
    BARLAVENTO (N - dN, o que dimensiona tombamento/deslizamento porque alivia o
    peso estabilizante). Verificar so o maior N deixaria o segundo passar
    despercebido - o mesmo motivo pelo qual `dimensiona_sapata_env` existe.

    M = 0: ver a nota de escopo no cabecalho - o momento fletor na base de cada
    pilar nao e' calculado pelo modelo global.
    """
    casos = [("gravitacional", N_base_k, 0.0, 0.0)]
    for direcao, registro in sorted(horizontais.items()):
        info = registro["por_pilar"].get(nome)
        if not info:
            continue
        dn, v = info["dN_kN"], info["V_kN"]
        casos.append(("sotavento_%s" % direcao, N_base_k + abs(dn), v, 0.0))
        casos.append(("barlavento_%s" % direcao, max(N_base_k - abs(dn), 0.0),
                      v, 0.0))
    return casos


# ---------------------------------------------------------------------------
# escolha do tipo + dimensionamento por pilar
# ---------------------------------------------------------------------------
def _perfil_para_geotecnia(perfil):
    """geotecnia_spt le {N, dz}; estaca_profunda tambem exige `tipo`. O mesmo
    perfil serve aos dois - so a estaca exige o tipo de solo declarado."""
    return [{"N": c["N"], "dz": c["dz"]} for c in perfil]


def escolhe_tipo(spec_fundacao, N_max_kN):
    """Tipo da fundacao da OBRA: o declarado vence; senao, o que a sondagem
    recomenda sob o pilar mais carregado. Devolve (tipo, recomendacao|None)."""
    declarado_tipo = spec_fundacao.get("tipo")
    perfil = spec_fundacao.get("perfil_spt")
    recomendacao = None
    if perfil:
        recomendacao = gspt.recomenda_fundacao(
            _perfil_para_geotecnia(perfil), N_max_kN,
            cota_apoio_m=spec_fundacao.get("cota_apoio_m", 1.0),
            B_max_m=spec_fundacao.get("B_max_sapata_m", 3.0))
    if declarado_tipo:
        return declarado_tipo, recomendacao
    if recomendacao and recomendacao["tipo"] in TIPOS:
        return recomendacao["tipo"], recomendacao
    if recomendacao:                                  # 'revisar': sem camada boa
        raise EntradaFundacao(
            "a sondagem nao permite escolher o tipo de fundacao: %s"
            % recomendacao["justificativa"])
    return "sapata", None


def _sigma_solo(spec_fundacao, recomendacao):
    """Tensao admissivel: a declarada vence a derivada do SPT (N/50).

    Sem nenhuma das duas, LEVANTA. Nao ha default: arbitrar a tensao do solo e'
    inventar o dado que decide toda a fundacao.
    """
    declarada_sigma = spec_fundacao.get("sigma_solo_adm")
    if declarada_sigma:
        return float(declarada_sigma), "declarada no spec"
    if recomendacao and recomendacao.get("sapata"):
        sapata = recomendacao["sapata"]
        return (float(sapata["sigma_adm_kNm2"]),
                "derivada do SPT (N/50; N medio no bulbo = %.1f)"
                % sapata["N_medio_bulbo"])
    raise EntradaFundacao(
        "sem sigma_solo_adm declarada e sem SPT que a derive (o solo raso nao "
        "atendeu o criterio N/50): fundacao rasa nao pode ser dimensionada")


def _caso_base(spec_fundacao, sigma_solo, secao_pilar, materiais):
    """Parametros do solo/concreto comuns a todas as combinacoes de um pilar."""
    b, h = secao_pilar
    return {
        "sigma_solo_adm": sigma_solo,
        "mu": spec_fundacao.get("mu_solo", 0.5),
        "coesao": spec_fundacao.get("coesao", 0.0),
        "h_reaterro": spec_fundacao.get("cota_apoio_m", 1.0),
        # o pedestal tem a secao do PILAR que ele recebe - e' o que define o
        # balanco da sapata e, com ele, a rigidez (22.6.1) e a armadura.
        "d_ped": h, "b_ped": b, "h_ped": spec_fundacao.get("h_pedestal_m", 0.5),
        "fck": spec_fundacao.get("fck", materiais["fck"]),
        "fyk": spec_fundacao.get("fyk", materiais["fyk"]),
        "cobrimento": spec_fundacao.get("cobrimento", 0.05),
        "verificacao_estabilidade": spec_fundacao.get("verificacao_estabilidade"),
    }


def _dimensiona_raso(tipo, caso_base, casos, escada):
    if tipo == "bloco":
        return fsap.dimensiona_bloco_env(caso_base, casos)
    return fsap.dimensiona_sapata_env(caso_base, casos, escada=escada)


def _geometria_rasa(tipo, resultado):
    aprovado = resultado["aprovado"]
    if not aprovado:
        return None
    if tipo == "bloco":
        B, L, h, beta = aprovado
        return {"B_m": B, "L_m": L, "h_m": h, "beta_graus": round(beta, 1)}
    B, L, h, _rA, _c = aprovado
    parte_b = resultado.get("parte_B") or {}
    geometria = {"B_m": B, "L_m": L, "h_m": h}
    for eixo in ("flexao_L", "flexao_B"):
        registro = parte_b.get(eixo)
        if registro:
            geometria["As_%s_cm2" % eixo[-1]] = round(
                registro["As_adot"] * 1e4, 2)
    return geometria


def _dimensiona_estaca(spec_fundacao, casos, secao_pilar, materiais):
    """Estaca + bloco de coroamento pelo pior N das combinacoes.

    O CORTANTE das combinacoes nao e' usado aqui: verificar a estaca a esforco
    horizontal exige um metodo de estaca carregada transversalmente (Broms,
    Matlock-Reese) que este framework nao tem. O escopo publica
    `esforco_horizontal_na_estaca: not_available` - e' fronteira nomeada, nao
    verificacao esquecida.
    """
    estaca_cfg = spec_fundacao.get("estaca") or {}
    perfil = spec_fundacao["perfil_spt"]
    for camada in perfil:
        if not camada.get("tipo"):
            raise EntradaFundacao(
                "o perfil SPT precisa do TIPO DE SOLO de cada camada para o "
                "metodo de Aoki-Velloso (K e alpha da Tab.12.6 dependem dele)")
    N_max = max(caso[1] for caso in casos)
    _b, h = secao_pilar
    resultado = ep.verifica_estaca({
        "perfil": copy.deepcopy(perfil),
        "D": estaca_cfg.get("D_m", 0.30),
        "L": estaca_cfg.get("L_m", _profundidade_sugerida(perfil)),
        "tipo_estaca": estaca_cfg.get("tipo_estaca", "pre_moldada"),
        "N_pilar": N_max,
        "bloco": {"a_pilar": h, "fck": spec_fundacao.get("fck", materiais["fck"]),
                  "fyk": spec_fundacao.get("fyk", materiais["fyk"]),
                  "cobrimento": spec_fundacao.get("cobrimento", 0.05)},
    })
    grupo = resultado["grupo"]
    ok = grupo["util"] is not None and grupo["util"] <= 1.0
    geometria = {"n_estacas": grupo["n"],
                 "D_m": resultado["capacidade"]["D"],
                 "L_m": resultado["capacidade"]["L"],
                 "P_adm_kN": resultado["capacidade"]["P_adm_kN"],
                 "util": grupo["util"]}
    bloco = resultado.get("bloco")
    if bloco:
        geometria["bloco_h_m"] = bloco["h"]
    else:
        # `estaca_profunda.bloco_coroamento` so tem o modelo de bielas para 2 e
        # 4 estacas. Com 1 a estaca recebe o pilar direto; com 3, 5 ou mais o
        # bloco NAO foi dimensionado - e isso viaja no resultado em vez de o
        # bloco simplesmente sumir do quadro e do modelo 3D.
        geometria["bloco_dimensionado"] = False
        geometria["bloco_motivo"] = (
            "estaca unica: o pilar apoia direto no topo da estaca"
            if grupo["n"] == 1 else
            "bloco de %d estacas fora do modelo de bielas implementado "
            "(2 ou 4); dimensionar em separado" % grupo["n"])
    return resultado, geometria, ok


N_COMPETENTE = 20          # SPT que caracteriza a camada de apoio (geotecnia_spt)


def _profundidade_sugerida(perfil):
    """Comprimento de estaca que ATRAVESSA a 1a camada competente (N >= 20).

    A ponta para na BASE dessa camada, nao no topo dela. E' a escolha
    conservadora que nao exige arbitrar um embutimento: parar no topo obrigaria
    a somar "3D" ou "1 m" de penetracao, numeros que nenhum dado do projeto
    fornece. Quem quiser a estaca mais curta declara `estaca.L_m`.

    Sem camada competente no perfil, levanta - a estaca precisa de onde se
    apoiar, e escolher a ponta numa camada mole seria inventar apoio.
    """
    profundidade = 0.0
    for camada in perfil:
        profundidade += camada["dz"]
        if camada["N"] >= N_COMPETENTE:
            return round(profundidade, 1)
    raise EntradaFundacao(
        "o perfil SPT nao tem camada competente (N >= %d) ate %.1f m: declare "
        "estaca.L_m ou aprofunde a sondagem" % (N_COMPETENTE, profundidade))


def dimensiona(spec_fundacao, contexto):
    """Dimensiona a fundacao de TODOS os pilares do edificio.

    spec_fundacao: a secao `estrutura.fundacao` do spec (ver cabecalho).
    contexto: {'pilares': [{nome, i, j, N_base_k, secao (b,h)}],
               'eixos_x', 'eixos_y' (m), 'materiais' {fck, fyk},
               'estabilidade' (opc, de estabilidade_edificio.verifica)}.

    Retorna {'tipo', 'sigma_solo_adm', 'por_pilar', 'gate', ...}. Levanta
    EntradaFundacao quando a entrada declarada nao permite dimensionar.
    """
    _valida(spec_fundacao)
    pilares = contexto["pilares"]
    if not pilares:
        raise EntradaFundacao("nenhum pilar na descida de cargas")

    horizontais = esforcos_horizontais(
        contexto.get("estabilidade"), pilares,
        contexto["eixos_x"], contexto["eixos_y"])

    # o tipo e' da OBRA: escolhido sob o pilar mais carregado, ja com o dN de
    # tombamento - senao a sondagem seria consultada para uma carga que nao e' a
    # que a fundacao vai receber.
    N_max_obra = max(
        max(caso[1] for caso in combinacoes_do_pilar(
            p["nome"], p["N_base_k"], horizontais))
        for p in pilares)
    tipo, recomendacao = escolhe_tipo(spec_fundacao, N_max_obra)

    sigma_solo = nota_sigma = None
    if tipo in ("sapata", "bloco"):
        sigma_solo, nota_sigma = _sigma_solo(spec_fundacao, recomendacao)

    escada = _escada(spec_fundacao)
    por_pilar = {}
    reprovados = []
    for pilar in pilares:
        casos = combinacoes_do_pilar(pilar["nome"], pilar["N_base_k"], horizontais)
        caso_base = _caso_base(spec_fundacao, sigma_solo, pilar["secao"],
                               contexto["materiais"])
        if tipo == "estaca":
            bruto, geometria, ok = _dimensiona_estaca(
                spec_fundacao, casos, pilar["secao"], contexto["materiais"])
        else:
            bruto = _dimensiona_raso(tipo, caso_base, casos, escada)
            geometria = _geometria_rasa(tipo, bruto)
            ok = geometria is not None
        registro = {
            "nome": pilar["nome"], "posicao": pilar.get("posicao"),
            "i": pilar["i"], "j": pilar["j"],
            "N_base_k": pilar["N_base_k"],
            "N_dimensionamento_kN": round(max(c[1] for c in casos), 1),
            "combinacoes": [{"nome": c[0], "N_kN": round(c[1], 1),
                             "V_kN": round(c[2], 1), "M_kNm": round(c[3], 1)}
                            for c in casos],
            "geometria": geometria, "OK": ok, "bruto": bruto,
        }
        por_pilar[pilar["nome"]] = registro
        if not ok:
            reprovados.append(pilar["nome"])

    gate = {"OK": not reprovados, "tipo": tipo, "n_pilares": len(pilares),
            "reprovados": reprovados,
            "N_max_kN": round(N_max_obra, 1)}
    return {
        "tipo": tipo,
        # a cota de apoio viaja no resultado porque e' ela que posiciona a peca
        # no modelo 3D/BIM: a sapata tem o TOPO nela, e nao na cota zero.
        "cota_apoio_m": float(spec_fundacao.get("cota_apoio_m", 1.0)),
        "sigma_solo_adm": sigma_solo,
        "proveniencia_sigma": nota_sigma,
        "recomendacao_spt": recomendacao,
        "acao_horizontal": horizontais,
        "por_pilar": por_pilar,
        "gate": gate,
        "escopo": _escopo(tipo, bool(horizontais)),
        "avisos": _avisos(spec_fundacao, tipo, horizontais, recomendacao,
                          por_pilar),
    }


def _escada(spec_fundacao):
    """Escada de sapatas do projeto (opcional). O default e' o do modulo."""
    escada = spec_fundacao.get("escada_sapata")
    if escada is None:
        return None
    if (not isinstance(escada, list) or not escada
            or not all(isinstance(d, (list, tuple)) and len(d) == 3
                       and all(_positivo(v) for v in d) for d in escada)):
        raise EntradaFundacao(
            "escada_sapata deve ser uma lista de (B, L, h) positivos")
    return [tuple(float(v) for v in d) for d in escada]


def _escopo(tipo, com_horizontal):
    return {
        "geotecnia_spt": "implemented",
        "fundacao_rasa": "implemented" if tipo in ("sapata", "bloco")
                         else "not_applicable",
        "fundacao_profunda": "implemented" if tipo == "estaca"
                             else "not_applicable",
        "bloco_de_coroamento": ("partial" if tipo == "estaca"
                                else "not_applicable"),
        # estaca carregada transversalmente (Broms / Matlock-Reese) nao existe
        # no framework: o cortante da base nao e' verificado NA estaca.
        "esforco_horizontal_na_estaca": ("not_available" if tipo == "estaca"
                                         else "not_applicable"),
        # ver a nota de escopo do cabecalho: o modelo global nao devolve esforco
        # por barra na base.
        "momento_base_pilar": "not_available",
        "acao_horizontal_na_fundacao": ("implemented" if com_horizontal
                                        else "not_available"),
        "viga_baldrame": "not_available",
        "recalque_diferencial": "not_available",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def _avisos(spec_fundacao, tipo, horizontais, recomendacao, por_pilar=None):
    avisos = []
    sem_bloco = sorted(
        nome for nome, registro in (por_pilar or {}).items()
        if (registro.get("geometria") or {}).get("bloco_dimensionado") is False
        and (registro["geometria"].get("n_estacas") or 0) > 1)
    if sem_bloco:
        avisos.append({
            "code": "bloco_de_coroamento_nao_dimensionado",
            "pilares": sem_bloco,
            "detail": "o modelo de bielas implementado cobre blocos de 2 e 4 "
                      "estacas; os pilares %s ficaram com um numero fora disso "
                      "e o bloco NAO foi dimensionado nem modelado"
                      % ", ".join(sem_bloco)})
    if not horizontais:
        avisos.append({
            "code": "fundacao_so_gravitacional",
            "detail": "sem estabilidade global calculada (estrutura.vento nao "
                      "declarado), a fundacao foi dimensionada APENAS para a "
                      "carga vertical: tombamento e deslizamento nao foram "
                      "solicitados por acao horizontal nenhuma"})
    avisos.append({
        "code": "momento_base_pilar_nao_avaliado",
        "detail": "o modelo de estabilidade e' um portico GLOBAL (gamma_z e ELS) "
                  "e nao devolve momento por pilar na base; as combinacoes da "
                  "fundacao usam M=0 no topo da sapata"})
    if not spec_fundacao.get("verificacao_estabilidade"):
        avisos.append({
            "code": "verificacao_estabilidade_legada",
            "detail": "fundacao.verificacao_estabilidade nao declarada: a "
                      "estabilidade roda no caminho legado de FS global; declare "
                      "o metodo (NBR 6122 por valores de calculo ou FS global)"})
    if (spec_fundacao.get("tipo") and recomendacao
            and recomendacao["tipo"] in TIPOS
            and recomendacao["tipo"] != spec_fundacao["tipo"]):
        avisos.append({
            "code": "tipo_diverge_da_sondagem",
            "declarado": spec_fundacao["tipo"],
            "recomendado": recomendacao["tipo"],
            "detail": "o tipo declarado prevalece, mas a sondagem recomendava "
                      "outro: %s" % recomendacao["justificativa"]})
    if tipo == "estaca" and not (spec_fundacao.get("estaca") or {}).get("L_m"):
        avisos.append({
            "code": "comprimento_de_estaca_lido_da_sondagem",
            "detail": "estaca.L_m nao declarado: adotado ATRAVESSANDO a primeira "
                      "camada competente (N >= %d) do perfil informado, ate a "
                      "base dela" % N_COMPETENTE})
    return avisos


def relatorio_pt(resultado):
    """Quadro da fundacao, um pilar por linha."""
    gate = resultado["gate"]
    linhas = [
        "FUNDACAO DO EDIFICIO MULTIPAVIMENTO",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
        "  Tipo adotado: %s (%d pilares)" % (resultado["tipo"], gate["n_pilares"]),
    ]
    if resultado["sigma_solo_adm"]:
        linhas.append("  sigma_solo,adm = %.0f kN/m2 (%s)"
                      % (resultado["sigma_solo_adm"],
                         resultado["proveniencia_sigma"]))
    linhas.append("  N maximo de dimensionamento: %.1f kN" % gate["N_max_kN"])
    linhas.append("")
    linhas.append("  %-6s %-12s %10s | %s" % ("pilar", "posicao", "N_dim(kN)",
                                              "geometria"))
    linhas.append("  " + "-" * 62)
    for nome in sorted(resultado["por_pilar"]):
        registro = resultado["por_pilar"][nome]
        geometria = registro["geometria"]
        if geometria is None:
            texto = "REPROVA"
        elif "n_estacas" in geometria:
            texto = "%d estacas D%.0f cm L%.1f m (util %.2f)" % (
                geometria["n_estacas"], geometria["D_m"] * 100,
                geometria["L_m"], geometria["util"])
        else:
            texto = "%.2f x %.2f x %.2f m" % (geometria["B_m"], geometria["L_m"],
                                              geometria["h_m"])
        linhas.append("  %-6s %-12s %10.1f | %s"
                      % (nome, registro["posicao"] or "-",
                         registro["N_dimensionamento_kN"], texto))
    linhas.append("")
    linhas.append("  Gate: %s%s" % ("ATENDE" if gate["OK"] else "REPROVA",
                                    "" if gate["OK"] else
                                    " (%s)" % ", ".join(gate["reprovados"])))
    for aviso in resultado["avisos"]:
        linhas.append("  [aviso] %s" % aviso["detail"])
    return "\n".join(linhas)
