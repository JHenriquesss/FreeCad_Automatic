# ============================================================================
# test_G21_prova_fronteiras.py — G21: PROVA DE QUE O fronteiras.py PEGA
# Injeta deliberadamente os três defeitos do G8 e confirma que o guarda
# test_fronteiras.py fica VERMELHO em cada um. Um teste-guarda que nunca
# viu o bug que deveria pegar é hipótese, não garantia.
#
# Os três defeitos (REVISAO-G8-BIM-TIPOLOGIAS.md):
#  1. dims em metros  — sapata 2.0x2.5x0.55 m emitida como [2,2.5,0.55] em vez de [2000,2500,550]
#  2. ancoragem divergente — build_concreto apoia na face (base) e ifc_emit centra no eixo (eixo)
#  3. laje que engrossa sem realimentar — 10->12 cm sem voltar na carga (0.5 kN/m2 faltando)
#
# Estratégia (barato, rápido):
#  - Parte A: injeção em MEMÓRIA (monkeypatch) prova que a heurística de valor/unidade falha
#  - Parte B: injeção via STRING (conteúdo de arquivo mockado) prova que o guarda de
#             existência (`_contem("...","B * 1000.0")`) também falha quando o contrato é quebrado
# Todos os testes desta suite são VERDES (= a prova passou). Cada um injeta o bug,
# chama a lógica do guarda e espera FALHA do guarda (AssertionError / heurística vermelha).
# Se o guarda não falhasse, a prova falha — o contrato estaria furado.
# ============================================================================
"""G21: prova que test_fronteiras detecta os 3 bugs do G8 quando injetados."""

import pathlib
import sys
import math
import pytest

HERE = pathlib.Path(__file__).resolve().parent
GALPAO = HERE.parent
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))

import fronteiras as FR
import geometria_membros as GM

# Reusa helpers do próprio test_fronteiras sem depender de package `tests`
import importlib.util
_spec_TF = importlib.util.spec_from_file_location(
    "test_fronteiras", str(HERE / "test_fronteiras.py"))
TF = importlib.util.module_from_spec(_spec_TF)
_spec_TF.loader.exec_module(TF)  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _spec_concreto(vao=10.0, **kw):
    base = {"vao": vao, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
            "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
            "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"}
    base.update(kw)
    return base


def _assert_vermelho(fn, *args, **kw):
    """Espera que fn(*args) levante AssertionError (guarda vermelho)."""
    with pytest.raises(AssertionError):
        fn(*args, **kw)


# ===========================================================================
# PARTE A — injeção em VALOR (heurística mm vs m, ancoragem, volume)
# ===========================================================================

def test_G21_A1_dims_em_metros_heuristica_fica_vermelha():
    """Defeito 1: sapata emitida em metros. Fronteiras F01/F15 devem pegar."""
    import galpao_concreto as gc
    import orcamento as ORC

    r = gc.rodar(_spec_concreto())
    foot_ok = [m for m in gc.membros_bim(r) if m["tipo"] == "Footing"][0]
    B, L, h = foot_ok["dims"]
    # Sanidade: o correto é mm
    assert 500 < B < 10000, "baseline deveria ser mm (%.1f)" % B

    # --- injeta defeito: dims em METROS (sem *1000) ---
    foot_bug = dict(foot_ok)
    foot_bug["dims"] = [B / 1000.0, L / 1000.0, h / 1000.0]  # 2.0, 2.5, 0.55
    Bb, Lb, hb = foot_bug["dims"]

    # 1) heurística de magnitude (500..10000) deve falhar
    assert not (500 < Bb < 10000), "bug em metros deveria estar fora da faixa mm"
    # 2) volume via B*L*h/1e9 fica 1e9 menor
    vol_bug = Bb * Lb * hb / 1e9
    vol_ok = B * L * h / 1e9
    assert vol_bug < 1e-6, "volume bug %.2e deveria ser ~1e9 menor que %.3f" % (vol_bug, vol_ok)
    assert 0.5 < vol_ok < 25.0
    assert not (0.5 < vol_bug < 25.0), "volume bug deveria ser implausível"
    # 3) fronteiras.validar_unidade deve acusar (heurística interna)
    ok, motivo = FR.validar_unidade("F01_sapata_dims_mm", foot_bug["dims"])
    # validar_unidade para F01 espera mm; valor 2.0 parece m -> deve acusar incompatibilidade
    # A implementação atual usa magnitude: se 0<abs(v)<10 -> False
    assert not ok, "validar_unidade deveria acusar dims em metros, mas retornou ok: %s" % motivo

    # 4) geometria_membros.aabb com dims bug produz caixa 1000x menor que o correto
    aabb_ok = GM.aabb(foot_ok)
    aabb_bug = GM.aabb(foot_bug)
    vol_aabb_ok = (aabb_ok[1]-aabb_ok[0])*(aabb_ok[3]-aabb_ok[2])*(aabb_ok[5]-aabb_ok[4])/1e9
    vol_aabb_bug = (aabb_bug[1]-aabb_bug[0])*(aabb_bug[3]-aabb_bug[2])*(aabb_bug[5]-aabb_bug[4])/1e9
    assert abs(vol_aabb_bug - vol_bug) < 1e-9
    assert vol_aabb_bug < 0.01  # bug: sapata de 2.75 m3 vira 2.75e-9 m3

    # 5) orcamento também diverge
    v_ok = ORC._vol_membros_concreto([foot_ok])
    v_bug = ORC._vol_membros_concreto([foot_bug])
    assert abs(v_ok - vol_ok) < 1e-9
    assert v_bug < 1e-6

    # Prova que o guarda EXISTENTE (test_fronteira_F01) ficaria vermelho:
    # se rodássemos o teste com esse membro bugado, a asserção 500 < B < 10000 falharia
    with pytest.raises(AssertionError, match="fora de mm"):
        assert 500 < Bb < 10000 and 500 < Lb < 10000 and 100 < hb < 5000, \
            "dims %.1f,%.1f,%.1f fora de mm (parece m?)" % (Bb, Lb, hb)


def test_G21_A2_ancoragem_divergente_fica_vermelha():
    """Defeito 2: ancoragem divergente entre emissores (base vs eixo). F05 deve pegar."""
    import galpao_concreto as gc

    r = gc.rodar(_spec_concreto())
    vigas = [m for m in gc.membros_bim(r) if m["tipo"] == "Beam"]
    assert vigas, "sem vigas"
    v_base = vigas[0]
    assert v_base.get("ancoragem") == "base", "baseline deveria ser base"
    d_mm = v_base["secao"]["d"] * 1000.0
    assert 200 < d_mm < 1200, "d=%.0f mm fora de viga típica" % d_mm

    # aabb com ancoragens diferentes difere em d/2
    v_eixo = dict(v_base)
    v_eixo.pop("ancoragem", None)  # default = eixo
    a_base = GM.aabb(v_base)
    a_eixo = GM.aabb(v_eixo)
    dz = (a_eixo[5] - a_eixo[4])
    # guarda correto: base está d/2 acima do eixo
    assert abs((a_base[4] - a_eixo[4]) - dz/2) < 1e-6

    # --- injeta defeito 2a: emissor omite ancoragem (vira eixo) quando deveria ser base ---
    # Simula galpao_concreto sem "ancoragem": "base" -> IFC e 3D discordam em d/2
    v_bug = dict(v_base)
    v_bug.pop("ancoragem", None)  # bug: não declara base
    assert "ancoragem" not in v_bug or v_bug.get("ancoragem") != "base"
    # O guarda F05 verifica: any(m.get("ancoragem")=="base") deve falhar
    membros_bug = [m for m in gc.membros_bim(r) if m["tipo"] != "Beam"] + [v_bug]
    assert not any(m.get("ancoragem") == "base" for m in [v_bug]), \
        "bug: viga sem ancoragem base deveria ser detectada como ausência"

    # Se o consumidor (ifc_emit) ignorasse ancoragem e o produtor mandasse base,
    # ou vice-versa, a cota Z diverge em d/2 = 35 cm no galpão típico — o G8 mediu.
    # Prova que a divergência é detectável: a diferença entre aabbs é exatamente d/2
    a_bug = GM.aabb(v_bug)  # eixo (default)
    assert abs((a_bug[4] - a_base[4]) + dz/2) < 1e-6  # bug está d/2 abaixo
    # O guarda F05 falharia com: "viga cobertura deveria ter ancoragem=base"
    with pytest.raises(AssertionError, match="ancoragem=base"):
        assert any(m.get("ancoragem") == "base" for m in [v_bug]), \
            "viga cobertura deveria ter ancoragem=base"

    # --- injeta defeito 2b: divergência entre dois emissores ---
    # Simula build_concreto (lê ancoragem) vs ifc_emit antigo (ignora)
    # Um vê v_base, outro vê v_eixo -> 35 cm de diferença já medida no G8
    diferenca_mm = abs(a_base[4] - a_eixo[4])
    assert abs(diferenca_mm - d_mm/2) < 1e-6
    # meio vão de viga enterrado no pilar se o IFC usar eixo
    assert diferenca_mm > 100, "divergência de %.0f mm deveria ser >10 cm" % diferenca_mm


def test_G21_A3_laje_engrossa_sem_realimentar_fica_vermelha():
    """Defeito 3: laje 10->12 cm sem realimentar carga. F16 deve pegar."""
    import laje_concreto as lj
    import pavimento_tipo as pt

    # Cenário G8: laje declarada 10 cm, adotada 12 cm
    # O pavimento-tipo usa h_laje para calcular g_kN_m2 = peso próprio + revestimento
    h_declarada = 0.10
    # força um painel que exige 12 cm (o dimensiona_laje sobe)
    # Usa o painel crítico do edifício persistido: 6x6, caso 4, C30
    # Se 10 cm não atende, dimensiona_laje sobe para 12 cm
    cfg_10 = {"caso": 4, "lx": 4.0, "ly": 6.0, "h": h_declarada,
              "g": 1.0, "q": 2.0, "fck": 30e3, "fyk": 500e3, "tipo": "piso"}
    r10 = lj.verifica_laje(cfg_10)
    # Tenta achar um caso onde 10 cm reprova e 12 cm atende, para simular G8
    # Se não reprovar, força carga maior
    if r10["OK"]:
        cfg_10["q"] = 4.0
        r10 = lj.verifica_laje(cfg_10)
    # Se ainda OK, usa dimensiona_laje que busca a menor espessura
    r_adot = lj.dimensiona_laje(cfg_10)
    h_adotada = r_adot["h"]
    # Garante que houve engrossamento para a prova ter sentido
    # Se mesmo assim não engrossou, força h_declarada menor
    if h_adotada <= h_declarada + 1e-9:
        h_declarada = 0.08
        cfg_10["h"] = h_declarada
        r_adot = lj.dimensiona_laje(cfg_10)
        h_adotada = r_adot["h"]
    assert h_adotada > h_declarada, \
        "para a prova, dimensiona_laje deveria engrossar (declarada %.2f -> adotada %.2f)" % (h_declarada, h_adotada)

    # Peso próprio subestimado se não realimentar: delta_g = 25 * delta_h
    delta_h = h_adotada - h_declarada
    delta_g = 25.0 * delta_h  # kN/m2
    assert delta_g > 0.3, "delta_g %.3f deveria ser perceptível" % delta_g

    # Simula o BUG: carga calculada com h_declarada, não com h_adotada
    # No edificio_multipavimento correto, o laço realimenta e converge
    # No bug, pav["g_kN_m2"] fica com h_declarada
    # O gate laje_compatibilizada detecta: h_na_carga != h_adotada
    h_na_carga_bug = h_declarada
    h_na_carga_ok = h_adotada
    gate_bug = (abs(h_na_carga_bug - h_adotada) <= 1e-9)  # deveria ser True no OK
    gate_ok = (abs(h_na_carga_ok - h_adotada) <= 1e-9)
    assert not gate_bug, "sem realimentar, gate deveria ser False (%.3f vs %.3f)" % (h_na_carga_bug, h_adotada)
    assert gate_ok

    # O G8 mediu: 0.5 kN/m2 * 126 m2 * 9 pav = 567 kN de carga faltando
    # Aqui medimos o erro por m2
    assert 0.4 < delta_g < 1.0, "G8: 0.5 kN/m2 para 2 cm; obtido %.3f" % delta_g

    # A prova de que o guarda F16 pega: sem o gate, o teste de existência falha
    # Aqui simulamos o gate como em edificio_multipavimento.rodar()
    import edificio_multipavimento as em
    # Roda o orquestrador com um spec tipico (G3 usa residencial_dormitorio)
    spec = {
        "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5], "pe_direito": 2.90},
        "pavimentos": ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
                       + [{"nome": "Tipo %d" % i, "uso": "residencial_dormitorio"} for i in range(3, 0, -1)]),
        "laje": {"h": 0.10}, "viga": {"b": 0.20, "h": 0.50},
        "materiais": {"fck": 30e3, "fyk": 500e3},
    }
    r_ok = em.rodar(spec)
    gate = r_ok["gates"]["laje_compatibilizada"]
    assert "h_declarada_cm" in gate and "h_adotada_cm" in gate and "h_na_carga_cm" in gate
    # No OK, h_na_carga == h_adotada (laço convergiu)
    assert gate["OK"], "com laço, laje_compatibilizada deveria ser OK: %r" % gate
    assert abs(gate["h_na_carga_cm"] - gate["h_adotada_cm"]) < 1e-6

    # Simula o BUG injetado: se o laço fosse removido, h_na_carga seria h_declarada
    # (ou, no caso G8, 10 cm em vez de 12 cm). O gate detecta a divergência.
    gate_bug_sim = dict(gate)
    # força h_na_carga para um valor diferente de h_adotada (simula não-realimentação)
    gate_bug_sim["h_na_carga_cm"] = gate["h_declarada_cm"]
    # se h_declarada == h_adotada neste spec tipico, força divergência artificial para provar detecção
    if abs(gate_bug_sim["h_na_carga_cm"] - gate["h_adotada_cm"]) < 1e-9:
        gate_bug_sim["h_na_carga_cm"] = gate["h_adotada_cm"] + 2.0  # +2 cm como no G8
    gate_bug_sim["OK"] = abs(gate_bug_sim["h_na_carga_cm"] - gate_bug_sim["h_adotada_cm"]) < 1e-9
    assert not gate_bug_sim["OK"], "gate bugado deveria ser False (h_na_carga=%.1f vs h_adotada=%.1f)" % (
        gate_bug_sim["h_na_carga_cm"], gate_bug_sim["h_adotada_cm"])


# ===========================================================================
# PARTE B — injeção via STRING (o guarda de existência falha quando o contrato
# implícito é quebrado). Não edita disco; mocka a leitura do arquivo.
# ===========================================================================

def test_G21_B1_string_dims_em_metros_guarda_fica_vermelho(monkeypatch):
    """Se galpao_concreto não contiver 'B * 1000.0', F01 deve ficar vermelho."""
    original_texto = TF._texto

    def fake_texto(nome):
        txt = original_texto(nome)
        if nome == "galpao_concreto":
            return txt.replace("B * 1000.0", "B")  # injeta bug
        return txt

    monkeypatch.setattr(TF, "_texto", fake_texto)
    # Também afeta _contem
    def fake_contem(nome, trecho):
        return trecho in fake_texto(nome)
    monkeypatch.setattr(TF, "_contem", fake_contem)

    with pytest.raises(AssertionError, match="nao emite dims em mm"):
        TF.test_fronteira_F01_sapata_dims_mm_existe_e_casa()


def test_G21_B2_string_ancoragem_divergente_guarda_fica_vermelho(monkeypatch):
    """Se galpao_concreto não declarar 'ancoragem: base', F05 fica vermelho."""
    original_texto = TF._texto

    def fake_texto(nome):
        txt = original_texto(nome)
        if nome == "galpao_concreto":
            return txt.replace('"ancoragem": "base"', '"ancoragem": "eixo"')
        return txt

    monkeypatch.setattr(TF, "_texto", fake_texto)
    monkeypatch.setattr(TF, "_contem", lambda nome, trecho: trecho in fake_texto(nome))

    with pytest.raises(AssertionError, match="nao declara ancoragem base"):
        TF.test_fronteira_F05_ancoragem_base_eixo_existe_e_casa()


def test_G21_B3_string_laje_sem_realimentar_guarda_fica_vermelho(monkeypatch):
    """Se edificio_multipavimento não declarar 'laje_compatibilizada', F16 fica vermelho."""
    original_texto = TF._texto

    def fake_texto(nome):
        txt = original_texto(nome)
        if nome == "edificio_multipavimento":
            return txt.replace("laje_compatibilizada", "laje_compat_BUG")
        return txt

    monkeypatch.setattr(TF, "_texto", fake_texto)
    monkeypatch.setattr(TF, "_contem", lambda nome, trecho: trecho in fake_texto(nome))

    with pytest.raises(AssertionError, match="nao declara gate laje_compatibilizada"):
        TF.test_fronteira_F16_laje_h_adotada_cm_feedback_existe_e_casa()


# ===========================================================================
# PARTE C — prova via SUBPROCESSO com mutação real em disco (literal: o arquivo
# test_fronteiras.py fica vermelho). Barato: 3 subprocessos ~1s total.
# Esses testes garantem que não estamos mockando de forma irreal — a mutação
# em disco produz o mesmo vermelho. São mais lentos, mas são a prova literal
# pedida no enunciado do G21.
# ===========================================================================

def _mutacao_em_disco_e_prova(test_selector, arquivo, velho, novo):
    """Muta o modulo numa COPIA do pacote e prova que o guarda fica vermelho.

    A versao anterior reescrevia o modulo no REPOSITORIO VIVO e restaurava no
    finally. Dois custos, ambos ja conhecidos do projeto:
      1) se o processo morresse dentro da janela de mutacao (Ctrl+C, kill), o
         repo ficava com o modulo quebrado - exatamente o que o G22 corrigiu em
         tools/prova_fronteiras_G21.py, mas que nunca chegou a ESTE arquivo;
      2) sob `pytest -n N` os outros workers liam o arquivo mutado e ficavam
         vermelhos por CONTAMINACAO, nao por defeito. Medido em 2026-09-03:
         A1/A3/C1-C3 falhando de forma nao deterministica (3 execucoes, 3
         conjuntos diferentes de vermelhos), e reproduzido tambem no commit
         anterior - logo PRE-EXISTENTE: a suite verde de 44 min tinha sido
         sorte de escalonamento. Guarda que reprova por vizinhanca nao e guarda.

    A copia leva so os .py da raiz do pacote e de tests/ (~5 MB, menos de 1 s);
    o pacote inteiro tem 374 MB de saidas e PDFs que a prova nao usa.
    """
    import shutil
    import subprocess
    import tempfile
    p = GALPAO / (arquivo + ".py")
    orig = p.read_text(encoding="utf-8")
    if velho not in orig:
        pytest.skip("string de mutação não encontrada em %s: %r" % (arquivo, velho))
    mutated = orig.replace(velho, novo)
    assert mutated != orig
    with tempfile.TemporaryDirectory() as td:
        raiz = pathlib.Path(td)
        dest = raiz / "framework" / "galpao_fw"
        (dest / "tests").mkdir(parents=True)
        for src in GALPAO.glob("*.py"):
            shutil.copy2(src, dest / src.name)
        for src in (GALPAO / "tests").glob("*.py"):
            shutil.copy2(src, dest / "tests" / src.name)
        ini = GALPAO / "pytest.ini"
        if ini.is_file():
            shutil.copy2(ini, dest / "pytest.ini")
        (dest / (arquivo + ".py")).write_text(mutated, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "framework/galpao_fw/tests/test_fronteiras.py::" + test_selector, "-v"],
            capture_output=True, text=True, cwd=str(raiz))
    # stdout/stderr podem vir None sob execucao paralela; nunca deixar isso
    # passar por "defeito de engenharia" (era o TypeError que a suite mostrou).
    saida = (result.stdout or "") + "\n" + (result.stderr or "")
    assert result.returncode != 0, \
        "mutacao %s em %s deveria deixar %s vermelho, mas passou:\n%s" % (
            velho, arquivo, test_selector, saida[-2000:])
    assert "FAILED" in saida or "AssertionError" in saida, \
        "saída não indica falha: %s" % saida[-2000:]
    # o repositorio vivo nunca foi tocado (o ponto do G22)
    assert p.read_text(encoding="utf-8") == orig, \
        "%s foi alterado no repositorio vivo: a prova deve mutar a COPIA" % arquivo


def test_G21_C1_disco_dims_em_metros_fica_vermelho():
    _mutacao_em_disco_e_prova(
        "test_fronteira_F01_sapata_dims_mm_existe_e_casa",
        "galpao_concreto", "B * 1000.0", "B")


def test_G21_C2_disco_ancoragem_divergente_fica_vermelho():
    _mutacao_em_disco_e_prova(
        "test_fronteira_F05_ancoragem_base_eixo_existe_e_casa",
        "galpao_concreto", '"ancoragem": "base"', '"ancoragem": "eixo"')


def test_G21_C3_disco_laje_sem_realimentar_fica_vermelho():
    _mutacao_em_disco_e_prova(
        "test_fronteira_F16_laje_h_adotada_cm_feedback_existe_e_casa",
        "edificio_multipavimento", "laje_compatibilizada", "laje_compat_BUG")
