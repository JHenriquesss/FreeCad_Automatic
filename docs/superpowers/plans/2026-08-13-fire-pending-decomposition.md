# Fire Pending Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose the pending NBR 12693/NBR 13434 fire-protection item into two source-scoped, auditable research candidates.

**Architecture:** Extend the existing static decomposition in `tools/loops/discovery.py` with two explicit fire topics and canonical local paths. Extend the existing prompt dispatcher in `tools/loops/__main__.py`; reuse the source-scope and local-PDF quality gates without changing their behavior.

**Tech Stack:** Python 3.12 standard library, pytest, existing NotebookLM CLI adapter.

## Global Constraints

- Use only the explicit item from `fontes/fontes-faltantes.md:P1` as the decomposition trigger.
- Do not presume an edition for NBR 12693 or NBR 13434.
- Never broaden an atomic candidate to another source or to the whole notebook.
- Do not change engineering production code in this phase.
- Follow red-green TDD for discovery and prompt behavior.

---

### Task 1: Lock the discovery contract with failing tests

**Files:**
- Modify: `tools/loops/tests/test_discovery.py`
- Modify: `tools/loops/tests/test_cli.py`

**Interfaces:**
- Consumes: existing `discover_candidates`, `TaskCandidate`, `_research_question`, and `_research_retry_question`.
- Produces: executable expectations for two atomic candidates and their prompt topics.

- [x] **Step 1: Write the failing discovery test**

Add a temporary-project test with the exact P1 sentence and assert that discovery
returns one candidate with origin suffix `:nbr12693` and one with suffix
`:nbr13434`. Assert the following values:

```python
assert extinguishers.topic == "extintores"
assert extinguishers.discipline == "seguranca"
assert extinguishers.source_paths == (
    "09_INCENDIO/INCENDIO__NBR__NBR-12693__sistemas-extintores.pdf",
)
assert signage.topic == "sinalizacao_incendio"
assert signage.discipline == "seguranca"
assert signage.source_paths == (
    "09_INCENDIO/INCENDIO__NBR__NBR-13434__sinalizacao-seguranca.pdf",
)
assert any(item.title.startswith("Proteção contra incêndio:") for item in candidates)
```

Also assert that running discovery twice yields identical `(id, origin, source_paths)` tuples.

- [x] **Step 2: Run only the new discovery test and verify RED**

Run:

```text
python -m pytest -q tools/loops/tests/test_discovery.py -k fire_pending
```

Expected: failure because the current discovery returns only the broad candidate.

- [x] **Step 3: Write the failing prompt tests**

Create one `TaskCandidate` per topic and assert the normal and retry prompts
contain the relevant norm number, relevant subject, `section/table` wording,
the exact authorized source ID, and no claim of a year. Assert that the two
normal prompts differ and that both retry prompts are non-`None`.

- [x] **Step 4: Run only the new prompt tests and verify RED**

Run:

```text
python -m pytest -q tools/loops/tests/test_cli.py -k fire_prompt
```

Expected: failure because both topics currently use the generic prompt and the
generic retry returns `None`.

### Task 2: Implement atomic fire discovery and prompts

**Files:**
- Modify: `tools/loops/discovery.py`
- Modify: `tools/loops/__main__.py`

**Interfaces:**
- Consumes: the failing tests from Task 1 and the existing `TaskCandidate` constructor.
- Produces: `topic="extintores"`, `topic="sinalizacao_incendio"`, stable source paths, and auditable prompts.

- [x] **Step 1: Add canonical source constants**

Add these immutable tuples next to the other fire source constants:

```python
_EXTINTORES_NBR12693_SOURCES = (
    "09_INCENDIO/INCENDIO__NBR__NBR-12693__sistemas-extintores.pdf",
)
_SINALIZACAO_NBR13434_SOURCES = (
    "09_INCENDIO/INCENDIO__NBR__NBR-13434__sinalizacao-seguranca.pdf",
)
```

- [x] **Step 2: Add the P1 decomposition branch**

Before the existing generic return in `_candidates_for_item`, match normalized
title terms `protecao contra incendio`, `12693`, `13434`, and the exact origin
prefix `fontes/fontes-faltantes.md:P1`. Return the two atomics followed by
`_candidate(title, origin, evidence_path, suggestions)`. Use origins
`f"{origin}:nbr12693"` and `f"{origin}:nbr13434"`, topics `extintores` and
`sinalizacao_incendio`, discipline `seguranca`, priorities `55` and `50`,
respectively, and the constants above.

- [x] **Step 3: Add topic-specific test selection**

In `_tests_for_candidate`, select the existing fire tests for both topics in
this order when present:

```python
preferred = (
    "framework/galpao_fw/tests/test_incendio_robustez.py",
    "framework/galpao_fw/tests/test_seguranca_incendio.py",
    "framework/galpao_fw/tests/test_incendio_bim.py",
)
```

Return only paths that exist in `available`, preserving deterministic order.

- [x] **Step 4: Add focused research and retry prompts**

In both prompt functions, add branches keyed by the two topics. The normal
prompts must require only verifiable requirements from the named norm, section
or table references, and the exact authorized source ID. The retry prompts
must request at most eight compact items, textual citations, and explicit
declaration when the source does not cover a requested point.

- [x] **Step 5: Run the focused tests and verify GREEN**

Run:

```text
python -m pytest -q tools/loops/tests/test_discovery.py -k fire_pending
python -m pytest -q tools/loops/tests/test_cli.py -k fire_prompt
```

Expected: all focused tests pass.

### Task 3: Verify the phase boundary and register the result

**Files:**
- Modify: `fontes/pendencias-atualizacao.md`
- Modify: `sessions/2026-08-13.md`

**Interfaces:**
- Consumes: the atomic candidates and prompts from Task 2.
- Produces: an operational note for the missing files and a session record.

- [x] **Step 1: Record the canonical pending paths**

Append a concise note beside the existing NBR 12693/NBR 13434 pendency stating
that the loop now requests the two exact paths, with edition confirmation still
pending. Do not mark either source as obtained.

- [x] **Step 2: Run the focused, adapter, and full loop test suites**

Run:

```text
python -m pytest -q tools/loops/tests/test_discovery.py tools/loops/tests/test_cli.py
python -m pytest -q tools/loops/tests/test_research_nlm.py
python -m pytest -q tools/loops/tests
```

Expected: zero failures in each command.

- [x] **Step 3: Revalidate NotebookLM credentials before the real dry-run**

Run:

```text
nlm login --check
```

If it reports invalid credentials, run `nlm login`, then repeat the check before
the dry-run. Do not run a query until authentication is valid.

- [x] **Step 4: Run one bounded real loop iteration**

Run the normal loop with one iteration and no retry of persistent blocked tasks:

```text
python -m tools.loops --max-iterations 1 --command-timeout 30
```

Expected: it selects an atomic fire candidate, records a manual source request
for the missing canonical PDF, and produces no `nlm-response-*.json` artifact
for that parked task.

- [x] **Step 5: Review the diff and commit the phase**

Run:

```text
git diff --check
git status --short
git diff -- tools/loops/discovery.py tools/loops/__main__.py tools/loops/tests/test_discovery.py tools/loops/tests/test_cli.py fontes/pendencias-atualizacao.md
```

Commit only the phase files:

```text
git add tools/loops/discovery.py tools/loops/__main__.py tools/loops/tests/test_discovery.py tools/loops/tests/test_cli.py docs/superpowers/specs/2026-08-13-fire-pending-decomposition-design.md docs/superpowers/plans/2026-08-13-fire-pending-decomposition.md
git commit -m "feat: decompose fire source pending work"
```

Do not stage `.loop-runtime`, `fontes` PDFs, unrelated user changes, or session
logs ignored by the repository.

## Self-review checklist

- The design requirement for two atomic candidates maps to Task 1 and Task 2.
- The no-edition-presumption requirement maps to the canonical neutral paths and prompt assertions.
- The no-query-before-source requirement is verified by the existing adapter tests plus Task 3 dry-run.
- The duplicate pending line is deliberately out of scope and remains unmodified.
- No production engineering module is included in the file list.

## Next phase seed

After the user supplies the two PDFs, re-catalog them, validate text extraction,
and run the two atomic research tasks independently; do not implement rules until
each response has auditable citations.

## Phase verification record

- Focused discovery/CLI tests: 3 passed.
- Discovery plus CLI suite: 51 passed.
- NotebookLM adapter suite: 24 passed.
- Full loop suite: 198 passed.
- `nlm login --check`: valid; 64 notebooks visible.
- Real bounded loop: `manual_source_required` for NBR 12693; no new NLM response artifact.
- Review: local diff review completed; independent reviewer timed out before returning findings.
