"""Testes G15 - validacao de sistema contra projeto real.

Cobre: vento, Cpe, parede, equilibrio, secoes, armadura, quantitativos,
eletrica (IB/secao/quedas/demanda), hidraulica (DN/pressao), estrutura
(pilar/sapata) e o guard d*sen45. Cada teste chama o check correspondente
de validacao_sistema_g15 e assere PASS dentro da tolerancia de engenharia.

A validacao de sistema nao substitui a de nucleo (validacao.py); ela a
complementa aferindo o SISTEMA (spec->calculo->quantitativo) contra
handcalc/memo publicado, com a mesma grandeza dos dois lados.
"""
import math
import pathlib as _pl
import pytest
import validacao_sistema_g15 as G15

# D81/G45: caminhos ancorados no ARQUIVO, nunca no cwd. A versao anterior
# usava "docs/...", "projects/...", "tools/..." relativos ao diretorio de
# invocacao — o veredito mudava com o cwd (verde na raiz do repo, vermelho
# em framework/galpao_fw; e o quarto-caso com cwd="framework/galpao_fw"
# relativo falhava no sentido inverso). Veredito que depende de onde o
# pytest foi chamado e sorteio, nao teste: mesma classe do D81.
_REPO = _pl.Path(__file__).resolve().parents[5]
_GALPAO = _pl.Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("fn", G15.CHECKS)
def test_g15_checks_pass(fn):
    nome, ok, err, det = fn()
    assert ok, f"{nome} falhou (err={err:.2%}) :: {det}"


def test_g15_todos_passam():
    ok, resultados = G15.rodar(verbose=False)
    assert ok, f"Nem todos os {len(G15.INVENTARIO_CHECKS)} checks passaram: {[n for n,ok,_ ,_ in resultados if not ok]}"
    # G30: inventário nomeado — acrescentar check é ato explícito, não subir número
    assert len(resultados) == len(G15.INVENTARIO_CHECKS), f"inventario {len(G15.INVENTARIO_CHECKS)} vs resultados {len(resultados)}"
    nomes = sorted(fn.__name__ for fn in G15.CHECKS)
    inv = sorted(G15.INVENTARIO_CHECKS)
    assert nomes == inv, f"CHECKS diverge do INVENTARIO: missing={set(inv)-set(nomes)} extra={set(nomes)-set(inv)}"


def test_g15_inventario_explicito():
    """G30: CHECKS deve ser exatamente o INVENTARIO nomeado — número não sobe sozinho."""
    assert hasattr(G15, "INVENTARIO_CHECKS"), "G30: validacao_sistema_g15 deve expor INVENTARIO_CHECKS"
    assert isinstance(G15.INVENTARIO_CHECKS, list) and len(G15.INVENTARIO_CHECKS) >= 27
    # cada nome deve corresponder a uma função em CHECKS
    check_names = {fn.__name__ for fn in G15.CHECKS}
    for nome in G15.INVENTARIO_CHECKS:
        assert nome in check_names, f"inventario {nome} sem funcao correspondente em CHECKS"
    # e não pode haver função fora do inventario
    assert check_names == set(G15.INVENTARIO_CHECKS), "CHECKS tem funcao fora do INVENTARIO ou vice-versa"


def test_g15_sem_falsa_divergencia_d_sen45():
    """Guard: d vs d*sen45 sao grandezas diferentes; nunca comparar direto."""
    d = 400.0
    d_proj = d * math.sin(math.radians(45.0))
    # \"divergencia\" falsa se comparar sem converter:
    falso_err = abs(d - d_proj) / d  # 29.3%
    assert falso_err > 0.25, "Guard: d vs d*sen45 devia dar ~29% de falsa divergencia"
    # O check de G15 deve passar (ele nao compara grandezas diferentes)
    nome, ok, err, det = G15.check_armadilha_d_sen45()
    assert ok


def test_g15_quantitativo_aco_grandeza_inclinada():
    """Quantitativo usa L_rafter inclinado, nao projecao."""
    nome, ok, err, det = G15.check_quantitativo_aco_amostra()
    assert ok
    assert "INCLINADO" in det
    assert "10.112" in det  # L correto
    assert "10.0" in det    # projecao mencionada como armadilha


def test_g15_vento_define_z_cumeeira():
    nome, ok, err, det = G15.check_vento_amostra()
    assert ok
    assert "cumeeira" in det  # z=9.5 explicitado


def test_g15_carga_parede_no_baldrame():
    nome, ok, err, det = G15.check_carga_parede_amostra()
    assert ok
    assert "BALDRAME" in det
    assert "NAO carrega coluna" in det


def test_g15_eletrica_ib_monofasico():
    nome, ok, err, det = G15.check_eletrica_casa_ib()
    assert ok
    assert "S/V monofasico" in det


def test_g15_cbca_regressao_bate():
    """CBCA ja homologado: nao pode regredir."""
    nome, ok, err, det = G15.check_vento_cbca_referencia()
    assert ok, det
    assert err < 0.05  # vertical 5% / H/M 15%


def test_g19_sjb_preflight_guard_bloqueado_ou_ready():
    """G19 guard: SJB deve estar blocked (9 campos) ou ready — nunca FAIL por falta de obra."""
    nome, ok, err, det = G15.check_galpao_sjb_preflight_comportamento()
    assert ok, f"{nome} deveria PASS (guard G19): {det}"
    # detalhe deve mencionar AGUARDANDO ou READY
    assert ("AGUARDANDO OBRA REAL" in det) or ("READY" in det) or ("Status" in det)


def test_g19_sjb_memorial_skip_enquanto_sem_obra():
    """G19: sem memorial real, harness deve SKIP (PASS) e nao falsificar validacao contra concreto."""
    nome, ok, err, det = G15.check_galpao_sjb_memorial_comparacao()
    assert ok, f"{nome} deveria PASS/SKIP: {det}"
    # enquanto SJB blocked, deve mencionar SKIP e nunca contra concreto
    assert "SKIP" in det
    assert "AGUARDANDO" in det


def test_g19_obra_conhecida_agente_36x24():
    """G19: obra conhecida do agente (proposta 36x24) deve validar com 0% erro quando sidecar coincide."""
    nome, ok, err, det = G15.check_obra_conhecida_agente_36x24()
    assert ok, f"{nome} deveria PASS: {det}"
    assert "peso_aco_primario_kg" in det
    assert "Mcol_kNm" in det
    assert "PROPOSTA NAO E OBRA REAL" in det


def test_g19_guard_rejeita_sidecar_sintetico_como_real(monkeypatch, tmp_path):
    """G19 guard: copiar sidecar sintetico para galpao-sjb-valores-referencia.json deve ser BLOQUEADO, nao PASS."""
    import pathlib, json, shutil
    # D81/G45: a versao anterior reescrevia o spec VIVO e criava memorial
    # VIVO, restaurando no finally — sob `pytest -n 4` os vizinhos liam o
    # spec mutado na janela (contaminacao) e um kill deixava o repo com o
    # spec trocado. O check le os globais do modulo: apontar para copias
    # no tmp exercita a mesma logica sem tocar no repositorio vivo.
    sjb_spec = pathlib.Path(G15._SJB_SPEC)
    proposta_spec = pathlib.Path(G15._PROPOSTA_SPEC)
    sintetico = pathlib.Path(G15._PROPOSTA_SIDECAR)
    vivo_json = pathlib.Path(G15._SJB_MEMORIAL_JSON)
    vivo_pdf = pathlib.Path(G15._SJB_MEMORIAL_PDF)
    vivo_spec_texto = sjb_spec.read_text(encoding="utf-8")
    tmp_sjb = tmp_path / "project-spec.json"
    tmp_json = tmp_path / "galpao-sjb-valores-referencia.json"
    tmp_pdf = tmp_path / "galpao-sjb-memorial.pdf"
    # tornar SJB ready copiando proposta (na copia) + memorial falso sintetico
    tmp_sjb.write_text(proposta_spec.read_text(encoding="utf-8"), encoding="utf-8")
    tmp_pdf.write_text("%PDF-1.4 dummy", encoding="utf-8")
    tmp_json.write_text(sintetico.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(G15, "_SJB_SPEC", tmp_sjb)
    monkeypatch.setattr(G15, "_SJB_MEMORIAL_JSON", tmp_json)
    monkeypatch.setattr(G15, "_SJB_MEMORIAL_PDF", tmp_pdf)
    nome, ok, err, det = G15.check_galpao_sjb_memorial_comparacao()
    assert not ok, f"Guard deveria BLOQUEAR sidecar sintético como real, mas retornou PASS: {det}"
    assert "BLOQUEADO" in nome or "BLOQUEADO" in det
    assert "PROPOSTA" in det or "EXEMPLO SINTETICO" in det
    # o repositorio vivo nunca foi tocado
    assert sjb_spec.read_text(encoding="utf-8") == vivo_spec_texto
    assert not vivo_json.exists() and not vivo_pdf.exists()


def test_g19_detecta_divergencia_peso(monkeypatch, tmp_path):
    """G19: harness deve FAIL quando sidecar diverge >10% no peso (prova que não é só PASS)."""
    import pathlib, json
    # D81/G45: a versao anterior reescrevia o sidecar VIVO e restaurava no
    # finally — vizinhos sob `-n 4` liam o peso mutado na janela e o
    # check_obra_conhecida deles falhava por contaminacao. Copia no tmp +
    # monkeypatch no global que o check realmente le.
    sidecar = pathlib.Path(G15._PROPOSTA_SIDECAR)
    vivo_texto = sidecar.read_text(encoding="utf-8")
    data = json.loads(vivo_texto)
    # introduzir divergência de 20% no peso (tol é 10%)
    orig = float(data["valores_referencia"]["peso_aco_primario_kg"])
    data["valores_referencia"]["peso_aco_primario_kg"] = orig * 1.20
    # manter aviso de proposta para não ser confundido com guard de prova, mas ainda é proposta
    tmp_sidecar = tmp_path / "proposta-36x24-exemplo-valores-referencia.json"
    tmp_sidecar.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(G15, "_PROPOSTA_SIDECAR", tmp_sidecar)
    nome, ok, err, det = G15.check_obra_conhecida_agente_36x24()
    assert not ok, f"Harness deveria FAIL com 20% de divergência no peso, mas retornou PASS: {det}"
    assert "peso_aco_primario_kg" in det
    assert "FAIL" in det
    assert err > 0.10
    # o sidecar vivo continua byte a byte igual
    assert sidecar.read_text(encoding="utf-8") == vivo_texto


def test_g19_checklist_9_campos_batem_com_preflight():
    """G19: CHECKLIST-9-CAMPOS.md deve listar exatamente os 9 erros que o preflight retorna hoje."""
    import pathlib, json, re
    # 1. contar linhas da checklist (tabela)
    checklist = _REPO / "docs/validacao_g15/CHECKLIST-9-CAMPOS.md"
    assert checklist.is_file(), f"CHECKLIST-9-CAMPOS.md não encontrado: {checklist}"
    texto = checklist.read_text(encoding="utf-8")
    # linhas da tabela que começam com "| 1 |", "| 2 |" ... "| 9 |"
    linhas = [l for l in texto.splitlines() if re.match(r"\|\s*[1-9]\s*\|", l)]
    assert len(linhas) == 9, f"CHECKLIST deve ter 9 linhas de campos, veio {len(linhas)}: {linhas[:2]}"
    # verificar que menciona os 3 de geometria e 6 disciplinas
    assert "comprimento" in texto and "pe_direito" in texto
    assert texto.count("pending_discipline_input") >= 6 or texto.count("concreto") >= 6
    # 2. preflight real do SJB bloqueado
    import project_loop
    # garantir que spec canônico ainda está bloqueado (não foi promovido da proposta)
    spec = json.loads((_REPO / "projects/galpao-sjb/project-spec.json").read_text(encoding="utf-8"))
    rep = project_loop.preflight_project(spec, options={"require_source_refs": True})
    assert rep["status"] == "blocked", f"SJB canônico deveria estar blocked, veio {rep['status']}"
    errs = rep["preflight"]["errors"]
    assert len(errs) == 9, f"preflight deveria ter 9 erros, veio {len(errs)}: {errs}"
    geom = [e for e in errs if e["code"] == "invalid_common_geometry"]
    pend = [e for e in errs if e["code"] == "pending_discipline_input"]
    assert len(geom) == 3, f"esperado 3 invalid_common_geometry, veio {geom}"
    assert len(pend) == 6, f"esperado 6 pending_discipline_input, veio {pend}"
    # 3. proposta deve estar ready (prova que checklist é acionável)
    proposta = json.loads((_REPO / "projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json").read_text(encoding="utf-8"))
    rep2 = project_loop.preflight_project(proposta, options={"require_source_refs": True})
    assert rep2["status"] == "ready", f"proposta 36x24 deveria estar ready, veio {rep2['status']} warnings={rep2['preflight']['warnings']}"


def test_g19_esquema_9_campos_valida_blocked_e_ready():
    """G19: ESQUEMA-9-CAMPOS.json + validar_9_campos.py devem bater com o gate real."""
    import pathlib, json, subprocess, sys
    esquema = _REPO / "docs/validacao_g15/ESQUEMA-9-CAMPOS.json"
    assert esquema.is_file(), f"ESQUEMA não encontrado: {esquema}"
    data = json.loads(esquema.read_text(encoding="utf-8"))
    assert "turnkey" in str(data) and "geometria" in str(data)
    # validar_9_campos.py no SJB bloqueado deve reportar 9 faltas (robusto a encoding)
    res = subprocess.run([sys.executable, str(_REPO / "tools/validar_9_campos.py"), "--spec", str(_REPO / "projects/galpao-sjb/project-spec.json"), "--json"],
                         capture_output=True, text=False)
    stdout = res.stdout.decode("utf-8", errors="replace")
    assert res.returncode in (0, 1), f"validar_9_campos.py falhou: {res.stderr.decode('utf-8', errors='replace')[:500]}"
    out = json.loads(stdout)
    assert out["gate_status"] == "blocked"
    assert len(out["faltas_esquema"]) == 9
    assert len(out["gate_errors"]) == 9
    # proposta deve estar OK
    res2 = subprocess.run([sys.executable, str(_REPO / "tools/validar_9_campos.py"), "--spec", str(_REPO / "projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json"), "--json"],
                          capture_output=True, text=False)
    stdout2 = res2.stdout.decode("utf-8", errors="replace")
    out2 = json.loads(stdout2)
    assert out2["gate_status"] == "ready"
    assert out2["esquema_ok"] is True
    assert out2["can_start_loop2"] is True


def test_g19_gerar_sidecar_extraido_do_framework():
    """G19: tools/gerar_sidecar.py deve extrair peso/Mcol do framework e gerar sidecar com 0.0% de divergência."""
    import pathlib, json, subprocess, sys, tempfile, shutil
    # caso ready (proposta) deve gerar sidecar com peso 23206 e Mcol 235.99
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="test_gerar_sidecar_"))
    out = tmp / "sidecar.json"
    try:
        res = subprocess.run([sys.executable, str(_REPO / "tools/gerar_sidecar.py"),
                              "--spec", str(_REPO / "projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json"),
                              "--out", str(out),
                              "--fonte", "Memorial Teste CREA 999 ART pg 1"],
                             capture_output=True, text=False)
        stdout = res.stdout.decode("utf-8", errors="replace")
        assert res.returncode == 0, f"gerar_sidecar.py falhou: {stdout[:500]} {res.stderr.decode('utf-8', errors='replace')[:500]}"
        assert out.is_file()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["valores_referencia"]["peso_aco_primario_kg"] == 23206.0
        assert data["valores_referencia"]["Mcol_kNm"] == 235.99
        assert "HEB280" in data["valores_referencia"]["perfis"]["coluna"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # caso blocked deve falhar com código 3
    res2 = subprocess.run([sys.executable, str(_REPO / "tools/gerar_sidecar.py"),
                           "--spec", str(_REPO / "projects/galpao-sjb/project-spec.json"),
                           "--out", str(tmp / "should_not_exist.json")],
                          capture_output=True, text=False)
    assert res2.returncode == 3, f"gerar_sidecar.py deveria falhar com blocked (3), veio {res2.returncode}"


def test_g19_quarto_caso_1_comando_output():
    """G19: python -m validacao_sistema_g15 deve imprimir G19 quarto caso em 1 comando (promessa da REVISAO)."""
    import subprocess, sys, pathlib, tempfile
    # roda o harness como documentado em QUARTO-CASO-1-COMANDO.md (inventario nomeado G30)
    #
    # D81: a saida vai para ARQUIVO, nao para PIPE. Com `capture_output=True` a
    # suite completa sob `-n 4` travou 900 s aqui: o processo filho JA tinha
    # saido (returncode 1) e mesmo assim `communicate` ficou preso porque a
    # ponta de escrita do pipe continuava aberta - a thread leitora nunca via
    # EOF. Redirecionar para arquivo elimina a dependencia de EOF do pipe, e o
    # timeout passa a medir o tempo do filho, nao a vida de um handle. O
    # harness sozinho leva ~123 s; o teto largo cobre carga de maquina, mas o
    # veredito nao depende mais dela.
    with tempfile.TemporaryDirectory() as td:
        fout = pathlib.Path(td) / "harness.out"
        ferr = pathlib.Path(td) / "harness.err"
        with open(fout, "wb") as fo, open(ferr, "wb") as fe:
            res = subprocess.run([sys.executable, "-m", "validacao_sistema_g15"],
                                 cwd=str(_GALPAO),
                                 stdout=fo, stderr=fe, timeout=900)
        stdout = fout.read_bytes().decode("utf-8", errors="replace")
        stderr = ferr.read_bytes().decode("utf-8", errors="replace")
    assert res.returncode == 0, f"validacao_sistema_g15 falhou: {stdout[:1000]} {stderr[:500]}"
    # deve conter resumo G19/G30 e TODOS PASSARAM (inventario nomeado)
    assert "G19 quarto caso" in stdout, f"output deve conter 'G19 quarto caso', veio: {stdout[-2000:]}"
    assert "G19: AGUARDANDO OBRA REAL" in stdout or "G19: SJB READY" in stdout
    assert "TODOS PASSARAM" in stdout
    # G30: deve conter procedencia completa
    assert "G30" in stdout or "procedencia" in stdout.lower()
    # verificar que QUARTO-CASO-1-COMANDO.md existe e documenta o comando
    qcaso = _REPO / "docs/validacao_g15/QUARTO-CASO-1-COMANDO.md"
    assert qcaso.is_file()
    assert "python -m validacao_sistema_g15" in qcaso.read_text(encoding="utf-8")
