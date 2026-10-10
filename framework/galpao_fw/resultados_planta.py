# ============================================================================
# resultados_planta.py - AS SAIDAS DO ELETRICO SOBRE PLANTA COMO ESTRUTURAS
# TIPADAS (plano de 2026-10-08, Fase 1: "entradas e saidas como estruturas de
# dados tipadas"; Fase 5). A entrada (criterios) foi tipada no D217; aqui ficam
# as saidas que `circuitos_planta` escreve: a divisao em circuitos, o
# dimensionamento e a demanda com o padrao de entrada - e a leitura da planta
# que os leitores de DXF e de IFC entregam (D220).
#
# O motor continua devolvendo dicionarios (e' o que os relatorios e os
# desenhos ja leem). Este modulo e' o CONTRATO desses dicionarios:
#   - `divisao(d)`, `dimensionamento(d)` e `entrada(d)` leem o dicionario e
#     devolvem a estrutura imutavel; chave que falta ou chave que a estrutura
#     nao conhece reprova e diz qual, em vez de virar KeyError la adiante ou
#     dado que ninguem le;
#   - `.para_dict()` devolve o dicionario de volta, igual ao lido.
# Nada e' preenchido: o que o motor deixa ausente fica None e nao volta.
#
# O que vem de OUTROS motores e passa por dentro destas saidas (`circuits` do
# dimensionamento residencial, `calculation` da demanda, `service_entry` do
# padrao de entrada) fica como o motor de origem devolve: o contrato deles e'
# deles.
# ============================================================================
"""Contrato tipado das saidas de circuitos_planta."""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping, Optional, Tuple


class SaidaForaDoContrato(ValueError):
    """O dicionario nao tem a forma que `circuitos_planta` escreve."""


def _conferir(d, obrigatorias, opcionais, onde):
    if not isinstance(d, dict):
        raise SaidaForaDoContrato("%s: esperado um objeto, veio %s" % (onde, type(d).__name__))
    faltam = [c for c in obrigatorias if c not in d]
    sobram = sorted(c for c in d if c not in obrigatorias and c not in opcionais)
    if faltam or sobram:
        raise SaidaForaDoContrato("%s: faltam %r, fora do contrato %r" % (onde, faltam, sobram))


def _sem_none(pares):
    return {k: v for k, v in pares if v is not None}


@dataclasses.dataclass(frozen=True)
class Ponto:
    id: str
    room: str
    kind: str
    power_va: float
    voltage_v: float
    nome: Optional[str] = None                 # so o ponto de equipamento

    OBRIGATORIAS = ("id", "room", "kind", "power_va", "voltage_v")
    OPCIONAIS = ("nome",)

    def para_dict(self):
        return _sem_none((c, getattr(self, c)) for c in self.OBRIGATORIAS + self.OPCIONAIS)


@dataclasses.dataclass(frozen=True)
class Circuito:
    id: str
    classe: str
    use: str
    point_ids: Tuple[str, ...]
    ambientes: Tuple[str, ...]
    potencia_va: float
    tensao_v: float
    n_fases: int
    corrente_a: float
    local: str
    fases: Tuple[str, ...]
    equipamento: Optional[str] = None
    independente_exigido_9_5_3_1: Optional[bool] = None

    OBRIGATORIAS = ("id", "classe", "use", "point_ids", "ambientes", "potencia_va", "tensao_v",
                    "n_fases", "corrente_a", "local", "fases")
    OPCIONAIS = ("equipamento", "independente_exigido_9_5_3_1")
    LISTAS = ("point_ids", "ambientes", "fases")

    def para_dict(self):
        d = _sem_none((c, getattr(self, c)) for c in self.OBRIGATORIAS + self.OPCIONAIS)
        for c in self.LISTAS:
            d[c] = list(d[c])
        return d


@dataclasses.dataclass(frozen=True)
class Quadro:
    carga_instalada_va: float
    n_circuitos: int
    n_pontos: int
    carga_por_fase_va: Mapping[str, float]
    desequilibrio_pct: float
    escopo: str

    CAMPOS = ("carga_instalada_va", "n_circuitos", "n_pontos", "carga_por_fase_va",
              "desequilibrio_pct", "escopo")

    def para_dict(self):
        d = {c: getattr(self, c) for c in self.CAMPOS}
        d["carga_por_fase_va"] = dict(self.carga_por_fase_va)
        return d


@dataclasses.dataclass(frozen=True)
class Divisao:
    pontos: Tuple[Ponto, ...]
    circuitos: Tuple[Circuito, ...]
    quadro: Optional[Quadro]                   # None quando a divisao nao foi feita
    erros: Tuple[Mapping[str, Any], ...]
    atende: bool
    criterios: Optional[Mapping[str, Any]] = None   # ausente quando os criterios reprovam

    def para_dict(self):
        d = {"pontos": [p.para_dict() for p in self.pontos],
             "circuitos": [c.para_dict() for c in self.circuitos],
             "quadro": None if self.quadro is None else self.quadro.para_dict(),
             "erros": [dict(e) for e in self.erros]}
        if self.criterios is not None:
            d["criterios"] = dict(self.criterios)
        d["ATENDE"] = self.atende
        return d


@dataclasses.dataclass(frozen=True)
class LinhaDoResumo:
    id: str
    classe: str
    local: str
    comprimento_m: float
    origem_comprimento: str
    corrente_a: float
    secao_mm2: Any
    governante: Any
    queda_pct: Any
    disjuntor_a: Any
    dr: Any

    CAMPOS = ("id", "classe", "local", "comprimento_m", "origem_comprimento", "corrente_a",
              "secao_mm2", "governante", "queda_pct", "disjuntor_a", "dr")

    def para_dict(self):
        return {c: getattr(self, c) for c in self.CAMPOS}


@dataclasses.dataclass(frozen=True)
class Comprimento:
    comprimento_m: Any
    origem: str
    distancia_ortogonal_m: Optional[float] = None      # so no comprimento estimado
    ambiente_mais_distante: Optional[str] = None       # pela planta (D207)

    OBRIGATORIAS = ("comprimento_m", "origem")
    OPCIONAIS = ("distancia_ortogonal_m", "ambiente_mais_distante")

    def para_dict(self):
        return _sem_none((c, getattr(self, c)) for c in self.OBRIGATORIAS + self.OPCIONAIS)


@dataclasses.dataclass(frozen=True)
class Dimensionamento:
    circuits: Optional[Mapping[str, Any]]      # saida do motor residencial, como ele devolve
    resumo: Tuple[LinhaDoResumo, ...]
    comprimentos: Mapping[str, Comprimento]
    erros: Tuple[Mapping[str, Any], ...]
    atende: bool

    def para_dict(self):
        return {"circuits": None if self.circuits is None else dict(self.circuits),
                "resumo": [r.para_dict() for r in self.resumo],
                "comprimentos": {k: v.para_dict() for k, v in self.comprimentos.items()},
                "erros": [dict(e) for e in self.erros], "ATENDE": self.atende}


@dataclasses.dataclass(frozen=True)
class Entrada:
    rooms: Optional[Mapping[str, int]]
    heating: Tuple[Mapping[str, Any], ...]
    installed_load_kw: Optional[float]
    calculation: Mapping[str, Any]             # saida do motor de demanda
    service_entry: Mapping[str, Any]           # saida do motor do padrao de entrada
    erros: Tuple[Mapping[str, Any], ...]
    atende: bool

    def para_dict(self):
        return {"rooms": None if self.rooms is None else dict(self.rooms),
                "heating": [dict(h) for h in self.heating],
                "installed_load_kw": self.installed_load_kw,
                "calculation": dict(self.calculation),
                "service_entry": dict(self.service_entry),
                "erros": [dict(e) for e in self.erros], "ATENDE": self.atende}


def _item(classe, d, onde):
    _conferir(d, classe.OBRIGATORIAS, classe.OPCIONAIS, onde)
    valores = dict(d)
    for c in getattr(classe, "LISTAS", ()):
        valores[c] = tuple(valores[c])
    return classe(**valores)


def _lista(valor, onde):
    if not isinstance(valor, list):
        raise SaidaForaDoContrato("%s: esperada uma lista, veio %s" % (onde, type(valor).__name__))
    return valor


def divisao(d):
    """Le a saida de `circuitos_planta.dividir`."""
    _conferir(d, ("pontos", "circuitos", "quadro", "erros", "ATENDE"), ("criterios",), "divisao")
    quadro = None
    if d["quadro"] is not None:
        _conferir(d["quadro"], Quadro.CAMPOS, (), "divisao.quadro")
        quadro = Quadro(**d["quadro"])
    return Divisao(
        pontos=tuple(_item(Ponto, p, "divisao.pontos[%d]" % k)
                     for k, p in enumerate(_lista(d["pontos"], "divisao.pontos"), start=1)),
        circuitos=tuple(_item(Circuito, c, "divisao.circuitos[%d]" % k)
                        for k, c in enumerate(_lista(d["circuitos"], "divisao.circuitos"),
                                              start=1)),
        quadro=quadro, erros=tuple(_lista(d["erros"], "divisao.erros")),
        atende=d["ATENDE"], criterios=d["criterios"] if "criterios" in d else None)


def dimensionamento(d):
    """Le a saida de `circuitos_planta.dimensionar` / `dimensionar_da_planta`."""
    _conferir(d, ("circuits", "resumo", "comprimentos", "erros", "ATENDE"), (), "dimensionamento")
    resumo = []
    for k, r in enumerate(_lista(d["resumo"], "dimensionamento.resumo"), start=1):
        _conferir(r, LinhaDoResumo.CAMPOS, (), "dimensionamento.resumo[%d]" % k)
        resumo.append(LinhaDoResumo(**r))
    if not isinstance(d["comprimentos"], dict):
        raise SaidaForaDoContrato("dimensionamento.comprimentos: esperado um objeto")
    comprimentos = {}
    for circuito, c in d["comprimentos"].items():
        comprimentos[circuito] = _item(Comprimento, c,
                                       "dimensionamento.comprimentos.%s" % circuito)
    return Dimensionamento(circuits=d["circuits"], resumo=tuple(resumo),
                           comprimentos=comprimentos,
                           erros=tuple(_lista(d["erros"], "dimensionamento.erros")),
                           atende=d["ATENDE"])


def entrada(d):
    """Le a saida de `circuitos_planta.demanda_e_entrada`."""
    _conferir(d, ("rooms", "heating", "installed_load_kw", "calculation", "service_entry",
                  "erros", "ATENDE"), (), "entrada")
    for campo in ("calculation", "service_entry"):
        if not isinstance(d[campo], dict):
            raise SaidaForaDoContrato("entrada.%s: esperado um objeto" % campo)
    return Entrada(rooms=d["rooms"], heating=tuple(_lista(d["heating"], "entrada.heating")),
                   installed_load_kw=d["installed_load_kw"], calculation=d["calculation"],
                   service_entry=d["service_entry"],
                   erros=tuple(_lista(d["erros"], "entrada.erros")), atende=d["ATENDE"])


# ----------------------------------------------------------------------------
# Leitura da planta (ambientes_dxf e ambientes_ifc): o mesmo contrato para as
# duas origens. O que so uma origem traz e' opcional e fica None na outra.
# ----------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class Ambiente:
    nome: str
    tipo: str
    area_m2: float
    perimetro_m: float

    OBRIGATORIAS = ("nome", "tipo", "area_m2", "perimetro_m")
    OPCIONAIS = ()

    def para_dict(self):
        return {c: getattr(self, c) for c in self.OBRIGATORIAS}


@dataclasses.dataclass(frozen=True)
class Leitura:
    """Saida de `ler_ambientes` (DXF ou IFC)."""
    ambientes: Tuple[Ambiente, ...]
    erros: Tuple[Mapping[str, Any], ...]
    geometria: Mapping[str, Any]               # {ambiente: [[x_m, y_m], ...]}
    quadro_m: Optional[Tuple[float, float]]    # None quando a planta nao marca o quadro
    metros_por_unidade: Any
    camada: Optional[str] = None               # so no DXF
    pavimento: Optional[str] = None            # so no IFC
    pavimentos: Optional[Tuple[str, ...]] = None

    OBRIGATORIAS = ("ambientes", "erros", "geometria", "quadro_m", "metros_por_unidade")
    OPCIONAIS = ("camada", "pavimento", "pavimentos")

    def para_dict(self, chaves):
        """`chaves` e' a ordem e o conjunto de chaves do dicionario de origem:
        `pavimento` pode ser None DE VERDADE no IFC, e so a origem diz se a
        chave existia."""
        d = {}
        for c in chaves:
            v = getattr(self, c)
            if c == "ambientes":
                v = [a.para_dict() for a in v]
            elif c == "erros":
                v = [dict(e) for e in v]
            elif c == "geometria":
                v = {k: [list(p) for p in pts] for k, pts in v.items()}
            elif c in ("quadro_m", "pavimentos") and v is not None:
                v = list(v)
            d[c] = v
        return d


@dataclasses.dataclass(frozen=True)
class LeituraDaPrevisao:
    """O bloco `leitura_dxf` que `previsao_de_cargas` anexa ao resultado."""
    arquivo: str
    metros_por_unidade: Any
    geometria: Mapping[str, Any]
    quadro_m: Optional[Tuple[float, float]]
    erros: Tuple[Mapping[str, Any], ...]
    camada: Optional[str] = None
    origem: Optional[str] = None
    pavimento: Optional[str] = None

    OBRIGATORIAS = ("arquivo", "metros_por_unidade", "geometria", "quadro_m", "erros")
    OPCIONAIS = ("camada", "origem", "pavimento")


def _geometria(valor, ambientes, onde):
    if not isinstance(valor, dict):
        raise SaidaForaDoContrato("%s: esperado um objeto" % onde)
    for nome, pts in valor.items():
        if not isinstance(pts, list) or len(pts) < 3 or not all(
                isinstance(p, (list, tuple)) and len(p) == 2 for p in pts):
            raise SaidaForaDoContrato("%s.%s: esperados 3 ou mais pontos [x, y]" % (onde, nome))
    if ambientes is not None and sorted(valor) != sorted(ambientes):
        raise SaidaForaDoContrato(
            "%s: os ambientes com geometria %r nao sao os ambientes lidos %r"
            % (onde, sorted(valor), sorted(ambientes)))
    return {nome: tuple(tuple(p) for p in pts) for nome, pts in valor.items()}


def _quadro(valor, onde):
    if valor is None:
        return None
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        raise SaidaForaDoContrato("%s: esperado [x, y] ou nulo" % onde)
    return tuple(valor)


def leitura(d):
    """Le a saida de `ambientes_dxf.ler_ambientes` ou `ambientes_ifc.ler_ambientes`."""
    _conferir(d, Leitura.OBRIGATORIAS, Leitura.OPCIONAIS, "leitura")
    ambientes = tuple(_item(Ambiente, a, "leitura.ambientes[%d]" % k)
                      for k, a in enumerate(_lista(d["ambientes"], "leitura.ambientes"),
                                            start=1))
    opcionais = {c: d[c] for c in Leitura.OPCIONAIS if c in d}
    if "pavimentos" in opcionais and opcionais["pavimentos"] is not None:
        opcionais["pavimentos"] = tuple(opcionais["pavimentos"])
    return Leitura(
        ambientes=ambientes, erros=tuple(_lista(d["erros"], "leitura.erros")),
        geometria=_geometria(d["geometria"], [a.nome for a in ambientes], "leitura.geometria"),
        quadro_m=_quadro(d["quadro_m"], "leitura.quadro_m"),
        metros_por_unidade=d["metros_por_unidade"], **opcionais)


def leitura_da_previsao(d):
    """Le o bloco `leitura_dxf` do resultado de `previsao_de_cargas`."""
    _conferir(d, LeituraDaPrevisao.OBRIGATORIAS, LeituraDaPrevisao.OPCIONAIS, "leitura_dxf")
    return LeituraDaPrevisao(
        arquivo=d["arquivo"], metros_por_unidade=d["metros_por_unidade"],
        geometria=_geometria(d["geometria"], None, "leitura_dxf.geometria"),
        quadro_m=_quadro(d["quadro_m"], "leitura_dxf.quadro_m"),
        erros=tuple(_lista(d["erros"], "leitura_dxf.erros")),
        **{c: d[c] for c in LeituraDaPrevisao.OPCIONAIS if c in d})
