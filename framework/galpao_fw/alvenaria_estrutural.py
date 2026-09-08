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
#     (veredito reprovado); parede armada acima de 30 vai ao Anexo C
#     (P-Delta, verifica_parede_esbelta_anexo_C, G63). Pilar armado acima
#     de 30 reprova (o titulo da 11.2.2 so cobre ate 30; pilar nao tem
#     Anexo C). Lambda nao satura no teto nem vira razao que devolve OK:
#     regra do G51 e do D82.
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
# G63 (depois do G61): ACAO HORIZONTAL DISPONIVEL neste modulo.
#   - contraventamento por rigidez (9.6.2, flanges bf ate 6t na 10.1.3):
#     distribuir_horizontal_por_rigidez(Qh, paredes) reparte Qh pelas
#     paredes proporcional a rigidez relativa k = Ea.I/he^3 (mesmo he e
#     mesmo Ea, proporcional a I). Qh declarada SEM distribuicao continua
#     RECUSANDO com motivo escrito (o vento nunca some em silencio).
#     estabilidade_b1b2.py e reticulado (NBR 8800 Anexo D, MAES de portico
#     de aco) e nao serve aqui: a semelhanca de simbolos nao e parentesco
#     de regra (D84). Nao adaptar, nao importar.
#   - flexo-compressao 11.5: verifica_flexo_compressao_115(Nd, Md) com
#     tensoes elasticas N/A +/- M/W, fs com Es/Ea e fyd da Er1:2021.
#   - Anexo C (parede armada esbelta, P-Delta): verifica_parede_esbelta_
#     anexo_C com Md,total amplificado por 1/(1-Nd/Ncr).
#   - cisalhamento no plano (11.4): fora deste lote; o Vd por parede e
#     REPORTADO (Fi da distribuicao) mas nao verificado. escopo() publica
#     not_available com esse motivo.
#   - BIM e pranchas de alvenaria: G62 (implemented).
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
simples (11.3.3, fyd da errata), flexo-compressao (11.5, G63), Anexo C
(G63), contraventamento por rigidez (9.6.2 com flanges ate 6t na 10.1.3,
G63), esbeltez com tetos da Tab.9 (10.1.2), gamma_m da Tab.2 e fk a
partir do fpk de prisma (6.2.2.3, Parte 3). fpk e entrada declarada sem
default; lambda acima do teto reprova; Qh avulsa recusa com motivo (a
distribuida verifica na 11.5); peso proprio interno zero.
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

# 10.1.3: flange colaborante da parede de contraventamento ate 6t por lado.
FLANGE_LIMITE_6T = 6.0

# Tolerancia absoluta do fechamento horizontal (kN): a soma das Fi
# distribuidas bate com Qh; relacao, nunca numero congelado.
TOL_FECHAMENTO_HORIZONTAL_KN = 1e-6

# C.1-f (leitura do lote): tracao na alvenaria ate 10 % de fpk/gamma_m.
FATOR_TRACAO_ANEXO_C = 0.10


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
    """Recusa nomeada da acao horizontal AVULSA (G63).

    Qh declarada sem distribuicao por parede RECUSA: o vento vai para as
    paredes de contraventamento via distribuir_horizontal_por_rigidez
    (9.6.2, flanges ate 6t na 10.1.3) e cada parede se verifica na
    flexo-compressao 11.5. estabilidade_b1b2.py e reticulado (NBR 8800) e
    nao serve aqui (D84). None ou zero segue o caminho gravitacional
    (11.2); resto recusa (o vento nunca some em silencio)."""
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
            "sem distribuicao por parede. Use "
            "distribuir_horizontal_por_rigidez(Qh, paredes) (NBR 16868-1 "
            "9.6.2, flanges ate 6t na 10.1.3) e verifique cada parede na "
            "flexo-compressao 11.5. Sem distribuicao calculada o caso "
            "recusa em vez de zerar o vento." % (qh,))


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


def secao_efetiva_contraventamento(comprimento_alma_m, te_m,
                                       flange_esq_m=0.0, flange_dir_m=0.0,
                                       te_flange_m=None):
    """Secao efetiva da parede de contraventamento (10.1.3).

    Alma te x L no plano do vento; cada flange transversal colabora ate
    6t (FLANGE_LIMITE_6T): bf_adot = min(bf_declarada, 6.te). O flange
    entra como area concentrada no bordo (A_fl = bf_adot.tf) e o I soma
    A_fl.(L/2)^2 ao I da alma (te.L^3/12); a inercia propria do flange
    e desprezada (conservador). tf default = te.
    """
    L = float(comprimento_alma_m)
    te = float(te_m)
    if not L > 0:
        raise EntradaAlvenaria("alma_nao_positiva: L = %r m" % (L,))
    if not te > 0:
        raise EntradaAlvenaria("te_nao_positiva: %r" % (te,))
    tf = float(te_flange_m) if te_flange_m is not None else te
    if not tf > 0:
        raise EntradaAlvenaria("tf_flange_nao_positiva: %r" % (tf,))
    cap = FLANGE_LIMITE_6T * te
    bf_esq = float(flange_esq_m or 0.0)
    bf_dir = float(flange_dir_m or 0.0)
    if not bf_esq >= 0 or not bf_dir >= 0:
        raise EntradaAlvenaria("flange_negativa: esq=%r dir=%r"
                               % (bf_esq, bf_dir))
    bf_esq_adot = min(bf_esq, cap)
    bf_dir_adot = min(bf_dir, cap)
    A_alma = te * L
    A_esq = bf_esq_adot * tf
    A_dir = bf_dir_adot * tf
    A_eff = A_alma + A_esq + A_dir
    I_alma = te * L ** 3 / 12.0
    I_eff = I_alma + (A_esq + A_dir) * (L / 2.0) ** 2
    return {"A_eff_m2": A_eff, "I_eff_m4": I_eff,
            "bf_esq_declarada_m": bf_esq, "bf_dir_declarada_m": bf_dir,
            "bf_esq_adotada_m": bf_esq_adot, "bf_dir_adotada_m": bf_dir_adot,
            "cap_6t_m": cap,
            "flange_capada": bool(bf_esq > cap or bf_dir > cap)}


def rigidez_parede(I_eff_m4, he_m, Ea_kN_m2=None):
    """Rigidez relativa da parede ao vento no plano (9.6.2).

    k = Ea.I/he^3 (consola vertical; diafragma rigido distribui por k
    relativo). Ea ausente (None) vale 1,0: com mesmo bloco o Ea cancela
    e a reparticao sai por I/he^3. he pela 9.4.1.
    """
    I = float(I_eff_m4)
    he = float(he_m)
    if not I > 0:
        raise EntradaAlvenaria("I_nao_positiva: %r m4" % (I,))
    if not he > 0:
        raise EntradaAlvenaria("he_nao_positiva: %r" % (he,))
    Ea = float(Ea_kN_m2) if Ea_kN_m2 is not None else 1.0
    if not Ea > 0:
        raise EntradaAlvenaria("Ea_nao_positiva: %r" % (Ea,))
    return Ea * I / he ** 3


def distribuir_horizontal_por_rigidez(Qh_kN, paredes, tol_kN=None):
    """Reparte Qh pelas paredes de contraventamento por rigidez (9.6.2).

    Qh_kN: acao horizontal de calculo no nivel (kN, DECLARADA).
    paredes: [{nome, comprimento_m, te_m, he_m, flange_esq_m?, flange_dir_m?,
      te_flange_m?, Ea_kN_m2?}]. Flanges capadas em 6t (10.1.3).
    Parede sem rigidez declaravel (chave ausente ou nao positiva) NAO some
    em silencio: e excluida da reparticao e aparece nomeada em
    paredes_sem_rigidez, e o resultado sai recusado (OK False) ate que ou
    entre (com rigidez) ou seja justificada fora. O fechamento
    soma(Fi) = Qh e conferido com tol_kN (default 1e-6 kN).
    """
    if Qh_kN is None:
        raise EntradaAlvenaria(
            "qh_nao_declarada: a distribuicao 9.6.2 reparte Qh declarada; "
            "sem Qh nao ha o que repartir.")
    try:
        Qh = float(Qh_kN)
    except (TypeError, ValueError):
        raise EntradaAlvenaria("qh_invalida: %r" % (Qh_kN,))
    if not isinstance(paredes, (list, tuple)) or not paredes:
        raise EntradaAlvenaria(
            "paredes_nao_declaradas: a 9.6.2 reparte Qh entre paredes de "
            "contraventamento declaradas (nome, comprimento_m, te_m, he_m).")
    tol = float(tol_kN) if tol_kN is not None else TOL_FECHAMENTO_HORIZONTAL_KN
    nomes = [str(p.get("nome", "?")) for p in paredes]
    if len(set(nomes)) != len(nomes):
        raise EntradaAlvenaria(
            "parede_nome_duplicado: %r" % (sorted(nomes),))
    por_parede = []
    sem_rigidez = []
    for p in paredes:
        nome = str(p.get("nome", "?"))
        try:
            L = float(p["comprimento_m"])
            te = float(p["te_m"])
            he = float(p["he_m"])
            sec = secao_efetiva_contraventamento(
                L, te, p.get("flange_esq_m", 0.0),
                p.get("flange_dir_m", 0.0), p.get("te_flange_m"))
            k = rigidez_parede(sec["I_eff_m4"], he, p.get("Ea_kN_m2"))
        except (KeyError, TypeError, ValueError, EntradaAlvenaria) as exc:
            sem_rigidez.append({"nome": nome, "motivo": str(exc)})
            continue
        por_parede.append({"nome": nome, "comprimento_m": L, "te_m": te,
                           "he_m": he, "A_eff_m2": sec["A_eff_m2"],
                           "I_eff_m4": sec["I_eff_m4"],
                           "bf_esq_adotada_m": sec["bf_esq_adotada_m"],
                           "bf_dir_adotada_m": sec["bf_dir_adotada_m"],
                           "flange_capada": sec["flange_capada"],
                           "Ea_kN_m2": p.get("Ea_kN_m2"),
                           "k_rel": k})
    if not por_parede:
        return {"OK": False, "veredito": "recusado",
                "motivo": ("nenhuma_parede_com_rigidez: Qh = %.3f kN sem "
                           "uma parede de contraventamento com rigidez "
                           "declaravel (NBR 16868-1 9.6.2)." % (Qh,)),
                "Qh_kN": Qh, "soma_Fi_kN": 0.0, "por_parede": [],
                "paredes_sem_rigidez": [s["nome"] for s in sem_rigidez],
                "detalhe_sem_rigidez": sem_rigidez}
    k_total = sum(r["k_rel"] for r in por_parede)
    for r in por_parede:
        r["quota"] = r["k_rel"] / k_total
        r["Fi_kN"] = round(Qh * r["quota"], 6)
    soma = sum(r["Fi_kN"] for r in por_parede)
    erro = soma - Qh
    fecha = abs(erro) <= tol
    if sem_rigidez:
        nomes_fora = ", ".join(sorted(s["nome"] for s in sem_rigidez))
        motivo = ("parede_sem_rigidez_declarada: %s sem rigidez declaravel "
                  "nao entra na reparticao de Qh = %.3f kN (NBR 16868-1 "
                  "9.6.2): ou declara (comprimento_m, te_m, he_m) ou a "
                  "parede aparece nomeada aqui em vez de sumir."
                  % (nomes_fora, Qh))
        ok, veredito = False, "recusado"
    elif not fecha:
        motivo = ("fechamento_horizontal_diverge: soma(Fi) = %.6f kN difere "
                  "de Qh = %.6f kN em %.6f kN." % (soma, Qh, erro))
        ok, veredito = False, "recusado"
    else:
        motivo, ok, veredito = "", True, "distribuida"
    return {"OK": bool(ok), "veredito": veredito, "motivo": motivo,
            "Qh_kN": Qh, "soma_Fi_kN": round(soma, 6),
            "erro_fechamento_kN": round(erro, 6),
            "fechamento_OK": bool(fecha),
            "por_parede": por_parede,
            "paredes_sem_rigidez": [s["nome"] for s in sem_rigidez],
            "detalhe_sem_rigidez": sem_rigidez}


def confere_fechamento_horizontal(distribuicao, Qh_kN, tol_kN=None):
    """Guarda de fechamento do horizontal (G63): soma(Fi) bate com Qh.

    distribuicao: retorno de distribuir_horizontal_por_rigidez ou lista
    [{Fi_kN}|{Vd_kN}]. Relacao, nunca numero congelado.
    """
    if Qh_kN is None:
        raise EntradaAlvenaria("qh_nao_declarada: sem Qh nao ha fechamento.")
    Qh = float(Qh_kN)
    tol = float(tol_kN) if tol_kN is not None else TOL_FECHAMENTO_HORIZONTAL_KN
    if isinstance(distribuicao, dict) and "por_parede" in distribuicao:
        fis = [float(r.get("Fi_kN", 0.0)) for r in distribuicao["por_parede"]]
    else:
        fis = [float(r.get("Fi_kN", r.get("Vd_kN", 0.0)))
               for r in distribuicao]
    soma = sum(fis)
    erro = soma - Qh
    ok = abs(erro) <= tol
    return {"OK": bool(ok), "Qh_kN": Qh, "soma_Fi_kN": round(soma, 6),
            "erro_kN": round(erro, 6), "n_paredes": len(fis),
            "motivo": ("" if ok else
                       "fechamento_horizontal_diverge: soma(Fi) = %.6f kN "
                       "difere de Qh = %.6f kN em %.6f kN."
                       % (soma, Qh, erro))}


def _fs_flexo_115(fpk, tipo_bloco, fyk, combinacao, es_kNm2=None):
    """fs de calculo da 11.5 com a Er1:2021: min(fpk.Es/Ea, fyk)/gamma_s.

    11.5.3.2 pos-errata: "fs <= fpk.Es/Ea" vale para a armadura comprimida
    e cada "fyk" do item vira "fyd". Es default 210 GPa (6.1.4).
    """
    if fyk is None:
        raise EntradaAlvenaria(
            "fyk_nao_declarado: a 11.5 armada corta fs em fyd; sem fyk "
            "declarado nao ha fs.")
    Ea = modulo_deformacao(fpk, tipo_bloco)
    Es = float(es_kNm2) if es_kNm2 is not None else ES_ACO_KNM2
    if not Es > 0:
        raise EntradaAlvenaria("Es_nao_positivo: %r" % (Es,))
    fs_cara = min(float(fpk) * Es / Ea, float(fyk))
    gs = gamma_m(combinacao)["aco"]
    return {"fs_kN_m2": fs_cara / gs, "fs_cara_kN_m2": fs_cara,
            "Ea_kN_m2": Ea, "Es_kN_m2": Es, "gamma_s": gs,
            "errata_Ea_fyd_aplicada": True}


def verifica_flexo_compressao_115(Nd, Md_kNm, fpk, he, te, L,
                                  material="bloco", combinacao="normal",
                                  As=0.0, fyk=None,
                                  tipo_bloco="bloco_concreto",
                                  habitacao_terrea=False, Vd_kN=None,
                                  es_kNm2=None):
    """Parede em flexo-compressao no plano, 11.5 (G63).

    Nd (kN, de calculo) + Md (kNm, de calculo, ex.: Fi.he da 9.6.2) na
    secao te x L: tensoes elasticas sigma = N/A +/- M/W (W = te.L^2/6).
    R = [1-(lambda/40)^3] com lambda = he/te (10.1.2); teto da Tab.9
    (24 sem armadura, 30 armada). Compressao: sigma_max <= fd.R.
    Tracao (sigma_min < 0): sem As REPROVA (flexo_tracao_sem_armadura,
    com o T que o aco teria de levar); com As, o bloco triangular de
    tracao T tem de caber em As.fs (fs da _fs_flexo_115, errata).
    Vd_kN (Fi da parede) e REPORTADO, nao verificado: o cisalhamento no
    plano (11.4) segue fora do lote (ver escopo()).
    """
    Nd = float(Nd)
    Md = float(Md_kNm)
    L = float(L)
    As = float(As)
    if Nd < 0:
        raise EntradaAlvenaria("Nd_negativa: %r kN" % (Nd,))
    if not L > 0:
        raise EntradaAlvenaria("L_nao_positivo: %r m" % (L,))
    if not As >= 0:
        raise EntradaAlvenaria("As_negativa: %r m2" % (As,))
    if As > 0 and fyk is None:
        raise EntradaAlvenaria(
            "fyk_nao_declarado: parede armada na 11.5 exige fyk.")
    fk = fk_de_fpk(fpk, material)
    armada = As > 0
    gm = gamma_alvenaria(combinacao, armada, habitacao_terrea)
    fd = fk / gm
    lam = esbeltez(he, te)
    teto = teto_esbeltez(armada, habitacao_terrea)
    base = {"Nd_kN": Nd, "Md_kNm": Md, "fk_kN_m2": round(fk, 3),
            "fd_kN_m2": round(fd, 3), "lambda_": round(lam, 4),
            "lambda_teto": teto, "gamma_m": gm, "A_m2": round(te * L, 4),
            "L_m": L, "As_m2": As}
    if Vd_kN is not None:
        base["Vd_kN"] = float(Vd_kN)
    if lam > teto:
        base.update(_base_resultado(
            "reprovado", False,
            "esbeltez_acima_do_teto: lambda = %.2f acima de %.0f "
            "(NBR 16868-1 Tab.9, 10.1.2)%s."
            % (lam, teto, ("; parede armada acima de 30 pede o Anexo C "
                           "(verifica_parede_esbelta_anexo_C)" if armada
                           else ""))))
        return base
    A = te * L
    W = te * L * L / 6.0
    sN = Nd / A
    sM = abs(Md) / W
    smax = sN + sM
    smin = sN - sM
    R = R_esbeltez(lam)
    cap = fd * R
    base.update({"R_redutor": round(R, 4),
                 "sigma_N_kN_m2": round(sN, 3),
                 "sigma_M_kN_m2": round(sM, 3),
                 "sigma_max_kN_m2": round(smax, 3),
                 "sigma_min_kN_m2": round(smin, 3),
                 "cap_compressao_kN_m2": round(cap, 3)})
    if smin >= 0:
        ok = smax <= cap
        base.update(_base_resultado(
            "aprovado" if ok else "reprovado", ok,
            "" if ok else ("flexo_compressao_insuficiente: sigma_max = %.1f "
                           "kN/m2 acima de fd.R = %.1f kN/m2 "
                           "(NBR 16868-1 11.5)." % (smax, cap))))
        return base
    x_trac = L * abs(smin) / (smax + abs(smin)) if (smax + abs(smin)) > 0 else 0.0
    T = abs(smin) * te * x_trac / 2.0
    base.update({"tracao_kN": round(T, 3),
                 "borda_tracionada_m": round(x_trac, 4)})
    if not armada:
        base.update(_base_resultado(
            "reprovado", False,
            "flexo_tracao_sem_armadura: sigma_min = %.1f kN/m2 (tracao) e "
            "a parede nao tem As; o bloco tracionado T = %.3f kN pede "
            "armadura (NBR 16868-1 11.5 armada)." % (smin, T)))
        return base
    fs = _fs_flexo_115(fpk, tipo_bloco, fyk, combinacao, es_kNm2)
    Ts = As * fs["fs_kN_m2"]
    base.update({"fs_kN_m2": round(fs["fs_kN_m2"], 3),
                 "Ts_kN": round(Ts, 3),
                 "errata_Ea_fyd_aplicada": True})
    ok = (smax <= cap) and (T <= Ts)
    if smax > cap:
        motivo = ("flexo_compressao_insuficiente: sigma_max = %.1f kN/m2 "
                  "acima de fd.R = %.1f kN/m2 (NBR 16868-1 11.5)."
                  % (smax, cap))
    elif T > Ts:
        motivo = ("armadura_insuficiente_115: T = %.3f kN acima de "
                  "As.fs = %.3f kN (NBR 16868-1 11.5, fs com Es/Ea e fyd "
                  "da Er1:2021)." % (T, Ts))
    else:
        motivo = ""
    base.update(_base_resultado("aprovado" if ok else "reprovado", ok, motivo))
    return base


def verifica_parede_esbelta_anexo_C(Nd, Md1_kNm, fpk, he, te, L, As, fyk,
                                    tipo_bloco="bloco_concreto",
                                    material="bloco", combinacao="normal",
                                    es_kNm2=None):
    """Parede ARMADA esbelta (lambda > 30), Anexo C, P-Delta (G63).

    Campo: parede armada com lambda = he/te acima de 30 (Tab.9/11.2.2 vao
    ate 30). Abaixo de 30 o metodo nao se aplica: recusa com o endereco
    da 11.5. Ncr = pi^2.Ea.I_oop/he^2 (I_oop = L.te^3/12); Nd >= Ncr
    reprova (flambagem). Md,total = Md1/(1-Nd/Ncr) (amplificacao P-Delta
    elastica, C.2). Compressao: sigma_max <= fd (sem R: a 2a ordem ja esta
    no momento). Tracao: limitada a 10 % de fpk/gamma_m (C.1-f, leitura do
    lote) e, havendo bloco tracionado T, coberta por As.fs (errata).
    Pilar nao tem Anexo C (segue reprovando na 11.2.2).
    """
    Nd = float(Nd)
    Md1 = float(Md1_kNm)
    L = float(L)
    As = float(As)
    if Nd < 0:
        raise EntradaAlvenaria("Nd_negativa: %r kN" % (Nd,))
    if not L > 0:
        raise EntradaAlvenaria("L_nao_positivo: %r m" % (L,))
    if not As > 0:
        raise EntradaAlvenaria(
            "anexo_C_pede_parede_armada: As = %r m2; sem armadura a parede "
            "acima de 30 reprova na Tab.9 (NBR 16868-1 10.1.2)." % (As,))
    if fyk is None:
        raise EntradaAlvenaria(
            "fyk_nao_declarado: o Anexo C armado corta fs em fyd.")
    lam = esbeltez(he, te)
    if lam <= LAMBDA_TETO_ARMADA:
        raise EntradaAlvenaria(
            "anexo_C_so_acima_30: lambda = %.2f dentro do campo da 11.2/11.5; "
            "o Anexo C (NBR 16868-1) so cobre parede armada acima de 30 "
            "(use verifica_flexo_compressao_115)." % (lam,))
    fk = fk_de_fpk(fpk, material)
    gm = gamma_m(combinacao)["alvenaria"]
    fd = fk / gm
    Ea = modulo_deformacao(fpk, tipo_bloco)
    te = float(te)
    he = float(he)
    I_oop = L * te ** 3 / 12.0
    Ncr = math.pi ** 2 * Ea * I_oop / he ** 2
    base = {"Nd_kN": Nd, "Md1_kNm": Md1, "fk_kN_m2": round(fk, 3),
            "fd_kN_m2": round(fd, 3), "lambda_": round(lam, 4),
            "gamma_m": gm, "Ea_kN_m2": Ea, "Ncr_kN": round(Ncr, 3),
            "L_m": L, "te_m": te, "he_m": he, "As_m2": As}
    if Nd >= Ncr:
        base.update(_base_resultado(
            "reprovado", False,
            "flambagem_anexo_C: Nd = %.3f kN acima de Ncr = %.3f kN "
            "(NBR 16868-1 Anexo C)." % (Nd, Ncr)))
        return base
    ampl = 1.0 / (1.0 - Nd / Ncr)
    Md_tot = Md1 * ampl
    A = te * L
    W = L * te * te / 6.0
    sN = Nd / A
    sM = abs(Md_tot) / W
    smax = sN + sM
    smin = sN - sM
    cap_trac = FATOR_TRACAO_ANEXO_C * float(fpk) / gm
    fs = _fs_flexo_115(fpk, tipo_bloco, fyk, combinacao, es_kNm2)
    Ts = As * fs["fs_kN_m2"]
    base.update({"amplificacao_PDelta": round(ampl, 4),
                 "Md_total_kNm": round(Md_tot, 4),
                 "sigma_max_kN_m2": round(smax, 3),
                 "sigma_min_kN_m2": round(smin, 3),
                 "cap_tracao_C1f_kN_m2": round(cap_trac, 3),
                 "fs_kN_m2": round(fs["fs_kN_m2"], 3),
                 "Ts_kN": round(Ts, 3),
                 "errata_Ea_fyd_aplicada": True})
    if smax > fd:
        motivo = ("compressao_anexo_C_insuficiente: sigma_max = %.1f kN/m2 "
                  "acima de fd = %.1f kN/m2 com Md,total = %.3f kNm "
                  "(NBR 16868-1 Anexo C)." % (smax, fd, Md_tot))
        ok = False
    elif smin < -cap_trac:
        motivo = ("tracao_acima_C1f: sigma_min = %.1f kN/m2 abaixo de "
                  "-%.1f kN/m2 (10 %% de fpk/gamma_m, NBR 16868-1 C.1-f)."
                  % (smin, cap_trac))
        ok = False
    elif smin < 0:
        x_trac = te * abs(smin) / (smax + abs(smin))
        T = abs(smin) * L * x_trac / 2.0
        base.update({"tracao_kN": round(T, 3)})
        if T > Ts:
            motivo = ("armadura_insuficiente_anexo_C: T = %.3f kN acima de "
                      "As.fs = %.3f kN (fs com Es/Ea e fyd da Er1:2021)."
                      % (T, Ts))
            ok = False
        else:
            motivo, ok = "", True
    else:
        motivo, ok = "", True
    base.update(_base_resultado("aprovado" if ok else "reprovado", ok, motivo))
    return base


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


def verifica_parede_armada_anexo_C(*a, **kw):
    """Alias legado (G60): o Anexo C agora e verifica_parede_esbelta_anexo_C
    (G63, P-Delta com Md,total de C.2 e teto de tracao de C.1-f). Chamada sem
    os esforcos recusa com o endereco novo em vez de fingir conta."""
    if not a and not kw:
        raise EntradaAlvenaria(
            "anexo_C_pede_esforcos: use verifica_parede_esbelta_anexo_C(Nd, "
            "Md1_kNm, fpk, he, te, L, As, fyk) (NBR 16868-1 Anexo C, G63).")
    return verifica_parede_esbelta_anexo_C(*a, **kw)


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
    """Igualdade que atravessa a fronteira peso (F21, molde G52) — CASO ISOLADO.

    Nd_usado_kN: o Nd que entrou na verificacao do elemento.
    carga_via_6120_kN: a mesma carga pela via da carga
    (cargas_nbr6120.carga_linear_parede x comprimento).
    Vale quando Nd E a propria parede (G60). Com laje acima, Nd deixa de
    ser o peso da parede e esta igualdade QUEBRA POR CONSTRUCAO: use
    confere_fronteira_peso_parcela (G61).
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


def confere_fronteira_peso_parcela(Nd_parede_kN, tipo_parede_6120,
                                   espessura_cm, altura_m,
                                   comprimento_m, revestimento_cm=1.0,
                                   tol_kN=1e-3):
    """Igualdade da fronteira peso para o CASO REAL (F21, G61).

    Com laje e pavimentos acima, Nd = laje + parede e Nd total nunca bate
    com o peso da parede. O guarda compara a PARCELA de Nd atribuivel a
    parede contra carga_linear_parede x L — relacao, nunca numero congelado:
    a carga via NBR 6120 e recomputada aqui dentro (revestimento fora do
    default como filtro de nome morto), nao recebida pronta.

    Nd_parede_kN: parcela isolada por linha de parede, na mesma base da
    carga via 6120 (caracteristica x caracteristica, ou calculo x calculo
    com o mesmo GF dos dois lados). Quem chama ISOLA a parcela no
    resultado (estrutura_casa.dimensiona_alvenaria_portante); sem parcela
    isolavel a junta e inverificavel e o caso RECUSA.
    """
    import cargas_nbr6120 as _cg
    if Nd_parede_kN is None:
        return {"OK": False, "Nd_parede_kN": None,
                "carga_via_6120_kN": None, "diferenca_kN": None,
                "motivo": ("fronteira_peso_parcela_ausente: a parcela de Nd "
                           "atribuivel a parede nao foi isolada no resultado; "
                           "sem parcela isolavel a junta e inverificavel (F21).")}
    a = float(Nd_parede_kN)
    carga_lin = _cg.carga_linear_parede(tipo_parede_6120, espessura_cm,
                                        altura_m, revestimento_cm)
    b = float(carga_lin) * float(comprimento_m)
    ok = abs(a - b) <= float(tol_kN)
    return {"OK": bool(ok),
            "Nd_parede_kN": a, "carga_via_6120_kN": round(b, 4),
            "carga_linear_kN_m": round(float(carga_lin), 4),
            "comprimento_m": float(comprimento_m),
            "diferenca_kN": round(a - b, 4),
            "motivo": ("" if ok else
                       "fronteira_peso_parcela_diverge: parcela de Nd da parede "
                       "(%.3f kN) difere da carga via NBR 6120 (%.3f kN/m x %.3f m "
                       "= %.3f kN) em %.3f kN: peso proprio contado duas vezes "
                       "ou nenhuma." % (a, carga_lin, float(comprimento_m),
                                        b, a - b))}


def escopo():
    """O que este lote cobre e o que deixa de fora, dito em voz alta."""
    return {
        "compressao_parede_11_2_1": "implemented",
        "compressao_pilar_11_2_1": "implemented",
        "pilar_armado_11_2_2": "implemented",
        "flexao_simples_11_3_3": "implemented",
        # G63: distribuicao 9.6.2 + 11.5 + Anexo C disponiveis; o
        # cisalhamento no plano (11.4) segue fora e nomeado.
        "flexo_compressao_11_5": "implemented",
        "parede_muito_esbelta_anexo_C": "implemented",
        "acao_horizontal_contraventamento": "implemented",
        "cisalhamento_11_4": "not_available",
        # A prancha DESENHA verga e contraverga (com apoio de 0,40 m); ninguem
        # as dimensiona. Desenho que sugere calculo inexistente e rotulo
        # dirigindo geometria: fica dito aqui em vez de implicito na folha.
        "verga_contraverga": "not_available",
        # G62: a parede calculada vira folha (desenho_alvenaria sobre as
        # primitivas de desenho_svg_base) e membro BIM (tipo Wall + Footing
        # corrido em bim_edificio, IfcWall/IfcFooting em ifc_emit).
        "bim_alvenaria": "implemented",
        "pranchas_alvenaria": "implemented",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def motivos_escopo():
    """Motivo escrito de cada not_available (D94/G59 pedem artigo, nao
    silencio)."""
    return {
        "flexo_compressao_11_5":
            "G63: verifica_flexo_compressao_115 (NBR 16868-1 11.5, tensoes "
            "N/A +/- M/W, fs com Es/Ea e fyd da Er1:2021).",
        "parede_muito_esbelta_anexo_C":
            "G63: verifica_parede_esbelta_anexo_C (NBR 16868-1 Anexo C, "
            "P-Delta com Md,total de C.2 e teto de tracao de C.1-f).",
        "acao_horizontal_contraventamento":
            "G63: distribuir_horizontal_por_rigidez (NBR 16868-1 9.6.2, "
            "flanges ate 6t na 10.1.3) + confere_fechamento_horizontal "
            "(soma Fi = Qh). estabilidade_b1b2.py e reticulado e nao serve "
            "aqui (D84). Qh avulsa recusa com motivo em vez de zerar o vento.",
        "cisalhamento_11_4":
            "NBR 16868-1 11.4 (cisalhamento no plano da parede de "
            "contraventamento): sem conta neste lote; o Vd por parede "
            "(Fi da 9.6.2) e reportado mas nao verificado.",
        "verga_contraverga":
            "A elevacao desenha verga e contraverga sobre cada vao (apoio de "
            "0,40 m de cada lado, pratica corrente), mas NENHUM modulo as "
            "dimensiona: nao ha flexao da verga (vao livre + carga da parede "
            "acima, arco de descarga) nem armadura calculada. A folha mostra "
            "a peca; o memorial nao a verifica. Enquanto assim, a verga e "
            "detalhe construtivo declarado, nao dimensionamento.",
        "bim_alvenaria":
            "G62: membros BIM da parede (tipo Wall por linha e nivel, Footing "
            "corrido por linha em bim_edificio; IfcWall/IfcFooting em "
            "ifc_emit). Fiadas e graute seguem na prancha e no caderno "
            "(NBR 16868-2).",
        "pranchas_alvenaria":
            "G62: elevacao das paredes (fiadas 0,20 m, vãos declarados, "
            "vergas/contravergas, quadro de blocos) + plantas de 1a/2a fiada "
            "em desenho_alvenaria, sobre as primitivas de desenho_svg_base.",
    }


def linha_memorial_cadeia_gravitacional():
    """Linha de memorial para as cadeias gravitacionais (edificio e casa).

    Fonte unica do texto: os relatorios importam daqui em vez de congelar
    o motivo (D86). G63: o contraventamento por rigidez (9.6.2/10.1.3),
    a flexo-compressao 11.5 e o Anexo C estao disponiveis neste modulo;
    o cisalhamento no plano (11.4) segue fora."""
    return ("[ALVENARIA ESTRUTURAL (NBR 16868-1:2020+Er1:2021): vertical "
            "disponivel em alvenaria_estrutural (compressao 11.2, flexao "
            "11.3.3, flexo-compressao 11.5, Anexo C e contraventamento 9.6.2 "
            "com flanges ate 6t na 10.1.3 — G63); na casa portante o Nd da "
            "parede vem da laje (G61) e a parede vira folha e BIM (G62); "
            "cisalhamento 11.4 fora do lote.]")


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
    # G61: parcela no caso real (relacao via carga_linear_parede x L)
    import cargas_nbr6120 as _cg61
    _g = _cg61.carga_linear_parede("bloco_concreto_estrutural", 14.0, 2.7, 2.0)
    assert confere_fronteira_peso_parcela(
        _g * 3.3, "bloco_concreto_estrutural", 14.0, 2.7, 3.3, 2.0)["OK"] is True
    assert confere_fronteira_peso_parcela(
        _g * 3.3 * 1.10, "bloco_concreto_estrutural", 14.0, 2.7, 3.3,
        2.0)["OK"] is False
    assert confere_fronteira_peso_parcela(
        None, "bloco_concreto_estrutural", 14.0, 2.7, 3.3)["OK"] is False
    # escopo publica o fora com motivo
    e = escopo()
    assert e["bim_alvenaria"] == "implemented"
    assert e["pranchas_alvenaria"] == "implemented"
    # G63: horizontal, 11.5 e Anexo C disponiveis; cisalhamento segue fora.
    assert e["flexo_compressao_11_5"] == "implemented"
    assert e["parede_muito_esbelta_anexo_C"] == "implemented"
    assert e["acao_horizontal_contraventamento"] == "implemented"
    assert e["cisalhamento_11_4"] == "not_available"
    assert "11.5" in motivos_escopo()["flexo_compressao_11_5"]
    # G63: flange capada em 6t e fechamento soma = Qh (relacao).
    sec = secao_efetiva_contraventamento(3.0, 0.14, 2.0, 0.0)
    assert abs(sec["bf_esq_adotada_m"] - 6.0 * 0.14) < 1e-12
    assert sec["flange_capada"] is True
    d = distribuir_horizontal_por_rigidez(
        10.0, [{"nome": "PX-1", "comprimento_m": 3.0, "te_m": 0.14,
                "he_m": 2.7},
               {"nome": "PX-2", "comprimento_m": 1.5, "te_m": 0.14,
                "he_m": 2.7}])
    assert d["OK"] is True
    assert abs(d["soma_Fi_kN"] - 10.0) <= TOL_FECHAMENTO_HORIZONTAL_KN
    assert confere_fechamento_horizontal(d, 10.0)["OK"] is True
    # parede sem rigidez aparece nomeada em vez de sumir
    d2 = distribuir_horizontal_por_rigidez(
        10.0, [{"nome": "PX-1", "comprimento_m": 3.0, "te_m": 0.14,
                "he_m": 2.7},
               {"nome": "PX-fantasma"}])
    assert d2["OK"] is False
    assert "PX-fantasma" in d2["paredes_sem_rigidez"]
    assert "PX-fantasma" in d2["motivo"]
    # 11.5: compressao pura coincide com a 11.2.1 (relacao entre funcoes)
    r115 = verifica_flexo_compressao_115(100.0, 0.0, 4000.0, 2.7, 0.14, 1.0)
    assert r115["OK"] is True
    assert abs(r115["sigma_max_kN_m2"] - 100.0 / 0.14) < 1.0
    # Anexo C: Md,total amplifica o Md1 (P-Delta) e Ncr limita
    c = verifica_parede_esbelta_anexo_C(50.0, 2.0, 4000.0, 5.0, 0.14, 2.0,
                                        4e-4, 500e3)
    assert c["Md_total_kNm"] > 2.0
    assert c["Ncr_kN"] > 50.0
    # linha de memorial: fonte unica, sem motivo congelado
    lin = linha_memorial_cadeia_gravitacional()
    assert "16868-1:2020" in lin and "Er1:2021" in lin
    assert "G61" in lin and "G63" in lin
    print("alvenaria_estrutural self-test PASSED")
    return True


if __name__ == "__main__":
    _selftest()
