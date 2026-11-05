# Project demonstration

A plain, twenty-slide walkthrough of the implemented Filing Fact-Checker.
The deck uses white backgrounds, black Arial text, native editable tables and
diagrams, and one screenshot of the actual reviewer application.

## Files

- [Editable PowerPoint](Filing-Fact-Checker-Demo.pptx)
- [PDF for presenting or sharing](Filing-Fact-Checker-Demo.pdf)
- [Presenter guide and full speaker notes](PRESENTER_GUIDE.md)
- [Four statements for a live demonstration](demo-statements.txt)
- [Recorded source-backed examples](recorded-examples.json)
- [Deck overview](overview.png)

The PowerPoint includes source references and explanatory speaker notes for every
slide. Tables, text and architecture diagrams remain editable. The PDF contains
the same twenty slides and can be presented without the application or model.

## Slide map

| Slides | Content |
|---|---|
| 1–3 | Project, task, verdicts and official filing corpus |
| 4–6 | Architecture, preparation, retrieval and MERMAID adaptation |
| 7–9 | Tools, bounded execution, state and persistent evidence memory |
| 10–12 | Evidence gate, financial interpretation, API and streaming |
| 13–16 | Actual reviewer interface and examples for all four verdicts |
| 17 | Errors, limits and recovery |
| 18–19 | Complete benchmark, original baseline and ablation findings |
| 20 | Run commands, verification and project handoff |

For a short presentation, use slides 1, 4, 13–16 and 18–20. The remaining slides
support a detailed technical discussion. A complete walkthrough usually needs
more time than this selected route.

## Evidence and interpretation

The demo examples come from the saved final benchmark, rather than a new run.
The interface screenshot documents a separate validated UI run, so its counters
are specific to that capture. Financial facts describe the supplied historical
filings. “Latest” means latest within that corpus.

The benchmark covers twenty unique development claims in three configurations,
giving sixty runs. Expected labels stay outside the agent. The recorded accuracy
does not establish generalization to every unseen claim, and local timings vary.

The deck describes the application evaluated in `results/benchmark/`, with the
source and measurement details in [Evaluation](../EVALUATION.md). No application
behavior or benchmark results changed while producing the presentation.

The source module in `source/build-deck.mjs` exports `buildDemo(presentation)` for
the Artifact Tool presentation facade. It is separate from application runtime
dependencies. Its image source is the existing validation screenshot in
`docs/images/reviewer-validation.jpg`.
