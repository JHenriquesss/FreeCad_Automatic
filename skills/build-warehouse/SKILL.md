---
name: build-warehouse
description: Use when Codex needs to plan, model, draft, or automate a steel warehouse/galpao workflow in FreeCAD, including selecting reusable CAD blocks, using steel profile references, creating project folders, preparing FreeCAD scripts, generating deliverables, or coordinating engineering inputs for industrial buildings.
---

# Build Warehouse

Use this skill to help build a steel warehouse workflow around FreeCAD and the
local CAD block library. Treat all geometry as drafting/automation input until
an engineer approves it.

## First Steps

1. Read `references/block-map.md` to locate available blocks and standards.
2. Read `references/project-inputs.md` before starting a real project.
3. Ask for missing engineering inputs instead of inventing dimensions.
4. Prefer parametric FreeCAD scripts for repeatable frames, purlins, roof
   sheets, and openings.
5. Save project-specific work under `projects/<project-slug>/`.

## Workflow

1. Create or inspect a project folder.
2. Capture the design brief: dimensions, spans, height, roof slope, load
   assumptions, materials, local code, openings, crane/industrial equipment,
   and deliverables.
3. Map reusable assets from `libraries/cad-blocks/steel-warehouse/`.
4. Use `libraries/standards/freecad-bim/profiles.csv` for profile discovery.
5. Create FreeCAD automation only after the required inputs are clear.
6. Export deliverables into `projects/<project-slug>/exports/`.
7. Document assumptions and pending engineering decisions in the project notes.

## Rules

- Do not present generated geometry as structurally verified.
- Do not select final member sizes without explicit engineer approval.
- Preserve source attribution when using downloaded CAD blocks.
- Prefer `.FCStd` for editable FreeCAD objects and `.step` for neutral import.
- Keep external downloads in `libraries/` with source/license notes.

## References

- `references/block-map.md`: available libraries and what each folder is for.
- `references/project-inputs.md`: minimum inputs for a warehouse project.
- `references/deliverables.md`: expected outputs and folder locations.
