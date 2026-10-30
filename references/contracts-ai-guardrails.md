# 04 — AI Guardrails & Structured Outputs

Bringing the non-deterministic component (LLMs, speech-to-text) inside the contract discipline. An LLM is a dependency that *usually* honors the schema — the system must be correct even when it doesn't.

## Index
1. The core stance: the model is untrusted input
2. Getting structured output (strongest to weakest)
3. Post-inference validation — always
4. Failure paths and fallbacks
5. Contract between app and AI layer
6. Cost, latency, and context as contract constraints
7. Guarding inputs, not just outputs
8. Testing the non-deterministic

---

## 1. The core stance: the model is untrusted input

Treat every model response like a request body from the public internet: **parse, validate, reject, never assume**. The failure modes are known: invalid JSON, valid JSON with a missing/extra field, wrong enum casing, hallucinated values that pass shape checks but violate business rules (an appointment slot that doesn't exist), prompt-injected instructions embedded in user content, and drift after a provider model update. A pipeline that string-interpolates model output into the typed world without a validation gate is the AI equivalent of SQL concatenation.

## 2. Getting structured output (strongest to weakest)

Prefer the strongest mechanism the provider offers; layer them, don't rely on politeness:
1. **Native structured outputs / schema-constrained decoding** — the API enforces a JSON Schema on generation (OpenAI structured outputs; similar features elsewhere). Strongest: malformed output becomes (nearly) impossible. Use when available and the schema is expressible.
2. **Function calling / tools** — the model fills typed function parameters; the platform validates argument shape. Natural fit when the output *is* an action ("schedule_appointment(date, service)"). In .NET, Microsoft.Extensions.AI / Semantic Kernel bind tool parameters to C# types.
3. **JSON mode** — guarantees syntactically valid JSON but **not** your schema; fields can still be missing or wrong. Must be paired with validation.
4. **Prompt-only instruction** ("respond only with JSON matching...") — weakest; acceptable only with full validation + repair behind it.
Keep the schema **small and flat**: deep nesting, unions, and clever polymorphism raise failure rates. If the output is complex, decompose into multiple smaller calls with simple schemas.

## 3. Post-inference validation — always

Regardless of mechanism, run the gate before the value enters the system:
- **Shape:** deserialize with STJ into the target record; unknown-field tolerance on, but *required* fields enforced (`required` members / explicit checks). Reject on failure — don't default-fill silently.
- **Semantics:** business validation the schema can't express — the slot exists, the date is in the future, the ID references a real entity, numeric ranges. Same validators you'd run on user input; reuse them.
- **Repair loop (bounded):** on validation failure, one retry with the error appended ("your response failed: field X missing — return corrected JSON only") often fixes it cheaply. **Cap retries (1–2)** and then take the failure path — unbounded repair loops burn tokens and hide systemic problems.
- Log validation failures with the raw output — this is your drift detector when the provider updates the model.

## 4. Failure paths and fallbacks

Design the failure path with the same care as the happy path; for a conversational agent it's the difference between a bad day and a lost customer:
- **Degrade tiers:** retry (bounded, with jitter) → fallback model/provider → rule-based/template response → human handoff ("I'll have someone confirm this for you") → queue for later. Choose the tiers per operation criticality; encode them, don't improvise in the handler.
- **Timeouts and circuit breakers** on the AI call like any external dependency (Polly / resilience handler): a hung LLM call must not hold a request thread or a user hostage.
- **Never block a critical business action on AI availability** when a non-AI path exists — the AI qualifies leads; a dumb form still captures them when it's down.
- Idempotency on AI-triggered side effects: if the pipeline retries, the appointment must not be booked twice (idempotency keys / natural keys, same discipline as messaging in ref 02).

## 5. Contract between app and AI layer

Isolate the AI behind an internal contract so the rest of the system stays deterministic:
- A typed interface (`Task<LeadQualification> QualifyAsync(ConversationContext ctx, CancellationToken ct)`) whose **return types are validated records** — the messy prompt/parse/validate/repair lives inside; callers see only clean types or a typed failure result.
- **Version prompts + schemas together** in the repo (a prompt change is a contract-relevant change: review it, diff it, test it). Record model name/version per interaction for auditability.
- Pin model versions where the provider allows; treat a model upgrade like a dependency upgrade — run the eval suite (§8) before rollout, don't absorb it silently.
- This is also the seam for the fallback tiers, caching, and cost controls — one place, not scattered across handlers.

## 6. Cost, latency, and context as contract constraints

Non-functional limits belong in the design, same as SLOs in an API spec:
- **Budget per interaction:** max tokens in/out per call and per conversation; truncate/summarize history to fit — unbounded conversation context is unbounded cost and latency.
- **Latency budget:** decide sync vs async per operation — a WhatsApp reply tolerates seconds; anything longer goes through the queue/worker with a "typing…"/deferred pattern (the async boundary then follows ref 02's contract rules).
- **Caching:** cache deterministic sub-results (embeddings for identical text, answers to recurring identical intents) with explicit TTL and invalidation. Semantic caching (vector-similarity hit on "same question, different words") is powerful for high-repetition flows but adds an infra dependency and a correctness risk (false hits) — adopt it when repetition volume is measured, not preemptively.
- Track cost per conversation/tenant as a first-class metric with alerts — cost regressions are production incidents in AI systems.

## 7. Guarding inputs, not just outputs

- **Prompt injection:** user content is data, not instructions. Separate system instructions from user content structurally (message roles); never concatenate user text into the instruction block; treat "ignore previous instructions" survivability as a test case. If the model has tools, constrain them (allow-lists, scoped permissions) so injected instructions can't do damage even when they land.
- **Boundary limits:** cap user input size before it reaches the model (cost + injection surface); strip/neutralize markup that could smuggle instructions.
- **PII discipline:** decide and document what user data may enter prompts (and thus provider logs); redact what mustn't. This is a contract with your own compliance posture, in writing.

## 8. Testing the non-deterministic

- **Deterministic layer tests:** everything around the model — validators, repair loop, fallbacks, prompt assembly — is normal code; unit test it with recorded/fake model responses (valid, malformed, malicious).
- **Golden/eval suite:** a versioned set of representative inputs with assertions on the *validated output* (schema-valid, correct intent classification, required fields present) run against the real model on a schedule and before model/prompt changes. Assert properties, not exact strings — exact-match tests on LLM output are flaky by construction.
- **Contract tests still apply:** the AI service's *external* contract (its API/messages) is spec'd and pact-tested like any service (refs 01–03) — consumers of the AI worker shouldn't know or care there's a model inside.
