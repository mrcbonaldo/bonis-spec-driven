# Risk Tiers - Delivery Efficiency and Risk-Based Validation

**Goal:** Spend validation effort where a defect is expensive, and nowhere else. Scope decides how the work is decomposed; **risk decides how deeply it is validated.** The two axes are independent: a 2-file change to fee calculation is small *and* Tier A; a 15-file admin CRUD is large *and* Tier C.

Specs (acceptance criteria, OpenAPI/AsyncAPI contracts, ADRs) are the source of truth and are never skipped. What scales with risk is ceremony, prose, and test depth - not the contract.

---

## Principles

- Prioritize working software and incremental delivery over exhaustive documentation.
- Apply validation rigor proportionally to business and technical risk.
- Reuse established architectural patterns, conventions, and existing specifications.
- Do not create redundant documentation, tests, or validation scenarios.
- Test each business behavior in exactly one layer, unless a reason is written next to the test.
- Prioritize critical business rules, security boundaries, data isolation, financial operations, and external integrations.
- Avoid unnecessary task fragmentation and excessive implementation planning.
- Do not introduce improvements unrelated to the current requirement. Record them in `.specs/BACKLOG.md`.
- Stop refining when acceptance criteria are satisfied and the tier's required validations pass.
- **Never trade correctness, security, data integrity, or tenant isolation for speed.**

---

## Classifying the Tier

Declare the tier in `spec.md`, right under the title:

```markdown
**Risk tier:** A
**Risk rationale:** [one line - required for B and C]
```

**Tier A** - the change touches ANY of:

- money movement, prices, fees, split / commission calculation, refunds, payouts
- balances, ledger, reconciliation
- payment webhooks, idempotency, retry/dedup of financial events
- authentication, authorization, permission checks
- tenant isolation / multi-tenant data boundaries
- personal or sensitive data (PII), secrets, encryption
- integrations with external financial or payment providers
- irreversible data migrations

**Tier B** - user-facing business flows not covered by A (catalog, checkout UX that does not compute money, notifications, onboarding, search).

**Tier C** - admin/backoffice screens, CRUD over non-sensitive data, configuration, reports/read models, UI-only changes, internal tooling.

**Rules:**

- **When in doubt, choose the higher tier.** A wrong A costs minutes; a wrong C costs an incident.
- B and C require a one-line `Risk rationale`. `validate_spec.py` flags a B/C spec whose text mentions a Tier-A trigger: it is an ERROR without a rationale and a WARN with one (confirm the rationale actually addresses it).
- A feature takes the tier of its riskiest requirement. Do not split a Tier-A requirement out of a feature to make the rest cheaper unless it is genuinely independent.
- A spec with no declared tier is treated as **Tier A** by every validator (safe default).
- The tier can only be lowered by the user. The agent may raise it on its own at any point and says so in one line.

---

## What Each Tier Requires

| | **A - critical** | **B - standard** | **C - light** |
|---|---|---|---|
| **Phases** | Specify → Design (when structural) → Tasks → Implement → Verify | Specify (spec + implicit tasks in one doc) → Implement → Verify | Short spec → Implement |
| **Spec** | Full template, EARS ACs, requirement IDs, assumptions table, full implicit-dimension sweep | Full template, EARS ACs, requirement IDs; sweep only dimensions present | Problem, Out of Scope, 3-5 ACs with SHALL. Requirement IDs optional |
| **Discuss** | When a gray area is unresolved | When a gray area is unresolved | Only if the user asks |
| **Tasks granularity** | Atomic tasks (one concept each) | Vertical slices (one endpoint/flow end to end per task) | Vertical slices; inline plan, no `tasks.md` unless > 8 steps |
| **Tests** | Unit + property-based on domain rules; integration with a real database (e.g. Testcontainers); contract tests against external APIs | Integration tests on main flows + listed error paths | Integration/smoke test on the happy path + validation errors |
| **Per-task adequacy review** | Full Checks A-D with both mapping tables | Checks A-D, one-line verdict; mapping table only for domain-layer criteria | One-line verdict |
| **Commits** | One per task | One per vertical slice | One per vertical slice |
| **Verifier (author ≠ verifier)** | Always, per feature | Always, per feature | Not required - gate + self-check |
| **Discrimination sensor** | Yes: ≥5 mutations or mutation tooling on Tier-A code | No by default; 1-3 mutations only on domain files in the diff when the feature has non-trivial domain logic | No |
| **Traceability chain** | Full (spec → task → evidence → verdict) | Full | Not required |
| **`validate_state.py`** | PASS report + file:line evidence + traceability | PASS report + file:line evidence + traceability | Passes without `validation.md` |

**Never relaxed in any tier:**

- Tests derive from the spec's acceptance criteria and assert spec-defined outcomes.
- The test runner decides when a task is done - not self-assessment.
- Never weaken, skip, or delete a test to make it pass.
- Blast radius: push, deploy, production DB changes need an explicit go-ahead.
- `docs/CONSTITUTION.md` rules are invariants.
- Tier A keeps the Verifier, the sensor, and the full traceability chain.

---

## Test Economy (all tiers)

- **One behavior, one layer.** If an integration test already asserts a rule end to end, do not repeat the same assertion in a unit test - unless the unit test covers a combinatorial space the integration test cannot (then say so in a comment).
- **Prefer high-leverage tests:** property-based tests (e.g. FsCheck, Hypothesis, fast-check) for calculations and invariants ("the parts always sum to the total", "no negative amount", "rounding is deterministic") replace dozens of hand-written cases.
- **Do not test:** DTOs, mappings, pass-through handlers, framework or library behavior, auto-generated code.
- **Coverage targets are per layer, not global:** domain high, edges low.
- **Run affected tests per task** (filter by test project/category), the full suite once at the end of a phase and in Verify.

---

## Definition of Done

1. Acceptance criteria met.
2. Existing test suite green.
3. Tests required by the tier are present and passing.
4. No new architecture or Constitution violations.
5. Spec and code in sync (no unrecorded `SPEC_DEVIATION`).
6. `validate_state.py <feature>` exits 0 (tier-aware).
