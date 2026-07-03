# Deliverables

Use this folder layout per project:

```text
projects/<project-slug>/
├─ brief.md
├─ inputs/
├─ work/
├─ exports/
│  ├─ freecad/
│  ├─ dxf/
│  ├─ step/
│  ├─ pdf/
│  └─ takeoff/
└─ notes/
```

## Minimum Outputs

- `work/<project-slug>.FCStd`
- `exports/step/<project-slug>.step`
- `exports/dxf/<project-slug>-plans.dxf`
- `exports/pdf/<project-slug>-drawing-set.pdf`
- `exports/takeoff/<project-slug>-material-takeoff.csv`
- `notes/assumptions.md`

## Quality Checks

- Confirm units.
- Confirm model origin and datum.
- Confirm layers/object names.
- Confirm source attribution for reused blocks.
- Confirm unresolved engineering assumptions are listed.
