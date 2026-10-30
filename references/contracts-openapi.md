# 01 — OpenAPI Contracts (HTTP)

Judgment for designing HTTP API contracts with OpenAPI (3.x). Not a spec syntax tutorial — what makes a contract good, and the .NET tooling around it.

## Index
1. Design-first mechanics
2. Resource and operation design
3. Schemas: the payload discipline
4. The error contract
5. Versioning and evolving without breaking
6. Auth, pagination, filtering conventions
7. .NET toolchain for OpenAPI

---

## 1. Design-first mechanics

- Author the spec as YAML in the repo (`/spec` or alongside the service). Split large specs with `$ref` into components files; bundle for distribution.
- **Review the spec in PR with the consumers** before implementation starts. Contract review checklist: naming consistency, required/nullable correctness, error model coverage, breaking-change scan, examples present.
- ASP.NET Core 10 generates OpenAPI 3.1 natively from code — that's fine for *publishing* a spec, but in SDD the generated document is compared against the authored contract in CI (or the authored spec is the generation source). Either direction works; **pick one direction of truth and enforce it**. Two hand-maintained versions always diverge.
- Lint the spec in CI (Spectral is the de-facto linter) with a ruleset encoding your conventions — naming, required descriptions, error responses on every operation.

## 2. Resource and operation design

- Model **resources and state transitions**, not RPC verbs: `POST /appointments` + `PATCH /appointments/{id}` beats `/createAppointment`. Where an action truly isn't CRUD (e.g. `/appointments/{id}/confirm`), a sub-resource action endpoint is honest — don't contort it.
- Correct verb semantics matter because consumers and infrastructure rely on them: GET is safe/cacheable, PUT is idempotent full-replace, PATCH is partial, DELETE idempotent, POST is the non-idempotent default (give it an idempotency-key mechanism when consumers will retry).
- Status codes are part of the contract: 200/201(+Location)/204 for success variants; 400 validation, 401 vs 403, 404, 409 conflict (optimistic concurrency, duplicates), 422 semantic invalid, 429 rate limit; 5xx for faults. Spec every response the consumer must handle, not just 200.
- Consistent casing and naming across the whole surface (pick camelCase JSON and stick to it); plural resource names; no leaking internal table/entity names when the domain language differs.

## 3. Schemas: the payload discipline

- **Every property deliberately `required` or optional, `nullable` or not.** The most common contract bug is an implicitly-optional field the consumer assumed was always present.
- Use `enum` for closed sets — but know that **adding an enum value is breaking for consumers that validate strictly**; if the set will grow, document open-world handling ("treat unknown as X") or use a string with documented values.
- Constrain what you can: `format` (uuid, date-time, email), `minLength/maxLength`, `minimum/maximum`, `pattern`. Constraints in the schema become generated validation for free and stop garbage at the edge.
- Prefer **separate request/response schemas** over one shared model with server-managed fields marked `readOnly` — id/createdAt on create-requests confuse generators and consumers.
- Compose with `allOf` for extension; use discriminated unions (`oneOf` + `discriminator`) for polymorphic payloads — mirrors STJ polymorphic serialization on the .NET side.
- Realistic `example`/`examples` on every schema — they drive mocks and catch nonsense shapes at review time.

## 4. The error contract

- One error shape for the whole API: **RFC 7807 ProblemDetails** (`type`, `title`, `status`, `detail`, plus an `errors` dictionary for validation). Define it once in `components`, reference it from every 4xx/5xx.
- Machine-readable error *codes* (stable strings, e.g. `slot_already_taken`) beat parsing human messages — consumers branch on codes; messages are for humans and may change.
- Spec the rate-limit behavior: 429 + `Retry-After`. Spec what a validation 400 looks like field-by-field.

## 5. Versioning and evolving without breaking

Breaking vs additive — memorize the classification:
- **Additive (safe):** new endpoint; new *optional* request field; new response field (consumers must ignore unknowns — state that rule in the spec); new enum value *only if* open-world handling is documented.
- **Breaking:** removing/renaming anything; changing a type or format; making an optional field required; narrowing constraints; changing error codes/status semantics; changing auth.
- Strategy: **avoid versioning by designing additively** as long as possible. When you must break: URL major version (`/v2/...`) is the bluntest and clearest; header/media-type versioning is cleaner but harder for consumers. Run old and new in parallel with a sunset window (announce via `Deprecation`/`Sunset` headers and in the spec's `deprecated: true`).
- Automate breaking-change detection in CI: diff the spec against the base branch (oasdiff or similar) and fail on breaking diffs without an explicit version bump.

## 6. Auth, pagination, filtering conventions

- Declare security schemes in the spec (`bearerAuth` JWT etc.) and apply per-operation — consumers generate auth handling from it.
- Pagination is contract: pick one style (cursor-based scales better than offset for deep pages), spec the parameters (`cursor`, `limit`) and the envelope (`items`, `nextCursor`). Never return unbounded lists.
- Filtering/sorting parameters explicitly enumerated — a free-form `filter` string is an unspecifiable contract.
- Spec payload limits and timeouts where consumers need to know them (upload size, long-poll durations).

## 7. .NET toolchain for OpenAPI

- **Publish from code:** ASP.NET Core 10 built-in OpenAPI (`AddOpenApi`/`MapOpenApi`), enriched with `WithSummary/WithDescription/Produces` metadata on Minimal APIs.
- **Generate clients:** **Kiota** (Microsoft, modern) or **NSwag** for typed C# clients; regenerate in CI when spec changes so consumers compile against the new truth.
- **Generate server stubs:** NSwag/OpenAPI Generator for controller/DTO scaffolding from an authored spec.
- **Mocks from spec:** Prism (`prism mock openapi.yaml`) or WireMock for consumer parallel work — the frontend codes against the mock on day one.
- **Runtime validation:** middleware validating requests/responses against the spec in dev/test environments catches drift the type system misses.
- **CI gates:** Spectral lint + breaking-change diff + spec-vs-code comparison. All three cheap; together they make drift structurally impossible.
