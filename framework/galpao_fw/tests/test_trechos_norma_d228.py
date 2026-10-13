# ============================================================================
# test_trechos_norma_d228.py - TRECHOS LITERAIS DAS NORMAS NO MEMORIAL (D228).
# O texto de cada trecho e' recortado do acervo por ferramenta
# (tools/gera_trechos_norma.py); aqui se confere a estrutura, o casamento com as
# secoes do memorial e que os numeros que o motor usa estao no trecho citado.
# ============================================================================
"""Trechos de norma citados no memorial de calculo."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_nbr8800
import galpao_portico as gp
import ligacoes
import relatorio_calculo as RC
import solda_perfil_chapa
import trechos_norma as T


def _trecho(item):
    achados = [t for t in T.TRECHOS if t["item"] == item]
    assert len(achados) == 1, item
    return achados[0]["texto"]


def test_todo_trecho_tem_norma_item_e_texto():
    for t in T.TRECHOS:
        assert t["norma"].startswith("ABNT NBR ") and t["edicao_id"].startswith("ed_")
        assert t["item"] and t["lido_no_item"] and len(t["texto"]) > 30
        assert "Todos os direitos reservados" not in t["texto"]     # rodape de pagina


def test_toda_secao_citada_existe_no_memorial():
    # as chaves sao prefixos dos titulos que rodar_galpao escreve no consolidado
    titulos = ("1. VENTO", "1b. VENTO LONGITUDINAL", "2. PORTICO 1a ORDEM", "4. PERFIS",
               "12b. SOLDA DO PERFIL NA CHAPA")
    for t in T.TRECHOS:
        assert any(tit.upper().startswith(t["secao"].upper()) for tit in titulos), t["secao"]
    assert len(T.da_secao("1. VENTO")) == 7 and T.da_secao("9. VERGA DA PORTA") == []
    # "1. VENTO" nao pode puxar os trechos de "1b. VENTO LONGITUDINAL" nem o contrario
    assert all(t["secao"] == "1b. VENTO LONGITUDINAL" for t in T.da_secao("1b. VENTO LONGITUDINAL"))


def test_numeros_do_motor_estao_no_trecho_citado():
    assert "q = 0,613 Vk²" in _trecho("4.2 c)")
    assert "cpi = +0,2" in _trecho("6.3.2.1 a)") and "cpi = -0,3" in _trecho("6.3.2.1 a)")
    assert "cpi = +0,8" in _trecho("6.3.2.1 c)")
    assert "H/300" in _trecho("B.3, Tabela B.1")
    assert "não podem ser incluídas nas combinações" in _trecho("4.8.6.2, Tabela 1, nota a")
    assert "C0_grav" in gp._combos_elu()                 # a combinacao que a nota a pede
    assert "χ A_ef f_y/γ_a1" in _trecho("5.3.2")
    assert "E = 200 000 MPa" in _trecho("4.6.2.9") and check_nbr8800.E == 200e6
    assert "G = 77 000 MPa" in _trecho("4.6.2.9") and check_nbr8800.G_ACO == 77e6
    assert "| 485" in _trecho("A.4, Tabela A.4") and solda_perfil_chapa.FW_E70 == 485e3


@pytest.mark.parametrize("t_mm, perna", [(6.3, "3 mm"), (12.5, "5 mm"), (19.0, "6 mm"), (19.1, "8 mm")])
def test_perna_minima_do_motor_e_a_da_tabela_citada(t_mm, perna):
    tabela = _trecho("6.2.6.2.1")
    linha = {"3 mm": "Abaixo de 6,3 e até 6,3 mm | 3 mm", "5 mm": "Acima de 6,3 até 12,5 mm | 5 mm",
             "6 mm": "Acima de 12,5 até 19 mm | 6 mm", "8 mm": "Acima de 19 mm | 8 mm"}[perna]
    assert linha in tabela
    assert ligacoes.solda_filete_minimo(t_mm) == float(perna.split()[0])


def test_memorial_em_pdf_traz_os_trechos(tmp_path):
    import pymupdf
    corpo = ["#" * 70, "1. VENTO", "#" * 70, "", "VENTO (ABNT NBR 6123:2023)\n  q = 1,066 kN/m2", "", "",
             "#" * 70, "12b. SOLDA DO PERFIL NA CHAPA", "#" * 70, "", "ADOTADA: filete de 10 mm", "", ""]
    (tmp_path / "MEMORIAL-CONSOLIDADO.txt").write_text("GALPAO DE TESTE\n\n" + "\n".join(corpo),
                                                       encoding="utf-8")
    pdf = RC.gerar_pdf(str(tmp_path))
    texto = " ".join(" ".join(p.get_text().split()) for p in pymupdf.open(pdf))
    assert "TRECHOS DA NORMA" in texto
    assert "ABNT NBR 6123:2023, 4.2 c)" in texto and "0,613" in texto
    assert "ABNT NBR 8800:2024/Er1:2025, 6.2.6.2.1" in texto and "Acima de 19 mm" in texto
