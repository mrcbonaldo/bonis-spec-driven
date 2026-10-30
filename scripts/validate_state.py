#!/usr/bin/env python3
"""
validate_state.py - deterministic completion gate for a feature.

The skill's strongest invariant is "the Verifier is always-on, never prompted;
a feature is not done until validation.md reports PASS." That is prose the model
must remember. This turns it into a checkable pass/fail the closing step runs
automatically, so declaring a feature done without a real Verifier report fails
loudly instead of slipping through.

It does NOT merely check that validation.md exists - a report that exists but is
empty, still holds the template placeholder, or has no evidence would pass a
shallow existence check while proving nothing. This gate requires a real,
filled verdict plus at least one file:line evidence citation.

When the feature's spec.md has requirement IDs, a PASS report must also close
the traceability chain for every requirement that is not Deferred:
  - it has a Verified row in validation.md's `Requirement Traceability Update`
  - it has a file:line evidence row in the `Spec-Anchored Acceptance Criteria` table
  - spec.md's traceability table marks it Verified
and validation.md names no requirement that spec.md does not define.

Risk tier (read from spec.md; missing = Tier A):
  Tier A/B - everything above applies.
  Tier C   - no Verifier runs, so validation.md is not required. If one exists,
             its verdict must not be FAIL or an unfilled placeholder.

Operates only on the .specs/ markdown artifacts (stack- and tool-agnostic). No
dependencies. Run from the project root (the dir that contains .specs), or pass
--root. Meant to be invoked by the skill as the closing gate of Verify, the
same way lessons.py is invoked at distillation - not a manual step.

Usage:
  python3 <skill-dir>/scripts/validate_state.py [feature]
  python3 <skill-dir>/scripts/validate_state.py

  Invoke from the skill directory that ships this script (not the project root).
  Pass --root when cwd is not the project that contains .specs/.

Exit codes: 0 ok, 1 a completed feature is missing a real PASS report,
            2 usage error.
"""

import argparse
import os
import re
import sys

# Read requirement IDs exactly as the spec gate does. Never leave __pycache__ in the skill directory.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_spec import ID_RE, requirement_ids, spec_tier, table_rows  # noqa: E402

# A file:line citation: a path with an extension, then :<line>. e.g. src/a.ts:42
EVIDENCE_RE = re.compile(r"[\w./-]+\.[A-Za-z0-9]+:\d+")
REQ_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")


def _utf8_stdio():
    # Windows pipes default to the ANSI code page; artifact text is UTF-8. Never crash on output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def _feature_dirs(root):
    base = os.path.join(root, ".specs", "features")
    if not os.path.isdir(base):
        return base, []
    dirs = [
        d for d in sorted(os.listdir(base))
        if os.path.isdir(os.path.join(base, d))
    ]
    return base, dirs


def _verdict(text):
    """Return 'pass', 'fail', 'unfilled', or None from a validation report."""
    # Look at the '## Validation' heading first, then a '**Result**' line.
    lines = text.splitlines()
    candidates = [
        ln for ln in lines
        if re.search(r"^#{1,4}\s*validation\b", ln.strip(), re.IGNORECASE)
        or re.search(r"\*{0,2}result\*{0,2}\s*:", ln.strip(), re.IGNORECASE)
    ]
    hay = " ".join(candidates) if candidates else text
    has_pass = re.search(r"\bPASS\b", hay) is not None
    has_fail = re.search(r"\bFAIL\b", hay) is not None
    if has_pass and has_fail:
        # Both present on the verdict line = unfilled template "[PASS | FAIL]".
        return "unfilled"
    if has_pass:
        return "pass"
    if has_fail:
        return "fail"
    return None


def _appears_complete(fdir):
    """Conservative completeness heuristic for the cross-check mode.

    A feature 'appears complete' if it already has a validation.md, or if it has
    a tasks.md with at least one task and no unchecked '- [ ]' boxes left. When
    the signal is ambiguous (no tasks.md, Tasks phase skipped), returns False so
    an in-flight feature is never falsely flagged.
    """
    if os.path.exists(os.path.join(fdir, "validation.md")):
        return True
    tasks = os.path.join(fdir, "tasks.md")
    if not os.path.exists(tasks):
        return False
    body = open(tasks, encoding="utf-8", errors="replace").read()
    if not re.search(r"^#{2,4}\s+T\d+\s*:", body, re.MULTILINE):
        return False
    if re.search(r"^\s*-\s*\[\s\]", body, re.MULTILINE):
        return False  # unchecked box remains -> still in progress
    return True


def _check_feature(fdir, name):
    """Return list of error strings for one feature (empty = pass)."""
    errors = []
    tier = spec_tier(os.path.join(fdir, "spec.md"))
    vpath = os.path.join(fdir, "validation.md")
    if tier == "C":
        if not os.path.exists(vpath):
            print(f"validate_state: {name} is Tier C - no Verifier report required (gate + self-check close it).")
            return errors
        verdict = _verdict(open(vpath, encoding="utf-8", errors="replace").read())
        if verdict == "fail":
            errors.append(f"{name}: validation.md verdict is FAIL - fix the gaps before marking done")
        elif verdict == "unfilled":
            errors.append(f"{name}: validation.md verdict is still the template placeholder '[PASS | FAIL]' - fill it or delete the file (Tier C needs no report)")
        return errors
    if not os.path.exists(vpath):
        errors.append(
            f"{name}: no validation.md - a Tier {tier} feature is not done until the Verifier "
            f"writes it (author != verifier). Dispatch validation before marking done."
        )
        return errors
    text = open(vpath, encoding="utf-8", errors="replace").read()
    verdict = _verdict(text)
    if verdict is None:
        errors.append(f"{name}: validation.md has no PASS/FAIL verdict (a prose-only report does not count)")
    elif verdict == "unfilled":
        errors.append(f"{name}: validation.md verdict is still the template placeholder '[PASS | FAIL]' - not filled")
    elif verdict == "fail":
        errors.append(f"{name}: validation.md verdict is FAIL - route the ranked gaps to fix tasks, then re-verify (feature is not done)")
    if verdict == "pass" and not EVIDENCE_RE.search(text):
        errors.append(f"{name}: validation.md is PASS but cites no file:line evidence - evidence-or-zero not satisfied")
    if verdict == "pass":
        errors += _traceability_errors(fdir, name, text.splitlines())
    return errors


def _is_verified(cell):
    return bool(re.search(r"\bverified\b", cell, re.IGNORECASE)) and not re.search(r"\bnot\b|needs fix|❌", cell, re.IGNORECASE)


def _traceability_errors(fdir, name, report):
    """A PASS report must verify, with file:line evidence, every requirement spec.md does not defer."""
    spec = os.path.join(fdir, "spec.md")
    if not os.path.exists(spec):
        return []
    ids = requirement_ids(open(spec, encoding="utf-8", errors="replace").read().splitlines())
    if not ids:
        return []  # brief spec without requirement IDs: nothing to trace

    header, rows = table_rows(report, "Requirement Traceability Update")
    names = [h.lower() for h in header]
    col = names.index("new status") if "new status" in names else -1
    verdicts = {cells[0]: cells[col] for cells in rows if len(cells) > 1 and ID_RE.match(cells[0])}

    evidenced = set()
    _, ac_rows = table_rows(report, "Spec-Anchored Acceptance Criteria")
    for cells in ac_rows:
        row = " | ".join(cells)
        if EVIDENCE_RE.search(row) and "❌" not in row:
            evidenced.update(r for r in REQ_ID_RE.findall(row) if r in ids)

    errors = []
    for rid, status in ids.items():
        if status == "deferred":
            continue
        if rid not in verdicts:
            errors.append(f"{name}: {rid} is missing from validation.md's Requirement Traceability Update - every requirement needs a verdict")
        elif not _is_verified(verdicts[rid]):
            errors.append(f"{name}: {rid} is not Verified in validation.md ('{verdicts[rid]}')")
        if rid not in evidenced:
            errors.append(f"{name}: {rid} has no file:line evidence row in validation.md's Spec-Anchored Acceptance Criteria table")
        if status != "verified":
            errors.append(f"{name}: spec.md traceability still shows {rid} as '{status}' - update it to Verified")
    for rid in verdicts:
        if rid not in ids:
            errors.append(f"{name}: validation.md lists {rid}, which is not in spec.md")
    return errors


def _resolve(root, feature):
    base, dirs = _feature_dirs(root)
    if not os.path.isdir(base):
        print(f"validate_state: no {base} directory - nothing to check.")
        return []
    if feature:
        fdir = feature if os.path.isdir(feature) else os.path.join(base, feature)
        if not os.path.isdir(fdir):
            print(f"validate_state: feature not found: {feature}", file=sys.stderr)
            raise SystemExit(2)
        return [(fdir, os.path.basename(os.path.normpath(fdir)))]
    if len(dirs) == 1:
        return [(os.path.join(base, dirs[0]), dirs[0])]
    if not dirs:
        print("validate_state: no features under .specs/features/ - nothing to check.")
        return []
    # Cross-check mode: only features that appear complete.
    picked = [(os.path.join(base, d), d) for d in dirs if _appears_complete(os.path.join(base, d))]
    if not picked:
        print("validate_state: no completed feature detected (all in progress) - nothing to gate.")
    return picked


def main(argv=None):
    _utf8_stdio()
    p = argparse.ArgumentParser(prog="validate_state.py", description="Deterministic completion gate: a done feature must have a real PASS validation report.")
    p.add_argument("feature", nargs="?", default=None, help="Feature dir or name (default: sole feature, else cross-check all completed)")
    p.add_argument("--root", default=".", help="Project root containing .specs/ (default: current dir)")
    args = p.parse_args(argv)
    root = os.path.abspath(args.root)

    targets = _resolve(root, args.feature)
    all_errors = []
    for fdir, name in targets:
        all_errors += _check_feature(fdir, name)

    for e in all_errors:
        print(f"  ERROR {e}")
    n = len(all_errors)
    checked = ", ".join(name for _, name in targets) or "(none)"
    print(f"\nvalidate_state: {n} error(s) across [{checked}]")
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
