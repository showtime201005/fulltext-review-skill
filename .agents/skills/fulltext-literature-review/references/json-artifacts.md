# Coordinator handoff commands (v2)

New runs use schema_version 2 / contract_version 3. Historical files stay unchanged. Reader and checker examples live only in reading.md and verification.md; workers load their own role guide.

## Write UTF-8

Prefer apply_patch for authored JSON and Markdown. Reload prose after writing. If shell writing is necessary, use this PowerShell pattern (no Python pipe):

```powershell
$content = @'
{"title":"中文與 π、α"}
'@
[IO.File]::WriteAllText($absoluteTarget, $content, [Text.UTF8Encoding]::new($false))
```

Tools supply hashes. A source fingerprint mismatch requires inspection; never overwrite it to bless old evidence.

## One-call handoffs

```text
python scripts/artifacts.py prepare RUN/papers/P001.json --author ACTUAL_CHECKER
python scripts/artifacts.py prepare RUN/checks/P001.json
```

The first command validates, supplies source metadata, renders the paper, binds the independent check, and builds handoffs/P001.md with original excerpts, image paths and a source index. Give the checker that packet and its prepared check; full source paths remain available. A packet does not establish independent inspection.

The second command prepares the returned check and refreshes only the affected paper Markdown. The checker sets completed=true after actual inspection. No separate whole-run render is needed.

For the one content repair, preserve the original report and rerun the first command with the same checker. The tool carries only unchanged assessments; changed content/sources need targeted confirmation. Use start-check directly when only binding is needed. Existing prepare without --author remains available for early output without dispatch.

## Synthesis and delivery

Write synthesis.md with metadata and a whole-report claim anchor:

```html
<!-- review-meta {"contract_version":3,"kind":"synthesis","id":"S","author":"ACTUAL_AUTHOR","revision":"r1"} -->
<a id="S-C01"></a>
```

Build its method/contribution table from the first returned paper while checks proceed. After upstream checks settle:

```text
python scripts/artifacts.py start-check RUN/synthesis.md --author ACTUAL_CHECKER
python scripts/artifacts.py prepare RUN/checks/synthesis.json
python scripts/check_artifacts.py --run RUN --record-event delivery
```

Delivery checks the three basic criteria and records complete/partial. Always share existing reports and exact gaps.

## Simple timing

Initialize run.md with one review-run comment: contract_version:3, started_at:null, delivered_at:null, execution:"active". Record start before registration and first-report after the first successful readable output. Preserve the original delivery time when later making user-requested revisions.

For performance tests, finish code/tests before the fresh run. Note reading and checking dispatch/return observations in three aggregate stage groups (reading, basic paper checks, synthesis/delivery). Parallel stages may overlap; don't add their durations as total time. Missing measurements stay unknown, never an acceptance failure.
