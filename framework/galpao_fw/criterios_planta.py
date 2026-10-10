# ============================================================================
# criterios_planta.py - OS CRITERIOS DE PROJETO DO ELETRICO SOBRE PLANTA COMO
# ESTRUTURA TIPADA (plano de 2026-10-08, Fase 1: "entradas e saidas como
# estruturas de dados tipadas"; Fase 5).
#
# O arquivo de criterios e' um JSON escrito a mao por quem projeta. Ate aqui
# ele chegava a `circuitos_planta` como dicionario solto: chave obrigatoria que
# falta ja reprovava, mas chave com o NOME ERRADO passava em silencio - e nas
# chaves opcionais isso muda o resultado sem aviso (`comprimento_m` no lugar
# de `comprimentos_m`: o comprimento declarado some e o circuito e' dimensionado
# pelo comprimento estimado).
#
# `ler(dicionario)` devolve os criterios tipados ou a lista de erros:
#   - chave que o motor nao conhece, em qualquer nivel, reprova e diz qual
#     chave parecida existe;
#   - o que falta ou tem valor invalido continua sendo dito pelos validadores
#     de `circuitos_planta` (uma regra so, nao copiada aqui).
# `Criterios.para_dict()` devolve o dicionario que `circuitos_planta` consome:
# para criterios validos, e' igual ao que foi lido.
#
# Nenhum valor e' preenchido: campo opcional ausente fica None e nao volta ao
# dicionario.
# ============================================================================
"""Criterios de projeto do eletrico sobre planta: leitura tipada e sem chave solta."""

from __future__ import annotations

import dataclasses
import difflib
from typing import Any, Mapping, Optional, Tuple

import circuitos_planta as CP

CHAVES_OBRIGATORIAS = ("tensao_v", "n_fases", "limite_va", "equipamentos")
CHAVES_OPCIONAIS = ("instalacao", "tracado", "comprimentos_m", "rede", "demanda")
CHAVES_EQUIPAMENTO = ("nome", "ambiente", "potencia_va", "tensao_v", "n_fases", "grupo_demanda")
CHAVES_TRACADO = ("fator", "acrescimo_vertical_m")
CHAVES_DEMANDA = CP.LISTAS_DE_DEMANDA + ("modulo_por_tipo",)


@dataclasses.dataclass(frozen=True)
class Equipamento:
    nome: str
    ambiente: str
    potencia_va: float
    tensao_v: float
    n_fases: int
    grupo_demanda: Optional[str] = None      # so a demanda (D210) o exige

    def para_dict(self):
        d = {"nome": self.nome, "ambiente": self.ambiente, "potencia_va": self.potencia_va,
             "tensao_v": self.tensao_v, "n_fases": self.n_fases}
        if self.grupo_demanda is not None:
            d["grupo_demanda"] = self.grupo_demanda
        return d


@dataclasses.dataclass(frozen=True)
class Instalacao:
    isolacao: Any
    metodo_referencia: Any
    temperatura_ambiente_c: Any
    circuitos_agrupados: Any
    queda_tensao_max_pct: Any
    exposicao_dps: Any
    fator_potencia: Mapping[str, float]

    def para_dict(self):
        d = {c: getattr(self, c) for c in CP.CAMPOS_INSTALACAO}
        d["fator_potencia"] = dict(self.fator_potencia)
        return d


@dataclasses.dataclass(frozen=True)
class Tracado:
    fator: float
    acrescimo_vertical_m: float

    def para_dict(self):
        return {"fator": self.fator, "acrescimo_vertical_m": self.acrescimo_vertical_m}


@dataclasses.dataclass(frozen=True)
class Rede:
    location_factor: Any
    voltage_system: Any
    supply_type: Any
    network_kind: Any

    def para_dict(self):
        return {c: getattr(self, c) for c in CP.CAMPOS_REDE}


@dataclasses.dataclass(frozen=True)
class Demanda:
    motores: Tuple[Mapping[str, Any], ...]
    iluminacao_especial: Tuple[Mapping[str, Any], ...]
    modulo_por_tipo: Optional[Mapping[str, str]] = None

    def para_dict(self):
        d = {"motores": [dict(m) for m in self.motores],
             "iluminacao_especial": [dict(i) for i in self.iluminacao_especial]}
        if self.modulo_por_tipo is not None:
            d["modulo_por_tipo"] = dict(self.modulo_por_tipo)
        return d


@dataclasses.dataclass(frozen=True)
class Criterios:
    tensao_v: float
    n_fases: int
    limite_va: Mapping[str, float]
    equipamentos: Tuple[Equipamento, ...]
    instalacao: Optional[Instalacao] = None
    tracado: Optional[Tracado] = None
    comprimentos_m: Optional[Mapping[str, float]] = None
    rede: Optional[Rede] = None
    demanda: Optional[Demanda] = None

    def para_dict(self):
        """O dicionario que `circuitos_planta` consome; bloco ausente nao entra."""
        d = {"tensao_v": self.tensao_v, "n_fases": self.n_fases,
             "limite_va": dict(self.limite_va),
             "equipamentos": [e.para_dict() for e in self.equipamentos]}
        for nome in ("instalacao", "tracado", "rede", "demanda"):
            bloco = getattr(self, nome)
            if bloco is not None:
                d[nome] = bloco.para_dict()
        if self.comprimentos_m is not None:
            d["comprimentos_m"] = dict(self.comprimentos_m)
        return d


def _desconhecidas(bloco, conhecidas, caminho, erros):
    """Chave fora das conhecidas reprova, com a parecida quando ha."""
    for chave in bloco:
        if chave in conhecidas:
            continue
        parecidas = difflib.get_close_matches(str(chave), conhecidas, n=1, cutoff=0.6)
        erros.append({"code": "criterio_desconhecido",
                      "campo": "%s%s" % (caminho, chave),
                      "parecida": parecidas[0] if parecidas else None,
                      "detail": "chave que o motor nao le" + (
                          "; a chave lida e' %s" % parecidas[0] if parecidas
                          else "; chaves lidas: %s" % ", ".join(conhecidas))})


def _nao_e_objeto(valor, campo, erros):
    if isinstance(valor, dict):
        return False
    erros.append({"code": "criterio_ausente", "campo": campo,
                  "detail": "deve ser um objeto"})
    return True


def erros_de_chave(criterios):
    """So as chaves com nome que o motor nao le, em todos os niveis."""
    erros = []
    if not isinstance(criterios, dict):
        return erros
    _desconhecidas(criterios, CHAVES_OBRIGATORIAS + CHAVES_OPCIONAIS, "", erros)
    if "limite_va" in criterios and isinstance(criterios["limite_va"], dict):
        _desconhecidas(criterios["limite_va"], CP.CLASSES_COM_LIMITE, "limite_va.", erros)
    if "equipamentos" in criterios and isinstance(criterios["equipamentos"], list):
        for j, eq in enumerate(criterios["equipamentos"], start=1):
            if isinstance(eq, dict):
                _desconhecidas(eq, CHAVES_EQUIPAMENTO, "equipamentos[%d]." % j, erros)
    if "instalacao" in criterios and isinstance(criterios["instalacao"], dict):
        inst = criterios["instalacao"]
        _desconhecidas(inst, CP.CAMPOS_INSTALACAO + ("fator_potencia",), "instalacao.", erros)
        if "fator_potencia" in inst and isinstance(inst["fator_potencia"], dict):
            _desconhecidas(inst["fator_potencia"], CP.CLASSES, "instalacao.fator_potencia.",
                           erros)
    for nome, conhecidas in (("tracado", CHAVES_TRACADO), ("rede", CP.CAMPOS_REDE),
                             ("demanda", CHAVES_DEMANDA)):
        if nome in criterios and isinstance(criterios[nome], dict):
            _desconhecidas(criterios[nome], conhecidas, nome + ".", erros)
    return erros


def ler(criterios):
    """Devolve (Criterios, []) ou (None, erros). Os erros juntam as chaves
    desconhecidas e o que os validadores de `circuitos_planta` ja dizem do que
    falta ou esta invalido nos blocos presentes."""
    erros = erros_de_chave(criterios) + CP._erros_dos_criterios(criterios)
    if not isinstance(criterios, dict):
        return None, erros
    equipamentos = criterios["equipamentos"] if "equipamentos" in criterios else []
    if isinstance(equipamentos, list):
        for j, eq in enumerate(equipamentos, start=1):
            faltam = [c for c in CHAVES_EQUIPAMENTO[:5] if not isinstance(eq, dict) or c not in eq]
            if faltam:
                erros.append({"code": "equipamento_incompleto", "indice": j, "campos": faltam,
                              "detail": "equipamento precisa de nome, ambiente, potencia_va, "
                                        "tensao_v e n_fases"})
    if "instalacao" in criterios:
        erros += CP._erros_da_instalacao(criterios["instalacao"])
    if "tracado" in criterios and not _nao_e_objeto(criterios["tracado"], "tracado", erros):
        for campo in CHAVES_TRACADO:
            if campo not in criterios["tracado"]:
                erros.append({"code": "criterio_ausente", "campo": "tracado.%s" % campo,
                              "detail": "criterio de tracado declarado por quem projeta"})
    if "comprimentos_m" in criterios:
        _nao_e_objeto(criterios["comprimentos_m"], "comprimentos_m", erros)
    if "rede" in criterios and not _nao_e_objeto(criterios["rede"], "rede", erros):
        for campo in CP.CAMPOS_REDE:
            if campo not in criterios["rede"]:
                erros.append({"code": "criterio_ausente", "campo": "rede.%s" % campo,
                              "detail": "dado da rede declarado por quem projeta"})
    if "demanda" in criterios and not _nao_e_objeto(criterios["demanda"], "demanda", erros):
        dem = criterios["demanda"]
        for lista in CP.LISTAS_DE_DEMANDA:
            if lista not in dem or not isinstance(dem[lista], list):
                erros.append({"code": "criterio_ausente", "campo": "demanda.%s" % lista,
                              "detail": "lista declarada (vazia se nao ha)"})
        if "modulo_por_tipo" in dem:
            _nao_e_objeto(dem["modulo_por_tipo"], "demanda.modulo_por_tipo", erros)
    if erros:
        return None, erros

    def _bloco(nome, classe):
        return classe(**criterios[nome]) if nome in criterios else None

    dem = None
    if "demanda" in criterios:
        d = criterios["demanda"]
        dem = Demanda(motores=tuple(d["motores"]),
                      iluminacao_especial=tuple(d["iluminacao_especial"]),
                      modulo_por_tipo=d["modulo_por_tipo"] if "modulo_por_tipo" in d else None)
    return Criterios(
        tensao_v=criterios["tensao_v"], n_fases=criterios["n_fases"],
        limite_va=dict(criterios["limite_va"]),
        equipamentos=tuple(Equipamento(**eq) for eq in equipamentos),
        instalacao=_bloco("instalacao", Instalacao), tracado=_bloco("tracado", Tracado),
        comprimentos_m=(dict(criterios["comprimentos_m"])
                        if "comprimentos_m" in criterios else None),
        rede=_bloco("rede", Rede), demanda=dem), []


def relatorio_pt(erros):
    """Uma linha por erro de leitura dos criterios."""
    linhas = []
    for e in erros:
        alvo = e["campo"] if "campo" in e else "equipamento %s" % e["indice"]
        linhas.append("ERRO %s em %s: %s" % (e["code"], alvo, e["detail"]))
    return "\n".join(linhas)
