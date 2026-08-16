"""CLI fina para executar um spec de projeto por arquivo."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from project_io import (ProjectSpecFileError, preflight_project_file,
                        run_project_file)


class ReadinessBlockedError(RuntimeError):
    """O manifesto de prontidão existe, mas não libera a execução."""


def build_parser():
    parser = argparse.ArgumentParser(
        description="Executa o Loop de projeto a partir de um spec JSON")
    parser.add_argument("--spec", help="caminho do spec JSON")
    parser.add_argument("--iterate-from", dest="iterate_from",
                        help="manifesto ou pasta da iteração pai")
    parser.add_argument("--review-from", dest="review_from",
                        help="manifesto/pasta pai para revisao de coordenacao")
    parser.add_argument("--resolution-plan", dest="resolution_plan",
                        help="plano JSON de decisoes para revisao")
    parser.add_argument("--iteration-plan", dest="iteration_plan",
                        help="JSON com passos explícitos de iteração")
    parser.add_argument("--verify-run", dest="verify_run",
                        help="verificar manifesto e hashes de uma execução")
    parser.add_argument("--verify-source-refs", action="store_true",
                        help="consultar ao vivo as fontes declaradas no spec")
    parser.add_argument("--preflight-only", action="store_true",
                        help="homologar o spec sem executar disciplinas")
    parser.add_argument("--out-dir",
                        help="pasta da iteração de saída")
    parser.add_argument("--readiness",
                        help="project-readiness.json aprovado para iniciar")
    parser.add_argument("--no-ifc", action="store_true",
                        help="não solicitar a emissão IFC")
    parser.add_argument("--generate-3d", action="store_true",
                        help="solicitar modelo 3D opcional")
    parser.add_argument("--generate-2d", action="store_true",
                        help="solicitar desenhos 2D opcionais")
    parser.add_argument("--generate-caderno", action="store_true",
                        help="solicitar caderno opcional")
    parser.add_argument("--require-source-refs", action="store_true",
                        help="bloquear disciplinas sem fonte declarada")
    parser.add_argument("--required-discipline", action="append",
                        dest="required_disciplines", metavar="NOME",
                        help="disciplina obrigatória; pode ser repetida")
    parser.add_argument("--freecad-exe",
                        help="executável FreeCAD para entregáveis opcionais")
    parser.add_argument("--update", action="append", default=[],
                        dest="updates", metavar="CAMINHO=JSON",
                        help="alteração pontual para uma iteração; pode repetir")
    parser.add_argument("--resolution", action="append", default=[],
                        dest="resolutions", metavar="JSON",
                        help="decisão JSON para uma iteração; pode repetir")
    return parser


def _options(args, *, readiness=None):
    options = {
        "generate_ifc": not args.no_ifc,
        "generate_3d": args.generate_3d,
        "generate_2d": args.generate_2d,
        "generate_caderno": args.generate_caderno,
        "require_source_refs": args.require_source_refs,
    }
    if args.required_disciplines:
        options["required_disciplines"] = args.required_disciplines
    if args.freecad_exe:
        options["freecad_exe"] = args.freecad_exe
    if readiness is not None:
        options["readiness"] = readiness
    return options


def _review_options(args):
    """Retorna somente patches explicitamente solicitados na revisao."""
    options = {}
    if args.no_ifc:
        options["generate_ifc"] = False
    if args.generate_3d:
        options["generate_3d"] = True
    if args.generate_2d:
        options["generate_2d"] = True
    if args.generate_caderno:
        options["generate_caderno"] = True
    if args.require_source_refs:
        options["require_source_refs"] = True
    if args.required_disciplines:
        options["required_disciplines"] = args.required_disciplines
    if args.freecad_exe:
        options["freecad_exe"] = args.freecad_exe
    return options


def _status_code(status):
    return {"passed": 0, "needs_review": 0, "blocked": 2,
            "failed": 3}.get(status, 3)


def _readiness_status_code(status):
    return {"ready": 0, "needs_review": 1, "blocked": 2}.get(status, 3)


def _source_status_code(status):
    return {"ready": 0, "blocked": 2}.get(status, 3)


def _parse_updates(values):
    updates = {}
    for item in values or []:
        path, separator, encoded = str(item).partition("=")
        if not separator or not path.strip():
            raise ValueError(
                "--update deve usar CAMINHO=JSON: %s" % item)
        try:
            value = json.loads(encoded)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "valor JSON invalido em --update %s" % path) from exc
        updates[path.strip()] = value
    return updates


def _parse_resolutions(values):
    resolutions = []
    for item in values or []:
        try:
            value = json.loads(item)
        except json.JSONDecodeError as exc:
            raise ValueError("--resolution deve conter JSON valido") from exc
        if not isinstance(value, dict):
            raise ValueError("--resolution deve conter um objeto JSON")
        resolutions.append(value)
    return resolutions


def _load_iteration_plan(path):
    source = Path(path).expanduser()
    if not source.is_file():
        raise ValueError("arquivo de plano não encontrado: %s" % source)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("plano não está em UTF-8: %s" % source) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            "JSON de plano inválido em %s (linha %d, coluna %d)"
            % (source, exc.lineno, exc.colno)) from exc
    if isinstance(document, dict):
        document = document.get("steps")
    if not isinstance(document, list):
        raise ValueError("plano deve ser uma lista ou objeto com steps")
    return document


def _load_readiness(path):
    source = Path(path).expanduser()
    if source.is_dir():
        source = source / "project-readiness.json"
    if not source.is_file():
        raise ValueError("manifesto de readiness não encontrado: %s" % source)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("readiness não está em UTF-8: %s" % source) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            "JSON de readiness inválido em %s (linha %d, coluna %d)"
            % (source, exc.lineno, exc.colno)) from exc
    if not isinstance(document, dict):
        raise ValueError("readiness deve conter um objeto JSON")
    return source.resolve(), document


def _validate_readiness(path, document, spec, *, require_source_refs=False):
    if document.get("schema") != "freecad-automatic/project-readiness":
        raise ValueError("schema de readiness não suportado")
    if document.get("schema_version") != 1:
        raise ValueError("schema_version de readiness não suportado")
    if document.get("status") != "ready" or \
            document.get("can_start_project_loop") is not True:
        raise ReadinessBlockedError(
            "readiness não libera o Loop 2: %s" % document.get("status"))
    if "input" not in document or document["input"] != spec:
        raise ValueError("readiness não corresponde ao spec informado")
    from project_loop import normalize_spec
    project_id = normalize_spec(spec)["project_id"]
    if document.get("project_id") != project_id:
        raise ValueError("project_id do readiness não corresponde ao spec")
    if require_source_refs:
        source = document.get("source_verification")
        if not isinstance(source, dict) or source.get("status") != "ready" \
                or source.get("ok") is not True:
            raise ReadinessBlockedError(
                "readiness não contém verificação viva de fontes liberada")
    return path


def _canonical_sha256(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _readiness_metadata(path, document):
    source = document.get("source_verification")
    metadata = {
        "schema": document.get("schema"),
        "schema_version": document.get("schema_version"),
        "status": document.get("status"),
        "can_start_project_loop": document.get("can_start_project_loop"),
        "project_id": document.get("project_id"),
        "input_sha256": _canonical_sha256(document.get("input")),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    if isinstance(source, dict):
        metadata["source_verification"] = {
            "status": source.get("status"),
            "ok": source.get("ok"),
            "checked_references": source.get("checked_references"),
            "error_count": len(source.get("errors", [])),
        }
    return metadata


def _invalid_input(exc):
    print(json.dumps({"status": "invalid_input", "error": str(exc)},
                     ensure_ascii=False))
    return 4


def main(argv=None):
    args = build_parser().parse_args(argv)
    readiness_path = None
    try:
        if args.verify_run:
            if (args.spec or args.iterate_from or args.review_from or
                    args.resolution_plan or args.out_dir or
                    args.iteration_plan or args.verify_source_refs or
                    args.readiness or args.preflight_only or
                    args.updates or args.resolutions):
                raise ValueError(
                    "--verify-run não pode ser combinado com execução ou iteração")
            from project_loop import verify_project_run
            verification = verify_project_run(args.verify_run)
            print(json.dumps(verification, ensure_ascii=False))
            return 0 if verification["ok"] else 3
        if args.verify_source_refs:
            if (args.iterate_from or args.review_from or args.resolution_plan or
                    args.iteration_plan or
                    args.readiness or args.updates or args.resolutions):
                raise ValueError(
                    "--verify-source-refs não pode ser combinado com execução ou iteração")
            if not args.spec:
                raise ValueError("--verify-source-refs exige --spec")
            if not args.out_dir:
                raise ValueError("verificação de fontes requer --out-dir")
            from project_io import load_project_spec
            from project_source_gate import (persist_source_verification,
                                             verify_project_source_refs)
            spec = load_project_spec(args.spec)
            verification = verify_project_source_refs(spec)
            if args.preflight_only:
                result = preflight_project_file(
                    args.spec, args.out_dir, options=_options(args))
                source_ok = verification.get("ok") is True
                if not source_ok:
                    result["status"] = "blocked"
                result["source_verification"] = verification
                result["can_start_project_loop"] = bool(
                    result.get("can_start_project_loop") and source_ok and
                    result.get("status") == "ready")
                report_path = (Path(args.out_dir).expanduser().resolve()
                               / "reports" / "source-verification.json")
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                readiness_path = (Path(args.out_dir).expanduser().resolve()
                                  / "project-readiness.json")
                readiness_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                print(json.dumps({
                    "project_id": result.get("project_id"),
                    "status": result.get("status"),
                    "can_start_project_loop": result.get(
                        "can_start_project_loop"),
                    "source_status": verification.get("status"),
                    "manifest": str(readiness_path),
                }, ensure_ascii=False))
                return _readiness_status_code(result.get("status"))
            report_path = persist_source_verification(
                verification, args.out_dir)
            print(json.dumps({
                "project_id": verification.get("project_id"),
                "status": verification.get("status"),
                "ok": verification.get("ok"),
                "checked_references": verification.get("checked_references"),
                "errors": len(verification.get("errors", [])),
                "manifest": str(report_path),
            }, ensure_ascii=False))
            return _source_status_code(verification.get("status"))
        if args.iteration_plan:
            if args.iterate_from or args.review_from or args.resolution_plan:
                raise ValueError(
                    "--iteration-plan não pode ser combinado com --iterate-from")
            if args.preflight_only:
                raise ValueError(
                    "--iteration-plan não pode ser combinado com --preflight-only")
            if args.updates or args.resolutions:
                raise ValueError(
                    "--iteration-plan não pode ser combinado com --update/--resolution")
            if not args.spec:
                raise ValueError("--iteration-plan exige --spec")
            if not args.out_dir:
                raise ValueError("execução requer --out-dir")
            if not args.readiness:
                raise ValueError(
                    "--iteration-plan exige --readiness aprovado")
            from project_io import load_project_spec
            from project_loop import run_project_sequence
            spec = load_project_spec(args.spec)
            execution_options = _options(args)
            if args.readiness:
                readiness_path, readiness = _load_readiness(args.readiness)
                _validate_readiness(
                    readiness_path, readiness, spec,
                    require_source_refs=args.require_source_refs)
                execution_options = _options(
                    args, readiness=_readiness_metadata(readiness_path, readiness))
            plan = _load_iteration_plan(args.iteration_plan)
            result = run_project_sequence(
                spec, args.out_dir, steps=plan, options=execution_options)
            sequence = result["sequence"]
            manifest = (Path(args.out_dir).expanduser().resolve()
                        / "project-sequence.json")
            output = {
                "project_id": sequence.get("project_id"),
                "status": sequence.get("status"),
                "completed_iterations": sequence.get("completed_iterations"),
                "manifest": str(manifest),
            }
            if readiness_path is not None:
                output["readiness"] = str(readiness_path)
            print(json.dumps(output, ensure_ascii=False))
            return _status_code(sequence.get("status"))
        if args.review_from or args.resolution_plan:
            if not args.review_from or not args.resolution_plan:
                raise ValueError(
                    "--review-from e --resolution-plan devem ser usados juntos")
            if (args.spec or args.iterate_from or args.iteration_plan or
                    args.verify_source_refs or args.readiness or
                    args.preflight_only or args.updates or args.resolutions):
                raise ValueError(
                    "revisao nao pode ser combinada com execucao/iteracao")
            if not args.out_dir:
                raise ValueError("revisao requer --out-dir")
            from project_loop import review_project
            result = review_project(
                args.review_from, args.resolution_plan,
                out_dir=args.out_dir, options=_review_options(args))
            manifest = (Path(args.out_dir).expanduser().resolve()
                        / "project-run.json")
            print(json.dumps({
                "project_id": result.get("project_id"),
                "status": result.get("status"),
                "review_status": (result.get("coordination") or {}).get(
                    "review_status"),
                "run_id": result.get("run_id"),
                "manifest": str(manifest),
            }, ensure_ascii=False))
            return _status_code(result.get("status"))
        if args.readiness and args.preflight_only:
            raise ValueError(
                "--readiness não pode ser combinado com --preflight-only")
        if args.readiness and args.iterate_from:
            raise ValueError(
                "--readiness só pode liberar uma execução inicial com --spec")
        if not args.spec and not args.iterate_from:
            raise ValueError("informe --spec, --iterate-from ou --review-from")
        if not args.out_dir:
            raise ValueError("execução requer --out-dir")
        updates = _parse_updates(args.updates)
        resolutions = _parse_resolutions(args.resolutions)
        if args.iterate_from:
            if args.preflight_only:
                raise ValueError(
                    "--preflight-only exige --spec; homologue o spec antes da iteração")
            if not args.spec and not updates and not resolutions:
                raise ValueError(
                    "uma iteração exige --spec, --update ou --resolution")
            from project_io import load_project_spec
            from project_loop import iterate_project
            spec_override = (load_project_spec(args.spec)
                             if args.spec else None)
            result = iterate_project(
                args.iterate_from, spec=spec_override, out_dir=args.out_dir,
                updates=updates, resolutions=resolutions,
                options=_options(args))
        else:
            if updates or resolutions:
                raise ValueError(
                    "--update/--resolution só podem ser usados com --iterate-from")
            if args.preflight_only:
                result = preflight_project_file(
                    args.spec, args.out_dir, options=_options(args))
                manifest = (Path(args.out_dir).expanduser().resolve()
                            / "project-readiness.json")
                print(json.dumps({
                    "project_id": result.get("project_id"),
                    "status": result.get("status"),
                    "can_start_project_loop": result.get(
                        "can_start_project_loop"),
                    "manifest": str(manifest),
                }, ensure_ascii=False))
                return _readiness_status_code(result.get("status"))
            if args.readiness:
                from project_io import load_project_spec
                readiness_path, readiness = _load_readiness(args.readiness)
                spec = load_project_spec(args.spec)
                _validate_readiness(
                    readiness_path, readiness, spec,
                    require_source_refs=args.require_source_refs)
            execution_options = _options(args)
            if readiness_path is not None:
                execution_options = _options(
                    args, readiness=_readiness_metadata(readiness_path, readiness))
            result = run_project_file(args.spec, args.out_dir,
                                      options=execution_options)
    except ReadinessBlockedError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)},
                         ensure_ascii=False))
        return 2
    except (ProjectSpecFileError, KeyError, OSError, TypeError, ValueError) as exc:
        return _invalid_input(exc)

    manifest = Path(args.out_dir).expanduser().resolve() / "project-run.json"
    output = {
        "project_id": result.get("project_id"),
        "status": result.get("status"),
        "run_id": result.get("run_id"),
        "manifest": str(manifest),
    }
    if readiness_path is not None:
        output["readiness"] = str(readiness_path)
    print(json.dumps(output, ensure_ascii=False))
    return _status_code(result.get("status"))


if __name__ == "__main__":
    raise SystemExit(main())
