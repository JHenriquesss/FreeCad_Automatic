#!/usr/bin/env python3
"""
Gera sidecar G19 a partir de um project-spec.json ready.

Extrai do run efêmero (project_loop) os valores que o harness compara
(peso_aco, Mcol, perfis) e preenche o template
docs/validacao_g15/galpao-sjb-valores-referencia.json.template.

Uso:
    python tools/gerar_sidecar.py --spec projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json --out /tmp/meu-sidecar.json
    python tools/gerar_sidecar.py --spec projects/galpao-sjb/project-spec.json --out docs/validacao_g15/galpao-sjb-valores-referencia.json
    # depois edite --out para adicionar fonte CREA/ART/pagina e anexe o PDF

O sidecar gerado já vem com 0.0% de divergência contra o framework (pois foi extraído dele);
substitua os valores pelos do memorial real quando for validar contra obra construída.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys
import tempfile
import shutil

REPO = pathlib.Path(__file__).resolve().parents[1]
FW = REPO / "framework" / "galpao_fw"
TEMPLATE = REPO / "docs" / "validacao_g15" / "galpao-sjb-valores-referencia.json.template"

def main():
    ap = argparse.ArgumentParser(description="Gera sidecar G19 a partir de spec ready")
    ap.add_argument("--spec", required=True, help="caminho do project-spec.json (deve estar ready)")
    ap.add_argument("--out", required=True, help="caminho de saída do sidecar JSON")
    ap.add_argument("--fonte", default="", help="fonte do memorial (ex: 'Memorial Galpao SJB - Eng Fulano CREA 123456 ART ... pg 4')")
    args = ap.parse_args()
    spec_path = pathlib.Path(args.spec)
    out_path = pathlib.Path(args.out)
    if not spec_path.is_file():
        print(f"spec não encontrado: {spec_path}", file=sys.stderr)
        sys.exit(2)
    if not TEMPLATE.is_file():
        print(f"template não encontrado: {TEMPLATE}", file=sys.stderr)
        sys.exit(2)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    sys.path.insert(0, str(FW))
    import project_loop, builtin_adapters
    try:
        builtin_adapters.register_builtin_adapters()
    except Exception:
        pass
    rep = project_loop.preflight_project(spec, options={"require_source_refs": True})
    if rep["status"] != "ready":
        print(f"spec não está ready: status={rep['status']} errors={rep['preflight']['errors'][:2]}", file=sys.stderr)
        print("Dica: rode python tools/validar_9_campos.py --spec " + str(spec_path), file=sys.stderr)
        sys.exit(3)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gerar_sidecar_"))
    try:
        manifest = project_loop.run_project(spec, str(tmp), options={"generate_3d": False, "generate_2d": False})
        dis = json.loads((tmp / "reports" / "disciplinas.json").read_text(encoding="utf-8"))
        aco_raw = dis.get("aco", {}).get("native", {}).get("raw", {}) if isinstance(dis.get("aco"), dict) else {}
        # extrair
        peso = aco_raw.get("romaneio_peso_primario_kg")
        esf_col = aco_raw.get("esf_coluna", {}) if isinstance(aco_raw.get("esf_coluna"), dict) else {}
        mcol = esf_col.get("M_kNm")
        perfil_col = aco_raw.get("perfil_colunas")
        perfil_raf = aco_raw.get("perfil_raf")
        if isinstance(perfil_col, list):
            perfil_col_str = "/".join(str(x) for x in perfil_col)
        else:
            perfil_col_str = str(perfil_col) if perfil_col else ""
        # carregar template
        sidecar = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        # preencher
        sidecar["fonte"] = args.fonte or sidecar.get("fonte", "").replace("XYZ", spec_path.stem).replace("Fulano", "PREENCHER CREA/ART")
        sidecar["proveniencia"] = f"Gerado automaticamente de {spec_path} via tools/gerar_sidecar.py em 1 comando; substituir valores pelos do memorial real quando validar contra concreto"
        geo = spec.get("turnkey", {}).get("geometria", {}) if isinstance(spec.get("turnkey"), dict) else {}
        sidecar["geometria"] = {
            "comprimento": geo.get("comprimento"),
            "vao": geo.get("vao"),
            "pe_direito": geo.get("pe_direito"),
            "bay": spec.get("structure", {}).get("geometria", {}).get("bay") if isinstance(spec.get("structure"), dict) else None,
        }
        vals = sidecar.setdefault("valores_referencia", {})
        vals["Mcol_kNm"] = mcol
        vals["peso_aco_primario_kg"] = peso
        vals["peso_aco_t"] = round(peso/1000, 3) if isinstance(peso, (int, float)) else None
        vals["perfis"] = {"coluna": perfil_col_str, "viga": str(perfil_raf) if perfil_raf else None}
        vals["observacoes"] = f"Gerado de {spec_path.name} run status={manifest.get('status')} - substituir pelos valores do memorial real (tolerancias G19: peso 10% M 15% V 5%)"
        # limpar marcadores de exemplo
        sidecar.pop("_comentario", None)
        # escrever
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"sidecar gerado: {out_path} ({out_path.stat().st_size} bytes)")
        print(f"  peso_aco_primario_kg={peso} Mcol={mcol} perfis={perfil_col_str}/{perfil_raf}")
        print(f"  próximo: edite {out_path} para colocar fonte CREA/ART/pagina e valores do memorial real, e anexe o PDF em docs/validacao_g15/galpao-sjb-memorial.pdf")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
