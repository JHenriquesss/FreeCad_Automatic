"""Adaptador nativo da tipologia galpao."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import entregaveis_projeto as ep
from project_loop import (
    KNOWN_DISCIPLINES,
    _add_artifact,
    _empty_discipline,
    _json_safe,
    _relative_runtime_paths,
    _selected_turnkey_spec,
    _write_json,
    register_adapter,
)


def _write_coordination(manifest, run_dir, normalized, options, turnkey_result):
    policy = copy.deepcopy(manifest.get("coordination_policy") or {
        "enabled": True,
        "folga_mm": options.folga_mm,
        "vol_min_mm3": options.vol_min_mm3,
        "resolution_mode": "manual_approval",
    })
    if policy.get("enabled") is False:
        manifest["coordination"] = {
            "status": "disabled",
            "open": 0,
            "n_clashes": 0,
            "n_revisar": 0,
            "policy": policy,
            "resolution_requests": manifest["coordination"].get(
                "resolution_requests", []),
        }
        return

    import compatibilizacao as cp
    import galpao_turnkey as tk

    coordination_dir = Path(run_dir) / "coordination"
    coordination_dir.mkdir(parents=True, exist_ok=True)
    report = tk.checa_interferencia_federada(
        turnkey_result, _selected_turnkey_spec(normalized),
        folga=policy["folga_mm"], vol_min=policy["vol_min_mm3"])
    pendencias = cp.gerar_pendencias(report)
    summary = cp.resumo(pendencias)
    _write_json(coordination_dir / "clash.json", report)
    _write_json(coordination_dir / "pendencias.json", pendencias)
    _write_json(coordination_dir / "pendencias.bcf.json", cp.bcf_topics(pendencias))
    (coordination_dir / "matriz.svg").write_text(
        cp.matriz_svg(report, pendencias), encoding="utf-8")
    (coordination_dir / "relatorio.txt").write_text(
        tk.relatorio_clash_pt(report) + "\n\n" + cp.relatorio_pt(pendencias, summary),
        encoding="utf-8")
    manifest["coordination"] = {
        "status": "generated",
        "n_membros": report.get("n_membros", 0),
        "n_clashes": report.get("n_clashes", 0),
        "n_revisar": report.get("n_revisar", 0),
        "n_esperado": report.get("n_esperado", 0),
        "open": summary.get("abertas", 0),
        "OK": report.get("OK"),
        "OK_revisar": report.get("OK_revisar"),
        "policy": policy,
        "resolution_requests": manifest["coordination"].get(
            "resolution_requests", []),
    }
    for relative, kind in (
        ("coordination/clash.json", "clash-report"),
        ("coordination/pendencias.json", "coordination-issues"),
        ("coordination/pendencias.bcf.json", "bcf-topics"),
        ("coordination/matriz.svg", "coordination-matrix"),
        ("coordination/relatorio.txt", "coordination-report"),
    ):
        _add_artifact(manifest, run_dir, Path(run_dir) / relative, kind)


def _emit_ifc(manifest, run_dir, normalized, options, turnkey_result):
    if not options.generate_ifc:
        manifest["deliverables"]["ifc"] = {"status": "not_requested"}
        return
    try:
        import ifc_emit
        if not ifc_emit.disponivel():
            manifest["deliverables"]["ifc"] = {
                "status": "not_available",
                "detail": "ifcopenshell ausente",
            }
            return
        import galpao_turnkey as tk
        bim_dir = Path(run_dir) / "bim"
        bim_dir.mkdir(parents=True, exist_ok=True)
        bim_manifest = tk.emitir_bim(
            turnkey_result, str(run_dir), spec=_selected_turnkey_spec(normalized))
        if isinstance(bim_manifest, dict) and bim_manifest.get("erro"):
            manifest["deliverables"]["ifc"] = {
                "status": "not_available", "detail": bim_manifest["erro"]}
            return

        # O emissor turnkey legado ainda nao tinha HVAC/hidraulica no mapa de
        # arquivos individuais; o loop completa o contrato pelos emissores publicos.
        for name, module_name in (("climatizacao", "galpao_climatizacao"),
                                  ("hidraulica", "galpao_hidraulica")):
            native = (turnkey_result.get("disciplinas", {}).get(name) or {})
            raw = native.get("raw")
            if not native.get("rodou") or not isinstance(raw, dict):
                continue
            path = bim_dir / (name + ".ifc")
            module = __import__(module_name)
            if module.emitir_bim(raw, str(path)) and path.is_file():
                if isinstance(bim_manifest, dict):
                    bim_manifest.setdefault("arquivos", {})[name] = str(path)

        generated = []
        if isinstance(bim_manifest, dict):
            for name, value in (bim_manifest.get("arquivos") or {}).items():
                if isinstance(value, str) and not value.startswith("ERRO:"):
                    path = Path(value)
                    if path.is_file():
                        generated.append(_add_artifact(
                            manifest, run_dir, path, "ifc-discipline",
                            discipline=name))
            federated = bim_manifest.get("federado")
            if isinstance(federated, str) and Path(federated).is_file():
                generated.append(_add_artifact(
                    manifest, run_dir, federated, "ifc-federated"))
        generated_disciplines = {
            item.get("discipline") for item in generated
            if item.get("discipline")
        }
        missing_disciplines = sorted(
            set(normalized["requested_disciplines"]) - generated_disciplines)
        if not generated:
            manifest["deliverables"]["ifc"] = {
                "status": "not_available",
                "detail": "nenhum membro IFC foi emitido",
            }
        elif missing_disciplines:
            manifest["deliverables"]["ifc"] = {
                "status": "failed",
                "artifacts": [item["path"] for item in generated],
                "missing_disciplines": missing_disciplines,
                "detail": "IFC incompleto para as disciplinas solicitadas",
            }
        else:
            manifest["deliverables"]["ifc"] = {
                "status": "generated",
                "artifacts": [item["path"] for item in generated],
            }
    except Exception as exc:
        manifest["deliverables"]["ifc"] = {
            "status": "failed",
            "detail": "%s: %s" % (type(exc).__name__, exc),
        }


def _freecad_executable(options):
    if options.freecad_exe:
        return Path(options.freecad_exe).expanduser()
    configured = os.environ.get("FREECAD_EXE")
    if configured:
        return Path(configured).expanduser()
    return Path(r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")


def _register_tree(manifest, run_dir, root, kind):
    root = Path(root)
    if not root.is_dir():
        return []
    records = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name in {"project-run.json", "spec.json"}:
            continue
        records.append(_add_artifact(manifest, run_dir, path, kind))
    return records


def _optional_status(error, *, unavailable_tokens=("nao encontrado", "indisponivel",
                                                     "ausente", "sem membros")):
    text = str(error).lower()
    if any(token in text for token in unavailable_tokens):
        return "not_available"
    return "failed"


def _emit_model_3d(manifest, run_dir, normalized, options, turnkey_result):
    if not options.generate_3d:
        manifest["deliverables"]["model_3d"] = {"status": "not_requested"}
        return
    if options.freecad_exe and not _freecad_executable(options).is_file():
        manifest["deliverables"]["model_3d"] = {
            "status": "not_available", "detail": "freecad.exe nao encontrado"}
        return
    try:
        import galpao_turnkey as tk
        model_dir = Path(run_dir) / "model"
        model_dir.mkdir(parents=True, exist_ok=True)
        result = tk.montar_3d_federado(
            turnkey_result, str(model_dir), spec=_selected_turnkey_spec(normalized),
            doc_name=normalized["project_id"], timeout=options.timeout_seconds)
        if isinstance(result, dict) and result.get("erro"):
            manifest["deliverables"]["model_3d"] = {
                "status": _optional_status(result["erro"]),
                "detail": result["erro"],
            }
            return
        artifacts = _register_tree(manifest, run_dir, model_dir, "model-3d")
        model_result = result.get("result") if isinstance(result, dict) else None
        model_disciplines = (set(model_result.get("por_disciplina") or {})
                             if isinstance(model_result, dict)
                             and "por_disciplina" in model_result else None)
        missing_disciplines = sorted(
            set(normalized["requested_disciplines"]) - model_disciplines
        ) if model_disciplines is not None else []
        manifest["deliverables"]["model_3d"] = {
            "status": ("failed" if missing_disciplines else
                       ("generated" if artifacts else "not_available")),
            "artifacts": [item["path"] for item in artifacts],
        }
        if missing_disciplines:
            manifest["deliverables"]["model_3d"]["missing_disciplines"] = \
                missing_disciplines
            manifest["deliverables"]["model_3d"]["detail"] = \
                "modelo 3D incompleto para as disciplinas solicitadas"
    except Exception as exc:
        manifest["deliverables"]["model_3d"] = {
            "status": _optional_status(exc),
            "detail": "%s: %s" % (type(exc).__name__, exc),
        }


def _emit_drawings(manifest, run_dir, normalized, options, turnkey_result=None):
    requested = bool(options.generate_2d or options.generate_caderno)
    if not requested:
        manifest["deliverables"]["drawings"] = {"status": "not_requested"}
        return
    if not _freecad_executable(options).is_file():
        manifest["deliverables"]["drawings"] = {
            "status": "not_available", "detail": "freecad.exe nao encontrado"}
        return
    try:
        import caderno_turnkey as ct
        drawings_dir = Path(run_dir) / "drawings"
        drawings_dir.mkdir(parents=True, exist_ok=True)
        result = ct.montar_caderno(
            _selected_turnkey_spec(normalized), str(drawings_dir),
            disciplinas=normalized["requested_disciplines"],
            freecad_exe=str(_freecad_executable(options)),
            timeout=options.timeout_seconds)
        artifacts = _register_tree(manifest, run_dir, drawings_dir, "drawing")
        if isinstance(result, dict) and result.get("path"):
            path = Path(result["path"])
            if path.is_file():
                _add_artifact(manifest, run_dir, path, "executive-dossier")
        error = (result or {}).get("erro") if isinstance(result, dict) else None
        timed_out = isinstance(result, dict) and result.get("timed_out") is True
        requested_disciplines = set(normalized["requested_disciplines"])
        emitted_disciplines = set((result or {}).get("disciplinas") or {}) \
            if isinstance(result, dict) else set()
        missing_disciplines = sorted(requested_disciplines - emitted_disciplines)
        statuses = result.get("status") if isinstance(result, dict) else {}
        statuses = statuses or {}
        failed_disciplines = sorted(
            name for name in requested_disciplines
            if isinstance(statuses.get(name), dict)
            and (statuses[name].get("ok") is False
                 or statuses[name].get("timeout") is True
                 or statuses[name].get("erro"))
        ) if isinstance(statuses, dict) else []
        result_for_manifest = copy.deepcopy(result)
        if isinstance(result_for_manifest, dict):
            result_for_manifest["missing_disciplines"] = missing_disciplines
            result_for_manifest["failed_disciplines"] = failed_disciplines
        status = "failed" if (
            timed_out or missing_disciplines or failed_disciplines) else (
            "generated" if artifacts else _optional_status(
                error or "nenhuma prancha emitida"))
        manifest["deliverables"]["drawings"] = {
            "status": status,
            "result": _json_safe(_relative_runtime_paths(
                result_for_manifest, run_dir)),
        }
    except Exception as exc:
        manifest["deliverables"]["drawings"] = {
            "status": _optional_status(exc),
            "detail": "%s: %s" % (type(exc).__name__, exc),
        }


def _basic_classify(native):
    if not native.get("rodou"):
        return "failed" if native.get("erro") else "blocked"
    if native.get("ATENDE") is False:
        return "failed"
    return "passed"


def _review_signals(value, path=""):
    """Localiza premissas provisorias sem reinterpretar os gates do motor."""
    signals = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = "%s.%s" % (path, key) if path else str(key)
            if key == "default" and child is True:
                signals.append({"code": "assumed_default", "path": child_path,
                                "detail": "valor comercial/default requer confirmacao"})
            if key == "dimensionamento_completo" and child is False:
                signals.append({"code": "incomplete_dimensioning", "path": child_path,
                                "detail": "dimensionamento declarado incompleto"})
            if key == "inconclusivo" and child is True:
                signals.append({"code": "inconclusive", "path": child_path,
                                "detail": "resultado inconclusivo requer decisao"})
            if key == "a_confirmar" and child:
                signals.append({"code": "to_confirm", "path": child_path,
                                "detail": "campo marcado A CONFIRMAR"})
            signals.extend(_review_signals(child, child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            signals.extend(_review_signals(child, "%s[%d]" % (path, index)))
    elif isinstance(value, str) and "A CONFIRMAR" in value.upper():
        signals.append({"code": "to_confirm_text", "path": path,
                        "detail": "resultado contem A CONFIRMAR"})
    return signals


def _preflight_blocked_names(preflight):
    return {
        item["discipline"] for item in preflight.get("errors", [])
        if item.get("discipline")
    }


def _run_turnkey(normalized, run_dir, preflight=None):
    import galpao_turnkey as tk
    preflight = preflight or {"errors": []}
    blocked = _preflight_blocked_names(preflight)
    turnkey_spec = _selected_turnkey_spec(normalized)
    for name in blocked:
        turnkey_spec.pop(name, None)
    result = tk.rodar(turnkey_spec, str(run_dir / "disciplines"))
    records = {}
    for name in normalized["requested_disciplines"]:
        if name in blocked:
            errors = [copy.deepcopy(item) for item in preflight["errors"]
                      if item.get("discipline") == name]
            records[name] = _empty_discipline("blocked", errors=errors)
            continue
        native = result.get("disciplinas", {}).get(name)
        if native is None:
            records[name] = _empty_discipline("blocked",
                                              errors=[{"code": "not_executed"}])
            continue
        warnings = _review_signals(native)
        status = _basic_classify(native)
        if status == "passed" and warnings:
            status = "needs_review"
        records[name] = _empty_discipline(
            status,
            native_atende=native.get("ATENDE"),
            reprovados=list(native.get("reprovados", [])),
            gates=_json_safe(native.get("gates", {})),
            warnings=warnings,
            errors=([{"code": "discipline_error", "detail": native.get("erro")}]
                    if native.get("erro") else []),
            native=native,
        )
    return result, records


def _write_turnkey_report(manifest, run_dir, normalized, options, turnkey_result):
    import galpao_turnkey as tk
    report_path = Path(run_dir) / "reports" / "turnkey.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(tk.relatorio_pt(turnkey_result), encoding="utf-8")
    _add_artifact(manifest, run_dir, report_path, "turnkey-report")


def register_galpao_adapter() -> None:
    register_adapter(
        "galpao", _run_turnkey,
        project_types=("galpao", "industrial"),
        disciplines=KNOWN_DISCIPLINES,
        # A ordem dos extras e a ordem de execucao: o cronograma custeia as
        # atividades com a planilha que o orcamento acabou de gravar.
        deliverables=("ifc", "model_3d", "drawings", "coordination", "iteration",
                      "desenhos_concreto", "orcamento", "cronograma",
                      "caderno_encargos", "pacote_legal", "obras_sitio",
                      "fotovoltaico"),
        hooks={
            "report": _write_turnkey_report,
            "coordination": _write_coordination,
            "ifc": _emit_ifc,
            "model_3d": _emit_model_3d,
            "drawings": _emit_drawings,
            "desenhos_concreto": ep.emitir_desenhos_concreto,
            "orcamento": ep.emitir_orcamento,
            "cronograma": ep.emitir_cronograma,
            "caderno_encargos": ep.emitir_caderno_encargos,
            "pacote_legal": ep.emitir_pacote_legal,
            "obras_sitio": ep.emitir_obras_sitio,
            "fotovoltaico": ep.emitir_fotovoltaico,
        },
    )


register_galpao_adapter()
