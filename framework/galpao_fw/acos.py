# ============================================================================
# acos.py - CLASSES DE ACO ESTRUTURAL (fy, fu)
# ----------------------------------------------------------------------------
# FONTE (nao de memoria): Pfeil & Pfeil, "Estruturas de aco - dimensionamento
# pratico de acordo com a NBR 8800", Cap. 1 (pesquisa/aço/...pdf, pag. 33 do PDF):
#
#   "os acos podem ser enquadrados nas seguintes categorias, designadas a partir
#    do limite de escoamento do aco fy:
#      MR250,      aco de media resistencia (fy = 250 MPa; fu = 400 MPa)
#      AR350,      aco de alta resistencia (fy = 350 MPa; fu = 450 MPa)
#      AR-COR 415, aco de alta resistencia (fy = 415 MPa; fu = 520 MPa),
#                  resistente a corrosao.
#    O aco MR250 corresponde ao aco ASTM A36."
#
# ASTM A572 Gr50 (fy 345 / fu 450) vem da Tabela 1.1 do mesmo capitulo (acos de
# baixa liga) - e o aco do exemplo do Manual CBCA que validacao.py reproduz.
#
# POR QUE ESTE MODULO EXISTE: fy vinha de PARAMS_REF["fy"]=250e3 e fu estava
# LITERAL (400e3) no rodar_galpao. Todo projeto saia em MR250 sem o engenheiro
# poder escolher, e uma classe so com fy deixaria as LIGACOES com o fu errado
# (fu entra em ruptura da secao liquida, block shear e pressao de contato).
# Classe = par (fy, fu); nunca so fy.
# ============================================================================
"""Classes de aco estrutural (fy, fu em kPa). Fonte: Pfeil, NBR 8800 Cap.1."""

from __future__ import annotations

# nome -> (fy_kPa, fu_kPa, observacao)
ACOS = {
    "MR250":      (250e3, 400e3, "media resistencia (= ASTM A36)"),
    "A572-G50":   (345e3, 450e3, "ASTM A572 Gr50, baixa liga"),
    "AR350":      (350e3, 450e3, "alta resistencia (ABNT)"),
    "AR-COR415":  (415e3, 520e3, "alta resistencia, resistente a corrosao"),
}
PADRAO = "MR250"


def normaliza(nome):
    """Aceita variacoes de escrita ('ar 350', 'A572 G50') -> chave canonica."""
    if nome is None:
        return None
    k = str(nome).strip().upper().replace(" ", "").replace("_", "-")
    if k in ACOS:
        return k
    equiv = {"A36": "MR250", "ASTMA36": "MR250", "MR-250": "MR250",
             "A572G50": "A572-G50", "A572": "A572-G50", "ASTMA572G50": "A572-G50",
             "AR-350": "AR350", "ARCOR415": "AR-COR415", "AR-COR-415": "AR-COR415"}
    return equiv.get(k.replace("-", "")) or equiv.get(k)


def propriedades(nome):
    """(fy, fu) em kPa da classe. Levanta se desconhecida - NAO adivinha: um aco
    errado muda a resistencia de TODA a estrutura."""
    k = normaliza(nome)
    if k is None:
        raise ValueError(
            "classe de aco desconhecida: %r. Conhecidas: %s"
            % (nome, ", ".join(sorted(ACOS))))
    fy, fu, _ = ACOS[k]
    return fy, fu


def nome_por_fy(fy_kPa):
    """Designacao a partir do fy (p/ o carimbo). Sem correspondencia declara o
    valor - nao inventa designacao comercial."""
    for k, (fy, _fu, _o) in ACOS.items():
        if abs(fy - fy_kPa) < 1.0:
            return k
    return "fy=%d MPa" % round(fy_kPa / 1000.0)


def descricao(nome):
    k = normaliza(nome) or PADRAO
    fy, fu, obs = ACOS[k]
    return "%s (fy=%d MPa, fu=%d MPa) - %s" % (k, fy / 1000, fu / 1000, obs)


def _selftest():
    assert propriedades("MR250") == (250e3, 400e3)
    assert propriedades("a572 g50") == (345e3, 450e3)
    assert normaliza("AR 350") == "AR350"
    assert nome_por_fy(250e3) == "MR250"
    assert nome_por_fy(300e3) == "fy=300 MPa"     # nao inventa
    try:
        propriedades("AR300")                     # nao existe (erro que ja cometi)
    except ValueError:
        pass
    else:
        raise AssertionError("AR300 nao deveria existir")
    print("acos self-test PASSED:", ", ".join(sorted(ACOS)))


if __name__ == "__main__":
    _selftest()
