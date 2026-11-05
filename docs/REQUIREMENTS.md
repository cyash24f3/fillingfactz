# Requirements and verification

The application implements the filing-verification requirements of the technical
assignment. The presentation/demo is intentionally deferred.

| Requirement | Implementation | Verification |
|---|---|---|
| Official filing evidence only | Three reference PDFs, manifest, local corpus; no web-search tool | Source hashes, exact quotations, and PDF-page validation |
| Four verdicts | Typed verdict schema and period/scope policy | Twenty labelled statements covering all labels |
| MERMAID adaptation | Decomposer, iterative Executor, registry tools, evidence memory | Design rationale and LangGraph architecture documentation |
| LangGraph agents | Outer workflow plus nested Executor graph | Graph failure/recovery and bounded-execution tests |
| Clear stopping | Accepted submission, model/tool budgets, finalization after repeated searches without new evidence | Budget and search-stagnation tests |
| Malformed output and tool errors | Validated tool arguments; feedback and retry; explicit incomplete state | Fault-injection and recovery tests |
| Reusable evidence | Namespaced SQLite memory with topical relevance filtering | Recall, namespace, stemming, and stale-source tests |
| Newer disclosures | Filing metadata, current/historical policy, temporal row checks | Three outdated claims and historical-date controls |
| Extensible tools | Schema/handler registry | Search fusion and page-context tools use the same Executor path |
| Source provenance | Filing, page, passage ID, original quotation, source URL, PDF hash | Quote-style, changed-word, and source-reference tests |
| Async streamed API | FastAPI POST endpoints and SSE event stream | API contract, transport, protocol, and live endpoint checks |
| Reviewer UI | Single and batch review, live steps, evidence, usage, downloads | Streamlit application tests and live browser checks |
| Whole-set evaluation | 20 statements × full / memory-off / Decomposer-off | 60-run predictions and measured comparison table |
| Missing disclosures | NOT_ENOUGH_INFO policy; search coverage and trace retained | Regional headcount, attrition, and future-forecast cases |
| Units and rounding | Page unit context and numeric consistency checks | Rounded billion, thousands-to-dollars, and exactness tests |
| Similar metrics/populations | Row-label and employee-population checks | Revenue mix-up and regional/global scope tests |
| PDF quirks | Page-aware chunks, TOC filtering, compact headers, bounded neighbouring-page reads | Page-boundary navigation and unit-context tests |
| Repository and documentation | Public GitHub repository, run instructions, design, architecture, results | Clean-checkout tests and GitHub verification |

## Interpretation

A matching label with `status: incomplete` is not credited as correct. Missing-
information judgments retain the search trail and relevant context where supplied;
no isolated quotation can prove absence across a corpus. Exact quote matching
establishes provenance, while the model remains responsible for semantic judgment.

Benchmark results identify their evaluated source hashes and are preserved when
the implementation changes. The development dataset is not a held-out test set.
Latency is measured on local hardware and should be considered alongside calls,
tokens, accuracy, and completion rather than as a universal performance claim.
