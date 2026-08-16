"""Contrato puro para revisão auditável das pendências do Loop 2.

Este módulo não conhece FreeCAD nem executa disciplinas. Ele valida decisões,
calcula o escopo afetado e reconcilia os conflitos persistentes por GUID. A
criação da nova rodada e a persistência de artefatos ficam em ``project_loop``.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PLAN_SCHEMA = "freecad-automatic/coordination-resolution-plan"
PLAN_SCHEMA_VERSION = 1
REPORT_SCHEMA = "freecad-automatic/coordination-review-report"
REPORT_SCHEMA_VERSION = 1
CLASSIFICATIONS = ("expected", "real", "inconclusive")
APPROVAL_STATUSES = ("pending", "approved", "rejected")
RECONCILIATION_STATES = (
    "accepted_expected", "resolved", "reopened", "inconclusive_open",
    "new_open",
)
KNOWN_DISCIPLINES = (
    "concreto", "aco", "eletrico", "incendio", "climatizacao", "hidraulica",
)
_COMMON_PATHS = {"geometria", "estrutura", "common", "comum"}


def _json_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def load_resolution_plan(value: Any) -> dict[str, Any]:
    """Carrega um plano de dicionário ou de arquivo JSON sem alterá-lo."""
    if isinstance(value, dict):
        return _json_copy(value)
    path = Path(value).expanduser()
    if path.is_dir():
        path = path / "coordination" / "resolution-plan.json"
    if not path.is_file():
        raise ValueError("plano de resolução não encontrado: %s" % path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("plano de resolução não está em UTF-8: %s" % path) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            "JSON de plano de resolução inválido em %s (linha %d, coluna %d)"
            % (path, exc.lineno, exc.colno)
        ) from exc
    if not isinstance(document, dict):
        raise ValueError("plano de resolução deve conter um objeto JSON")
    return document


def _issue_list(pendencias: Any) -> list[dict[str, Any]]:
    if isinstance(pendencias, list):
        records = pendencias
    elif isinstance(pendencias, dict):
        records = pendencias.get("pendencias", pendencias.get("issues"))
        if records is None:
            records = pendencias.get("items")
    else:
        records = None
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise ValueError("pendências devem ser uma lista de objetos")
    result = []
    seen_ids = set()
    guid_occurrences = {}
    seen_coordination_keys = set()
    for item in records:
        issue_id = item.get("id", item.get("issue_id"))
        guid = item.get("guid")
        if not isinstance(issue_id, str) or not issue_id.strip():
            raise ValueError("pendência requer id CLH-*")
        if not isinstance(guid, str) or not guid.strip():
            raise ValueError("pendência %s requer guid estável" % issue_id)
        if issue_id in seen_ids:
            raise ValueError("issue_id duplicado: %s" % issue_id)
        seen_ids.add(issue_id)
        occurrence = guid_occurrences.get(guid, 0) + 1
        guid_occurrences[guid] = occurrence
        coordination_key = (
            guid if occurrence == 1 else "%s~%d" % (guid, occurrence))
        while coordination_key in seen_coordination_keys:
            occurrence += 1
            guid_occurrences[guid] = occurrence
            coordination_key = "%s~%d" % (guid, occurrence)
        seen_coordination_keys.add(coordination_key)
        normalized = _json_copy(item)
        normalized["_coordination_key"] = coordination_key
        result.append(normalized)
    return result


def _path_parts(path: Any) -> list[str]:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("update requer caminho pontuado")
    parts = path.split(".")
    if any(not part.strip() for part in parts):
        raise ValueError("caminho de update inválido: %r" % path)
    return parts


def _get_path(document: Any, path: str) -> Any:
    target = document
    for part in _path_parts(path):
        if not isinstance(target, dict) or part not in target:
            raise KeyError(path)
        target = target[part]
    return target


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("approved_at é obrigatório para decisão approved")
    encoded = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(encoded)
    except ValueError as exc:
        raise ValueError("approved_at deve ser timestamp ISO-8601") from exc
    return value.strip()


def _decision_copy(decision: Any, parent_input: dict[str, Any], issue_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise ValueError("cada decisão deve ser um objeto")
    issue_id = decision.get("issue_id")
    if not isinstance(issue_id, str) or not issue_id.strip():
        raise ValueError("decisão requer issue_id")
    if issue_id not in issue_map:
        raise ValueError("issue_id inexistente: %s" % issue_id)
    classification = decision.get("classification")
    if classification not in CLASSIFICATIONS:
        raise ValueError("classification inválida para %s" % issue_id)
    approval_status = decision.get("approval_status")
    if approval_status not in APPROVAL_STATUSES:
        raise ValueError("approval_status inválido para %s" % issue_id)
    updates = decision.get("updates", {})
    if updates is None:
        updates = {}
    if not isinstance(updates, dict):
        raise ValueError("updates deve ser um objeto para %s" % issue_id)
    normalized_updates = {}
    for path, value in updates.items():
        _path_parts(path)
        try:
            _get_path(parent_input, path)
        except KeyError as exc:
            raise ValueError("caminho de update ausente: %s" % path) from exc
        try:
            json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("valor de update não é JSON: %s" % path) from exc
        normalized_updates[path] = _json_copy(value)

    if approval_status != "approved" and normalized_updates:
        raise ValueError("updates só podem existir em decisão approved: %s" % issue_id)
    if approval_status == "approved":
        approver = decision.get("approved_by")
        if not isinstance(approver, str) or not approver.strip():
            raise ValueError("approved_by é obrigatório para decisão approved")
        approved_at = _validate_timestamp(decision.get("approved_at"))
    else:
        approver = decision.get("approved_by")
        approved_at = decision.get("approved_at")
    if (classification == "real" and approval_status == "approved"
            and not normalized_updates):
        raise ValueError("decisão real approved requer update aplicável")

    affected = decision.get("affected_disciplines", [])
    if affected is None:
        affected = []
    if not isinstance(affected, list) or any(
            item not in KNOWN_DISCIPLINES for item in affected):
        raise ValueError("affected_disciplines inválidas para %s" % issue_id)

    normalized = _json_copy(decision)
    normalized.update({
        "issue_id": issue_id,
        "classification": classification,
        "approval_status": approval_status,
        "approved_by": approver,
        "approved_at": approved_at,
        "affected_disciplines": list(dict.fromkeys(affected)),
        "updates": normalized_updates,
    })
    return normalized


def validate_resolution_plan(
    plan: Any,
    pendencias: Any,
    parent_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Valida e normaliza o plano completo antes de criar uma execução."""
    normalized = load_resolution_plan(plan)
    if normalized.get("schema") != PLAN_SCHEMA:
        raise ValueError("schema de plano de resolução não suportado")
    if normalized.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise ValueError("schema_version de plano de resolução não suportado")
    if not isinstance(parent_manifest, dict):
        raise ValueError("manifesto pai inválido")
    if normalized.get("parent_run_id") != parent_manifest.get("run_id"):
        raise ValueError("parent_run_id não corresponde ao manifesto pai")
    if normalized.get("project_id") != parent_manifest.get("project_id"):
        raise ValueError("project_id não corresponde ao manifesto pai")
    parent_input = parent_manifest.get("input")
    if not isinstance(parent_input, dict):
        raise ValueError("manifesto pai não contém input de spec")
    issues = _issue_list(pendencias)
    issue_map = {item.get("id", item.get("issue_id")): item for item in issues}
    decisions = normalized.get("decisions", [])
    if not isinstance(decisions, list):
        raise ValueError("decisions deve ser uma lista")
    validated = []
    seen = set()
    for raw in decisions:
        decision = _decision_copy(raw, parent_input, issue_map)
        issue_id = decision["issue_id"]
        if issue_id in seen:
            raise ValueError("decisão duplicada para issue_id: %s" % issue_id)
        seen.add(issue_id)
        validated.append(decision)
    normalized["decisions"] = validated
    return normalized


def _decision_map(plan: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(plan, dict) or not isinstance(plan.get("decisions", []), list):
        raise ValueError("plano requer decisions como lista")
    return {item["issue_id"]: item for item in plan["decisions"]}


def classify_pendencias(
    pendencias: Any,
    plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Adiciona classificação calculada, sem mutar a lista de origem."""
    issues = _issue_list(pendencias)
    decisions = _decision_map(plan) if plan is not None else {}
    result = []
    for issue in issues:
        issue_id = issue.get("id", issue.get("issue_id"))
        decision = decisions.get(issue_id)
        classification = (
            decision.get("classification") if decision else
            ("expected" if issue.get("esperado") is True else "inconclusive")
        )
        item = _json_copy(issue)
        item.pop("_coordination_key", None)
        item["classification"] = classification
        item["approval_status"] = (
            decision.get("approval_status") if decision else "pending")
        result.append(item)
    return result


def collect_approved_updates(plan: dict[str, Any]) -> dict[str, Any]:
    """Combina updates aprovados e rejeita valores divergentes no mesmo path."""
    result = {}
    for decision in plan.get("decisions", []):
        if decision.get("approval_status") != "approved":
            continue
        for path, value in (decision.get("updates") or {}).items():
            if path in result and result[path] != value:
                raise ValueError("updates conflitantes para o caminho: %s" % path)
            result[path] = _json_copy(value)
    return result


def _discipline_from_path(path: str) -> str | None:
    parts = _path_parts(path)
    for part in parts:
        if part in KNOWN_DISCIPLINES:
            return part
        if part in _COMMON_PATHS:
            return part
    return None


def derive_affected_disciplines(
    plan: dict[str, Any],
    requested_disciplines: Any,
) -> list[str]:
    """Calcula o escopo afetado, preservando a ordem do escopo solicitado."""
    requested = list(dict.fromkeys(
        item for item in (requested_disciplines or [])
        if isinstance(item, str) and item in KNOWN_DISCIPLINES
    ))
    affected = set()
    common = False
    for decision in plan.get("decisions", []):
        affected.update(
            item for item in decision.get("affected_disciplines", [])
            if item in KNOWN_DISCIPLINES
        )
        if decision.get("approval_status") != "approved":
            continue
        for path in (decision.get("updates") or {}):
            discipline = _discipline_from_path(path)
            if discipline in _COMMON_PATHS:
                common = True
            elif discipline in KNOWN_DISCIPLINES:
                affected.add(discipline)
    if common:
        return requested
    ordered = [item for item in requested if item in affected]
    ordered.extend(item for item in KNOWN_DISCIPLINES
                   if item in affected and item not in ordered)
    return ordered


def _effective_classification(issue: dict[str, Any], decisions: dict[str, dict[str, Any]]) -> str:
    decision = decisions.get(issue.get("id", issue.get("issue_id")))
    if decision is None:
        return "expected" if issue.get("esperado") is True else "inconclusive"
    if decision.get("classification") == "real" and \
            decision.get("approval_status") != "approved":
        return "inconclusive"
    return decision.get("classification")


def _empty_counts() -> dict[str, int]:
    return {state: 0 for state in RECONCILIATION_STATES}


def reconcile_pendencias(
    parent_pendencias: Any,
    child_pendencias: Any,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Reconcilia pai e filho por identidade estável, nunca pela posição."""
    parent = _issue_list(parent_pendencias)
    child = _issue_list(child_pendencias)
    decisions = _decision_map(plan)
    child_by_key = {item["_coordination_key"]: item for item in child}
    parent_keys = {item["_coordination_key"] for item in parent}
    items = []
    counts = _empty_counts()
    open_issue_ids = []
    resolved_issue_ids = []

    for issue in parent:
        issue_id = issue.get("id", issue.get("issue_id"))
        guid = issue["guid"]
        coordination_key = issue["_coordination_key"]
        classification = _effective_classification(issue, decisions)
        present = coordination_key in child_by_key
        if classification == "expected":
            state = "accepted_expected"
        elif classification == "real":
            state = "reopened" if present else "resolved"
        else:
            state = "inconclusive_open"
        item = {
            "issue_id": issue_id,
            "guid": guid,
            "coordination_key": coordination_key,
            "classification": classification,
            "state": state,
            "parent_present": True,
            "child_present": present,
        }
        items.append(item)
        counts[state] += 1
        if state == "resolved":
            resolved_issue_ids.append(issue_id)
        elif state not in {"accepted_expected", "resolved"}:
            open_issue_ids.append(issue_id)

    for issue in child:
        if issue["_coordination_key"] in parent_keys:
            continue
        issue_id = issue.get("id", issue.get("issue_id"))
        item = {
            "issue_id": issue_id,
            "guid": issue["guid"],
            "coordination_key": issue["_coordination_key"],
            "classification": "inconclusive",
            "state": "new_open",
            "parent_present": False,
            "child_present": True,
        }
        items.append(item)
        counts["new_open"] += 1
        open_issue_ids.append(issue_id)

    return {
        "items": items,
        "counts": counts,
        "open_issue_ids": open_issue_ids,
        "resolved_issue_ids": resolved_issue_ids,
    }


def _requested_deliverables(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    options = manifest.get("options") or {}
    result = []
    if options.get("generate_ifc"):
        result.append(("ifc", "ifc"))
    if options.get("generate_3d"):
        result.append(("model_3d", "model_3d"))
    if options.get("generate_2d"):
        result.append(("drawings", "drawings"))
    if options.get("generate_caderno") and not any(
            item[0] == "drawings" for item in result):
        result.append(("drawings", "caderno"))
    return result


def build_review_report(
    parent_pendencias: Any,
    child_pendencias: Any,
    plan: dict[str, Any],
    *,
    manifest: dict[str, Any],
    verification: dict[str, Any],
    affected_disciplines: Any = (),
    rerun_disciplines: Any = (),
    applied_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monta o relatório persistível e decide somente o status da coordenação."""
    reconciliation = reconcile_pendencias(parent_pendencias, child_pendencias, plan)
    reasons = []
    if reconciliation["open_issue_ids"]:
        reasons.append("há pendências de coordenação abertas")
    if verification.get("ok") is not True:
        reasons.append("verificação de hashes do filho falhou")
    preflight = manifest.get("preflight") or {}
    if preflight.get("ok") is not True or preflight.get("can_execute") is False:
        reasons.append("preflight não libera a execução")
    if manifest.get("status") in {"blocked", "failed"}:
        reasons.append("a execução filha está bloqueada ou falhou")
    native_statuses = {
        name: record.get("status")
        for name, record in (manifest.get("disciplines") or {}).items()
        if isinstance(record, dict)
    }
    native_blockers = {
        name: record.get("status")
        for name, record in (manifest.get("disciplines") or {}).items()
        if isinstance(record, dict) and record.get("status") in {"blocked", "failed"}
    }
    if native_blockers:
        reasons.append("há disciplina bloqueada ou reprovada")
    deliverables = manifest.get("deliverables") or {}
    missing_deliverables = []
    for key, label in _requested_deliverables(manifest):
        if (deliverables.get(key) or {}).get("status") != "generated":
            missing_deliverables.append(label)
    if missing_deliverables:
        reasons.append("entregáveis ausentes: " + ", ".join(missing_deliverables))
    review_status = "approved" if not reasons else "needs_review"
    decisions = plan.get("decisions", [])
    return {
        "schema": REPORT_SCHEMA,
        "schema_version": REPORT_SCHEMA_VERSION,
        "review_status": review_status,
        "reconciliation": reconciliation,
        "classification_counts": {
            classification: sum(
                1 for item in reconciliation["items"]
                if item["classification"] == classification
            )
            for classification in CLASSIFICATIONS
        },
        "decision_count": len(decisions),
        "approved_decision_count": sum(
            1 for item in decisions if item.get("approval_status") == "approved"),
        "open_issue_ids": list(reconciliation["open_issue_ids"]),
        "resolved_issue_ids": list(reconciliation["resolved_issue_ids"]),
        "affected_disciplines": list(affected_disciplines or []),
        "rerun_disciplines": list(rerun_disciplines or []),
        "applied_updates": _json_copy(applied_updates or {}),
        "verification": {
            "ok": verification.get("ok") is True,
            "artifact_count": verification.get("artifact_count"),
            "valid_artifacts": verification.get("valid_artifacts"),
        },
        "native_blockers": native_blockers,
        "native_statuses": native_statuses,
        "missing_deliverables": missing_deliverables,
        "reasons": reasons,
    }


__all__ = [
    "APPROVAL_STATUSES", "CLASSIFICATIONS", "PLAN_SCHEMA",
    "RECONCILIATION_STATES", "build_review_report", "classify_pendencias",
    "collect_approved_updates", "derive_affected_disciplines",
    "load_resolution_plan", "reconcile_pendencias", "validate_resolution_plan",
]
