# Synthetic reading-report fixture: Study A

This is a deliberately supplied report artifact for workflow testing, not a real publication. Author identity: `/fixture-author`. Revision: r1. Reading: complete. Verification: pending. Paper ID: P001. DOI: unknown.

## Research question and method

Does adaptation improve calibration? P001-C01 — author claim: The experiment uses twenty paired synthetic controlled sequences and mean accuracy. Evidence: paper-a.md, Methods, lines 13–15, “Twenty synthetic sensor sequences”.

## Author results

P001-C02 — author claim: Controlled adaptive mean accuracy is 0.92, exceeding baseline 0.74. Evidence: P001-I001, Figure 1, tests/fixtures/figures/controlled.png, and paper-a.md Results lines 17–21.

P001-C03 — author claim: The improvement is statistically significant. Evidence: paper-a.md Results lines 2–3, “This study compares adaptive calibration”.

## Agent analysis

P001-C04 — agent analysis: The design is invalid because all calibration research must use at least 1000 samples. Evidence: the reported sample of twenty in Methods. This universal sample-size rule requires no additional source.

## Author limitations

P001-C05 — author claim: The small synthetic sample and absence of intervals limit inference. Evidence: paper-a.md Discussion lines 31–33.

## Coverage

| Unit | Locator | Type | Status | Understanding |
| --- | --- | --- | --- | --- |
| Title and abstract | paper-a.md lines 1–7 | text | read | Controlled comparison |
| Research question | paper-a.md lines 9–11 | text | read | Improvement question |
| Methods | paper-a.md lines 13–15 | text | read | Paired synthetic experiment |
| Results and Figure 1 | paper-a.md lines 17–29 and controlled.png | text/image/table | read | Adaptive wins |
| Discussion | paper-a.md lines 31–33 | text | read | Small sample |
| References | paper-a.md lines 35–37 | text | read | One bibliography entry |

No gaps. This report is ready for integration.
