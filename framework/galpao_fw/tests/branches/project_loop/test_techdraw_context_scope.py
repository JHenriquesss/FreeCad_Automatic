from types import SimpleNamespace
import inspect

import techdraw_exec as TD


def _obj(label):
    return SimpleNamespace(Label=label)


def test_contexto_mantem_estrutura_principal_e_exclui_detalhes():
    objetos = [
        _obj("PORTICO_01_C00"),
        _obj("VAO_01_CUMEEIRA_S00"),
        _obj("TERCA_BEIRAL_E"),
        _obj("TELHA_01"),
        _obj("CALHA_01"),
        _obj("BOCAL_01"),
        _obj("CONDUTOR_01"),
        _obj("CONTRAV_COBERTURA_01"),
        _obj("CONEX_GUSSET_COB_01"),
        _obj("CHUMBADOR_C00_01"),
        _obj("PORCA_C00_01"),
        _obj("ARRUELA_C00_01"),
        _obj("CLIPE_GIRT_E_01"),
    ]

    resultado = TD._contexto(objetos)

    assert [o.Label for o in resultado] == [
        "PORTICO_01_C00",
        "VAO_01_CUMEEIRA_S00",
        "TERCA_BEIRAL_E",
        "TELHA_01",
        "CALHA_01",
        "BOCAL_01",
        "CONDUTOR_01",
        "CONTRAV_COBERTURA_01",
    ]
    assert resultado is not objetos


def test_vistas_gerais_usam_fontes_de_contexto_reduzidas():
    for fn in (TD._pr_cobertura, TD._pr_elevacoes):
        assert "_contexto(objs)" in inspect.getsource(fn)


def test_cobertura_incompleta_nao_e_aprovada():
    assert TD._cobertura_ok({"nao_cobertos": []}) is True
    assert TD._cobertura_ok({"nao_cobertos": ["CONDUTOR"]}) is False
