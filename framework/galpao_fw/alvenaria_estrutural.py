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
#   - cisalhamento no plano (11.4, G67): verifica_cisalhamento_114(Vd, fa,
#     sigma) com fvk da Tab.4 (6.2.2.6) e tau_vd = Vd/(te.L) da 11.4.1;
#     o Fi da 9.6.2 passa a ser VERIFICADO, nao so reportado.
#   - vento por nivel (G67, NBR 6123 4.2.3 Fa = Ca.q.Ae): vento_fa_por_nivel
#     da origem ao Qh de cada nivel (Ca declarado do abaco da Fig.4, q via
#     vento_nbr6123.s2_factor homologado); Qh avulsa segue recusando.
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
(G63), cisalhamento no plano (11.4 com fvk da Tab.4 em 6.2.2.6, G67),
contraventamento por rigidez (9.6.2 com flanges ate 6t na 10.1.3,
G63) e vento por nivel (NBR 6123 4.2.3 Fa = Ca.q.Ae, G67), esbeltez
com tetos da Tab.9 (10.1.2), gamma_m da Tab.2 e fk a partir do fpk de
prisma (6.2.2.3, Parte 3). fpk e fa sao entradas declaradas sem
default; lambda acima do teto reprova; Qh avulsa recusa com motivo (a
distribuida verifica na 11.5 e na 11.4); peso proprio interno zero.
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

# G70 (verga desenhada ganha conta): geometria declarada da verga /
# contraverga, usada pelo CALCULO, pelo DESENHO e pela CONFERENCIA.
# Apoio de cada lado (m): comprimento de apoio da peca sobre a parede.
# O desenho antigo usava 0,20 m por lado (linha de 0,20*ESC para cada lado,
# total +0,40 m sobre o vao); a convencao fica escrita aqui, nao no SVG.
APOIO_VERGA_M = 0.20
# Altura da verga (m): uma fiada de 0,20 m (canaleta armada). O d util
# desconta 0,03 m de cobrimento.
ALTURA_VERGA_M = 0.20
COBRIMENTO_VERGA_M = 0.03
# Contraverga: detalhe construtivo sob o peitoril das janelas (nao peca
# calculada pela 11.3). Mesma largura da verga, altura de 0,10 m em concreto
# com 2x6.3 corridos: costura a tracao diagonal que abre fissura no canto do
# vao quando o peitoril recalca. Sem ela o canto fissura; com ela nao ha conta
# de flexao a fazer (nao vence vao, nao recebe arco).
ALTURA_CONTRAVERGA_M = 0.10
APOIO_CONTRAVERGA_M = 0.20

# G70 (uma so verdade nos cruzamentos): a parede em X e continua; a parede
# em Y e CORTADA em cada cruzamento com recuo de te/2 de cada lado (parede)
# ou B/2 (sapata corrida). O ORCAMENTO mede a linha INTEIRA (bruto, a favor
# do orcamento) e o MODELO soma os trechos LIQUIDOS (sem dupla ocupacao de
# volume); os dois derivam desta mesma regra, escrita aqui uma unica vez.
# L_liquido_y = L_bruto - (n_linhas_x_com_parede - 1) * te, com minimo de um
# recuo (contorno: L - te). Ver comprimento_liquido_y() e recuo_cruzamento().
CONVENCAO_CRUZAMENTOS = (
    "parede em X continua; parede em Y cortada em cada cruzamento "
    "(recuo te/2 por lado na parede, B/2 na corrida); orcamento mede a linha "
    "inteira (bruto, a favor do orcamento), modelo soma os trechos liquidos; "
    "ambos derivam de alvenaria_estrutural.comprimento_liquido_y (G70)")

# 10.1.3: flange colaborante da parede de contraventamento ate 6t por lado.
FLANGE_LIMITE_6T = 6.0

# Tolerancia absoluta do fechamento horizontal (kN): a soma das Fi
# distribuidas bate com Qh; relacao, nunca numero congelado.
TOL_FECHAMENTO_HORIZONTAL_KN = 1e-6

# C.1-f (leitura do lote): tracao na alvenaria ate 10 % de fpk/gamma_m.
FATOR_TRACAO_ANEXO_C = 0.10

# 6.2.2.6 Tab.4 (G67): faixas de resistencia media da argamassa (MPa) ->
# (tau0_MPa, teto_MPa) de fvk = tau0 + 0,5.sigma. Patamar fora recusa.
FVK_TABELA_4 = (
    (1.5, 3.4, 0.10, 1.0),
    (3.5, 7.0, 0.15, 1.4),
    (7.0, float("inf"), 0.35, 1.7),
)
COEF_ATRITO_FVK = 0.5
# 11.4.3/armada (G67): fvk = 0,35 + 17,5.rho <= 0,7 MPa, rho <= 2 %.
FVK_ARMADA_TAU0_MP = 0.35
FVK_ARMADA_COEF = 17.5
FVK_ARMADA_TETO_MP = 0.7
FVK_ARMADA_RHO_TETO = 0.02


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
    """DECLARACAO de integridade do horizontal (G63), triada no G69 (D86).

    Lado A (soma): soma dos Fi da distribuicao (cada Fi = Qh x quota, com
    quota = k_rel/k_total calculada em distribuir_horizontal_por_rigidez).
    Lado B (Qh): a mesma Qh DECLARADA que entrou na reparticao.
    Os dois lados nascem da MESMA expressao: quotas somam 1 por construcao,
    entao a soma fecha mesmo com a rigidez errada (parede errada, I/he
    errado, direcao trocada). E' guarda decorativa como CONFERENCIA fisica;
    como DECLARACAO ela pega adulteracao posterior (Fi editado a mao,
    parede removida da lista) — nunca erro de formula. Nao apagar sem
    substituto (G69). A relacao independente do plano esta em
    estrutura_casa.verifica_fechamento_alvenaria (simetria, G61).

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


def fvk_caracteristico_6226(fa_MPa, sigma_MPa):
    """fvk da Tab.4 (6.2.2.6, G67), em kN/m2.

    fa_MPa: resistencia MEDIA a compressao da argamassa (MPa, DECLARADA,
      sem default — faixas da Tab.4, nao se interpola patamar).
    sigma_MPa: tensao normal de pre-compressao na junta (MPa, >= 0),
      considerando-se APENAS as acoes permanentes ponderadas por 0,9
      (acao favoravel, nota da Tab.4).
    fvk = tau0 + 0,5.sigma, capado no teto da faixa. Vale para
    assentamento com juntas verticais preenchidas; fora disso o caso
    RECUSA em verifica_cisalhamento_114 (o campo da tabela).
    """
    if fa_MPa is None:
        raise EntradaAlvenaria(
            "fa_nao_declarada: o fvk da Tab.4 (NBR 16868-1 6.2.2.6) e por "
            "faixa de resistencia da argamassa; sem fa declarada nao ha fvk.")
    fa = float(fa_MPa)
    sig = float(sigma_MPa)
    if not sig >= 0:
        raise EntradaAlvenaria("sigma_negativa: %r MPa" % (sig,))
    for fa_min, fa_max, tau0, teto in FVK_TABELA_4:
        if fa_min - 1e-9 <= fa <= fa_max + 1e-9:
            fvk_mp = min(tau0 + COEF_ATRITO_FVK * sig, teto)
            return {"fvk_MPa": fvk_mp, "fvk_kN_m2": fvk_mp * 1000.0,
                    "tau0_MPa": tau0, "teto_MPa": teto,
                    "faixa_MPa": (fa_min, fa_max),
                    "fonte": "NBR 16868-1 Tab.4 (6.2.2.6)"}
    raise EntradaAlvenaria(
        "fa_fora_da_tabela_4: fa = %.2f MPa fora das faixas 1,5-3,4 / "
        "3,5-7,0 / acima de 7,0 MPa (NBR 16868-1 Tab.4, 6.2.2.6)."
        % (fa,))


def verifica_cisalhamento_114(Vd_kN, N_perm_kN, te_m, L_m, fa_MPa,
                              combinacao="normal",
                              juntas_verticais_preenchidas=True):
    """Parede nao armada ao cisalhamento no plano, 11.4 (G67).

    Vd_kN: cortante DE CALCULO na parede (kN, ex.: Fi da 9.6.2 x 1,4).
    N_perm_kN: normal CARACTERISTICA das acoes PERMANENTES na parede
      (kN, >= 0 — laje g + parede + telhado g; o 0,9 favoravel entra aqui
      dentro, nota da Tab.4, nunca por fora).
    te_m x L_m: secao da ALMA (m; 11.4.1: em secao com flanges, so a alma).
    fa_MPa: resistencia media da argamassa (MPa, DECLARADA).
    juntas_verticais_preenchidas: o campo da Tab.4; False RECUSA (a tabela
      so vale com elas preenchidas, 6.2.2.6).
    tau_vd = Vd/(te.L) <= fvk/gamma_m (11.4.1 + 11.4.2). Parede ARMADA ao
    cisalhamento (11.4.3, Va + Vs) RECUSA com endereco: fora deste lote.
    """
    if not juntas_verticais_preenchidas:
        return _base_resultado(
            "recusado", False,
            "juntas_verticais_nao_preenchidas: o fvk da Tab.4 (NBR 16868-1 "
            "6.2.2.6) so vale para assentamento com juntas verticais "
            "preenchidas; sem elas nao ha fvk neste lote.",
            Vd_kN=float(Vd_kN))
    Vd = float(Vd_kN)
    Np = float(N_perm_kN)
    te = float(te_m)
    L = float(L_m)
    if Vd < 0:
        raise EntradaAlvenaria("Vd_negativa: use o modulo (Vd = %r kN)."
                               % (Vd,))
    if not Np >= 0:
        raise EntradaAlvenaria("N_perm_negativa: %r kN" % (Np,))
    if not te > 0:
        raise EntradaAlvenaria("te_nao_positiva: %r" % (te,))
    if not L > 0:
        raise EntradaAlvenaria("L_nao_positivo: %r m" % (L,))
    A = te * L
    sigma = 0.9 * Np / A / 1000.0            # MPa (0,9 favoravel, Tab.4)
    fvk = fvk_caracteristico_6226(fa_MPa, sigma)
    gm = gamma_m(combinacao)["alvenaria"]
    fvd = fvk["fvk_kN_m2"] / gm
    tau = Vd / A
    VRd = fvd * A
    ok = tau <= fvd
    return _base_resultado(
        "aprovado" if ok else "reprovado", ok,
        "" if ok else ("cisalhamento_insuficiente: tau_vd = %.1f kN/m2 "
                       "acima de fvd = fvk/gamma_m = %.1f kN/m2 "
                       "(NBR 16868-1 11.4.1 + 11.4.2, fvk da Tab.4)."
                       % (tau, fvd)),
        Vd_kN=Vd, N_perm_kN=Np, te_m=te, L_m=L, A_m2=round(A, 4),
        sigma_MPa=round(sigma, 4), fa_MPa=float(fa_MPa),
        fvk_kN_m2=round(fvk["fvk_kN_m2"], 3),
        fvk_MPa=round(fvk["fvk_MPa"], 4),
        fvd_kN_m2=round(fvd, 3), tau_vd_kN_m2=round(tau, 3),
        VRd_kN=round(VRd, 3), gamma_m=gm,
        fonte_fvk=fvk["fonte"])


def vento_fa_por_nivel(n_pavimentos, pe_direito_m, largura_frontal_m,
                       vento):
    """Forca de arrasto por nivel, NBR 6123 4.2.3 Fa = Ca.q.Ae (G67).

    n_pavimentos/pe_direito_m/largura_frontal_m: geometria (m). A faixa
    tributaria do nivel i vai de z_i - pe/2 a z_i + pe/2, exceto o ultimo
    (topo), que termina no topo; a meia-altura inferior (0 a pe/2) desce
    direto a fundacao e NAO e atribuida a nivel nenhum — a mesma particao
    de estabilidade_edificio._cotas_e_areas (origem do Qh, nao numero).
    vento: {v0 (m/s), cat (I-V), classe (A-C), s1?, s3?, ca (numero > 0,
      DECLARADO do abaco da Fig.4 com h/l1 e l1/l2 — a norma so da abaco)}.
    q via vento_nbr6123.s2_factor (homologado; nao recalculado aqui).
    Devolve por nivel {z, h_trib, Ae, s2, vk, q, Fa} + F_total + M_base.
    """
    import vento_nbr6123 as _vt
    n = int(n_pavimentos)
    pe = float(pe_direito_m)
    l1 = float(largura_frontal_m)
    if not n >= 1:
        raise EntradaAlvenaria("n_pavimentos_nao_positivo: %r" % (n,))
    if not pe > 0:
        raise EntradaAlvenaria("pe_direito_nao_positivo: %r" % (pe,))
    if not l1 > 0:
        raise EntradaAlvenaria("largura_frontal_nao_positiva: %r" % (l1,))
    if not isinstance(vento, dict):
        raise EntradaAlvenaria(
            "vento_nao_declarado: o sobrado pede vento NBR 6123 (v0, cat, "
            "classe, ca declarado do abaco da Fig.4); Qh avulsa segue "
            "recusando.")
    try:
        v0 = float(vento["v0"])
        cat, classe = vento["cat"], vento["classe"]
        ca = float(vento["ca"])
    except (KeyError, TypeError, ValueError):
        raise EntradaAlvenaria(
            "vento_incompleto: declare v0/cat/classe + ca (NBR 6123 Fig.4, "
            "abaco lido pelo projetista, recebido %r)." % (vento,))
    if not v0 > 0:
        raise EntradaAlvenaria("v0_nao_positivo: %r" % (v0,))
    if not ca > 0:
        raise EntradaAlvenaria("ca_nao_positivo: %r" % (ca,))
    s1 = float(vento.get("s1", 1.0))
    s3 = float(vento.get("s3", 1.0))
    niveis = []
    for i in range(1, n + 1):
        z = i * pe
        h_trib = pe if i < n else pe / 2.0
        Ae = l1 * h_trib
        _b, _fr, _p, s2 = _vt.s2_factor(cat, classe, z)
        vk = v0 * s1 * s2 * s3
        q = 0.613 * vk ** 2 / 1000.0
        Fa = ca * q * Ae
        niveis.append({"nivel": i, "z_m": round(z, 3),
                       "h_trib_m": round(h_trib, 3),
                       "Ae_m2": round(Ae, 3), "s2": round(s2, 4),
                       "vk_m_s": round(vk, 2), "q_kN_m2": round(q, 4),
                       "Fa_kN": round(Fa, 3)})
    F_tot = sum(v["Fa_kN"] for v in niveis)
    M_base = sum(v["Fa_kN"] * v["z_m"] for v in niveis)
    return {"n_pavimentos": n, "pe_direito_m": pe,
            "largura_frontal_m": l1, "ca": ca,
            "ca_fonte": ("NBR 6123 Figura 4 (abaco): Ca em funcao de h/l1 "
                         "e l1/l2 — lido pelo projetista, nao derivado aqui"),
            "niveis": niveis, "F_total_kN": round(F_tot, 3),
            "M_base_kNm": round(M_base, 3)}


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
    Vd_kN (Fi da parede) e REPORTADO para a 11.4 (G67 verifica em
    verifica_cisalhamento_114); aqui nao e verificado.
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


def recuo_cruzamento(te_ou_B_m):
    """Recuo de cada lado no corte em Y (G70): te/2 na parede, B/2 na corrida.

    Fonte unica da convencao (CONVENCAO_CRUZAMENTOS): bim_edificio e
    gestao_casa derivam daqui, nunca de numero repetido.
    """
    t = float(te_ou_B_m)
    if not t > 0:
        raise EntradaAlvenaria("recuo_nao_positivo: %r" % (te_ou_B_m,))
    return t / 2.0


def comprimento_liquido_y(L_bruto_m, n_linhas_x, te_m):
    """L liquido da linha em Y apos o corte nos cruzamentos (G70).

    L_bruto: linha inteira (o que o orcamento mede, a favor do orcamento).
    n_linhas_x: quantas linhas em X com parede cruzam o eixo Y.
    te: espessura da parede. L_liq = L_bruto - max(n_x-1,1)*te.
    Com so o contorno (n_x=2) devolve L-te (um recuo em cada ponta); com
    malha interna, um te por vao interno. A corrida usa a mesma funcao com
    B no lugar de te.
    """
    L = float(L_bruto_m)
    te = float(te_m)
    try:
        n_x = int(n_linhas_x)
    except (TypeError, ValueError):
        raise EntradaAlvenaria("n_linhas_x_invalido: %r" % (n_linhas_x,))
    if not L > 0 or not te > 0 or n_x < 0:
        raise EntradaAlvenaria(
            "cruzamento_invalido: L=%r n_x=%r te=%r" % (L_bruto_m, n_linhas_x, te_m))
    cortes = max(n_x - 1, 1)
    liq = L - cortes * te
    if not liq > 0:
        raise EntradaAlvenaria(
            "linha_y_sem_trecho: L=%.3f m com %d linhas em X e te=%.3f m "
            "nao deixa trecho positivo" % (L, n_x, te))
    return round(liq, 4)


def detalhe_contraverga(larg_vao_m, apoio_m=None):
    """Contraverga sob o peitoril: DETALHE construtivo, nao peca calculada.

    Funcao: costurar a tracao diagonal que abre fissura a 45 graus no canto
    do vao quando o peitoril recalca. Dimensao: larg + 2*apoio de cada lado,
    altura ALTURA_CONTRAVERGA_M (0,10 m) em concreto com 2x6.3 corridos.
    Nao ha verificacao de flexao pela 11.3 aqui (nao vence vao, nao recebe
    arco de descarga): o motivo fica escrito para a folha nao prometer conta.
    """
    larg = float(larg_vao_m)
    if not larg > 0:
        raise EntradaAlvenaria("vao_nao_positivo_contraverga: %r" % (larg_vao_m,))
    ap = float(apoio_m) if apoio_m is not None else APOIO_CONTRAVERGA_M
    if not ap > 0:
        raise EntradaAlvenaria("apoio_nao_positivo_contraverga: %r" % (apoio_m,))
    return {"peca": "contraverga",
            "funcao": "costurar a tracao diagonal no canto do vao "
                      "(fissuracao no canto do vao sob o peitoril)",
            "comprimento_m": round(larg + 2.0 * ap, 3),
            "altura_m": ALTURA_CONTRAVERGA_M,
            "apoio_m": round(ap, 3),
            "armadura": "2x6.3 corridos (detalhe construtivo)",
            "calculada_113": False,
            "motivo": "detalhe_construtivo_nao_peca_calculada: a contraverga "
                      "nao vence vao em flexao (11.3 nao se aplica); evita a "
                      "fissura no canto do vao, nao carrega arco."}


def dimensiona_verga_1133(larg_vao_m, h_parede_acima_m, peso_parede_kN_m2,
                          q_laje_linear_kN_m=0.0, h_laje_sobre_verga_m=None,
                          fpk=None, material="bloco", te_m=0.14,
                          combinacao="normal", fyk=500e3, phi_mm=10.0,
                          bloco="concreto", ranhurado=False,
                          apoio_m=None, altura_verga_m=None,
                          gf=1.4):
    """Verga sobre o vao em flexao simples 11.3.3 COM arco de descarga (G70).

    Vao: L_calculo = larg_vao + apoio (vao livre mais UM apoio, efetivo de
    apoio simples); a PECA mede larg + 2*apoio (desenho confere esse total).
    Carga da parede: arco a 45 graus sobre o vao (triangulo isosceles de base
    L_calculo e altura L_calculo/2). Se a parede acima chega para formar o
    arco (h_parede_acima >= L_calculo/2), so o triangulo pesa na verga:
    q_parede = peso * h_arco/2 (peso do triangulo rateado em L). Sem altura
    para o arco, a verga leva a parede cheia (q = peso*h_acima): sem o arco
    a verga sai grosseiramente superdimensionada; com o arco mal aplicado
    (triangulo onde nao cabe, ou laje dentro do triangulo ignorada) sai
    contra a seguranca.
    Laje: so entra a parcela que cai DENTRO do triangulo. A laje pousa no
    topo da parede a h_laje_sobre_verga do topo do vao (default = h_acima);
    se essa cota esta acima de h_arco, o arco desvia a laje para os lados e
    a verga nao a recebe (q_laje=0); se esta dentro, a verga recebe a linha
    toda (q_laje_linear). Peso proprio da canaleta (25*te*h_verga) soma.
    Flexao: Md = q_tot*L^2/8 (ELU com gf); fd = fk/gamma (fk de fk_de_fpk,
    gamma de gamma_alvenaria sem armadura/terrea=False); d = h_verga -
    cobrimento; As escolhido entre 2 barras (6.3/8/10/12.5) pela primeira que
    passa em verifica_flexao_simples_1133 (fyd da Er1:2021, redutores e teto
    0,3.fd.b.d2 dentro da verifica).
    Devolve o dimensionamento com o arco declarado (arco_formado True/False)
    e a armadura adotada; se nenhuma bitola passa, OK=False com motivo (em
    vez de devolver As que nao verifica).
    """
    larg = float(larg_vao_m)
    h_ac = float(h_parede_acima_m)
    peso = float(peso_parede_kN_m2)
    if not larg > 0:
        raise EntradaAlvenaria("vao_nao_positivo_verga: %r" % (larg_vao_m,))
    if not h_ac >= 0:
        raise EntradaAlvenaria("h_acima_negativa_verga: %r" % (h_parede_acima_m,))
    if not peso > 0:
        raise EntradaAlvenaria("peso_parede_nao_positivo_verga: %r"
                               % (peso_parede_kN_m2,))
    ap = float(apoio_m) if apoio_m is not None else APOIO_VERGA_M
    hv_fixa = float(altura_verga_m) if altura_verga_m is not None else None
    if not ap > 0 or (hv_fixa is not None and not hv_fixa > 0):
        raise EntradaAlvenaria("apoio_ou_altura_nao_positivos_verga: ap=%r h=%r"
                               % (apoio_m, altura_verga_m))
    if fpk is None:
        raise EntradaAlvenaria(
            "fpk_nao_declarado_verga: sem fpk nao ha fk nem fd (regra do SPT).")
    te = float(te_m)
    if not te > 0:
        raise EntradaAlvenaria("te_nao_positiva_verga: %r" % (te_m,))
    L = larg + ap
    comp_peca = larg + 2.0 * ap
    h_arco_pot = L / 2.0
    arco = h_ac >= h_arco_pot - 1e-9
    h_arco = h_arco_pot if arco else h_ac
    if arco:
        q_parede = peso * h_arco / 2.0
    else:
        q_parede = peso * h_ac
    q_laje = float(q_laje_linear_kN_m or 0.0)
    if q_laje < 0:
        raise EntradaAlvenaria("q_laje_negativa_verga: %r" % (q_laje_linear_kN_m,))
    h_laje = float(h_laje_sobre_verga_m) if h_laje_sobre_verga_m is not None else h_ac
    laje_dentro = (q_laje > 0) and (h_laje <= h_arco + 1e-9)
    q_laje_cons = q_laje if laje_dentro else 0.0
    fk = fk_de_fpk(float(fpk), material)
    gm = gamma_alvenaria(combinacao, False, False)
    fd = fk / gm
    import math as _m
    # Altura por fiadas: 0,20 (1 fiada) e, se nao verificar, 0,30/0,40/0,60.
    # Verga de 0,20 que nao passa nao vira As maior que o teto (z negativa):
    # vira peca mais alta, dita no resultado. Altura declarada fixa nao escala.
    alturas = [hv_fixa] if hv_fixa is not None else [0.20, 0.30, 0.40, 0.60]
    melhor_falha = None
    for hv in alturas:
        q_pp = 25.0 * te * hv
        q_tot_k = q_parede + q_laje_cons + q_pp
        Md = float(gf) * q_tot_k * L * L / 8.0
        d = hv - COBRIMENTO_VERGA_M
        if not d > 0:
            raise EntradaAlvenaria("d_nao_positivo_verga: h=%.3f cobr=%.3f"
                                   % (hv, COBRIMENTO_VERGA_M))
        adotada = None
        ultima = None
        for phi in (6.3, 8.0, 10.0, 12.5):
            if phi_mm is not None and phi > float(phi_mm) + 1e-9:
                continue
            As = 2.0 * _m.pi * (phi / 1000.0) ** 2 / 4.0
            r = verifica_flexao_simples_1133(Md, As, te, d, fd, fyk, phi,
                                             bloco=bloco, ranhurado=ranhurado)
            ultima = (phi, As, r)
            if r["OK"]:
                adotada = (phi, As, r)
                break
        if adotada is None and phi_mm is not None:
            phi = float(phi_mm)
            As = 2.0 * _m.pi * (phi / 1000.0) ** 2 / 4.0
            r = verifica_flexao_simples_1133(Md, As, te, d, fd, fyk, phi,
                                             bloco=bloco, ranhurado=ranhurado)
            ultima = (phi, As, r)
            if r["OK"]:
                adotada = (phi, As, r)
        if adotada is not None:
            phi_ad, As_ad, res = adotada
            return {"OK": True,
                    "veredito": "aprovado",
                    "motivo": "",
                    "L_calculo_m": round(L, 3),
                    "comprimento_peca_m": round(comp_peca, 3),
                    "apoio_m": round(ap, 3),
                    "altura_verga_m": round(hv, 3),
                    "d_m": round(d, 3),
                    "h_arco_m": round(h_arco, 4),
                    "arco_formado": bool(arco),
                    "q_parede_kN_m": round(q_parede, 3),
                    "q_laje_kN_m": round(q_laje_cons, 3),
                    "laje_dentro_do_arco": bool(laje_dentro),
                    "q_pp_kN_m": round(q_pp, 3),
                    "q_total_k_kN_m": round(q_tot_k, 3),
                    "Md_kNm": round(Md, 3),
                    "phi_mm": phi_ad, "As_m2": As_ad,
                    "As_cm2": round(As_ad * 1e4, 3),
                    "armadura": "2x%.1f" % (phi_ad,),
                    "MRd_kNm": res["MRd_kNm"],
                    "fd_kN_m2": round(fd, 1), "fk_kN_m2": round(fk, 1),
                    "gamma_m": gm,
                    "peso_proprio_interno_kN": 0.0}
        phi_ad, As_ad, res = ultima
        melhor_falha = (hv, d, q_pp, q_tot_k, Md, phi_ad, As_ad, res)
    hv, d, q_pp, q_tot_k, Md, phi_ad, As_ad, res = melhor_falha
    return {"OK": False,
            "veredito": "reprovado",
            "motivo": ("verga_nao_passou_1133: Md=%.3f kNm acima do MRd com "
                       "2x%.1f em h=%.2f m (NBR 16868-1 11.3.3 com fyd da "
                       "Er1:2021)." % (Md, phi_ad, hv)),
            "L_calculo_m": round(L, 3),
            "comprimento_peca_m": round(comp_peca, 3),
            "apoio_m": round(ap, 3),
            "altura_verga_m": round(hv, 3),
            "d_m": round(d, 3),
            "h_arco_m": round(h_arco, 4),
            "arco_formado": bool(arco),
            "q_parede_kN_m": round(q_parede, 3),
            "q_laje_kN_m": round(q_laje_cons, 3),
            "laje_dentro_do_arco": bool(laje_dentro),
            "q_pp_kN_m": round(q_pp, 3),
            "q_total_k_kN_m": round(q_tot_k, 3),
            "Md_kNm": round(Md, 3),
            "phi_mm": phi_ad, "As_m2": As_ad,
            "As_cm2": round(As_ad * 1e4, 3),
            "armadura": "2x%.1f" % (phi_ad,),
            "MRd_kNm": res["MRd_kNm"],
            "fd_kN_m2": round(fd, 1), "fk_kN_m2": round(fk, 1),
            "gamma_m": gm,
            "peso_proprio_interno_kN": 0.0}


def confere_fronteira_peso(Nd_usado_kN, carga_via_6120_kN, tol_kN=1e-3):
    """DECLARACAO da fronteira peso (F21, molde G52) — CASO ISOLADO, triada G69.

    Lado A (Nd_usado_kN): o Nd que entrou na verificacao do elemento.
    Lado B (carga_via_6120_kN): a mesma carga pela via da carga
    (cargas_nbr6120.carga_linear_parede x comprimento), passada PRONTA por
    quem chama. Quando o chamador calcula os dois lados como q x L, os dois
    lados nascem da mesma expressao (D86): a igualdade pega transcricao
    (peso contado duas vezes ou nenhuma, GF misturado), nunca fisica nova.
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
    """DECLARACAO da fronteira peso para o CASO REAL (F21, G61), triada G69 (D86).

    Lado A (Nd_parede_kN): parcela isolada por linha de parede, na mesma base
    da carga via 6120. Quem chama ISOLA a parcela no resultado
    (estrutura_casa.dimensiona_alvenaria_portante calcula N_parede_k =
    q_parede x L, com q_parede = carga_linear_parede).
    Lado B (carga via 6120): recomputada AQUI DENTRO como
    carga_linear_parede(tipo, esp, altura, revestimento) x L.
    Os dois lados nascem da MESMA expressao (q x L, mesma tabela): a guarda
    concordaria consigo mesma com a parede errada — e' decorativa como
    CONFERENCIA do plano. Como DECLARACAO ela pega transcricao (L errado,
    GF de um lado so, revestimento com nome morto, parcela ausente) e por
    isso NAO pode ser apagada sem substituto (G69). A relacao independente
    do plano e' estrutura_casa.confere_simetria_quinhao via
    verifica_fechamento_alvenaria (G61): plano simetrico com quinhoes
    espelhados diferentes reprova mesmo com o total fechando.

    Nd_parede_kN: parcela isolada por linha de parede, na mesma base da
    carga via 6120 (caracteristica x caracteristica, ou calculo x calculo
    com o mesmo GF dos dois lados). Sem parcela isolavel a junta e
    inverificavel e o caso RECUSA.
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
        # G63: distribuicao 9.6.2 + 11.5 + Anexo C disponiveis; G67 fecha
        # a 11.4 e da origem ao vento (6123 por nivel).
        "flexo_compressao_11_5": "implemented",
        "parede_muito_esbelta_anexo_C": "implemented",
        "acao_horizontal_contraventamento": "implemented",
        "cisalhamento_11_4": "implemented",
        "vento_por_nivel_6123": "implemented",
        # G70: a verga desenhada ganha conta (11.3.3 com arco de descarga);
        # a contraverga segue detalhe construtivo declarado (nao peca de flexao).
        "verga_contraverga": "implemented",
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
            "G67: verifica_cisalhamento_114 (NBR 16868-1 11.4.1 + 11.4.2, "
            "tau_vd = Vd/(te.L) contra fvk/gamma_m com fvk da Tab.4 em "
            "6.2.2.6 por faixa de fa; parede armada ao cisalhamento "
            "(11.4.3, Va + Vs) segue fora com endereco).",
        "vento_por_nivel_6123":
            "G67: vento_fa_por_nivel (NBR 6123 4.2.3 Fa = Ca.q.Ae por "
            "nivel, Ca declarado do abaco da Fig.4, q via "
            "vento_nbr6123.s2_factor). Qh avulsa segue recusando.",
        "verga_contraverga":
            "G70: dimensiona_verga_1133 (NBR 16868-1 11.3.3 com fyd da "
            "Er1:2021): vao livre mais apoio, carga da parede acima com o "
            "arco de descarga a 45 graus (so o triangulo quando a parede "
            "chega para forma-lo, parede cheia quando nao chega) mais a "
            "parcela de laje que cair dentro do triangulo e o peso da "
            "canaleta; armadura 2 barras pela primeira bitola que verifica. "
            "A contraverga sob o peitoril e detalhe construtivo declarado "
            "(larg + 2 apoios x 0,10 m, 2x6.3): costura a fissuracao no "
            "canto do vao, nao peca calculada em flexao.",
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
    G67: o cisalhamento no plano (11.4, fvk da Tab.4) e o vento por nivel
    (NBR 6123 Fa = Ca.q.Ae) tambem."""
    return ("[ALVENARIA ESTRUTURAL (NBR 16868-1:2020+Er1:2021): vertical "
            "disponivel em alvenaria_estrutural (compressao 11.2, flexao "
            "11.3.3, flexo-compressao 11.5, cisalhamento 11.4, Anexo C e "
            "contraventamento 9.6.2 com flanges ate 6t na 10.1.3 — G63/G67; "
            "vento por nivel NBR 6123 4.2.3 Fa = Ca.q.Ae com Ca declarado; "
            "verga 11.3.3 com arco de descarga e contraverga como detalhe — "
            "G70); "
            "na casa portante o Nd da parede vem da laje (G61/G67) e a "
            "parede vira folha e BIM (G62).]")


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
    # G63: horizontal, 11.5 e Anexo C disponiveis; G67 fecha a 11.4 e o
    # vento por nivel.
    assert e["flexo_compressao_11_5"] == "implemented"
    assert e["parede_muito_esbelta_anexo_C"] == "implemented"
    assert e["acao_horizontal_contraventamento"] == "implemented"
    assert e["cisalhamento_11_4"] == "implemented"
    assert e["vento_por_nivel_6123"] == "implemented"
    assert "11.4" in motivos_escopo()["cisalhamento_11_4"]
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
    # G67: 11.4 — fvk da Tab.4 por faixa de fa, tau = Vd/(te.L) <= fvk/gm.
    f1 = fvk_caracteristico_6226(2.0, 0.39)
    assert abs(f1["fvk_MPa"] - min(0.10 + 0.5 * 0.39, 1.0)) < 1e-9
    f2 = fvk_caracteristico_6226(5.0, 0.39)
    assert abs(f2["fvk_MPa"] - min(0.15 + 0.5 * 0.39, 1.4)) < 1e-9
    f3 = fvk_caracteristico_6226(8.0, 0.39)
    assert abs(f3["fvk_MPa"] - min(0.35 + 0.5 * 0.39, 1.7)) < 1e-9
    r114 = verifica_cisalhamento_114(10.0, 60.0, 0.14, 2.40, 5.0)
    assert r114["OK"] is True
    assert abs(r114["tau_vd_kN_m2"] - 10.0 / (0.14 * 2.40)) < 1e-3
    assert abs(r114["VRd_kN"] - r114["fvd_kN_m2"] * 0.14 * 2.40) < 1e-2
    assert r114["peso_proprio_interno_kN"] == 0.0
    # G67: vento por nivel — Fa = Ca.q.Ae com q do s2 homologado.
    import vento_nbr6123 as _vt67
    w = vento_fa_por_nivel(2, 2.7, 8.0,
                           {"v0": 40.0, "cat": "II", "classe": "B",
                            "ca": 1.0})
    assert len(w["niveis"]) == 2
    assert abs(w["F_total_kN"] - sum(v["Fa_kN"] for v in w["niveis"])) < 1e-6
    _b, _fr, _p, _s2 = _vt67.s2_factor("II", "B", 5.4)
    _q = 0.613 * (40.0 * _s2) ** 2 / 1000.0
    assert w["niveis"][1]["q_kN_m2"] == round(_q, 4)
    assert w["niveis"][1]["Fa_kN"] == round(1.0 * _q * 8.0 * 2.7 / 2.0, 3)
    # linha de memorial: fonte unica, sem motivo congelado
    lin = linha_memorial_cadeia_gravitacional()
    assert "16868-1:2020" in lin and "Er1:2021" in lin
    assert "G61" in lin and "G63" in lin and "G67" in lin
    # G70: verga 11.3.3 com arco + contraverga detalhe + cruzamento unico.
    assert e["verga_contraverga"] == "implemented"
    assert "arco" in motivos_escopo()["verga_contraverga"]
    import cargas_nbr6120 as _cg70
    _peso70 = _cg70.peso_alvenaria("bloco_concreto_estrutural", 14.0, 2.0)
    # arco formado: parede alta desvia a laje (q_laje fora do triangulo).
    v1 = dimensiona_verga_1133(0.9, 0.6, _peso70, q_laje_linear_kN_m=3.0,
                               h_laje_sobre_verga_m=0.6, fpk=4000.0,
                               material="bloco", te_m=0.14)
    assert v1["OK"] and v1["arco_formado"] is True
    assert v1["q_laje_kN_m"] == 0.0 and v1["laje_dentro_do_arco"] is False
    assert v1["comprimento_peca_m"] == round(0.9 + 2.0 * APOIO_VERGA_M, 3)
    assert v1["L_calculo_m"] == round(0.9 + APOIO_VERGA_M, 3)
    # sem altura para o arco: parede cheia + laje dentro (contra a seguranca
    # ignorar a laje aqui).
    v2 = dimensiona_verga_1133(1.2, 0.3, _peso70, q_laje_linear_kN_m=3.0,
                               h_laje_sobre_verga_m=0.3, fpk=4000.0,
                               material="bloco", te_m=0.14)
    assert v2["OK"] and v2["arco_formado"] is False
    assert v2["q_laje_kN_m"] == 3.0 and v2["laje_dentro_do_arco"] is True
    assert v2["q_parede_kN_m"] == round(_peso70 * 0.3, 3)
    # sem arco a conta explode (superdimensionada); o arco declarado reduz.
    assert v2["q_parede_kN_m"] > v1["q_parede_kN_m"] - 1.0
    dc70 = detalhe_contraverga(1.2)
    assert dc70["calculada_113"] is False and "fissura" in dc70["motivo"]
    assert dc70["comprimento_m"] == round(1.2 + 2.0 * APOIO_CONTRAVERGA_M, 3)
    assert recuo_cruzamento(0.14) == 0.07
    assert comprimento_liquido_y(8.0, 3, 0.14) == round(8.0 - 2 * 0.14, 4)
    assert comprimento_liquido_y(4.0, 2, 0.14) == round(4.0 - 0.14, 4)
    assert "comprimento_liquido_y" in CONVENCAO_CRUZAMENTOS
    print("alvenaria_estrutural self-test PASSED")
    return True


if __name__ == "__main__":
    _selftest()
