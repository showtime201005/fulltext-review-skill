## 2026-10-27：文末參考文獻

綜合報告固定增加 References／參考文獻，預設 APA 7，可依要求採 IEEE，保留每篇 corpus ID 對照。資料來自供應稿件與可用 metadata；缺少年份使用 n.d.、未知刊物不猜補，無已確認公開連結時連至本地原文。未擴張 schema 或新增查核流程。

已替 lean-acceptance-008/synthesis.md r2 補上三篇完整作者與題名。原查核者只確認書目與原正文未變；三項基本驗收通過，skill 格式驗證通過。未做外部出版資訊搜尋；原測試耗時不包含本次使用者要求的後續更新。

## 2026-10-27：五項交接優化與獨立計時實測

五項已落實：UTF-8 直接寫檔及可靠備用範例；prepare PAPER --author 合併單篇整理／輸出／查核綁定；原文交接包；角色單獨短指引及範例；第一篇返回即建立綜合初稿。prepare CHECK 只刷新對應單篇，避免全批重繪。交接包附原文摘錄與上下文、未引用章節／表格索引及圖片路徑；過長段落明示省略，checker 依需要擴讀原文並實際看圖，不把交接包當成驗證。

- 程式僅修改既有 artifacts.py 與 test_json_artifacts.py；完整 106 項回歸測試通過，JSON 子集 38 項通過。新測試涵蓋合併交接、原文失效時不供應假摘錄、只更新受影響報告與手寫檔保護，另修正綜合重綁時上游變更不能沿用舊判定。Skill 格式檢查通過。
- 全新三篇測試 [lean-acceptance-008/run.md](tests/results/lean-acceptance-008/run.md) 在程式／測試完成後開始，期間沒有修改 runtime。完整閱讀 1,789 行及 56 張圖，核心發現 4／5／4，全數獲支持；綜合稿亦獲獨立查核支持。三項基本驗收皆通過。
- 首份可讀報告 133.496 秒（約 2 分 13 秒），交付 411.231 秒（約 6 分 51 秒）。觀察區間：閱讀 186.458 秒、單篇查核 207.843 秒、綜合至交付 254.730 秒；區間重疊，不可相加。這是 coordinator 觀察時間，不是 worker 純運算時間。
- 編碼修復 0 次。P001 一次內容補充：區分初始 cutting 骨幹與 sewing／部署骨幹，同一查核者只確認改動；沒有整篇重讀。綜合稿在單篇查核期間建立，完成後只做簡短跨篇檢查。
- 主交付：[synthesis.md](tests/results/lean-acceptance-008/synthesis.md)。保留約 60% 學術回顧／40% 證據評析的寫作方向。

限制：僅一次新的實測，不能推導穩定加速倍數；前次007含開發重疊，不是嚴格對照。查核使用相同原文與實際圖像，不含論文實驗重現。下文為先前版本與驗證歷史。

## 2026-10-27：學術回顧與評析比例更新

使用者要求預設約 60% 學術回顧、40% 證據評析。已更新入口、閱讀／綜合／查核指引及使用指南；比例只作寫作重心，不新增驗收規則。lean-acceptance-007/synthesis.md 增加動機、機制與貢獻，集中限制討論並採中性語氣。原查核者提出一項方法階段歸屬修正，r3 修正後經針對性確認支持。三項基本驗收仍全數通過，skill 格式驗證通過。未改 runtime、未重跑論文閱讀或實驗；原 run 的交付耗時不包含本次後續改寫。

## 2026-10-27：精簡版已完成實作與三篇驗收

依 [SIMPLIFICATION_PLAN.md](SIMPLIFICATION_PLAN.md) 實作：新資料使用 schema v2／contract v3，通常每篇 3–5 項核心發現，一次獨立基本查核與必要時的一次內容修正。精簡 Markdown 不再逐欄展開機器資料；來源雜湊、查核綁定與版本保存由工具處理。一份壞查核檔不阻止其他檔案輸出。新流程只檢查閱讀完成、報告齊全、核心內容已處理；事件漏記不阻擋交付。

- 程式：完整 102 項測試通過；最後友善診斷顯示修改後的 34 項 JSON 測試通過。新增六項 v2 行為測試，涵蓋空圖片行號、漏記事件、壞檔隔離、舊查核失效、定位錯誤與缺少必要交付。
- Skill：quick_validate 通過。入口與各角色指引已縮短；歷史計畫標為歷史，HTML 指南已更新。
- 三篇端到端：[lean-acceptance-007/run.md](tests/results/lean-acceptance-007/run.md)。從原文重新閱讀 1,789 行、實際查看 56 張圖；每篇核心重點 4／5／4，共 13 項均獲不同作者的 checker 支持。綜合稿另經簡短獨立查核支持。
- 三項基本驗收全部通過；沒有內容修正要求。主交付：[synthesis.md](tests/results/lean-acceptance-007/synthesis.md)，另含三份單篇 Markdown／JSON 與查核紀錄。
- 首份可讀報告約 187.972 秒，總交付約 420.350 秒（7 分鐘）。實作收尾與閱讀重疊，時間含協調及開發等待；不是受控速度比較。
- 實測修復兩篇的 Windows Unicode 寫檔損壞，以及一篇將來源不確定性誤放 coverage.gaps 的機械問題。未重讀整篇、未改寫歷史 run。首份報告事件曾誤記，已在 run.md 留下更正說明。

限制：未重跑論文實驗；來源矛盾和小樣本限制仍在文獻報告中。基本驗收核對資料與紀錄一致性，不能單靠程式證明科學理解或杜絕未知錯誤。歷史驗證如下。

## 2026-10-26 User-approved focused verification and early reports

User explicitly chose focused independent verification with unchecked secondary details disclosed. Full text/image reading remains required. Readers now publish generated Markdown after successful reading preflight/coverage while the run stays active; verification status is prominent at the top. Final checked delivery remains separate from first report availability.

Default checker scope includes all comparison claims, core quantitative results with their conditions/denominators, required methodological premises, material limitations/negative findings, suspected defects and all substantive synthesis inferences. Raw inventory checks still detect material omissions. Secondary claims remain explicit pending findings with no invented inspection; the check and run remain needs-confirmation, with new stop_reason=scope when appropriate. Secondary pending work does not trigger repair or routine expansion. Exhaustive checking is available on explicit request. Synthesis uses supported premises and does not reopen paper loops for secondary details.

No artifact schema migration or new workflow service. Validator accepts scope only with needs-confirmation and still rejects a passed check with pending claims. Rendering now puts handoff verification status near the title. New regressions cover focused pending disposition and rejection of a scope-limited full-pass label. All 96 tests passed, local reference links resolve and skill validation passed. Frozen historical reports were not regenerated.

Tradeoff accepted: not every implementation detail is independently verified; scope must be visible and material selection remains a verifier judgment, not mechanically certified by preflight. Complete delivery refers to the agreed focused scope, not exhaustive verification. First-report time and final verification time must be reported separately. This policy has not yet had a fresh corpus benchmark; earlier exhaustive runs are different-scope comparisons, not pure speed baselines.

## 2026-10-26 Lean acceptance 005 and targeted rework fixes

[Evaluation](tests/results/json-acceptance-005/EVALUATION.md): complete delivery in 1,070.3 seconds (17m50.3s), 9.9% longer than run004. Initial read/report stages shortened about 14-37%; paper JSON fell 19.5% to 100,645 bytes (36 final claims). One material result was omitted from P001 claims and restored in its sole repair/recheck. Coordinator shell encoding corrupted three synthesis locator separators; its sole repair/recheck fixed them. Sources unchanged and coverage complete; overall quality remains needs-confirmation for source gaps, synthesis passed.

The run required a validator hotfix: original excerpt fields may faithfully quote question-digit damage, while authored statements/reasons/locators remain rejected. The initial check and failures are preserved; same tracked checkpoint retry passed with unchanged check bytes. This interrupted run does not demonstrate a clean speedup or error-free contract execution.

After delivery, a one-sentence reader completeness check requires important results tables/analysis sections to reach claims instead of only notes. Markdown preflight now warns about question-digit encoding damage before handoff without rejecting literal damaged quotations. Added focused regressions and made test_artifacts.py's sibling-script imports explicit (its isolated run previously depended on test_json_artifacts.py loading first). All 94 tests passed; the 42 artifact tests also pass independently. Skill format validation passed. Historical frozen report/check bytes are unchanged by post-delivery edits.

Tradeoff: a brief reader inventory-to-claim check adds work but targets observed rework. Warnings require inspection; they are not scientific proof. No new schema, dependencies, mandatory review rounds or reduced reading scope. The final patched skill has not yet had a fresh full-corpus timing run.

## 2026-10-26 Lean instruction revision after acceptance 004

Rewrote six instruction files in place: SKILL.md and reading/verification/synthesis/report-contract/json-artifacts references. Whitespace-delimited English word counts decreased from 7,323 to 3,488 (52.4%); entrypoint 1,712 to 735 (57.1%). These are instruction-size measurements, not token counts or runtime savings. No runtime scripts, schema, fixtures or historical reports changed.

The shared contract now owns limits/state/timing; role references describe only their work. JSON guidance defines one independently judgeable conclusion per claim, groups only compatible supporting details/results, assigns values/conditions/uncertainty/evidence distinct purposes, and keeps pass reasons brief. A qualifying limitation need not become a redundant second claim; it remains in uncertainty/issues with affected IDs, while independent limitations still receive claims. Negative findings, full text/image coverage, original evidence, all reported claim components, independent checks, single repair/recheck, final source/coverage/view checks and exact-byte bindings remain required. Synthesis checking reuses settled upstream checks and targets new inference or conflicts.

Tradeoffs: less repeated explanation and coarser grouping of genuinely related details; readers may follow IDs/locators for detail. A grouped claim cannot pass if one substantive component fails. No hard claim limit, reduced reading scope, weaker verification, model change, or schema migration was introduced.

Validation: Skill Creator quick_validate passed; all local Markdown links in the six edited files resolve, and no replacement characters remain. Runtime tests were not repeated because executable code/schema are unchanged. A fresh full-corpus execution has not yet tested instruction adherence, output-size reduction or end-to-end speed. Compare the next complete run against acceptance 004 (973.6 seconds, 125,031 paper-JSON bytes, 53 paper claims), retaining scope and checking omissions as well as errors. Do not treat document shortening as measured review acceleration.

## 2026-10-26 Fresh three-paper complete acceptance 004

[Evaluation](tests/results/json-acceptance-004/EVALUATION.md): complete report/check delivery in 973.6 seconds (16m13.6s), with 1,789 text lines and 56 images covered, 59 source fingerprints unchanged, 53 paper claims and seven synthesis claims checked, zero requested content repairs and zero tracked preflight failures. Seven generated Markdown views plus the authored synthesis are present. Overall quality remains needs-confirmation due to disclosed source gaps; synthesis check passed on qualified conclusions. No speedup demonstrated: prior 807-second run was incomplete and timing was not comparable; current paper JSON increased 61.26%. Next target is output granularity and duplicated evidence prose under the same full-coverage and independent-check requirements. Historical run003 remains unchanged by this acceptance.

## 2026-10-26 Coordination and timing implementation

Implemented the first speed-plan increment: no default hard deadline; clean worker contexts with role-specific references and compact returns; bounded tool output; serialized shared writes; required independent synthesis check. Historical planning documents now explicitly defer to the current skill contract.

`check_artifacts.py --record-event` stamps start and observed workflow events using current UTC, preserves the original start and rejects duplicate stage events. It updates dispatch counters through an atomic run.md replacement. The coordinator remains the sole writer. `--record-event delivery` runs tracked final validation with generated views and complete-delivery requirements before recording delivery time. Complete delivery reconciles registered source papers with run artifacts, requires synthesis, paper coverage and returned independent checks, and permits disclosed source limitations. Source freshness and detailed coverage reconciliation remain separate required gates. Ordinary preflight still supports honestly partial historical runs.

Validation: 92 tests passed using `python -X utf8 -m unittest discover -s tests -p 'test_*.py'`; after strengthening the Unicode regression assertion, all 25 JSON tests passed again. Skill Creator quick_validate passed. New regressions cover no-deadline continuation, immutable start, duplicate events, failed delivery/retry limits, final-validation-before-delivery ordering, completeness inventory and original damaged excerpts versus newly corrupted statements.

No historical paper reports were repaired or accepted in this increment. The reopened three-paper run remains unfinished; no real-corpus speedup or complete acceptance is claimed. Next measurement uses the same three supplied papers, purpose, model and concurrency limit with fresh outputs and observed timings.

# Fulltext Literature Review Skill — Delivery and Validation

## Current revision — authoritative JSON and generated views (2026-10-26)

The user's accepted design is implemented in the skill's [JSON handoff](.agents/skills/fulltext-literature-review/references/json-artifacts.md) and [schema](.agents/skills/fulltext-literature-review/references/artifact.schema.json). Readers write paper JSON; independent verifiers write check JSON; a deterministic standard-library renderer produces their Markdown views. The synthesis remains agent-written Markdown with an independent JSON check. Existing source inventory and workflow contract v2 are retained; JSON schema version 1 is a separate format version. Historical runs were not migrated.

`artifacts.py` validates the bundled schema and semantic invariants, generates Markdown without rewriting authoritative JSON, and selects comparison claims without another model summary. The comparison projection includes method references, selected main findings, all negative/limitation claims, numerical conditions and issues. It explicitly does not establish verification eligibility. Check rounds preserve original findings and bind exact report bytes; a single recheck carries unchanged IDs explicitly. Withdrawals override current eligibility while preserving history.

`check_artifacts.py` and `sources.py coverage` accept JSON through a deterministic projection into their existing validation logic. JSON is preferred over sibling generated Markdown, so rendering does not change check hashes or duplicate claim declarations. Source evidence IDs/hashes/ranges are reconciled with the manifest; source byte freshness remains a separate source/coverage check. A hand-edited generated view is not authoritative and must be regenerated at delivery. The renderer refuses to overwrite unrelated handwritten Markdown. JSON parse errors, duplicate keys, non-finite constants, wrong types and unknown fields fail rather than silently losing content. No dependency or new scheduler was added. The workflow uses at most ten concurrent subagents; global agent configuration was not changed.

Validation: all **81 tests passed** (36 existing artifact tests, 26 existing source tests, 19 new JSON behavior tests) in 28.162 seconds with `C:/Users/c9363/Desktop/pymupdf-env/Scripts/python.exe`. The JSON tests cover generated-view/hash independence, post-check mutations, source/line mismatches, image/line attestations, incomplete handoffs, identity/path bindings, one-recheck carry-forward, withdrawal/history, negative-result preservation, literal source text, synthesis checks and CLI behavior. Image unit fixtures validate attestations only, not visual interpretation. Skill Creator `quick_validate.py` passed; all three scripts compiled.

The independent [three-paper synthetic forward test](tests/results/json-acceptance-001/run.md) delivered three fully read JSON papers and three independent JSON checks: all 14 declared paper claims passed round 0, no schema or scientific repairs were required, actual image inspection and coverage/source checks completed. Six Markdown views were generated. The synthesis draft's independent check remained pending at freeze. **614 seconds elapsed: late partial delivery, not complete acceptance.**

The coordinator observed a 151-second renderer execution-call delay. Parent post-delivery read-only preflight passed with over_budget true. A temporary-directory reproduction loaded/rendered/wrote the same six artifacts in 0.292881 seconds and exactly matched the frozen views; the original delay's cause remains unproven. Three combined instruction outputs hit the outer tool-output limit; role instructions were recovered, but complete schema recovery was not established for two checkers. The shared contract now calls for separate bounded instruction results. [Detailed evaluation](tests/results/json-acceptance-evaluation.md) preserves these limits. No ten-paper real-corpus speed comparison, token/cost saving, or academic accuracy improvement is established.

## Previous revision — bounded verification and delivery (2026-10-26)

The implementation follows [PERFORMANCE_REVISION_PLAN.md](PERFORMANCE_REVISION_PLAN.md). New artifacts use contract version 2; historical runs remain unchanged and retain legacy preflight behavior.

- Each paper and synthesis allows initial verification round 0 plus at most one consolidated repair/recheck round 1. Revision labels do not determine rounds. Later defects revoke eligibility or remain unresolved without restarting upstream work.
- One reader per paper; ten simultaneous readers are the target when actual runtime capacity permits. User configuration now sets `agents.max_concurrent_threads_per_session = 32`, with a backup recorded in the plan. The current session still exposes only three worker slots. A fresh session must verify capacity; no ten-reader performance claim has been made.
- Default end-to-end budget is 600 seconds with a 120-second delivery reserve. Deadline handoff retains unread/unverified work explicitly. This is agent scheduling guidance plus recorded-event validation, not a real-time process supervisor; an uninterruptible tool may overrun and must be reported.
- `check_artifacts.py` validates the coordinator's versioned state/events, one-repair counters, current claim verdicts/withdrawals, independent dispatch identity bindings and visible revision labels; it derives elapsed, dispatch-to-return and ready-to-dispatch intervals. It rejects false exhaustion, repeated rounds and unsupported pass states. Worker artifact-only handoffs may precede coordinator reconciliation; whole-run preflight reconciles all current artifacts.
- Chart metric/stage/denominator interpretation and numerical consistency are explicit reader/verifier responsibilities. The tool validates declared state, not chart interpretation or scientific correctness. Current status is concise; necessary historical evidence remains once below it.

Validation performed with `C:/Users/c9363/Desktop/deepagents-practice/.venv/Scripts/python.exe` (Python 3.12.13): the full then-current suite passed 59 tests in 13.255 seconds (33 artifact + 26 source). After three additional state/identity guards, the affected artifact suite passed all 36 tests in 0.348 seconds; source handling was unchanged. Skill Creator `quick_validate.py` returned `Skill is valid!`. No dependency was installed. The WindowsApps Python alias remains unsuitable; use the recorded interpreter.

Independent simulated handoff: a fresh-context subagent used the skill on [a supplied checkpoint](tests/results/performance-handoff-001/HANDOFF.md), then [delivered](tests/results/performance-handoff-001/DELIVERY.md) without further science dispatches. It withdrew a mistaken 70% claim against source 12/20 = 60%, preserved the report bytes and prior finding, retained round 1 / repair_used 1, and disclosed missing coverage/manifest and pending synthesis. Final preflight and parent state/hash assertions passed. [Evaluation](tests/results/performance-handoff-001/EVALUATION.md) records the simulation boundary and an LF/CRLF fixture-hash limitation; no real source-version continuity or 600-second speedup is claimed. This exercise is separate from full-reading acceptance and scientific-accuracy evaluation.

Remaining validation: fresh-session ten-reader capacity; one bounded ten-paper real acceptance under the new skill; full image/figure behavior under that run; stable latency and expert correctness. Unit tests and a simulated checkpoint do not establish those outcomes. Do not rerun the old corpus indefinitely to turn these pending items into apparent passes.

## Historical validation records

Status: first implementation delivered. The synthetic end-to-end run passed its independent paper and synthesis checks. This report distinguishes observed behavior, simulated boundary exercises and untested capabilities; it does not certify academic accuracy on arbitrary papers.

## Use the skill

Open this workspace in Codex. The project-local entry point is [.agents/skills/fulltext-literature-review/SKILL.md](.agents/skills/fulltext-literature-review/SKILL.md).

Example request:

```text
Use $fulltext-literature-review to fully read the supplied Markdown papers
and their linked images. Purpose: [your research question].
Inputs: [explicit paper paths, associated supplements].
Write to [a new output directory outside the inputs].
```

Without a purpose, the skill first proposes a focus and waits for confirmation. After confirmation, it proceeds through reading, independent verification, repair, synthesis and independent synthesis verification. Runtime output defaults to English. Inputs remain unchanged; missing images or unresolved understanding remain explicit gaps.

This session demonstrated loading the skill by explicit absolute path, following its relative references, and executing it through actual Codex subagents. Automatic discovery in a **fresh Codex client session** was not separately tested. If the existing chat does not show the new skill, explicitly ask it to read the entry-point path and follow it. No global installation or Codex configuration change was made.

## Implemented files

| Component | Delivered role |
| --- | --- |
| `SKILL.md` | One coordinator workflow, focus gate, corpus boundary, actual subagent dispatch and stopping rules |
| `references/report-contract.md` | Markdown artifacts, ownership, stable IDs, evidence locators, version reconciliation, reading/verification/execution states |
| `references/reading.md` | Full Markdown/image reading, coverage, type-sensitive interpretation and gaps |
| `references/verification.md` | Independent selective paper checking and synthesis checking, accurate input quotations, version-bound ledgers |
| `references/synthesis.md` | Theme-based comparison, contradiction/comparability, corpus-bounded conclusions |
| `scripts/sources.py` | Standard-library CLI for explicit source registration, numbered version-checked reads, consistency checks and fingerprints |
| `tests/test_sources.py` | Thirteen behavior tests for deterministic file-handling logic |
| `tests/fixtures/` | Three synthetic papers, one image, long/broken variants and defective report/stopping-rule fixtures |
| `tests/scenarios.md` | Evaluator-only facts and reproducible behavioral tasks |
| `tests/results/` | Actual reader/verifier artifacts and isolated boundary exercises |

No model API client, execution engine, database, Markdown parser dependency or UI layer was added. Source/image discovery is agent-guided; the helper handles explicit local files. No old project code was imported or changed. An existing venv's interpreter was reused for verification; this skill itself imports only the Python standard library.

## Environment and deterministic checks

- Working test interpreter: `C:\Users\c9363\Desktop\deepagents-practice\.venv\Scripts\python.exe`, Python 3.12.13. The default WindowsApps `python.exe` alias could not execute; this did not require installing a dependency.
- All **13 source CLI tests passed** using `-X utf8 -m unittest discover -s tests -v`. Coverage includes exact inclusive physical lines, BOM/CRLF/CR handling, non-ASCII and spaced paths, stable IDs for path aliases, binary images, missing files, changed fingerprints and explicit refresh, failed-batch preservation, invalid ranges/encodings/manifests, empty text, supplement association and report fingerprinting.
- The environment-provided skill-creator `quick_validate.py` reported **“Skill is valid!”**. Its PyYAML installation is a validator dependency, not a runtime dependency of the delivered skill.
- Actual image viewing and subagent source access succeeded. [P0 probe](tests/results/p0-probe.md) records the early observations. Its missing-source-tool issue was resolved by implementing `sources.py` before the review runs.
- Final artifact-integrity reconciliation checks that current report SHA-256 values occur in their version-bound checks and that registered original sources remain unchanged. This is file-version verification, not a semantic quality test.

To rerun unit tests, use any working Python 3.10+ interpreter from this workspace:

```text
python -X utf8 -m unittest discover -s tests -v
```

## P0–P6 outcomes

| Phase | Actual outcome |
| --- | --- |
| P0 | Text/image access, explicit-path skill loading, relative references, distinct subagents and assigned-file writes tested. Fresh-client automatic discovery remains untested. |
| P1 | Shared contracts and source helper implemented; all thirteen behavior tests passed. |
| P2 | A real reader fully read Study A; another actual subagent checked raw text/image and coverage. Separate defective-report repair received a round-1 independent pass. |
| P3 | Explicit-purpose baseline proceeded without focus reapproval; no-purpose test stopped awaiting focus. Same three papers were reread with overlapping/queued workers and distinct independent checkers. |
| P4 | Coordinator produced a thematic synthesis of all three checked papers; a different subagent independently checked all six substantive synthesis claims. |
| P5 | Behavioral artifacts recorded below. Missing-capability and exhausted-history cases are simulations; no unavailable real environment or three actual failed historical rounds is claimed. |
| P6 | Skill-format validation, local reference checks, usage and limitations documented; current report/source fingerprints reconciled. |

## Behavioral evidence

| Case | Result and evidence | Qualification |
| --- | --- | --- |
| A1 — explicit purpose | [Complete baseline run](tests/results/sequential/run.md): actual reader reports, independent paper checks, synthesis and independent synthesis check | Three synthetic papers, not real academic corpus benchmarking |
| A2 — no purpose | [Focus branch](tests/results/focus-branch/run.md): overviewed every supplied paper, proposed a question, stopped `waiting-for-focus`; no deep reports or invented approval | Confirmation was intentionally not simulated; resume-after-user-reply was not separately exercised |
| A3 — truncation / images | [Long report](tests/results/long-read/papers/P001.md): initial output explicitly truncated from 13,283 tokens; all 329 lines then recovered in five contiguous reads; image viewed; late stress reversal retained | This artifact tests reading; it is still pending its own independent report verification |
| A4 — wrong value / locator / criticism | [Defective report check](tests/results/faulty-paper-check.md): actual verifier identified 0.92 versus image 0.82, false significance, unsupported sample threshold and bad locators | Defects were deliberately seeded; evaluator answer file was withheld |
| A5 — omitted coverage | Same actual check found missing appendices, suppressed stress result, incomplete table range and false complete label | Does not prove detection of all subtle omissions |
| A6 — missing image | [Broken-image report](tests/results/broken-image/papers/P001.md): exact referenced path absent, image-view attempt failed, reading `gaps`, controlled numeric values left unknown | Unaffected stress text was retained; this artifact is not a fully verified review |
| A7 — incompatibility / contradictions | [Baseline synthesis](tests/results/sequential/synthesis.md) and [independent check](tests/results/sequential/checks/synthesis.md): controlled benefit, humidity reversal and cold loss retained; accuracy and macro-F1 not pooled; theory not treated as experiment | No assertion about a real research field |
| A8 — outside facts / field gaps | [Defective synthesis check](tests/results/faulty-synthesis-check.md) rejected extrapolation from missing mechanism to field-wide absence | Tests explicit seeded overreach, not exhaustive external-fact detection |
| A9 — stopping limit | [Boundary exercise A](tests/results/boundary-exercises.md): actor preserved rounds 0/1/2, no third repair, explicit pending impact | **Simulated persisted history**; not three actual failed repair loops. One actual successful repair/recheck is separately recorded below |
| A10 — ungrounded synthesis | Same defective synthesis check rejected universal superiority, metric pooling and empirical reinterpretation of the countermodel | Independent checker had access to verified reports and originals |
| A11 — version change | Unit tests actually mutated source copies and rejected stale reads. [Stale-report exercise](tests/results/stale-version/result.md) actually copied/changed a report, detected hash mismatch and affected dependent arithmetic, kept stale check unchanged | No full downstream rerun after the mutation; the exercise deliberately stops pending recheck |
| A12 — independence / resource boundary | [Parallel exercise](tests/results/parallel/run.md) records different actual authors/checkers and separate write paths; [boundary exercise B](tests/results/boundary-exercises.md) stops blocked without independent agents | Missing-agent environment is **simulated**, not a second real client environment; no throughput/speedup measurement |
| A13 — injection / bibliography | Actual baseline reader and verifier treated adversarial quotation as data and retained unknown author/year/DOI fields | One explicit injection fixture, not a comprehensive security evaluation |

### Actual repair and round-1 recheck

The [original defective report](tests/fixtures/faulty-paper.md) was checked at round 0 by `/root/focus_branch_test`. A replacement author `/root` explicitly repaired it into [r2](tests/results/repair/papers/P001.md). `/root/paper_verifier`, a different agent from both authors, appended an actual **round 1** to [the preserved check history](tests/results/repair/checks/P001.md).

The repair fixed the visual value, significance claim, source ranges, unsupported universal criticism and missing stress/table/appendix evidence. Round 1 passed all seven current claims and eleven coverage units at its recorded hash. Earlier defective statements remained in the history; the round counter did not reset. The original defective fixture remains unchanged.

### Observed check-artifact defect and correction

During evaluation, the coordinator found that the defective-report verifier had miscopied two input locator ranges even though its main judgments were correct. The same verifier reopened the actual input and corrected its check, distinguishing the input range from recommended raw-source ranges. `verification.md` now requires exact transcription and final reconciliation against the fingerprinted report. This observed failure is evidence that independent agents can still make mistakes; it is not hidden by a blanket “all tests passed” claim.

## Deliverables and remaining limits

The [baseline run](tests/results/sequential/run.md) is the complete worked example: three paper reports, one synthesis and four independent check files. Its 20 substantive paper claims and six synthesis claims passed at their recorded versions; no unresolved baseline reading/check issue remained. Historical report handoff states stay unchanged so fingerprints remain valid; current outcomes are in the check files and run index.

The [parallel exercise](tests/results/parallel/run.md) demonstrates fresh reading and independently checked per-paper outputs on the same corpus, with overlapping and queued work. It did not produce a second synthesis. Other isolated test artifacts deliberately retain pending/gap states rather than claiming a full review.

Remaining untested: fresh-client automatic skill discovery; long production papers, difficult formulas and low-resolution images across actual disciplines; resumption after an actual user focus confirmation; a genuinely unavailable-agent environment; repeated real failed repairs through both allowed rounds; large-corpus cost, latency and scaling.

The skill defines an auditable process using instructions and actual tools. It cannot guarantee full comprehension, perfect coverage, zero hallucination or independent model errors. Source hashes detect byte changes, not truth. Original inputs and existing projects were not modified. Global installation, plugin packaging and model/API setup are outside this delivery.

## Subsequent real-corpus trial

After the initial synthetic validation above, the user supplied ten actual research-paper Markdown files with 184 image paths and explicitly confirmed the proposed review focus. The [completed real run](runs/real-corpus-001/run.md) contains ten reports, ten paper checks, [an English thematic synthesis](runs/real-corpus-001/synthesis.md) and [its independent check](runs/real-corpus-001/checks/synthesis.md).

All 6,852 text lines and 184 images were inspected; source/understanding gaps were retained. Independent checkers examined 170 paper claims. P003 required correction of an erroneous table-count criticism and an overstated temporal-trace interpretation; P001/P005 needed table-format repairs. All three r2 reports received round-1 rechecks. The synthesis's 22 qualified conclusions passed independent round 0; no synthesis repair was requested.

Overall real-run quality remains **needs-confirmation** for source deficiencies, not a blanket academic-accuracy pass: unreadable/interleaved material, missing promised results or witnesses, internal inconsistencies and incomplete methods constrain specific conclusions. No external evidence was added or underlying experiment reproduced. All 194 original fingerprints remained unchanged. This trial supersedes the earlier statement that no real papers had been tested, but does not establish general accuracy, production scale or fresh-client discovery.

The observed table-pipe and scientific-symbol transcription defects also led to one concise shared-contract instruction: explicitly use UTF-8, reread written symbols, and check literal-pipe escaping/column counts. This is a documentation refinement, not a new workflow engine or parser dependency.

## Revision A–E — 2026-10-26

Implemented the first batch in [REVISION_PLAN.md](REVISION_PLAN.md): single-paper rolling dispatch, concise per-claim checks, separate coverage/understanding/source-issue states, structural preflight and actual-clock event records. New report metadata/claim anchors apply only to new runs. Original source CLI behavior and historical artifacts remain unchanged. No dependency or workflow engine was added.

The new standard-library `check_artifacts.py` checks generated report/check/index formatting, local file links, explicit claim declarations/references, and current check-to-report author/revision/SHA-256 bindings. It understands the skill's narrow generated Markdown format, not arbitrary Markdown. Encoding warnings need source inspection; the tool cannot recover corrupted scientific symbols or establish actual agent independence from identity strings. It does not assess scientific truth, completeness of important claims or comprehension.

Twenty-nine behavior tests passed (13 source CLI, 16 preflight), including UTF-8 defects, escaped/unescaped table pipes, code fences, local links with spaces/parentheses, current versus historical hashes, revision/author mismatches, non-object metadata and coordinator-index links. A test actually exposed a non-object-metadata crash; parsing now clears invalid metadata before later validation. Skill format validation passed.

The [scoped synthetic paper exercise](tests/results/revision-001/run.md) used three fresh readers and actual independent checks: all sixteen substantive claims passed with their qualifications. First checks were dispatched before the longest reader returned; all six artifacts passed structure/version checks. This exercise produced no synthesis, and no repairs were requested. Full-reading observations and source limits were kept separate. No claim of academic accuracy or measured speedup follows from synthetic fixtures.

The [instrumented real-corpus trial](runs/real-corpus-002/run.md) completed: all124 reported important claim groups and17 synthesis conclusions received independent qualified passes. P003/P006/P008 required actual round-1 repairs; old findings and explicit unchanged-ID carry-forward remain in the checks. All194 originals were unchanged. This is validation evidence, not the product of this skill-revision task or an academic accuracy score.

The trial took39min56s from recorded trial start to worker-reported synthesis-check completion, excluding source registration and later engineering handoff documentation. It **did not meet the20–24min exploratory target**. Paper-check words fell20,788→15,683 (24.6%); total report/check words fell65,524→49,996 (23.7%). These are output-size measurements, not token-cost or latency improvements. Timing contains overlapping work, coordinator observation delay and in-run engineering refinements; the rough old30min estimate and unmatched settings do not establish a controlled comparison. Token/cost usage and expert gold standard remain unavailable.

R1 is partially validated: actual single-paper tasks/overlapping checks were exercised, and the scoped synthetic exercise used a fresh independent checker when its author was idle. The real trial still reused an ineligible author for other work at some free slots, contributing to ready-check waits up to6min06s. `SKILL.md` now explicitly schedules free slots rather than a fixed roster, starts a fresh checker for the oldest ready report, and records ownership waits. **No full ten-paper timing rerun after that final clarification was performed.** The instruction change is not a measured speedup.

R2 has actual round-1 version reconciliation/history evidence. R3 has actual complete-coverage/understanding-gap cases plus a [fresh missing-image reading exercise](tests/results/revision-broken-001/run.md): all text observed, absent required graphic, coverage incomplete/understanding gaps, controlled numerical values left unknown. That isolated report remains pending independent verification and is not presented as a full review. R4 has29 passing tests plus actual artifact preflights; R5 has an instrumented trial with the limits above. Repeated genuinely failed repairs through both allowed rounds and fresh-client automatic skill discovery remain untested.

At the end of the A–E trial, compact source output (F) was still deferred; it was completed later below. Observed discovery-output truncations led to filtering the manifest by assigned paper before displaying it separately from instructions. An observed verifier request to convert every raw path to a clickable link was rejected as an invented requirement; the contract now explicitly accepts exact code/plain paths. These refinements address execution overhead without weakening evidence requirements.

The user's final scope clarification is authoritative: the deliverable is the revised skill, helpers and necessary tests. Report artifacts are supporting test evidence; further report repair/review runs are not part of the continuing revision task.

## Remaining skill work completed — scoped validation

The final scheduling clarification received a [small actual dispatch probe](tests/results/slot-dispatch-001/result.md). With one worker position, the P001 author completed, P001 checking was ready and P002 marker-writing remained queued. A fresh independent checker occupied that position before P002. Actual dispatch identities, clocks and exact-byte/SHA-256 assertions were recorded; author and checker were different child agents. This validates the exercised scheduling choice, not a full multi-slot latency benchmark. The probe created only tiny synthetic markers/check evidence; no academic reports or real corpus were used.

F is implemented in the existing standard-library `sources.py`:

- `read --format text` emits one compact JSON metadata line followed by complete `number<TAB>text` physical lines. Default/explicit JSON bytes and error behavior remain compatible. Unicode, tabs, blank lines, a20,000-character line and U+2028 remain intact; no truncation/wrapping is added. A four-line temporary sample shrank461→235 output characters (49.0%); this is not a measured overall speedup.
- `coverage --manifest M --paper P001 --report FILE` checks observation comments in the report's existing coverage section, matching paper metadata, source association/current bytes/hash/physical line count, confirmed text interval unions, supplements and registered image attestations. Missing ranges/images, stale hashes and malformed/foreign observations fail; legal rereads produce warnings. Fenced examples and unconfirmed records do not count. The command writes nothing and does not automatically log a successful tool call as observed.
- It only checks **registered-source attestations**. Actual inventory comparison, unresolved unregistered references, real image viewing, comprehension and scientific checking remain agent responsibilities. Historical report artifacts were not retrofitted with fabricated records. The skill/reading/verification/contract instructions now route new paper handoffs through both structural preflight and coverage reconciliation.

Final regression: **42 tests passed** (26 source/compact/coverage tests +16 artifact tests), and `quick_validate.py` passed. Coverage tests use isolated temporary sources and observation fixtures, not full paper reports: complete and partial ranges, unconfirmed/truncated-range attestations, missing supplements/images, repeated ranges, changed/missing/refreshed sources, tampered line counts, malformed metadata/JSON, cross-paper IDs and fenced examples. Prior13 source behaviors and default JSON compatibility still pass.

All planned A–F implementation work is complete. No new dependencies, runtime engine, global installation or further real-corpus review was added. Overall acceleration, larger scheduling cases, expert accuracy and fresh-client automatic discovery remain unproven; these limits do not justify continuing to repair review reports as part of this task.
