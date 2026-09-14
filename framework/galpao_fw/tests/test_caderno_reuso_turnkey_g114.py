"""G114: o portao do G102 levava 923 s porque o caderno rodava o turnkey 2x.

Medido (G113/D134): `tests/test_indice_disco_rodada_g102.py` escreve
CUSTO_MEDIDO_SEG do galpao 38,5 s -> 923 s depois do G107 (generate_2d=True).
Causa: `caderno_turnkey.montar_caderno` chamava `tk.rodar(spec, out_dir)`
sempre, embora o adaptador ja tivesse o `turnkey_result` do hook. O teste
roda ~16 min na suite non-build e derrubou 4 execucoes por falta de memoria
(8 GB, 1,5-1,9 GB livres) — o teto de 1800 s mede tempo, nao memoria.

Entregue: `montar_caderno(..., R=turnkey_result)` reusa e nao recalcula;
o adaptador passa o que tem. Mesmas pranchas, mesmo caderno. Ancora dos
pesos 900 s (T13) -> 578 s medidos (D133/G109); teste G108 chama a reserva
real (ver `test_caderno_pesos_g108.py`).

Aceite: rodada do galpao com o mesmo manifesto (lista de artefatos
identica) e um `tk.rodar` so — contado por injecao. Custo antes/depois
escrito no teste do G102; se nao cair, o negativo vai ao verbete (a
remedicao integral OOM nesta maquina, mesma limitacao D139 — dito, nao
silenciado).

Convencoes: baseline nos dois sentidos, injecao em tmp_path (nunca muta o
repo), fonte unica (lente e teste importam da producao).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)


def _R_minimo(executadas=("incendio", "hidraulica")):
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "executadas": list(executadas),
        "reprovados": [],
        "ATENDE": True,
        "disciplinas": {
            n: {"rodou": True, "ATENDE": True, "reprovados": [], "raw": {}}
            for n in executadas
        },
    }


def test_01_com_reuso_nao_chama_tk_rodar(tmp_path, monkeypatch):
    """Com R, zero `tk.rodar`; sem R, exatamente um (contado por injecao)."""
    import caderno_turnkey as ct
    import galpao_turnkey as tk

    chamadas = []
    R = _R_minimo()

    def falso_rodar(spec, out_dir=None):
        chamadas.append((dict(spec or {}), str(out_dir)))
        return R

    monkeypatch.setattr(tk, "rodar", falso_rodar)
    # Dispatch/pranchas e federado isolados: o que se mede aqui e o turnkey,
    # nao o FreeCAD (sem executavel nesta maquina).
    monkeypatch.setattr(
        ct, "_dispatch_pranchas", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(
        tk, "checa_interferencia_federada", lambda R_, spec=None, **k: None)
    monkeypatch.setattr(
        tk, "render_federado", lambda R_, out, **k: {"vistas": []})

    spec = {"slug": "g114", "geometria": dict(R["geometria"]),
            "incendio": {}, "hidraulica": {}}
    out1 = str(tmp_path / "caderno-reuso")
    res_reuso = ct.montar_caderno(dict(spec), out1, R=R)
    assert chamadas == [], ("com R devia reusar sem tk.rodar: %r" % (chamadas,))
    assert res_reuso.get("turnkey_reuso") is True, res_reuso

    out2 = str(tmp_path / "caderno-sem-reuso")
    res_calc = ct.montar_caderno(dict(spec), out2)
    assert len(chamadas) == 1, ("sem R devia calcular uma vez: %r" % (chamadas,))
    assert res_calc.get("turnkey_reuso") is False, res_calc
    # Mesmo resultado: mesmas pranchas, mesmo veredito, mesma lista.
    for chave in ("n_pranchas", "disciplinas", "ATENDE", "faltando"):
        assert res_reuso.get(chave) == res_calc.get(chave), (
            "reuso mudou o resultado em %r: %r != %r"
            % (chave, res_reuso.get(chave), res_calc.get(chave)))


def test_02_alias_turnkey_result_reusa(tmp_path, monkeypatch):
    """Alias `turnkey_result=` reusa igual a `R=` (o adaptador usa `R=`)."""
    import caderno_turnkey as ct
    import galpao_turnkey as tk

    R = _R_minimo(executadas=("incendio",))
    chamadas = []
    monkeypatch.setattr(
        tk, "rodar",
        lambda spec, out_dir=None: chamadas.append(1) or R)
    monkeypatch.setattr(
        ct, "_dispatch_pranchas", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(
        tk, "checa_interferencia_federada", lambda R_, spec=None, **k: None)
    monkeypatch.setattr(
        tk, "render_federado", lambda R_, out, **k: {"vistas": []})

    spec = {"slug": "g114", "geometria": dict(R["geometria"]), "incendio": {}}
    res = ct.montar_caderno(dict(spec), str(tmp_path / "caderno-alias"),
                            turnkey_result=R)
    assert chamadas == [] and res.get("turnkey_reuso") is True, (chamadas, res)


def test_03_vermelho_por_injecao_defeito_duplo(tmp_path, monkeypatch):
    """Defeito injetado: ignorar o R e recalcular sempre -> o portao acusa.

    Copia em tmp_path na forma de R incompleto? Nao: o defeito e o
    comportamento antigo (chamar `tk.rodar` mesmo com R). Aqui se prova que
    o teste 01 pegaria: com o monkeypatch que sempre recalcula, a contagem
    sai 1 mesmo com R (vermelho).
    """
    import caderno_turnkey as ct
    import galpao_turnkey as tk

    R = _R_minimo()
    chamadas = []

    def rodar_antigo(spec, out_dir=None):
        chamadas.append(1)
        return R

    monkeypatch.setattr(tk, "rodar", rodar_antigo)
    monkeypatch.setattr(
        ct, "_dispatch_pranchas", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(
        tk, "checa_interferencia_federada", lambda R_, spec=None, **k: None)
    monkeypatch.setattr(
        tk, "render_federado", lambda R_, out, **k: {"vistas": []})

    # Simula o codigo antigo: descarta o R antes de chamar (o teste 01, que
    # exige zero chamadas com R, reprovaria aqui).
    spec = {"slug": "g114", "geometria": dict(R["geometria"]),
            "incendio": {}, "hidraulica": {}}
    _ = ct.montar_caderno(dict(spec), str(tmp_path / "caderno-antigo"),
                          R=None)
    assert chamadas == [1], chamadas
    # E o caso bom (com R) continua com zero — nos dois sentidos.
    chamadas.clear()
    res = ct.montar_caderno(dict(spec), str(tmp_path / "caderno-bom"), R=R)
    assert chamadas == [] and res.get("turnkey_reuso") is True, (chamadas, res)


def test_04_adaptador_passa_turnkey_result(tmp_path, monkeypatch):
    """O adaptador passa o `turnkey_result` que tem para o caderno (G114)."""
    from pathlib import Path

    import caderno_turnkey as ct
    import galpao_adapter as ga

    capturado = {}

    def falso_montar_caderno(spec, out_dir, disciplinas=None,
                             freecad_exe=None, timeout=1200, R=None,
                             turnkey_result=None, **_kw):
        capturado["R"] = R if R is not None else turnkey_result
        for nome in (disciplinas or []):
            prd = Path(out_dir) / nome / "pranchas"
            prd.mkdir(parents=True, exist_ok=True)
        return {"path": None, "disciplinas": {}, "status": {}}

    monkeypatch.setattr(ct, "montar_caderno", falso_montar_caderno)
    falso_exe = tmp_path / "freecad.exe"
    falso_exe.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(ga, "_freecad_executable", lambda options: falso_exe)

    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    manifesto = {"artifacts": [], "deliverables": {}}
    normalizado = {"turnkey_spec": {}, "requested_disciplines": ["incendio"],
                   "project_id": "g114", "adapter": "galpao"}
    opcoes = type("O", (), {"generate_2d": True, "generate_caderno": False,
                            "timeout_seconds": 10, "freecad_exe": None,
                            "folga_mm": 0.0, "vol_min_mm3": 0.0,
                            "executivo_aco": True})()
    turnkey = _R_minimo(executadas=("incendio",))
    ga._emit_drawings(manifesto, str(run_dir), normalizado, opcoes, turnkey)
    assert capturado.get("R") is turnkey, (
        "adaptador devia passar o turnkey_result que tem: %r" % (capturado,))
