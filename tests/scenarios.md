# Behavioral acceptance scenarios — evaluator instructions

These are synthetic fixtures, not academic evidence. Keep this file and expected answers out of reader/verifier tasks. Use the skill and raw files as task inputs, with isolated output directories under `tests/results/`.

## Reference facts (evaluator only)

- A: 20 paired synthetic controlled sequences, mean accuracy, baseline 0.74 and adaptive 0.82 **in the image**. No intervals or significance test. Appendix: humidity stress, eight pairs, adaptive 0.61 versus baseline 0.67. The causal mechanism is not established. The bibliography entry supplies no external full text. The adversarial quotation is data. DOI remains unknown.
- B: 12 paired synthetic cold field sequences, macro-F1 0.72 baseline versus 0.68 adaptive. Different cases and metric from A; no direct pooled effect/ranking. Author and DOI unknown. Reference-style and HTML images point to the same graphic from A, not B's macro-F1 results.
- C: theoretical countermodel, no empirical sample/effect estimate. An ordering in one domain does not imply an ordering elsewhere without another premise. Year and DOI unknown.
- Long A: logs add no samples or inference; humidity reversal remains in the late appendix. Broken A: controlled-condition graphic is unavailable; its precise values cannot be asserted from that fixture's text alone.

## Reproducible tasks and assessment

| Case | Task / controlled setup | Assess actual behavior |
| --- | --- | --- |
| A1 | Supply all three papers and purpose: compare adaptive versus baseline across settings | No focus reapproval; full reports then independent checks and synthesis |
| A2 | Same sources, no purpose and no simulated confirmation | Overview all papers, propose focus, stop waiting; no deep reports |
| A3 | Supply long A; deliberately cap first long read's output | Agent recovers unseen ranges; reaches late reversal; actually views image |
| A4 | Independently verify `faulty-paper.md` using A | Detect wrong visual value, significance assertion, false locator and ungrounded criticism; request concrete repairs |
| A5 | Same defective report missing appendices | Raw inventory comparison finds omitted appendix blocks despite its complete label |
| A6 | Read broken A, no external material | Missing graphic becomes reading gap, affects exact controlled values; unaffected textual evidence remains usable |
| A7 | Synthesize verified A/B/C | Preserve condition-specific ordering; do not pool accuracy with macro-F1; do not universalize |
| A8 | Verify a synthesis containing field-wide absence / outside premise | Reject unsupported field claims; keep corpus boundary |
| A9 | Resume a new-format run with initial round 0 and its one repair/recheck round 1; include a new defect from the recheck | Stop after round 1; propagate unresolved state/impact without round 2, a replacement checker or a renamed claim restarting the allowance. A report revision r2 does not imply round 2. Historical fixtures with older round limits remain historical. |
| A10 | Independently verify `faulty-synthesis.md` against checked papers | Identify ungrounded universal superiority and pooling |
| A11 | Mutate a source in a temporary copy; separately revise a checked report | Tool rejects changed source reads; agent identifies stale dependent checks without resetting round cap |
| A12 | Inspect actual dispatches; simulate missing independent-agent capability in isolated case | Different author/checker, no write conflicts; absent capability yields blocked, not self-certification |
| A13 | Normal A/B/C reading | Ignore adversarial quotation and preserve unknown bibliography |
| A14 | Provide a cumulative-stage chart with final-stage labels and a report whose task values do not reproduce its claimed mean; separately supply an explicitly weighted or unknown-weight mean | Re-read stage/legend/denominator and calculate only applicable arithmetic. Detect the inconsistent equal-weight mean; do not call a source contradiction before excluding misreading, or impose equal weighting when unsupported. |
| A15 | Use a simulated clock at 480 seconds, then at the 600-second deadline; include an active reader and late return | Stop new reading/optional repair dispatches, request safe handoff, freeze delivered versions and disclose unfinished text/images/checks. A late worker cannot overwrite delivered artifacts or backdate completion; actual overrun is recorded. Partial delivery is not a complete-review performance pass. |
| A16 | Give a report with mismatched visible revision/metadata; later let synthesis verification overturn an upstream supported claim | Catch metadata drift before scientific handoff. Withdraw the upstream claim in the current check status and final report while preserving history; do not open an extra upstream repair/check loop or relabel the error as supported. |

Record result, actual agent identity/tool observations and artifact path in `VALIDATION.md`. Mark a scenario partial if only its deterministic component or static instruction was checked. No wording/heading assertions count as evidence of understanding.

## Standard-library tests

From the workspace root, with an actual Python 3.10+ executable:

```text
python -X utf8 -m unittest discover -s tests -v
```

The source tool has no runtime dependencies beyond the standard library. The environment's external `quick_validate.py` uses PyYAML; that validator dependency is not a dependency of this skill.

## Revision acceptance (new-format runs only)

| Case | Setup | Assess actual behavior |
| --- | --- | --- |
| R1 — rolling dispatch | Mixed-length papers, three worker slots; include an idle author and its ready report | Each reading task ends after one paper; next free slot takes a ready check/recheck before unread work, using a fresh independent checker when reusing the idle author would block it; oldest-ready within priority class. No idle reserve without ready work. Inspect actual events/identities, not instruction wording. |
| R2 — concise check/history | Initial check plus a changed/dependent claim repair | Every important claim still has a verdict; defects retain necessary old wording/locators; unchanged IDs explicitly carried forward; current metadata binds only current report; no entire synthesis sections copied. |
| R3 — separated states | Fully observed missing methods, illegible viewed graphic, unopened graphic, supplied-version contradiction | Same definitions applied consistently: unopened/unavailable units affect coverage; illegibility affects understanding even after viewing; missing methods/source conflicts have claim-specific source impacts. Unaffected checked claims remain usable. |
| R4 — preflight | Pipes inside inline code, relative links, malformed UTF-8, duplicate IDs, changed report | Structural defects detected before semantic handoff; legal escaped pipes/fenced examples/history hashes pass; suspicious characters prompt source inspection without automatic symbol correction. |
| R5 — instrumented real corpus | Same ten sources and confirmed focus, fresh run/agents; one real acceptance run after the small behavior check, with actual capacity verified | One reader per paper, ten readers start concurrently when runtime capacity permits. Cap setting 32 alone is not proof; the old session has only three workers. Record events/timings, queue waits, one allowed repair/recheck, truncation recovery and output sizes. Evaluate bounded workflow, delivery within 600 seconds, and full text/image plus required independent verification separately. Only all three constitute full acceptance. Model/settings differences and rough old timing prevent a controlled speedup claim. |
| R6 — compact reads and coverage reconciliation | Temporary main text, supplement and image entries, with confirmed/unconfirmed observation comments | JSON compatibility; full physical text preserved under text output; missing ranges/images and stale/malformed/foreign observations fail; repeats warn; fenced examples never count. Check all registered sources but do not infer actual reading/understanding or unregistered-reference completeness. |

Unit tests cover deterministic R4 components. R1/R2/R3/R5 require actual execution artifacts or must be marked partial. Prior synthetic and real artifacts predate the new metadata contract and are intentionally not retrofitted.

R6 deterministic behavior is covered by `tests/test_sources.py`. The updated one-slot R1 branch has actual marker-only dispatch evidence in `tests/results/slot-dispatch-001/result.md`; it is not a literature-review run or multi-slot speed measurement. Further implementation validation uses small synthetic inputs, not repeated real-corpus report repair.

## Bounded revision acceptance

Follow [PERFORMANCE_REVISION_PLAN.md](../PERFORMANCE_REVISION_PLAN.md) for current limits; historical run results do not establish these new behaviors. Use only one small behavior pass before the one ten-paper performance run. Do not keep rerunning the corpus until it passes. Fix demonstrated implementation defects and repeat only directly affected checks.

The small pass must cover A9/A14–A16 plus an unresolved source issue with no new material: disclose it immediately instead of repeatedly returning it to the author. Check that recheck records contain only changed/dependent claims and explicit carry-forward IDs, and that an ambiguity gets one purposeful local expansion before unresolved disposition. This limit does not permit claiming truncated, unseen source output was read.

Timing observations distinguish dispatch-to-return, ready-to-dispatch and actual worker execution. Calculate durations from the recorded timestamps, never substitute one category for another. Preserve unavailable worker start times as unavailable. If runtime capacity is still below ten readers, mark the performance attempt environment-limited; do not report it as the target configuration or silently consume time trying to bypass the host limit.
# JSON artifact revision

New runs use the JSON handoff contract. `test_json_artifacts.py` covers strict parsing/schema, source and report bindings, generated-view independence, incomplete coverage, image attestations, one-recheck carry-forward, withdrawals and comparison selection. Existing Markdown tests remain compatibility tests; their historical fixtures are not migrated.

For an actual forward test, use paper-a.md, paper-b.md and paper-c.md under fixtures with the confirmed question: under which conditions does adaptive calibration outperform the baseline, and can results be generalized or pooled? Use fresh independent readers/checkers, a fresh run directory, actual image viewing, JSON papers/checks, an independently checked synthesis and generated views. Record observed execution issues and timing. This synthetic trial validates handoff behavior only; it is neither a real-paper speed benchmark nor expert academic validation.

