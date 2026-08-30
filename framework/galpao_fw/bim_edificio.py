# ============================================================================
# bim_edificio.py - MODELO NEUTRO + BIM (IFC4) DO EDIFICIO MULTIPAVIMENTO
#
# O G3 entregou a cadeia de calculo (carga NBR 6120 -> laje -> viga continua ->
# pilar -> descida) e o G5 a ligou ao Project Loop, mas a tipologia 'edificio'
# declarava apenas report e drawings: o resultado do calculo existia como numero
# no relatorio e como planta 2D, nunca como MODELO. Este modulo e' a camada que
# faltava - o mesmo papel que `modelo_neutro` faz para o galpao de aco.
#
# CAMINHO BARATO (o do roteiro de interoperabilidade): a malha do pavimento-tipo
# e' REGULAR e ja esta calculada; entao o BIM sai por `ifc_emit` PURO-Python, sem
# FreeCAD. O caminho FreeCAD existe em paralelo (build_concreto, caixas solidas)
# e serve de CROSS-CHECK: as duas descricoes da mesma estrutura tem de bater peca
# a peca (o anti-padrao que este projeto persegue e' "duas descricoes, uma
# envelhece").
#
# CONVENCAO GEOMETRICA (a mesma dos demais verticais, para federar sem
# transformacao): coordenadas em MILIMETROS; X = direcao dos vaos_x, Y = direcao
# dos vaos_y, Z = altura, origem no canto (0,0) da malha e base do 1o lance em
# z=0. Secao de barra em METROS; caixa (`dims`) em MILIMETROS.
#
# ORIENTACAO DA SECAO - e' aqui que mora o bug caro (dois precedentes no
# historico: coluna de galpao com o eixo forte fora do plano do portico, e TODA
# barra retangular do 3D federado girada 90 graus). A regra unica deste modulo:
#
#   `bf` = largura, a dimensao HORIZONTAL transversal ao eixo da barra;
#   `d`  = altura, a dimensao no eixo VERTICAL (viga) / na direcao X (pilar).
#
# Ela vale simultaneamente para o emissor IFC e para o build FreeCAD porque as
# duas bases locais coincidem; os testes de guarda MEDEM o retangulo emitido (nao
# leem a string do perfil), que e' a unica forma de pegar uma peca deitada.
#
# EMPILHAMENTO VERTICAL (por que as pecas nao se interpenetram): o nivel k tem o
# TOPO DA LAJE na cota z_k = k * pe_direito. Dai para baixo:
#   laje   : z_k - h_laje  ..  z_k
#   viga   : z_k - h_viga  ..  z_k - h_laje   (a NERVURA, abaixo da laje)
#   pilar  : z_(k-1)       ..  z_k - h_viga   (encosta na face inferior da viga)
# Cada par compartilha FACE e nao volume - a varredura de interferencia sai
# limpa sem folga artificial. As vigas em Y sao recuadas de b/2 em cada ponta,
# onde encontram as vigas em X: sem esse recorte as duas se cruzariam no no' e o
# mesmo concreto seria contado duas vezes no quantitativo.
#
# A FUNDACAO entra no modelo (G9) quando ela foi DIMENSIONADA - isto e', quando
# a sondagem estava declarada. Sapata e bloco viram IfcFooting sob o pilar, com
# o topo na cota de apoio; a estaca vira IfcPile por estaca do grupo. Sem
# fundacao calculada, nenhuma peca de fundacao e' emitida: um IFC com uma sapata
# inventada e' pior que um IFC sem sapata nenhuma.
#
# O QUE ESTE MODULO NAO EMITE, e por que: escada (nao ha posicao declarada na
# malha), alvenaria (bloqueada por fonte), viga baldrame (nao dimensionada).
# Peca que nao foi calculada nao entra no modelo.
# ============================================================================
"""Modelo neutro e IFC4 do edificio multipavimento, puro-Python (sem FreeCAD)."""

from __future__ import annotations

import geometria_membros as gm

MM = gm.MM

# tolerancia geometrica das conferencias (mm). 1 mm: abaixo disso e'
# arredondamento de ponto flutuante, acima e' outra estrutura.
TOL_MM = gm.TOL_MM


class GeometriaIncoerente(ValueError):
    """A entrada nao descreve um edificio construivel (nao um erro de calculo)."""


def _fck_MPa(estrutura):
    """fck em MPa a partir do resultado; kN/m2 -> MPa (o spec usa kN/m2)."""
    laje = estrutura.get("laje") or {}
    fck = laje.get("fck")
    return float(fck) / 1000.0 if fck else None


def _material(estrutura):
    fck = _fck_MPa(estrutura)
    return "Concreto C%.0f" % fck if fck else "Concreto"


def _eixos(vaos):
    """Coordenadas (m) das linhas de eixo a partir da lista de vaos."""
    xs = [0.0]
    for v in vaos:
        xs.append(xs[-1] + float(v))
    return xs


def niveis(estrutura, pe_direito):
    """Cotas do TOPO DA LAJE de cada pavimento, da BASE para o topo (mm).

    `estrutura['descida']['pavimentos']` vem do TOPO para a BASE (a ordem em que
    a carga desce); o modelo 3D e' montado de baixo para cima, entao a lista e'
    invertida aqui - uma vez so, neste ponto, para que nenhum outro trecho
    precise lembrar da inversao.
    """
    pavs = list(estrutura["descida"]["pavimentos"])[::-1]
    nomes = [pv["nome"] for pv in pavs]
    if len(set(nomes)) != len(nomes):
        # o nome do pavimento e' a CHAVE do IfcBuildingStorey e o sufixo da marca
        # de cada peca. Repetido, dois andares viram um so no visualizador e as
        # pecas de um somem dentro do outro - em silencio.
        raise GeometriaIncoerente(
            "ha pavimentos com o mesmo nome (%s); o nome identifica o andar no "
            "modelo e nao pode repetir"
            % ", ".join(sorted({n for n in nomes if nomes.count(n) > 1})))
    return [{"nome": nome, "elevacao_mm": (k + 1) * pe_direito * MM}
            for k, nome in enumerate(nomes)]


def _lances_da_base_para_o_topo(pilares, nome):
    """Lances do pilar `nome` na ordem do modelo 3D (base -> topo)."""
    return list(pilares[nome]["lances"])[::-1]


def membros_bim(estrutura, pe_direito=None):
    """Modelo neutro do edificio: pilares, vigas e lajes de todos os pavimentos.

    `estrutura` e' o resultado de `edificio_multipavimento.rodar` (o mesmo dict
    que o adaptador guarda em result['estrutura']). Retorna a lista de membros
    no contrato do `ifc_emit` / `build_concreto`, cada um com a chave
    'pavimento' (o nome do nivel) para que o IFC saia com um IfcBuildingStorey
    por pavimento em vez de um 'Terreo' unico com o predio inteiro dentro.

    Levanta GeometriaIncoerente quando a secao declarada nao permite o
    empilhamento (viga mais rasa que a laje, pe-direito menor que a viga): sao
    dados que descrevem um predio impossivel, e o modelo nao deve arbitrar um
    conserto em silencio.
    """
    pav = estrutura["pavimento"]
    pilares = estrutura["pilares"]

    vaos_x = [float(v) for v in pav["vaos_x"]]
    vaos_y = [float(v) for v in pav["vaos_y"]]
    xs, ys = _eixos(vaos_x), _eixos(vaos_y)

    h_laje = float(estrutura["laje"]["h"])
    b_viga, h_viga = _secao_viga(pav)
    if pe_direito is None:
        pe_direito = _pe_direito(pilares)
    pe_direito = float(pe_direito)

    if h_viga <= h_laje + 1e-9:
        raise GeometriaIncoerente(
            "a viga (h=%.3f m) nao e' mais alta que a laje (h=%.3f m): nao ha "
            "nervura abaixo da laje para modelar" % (h_viga, h_laje))
    if pe_direito <= h_viga + 1e-9:
        raise GeometriaIncoerente(
            "o pe-direito (%.3f m) nao e' maior que a altura da viga (%.3f m): "
            "nao sobra lance de pilar" % (pe_direito, h_viga))
    if 2.0 * b_viga >= min(vaos_y) - 1e-9:
        raise GeometriaIncoerente(
            "a largura da viga (%.3f m) consome o menor vao em Y (%.3f m): a "
            "nervura recuada ficaria de comprimento nulo ou negativo"
            % (b_viga, min(vaos_y)))

    material = _material(estrutura)
    lvls = niveis(estrutura, pe_direito)
    membros = []

    # ------------------------------------------------------------- PILARES
    # um membro por LANCE. A secao do lance e' a que o dimensionamento adotou
    # (ela CRESCE ao descer), entao o modelo mostra o pilar engrossando - e nao
    # a secao da base repetida em toda a altura.
    grade = {(p["i"], p["j"]): p for p in pav["pilares"]}
    for (i, j), p in sorted(grade.items()):
        nome = p["nome"]
        if nome not in pilares:
            # pular em silencio deixaria um furo na malha que so a contagem
            # pegaria depois - e o modelo mostraria uma laje sem apoio.
            raise GeometriaIncoerente(
                "o pilar %s existe na malha do pavimento mas nao foi "
                "dimensionado; nao ha secao para modela-lo" % nome)
        x, y = xs[i] * MM, ys[j] * MM
        lances = _lances_da_base_para_o_topo(pilares, nome)
        if len(lances) != len(lvls):
            raise GeometriaIncoerente(
                "o pilar %s tem %d lances para %d pavimentos: o modelo 3D nao "
                "consegue dizer qual lance esta em qual nivel"
                % (nome, len(lances), len(lvls)))
        for k, lance in enumerate(lances):
            z0 = k * pe_direito * MM
            z1 = lvls[k]["elevacao_mm"] - h_viga * MM
            b, h = float(lance["b"]), float(lance["h"])
            membros.append({
                "tipo": "Column", "marca": "%s-%s" % (nome, lvls[k]["nome"]),
                "perfil": "P%.0fx%.0f" % (h * 100, b * 100),
                # bf ocupa X e d ocupa Y: 'h' e' a dimensao na direcao x (a
                # convencao de pilar_continuo). Invertido, o pilar entra no BIM
                # girado 90 graus e o eixo forte sai do plano dimensionado.
                "secao": {"forma": "RECT", "bf": h, "d": b},
                "p1": [x, y, z0], "p2": [x, y, z1],
                "material": material, "pavimento": lvls[k]["nome"],
                "armadura": {"As_long_cm2": float(lance.get("As_cm2") or 0.0),
                             "taxa_pct": float(lance.get("taxa_pct") or 0.0),
                             "N_base_kN": float(lance.get("N_base_k") or 0.0)},
            })

    # --------------------------------------------------------------- VIGAS
    sec_viga = {"forma": "RECT", "bf": b_viga, "d": h_viga - h_laje}
    # ancoragem 'base': a linha p1/p2 e' a FACE INFERIOR da nervura (cota
    # z_k - h_viga), e ela sobe ate a face inferior da laje. Sem declarar, o
    # emissor IFC centraria o perfil no eixo e a viga desceria d/2 dentro do
    # pilar - a divergencia que o cross-check com o build FreeCAD expos.
    ancoragem = "base"
    perfil_viga = "V%.0fx%.0f" % (b_viga * 100, h_viga * 100)
    for nivel in lvls:
        # a barra e' ancorada pelo FUNDO da nervura: o emissor sobe `d` a partir
        # de p1.z (mesma regra do build), entao o topo cai em z_top - h_laje.
        zb = nivel["elevacao_mm"] - h_viga * MM
        for j in range(len(ys)):                       # vigas que correm em X
            for i in range(len(vaos_x)):
                membros.append({
                    "tipo": "Beam", "marca": "VX-%d-%d-%s" % (j, i + 1, nivel["nome"]),
                    "perfil": perfil_viga, "secao": dict(sec_viga),
                    "ancoragem": ancoragem,
                    "p1": [xs[i] * MM, ys[j] * MM, zb],
                    "p2": [xs[i + 1] * MM, ys[j] * MM, zb],
                    "material": material, "pavimento": nivel["nome"]})
        for i in range(len(xs)):                       # vigas que correm em Y
            for j in range(len(vaos_y)):
                # recuo de b/2 nas duas pontas: a viga em Y morre na FACE da
                # viga em X que ela encontra, em vez de atravessa-la.
                y0 = (ys[j] + b_viga / 2.0) * MM
                y1 = (ys[j + 1] - b_viga / 2.0) * MM
                membros.append({
                    "tipo": "Beam", "marca": "VY-%d-%d-%s" % (i, j + 1, nivel["nome"]),
                    "perfil": perfil_viga, "secao": dict(sec_viga),
                    "ancoragem": ancoragem,
                    "p1": [xs[i] * MM, y0, zb], "p2": [xs[i] * MM, y1, zb],
                    "material": material, "pavimento": nivel["nome"]})

    # ---------------------------------------------------------------- LAJES
    # A laje do painel critico carrega a armadura CALCULADA; as demais nao. O
    # calculo dimensionou UM painel (o de maior area) e estendeu o resultado por
    # gate, nao por painel: copiar essa armadura para todos seria publicar um
    # numero que ninguem calculou naquela posicao.
    laje = estrutura["laje"]
    critico = max(pav["paineis"], key=lambda p: p["lx"] * p["ly"])
    for nivel in lvls:
        z_top = nivel["elevacao_mm"]
        for painel in pav["paineis"]:
            i, j = painel["i"], painel["j"]
            lx, ly = float(painel["lx"]), float(painel["ly"])
            membro = {
                "tipo": "Slab", "marca": "L%d%d-%s" % (i + 1, j + 1, nivel["nome"]),
                "perfil": "LAJE h=%.0fcm" % (h_laje * 100),
                "dims": [lx * MM, ly * MM, h_laje * MM],
                "centro": [(xs[i] + lx / 2.0) * MM, (ys[j] + ly / 2.0) * MM,
                           z_top - h_laje * MM / 2.0],
                "material": material, "pavimento": nivel["nome"]}
            if (i, j) == (critico["i"], critico["j"]):
                membro["armadura"] = _armadura_laje(laje)
            membros.append(membro)

    membros.extend(membros_fundacao(estrutura, xs, ys, material))
    return membros


def membros_fundacao(estrutura, xs, ys, material):
    """Pecas de fundacao sob cada pilar, se a fundacao foi DIMENSIONADA.

    Sapata/bloco -> IfcFooting (caixa com o TOPO na cota de apoio, portanto
    enterrada: z de -(cota+h) a -cota). Estaca -> um IfcPile por estaca do grupo,
    descendo L a partir do fundo do bloco de coroamento.

    Fundacao nao dimensionada devolve lista vazia - e' a mesma regra do resto do
    modulo: peca que ninguem calculou nao aparece.
    """
    fundacao = estrutura.get("fundacao")
    if not isinstance(fundacao, dict) or not fundacao.get("por_pilar"):
        return []
    cota = float((fundacao.get("cota_apoio_m")
                  if fundacao.get("cota_apoio_m") is not None else 1.0))
    membros = []
    for nome in sorted(fundacao["por_pilar"]):
        registro = fundacao["por_pilar"][nome]
        geometria = registro.get("geometria")
        if not geometria:                              # pilar reprovado: sem peca
            continue
        x, y = xs[registro["i"]] * MM, ys[registro["j"]] * MM
        if "n_estacas" in geometria:
            membros.extend(_estacas_do_pilar(nome, geometria, x, y, cota, material))
        else:
            membros.append(_footing(nome, geometria, x, y, cota, material,
                                    registro))
    return membros


def _footing(nome, geometria, x, y, cota, material, registro):
    """Sapata/bloco: caixa com o TOPO na cota de apoio (z = -cota)."""
    B = float(geometria["B_m"]) * MM
    L = float(geometria["L_m"]) * MM
    h = float(geometria["h_m"]) * MM
    membro = {
        "tipo": "Footing", "marca": "SAP-%s" % nome,
        "perfil": "S%.0fx%.0f" % (geometria["B_m"] * 100, geometria["L_m"] * 100),
        "dims": [B, L, h],
        "centro": [x, y, -cota * MM - h / 2.0],
        "material": material, "pavimento": "Fundacao",
    }
    armadura = {"N_dimensionamento_kN": float(registro["N_dimensionamento_kN"])}
    for eixo in ("L", "B"):
        chave = "As_%s_cm2" % eixo
        if geometria.get(chave) is not None:
            armadura[chave] = float(geometria[chave])
    if "beta_graus" in geometria:                      # bloco de concreto SIMPLES
        armadura["beta_graus"] = float(geometria["beta_graus"])
        armadura["concreto_simples"] = True
    membro["armadura"] = armadura
    return membro


def _estacas_do_pilar(nome, geometria, x, y, cota, material):
    """Uma IfcPile por estaca do grupo, na malha do bloco de coroamento."""
    import estaca_profunda as ep

    n = int(geometria["n_estacas"])
    D = float(geometria["D_m"])
    L = float(geometria["L_m"])
    h_bloco = float(geometria.get("bloco_h_m") or 0.0)
    espacamento = 3.0 * D                              # malha padrao do modulo
    topo = -(cota + h_bloco) * MM                      # estaca nasce sob o bloco
    membros = []
    for k, (dx, dy) in enumerate(ep.offsets_grupo(n, espacamento), start=1):
        membros.append({
            "tipo": "Pile", "marca": "EST-%s-%d" % (nome, k),
            "perfil": "D%.0f" % (D * 100),
            "secao": {"forma": "ROUND", "D": D, "bf": D, "d": D},
            "p1": [x + dx * MM, y + dy * MM, topo],
            "p2": [x + dx * MM, y + dy * MM, topo - L * MM],
            "material": material, "pavimento": "Fundacao"})
    if h_bloco > 0:
        # o bloco de coroamento e' a peca que recebe o pilar; sem ele as estacas
        # apareceriam soltas sob a coluna.
        lado = max(2.0 * espacamento, 1.0) * MM if n > 1 else max(2.5 * D, 0.8) * MM
        membros.append({
            "tipo": "Footing", "marca": "BLC-%s" % nome,
            "perfil": "BLOCO %d est." % n,
            "dims": [lado, lado, h_bloco * MM],
            "centro": [x, y, -cota * MM - h_bloco * MM / 2.0],
            "material": material, "pavimento": "Fundacao"})
    return membros


def _armadura_laje(laje):
    """Pset da laje do painel critico: As adotada e malha, por direcao."""
    arm = laje.get("armaduras") or {}
    out = {"painel_critico": True, "h_cm": float(laje.get("h", 0.0)) * 100.0}
    for direcao in ("m_x", "m_y"):
        registro = arm.get(direcao) or {}
        malha = registro.get("malha") or {}
        out["As_%s_cm2_m" % direcao[-1]] = float(
            registro.get("As_adotada") or 0.0) * 1e4
        if malha.get("phi_mm"):
            out["malha_%s" % direcao[-1]] = "phi %.1f c/ %.0f cm" % (
                float(malha["phi_mm"]), float(malha.get("s") or 0.0) * 100.0)
    return out


def _secao_viga(pav):
    """(b, h) da viga do pavimento, deduzidos do PESO PROPRIO que o calculo usou.

    O pavimento-tipo nao republica b_viga/h_viga, mas publica
    `peso_viga_kN_m` = gamma * b * h e as vigas trazem os seus vaos. Ler a secao
    de volta do peso amarra o modelo ao numero que ENTROU na analise: se um dia
    o peso proprio da viga mudar sem que a secao mude, o modelo denuncia em vez
    de desenhar uma viga que nao foi a calculada.
    """
    peso = float(pav["peso_viga_kN_m"])
    area = peso / 25.0                                  # gamma = 25 kN/m3
    b = float(pav.get("b_viga") or 0.0)
    h = float(pav.get("h_viga") or 0.0)
    if b > 0 and h > 0:
        if abs(b * h - area) > 1e-4:
            raise GeometriaIncoerente(
                "a secao da viga (%.3f x %.3f m) nao reproduz o peso proprio "
                "usado na analise (%.3f kN/m)" % (b, h, peso))
        return b, h
    raise GeometriaIncoerente(
        "o pavimento-tipo nao publica b_viga/h_viga; sem a secao declarada nao "
        "ha viga a modelar (peso proprio de %.3f kN/m => area %.4f m2)"
        % (peso, area))


def _pe_direito(pilares):
    """Pe-direito comum a todos os lances; divergencia e' erro de entrada."""
    valores = {round(float(l["pe_direito"]), 6)
               for p in pilares.values() for l in p["lances"]}
    if len(valores) != 1:
        raise GeometriaIncoerente(
            "os lances declaram pe-direitos diferentes (%s); o modelo 3D exige "
            "uma malha de pavimentos uniforme"
            % ", ".join("%.3f" % v for v in sorted(valores)))
    return valores.pop()


# ---------------------------------------------------------------------------
# CONFERENCIAS rotulo x geometria (o que os testes de guarda medem)
# ---------------------------------------------------------------------------
def confere_modelo(estrutura, membros):
    """Compara o MODELO com o CALCULO e devolve as contagens lado a lado.

    Nao levanta: devolve o quadro para quem chamou decidir. `ok` so e' True
    quando todas as contagens batem - um pilar que sumiu do modelo e' um pilar
    que o projetista nao vai ver no visualizador, e nenhum teste de numero pega
    isso.
    """
    pav = estrutura["pavimento"]
    n_niveis = len(estrutura["descida"]["pavimentos"])
    n_pilares = len(estrutura["pilares"])
    nx, ny = len(pav["vaos_x"]), len(pav["vaos_y"])

    por_tipo = {}
    for m in membros:
        por_tipo[m["tipo"]] = por_tipo.get(m["tipo"], 0) + 1
    esperado = {
        "Column": n_pilares * n_niveis,
        # vigas: (ny+1) linhas em X x nx tramos + (nx+1) linhas em Y x ny tramos
        "Beam": ((ny + 1) * nx + (nx + 1) * ny) * n_niveis,
        "Slab": pav["n_paineis"] * n_niveis,
    }
    # FUNDACAO: uma peca por pilar APROVADO (sapata/bloco) ou um bloco + n
    # estacas. A conta e' feita a partir do que o calculo aprovou, nao do que o
    # modelo emitiu - senao a conferencia se compararia consigo mesma.
    fundacao = estrutura.get("fundacao")
    n_footing = n_pile = 0
    if isinstance(fundacao, dict) and fundacao.get("por_pilar"):
        for registro in fundacao["por_pilar"].values():
            geometria = registro.get("geometria")
            if not geometria:
                continue
            if "n_estacas" in geometria:
                n_pile += int(geometria["n_estacas"])
                if geometria.get("bloco_h_m"):
                    n_footing += 1
            else:
                n_footing += 1
    if n_footing:
        esperado["Footing"] = n_footing
    if n_pile:
        esperado["Pile"] = n_pile

    pavimentos_modelo = {m["pavimento"] for m in membros}
    n_andares = n_niveis + (1 if (n_footing or n_pile) else 0)
    return {
        "ok": por_tipo == esperado and len(pavimentos_modelo) == n_andares,
        "por_tipo": por_tipo, "esperado": esperado,
        "n_pavimentos_modelo": len(pavimentos_modelo),
        "n_pavimentos_calculo": n_andares,
    }


def confere_empilhamento(membros):
    """Nenhum par de membros pode ocupar o MESMO volume (AABB, mm3).

    Delega a primitiva compartilhada `geometria_membros`: laje sobre nervura
    sobre pilar compartilham FACE, nunca volume.
    """
    return gm.interpenetracoes(membros)


def _aabb(m):
    """Caixa envolvente do membro em mm (primitiva compartilhada)."""
    return gm.aabb(m)


def quantitativo(membros):
    """Volume de concreto por tipo de peca (m3), direto do modelo neutro."""
    return gm.quantitativo(membros)


def pavimentos_ifc(estrutura, pe_direito):
    """Andares do IFC, incluindo o nivel de FUNDACAO quando ele tem peca.

    Um IfcBuildingStorey por pavimento, mais 'Fundacao' na cota da base. Sem o
    andar declarado, as sapatas cairiam no primeiro pavimento e o navegador do
    visualizador mostraria a fundacao dentro do Tipo 1.
    """
    andares = niveis(estrutura, pe_direito)
    fundacao = estrutura.get("fundacao")
    if isinstance(fundacao, dict) and fundacao.get("por_pilar"):
        cota = float(fundacao.get("cota_apoio_m")
                     if fundacao.get("cota_apoio_m") is not None else 1.0)
        andares = [{"nome": "Fundacao", "elevacao_mm": -cota * MM}] + andares
    return andares


def emitir_bim(estrutura, path, nome="Edificio"):
    """Escreve o IFC4 do edificio (um IfcBuildingStorey por pavimento).

    Requer ifcopenshell (ifc_emit.disponivel()). Retorna o path.
    """
    import ifc_emit

    membros = membros_bim(estrutura)
    pe = _pe_direito(estrutura["pilares"])
    return ifc_emit.emitir_ifc(membros, path, nome=nome,
                               pavimentos=pavimentos_ifc(estrutura, pe))


def montar_3d(estrutura, out_dir, doc_name="edificio", headless=None,
              host="http://localhost:9875", timeout=300):
    """Constroi o MODELO 3D SOLIDO (FreeCAD) do edificio e exporta FCStd/STEP/IFC.

    Reusa `build_concreto.py` - o build que ja monta caixas de concreto a partir
    de um PAYLOAD DE DADOS (sem importar modulo irmao, entao a armadilha do
    freecad.exe que cacheia a versao antiga do irmao nao se aplica). O 3D existe
    para uma pergunta que o emissor puro nao responde: a interferencia sobre os
    SOLIDOS REAIS (OCCT common()), nao sobre caixas envolventes.
    """
    import os

    import framework as FW
    import rodar_projeto as RP

    payload = {"membros": membros_bim(estrutura),
               "export_dir": str(out_dir).replace("\\", "/"),
               "doc_name": doc_name}
    src = RP._ship_build_src(
        FW.raiz_repo() / "framework" / "galpao_fw" / "build_concreto.py")
    if headless is None:
        headless = os.environ.get("FREECAD_HEADLESS", "").strip() in (
            "1", "true", "True")
    if headless:
        return RP._montar_headless(src, payload, out_dir, timeout)
    import xmlrpc.client
    try:
        return RP._montar_bridge(src, payload, host, timeout)
    except (OSError, xmlrpc.client.ProtocolError):
        return RP._montar_headless(src, payload, out_dir, timeout)
