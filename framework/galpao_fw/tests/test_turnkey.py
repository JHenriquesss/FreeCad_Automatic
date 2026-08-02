"""Orquestrador-mestre TURNKEY (galpao_turnkey): consolidacao dos verticais num
unico rodar(spec). Verifica propagacao da geometria comum, agregacao do ATENDE
global (AND), pulo seguro do vertical de aco sem out_dir e ISOLAMENTO de falha de
uma disciplina (nao derruba as demais). Tudo PURO -> CI (nao invoca FreeCAD nem o
vertical de aco, que escreve arquivos)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_turnkey as tk


def _spec_concreto_ok():
    return {"vao": 10.0, "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
            "s1": 1.0, "s3": 1.0, "G_roof": 0.30, "Q_roof": 0.25,
            "fck": 30e3, "fyk": 500e3, "sigma_solo_adm": 250.0}


def _spec_eletrico():
    return {"tensao_V": 380.0,
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}}


def _spec_incendio():
    return {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0}}


def _spec_mestre(**kw):
    b = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
         "concreto": _spec_concreto_ok(), "eletrico": _spec_eletrico(),
         "incendio": _spec_incendio()}
    b.update(kw)
    return b


def test_selftest():
    tk._selftest()


def test_tres_verticais_executam_e_atende():
    R = tk.rodar(_spec_mestre())
    assert set(R["executadas"]) == {"concreto", "eletrico", "incendio"}
    assert R["ATENDE"] is True and R["reprovados"] == []


def test_geometria_comum_propaga_para_LWH():
    # incendio/eletrico recebem geometria={L,W,H} a partir da comum
    R = tk.rodar(_spec_mestre())
    inc = R["disciplinas"]["incendio"]["raw"]
    assert inc["spec"]["C"] == 40.0 and inc["spec"]["L"] == 20.0 and inc["spec"]["H"] == 6.0
    assert inc["gates"]["iluminacao_emergencia"]["N_aclaramento"] == 6


def test_geometria_aceita_dialeto_LWH():
    # geometria comum informada como {L,W,H} deve ser entendida
    R = tk.rodar(_spec_mestre(geometria={"L": 60.0, "W": 25.0, "H": 8.0}))
    assert R["geometria"] == {"comprimento": 60.0, "vao": 25.0, "pe_direito": 8.0}


def test_disciplina_nao_sobrescreve_geometria_propria():
    # concreto trouxe vao=10; a comum (vao=20) NAO sobrescreve. A viga de 10 m
    # ATENDE em concreto armado (a de 20 m viraria protendida) -> confirma o vao usado.
    R = tk.rodar(_spec_mestre())
    assert R["disciplinas"]["concreto"]["ATENDE"] is True


def test_veredito_global_e_and():
    # forcar o eletrico a reprovar (carga gigante sem subestacao adequada) -> global reprova
    R = tk.rodar(_spec_mestre(eletrico={"tensao_V": 380.0,
                 "cargas": {"motores": [{"P_cv": 300.0, "eta": 0.9, "Fp": 0.85, "n": 60}],
                            "iluminacao_kW": 50.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
                 "alimentador": {"L_km": 0.05}}))
    if R["disciplinas"]["eletrico"]["ATENDE"] is False:
        assert R["ATENDE"] is False and "eletrico" in R["reprovados"]


def test_aco_sem_outdir_e_pulado():
    R = tk.rodar(_spec_mestre(aco={"qualquer": 1}))
    d = R["disciplinas"]["aco"]
    assert d["rodou"] is False and d["ATENDE"] is None
    assert "aco" in R["puladas"] and "requer out_dir" in d["nota"]
    # aco pulado nao entra no veredito global
    assert R["ATENDE"] is True


def test_falha_de_disciplina_fica_isolada():
    R = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
                  "incendio": _spec_incendio(), "eletrico": "spec_invalido"})
    assert R["disciplinas"]["eletrico"]["rodou"] is False
    assert "erro" in R["disciplinas"]["eletrico"]
    assert R["disciplinas"]["incendio"]["rodou"] is True     # a outra seguiu
    assert R["ATENDE"] is False                              # a quebrada reprova


def test_disciplina_ausente_nao_aparece():
    R = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
                  "eletrico": _spec_eletrico()})
    assert "concreto" not in R["disciplinas"] and "incendio" not in R["disciplinas"]
    assert R["executadas"] == ["eletrico"]


def test_relatorio_pt_lista_disciplinas():
    txt = tk.relatorio_pt(tk.rodar(_spec_mestre()))
    assert "TURNKEY" in txt and "RESULTADO GLOBAL: ATENDE" in txt
    assert "concreto" in txt.lower() and "incendio" in txt.lower()
    assert "6,0 m" in txt                                    # virgula decimal pt-BR


def test_nenhuma_disciplina_nao_atende():
    R = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0}})
    assert R["executadas"] == [] and R["ATENDE"] is False    # nada executado != ATENDE vazio
