# ============================================================================
# vibracao_piso.py - O QUE ESTE SCRIPT FAZ / VERIFICA
# ELS de VIBRACAO de piso pela ABNT NBR 8800:2008, item 11.4 e Anexo L. Era o
# item `vibracao_piso` que o `edificio_adapter` publicava como not_available
# desde a auditoria de gaps do G2.
#
# O QUE A NORMA DA, E O QUE ELA NAO DA (a distincao e o modulo inteiro):
#
#   L.1.2  - "Em nenhum caso a frequencia natural da estrutura do piso pode ser
#            inferior a 3 Hz." Piso conservador ABSOLUTO, vale para toda classe.
#   L.3.2  - caminhada regular (residencias, escritorios): f_n >= 4 Hz. Condicao
#            SATISFEITA se o deslocamento vertical TOTAL do piso, causado pelas
#            acoes permanentes EXCLUINDO A PARCELA DEPENDENTE DO TEMPO e pelas
#            acoes variaveis, calculado CONSIDERANDO-SE AS VIGAS COMO BIAPOIADAS
#            e com as combinacoes FREQUENTES de servico (4.7.7.3.3), <= 20 mm.
#   L.3.3  - saltos/danca ritmica (academias, saloes de danca, ginasios,
#            estadios): f_n >= 6 Hz (<= 9 mm); aumentada para 8 Hz (<= 5 mm) se a
#            atividade for muito repetitiva, como ginastica aerobica.
#   L.2    - avaliacao PRECISA: analise dinamica com amortecimento estrutural e
#            nao-estrutural, natureza da excitacao, razao de amortecimento modal
#            e pesos efetivos do piso. Procedimentos em S.4.
#
#   A NORMA NAO DA NENHUMA FORMULA PARA f_n. Nao existe no Anexo L a expressao
#   f = k/raiz(delta) nem tabela de amortecimento - checado na fonte. Por isso
#   este modulo NUNCA estima f_n: ou o projetista DECLARA o f_n que saiu da sua
#   analise dinamica (e ai a verificacao e por frequencia), ou a verificacao e a
#   via simplificada por deslocamento. Estimar f_n com formula de fora do acervo
#   seria inventar o dado que decide o gate (licao "AR300").
#
# DUAS ARMADILHAS QUE ESTE MODULO EXISTE PARA NAO CAIR:
#
#   1. VIGA BIAPOIADA. L.3.2/L.3.3 mandam calcular a viga como BIAPOIADA mesmo
#      quando ela e continua. Reaproveitar a flecha da viga continua (2,6/384)
#      no lugar da biapoiada (5/384) da ~52% do deslocamento e faz um piso
#      reprovado passar calado. A vinculacao da LAJE nao muda - a norma diz
#      "vigas", nao "lajes", e o modulo segue isso ao pe da letra.
#   2. PARCELA DEPENDENTE DO TEMPO. O deslocamento e o IMEDIATO. Usar a flecha
#      diferida (x (1+alpha_f), que o resto do framework calcula para a Tabela
#      13.3 da NBR 6118) reprovaria pisos que atendem, e trocar o criterio de
#      13.3 por este reprovaria o inverso. Sao ELS diferentes e convivem.
#
# CLASSIFICACAO NAO TEM DEFAULT. Um uso da Tabela 10 da NBR 6120 que nao esteja
# no mapa sai como `nao_classificado` e o gate REPROVA - classificar um ginasio
# como caminhada troca 9 mm por 20 mm em silencio, que e a forma exata da
# saturacao silenciosa que este framework persegue.
#
# L.3.1 (transcrito): "A opcao por esse tipo de avaliacao fica a criterio do
# projetista e pode nao constituir uma solucao adequada para o problema." Por
# isso o resultado da via simplificada carrega sempre essa ressalva - atender
# L.3.2 nao e' certificado de conforto, e o modulo nao o apresenta como tal.
#
# FONTE: ABNT NBR 8800:2008, 11.4 e Anexos L e S.4; psi_1 da Tabela 2.
# Unidades: m, kN ; fck em kN/m2 ; deslocamentos publicados em mm.
# ============================================================================
"""ELS de vibracao de piso (NBR 8800 11.4 / Anexo L): classificacao por uso,
deslocamento da combinacao frequente com as VIGAS BIAPOIADAS e verificacao por
frequencia natural quando ela e' declarada."""

from __future__ import annotations

import laje_concreto as lj
import viga_baldrame as vb

# ---------------------------------------------------------------------------
# L.1.2 - piso absoluto da frequencia natural, vale em qualquer caso.
# ---------------------------------------------------------------------------
F_MIN_ABSOLUTA_HZ = 3.0

# ---------------------------------------------------------------------------
# L.3.2 / L.3.3 - classes da avaliacao simplificada.
# ---------------------------------------------------------------------------
CLASSES_ANEXO_L = {
    "caminhada": {
        "f_min_Hz": 4.0, "d_lim_m": 0.020, "item": "L.3.2",
        "descricao": "pisos em que as pessoas caminham regularmente, como os de "
                     "residencias e escritorios"},
    "ritmica": {
        "f_min_Hz": 6.0, "d_lim_m": 0.009, "item": "L.3.3",
        "descricao": "pisos em que as pessoas saltam ou dancam de forma ritmica, "
                     "como os de academias de ginastica, saloes de danca, "
                     "ginasios e estadios de esportes"},
    "ritmica_repetitiva": {
        "f_min_Hz": 8.0, "d_lim_m": 0.005, "item": "L.3.3",
        "descricao": "atividade muito repetitiva, como ginastica aerobica"},
}

# Usos que nao sao piso de circulacao humana regular. Ficam NOMEADOS em vez de
# cair no mapa geral: a cobertura de manutencao e o forro nao tem caminhada
# regular nem atividade ritmica, e o Anexo L nao lhes atribui criterio.
CLASSE_NAO_APLICAVEL = "nao_aplicavel"

# ---------------------------------------------------------------------------
# Tabela 2 da NBR 8800 - psi_1 das acoes variaveis de uso e ocupacao. As linhas
# sao as da norma; as notas b e c da tabela e' que definem em qual linha cada
# edificacao cai (b: residenciais de acesso restrito; c: comerciais, de
# escritorios e de acesso publico).
# ATENCAO: ESCRITORIO cai na linha 2 (psi_1 = 0,6), nao na linha 1. A nota c da
# Tabela 2 diz "edificacoes comerciais, DE ESCRITORIOS e de acesso publico".
# ---------------------------------------------------------------------------
PSI_1_TAB2 = {
    "restrito": 0.4,    # linha 1: sem predominancia de equipamentos fixos nem de
                        # elevadas concentracoes de pessoas (nota b: residenciais
                        # de acesso restrito)
    "publico": 0.6,     # linha 2: com predominancia de equipamentos fixos ou de
                        # elevadas concentracoes de pessoas (nota c)
    "deposito": 0.7,    # linha 3: bibliotecas, arquivos, depositos, oficinas e
                        # garagens e sobrecargas em coberturas
}

# ---------------------------------------------------------------------------
# Mapa uso (chave da Tabela 10 da NBR 6120, `cargas_nbr6120.CARGAS_USO`) ->
# (classe do Anexo L, linha da Tabela 2 da NBR 8800).
# SEM DEFAULT: uso ausente daqui sai `nao_classificado` e reprova o gate.
# ---------------------------------------------------------------------------
CLASSE_POR_USO = {
    # residenciais - acesso restrito (nota b da Tabela 2)
    "residencial_dormitorio": ("caminhada", "restrito"),
    "residencial_sala_copa_cozinha": ("caminhada", "restrito"),
    "residencial_sanitario": ("caminhada", "restrito"),
    "residencial_servico": ("caminhada", "restrito"),
    "residencial_corredor_privativo": ("caminhada", "restrito"),
    "residencial_corredor_comum": ("caminhada", "restrito"),
    "sotao": ("caminhada", "restrito"),
    "sacada_residencial": ("caminhada", "restrito"),
    "escada_residencial_privativa": ("caminhada", "restrito"),
    "escada_sem_acesso_publico": ("caminhada", "restrito"),
    "escada_residencial_comum": ("caminhada", "restrito"),
    # escritorios, comercio, escolas - acesso publico (nota c da Tabela 2)
    "escritorio_sala_uso_geral": ("caminhada", "publico"),
    "escritorio_corredor_privativo": ("caminhada", "publico"),
    "escritorio_corredor_comum": ("caminhada", "publico"),
    "escada_comercial": ("caminhada", "publico"),
    "escada_com_acesso_publico": ("caminhada", "publico"),
    "escada_escola": ("caminhada", "publico"),
    "escada_shopping": ("caminhada", "publico"),
    "sacada_comercial": ("caminhada", "publico"),
    "sacada_acesso_publico": ("caminhada", "publico"),
    "loja": ("caminhada", "publico"),
    "loja_sanitario": ("caminhada", "publico"),
    "loja_administrativa": ("caminhada", "publico"),
    "praca_alimentacao_publico": ("caminhada", "publico"),
    "praca_alimentacao_cozinha": ("caminhada", "publico"),
    "restaurante_salao": ("caminhada", "publico"),
    "escola_sala_aula": ("caminhada", "publico"),
    "escola_corredor": ("caminhada", "publico"),
    "escola_sanitario": ("caminhada", "publico"),
    # bibliotecas, depositos, garagens - linha 3 da Tabela 2
    "biblioteca_leitura_sem_estantes": ("caminhada", "deposito"),
    "biblioteca_leitura_com_estantes": ("caminhada", "deposito"),
    "biblioteca_arquivo_deslizante": ("caminhada", "deposito"),
    "loja_deposito": ("caminhada", "deposito"),
    "restaurante_deposito": ("caminhada", "deposito"),
    "garagem_ate_30kN": ("caminhada", "deposito"),
    # ritmicos (L.3.3). `ginasio_esportes` fica em 6 Hz: os 8 Hz sao para
    # atividade MUITO repetitiva (ginastica aerobica), que a Tabela 10 da 6120
    # nao distingue - quem tiver academia declara `classe` explicitamente.
    "ginasio_esportes": ("ritmica", "publico"),
    "escada_arquibancada": ("ritmica", "publico"),
    # nao sao piso de circulacao humana regular
    "cobertura_manutencao": (CLASSE_NAO_APLICAVEL, "deposito"),
    "cobertura_placas_solares": (CLASSE_NAO_APLICAVEL, "deposito"),
    "forro_manutencao": (CLASSE_NAO_APLICAVEL, "deposito"),
}

RESSALVA_L31 = ("L.3.1: a opcao pela avaliacao simplificada fica a criterio do "
                "projetista e pode nao constituir uma solucao adequada para o "
                "problema - atender L.3.2/L.3.3 nao dispensa o julgamento tecnico")

AVALIACAO_PRECISA_FORA_DO_ACERVO = (
    "avaliacao precisa (L.2: analise dinamica com amortecimento modal e pesos "
    "efetivos do piso) NAO e' calculada aqui - as referencias de S.4 (Murray/"
    "Allen/Ungar AISC DG11, Wyatt SCI P076, CEB 209, NBCC, ATC DG1) nao estao no "
    "acervo. Declare 'f_n_Hz' se a analise dinamica foi feita por fora")


class UsoNaoClassificado(ValueError):
    """Uso sem classe do Anexo L: nao ha criterio a aplicar, e arbitrar um
    trocaria o limite em silencio."""


# ---------------------------------------------------------------------------
# 1. CLASSIFICACAO
# ---------------------------------------------------------------------------

def classifica(uso):
    """Devolve (classe, linha_psi_1) para uma chave de uso da Tabela 10 da NBR
    6120. Uso desconhecido devolve (None, None) - quem chama decide, mas
    `verifica` REPROVA, nunca adota uma classe por conta propria."""
    return CLASSE_POR_USO.get(uso, (None, None))


def psi_1(linha):
    """psi_1 da Tabela 2 da NBR 8800 pela linha de uso e ocupacao."""
    if linha not in PSI_1_TAB2:
        raise ValueError("linha de psi_1 desconhecida: %r (use %s)"
                         % (linha, sorted(PSI_1_TAB2)))
    return PSI_1_TAB2[linha]


def criterio(classe):
    """(f_min_Hz, d_lim_m, item) da classe do Anexo L."""
    if classe not in CLASSES_ANEXO_L:
        raise UsoNaoClassificado(
            "classe do Anexo L desconhecida: %r (use %s)"
            % (classe, sorted(CLASSES_ANEXO_L)))
    c = CLASSES_ANEXO_L[classe]
    return c["f_min_Hz"], c["d_lim_m"], c["item"]


# ---------------------------------------------------------------------------
# 2. DESLOCAMENTO DA COMBINACAO FREQUENTE
# ---------------------------------------------------------------------------

def flecha_viga_biapoiada(cfg_viga, w, fck):
    """Flecha IMEDIATA de uma viga de concreto BIAPOIADA sob carga w (kN/m).

    L.3.2/L.3.3 mandam calcular as vigas como biapoiadas AINDA QUE SEJAM
    CONTINUAS - e isso que este `continua=False` fixa. Passar continua=True
    devolveria 2,6/384 no lugar de 5/384 (52% do valor) e faria um piso
    reprovado passar, sem nenhum gate reclamar.

    A rigidez e' a IMEDIATA (Branson, 17.3.2), sem o (1+alpha_f) da fluencia:
    a norma pede o deslocamento "excluindo a parcela dependente do tempo".

    Sem As declarada a secao so pode ser tomada como BRUTA, o que subestima a
    flecha assim que a viga fissura. Nesse caso o resultado sai com
    `avaliavel=False` e quem chama nao pode dar o piso por atendido."""
    b = cfg_viga["b"]
    h = cfg_viga["h"]
    L = cfg_viga["L"]
    d = cfg_viga.get("d", h - 0.04)
    As = cfg_viga.get("As_m2", 0.0)
    fl = vb._flecha_alvenaria(b, h, d, L, w, fck, As, continua=False)
    avaliavel = bool(As > 0) or not fl["fissura"]
    return {"d_imediata_mm": fl["d_imediata_mm"], "fissura": fl["fissura"],
            "Mr": fl["Mr"], "Ma": fl["Ma"], "L": L, "w": round(w, 3),
            "secao": "Branson (I_eq)" if As > 0 else "bruta (I_c)",
            "avaliavel": avaliavel}


def flecha_laje_frequente(cfg_laje, p, fck):
    """Flecha IMEDIATA do painel de laje sob a carga p (kN/m2) da combinacao
    frequente, na vinculacao REAL do painel.

    A vinculacao da laje NAO vira biapoiada: L.3.2 fala em considerar as VIGAS
    como biapoiadas, e so elas. Trocar o caso de vinculacao do painel seria
    inventar exigencia que a norma nao faz."""
    fl = lj.flecha_laje(
        cfg_laje["caso"], cfg_laje["lx"], cfg_laje["ly"], p, cfg_laje["h"], fck,
        As_tracao=cfg_laje.get("As_m2", 0.0),
        M_servico=cfg_laje.get("M_servico"),
        considerar_fissuracao=cfg_laje.get("considerar_fissuracao", True),
        d=cfg_laje.get("d"))
    As = cfg_laje.get("As_m2", 0.0)
    return {"d_imediata_mm": round(fl["f_imediata"] * 1000, 2),
            "fissurou": fl["fissurou"], "fator_fissuracao": fl["fator_fissuracao"],
            "secao": "Branson (I_eq)" if As > 0 else "bruta (I_c)",
            "p": round(p, 3)}


# ---------------------------------------------------------------------------
# 3. VERIFICACAO
# ---------------------------------------------------------------------------

def verifica(cfg):
    """Verifica o ELS de vibracao de um piso pelo Anexo L da NBR 8800.

    cfg: {
      'uso'    : chave da Tabela 10 da NBR 6120 (ou declare 'classe');
      'classe' : opc - forca a classe do Anexo L ('caminhada', 'ritmica',
                 'ritmica_repetitiva'); tem precedencia sobre 'uso';
      'psi_1'  : opc - sobrepoe o psi_1 da Tabela 2 deduzido do uso;
      'g','q'  : cargas de area do pavimento (kN/m2), permanente e variavel;
      'laje'   : {'caso','lx','ly','h', 'As_m2' opc, 'M_servico' opc} - o painel
                 CRITICO (o de maior flecha);
      'viga'   : {'L','b','h', 'd' opc, 'As_m2' opc, 'g_kN_m','q_kN_m'} - a viga
                 CRITICA que apoia esse painel;
      'fck'    : kN/m2;
      'f_n_Hz' : opc - frequencia natural VINDA DE ANALISE DINAMICA do
                 projetista. Declarada, a verificacao passa a ser por
                 frequencia (L.1.2 + L.3.2/L.3.3) e o deslocamento vira
                 informativo. NUNCA e' estimada aqui.
    }

    Devolve dict com o deslocamento total, o limite, os vereditos e os avisos.
    """
    fck = cfg["fck"]
    uso = cfg.get("uso")
    classe = cfg.get("classe")
    linha = None
    if classe is None:
        classe, linha = classifica(uso)
    avisos = []

    base = {"uso": uso, "classe": classe, "fonte": "NBR 8800:2008 11.4 / Anexo L"}

    if classe is None:
        return dict(base, aplicavel=True, avaliavel=False, OK=False,
                    motivo="nao_classificado",
                    avisos=["uso %r nao tem classe do Anexo L neste mapa: sem "
                            "classe nao ha limite a aplicar, e adotar 'caminhada' "
                            "trocaria 9 mm por 20 mm em silencio. Declare 'classe'"
                            % uso])
    if classe == CLASSE_NAO_APLICAVEL:
        return dict(base, aplicavel=False, avaliavel=True, OK=True,
                    motivo="sem caminhada regular nem atividade ritmica",
                    avisos=["uso %r nao e' piso de circulacao humana regular: o "
                            "Anexo L nao lhe atribui criterio (L.3.2/L.3.3 nao se "
                            "aplicam)" % uso])

    f_min, d_lim, item = criterio(classe)
    if cfg.get("psi_1") is not None:
        p1 = cfg["psi_1"]
        linha_txt = "declarado no spec"
    else:
        if linha is None:
            raise UsoNaoClassificado(
                "classe %r foi declarada sem 'uso' nem 'psi_1': o psi_1 da Tabela 2 "
                "da NBR 8800 depende da ocupacao e nao tem default" % classe)
        p1 = psi_1(linha)
        linha_txt = "Tabela 2 NBR 8800, linha %r" % linha

    # --- combinacao FREQUENTE (4.7.7.3.3): F_ser = Fgk + psi_1*Fq1k ---------
    g, q = cfg["g"], cfg["q"]
    p_freq = g + p1 * q
    fl_laje = flecha_laje_frequente(cfg["laje"], p_freq, fck)

    v = cfg["viga"]
    w_freq = v["g_kN_m"] + p1 * v["q_kN_m"]
    fl_viga = flecha_viga_biapoiada(v, w_freq, fck)

    # O deslocamento do PISO e o da laje SOMADO ao do apoio que se move: o
    # painel flecha em relacao as vigas, e as vigas flecham em relacao aos
    # pilares. Somar as duas parcelas e o que "deslocamento vertical total do
    # piso" quer dizer; ficar so com a laje ignora a viga, que num vao grande
    # e' justamente a parcela dominante que o Anexo L quer limitar.
    d_total_mm = fl_laje["d_imediata_mm"] + fl_viga["d_imediata_mm"]
    d_lim_mm = d_lim * 1000.0
    ok_desl = d_total_mm <= d_lim_mm + 1e-9

    f_n = cfg.get("f_n_Hz")
    ok_freq = None
    ok_f_abs = None
    if f_n is not None:
        ok_f_abs = f_n >= F_MIN_ABSOLUTA_HZ
        ok_freq = f_n >= f_min
        avaliacao = "frequencia declarada"
        OK = bool(ok_f_abs and ok_freq)
        if not ok_f_abs:
            avisos.append("f_n = %.2f Hz < 3 Hz: L.1.2 proibe em qualquer caso"
                          % f_n)
        elif not ok_freq:
            avisos.append("f_n = %.2f Hz < %.1f Hz exigidos por %s (%s)"
                          % (f_n, f_min, item, classe))
    else:
        avaliacao = "simplificada (deslocamento)"
        OK = bool(ok_desl)
        if not ok_desl:
            avisos.append(
                "deslocamento total %.1f mm > %.0f mm de %s: a condicao "
                "f_n >= %.1f Hz NAO fica satisfeita pela via simplificada. %s"
                % (d_total_mm, d_lim_mm, item, f_min,
                   AVALIACAO_PRECISA_FORA_DO_ACERVO))
        avisos.append(RESSALVA_L31)

    if not fl_viga["avaliavel"]:
        # viga que fissura sob a combinacao frequente e sem As declarada: a
        # secao bruta subestima a flecha, entao um OK aqui seria OK por dado
        # ausente. Piso conservador: nao avaliavel.
        OK = False
        avisos.append("viga fissura sob a combinacao frequente (Ma = %.1f kN.m > "
                      "Mr = %.1f kN.m) e 'As_m2' nao foi declarada: com secao "
                      "BRUTA a flecha sai subestimada, entao este piso nao pode "
                      "ser dado por atendido" % (fl_viga["Ma"], fl_viga["Mr"]))

    return dict(
        base, aplicavel=True, avaliavel=fl_viga["avaliavel"],
        item=item, f_min_Hz=f_min, f_min_absoluta_Hz=F_MIN_ABSOLUTA_HZ,
        psi_1=p1, psi_1_origem=linha_txt, p_freq_kN_m2=round(p_freq, 3),
        w_freq_kN_m=round(w_freq, 3),
        laje=fl_laje, viga=fl_viga,
        d_laje_mm=fl_laje["d_imediata_mm"], d_viga_mm=fl_viga["d_imediata_mm"],
        d_total_mm=round(d_total_mm, 2), d_lim_mm=round(d_lim_mm, 2),
        ok_deslocamento=ok_desl, f_n_Hz=f_n, ok_frequencia=ok_freq,
        ok_f_min_absoluta=ok_f_abs, avaliacao=avaliacao,
        avisos=avisos, OK=OK)


def relatorio_pt(r):
    """Quadro-resumo da verificacao de vibracao de piso."""
    L = ["VIBRACAO DE PISO - NBR 8800:2008, 11.4 e Anexo L"]
    if not r.get("aplicavel", True):
        L.append("  uso %r: criterio NAO APLICAVEL (%s)"
                 % (r.get("uso"), r.get("motivo")))
        return "\n".join(L)
    if r.get("motivo") == "nao_classificado":
        L.append("  uso %r: NAO CLASSIFICADO - sem criterio a aplicar" % r.get("uso"))
        L += ["  ! " + a for a in r.get("avisos", [])]
        return "\n".join(L)
    L += [
        "  classe: %s (%s) ; f_n minima = %.1f Hz ; piso absoluto = %.1f Hz (L.1.2)"
        % (r["classe"], r["item"], r["f_min_Hz"], r["f_min_absoluta_Hz"]),
        "  combinacao frequente (4.7.7.3.3): psi_1 = %.1f (%s)"
        % (r["psi_1"], r["psi_1_origem"]),
        "  deslocamento imediato: laje %.1f mm + viga BIAPOIADA %.1f mm = %.1f mm"
        % (r["d_laje_mm"], r["d_viga_mm"], r["d_total_mm"]),
        "  limite de %s: %.0f mm -> %s"
        % (r["item"], r["d_lim_mm"], "OK" if r["ok_deslocamento"] else "EXCEDIDO"),
    ]
    if r.get("f_n_Hz") is not None:
        L.append("  f_n DECLARADA = %.2f Hz (analise dinamica do projetista)"
                 % r["f_n_Hz"])
    L += ["  ! " + a for a in r.get("avisos", [])]
    L.append("  RESULTADO: %s" % ("ATENDE" if r["OK"] else "REPROVADO"))
    return "\n".join(L)
