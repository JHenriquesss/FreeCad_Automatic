"""G122 - as diferencas 2014 -> 2023 pre-Emenda, secao a secao.

Medido: F016 (2014, texto extraivel) x F150 decodificada G117/G120 (641190
bytes, desconhecidos={'0BD8': 188} declarado); confronto secao a secao nas
45 familias que o framework cita; diferenca de texto so vira veredito com
imagem das duas edicoes (8.2.5/8.2.8 p.23-24, 15.4.2 p.103, 15.7.2/15.7.3
p.106, 18.2.3/18.2.4 p.146-147, todas lidas em 200 dpi). Este goal NAO troca
base normativa de modulo nenhum.

Entregue:
  1. LENTE (confronto_2014_2023_g122.py, fonte unica): CONFRONTO_G122 (45) +
     FAMILIAS_G122 + MODULOS_POR_FAMILIA + cobre_inventario (cada OK chega
     ao veredito global - contra saturacao silenciosa) + caso C5 que chama
     a funcao REAL (premoldado_nbr9062._fctm para 2014; a prescricao literal
     da 2023 para o novo numero - contra assercao tautologica).
  2. PORTAO (test_01): o inventario wiki real cobre as 45 + modulos +
     enderecos das divergentes.
  3. BASELINE (test_02, nos dois sentidos): 45 familias congeladas; cada
     familia num item so; divergentes = 1 NUMERO-MUDA (8.2.5) + 3
     REGRA-MUDA/EDITORIAL com imagem (8.2.8/15.7.2/15.4.2/15.7.3/18.2.4).
  4. INJECAO (test_03, tmp_path, nunca o repo): familia ou modulo removido
     = vermelho (o acumulador faltando_* dispara); intacto = verde.
  5. CASOS (test_04): C5 fctm C60 4,300 (2014, funcao real) vs 4,355 MPa
     (2023, prescricao), +1,3%.

O que a lente NAO cobre: clausulas que o framework nao cita; miolo de
formulas/tabelas/figuras (limite declarado por familia, ver imagem); a
migracao em si (decisao do usuario, G123).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import confronto_2014_2023_g122 as lente

INVENTARIO = os.path.join(GALPAO, "wiki",
                          "07-nbr6118-2023-em1-impacto-g116.md")


def test_01_portao_inventario_real_cobre_tudo():
    """Um assert so: as 45 familias, os modulos citados e os enderecos das
    divergentes estao no inventario wiki real."""
    with open(INVENTARIO, encoding="utf-8") as f:
        texto = f.read()
    r = lente.cobre_inventario(texto)
    faltas = (["fam:" + k for k in r["faltando_familias"]]
              + ["mod:" + k for k in r["faltando_modulos"]]
              + ["end:" + k for k in r["sem_endereco"]])
    assert r["ok"] and not faltas, "inventario nao cobre: %r" % faltas


def test_02_baseline_tamanhos_nos_dois_sentidos():
    """Baseline congelado: 45 familias; vereditos disjuntos; divergentes com
    endereco; limites de formula/tabela declarados."""
    quebras = []
    if len(lente.FAMILIAS_G122) != 45:
        quebras.append("familias=%d, esperado 45" % len(lente.FAMILIAS_G122))
    if len(lente.CONFRONTO_G122) != 45:
        quebras.append("confronto=%d, esperado 45" % len(lente.CONFRONTO_G122))
    ids = [f for f, _v, _d, _p, _m in lente.CONFRONTO_G122]
    if len(set(ids)) != 45:
        quebras.append("familias duplicadas no confronto")
    if set(ids) != set(lente.FAMILIAS_G122):
        quebras.append("FAMILIAS_G122 != chaves do CONFRONTO (dois sentidos)")
    vers = {}
    for _f, v, _d, _p, _m in lente.CONFRONTO_G122:
        vers[v] = vers.get(v, 0) + 1
        if v not in ("IGUAL", "EDITORIAL", "REGRA-MUDA", "NUMERO-MUDA"):
            quebras.append("veredito invalido: %r" % v)
    if vers.get("NUMERO-MUDA", 0) != 1:
        quebras.append("NUMERO-MUDA=%s, esperado 1 (8.2.5)"
                       % vers.get("NUMERO-MUDA", 0))
    # cada divergente tem modulo + pagina de imagem anotada
    for fam, ver, _det, pag, mods in lente.CONFRONTO_G122:
        if ver in ("NUMERO-MUDA", "REGRA-MUDA") and not mods:
            quebras.append("divergente sem modulo: %s" % fam)
        if ver in ("NUMERO-MUDA", "REGRA-MUDA") and not pag:
            quebras.append("divergente sem pagina-imagem: %s" % fam)
    assert not quebras, "baseline quebrou:\n" + "\n".join(quebras)


def test_03_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: familia ou modulo removido dao vermelho (o
    acumulador faltando_* dispara de verdade); o texto intacto da verde."""
    with open(INVENTARIO, encoding="utf-8") as f:
        texto = f.read()
    base = lente.cobre_inventario(texto)
    assert base["ok"] is True
    # acumulador de familias dispara: remove a linha da 8.2.5
    sem_fam = texto.replace("8.2.5", "FAMILIA REMOVIDA")
    r1 = lente.cobre_inventario(sem_fam)
    assert r1["ok"] is False
    assert r1["faltando_familias"], "acumulador faltando_familias nao disparou"
    # acumulador de modulos dispara: remove um modulo citado
    sem_mod = texto.replace("premoldado_nbr9062", "MODULO REMOVIDO")
    r2 = lente.cobre_inventario(sem_mod)
    assert r2["ok"] is False
    assert r2["faltando_modulos"], "acumulador faltando_modulos nao disparou"
    # acumulador de enderecos dispara: apaga os .py: das divergentes
    sem_end = texto.replace(".py:", "PY SEM ENDERECO")
    r3 = lente.cobre_inventario(sem_end)
    assert r3["ok"] is False
    assert r3["sem_endereco"], "acumulador sem_endereco nao disparou"
    copia = str(tmp_path / "inventario.txt")
    with open(copia, "w", encoding="utf-8") as f:
        f.write(texto)
    with open(copia, encoding="utf-8") as f:
        assert lente.cobre_inventario(f.read())["ok"] is True


def test_04_caso_fctm_c60_mesmo_caso_nas_duas_regras():
    """Um assert so: o caso C5 chama a funcao real e da os numeros
    congelados (2014 < 2023, +1,3%)."""
    quebras = []
    c5 = lente.caso_c5_fctm_c60()
    if abs(c5["fctm_2014_MPa"] - 4.300) > 0.005:
        quebras.append("C5 2014=%.4f, esperado 4,300"
                       % c5["fctm_2014_MPa"])
    if abs(c5["fctm_2023_MPa"] - 4.355) > 0.005:
        quebras.append("C5 2023=%.4f, esperado 4,355"
                       % c5["fctm_2023_MPa"])
    if not (c5["fctm_2023_MPa"] > c5["fctm_2014_MPa"]):
        quebras.append("C5: 2023 devia superar 2014")
    assert not quebras, "caso divergiu:\n" + "\n".join(quebras)


def test_05_conta_da_8_2_5_x_inventario_consegue_acusar(tmp_path):
    """G125 (auditoria do G122): o item NUMERO-MUDA listava 6 modulos e a
    formula C55+ morava em 10 (mais o desenho_piso, que so cita). A lente
    procura a CONTA, nao a citacao, e acusa nos dois sentidos; o endereco
    da divergente e cobrado na linha da familia, nao em qualquer lugar."""
    quebras = []
    real = lente.confere_sites_8_2_5()
    if not real["OK"]:
        quebras.append("arvore real: %r" % real)
    if len(real["sites"]) != 10:
        quebras.append("sites da formula=%d, esperado 10: %r"
                       % (len(real["sites"]), sorted(real["sites"])))
    # modulo novo com a conta, fora do inventario -> nao_inventariados
    (tmp_path / "modulo_novo.py").write_text(
        "import math" + chr(10)
        + "fctm = 2.12 * math.log(1.0 + 0.11 * 60.0)" + chr(10),
        encoding="utf-8")
    novo = lente.confere_sites_8_2_5(str(tmp_path))
    if "modulo_novo" not in novo["nao_inventariados"]:
        quebras.append("conta fora do inventario nao acusou: %r" % novo)
    # nenhum modulo do item tem a conta neste diretorio -> sem_formula
    if len(novo["sem_formula"]) != 10 or novo["OK"]:
        quebras.append("item sem a conta nao acusou: %r" % novo)
    # conta so em comentario nao e conta
    (tmp_path / "modulo_novo.py").write_text(
        "# fctm = 2.12 * math.log(1.0 + 0.11 * fck)" + chr(10),
        encoding="utf-8")
    if lente.sites_formula_fctm(str(tmp_path)):
        quebras.append("comentario contou como conta")
    # endereco apagado SO na linha da 8.2.5 -> sem_endereco, mesmo com
    # outros ".py:" no texto (antes um endereco qualquer satisfazia tudo)
    with open(INVENTARIO, encoding="utf-8") as f:
        texto = f.read()
    linhas = [l.replace(".py:", "_py") if l.startswith("- 8.2.5 |") else l
              for l in texto.split(chr(10))]
    sem_825 = chr(10).join(linhas)
    r = lente.cobre_inventario(sem_825)
    if ".py:" not in sem_825 or r["sem_endereco"] != ["8.2.5"] or r["ok"]:
        quebras.append("endereco da 8.2.5 apagado nao acusou: %r"
                       % r["sem_endereco"])
    assert not quebras, "G125:" + chr(10) + chr(10).join(quebras)

