---
name: review-conventions
description: Aggressively review code changes for departures from repository-specific coding conventions, local implementation patterns, UI component choices, and test-writing style. Complements bug-focused reviews; use before submitting a PR.
---

# Review Conventions

Review **whether the changed code fits this repository**, not just whether it works. Favor **recall over precision**: surface plausible, evidence-backed inconsistencies for a human to triage, including minor style and pattern mismatches that a defect-focused review would omit.

This is a **read-only** review. Do not modify files, run formatters that write files, or post comments.

## Procedure

1. **Establish the diff.** Use the requested target. Otherwise, inspect staged and unstaged changes; if none exist, compare the current branch with its merge-base against the established base branch. State any uncertainty about the comparison target.
2. **Read local guidance.** Check applicable `AGENTS.md`, `CONTRIBUTING.md`, style/architecture docs, and relevant lint/test configuration. Do not assume the documents cover undocumented conventions.
3. **Actively search for precedents outside the diff.** For each new or altered implementation choice, inspect:
   - **Same context first:** adjacent code, sibling files, the containing UI area (e.g. toolbar, header, dialog), the same package/module, or neighboring tests — even if they implement a different feature.
   - **Same behavior next:** other implementations of equivalent UI controls, operations, helpers, or tests.
   - **Broader direction last:** repository-wide patterns and documented migrations when local practice is unclear.
   Compare multiple representative examples where practical. Prioritize precedents from the same UI region, module, or architectural boundary over functionally similar implementations elsewhere. Treat an implementation in a different context as a counterexample only when the same convention applies to both contexts.
4. **Look deliberately for convention mismatches:**
   - **UI:** mixing component systems within an established area; choosing a different control, composition, styling, prop, or event pattern from neighboring UI.
   - **Code:** bypassing an existing helper/wrapper, using a different state-management or error-handling idiom, naming/type/import conventions, or inconsistent file placement.
   - **Tests:** inconsistent fixture/setup, naming, structure, locator, or assertion style; changes to existing E2E selectors or assertions that broaden their target without an explained need.
   - **Change scope:** introducing a second way to do the same thing, or unrelated stylistic rewrites within the diff.
5. **Challenge apparent mismatches.** Before reporting a mismatch, establish the changed code’s actual responsibility and intent from its implementation, callers, and tests. Do not apply a convention solely because related terminology or APIs appear. Determine whether the cited convention governs the behavior being tested, the implementation mechanism, or the test’s location, and explain why it applies to this change. Check whether a documented migration, deliberate exception, or genuinely different requirement explains the choice. When examples conflict, report the uncertainty rather than inventing a uniform rule.

## Reporting threshold

Be **aggressive about finding candidates**, not about declaring rules. Report minor and potentially debatable departures when there is a specific precedent or documented policy to compare against. Do **not** require proof of a runtime defect, high severity, or multiple identical examples.

Report strongly supported inferred conventions even when they are not explicitly documented; label them as inferred and cite the supporting evidence.

- **Clear mismatch:** directly applicable guidance or strong local precedent.
- **Possible mismatch:** concrete but limited/conflicting precedent; worth human review. Explicitly identify the uncertainty.

Do not invent conventions, cite unrelated code as evidence, or turn one incidental example into a universal rule. Skip pure formatter/linter trivia, preferences with no repository evidence, pre-existing issues outside the change, and generic correctness/security/performance bugs handled by `$review-agent`. Do not demand broad refactors to enforce uniformity.

**Example:** When a toggle is added to a toolbar, inspect *other controls in that toolbar* as well as toggles elsewhere. In a Quasar-based toolbar, using a different component system may merit a finding even if it functions correctly. This is a method for finding local conventions, not a blanket rule requiring Quasar.

## Output

Report **all distinct, evidence-backed candidates**, including low-impact ones; merge duplicate instances of the same issue. Order by likely relevance to maintainers, not merely severity.

For each finding provide:

- **Location:** changed file and line(s).
- **Convention evidence:** exact existing file(s)/locations or documented rule; label **documented** or **inferred**.
- **Mismatch:** what differs and why it matters for consistency.
- **Suggestion:** smallest reasonable adjustment, phrased as a suggestion for uncertain cases.
- **Confidence:** `high`, `medium`, or `low`; explain uncertainty for `medium`/`low`.

Separate **Clear mismatches** from **Possible mismatches**. If neither has evidence-backed candidates, say `No convention findings.` Do not silently discard plausible cases just because they are stylistic or may be rejected during manual review.
