# ============================================================================
# test_dossie_pranchas_ifc_d230.py - O DOSSIE LEVA AS PRANCHAS QUE A CORRIDA
# GRAVOU. Antes do D230 so' entravam as PE*.pdf do FreeCAD: corrida sem
# FreeCAD e com as pranchas do IFC (Bonsai) saia com "faltando: pranchas",
# e as folhas ficavam so' na pasta ao lado.
# ============================================================================
"""Dossie: pranchas do FreeCAD ou, sem elas, as do IFC."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

fitz = pytest.importorskip("fitz")

import dossie as D

SPEC = {"slug": "t", "descricao": "teste", "geometria": {"comprimento": 20, "span": 10}}


def _pdf(caminho, texto, paginas=1):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    doc = fitz.open()
    for i in range(paginas):
        doc.new_page(width=842, height=595).insert_text((50, 80), "%s p%d" % (texto, i + 1))
    doc.save(caminho)
    doc.close()
    return caminho


def _textos(caminho):
    with fitz.open(caminho) as d:
        return [p.get_text() for p in d]


def test_sem_pe_do_freecad_entram_as_folhas_do_ifc_declaradas_no_spec(tmp_path):
    out = str(tmp_path)
    folhas = [_pdf(os.path.join(out, "pranchas-ifc", "pdf", "EST-%02d.pdf" % k), "FOLHA-IFC-%d" % k)
              for k in (2, 1)]
    spec = dict(SPEC, estrutura={"pranchas_ifc": {"pdf": folhas}})
    r = D.gerar_dossie(out, spec, relatorio="VEREDITO: ATENDE")
    assert r["n_pranchas"] == 2 and r["origem_pranchas"] == "IFC"
    assert not [f for f in r["faltando"] if "pranchas" in f]
    paginas = _textos(r["path"])
    assert r["n_paginas"] == len(paginas)
    # as duas folhas fecham o dossie, na ordem do nome
    assert "FOLHA-IFC-1" in paginas[-2] and "FOLHA-IFC-2" in paginas[-1]


def test_folha_do_ifc_no_disco_entra_mesmo_sem_o_spec_declarar(tmp_path):
    out = str(tmp_path)
    _pdf(os.path.join(out, "pranchas-ifc", "pdf", "EST-01.pdf"), "FOLHA-IFC")
    r = D.gerar_dossie(out, dict(SPEC), relatorio="x")
    assert r["n_pranchas"] == 1 and r["origem_pranchas"] == "IFC"
    assert "FOLHA-IFC" in _textos(r["path"])[-1]


def test_pdf_declarado_que_nao_existe_nao_conta(tmp_path):
    out = str(tmp_path)
    spec = dict(SPEC, estrutura={"pranchas_ifc": {
        "pdf": [os.path.join(out, "pranchas-ifc", "pdf", "sumiu.pdf")]}})
    r = D.gerar_dossie(out, spec, relatorio="x")
    assert r["n_pranchas"] == 0 and r["origem_pranchas"] is None
    assert any("pranchas (nenhuma" in f for f in r["faltando"])


def test_pe_do_freecad_tem_precedencia_e_as_do_ifc_nao_duplicam(tmp_path):
    out = str(tmp_path)
    _pdf(os.path.join(out, "pranchas", "PE01.pdf"), "FOLHA-PE")
    _pdf(os.path.join(out, "pranchas-ifc", "pdf", "EST-01.pdf"), "FOLHA-IFC")
    r = D.gerar_dossie(out, dict(SPEC), relatorio="x")
    assert r["n_pranchas"] == 1 and r["origem_pranchas"] == "FreeCAD"
    tudo = "\n".join(_textos(r["path"]))
    assert "FOLHA-PE" in tudo and "FOLHA-IFC" not in tudo


def test_corrida_de_pranchas_que_nao_gravou_pdf_segue_faltando(tmp_path):
    spec = dict(SPEC, estrutura={"pranchas_ifc": {"gerado": True, "nao_gerado": {
        "pdf": "Inkscape nao encontrado"}}})
    r = D.gerar_dossie(str(tmp_path), spec, relatorio="x")
    assert r["n_pranchas"] == 0 and any("pranchas (nenhuma" in f for f in r["faltando"])
