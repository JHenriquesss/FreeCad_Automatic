"""D172 - auditoria do lote G137-G142: o que o diff do lote deixou passar.

Medido (2026-09-14, arvore f22dfe9, fontes vivas):
1. `desenho_incendio.detalhes_hidrantes_rotas_svg(..., nivel_unico=True)`
   (PE-IN-02 do galpao, G138) herdava o `int(N or 0) or 1` do predio: com
   hidrantes nao calculados (spec sem `hidrantes`) ou N=0 a folha desenhava
   "HID-1 (terreo)", escrevia "1 hidrante(s)" e "RESERVA DE INCENDIO 0.0 m3"
   - numero inventado ao lado da caixa que diz "nao calculados" (medido: 1
   simbolo nos dois casos; N=3 dava 3). Saturacao silenciosa.
2. `galpao_seguranca_incendio.montar_pranchas` (rota SVG, a de producao):
   qualquer excecao na INC03 devolvia `{"erro"}` e a disciplina inteira
   virava falha - INC01/INC02 ja gravadas saiam do status. O
   `test_hidrantes_g138.test_04` congelava esse `erro` (baseline do defeito).
3. A causa da folha que caiu (`locacao_erro` da PE04, e agora
   `detalhes_erro` da INC03) nunca chegava ao motivo da pulada: o laco do
   G93 escrevia so o motivo generico.
4. `galpao_concreto.gerar_prancha_locacao` carimbava `fck_MPa` com default
   30 quando o spec do resultado nao trazia o valor (a conta le
   `r["spec"]["fck_MPa"]` direto, sem default).

Convencoes do BACKLOG: vermelho por injecao em tmp_path (copia do fonte,
nunca o repo), um assert so por teste, fonte independente (o calculo).
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

_SIMBOLO = re.compile(r"HID-\d+ \(terreo\)")


def _folha(di, hidrantes):
    inc, est, aus = di.adaptar_galpao_para_detalhes({"hidrantes": hidrantes})
    return di.detalhes_hidrantes_rotas_svg(inc, est, ausencias=aus,
                                           nivel_unico=True)


def _gaps_hidrantes(di):
    """Um por um: simbolos desenhados == N do calculo (0 sem calculo)."""
    gaps = []
    casos = (("sem hidrantes", None, 0),
             ("N=0", {"N_hidrantes": 0, "tipo": 2,
                      "reserva_incendio_m3": 0.0}, 0),
             ("N=3", {"N_hidrantes": 3, "tipo": 2,
                      "reserva_incendio_m3": 36.0}, 3))
    for nome, hid, esperado in casos:
        svg = _folha(di, hid)
        n = len(_SIMBOLO.findall(svg))
        if n != esperado:
            gaps.append("%s: %d simbolo(s) HID desenhado(s), calculo da %d"
                        % (nome, n, esperado))
        if hid is None and "RESERVA DE INCENDIO 0.0 m3" in svg:
            gaps.append("%s: reserva 0.0 m3 inventada" % nome)
        if esperado == 0 and "nenhum simbolo" not in svg:
            gaps.append("%s: folha nao diz que nao desenhou hidrante" % nome)
    return gaps


def test_01_hidrantes_nao_calculados_nao_viram_simbolo(tmp_path):
    """Lado bom no fonte vivo; lado vermelho numa copia com a guarda
    desligada (o `or 1` volta a desenhar HID-1)."""
    import xml.etree.ElementTree as ET

    import desenho_incendio as di
    from desenho_svg_base import confere_folha_svg

    gaps = ["vivo: " + g for g in _gaps_hidrantes(di)]
    for hid in (None, {"N_hidrantes": 0, "tipo": 2,
                       "reserva_incendio_m3": 0.0}):
        svg = _folha(di, hid)
        ET.fromstring(svg)
        guarda = confere_folha_svg(svg)
        if not guarda.get("ok"):
            gaps.append("guarda reprova a folha sem hidrantes: %r" % (guarda,))
    fonte = open(os.path.join(GALPAO, "desenho_incendio.py"),
                 encoding="utf-8").read()
    marca = "        if not n_decl:"
    if fonte.count(marca) != 1:
        gaps.append("marca da guarda D172 nao achada 1x no fonte")
    else:
        copia = tmp_path / "desenho_incendio_injetado.py"
        copia.write_text(fonte.replace(marca, "        if False:"),
                         encoding="utf-8")
        spec = importlib.util.spec_from_file_location("di_injetado_d172",
                                                      str(copia))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not _gaps_hidrantes(mod):
            gaps.append("injecao (guarda desligada) nao foi acusada")
    assert not gaps, "D172 hidrantes:\n%s" % "\n".join("  - " + g for g in gaps)


def test_02_incendio_inc03_que_cai_nao_derruba_inc01_inc02(tmp_path,
                                                          monkeypatch):
    """A INC03 que cai fica nomeada (`detalhes_erro`) e as outras duas
    seguem no status; a causa chega ao motivo da PE-IN-02 pulada."""
    import desenho_incendio as di
    import galpao_adapter as ga
    import galpao_seguranca_incendio as gsi

    r = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidrantes": {"ocupacao": "industrial_I2"}})
    gaps = []

    def emissor_morto(*_a, **_k):
        raise RuntimeError("emissor de detalhes desligado (injecao D172)")

    monkeypatch.setattr(di, "detalhes_hidrantes_rotas_svg", emissor_morto)
    res = gsi.montar_pranchas(r, str(tmp_path / "morto"))
    if res.get("erro") or not res.get("ok"):
        gaps.append("INC03 caida derrubou a disciplina: %r" % (res,))
    if res.get("pranchas") != ["INC01_PLANTA", "INC02_RESUMO"]:
        gaps.append("INC01/INC02 fora do status: %r" % (res.get("pranchas"),))
    for arq in res.get("arquivos") or []:
        if not os.path.getsize(arq):
            gaps.append("arquivo vazio: %s" % arq)
    if "injecao D172" not in str(res.get("detalhes_erro")):
        gaps.append("causa da INC03 nao nomeada: %r" % (res,))
    indice = [{"codigo": "PE-IN-01", "titulo": "Planta"},
              {"codigo": "PE-IN-02", "titulo": "Detalhes"}]
    puladas = ga._conferir_indice_galpao(
        indice, ga._PRANCHA_ARQUIVO_GALPAO, ["INC01_PLANTA.pdf"],
        causas={"PE-IN-02": res.get("detalhes_erro")})
    motivos = {p["prancha"]: p["motivo"] for p in puladas}
    if "injecao D172" not in motivos.get("INC03_DETALHES.pdf", ""):
        gaps.append("causa fora do motivo da pulada: %r" % (puladas,))
    sem_causa = ga._conferir_indice_galpao(
        indice, ga._PRANCHA_ARQUIVO_GALPAO, ["INC01_PLANTA.pdf"])
    if "causa proxima" in sem_causa[0]["motivo"]:
        gaps.append("sem causa medida o motivo inventou uma: %r" % (sem_causa,))
    assert not gaps, "D172 incendio:\n%s" % "\n".join("  - " + g for g in gaps)


def test_03_causas_saem_dos_status_das_disciplinas():
    """`_causas_folhas_galpao` le as duas chaves dos status (fonte: o que
    montar_pranchas de concreto/incendio gravam), e nada sem elas."""
    import galpao_adapter as ga

    gaps = []
    vivas = ga._causas_folhas_galpao(
        {"concreto": {"ok": True, "locacao_erro": "ValueError: sem sapata"},
         "incendio": {"ok": True, "detalhes_erro": "RuntimeError: x"}})
    if vivas != {"PE-CO-04": "ValueError: sem sapata",
                 "PE-IN-02": "RuntimeError: x"}:
        gaps.append("causas mal lidas: %r" % (vivas,))
    if ga._causas_folhas_galpao({"concreto": {"ok": True}, "incendio": None}):
        gaps.append("sem erro nos status nao ha causa")
    assert not gaps, "D172 causas:\n%s" % "\n".join("  - " + g for g in gaps)


def test_04_pe04_de_reserva_nao_carimba_fck_por_default(tmp_path):
    """Sem `fck_MPa` no spec do resultado a PE04 recusa (a conta le direto,
    sem default); com o valor, a folha sai. Medido: o carimbo da rota pura
    nao imprime o material (texto da pagina sem C30/C35), entao o default
    30 era morto na folha - o teste cobra a recusa, nao um texto que nao
    existe."""
    import copy

    import galpao_concreto as gc

    r = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
                  "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
                  "G_roof": 0.30, "Q_roof": 0.25, "fck": 35e3, "fyk": 500e3,
                  "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"})
    spec = {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7,
            "sigma_solo_adm": 250.0}
    gaps = []
    pdf = gc.gerar_prancha_locacao(r, str(tmp_path / "bom"), spec)
    if not os.path.getsize(pdf):
        gaps.append("com fck no resultado a PE04 devia sair: %r" % (pdf,))
    sem = copy.deepcopy(r)
    del sem["spec"]["fck_MPa"]
    try:
        gc.gerar_prancha_locacao(sem, str(tmp_path / "sem"), spec)
        gaps.append("sem fck_MPa no resultado a PE04 carimbou um default")
    except KeyError:
        pass
    assert not gaps, "D172 fck:\n%s" % "\n".join("  - " + g for g in gaps)
