# Structural Fire Pending Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove one known fire-source duplicate and decompose NBR 15200, NBR 14432, and NBR 14323 into source-scoped research candidates.

**Architecture:** Keep the existing discovery pipeline and add narrow predicates in `_candidates_for_item`. The canonical `fontes/fontes-faltantes.md` item remains the source of truth for NBR 12693/NBR 13434; only its exact mirror entry is ignored. The structural-fire item emits three atomics plus the original broad trace candidate, while prompt dispatch remains topic-based.

**Tech Stack:** Python 3.12 standard library, pytest, existing NotebookLM CLI adapter and local PDF quality gate.

## Global Constraints

- Do not presume editions for NBR 15200, NBR 14432, or NBR 14323.
- Use only the three explicit canonical paths under `09_INCENDIO`.
- Never broaden a candidate to the complete fire notebook or use another norm as a substitute.
- Do not modify engineering production modules in this phase.
- Preserve unrelated dirty and untracked user files.
- Follow red-green TDD for discovery and prompt behavior.

---

### Task 1: Establish failing contracts

**Files:**
- Modify: `tools/loops/tests/test_discovery.py`
- Modify: `tools/loops/tests/test_cli.py`

**Interfaces:**
- Consumes: `discover_candidates`, `TaskCandidate`, `_research_question`, and `_research_retry_question`.
- Produces: regression contracts for the mirror and the three structural-fire atomics.

- [x] **Step 1: Add the mirror regression test**

Create a temporary `fontes/fontes-faltantes.md` containing the canonical P1
protection item and a temporary `fontes/pendencias-atualizacao.md` containing
the updated mirror line under the exact fire heading. Assert that the canonical
source produces `:nbr12693` and `:nbr13434`, and that no candidate whose title
mentions both norms has the `pendencias-atualizacao.md` origin.

- [x] **Step 2: Run the mirror test and verify RED**

Run:

```text
python -m pytest -q tools/loops/tests/test_discovery.py -k fire_mirror
```

Expected: failure because the mirror currently produces a generic candidate.

- [x] **Step 3: Add the three-norm decomposition test**

Create a temporary pending document with the exact structural-fire sentence and
the existing fire test files. Find candidates by origin suffix and assert:

```python
expected = {
    "nbr15200": (
        "fogo_concreto",
        "09_INCENDIO/INCENDIO__NBR__NBR-15200__estruturas-concreto-incendio.pdf",
    ),
    "nbr14432": (
        "resistencia_fogo",
        "09_INCENDIO/INCENDIO__NBR__NBR-14432__exigencias-resistencia-fogo.pdf",
    ),
    "nbr14323": (
        "fogo_aco",
        "09_INCENDIO/INCENDIO__NBR__NBR-14323__estruturas-aco-incendio.pdf",
    ),
}
```

Assert each atomic discipline is `seguranca`, each source path is a singleton,
the broad title remains present with empty `source_paths`, and two discovery
runs produce identical IDs and origins.

- [x] **Step 4: Run the decomposition test and verify RED**

Run:

```text
python -m pytest -q tools/loops/tests/test_discovery.py -k structural_fire
```

Expected: failure because the current implementation returns one generic item.

- [x] **Step 5: Add the prompt contract test**

Parameterize candidates for all three topics and assert each normal prompt
contains its norm number, subject, `seção/tabela`, and exact source ID; assert
the retry is not `None`, contains the norm number, `citações textuais`, and the
source ID; assert no prompt invents a year.

- [x] **Step 6: Run the prompt test and verify RED**

Run:

```text
python -m pytest -q tools/loops/tests/test_cli.py -k structural_fire_prompt
```

Expected: failure because the topics currently use the generic prompt and no
retry prompt.

### Task 2: Implement the narrow discovery and prompt behavior

**Files:**
- Modify: `tools/loops/discovery.py`
- Modify: `tools/loops/__main__.py`

**Interfaces:**
- Consumes: the failing contracts from Task 1.
- Produces: stable atomics `fogo_concreto`, `resistencia_fogo`, and `fogo_aco`.

- [x] **Step 1: Add source constants**

Add immutable tuples for the three exact canonical paths under the existing fire
constants. Do not add year suffixes.

- [x] **Step 2: Add the narrow mirror exclusion**

Before the generic return in `_candidates_for_item`, return an empty list only
when the normalized title starts with the NBR 12693/NBR 13434 mirror wording and
the origin starts with
`fontes/pendencias-atualizacao.md:Incêndio, geotecnia e segurança do trabalho`.
Leave all other items from that file untouched.

- [x] **Step 3: Add the structural-fire decomposition branch**

Match normalized title terms `15200`, `14432`, `14323`, and `estruturas em
incendio`, with origin starting with the same fire heading. Return atomics with
origins `:nbr15200`, `:nbr14432`, and `:nbr14323`, topics and paths from the
contract, priorities `48`, `46`, and `44`, discipline `seguranca`, followed by
the broad original candidate.

- [x] **Step 4: Add topic-specific test selection**

For `fogo_concreto`, prefer existing
`framework/galpao_fw/tests/test_fogo_nbr15200.py`, then
`test_incendio_robustez.py`, `test_seguranca_incendio.py`, and
`test_incendio_bim.py`. For `resistencia_fogo` and `fogo_aco`, use the latter
three in the same order. Return only existing paths.

- [x] **Step 5: Add focused normal and retry prompts**

Add one branch per topic. The normal prompt must name only its NBR, require
verifiable requirements and section/table references, and use the authorized
source ID. The retry must cap the answer at eight items, require textual
citations, forbid invented guards/rules, and request a declaration when the
source has no coverage.

- [x] **Step 6: Run focused tests and verify GREEN**

Run:

```text
python -m pytest -q tools/loops/tests/test_discovery.py -k 'fire_mirror or structural_fire'
python -m pytest -q tools/loops/tests/test_cli.py -k structural_fire_prompt
```

Expected: all new tests pass.

### Task 3: Update operational notes and verify the real loop

**Files:**
- Modify: `fontes/pendencias-atualizacao.md`
- Modify: `sessions/2026-08-13.md`

**Interfaces:**
- Consumes: the atomics and prompts from Task 2.
- Produces: auditable pending paths and a session record.

- [x] **Step 1: Record the three canonical paths**

Append the exact paths to the structural-fire pending line and state that the
editions remain to be confirmed. Do not mark any source as obtained.

- [x] **Step 2: Run all automated verification**

Run:

```text
python -m pytest -q tools/loops/tests/test_discovery.py tools/loops/tests/test_cli.py
python -m pytest -q tools/loops/tests/test_research_nlm.py
python -m pytest -q tools/loops/tests
git diff --check
```

Expected: zero test failures and no whitespace errors.

- [x] **Step 3: Revalidate NotebookLM**

Run `nlm login --check`; if invalid, run `nlm login` and repeat the check.

- [x] **Step 4: Run one bounded real iteration**

Run:

```text
python -m tools.loops --max-iterations 1 --command-timeout 30
```

Expected: the first unblocked structural-fire atomic is selected, its missing
source is recorded in `.loop-runtime/manual-source-requests.md`, and no new
`nlm-response-*.json` is created for the parked task.

- [x] **Step 5: Review and commit only phase files**

Review the staged diff, leave runtime/source/session changes unstaged, then
commit the code, tests, and two phase documents with:

```text
git commit -m "feat: decompose structural fire source pending work"
```

## Phase verification record

- Focused discovery and prompt tests: 5 passed.
- Discovery plus CLI regression suite: 56 passed.
- NotebookLM adapter suite: 24 passed.
- Full loop suite: 203 passed.
- `py_compile` and `git diff --check`: passed.
- `nlm login --check`: valid; 64 notebooks visible.
- Real bounded loop: `manual_source_required` for NBR 15200; no new NLM response artifact.
- Review: local diff review completed; independent reviewer timed out before returning findings.

## Next phase seed

When the user supplies any structural-fire PDF, catalog it under the exact path,
run the local text-quality gate, then research only that atomic task and require
auditable NotebookLM citations before implementing engineering rules.
