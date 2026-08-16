"""Entrada de specs de projeto por arquivo.

Este módulo valida somente o envelope de transporte. Regras de engenharia,
normalização e execução continuam em :mod:`project_loop`.
"""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_SPEC_SCHEMA = "freecad-automatic/project-spec"
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})


class ProjectSpecFileError(ValueError):
    """Erro acionável ao carregar um spec de projeto do disco."""


def _path_label(path):
    return str(path)


def load_project_spec(path, *, allow_legacy=True):
    """Carrega e valida um spec JSON sem preencher nenhum campo.

    O envelope versionado é validado quando ``schema`` está presente. Um
    documento sem envelope continua aceito como spec legado somente quando
    ``allow_legacy`` é verdadeiro.
    """
    try:
        source = Path(path).expanduser()
    except TypeError as exc:
        raise ProjectSpecFileError("caminho de spec invalido: %r" % (path,)) from exc
    if not source.is_file():
        raise ProjectSpecFileError("arquivo de spec nao encontrado: %s"
                                   % _path_label(source))
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ProjectSpecFileError("spec nao esta em UTF-8: %s"
                                   % _path_label(source)) from exc
    except json.JSONDecodeError as exc:
        raise ProjectSpecFileError(
            "JSON de spec invalido em %s (linha %d, coluna %d)"
            % (_path_label(source), exc.lineno, exc.colno)) from exc

    if not isinstance(document, dict):
        raise ProjectSpecFileError("raiz do spec deve ser um objeto JSON: %s"
                                   % _path_label(source))

    schema = document.get("schema")
    if schema is None:
        if not allow_legacy:
            raise ProjectSpecFileError(
                "spec legado recusado; informe schema=%s e schema_version=1: %s"
                % (PROJECT_SPEC_SCHEMA, _path_label(source)))
    else:
        if schema != PROJECT_SPEC_SCHEMA:
            raise ProjectSpecFileError(
                "schema de spec nao suportado %r (esperado %r): %s"
                % (schema, PROJECT_SPEC_SCHEMA, _path_label(source)))
        version = document.get("schema_version")
        if (isinstance(version, bool) or not isinstance(version, int)
                or version not in SUPPORTED_SCHEMA_VERSIONS):
            raise ProjectSpecFileError(
                "schema_version nao suportado %r (suportado: %s): %s"
                % (version, sorted(SUPPORTED_SCHEMA_VERSIONS),
                   _path_label(source)))
    return document


def _validate_normalizable_spec(spec):
    from project_loop import normalize_spec

    try:
        normalize_spec(spec)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ProjectSpecFileError(
            "spec semanticamente invalido: %s" % exc) from exc


def run_project_file(spec_path, out_dir, options=None, *, iteration=1,
                     parent_run_id=None, changes=None, resolutions=None):
    """Carrega ``spec_path`` e delega a execução ao Loop de projeto."""
    from project_loop import run_project

    spec = load_project_spec(spec_path)
    _validate_normalizable_spec(spec)
    return run_project(spec, out_dir, options=options, iteration=iteration,
                       parent_run_id=parent_run_id, changes=changes,
                       resolutions=resolutions)


def preflight_project_file(spec_path, out_dir, options=None):
    """Carrega um spec e executa somente o gate de prontidao."""
    from project_loop import preflight_project

    spec = load_project_spec(spec_path)
    _validate_normalizable_spec(spec)
    try:
        return preflight_project(spec, out_dir, options=options)
    except ProjectSpecFileError:
        raise
    except (AttributeError, TypeError, ValueError) as exc:
        raise ProjectSpecFileError(
            "spec nao pode ser homologado: %s" % exc) from exc


__all__ = ["PROJECT_SPEC_SCHEMA", "ProjectSpecFileError",
           "SUPPORTED_SCHEMA_VERSIONS", "load_project_spec",
           "preflight_project_file", "run_project_file"]
