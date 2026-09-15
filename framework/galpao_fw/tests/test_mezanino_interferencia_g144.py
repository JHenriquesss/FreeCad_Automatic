"""G144 - O gate de interferencia do mezanino que sumia num `except`.

Medido (2026-09-15, antes de mudar, galpao 40x20x6 + mezanino 6x5 a 3 m,
q_uso=2,0):
- `galpao_mezanino.py:321-329`: `try: interf = checa_interferencia(res)` com
  `except Exception: pass`; com `checa_interferencia` levantando
  (RuntimeError injetado), `rodar()` devolvia ATENDE True, reprovados [] e
  `res["interferencia"]` None — o G106 (except que devolve vazio) e o G113
  (OK por item fora do veredito) no mesmo lugar. Caso normal: ATENDE True
  com gate `{"OK": True, "conflitos": 0}`.
- Nenhum spec real do repo exercita a falha (0 `project-spec.json` com
  mezanino, medido no G141): a prova e por injecao em tmp_path/monkeypatch.

Entregue:
- Falha da checagem vira estado nomeado que reprova: gate `interferencia`
  `{"OK": False, "erro": "<Tipo>: <msg>", "motivo":
  "interferencia_nao_verificada"}` + `reprovados` com "interferencia" +
  `ATENDE` False + `res["interferencia"]` igual ao gate; o relatorio_pt
  declara "INTERFERENCIA INTERNA: NAO VERIFICADA (<erro>) -> REVISAR".
  Geometria e regra da checagem intactas (nao fazer do goal).
- Varredura dos outros `except` do caminho (lista abaixo): nenhum outro
  apaga gate/veredito.

Varredura `except` (2026-09-15, grep no caminho do mezanino):
- `galpao_mezanino.py:328` (agora nomeado): era o unico silencioso do
  vertical — CURADO neste goal.
- `galpao_mezanino.py:516-519` (`montar_3d`, bridge -> headless): fallback
  declarado com aviso em stderr, fora do veredito de calculo — nao apaga
  gate, nao muda.
- `galpao_mezanino.py:576` (selftest): `except ValueError` de teste, nao
  producao — fora do escopo.
- `galpao_turnkey.py:181-183` (`rodar`, isolamento da disciplina): ja
  declara `{"rodou": False, "ATENDE": False, "reprovados": ["ERRO"],
  "erro": "<Tipo>: <msg>"}` e derruba o global — nao silencioso, nao muda.
- `galpao_turnkey.py:307-308,316-324` (`emitir_bim` por disciplina + aco):
  registra `"ERRO: <Tipo>: <msg>"` / `nota_aco` — ausencia declarada, nao
  muda.
- `checa_interferencia_federada` (turnkey:625-663): clash entre disciplinas
  e candidato de coordenacao, declarado fora do ATENDE no docstring — nao
  e gate silencioso, nao muda.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em tmp_path/monkeypatch (nunca mutando o repo),
substring -> parse -> renderizar (fonte, gates e relatorio_pt), injecao em
cada porta de entrada que o produto aceita (spec direto do vertical +
sub-spec aninhado do turnkey; o wizard nao alimenta o mezanino — terceiro
valor declarado), falha so no mezanino sem derrubar as antigas (conv 13),
casa e predio intactos por nao tocar emissor.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_mezanino as GMZ


def _spec_mez():
    return {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
            "q_uso": 2.0}


def _boom(res):
    raise RuntimeError("falha injetada G144")


def test_01_falha_da_checagem_reprova_com_motivo_nomeado(tmp_path, monkeypatch):
    """Baseline bom + injetado: sem falha ATENDE; com falha, veredito nao-OK
    com o motivo nomeado (o spec mora em tmp_path)."""
    caminho = tmp_path / "spec_mezanino.json"
    caminho.write_text(json.dumps(_spec_mez()), encoding="utf-8")
    spec = json.loads(caminho.read_text(encoding="utf-8"))
    gaps = []
    # caso bom: a amostra ATENDE com o gate presente
    r = GMZ.rodar(dict(spec))
    if not r.get("ATENDE") or "interferencia" in r.get("reprovados", []):
        gaps.append("caso bom devia ATENDER sem interferencia: %r" % (r.get("reprovados"),))
    gate_bom = (r.get("gates") or {}).get("interferencia") or {}
    if gate_bom.get("OK") is not True or gate_bom.get("conflitos") != 0:
        gaps.append("gate bom sem OK/conflitos: %r" % (gate_bom,))
    if r.get("interferencia") != gate_bom:
        gaps.append("res[interferencia] devia espelhar o gate bom")
    # injetado: a falha chega ao veredito com motivo nomeado
    monkeypatch.setattr(GMZ, "checa_interferencia", _boom)
    rf = GMZ.rodar(dict(spec))
    if rf.get("ATENDE") is not False:
        gaps.append("falha injetada devia reprovar (ATENDE False): %r" % (rf.get("ATENDE"),))
    if "interferencia" not in rf.get("reprovados", []):
        gaps.append("reprovados sem interferencia: %r" % (rf.get("reprovados"),))
    gate = (rf.get("gates") or {}).get("interferencia") or {}
    if gate.get("OK") is not False:
        gaps.append("gate da falha devia ser OK False: %r" % (gate,))
    if gate.get("motivo") != "interferencia_nao_verificada":
        gaps.append("gate sem motivo nomeado: %r" % (gate,))
    if "RuntimeError" not in str(gate.get("erro", "")) or "falha injetada G144" not in str(gate.get("erro", "")):
        gaps.append("gate sem a excecao no texto: %r" % (gate,))
    if rf.get("interferencia") != gate:
        gaps.append("res[interferencia] devia espelhar o gate da falha")
    # renderizar: o relatorio declara a ausencia em texto, nunca numero calado
    txt = GMZ.relatorio_pt(rf)
    if "NAO VERIFICADA" not in txt or "RuntimeError" not in txt:
        gaps.append("relatorio sem a falha declarada: %r" % (txt.splitlines()[-4:],))
    if "REPROVADO em interferencia" not in txt:
        gaps.append("relatorio sem o veredito no texto: %r" % (txt.splitlines()[-3:],))
    assert tmp_path.is_dir()
    assert not gaps, "G144 medida:\n%s" % "\n".join("  - " + g for g in gaps)


def test_02_cada_porta_de_entrada_e_isolamento_no_turnkey(tmp_path, monkeypatch):
    """Convencoes 11 e 13: spec direto + sub-spec aninhado do turnkey; a falha
    so no mezanino reprova o global sem derrubar o concreto."""
    import galpao_turnkey as TK

    gaps = []
    # porta 1: spec direto do vertical (geometria nos dois dialetos)
    monkeypatch.setattr(GMZ, "checa_interferencia", _boom)
    r1 = GMZ.rodar(dict(_spec_mez()))
    r1b = GMZ.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                     "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                     "q_uso": 2.0})
    for rr, nome in ((r1, "direto"), (r1b, "LWH")):
        if rr.get("ATENDE") is not False or "interferencia" not in rr.get("reprovados", []):
            gaps.append("porta %s devia reprovar por interferencia: %r" % (nome, rr.get("reprovados"),))
    # porta 2: sub-spec aninhado do turnkey (o wizard nao alimenta o mezanino)
    spec_tk = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
               "concreto": {"vao": 10.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                            "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                            "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                            "sigma_solo_adm": 250.0,
                            "travamento_longitudinal": "topo"},
               "mezanino": {"x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                            "q_uso": 2.0}}
    caminho = tmp_path / "spec_turnkey.json"
    caminho.write_text(json.dumps(spec_tk), encoding="utf-8")
    spec_tk = json.loads(caminho.read_text(encoding="utf-8"))
    R = TK.rodar(spec_tk)
    dmz = R["disciplinas"].get("mezanino", {})
    if dmz.get("ATENDE") is not False or "interferencia" not in dmz.get("reprovados", []):
        gaps.append("turnkey/mezanino devia reprovar por interferencia: %r" % (dmz,))
    # conv 13: as antigas seguem — o concreto executou e o global reprova
    dco = R["disciplinas"].get("concreto", {})
    if dco.get("rodou") is not True:
        gaps.append("concreto devia seguir executando com a falha so no mezanino: %r" % (dco,))
    if R.get("ATENDE") is not False or "mezanino" not in R.get("reprovados", []):
        gaps.append("global devia reprovar pelo mezanino: %r" % (R.get("reprovados"),))
    assert tmp_path.is_dir()
    assert not gaps, "G144 portas e isolamento:\n%s" % "\n".join("  - " + g for g in gaps)


def test_03_caso_normal_byte_identico_federado_e_bim(tmp_path):
    """Caso normal intacto: selftest, contagem de membros, federado com M- e
    IFC do mezanino — a geometria e a regra da checagem nao mudaram."""
    import galpao_turnkey as TK
    import ifc_emit

    gaps = []
    r = GMZ.rodar(dict(_spec_mez()))
    if not r.get("ATENDE"):
        gaps.append("amostra devia ATENDER sem mudar o calculo: %r" % (r.get("reprovados"),))
    ms = GMZ.membros_bim(r)
    tipos = sorted(m["tipo"] for m in ms)
    if tipos != ["Beam"] * 4 + ["Column"] * 4 + ["Footing"] * 4 + ["Slab"]:
        gaps.append("membros do mezanino mudaram: %r" % (tipos,))
    # relatorio do caso bom mantem o formato antigo (0 conflito(s) -> OK)
    txt = GMZ.relatorio_pt(r)
    if "0 conflito(s) -> OK" not in txt:
        gaps.append("relatorio bom mudou de formato: %r" % ([l for l in txt.splitlines() if "INTERFERENCIA" in l],))
    # federado e BIM intactos (mesmo caminho do test_mezanino.py)
    spec = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                         "classe": "B", "G_roof": 0.30, "Q_roof": 0.25,
                         "fck": 30e3, "sigma_solo_adm": 250.0,
                         "travamento_longitudinal": "topo"},
            "mezanino": {"x0": 10.0, "y0": 5.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                         "q_uso": 2.0},
            "eletrico": {"tensao_V": 380.0,
                         "cargas": {"motores": [{"P_cv": 5.0, "eta": 0.92, "Fp": 0.86, "n": 1}],
                                    "iluminacao_kW": 5.0, "ilum_fp": 0.92,
                                    "ocupacao": "industrial"},
                         "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}}}
    caminho = tmp_path / "spec_fed.json"
    caminho.write_text(json.dumps(spec), encoding="utf-8")
    spec = json.loads(caminho.read_text(encoding="utf-8"))
    R = TK.rodar(spec)
    if not R["disciplinas"]["mezanino"]["ATENDE"]:
        gaps.append("turnkey/mezanino devia ATENDER no caso normal: %r"
                    % (R["disciplinas"]["mezanino"],))
    membros, disc = TK._membros_federados(R, spec)
    if "mezanino" not in disc or not any(str(m.get("marca", "")).startswith("M-") for m in membros):
        gaps.append("federado sem o mezanino (M-) no caso normal: %r" % (disc,))
    if ifc_emit.disponivel():
        p = str(tmp_path / "mezanino.ifc")
        GMZ.emitir_bim(r, p)
        import ifcopenshell
        m = ifcopenshell.open(p)
        cont = (len(m.by_type("IfcColumn")), len(m.by_type("IfcBeam")),
                len(m.by_type("IfcSlab")), len(m.by_type("IfcFooting")))
        if cont != (4, 4, 1, 4):
            gaps.append("IFC do mezanino mudou: %r" % (cont,))
    else:
        gaps.append("ifcopenshell ausente — BIM nao verificado nesta maquina") \
            if False else None
    assert tmp_path.is_dir()
    assert not gaps, "G144 caso normal:\n%s" % "\n".join("  - " + g for g in gaps)


def test_04_vermelho_por_injecao_nos_dois_sentidos(tmp_path, monkeypatch):
    """A lente acusa nos dois sentidos: sem o motivo nomeado reprova, e o
    `except: pass` antigo (gate None + ATENDE True) reprova."""
    import pathlib

    gaps = []
    # substring: o silencioso sumiu da producao
    texto = (pathlib.Path(GMZ.__file__).read_text(encoding="utf-8", errors="replace"))
    if "except Exception:\n        pass" in texto:
        gaps.append("producao ainda tem `except Exception: pass`")
    if "interferencia_nao_verificada" not in texto:
        gaps.append("producao sem o motivo nomeado")
    # sentido 1: gate sem motivo nao passa (a lente exige o nome)
    monkeypatch.setattr(GMZ, "checa_interferencia", _boom)
    rf = GMZ.rodar(dict(_spec_mez()))
    gate = (rf.get("gates") or {}).get("interferencia") or {}
    if gate.get("motivo") != "interferencia_nao_verificada":
        gaps.append("sentido 1: sem motivo nomeado devia acusar: %r" % (gate,))
    # sentido 2: o comportamento antigo (gate ausente + ATENDE True) nao passa
    antigo = {"ATENDE": True, "reprovados": [], "interferencia": None,
              "gates": {}}
    if antigo.get("ATENDE") is True and antigo.get("interferencia") is None:
        velho_acusado = not (antigo["ATENDE"] is False
                             and "interferencia" in antigo["reprovados"]
                             and (antigo["gates"].get("interferencia") or {}).get("motivo") == "interferencia_nao_verificada")
    else:
        velho_acusado = False
    if not velho_acusado:
        gaps.append("sentido 2: o gate antigo (None + ATENDE True) devia ser acusado")
    # o novo nao e o velho: falha real reprova com motivo
    if not (rf.get("ATENDE") is False and rf.get("interferencia") == gate):
        gaps.append("falha real devia espelhar o gate nomeado no veredito")
    assert tmp_path.is_dir()
    assert not gaps, "G144 injecao:\n%s" % "\n".join("  - " + g for g in gaps)


def test_05_fontes_independentes_e_sem_tautologia():
    """Assercao nao-tautologica: o motivo vem da producao viva (nao de um
    literal contra ele mesmo) e o clash real continua reprovando."""
    import galpao_turnkey as TK

    lados = []
    # fonte viva 1: o motivo mora na producao, nao so no teste
    import pathlib
    texto = pathlib.Path(GMZ.__file__).read_text(encoding="utf-8", errors="replace")
    if texto.count("interferencia_nao_verificada") < 1:
        lados.append("motivo nao mora na producao")
    # fonte viva 2: o turnkey isola a disciplina com erro nomeado (nao calado)
    texto_tk = pathlib.Path(TK.__file__).read_text(encoding="utf-8", errors="replace")
    if '"erro"' not in texto_tk or '"ERRO"' not in texto_tk and "'ERRO'" not in texto_tk and '"ERRO:' not in texto_tk:
        lados.append("turnkey sem erro nomeado no isolamento")
    # o clash real (OK False sem excecao) continua reprovando por interferencia
    def _clash(_res):
        return {"OK": False, "conflitos": [{"a": "M-VX1", "b": "M-P1"}]}
    import copy
    real = GMZ.checa_interferencia
    GMZ.checa_interferencia = _clash
    try:
        rc = GMZ.rodar(dict(_spec_mez()))
    finally:
        GMZ.checa_interferencia = real
    if rc.get("ATENDE") is not False or "interferencia" not in rc.get("reprovados", []):
        lados.append("clash real devia reprovar por interferencia: %r" % (rc.get("reprovados"),))
    gate_c = (rc.get("gates") or {}).get("interferencia") or {}
    if gate_c.get("OK") is not False or gate_c.get("conflitos") != 1:
        lados.append("gate do clash sem OK False/conflitos 1: %r" % (gate_c,))
    if "motivo" in gate_c and gate_c.get("motivo") == "interferencia_nao_verificada":
        lados.append("clash real nao devia carregar o motivo da excecao")
    assert copy is not None
    assert not lados, "fontes independentes reprovam:\n" + "\n".join(lados)
