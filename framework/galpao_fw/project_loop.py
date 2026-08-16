"""Orquestrador persistente do Loop de projeto.

Esta camada recebe um spec de projeto, normaliza os formatos legados do
framework e registra uma execução auditável. Os calculadores continuam sendo
stateless e permanecem responsáveis pelas regras de engenharia; este módulo
coordena estados, artefatos e iterações.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from coordination_review import (
    build_review_report,
    collect_approved_updates,
    derive_affected_disciplines,
    load_resolution_plan,
    validate_resolution_plan,
)


SCHEMA = "freecad-automatic/project-run"
SCHEMA_VERSION = 1
SEQUENCE_SCHEMA = "freecad-automatic/project-sequence"
SEQUENCE_SCHEMA_VERSION = 1
READINESS_SCHEMA = "freecad-automatic/project-readiness"
READINESS_SCHEMA_VERSION = 1
KNOWN_DISCIPLINES = ("concreto", "aco", "eletrico", "incendio",
                     "climatizacao", "hidraulica")
DISCIPLINE_STATUSES = ("passed", "needs_review", "blocked", "failed",
                       "not_requested", "not_available")
_PROJECT_ADAPTERS = {}
_PROJECT_CAPABILITIES = {}
_PROJECT_HOOKS = {}
PENDING_MARKER = "__PENDENTE__"


def _tokens(values):
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    result = []
    for value in values:
        token = str(value).strip()
        if token and token not in result:
            result.append(token)
    return tuple(result)


def register_adapter(name, runner, *, project_types=(), disciplines=(),
                     deliverables=(), hooks=None):
    """Registra um runner de projeto com o contrato ``(normalized, run_dir)``.

    O runner deve retornar ``(turnkey_result, discipline_records)``; o segundo
    item usa os estados definidos por este módulo. O adaptador nativo do galpão
    é registrado ao carregar o módulo. Metadados e hooks são opcionais para
    manter compatibilidade com runners antigos.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("nome do adaptador deve ser uma string nao vazia")
    if not callable(runner):
        raise TypeError("runner do adaptador deve ser chamavel")
    if hooks is None:
        hooks = {}
    if not isinstance(hooks, dict):
        raise TypeError("hooks do adaptador devem ser um dicionario")
    allowed_hooks = {"report", "coordination", "ifc", "model_3d", "drawings"}
    unknown_hooks = sorted(set(hooks) - allowed_hooks)
    if unknown_hooks:
        raise ValueError("hooks desconhecidos: " + ", ".join(unknown_hooks))
    for hook_name, hook in hooks.items():
        if not callable(hook):
            raise TypeError("hook %s do adaptador deve ser chamavel" % hook_name)
    key = name.strip()
    _PROJECT_ADAPTERS[key] = runner
    _PROJECT_CAPABILITIES[key] = {
        "name": key,
        "project_types": list(_tokens(project_types)),
        "disciplines": list(_tokens(disciplines)),
        "deliverables": list(_tokens(deliverables)),
    }
    _PROJECT_HOOKS[key] = dict(hooks)


def describe_adapters(name=None):
    """Retorna capacidades declaradas sem expor os callables dos hooks."""
    if name is not None:
        key = str(name).strip()
        value = _PROJECT_CAPABILITIES.get(key)
        return [copy.deepcopy(value)] if value is not None else []
    return [copy.deepcopy(_PROJECT_CAPABILITIES[key])
            for key in sorted(_PROJECT_CAPABILITIES)]


def _adapter_capabilities(name):
    value = _PROJECT_CAPABILITIES.get(name)
    if value is None:
        return {
            "name": name,
            "project_types": [],
            "disciplines": [],
            "deliverables": [],
        }
    return copy.deepcopy(value)


@dataclass(frozen=True)
class ProjectLoopOptions:
    """Políticas da execução; não contém premissas de engenharia."""

    required_disciplines: tuple[str, ...] = ()
    require_source_refs: bool = False
    generate_ifc: bool = True
    generate_3d: bool = False
    generate_2d: bool = False
    generate_caderno: bool = False
    folga_mm: float = 1.0
    vol_min_mm3: float = 1000.0
    freecad_exe: str | None = None
    timeout_seconds: int = 1200
    readiness: dict[str, Any] | None = None

    @classmethod
    def from_value(cls, value: "ProjectLoopOptions | dict[str, Any] | None"):
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            raise TypeError("options deve ser ProjectLoopOptions, dict ou None")
        names = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - names)
        if unknown:
            raise ValueError("opcoes desconhecidas: " + ", ".join(unknown))
        data = dict(value)
        if "required_disciplines" in data:
            data["required_disciplines"] = tuple(dict.fromkeys(
                str(item) for item in data["required_disciplines"]))
        return cls(**data)

    def to_dict(self):
        return {
            "required_disciplines": list(self.required_disciplines),
            "require_source_refs": self.require_source_refs,
            "generate_ifc": self.generate_ifc,
            "generate_3d": self.generate_3d,
            "generate_2d": self.generate_2d,
            "generate_caderno": self.generate_caderno,
            "folga_mm": self.folga_mm,
            "vol_min_mm3": self.vol_min_mm3,
            "freecad_exe": self.freecad_exe,
            "timeout_seconds": self.timeout_seconds,
            "readiness": copy.deepcopy(self.readiness),
        }


def _json_safe(value):
    """Converte resultados de motores em uma estrutura JSON sem os alterar."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(child) for child in value]
    return repr(value)


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(value), ensure_ascii=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")


def _ensure_run_dir_available(run_dir):
    """Evita misturar uma nova rodada com saída antiga ou interrompida."""
    run_dir = Path(run_dir)
    if not run_dir.exists():
        return
    if not run_dir.is_dir():
        raise ValueError("pasta da execucao nao e um diretorio: %s" % run_dir)
    if (run_dir / "project-run.json").is_file():
        raise ValueError(
            "diretorio da execucao ja contem project-run.json; use uma pasta nova")
    if any(run_dir.iterdir()):
        raise ValueError("pasta da execucao deve estar vazia")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_runtime_paths(value, run_dir):
    """Normaliza caminhos de resultados auxiliares para o manifesto.

    Resultados de ferramentas legadas podem conter caminhos absolutos mesmo
    quando os artefatos já estão dentro da execução. Caminhos internos viram
    POSIX relativo; um caminho externo é mantido apenas como marcador
    diagnóstico relativo, nunca como caminho absoluto persistido.
    """
    root = Path(run_dir).expanduser().resolve()
    if isinstance(value, dict):
        return {key: _relative_runtime_paths(child, root)
                for key, child in value.items()}
    if isinstance(value, list):
        return [_relative_runtime_paths(child, root) for child in value]
    if isinstance(value, tuple):
        return tuple(_relative_runtime_paths(child, root) for child in value)
    if isinstance(value, str):
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            return value
        try:
            return candidate.resolve().relative_to(root).as_posix()
        except ValueError:
            return "<external-path>/%s" % candidate.name
    return value


def _utc_run_id():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return "project-" + stamp


def _slug(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "projeto"


def _project_type(project):
    if not isinstance(project, dict):
        return None
    for key in ("type", "project_type", "tipo"):
        value = project.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _geometry_from_structural(spec):
    geo = spec.get("geometria") or {}
    if not isinstance(geo, dict):
        return {}
    out = {}
    for target, keys in (
        ("comprimento", ("comprimento", "L")),
        ("vao", ("span", "vao", "W", "largura")),
        ("pe_direito", ("eave", "pe_direito", "H")),
    ):
        for key in keys:
            if geo.get(key) is not None:
                out[target] = geo[key]
                break
    return out


def _geometry_from_turnkey(spec):
    geo = spec.get("geometria") or spec.get("geometry") or {}
    if not isinstance(geo, dict):
        return {}
    out = {}
    for target, keys in (
        ("comprimento", ("comprimento", "L", "length_m")),
        ("vao", ("vao", "W", "largura", "width_m")),
        ("pe_direito", ("pe_direito", "H", "height_m", "eave")),
    ):
        for key in keys:
            if geo.get(key) is not None:
                out[target] = geo[key]
                break
    return out


def _is_structural_legacy(spec):
    if any(key in spec for key in ("terreno", "fundacao")):
        return True
    geo = spec.get("geometria")
    return isinstance(geo, dict) and any(
        key in geo for key in ("span", "eave", "bay", "base_fixed"))


def _add_structure_to_turnkey(turnkey, structure):
    result = copy.deepcopy(turnkey)
    if structure is not None and "aco" not in result:
        result["aco"] = copy.deepcopy(structure)
    if "geometria" not in result:
        result["geometria"] = _geometry_from_structural(structure or {})
    return result


def _inferred_disciplines(turnkey, structure, adapter=None):
    names = [name for name in KNOWN_DISCIPLINES if name in turnkey]
    capabilities = _PROJECT_CAPABILITIES.get(adapter) or {}
    for name in capabilities.get("disciplines", []):
        if name in turnkey and name not in names:
            names.append(name)
    if structure is not None and "aco" not in names:
        names.insert(1 if "concreto" in names else 0, "aco")
    return names


def normalize_spec(spec):
    """Normaliza envelope versionado e os dois formatos legados sem mutação."""
    if not isinstance(spec, dict):
        raise TypeError("spec deve ser um dicionario")
    raw = copy.deepcopy(spec)
    derivations = []
    source_refs_value = raw.get("source_refs")
    source_refs = ({} if source_refs_value is None
                   else copy.deepcopy(source_refs_value))
    adapter = str(raw.get("adapter") or
                  (raw.get("project") or {}).get("adapter") or "galpao")
    project = copy.deepcopy(raw.get("project") or {})

    if raw.get("schema") == "freecad-automatic/project-spec":
        turnkey = copy.deepcopy(raw.get("turnkey") or {})
        structure = copy.deepcopy(raw.get("structure"))
        if structure is not None:
            if "aco" not in turnkey:
                turnkey["aco"] = copy.deepcopy(structure)
                derivations.append("structure -> turnkey.aco")
            if "geometria" not in turnkey:
                turnkey["geometria"] = _geometry_from_structural(structure)
                derivations.append("structure.geometria -> turnkey.geometria")
        if "geometria" not in turnkey and raw.get("geometry"):
            turnkey["geometria"] = copy.deepcopy(raw["geometry"])
            derivations.append("geometry -> turnkey.geometria")
        project_id = _slug(project.get("slug") or raw.get("slug"))
    elif _is_structural_legacy(raw):
        structure = copy.deepcopy(raw)
        turnkey = {"geometria": _geometry_from_structural(raw),
                   "aco": copy.deepcopy(raw)}
        project_id = _slug(raw.get("slug"))
        derivations.append("legacy estrutural -> turnkey.aco")
        derivations.append("legacy estrutural.geometria -> turnkey.geometria")
    else:
        turnkey = copy.deepcopy(raw)
        structure = (copy.deepcopy(raw.get("aco"))
                     if isinstance(raw.get("aco"), dict) else None)
        project_id = _slug(raw.get("slug"))

    if not isinstance(turnkey, dict):
        raise TypeError("turnkey spec deve ser um dicionario")
    if "geometria" not in turnkey:
        geometry = _geometry_from_turnkey(turnkey)
        if geometry:
            turnkey["geometria"] = geometry
            derivations.append("geometry -> turnkey.geometria")
    if "geometria" in turnkey and not isinstance(turnkey["geometria"], dict):
        raise TypeError("geometria do turnkey deve ser um objeto JSON")

    return {
        "adapter": adapter,
        "project_id": project_id,
        "project_type": _project_type(project),
        "turnkey_spec": turnkey,
        "structure_spec": structure,
        "requested_disciplines": _inferred_disciplines(
            turnkey, structure, adapter=adapter),
        "source_refs": source_refs,
        "derivations": derivations,
        "site": copy.deepcopy(raw.get("site") or {}),
        "project": copy.deepcopy(raw.get("project") or {}),
        "raw_spec": raw,
    }


def _selected_turnkey_spec(normalized):
    """Retorna o turnkey de execução limitado às disciplinas solicitadas.

    O input original permanece intacto no manifesto. O recorte evita que uma
    rodada parcial calcule, coordene ou emita entregáveis de verticais que o
    usuário não pediu.
    """
    selected = copy.deepcopy(normalized["turnkey_spec"])
    requested = set(normalized.get("requested_disciplines") or ())
    capabilities = _adapter_capabilities(normalized["adapter"])
    known = set(KNOWN_DISCIPLINES) | set(capabilities.get("disciplines") or ())
    for name in known - requested:
        selected.pop(name, None)
    return selected


def _source_refs_for(source_refs, discipline):
    if isinstance(source_refs, list):
        return source_refs
    if not isinstance(source_refs, dict):
        return []
    value = source_refs.get(discipline, source_refs.get("all", []))
    return value if isinstance(value, list) else []


def _source_ref_validation_issue(source_ref):
    if not isinstance(source_ref, dict):
        return {
            "code": "invalid_source_ref",
            "detail": "referencia de fonte deve ser um objeto JSON",
        }
    source_id = source_ref.get("source_id") or source_ref.get("id")
    if source_id is None or not str(source_id).strip():
        return {
            "code": "invalid_source_ref",
            "detail": "referencia de fonte requer source_id ou id",
        }
    provenance = ("notebook_id", "catalog_id", "path", "uri", "url")
    if not any(source_ref.get(key) is not None
               and str(source_ref.get(key)).strip() for key in provenance):
        return {
            "code": "invalid_source_ref",
            "detail": "referencia de fonte requer notebook_id, catalog_id ou localizador",
        }
    return None


def _source_ref_issue(source_ref):
    """Retorna uma falha somente quando a fonte declara estado não utilizável.

    O loop não consulta o NotebookLM. Ele pode, porém, receber no spec um
    snapshot do estado remoto e não deve aceitar silenciosamente uma fonte
    marcada como erro, processamento ou preparação. Estados textuais locais
    como ``catalogada`` permanecem neutros, pois não são estados do CLI.
    """
    if not isinstance(source_ref, dict) or "status" not in source_ref:
        return None
    status = source_ref.get("status")
    token = str(status).strip().lower()
    unready_numeric = isinstance(status, (int, float)) and not isinstance(status, bool) \
        and status != 2
    unready_text = token in {
        "1", "3", "5", "erro", "error", "processing", "processando",
        "preparation", "preparacao", "preparação",
    }
    if not (unready_numeric or unready_text):
        return None
    return {
        "code": "source_not_ready",
        "source_id": source_ref.get("source_id") or source_ref.get("id"),
        "status": status,
        "detail": "fonte declarada como erro, processamento ou preparação",
    }


def _source_ref_warning(source_ref):
    if not isinstance(source_ref, dict) or not source_ref.get("is_stale"):
        return None
    return {
        "code": "stale_source",
        "source_id": source_ref.get("source_id") or source_ref.get("id"),
        "detail": "fonte marcada como desatualizada; confirmar sincronização",
    }


def _pending_paths(value, path):
    """Retorna caminhos que contêm o marcador explícito de entrada pendente."""
    if value == PENDING_MARKER:
        return [path]
    if isinstance(value, dict):
        paths = []
        for key, child in value.items():
            child_path = "%s.%s" % (path, key) if path else str(key)
            paths.extend(_pending_paths(child, child_path))
        return paths
    if isinstance(value, list):
        paths = []
        for index, child in enumerate(value):
            paths.extend(_pending_paths(child, "%s[%d]" % (path, index)))
        return paths
    return []


def _invalid_coordination_policy(path, detail, **extra):
    return {
        "code": "invalid_coordination_policy",
        "path": path,
        "detail": detail,
        **extra,
    }


def _effective_coordination_policy(normalized, options):
    """Resolve a política declarativa de coordenação do projeto."""
    policy = {
        "enabled": True,
        "folga_mm": options.folga_mm,
        "vol_min_mm3": options.vol_min_mm3,
        "resolution_mode": "manual_approval",
    }
    raw = normalized["raw_spec"].get("coordination_policy")
    if raw is None:
        return policy, []

    errors = []
    if not isinstance(raw, dict):
        return policy, [_invalid_coordination_policy(
            "coordination_policy",
            "coordination_policy deve ser um objeto JSON",
        )]

    allowed = {"enabled", "folga_mm", "vol_min_mm3", "resolution_mode"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        errors.append(_invalid_coordination_policy(
            "coordination_policy",
            "coordination_policy contém chaves desconhecidas",
            keys=unknown,
        ))

    if "enabled" in raw:
        value = raw["enabled"]
        if not isinstance(value, bool):
            errors.append(_invalid_coordination_policy(
                "coordination_policy.enabled",
                "enabled deve ser booleano",
                value=value,
            ))
        else:
            policy["enabled"] = value

    for key in ("folga_mm", "vol_min_mm3"):
        if key not in raw:
            continue
        value = raw[key]
        if (isinstance(value, bool) or
                not isinstance(value, (int, float)) or
                not math.isfinite(float(value)) or
                float(value) < 0):
            errors.append(_invalid_coordination_policy(
                "coordination_policy.%s" % key,
                "%s deve ser número finito >= 0" % key,
                value=value,
            ))
        else:
            policy[key] = float(value)

    if "resolution_mode" in raw:
        value = raw["resolution_mode"]
        if value != "manual_approval":
            errors.append(_invalid_coordination_policy(
                "coordination_policy.resolution_mode",
                "resolution_mode deve ser manual_approval",
                value=value,
            ))
        else:
            policy["resolution_mode"] = value

    return policy, errors


def _preflight(normalized, options, *, validate_discipline_shapes=False):
    turnkey = normalized["turnkey_spec"]
    structure = normalized["structure_spec"]
    requested = list(options.required_disciplines or
                     normalized["requested_disciplines"])
    requested = list(dict.fromkeys(requested))
    errors = []
    warnings = []
    coordination_policy, coordination_policy_errors = (
        _effective_coordination_policy(normalized, options))
    errors.extend(coordination_policy_errors)
    adapter_capabilities = _adapter_capabilities(normalized["adapter"])
    declared_project_type = normalized.get("project_type")
    supported_project_types = adapter_capabilities.get("project_types") or []
    if declared_project_type and supported_project_types:
        supported_tokens = {
            str(value).strip().casefold()
            for value in supported_project_types
        }
        if declared_project_type.casefold() not in supported_tokens:
            errors.append({
                "code": "unsupported_project_type",
                "project_type": declared_project_type,
                "supported_project_types": list(supported_project_types),
                "detail": "tipo de projeto não é suportado pelo adaptador",
            })
    source_document = normalized["source_refs"]
    if not isinstance(source_document, (dict, list)):
        errors.append({
            "code": "invalid_source_refs",
            "detail": "source_refs deve ser um objeto ou lista JSON",
        })
    elif isinstance(source_document, dict):
        for source_key, source_value in source_document.items():
            if not isinstance(source_value, list):
                errors.append({
                    "code": "invalid_source_refs",
                    "discipline": source_key,
                    "detail": "cada entrada de source_refs deve ser uma lista",
                })
    if normalized["adapter"] not in _PROJECT_ADAPTERS:
        errors.append({"code": "unsupported_adapter",
                       "adapter": normalized["adapter"],
                       "supported_adapters": sorted(_PROJECT_ADAPTERS),
                       "detail": "nenhum runner registrado para o adaptador"})
    allowed_disciplines = set(KNOWN_DISCIPLINES) | set(
        adapter_capabilities["disciplines"])
    for discipline in requested:
        if discipline not in allowed_disciplines:
            errors.append({"code": "unsupported_discipline",
                           "discipline": discipline,
                           "detail": "nenhum adaptador de disciplina registrado"})
    geometry = _geometry_from_turnkey(turnkey)
    for key in ("comprimento", "vao", "pe_direito"):
        value = geometry.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            errors.append({"code": "invalid_common_geometry", "path": key,
                           "detail": "geometria comum requer valor numerico > 0"})

    structural = None
    if structure is not None:
        try:
            import projeto_spec as PS
            structural = PS.validar(structure)
        except Exception as exc:
            structural = {"ok": False, "faltando": [], "a_confirmar": [],
                           "avisos": [], "erro": "%s: %s" % (type(exc).__name__, exc)}
        if not structural.get("ok"):
            errors.append({"code": "invalid_structure_spec", "discipline": "aco",
                           "faltando": structural.get("faltando", []),
                           "detail": structural.get("erro")})
        warnings.extend({"code": "structure_warning", "path": path, "detail": detail}
                        for path, detail in structural.get("avisos", []))

    missing_sources = {}
    source_issues = {}
    pending_inputs = {}
    for discipline in requested:
        if discipline in turnkey:
            payload = turnkey[discipline]
            if (validate_discipline_shapes
                    and not isinstance(payload, dict)):
                errors.append({
                    "code": "invalid_discipline_input",
                    "discipline": discipline,
                    "path": "turnkey.%s" % discipline,
                    "detail": "payload da disciplina deve ser um objeto JSON",
                })
            paths = _pending_paths(payload,
                                   "turnkey.%s" % discipline)
            if paths:
                pending_inputs[discipline] = paths
                errors.append({
                    "code": "pending_discipline_input",
                    "discipline": discipline,
                    "paths": paths,
                    "detail": "disciplina ainda contém campos __PENDENTE__",
                })
        refs = _source_refs_for(normalized["source_refs"], discipline)
        issues = []
        for index, source_ref in enumerate(refs):
            validation_issue = _source_ref_validation_issue(source_ref)
            if validation_issue:
                issue = {"index": index, **validation_issue}
                issues.append(issue)
                errors.append({"discipline": discipline, **issue})
                continue
            issue = _source_ref_issue(source_ref)
            if issue:
                issues.append(issue)
                errors.append({"discipline": discipline, **issue})
            warning = _source_ref_warning(source_ref)
            if warning:
                warnings.append({"discipline": discipline, **warning})
        if issues:
            source_issues[discipline] = issues
        if options.require_source_refs:
            if not refs:
                missing_sources[discipline] = {
                    "code": "missing_source_refs",
                    "detail": "nenhuma fonte declarada para a disciplina",
                }
                errors.append({"discipline": discipline, **missing_sources[discipline]})

    return {
        "ok": not errors,
        "can_execute": not any(not item.get("discipline") for item in errors),
        "geometry": geometry,
        "requested_disciplines": requested,
        "errors": errors,
        "warnings": warnings,
        "missing_sources": missing_sources,
        "source_issues": source_issues,
        "pending_inputs": pending_inputs,
        "coordination_policy": coordination_policy,
        "adapter_capabilities": adapter_capabilities,
        "structure": structural,
        "derivations": list(normalized["derivations"]),
    }


def _readiness_status(preflight):
    if not preflight.get("ok"):
        return "blocked"
    if preflight.get("warnings"):
        return "needs_review"
    return "ready"


def preflight_project(spec, out_dir=None, options=None):
    """Homologa um spec sem executar disciplinas ou gerar entregaveis.

    O retorno usa o schema ``project-readiness``. Quando ``out_dir`` e
    informado, o input, o preflight e o manifesto de prontidao sao persistidos
    nessa pasta; nenhum ``project-run.json`` e criado.
    """
    opts = ProjectLoopOptions.from_value(options)
    normalized = normalize_spec(spec)
    requested = list(opts.required_disciplines or
                     normalized["requested_disciplines"])
    normalized["requested_disciplines"] = list(dict.fromkeys(requested))
    preflight = _preflight(
        normalized, opts, validate_discipline_shapes=True)
    status = _readiness_status(preflight)

    run_dir = None
    if out_dir is not None:
        run_dir = Path(out_dir).expanduser().resolve()
        _ensure_run_dir_available(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        _write_json(run_dir / "input" / "spec.json", normalized["raw_spec"])
        _write_json(run_dir / "reports" / "preflight.json", preflight)

    report = {
        "schema": READINESS_SCHEMA,
        "schema_version": READINESS_SCHEMA_VERSION,
        "project_id": normalized["project_id"],
        "project_type": normalized.get("project_type"),
        "adapter": normalized["adapter"],
        "adapter_capabilities": copy.deepcopy(
            preflight.get("adapter_capabilities") or {}),
        "options": opts.to_dict(),
        "input": copy.deepcopy(normalized["raw_spec"]),
        "input_path": "input/spec.json" if run_dir is not None else None,
        "input_sha256": (_sha256_file(run_dir / "input" / "spec.json")
                         if run_dir is not None else None),
        "site": normalized["site"],
        "sources": normalized["source_refs"],
        "requested_disciplines": list(preflight["requested_disciplines"]),
        "coordination_policy": copy.deepcopy(
            preflight["coordination_policy"]),
        "preflight": preflight,
        "status": status,
        "can_start_project_loop": status == "ready",
    }
    if run_dir is not None:
        _write_json(run_dir / "project-readiness.json", report)
    return report


def _empty_discipline(status, **extra):
    value = {"status": status, "native_atende": None, "reprovados": [],
             "gates": {}, "warnings": [], "errors": [], "artifacts": []}
    value.update(extra)
    return value


def _blocked_disciplines(normalized, preflight):
    requested = preflight["requested_disciplines"]
    records = {}
    for name in requested:
        discipline_errors = [copy.deepcopy(item)
                             for item in preflight["errors"]
                             if item.get("discipline") == name]
        if not discipline_errors:
            discipline_errors = [copy.deepcopy(item) for item in preflight["errors"]
                                 if item.get("code") in {
                                     "invalid_common_geometry", "unsupported_adapter",
                                 }]
        if not discipline_errors:
            discipline_errors = [{"code": "preflight_blocked",
                                  "detail": "disciplina não pode iniciar o preflight"}]
        records[name] = _empty_discipline(
            "blocked", errors=discipline_errors,
        )
    return records


def register_artifact(run_dir, path, kind, status="generated", *, discipline=None,
                      required=False, detail=None):
    """Registra um arquivo somente se ele estiver dentro da execução."""
    root = Path(run_dir).expanduser().resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("artefato fora da pasta da execucao: %s" % candidate) from exc
    record = {"path": relative, "kind": kind, "status": status,
              "required": bool(required)}
    if discipline is not None:
        record["discipline"] = discipline
    if detail is not None:
        record["detail"] = str(detail)
    if candidate.is_file():
        record["size"] = candidate.stat().st_size
        record["sha256"] = _sha256_file(candidate)
    else:
        record["size"] = None
        record["sha256"] = None
    return record


def _add_artifact(manifest, run_dir, path, kind, status="generated", **kwargs):
    record = register_artifact(run_dir, path, kind, status, **kwargs)
    paths = {item.get("path") for item in manifest["artifacts"]}
    if record["path"] not in paths:
        manifest["artifacts"].append(record)
    return record


def _record_standard_artifacts(manifest, run_dir):
    for relative, kind in (
        ("input/spec.json", "input-spec"),
        ("reports/preflight.json", "preflight-report"),
        ("reports/disciplinas.json", "discipline-report"),
        ("reports/adapter-result.json", "adapter-result"),
        ("reports/execution-error.json", "execution-error"),
    ):
        path = Path(run_dir) / relative
        if path.is_file():
            _add_artifact(manifest, run_dir, path, kind)


def _record_untracked_artifacts(manifest, run_dir, *, status="partial",
                                kind="partial-artifact"):
    """Registra arquivos produzidos antes de uma falha para não perdê-los."""
    root = Path(run_dir).resolve()
    known = {item.get("path") for item in manifest.get("artifacts", [])}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "project-run.json" or relative in known:
            continue
        _add_artifact(
            manifest, root, path, kind, status=status,
            detail="arquivo encontrado após falha da execução",
        )


def _project_status(records, preflight, deliverables=None, coordination=None):
    statuses = [item["status"] for item in records.values()]
    if not preflight["ok"] or "blocked" in statuses:
        return "blocked"
    if "failed" in statuses:
        return "failed"
    deliverables = deliverables or {}
    if any(item.get("status") == "failed" for item in deliverables.values()
           if isinstance(item, dict)):
        return "failed"
    coordination = coordination or {}
    if coordination.get("status") == "failed":
        return "failed"
    if "needs_review" in statuses:
        return "needs_review"
    if any(item.get("status") == "not_available" for item in deliverables.values()
           if isinstance(item, dict)):
        return "needs_review"
    if coordination.get("status") == "not_available":
        return "needs_review"
    if coordination.get("status") == "disabled":
        return "needs_review"
    if coordination.get("n_revisar", 0) or coordination.get("open", 0):
        return "needs_review"
    return "passed" if statuses else "blocked"


def _base_manifest(normalized, options, run_dir, preflight, *, iteration,
                   parent_run_id, changes, resolutions):
    input_path = run_dir / "input" / "spec.json"
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "run_id": _utc_run_id(),
        "project_id": normalized["project_id"],
        "project_type": normalized.get("project_type"),
        "readiness": copy.deepcopy(options.readiness),
        "adapter": normalized["adapter"],
        "adapter_capabilities": copy.deepcopy(
            preflight.get("adapter_capabilities") or {}),
        "iteration": int(iteration),
        "parent_run_id": parent_run_id,
        "options": options.to_dict(),
        "input": copy.deepcopy(normalized["raw_spec"]),
        "input_path": "input/spec.json",
        "input_sha256": (_sha256_file(input_path) if input_path.is_file() else None),
        "site": normalized["site"],
        "sources": normalized["source_refs"],
        "coordination_policy": copy.deepcopy(
            preflight["coordination_policy"]),
        "preflight": preflight,
        "disciplines": {},
        "deliverables": {},
        "coordination": {"status": "not_run", "open": 0,
                          "n_clashes": 0, "n_revisar": 0,
                          "policy": copy.deepcopy(
                              preflight["coordination_policy"]),
                          "resolution_requests": list(resolutions or [])},
        "artifacts": [],
        "errors": [],
        "changes": dict(changes or {}),
        "resolutions": list(resolutions or []),
        "status": "blocked",
        "atende": False,
        "_runtime_run_dir": str(run_dir),
        "_input_path_exists": input_path.exists(),
    }


def _persist_manifest(run_dir, manifest):
    manifest = copy.deepcopy(manifest)
    runtime_run_dir = manifest.pop("_runtime_run_dir", None)
    manifest.pop("_input_path_exists", None)
    _write_json(run_dir / "project-run.json", manifest)
    if runtime_run_dir is not None:
        manifest["_runtime_run_dir"] = runtime_run_dir
    return manifest


def _persist_verified_manifest(run_dir, manifest):
    """Persiste, verifica artefatos e grava o resultado sem caminho absoluto."""
    _persist_manifest(run_dir, manifest)
    verification = verify_project_run(run_dir)
    persisted_verification = copy.deepcopy(verification)
    persisted_verification.pop("run_dir", None)
    manifest["verification"] = persisted_verification
    if not verification["ok"] and manifest.get("status") != "blocked":
        manifest["status"] = "failed"
        manifest["atende"] = False
    manifest["verification"]["project_status"] = manifest.get("status")
    return _persist_manifest(run_dir, manifest)


def _finish_blocked_manifest(run_dir, normalized, options, preflight, iteration,
                             parent_run_id, changes, resolutions):
    manifest = _base_manifest(normalized, options, run_dir, preflight,
                              iteration=iteration, parent_run_id=parent_run_id,
                              changes=changes, resolutions=resolutions)
    manifest["disciplines"] = _blocked_disciplines(normalized, preflight)
    manifest["deliverables"]["ifc"] = {"status": "blocked"}
    manifest["coordination"] = {
        "status": "blocked", "open": 0, "n_clashes": 0, "n_revisar": 0,
        "policy": copy.deepcopy(preflight["coordination_policy"]),
        "resolution_requests": list(resolutions or []),
    }
    _record_standard_artifacts(manifest, run_dir)
    manifest["status"] = "blocked"
    return _persist_verified_manifest(run_dir, manifest)


def _finish_failed_manifest(run_dir, normalized, options, preflight, iteration,
                            parent_run_id, changes, resolutions, exc):
    """Fecha uma execução que falhou fora dos retornos normais do adaptador."""
    error = {
        "code": "execution_failed",
        "type": type(exc).__name__,
        "detail": str(exc),
    }
    manifest = _base_manifest(normalized, options, run_dir, preflight,
                              iteration=iteration, parent_run_id=parent_run_id,
                              changes=changes, resolutions=resolutions)
    manifest["errors"] = [error]
    manifest["disciplines"] = {
        name: _empty_discipline("failed", errors=[copy.deepcopy(error)])
        for name in preflight.get("requested_disciplines", [])
    }
    manifest["deliverables"] = {
        "ifc": {"status": "failed" if options.generate_ifc else "not_requested"},
        "model_3d": {"status": "failed" if options.generate_3d else "not_requested"},
        "drawings": {"status": "failed" if (
            options.generate_2d or options.generate_caderno) else "not_requested"},
    }
    manifest["coordination"] = {
        "status": "failed", "open": 0, "n_clashes": 0, "n_revisar": 0,
        "policy": copy.deepcopy(preflight["coordination_policy"]),
        "resolution_requests": list(resolutions or []),
        "error": error["detail"],
    }
    _write_json(run_dir / "reports" / "execution-error.json", error)
    _record_standard_artifacts(manifest, run_dir)
    _record_untracked_artifacts(manifest, run_dir)
    manifest["status"] = "failed"
    manifest["atende"] = False
    return _persist_verified_manifest(run_dir, manifest)


def _execute_and_persist(run_dir, normalized, options, preflight, iteration,
                         parent_run_id, changes, resolutions):
    manifest = _base_manifest(normalized, options, run_dir, preflight,
                              iteration=iteration, parent_run_id=parent_run_id,
                              changes=changes, resolutions=resolutions)
    runner = _PROJECT_ADAPTERS.get(normalized["adapter"])
    if runner is None:
        manifest["disciplines"] = _blocked_disciplines(normalized, preflight)
        manifest["status"] = "blocked"
        return _persist_verified_manifest(run_dir, manifest)
    blocked_names = {
        item["discipline"] for item in preflight.get("errors", [])
        if item.get("discipline")
    }
    if (not preflight.get("can_execute", preflight["ok"]) or
            set(preflight["requested_disciplines"]) <= blocked_names):
        manifest["disciplines"] = _blocked_disciplines(normalized, preflight)
        manifest["status"] = "blocked"
        return _persist_verified_manifest(run_dir, manifest)
    runner_parameters = inspect.signature(runner).parameters.values()
    accepts_preflight = any(
        parameter.name == "preflight" or
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in runner_parameters
    )
    result, records = runner(
        normalized, run_dir, preflight=preflight) if accepts_preflight else runner(
            normalized, run_dir)
    manifest["disciplines"] = records
    hooks = _PROJECT_HOOKS.get(normalized["adapter"], {})
    _write_json(run_dir / "reports" / "disciplinas.json", records)
    report_hook = hooks.get("report")
    try:
        if report_hook:
            report_hook(manifest, run_dir, normalized, options, result)
        else:
            _write_json(run_dir / "reports" / "adapter-result.json", result)
            manifest["deliverables"]["adapter_report"] = {
                "status": "generated", "artifacts": ["reports/adapter-result.json"]}
    except Exception as exc:
        manifest["deliverables"]["adapter_report"] = {
            "status": "failed", "error": "%s: %s" % (type(exc).__name__, exc)}

    coordination_hook = hooks.get("coordination")
    try:
        if coordination_hook:
            coordination_hook(manifest, run_dir, normalized, options, result)
        else:
            manifest["coordination"] = {
                "status": "not_available", "open": 0, "n_clashes": 0,
                "n_revisar": 0,
                "policy": copy.deepcopy(preflight["coordination_policy"]),
                "detail": "adaptador não fornece hook de coordenação",
                "resolution_requests": list(resolutions or []),
            }
    except Exception as exc:
        manifest["coordination"] = {
            "status": "failed", "open": 0, "n_clashes": 0, "n_revisar": 0,
            "policy": copy.deepcopy(preflight["coordination_policy"]),
            "error": "%s: %s" % (type(exc).__name__, exc),
            "resolution_requests": list(resolutions or []),
        }

    if hooks.get("ifc"):
        hooks["ifc"](manifest, run_dir, normalized, options, result)
    else:
        manifest["deliverables"]["ifc"] = {
            "status": "not_available" if options.generate_ifc else "not_requested",
            "detail": "adaptador não fornece hook IFC",
        }
    if hooks.get("model_3d"):
        hooks["model_3d"](manifest, run_dir, normalized, options, result)
    else:
        manifest["deliverables"]["model_3d"] = {
            "status": "not_available" if options.generate_3d else "not_requested",
            "detail": "adaptador não fornece hook de modelo 3D",
        }
    if hooks.get("drawings"):
        hooks["drawings"](manifest, run_dir, normalized, options, result)
    else:
        drawings_requested = bool(options.generate_2d or options.generate_caderno)
        manifest["deliverables"]["drawings"] = {
            "status": "not_available" if drawings_requested else "not_requested",
            "detail": "adaptador não fornece hook de desenhos",
        }
    _record_standard_artifacts(manifest, run_dir)
    manifest["status"] = _project_status(
        records, preflight, manifest["deliverables"], manifest["coordination"])
    manifest["atende"] = manifest["status"] == "passed"
    return _persist_verified_manifest(run_dir, manifest)


def classify_discipline(record):
    """Retorna o estado persistido de uma disciplina."""
    status = record.get("status") if isinstance(record, dict) else None
    if status not in DISCIPLINE_STATUSES:
        raise ValueError("estado de disciplina invalido: %r" % (status,))
    return status


def run_project(spec, out_dir, options=None, *, iteration=1,
                parent_run_id=None, changes=None, resolutions=None):
    """Executa uma iteração e grava seu manifesto em ``out_dir``."""
    opts = ProjectLoopOptions.from_value(options)
    normalized = normalize_spec(spec)
    requested = list(opts.required_disciplines or normalized["requested_disciplines"])
    normalized["requested_disciplines"] = list(dict.fromkeys(requested))
    run_dir = Path(out_dir).expanduser().resolve()
    _ensure_run_dir_available(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "input" / "spec.json", normalized["raw_spec"])
    preflight = _preflight(normalized, opts)
    _write_json(run_dir / "reports" / "preflight.json", preflight)
    blocked_names = {
        item["discipline"] for item in preflight.get("errors", [])
        if item.get("discipline")
    }
    if (not preflight.get("can_execute", preflight["ok"]) or
            set(preflight["requested_disciplines"]) <= blocked_names):
        return _finish_blocked_manifest(run_dir, normalized, opts, preflight,
                                        iteration, parent_run_id, changes, resolutions)
    try:
        return _execute_and_persist(run_dir, normalized, opts, preflight,
                                    iteration, parent_run_id, changes, resolutions)
    except Exception as exc:
        return _finish_failed_manifest(
            run_dir, normalized, opts, preflight, iteration, parent_run_id,
            changes, resolutions, exc)


def _load_manifest(value):
    if isinstance(value, dict):
        return copy.deepcopy(value)
    path = Path(value)
    if path.is_dir():
        path = path / "project-run.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_with_run_dir(value):
    if isinstance(value, dict):
        manifest = copy.deepcopy(value)
        raw_run_dir = manifest.get("_runtime_run_dir")
        if not raw_run_dir:
            raise ValueError(
                "manifesto em memoria requer _runtime_run_dir para verificacao")
        run_dir = Path(raw_run_dir).expanduser().resolve()
        return manifest, run_dir

    manifest_path = Path(value).expanduser().resolve()
    run_dir = manifest_path if manifest_path.is_dir() else manifest_path.parent
    if manifest_path.is_dir():
        manifest_path = manifest_path / "project-run.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            "project-run.json nao encontrado: %s" % manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("project-run.json invalido: %s" % manifest_path) from exc
    if not isinstance(manifest, dict):
        raise ValueError("project-run.json deve conter um objeto JSON")
    return manifest, run_dir


def verify_project_run(manifest_or_path):
    """Verifica a integridade dos artefatos declarados por uma execução.

    A função não recalcula o projeto nem altera arquivos. Ela compara presença,
    tamanho e SHA-256 dos artefatos com o manifesto e também rejeita caminhos
    absolutos ou que escapem da pasta da execução.
    """
    manifest, run_dir = _manifest_with_run_dir(manifest_or_path)
    root = run_dir.resolve()
    records = manifest.get("artifacts")
    if not isinstance(records, list):
        raise ValueError("manifesto requer artifacts como lista")

    errors = []
    seen = set()
    checked = 0
    valid = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append({
                "code": "invalid_artifact_record",
                "index": index,
                "detail": "registro de artefato deve ser um objeto JSON",
            })
            continue
        relative = record.get("path")
        if not isinstance(relative, str) or not relative.strip():
            errors.append({
                "code": "invalid_artifact_path",
                "index": index,
                "detail": "artefato requer path relativo",
            })
            continue
        candidate_path = Path(relative)
        if candidate_path.is_absolute():
            errors.append({
                "code": "absolute_artifact_path",
                "index": index,
                "path": relative,
                "detail": "manifesto nao pode persistir caminho absoluto",
            })
            continue
        normalized_relative = candidate_path.as_posix()
        if normalized_relative in seen:
            errors.append({
                "code": "duplicate_artifact_path",
                "index": index,
                "path": normalized_relative,
                "detail": "path de artefato repetido",
            })
            continue
        seen.add(normalized_relative)
        candidate = (root / candidate_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append({
                "code": "artifact_outside_run",
                "index": index,
                "path": relative,
                "detail": "artefato escapa da pasta da execucao",
            })
            continue

        checked += 1
        item_errors = []
        if not candidate.is_file():
            item_errors.append({
                "code": "artifact_missing",
                "path": normalized_relative,
                "detail": "arquivo declarado nao existe",
            })
        else:
            expected_size = record.get("size")
            if expected_size is not None and candidate.stat().st_size != expected_size:
                item_errors.append({
                    "code": "artifact_size_mismatch",
                    "path": normalized_relative,
                    "expected": expected_size,
                    "actual": candidate.stat().st_size,
                })
            expected_hash = record.get("sha256")
            if expected_hash:
                actual_hash = _sha256_file(candidate)
                if actual_hash != expected_hash:
                    item_errors.append({
                        "code": "artifact_hash_mismatch",
                        "path": normalized_relative,
                        "expected": expected_hash,
                        "actual": actual_hash,
                    })
            elif record.get("status", "generated") == "generated":
                item_errors.append({
                    "code": "artifact_hash_missing",
                    "path": normalized_relative,
                    "detail": "artefato gerado requer SHA-256",
                })
        errors.extend(item_errors)
        if not item_errors:
            valid += 1

    return {
        "schema": "freecad-automatic/project-run-verification",
        "schema_version": 1,
        "run_id": manifest.get("run_id"),
        "project_id": manifest.get("project_id"),
        "project_status": manifest.get("status"),
        "run_dir": str(root),
        "artifact_count": len(records),
        "checked_artifacts": checked,
        "valid_artifacts": valid,
        "ok": not errors,
        "errors": errors,
    }


def _set_dotted_path(document, path, value):
    parts = str(path).split(".")
    if not parts or any(not part for part in parts):
        raise ValueError("caminho de alteracao invalido: %r" % (path,))
    target = document
    for part in parts[:-1]:
        if not isinstance(target, dict) or part not in target:
            raise KeyError("caminho de alteracao ausente: %s" % path)
        target = target[part]
    if not isinstance(target, dict):
        raise KeyError("pai do caminho nao e dicionario: %s" % path)
    target[parts[-1]] = copy.deepcopy(value)


def iterate_project(previous_run, spec=None, *, updates=None, resolutions=None,
                    out_dir=None, options=None):
    """Cria uma nova execução a partir de um manifesto, sem alterar o pai."""
    can_verify_parent = (
        isinstance(previous_run, (str, Path))
        or (isinstance(previous_run, dict)
            and previous_run.get("_runtime_run_dir")))
    if can_verify_parent:
        verification = verify_project_run(previous_run)
        if not verification["ok"]:
            codes = sorted({item.get("code", "artifact_error")
                            for item in verification["errors"]})
            raise ValueError(
                "execução pai não íntegra: " + ", ".join(codes))
    parent = _load_manifest(previous_run)
    parent_dir = Path(parent.get("_runtime_run_dir") or
                      parent.get("run_dir") or "")
    if isinstance(previous_run, (str, Path)):
        parent_dir = Path(previous_run).expanduser().resolve()
        if parent_dir.name == "project-run.json":
            parent_dir = parent_dir.parent
    if spec is None:
        input_path = parent_dir / parent.get("input_path", "input/spec.json")
        spec = json.loads(input_path.read_text(encoding="utf-8"))
    else:
        spec = copy.deepcopy(spec)
    changes = dict(updates or {})
    for path, value in changes.items():
        _set_dotted_path(spec, path, value)
    iteration = int(parent.get("iteration", 1)) + 1
    if out_dir is None:
        out_dir = parent_dir.parent / ("iteration-%03d" % iteration)
    parent_options = parent.get("options") or {}
    if isinstance(options, ProjectLoopOptions):
        effective_options = options.to_dict()
    elif options is None:
        effective_options = dict(parent_options)
    else:
        # Dicionario de opcoes e um patch da politica pai: uma alteracao
        # pontual (por exemplo, desligar IFC) nao deve apagar o escopo de
        # disciplinas, o prazo ou a exigencia de fontes da rodada anterior.
        effective_options = dict(parent_options)
        effective_options.update(dict(options))
    if (effective_options.get("readiness") is None and
            parent_options.get("readiness") is not None):
        effective_options["readiness"] = copy.deepcopy(
            parent_options["readiness"])
    return run_project(spec, out_dir, options=effective_options,
                        iteration=iteration, parent_run_id=parent.get("run_id"),
                        changes=changes, resolutions=resolutions)


def review_project(previous_run, resolution_plan, out_dir=None, options=None):
    """Revisa a coordenação do pai e cria uma rodada filha auditável.

    O plano é validado e reduzido a updates aprovados antes de qualquer nova
    execução. O pai nunca é alterado; plano e relatório entram como artefatos
    hashados do filho.
    """
    can_verify_parent = (
        isinstance(previous_run, (str, Path))
        or (isinstance(previous_run, dict)
            and previous_run.get("_runtime_run_dir")))
    if not can_verify_parent:
        raise ValueError(
            "manifesto em memoria requer _runtime_run_dir para verificacao")
    verification = verify_project_run(previous_run)
    if not verification["ok"]:
        codes = sorted({item.get("code", "artifact_error")
                        for item in verification["errors"]})
        raise ValueError("execução pai não íntegra: " + ", ".join(codes))

    parent, parent_dir = _manifest_with_run_dir(previous_run)
    issues_path = parent_dir / "coordination" / "pendencias.json"
    if not issues_path.is_file():
        raise ValueError("execução pai não contém coordination/pendencias.json")
    try:
        parent_issues = json.loads(issues_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("pendências do pai são inválidas") from exc

    plan = validate_resolution_plan(
        load_resolution_plan(resolution_plan), parent_issues, parent)
    approved_updates = collect_approved_updates(plan)
    requested = (parent.get("options") or {}).get("required_disciplines")
    if not requested:
        requested = list((parent.get("disciplines") or {}).keys())
    affected = derive_affected_disciplines(plan, requested)
    review_options = options
    if affected:
        if isinstance(options, ProjectLoopOptions):
            review_options = options.to_dict()
        elif options is None:
            review_options = {}
        else:
            review_options = dict(options)
        requested_scope = list(review_options.get("required_disciplines") or
                               requested)
        review_options["required_disciplines"] = list(dict.fromkeys(
            requested_scope + list(affected)))

    child = iterate_project(
        previous_run,
        updates=approved_updates,
        resolutions=plan["decisions"],
        out_dir=out_dir,
        options=review_options,
    )
    child_dir = Path(child.get("_runtime_run_dir") or out_dir).expanduser().resolve()
    child_issues_path = child_dir / "coordination" / "pendencias.json"
    coordination_output_missing = not child_issues_path.is_file()
    if coordination_output_missing:
        child_issues = parent_issues
    else:
        try:
            child_issues = json.loads(
                child_issues_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            child_issues = parent_issues
            coordination_output_missing = True

    rerun = list((child.get("options") or {}).get("required_disciplines") or
                 (child.get("disciplines") or {}).keys())
    child_verification = verify_project_run(child)
    report = build_review_report(
        parent_issues,
        child_issues,
        plan,
        manifest=child,
        verification=child_verification,
        affected_disciplines=affected,
        rerun_disciplines=rerun,
        applied_updates=approved_updates,
    )
    if coordination_output_missing:
        report["review_status"] = "needs_review"
        report["reasons"].append(
            "coordination/pendencias.json não foi gerado no filho")

    plan_path = child_dir / "coordination" / "resolution-plan.json"
    report_path = child_dir / "coordination" / "review-report.json"
    _write_json(plan_path, plan)
    _write_json(report_path, report)
    child.setdefault("coordination", {})
    child["coordination"].update({
        "review_status": report["review_status"],
        "resolution_plan_path": "coordination/resolution-plan.json",
        "review_report_path": "coordination/review-report.json",
        "affected_disciplines": list(affected),
        "rerun_disciplines": list(rerun),
        "applied_updates": copy.deepcopy(approved_updates),
    })
    child["review"] = {
        "resolution_plan_path": "coordination/resolution-plan.json",
        "review_report_path": "coordination/review-report.json",
        "review_status": report["review_status"],
    }
    if report["review_status"] != "approved" and child.get("status") == "passed":
        child["status"] = "needs_review"
        child["atende"] = False
    _add_artifact(child, child_dir, plan_path, "coordination-resolution-plan",
                  required=True)
    _add_artifact(child, child_dir, report_path, "coordination-review-report",
                  required=True)
    return _persist_verified_manifest(child_dir, child)


def _normalize_sequence_steps(steps):
    if steps is None:
        return []
    if not isinstance(steps, list):
        raise TypeError("steps deve ser uma lista")
    normalized = []
    allowed = {"spec", "updates", "resolutions"}
    for index, raw in enumerate(steps, 1):
        if not isinstance(raw, dict):
            raise TypeError("step %d deve ser um objeto" % index)
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise ValueError(
                "campos desconhecidos no step %d: %s" %
                (index, ", ".join(unknown)))
        updates = raw.get("updates") or {}
        if not isinstance(updates, dict):
            raise ValueError("updates deve ser um objeto (step %d)" % index)
        for path in updates:
            if not isinstance(path, str) or not path.strip():
                raise ValueError("step %d possui caminho de update invalido" % index)
        resolutions = raw.get("resolutions") or []
        if not isinstance(resolutions, list):
            raise TypeError("step %d resolutions deve ser uma lista" % index)
        if any(not isinstance(item, dict) for item in resolutions):
            raise TypeError("step %d resolutions deve conter objetos" % index)
        spec = raw.get("spec")
        if spec is not None and not isinstance(spec, dict):
            raise TypeError("step %d spec deve ser um objeto" % index)
        normalized.append({
            "spec": copy.deepcopy(spec),
            "updates": copy.deepcopy(updates),
            "resolutions": copy.deepcopy(resolutions),
        })
    return normalized


def _sequence_status(runs, errors=None):
    if errors:
        return "failed"
    statuses = [run.get("status") for run in runs]
    if "blocked" in statuses:
        return "blocked"
    if "failed" in statuses:
        return "failed"
    if "needs_review" in statuses:
        return "needs_review"
    return "passed" if statuses and all(status == "passed" for status in statuses) else "blocked"


def _sequence_report(root, sequence_id, project_id, options, steps, runs,
                     errors=None):
    root = Path(root).resolve()
    summaries = []
    for run in runs:
        run_dir = Path(run.get("_runtime_run_dir") or root).resolve()
        try:
            relative = run_dir.relative_to(root).as_posix()
        except ValueError:
            relative = "<external-path>"
        verification = copy.deepcopy(run.get("verification") or {})
        verification.pop("run_dir", None)
        summaries.append({
            "iteration": run.get("iteration"),
            "run_id": run.get("run_id"),
            "parent_run_id": run.get("parent_run_id"),
            "path": relative,
            "status": run.get("status"),
            "verification": verification,
        })
    return {
        "schema": SEQUENCE_SCHEMA,
        "schema_version": SEQUENCE_SCHEMA_VERSION,
        "sequence_id": sequence_id,
        "project_id": project_id,
        "options": options.to_dict(),
        "readiness": copy.deepcopy(options.readiness),
        "requested_iterations": len(steps) + 1,
        "completed_iterations": len(summaries),
        "status": _sequence_status(runs, errors),
        "iterations": summaries,
        "steps": [{
            "updates": step["updates"],
            "resolutions": step["resolutions"],
            "has_spec_override": step["spec"] is not None,
        } for step in steps],
        "errors": list(errors or []),
    }


def run_project_sequence(spec, out_dir, steps=None, options=None):
    """Executa uma sequência declarativa de iterações explícitas.

    A primeira rodada usa ``spec``; cada passo seguinte pode fornecer um
    ``spec`` substituto, ``updates`` e/ou ``resolutions``. Cada execução fica
    em ``iteration-NNN`` e o diretório raiz recebe ``project-sequence.json``.
    Nenhuma alteração é inferida pelo orquestrador.
    """
    opts = ProjectLoopOptions.from_value(options)
    plan = _normalize_sequence_steps(steps)
    normalized = normalize_spec(spec)
    root = Path(out_dir).expanduser().resolve()
    _ensure_run_dir_available(root)
    root.mkdir(parents=True, exist_ok=True)
    sequence_id = _utc_run_id().replace("project-", "sequence-", 1)
    runs = []
    errors = []

    def persist_sequence():
        report = _sequence_report(root, sequence_id, normalized["project_id"],
                                  opts, plan, runs, errors)
        _write_json(root / "project-sequence.json", report)
        return report

    try:
        parent = run_project(spec, root / "iteration-001", options=opts)
        runs.append(parent)
        persist_sequence()
        for index, step in enumerate(plan, 2):
            parent = iterate_project(
                parent,
                spec=step["spec"],
                updates=step["updates"],
                resolutions=step["resolutions"],
                out_dir=root / ("iteration-%03d" % index),
                options=opts,
            )
            runs.append(parent)
            persist_sequence()
    except Exception as exc:
        errors.append({
            "iteration": len(runs) + 1,
            "code": type(exc).__name__,
            "detail": str(exc),
        })
        persist_sequence()
        raise

    return {"sequence": persist_sequence(), "runs": runs}


def load_project_spec(path, *, allow_legacy=True):
    """Reexporta o carregador de arquivo para manter uma API de entrada única."""
    from project_io import load_project_spec as _load_project_spec
    return _load_project_spec(path, allow_legacy=allow_legacy)


def run_project_file(spec_path, out_dir, options=None, *, iteration=1,
                     parent_run_id=None, changes=None, resolutions=None):
    """Executa o Loop usando um spec JSON, sem duplicar o motor."""
    from project_io import run_project_file as _run_project_file
    return _run_project_file(
        spec_path, out_dir, options=options, iteration=iteration,
        parent_run_id=parent_run_id, changes=changes, resolutions=resolutions)


def preflight_project_file(spec_path, out_dir, options=None):
    """Executa somente o gate de prontidao para um spec JSON."""
    from project_io import preflight_project_file as _preflight_project_file
    return _preflight_project_file(spec_path, out_dir, options=options)


from builtin_adapters import register_builtin_adapters

register_builtin_adapters()


__all__ = ["ProjectLoopOptions", "classify_discipline", "describe_adapters",
           "iterate_project", "load_project_spec", "normalize_spec",
           "preflight_project", "preflight_project_file", "register_adapter",
           "register_artifact", "review_project", "run_project",
           "run_project_file", "run_project_sequence", "verify_project_run"]
