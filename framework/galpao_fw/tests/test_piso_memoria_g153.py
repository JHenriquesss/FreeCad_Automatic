"""G153 - o piso que abortava por uma amostra so (fonte: tools/suite_paralela.py).

O G142 passou com minimo de 159 MB numa unica amostra (sem serie, sem
duracao); com o piso de amostra unica teria sido abortado. O resumo guardava
so o minimo - sem saber se foi pico de 1 s ou minutos. Aqui a serie de
amostras vai para o resumo, a regra confirma em K=3 seguidas (~3 s) e a carga
da maquina e gravada; vermelho por injecao nos dois sentidos (transitoria nao
aborta, sustentada aborta e mata a arvore).

Convencoes: baseline nos dois sentidos (test_01/test_02), injecao em tmp_path
(o repo nunca e mutado), instrumento acusa por parte (gap nomeia piso + livre
+ confirmacao), constante medida lida pela producao (test_01, conv. 8), prova
com processo real ocupado e arvore lida no instante do aborto (conv. 14: o
lento dorme no worker quando o falso seca).
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(GALPAO, "tools"))
sys.path.insert(0, HERE)

import suite_paralela as sp  # noqa: E402


def test_01_confirmacao_derivada_do_medido_e_lida_pela_producao():
    """K=3 existe, vale 3 e o motivo medido esta escrito; a producao le.

    Convencao 8: constante "medida" que a producao nao le e comentario - aqui
    o runner le K por default (confirmacao + resumo), e o motivo cita as
    fontes (G142 159 de amostra unica, D176 251, D177 300, serie no resumo).
    Mudar o valor ou apagar a leitura reprova.
    """
    lados = []
    if sp.CONFIRMACAO_PISO_AMOSTRAS != 3:
        lados.append("CONFIRMACAO_PISO_AMOSTRAS=%r, esperado 3 (derivado do "
                     "medido G153)" % (sp.CONFIRMACAO_PISO_AMOSTRAS,))
    fonte = open(os.path.join(GALPAO, "tools", "suite_paralela.py"),
                 encoding="utf-8").read()
    for marca in ("159", "G142", "CONFIRMACAO_PISO_AMOSTRAS",
                  "memoria_serie_amostras", "memoria_quedas_abaixo_piso",
                  "carga_maquina", "confirma_queda_consecutiva",
                  "quedas_abaixo_piso"):
        if marca not in fonte:
            lados.append("derivacao/leitura sem a marca %r no fonte" % marca)
    # a producao le por default: 1 amostra baixa nao confirma, 3 confirmam
    if sp.confirma_queda_consecutiva([5000.0, 5000.0, 50.0]):
        lados.append("1 amostra baixa confirmou com K default (devia ser 3)")
    if not sp.confirma_queda_consecutiva([50.0, 40.0, 30.0]):
        lados.append("3 seguidas baixas nao confirmaram com K default")
    if '"memoria_serie_amostras"' not in fonte.replace("'", '"'):
        lados.append("resumo.json sem o campo memoria_serie_amostras")
    if '"carga_maquina"' not in fonte.replace("'", '"'):
        lados.append("resumo.json sem o campo carga_maquina")
    assert not lados, "confirmacao G153 reprova:\n" + "\n".join(lados)


def test_02_veredito_confirmado_vermelho_nos_dois_sentidos():
    """Amostrador falso puro: transitoria passa, sustentada acusa, None cala."""
    lados = []
    # transitoria de 1-2 s nao confirma (K=3)
    for hist in ([50.0], [5000.0, 50.0], [5000.0, 50.0, 40.0],
                 [50.0, 40.0, 5000.0], [50.0, None, 30.0],
                 [50.0, 40.0, 200.0], [5000.0, 5000.0, 5000.0], []):
        if sp.confirma_queda_consecutiva(hist, 200, 3):
            lados.append("transitoria confirmou (devia passar): %r" % (hist,))
    # sustentada de 3 s+ confirma
    for hist in ([50.0, 40.0, 30.0], [10.0, 10.0, 10.0, 10.0],
                 [5000.0, 50.0, 40.0, 30.0]):
        if not sp.confirma_queda_consecutiva(hist, 200, 3):
            lados.append("sustentada nao confirmou (devia abortar): %r" % (hist,))
    # piso custom e K custom, um por um (convencao 13 na forma do runner)
    if not sp.confirma_queda_consecutiva([100.0, 100.0], 500, 2):
        lados.append("piso custom 500/K2 nao confirmou [100,100]")
    if sp.confirma_queda_consecutiva([100.0, 600.0], 500, 2):
        lados.append("piso custom 500/K2 confirmou com folga no meio")
    if sp.confirma_queda_consecutiva([50.0, 40.0, 30.0], None, 3):
        lados.append("piso None confirmou em vez de declarar")
    if sp.confirma_queda_consecutiva([50.0, 40.0, 30.0], 200, None):
        lados.append("K None confirmou em vez de declarar")
    if sp.confirma_queda_consecutiva([50.0, 40.0, 30.0], 200, 0):
        lados.append("K 0 confirmou em vez de declarar")
    # quedas derivadas da serie: duracao e minimo, trecho maximal
    q = sp.quedas_abaixo_piso([(0.0, 500.0), (1.0, 50.0), (2.0, 40.0),
                               (3.0, 500.0), (4.0, 10.0)], 200)
    if len(q) != 2:
        lados.append("quedas deviam ser 2 trechos: %r" % (q,))
    else:
        if q[0]["n_amostras"] != 2 or q[0]["duracao_s"] != 1.0:
            lados.append("1a queda fora (2 amostras, 1 s): %r" % (q[0],))
        if q[0]["minimo_mb"] != 40:
            lados.append("minimo da 1a queda fora (40): %r" % (q[0],))
        if q[1]["n_amostras"] != 1 or q[1]["duracao_s"] != 0.0:
            lados.append("2a queda fora (1 amostra, 0 s): %r" % (q[1],))
    if sp.quedas_abaixo_piso([], 200) != []:
        lados.append("serie vazia devia declarar []")
    if sp.quedas_abaixo_piso([(0.0, 500.0)], 200) != []:
        lados.append("serie sem queda devia declarar []")
    assert not lados, "confirmacao pura reprova:\n" + "\n".join(lados)


def _recorte_rapido():
    return ("tests/test_suite_paralela_d164.py::"
            "test_01_conferencia_vermelha_nos_dois_sentidos")


def _ler_resumo(saida):
    with open(os.path.join(saida, "resumo.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_03_transitoria_nao_aborta_e_sustentada_aborta(tmp_path):
    """Vermelho por injecao no runner: 1 amostra seca passa, 3 secam e abortam.

    Processo "do usuario" (filho deste teste, nao do runner) segue vivo nos
    dois sentidos - o runner so termina a propria arvore (conv. 14: a sonda
    usa processo real; o recorte rapido acaba antes, entao a arvore morta se
    confere no test_04 com teste lento).
    """
    usuario = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # transitoria: uma amostra seca no meio da folga - nao confirma
        seq = iter([5000.0, 5000.0, 50.0, 5000.0, 5000.0, 5000.0])

        def falso_transitoria():
            try:
                return next(seq)
            except StopIteration:
                return 5000.0

        saida_t = str(tmp_path / "saida_transitoria")
        rc_t = sp.main(["-n", "1", "--saida", saida_t, _recorte_rapido()],
                       _amostra_fn=falso_transitoria, _intervalo_s=0.2,
                       _recuperacao_s=2.0)
        res_t = _ler_resumo(saida_t)
        lados = []
        if rc_t != 0:
            lados.append("transitoria retornou rc=%r, esperado 0" % (rc_t,))
        if any("piso de memoria livre" in q for q in res_t["quebras"]):
            lados.append("transitoria abortou (devia passar): %r"
                         % (res_t["quebras"],))
        if len(res_t.get("memoria_quedas_abaixo_piso") or []) != 1:
            lados.append("transitoria devia registrar 1 queda de 1 amostra: %r"
                         % (res_t.get("memoria_quedas_abaixo_piso"),))
        else:
            q = res_t["memoria_quedas_abaixo_piso"][0]
            if q["n_amostras"] != 1 or q["duracao_s"] != 0.0:
                lados.append("queda transitoria fora (1 amostra, 0 s): %r" % (q,))
        if not res_t.get("memoria_serie_amostras"):
            lados.append("resumo sem serie de amostras na transitoria")
        if usuario.poll() is not None:
            lados.append("o runner matou o processo do usuario na transitoria")
        assert not lados, "transitoria G153 reprova:\n" + "\n".join(lados)
    finally:
        if usuario.poll() is None:
            usuario.terminate()
            try:
                usuario.wait(timeout=15)
            except Exception:
                usuario.kill()

    usuario2 = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # sustentada: 3 seguidas secas - confirma, aborta e mata a arvore
        seq2 = iter([5000.0, 50.0, 40.0, 30.0, 20.0])

        def falso_sustentada():
            try:
                return next(seq2)
            except StopIteration:
                return 20.0

        saida_s = str(tmp_path / "saida_sustentada")
        rc_s = sp.main(["-n", "1", "--saida", saida_s, _recorte_rapido()],
                       _amostra_fn=falso_sustentada, _intervalo_s=0.2,
                       _recuperacao_s=2.0)
        res_s = _ler_resumo(saida_s)
        lados = []
        if rc_s != 1:
            lados.append("sustentada retornou rc=%r, esperado 1" % (rc_s,))
        if not any("piso de memoria livre" in q for q in res_s["quebras"]):
            lados.append("sustentada sem quebra nomeada: %r" % (res_s["quebras"],))
        if not any("confirmado em 3" in q for q in res_s["quebras"]):
            lados.append("quebra sem dizer a confirmacao: %r" % (res_s["quebras"],))
        if res_s.get("memoria_confirmacao_amostras") != 3:
            lados.append("resumo sem K=3: %r" % (res_s.get("memoria_confirmacao_amostras"),))
        if not res_s.get("memoria_serie_amostras"):
            lados.append("resumo sem serie de amostras na sustentada")
        if usuario2.poll() is not None:
            lados.append("o runner matou o processo do usuario na sustentada")
        assert not lados, "sustentada G153 reprova:\n" + "\n".join(lados)
    finally:
        if usuario2.poll() is None:
            usuario2.terminate()
            try:
                usuario2.wait(timeout=15)
            except Exception:
                usuario2.kill()


def test_04_aborto_sustentado_mata_a_arvore_com_teste_lento(tmp_path):
    """Convencao 14: o falso seca quando o teste lento ja esta no worker.

    O worker nao pode estar vivo 10 s depois do aborto e o resumo tem de
    nomea-lo em descendentes_terminados; o processo do usuario segue vivo.
    """
    import ctypes

    def vivo(pid):
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        try:
            c = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(h, ctypes.byref(c))) and c.value == 259
        finally:
            k32.CloseHandle(h)

    marcador = tmp_path / "pid_worker.txt"
    lento = tmp_path / "test_lento_g153.py"
    # D179: sem ini ao lado, a raiz do pytest aninhado vira C:\Users\<user> e a
    # coleta varre o Temp inteiro (pasta de outro app apagada no meio = erro;
    # a serial da auditoria D179 falhou assim).
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
                     _amostra_fn=falso, _intervalo_s=0.2, _recuperacao_s=2.0)
        gaps = []
        if not marcador.exists():
            gaps.append("o teste lento nao chegou ao worker (sonda invalida)")
        else:
            pid = int(marcador.read_text())
            limite = time.time() + 10
            while time.time() < limite and vivo(pid):
                time.sleep(0.5)
            if vivo(pid):
                gaps.append("worker %d segue vivo 10 s depois do aborto" % pid)
        with open(os.path.join(saida, "resumo.json"), encoding="utf-8") as fh:
            resumo = json.load(fh)
        if rc != 1 or not any("piso de memoria livre" in q for q in resumo["quebras"]):
            gaps.append("aborto sem quebra nomeada: rc=%r %r" % (rc, resumo["quebras"]))
        if pid is not None and pid not in (resumo.get("descendentes_terminados") or []):
            gaps.append("resumo nao nomeia o worker terminado: %r"
                        % (resumo.get("descendentes_terminados"),))
        if not resumo.get("memoria_serie_amostras"):
            gaps.append("resumo sem serie de amostras no aborto real")
        if usuario.poll() is not None:
            gaps.append("o runner matou o processo do usuario")
        assert not gaps, "D176/aborto G153:\n" + "\n".join("  - " + g for g in gaps)
    finally:
        if pid is not None and vivo(pid):
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if usuario.poll() is None:
            usuario.terminate()
            try:
                usuario.wait(timeout=15)
            except Exception:
                usuario.kill()


def test_06_censo_declara_arquivo_vazio_do_aborto(tmp_path):
    """O aborto mata o worker no meio da escrita: coletados vazio nao levanta.

    Vermelho do G153: `ler_coletados` com `json.load('')` levantava
    JSONDecodeError e o proprio resumo do aborto morria. Arquivo vazio ou
    linha ruim declara ausencia; arquivo bom segue lido.
    """
    import censo_freecad as cf

    (tmp_path / "coletados-gw0.json").write_text("", encoding="utf-8")
    (tmp_path / "coletados-gw1.json").write_text(
        json.dumps(["tests/test_b.py"]), encoding="utf-8")
    (tmp_path / "freecad-gw0.jsonl").write_text(
        "{linha ruim}\n"
        + json.dumps({"worker": "gw0", "pid": 11, "exe": "freecad.exe",
                      "nodeid": "tests/test_a.py::t1"}) + "\n",
        encoding="utf-8")
    lados = []
    try:
        col = cf.ler_coletados(str(tmp_path))
    except Exception as e:
        lados.append("ler_coletados levantou: %r" % (e,))
        col = None
    try:
        reg = cf.ler_registros(str(tmp_path))
    except Exception as e:
        lados.append("ler_registros levantou: %r" % (e,))
        reg = None
    if col is not None and col != {"tests/test_b.py"}:
        lados.append("coletados fora (vazio declara, bom le): %r" % (col,))
    if reg is not None and [r["nodeid"] for r in reg] != ["tests/test_a.py::t1"]:
        lados.append("registros fora (linha ruim pula, boa fica): %r" % (reg,))
    assert not lados, "censo do aborto reprova:\n" + "\n".join(lados)


def test_05_serie_carga_e_volta_declaradas_no_resumo(tmp_path):
    """O resumo carrega serie, quedas, carga da maquina e volta declarada."""
    saida = str(tmp_path / "saida_folga")
    rc = sp.main(["-n", "1", "--saida", saida, _recorte_rapido()],
                 _amostra_fn=lambda: 5000.0, _intervalo_s=0.2,
                 _recuperacao_s=2.0)
    resumo = _ler_resumo(saida)
    lados = []
    if rc != 0:
        lados.append("folga retornou rc=%r: %r" % (rc, resumo["quebras"]))
    serie = resumo.get("memoria_serie_amostras")
    if not isinstance(serie, list) or not serie:
        lados.append("serie ausente ou vazia: %r" % (serie,))
    else:
        ts = [t for t, _v in serie]
        if any(b - a < 0 for a, b in zip(ts, ts[1:])):
            lados.append("serie fora de ordem temporal")
        if any(v is None for _t, v in serie):
            lados.append("serie com None em corrida de folga pura")
        vals = [v for _t, v in serie]
        if min(vals) != resumo.get("memoria_livre_min_mb"):
            lados.append("minimo do resumo != minimo da serie: %r vs %r"
                         % (resumo.get("memoria_livre_min_mb"), min(vals)))
    if resumo.get("memoria_quedas_abaixo_piso") != []:
        lados.append("folga pura devia declarar quedas []: %r"
                     % (resumo.get("memoria_quedas_abaixo_piso"),))
    carga = resumo.get("carga_maquina") or {}
    if carga.get("cpu_logicos") != 8:
        lados.append("carga sem cpu_logicos=8: %r" % (carga,))
    if not isinstance(carga.get("total_phys_mb"), (int, float)):
        lados.append("carga sem total_phys_mb medido: %r" % (carga,))
    if carga.get("n_amostras") != len(serie or []):
        lados.append("carga n_amostras != len(serie): %r" % (carga,))
    if resumo.get("tempo_memoria_volta_s") is not None:
        lados.append("sem brecha a volta devia ser None (declarada): %r"
                     % (resumo.get("tempo_memoria_volta_s"),))
    assert not lados, "serie/carga G153 reprova:\n" + "\n".join(lados)
