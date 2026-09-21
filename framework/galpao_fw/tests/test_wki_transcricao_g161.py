"""G161 - as 476 celulas WKI conferidas na imagem (D190).

Defeito: `demanda_residencial_enel.py` lia ~476 celulas numericas
transcritas da WKI (F131) sem uma unica conferencia na imagem
(`_MOTOR_TABLE_KVA` 370, `_HEATING_TABLE` 90, `ROOM_MODULES_KVA` 7,
`LOCATION_FACTORS` 4, `_SPECIAL_LIGHTING_POWER_FACTORS` 4,
`_MOTOR_TABLE_MAX_QUANTITY` 1, `_MOTOR_NO_PLATE_KW_PER_CV` 1).
Um erro ja saiu dai (6734fc8: 2,584 kVA onde a coluna de quantidade 2
imprime 2,28 kVA) - defeito de LEITURA (6.2.3.2 consulta por quantidade
consolidada), nao de celula.

Censo na imagem (F131 = WKI-OMBR-MAT-18-0263-INBR-R01, todas as paginas
abertas como IMAGEM, nunca so extracao de texto):
- TABELA 2 (motores trifasicos) + TABELA 3 (monofasicos), p.14: 370/370
  celulas vistas, 0 divergencias. As 3 celulas "estranhas" sao DA FONTE
  e foram mantidas: tri 15CV/qtd4 = 33,29; mono 1 1/2CV/qtd2 = 2,53;
  mono 10CV/qtd7 = 33,41.
- TABELA 1 (aquecimento), p.13: 90/90 celulas vistas (30 linhas x
  minimo + 2 fatores), 0 divergencias. Faixas "26 A 30", "31 A 40",
  "41 A 50", "51 A 60", "61 OU MAIS" viram minimos 26/31/41/51/61.
- Comodos, p.6-7: quarto 1,50 / sala 1,60 / banheiro 2,30 /
  cozinha_1 1,50 / cozinha_2 2,10 / area_servico 1,90 / outros 0,35.
- Localizacao 6.2.2.2, p.7: 1 / 0,88 / 0,75 / 0,55.
- Iluminacao 6.2.3.3, p.8: vapor /0,9; incandescente kW=kVA.
- Item 6.1, p.5: sem placa 1500 W por CV; vapor 0,90 (p.5).
- Leitura 6.2.3.2, p.8: 100% da maior demanda de mesma potencia + 70%
  das demais. Aquecimento (Nota 1, p.13) NAO consolida: cada tipo de
  aparelho separado, soma no fim - o Exemplo 1 (p.29) prova.
- Exemplo resolvido EXISTE: 6.6.1 EXEMPLO 1 p.28-30 (casa Santa Rosa,
  Dc = 23,69 kVA). Fixture no test_03 abaixo.

Guarda (convencao 17): os literais ESPERADO_* deste arquivo sao a
transcricao independente vista na imagem (convencao 5: a prova vem de
fora do modulo - nada aqui e importado de demanda_residencial_enel).
Proxima edicao que trocar uma celula reprova nomeando parte+celula
(convencao 7, por parte). Injecao em tmp_path (convencao 2).
"""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import demanda_residencial_enel as WKI

# Fonte das imagens conferidas (F131).
FONTE = "F131 WKI-OMBR-MAT-18-0263-INBR-R01"

# Transcrição independente da TABELA 2, p.14 (vista na imagem).
ESPERADO_TRI = {
    "1/3": (0.65, 0.98, 1.24, 1.50, 1.76, 1.95, 2.15, 2.34, 2.53, 2.73),
    "1/2": (0.87, 1.31, 1.65, 2.00, 2.35, 2.61, 2.87, 3.13, 3.39, 3.65),
    "3/4": (1.26, 1.89, 2.39, 2.90, 3.40, 3.78, 4.16, 4.54, 4.91, 5.29),
    "1": (1.52, 2.28, 2.89, 3.50, 4.10, 4.56, 5.02, 5.47, 5.93, 6.38),
    "1 1/2": (2.17, 3.26, 4.12, 4.99, 5.86, 6.51, 7.16, 7.81, 8.46, 9.11),
    "2": (2.70, 4.05, 5.13, 6.21, 7.29, 8.10, 8.91, 9.72, 10.53, 11.34),
    "3": (4.04, 6.06, 7.68, 9.29, 10.91, 12.12, 13.13, 14.54, 15.76, 16.97),
    "4": (5.03, 7.55, 9.56, 11.57, 13.58, 15.09, 16.60, 18.11, 19.62, 21.13),
    "5": (6.02, 9.03, 11.44, 13.85, 16.25, 18.86, 19.87, 21.67, 23.48, 25.28),
    "7 1/2": (8.65, 12.98, 16.44, 19.90, 23.36, 25.95, 28.55, 31.14, 33.74, 36.33),
    "10": (11.54, 17.31, 21.93, 26.54, 31.16, 34.62, 38.08, 41.54, 45.01, 48.47),
    "12 1/2": (14.09, 21.14, 26.77, 32.41, 38.04, 42.27, 46.50, 50.72, 54.95, 59.18),
    "15": (16.65, 24.98, 31.63, 33.29, 44.96, 49.95, 54.95, 59.94, 64.93, 69.93),
    "20": (22.10, 33.15, 41.99, 50.83, 59.67, 66.30, 72.93, 79.56, 86.19, 92.82),
    "25": (25.83, 38.75, 49.08, 59.41, 69.74, 77.49, 85.24, 92.99, 100.74, 108.49),
    "30": (30.52, 45.78, 57.99, 70.20, 82.40, 91.56, 100.72, 109.87, 119.03, 128.18),
    "40": (39.74, 59.61, 75.51, 91.40, 107.30, 119.22, 131.14, 143.06, 154.99, 166.91),
    "50": (48.73, 73.10, 92.59, 112.08, 131.57, 146.19, 160.81, 175.43, 190.05, 204.67),
    "60": (58.15, 87.23, 110.49, 133.74, 157.01, 174.45, 191.90, 209.34, 226.79, 244.23),
    "75": (72.28, 108.42, 137.33, 166.24, 195.16, 216.84, 238.52, 260.21, 281.89, 303.58),
    "100": (95.56, 143.34, 181.56, 219.79, 258.01, 286.68, 315.35, 344.02, 372.68, 401.35),
    "125": (117.05, 175.58, 222.40, 269.22, 316.04, 351.15, 386.27, 421.38, 456.50, 491.61),
    "150": (141.29, 211.94, 263.45, 324.97, 381.43, 423.87, 466.26, 508.64, 551.03, 593.42),
    "200": (190.18, 285.27, 361.34, 437.41, 513.49, 570.54, 627.59, 684.65, 741.70, 789.76),
}

# Transcrição independente da TABELA 3, p.14 (vista na imagem).
ESPERADO_MONO = {
    "1/4": (0.66, 0.99, 1.25, 1.52, 1.78, 1.98, 2.18, 2.38, 2.57, 2.77),
    "1/3": (0.77, 1.16, 1.46, 1.77, 2.08, 2.31, 2.54, 2.77, 3.00, 3.23),
    "1/2": (1.18, 1.77, 2.24, 2.71, 3.19, 3.54, 3.89, 4.25, 4.60, 4.96),
    "3/4": (1.34, 2.01, 2.55, 3.03, 3.62, 4.02, 4.42, 4.82, 5.23, 5.63),
    "1": (1.56, 2.34, 2.96, 3.59, 4.21, 4.68, 5.01, 5.62, 6.08, 6.55),
    "1 1/2": (2.35, 2.53, 4.47, 5.41, 6.35, 7.05, 7.76, 8.46, 9.17, 9.87),
    "2": (2.97, 4.46, 5.64, 6.83, 8.02, 8.91, 9.80, 10.69, 11.58, 12.47),
    "3": (4.07, 6.11, 7.73, 9.36, 10.99, 12.21, 13.43, 14.65, 15.87, 17.09),
    "5": (6.16, 9.24, 11.70, 14.17, 16.63, 18.48, 20.33, 22.18, 24.02, 25.87),
    "7 1/2": (8.84, 13.26, 16.80, 20.33, 23.87, 26.52, 29.17, 31.82, 34.48, 37.13),
    "10": (11.64, 17.46, 22.12, 26.77, 31.43, 34.92, 33.41, 41.90, 45.40, 48.89),
    "12 1/2": (14.94, 22.41, 28.39, 34.03, 40.34, 44.02, 49.30, 53.78, 58.27, 62.75),
    "15": (16.94, 25.41, 32.19, 38.96, 45.74, 50.82, 55.90, 60.98, 66.07, 71.15),
}

# Transcrição independente da TABELA 1, p.13 (vista na imagem):
# (quantidade minima, fator <= 3,5 kW, fator > 3,5 kW).
ESPERADO_HEATING = (
    (1, 80.0, 80.0), (2, 75.0, 65.0), (3, 70.0, 55.0), (4, 66.0, 50.0),
    (5, 62.0, 45.0), (6, 59.0, 43.0), (7, 56.0, 40.0), (8, 53.0, 36.0),
    (9, 51.0, 35.0), (10, 49.0, 34.0), (11, 47.0, 32.0), (12, 45.0, 32.0),
    (13, 43.0, 32.0), (14, 41.0, 32.0), (15, 40.0, 32.0), (16, 39.0, 28.0),
    (17, 38.0, 28.0), (18, 37.0, 28.0), (19, 36.0, 28.0), (20, 35.0, 28.0),
    (21, 34.0, 26.0), (22, 33.0, 26.0), (23, 32.0, 26.0), (24, 31.0, 26.0),
    (25, 30.0, 26.0), (26, 30.0, 24.0), (31, 30.0, 22.0), (41, 30.0, 20.0),
    (51, 30.0, 18.0), (61, 30.0, 16.0),
)

ESPERADO_ROOMS = {
    "quarto": 1.50, "sala": 1.60, "banheiro": 2.30, "cozinha_1": 1.50,
    "cozinha_2": 2.10, "area_servico": 1.90, "outros": 0.35,
}
ESPERADO_LOCATION = (1.00, 0.88, 0.75, 0.55)
ESPERADO_SPECIAL = {
    "incandescent": 1.0, "vapor_mercury": 0.9,
    "vapor_sodium": 0.9, "vapor_metallic": 0.9,
}
ESPERADO_MAX_QTY = 10
ESPERADO_NO_PLATE = 1.5


def confere_transcricao(motor_table, heating, rooms, location, special,
                        max_qty, no_plate):
    """Compara a produção contra a transcrição vista na imagem.

    Devolve gaps; cada gap nomeia a PARTE e a célula (convencao 7).
    """
    gaps = []
    for power, values in ESPERADO_TRI.items():
        for qty, seen in enumerate(values, start=1):
            got = motor_table.get(("trifasica", power, qty))
            if got is None or abs(float(got) - seen) > 1e-9:
                gaps.append("motores_trifasicos: (%r, qtd %d) produção=%r "
                            "imagem=%.2f" % (power, qty, got, seen))
    for power, values in ESPERADO_MONO.items():
        for qty, seen in enumerate(values, start=1):
            got = motor_table.get(("monofasica", power, qty))
            if got is None or abs(float(got) - seen) > 1e-9:
                gaps.append("motores_monofasicos: (%r, qtd %d) produção=%r "
                            "imagem=%.2f" % (power, qty, got, seen))
    if len(motor_table) != 370:
        gaps.append("motores_tamanho: produção tem %d células, imagem tem "
                    "370" % len(motor_table))
    for idx, seen_row in enumerate(ESPERADO_HEATING):
        got_row = heating[idx] if idx < len(heating) else None
        if got_row is None or tuple(got_row) != tuple(seen_row):
            gaps.append("aquecimento: linha %d produção=%r imagem=%r"
                        % (idx, got_row, seen_row))
    if len(heating) != len(ESPERADO_HEATING):
        gaps.append("aquecimento_tamanho: produção tem %d linhas, imagem "
                    "tem %d" % (len(heating), len(ESPERADO_HEATING)))
    for room, seen in ESPERADO_ROOMS.items():
        got = rooms.get(room)
        if got is None or abs(float(got) - seen) > 1e-9:
            gaps.append("comodos: %r produção=%r imagem=%.2f"
                        % (room, got, seen))
    if tuple(location) != tuple(ESPERADO_LOCATION):
        gaps.append("localizacao: produção=%r imagem=%r"
                    % (location, ESPERADO_LOCATION))
    for kind, seen in ESPERADO_SPECIAL.items():
        got = special.get(kind)
        if got is None or abs(float(got) - seen) > 1e-9:
            gaps.append("iluminacao_especial: %r produção=%r imagem=%.2f"
                        % (kind, got, seen))
    if max_qty != ESPERADO_MAX_QTY:
        gaps.append("escalar_max_qty: produção=%r imagem=%r"
                    % (max_qty, ESPERADO_MAX_QTY))
    if abs(float(no_plate) - ESPERADO_NO_PLATE) > 1e-9:
        gaps.append("escalar_sem_placa: produção=%r imagem=%r"
                    % (no_plate, ESPERADO_NO_PLATE))
    return gaps


def _producao_atual():
    return (WKI._MOTOR_TABLE_KVA, WKI._HEATING_TABLE, WKI.ROOM_MODULES_KVA,
            WKI.LOCATION_FACTORS, WKI._SPECIAL_LIGHTING_POWER_FACTORS,
            WKI._MOTOR_TABLE_MAX_QUANTITY, WKI._MOTOR_NO_PLATE_KW_PER_CV)


def _payload_base():
    return {
        "network": {"location_factor": 0.88},
        "rooms": {"quarto": 3, "sala": 2, "banheiro": 3, "cozinha": 1,
                  "area_servico": 1, "outros": 4},
        "loads": {"installed_load_kw": 0.0, "heating": [], "motors": [],
                  "special_lighting": []},
    }


def test_01_baseline_verde_476_celulas():
    """As 476 células da produção batem com o visto na imagem."""
    gaps = confere_transcricao(*_producao_atual())
    assert not gaps, "transcrição WKI diverge da imagem:\n" + "\n".join(gaps)


def test_02_vermelho_por_injecao_por_parte(tmp_path):
    """Célula alterada em tmp_path acusa a célula e a parte (conv 7).

    A prova sai do arquivo copiado em tmp_path, nunca do repo.
    """
    motor, heating, rooms, loc, spec, max_qty, no_plate = _producao_atual()
    lados = []

    # Parte 1: trifásicos (coluna de quantidade, onde morava o 6734fc8).
    inj_tri = copy.deepcopy(dict(motor))
    inj_tri[("trifasica", "1", 2)] = 9.99
    p = tmp_path / "tri.json"
    p.write_text(json.dumps({"v": inj_tri[("trifasica", "1", 2)]}),
                 encoding="utf-8")
    if json.loads(p.read_text(encoding="utf-8"))["v"] != 9.99:
        lados.append("tmp_path não guardou a injeção tri")
    gaps = confere_transcricao(inj_tri, heating, rooms, loc, spec,
                               max_qty, no_plate)
    if not [g for g in gaps if "motores_trifasicos" in g and "'1'" in g]:
        lados.append("injeção tri 1CV/qtd2 não acusou: %r" % (gaps,))

    # Parte 2: monofásicos.
    inj_mono = copy.deepcopy(dict(motor))
    inj_mono[("monofasica", "2", 1)] = 9.99
    gaps = confere_transcricao(inj_mono, heating, rooms, loc, spec,
                               max_qty, no_plate)
    if not [g for g in gaps if "motores_monofasicos" in g]:
        lados.append("injeção mono não acusou: %r" % (gaps,))

    # Parte 3: aquecimento.
    inj_heat = [list(row) for row in heating]
    inj_heat[0] = [1, 11.0, 80.0]
    p2 = tmp_path / "heat.json"
    p2.write_text(json.dumps(inj_heat), encoding="utf-8")
    inj_heat = [tuple(r) for r in json.loads(p2.read_text(encoding="utf-8"))]
    gaps = confere_transcricao(motor, inj_heat, rooms, loc, spec,
                               max_qty, no_plate)
    if not [g for g in gaps if "aquecimento" in g]:
        lados.append("injeção aquecimento não acusou: %r" % (gaps,))

    # Parte 4: cômodos.
    inj_rooms = dict(rooms)
    inj_rooms["quarto"] = 9.99
    gaps = confere_transcricao(motor, heating, inj_rooms, loc, spec,
                               max_qty, no_plate)
    if not [g for g in gaps if "comodos" in g and "quarto" in g]:
        lados.append("injeção cômodo não acusou: %r" % (gaps,))

    # Parte 5: localização / iluminação / escalares.
    gaps = confere_transcricao(motor, heating, rooms, (1.0,), spec,
                               max_qty, no_plate)
    if not [g for g in gaps if "localizacao" in g]:
        lados.append("injeção localização não acusou: %r" % (gaps,))
    inj_spec = dict(spec)
    inj_spec["vapor_mercury"] = 0.5
    gaps = confere_transcricao(motor, heating, rooms, loc, inj_spec,
                               max_qty, no_plate)
    if not [g for g in gaps if "iluminacao_especial" in g]:
        lados.append("injeção iluminação não acusou: %r" % (gaps,))
    gaps = confere_transcricao(motor, heating, rooms, loc, spec,
                               11, no_plate)
    if not [g for g in gaps if "escalar_max_qty" in g]:
        lados.append("injeção escalar não acusou: %r" % (gaps,))

    # Cópia limpa via tmp_path não acusa (sem falso-positivo).
    motor_f = {":".join((k[0], k[1], str(k[2]))): v
               for k, v in motor.items()}
    p3 = tmp_path / "limpa.json"
    p3.write_text(json.dumps({"n": len(motor_f)}), encoding="utf-8")
    gaps = confere_transcricao(*_producao_atual())
    if gaps:
        lados.append("cópia limpa acusou: %r" % (gaps,))

    assert not lados, "guarda G161 por parte:\n" + "\n".join(lados)


def test_03_exemplo_1_wki_residencial():
    """Aferição pelo exemplo resolvido da fonte (6.6.1 EXEMPLO 1, p.28-30).

    Casa Santa Rosa/Niterói: a=14,67 b=4,72 c=4,48 d=1,67 Dc=23,69 kVA.
    Motores do exemplo são monofásicos (2x1/4 + 2x1/3 + 1x2CV bomba).
    """
    payload = _payload_base()
    payload["loads"]["heating"] = [{"quantity": 1, "power_kw": 4.4},
                                   {"quantity": 1, "power_kw": 1.5}]
    payload["loads"]["motors"] = [
        {"quantity": 2, "power_cv": "1/4", "connection": "monofasica"},
        {"quantity": 2, "power_cv": "1/3", "connection": "monofasica"},
        {"quantity": 1, "power_cv": "2", "connection": "monofasica"},
    ]
    payload["loads"]["special_lighting"] = [{"power_kw": 1.5,
                                             "kind": "vapor_mercury"}]
    result = WKI.calculate_residential_demand(payload)
    assert result["ok"] is True
    calc = result["calculation"]
    assert calc["rooms"]["subtotal_kva"] == pytest.approx(20.00)
    assert calc["demand"]["a"] == pytest.approx(14.67, abs=0.01)
    assert calc["demand"]["b"] == pytest.approx(4.72, abs=0.01)
    assert calc["demand"]["c"] == pytest.approx(4.48, abs=0.01)
    assert calc["demand"]["d"] == pytest.approx(1.67, abs=0.01)
    assert calc["demand"]["final_kva"] == pytest.approx(23.69, abs=0.02)


def test_04_leitura_consolidada_e_recusa_por_tabela():
    """Modo de leitura por tabela (o caminho do 6734fc8) + recusa.

    Motores consolidam mesma potência; aquecimento NÃO (Nota 1 p.13:
    cada tipo separado, soma no fim - o Exemplo 1 prova: 3,52 + 1,20).
    """
    # Motores: duas declarações iguais consolidam na coluna qtd 2.
    payload = _payload_base()
    payload["network"]["location_factor"] = 1.0
    payload["rooms"] = {"quarto": 2, "sala": 1, "banheiro": 1,
                        "cozinha": 1, "area_servico": 1, "outros": 0}
    payload["loads"]["motors"] = [
        {"quantity": 1, "power_cv": "1", "connection": "trifasica"},
        {"quantity": 1, "power_cv": "1", "connection": "trifasica"},
    ]
    result = WKI.calculate_residential_demand(payload)
    assert result["ok"] is True
    assert result["calculation"]["motors"]["demand_kva"] == pytest.approx(2.28)

    # Motores: quantidade consolidada acima de 10 recusa.
    payload["loads"]["motors"] = [
        {"quantity": 6, "power_cv": "1", "connection": "trifasica"},
        {"quantity": 5, "power_cv": "1", "connection": "trifasica"},
    ]
    refused = WKI.calculate_residential_demand(payload)
    assert refused["ok"] is False
    assert any(e["code"] == "motor_outside_table"
               for e in refused["errors"])

    # Aquecimento: mesma potência em duas declarações SOMA (não consolida).
    payload["loads"]["motors"] = []
    payload["loads"]["heating"] = [{"quantity": 1, "power_kw": 4.4},
                                   {"quantity": 1, "power_kw": 4.4}]
    result = WKI.calculate_residential_demand(payload)
    assert result["ok"] is True
    assert result["calculation"]["heating"]["demand_kva"] == pytest.approx(
        2 * 4.4 * 0.80)

    # Aquecimento: quantidade/faixa consolidada numa declaração + recusa.
    payload["loads"]["heating"] = [{"quantity": 2, "power_kw": 4.0}]
    result = WKI.calculate_residential_demand(payload)
    assert result["calculation"]["heating"]["items"][0][
        "factor_percent"] == pytest.approx(65.0)
    payload["loads"]["heating"] = [{"quantity": 0, "power_kw": 1.0}]
    refused = WKI.calculate_residential_demand(payload)
    assert refused["ok"] is False
