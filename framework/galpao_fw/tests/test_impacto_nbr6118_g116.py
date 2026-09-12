"""G116 - o impacto de migrar a NBR 6118 de 2014 para 2023 + Emenda 1.

Medido: F098 (Emenda 1:2026, 23 pags, texto legivel) traz 85 cabecalhos de
instrucao agrupados em 51 itens; F016 (2014, texto extraivel) e F150
decodificada no G117 dao o antes/depois; 2014 = 2023 pre-Em1 nas clausulas de
intersecao sondadas, menos a 15.7.3 (paragrafo do galpao e novidade da edicao
2023). O framework calcula pela 2014 e este goal NAO troca base nenhuma.

Entregue:
  1. LENTE (impacto_nbr6118_g116.py, fonte unica): ITENS_EM1 (51) +
     CABECALHOS_EM1 (85) + CAB_PARA_ITEM (particao congelada) + FAMILIAS_FW
     (45, do grep 6118/17.3/15.8) + cobre_inventario (cada OK chega ao
     veredito global - contra a saturacao silenciosa) + 4 casos que chamam as
     funcoes REAIS (compatibilizacao, puncao, pilar, premoldado) sem alterar
     modulo nenhum (contra assercao tautologica: o numero 2014 vem da funcao
     real; o 2023+Em1 e a prescricao literal da Emenda).
  2. PORTAO (test_01): o inventario wiki real cobre os 85 + 45 + modulos.
  3. BASELINE (test_02, nos dois sentidos): 85/51/45 congelados + particao
     exata (cada cabecalho num item so; todo item com >= 1).
  4. INJECAO (test_03, tmp_path, nunca o repo): cabecalho ou familia
     removida = vermelho; intacto = verde.
  5. CASOS (test_04): C1 furo125 a_confirmar/divergente-conservador; C2
     colapso OK nas duas + lacuna C''; C3 lambda210 conforme; C4 fckj C60
     41032 vs 49124 kN/m2.

O que a lente NAO cobre: 2014 -> 2023 fora da Emenda (menos 15.7.3);
figuras/tabelas (so a prosa); a migracao em si (decisao do usuario).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import impacto_nbr6118_g116 as lente

INVENTARIO = os.path.join(GALPAO, "wiki",
                          "07-nbr6118-2023-em1-impacto-g116.md")


def test_01_portao_inventario_real_cobre_tudo():
    """Um assert so: os 85 cabecalhos, as 45 familias e os modulos citados
    estao no inventario wiki real."""
    with open(INVENTARIO, encoding="utf-8") as f:
        texto = f.read()
    r = lente.cobre_inventario(texto)
    faltas = (["cab:" + k for k, v in r["cabecalhos"].items() if not v]
              + ["fam:" + k for k, v in r["familias"].items() if not v]
              + ["mod:" + k for k, v in r["modulos"].items() if not v])
    assert r["ok"] and not faltas, "inventario nao cobre: %r" % faltas


def test_02_baseline_tamanhos_e_particao_nos_dois_sentidos():
    """Baseline congelado: 85 cabecalhos, 51 itens, 45 familias; cada
    cabecalho num item so; todo item com >= 1; destinos sao itens validos."""
    quebras = []
    if len(lente.CABECALHOS_EM1) != 85:
        quebras.append("cabecalhos=%d, esperado 85"
                       % len(lente.CABECALHOS_EM1))
    if len(lente.ITENS_EM1) != 51:
        quebras.append("itens=%d, esperado 51" % len(lente.ITENS_EM1))
    if len(lente.FAMILIAS_FW) != 45:
        quebras.append("familias=%d, esperado 45" % len(lente.FAMILIAS_FW))
    ids = {i for i, _r, _n, _f, _v, _d in lente.ITENS_EM1}
    if len(lente.CAB_PARA_ITEM) != 85:
        quebras.append("mapa=%d, esperado 85" % len(lente.CAB_PARA_ITEM))
    for cab in lente.CABECALHOS_EM1:
        if cab not in lente.CAB_PARA_ITEM:
            quebras.append("cabecalho sem item: %r" % cab)
    for cab, item in lente.CAB_PARA_ITEM.items():
        if cab not in lente.CABECALHOS_EM1:
            quebras.append("mapa cita cabecalho fora do congelado: %r" % cab)
        if item not in ids:
            quebras.append("mapa cita item inexistente: %r" % item)
    sem = sorted(ids - set(lente.CAB_PARA_ITEM.values()))
    if sem:
        quebras.append("itens sem cabecalho: %r" % sem)
    assert not quebras, "baseline quebrou:\n" + "\n".join(quebras)


def test_03_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: cabecalho ou familia removida dao vermelho;
    o texto intacto da verde. A lente e chamada de verdade."""
    with open(INVENTARIO, encoding="utf-8") as f:
        texto = f.read()
    assert lente.cobre_inventario(texto)["ok"] is True
    sem_cab = texto.replace("Pagina 75, 13.2.5.1-b)", "PAGINA REMOVIDA")
    assert lente.cobre_inventario(sem_cab)["ok"] is False
    sem_fam = texto.replace("Tab.A.1", "TABELA REMOVIDA")
    assert lente.cobre_inventario(sem_fam)["ok"] is False
    copia = str(tmp_path / "inventario.txt")
    with open(copia, "w", encoding="utf-8") as f:
        f.write(texto)
    with open(copia, encoding="utf-8") as f:
        assert lente.cobre_inventario(f.read())["ok"] is True


def test_04_casos_efeito_mesmo_caso_nas_duas_regras():
    """Um assert so: os 4 casos chamam funcao real e dao os numeros
    congelados (C1/C4 divergem, C2/C3 estabilizam)."""
    quebras = []
    c1 = lente.caso_c1_furo_circular()
    if c1["veredito_2014"] != "a_confirmar":
        quebras.append("C1 2014=%r, esperado a_confirmar"
                       % c1["veredito_2014"])
    if c1["dispensavel_2023_em1"] is not True:
        quebras.append("C1 2023+Em1 devia dispensar")
    c2 = lente.caso_c2_colapso()
    if c2["ok_2014"] is not True:
        quebras.append("C2 2014 devia passar (numero igual nas duas)")
    c3 = lente.caso_c3_lambda_pouco_comprimido()
    if c3["admite_baixo"] is not True:
        quebras.append("C3 nu=0,05 devia admitir pela ressalva")
    if c3["reprova_alto"] is not True:
        quebras.append("C3 nu=0,50 devia reprovar em 15.8.1")
    c4 = lente.caso_c4_fckj_c60()
    if abs(c4["fckj_2014_kNm2"] - 41032) > 1.0:
        quebras.append("C4 2014=%.1f, esperado 41032"
                       % c4["fckj_2014_kNm2"])
    if abs(c4["fckj_2023_em1_kNm2"] - 49124) > 1.0:
        quebras.append("C4 2023+Em1=%.1f, esperado 49124"
                       % c4["fckj_2023_em1_kNm2"])
    if not (c4["fckj_2023_em1_kNm2"] > c4["fckj_2014_kNm2"]):
        quebras.append("C4: 2023+Em1 devia superar 2014 (s 0,20 < 0,38)")
    assert not quebras, "casos divergiram:\n" + "\n".join(quebras)
