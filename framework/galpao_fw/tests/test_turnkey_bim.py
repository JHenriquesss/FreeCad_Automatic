"""BIM/IFC FEDERADO do turnkey: emitir_bim(R, out_dir, spec) escreve um IFC por
disciplina (frame nativo) + turnkey_federado.ifc (concreto transformado + eletrico +
incendio no frame comum). Camada pura (transform/contagem) em CI; a emissao IFC roda
so com ifcopenshell. O aco sai por pipeline proprio (arquivo separado)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_turnkey as tk
import ifc_emit


def _spec():
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                     "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                     "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3, "sigma_solo_adm": 250.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}],
                                "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0}},
    }


# ------------------------------- camada PURA (CI) ----------------------------
def test_transform_concreto_para_frame_comum():
    # barra: [x,y,z] -> [y, x + vao/2*1000, z]; vao=20 -> dy=10000
    m = {"tipo": "Column", "marca": "P1E", "p1": [-5000.0, 0.0, 0.0],
         "p2": [-5000.0, 0.0, 6000.0]}
    out = tk._concreto_no_frame_comum([m], 20.0)[0]
    assert out["p1"] == [0.0, 5000.0, 0.0]              # X_comum=Y_conc ; Y_comum=x+10000
    assert out["p2"] == [0.0, 5000.0, 6000.0]
    assert out["marca"] == "C-P1E"                      # prefixo de disciplina
    # caixa (sapata): dims de planta trocam B<->L (rotacao 90)
    f = {"tipo": "Footing", "marca": "S1", "dims": [1200.0, 1800.0, 400.0],
         "centro": [-5000.0, 0.0, -200.0]}
    of = tk._concreto_no_frame_comum([f], 20.0)[0]
    assert of["dims"] == [1800.0, 1200.0, 400.0]
    assert of["centro"] == [0.0, 5000.0, -200.0]


def test_membros_federados_reune_as_tres_disciplinas():
    R = tk.rodar(_spec())
    membros, disc = tk._membros_federados(R)
    assert set(disc) == {"concreto", "eletrico", "incendio"}      # sem aco no _spec()
    marcas = [m["marca"][0] for m in membros]
    assert "C" in marcas and "E" in marcas and "I" in marcas      # concreto/eletrico/incendio
    # federado = soma dos membros_bim das tres disciplinas executadas
    import galpao_concreto as gc, galpao_eletrico as ge, galpao_seguranca_incendio as gi
    dd = R["disciplinas"]
    esperado = (len(gc.membros_bim(dd["concreto"]["raw"]))
                + len(ge.membros_bim(dd["eletrico"]["raw"]))
                + len(gi.membros_bim(dd["incendio"]["raw"])))
    assert len(membros) == esperado


def test_federado_footprint_coerente():
    # apos a transformacao, concreto e instalacoes ocupam o MESMO footprint XY [0..comp]x[0..vao]
    R = tk.rodar(_spec())
    membros, _ = tk._membros_federados(R)
    def _xy(m):
        pts = [m["p1"], m["p2"]] if "p1" in m else [m["centro"]]
        return pts
    conc = [p for m in membros if m["marca"].startswith("C-") for p in _xy(m)]
    xs = [p[0] for p in conc]; ys = [p[1] for p in conc]
    assert min(xs) >= 0.0 and max(xs) <= 40000.0 + 1     # X = comprimento [0..40 m]
    assert min(ys) >= 0.0 and max(ys) <= 20000.0 + 1     # Y = largura [0..20 m]


# ------------------------- emissao IFC (gated no ifcopenshell) ---------------
@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_emitir_bim_gera_pasta_e_federado(tmp_path):
    R = tk.rodar(_spec())
    man = tk.emitir_bim(R, str(tmp_path), spec=_spec())
    # um IFC por disciplina de contrato membros_bim
    for disc in ("concreto", "eletrico", "incendio"):
        assert os.path.exists(man["arquivos"][disc])
    # sem 'aco' no spec: nem arquivo nem nota de aco (a nota so aparece quando ha aco)
    assert "aco" not in man["arquivos"] and man["nota_aco"] is None
    # federado com as tres disciplinas
    assert set(man["disciplinas_federadas"]) == {"concreto", "eletrico", "incendio"}
    assert os.path.exists(man["federado"]) and os.path.getsize(man["federado"]) > 0
    import ifcopenshell
    m = ifcopenshell.open(man["federado"])
    assert m.schema == "IFC4"
    assert len(m.by_type("IfcColumn")) >= 2                  # pilares de concreto
    assert len(m.by_type("IfcFireSuppressionTerminal")) >= 1  # chuveiros/hidrantes
    assert len(m.by_type("IfcCableCarrierSegment")) == 1     # eletrocalha


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_emitir_bim_sem_spec_aco_nota(tmp_path):
    spec = _spec(); spec["aco"] = {"qualquer": 1}
    R = tk.rodar(spec)                                       # aco pulado (sem out_dir no rodar)
    man = tk.emitir_bim(R, str(tmp_path))                    # sem spec -> nao emite aco.ifc
    assert man["nota_aco"] and "aco.ifc nao gerado" in man["nota_aco"]


# spec de aco JA ENRIQUECIDO (perfis adotados) -> membros_do_spec funciona sem calculo,
# entao o federado inclui o aco pelo fallback spec['aco'] (mesmo frame, sem transformar).
_ACO_ENRIQUECIDO = {
    "slug": "aco_fed", "geometria": {"span": 20.0, "comprimento": 28.5, "eave": 8.0,
                                     "ridge": 9.5, "bay": 5.7},
    "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180"},
}


def test_aco_federa_no_frame_comum_via_spec_enriquecido():
    spec = dict(_spec()); spec["aco"] = _ACO_ENRIQUECIDO
    R = tk.rodar(spec)                                   # aco pulado (sem out_dir), mas...
    membros, disc = tk._membros_federados(R, spec)       # ...federa pelo spec['aco'] enriquecido
    assert "aco" in disc
    aco = [m for m in membros if m["marca"].startswith("A-")]
    assert aco, "aco deveria contribuir membros ao federado"
    # aco ja no frame comum (modelo_neutro X=comprimento[0..], Y=vao[0..]): X e Y >= 0.
    # (paineis de fechamento usam 'poligono' e nao entram nesta checagem de eixo.)
    checou = 0
    for m in aco:
        pts = [m["p1"], m["p2"]] if "p1" in m else ([m["centro"]] if "centro" in m else [])
        for (x, y, z) in pts:
            assert x >= -1 and y >= -1, (x, y)           # sem centrar em 0 (nao e' concreto)
            checou += 1
    assert checou > 0


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_federado_com_aco_tem_estrutura_de_aco(tmp_path):
    spec = dict(_spec()); spec["aco"] = _ACO_ENRIQUECIDO
    man = tk.emitir_bim(tk.rodar(spec), str(tmp_path), spec=spec)
    assert "aco" in man["disciplinas_federadas"]
    import ifcopenshell
    m = ifcopenshell.open(man["federado"])
    # portico de aco: colunas + rafters (IfcColumn/IfcBeam/IfcMember) no MESMO arquivo
    assert len(m.by_type("IfcColumn")) >= 2
    assert len(m.by_type("IfcBeam")) + len(m.by_type("IfcMember")) >= 2
    assert os.path.exists(man["arquivos"]["aco"])       # e o aco.ifc standalone tambem


def test_emitir_bim_sem_ifcopenshell(monkeypatch, tmp_path):
    # sem ifcopenshell, retorna erro limpo (nao levanta)
    monkeypatch.setattr(ifc_emit, "disponivel", lambda: False)
    man = tk.emitir_bim(tk.rodar(_spec()), str(tmp_path))
    assert "erro" in man and "ifcopenshell" in man["erro"]
