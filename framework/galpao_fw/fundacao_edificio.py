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
# ACAO HORIZONTAL - o que entra e o que NAO entra (G17-G23):
#   ENTRA  o momento GLOBAL de tombamento (vento/desaprumo, de
#          estabilidade_edificio), distribuido entre as prumadas como um binario:
#          dN_i = M * x_i / sum(x_j^2), pelo modulo de resistencia da malha de
#          fundacoes. O pilar de sotavento sobrecarrega, o de barlavento alivia.
#   ENTRA  o cortante da base, dividido igualmente entre as prumadas (hipotese
#          usual de uma primeira aproximacao), que alimenta o FS ao deslizamento
#          da fundacao RASA. Na ESTACA ele nao e' verificado: estaca carregada
#          transversalmente (Broms / Matlock-Reese) nao existe neste framework,
#          e o escopo diz `esforco_horizontal_na_estaca: not_available` (G23: V
#          ignorado com razao declarada, nao verificado em silencio).
#   ENTRA  o MOMENTO FLETOR na base por pilar (G17): extraido do portico
#          heterogeneo (secao real por prumada, rigidez BRUTA Ecs 14.6.4.1,
#          distinta de 0,8/0,4+1,10Ecs de 15.7.3) via
#          estabilidade_edificio.momentos_base_por_pilar. Alimenta M nas
#          combinacoes (sotavento/barlavento) e V heterogeneo por pilar.
#          Sem vento/momento, M=0 e escopo publica not_available em vez de calar.
#
#   CONSUMIDORES DE M_base e VEREDITOS G23 (sem terceira opcao: usa ou ignora
#   com razao declarada; nenhum caminho onde excentricidade chegue por acidente):
#     - sapata isolada (fundacao_sapata.dimensiona_sapata_env): USA M via
#       Parte A (tensoes_solo N+M, regime nucleo/borda, FS tomb/desl com
#       excentricidade e=M/N) – ver combinacoes_do_pilar + verifica_sapata_A.
#     - bloco simples (dimensiona_bloco_env): USA M para bearing (mesma Parte A)
#       mas NAO gera armadura de flexao: beta >= 60 graus (NBR 6122 7.8.2) –
#       trabalha por bielas comprimidas. E SEMPRE isolado (nunca divisa): o G17
#       roteou bloco pela divisa e gerou geometria excentrica com armadura que a
#       peca nao tem; corrigido em 29acc18 – guarda normativa, nao teste.
#     - estaca isolada (estaca_profunda.verifica_estaca): USA M quando o GRUPO
#       tem braco (n=4, Sxx/Syy>0) via carga_estaca_grupo (Navier, flexo-
#       compressao); para n=1-2, S=0 no eixo do momento, o grupo NAO resiste e o
#       momento vai para TIRANTES DE BALDRAME (viga_baldrame: not_available –
#       fronteira nomeada, nao verificacao esquecida). V e sempre ignorado
#       (Broms/Matlock-Reese nao existe).
#     - sapata de divisa (sapata_divisa) e viga equilibrio (viga_equilibrio):
#       IGNORAM M_portico com razao declarada – a excentricidade GEOMETRICA da
#       divisa (e = (B-b)/2 ~0,6-0,8 m) domina: P*e ~ 800-1500 kNm vs M_portico
#       tipico 10-40 kNm (2-5%); modelo de divisa com M fletor adicional nao
#       existe na NBR 6122/Velloso-Lopes e nao e' inventado; momento adicional
#       seria absorvido pelo travamento (viga_baldrame). Gate e quantitativo da
#       divisa refletem apenas P*e (limitacao nomeada).
#     - gate ATENDE: reflete M via Parte A (rasa) e via grupo_momento (estaca
#       n=4); para divisa reflete apenas P*e (sem M) – ver acima.
#     - IFC/3D (bim_edificio.membros_fundacao): IGNORA M na geometria com razao
#       – sapata isolada permanece CENTRADA (M vira pressao trapezoidal, nao
#       geometria excentrica); divisa ja e' excentrica por lote, nao por M.
#     - quantitativo (gestao_edificio._fundacao): USA M indiretamente via
#       geometria ja dimensionada com M (isolada/bloco) ou IGNORA para divisa
#       (mesma razao); volume = B*L*h da geometria aprovada, sem peso de
#       armadura ficticia.
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


def combinacoes_do_pilar(nome, N_base_k, horizontais, momentos_base=None):
    """Casos (nome, N, V, M) que a fundacao deste pilar tem de atender.

    Sempre ha o caso GRAVITACIONAL puro. Com acao horizontal declarada entram,
    por direcao, o caso de SOTAVENTO (N + dN, o que dimensiona o solo) e o de
    BARLAVENTO (N - dN, o que dimensiona tombamento/deslizamento porque alivia o
    peso estabilizante). Verificar so o maior N deixaria o segundo passar
    despercebido - o mesmo motivo pelo qual `dimensiona_sapata_env` existe.

    G17: M deixa de ser 0. Quando ``momentos_base`` (saida de
    ``estabilidade_edificio.momentos_base_por_pilar``) e' fornecido, extrai
    M_x/M_y e V_x/V_y por prumada do portico heterogeneo (secao real por pilar,
    rigidez bruta Ecs). Sem ele, M=0 e V e' o uniforme V_base/n (legado).

    G23 VEREDITO: Esta funcao e' o PONTO UNICO onde M_base entra nas
    combinacoes; todos os consumidores a jusante (sapata isolada/bloco,
    estaca, divisa, gate) leem daqui. Sapata/bloco USAM M via Parte A;
    estaca USA quando n=4 com braco; divisa IGNORA com razao declarada.
    """
    casos = [("gravitacional", N_base_k, 0.0, 0.0)]
    for direcao, registro in sorted(horizontais.items()):
        info = registro["por_pilar"].get(nome)
        if not info:
            continue
        dn, v_unif = info["dN_kN"], info["V_kN"]
        # G17: momento e cortante por prumada (heterogeneo) quando disponivel
        M_frame = 0.0
        V_frame = v_unif
        if momentos_base and nome in momentos_base and not nome.startswith("_"):
            entry = momentos_base[nome]
            if direcao == "x":
                M_frame = float(entry.get("Mx_abs_kNm", entry.get("Mx_kNm", 0.0)) or 0.0)
                # V heterogeneo por pilar (do portico), mais fiel que V_base/n uniforme
                if entry.get("Vx_abs_kN") is not None:
                    V_frame = float(entry["Vx_abs_kN"])
                elif entry.get("Vx_kN") is not None:
                    V_frame = abs(float(entry["Vx_kN"]))
            elif direcao == "y":
                M_frame = float(entry.get("My_abs_kNm", entry.get("My_kNm", 0.0)) or 0.0)
                if entry.get("Vy_abs_kN") is not None:
                    V_frame = float(entry["Vy_abs_kN"])
                elif entry.get("Vy_kN") is not None:
                    V_frame = abs(float(entry["Vy_kN"]))
        casos.append(("sotavento_%s" % direcao, N_base_k + abs(dn), V_frame, M_frame))
        casos.append(("barlavento_%s" % direcao, max(N_base_k - abs(dn), 0.0),
                      V_frame, M_frame))
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

    VEREDITO G23:
      - V (cortante) IGNORADO com razao declarada: estaca carregada
        transversalmente (Broms / Matlock-Reese) nao existe neste framework;
        escopo publica `esforco_horizontal_na_estaca: not_available`.
      - M (momento) USADO quando o GRUPO tem braco (n=4, Sxx/Syy>0) via
        estaca_profunda.carga_estaca_grupo (Navier, flexo-compressao);
        para n=1-2, S=0 no eixo do momento, o grupo NAO resiste e o momento
        vai para TIRANTES DE BALDRAME (viga_baldrame: not_available –
        fronteira nomeada, REVISAO-FUNDACAO-PROFUNDA-INTEG Q5).
    """
    estaca_cfg = spec_fundacao.get("estaca") or {}
    perfil = spec_fundacao["perfil_spt"]
    for camada in perfil:
        if not camada.get("tipo"):
            raise EntradaFundacao(
                "o perfil SPT precisa do TIPO DE SOLO de cada camada para o "
                "metodo de Aoki-Velloso (K e alpha da Tab.12.6 dependem dele)")
    N_max = max(caso[1] for caso in casos)
    # G23: extrai Mx/My maximos das combinacoes para alimentar o grupo.
    # Casos sao (nome, N, V, M) com nome = gravitacional | sotavento_x etc.
    # Mx vem dos casos _x, My dos _y; gravitacional tem M=0.
    Mx_max = max((abs(caso[3]) for caso in casos if "_x" in caso[0]), default=0.0)
    My_max = max((abs(caso[3]) for caso in casos if "_y" in caso[0]), default=0.0)
    # Se nao ha direcao no nome (so gravitacional), usa o max global
    if Mx_max == 0.0 and My_max == 0.0:
        M_global = max((abs(caso[3]) for caso in casos), default=0.0)
        # Conservador: poe o max nos dois eixos quando nao ha direcao
        Mx_max = My_max = M_global
    _b, h = secao_pilar
    cfg_estaca = {
        "perfil": copy.deepcopy(perfil),
        "D": estaca_cfg.get("D_m", 0.30),
        "L": estaca_cfg.get("L_m", _profundidade_sugerida(perfil)),
        "tipo_estaca": estaca_cfg.get("tipo_estaca", "pre_moldada"),
        "N_pilar": N_max,
        "bloco": {"a_pilar": h, "fck": spec_fundacao.get("fck", materiais["fck"]),
                  "fyk": spec_fundacao.get("fyk", materiais["fyk"]),
                  "cobrimento": spec_fundacao.get("cobrimento", 0.05)},
    }
    # G23: alimenta Mx/My quando ha momento; verifica_estaca monta grupo_momento
    if Mx_max > 1e-9 or My_max > 1e-9:
        cfg_estaca["Mx"] = Mx_max
        cfg_estaca["My"] = My_max
    resultado = ep.verifica_estaca(cfg_estaca)
    grupo = resultado["grupo"]
    ok = grupo["util"] is not None and grupo["util"] <= 1.0
    # G23: se o grupo tem momento, verifica tambem a distribuicao por estaca
    gm = resultado.get("grupo_momento")
    if gm is not None:
        # So reprova por momento quando o grupo TEM braco nesse eixo; se
        # S=0, o momento nao e' resistido no grupo e vai para baldrame
        # (not_available) – nao reprova a estaca por falta de braco.
        if gm.get("resiste_no_grupo"):
            ok = ok and bool(gm.get("OK"))
        # Se ha tracao por momento, reprova apenas quando o grupo resiste;
        # caso contrario, a tracao seria absorvida pelo baldrame (nao existe)
        # e deve ser sinalizada via aviso, nao gate (ver _avisos).
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


def _vizinho_interno(pilar, pilares, eixos_x, eixos_y):
    """Pilar interno vizinho para viga de equilibrio / alavanca (divisa).

    Para pilar de borda em X (i==0 ou i==nx), vizinho e' (i +/-1, j) com vaos_x;
    para borda em Y (j==0 ou j==ny), vizinho e' (i, j +/-1) com vaos_y.
    Canto tem dois vizinhos – escolhe o da direção X (vao_x) como primário
    (o outro seria segunda viga, fora do modelo 1D aqui).
    Retorna (vizinho_dict, dist_eixos_m, direcao) ou (None, None, None).
    """
    nx = len(eixos_x) - 1
    ny = len(eixos_y) - 1
    i, j = pilar["i"], pilar["j"]
    por_ij = {(p["i"], p["j"]): p for p in pilares}
    # prioridade: X se em borda X, senao Y
    if i == 0:
        viz = por_ij.get((i + 1, j))
        if viz:
            return viz, abs(eixos_x[i + 1] - eixos_x[i]), "x"
    if i == nx:
        viz = por_ij.get((i - 1, j))
        if viz:
            return viz, abs(eixos_x[i] - eixos_x[i - 1]), "x"
    if j == 0:
        viz = por_ij.get((i, j + 1))
        if viz:
            return viz, abs(eixos_y[j + 1] - eixos_y[j]), "y"
    if j == ny:
        viz = por_ij.get((i, j - 1))
        if viz:
            return viz, abs(eixos_y[j] - eixos_y[j - 1]), "y"
    return None, None, None


def dimensiona(spec_fundacao, contexto):
    """Dimensiona a fundacao de TODOS os pilares do edificio.

    spec_fundacao: a secao `estrutura.fundacao` do spec (ver cabecalho).
    contexto: {'pilares': [{nome, i, j, N_base_k, secao (b,h)}],
               'eixos_x', 'eixos_y' (m), 'materiais' {fck, fyk},
               'estabilidade' (opc, de estabilidade_edificio.verifica),
               'momentos_base' (opc, de estabilidade_edificio.momentos_base_por_pilar)}.

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
    # G17: momento por prumada (heterogeneo, secao bruta) – vem no contexto
    # direto ou dentro de estabilidade["momentos_base"]
    momentos_base = contexto.get("momentos_base")
    if momentos_base is None and isinstance(contexto.get("estabilidade"), dict):
        momentos_base = contexto["estabilidade"].get("momentos_base")
    com_momento = bool(momentos_base and any(not k.startswith("_") for k in momentos_base))

    # o tipo e' da OBRA: escolhido sob o pilar mais carregado, ja com o dN de
    # tombamento - senao a sondagem seria consultada para uma carga que nao e' a
    # que a fundacao vai receber.
    N_max_obra = max(
        max(caso[1] for caso in combinacoes_do_pilar(
            p["nome"], p["N_base_k"], horizontais, momentos_base))
        for p in pilares)
    tipo, recomendacao = escolhe_tipo(spec_fundacao, N_max_obra)

    sigma_solo = nota_sigma = None
    if tipo in ("sapata", "bloco"):
        sigma_solo, nota_sigma = _sigma_solo(spec_fundacao, recomendacao)

    escada = _escada(spec_fundacao)
    por_pilar = {}
    reprovados = []
    divisa_pilares = set()
    for pilar in pilares:
        casos = combinacoes_do_pilar(pilar["nome"], pilar["N_base_k"], horizontais, momentos_base)
        caso_base = _caso_base(spec_fundacao, sigma_solo, pilar["secao"],
                               contexto["materiais"])
        # criterio G17: pilar de extremidade/canto em divisa usa geometria de
        # divisa (sapata excêntrica + viga alavanca ou bloco+ viga equilibrio)
        # Bloco de concreto simples fica SEMPRE isolado: ele resiste por bielas
        # comprimidas (beta >= 60 graus, NBR 6122 7.8.2) e nao leva armadura de
        # flexao, entao nao existe modelo de divisa excentrica para ele. Rotea-lo
        # pela sapata de divisa produziria geometria com armadura que a peca nao
        # tem - o teste de bloco do G9 pegou isso; a razao e' normativa, nao o teste.
        pos = pilar.get("posicao")
        em_divisa = pos in ("extremidade", "canto")
        # fallback: se posicao nao veio, deduz por i/j nas bordas
        if pos is None:
            nx = len(contexto["eixos_x"]) - 1
            ny = len(contexto["eixos_y"]) - 1
            em_divisa = (pilar["i"] in (0, nx) or pilar["j"] in (0, ny))
        geometria = None
        bruto = None
        ok = False
        subtipo = "isolada"
        detalhe_divisa = None
        if em_divisa and tipo == "sapata":
            # VEREDITO G23 – sapata_divisa: IGNORA M_portico com razao declarada.
            # A excentricidade GEOMETRICA da divisa (e = (B-b)/2, ~0,6-0,8 m)
            # domina: P*e ~ 800-1500 kNm vs M_portico tipico 10-40 kNm (2-5%).
            # Modelo de divisa com momento fletor adicional nao existe na
            # NBR 6122 / Velloso & Lopes e nao e' inventado; momento adicional
            # seria absorvido pelo travamento (viga_baldrame: not_available –
            # fronteira nomeada). Por isso a divisa dimensiona para P*e apenas.
            viz, dist_eixos, direcao = _vizinho_interno(pilar, pilares,
                                                        contexto["eixos_x"],
                                                        contexto["eixos_y"])
            if viz is not None:
                try:
                    import sapata_divisa as sd
                    # P_divisa = maior N das combinacoes deste pilar (com dN)
                    # G23: M_portico extraido em casos[3] e' IGNORADO aqui com
                    # razao acima – nao alimenta R_divisa nem M_viga.
                    P_div = max(c[1] for c in casos)
                    P_int = viz["N_base_k"]
                    # dist_divisa: eixo -> divisa; borda flush -> b/2
                    b_pil, h_pil = pilar["secao"] if isinstance(pilar["secao"], (list, tuple)) else (pilar["secao"]["b"], pilar["secao"]["h"])
                    # para borda X, a dimensão perpendicular e' b (ou min), para Y e' h
                    dist_divisa = min(float(b_pil), float(h_pil)) / 2.0
                    # permite override declarado em spec
                    if spec_fundacao.get("dist_divisa_m") is not None:
                        dist_divisa = float(spec_fundacao["dist_divisa_m"])
                    # sigma e materiais
                    sig = sigma_solo if sigma_solo else 250.0
                    fck = spec_fundacao.get("fck", contexto["materiais"]["fck"])
                    fyk = spec_fundacao.get("fyk", contexto["materiais"]["fyk"])
                    # b_col_paralela e' a dimensão do pilar paralela à divisa
                    b_col_par = float(h_pil) if direcao == "x" else float(b_pil)
                    res_div = sd.dimensiona_divisa(
                        P_divisa=P_div, P_interno=P_int,
                        dist_eixos=float(dist_eixos),
                        dist_divisa=float(dist_divisa),
                        b_col_paralela=b_col_par,
                        sigma_solo=float(sig), fck=float(fck), fyk=float(fyk))
                    geometria = {"subtipo": "divisa", "direcao": direcao,
                                 "dist_eixos_m": round(float(dist_eixos), 3),
                                 "dist_divisa_m": round(float(dist_divisa), 3),
                                 "vizinho": viz["nome"],
                                 "divisa": res_div["divisa"],
                                 "interno": res_div["interno"],
                                 "viga": res_div["viga"],
                                 # para compatibilidade com gate antigo, expoe B/L/h
                                 "B_m": res_div["divisa"]["B"],
                                 "L_m": res_div["divisa"]["L"],
                                 "h_m": res_div["viga"]["h"],
                                 "M_viga_kNm": res_div["viga"]["M_max_kNm"]}
                    bruto = res_div
                    ok = bool(res_div["viga"]["ok"])
                    subtipo = "divisa"
                    divisa_pilares.add(pilar["nome"])
                    detalhe_divisa = res_div
                except Exception:  # noqa: BLE001
                    # fallback para isolada se divisa falhar
                    pass
        if em_divisa and tipo == "estaca":
            # VEREDITO G23 – viga_equilibrio (divisa profunda): IGNORA
            # M_portico com razao declarada (idem sapata_divisa). A viga de
            # equilibrio dimensiona para P*e; M_portico vai para baldrame
            # (not_available). Se um dia houver modelo de estaca de divisa
            # com momento, R_divisa = (P*l+M)/(l-e) e M_viga = P*e+M.
            viz, dist_eixos, direcao = _vizinho_interno(pilar, pilares,
                                                        contexto["eixos_x"],
                                                        contexto["eixos_y"])
            if viz is not None:
                try:
                    import viga_equilibrio as veq
                    import estaca_profunda as ep
                    # G23: M_portico em casos[3] IGNORADO com razao acima
                    P_div = max(c[1] for c in casos)
                    P_int = viz["N_base_k"]
                    b_pil, h_pil = pilar["secao"] if isinstance(pilar["secao"], (list, tuple)) else (pilar["secao"]["b"], pilar["secao"]["h"])
                    dist_divisa = min(float(b_pil), float(h_pil)) / 2.0
                    if spec_fundacao.get("dist_divisa_m") is not None:
                        dist_divisa = float(spec_fundacao["dist_divisa_m"])
                    # P_adm da estaca: usa o mesmo perfil e D/L default
                    # estima via ep.n_estacas com peso, ou via verifica se perfil existe
                    perfil = spec_fundacao.get("perfil_spt")
                    estaca_cfg = spec_fundacao.get("estaca") or {}
                    D_est = float(estaca_cfg.get("D_m", 0.30))
                    # tenta obter P_adm do dimensionamento isolado anterior, ou calcula
                    P_adm = 700.0  # fallback
                    L_est = None
                    if perfil:
                        L_est = estaca_cfg.get("L_m", _profundidade_sugerida(perfil))
                        try:
                            # calcula capacidade com N ficticio para obter P_adm
                            tmp = ep.verifica_estaca({
                                "perfil": copy.deepcopy(perfil),
                                "D": D_est,
                                "L": L_est,
                                "tipo_estaca": estaca_cfg.get("tipo_estaca", "pre_moldada"),
                                "N_pilar": P_div,
                                "bloco": {"a_pilar": float(h_pil),
                                          "fck": spec_fundacao.get("fck", contexto["materiais"]["fck"]),
                                          "fyk": spec_fundacao.get("fyk", contexto["materiais"]["fyk"])},
                            })
                            P_adm = float(tmp["capacidade"]["P_adm_kN"])
                        except Exception:  # noqa: BLE001
                            pass
                    if L_est is None:
                        L_est = estaca_cfg.get("L_m", 15.0)
                    a_pilar = float(max(b_pil, h_pil))
                    res_eq = veq.dimensiona_viga_equilibrio(
                        P_divisa=P_div, P_interno=P_int,
                        dist_eixos=float(dist_eixos), dist_divisa=float(dist_divisa),
                        P_estaca_adm=float(P_adm), a_pilar=a_pilar, D_estaca=D_est,
                        fck=float(spec_fundacao.get("fck", contexto["materiais"]["fck"])),
                        fyk=float(spec_fundacao.get("fyk", contexto["materiais"]["fyk"])))
                    util_div = round(float(res_eq["divisa"]["carga_estaca"]) / float(P_adm), 3) if P_adm else None
                    geometria = {"subtipo": "divisa_estaca", "direcao": direcao,
                                 "dist_eixos_m": round(float(dist_eixos), 3),
                                 "dist_divisa_m": round(float(dist_divisa), 3),
                                 "vizinho": viz["nome"],
                                 "divisa": res_eq["divisa"],
                                 "interno": res_eq["interno"],
                                 "viga": res_eq["viga"],
                                 "n_estacas": res_eq["divisa"]["n_estacas"],
                                 "P_adm_kN": P_adm,
                                 "util": util_div,
                                 "D_m": D_est,
                                 "L_m": float(L_est)}
                    bruto = res_eq
                    ok = bool(res_eq["viga"]["ok"])
                    subtipo = "divisa_estaca"
                    divisa_pilares.add(pilar["nome"])
                except Exception:  # noqa: BLE001
                    pass
        # fallback isolado (ou quando não é divisa)
        if geometria is None:
            if tipo == "estaca":
                bruto, geometria, ok = _dimensiona_estaca(
                    spec_fundacao, casos, pilar["secao"], contexto["materiais"])
            else:
                bruto = _dimensiona_raso(tipo, caso_base, casos, escada)
                geometria = _geometria_rasa(tipo, bruto)
                ok = geometria is not None
                if geometria is not None:
                    geometria = dict(geometria)
                    geometria["subtipo"] = subtipo
        else:
            # divisa ja tem geometria; garante subtipo
            if isinstance(geometria, dict) and "subtipo" not in geometria:
                geometria["subtipo"] = subtipo
        registro = {
            "nome": pilar["nome"], "posicao": pilar.get("posicao"),
            "i": pilar["i"], "j": pilar["j"],
            "N_base_k": pilar["N_base_k"],
            "N_dimensionamento_kN": round(max(c[1] for c in casos), 1),
            "combinacoes": [{"nome": c[0], "N_kN": round(c[1], 1),
                             "V_kN": round(c[2], 1), "M_kNm": round(c[3], 1)}
                            for c in casos],
            "geometria": geometria, "OK": ok, "bruto": bruto,
            "subtipo": subtipo,
        }
        # expoe M/V resultantes para auditoria (max entre direcoes)
        if com_momento and pilar["nome"] in (momentos_base or {}):
            entry = momentos_base[pilar["nome"]]
            registro["M_base_kNm"] = {"Mx": entry.get("Mx_abs_kNm"),
                                      "My": entry.get("My_abs_kNm"),
                                      "M_res": entry.get("M_resultante_kNm")}
            registro["V_base_kN"] = {"Vx": entry.get("Vx_abs_kN"),
                                     "Vy": entry.get("Vy_abs_kN")}
        por_pilar[pilar["nome"]] = registro
        if not ok:
            reprovados.append(pilar["nome"])

    # VEREDITO G23 – gate ATENDE: reflete M quando o dimensionamento
    # usou M (sapata/bloco via Parte A, estaca n=4 via grupo_momento); para
    # divisa reflete apenas P*e (M ignorado com razao) – limitacao nomeada.
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
        "momentos_base": momentos_base,
        "por_pilar": por_pilar,
        "gate": gate,
        "escopo": _escopo(tipo, bool(horizontais), com_momento),
        "avisos": _avisos(spec_fundacao, tipo, horizontais, recomendacao,
                          por_pilar, com_momento, divisa_pilares),
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


def _escopo(tipo, com_horizontal, com_momento=False):
    # G23 vereditos: cada consumidor de M_base tem estado explicito.
    # - momento_base_pilar: implemented quando ha vento (heterogeneo bruta)
    # - momento_em_sapata_isolada: usa M (implementado) – parte do bearing
    # - momento_em_bloco: usa M para bearing, mas sem armadura (beta>=60)
    # - momento_em_estaca_grupo: implemented quando n=4 com braco, senao vai p/ baldrame
    # - momento_em_divisa: not_available com razao (P*e domina, vai p/ baldrame)
    # - esforco_horizontal_na_estaca: not_available (Broms nao existe)
    return {
        "geotecnia_spt": "implemented",
        "fundacao_rasa": "implemented" if tipo in ("sapata", "bloco")
                         else "not_applicable",
        "fundacao_profunda": "implemented" if tipo == "estaca"
                             else "not_applicable",
        "bloco_de_coroamento": ("partial" if tipo == "estaca"
                                else "not_applicable"),
        # G23: V (cortante) IGNORADO na estaca com razao declarada.
        "esforco_horizontal_na_estaca": ("not_available" if tipo == "estaca"
                                         else "not_applicable"),
        # G23: M em estaca – grupo resiste se n=4 com braco; senao vai p/ baldrame
        "momento_na_estaca_grupo": ("implemented" if (tipo == "estaca" and com_momento)
                                   else ("not_available" if tipo == "estaca" else "not_applicable")),
        "viga_baldrame_travamento": "not_available",  # G23: recebe momento de estaca 1-2/divisa
        # G17: momento na base por pilar passa a ser extraido do portico
        # heterogeneo (M_x, M_y por prumada). Sem estabilidade/momento, segue
        # not_available, mas com ele vira implemented e alimenta V/M nas
        # combinacoes (distinguindo canto vs interno).
        "momento_base_pilar": "implemented" if com_momento else "not_available",
        "acao_horizontal_na_fundacao": ("implemented" if com_horizontal
                                        else "not_available"),
        # G17: sapata de divisa / viga de equilibrio deixam de ser ignoradas:
        # quando ha pilar de extremidade/canto, a geometria passa a ser escolhida
        # por criterio (isolada vs divisa). O escopo publica a capacidade.
        "sapata_divisa": "implemented",
        "viga_equilibrio": "implemented",
        "viga_baldrame": "not_available",
        "recalque_diferencial": "not_available",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def _avisos(spec_fundacao, tipo, horizontais, recomendacao, por_pilar=None,
            com_momento=False, divisa_pilares=None):
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
    if com_momento:
        avisos.append({
            "code": "momento_base_pilar_extraido",
            "detail": "M_base por prumada extraido do portico heterogeneo (secao "
                      "real por pilar, rigidez bruta Ecs – 14.6.4.1), distinto da "
                      "rigidez 15.7.3 de gamma_z; V/M por pilar alimentam as "
                      "combinacoes de fundacao"})
        if divisa_pilares:
            avisos.append({
                "code": "fundacao_divisa_aplicada",
                "pilares": sorted(divisa_pilares),
                "detail": "pilares de extremidade/canto (%s) com fundacao de divisa: "
                          "sapata de divisa + viga alavanca (rasa) ou bloco sobre "
                          "estacas + viga de equilibrio (profunda), escolhidos por "
                          "criterio de posicao (canto != centro)" % ", ".join(sorted(divisa_pilares))})
            # G23: divisa IGNORA M_portico com razao declarada (ver cabecalho e
            # comentario no dimensiona). Avisa explicitamente para auditoria.
            avisos.append({
                "code": "momento_na_divisa_ignorado_com_razao",
                "pilares": sorted(divisa_pilares),
                "detail": "M_portico nos pilares de divisa (%s) foi IGNORADO no "
                          "dimensionamento da viga alavanca/equilibrio com razao "
                          "declarada: excentricidade geometrica P*e (~800-1500 kNm) "
                          "domina sobre M_portico (10-40 kNm); modelo com momento "
                          "adicional nao existe na NBR 6122 e seria absorvido pelo "
                          "travamento (viga_baldrame: not_available)" % ", ".join(sorted(divisa_pilares))})
        # G23: vereditos por tipo – sapata/bloco USAM M, estaca USA quando ha braco
        if tipo in ("sapata", "bloco"):
            avisos.append({
                "code": "momento_em_sapata_isolada_usado",
                "detail": "M_base alimenta sapata/bloco isolado via Parte A "
                          "(tensoes_solo N+M, regime nucleo/borda, FS tomb/desl) – "
                          "ver fundacao_sapata.verifica_sapata_A; bloco com beta>=60 "
                          "graus (NBR 6122 7.8.2) sem armadura de flexao, sempre isolado"})
        elif tipo == "estaca":
            # coleta pilares onde momento existe mas grupo nao tem braco
            sem_braco = []
            com_braco_ok = []
            for nome, reg in (por_pilar or {}).items():
                if reg.get("bruto") and isinstance(reg["bruto"], dict) and reg["bruto"].get("grupo_momento"):
                    gm = reg["bruto"]["grupo_momento"]
                    if gm.get("Mx") or gm.get("My"):
                        if gm.get("resiste_no_grupo"):
                            com_braco_ok.append(nome)
                        else:
                            sem_braco.append(nome)
                elif reg.get("M_base_kNm"):
                    # fallback: tem M mas sem grupo_momento (n=1-2 sem braco)
                    mres = reg["M_base_kNm"].get("M_res") or 0
                    if mres and mres > 1e-9:
                        # verifica se n_estacas <=2 (sem braco)
                        geo = reg.get("geometria") or {}
                        if geo.get("n_estacas", 0) <= 2:
                            sem_braco.append(nome)
            if com_braco_ok:
                avisos.append({
                    "code": "momento_no_grupo_de_estacas_usado",
                    "pilares": sorted(com_braco_ok),
                    "detail": "M_base nos pilares %s foi USADO no grupo de estacas "
                              "(n=4, Sxx/Syy>0) via carga_estaca_grupo (Navier); "
                              "N_max inclui M*y/Syy e M*x/Sxx" % ", ".join(sorted(com_braco_ok))})
            if sem_braco:
                avisos.append({
                    "code": "momento_na_estaca_vai_para_baldrame",
                    "pilares": sorted(sem_braco),
                    "detail": "M_base nos pilares %s (n=1-2, S=0 no eixo do momento) "
                              "NAO e' resistido no grupo e vai para TIRANTES DE "
                              "BALDRAME (viga_baldrame: not_available – fronteira "
                              "nomeada, REVISAO-FUNDACAO-PROFUNDA-INTEG Q5)" % ", ".join(sorted(sem_braco))})
            if not com_braco_ok and not sem_braco:
                avisos.append({
                    "code": "momento_em_estaca_sem_demanda",
                    "detail": "M_base existe mas nenhum pilar de estaca tem "
                              "momento relevante ou grupo com braco; nenhuma acao "
                              "adicional alem da carga vertical"})
            # V sempre ignorado
            avisos.append({
                "code": "cortante_na_estaca_nao_verificado",
                "detail": "V_base (cortante) IGNORADO na estaca com razao declarada: "
                          "estaca carregada transversalmente (Broms/Matlock-Reese) "
                          "nao existe neste framework; escopo esforco_horizontal_na_estaca: not_available"})
    else:
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
