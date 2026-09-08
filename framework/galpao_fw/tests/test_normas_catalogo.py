"""Guarda G65: toda NBR citada em *.py precisa de lastro em fontes/catalogo.csv.

Mede o mesmo cruzamento que fundou o bloco de fontes: extrai os numeros de
NBR citados nos modulos-fonte (framework/galpao_fw/*.py, fora de tests/) e
exige um identificador NBR-XXXX correspondente no catalogo. Citar norma
substituida como fonte (7229/13969 -> NBR 17076:2024; 13792 -> NBR 16981:2021)
reprova com mensagem apontando a vigente. Notas de procedencia que mencionam
a norma antiga junto de "sucede/cancela/substitui/contra/legada" nao sao
fonte e nao reprovam.

LACUNAS_PRE_EXISTENTES documenta citacoes sem lastro anteriores a G65 e fora
do seu escopo (5413, 5444, 13438): o teste reprova se elas sumirem sem atual
izar o conjunto (viraram lastro ou foram removidas) ou se surgir citacao nova
sem lastro.
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(GALPAO))
CATALOGO = os.path.join(REPO, "fontes", "catalogo.csv")

PAT_NBR = re.compile(r"NBR[\s_\-]*(\d{4,5})", re.IGNORECASE)
PAT_MARCADOR_PROCEDENCIA = re.compile(
    r"sucede|cancela|substitui|contra(?:\s+a)?\s+NBR|legada|anterior|conferid",
    re.IGNORECASE,
)

# norma antiga -> vigente que a sucede (identificador do catalogo).
SUBSTITUIDAS = {
    "7229": "NBR-17076-2024",
    "13969": "NBR-17076-2024",
    "13792": "NBR-16981-2021",
}

# Citacoes sem lastro anteriores a G65, fora do escopo (nao sao fonte de
# calculo: comentarios secundarios e rotulo de dado). Novas citacoes sem
# lastro reprovam; estas reprovam se mudarem sem atualizar o conjunto.
LACUNAS_PRE_EXISTENTES = frozenset({"13438", "5413", "5444"})


def _numeros_catalogo():
    with open(CATALOGO, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    nums = set()
    for lin in linhas:
        ident = (lin.get("identificador") or "")
        if ident.upper().startswith("NBR"):
            nums.update(re.findall(r"(\d{4,5})", ident))
    return nums


def _modulos_fonte():
    return sorted(
        p
        for p in os.listdir(GALPAO)
        if p.endswith(".py") and os.path.isfile(os.path.join(GALPAO, p))
    )


def _citacoes_por_arquivo():
    cit = {}
    for nome in _modulos_fonte():
        with open(os.path.join(GALPAO, nome), encoding="utf-8",
                  errors="ignore") as f:
            linhas = f.readlines()
        achados = []
        for i, lin in enumerate(linhas, 1):
            for num in PAT_NBR.findall(lin):
                achados.append((num, i, lin.strip()))
        if achados:
            cit[nome] = achados
    return cit


def test_substituidas_nao_sao_fonte():
    """NBR 7229/13969/13792 como fonte reprova; nota de procedencia nao."""
    cit = _citacoes_por_arquivo()
    crimes = []
    for arq, achados in sorted(cit.items()):
        for num, linha, texto in achados:
            if num not in SUBSTITUIDAS:
                continue
            if PAT_MARCADOR_PROCEDENCIA.search(texto):
                continue  # nota de procedencia, nao promessa de referencia
            crimes.append(
                "%s:%d: NBR %s citada sem marcador de procedencia "
                "(sucede/cancela/substitui/contra/legada/conferida; "
                "usa %s) -> %r" % (arq, linha, num,
                                   SUBSTITUIDAS[num], texto[:120])
            )
    assert not crimes, (
        "citacao de norma substituida como fonte (G65):\n" + "\n".join(crimes)
    )


def test_toda_nbr_citada_tem_lastro():
    """Todo numero citado precisa de identificador NBR-XXXX no catalogo."""
    catalogo = _numeros_catalogo()
    assert "17076" in catalogo and "16981" in catalogo, (
        "catalogo sem as vigentes NBR-17076-2024 / NBR-16981-2021"
    )
    cit = _citacoes_por_arquivo()
    sem_lastro = {}
    for arq, achados in sorted(cit.items()):
        faltam = sorted({num for num, _, _ in achados} - catalogo)
        if faltam:
            sem_lastro[arq] = faltam
    novas = {}
    for arq, nums in sem_lastro.items():
        resto = [n for n in nums if n not in LACUNAS_PRE_EXISTENTES
                 and n not in SUBSTITUIDAS]
        if resto:
            novas[arq] = resto
    assert not novas, (
        "NBR citada em *.py sem lastro em fontes/catalogo.csv:\n"
        + "\n".join("%s: %s" % (a, ", ".join(n))
                    for a, n in sorted(novas.items()))
        + "\nAcrescente a fonte ao acervo ou atualize a citacao."
    )
    # Lacunas conhecidas continuam monitoradas: se sumirem do codigo ou
    # ganharem lastro, atualize LACUNAS_PRE_EXISTENTES em vez de silenciar.
    citadas = set()
    for achados in cit.values():
        citadas.update(num for num, _, _ in achados)
    fantasmas = sorted(set(LACUNAS_PRE_EXISTENTES) - citadas)
    resolvidas = sorted(set(LACUNAS_PRE_EXISTENTES) & catalogo)
    assert not fantasmas and not resolvidas, (
        "LACUNAS_PRE_EXISTENTES desatualizadas: sumiram do codigo %r; "
        "ganharam lastro %r. Atualize o conjunto." % (fantasmas, resolvidas)
    )
