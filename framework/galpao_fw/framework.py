# ============================================================================
# framework.py - PONTO DE ENTRADA do framework de galpao (isolamento/portabilidade)
# - VERSAO: carimbada em cada memorial (reprodutibilidade).
# - raiz_repo(): descobre a raiz do repo por __file__ (sem caminho absoluto).
# - novo_projeto(slug): cria uma pasta de projeto ISOLADA a partir do template,
#   sem copiar nada de outro projeto -> zero contaminacao.
# - reset_tudo(): zera o estado global de todos os modulos (sem vazamento).
# Roda em qualquer PC: caminhos relativos + estado limpo por run.
# ============================================================================
"""Entrada do framework de galpao: versao, raiz, scaffolder, reset global."""

from __future__ import annotations

import pathlib
import shutil

VERSAO = "0.1.0"


def raiz_repo():
    """Raiz do repo (framework/galpao_fw/ -> framework/ -> raiz)."""
    return pathlib.Path(__file__).resolve().parents[2]


def dir_projetos():
    return raiz_repo() / "projects"


def reset_tudo():
    """Zera o estado mutavel de todos os modulos com globais (evita vazamento)."""
    import galpao_portico as gp
    import vento_nbr6123 as vento
    gp.reset(); vento.reset()
    try:
        import estabilidade_b1b2 as est
        est.reset()
    except Exception:
        pass
    try:
        import build_galpao as bg
        bg.reset()
    except Exception:
        pass          # build_galpao so importa dentro do FreeCAD


def novo_projeto(slug, base=None):
    """Cria projects/<slug>/ a partir de projects/_template/ (ISOLADO). Nao copia
    nada de outro projeto. Retorna o Path do projeto. Erro se ja existir."""
    base = pathlib.Path(base) if base else dir_projetos()
    template = base / "_template"
    dest = base / slug
    if dest.exists():
        raise FileExistsError(f"projeto ja existe: {dest}")
    if template.exists():
        shutil.copytree(template, dest)
    else:                              # template minimo se nao houver
        for sub in ("inputs", "notes", "exports", "work"):
            (dest / sub).mkdir(parents=True, exist_ok=True)
    # carimbo de versao/reprodutibilidade
    (dest / "notes").mkdir(exist_ok=True)
    (dest / "notes" / "FRAMEWORK.txt").write_text(
        f"framework galpao_fw versao {VERSAO}\n"
        f"projeto criado por novo_projeto('{slug}')\n"
        "Dependencia: numpy < 2 (pycufsm). Ver framework/galpao_fw/REQUISITOS.txt\n",
        encoding="utf-8")
    return dest


def carimbo_versao():
    return f"framework galpao_fw v{VERSAO}"


if __name__ == "__main__":
    print(carimbo_versao())
    print("raiz:", raiz_repo())
    print("projetos:", dir_projetos())
