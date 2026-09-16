"""D176 - auditoria do lote G143-G148 (medida, nao lida).

Achados (fontes vivas, 2026-09-15):
1. G148: cruzado o piso, o runner terminava so o pytest pai. Os workers xdist
   seguiam vivos: sonda com teste de 60 s em -n 2 deu 4 processos novos vivos
   no aborto, 4 ainda vivos 10 s depois, 0 so aos ~40 s (quando o sleep do
   teste acabou). Num teste do grupo FreeCAD seria o freecad.exe (1,5-2 GB)
   segurando a memoria que o piso queria liberar.
2. G146: a planta de formas da PE-MZ-01 marcava as vigas VX0/VX1/VY0/VY1 (o
   rotulo do predio) e a armacao + o BIM marcavam M-VX1/M-VX2/M-VY1/M-VY2 -
   duas paginas da mesma folha sem correspondencia de marca.
3. G146: o titulo do carimbo "MEZANINO DE CONCRETO - FORMAS E ARMACAO" (39)
   passava por `techdraw_exec._cap_titulo` (26) e saia "... - FO…".

Convencoes: vermelho por injecao (o instrumento acusa no codigo antigo -
provado num worktree do 9f112ce), tmp_path, nada muta o repo.
"""
import ctypes
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, os.path.join(GALPAO, "tools"))


def _r_mez():
    import galpao_mezanino as gmz

    return gmz.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0,
                                    "pe_direito": 6.0},
                      "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                      "q_uso": 2.0})


_MARCA_VIGA = re.compile(r">\s*((?:M-)?V[XY]-?\d+)\s*<")


def _marcas_viga(svg):
    return set(_MARCA_VIGA.findall(svg or ""))


def test_01_marcas_de_viga_iguais_nas_formas_na_armacao_e_no_bim(tmp_path):
    import desenho_pavimento as dp
    import galpao_mezanino as gmz
    import techdraw_mezanino as tdm

    r = _r_mez()
    cfg = tdm.config_de_spec(r, str(tmp_path))
    bim = {m["marca"] for m in gmz.membros_bim(r) if m["tipo"] == "Beam"}
    formas = _marcas_viga(cfg["formas_svg"])
    armacao = _marcas_viga(cfg["armacao_svg"])
    gaps = []
    if bim != {"M-VX1", "M-VX2", "M-VY1", "M-VY2"}:
        gaps.append("BIM mudou: %r" % sorted(bim))
    if formas != bim:
        gaps.append("formas %r != BIM %r" % (sorted(formas), sorted(bim)))
    if armacao != bim:
        gaps.append("armacao %r != BIM %r" % (sorted(armacao), sorted(bim)))
    # o instrumento acusa: sem o rotulo do mezanino a planta volta a VX0..
    pav, _vv, _p, _s, aus = dp.adaptar_galpao_mezanino(r)
    sem = _marcas_viga(dp.planta_formas_svg(pav, ausencias=aus))
    if sem == bim:
        gaps.append("regua cega: planta sem rotulo casou com o BIM %r" % sorted(sem))
    # o predio segue com a marca de sempre (rotulo_viga=None)
    from tests.test_edificio_pranchas_g56 import _caso

    predio = _marcas_viga(dp.planta_formas_svg(_caso()[0]["pavimento"]))
    if "VX0" not in predio or any(m.startswith("M-") for m in predio):
        gaps.append("predio perdeu o rotulo VX0: %r" % sorted(predio))
    assert not gaps, "D176 marcas:\n" + "\n".join("  - " + g for g in gaps)


def test_02_carimbo_da_mz01_cabe_na_celula(tmp_path):
    import ast

    import galpao_mezanino as gmz
    from techdraw_exec import _cap_titulo

    gaps = []
    # toda chamada de _carimbo_mz na producao usa um titulo que nao e cortado
    for nome in ("galpao_mezanino.py", "techdraw_mezanino.py"):
        arv = ast.parse(open(os.path.join(GALPAO, nome), encoding="utf-8").read())
        chamadas = [n for n in ast.walk(arv) if isinstance(n, ast.Call)
                    and getattr(n.func, "id", getattr(n.func, "attr", "")) == "_carimbo_mz"]
        if not chamadas:
            gaps.append("%s sem chamada de _carimbo_mz" % nome)
        for c in chamadas:
            arg = c.args[1]
            if isinstance(arg, ast.Constant):
                titulo = arg.value
            else:
                import techdraw_mezanino as tdm
                titulo = getattr(tdm, getattr(arg, "attr", getattr(arg, "id", "")), None)
            if not isinstance(titulo, str) or _cap_titulo(titulo) != titulo:
                gaps.append("%s:%d titulo cortado no carimbo: %r -> %r"
                            % (nome, c.lineno, titulo,
                               _cap_titulo(titulo) if isinstance(titulo, str) else None))
    # e a folha renderizada traz o titulo inteiro no rodape (texto real do PDF)
    import fitz

    pdf = gmz.gerar_prancha_mezanino(_r_mez(), str(tmp_path), {"slug": "d176"})
    with fitz.open(pdf) as d:
        texto = " ".join(d[k].get_text() for k in range(d.page_count))
    if "…" in texto or "FO…" in texto:
        gaps.append("PDF com titulo cortado (reticencia no carimbo)")
    assert not gaps, "D176 carimbo:\n" + "\n".join("  - " + g for g in gaps)


def test_03_arvore_descendentes_so_do_proprio_filho():
    import suite_paralela as sp

    pares = [(10, 1), (11, 10), (12, 11), (13, 10), (20, 1), (21, 20),
             (10, 12), ("x", None)]
    gaps = []
    if sp.arvore_descendentes(pares, 10) != [11, 12, 13]:
        gaps.append("arvore de 10: %r" % (sp.arvore_descendentes(pares, 10),))
    if 20 in sp.arvore_descendentes(pares, 10) or 21 in sp.arvore_descendentes(pares, 10):
        gaps.append("processo do usuario entrou na arvore")
    if sp.arvore_descendentes([], 10) != []:
        gaps.append("sem snapshot devia declarar []")
    assert not gaps, "D176 arvore:\n" + "\n".join("  - " + g for g in gaps)


def _vivo(pid):
    """Independente da producao (roda tambem no codigo antigo)."""
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, int(pid))
    if not h:
        return False
    try:
        c = ctypes.c_ulong()
        return bool(k32.GetExitCodeProcess(h, ctypes.byref(c))) and c.value == 259
    finally:
        k32.CloseHandle(h)


def test_04_aborto_do_piso_nao_deixa_worker_vivo(tmp_path):
    """Injecao: amostrador falso seca quando o teste lento ja esta no worker."""
    import suite_paralela as sp

    marcador = tmp_path / "pid_worker.txt"
    lento = tmp_path / "test_lento_d176.py"
    # D179: sem ini ao lado, a raiz do pytest aninhado vira C:\Users\<user> e a
    # coleta varre o Temp inteiro (pasta de outro app apagada no meio = erro).
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    lento.write_text(
        "import os, time\n\n"
        "def test_lento():\n"
        "    open(%r, 'w').write(str(os.getpid()))\n"
        "    time.sleep(120)\n" % str(marcador), encoding="utf-8")
    usuario = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    inicio = time.time()

    def falso():
        if marcador.exists() or time.time() - inicio > 150:
            return 50.0
        return 5000.0

    pid = None
    try:
        saida = str(tmp_path / "saida")
        rc = sp.main(["-n", "1", "--saida", saida, str(lento)],
                     _amostra_fn=falso, _intervalo_s=0.2)
        gaps = []
        if not marcador.exists():
            gaps.append("o teste lento nao chegou ao worker (sonda invalida)")
        else:
            pid = int(marcador.read_text())
            limite = time.time() + 10
            while time.time() < limite and _vivo(pid):
                time.sleep(0.5)
            if _vivo(pid):
                gaps.append("worker %d segue vivo 10 s depois do aborto do piso" % pid)
        with open(os.path.join(saida, "resumo.json"), encoding="utf-8") as fh:
            resumo = json.load(fh)
        if rc != 1 or not any("piso de memoria livre" in q for q in resumo["quebras"]):
            gaps.append("aborto sem quebra nomeada: rc=%r %r" % (rc, resumo["quebras"]))
        if pid is not None and pid not in (resumo.get("descendentes_terminados") or []):
            gaps.append("resumo nao nomeia o worker terminado: %r"
                        % (resumo.get("descendentes_terminados"),))
        if usuario.poll() is not None:
            gaps.append("o runner matou o processo do usuario")
        assert not gaps, "D176 aborto:\n" + "\n".join("  - " + g for g in gaps)
    finally:
        if pid is not None and _vivo(pid):
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if usuario.poll() is None:
            usuario.terminate()
            try:
                usuario.wait(timeout=15)
            except Exception:
                usuario.kill()
