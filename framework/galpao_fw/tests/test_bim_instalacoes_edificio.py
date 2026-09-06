"""G53: instalacoes com geometria no mesmo frame da estrutura + clash do furo."""
import json
from pathlib import Path

import bim_edificio as bim
import bim_instalacoes_edificio as bie
import edificio_multipavimento as em
import eletrica_edificio as ee
import hidraulica_edificio as he
import incendio_edificio as ie


_CACHE = {}


def _caso():
    if _CACHE:
        return _CACHE["R"], _CACHE["H"], _CACHE["E"], _CACHE["I"]
    spec = json.loads((Path(__file__).parents[3] / "projects" /
                       "edificio-multipavimento" / "project-spec.json"
                       ).read_text(encoding="utf-8"))
    tk = spec["turnkey"]
    est_spec = {"geometria": tk["estrutura"]["geometria"],
                "pavimentos": tk["estrutura"]["pavimentos"],
                "materiais": tk["estrutura"]["materiais"],
                "laje": tk["estrutura"].get("laje"),
                "viga": tk["estrutura"].get("viga"),
                "vento": tk["estrutura"].get("vento"),
                "fundacao": tk["estrutura"].get("fundacao"),
                "escada": tk["estrutura"].get("escada")}
    R = em.rodar(est_spec)
    from edificio_adapter import _contexto_predio
    ctx0 = _contexto_predio(tk["estrutura"], R, None)
    I = ie.dimensiona(tk["incendio"], ctx0)
    ctx = _contexto_predio(
        tk["estrutura"], R,
        {"incendio": {"populacao_por_pavimento": I["populacao_por_pavimento"]}})
    H = he.dimensiona(tk["hidraulica"], ctx)
    E = ee.dimensiona(tk["eletrico"], ctx)
    _CACHE.update({"R": R, "H": H, "E": E, "I": I})
    return R, H, E, I


def test_mesmo_frame_e_prefixo_por_disciplina():
    R, H, E, I = _caso()
    mest = bim.membros_bim(R)
    fed, disc = bie.membros_federados_edificio(
        R, {"hidraulica": H, "eletrico": E, "incendio": I})
    assert "estrutura" in disc and "hidraulica" in disc
    assert "eletrico" in disc and "incendio" in disc
    # so a estrutura ja tem N pecas; o federado acrescenta sem remover nenhuma
    assert len(fed) > len(mest)
    # marcas prefixadas por disciplina, como o federado do galpao
    assert any(m["marca"].startswith("C-") for m in fed)
    assert any(m["marca"].startswith("P-") for m in fed)
    assert any(m["marca"].startswith("E-") for m in fed)
    assert any(m["marca"].startswith("I-") for m in fed)
    # DNs lidos do calculo, nao arbitrados
    agua = next(m for m in fed if m["marca"] == "P-H-AGUA-PRU")
    assert abs(agua["secao"]["D"] * 1000 - H["coluna"]["dn"]["DN_mm"]) < 1e-6


def test_clash_acha_o_furo_que_a_viga_nao_tem():
    R, H, E, I = _caso()
    rep = bie.checa_interferencia_edificio(
        R, {"hidraulica": H, "eletrico": E, "incendio": I})
    assert rep["n_clashes"] > 0
    # eletrocalha horizontal cruza viga VY na altura da nervura -> furo na viga
    vigas = [c for c in rep["clashes"] if "BeamxCableCarrier" in c["tipos"]]
    assert vigas, "eletrocalha deveria furar viga"
    # prumada vertical fura laje
    lajes = [c for c in rep["clashes"] if "SlabxPipe" in c["tipos"]]
    assert lajes, "prumada deveria furar laje"
    # so clash ENTRE disciplinas
    for c in rep["clashes"]:
        da, db = c["disciplinas"].split("x")
        assert da != db


def test_sem_disciplina_sem_peca():
    R, H, E, _I = _caso()
    fed, disc = bie.membros_federados_edificio(
        R, {"hidraulica": H, "eletrico": E})
    assert "incendio" not in disc
    assert not any(m["marca"].startswith("I-") for m in fed)


def test_escopo_publica_tracado():
    assert he._escopo(False)["tracado_das_prumadas"] == "implemented"
    assert ee._escopo(False)["tracado_e_prumadas_reais"] == "implemented"
