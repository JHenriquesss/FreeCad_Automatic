# Connections, Bases, And Durability

Use this reference when a steel warehouse model touches connection placeholders,
base interfaces, durability notes, or fabrication/mounting deliverables.

## Connection Scope

Classify every connection before detailing:

- Member force type: axial, shear, moment, combined force, or bracing force.
- Rigidity intent: pinned/flexible, semi-rigid, or rigid.
- Fabrication split: shop welded, field bolted, or mixed.
- Geometry: gusset plate, end plate, splice plate, web angle, seated support,
  truss node, base plate, or crane runway detail.
- Verification status: placeholder, engineer-approved concept, or calculated.

Do not generate final bolt counts, weld sizes, plate thicknesses, edge
distances, hole dimensions, or anchor details without engineer input.

## Typical Warehouse Connection Placeholders

- Column base: pinned or fixed base marker, base plate outline, anchors, grout,
  and pedestal/footing reference.
- Rafter-to-column or beam-to-column: moment joint marker or pinned support
  marker depending on typology.
- Truss nodes: gusset plate marker, member centerline convergence, and member
  orientation notes.
- Roof/wall bracing: cleat or gusset marker at frame intersections.
- Purlin/girt supports: clip/cleat marker and lap/continuity notes.
- Crane runway: console, runway beam, lateral restraint, and end stop markers.

## Base And Aco-Concreto Interface Checklist

Before modeling or documenting bases, confirm:

- Base behavior: pinned, fixed, or preliminary.
- Column profile and orientation.
- Concrete pedestal/footing geometry and strength assumption.
- Anchor/chumbador type, diameter, embedment concept, and projection.
- Shear transfer concept: anchor shear, friction, shear key, or other detail.
- Grout thickness and leveling method.
- Edge distances and constructability constraints.
- Corrosion protection at base, drainage, and access for inspection.

### Base plate constructability detail

Model the base as it is built, not idealised:

- Oversized anchor holes: base-plate holes for anchor rods are made noticeably
  larger than the rod to absorb foundation setting-out error. Model the hole
  bigger than the rod (ask; the engineer/AISC/NBR gives the value).
- Special washers (plate washers): because holes are oversized, thick square or
  circular plate washers with a standard hole are placed over each rod and
  welded to the base plate after levelling. Model them as thin plates named
  `WASHER_...`.
- Shear key (barra de cisalhamento): when horizontal forces are too large to
  pass through the anchors, weld a profile or plate under the base plate,
  embedded in the concrete. Model it as an optional `SHEARKEY_...` solid below
  the base plate, and flag it as engineer-decided.
- Grout gap: base plate sits above the concrete on grout (see
  `constructability-detailing.md` section 5).

## Durability Checklist

Before choosing paint or galvanizing notes, confirm:

- Exposure environment: interior dry, industrial, coastal, humid, chemical, or
  mixed.
- Whether the structure is fully enclosed, partially open, or exposed.
- Drainage details that avoid water retention at bases, laps, gutters, and
  horizontal surfaces.
- Surface preparation, coating system, dry-film thickness, and inspection
  criteria supplied by the engineer or specification.
- Galvanizing compatibility with member size, holes, venting, distortion risk,
  and field repair.
- Maintenance access and inspection frequency.

### Durability geometry rules (model actively)

- Drain holes: closed/tubular sections need drain holes for condensed water.
- Vent holes: hot-dip galvanised closed sections need vent/flow holes to let
  molten zinc and gases move; sealed pockets can EXPLODE in the zinc bath. Model
  vent + drain holes diametrically opposed near each end.
- Water traps: never model a "U" open upward exposed to weather, nor connection
  pockets that pond; add drain cuts where water could collect.
- Maintenance access: keep minimum clearances between parallel members and
  between members and walls so painting equipment and inspection tools fit
  (ask; suggested range 50-300 mm depending on depth). Flag clashes below the
  chosen clearance.

## Fabrication And Mounting Notes

A warehouse project should separate:

- Design drawings: geometry, axes, profiles, loads/assumptions, and design
  intent.
- Fabrication drawings: piece marks, holes, welds, plates, cuts, bills of
  material, and shop standards.
- Mounting drawings: erection sequence, grid, levels, temporary bracing,
  lifting points, field bolts, and tolerances.

The agent may draft these folders and placeholders, but the engineer must
approve fabrication and mounting data before release.

## FreeCAD Modeling Guidance

- Represent connection placeholders with simple parametric solids on named
  layers/groups, e.g. `CONN_BASE_PLACEHOLDER`, `CONN_GUSSET_PENDING`.
- Keep placeholders visually distinct from verified parts.
- Use object properties or project notes to record `status=pending_engineer`.
- Link placeholders to axes and member names so they can be replaced by final
  details later.
