# ============================================================================
# test_pecas_conexao_encaixe.py - pecas de CONEXAO nao podem ocupar o mesmo
# espaco que a peca em que se apoiam.
#
# POR QUE ESTA CLASSE ESCAPA: `checa_interferencia` EXCLUI pecas de conexao
# (_e_secundario / _compartilha_no). Elas nunca aparecem na contagem de clash,
# entao um clipe 60% enterrado ou dois esticadores no mesmo ponto passavam
# batido indefinidamente. Estes testes sao a rede que falta.
#
# ACHADOS DA VARREDURA (interpenetracao medida peca a peca no modelo da amostra):
#
#  1) PORCA DE NIVEL 100% dentro do PEDESTAL. O gap de graute estava DECLARADO
#     (GROUT_GAP=30) mas nao realizado: `z_ped_top = pbot` punha o concreto
#     encostado na face inferior da placa. A porca de nivel tem 28 mm - alguem a
#     dimensionou justamente para caber nos 30 mm do gap - e ficava enterrada no
#     concreto, impossivel de regular e errada na prancha de base.
#       antes: concreto -570..-70, placa -70..30, gap = 0
#       depois: concreto -600..-100, placa -70..30, gap = 30,0 mm exatos
#
#  2) DOIS ESTICADORES NO MESMO ESPACO. As duas diagonais de um X se cruzam no
#     meio, e o esticador ia sempre em frac=0,5: as duas mangas tinham bounding
#     box IDENTICA (115.236 mm3 de volume comum). Impossivel de montar.
#       depois: volume comum 0, 5,8 m de distancia, cada um sobre a sua barra.
#
#  3) GUSSET DE PAREDE 60,7% dentro da ESCORA DE BEIRAL. A chapa nascia no no do
#     beiral e descia; a escora (HEA_ESC) e centrada em EAVE_H, entao 115 dos
#     150 mm da chapa ficavam dentro dela.
#       depois: gusset 7735..7885, escora 7885..8115 - encosta (dist 0,00),
#       0 mm3 comum, e a diagonal continua chegando na chapa.
#
# CONTINUAM EMBUTIDAS DE PROPOSITO (nao sao bug): gancho do chumbador dentro do
# pedestal (100%), fuste do chumbador atravessando placa e concreto, porca
# rosqueada no chumbador, enrijecedor de joelho dentro do pilar, manga do
# esticador em volta da sua propria barra.
# ============================================================================
import ast
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

BUILD_SRC = os.path.join(GALPAO, "build_galpao.py")


@pytest.fixture(scope="module")
def src():
    return open(BUILD_SRC, encoding="utf-8").read()


# ---- 1) gap de graute -----------------------------------------------------
def test_topo_do_concreto_desce_o_gap_de_graute(src):
    assert "z_conc_top = pbot - GROUT_GAP" in src
    codigo = [l for l in src.splitlines() if not l.lstrip().startswith("#")]
    cru = r"=\s*pbot(?!\s*-\s*GROUT_GAP)"      # pbot "pelado", sem descontar o gap
    assert not [l for l in codigo if re.search(r"z_ped_top\s*" + cru, l)], (
        "pedestal voltou a encostar na face inferior da placa")
    assert not [l for l in codigo if re.search(r"z_bal_top\s*" + cru, l)], (
        "baldrame voltou a encostar na face inferior da placa")


def test_as_tres_fundacoes_usam_a_mesma_cota(src):
    """Sapata, estaca e baldrame tem que concordar sobre onde o concreto acaba."""
    assert "z_ped_top = z_conc_top" in src                 # sapata
    assert "_desenha_estaca(doc, x, yw, z_conc_top" in src  # estaca
    assert "z_bal_top = pbot - GROUT_GAP" in src            # baldrame


def test_estaca_recebe_a_cota_do_concreto_nao_a_da_placa(src):
    arv = ast.parse(src)
    fn = next(n for n in arv.body
              if isinstance(n, ast.FunctionDef) and n.name == "_desenha_estaca")
    assert "z_conc_top" in [a.arg for a in fn.args.args], (
        "o parametro ainda se chama pbot - nome mente sobre o que recebe")


def test_porca_de_nivel_cabe_no_gap(src):
    """A porca (28 mm) tem que caber no gap de graute, senao volta a enterrar."""
    import importlib.util
    gap = float(re.search(r"^GROUT_GAP\s*=\s*([\d.]+)", src, re.M).group(1))
    alt = float(re.search(r"pbot - ([\d.]+)\), \(ax, ay, pbot\), pod", src).group(1))
    assert alt <= gap, "porca de nivel (%.0f mm) nao cabe no gap (%.0f mm)" % (alt, gap)


# ---- 2) esticadores -------------------------------------------------------
def test_esticador_aceita_posicao_ao_longo_da_barra(src):
    arv = ast.parse(src)
    fn = next(n for n in arv.body
              if isinstance(n, ast.FunctionDef) and n.name == "_esticador")
    assert "frac" in [a.arg for a in fn.args.args]


def test_as_duas_diagonais_nao_usam_a_mesma_fracao(src):
    """frac=0,5 nos dois punha as mangas no mesmo espaco (o cruzamento do X)."""
    assert re.search(r"^FRAC_ESTIC = ", src, re.M)
    ns = {}
    exec(re.search(r"^FRAC_ESTIC = .*$", src, re.M).group(0), ns)
    assert ns["FRAC_ESTIC"] != 0.5, "voltou ao meio: as duas mangas se sobrepoem"
    assert 0.0 < ns["FRAC_ESTIC"] < 1.0


def test_todos_os_quatro_esticadores_declaram_a_fracao(src):
    """2 na cobertura + 2 em cada parede; A e B sempre complementares."""
    chamadas = re.findall(r"_esticador\(doc, \*(\w+), f\"[^\"]+\", frac=([^)]+)\)", src)
    assert len(chamadas) == 4, chamadas
    fracs = [c[1].strip() for c in chamadas]
    assert fracs.count("FRAC_ESTIC") == 2
    assert fracs.count("1.0 - FRAC_ESTIC") == 2


# ---- 3) gusset de parede x escora de beiral -------------------------------
def test_gusset_superior_nasce_abaixo_da_escora(src):
    assert "z_top_gus = EAVE_H - HEA_ESC[0] / 2.0" in src
    codigo = [l for l in src.splitlines() if not l.lstrip().startswith("#")]
    assert not [l for l in codigo
                if re.search(r"\(x[01], EAVE_H, \(-?1, 0, 0\), \(0, 0, -1\)\)", l)], (
        "gusset superior voltou a nascer no no do beiral, dentro da escora")


def test_tag_do_gusset_nao_depende_mais_da_cota(src):
    """O nome vinha de `'B' if nz < EAVE_H else 'T'`; agora TODO nz < EAVE_H,
    entao a tag tem que ser explicita ou todos virariam 'B'."""
    assert "'B' if nz < EAVE_H else 'T'" not in src
    assert '(x0, z_top_gus, (1, 0, 0), (0, 0, -1), "T")' in src


def test_fonte_compila(src):
    ast.parse(src)
