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
profiles/gerdau/autocad/
profiles/gerdau/autocad/dwg/
roof/steel-sheets/
openings/glass-skin/
```

## Gerdau Profile Blocks

Use these when the project asks for Gerdau steel profiles or Brazilian supplier
references:

```text
libraries/cad-blocks/steel-warehouse/profiles/gerdau/MANIFEST.md
libraries/cad-blocks/steel-warehouse/profiles/gerdau/autocad/dwg/
```

Available DWG groups:

```text
Cantoneira
Perfil I de abas inclinadas - Industria
Perfil U
Perfis W/HP 150, 200, 250, 310
Perfis W 360, 410, 530, 610
```

FreeCAD usually needs a DWG importer/converter configured. If DWG import fails,
convert the Gerdau DWG to DXF before importing.

## Standards And Profile References

```text
libraries/standards/freecad-bim/profiles.csv
libraries/standards/freecad-bim/ArchProfile.py
libraries/standards/freecad-draft-patterns/steel.svg
libraries/standards/freecad-draft-patterns/general_steel.svg
libraries/standards/gerdau/perfis-estruturais/perfis-estruturais-gerdau-informacoes-tecnicas.pdf
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
