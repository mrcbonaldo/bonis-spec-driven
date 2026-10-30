# 03 — Contract Testing (Consumer-Driven, Pact)

The safety net of SDD: automated proof that provider and consumers still agree, without integrated end-to-end environments. Catches the "silent change" — someone edits a C# property and forgets the world depends on it.

## Index
1. What contract tests are (and are not)
2. Consumer-driven flow with Pact
3. Provider verification done right
4. Message pacts (async)
5. Pact vs schema-diff vs E2E — choosing the guard
6. CI/CD wiring: can-i-deploy
7. Anti-patterns

---

## 1. What contract tests are (and are not)

A contract test verifies **the pair-wise agreement** between one consumer and one provider: "when I ask for X, I get a shape I can handle." It replaces the fragile alternative — spinning up both services (or all of them) in an integrated environment — with fast, isolated checks on each side.

They are **not** functional tests (they don't verify business logic correctness), **not** load tests, and **not** a replacement for the provider's own integration tests. Scope discipline matters: a contract asserts *what the consumer actually uses* — fields it reads, status codes it branches on — no more. Asserting the provider's whole response couples the test to things nobody depends on and generates false breakage.

## 2. Consumer-driven flow with Pact

Consumer-driven means **the consumer's real needs define the contract**, and the provider must satisfy the union of its consumers — inverting spec-first? No: it *complements* it. OpenAPI says what the provider offers; pacts prove which parts consumers rely on, making "can I remove this field?" answerable with data.

Flow (Pact, with PactNet in .NET):
1. **Consumer test:** the consumer's code runs against a **Pact mock provider**, declaring expected interactions ("given an appointment exists, GET /appointments/123 returns 200 with id, status"). Passing tests emit a **pact file** (JSON contract).
2. **Publish** the pact to a **Pact Broker** (or PactFlow) — versioned by consumer version + branch/tags.
3. **Provider verification:** the provider's CI replays every consumer's interactions against the real provider (in-memory via `WebApplicationFactory` is ideal) and reports results back to the broker.
4. Either side's pipeline **fails** if the agreement breaks — before deploy, per pair, with a precise diff of what broke and for whom.

Use **matchers** (type/regex matchers) rather than exact values wherever the consumer only cares about shape — exact-value pacts break on irrelevant data changes.

## 3. Provider verification done right

- **Provider states** ("given an appointment exists") are the hard part: the provider maps each state to setup code seeding exactly that data. Keep states few, named in business language, and reusable — an explosion of micro-states means consumers are over-specifying.
- Verify against the provider running with **test doubles only at its own external edges** (its DB seeded, third-party APIs stubbed) — verifying against a mocked controller verifies nothing.
- Run verification on every provider PR (against pacts of all consumers' main + deployed versions), not just on release day.
- Treat a failing verification as a conversation, not just a red build: either the provider is about to break someone (stop), or the consumer expects something never promised (fix the consumer/contract).

## 4. Message pacts (async)

Pact isn't HTTP-only — **message pacts** cover the event/queue world and pair with the AsyncAPI work (ref 02):
- **Consumer side:** the message consumer's handler is invoked with a Pact-provided sample message; the test asserts it can process the declared shape. Emits a pact describing the expected message.
- **Provider (producer) side:** verification asks the producer to *produce* each expected message type and checks the shape against the pact — without a broker in the loop.
This closes the loop the Gateway→Worker scenario needs: a change to the event DTO in the producer fails the producer's CI because the worker's pact no longer verifies.

## 5. Pact vs schema-diff vs E2E — choosing the guard

Three guards, different costs — a senior combines them, not picks one religiously:
- **Spec lint + breaking-change diff** (oasdiff/AsyncAPI diff): cheapest, catches *classes* of breakage (removed field, type change) with zero consumer knowledge. Run always.
- **Pact/CDCT:** catches breakage *for actual consumers*, including semantic reliance the schema can't express; enables `can-i-deploy`. Costs setup + broker + discipline. Highest value when consumers are separate teams/deployables you don't control atomically.
- **A few E2E smoke tests:** catch wiring/config issues contracts can't (auth misconfig, routing, infra). Keep them few — E2E as the primary guard is slow, flaky, and late.
If both sides of a boundary live in one repo and deploy together, schema-diff + integration tests may be enough; Pact shines exactly where deployment is independent.

## 6. CI/CD wiring: can-i-deploy

The broker records the verification **matrix** (which consumer version is compatible with which provider version). The **`can-i-deploy`** check queries it before a deployment: "is consumer v42 verified against the provider version currently in production?" — deploy proceeds only on green. This replaces "deploy and pray" release coordination between independently-deployed services, and is the tangible payoff of the whole setup.

Practical wiring: tag pact/verification results with environment (`deployed:prod`), run `can-i-deploy` as the final pipeline gate, and record deployments back to the broker so the matrix stays truthful.

## 7. Anti-patterns

- **Over-specified pacts** — asserting every field and exact values; breaks constantly, teaches teams to ignore red. Assert only what the consumer uses, with matchers.
- **Provider-driven "contract" tests** — the provider testing its own spec against itself catches drift but says nothing about consumers; don't confuse it with CDCT.
- **Contracts as functional tests** — pushing business-rule cases into pacts bloats verification; those belong in the provider's own tests.
- **No broker / pacts passed by hand** — files emailed around rot instantly; the broker's version matrix is half the value.
- **Skipping provider states hygiene** — flaky, order-dependent verification erodes trust fast.
- **100% pact coverage as a goal** — cover the consumer-critical interactions; the spec diff already guards the long tail.
