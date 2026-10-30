# 02 — AsyncAPI Event Contracts (Messaging)

Judgment for specifying asynchronous communication — the gap classic SDD leaves open. AsyncAPI is to events/channels what OpenAPI is to HTTP.

## Index
1. Why async contracts need a spec even more than HTTP
2. AsyncAPI mental model
3. Designing message contracts
4. Event vs command — spec them differently
5. Schema evolution and compatibility
6. Reliability semantics belong in the contract
7. Tooling and .NET integration

---

## 1. Why async contracts need a spec even more than HTTP

HTTP failures are loud (compile errors on client regen, 4xx at runtime). **Messaging failures are silent**: a producer changes a payload field, the consumer deserializes with defaults or dead-letters quietly, and you discover it days later in data corruption. There's no browser to poke it with, and the coupling is invisible — producer and consumer never reference each other in code.

So the async boundary is *the* place where an explicit contract earns its keep — including **in-process** channels (a Gateway handing work to a background Worker through a queue/channel): same drift risk, same fix. If a message crosses a boundary between components that deploy or evolve separately, it deserves a spec'd schema.

## 2. AsyncAPI mental model

Map from OpenAPI: **channels** (≈ paths) are the topics/queues/routing keys; **operations** declare whether your app *sends* or *receives* on a channel; **messages** (≈ request/response bodies) have headers + payload defined by schemas; **servers** describe the broker(s) (RabbitMQ, Kafka, MQTT...); **bindings** carry protocol-specific settings (exchange type, queue durability, Kafka partitioning key).

Key perspective decision: an AsyncAPI document describes *one application's* view (what it publishes and consumes). The system picture emerges from the set of documents — keep one spec per service, in that service's repo, plus shared message schemas in a common location if multiple services exchange them.

## 3. Designing message contracts

- **Envelope + payload.** Standardize an envelope across all messages: `messageId` (for dedup/idempotency), `type` + `version`, `timestamp`, `correlationId` (trace the flow), `causationId` (what triggered it), then the domain payload. Spec the envelope once, reference everywhere. CloudEvents is a reasonable off-the-shelf envelope if you don't want to invent one.
- **Name events in past tense, business language:** `appointment.confirmed`, `lead.qualified` — an event states a fact that happened. Payload carries the data consumers need to react *without calling you back* (within reason — see thin vs fat below).
- **Thin events** (just IDs, consumer fetches details) minimize payload coupling but reintroduce synchronous dependency and load; **fat events** (full state) decouple runtime but couple schemas harder. Pick per event by consumer needs and change-frequency of the data; state the choice in the spec description.
- Same schema discipline as HTTP: explicit required/optional/nullable, formats, constraints, realistic examples per message.

## 4. Event vs command — spec them differently

- **Event** — broadcast fact, past tense, zero or many consumers, producer doesn't know or care who listens. Channel naming: `domain.entity.event` (`cliflow.appointment.confirmed`).
- **Command** — directed request, imperative (`SendWhatsAppMessage`), exactly one logical handler, sender expects it to be acted on (and often wants a resulting event or reply).
- **Request-reply over messaging** — spec the reply channel and correlation explicitly (AsyncAPI supports reply definitions); don't leave "how do I get the answer" as tribal knowledge.
Confusing the two corrupts the architecture: commands published as events invite multiple handlers doing a one-time action twice. The spec should make the kind unmistakable (naming + description + one-handler note).

## 5. Schema evolution and compatibility

Messaging adds a twist HTTP doesn't have: **old messages persist in queues/logs** while new code deploys, so compatibility must hold in both directions across a deployment window.
- **Backward compatible** (new consumer reads old messages): don't add required fields without defaults; don't remove fields the consumer needs; don't change types.
- **Forward compatible** (old consumer reads new messages): consumers must **ignore unknown fields** — make that a stated rule of every contract and configure deserializers accordingly (STJ default is to ignore; keep it that way for messages).
- Version the message **type**, not just the payload (`type: appointment.confirmed`, `version: 2`), and run dual-publish or upcasting during migrations. For Kafka-style ecosystems a schema registry enforces compatibility mode automatically; with RabbitMQ, your CI diff on the AsyncAPI spec plays that role.
- Breaking a message schema = new message version consumed alongside the old until all consumers migrate. There is no "just deploy both sides at once" in a system with queued backlog.

## 6. Reliability semantics belong in the contract

Consumers can't be built correctly without knowing these — so spec them (in message/channel descriptions and bindings), don't leave them implicit:
- **Delivery guarantee:** at-least-once is the realistic default → consumers MUST be **idempotent** (dedupe on `messageId` or natural key). State it on every channel.
- **Ordering:** guaranteed only per partition/queue under specific configs — state what ordering the consumer may assume (usually: none across keys).
- **Retry & dead-letter:** how many redeliveries, backoff, where dead letters go, who monitors them.
- **TTL / expiry:** messages that are worthless after a deadline (e.g. a time-boxed reservation) — spec the TTL so consumers don't act on stale intent.
These are contract-level facts; the *implementation* (MassTransit retry config, outbox pattern) belongs to the code, and the *decision* to be async at all belongs to architecture.

## 7. Tooling and .NET integration

- **AsyncAPI Studio / CLI** for authoring and validating documents; **Generator** produces docs sites and some code targets.
- **In .NET:** decorate/reflect MassTransit or handler code with **Saunter** (AsyncAPI doc generation from code) or author spec-first and validate messages against the schemas in integration tests. As with OpenAPI: pick one direction of truth, enforce in CI.
- JSON Schema is the shared payload language between OpenAPI and AsyncAPI — factor common domain schemas into files `$ref`'d by both, so the REST view and the event view of the same entity can't diverge.
- CI: lint the AsyncAPI doc, diff for breaking changes on PR, and run consumer contract tests against message schemas (Pact supports message pacts — see ref 03).
