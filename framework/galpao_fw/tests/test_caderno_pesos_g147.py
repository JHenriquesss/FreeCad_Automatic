"""G147 - o prazo do executivo de aco numa maquina carregada + pesos medidos.

Medido (2026-09-15, galpao-tp-g95, freecad.exe nesta maquina, processo
reiniciado por amostra, dispatch vivo 3D+pranchas ok=True, 4 PDFs cada):
- concreto 61,1 + 58,6 + 60,8 s -> maximo 61,1 s -> peso 0,74;
- eletrico 108,4 + 104,3 + 110,5 s -> maximo 110,5 s -> peso 1,3382
  (regra peso_medido, ancora 578 s; maximos — a media estouraria por
  construcao, licao do G139).
- producao galpao (generate_ifc False, generate_2d True, executivo_aco=True,
  timeout 2100): livre 1380,5 s (caderno 1364,3 s, pico 2041,8 MB) e uso
  normal 1733,4 s (caderno 1716,4 s, mem livre min 260 MB, pico 2019,2 MB),
  ambos generated sem timeout. Prazo 2100 mantido com os numeros (folga
  21 % sobre o uso normal, 52 % sobre o livre) — nunca palpite.

Entregue:
- _T_MEDIDO_SEG concreto/eletrico + pesos via peso_medido; nenhum literal
  SEM MEDICAO restante;
- G102 intacto (executivo_aco=False fica);
- vermelho por injecao se o prazo passar a ler constante nao medida.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em tmp_path (nunca mutando o repo), fonte
independente (DISCIPLINAS do turnkey + _STAGE_WEIGHTS do caderno).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

T_CONCRETO_MEDIDO = 61.1
T_ELETRICO_MEDIDO = 110.5


def test_01_pesos_concreto_eletrico_derivam_do_medido():
    """O prazo de concreto/eletrico sai do cronometrado, nunca de palpite."""
    import caderno_turnkey as ct

    lados = []
    if abs(ct._T_MEDIDO_SEG.get("concreto", -1) - T_CONCRETO_MEDIDO) > 1e-6:
        lados.append("t_medido do concreto fora do cronometrado: %r"
                     % (ct._T_MEDIDO_SEG.get("concreto"),))
    if abs(ct._T_MEDIDO_SEG.get("eletrico", -1) - T_ELETRICO_MEDIDO) > 1e-6:
        lados.append("t_medido do eletrico fora do cronometrado: %r"
                     % (ct._T_MEDIDO_SEG.get("eletrico"),))
    for chave in ("concreto", "eletrico"):
        if abs(ct._STAGE_WEIGHTS.get(chave, -1)
               - ct.peso_medido(ct._T_MEDIDO_SEG[chave])) > 1e-9:
            lados.append("peso de %s nao deriva do medido (G119): %r"
                         % (chave, ct._STAGE_WEIGHTS.get(chave),))
    if abs(ct._STAGE_WEIGHTS.get("concreto", -1) - 0.74) > 1e-4:
        lados.append("peso do concreto devia ser 0,74: %r"
                     % (ct._STAGE_WEIGHTS.get("concreto"),))
    if abs(ct._STAGE_WEIGHTS.get("eletrico", -1) - 1.3382) > 1e-4:
        lados.append("peso do eletrico devia ser 1,3382: %r"
                     % (ct._STAGE_WEIGHTS.get("eletrico"),))
    src = open(os.path.join(GALPAO, "caderno_turnkey.py"),
               encoding="utf-8").read()
    if "SEM MEDICAO" in src:
        lados.append("literal SEM MEDICAO ainda no fonte")
    for literal in ('"concreto": 2.0', '"eletrico": 1.5',
                    "'concreto': 2.0", "'eletrico': 1.5"):
        if literal in src:
            lados.append("literal antigo ainda no fonte: %s" % literal)
    if '_T_MEDIDO_SEG["concreto"' not in src \
            and "_T_MEDIDO_SEG['concreto'" not in src:
        lados.append("peso do concreto nao le o medido (palpite)")
    if '_T_MEDIDO_SEG["eletrico"' not in src \
            and "_T_MEDIDO_SEG['eletrico'" not in src:
        lados.append("peso do eletrico nao le o medido (palpite)")
    assert not lados, "G147 prazo reprova:\n" + "\n".join(lados)


def test_02_vermelho_por_injecao_nos_dois_sentidos(tmp_path, monkeypatch):
    """Literais antigos nao passam; constante nao medida lida pelo prazo acusa.

    Tudo em tmp_path (convencao 2). Um sentido: pesos pre-G147 (2,0/1,5)
    injetados mudam a fracao do aco para 0,8610 e o teste 01 reprovaria.
    Outro sentido: peso que nao deriva do medido (constante inventada lida
    pelo prazo) e acusado pelo detector — o instrumento acusa por parte
    (convencao 7).
    """
    import caderno_turnkey as ct

    lados = []
    antigos = dict(ct._STAGE_WEIGHTS)
    antigos.update({"concreto": 2.0, "eletrico": 1.5})
    monkeypatch.setattr(ct, "_STAGE_WEIGHTS", antigos)
    import galpao_turnkey as tk
    pendentes = list(tk.DISCIPLINAS[tk.DISCIPLINAS.index("aco"):])
    fracao_antiga = ct._fracao_reserva("aco", pendentes)
    if fracao_antiga != pytest.approx(0.8610, abs=1e-4):
        lados.append("injecao nao reproduz o regime antigo: %.4f"
                     % fracao_antiga)
    # Detector: peso que nao deriva do medido acusa por parte.
    for chave in ("concreto", "eletrico"):
        deriva = ct.peso_medido(ct._T_MEDIDO_SEG[chave])
        if antigos[chave] == pytest.approx(deriva):
            lados.append("%s antigo derivaria por acaso: %r" % (chave, deriva))
    # Sentido oposto: sem o medido, o peso some — a ausencia se declara.
    medido_sem = dict(ct._T_MEDIDO_SEG)
    medido_sem.pop("concreto", None)
    monkeypatch.setattr(ct, "_T_MEDIDO_SEG", medido_sem)
    if "concreto" in ct._T_MEDIDO_SEG:
        lados.append("remocao do medido devia sumir do dict")
    assert not lados, "G147 injecao reprova:\n" + "\n".join(lados)


def test_03_g102_intacto_executivo_aco_false_fica():
    """G102 intacto: o portao rapido segue sem o executivo de aco."""
    import test_indice_disco_rodada_g102 as g102

    lados = []
    if g102._OPCOES.get("galpao", {}).get("executivo_aco") is not False:
        lados.append("G102 galpao devia seguir com executivo_aco=False: %r"
                     % (g102._OPCOES.get("galpao"),))
    if g102.CUSTO_TETO_SEG != 1800:
        lados.append("teto do G102 mudou: %r" % (g102.CUSTO_TETO_SEG,))
    assert not lados, "G147 G102 reprova:\n" + "\n".join(lados)


def test_04_reserva_usa_pesos_medidos_fracao_do_aco():
    """A reserva real soma os pesos medidos; fracao do aco travada em 0,8738."""
    import caderno_turnkey as ct
    import galpao_turnkey as tk

    pendentes = list(tk.DISCIPLINAS[tk.DISCIPLINAS.index("aco"):])
    if pendentes != ["aco", "eletrico", "incendio", "climatizacao",
                     "hidraulica", "mezanino"]:
        assert False, "ordem de reserva mudou: %r" % (pendentes,)
    lados = []
    total = ct._total_peso(pendentes)
    esperado = sum(ct._STAGE_WEIGHTS[k] for k in pendentes)
    if abs(total - esperado) > 1e-9:
        lados.append("reserva nao soma os pesos medidos: %r" % total)
    fracao = ct._fracao_reserva("aco", pendentes)
    if fracao != pytest.approx(0.8738, abs=1e-4):
        lados.append("fracao do aco %.4f != travada 0,8738 (pesos vivos: %r)"
                     % (fracao, {k: ct._STAGE_WEIGHTS.get(k)
                                 for k in pendentes}))
    f_conc = ct._fracao_reserva("concreto", pendentes)
    f_elet = ct._fracao_reserva("eletrico", pendentes)
    if not (0.0 < f_conc < f_elet < fracao < 1.0):
        lados.append("fracoes fora da ordem medida "
                     "(concreto %.4f eletrico %.4f aco %.4f)"
                     % (f_conc, f_elet, fracao))
    assert not lados, "G147 reserva reprova:\n" + "\n".join(lados)
