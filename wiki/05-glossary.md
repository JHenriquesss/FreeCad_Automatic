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

## Structural Calc (NBR)

- NBR 8800: steel structures (hot-rolled) design norm.
- NBR 6123: wind loads (S2, Vk, q, Cpe walls Tab.4 / roof Tab.5, Cpi dominant
  opening 6.2.5-c). Transverse frame = same incidence alpha=90 for walls+roof.
- NBR 14762: cold-formed steel design (purlins). MSE = Metodo da Secao Efetiva
  (effective section); Anexo F = free compression flange under suction (R factor).
- MAES / B1-B2: NBR 8800 Anexo D 2nd-order amplification (nt/lt split). B2 =
  global P-Delta (story); B1 = local P-delta (member).
- Deslocabilidade: sway classification by B2 (<=1.1 pequena, <=1.4 media, >1.4
  grande). Media -> 80% reduced stiffness (4.9.7.1.2).
- Forca nocional: notional horizontal load = 0.3% of story gravity (imperfection).
- Distortional buckling / Mdist: cold-formed flange-lip mode; elastic Mdist from
  FSM. FSM = Finite Strip Method; CUFSM / pycufsm = the tool.
- Ue: perfil U enrijecido (lipped channel), the cold-formed purlin section.
- Taxa de utilizacao: demand/capacity ratio; <=1.0 passes the norm.
- AISC DG1: base-plate-under-moment design guide (eccentricity method).
- ART: engineer's signed responsibility (Anotacao de Responsabilidade Tecnica).

## Engineering Status Terms

- Placeholder: modeled geometry not yet engineered.
- Engineer-approved: decision/input explicitly validated by responsible engineer.
- Verified: calculation/detail checked by engineer; agents must not infer this.
