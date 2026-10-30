# Contracts as Source of Truth (OpenAPI / AsyncAPI / JSON Schema)

**Goal:** the boundary contract is written and agreed first; code, clients, mocks and tests are generated from it or verified against it. Code that drifts from the contract fails the build, not the customer.

Contract work is not a separate workflow. It lives inside the phases:

| Phase | Contract work |
| ----- | ------------- |
| **Specify** | Any AC that changes an HTTP endpoint, event, webhook or payload names the contract file it changes (e.g. `api/openapi.yaml#/paths/~1charges/post`). Classify each contract change as **additive** or **breaking** in the spec's Assumptions table. |
| **Design** | Write or extend the contract before code. Error model, nullability, required-ness, examples, auth, idempotency, versioning are decided here. Record breaking-change decisions as `AD-NNN` in `.specs/STATE.md`. |
| **Tasks / Implement** | The first slice of a feature that changes a contract updates the contract file and regenerates stubs/clients/mocks in the same commit. Never hand-transcribe DTOs from the spec. |
| **Verify** | Contract drift check (spec vs. code) and contract tests are part of the gate for any feature that touched a contract. |

## When it pays off - proportionality

Full contract-first discipline when there are **multiple parties on a contract** (frontend + backend, service-to-service, external consumers, payment providers, webhooks) or breaking a consumer is expensive. For an internal endpoint with a single caller you own, code-first with generated docs is honest and cheaper - say so and move on. This follows the risk tiers: a contract carrying money, auth or tenant data is Tier A no matter how small the change.

## Non-negotiables (every contract, every tier)

- **Backward compatibility.** Additive changes (new optional fields, new endpoints/channels) are safe. Removals, renames, type changes and new *required* fields are **breaking** and need a version bump or migration window.
- **One error model.** HTTP: RFC 7807 ProblemDetails, defined once in the spec.
- **Explicit required / optional / nullable** on every field.
- **Realistic examples** per schema/operation - they feed mocks, docs and tests.
- **Idempotency stated** per operation (idempotency keys or natural idempotency). Mandatory for anything financial.
- **The contract lives in the repo**, versioned and reviewed via PR with the code.

## Tooling (.NET defaults)

- Clients: Kiota or NSwag. OpenAPI document model: Microsoft.OpenApi.
- Mocks: Prism or WireMock from the spec.
- Drift: regenerate/compare in CI and fail on mismatch.
- Consumer-driven contract tests: Pact (PactNet).
- NFRs in the contract (SLOs, rate limits, payload limits, timeouts) validated by load tests (e.g. k6) as deploy gates.

## Deep references (load only what the task needs)

| Topic | Reference |
| ----- | --------- |
| HTTP contract design | [contracts-openapi.md](contracts-openapi.md) |
| Event / message contracts | [contracts-asyncapi.md](contracts-asyncapi.md) |
| Consumer-driven contract testing | [contracts-testing.md](contracts-testing.md) |
| Constraining LLM output to schemas | [contracts-ai-guardrails.md](contracts-ai-guardrails.md) |

## Boundaries

- Architecture style, service boundaries and sync vs. async are decided by the `software-architect` skill; this reference picks up after that and specifies the contract *on* the boundary.
- How the implementation is written (serializers, minimal API shape, validation code) belongs to the `dotnet-csharp` skill.

## Posture

- Ask who the consumers are before designing - the contract serves them, not the database schema.
- Flag every breaking change explicitly in any contract diff.
- Do not spec speculative endpoints "for later".
- For AI-facing contracts, always schema-validate model output after inference and design the failure path.
