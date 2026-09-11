"""G97 - o portao que escondia o portao.

Contexto: test_09_cobertura_todo_py_varrido_ou_isento tinha quatro asserts
independentes em sequencia (faltando, sobrando, sem_motivo, ausentes); o
primeiro que estourava impedia a avaliacao dos outros tres. O portao do
G77 ficou vermelho desde o proprio commit fb53107 e ninguem viu: o
sobrando (a isencao de desenho_svg_base.py que virou nome morto, porque a
prosa da linha 229 passou a casar com a VALIDADE_RE) estava escondido
atras do faltando. O padrao se repetia em test_guardas_d86_g69.py,
test_folhas_g77.py, test_defaults_veredito_g75.py e no G91.

1. FERRAMENTA (varredura_asserts_sequencia.py, mesma familia de AST do
   G48/G51/G75/G83): para cada `def test_*` em tests/**/test_*.py que seja
   portao de censo/cobertura (nome com censo|varrido_ou_isento|
   coberta_ou_isenta|baseline|portao_*_tipologia|indice_disco|toda_folha, ou
   corpo que chama confere_cobertura|censo_de_folhas|chaves_desguardadas|
   conferir_indice_disco), acusa 2+ asserts independentes no mesmo portao.
   Guard clause (`assert r is not None` antes de `assert r["x"] == 3`) e
   dependencia, nao mascaramento: entra em ISENTAS_SEQUENCIA com motivo
   escrito (isencao sem motivo e silencio, nao triagem).
2. RECEITA: coletar todos os lados, montar uma mensagem unica e falhar uma
   vez so, com o relatorio completo. Aplicada aos portoes G51, G69, G75,
   G77, G83 e G91 (este arquivo trava que continuam de assert unico).
3. BASELINE nos dois sentidos: portao novo com asserts em sequencia e
   acusado (test_03, em tmp_path); os ja corrigidos ficam verdes (test_02).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_asserts_sequencia as va


def _seq():
    return {(d["arquivo"], d["funcao"]) for d in va.varredura()
            if d["classe"] == "ASSERTS_SEQUENCIA"}


# Portoes convertidos a mensagem unica neste goal. Entrada nova aqui = o
# defeito voltando (dois asserts em sequencia num portao de censo).
PORTOES_G97 = {
    ("test_varredura_faixa_validade_g51.py",
     "test_08_baseline_desguardadas_nos_dois_sentidos"),
    ("test_varredura_faixa_validade_g51.py",
     "test_09_cobertura_todo_py_varrido_ou_isento"),
    ("test_guardas_d86_g69.py",
     "test_censo_das_guardas_fecha_nos_DOIS_sentidos"),
    ("test_defaults_veredito_g75.py",
     "test_02_baseline_nos_dois_sentidos"),
    ("test_folhas_g77.py",
     "test_censo_encontra_as_folhas_da_arvore"),
    ("test_folhas_g77.py",
     "test_toda_folha_da_arvore_esta_coberta_ou_isenta"),
    ("test_guardas_um_eixo_g83.py",
     "test_02_baseline_nos_dois_sentidos"),
    ("test_indice_disco_g91.py",
     "test_02_baseline_g91_nos_dois_sentidos"),
    ("test_indice_disco_g91.py",
     "test_05_entrada_malformada_grita_e_laco_quebrado_e_nomeado"),
    ("test_escada_casa_g42.py",
     "test_varredura_casa_limpa_e_baseline_zerada"),
}


def test_01_ferramenta_enxerga_e_so_classe_conhecida():
    tudo = va.varredura()
    assert all(set(d) == {"arquivo", "funcao", "linha", "classe"}
               for d in tudo)
    assert {d["classe"] for d in tudo} <= {"ASSERTS_SEQUENCIA",
                                          "GUARD_CLAUSE"}
    # Fonte independente (convencao 5): a contagem via AST direto confirma
    # que a lente nao deriva do proprio resultado.
    import ast
    import pathlib
    n_asserts = 0
    for arq in sorted((pathlib.Path(GALPAO) / "tests").rglob("test_*.py")):
        try:
            arv = ast.parse(arq.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        n_asserts += sum(isinstance(n, ast.Assert) for n in ast.walk(arv))
    assert n_asserts > 100, "lente cega: %d asserts na suite?" % n_asserts


def test_02_portoes_corrigidos_ficam_verdes():
    """Baseline no sentido verde: os portoes da lista nao tem mais sequencia.

    Um assert so por portao, com todos os lados na mensagem (a receita).
    """
    seq = _seq()
    reabriram = sorted(seq & PORTOES_G97)
    res = va.confere()
    lados = []
    if reabriram:
        lados.append("portao voltou a ter asserts em sequencia: %r"
                     % (reabriram,))
    if not res["OK"]:
        lados.append(va.relatorio_pt(res))
    assert not lados, "G97 reabriu:\n" + "\n".join(lados)


_GAP_SEQ = [
    "import varredura_faixa_validade as vf",
    "",
    "def test_09_cobertura_todo_py_varrido_ou_isento():",
    "    r = vf.confere_cobertura()",
    "    assert not r['faltando'], r['faltando']",
    "    assert not r['sobrando'], r['sobrando']",
    "",
]

_GAP_GUARD = [
    "def test_09_cobertura_todo_py_varrido_ou_isento():",
    "    r = {'item': {'x': 1}}",
    "    assert r is not None",
    "    assert r['item']['x'] == 1",
    "",
]

_GAP_OK = [
    "import varredura_faixa_validade as vf",
    "",
    "def test_09_cobertura_todo_py_varrido_ou_isento():",
    "    r = vf.confere_cobertura()",
    "    assert r['OK'], (r['faltando'], r['sobrando'])",
    "",
]


def test_03_vermelho_por_injecao_nos_dois_sentidos(tmp_path):
    """Prova por injecao em diretorio temporario (nunca mutando o repo).

    Sentido vermelho: portao novo com dois asserts independentes em
    sequencia e acusado. Guard clause (dependente) nao e o defeito:
    sai como GUARD_CLAUSE, nunca como sequencia. Sentido verde: o mesmo
    portao com um assert so passa limpo.
    """
    gap = tmp_path / "test_gap_seq.py"
    gap.write_text("\n".join(_GAP_SEQ), encoding="utf-8")
    achados = {(d["arquivo"], d["funcao"], d["classe"])
               for d in va.varredura(raiz=str(tmp_path))}
    assert ("test_gap_seq.py",
            "test_09_cobertura_todo_py_varrido_ou_isento",
            "ASSERTS_SEQUENCIA") in achados, achados
    res = va.confere(raiz=str(tmp_path), isentos={})
    assert (("test_gap_seq.py",
             "test_09_cobertura_todo_py_varrido_ou_isento")
            in res["sequencias"]) and not res["OK"], res
    # Guard clause: dependencia legitima, isenta com motivo escrito.
    (tmp_path / "test_gap_seq.py").unlink()
    guard = tmp_path / "test_gap_guard.py"
    guard.write_text("\n".join(_GAP_GUARD), encoding="utf-8")
    achados_g = {(d["arquivo"], d["funcao"], d["classe"])
                 for d in va.varredura(raiz=str(tmp_path))}
    assert ("test_gap_guard.py",
            "test_09_cobertura_todo_py_varrido_ou_isento",
            "GUARD_CLAUSE") in achados_g, achados_g
    assert not [d for d in va.varredura(raiz=str(tmp_path))
                if d["classe"] == "ASSERTS_SEQUENCIA"], achados_g
    # Verde: mensagem unica passa limpa.
    guard.unlink()
    ok = tmp_path / "test_gap_ok.py"
    ok.write_text("\n".join(_GAP_OK), encoding="utf-8")
    assert va.varredura(raiz=str(tmp_path)) == []
    assert va.confere(raiz=str(tmp_path), isentos={})["OK"]
    # Isencao sem motivo e silencio, nao triagem.
    res_m = va.confere(
        raiz=str(tmp_path),
        isentos={("test_gap_ok.py",
                  "test_09_cobertura_todo_py_varrido_ou_isento"): "   "})
    assert (res_m["sem_motivo"]
            == [("test_gap_ok.py",
                 "test_09_cobertura_todo_py_varrido_ou_isento")]) \
        and not res_m["OK"], res_m


_Faixa_SEM_GUARDA = [
    "def verifica_algo(theta_deg, x):",
    "    # metodo so vale para theta entre 30 e 45 graus",
    "    return {'v': x * theta_deg, 'OK': True}",
]


def test_04_mensagem_unica_nomeia_os_dois_lados(tmp_path):
    """O aceite do G97: a isencao morta do G77, devolvida numa copia em
    tmp_path, aparece na mensagem de falha JUNTO com o outro lado, numa
    rodada so.

    Reproduz o caso real: desenho_svg_base.py produzia chave (a prosa da
    linha 229 casa com a VALIDADE_RE) e a isencao dele virou nome morto
    (sobrando), enquanto um modulo sem faixa e sem isencao e faltando. Com
    asserts em sequencia, o primeiro escondia o segundo; com a receita, os
    dois saem na mesma mensagem.
    """
    import varredura_faixa_validade as vf
    com_faixa = tmp_path / "zz_com_faixa.py"
    com_faixa.write_text("\n".join(_Faixa_SEM_GUARDA) + "\n",
                         encoding="utf-8")
    limpo = tmp_path / "zz_limpo.py"
    limpo.write_text("def soma(a, b):\n    return a + b\n", encoding="utf-8")
    # A isencao morta, devolvida: zz_com_faixa produz chave, logo a isencao
    # dele SOBRA; zz_limpo nao produz chave e nao esta isento, logo FALTA.
    isentos_morta = {"zz_com_faixa.py":
                     "isencao morta devolvida (G77: o modulo produz chave)"}
    r = vf.confere_cobertura(raiz=str(tmp_path), isentos=isentos_morta)
    assert not r["OK"], r
    assert r["faltando"] == ["zz_limpo.py"], r
    assert r["sobrando"] == ["zz_com_faixa.py"], r
    # A receita: um assert so, com os dois lados na mensagem.
    msg = ("cobertura reprova:\n"
           "  faltando: %r\n"
           "  sobrando: %r\n"
           "  sem_motivo: %r\n"
           "  ausentes: %r"
           % (r["faltando"], r["sobrando"], r["sem_motivo"],
              r["ausentes"]))
    assert "zz_limpo.py" in msg and "zz_com_faixa.py" in msg, msg
    assert r["sem_motivo"] == [] and r["ausentes"] == [], r
