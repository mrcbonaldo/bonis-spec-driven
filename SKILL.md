---
name: bonis-spec-driven
description: "Spec-driven workflow to specify, design, decompose, implement and verify software features. Phases are auto-sized on two axes: scope decides decomposition; risk tier (A critical, B standard, C light) decides validation depth. EARS acceptance criteria, requirement traceability, vertical-slice or atomic tasks, Conventional Commits, tier-aware Python validators. Tier A keeps an independent Verifier with a discrimination sensor; lighter tiers cut ceremony, never correctness, security or tenant isolation. Also covers API/event contracts (OpenAPI, AsyncAPI, contract tests). Triggers: specify feature, design, tasks, implement, validate, verify work, UAT, risk tier, API contract, OpenAPI, AsyncAPI, record decision, pause work, resume work. Not for architecture style or service-boundary decisions."
metadata:
  version: '2.0.0'
---

# Spec-Driven Development

Plan and implement features with precision. Rigor where risk is, speed everywhere else. Clear dependencies. Right tools. Zero ceremony.

```
┌──────────┐   ┌──────────┐   ┌─────────┐   ┌───────────┐   ┌──────────┐
│ SPECIFY  │ → │  DESIGN  │ → │  TASKS  │ → │ IMPLEMENT │ → │  VERIFY  │
└──────────┘   └──────────┘   └─────────┘   └───────────┘   └──────────┘
   required      optional*      optional*      required        required

* Agent auto-skips when scope doesn't need it
```

Verify always follows Implement automatically and is never prompted. Its depth follows the feature's **risk tier** - see [risk-tiers.md](references/risk-tiers.md): Tier A and B dispatch an independent Verifier; Tier C closes on the gate plus the author's self-check.

## Critical Rules (read before acting)

**Loading this skill's files.** Reference files live under `references/` in this skill's own directory (where this `SKILL.md` resides). Resolve them relative to the skill directory - never the workspace root - and load them through the active skill by name; never assume a fixed install path. When a step tells you to read a reference, **read it completely (to EOF)** before acting - never act on a partial/truncated read.

**Running this skill's scripts.** Every `scripts/*.py` shipped with this skill lives under that same skill directory. Resolve the skill directory first, then invoke `python3 <skill-dir>/scripts/<name>.py ...`. Never run `python3 scripts/...` from the consuming project root - that looks for a project-local `scripts/` tree that is not this skill. Project data under `.specs/` is still read/written relative to the project root (pass `--root` when the cwd is elsewhere). Below, `<skill-dir>` means the directory that contains this `SKILL.md`.

**Python interpreter.** `python3` in this skill means any Python 3 interpreter. The scripts use only the standard library. On Windows, where `python3` is often not on PATH, use `python` or `py -3` instead.

**Execution contract - every task, non-negotiable (holds even if you do not open the reference files):**

1. Tests derive from the spec's acceptance criteria and assert spec-defined outcomes - they never mirror the implementation.
2. The gate must pass (tests pass) before a task is done - the test runner decides, not self-assessment.
3. One atomic commit per task (Tier A) or per vertical slice (Tier B/C). Mark the work complete in `tasks.md` (and update spec traceability when used) **before** that commit, and include those updates in the same commit. Never weaken, skip, or delete tests to make them pass.
4. After the LAST task, the Verify phase starts automatically, never prompted. **Tier A:** a fresh Verifier (author ≠ verifier) runs the spec-anchored outcome check + discrimination sensor. **Tier B:** a fresh Verifier runs the spec-anchored check; the sensor runs only on non-trivial domain logic in the diff. **Tier C:** no Verifier - the full-suite gate and the author's self-check close the feature. See [risk-tiers.md](references/risk-tiers.md).
8. **Risk tier:** every spec declares `**Risk tier:** A|B|C` (missing = A). Tier-A triggers - money, split/fees, ledger, payment webhooks, idempotency, auth, tenant isolation, PII, external financial integrations - can never be classified lower. When in doubt, go higher; only the user lowers a tier. Correctness, security, data integrity and tenant isolation are never traded for speed in any tier.
5. **Blast radius:** approving a spec or tasks authorizes local implementation and local commits only. `git push`, force-push, deploy, production DB changes, and other remote / externally visible / destructive operations require an explicit go-ahead for that action.
6. **Constitution:** when `docs/CONSTITUTION.md` exists, its rules are project invariants. Never contradict them silently and never edit the file. See [constitution.md](references/constitution.md).
7. **Traceability (Tier A and B):** a requirement ID flows spec AC (`AUTH-01: WHEN ...`) → task `Requirement` → Verifier evidence row → verdict in `validation.md` and `spec.md`. A requirement leaves the chain only by being marked Deferred in `spec.md`. The validators below fail on any broken link. Tier C specs may omit requirement IDs.

**Deterministic gates run before human review - not from memory.** The structural gates for the spec and tasks are enforced by scripts in this skill's `scripts/` directory, so they cannot silently drift when the model forgets a step:

- Before confirming a spec: `python3 <skill-dir>/scripts/validate_spec.py <spec-path-or-feature>` (closure gate: EARS-shaped ACs, each AC prefixed with a known requirement ID, every requirement has an AC, filled assumptions, well-formed unique requirement IDs, required sections).
- Before presenting tasks for approval: `python3 <skill-dir>/scripts/validate_tasks.py <tasks-path-or-feature>` (granularity smell, every task drawn in a phase, diagram-vs-`Depends on` parity within a phase, no forward-phase dependency, every task carries `Tests` + `Gate` + `Requirement`, every requirement not Deferred maps to a task).
- On each commit: `python3 <skill-dir>/scripts/check_commit.py --message "<msg>"` (Conventional Commits). Optionally wire it as a git `commit-msg` guard (git only, no agent dependency) - see [implement.md](references/implement.md).
- Before declaring a feature done: `python3 <skill-dir>/scripts/validate_state.py <feature>` (tier-aware completion gate. Tier A/B: the Verifier's `validation.md` exists, its verdict is filled to PASS, and it cites `file:line` evidence - a missing, FAIL, placeholder, or evidence-free report fails; every requirement not Deferred is Verified with its own evidence row, in `validation.md` and `spec.md`. Tier C: no report required; a report that exists must still not be FAIL). The closing step of Verify runs this automatically, the same way the lessons layer runs at distillation; it is not a manual step.

All validators read the spec's risk tier; a spec without one is treated as Tier A.

A non-zero exit means STOP and fix before proceeding. Skip a script only when no code-execution tool is available; then perform the same checks by reading the artifact.

**Before Implement:** read [implement.md](references/implement.md) completely and run `<skill-dir>/scripts/validate_tasks.py`; if a formal `tasks.md` packs into more than one task-budgeted batch (> ~8 tasks), present the sub-agent offer first unless a standing decision in `.specs/STATE.md` pre-approves it (see Sub-Agent Delegation).

## Auto-Sizing: The Core Principle

**Two independent axes, not a fixed pipeline.** Before starting any feature, classify it on both:

1. **Risk tier (A/B/C) → validation depth:** spec rigor, test types, per-task review depth, commit granularity, Verifier, sensor, traceability. Full rubric and the Tier-A trigger list: [risk-tiers.md](references/risk-tiers.md). Read it before classifying.
2. **Scope (Small/Medium/Large/Complex) → decomposition:** whether Design and Tasks happen and how work is broken down (table below).

| Risk tier | Verify | Sensor | Commits | Per-task review |
| --------- | ------ | ------ | ------- | --------------- |
| **A** | Verifier, per feature | ≥5 mutations / tooling | per task | full Checks A-D + tables |
| **B** | Verifier, per feature | only on non-trivial domain logic | per vertical slice | one-line verdict (+ domain table) |
| **C** | gate + self-check | no | per vertical slice | one-line verdict |

Scope:

| Scope       | What                     | Specify                                                 | Design                                          | Tasks                         | Implement + Verify                                    |
| ----------- | ------------------------ | ------------------------------------------------------- | ----------------------------------------------- | ----------------------------- | ----------------------------------------------------- |
| **Small**   | ≤3 files, one sentence   | One-liner spec (inline)                                 | Skip                                            | Skip                          | Implement + verify inline                             |
| **Medium**  | Clear feature, <10 tasks | Spec (brief)                                            | Skip - design inline                            | Skip - tasks implicit         | Implement + verify                                    |
| **Large**   | Multi-component feature  | Full spec + requirement IDs                             | Architecture + components                       | Full breakdown + dependencies | Implement + verify per task                           |
| **Complex** | Ambiguity, new domain    | Full spec + [discuss gray areas](references/discuss.md) | [Research](references/design.md) + architecture | Breakdown + phase plan        | Implement + [interactive UAT](references/validate.md) |

**Rules:**

- **Specify, Implement and Verify are always required** - you always need to know WHAT, DO it, and PROVE it. Tier decides how heavy each one is.
- **Design is skipped** when the change is straightforward (no architectural decisions, no new patterns) - in any tier
- **Tasks is skipped** when there are ≤3 obvious steps (they become implicit in Implement). Tier B/C fold tasks into the spec unless the safety valve trips
- **Discuss is triggered within Specify** only when a gray area is genuinely unresolved - two or more valid behaviors and nothing in the spec, the codebase, `.specs/STATE.md` decisions, ADRs or the Constitution settles it. The mere presence of persistence, external calls or state is not a trigger; those dimensions are covered by the Specify sweep instead
- **Interactive UAT is triggered within Verify** only for user-facing features with complex behavior

**Safety valve:** Even when Tasks is skipped, Implement ALWAYS starts by listing steps inline (see [implement.md](references/implement.md)). If that listing reveals >8 vertical-slice steps (>5 for Tier A) or complex dependencies, STOP and create a formal `tasks.md` - the Tasks phase was wrongly skipped.

**Stop rule:** when the acceptance criteria pass and the tier's required validations pass, stop. No extra refactoring, no extra tests, no extra documentation. Out-of-scope ideas go to `.specs/BACKLOG.md`.

## .specs Structure

```
docs/
└── CONSTITUTION.md     # Optional, project-owned invariants (read-only for the agent)

.specs/
├── STATE.md            # Project memory: Decisions log (AD-NNN) + Handoff snapshot
├── BACKLOG.md          # Out-of-scope improvements noticed during work (append-only, one line each)
├── LESSONS.md          # Self-improving lessons playbook (rendered by scripts/lessons.py - do not hand-edit)
├── lessons.json        # Canonical lessons state (machine-owned)
└── features/           # Feature specifications
    └── [feature]/
        ├── spec.md         # Requirements with traceable IDs
        ├── context.md      # User decisions for gray areas (only when discuss is triggered)
        ├── design.md       # Architecture & components (only for Large/Complex)
        ├── tasks.md        # Tasks with verification (only for Large/Complex)
        └── validation.md   # Verifier report: PASS/FAIL, per-AC evidence, sensor result, diff range (Tier A/B)
```

**Create artifacts lazily.** Write each file only when its phase actually produces content - never scaffold empty `context.md`, `design.md`, or `tasks.md` up front. An empty file signals a phase happened when it did not; absence is the correct state for a skipped phase. The deterministic validators (`scripts/validate_spec.py`, `scripts/validate_tasks.py`, `scripts/check_commit.py`, `scripts/validate_state.py`) ship inside this skill's own `scripts/` directory, alongside `lessons.py`. Never create `docs/CONSTITUTION.md` on the user's behalf - it exists only when the project defines it.

## Workflow

**New feature:**

1. Specify → (Design) → (Tasks) → Implement → Verify (depth auto-sized)

**Resume work:**

1. Read `.specs/STATE.md` (Handoff + Decisions).
2. Reconcile Handoff against git (`branch`, `status --porcelain`, recent commits) and `tasks.md` - evidence wins over a stale snapshot. Full procedure: [memory.md](references/memory.md).
3. Propose the reconciled next step before writing code.

## Project Constitution (optional)

If `docs/CONSTITUTION.md` exists at the project root, treat it as the project's non-negotiable invariants: architectural decisions, security constraints, mandatory conventions, domain invariants, engineering principles. If it does not exist, continue normally - nothing in this skill depends on it.

- **Read it** before Specify, Design, and Implement.
- **Respect it.** It outranks `.specs/STATE.md` decisions, feature designs, and task definitions.
- **Report conflicts explicitly.** When a request, requirement, design choice, or task conflicts with a rule, stop and name the rule and the conflicting item. Never resolve it silently.
- **Never modify it.** Only the user changes the Constitution.

Full procedure: [constitution.md](references/constitution.md).

## Context Loading Strategy

**On-demand load (only what the current task needs):**

- `docs/CONSTITUTION.md` - when it exists: read at Specify, Design, and Implement ([constitution.md](references/constitution.md))
- `.specs/STATE.md` - Decisions section (read at Design, re-read on resume); Handoff section (read on resume only)
- confirmed lessons - load at Specify and Design via `python3 <skill-dir>/scripts/lessons.py list --status confirmed` ([lessons.md](references/lessons.md)); confirmed only, never candidates
- `references/risk-tiers.md` - at Specify (to classify) and whenever the tier decides a step
- `references/contracts.md` - when the feature adds or changes an HTTP endpoint, event, webhook or payload
- spec.md (when working on a specific feature)
- context.md (when designing or implementing from user decisions)
- design.md (when implementing from design)
- tasks.md (when executing tasks)

**Never load simultaneously:**

- Multiple feature specs
- Multiple architecture docs

**Target:** <40k tokens total context
**Reserve:** 160k+ tokens for work, reasoning, outputs
**Monitoring:** Display status when >40k (see [context-limits.md](references/context-limits.md))

## Sub-Agent Delegation

**Trigger:** count total tasks. If the feature packs into more than one task-budgeted batch (> ~8 tasks) → offer sub-agents; if it fits a single batch (≤ ~8 tasks) → execute inline.

**Offer-then-confirm** - never auto-spawn, unless `.specs/STATE.md` has a standing decision the user approved (e.g. `AD-NNN: auto-dispatch batch sub-agents for Tier B/C`). Then dispatch and say so in one line.

**Parallel batches (Tier B/C only):** batches with no dependency on each other (no `Depends on` edge crossing them) may run in parallel, each in its own git worktree, merged in phase order. Tier A batches always run sequentially.

**One worker per task-budgeted batch (~7 tasks, whole phases):** Phases stay the semantic/dependency unit; a **batch** is the execution unit - one or more *consecutive whole phases* packed to ~7 tasks. Walk phases in order, accumulate whole phases into the current batch until it reaches the budget, then start the next - **never split a phase** across workers. ~20 tasks → ~3 workers; scales linearly (40 → ~6). Each worker executes all its tasks in order (implement → gate → atomic commit), then reports a compact summary (tasks done, commit hashes, test counts, deviations). Batches run sequentially - a batch never starts until the previous one reports all tasks complete. Workers never spawn further sub-agents.

**Verifier (Tier A/B, never prompted):** After the final task is committed, the orchestrator dispatches a fresh Verifier sub-agent automatically - regardless of phase count. Tier C skips it (see [risk-tiers.md](references/risk-tiers.md)); steps (2) and (5) below apply per tier. Validation never requires a user prompt; it is the Verify phase, which follows Implement automatically. **Author ≠ verifier**: the Verifier re-derives coverage independently using evidence-or-zero; it does not inherit the author's mental model. The Verifier: (1) performs a **spec-anchored outcome check** - confirms each test's asserted value matches the spec-defined expected outcome, flags spec-precision gaps; (2) runs a **discrimination sensor** - injects behavior-level faults in an isolated scratch (temp worktree or file copies - never `git stash`), confirms tests kill them, discards the scratch and verifies real-tree porcelain matches the pre-sensor baseline; surviving mutants become fix tasks; (3) writes `.specs/features/[feature]/validation.md` (PASS/FAIL, per-AC evidence, sensor result, diff range); (4) returns a compact verdict + ranked gap list to the orchestrator in chat. Gaps become fix tasks; the fix→re-verify loop is bounded to 3 iterations before escalating. (5) **distills lessons** - turns each grounded failure (surviving mutant, spec-precision gap, failed AC, SPEC_DEVIATION) into a reusable project-local lesson via `<skill-dir>/scripts/lessons.py`; a clean PASS records nothing (see [lessons.md](references/lessons.md)).

**Model tier per role (only if the harness supports choosing a model per sub-agent).** Match the reasoning cost to the work instead of paying top-tier reasoning for boilerplate. A batch worker on a mechanical, low-ambiguity phase (entities, config, wiring, straightforward CRUD) runs on a faster/cheaper tier; a worker on a core-domain or high-ambiguity phase, and the Design phase itself, runs on a high-reasoning tier; the Verifier runs on a mid-to-high tier because it does adversarial reasoning and designs mutations. This is a portable recommendation: if the harness cannot set a per-sub-agent model, ignore it. Full rubric in [sub-agents.md](references/sub-agents.md).

**Standalone fallback:** Without sub-agents, run `validate.md` as an independent fresh-eyes pass after the final commit - including the spec-anchored check and discrimination sensor.

Full mechanics (worker payload, compact summary format, failure handling, context sizing, model tier, Verifier report format): [sub-agents.md](references/sub-agents.md).

## Commands

**Feature-level (auto-sized):**
| Trigger Pattern | Reference |
|----------------|-----------|
| Specify feature, define requirements | [specify.md](references/specify.md) |
| Discuss feature, capture context, how should this work | [discuss.md](references/discuss.md) |
| Design feature, architecture | [design.md](references/design.md) |
| Break into tasks, create tasks | [tasks.md](references/tasks.md) |
| Implement task, build, execute | [implement.md](references/implement.md) |
| Validate, verify, test, UAT, walk me through it | [validate.md](references/validate.md) |
| Risk tier, classify risk, how much rigor, definition of done | [risk-tiers.md](references/risk-tiers.md) |
| API contract, OpenAPI, AsyncAPI, breaking change, contract test, Pact | [contracts.md](references/contracts.md) |

**Memory:**
| Trigger Pattern | Reference |
|----------------|-----------|
| Record decision, this is a project-level decision | [memory.md](references/memory.md) |
| Pause work, end session, I need to stop | [memory.md](references/memory.md) |
| Resume work, continue, pick up where we left off | [memory.md](references/memory.md) |
| Load lessons, what have we learned, apply past lessons | [lessons.md](references/lessons.md) |
| Record lesson, distill lessons (auto-runs after validation) | [lessons.md](references/lessons.md) |
| Check against the constitution, project invariants | [constitution.md](references/constitution.md) |

## Knowledge Verification Chain

When researching, designing, or making any technical decision, follow this chain in order and stop at the first step that answers.

```
Step 1: Codebase → check existing code, conventions, and patterns already in use
Step 2: Project docs → `docs/CONSTITUTION.md` (when present), README, docs/, inline comments, `.specs/STATE.md` (Decisions)
Step 3: Context7 MCP → resolve library ID, then query for current API/patterns
Step 4: Web search → official docs, reputable sources, community patterns
Step 5: Flag as uncertain → "I'm not certain about X - here's my reasoning, but verify"
```

**Rules:**

- Stop at the first step that answers the question. An existing pattern in the codebase or a recorded decision ends the chain - do not consult Context7 or the web to re-confirm it. Go further only for a new library, a new API, or a pattern the project does not have yet
- Never skip to Step 5 if Steps 1-4 are available
- Step 5 is ALWAYS flagged as uncertain - never presented as fact
- **NEVER assume or fabricate.** If you cannot find an answer, say "I don't know" or "I couldn't find documentation for this". Inventing APIs, patterns, or behaviors causes cascading failures across design → tasks → implementation. Uncertainty is always preferable to fabrication.

## Output Behavior

**Do the work; do not narrate the machinery.** Produce the right artifact for the phase instead of announcing the phase ("I will now run the Specify phase"). The user judges the output, not a play-by-play of the process. This keeps the flow from reading as robotic.

**Match effort to the work.** Lightweight steps (feature-level checks, validation, mechanical tasks) do not need top-tier reasoning; heavy steps (complex design, ambiguous features) do. If the harness lets you pick a model per sub-agent, apply the tier rubric in [sub-agents.md](references/sub-agents.md); otherwise proceed and simply invest more care on the heavy steps. Mention this once per session at most, and only if it helps; skip it for an experienced user.

**Write generated artifacts in a plain, decided voice.** Specs, ADRs, validation reports, commit messages, and chat summaries follow the writing rules in [coding-principles.md](references/coding-principles.md): lead with the verdict, state decisions definitively, cut filler and mechanical hedging.

## Code Analysis

Use available tools with graceful degradation. See [code-analysis.md](references/code-analysis.md).
