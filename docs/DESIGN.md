# Design decisions

## MERMAID adaptation

The system adapts [MERMAID, sections 2.1–2.4](https://arxiv.org/html/2601.22361v2)
to a fixed corpus of long company filings.

| Component | Implementation |
|---|---|
| Decomposer | A validated subject/relation/object plan, attribution, period, topics, and queries |
| Executor | Bounded model/tool iteration with structured verdict submission |
| Toolset | Local PDF search and reads through a Python registry with argument schemas |
| Memory | Persistent source passages, quotations, and provenance, recalled with SQLite FTS5 |

The implementation uses a compact plan rather than a full knowledge graph, local
filing tools rather than web tools, and a registry rather than an MCP server.
Lexical recall keeps deployment small; semantic reranking is a possible extension.
Initial evidence is supplied by Python to reduce model-directed retrieval turns.

## Retrieval and memory

SQLite FTS5 provides local BM25 search without an embedding service. Initial
retrieval combines the first planning query with the original statement using
reciprocal rank fusion. This preserves specific metrics, amounts, and qualifiers
while reading only the selected passages.

Memory reuses evidence rather than caching answers. Stored entries are checked
against the current source before reuse, and all filings remain part of fresh
retrieval. Memory hits are measured separately from model/tool calls; a hit alone
does not establish an efficiency improvement.

## Verdict policy

- `SUPPORTED`: evidence confirms the statement for its metric, population, and period.
- `CONTRADICTED`: evidence refutes the statement for that scope.
- `OUTDATED`: an earlier filing supports a current/latest claim and a later filing
  changes the same fact. Both filings must be cited.
- `NOT_ENOUGH_INFO`: available disclosures do not resolve the statement.

Explicit historical statements are judged at their stated period. “Latest” is
relative to the supplied filings. A company-wide headcount does not automatically
establish a regional subset.

## Python and model responsibilities

The model interprets claims, proposes searches, evaluates source meaning, and
submits a verdict. Python handles parsing, retrieval, persistence, usage accounting,
budgets, schema validation, and quotation authentication.

Additional checks cover named metric labels, simple dollar amounts in explicitly
scaled numeric rows, earlier matching balances already loaded into state, selected
employee-scope comparisons, and disagreement between a verdict and an explicit
conclusion in its explanation. Rejected submissions produce feedback; the model
must resubmit a consistent result within the remaining budget.

## Stopping and errors

Default budgets are eight model calls and sixteen tool calls across the workflow.
Planning submissions, final submissions, automatic retrieval, and rejected tool
attempts count toward usage. Memory operations are reported separately. The last
available model request is reserved for finalization.

Malformed submissions and tool errors are returned as feedback. Repeated unstructured
output, model failure, or exhausted budgets produce `status: incomplete` and a
specific stop reason. An incomplete result is not credited as a completed
`NOT_ENOUGH_INFO` judgment. Unavailable token counts remain null.

## Scope

The included PDFs preserve benchmark pagination. Page context carries headings
and table-unit disclosures into later chunks. Source matching tolerates whitespace
and typographic quotation differences without joining nonadjacent text.

The system uses lexical retrieval and text extraction, with no OCR or dedicated
cross-page table reconstruction. Numeric checks apply to supported simple formats
and assume the first numeric table column is the reported period. Compound claims
are not independently split. Exact citations establish provenance; semantic and
financial interpretation still require model judgment and reviewer inspection.
