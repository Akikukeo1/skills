# Deep audit extension for review-defects

Read this file only after choosing **Deep** in `SKILL.md`. These are additional inspection activities, **not** a requirement to run every possible check on an ordinary PR. Record which were used. They do not replace the Standard behavior trace or independent adjudication.

## 1. Define the population and ledger

- **Mode 1 (diff):** enumerate every changed path and changed function, including tests, configuration and docs. Work outward to relevant unchanged dependencies. Use mechanical listing where possible (for example `git diff --name-only BASE...HEAD`, `git diff --function-context BASE...HEAD`, and language-appropriate AST/grep queries). An enumeration is a *lower bound*; it can miss dynamically registered code, generated files, and indirect dependencies.
- **Mode 2 (full codebase):** enumerate the entire requested codebase, tracing core workflows end to end and surveying components by area. Do not describe a diff-only pass as full-codebase inspection.
- Record a concise inspection ledger, in memory or an authorized output artifact: `location | expected contract | forward path | attempted counterexample | evidence | conclusion | unverified`. Mark understanding depth per area (`full`, `focused`, `partial`, `shallow`). `Shallow` is unverified, not cleared.
- For every changed function implicated by the audit, capture its input domain, return/error contract, side effects, and relevant boundary inputs. Also note the contracts of unchanged dependencies it invokes. Do not interpret a documented contract as proof of enforcement.

## 2. Enumerate candidates, then verify

Enumerate **locations first**, then assess each one in its code context. Use tool output, not recollection, to establish which instances you inspected. Consider:

| Class | Concrete scenario to try |
| --- | --- |
| Progress / retry | A required response never arrives or a normal update prevents a retry condition from becoming true |
| Partial failure | A write, rename, cleanup, or external call fails after earlier side effects |
| Validation / numeric | Empty, missing, boundary, non-finite, overflow, incompatible type or unexpected units |
| State transition | An event arrives in a state where no transition or recovery path is defined |
| Concurrent operation | State changes between observation and action; lock scope omits an actual writer |
| Idempotency | A retry, duplicate callback or stale completion applies effects twice |
| Persistence | A same-version or older valid artifact is rejected or restored with changed meaning |
| Lifetime / capacity | A cache, log, set or ledger retains entries beyond their needed lifetime without a bound |
| Temporal consistency | Old and new generations, timestamps, or partially formed results are combined |
| Evidence / provenance | A result or hash matches current bytes but no longer refers to the claimed execution |
| Display / tests | UI, docs, or assertions say a condition holds that the executable behavior does not guarantee |

Do not call the matrix exhaustive coverage: the main unit is the **change × surrounding behavior** chain, and these prompts only help find missed cases.

For each relevant candidate, ask which *reachable* state or event sequence makes the guarantee false. Confirm assignment/binding and value origins; check boundary acceptance against what the producer can actually emit. For a retained set, locate both insertions and removals, or state that removal/boundedness has not been established. For a verifier or lock, derive the **necessary target set independently** from actual reads/writes and compare with what is protected/checked. Do not close a candidate just because a helper exists.

## 3. Read a second way

For important changes, use distinct independent passes where available, ideally without sharing first-pass conclusions:

- **Behavior/consumer:** What does the downstream user or processing step require?
- **Failure/operator:** What remains after mid-operation failure, restart, retry or delay?
- **Data/provenance:** Are identifiers, artifacts, generations and observations linked to the same object and run?

The integrator rechecks disputed findings in real code, merges equivalent failure mechanisms, and attempts to disprove affirmative conclusions. More subagents are not inherently better: choose bounded, complementary tasks; do not require 20 workers. When independence is not available, explicitly label the second pass as a *different viewpoint in the same context*.

## 4. Validate dynamically when permitted

Choose experiments that force the suspected failure, not random trial counts:

- Exercise exactly-before/at/after boundaries and missing/corrupt configurations in a safe fixture.
- Inject a failed mandatory operation after earlier writes; check remaining state and next-run recovery.
- Verify producer → save → reader → continue, including older valid artifacts, without damaging real user data.
- Force the race ordering or late event necessary for the hypothesis; "not seen in N runs" is not a refutation.
- For retries, synthesize the failed state and execute successive normal cycles; a stored retry flag alone does not establish reachability.

State the *oracle* (expected invariant and observable signal), exact reproduced effect and steps. If the environment is read-only or the test could mutate project state, require additional authorization rather than running it. No live credentials, costly cluster jobs, private evaluation tasks, or untrusted scripts merely to increase coverage.

## 5. Finish with bounded claims

- Record inspected population and exclusions, plus enumeration blind spots.
- Classify each finding as **reproduced / static / unverified**, and **new regression / pre-existing / baseline unknown**.
- Record relevant invariants tested or reasoned about and the methods not executed.
- For unverified findings, name the minimal missing artifact or experiment. Confirmations based only on code reading remain static even after careful tracing.
- Distinguish confirmed defects from stylistic or future-maintainability suggestions; route those to the appropriate review track.
- Give the concise user-facing findings first; keep the ledger as audit evidence, not as a wall of GitHub inline comments.

Adapted from Chisiki1's Defect-Discovery Skill. Its source, licensing and adaptation notice are recorded in [../ATTRIBUTION.md](../ATTRIBUTION.md).
