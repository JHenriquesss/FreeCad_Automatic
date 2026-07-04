# Agent Scope

This folder is an isolated project workspace. An agent opened here may use the
shared repository knowledge, but must only write inside this project folder
unless the user explicitly asks for repository-level maintenance.

## Writable Area

Write only inside the current project folder:

```text
projects/<project-slug>/
```

## Read-Only Shared Context

The agent may read:

```text
../../wiki/
../../skills/
../../libraries/
../../pesquisa/
../../README.md
```

## Forbidden Writes

Do not modify:

```text
../../install.ps1
../../README.md
../../UPSTREAM.md
../../wiki/
../../skills/
../../libraries/
../../pesquisa/
../*/            # any sibling project folder
```

Exception: if the user explicitly switches to repository maintenance, stop
project work and confirm the new scope before editing shared files.

## Required Startup

1. Read this `AGENT_SCOPE.md`.
2. Read `../../wiki/00-index.md`.
3. Read `../../skills/build-warehouse/SKILL.md`.
4. Read `brief.md`.
5. Read `context/chat.md`, `context/decisions.md`, and `context/pending.md`.
6. Continue only within this project folder.

## Project Memory Rules

- Put project-specific chat summaries in `context/chat.md`.
- Put project decisions in `context/decisions.md`.
- Put unresolved questions in `context/pending.md`.
- Put engineering assumptions in `notes/assumptions.md`.
- Do not duplicate the shared wiki; link to shared files instead.
