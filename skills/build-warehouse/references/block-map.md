# Block Map

## Local CAD Blocks

Base path:

```text
libraries/cad-blocks/steel-warehouse/
```

Use these folders:

```text
profiles/hea/
profiles/heb/
roof/steel-sheets/
openings/glass-skin/
```

## Standards And Profile References

```text
libraries/standards/freecad-bim/profiles.csv
libraries/standards/freecad-bim/ArchProfile.py
libraries/standards/freecad-draft-patterns/steel.svg
libraries/standards/freecad-draft-patterns/general_steel.svg
```

`profiles.csv` includes profile classes such as circular tube, rectangular,
rectangular hollow, H/I profile, and U profile. Use it to discover available
profile families and dimensions before creating parametric objects.

## Missing Library Areas

These folders should be filled later with engineer-approved blocks:

```text
libraries/cad-blocks/steel-warehouse/columns/
libraries/cad-blocks/steel-warehouse/beams/
libraries/cad-blocks/steel-warehouse/trusses/
libraries/cad-blocks/steel-warehouse/purlins/
libraries/cad-blocks/steel-warehouse/bracing/
libraries/cad-blocks/steel-warehouse/connections/
libraries/cad-blocks/steel-warehouse/base-plates/
libraries/cad-blocks/steel-warehouse/anchors/
libraries/cad-blocks/steel-warehouse/gutters/
libraries/cad-blocks/steel-warehouse/doors/
```

Do not fabricate final connection details from generic blocks. Treat downloaded
files as starting references until the engineer supplies office standards.
