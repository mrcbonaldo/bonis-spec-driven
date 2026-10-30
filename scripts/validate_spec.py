#!/usr/bin/env python3
"""
validate_spec.py - deterministic closure-gate checks for a feature spec.md.

Turns the Requirement Closure Gate (Specify phase) into a checkable pass/fail
run BEFORE a spec is presented for confirmation, instead of trusting the model
to remember the checks. Pure standard library, zero dependencies. Operates only
on the spec.md markdown artifact - never on the target codebase - so it stays
stack-agnostic and tool-agnostic.

What it checks (heuristic markdown inspection, not a full parser):
  ERROR  - a required section is missing
  ERROR  - an acceptance criterion has no SHALL (not testable / not EARS-shaped)
  ERROR  - an Assumptions row has an empty "Chosen default" or "Rationale" cell
  ERROR  - a Requirement Traceability row has a malformed ID
  ERROR  - a Requirement Traceability row has no requirement ID
  ERROR  - a requirement ID appears in more than one Requirement Traceability row
  Once the traceability table has real IDs:
  ERROR  - an acceptance criterion has no `ID:` prefix, or names an ID not in the table
  ERROR  - a requirement in the table has no acceptance criterion
  WARN   - a requirement has an unknown Status value
  WARN   - an AC has SHALL but no recognizable EARS lead keyword
  WARN   - template placeholder rows are still present (spec not filled in)
  WARN   - open questions are not explicitly resolved

Risk tier (read from `**Risk tier:** A|B|C` near the top, or `risk: A` in frontmatter):
  WARN   - no tier declared -> the spec is treated as Tier A (safe default)
  ERROR  - Tier B/C without a `**Risk rationale:**` line
  ERROR  - Tier B/C spec mentions a Tier-A trigger (money, auth, tenant, PII, ...) and has no rationale
  WARN   - Tier B/C spec mentions a Tier-A trigger and has a rationale (confirm it addresses it)
  Tier C relaxes the shape: only Problem Statement and Out of Scope are required
  sections, at least one acceptance criterion with SHALL is required, and
  requirement IDs are optional.

Usage:
  python3 <skill-dir>/scripts/validate_spec.py [target] [--root DIR] [--strict]

  Invoke from the skill directory that ships this script (not the project root).
  target    Path to a spec.md, a feature directory, or a project root.
            Omitted -> auto-detect the single feature under <root>/.specs/features/.
  --root    Project root that contains .specs/ (default: current dir).
  --strict  Treat warnings as errors.

Exit codes: 0 pass, 1 errors found (or warnings under --strict), 2 usage error.
"""

import argparse
import os
import re
import sys

REQUIRED_SECTIONS = [
    "Problem Statement",
    "Out of Scope",
    "Assumptions & Open Questions",
    "User Stories",
    "Requirement Traceability",
]
REQUIRED_SECTIONS_TIER_C = ["Problem Statement", "Out of Scope"]

TIERS = ("A", "B", "C")
DEFAULT_TIER = "A"
TIER_LINE_RE = re.compile(r"^(?:risk\s*tier|risk)\s*:\s*([A-Za-z])\b(?!\s*\|)", re.IGNORECASE)
RATIONALE_LINE_RE = re.compile(r"^risk\s*rationale\s*:\s*(.*)$", re.IGNORECASE)
# Tier-A triggers (English + Portuguese). Matching one in a Tier B/C spec needs an explicit rationale.
TIER_A_TRIGGER_RE = re.compile(
    r"\b(payments?|pagamentos?|split|fees?|taxas?|commissions?|comiss\w*|refunds?|estornos?|reembols\w*|"
    r"payouts?|repasses?|saques?|ledger|balances?|saldos?|reconcil\w*|concilia\w*|webhooks?|idempot\w*|"
    r"authenticat\w*|authoriz\w*|autentica\w*|autoriza\w*|login|passwords?|senhas?|permissions?|permiss\w*|"
    r"tenants?|multi-?tenant|pii|lgpd|gdpr|cpf|cnpj|credit\s*card|cart[aã]o|pix|boletos?|"
    r"encrypt\w*|criptograf\w*|secrets?|money|dinheiro|prices?|pre[cç]os?)\b",
    re.IGNORECASE,
)

ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
PLACEHOLDER_RE = re.compile(r"^\s*\[.+\]\s*$")
# Lifecycle order. "deferred" = explicitly postponed out of this delivery (no task, no verification).
STATUS_VALUES = ("pending", "in design", "in tasks", "implementing", "verified", "deferred")
# An acceptance criterion starts with the requirement it belongs to: "AUTH-01: WHEN ...".
# The template's placeholder prefix "[FEAT]-01:" is recognized too, so its EARS shape is still read.
AC_TAG_RE = re.compile(r"^((?:[A-Z][A-Z0-9]*|\[[A-Z0-9]+\])-\d+)\s*:\s*(.*)$")


def _utf8_stdio():
    # Windows pipes default to the ANSI code page; artifact text is UTF-8. Never crash on output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def resolve_spec(target, root):
    """Return the path to a spec.md from a file, dir, or auto-detect."""
    if target:
        if os.path.isfile(target):
            return target
        if os.path.isdir(target):
            cand = os.path.join(target, "spec.md")
            if os.path.isfile(cand):
                return cand
            # maybe it's a project root
            return _autodetect(target)
        # Not a path: treat as a feature name under <root>/.specs/features/<name>/
        cand = os.path.join(root, ".specs", "features", target, "spec.md")
        if os.path.isfile(cand):
            return cand
        return None
    return _autodetect(root)


def _autodetect(root):
    base = os.path.join(root, ".specs", "features")
    if not os.path.isdir(base):
        return None
    features = [
        d for d in sorted(os.listdir(base))
        if os.path.isfile(os.path.join(base, d, "spec.md"))
    ]
    if len(features) == 1:
        return os.path.join(base, features[0], "spec.md")
    if len(features) == 0:
        return None
    # Ambiguous: signal the caller with the list.
    raise SystemExit(
        "validate_spec: multiple features found; pass one explicitly:\n  "
        + "\n  ".join(os.path.join(base, f, "spec.md") for f in features)
    )


def split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def section_bounds(lines, name):
    """Return (start, end) line indices for a `## name` section body."""
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^#{1,3}\s+" + re.escape(name) + r"\s*$", ln.strip()):
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^#{1,3}\s+\S", lines[j]):
            end = j
            break
    return (start, end)


def table_rows(lines, name):
    """Return (header, rows) as cell lists for the table inside a `## name` section."""
    b = section_bounds(lines, name)
    if b is None:
        return [], []
    data = [split_row(lines[i]) for i in range(*b) if lines[i].strip().startswith("|") and not is_separator(lines[i])]
    return (data[0], data[1:]) if data else ([], [])


def requirement_ids(lines):
    """Return {id: lowercase status} for the real (non-template) rows of the Requirement Traceability table.

    Shared with validate_tasks.py and validate_state.py so the three gates read requirement IDs one way.
    """
    header, rows = table_rows(lines, "Requirement Traceability")
    names = [h.lower() for h in header]
    col = names.index("status") if "status" in names else -1
    ids = {}
    for cells in rows:
        if cells and ID_RE.match(cells[0]):
            ids.setdefault(cells[0], cells[col].lower() if len(cells) > 1 else "")
    return ids


def _plain(line):
    """Strip markdown emphasis/code marks and list bullets so '**Risk tier:** A' reads as 'Risk tier: A'."""
    return re.sub(r"[*_`]", "", line).strip().lstrip("-").strip()


def risk_tier(lines):
    """Return (tier, declared, rationale) from the spec header or frontmatter.

    tier is 'A', 'B' or 'C'; an undeclared or placeholder tier ('[A | B | C]') yields
    (DEFAULT_TIER, False, ...). Shared with validate_tasks.py and validate_state.py so
    all three gates read the tier one way.
    """
    tier, declared, rationale = DEFAULT_TIER, False, ""
    for ln in lines[:60]:
        s = _plain(ln)
        m = TIER_LINE_RE.match(s)
        if m and m.group(1).upper() in TIERS and not declared:
            tier, declared = m.group(1).upper(), True
            continue
        r = RATIONALE_LINE_RE.match(s)
        if r:
            text = r.group(1).strip()
            if text and not PLACEHOLDER_RE.match(text):
                rationale = text
    return tier, declared, rationale


def spec_tier(spec_path):
    """Tier of the spec at spec_path; DEFAULT_TIER when the file is missing or undeclared."""
    if not spec_path or not os.path.isfile(spec_path):
        return DEFAULT_TIER
    with open(spec_path, encoding="utf-8", errors="replace") as f:
        return risk_tier(f.read().splitlines())[0]


def tier_a_triggers(lines):
    """Distinct Tier-A trigger words in the spec, ignoring the tier/rationale lines and Out of Scope."""
    skip = set()
    b = section_bounds(lines, "Out of Scope")
    if b:
        skip.update(range(*b))
    hits = []
    for i, ln in enumerate(lines):
        if i in skip:
            continue
        s = _plain(ln)
        if TIER_LINE_RE.match(s) or RATIONALE_LINE_RE.match(s):
            continue
        for m in TIER_A_TRIGGER_RE.finditer(ln):
            w = m.group(0).lower()
            if w not in hits:
                hits.append(w)
    return hits


def classify_ears(text):
    """Return (ok, note). ok requires a SHALL; note records the EARS pattern."""
    t = text.strip()
    low = t.lower()
    has_shall = bool(re.search(r"\bshall\b", low))
    if not has_shall:
        return (False, "no SHALL")
    kws = []
    if re.search(r"\bwhile\b", low):
        kws.append("WHILE")
    if re.search(r"\bwhen\b", low):
        kws.append("WHEN")
    if re.match(r"^\s*if\b", low) or re.search(r"\bif\b.*\bthen\b", low):
        kws.append("IF/THEN")
    if re.search(r"\bwhere\b", low):
        kws.append("WHERE")
    if len(kws) >= 2:
        return (True, "complex (" + "+".join(kws) + ")")
    if kws:
        pattern = {
            "WHILE": "state-driven",
            "WHEN": "event-driven",
            "IF/THEN": "unwanted-behavior",
            "WHERE": "optional-feature",
        }[kws[0]]
        return (True, pattern)
    if re.match(r"^\s*the\b", low):
        return (True, "ubiquitous")
    return (True, "warn: SHALL present but no EARS lead keyword")


def check(spec_path):
    with open(spec_path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    errors, warnings = [], []

    # 0. Risk tier.
    tier, declared, rationale = risk_tier(lines)
    if not declared:
        warnings.append("no '**Risk tier:** A|B|C' declared - treated as Tier A (declare it to unlock lighter gates)")
    if tier in ("B", "C"):
        if not rationale:
            errors.append(f"Tier {tier} needs a '**Risk rationale:**' line explaining why no Tier-A trigger applies")
        hits = tier_a_triggers(lines)
        if hits:
            words = ", ".join(hits[:8])
            if rationale:
                warnings.append(f"Tier {tier} spec mentions Tier-A triggers ({words}) - confirm the rationale covers them, otherwise raise to Tier A")
            else:
                errors.append(f"Tier {tier} spec mentions Tier-A triggers ({words}) without a rationale - raise to Tier A or justify")

    # 1. Required sections.
    for name in (REQUIRED_SECTIONS_TIER_C if tier == "C" else REQUIRED_SECTIONS):
        if section_bounds(lines, name) is None:
            errors.append(f"missing required section: ## {name}")

    # 2. Acceptance criteria are EARS-shaped (have a SHALL).
    in_ac = False
    acs = []  # (line number, requirement ID prefix or None) for every filled-in AC
    for i, ln in enumerate(lines, start=1):
        stripped = ln.strip()
        # The label may carry a parenthetical: "**Acceptance Criteria** (each line is one EARS pattern):".
        if re.match(r"^(?:#{1,4}\s+)?\*{0,2}Acceptance Criteria\*{0,2}(?:\s*\([^)]*\))?\s*:?\s*$", stripped):
            in_ac = True
            continue
        if in_ac:
            m = re.match(r"^\s*\d+\.\s+(.*)$", ln)
            if m:
                item = m.group(1).strip()
                tag = AC_TAG_RE.match(item)
                body = tag.group(2).strip() if tag else item
                if PLACEHOLDER_RE.match(body):
                    continue  # untouched template row
                acs.append((i, tag.group(1) if tag else None))
                ok, note = classify_ears(body)
                if not ok:
                    errors.append(f"L{i}: acceptance criterion has no SHALL (not testable): {item[:70]}")
                elif note.startswith("warn"):
                    warnings.append(f"L{i}: AC has SHALL but no EARS keyword (WHEN/WHILE/WHERE/IF or ubiquitous 'The … shall'): {item[:60]}")
            # Blank lines do not end the list: the template puts one between the label and the items.
            elif re.match(r"^#{1,3}\s", ln) or stripped.startswith("**") or stripped == "---":
                in_ac = False

    if tier == "C" and not acs:
        errors.append("Tier C spec has no acceptance criteria - list 3-5 numbered criteria with SHALL under 'Acceptance Criteria'")

    # 3. Assumptions table cells filled.
    b = section_bounds(lines, "Assumptions & Open Questions")
    if b:
        rows = [lines[i] for i in range(*b) if lines[i].strip().startswith("|")]
        data = [r for r in rows if not is_separator(r)]
        # drop the header row (first table row)
        if data:
            data = data[1:]
        template_seen = False
        for r in data:
            cells = split_row(r)
            if len(cells) < 3:
                continue
            assumption, chosen, rationale = cells[0], cells[1], cells[2]
            if PLACEHOLDER_RE.match(assumption) and PLACEHOLDER_RE.match(chosen):
                template_seen = True
                continue
            if not chosen or PLACEHOLDER_RE.match(chosen):
                errors.append(f"assumption '{assumption[:40]}' has empty 'Chosen default'")
            if not rationale or PLACEHOLDER_RE.match(rationale):
                errors.append(f"assumption '{assumption[:40]}' has empty 'Rationale'")
        if template_seen:
            warnings.append("Assumptions table still contains template placeholder rows")
        # open questions line
        oq = [lines[i] for i in range(*b) if "open questions" in lines[i].lower()]
        oq_clean = re.sub(r"[*_]", "", " ".join(oq)).lower()
        if not oq:
            warnings.append("no 'Open questions:' line in Assumptions section")
        elif not re.search(r"open questions.*:\s*none", oq_clean):
            warnings.append("open questions do not read as resolved ('Open questions: none')")

    # 4. Requirement traceability IDs.
    b = section_bounds(lines, "Requirement Traceability")
    if b:
        rows = [lines[i] for i in range(*b) if lines[i].strip().startswith("|")]
        data = [r for r in rows if not is_separator(r)]
        if data:
            data = data[1:]
        template_seen = False
        real_ids = 0
        seen = set()
        for r in data:
            cells = split_row(r)
            if not cells:
                continue
            rid = cells[0]
            if PLACEHOLDER_RE.match(rid) or "[" in rid:
                template_seen = True
                continue
            if not rid:
                rest = " | ".join(c for c in cells[1:] if c)
                if rest:
                    errors.append(f"traceability row without a requirement ID: '{rest[:60]}'")
                continue
            if not ID_RE.match(rid):
                errors.append(f"malformed requirement ID: '{rid}' (expected e.g. AUTH-01)")
            elif rid in seen:
                errors.append(f"duplicate requirement ID: '{rid}' appears in more than one traceability row")
            else:
                seen.add(rid)
                real_ids += 1
        if template_seen and real_ids == 0:
            warnings.append("Requirement Traceability has only template rows (no real IDs yet)")

    # 5. Requirement <-> acceptance criterion traceability (once the table has real IDs).
    ids = requirement_ids(lines)
    if ids:
        example = next(iter(ids))
        covered = set()
        for line_no, tag in acs:
            if tag is None:
                errors.append(f"L{line_no}: acceptance criterion has no requirement ID prefix (expected '{example}: WHEN ...')")
            elif tag not in ids:
                errors.append(f"L{line_no}: acceptance criterion names {tag}, which is not in Requirement Traceability")
            else:
                covered.add(tag)
        for rid, status in ids.items():
            if rid not in covered:
                errors.append(f"requirement {rid} has no acceptance criterion (prefix at least one AC with '{rid}:')")
            if status not in STATUS_VALUES:
                warnings.append(f"requirement {rid} has unknown status '{status}' (expected: {', '.join(STATUS_VALUES)})")

    return errors, warnings


def main(argv=None):
    _utf8_stdio()
    p = argparse.ArgumentParser(prog="validate_spec.py", description="Closure-gate checks for a feature spec.md.")
    p.add_argument("target", nargs="?", default=None)
    p.add_argument("--root", default=".")
    p.add_argument("--strict", action="store_true")
    args = p.parse_args(argv)

    spec = resolve_spec(args.target, args.root)
    if not spec:
        print("validate_spec: could not locate a spec.md. Pass a path or run from the project root.", file=sys.stderr)
        return 2

    errors, warnings = check(spec)
    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    fail = errors or (warnings and args.strict)
    tier = spec_tier(spec)
    print(f"\nvalidate_spec: Tier {tier} - {len(errors)} error(s), {len(warnings)} warning(s) in {spec}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
