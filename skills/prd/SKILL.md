---
name: "PRD Generator"
description: "Create a detailed PRD and decompose a large initiative into task files and completion reports (PRD -> tasks -> reports). Use when the user writes /prd, asks to create a PRD/TZ with task decomposition, or asks to generate files in tasks/prd_XX_* format."
---

# PRD Generator

Converts an initiative description into a structured delivery package: one PRD, task files, and a planning report.

```
/prd <description or file path>
```

---

## Workflow

### Step 0 — Branch

If in a git repo, create a dedicated branch:

```
git checkout -b codex/prd-XX-<slug>
```

`XX` = next available PRD number (zero-padded). Skip if not in a git repo.

### Step 1 — Read Input

Accept raw text or a file path. If a file path, read the file first. Normalize into a single source of requirements.

### Step 2 — Analyze and Save Scratchpad

Extract and write to `<feature>/docs/tasks/prd_XX_<slug>/prd_XX_scratch.md` before proceeding:

- Problem and target users
- Scope (in / out)
- Domain model — key entities and relationships
- API / integration needs
- Lifecycle / status model
- Acceptance criteria

### Step 3 — Write PRD

Determine `<feature>` from the input file path or user context. Slugs use kebab-case; numbers are zero-padded. Find the highest existing `prd_XX` number and increment.

Create: `<feature>/docs/tasks/prd_XX_<slug>/prd_XX_<slug>.md`

Required sections (quality gate — all must have concrete, testable content):

- **Objective** — clear goal statement
- **Non-objectives** — explicit exclusions
- **Data model** — entities, attributes, relationships
- **API list** — endpoints/methods with request/response
- **Validation & state transitions** — rules, constraints, status flow
- **Risks & mitigations** — identified risks with mitigation plans
- **Acceptance criteria** — measurable, testable statements

### Step 4 — Decompose into Tasks

Create: `<feature>/docs/tasks/prd_XX_<slug>/prd_XX_task_NN_<slug>.md`

Required sections per task (quality gate):

- **Goal** — what this task achieves
- **Scope** — boundaries
- **Subtasks** — numbered list
- **Deliverables** — concrete outputs
- **Definition of Done** — completion checklist
- **Tests** — verification steps
- **Dependencies** — which tasks must complete first

### Step 5 — Write Planning Report

After all task files are written, create one report:

`<feature>/docs/tasks/prd_XX_<slug>/prd_XX_rep_01_<slug>.md`

Required sections:

- **What was done** — summary of planning work
- **Files produced** — list of all files created
- **Deviations** — anything that differs from the input requirements
- **Next step** — first task to execute

### Step 6 — Commit

```bash
git add <feature>/docs/tasks/prd_XX_<slug>/
git commit -m "prd-XX: planning complete — <slug>"
```

---

## Troubleshooting

- **PRD quality gate fails** — ensure each section has concrete, testable content; vague sections don't pass
- **Task lacks clear DoD** — add specific, verifiable checklist items
- **Branch already exists** — use `git checkout` to switch instead of creating
- **Numbering conflict** — check existing `prd_*` directories for the latest number
