# Glossary

## FreeCAD / MCP

- `freecad-mcp`: external MCP server command installed by `uv tool`.
- `RobustMCPBridge`: FreeCAD workbench/addon running inside FreeCAD.
- XML-RPC port: `9875`, primary bridge connection used by clients.
- Socket port: `9876`, JSON-RPC bridge alternative.
- Embedded mode: direct import of FreeCAD into server process; not used on
  Windows.
- `v1-1`: FreeCAD 1.1 versioned user profile directory.
- Classic Mod layout: `Mod/RobustMCPBridge`.
- Namespace Mod layout: `Mod/freecad/RobustMCPBridge`.

## Repo

- Vendored upstream: local copy of upstream robust MCP project.
- Wrapper repo: this repo, owning installer/docs/skills/assets around upstream.
- LLM wiki: `wiki/`, compact project memory for future agents.
- Session log: `sessions/*.md`, ignored local work log.

## Steel Warehouse

- Galpao: steel warehouse/light industrial building.
- Portal frame: primary transverse rigid frame system.
- Tesoura/truss: triangulated roof structure.
- Purlin: roof secondary member.
- Girt: wall secondary member.
- Bracing: roof/wall stability system and load path.
- Gusset plate: connection plate for truss/bracing nodes.
- Base plate: steel plate at column-to-foundation interface.
- Chumbador/anchor: anchor rod connecting base plate to concrete.
- Tapamento/cladding: roof/wall enclosure system.
- Lanternim: roof monitor/ventilation/light opening.
- Gerdau W/HP: supplier profile family used in local CAD library.

## Engineering Status Terms

- Placeholder: modeled geometry not yet engineered.
- Engineer-approved: decision/input explicitly validated by responsible engineer.
- Verified: calculation/detail checked by engineer; agents must not infer this.
