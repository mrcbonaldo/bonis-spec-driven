# Project Constitution (optional)

**File:** `docs/CONSTITUTION.md` at the project root.

The project owns this file. When it exists, its rules are invariants every phase must respect: architectural decisions, security constraints, mandatory conventions, domain invariants, engineering principles. When it does not exist, skip everything here and continue normally.

---

## Rules

1. **Detect.** Check whether `docs/CONSTITUTION.md` exists. Absent → no-op, no warning, no scaffolding.
2. **Read when relevant.** Read it completely before Specify, Design, and Implement. Re-read it on resume.
3. **Respect it.** The Constitution outranks every other artifact this skill produces or reads.
4. **Never contradict it silently.** Every conflict is reported explicitly (format below).
5. **Never modify it.** Do not edit, append to, reformat, or "fix" the file. Only the user changes it.
6. **Never invent rules.** Apply what the file says. Do not infer unstated rules or extend a rule beyond its wording.

---

## Precedence

```
docs/CONSTITUTION.md  >  .specs/STATE.md active decisions (AD-NNN)  >  design.md  >  tasks.md
```

A design can supersede an `AD-NNN` decision (see [memory.md](memory.md)). Nothing in `.specs/` can supersede the Constitution. Only the user changing the file can.

---

## Where each phase checks it

| Phase | Check |
| ----- | ----- |
| Specify | Every requirement, acceptance criterion, and assumption conforms. A requested behavior that violates a rule is a conflict, not a requirement. |
| Design | The architecture, components, data models, and new `AD-NNN` entries conform. A decision cannot supersede a Constitution rule. |
| Implement | The task's planned change conforms before any code is written. A rule discovered mid-task that the task would break stops the task. |
| Verify | The Code Quality Check confirms the changed files conform (one row in [validate.md](validate.md)). |

---

## Conflict report

When a conflict appears, stop work on the conflicting item and report it in chat:

```markdown
**Constitution conflict**

- **Rule**: `docs/CONSTITUTION.md` - [section heading or quoted rule]
- **Conflicting item**: [requirement ID / design element / task ID / user request]
- **Why it conflicts**: [one sentence]
- **Options**: (1) change the item to conform; (2) you update the Constitution yourself
```

Then wait for the user. Do not proceed with the conflicting item until the user resolves it.

**Record the resolution** where the phase records decisions:

- Specify → a row in the spec's `Assumptions & Open Questions` table.
- Design → a row in the design's `Tech Decisions` table.
- Implement → a `// SPEC_DEVIATION` marker is NOT acceptable for a Constitution conflict. Stop the task and route the change back to the spec or design.

---

## Tips

- **Absent is normal** - most projects have no Constitution; skip silently
- **Quote, don't paraphrase** - cite the exact rule when reporting a conflict
- **Read-only, always** - the agent never writes to `docs/CONSTITUTION.md`
- **Generic by design** - this skill ships no project rules; every rule comes from the project's own file
