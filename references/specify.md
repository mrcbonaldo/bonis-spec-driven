# Specify

**Goal**: Capture WHAT to build with testable, traceable requirements.

If the feature has ambiguous gray areas (multiple valid approaches for user-facing behavior), the agent will automatically trigger the [discuss gray areas](discuss.md) process within this phase. For clear, well-defined features, it goes straight to the next phase.

## Implicit-Requirement Dimensions

The canonical rubric for requirements that are easy to miss. Referenced by [discuss.md](discuss.md) - defined here, not duplicated.

| Dimension | What to cover |
| --------- | ------------- |
| Input validation & bounds | Limits, formats, sanitization |
| Failure / partial-failure states | Timeouts, partial saves, rollbacks |
| Idempotency / retry / duplicate handling | Safe retries, dedup keys |
| Auth boundaries & rate limits | Who can call what, throttle rules |
| Concurrency / ordering | Race conditions, ordering guarantees |
| Data lifecycle / expiry | TTL, archival, deletion |
| Observability | Logging, metrics, tracing hooks |
| External-dependency failure | Circuit breakers, fallbacks |
| State-transition integrity | Valid transitions, guards |

---

## Process

### 0. Classify the Risk Tier (first, always)

Read [risk-tiers.md](risk-tiers.md) and declare the tier at the top of the spec (`**Risk tier:** A|B|C`, plus `**Risk rationale:**` for B/C). The tier sets how heavy the rest of this phase is:

- **Tier A:** everything below, full strength.
- **Tier B:** full template; dimensions sweep covers only dimensions present; closure gate at Medium depth.
- **Tier C:** use the short template at the end of this file. No sweep, no closure gate, no Discuss unless the user asks. Requirement IDs optional.

If the feature adds or changes an endpoint, event, webhook or payload, also read [contracts.md](contracts.md): ACs name the contract file they change, and each contract change is classified additive/breaking in the Assumptions table.

### 1. Clarify Requirements

**Read the Constitution first (when present):** If `docs/CONSTITUTION.md` exists, read it completely before clarifying. Every requirement, acceptance criterion, and assumption must conform to it. A requested behavior that violates a rule is a conflict to report, not a requirement to write - see [constitution.md](constitution.md).

**Then load confirmed lessons:** Before clarifying, load the project's confirmed lessons so past verification failures shape this spec instead of repeating. Run `python3 <skill-dir>/scripts/lessons.py list --status confirmed` (optionally `--scope [area]` or `--query [term]` for the area this feature touches) and apply what comes back as guidance. Load only `confirmed` - never `candidate` or `quarantined`. If no store exists yet or no code tool is available, skip silently. See [lessons.md](lessons.md).

**Lightweight context scan first (Knowledge Verification Chain Step 1):** Before asking questions, briefly scan existing code, patterns, and neighboring features relevant to this feature. Use what you find to ground your clarifying questions in reality - not to constrain the spec to current implementation. Keep it lightweight (stay within the <40k token budget; reuse the chain, no new machinery). The spec captures WHAT is needed, not only what exists.

You are a thinking partner, not an interviewer. Start open - let the user dump their mental model. Follow the energy: whatever they emphasize, dig into that.

Ask conversationally (not as a checklist):

- "What problem are you solving?"
- "Who is the user and what's their pain?"
- "What does success look like?"

If needed:

- "What are the constraints (time, tech, resources)?"
- "What is explicitly out of scope?"

**Facts you look up; decisions you ask.** Anything discoverable by reading the environment (the codebase, config, docs, existing conventions) you resolve yourself through the Knowledge Verification Chain - do not spend the user's attention asking for it. Reserve questions for genuine decisions that are the user's to make: scope, priorities, product behavior, trade-offs. A question you could have answered by reading the code erodes trust and wastes a turn.

**Challenge vagueness.** Never accept fuzzy answers. "Good" means what? "Users" means who? "Simple" means how? Make the abstract concrete: "Walk me through using this." "What does that actually look like?"

**Know when to stop - then run the dimensions sweep.** When you understand what they're building, why, who it's for, and what done looks like, run a closing **implicit-requirement dimensions sweep** before offering to proceed:

- **Tier A (any scope) / Large / Complex:** Cover every dimension above - each must resolve to a requirement OR an explicit `N/A because [reason]`. No blank entries allowed.
- **Tier B / Medium:** Cover only dimensions obviously present for this feature's domain; collapse the rest to a single `remaining dimensions N/A for this scope`.
- **Tier C / Small:** Skip the sweep entirely.

When tier and scope disagree, the stricter row wins.

The `N/A because...` escape is mandatory - it prevents inventing requirements to fill the checklist. Bound the sweep to THIS feature's scope; never add requirements outside the feature boundary.

### 2. Capture User Stories with Priorities

**P1 = MVP** (must ship), **P2** (should have), **P3** (nice to have)

Each story MUST be **independently testable** - you can implement and demo just that story.

### 3. Write Acceptance Criteria (EARS notation)

Write every acceptance criterion in **EARS** (Easy Approach to Requirements Syntax). Each criterion resolves to exactly one pattern, which keeps it unambiguous and directly testable. Choose the pattern that fits the requirement instead of forcing everything into a single shape:

| Pattern | Keyword | Template | Use for |
| ------- | ------- | -------- | ------- |
| Ubiquitous | (none) | The [system] SHALL [response] | Always-on invariants and constraints |
| Event-driven | WHEN | WHEN [trigger] THEN the [system] SHALL [response] | A response to a discrete trigger |
| State-driven | WHILE | WHILE [state] the [system] SHALL [response] | Behavior that holds during a state |
| Optional-feature | WHERE | WHERE [feature is present] the [system] SHALL [response] | Behavior gated behind an optional capability or flag |
| Unwanted-behavior | IF / THEN | IF [undesired condition] THEN the [system] SHALL [response] | Errors, failures, invalid input, timeouts |
| Complex | combination | WHILE [state], WHEN [trigger] the [system] SHALL [response] | Richer behavior combining the above |

**Why patterns beat one shape:** failure states, state transitions, and optional behavior become first-class criteria instead of footnotes squeezed into WHEN/THEN. The patterns map onto the implicit-requirement dimensions above: state-transition integrity to State-driven; failure and external-dependency failure to Unwanted-behavior; feature flags to Optional-feature.

**Rules:** one requirement per criterion (never bundle two behaviors); use concrete values (a specific status code, a specific message, a bound) rather than "quickly" or "gracefully"; every criterion contains a SHALL and is measurable. `python3 <skill-dir>/scripts/validate_spec.py` flags any criterion without a SHALL and any that matches no recognized pattern.

**Traceability starts here.** Prefix every criterion with the requirement ID it belongs to: `AUTH-01: WHEN ... THEN the system SHALL ...`. Several criteria can share one ID; every ID in the Requirement Traceability table needs at least one criterion. The same ID then flows into each task's `Requirement` field, the Verifier's evidence rows, and the final verdict in `validation.md` - the scripts check every link, so a requirement cannot disappear between phases.

### 4. Requirement Closure Gate (before confirm)

Before presenting the spec for confirmation, run the checks below. The spec is not presentable for confirmation until every item is resolved or assumption-logged - this is the guarantee that no requirement leaves the spec silently unclear.

**Tiered:** Tier A or Large/Complex = full gate; Tier B or Medium = resolve obvious ambiguities, log the rest as assumptions; Tier C or Small = skip entirely (consistent with skipping the sweep). The stricter of tier and scope wins.

1. **Unambiguity + precision (hard).** Every AC must (a) have a single interpretation and (b) define a precise, spec-defined expected outcome. Any AC that fails either check: resolve with the user, split it, or log it as an explicit assumption with the chosen interpretation and rationale. No AC proceeds readable two ways or with an undefined outcome.

2. **Open-questions / assumptions closure.** Enumerate every unresolved decision that surfaced during clarification. Each must be either (a) resolved with the user OR (b) recorded as an **assumption** (chosen default + rationale) in the spec's Assumptions & Open Questions section. Nothing proceeds unmarked.

3. **Declined gray areas become assumptions.** Any gray area the user declined to discuss or that went undiscussed is written to the spec's Assumptions & Open Questions section (agent's chosen default + rationale) - never silently dropped. See [discuss.md](discuss.md).

4. **Constitution conformance (only when `docs/CONSTITUTION.md` exists).** No AC, assumption, or out-of-scope decision contradicts a Constitution rule. Any conflict is reported to the user and resolved before confirmation; the resolution is logged as an assumption row. See [constitution.md](constitution.md).

Fix inline. This gate is bounded to THIS feature's stated dimensions and actual behavior - never to "anything imaginable." The Out of Scope table and anti-scope-creep rules remain the counterweights: the gate clarifies existing requirements, it never invents new ones.

**Deterministic backing (run before you present the spec).** The structural half of this gate is enforced by a script so it cannot drift when a step is forgotten: `python3 <skill-dir>/scripts/validate_spec.py <spec-path-or-feature>` checks that required sections exist, every AC is EARS-shaped (has a SHALL), no Assumptions row has an empty default or rationale, and requirement IDs are well-formed and unique. Once the traceability table has real IDs, it also checks that every AC starts with a known ID and every ID has at least one AC. A non-zero exit means fix before confirming. The script checks structure; you still own the judgment calls (is the interpretation right, is the outcome precise). If no code-execution tool is available, run the same checks by reading the spec.

---

## Template: `.specs/features/[feature]/spec.md`

```markdown
# [Feature Name] Specification

**Risk tier:** [A | B | C]
**Risk rationale:** [one line - required for B and C]

## Problem Statement

[Describe the problem in 2-3 sentences. What pain point are we solving? Why now?]

## Goals

- [ ] [Primary goal with measurable outcome]
- [ ] [Secondary goal with measurable outcome]

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature     | Reason         |
| ----------- | -------------- |
| [Feature X] | [Why excluded] |
| [Feature Y] | [Why excluded] |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default  | Rationale | Confirmed? |
| --------------------- | --------------- | --------- | ---------- |
| [ambiguity]           | [what we'll do] | [why]     | [y/n]      |

**Open questions:** none - all resolved or logged above (required before the spec is confirmed).

---

## User Stories

### P1: [Story Title] ⭐ MVP

**User Story**: As a [role], I want [capability] so that [benefit].

**Why P1**: [Why this is critical for MVP]

**Acceptance Criteria** (each line is one EARS pattern, prefixed by its requirement ID):

1. [FEAT]-01: WHEN [user action/event] THEN system SHALL [expected behavior]  <!-- event-driven -->
2. [FEAT]-01: IF [invalid input / failure] THEN system SHALL [graceful handling]  <!-- unwanted-behavior -->
3. [FEAT]-02: WHILE [state holds] system SHALL [behavior during that state]  <!-- state-driven -->
4. [FEAT]-02: The system SHALL [always-on invariant]  <!-- ubiquitous -->

**Independent Test**: [How to verify this story works alone - e.g., "Can demo by doing X and seeing Y"]

---

### P2: [Story Title]

**User Story**: As a [role], I want [capability] so that [benefit].

**Why P2**: [Why this isn't MVP but important]

**Acceptance Criteria**:

1. [FEAT]-03: WHEN [event] THEN system SHALL [behavior]
2. [FEAT]-03: WHEN [event] THEN system SHALL [behavior]

**Independent Test**: [How to verify]

---

### P3: [Story Title]

**User Story**: As a [role], I want [capability] so that [benefit].

**Why P3**: [Why this is nice-to-have]

**Acceptance Criteria**:

1. [FEAT]-04: WHEN [event] THEN system SHALL [behavior]

---

## Edge Cases

Edge cases are usually unwanted-behavior (IF/THEN) or boundary (WHEN) criteria:

- IF [error scenario] THEN system SHALL [graceful handling]
- IF [unexpected input] THEN system SHALL [validation response]
- WHEN [boundary condition] THEN system SHALL [behavior]

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story       | Phase  | Status  |
| -------------- | ----------- | ------ | ------- |
| [FEAT]-01      | P1: [Story] | Design | Pending |
| [FEAT]-02      | P1: [Story] | Design | Pending |
| [FEAT]-03      | P2: [Story] | -      | Pending |
| [FEAT]-04      | P3: [Story] | -      | Deferred |

**ID format:** `[CATEGORY]-[NUMBER]` (e.g., `AUTH-01`, `CART-03`, `NOTIF-02`). Each ID appears in exactly one row, and every acceptance criterion starts with its ID.

**Status values:** Pending → In Design → In Tasks → Implementing → Verified, or **Deferred** - explicitly postponed out of this delivery with the user's agreement. A Deferred requirement needs no task and no verification; every other requirement must reach Verified.

**Coverage:** X total, Y mapped to tasks, Z deferred (none unmapped)

---

## Success Criteria

How we know the feature is successful:

- [ ] [Measurable outcome - e.g., "User can complete X in < 2 minutes"]
- [ ] [Measurable outcome - e.g., "Zero errors in Y scenario"]
```

---

## Template: Tier C (short spec)

```markdown
# [Feature Name] Specification

**Risk tier:** C
**Risk rationale:** [why no Tier-A trigger applies - e.g. "admin CRUD over product categories, no money, no tenant data crossing"]

## Problem Statement

[1-2 sentences]

## Out of Scope

- [what this change does not do]

## Acceptance Criteria

1. WHEN [action] THEN the system SHALL [outcome]
2. IF [invalid input] THEN the system SHALL [response]
3. [3-5 criteria total, each with SHALL]
```

`validate_spec.py` accepts this shape for Tier C. If any criterion turns out to touch a Tier-A trigger, raise the tier and switch to the full template.

---

## Tips

- **Tier first** - classify before writing anything else; the tier decides how much of this file applies
- **P1 = Vertical Slice** - A complete, demo-able feature, not just backend or frontend
- **EARS is code** - If you can't write a criterion as a test, rewrite it; pick the pattern (WHEN / WHILE / WHERE / IF / ubiquitous) that fits
- **Requirement IDs are mandatory** - Every story maps to trackable IDs, and every AC starts with its ID
- **Defer explicitly** - A requirement left out of this delivery is marked Deferred, never silently dropped
- **Edge cases matter** - What breaks? What's empty? What's huge?
- **Out of Scope prevents creep** - If it's not here, it doesn't get built
- **Closure gate before confirm** - Three checks (four with a Constitution): unambiguity + precision, open-questions/assumptions closure, declined gray areas logged, Constitution conformance; scope-tiered; bounded to stated dimensions; never invents requirements
- **Confirm after the gate passes** - Present the spec for user confirmation only after the closure gate passes (no unresolved-and-unmarked items remain) and `validate_spec.py` exits clean; user approves spec before moving to discuss phase
