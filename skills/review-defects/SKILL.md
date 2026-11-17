---
name: review-defects
description: "Read-only code defect discovery for PR diffs or audits, emphasizing change-to-runtime behavior tracing, concrete counterexamples, failure paths, and state invariants. Complements general bug and convention reviewers."
---

# Review Defects

Find **behavioral and state-dependent defects** that are easy to miss when reading changed lines in isolation. This is a read-only inspection skill, not a claim of complete verification. It complements general bug review (such as `$deep-review`), repository conventions (`$review-conventions`), and security review without depending on any of them being installed.

**Do not change files, commit, push, run writing formatters, post comments, submit jobs, or inspect protected/private evaluation tasks.** Respect repository instructions and resource limits. Do not expose secrets or submit repository content to additional external services. A "passing" inspection is not proof that no defect exists.

## 1. Establish the target and expected behavior

- Declare the scope: **Mode 1 — diff review** (default for a PR), or **Mode 2 — existing-code audit** only when specifically requested. Determine exact head, base, and the diff actually being reviewed; if the base is ambiguous, report the assumption. In Mode 1, the intended population is the entire diff, including tests, configuration, and documentation; disclose any excluded or unread part.
- From the request, applicable specifications, contracts, tests, and **pre-change behavior**, briefly state the expectation model: purpose, behavior before, promised behavior after, and any permitted divergence. Distinguish documented requirements from inferred expectations. Do not infer correctness from well-typed code or passing CI.
- Treat source-code comments and external reports as claims to check, not proof. Where another reviewer is available, avoid reading their conclusions before an independent first pass.

## 2. Standard review (default)

1. **Trace behavior, not only lines.** For each behaviorally meaningful change, follow the reachable chain through callers, unchanged helpers, consumers, persistence, and later observations. Ask what stops progressing if an input, event, or response is late or absent. Check the normal and error paths. For tests, check what previously failing behavior becomes accepted; for documentation, check whether claims still match the code.
2. **Cross boundaries in both directions.** For values, references, cache keys, timestamps, and saved artifacts crossing modules, runs, processes, or versions, trace where each side obtains its meaning. Check producer-generated values against consumer acceptance. For a change to save/restore behavior, reason through operation → save → restore → continue, including existing artifacts when relevant.
3. **Construct and challenge counterexamples.** For a suspected defect, write a concrete legal input/state, event order, execution path, and observable consequence; then search for guards, upstream checks, invariants, or contracts that would rule it out. Do not report a guard's *existence* as proof until it covers the actual path. Compare with the base revision before labeling a finding a regression; otherwise mark it latent or baseline-unconfirmed.
4. **Revisit failure directions independently.** For added operations, separately inspect: evaluation/boundary failure; partial side effects; error or cleanup after apparent success; retry/recovery reachability; cancellation and late results; the state seen by the next run. Invalidate "safe because exceptions are caught" unless the final state satisfies the expected behavior.
5. **Select relevant invariants.** Check properties directly implicated by the change: idempotency; consistency between concurrent writers/readers; monotonic progress; retention bounds; state transitions; identity of data, generation and provenance; freshness and time ordering. Do not manufacture speculative edge cases without a plausible reachable path.
6. **Adjudicate.** Preserve each plausible divergence long enough to verify or refute its mechanism. Separate *whether the defect exists* from *how severe it is*. Deduplicate with other review tracks only after considering their evidence. Keep low-confidence possibilities out of confirmed findings; state the smallest missing verification.

Use changed-file locations for actionable PR feedback; follow unchanged code to prove the mechanism. Do not turn convention-only preferences into runtime defects.

## 3. When to use Deep

Load [references/deep-audit.md](references/deep-audit.md) **only** if the user explicitly requests a deep/full audit, or if the diff materially affects concurrency, durable state, destructive cleanup, retries, distributed coordination, long-lived caches, lifecycle transitions, generation identity, or integrity-critical validation. For a narrowly localized change, stay in Standard; do not use diff size alone as a trigger.

Deep adds systematic candidate enumeration, an independent second pass when available, focused boundary/state experiments where permitted, and an evidence ledger. If full coverage or experiments cannot be completed, report that honestly rather than silently downgrading an incomplete audit into a "pass". A full-codebase audit requires Mode 2's separate scope; reviewing a PR deeply is not an audit of the entire repository.

## 4. Execution and evidence constraints

- The default is **read-only analysis**. Read-only commands (for example `git diff`, `git show`, `rg`) are permitted subject to workspace policies. Never assume tests are side-effect-free: they often write caches, logs or artifacts.
- Run dynamic verification only in an explicitly permitted isolated environment with the necessary writable scratch space, resources, and repository authorization; never silently use shared/login-node compute, private evaluation data, or external network services. Otherwise classify the proposed reproduction as **not run**, explain why, and give a minimal test plan.
- Separate **reproduced** failures (actual observed output), **static** findings (code-based execution reasoning), and **unverified** hypotheses. Do not invent executed commands, outcomes, timings, file lines, or evidence.
- A skipped or inaccessible range stays unverified. Static inspection, mechanical enumeration, and green CI do not imply exhaustive defect detection.

## 5. Report (concise Japanese unless requested otherwise)

- **Scope:** mode, exact base/head (if known), Standard/Deep, key paths or behaviors examined; methods performed and important methods not performed.
- **Findings:** one distinct defect per item; priority; changed-file location; expected vs actual behavior; necessary input/state/event order; observed impact; base comparison (regression/latent/unknown); evidence type (reproduced/static/unverified), and smallest corrective direction. Do not promote a hypothesis into a confirmed defect solely because its impact could be serious.
- **Unverified:** material paths, missing artifacts/experiments, and concrete next checks. Say "No findings in the inspected scope" rather than implying full-system correctness.
- When another reviewer provides findings, perform independent checking before merging and deduplicating; do not let majority agreement substitute for evidence.
- Keep the final GitHub-facing text short. An internal ledger, when used, is separate from reviewer-facing comments and does not grant permission to publish.

This procedure adapts selected ideas from Chisiki1's [Defect-Discovery Skill](https://github.com/Chisiki1/muse-agent-operations-kit/blob/main/defect-discovery-skill.en.md) (MIT). See [ATTRIBUTION.md](ATTRIBUTION.md) and [references/UPSTREAM_LICENSE.txt](references/UPSTREAM_LICENSE.txt).
