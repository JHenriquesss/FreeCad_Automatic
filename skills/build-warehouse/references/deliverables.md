# Deliverables

Use this folder layout per project:

```text
projects/<project-slug>/
|-- AGENT_SCOPE.md
|-- brief.md
|-- context/
|   |-- chat.md
|   |-- decisions.md
|   `-- pending.md
|-- inputs/
|-- work/
|-- exports/
|   |-- freecad/
|   |-- dxf/
|   |-- step/
|   |-- pdf/
|   `-- takeoff/
`-- notes/
```

## Minimum Outputs

- `work/<project-slug>.FCStd`
- `exports/step/<project-slug>.step`
- `exports/dxf/<project-slug>-plans.dxf`
- `exports/pdf/<project-slug>-drawing-set.pdf`
- `exports/takeoff/<project-slug>-material-takeoff.csv`
- `notes/assumptions.md`
- `context/chat.md`
- `context/decisions.md`
- `context/pending.md`

## Quality Checks

- Confirm the agent obeyed `AGENT_SCOPE.md`.
- Confirm units.
- Confirm model origin and datum.
- Confirm layers/object names.
- Confirm source attribution for reused blocks.
- Confirm unresolved engineering assumptions are listed.
