# Decisions

## 2026-07-03 - Use freecad-addon-robust-mcp-server

Decision:
- Use `spkane/freecad-addon-robust-mcp-server` as vendored MCP server/bridge.

Why:
- Mature repo, supports Python execution, document access, XML-RPC/socket modes,
  and broad MCP tool surface.

Alternatives rejected:
- Smaller or less maintained FreeCAD MCP repos.
- Embedded FreeCAD mode on Windows.

## 2026-07-03 - Portable Wrapper Repo

Decision:
- Keep a wrapper repo with installer, vendored upstream, docs, libraries, skills,
  and project templates.

Why:
- User wants GitHub ZIP -> quick install on any PC.

Alternatives rejected:
- Manual per-client setup.
- Relying only on global machine state.

## 2026-07-03 - Global MCP Registration

Decision:
- Install global `freecad-mcp.exe` and register `freecad` MCP for Codex,
  Claude Desktop, Claude Code, OpenCode, and Antigravity.

Why:
- Same FreeCAD tool should be available across user agent surfaces.

Alternatives rejected:
- Project-only MCP config.
- Client-specific one-off commands.

## 2026-07-03 - Keep Research Raw Files Out Of Git

Decision:
- Ignore `pesquisa/` and convert findings into concise skill references.

Why:
- Raw PDFs can be large, licensed, or from unclear sources; skills should carry
  operational knowledge, not copyrighted corpora.

Alternatives rejected:
- Commit all PDFs.
- Require engineer to manually summarize everything before skill evolution.

## 2026-07-03 - Gerdau Assets Stored As Source ZIP + Working DWG

Decision:
- Preserve official Gerdau ZIPs and extract DWG working files.

Why:
- Source provenance remains intact; agents can find CAD blocks quickly.

Alternatives rejected:
- Re-download on every machine.
- Store only extracted files without source package.

## 2026-07-04 - FreeCAD Bridge Installed In Multiple Mod Layouts

Decision:
- Copy RobustMCPBridge to classic direct and namespace paths in base and versioned
  FreeCAD user profiles.

Why:
- FreeCAD 1.1 uses `v1-1`; upstream metadata references namespace layout; classic
  workbench discovery still expects direct addon folder with `Init.py`/`InitGui.py`.

Alternatives rejected:
- Only `%APPDATA%\FreeCAD\Mod\RobustMCPBridge`.
- Only `%APPDATA%\FreeCAD\v1-1\Mod\freecad\RobustMCPBridge`.

## 2026-07-04 - Patch Vendored Bridge For FreeCAD 1.1 Discovery

Decision:
- Add local `Init.py`/`InitGui.py` wrappers and make `GuiUp` access defensive.

Why:
- FreeCAD 1.1 did not load lowercase `init_gui.py` through classic discovery.
- `freecadcmd` lacks `FreeCAD.GuiUp`, causing startup exceptions before patch.

Alternatives rejected:
- Wait for upstream release.
- Tell user to start bridge manually every time.

## 2026-07-04 - Isolate Each Galpao Project Folder

Decision:
- Each project under `projects/<project-slug>/` gets `AGENT_SCOPE.md` and
  project-local `context/`.

Why:
- Agents need read access to shared wiki, skills, libraries, and research while
  being prevented from modifying sibling projects or shared configuration.

Alternatives rejected:
- Open all agents at repo root for project work.
- Duplicate shared libraries and research inside every project.

## 2026-07-04 - Default Auto-Start On + One-Click install.bat

Decision:
- Patch vendored `preferences.py` to `DEFAULT_AUTO_START = True`.
- Add `install.bat` double-click wrapper that runs `install.ps1` with
  `-ExecutionPolicy Bypass -InstallUvIfMissing`.

Why:
- Goal is "install FreeCAD, run installer, launch FreeCAD, MCP works" on any PC.
- Upstream default `False` required manually selecting the workbench and clicking
  Start each launch; a fresh profile has no stored `AutoStart` param, so the
  default governs first-run behavior.
- `install.bat` removes PowerShell command typing and auto-installs `uv`.

Alternatives rejected:
- Have the installer inject the `AutoStart` param into FreeCAD `user.cfg`
  (fragile; file may not exist before first FreeCAD launch, per-profile).
- Leave default `False` and document a manual enable step (breaks one-click goal).

## 2026-07-05 - Skill Computes, Engineer Reviews

Decision:
- The build-warehouse skill RUNS the calc toolkit (Gates 5-8) and emits PT
  memoriais; the engineer reviews/approves. Was: skill does not calculate.

Why:
- User is an engineer advancing work so a senior only reviews/corrects. The
  toolkit is validated per module; the skill orchestrates and documents.

Alternatives rejected:
- Keep the skill drafting-only with a manual engineer handoff.

## 2026-07-05 - Wrap Validated CUFSM (pycufsm), Pin numpy<2

Decision:
- Compute distortional Mdist by wrapping the validated `pycufsm` (CUFSM port) in
  `distorcional_fsm`, not by hand-coding finite-strip stiffness matrices. Pin
  numpy to 1.26.4.

Why:
- NBR 14762 delegates Mdist to elastic stability analysis (no closed form). Hand-
  coded FSM matrices from memory violate zero-method-error; pycufsm is validated.
- pycufsm 0.2.0 breaks on numpy 2.x (two incompatibilities, one compiled). All
  other modules are numpy-agnostic and still pass on 1.26.

Alternatives rejected:
- Hand-code the FSM eigensolver. Implement Lau-Hancock analytical (no source in
  repo). Keep Mdist as manual external input forever.

## 2026-07-05 - Fixed Base For The 20x10 Galpao

Decision:
- Adopt engastada (fixed) column bases for `projects/galpao`.

Why:
- Pinned bases fail ELS/ELU (drift 179 mm; rafter interaction 1.75). Fixed bases
  pass with the original HEA200/HEA180 (drift 30.8 mm; 0.67/0.87). Fixing the
  base is the lightest solution (trade steel for foundation moment ~60 kN.m).

Alternatives rejected:
- Pinned + heavier sections. Pinned + knee haunch (mao-francesa).

## 2026-07-05 - gamma_g,fav = 0.90 For The Purlin (Conservative)

Decision:
- `tercas_nbr14762` default favorable permanent coefficient = 0.90.

Why:
- NBR 8800 Table 1 note (a) literally gives 1.00 favorable; the RT prefers the
  conservative 0.90 (NBR 8681) for uplift (less stabilizing gravity -> more
  demand -> safer). Configurable via `cfg["gamma"]`. Note: the PORTICO keeps
  1.00 per NBR 8800 (the governing steel norm), verified against the rendered
  Table 1.

Alternatives rejected:
- Force 0.90 everywhere. Force 1.00 on the purlin against the RT's call.

## 2026-07-05 - Canonical Orchestrator + Parametric Geometry

Decision:
- One `rodar_galpao.py` orchestrator drives the chain from a params dict;
  geometry is parametric via `configurar()` in every geometry-bearing module.

Why:
- Dry-run exposed the toolkit was hardcoded to 20x10 and had no single runner
  (skill called modules ad hoc). Parametrization keeps validated formulas intact
  (defaults unchanged) while letting any dimension run.

Alternatives rejected:
- Keep ad-hoc module calls. Constrain the skill to ~20x10 only.

## 2026-07-05 - Flange-Brace Spacing By Inverting The Member Check

Decision:
- Derive the mao-francesa (flange-brace) count/spacing from the calc, not a
  geometric heuristic: `calc/mao_francesa.py` bisects the NBR 8800 5.5.1.2
  interaction for the max unbraced length Lb with interaction <= 1.0, gives
  braces/frame, and that Lb feeds the viga check. `build_galpao.MF_STRIDE`
  places braces per that stride.

Why:
- The brace spacing WAS a +/-150 mm guess and the check's viga `Lb=1.67` was
  hardcoded and disconnected from where braces were modelled — two unlinked
  assumptions. Inverting the same interaction the check uses closes the loop and
  is the governing limit (FLT alone ignores the axial term = unsafe).
- Ref 20x10: Lb_max 4.64 m, stride 2 -> 2 braces/frame (was 4), Lb 3.35 m, viga
  interaction 0.93 (honest; was 0.87 under the assumed 1.67).

Alternatives rejected:
- Invert FLT-only (ignores flexo-compression). Keep bracing every purlin.
  Keep the hardcoded Lb.

## 2026-07-05 - Secondary Members: Catalog J/Cw For The Channel FLT

Decision:
- `secundarios_nbr8800` checks the wall girt (U) and eave strut/ridge (I). For
  the girt's strong-axis FLT (channel), take J and Cw from the CATALOG (flagged
  A CONFIRMAR) and apply the same NBR 8800 Anexo G formula the section check
  uses — do NOT derive a channel Cw formula from memory. Missing J/Cw ->
  INCONCLUSIVO, never invented.

Why:
- Zero-method-error: the Anexo G method is verified; a from-memory channel Cw
  would be an unverifiable method/data error. Making J/Cw a catalog input keeps
  the method exact and the data auditable (same treatment as purlin Ief/Wef,y).
- Girt Lp for a channel is tiny (~0.87 m); punting FLT to "compact+braced only"
  made the check useless — full Anexo G with catalog Cw is the honest path.
- Ref 20x10: UPE100 girt needs 2 wall sag-rod lines (0.99); HEA160 strut 0.11 OK.

Alternatives rejected:
- Derive channel Cw from a memorized thin-wall formula. Cap Mrd,x to the plastic
  value only when Lb<=Lp (unusable). Leave secondary members unchecked.

## 2026-07-04 - Defer FreeCAD GUI Bridge Startup To InitGui

Decision:
- `RobustMCPBridge/Init.py` must only prepare import path/logging; `InitGui.py`
  owns GUI bridge startup.

Why:
- FreeCAD can run `Init.py` before `FreeCAD.GuiUp` is true. Starting there makes
  the bridge use headless queue processing inside the GUI process, causing
  XML-RPC `execute` calls to hang.

Alternatives rejected:
- Keep duplicate auto-start in both `Init.py` and `InitGui.py`.
- Rely on chat/client restart to clear bridge state.
