# ============================================================================
# marcas_peca.py - MARCAS DE PECA (piece marks) para fabricacao.
# Modulo PURO (sem FreeCAD) -> testavel headless E importavel como irmao dentro
# do FreeCAD (build_galpao o usa via sys.path do _ship_build_src). Uma marca por
# grupo (categoria, perfil): prefixo por categoria + numero por perfil distinto
# dentro do prefixo. Galpao tipico: 1 perfil/categoria -> C1, V1, T1...
# ============================================================================
"""Marcas de peca (piece marks) - agrupamento por (categoria, perfil)."""

from __future__ import annotations

# 1o match por substring da categoria (ordem importa: mais especifico antes).
PREFIXO_MARCA = [
    ("Colunas", "C"), ("Vigas de baldrame", "BD"), ("Vigas", "V"),
    ("Escoras", "E"), ("Montantes", "M"), ("Tercas de parede", "TP"),
    ("Tercas", "T"), ("Contraventamento", "CV"), ("Tirantes", "TR"),
    ("Mao-francesa do console", "MC"), ("Maos-francesas", "MF"),
    ("Viga de rolamento", "VR"), ("Consoles", "CS"), ("Trelica", "TL"),
    ("Sapatas", "S"), ("Pedestais", "P"), ("Estacas", "ES"), ("Blocos", "BL"),
    ("Placas de base", "PB"), ("Nervuras da base", "NB"), ("Chumbadores", "CH"),
    ("Arruelas", "AR"), ("Porcas de nivel", "PL"), ("Porcas", "PN"),
    ("Chapas gusset", "G"), ("Esticadores", "ET"), ("Calhas", "CL"),
    ("Condutores", "CD"), ("Bocais", "BC"), ("Telha", "TH"), ("Tapamento", "TA"),
    ("Vergas", "VG"), ("Clipes", "CP"), ("Misulas", "MI"), ("Chapa de topo", "CT"),
    ("Chapa console", "CC"), ("Parafusos", "PF"), ("Enrijecedor", "EN"),
    ("Alvenaria", "ALV"),
]


def prefixo_marca(cat):
    """Prefixo da marca para uma categoria (1o match por substring)."""
    for chave, pref in PREFIXO_MARCA:
        if chave in cat:
            return pref
    return "X"


def mapa_marcas(grupos):
    """Atribui uma MARCA a cada grupo (cat, perfil): prefixo por categoria +
    numero por perfil distinto dentro do prefixo. `grupos` = iteravel de (cat,
    perfil). Retorna {(cat, perfil): marca}. Deterministico (ordena os grupos)."""
    grupos = list(grupos)
    contadores, por_prefixo = {}, {}
    for (cat, prof) in sorted(grupos):
        pref = prefixo_marca(cat)
        d = por_prefixo.setdefault(pref, {})
        if prof not in d:
            contadores[pref] = contadores.get(pref, 0) + 1
            d[prof] = "%s%d" % (pref, contadores[pref])
    return {(cat, prof): por_prefixo[prefixo_marca(cat)][prof]
            for (cat, prof) in grupos}


def _selftest():
    grupos = [("Colunas", "HEA200"), ("Vigas", "HEA180"), ("Tercas", "Ue200"),
              ("Tercas de parede", "Ue150"), ("Colunas", "HEA240")]
    m = mapa_marcas(grupos)
    assert m[("Colunas", "HEA200")].startswith("C")
    assert m[("Vigas", "HEA180")] == "V1"
    assert m[("Tercas", "Ue200")] == "T1"
    assert m[("Tercas de parede", "Ue150")] == "TP1"    # nao confunde com Tercas
    # 2 perfis de coluna -> C1 e C2 distintos
    assert {m[("Colunas", "HEA200")], m[("Colunas", "HEA240")]} == {"C1", "C2"}
    # mesmo grupo -> mesma marca (deterministico)
    assert mapa_marcas(grupos) == m
    # categoria desconhecida -> prefixo X
    assert mapa_marcas([("Coisa nova", "z")])[("Coisa nova", "z")] == "X1"
    print("marcas_peca _selftest PASSED")


if __name__ == "__main__":
    _selftest()
