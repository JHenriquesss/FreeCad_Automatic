# ============================================================================
# alvenaria_estrutural.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Vertical de alvenaria estrutural (G60): a parede deixa de existir so como
# carga (NBR 6120 Tab.2 via cargas_nbr6120) e passa a existir tambem como
# ELEMENTO resistente, ABNT NBR 16868-1:2020 com a Errata 1 (Er1:2021).
#
# FONTE (lida na pagina, nao de memoria):
#   - Parte 1 (projeto): fontes/14_ALVENARIA_ESTRUTURAL/
#     ALVENARIA__NBR__NBR-16868-1-2020-ER1-2021__projeto.pdf (F133).
#     O arquivo e scan sem camada de texto (pymupdf devolve zero caracteres
#     nas 77 paginas); a leitura abaixo foi feita pagina a pagina no proprio
#     PDF. O PDF ABRE pela Errata 1 (Er1:2021, publicada em 13.04.2021),
#     que corrige designacoes de equacao ANTES do corpo:
#       p.1 (errata) -> 11.2.2: "Em" por "Ea";
#       p.1 (errata) -> 11.3.2 Fig.8 legenda: A s linha e F s linha passam
#         de "armadura tracionada" para "armadura comprimida";
#       p.1 (errata) -> 11.3.3: "fyk" por "fyd";
#       p.1 (errata) -> 11.5.3.2: "fs <= fpk . Es/Ea," passa a valer
#         "para armadura comprimida", e "fyk" por "fyd".
#     Quem implementar a formula pre-errata poe valor caracteristico onde
#     vai valor de calculo: erro de um gamma inteiro, para o lado errado.
#   - Parte 2 (execucao e controle): ...-NBR-16868-2-2020-...pdf (F134).
#     Alimenta o caderno_encargos (prumo 9.3.4, controle de argamassa e
#     graute, ensaios de recebimento), nao este calculo.
#   - Parte 3 (metodos de ensaio): ...-NBR-16868-3-2020-...pdf (F135).
#     E de la que sai o fpk: resistencia do PRISMA. Por isso o fpk aqui e
#     entrada DECLARADA, sem default em assinatura nenhuma (a regra do SPT
#     no G9). Sem fpk declarado o modulo recusa com motivo nomeado; nao
#     escolhe bloco "tipico" nenhum.
#
# NUCLEO IMPLEMENTADO (secao citada em cada conta):
#   - gamma_m, Tab.2 (6.2.2.2): 2,0 combinacoes normais; 1,5 especiais ou
#     de construcao e excepcionais; 1,0 no ELS. Colunas graute e aco vao
#     juntas no dicionario (1,15 / 1,15 / 1,0 para o aco).
#   - fk a partir do prisma, 6.2.2.3: blocos (190 mm, junta 10 mm) usam
#     70 % do fpk de prisma ou 85 % do fppk de pequena parede; tijolos
#     usam 60 % do fpk. Correlacao fora dessas duas cai em recusa.
#   - Ea (modulo de deformacao longitudinal), Tab.1 (6.2.1): bloco de
#     concreto 800/750/700 x fpk por patamar de fpk; bloco e tijolo
#     ceramicos 600 x fpk. Patamar de fpk fora dos tabelados recusa
#     (mesmo tratamento da Tab.2 da NBR 6120 em cargas_nbr6120: tabela
#     discreta nao se interpola em silencio).
#   - Esbeltez, 10.1.2: lambda = he / te. Tetos da Tab.9: 24 sem armadura,
#     30 com armadura (armaduras minimas da 12.2). A nota "a" da Tab.9
#     (habitacao terrea, parede sem armadura ate 30 com gamma_m = 3,0)
#     e opcao declarada, nunca silenciosa. Acima do teto o modulo REPROVA
#     (veredito reprovado); parede armada acima de 30 cai no Anexo C
#     (P-Delta), que este lote nao implementa: reprova com o motivo
#     apontando o Anexo C. Pilar armado acima de 30 reprova (o titulo da
#     11.2.2 so cobre ate 30). Lambda nao satura no teto nem vira razao
#     que devolve OK: regra do G51 e do D82.
#   - Compressao simples em parede e pilar sem armadura, 11.2.1:
#     NRd = fd x A x R (parede); NRd = 0,9 x fd x A x R (pilar);
#     fd = fk / gamma_m; R = [1 - (lambda/40)^3].
#   - Pilar armado com lambda ate 30, 11.2.2 (COM a errata: Ea, nao Em):
#     NRd = (fd x A + fs x As / gamma_s) x R;
#     fs = min(fpk x Es/Ea, fyk, teto do estribo: 250 MPa com espacamento
#     ate 24 x phi, 500 MPa ate 12 x phi). A lista da 11.2.2 nao foi
#     tocada pela errata no item do fyk: segue fyk ali, literal.
#   - Flexao simples com armadura simples, 11.3.3 (COM a errata: fyd):
#     MRd = As x fs x z; z = d x (1 - 0,5 x As x fs / (b x d x fd)),
#     teto 0,95 x d; MRd teto 0,3 x fd x b x d^2; fs corta em fyd
#     (fyk / gamma_s) com os redutores de aderencia do item (10 mm ->
#     fyd; 12,5 mm -> 0,75; 16 mm ou mais -> 0,50; ranhurado -> fyd).
#
# NAO IMPLEMENTADO NESTE LOTE (escopo() publica cada um com motivo):
#   - flexo-compressao 11.5 (diagrama de interacao): nao ha conta aqui.
#   - acao horizontal em contraventamento (9.6.2, flanges bf ate 6t,
#     distribuicao por rigidez): se Qh declarado diferente de zero, a
#     verificacao RECUSA com motivo escrito. estabilidade_b1b2.py e
#     reticulado e nao serve aqui. O vento nunca some em silencio.
#   - BIM e pranchas de alvenaria: proximo lote. O escopo publica
#     not_available com esse motivo.
#
# FRONTEIRA DO PESO (a laje do G52 outra vez, se descuidar): o peso
# proprio da parede entra pela via da CARGA (cargas_nbr6120,
# carga_linear_parede). Este modulo SOMA ZERO de peso proprio por dentro:
# recebe Nd pronto e devolve peso_proprio_interno_kN = 0,0 em todo
# resultado, para a igualdade atravessar a fronteira como dado. A
# igualdade mora em confere_fronteira_peso e no teste do G60, no molde
# do test_fronteira_carga_laje_g52.py (relacao, nunca numero congelado).
#
# Unidades: m, kN; fpk/fppk/fk/fyk/fyd em kN/m2. STATELESS, puro (sem numpy).
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Vertical de alvenaria estrutural (NBR 16868-1:2020 + Er1:2021).

Compressao simples (11.2.1), pilar armado (11.2.2, Ea da errata), flexao
simples (11.3.3, fyd da errata), esbeltez com tetos da Tab.9 (10.1.2),
gamma_m da Tab.2 e fk a partir do fpk de prisma (6.2.2.3, Parte 3).
fpk e entrada declarada sem default; lambda acima do teto reprova;
acao horizontal declarada recusa com motivo; peso proprio interno zero.
"""

from __future__ import annotations

import math

# --- ponderacao das resistencias, Tab.2 (6.2.2.2) ---------------------------
# Chaves: "normal", "especial" (= especiais ou de construcao), "excepcional",
# "els" (= ELS, gamma_m = 1,0). Coluna "aco" usada no fyd e no As/gamma_s.
GAMMA_M = {
    "normal": {"alvenaria": 2.0, "graute": 2.0, "aco": 1.15},
    "especial": {"alvenaria": 1.5, "graute": 1.5, "aco": 1.15},
    "excepcional": {"alvenaria": 1.5, "graute": 1.5, "aco": 1.0},
    "els": {"alvenaria": 1.0, "graute": 1.0, "aco": 1.0},
}

# Tab.9 nota "a": habitacao terrea, parede sem armadura ate lambda 30,
#     com o ponderador da alvenaria em 3,0. Nao e default: exige
#     habitacao_terrea=True declarado.
GAMMA_M_TERREA_SEM_ARMADURA = 3.0
LAMBDA_TETO_TERREA_SEM_ARMADURA = 30.0

# Tab.9 (10.1.2): tetos de lambda por presenca de armadura.
LAMBDA_TETO_SEM_ARMADURA = 24.0
LAMBDA_TETO_ARMADA = 30.0

# 10.1.1: acima de dois pavimentos, te minima 14 cm.
TE_MIN_MAIS_2_PAV_M = 0.14

# 11.2.1: pilar sem armadura leva 0,9.
FATOR_PILAR_SEM_ARMADURA = 0.9

# 6.2.2.3: fk a partir do ensaio (prisma fpk, pequena parede fppk).
FATOR_FK_BLOCO_DE_FPK = 0.70
FATOR_FK_BLOCO_DE_FPPK = 0.85
FATOR_FK_TIJOLO_DE_FPK = 0.60

# 6.1.4: sem ensaio do fabricante, Es do aco em 210 GPa.
ES_ACO_KNM2 = 210e6

# 11.2.2: tetos de fs pelo espacamento dos estribos (multiplos de phi).
FS_TETO_ESTRIBO_24PHI_MP = 250.0
FS_TETO_ESTRIBO_12PHI_MP = 500.0

# 11.3.3: teto de ductilidade do MRd.
FATOR_MRD_TETO_DUTIL = 0.30


class EntradaAlvenaria(ValueError):
    """A entrada declarada nao descreve parede que este lote possa calcular."""


def gamma_m(combinacao):
    """Ponderadores da Tab.2 (6.2.2.2) por combinacao.

    combinacao: "normal" | "especial" | "excepcional" | "els".
    Devolve copia {"alvenaria", "graute", "aco"}. Combinacao fora dessas
    recusa: arbitrar ponderador e o erro de um gamma inteiro.
    """
    try:
        g = GAMMA_M[combinacao]
    except KeyError:
        raise EntradaAlvenaria(
            "combinacao_desconhecida: %r nao consta na Tab.2 "
            "(NBR 16868-1 6.2.2.2). Opcoes: %s"
            % (combinacao, ", ".join(sorted(GAMMA_M))))
    return dict(g)


def fk_de_fpk(fpk, material, fppk=None):
    """fk da alvenaria a partir do ensaio, 6.2.2.3.

    fpk: resistencia caracteristica do PRISMA (kN/m2, Parte 3), DECLARADA.
      None recusa com motivo nomeado (regra do SPT no G9): sem ensaio
      declarado nao ha fk, e nenhum bloco "tipico" entra no lugar.
    material: "bloco" (concreto ou ceramico, 190 mm com junta de 10 mm)
      ou "tijolo".
    fppk: opcional, pequena parede (kN/m2); so combina com bloco
      (85 %); com tijolo recusa, a norma nao da essa correlacao.
    """
    if fpk is None:
        raise EntradaAlvenaria(
            "fpk_nao_declarado: a resistencia da alvenaria vem do prisma "
            "(NBR 16868-3) e o prisma e ensaio declarado. Sem fpk nao ha "
            "fk e o modulo recusa em vez de arbitrar bloco tipico.")
    fpk = float(fpk)
    if not fpk > 0:
        raise EntradaAlvenaria("fpk_nao_positivo: fpk = %r kN/m2" % (fpk,))
    if material == "bloco":
        if fppk is not None:
            fppk = float(fppk)
            if not fppk > 0:
                raise EntradaAlvenaria("fppk_nao_positivo: %r" % (fppk,))
            return FATOR_FK_BLOCO_DE_FPPK * fppk
        return FATOR_FK_BLOCO_DE_FPK * fpk
    if material == "tijolo":
        if fppk is not None:
            raise EntradaAlvenaria(
                "fppk_so_bloco: a 6.2.2.3 so da 85 %% de fppk para blocos; "
                "tijolo usa 60 %% do fpk.")
        return FATOR_FK_TIJOLO_DE_FPK * fpk
    raise EntradaAlvenaria(
        "material_desconhecido: %r. Opcoes: 'bloco', 'tijolo' "
        "(NBR 16868-1 6.2.2.3)." % (material,))


def modulo_deformacao(fpk, tipo_bloco):
    """Ea da Tab.1 (6.2.1), em kN/m2.

    tipo_bloco: "bloco_concreto" | "bloco_ceramico" | "tijolo_ceramico".
    Bloco de concreto por patamar de fpk (MPa): ate 20 -> 800 x fpk;
    22 e 24 -> 750 x fpk; a partir de 26 -> 700 x fpk. Patamar fora
    desses (21, 23, 25 e intermediarios nao tabelados) RECUSA: tabela
    discreta nao se interpola em silencio (mesmo trato da Tab.2 da
    NBR 6120 em cargas_nbr6120). Ceramicos: 600 x fpk.
    """
    if fpk is None:
        raise EntradaAlvenaria(
            "fpk_nao_declarado: o Ea da Tab.1 e multiplo do fpk de ensaio.")
    fpk = float(fpk)
    if not fpk > 0:
        raise EntradaAlvenaria("fpk_nao_positivo: fpk = %r kN/m2" % (fpk,))
    if tipo_bloco in ("bloco_ceramico", "tijolo_ceramico"):
        return 600.0 * fpk
    if tipo_bloco == "bloco_concreto":
        fpk_MPa = fpk / 1000.0
        if fpk_MPa <= 20.0:
            return 800.0 * fpk
        if abs(fpk_MPa - 22.0) < 1e-6 or abs(fpk_MPa - 24.0) < 1e-6:
            return 750.0 * fpk
        if fpk_MPa >= 26.0:
            return 700.0 * fpk
        raise EntradaAlvenaria(
            "Ea_sem_patamar_tabelado: fpk = %.3f MPa nao consta na Tab.1 "
            "(NBR 16868-1 6.2.1): patamares 800 ate 20 MPa, 750 em 22 e 24 "
            "MPa, 700 a partir de 26 MPa." % (fpk_MPa,))
    raise EntradaAlvenaria(
        "tipo_bloco_desconhecido: %r. Opcoes: 'bloco_concreto', "
        "'bloco_ceramico', 'tijolo_ceramico'." % (tipo_bloco,))


def esbeltez(he, te):
    """lambda = he / te (10.1.2). he pela 9.4.1, te pela 9.4.2 (sem
    revestimento, 9.5 desconta revestimento da secao resistente)."""
    he, te = float(he), float(te)
    if not he > 0:
        raise EntradaAlvenaria("he_nao_positiva: %r" % (he,))
    if not te > 0:
        raise EntradaAlvenaria("te_nao_positiva: %r" % (te,))
    return he / te


def R_esbeltez(lam):
    """R = [1 - (lambda/40)^3] (11.2.1, parede; 11.2.2 usa o mesmo R)."""
    return 1.0 - (float(lam) / 40.0) ** 3


def teto_esbeltez(armada, habitacao_terrea=False):
    """Teto de lambda da Tab.9 (10.1.2): 24 sem armadura, 30 com armadura
    (minimos da 12.2). Com habitacao_terrea=True e sem armadura, 30 pela
    nota "a" da Tab.9 (ai o gamma da alvenaria e 3,0: ver
    gamma_alvenaria)."""
    if armada:
        return LAMBDA_TETO_ARMADA
    if habitacao_terrea:
        return LAMBDA_TETO_TERREA_SEM_ARMADURA
    return LAMBDA_TETO_SEM_ARMADURA


def gamma_alvenaria(combinacao, armada, habitacao_terrea=False):
    """Ponderador da alvenaria: Tab.2, com a nota "a" da Tab.9 passando
    a 3,0 na habitacao terrea sem armadura (opcao declarada)."""
    if (not armada) and habitacao_terrea:
        if combinacao != "els":
            return GAMMA_M_TERREA_SEM_ARMADURA
        return 1.0
    return gamma_m(combinacao)["alvenaria"]


def _guarda_horizontal(acao_horizontal_kN):
    """Recusa nomeada da acao horizontal: o vento vai para as paredes de
    contraventamento distribuido por rigidez (9.6.2), conta que este lote
    nao implementa. estabilidade_b1b2.py e reticulado e nao serve aqui.
    None ou zero segue; resto recusa (o vento nunca some em silencio)."""
    if acao_horizontal_kN is None:
        return None
    try:
        qh = float(acao_horizontal_kN)
    except (TypeError, ValueError):
        raise EntradaAlvenaria(
            "acao_horizontal_invalida: %r" % (acao_horizontal_kN,))
    if qh == 0.0:
        return None
    return ("acao_horizontal_exige_contraventamento: Qh = %.3f kN declarada "
            "e este lote so verifica compressao gravitacional (11.2). A "
            "acao horizontal pede parede de contraventamento com "
            "distribuicao por rigidez (NBR 16868-1 9.6.2, flanges ate 6t "
            "na 10.1.3), fora do escopo deste lote. Sem distribuicao "
            "calculada o caso recusa em vez de zerar o vento." % (qh,))


def _guarda_espessura(te, n_pavimentos):
    """10.1.1: acima de dois pavimentos, te minima 14 cm. Sem
    n_pavimentos declarado a guarda nao tem o que conferir e passa
    adiante registrado (dado pedido, nao inventado)."""
    if n_pavimentos is None:
        return None
    if int(n_pavimentos) > 2 and float(te) < TE_MIN_MAIS_2_PAV_M:
        return ("espessura_minima_14cm: te = %.1f cm com %d pavimentos "
                "(NBR 16868-1 10.1.1 pede te >= 14 cm acima de dois "
                "pavimentos)." % (float(te) * 100.0, int(n_pavimentos)))
    return None


def _base_resultado(veredito, ok, motivo, **campos):
    res = {"OK": bool(ok), "veredito": veredito, "motivo": motivo,
           "peso_proprio_interno_kN": 0.0}
    res.update(campos)
    return res


def _comum_peso_zero():
    """Lembrete de fronteira em cada resultado: este modulo soma zero de
    peso proprio; o Nd entra pronto pela via da carga (cargas_nbr6120,
    carga_linear_parede). Ver F21 em fronteiras.py."""
    return 0.0


def verifica_parede_compressao(Nd, fpk, he, te, A, material="bloco",
                               combinacao="normal", acao_horizontal_kN=None,
                               n_pavimentos=None, habitacao_terrea=False,
                               fppk=None, comprimento_m=None):
    """Parede sem armadura em compressao simples, 11.2.1.

    NRd = fd x A x R; fd = fk / gamma_m; R = [1 - (lambda/40)^3].
    Nd (kN, de calculo) entra PRONTO, com o peso proprio ja dentro pela
    via da carga. A (m2) e a area bruta da secao resistente (11.1, sem
    revestimentos pela 9.5). comprimento_m e opcional e so vai ao
    relatorio (kN/m). Lambda acima do teto da Tab.9 REPROVA com motivo;
    acao horizontal declarada RECUSA com motivo.
    """
    Nd = float(Nd)
    A = float(A)
    if not A > 0:
        raise EntradaAlvenaria("area_nao_positiva: A = %r m2" % (A,))
    if Nd < 0:
        raise EntradaAlvenaria("Nd_negativa: %r kN" % (Nd,))
    motivo_qh = _guarda_horizontal(acao_horizontal_kN)
    if motivo_qh is not None:
        return _base_resultado("recusado", False, motivo_qh, Nd_kN=Nd)
    motivo_te = _guarda_espessura(te, n_pavimentos)
    if motivo_te is not None:
        return _base_resultado("reprovado", False, motivo_te, Nd_kN=Nd)
    fk = fk_de_fpk(fpk, material, fppk)
    gm = gamma_alvenaria(combinacao, False, habitacao_terrea)
    fd = fk / gm
    lam = esbeltez(he, te)
    teto = teto_esbeltez(False, habitacao_terrea)
    if lam > teto:
        return _base_resultado(
            "reprovado", False,
            "esbeltez_acima_do_teto: lambda = %.2f acima de %.0f "
            "(NBR 16868-1 Tab.9, 10.1.2, parede sem armadura%s). O teto "
            "reprova, nao satura: sem Anexo C neste lote."
            % (lam, teto,
               " em habitacao terrea" if habitacao_terrea else ""),
            Nd_kN=Nd, fk_kN_m2=round(fk, 3), fd_kN_m2=round(fd, 3),
            lambda_=round(lam, 4), lambda_teto=teto, gamma_m=gm)
    R = R_esbeltez(lam)
    NRd = fd * A * R
    ok = Nd <= NRd
    res = _base_resultado(
        "aprovado" if ok else "reprovado", ok,
        "" if ok else ("compressao_insuficiente: Nd = %.3f kN acima de "
                       "NRd = %.3f kN (NBR 16868-1 11.2.1, parede)."
                       % (Nd, NRd)),
        Nd_kN=Nd, NRd_kN=round(NRd, 3), fk_kN_m2=round(fk, 3),
        fd_kN_m2=round(fd, 3), lambda_=round(lam, 4), lambda_teto=teto,
        R_redutor=round(R, 4), gamma_m=gm, A_m2=A)
    res["peso_proprio_interno_kN"] = _comum_peso_zero()
    if comprimento_m is not None and float(comprimento_m) > 0:
        L = float(comprimento_m)
        res["Nd_kN_m"] = round(Nd / L, 3)
        res["NRd_kN_m"] = round(NRd / L, 3)
    return res


def verifica_pilar_compressao(Nd, fpk, he, te, A, material="bloco",
                              combinacao="normal", acao_horizontal_kN=None,
                              n_pavimentos=None, fppk=None):
    """Pilar sem armadura em compressao simples, 11.2.1.

    NRd = 0,9 x fd x A x R. Teto de lambda 24 (Tab.9, sem armadura).
    Mesma fronteira de peso da parede (soma zero por dentro).
    """
    Nd = float(Nd)
    A = float(A)
    if not A > 0:
        raise EntradaAlvenaria("area_nao_positiva: A = %r m2" % (A,))
    if Nd < 0:
        raise EntradaAlvenaria("Nd_negativa: %r kN" % (Nd,))
    motivo_qh = _guarda_horizontal(acao_horizontal_kN)
    if motivo_qh is not None:
        return _base_resultado("recusado", False, motivo_qh, Nd_kN=Nd)
    motivo_te = _guarda_espessura(te, n_pavimentos)
    if motivo_te is not None:
        return _base_resultado("reprovado", False, motivo_te, Nd_kN=Nd)
    fk = fk_de_fpk(fpk, material, fppk)
    gm = gamma_m(combinacao)["alvenaria"]
    fd = fk / gm
    lam = esbeltez(he, te)
    teto = teto_esbeltez(False)
    if lam > teto:
        return _base_resultado(
            "reprovado", False,
            "esbeltez_acima_do_teto: lambda = %.2f acima de %.0f "
            "(NBR 16868-1 Tab.9, 10.1.2, pilar sem armadura)."
            % (lam, teto),
            Nd_kN=Nd, fk_kN_m2=round(fk, 3), fd_kN_m2=round(fd, 3),
            lambda_=round(lam, 4), lambda_teto=teto, gamma_m=gm)
    R = R_esbeltez(lam)
    NRd = FATOR_PILAR_SEM_ARMADURA * fd * A * R
    ok = Nd <= NRd
    res = _base_resultado(
        "aprovado" if ok else "reprovado", ok,
        "" if ok else ("compressao_insuficiente: Nd = %.3f kN acima de "
                       "NRd = %.3f kN (NBR 16868-1 11.2.1, pilar com 0,9)."
                       % (Nd, NRd)),
        Nd_kN=Nd, NRd_kN=round(NRd, 3), fk_kN_m2=round(fk, 3),
        fd_kN_m2=round(fd, 3), lambda_=round(lam, 4), lambda_teto=teto,
        R_redutor=round(R, 4), gamma_m=gm, A_m2=A)
    res["peso_proprio_interno_kN"] = _comum_peso_zero()
    return res


def tensao_aco_pilar_armado(fpk, tipo_bloco, fyk, s_estribo_phi,
                            es_kNm2=None):
    """fs do pilar armado, 11.2.2, COM a Errata 1 (Ea, nao Em).

    fs = min(fpk x Es/Ea [errata], fyk [item mantido pela errata],
    teto do estribo: 500 MPa ate 12 x phi, 250 MPa ate 24 x phi).
    s_estribo_phi: espacamento dos estribos em multiplos de phi,
    DECLARADO (As so conta contraventada por estribos). Acima de 24 x
    phi recusa: a norma nao da teto alem dali. Es default 210 GPa
    (NBR 16868-1 6.1.4, conta da norma, nao arbitrada aqui).
    """
    if fyk is None:
        raise EntradaAlvenaria(
            "fyk_nao_declarado: o fs da 11.2.2 corta em fyk; sem fyk "
            "declarado nao ha fs.")
    if s_estribo_phi is None:
        raise EntradaAlvenaria(
            "estribo_nao_declarado: As da 11.2.2 e a area contraventada "
            "por estribos; sem espacamento declarado o As nao conta.")
    fyk = float(fyk)
    s_phi = float(s_estribo_phi)
    if not fyk > 0:
        raise EntradaAlvenaria("fyk_nao_positivo: %r" % (fyk,))
    if not s_phi > 0:
        raise EntradaAlvenaria("estribo_nao_positivo: %r" % (s_phi,))
    Ea = modulo_deformacao(fpk, tipo_bloco)
    Es = float(es_kNm2) if es_kNm2 is not None else ES_ACO_KNM2
    if not Es > 0:
        raise EntradaAlvenaria("Es_nao_positivo: %r" % (Es,))
    fs_prisma = float(fpk) * Es / Ea
    if s_phi <= 12.0:
        teto_estribo = FS_TETO_ESTRIBO_12PHI_MP * 1000.0
    elif s_phi <= 24.0:
        teto_estribo = FS_TETO_ESTRIBO_24PHI_MP * 1000.0
    else:
        raise EntradaAlvenaria(
            "estribo_acima_24phi: s = %.1f x phi; a 11.2.2 so da teto de "
            "fs ate 24 x phi (250 MPa) e 12 x phi (500 MPa)." % (s_phi,))
    fs = min(fs_prisma, fyk, teto_estribo)
    return {"fs_kN_m2": fs, "fs_prisma_kN_m2": fs_prisma,
            "fyk_kN_m2": fyk, "teto_estribo_kN_m2": teto_estribo,
            "Ea_kN_m2": Ea, "Es_kN_m2": Es,
            "errata_Ea_aplicada": True}


def verifica_pilar_armado(Nd, fpk, he, te, A, As, fyk, s_estribo_phi,
                          tipo_bloco="bloco_concreto", material="bloco",
                          combinacao="normal", acao_horizontal_kN=None,
                          n_pavimentos=None, es_kNm2=None):
    """Pilar armado em compressao simples, 11.2.2 (lambda ate 30).

    NRd = (fd x A + fs x As / gamma_s) x R, com fs pela
    tensao_aco_pilar_armado (errata: Es/Ea). Lambda acima de 30
    REPROVA (o titulo da 11.2.2 so cobre ate 30; pilar nao tem Anexo C).
    """
    Nd = float(Nd)
    A = float(A)
    As = float(As)
    if not A > 0:
        raise EntradaAlvenaria("area_nao_positiva: A = %r m2" % (A,))
    if not As >= 0:
        raise EntradaAlvenaria("As_negativa: %r m2" % (As,))
    if Nd < 0:
        raise EntradaAlvenaria("Nd_negativa: %r kN" % (Nd,))
    motivo_qh = _guarda_horizontal(acao_horizontal_kN)
    if motivo_qh is not None:
        return _base_resultado("recusado", False, motivo_qh, Nd_kN=Nd)
    motivo_te = _guarda_espessura(te, n_pavimentos)
    if motivo_te is not None:
        return _base_resultado("reprovado", False, motivo_te, Nd_kN=Nd)
    fk = fk_de_fpk(fpk, material)
    g = gamma_m(combinacao)
    fd = fk / g["alvenaria"]
    gs = g["aco"]
    lam = esbeltez(he, te)
    teto = teto_esbeltez(True)
    if lam > teto:
        return _base_resultado(
            "reprovado", False,
            "esbeltez_acima_do_teto: lambda = %.2f acima de %.0f "
            "(NBR 16868-1 Tab.9, 10.1.2; 11.2.2 so cobre ate 30 e pilar "
            "nao tem Anexo C)." % (lam, teto),
            Nd_kN=Nd, fk_kN_m2=round(fk, 3), fd_kN_m2=round(fd, 3),
            lambda_=round(lam, 4), lambda_teto=teto,
            gamma_m=g["alvenaria"])
    fs = tensao_aco_pilar_armado(fpk, tipo_bloco, fyk, s_estribo_phi,
                                 es_kNm2)["fs_kN_m2"]
    R = R_esbeltez(lam)
    NRd = (fd * A + fs * As / gs) * R
    ok = Nd <= NRd
    res = _base_resultado(
        "aprovado" if ok else "reprovado", ok,
        "" if ok else ("compressao_insuficiente: Nd = %.3f kN acima de "
                       "NRd = %.3f kN (NBR 16868-1 11.2.2, pilar armado)."
                       % (Nd, NRd)),
        Nd_kN=Nd, NRd_kN=round(NRd, 3), fk_kN_m2=round(fk, 3),
        fd_kN_m2=round(fd, 3), fs_kN_m2=round(fs, 3),
        lambda_=round(lam, 4), lambda_teto=teto,
        R_redutor=round(R, 4), gamma_m=g["alvenaria"], gamma_s=gs,
        A_m2=A, As_m2=As)
    res["peso_proprio_interno_kN"] = _comum_peso_zero()
    return res


def verifica_parede_armada_anexo_C():
    """Parede armada com lambda acima de 30: Anexo C (P-Delta, Md,total
    com w_d, P_d1, P_d2, e, Delta_d). Nao implementada neste lote:
    chamar e recusa com o motivo. Existe para a recusa ter endereco
    (o teste injeta a parede esbelta e exige vermelho nomeado)."""
    raise EntradaAlvenaria(
        "anexo_C_nao_implementado: parede armada com lambda acima de 30 "
        "pede o Anexo C da NBR 16868-1 (P-Delta, momento total de C.2, "
        "tensao teto 10 %% de fpk/gamma_m em C.1-f). Proximo lote.")


def verifica_flexao_simples_1133(Md, As, b, d, fd, fyk, phi_mm,
                                 bloco="concreto", ranhurado=False):
    """Flexao simples com armadura simples, 11.3.3, COM a Errata 1 (fyd).

    MRd = As x fs x z; z = d x (1 - 0,5 x As x fs / (b x d x fd)) com
    teto 0,95 x d; MRd com teto 0,3 x fd x b x d^2 (linha neutra ate
    0,45 x d, ductilidade). fs corta em fyd = fyk / gamma_s_aco, com
    os redutores de aderencia do item: bloco de concreto -> fyd;
    ceramico liso 10 mm -> fyd, 12,5 mm -> 0,75 x fyd, 16 mm ou mais ->
    0,50 x fyd; vazado ranhurado de boa aderencia (NOTA 1: ranhuras a
    cada 10 mm) -> fyd. A errata troca cada fyk do item por fyd: usar
    fyk aqui erra por um gamma_s inteiro. gamma_s_aco vem da Tab.2
    (1,15 normal/especial; 1,0 excepcional).
    """
    Md = float(Md)
    As, b, d = float(As), float(b), float(d)
    fd = float(fd)
    if fyk is None:
        raise EntradaAlvenaria("fyk_nao_declarado: sem fyk nao ha fyd.")
    fyk = float(fyk)
    phi_mm = float(phi_mm)
    if not As > 0:
        raise EntradaAlvenaria("As_nao_positiva: %r m2" % (As,))
    if not b > 0 or not d > 0:
        raise EntradaAlvenaria("b_ou_d_nao_positivos: b=%r d=%r" % (b, d))
    if not fd > 0:
        raise EntradaAlvenaria("fd_nao_positiva: %r" % (fd,))
    if not fyk > 0:
        raise EntradaAlvenaria("fyk_nao_positivo: %r" % (fyk,))
    if bloco not in ("concreto", "ceramico"):
        raise EntradaAlvenaria("bloco_desconhecido_1133: %r" % (bloco,))
    if bloco == "concreto":
        fyd = fyk / GAMMA_M["normal"]["aco"]
        fs = fyd
        redutor = 1.0
    elif ranhurado:
        fyd = fyk / GAMMA_M["normal"]["aco"]
        fs = fyd
        redutor = 1.0
    elif phi_mm <= 10.0:
        fyd = fyk / GAMMA_M["normal"]["aco"]
        fs = fyd
        redutor = 1.0
    elif phi_mm <= 12.5:
        fyd = fyk / GAMMA_M["normal"]["aco"]
        fs = 0.75 * fyd
        redutor = 0.75
    else:
        fyd = fyk / GAMMA_M["normal"]["aco"]
        fs = 0.50 * fyd
        redutor = 0.50
    z = d * (1.0 - 0.5 * As * fs / (b * d * fd))
    z = min(z, 0.95 * d)
    MRd = As * fs * z
    MRd_teto = FATOR_MRD_TETO_DUTIL * fd * b * d * d
    MRd_adot = min(MRd, MRd_teto)
    ok = Md <= MRd_adot
    return {"OK": bool(ok),
            "veredito": "aprovado" if ok else "reprovado",
            "motivo": ("" if ok else
                       "flexao_insuficiente: Md = %.3f kNm acima de "
                       "MRd = %.3f kNm (NBR 16868-1 11.3.3 com fyd da "
                       "Er1:2021)." % (Md, MRd_adot)),
            "Md_kNm": Md, "MRd_kNm": round(MRd_adot, 3),
            "MRd_sem_teto_kNm": round(MRd, 3),
            "MRd_teto_kNm": round(MRd_teto, 3),
            "fs_kN_m2": round(fs, 3), "fyd_kN_m2": round(fyd, 3),
            "fyk_kN_m2": fyk, "redutor_aderencia": redutor,
            "z_m": round(z, 4),
            "errata_fyd_aplicada": True,
            "peso_proprio_interno_kN": 0.0}


def confere_fronteira_peso(Nd_usado_kN, carga_via_6120_kN, tol_kN=1e-3):
    """Igualdade que atravessa a fronteira peso (F21, molde G52).

    Nd_usado_kN: o Nd que entrou na verificacao do elemento.
    carga_via_6120_kN: a mesma carga pela via da carga
    (cargas_nbr6120.carga_linear_parede x comprimento).
    Se os dois lados divergem, um deles contou peso que o outro nao
    contou: reprova a JUNTA, nao o elemento. Relacao, nunca numero
    congelado.
    """
    a, b = float(Nd_usado_kN), float(carga_via_6120_kN)
    ok = abs(a - b) <= float(tol_kN)
    return {"OK": bool(ok),
            "Nd_usado_kN": a, "carga_via_6120_kN": b,
            "diferenca_kN": round(a - b, 4),
            "motivo": ("" if ok else
                       "fronteira_peso_diverge: Nd do elemento (%.3f kN) "
                       "difere da carga via NBR 6120 (%.3f kN) em %.3f kN: "
                       "peso proprio contado duas vezes ou nenhuma."
                       % (a, b, a - b))}


def escopo():
    """O que este lote cobre e o que deixa de fora, dito em voz alta."""
    return {
        "compressao_parede_11_2_1": "implemented",
        "compressao_pilar_11_2_1": "implemented",
        "pilar_armado_11_2_2": "implemented",
        "flexao_simples_11_3_3": "implemented",
        "flexo_compressao_11_5": "not_available",
        "parede_muito_esbelta_anexo_C": "not_available",
        "acao_horizontal_contraventamento": "not_available",
        "bim_alvenaria": "not_available",
        "pranchas_alvenaria": "not_available",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def motivos_escopo():
    """Motivo escrito de cada not_available (D94/G59 pedem artigo, nao
    silencio)."""
    return {
        "flexo_compressao_11_5":
            "NBR 16868-1 11.5 (diagrama de interacao, fs com Es/Ea e fyd "
            "da Er1:2021): sem conta neste lote; proximo lote.",
        "parede_muito_esbelta_anexo_C":
            "NBR 16868-1 Anexo C (parede armada com lambda acima de 30, "
            "P-Delta): sem conta neste lote; a parede esbelta reprova "
            "com este motivo em vez de saturar no teto.",
        "acao_horizontal_contraventamento":
            "NBR 16868-1 9.6.2/10.1.3 (contraventamento distribuido por "
            "rigidez, flanges ate 6t): sem distribuicao neste lote; "
            "estabilidade_b1b2.py e reticulado e nao serve aqui. Qh "
            "declarada recusa com motivo em vez de zerar o vento.",
        "bim_alvenaria":
            "Membros BIM da parede (tipo Wall, fiadas, graute): proximo "
            "lote. Lote com calculo + BIM + executivo de tipologia nova "
            "de uma vez e grande demais para ser revisavel (G60).",
        "pranchas_alvenaria":
            "Desenhos de elevacao/fiadas diferenciadas (NBR 16868-1 "
            "5.3.1): proximo lote, junto com o BIM.",
    }


def linha_memorial_cadeia_gravitacional():
    """Linha de memorial para as cadeias gravitacionais (edificio e casa).

    O vertical existe neste modulo; a cadeia nao alimenta o Nd da parede
    nem o contraventamento (costura no Loop, BIM e pranchas: proximo
    lote). Fonte unica do texto: os relatorios importam daqui em vez de
    congelar o motivo (D86)."""
    return ("[ALVENARIA ESTRUTURAL (NBR 16868-1:2020+Er1:2021): vertical "
            "disponivel em alvenaria_estrutural (compressao 11.2, flexao "
            "11.3.3); esta cadeia gravitacional NAO alimenta o Nd da "
            "parede nem o contraventamento (BIM, pranchas e costura no "
            "Loop: proximo lote).]")


def relatorio_pt(r):
    """Quadro-resumo de uma verificacao de alvenaria."""
    L = ["ALVENARIA ESTRUTURAL (NBR 16868-1:2020 + Er1:2021) - quadro-resumo",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL"]
    estado = {True: "ATENDE", False: "REPROVA/RECUSA"}[bool(r.get("OK"))]
    L.append("  veredito: %s (%s)" % (estado, r.get("veredito", "?")))
    if r.get("motivo"):
        L.append("  motivo: %s" % r["motivo"])
    for chave in ("Nd_kN", "NRd_kN", "Md_kNm", "MRd_kNm", "fk_kN_m2",
                  "fd_kN_m2", "fs_kN_m2", "lambda_", "lambda_teto",
                  "R_redutor", "gamma_m"):
        if chave in r:
            L.append("  %s = %s" % (chave, r[chave]))
    L.append("  peso_proprio_interno_kN = %s (fronteira F21: soma zero)"
             % r.get("peso_proprio_interno_kN", 0.0))
    return "\n".join(L)


# ----------------------------------- selftest --------------------------------
def _selftest():
    # Tab.2 bit a bit
    assert gamma_m("normal") == {"alvenaria": 2.0, "graute": 2.0, "aco": 1.15}
    assert gamma_m("especial")["alvenaria"] == 1.5
    assert gamma_m("excepcional")["aco"] == 1.0
    assert gamma_m("els") == {"alvenaria": 1.0, "graute": 1.0, "aco": 1.0}
    try:
        gamma_m("rara")
        assert False
    except EntradaAlvenaria:
        pass
    # fk: ensaio, nao default
    assert fk_de_fpk(4000.0, "bloco") == 2800.0
    assert fk_de_fpk(4000.0, "tijolo") == 2400.0
    assert fk_de_fpk(4000.0, "bloco", fppk=3000.0) == 2550.0
    try:
        fk_de_fpk(None, "bloco")
        assert False
    except EntradaAlvenaria as e:
        assert "fpk_nao_declarado" in str(e)
    # Ea Tab.1
    assert modulo_deformacao(18000.0, "bloco_concreto") == 800.0 * 18000.0
    assert modulo_deformacao(22000.0, "bloco_concreto") == 750.0 * 22000.0
    assert modulo_deformacao(28000.0, "bloco_concreto") == 700.0 * 28000.0
    assert modulo_deformacao(5000.0, "bloco_ceramico") == 600.0 * 5000.0
    try:
        modulo_deformacao(21000.0, "bloco_concreto")
        assert False
    except EntradaAlvenaria as e:
        assert "Ea_sem_patamar_tabelado" in str(e)
    # nucleo 11.2.1 parede: NRd = fd.A.R
    r = verifica_parede_compressao(100.0, 4000.0, 2.7, 0.14, 0.14 * 1.0)
    lam = 2.7 / 0.14
    R = 1.0 - (lam / 40.0) ** 3
    assert abs(r["NRd_kN"] - (2800.0 / 2.0) * 0.14 * R) < 1e-3
    assert r["OK"] is True and r["peso_proprio_interno_kN"] == 0.0
    # pilar leva 0,9
    rp = verifica_pilar_compressao(100.0, 4000.0, 2.7, 0.14, 0.14 * 1.0)
    assert abs(rp["NRd_kN"] - 0.9 * r["NRd_kN"]) < 1e-3
    # lambda acima do teto reprova (nao satura)
    r2 = verifica_parede_compressao(10.0, 4000.0, 4.5, 0.14, 0.14 * 1.0)
    assert r2["OK"] is False and "esbeltez_acima_do_teto" in r2["motivo"]
    # vento declarado recusa
    r3 = verifica_parede_compressao(10.0, 4000.0, 2.7, 0.14, 0.14,
                                    acao_horizontal_kN=5.0)
    assert r3["OK"] is False and "acao_horizontal" in r3["motivo"]
    # fronteira peso
    assert confere_fronteira_peso(10.0, 10.0)["OK"] is True
    assert confere_fronteira_peso(10.0, 12.0)["OK"] is False
    # escopo publica o fora com motivo
    e = escopo()
    assert e["bim_alvenaria"] == "not_available"
    assert "Anexo C" in motivos_escopo()["parede_muito_esbelta_anexo_C"]
    # linha de memorial: fonte unica, sem motivo congelado
    lin = linha_memorial_cadeia_gravitacional()
    assert "16868-1:2020" in lin and "Er1:2021" in lin
    assert "NAO alimenta o Nd" in lin
    print("alvenaria_estrutural self-test PASSED")
    return True


if __name__ == "__main__":
    _selftest()
