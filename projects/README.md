# Projects Workspace

Each project lives in its own folder under `projects/`.

## Create A New Project

Copy the template folder and rename it with a short slug:

```powershell
Copy-Item -Recurse .\projects\_template .\projects\galpao-cliente-x
```

Then open the agent with this working directory:

```text
D:\dev\FreeCad_Automatic\projects\galpao-cliente-x
```

The first file an agent must read inside a project is:

```text
AGENT_SCOPE.md
```

## Isolation Rule

A project agent may read shared repo context but may write only in the current
project folder. Shared repo maintenance is a separate task and must be explicit.

## Shared Read-Only Context

- `../wiki/`
- `../skills/`
- `../libraries/`
- `../pesquisa/`

## Project Folder Contract

- `brief.md`: project identity, geometry, use, and constraints.
- `context/`: project-specific chat summary, decisions, and pending questions.
- `inputs/`: files received from the user/client.
- `work/`: editable model/script work in progress.
- `exports/`: FreeCAD, DXF, STEP, PDF, and takeoff outputs.
- `notes/`: assumptions and engineering notes.
