# Filing Fact-Checker: complete technical reference

This reference describes the implemented Filing Fact-Checker, its reasoning, evidence contracts, operational behavior, evaluation, and remaining limitations. It is intended to stand alone as context for a technical discussion or another assistant. Statements about implemented behavior refer to the repository snapshot preceding this document, commit `90b1afd`. The final benchmark records application-source hashes matching `d6a7e14`. Subsequent architecture and presentation commits changed documentation and artifacts, not the evaluated application logic.

The public repository is https://github.com/cyash24f3/fillingfactz. The system checks claims against three supplied historical CrowdStrike filings. Dates and amounts below describe those files, not the company's present position. Implemented safeguards, intended verdict policy, measured outcomes, and proposed extensions are distinguished throughout. No finite reference or development benchmark guarantees correct answers to every possible unseen claim.

## 1. Problem, users, and evidence boundary

The assignment addresses an analyst workflow in which AI-generated company summaries contain individual factual statements. An analyst needs to establish whether each statement agrees with official disclosures, understand changes between reports, and inspect the original evidence. Producing persuasive prose without traceable evidence would not solve this problem. The product therefore treats the source-backed report as its central output.

A request contains one statement. The result contains a classification, a short explanation, exact quotations with filing and PDF-page provenance, operational status, and measured resource usage. Streamlit supports individual and batch reviews. FastAPI exposes synchronous-result and streaming interfaces. The command-line interface and evaluator use the same Python workflow directly.

Only the supplied filings can establish facts. The model receives no web-search tool and cannot make its pretrained knowledge authoritative. This restriction improves reproducibility and makes source coverage explicit. It also limits conclusions: an undisclosed fact can be true outside the corpus while remaining unresolved here. Missing evidence is not proof of falsehood.

The architecture favors a small inspectable implementation over distributed infrastructure. Three long reports justify retrieval, but do not justify a separate search cluster, embedding service, task broker, or complex agent hierarchy by default. The main engineering challenge is preserving evidence meaning while controlling probabilistic model behavior.

## 2. Assignment requirements and delivered artifacts

The required stack is Python 3.11 or later, LangGraph, FastAPI, Streamlit, and an accessible LLM. The assignment requests an adaptation of MERMAID through a Decomposer, an iterative Executor, tools, and reusable evidence memory. It also requires bounded reasoning, malformed-output handling, exact citations, streaming progress, at least twenty labelled statements, and comparisons with memory disabled and with one agent.

The repository includes application modules, original PDF copies, the filing manifest, twenty labelled statements, expected evidence references, automated tests, saved predictions, usage summaries, environment metadata, and source hashes. Documentation covers architecture, design decisions, evaluation, requirements, and validation. GitHub Actions checks deterministic behavior without requiring a running local model.

The architecture deliverable is a native Excalidraw board with nine frames and 348 editable elements. Its sections cover the overview, retrieval, agents, state, evidence validation, interfaces, contracts, evaluation, and deployment. The presentation contains twenty slides, editable tables and diagrams, actual reviewer imagery, worked examples, speaker notes, and a live-demo guide.

Optional features remain separate from requirements. Semantic reranking, OCR, independent verification of compound subclaims, and durable graph resumption are not implemented. Adding a filing can reuse unchanged PDF parsing caches, but corpus changes still rebuild the combined SQLite index. Describing that as fully incremental indexing would overstate the implementation.

## 3. Verdict semantics and execution status

`SUPPORTED` means evidence confirms the statement for the relevant metric, population, date, and reporting period. `CONTRADICTED` means evidence refutes that same scoped claim. `OUTDATED` means an earlier filing supports a current or latest-state assertion and a later filing changes the same fact. `NOT_ENOUGH_INFO` means the available disclosures do not resolve the assertion.

Temporal qualification changes the classification. July cash can remain historically correct when a later October balance differs. Calling the July amount the most recently reported balance creates an outdated assertion. The term latest is relative to the supplied corpus, not the calendar date of execution.

Execution status is an independent axis. A complete result has passed the submission gate. An incomplete result records failure to obtain an accepted submission within operational constraints. The implementation uses a missing-information fallback label for several incomplete outcomes, but the UI flags that fallback and the evaluator never awards accuracy credit merely because it matches the gold label.

There is no numeric confidence threshold that automatically ends research. Successful termination means the model submitted a structured candidate that the deterministic gate accepted. That acceptance establishes particular contracts, not infallible semantic correctness. Similarly, complete missing-information reasoning does not mathematically prove absence throughout every possible interpretation of the filings.

## 4. Corpus identity and financial reporting context

The manifest lists three CrowdStrike reports: a 10-K for the fiscal year ended January 31, 2024, filed March 7, 2024; a 10-Q for July 31, 2024, filed August 29, 2024; and a 10-Q for October 31, 2024, filed November 27, 2024. Their identifiers are `10k_2024_01_31`, `10q_2024_07_31`, and `10q_2024_10_31`.

Reporting period and filing date serve different purposes. The period identifies what the numbers describe. The filing date orders publication. A newer filing can contain comparative values from an older date, so document recency alone cannot determine the applicable financial value.

CrowdStrike's fiscal year ends January 31. Fiscal 2025 therefore largely overlaps calendar 2024. Annual flow measures such as revenue differ from point-in-time balances such as cash. Quarterly or year-to-date revenue cannot automatically establish a full annual result. Forecasts and guidance also differ from completed actuals.

The included PDF copies anchor pagination. References use one-based PDF page numbers, which may differ from printed report numbers or a differently rendered SEC webpage. The manifest retains official source URLs, but runtime verification reads local indexed text. Opening a source URL is a reviewer convenience, not an additional evidence-fetching step performed by the agent.

## 5. Runtime topology and architectural boundaries

The local deployment has three principal processes: Ollama on port 11434, FastAPI on port 8000, and Streamlit on port 8501. The UI sends HTTP requests to FastAPI. The API constructs and invokes the LangGraph workflow. The workflow uses the Ollama client and local SQLite stores. CLI and evaluation commands invoke Python service or graph functions without HTTP.

The data path begins with PDF files and manifest metadata. PyMuPDF extracts text, preparation builds page-aware passages, and SQLite FTS5 indexes them. Python retrieval returns canonical passages. The model interprets the claim and evidence, proposes tool calls, and eventually submits a verdict candidate. Python authenticates citations and selected consistency conditions before assembling the report.

This separation makes the application easier to reason about. Transport code does not own verdict policy. Streamlit does not perform independent fact checking. The model cannot execute arbitrary Python because its action surface is a registry of named tools. Persistent storage is independent from the transient conversation.

The process topology is intentionally local. There is no distributed queue, tenant identity service, shared inference scheduler, or remote persistence layer. FastAPI serializes its own verification requests, but that lock does not coordinate separate CLI processes or multiple API workers. These boundaries are important when discussing scalability or production deployment.

## 6. Module responsibilities and package structure

`models.py` defines Pydantic contracts. `config.py` centralizes project paths, model name, chunk size, overlap, and index version. `documents.py` loads and validates manifest records. `ingestion.py` parses PDFs and prepares the corpus. `prepare.py` provides the package preparation entry point.

`retrieval.py` implements SQLite searches, passage reads, page reconstruction, and bounded neighboring-page context. `context_views.py` produces compact model-facing representations. `tools.py` defines argument models, registry metadata, handlers, query cleaning, and rank fusion.

`decomposer.py` creates a claim plan. `agent.py` contains the Executor state, prompts, nodes, routing, accounting, and submission loop. `graph.py` coordinates initialization, planning, memory recall, verification, and persistence. `memory.py` manages the evidence store. `llm.py` isolates Ollama inference and response metrics. `evidence.py` and `periods.py` implement quotation, monetary, population, and reporting-period checks.

`service.py` defines verification requests and async orchestration. `api.py` handles HTTP routes and SSE encoding. `ui_client.py` validates streams and batch inputs. `streamlit_app.py` renders the reviewer. `evaluate.py` compares configurations, while `api_evaluate.py` exercises real HTTP streams. `cli.py`, root `main.py`, and root `workflow.py` expose command-line execution. `watch_graph.py` illustrates streamed graph events. Small modules keep contracts reusable without introducing unnecessary services.

## 7. Schemas and representation changes

Pydantic models separate untrusted proposals from validated application objects. `Filing` constrains report metadata. `Passage` retains source identity, hash, page, offsets, text, and context. `ClaimPlan` describes the research target. `VerdictCandidate` contains the model's label, explanation, and requested citations. `Evidence` enriches accepted citations with canonical provenance. `VerificationResult` is the complete service contract.

A JSON document is serialized text. `json.loads` turns that text into Python values, usually a dictionary. `model_validate` then constructs a typed Pydantic instance. Printing that instance can show `field=value` notation, which is its representation, not plain-English conversion or lost data. `model_dump` returns Python data again, while `model_dump_json` serializes it as JSON text.

JSON Schema describes allowed structure. It is distinct from an instance carrying actual values. A model returning `properties` and field definitions instead of facts has emitted schema-shaped content, not a valid result. Strict validation catches that distinction.

Most core schemas forbid unexpected fields. Tool argument validation and candidate validation use strict mode to reduce coercion. `TypedDict` graph state provides a static structural description, but it does not itself perform Pydantic-style runtime validation. Runtime guarantees come from explicit validation calls and node logic. This distinction prevents treating type annotations as complete input enforcement.

The final report also exposes `searched_filings`, `read_passage_ids`, `research_plan`, and `decomposer_status`, making coverage and planning inspectable without reconstructing every event. `input_tokens` and `output_tokens` remain separate fields. `memory` contains enablement, namespace, recalled passage identifiers, saved passage count, and operation counters. These structured fields support automated downstream checks and reproducible comparisons independently of displayed prose.

## 8. PDF extraction, chunk boundaries, and provenance

`parse_pdf` opens PDF bytes with PyMuPDF and extracts each page using text mode with sorted reading order. It splits page text into 1,800-character chunks with 300-character overlap, giving a 1,500-character step. These are character limits, not token counts. A chunk never deliberately joins two PDF pages.

The passage identifier encodes filing, one-based PDF page, and zero-based chunk index, for example `10k_2024_01_31:p22:c1`. Each passage stores the original extracted text and its start/end offsets within the page. It also carries form, reporting date, filing date, URL, PDF SHA-256, table-of-contents flag, and page context.

Overlap preserves sentences near boundaries but increases index size and can produce repeated matches. Keeping page boundaries simplifies citation navigation and reconstruction. Character chunking is straightforward and stable, but it can split tables or sentences imperfectly. Semantic chunking could improve coherence while adding parser complexity and different reproducibility challenges.

The system detects likely table-of-contents pages among the first six pages when the text names a table of contents and contains several Item headings. This is a heuristic, not a universal document classifier. A PDF yielding no readable passages raises a clear error mentioning OCR. The application does not silently substitute generated text for unreadable evidence.

## 9. Page context and model-facing compaction

Chunks below a table heading may lose the units or date labels that determine their meaning. `page_context` retains the first five compacted page lines and parenthetical unit disclosures containing thousands, millions, or billions. It also handles unit text wrapped across lines and caps the retained context at 1,200 characters.

`compact_text` removes blank lines, a literal table-of-contents heading, selected SEC print headers, and excess horizontal whitespace. `compact_passage` sends only passage ID, filing ID, page, reporting dates, page context, and compacted text. Larger provenance fields remain available in canonical storage and final evidence objects.

Compaction reduces prompt cost while preserving the original source separately. The model sees a normalized representation, but citation validation maps requested quotations back to original text. Page context helps interpretation without becoming permission to manufacture a single quote by joining a heading to a distant row.

`read_page_context` exposes the first chunk from the requested page and available immediate neighbors, at most three complete chunks. It also lists other passage IDs for navigation. Listing an ID does not mark its content as read. The model must explicitly read a navigation-only passage before citing it. This bounded approach recovers context without loading entire neighboring pages into every prompt.

## 10. Preparation caches and SQLite index construction

Preparation computes a SHA-256 for each PDF and a fingerprint combining filing metadata, PDF hash, PyMuPDF version, index version, chunk size, and overlap. Including parser and configuration versions invalidates stale caches when extraction behavior changes. A corpus fingerprint then combines the source fingerprints.

If the existing SQLite metadata contains the same corpus fingerprint, preparation returns an index cache hit. Otherwise it attempts to reuse each filing's parsed JSON cache. Missing, invalid, or changed caches trigger parsing for that file. The combined FTS index is rebuilt transactionally from the resulting passages. Forced preparation bypasses both cache checks.

The virtual `passages` table indexes text using `porter unicode61`. Passage ID, filing ID, table-of-contents flag, and serialized payload are unindexed fields. Payload preserves the typed passage. An `index_meta` table stores the corpus fingerprint. SQL values use parameters rather than interpolated user text.

This is parsed-source caching, not an LLM answer cache. Repeating a claim still invokes inference. Preparation also reads source bytes to calculate fingerprints, so a cache hit is not zero filesystem work. The outer initializer and standalone verifier both call preparation, producing a small repeated check. That is a possible optimization, not a claim that current request initialization is free.

## 11. Search ranking, query fusion, and coverage

`search_filings` extracts up to twenty-four alphanumeric query terms and constructs a quoted OR expression. It searches each selected filing separately, excludes flagged table-of-contents rows, ranks with SQLite BM25, and returns bounded snippets plus source-labelled IDs. OR search improves recall but can admit weak matches. Porter stemming helps morphological variants without providing full semantic similarity.

`search_and_read` cleans generic query words and fuses query variants. With multiple variants it retrieves up to three candidates per filing per query, sums reciprocal-rank contributions `1 / (60 + rank)`, and selects the requested number per filing. It avoids comparing raw BM25 magnitudes across different queries. A passage appearing in several useful rankings gains agreement credit.

Bootstrap uses the first planning query and the original statement as an additional query when different. This protects specific amounts, metrics, and qualifiers that a broad generated query might omit. Default retrieval reads one selected passage from each filing. Later searches can request up to three per filing.

Every filing must be searched before acceptance. This prevents concluding from only the first favorable report. It does not mean every passage was read or every possible contradiction was found. Search coverage is an auditable procedural condition, while sufficient retrieval remains a substantive limitation.

## 12. Tool registry and model action selection

The model receives tool names, descriptions, and JSON argument schemas through Ollama's native function-calling interface. It chooses a named action based on these contracts and the current conversation. Python executes the call. The model never learns tool behavior solely through random trial or by inspecting arbitrary Python implementations.

Exposed tools are `search_and_read`, `read_passage`, and `read_page_context`. `submit_verdict` is a special terminal proposal handled inside the Executor. `list_filings` and `search_filings` remain registry functions but are hidden from the normal model schema because Python supplies the catalogue and combined retrieval avoids extra search-then-read turns.

Arguments forbid extra fields and constrain query length, result limits, page numbers, and optional additional queries. Unknown names or invalid arguments produce errors. Adding an ordinary retrieval tool generally requires a schema, description, handler, and registry entry, rather than changes throughout the Executor. A tool with new state semantics or side effects would need additional integration and tests.

A single logical search-and-read tool can run several SQL searches and passage reads. Therefore reported tool calls count application actions, not low-level database operations. Multiple requested tools in one model response execute sequentially. Submission must be the only call in its response, preventing ambiguous mixtures of unfinished research and finalization.

## 13. Local inference configuration and model choice

`llm.py` creates an Ollama client targeting `http://127.0.0.1:11434` with a 120-second request timeout. `ask_model` selects `qwen3.5:9b`, passes messages and tool schemas, disables the explicit thinking channel, requests temperature zero, sets an 8,192-token context and a maximum of 1,800 generated tokens, and keeps the model available for ten minutes.

Local inference meets the bring-your-own-model requirement without a paid API key. It also keeps the application independent from remote-provider availability. The tradeoff is local RAM pressure, hardware-dependent latency, and responsibility for installing a compatible Ollama/model combination. A nine-billion-parameter model name does not by itself establish exact quantization, loaded memory, accuracy, or speed.

Temperature zero reduces sampling variation but does not guarantee identical results across model builds, execution environments, or prompt changes. Disabling explicit thinking does not remove the model's capacity to interpret evidence. It limits a particular output mode and helps control generation overhead. Native tool calls provide structured proposals, but schemas remain necessary because malformed or semantically wrong arguments still occur.

The recorded environment identifies a model digest. Its metadata leaves some quantization details blank, so a specific quantization format should not be asserted. Context length is finite, and the application does not implement a general automatic history summarizer. Deduplication and bounded retrieval reduce, rather than eliminate, context pressure.

## 14. Decomposer design and fallback behavior

The Decomposer describes what needs checking, rather than deciding whether the claim is true. Its prompt preserves dates, quantities, units, negation, and qualifiers, and treats the statement as data. It asks for exactly one `submit_plan` call. The typed plan contains subject, relation, object, optional attribution, optional time reference, one to six topics, and one to four keyword queries.

Nullable attribution and time fields are still schema fields. Their nullability permits absence of a value, not necessarily omission of a required key. Empty strings for those two fields normalize to null. Subject, relation, and object must contain text. This distinction surfaced in the real final T18 run, where an empty object caused a validated fallback.

The function attempts one planning model request. It records the attempted model call even on failure. It counts at most one returned planning submission, rejects multiple calls or an unexpected function name, and returns fallback status when validation or transport fails. It does not retry planning indefinitely or silently replace missing facts with guesses.

Fallback means the Executor proceeds with the original claim and fresh retrieval. This keeps planning an optional aid rather than a single point of failure. A compact plan is simpler than a full knowledge graph and sufficient for this small corpus. It does not independently split or aggregate compound claims.

## 15. Outer LangGraph lifecycle

`build_graph` creates an outer `StateGraph` with initialize, decompose, recall, verify, and remember nodes in that order. Initialization strips the statement, rejects emptiness, records a monotonic start time, and prepares the corpus. Planning can be disabled, in which case its usage is zero and its status explicitly says disabled.

Recall creates `MemoryStats`, optionally loads relevant passages, and emits memory events. Recoverable memory errors become trace events, allowing verification to continue. Verify subtracts planning consumption from the total budgets before running the Executor. It then combines planning and execution usage, attaches the research plan and memory statistics, and builds one trace with stage labels.

Remember persists evidence only when memory is enabled, execution completed, and accepted evidence exists. A complete missing-information result can have contextual evidence and therefore can also save passages. A complete result with no evidence performs no write. Storage errors do not retroactively change the accepted verdict, but they remain visible in the trace.

The final elapsed time covers initialization through the remember node. It includes preparation checks, planning, recall, verification, and attempted persistence. API queue waiting occurs before graph initialization and is excluded. The graph is compiled per request. That is simple and isolates options, although reusable compiled graphs could reduce minor orchestration overhead when model latency no longer dominates.

## 16. Executor graph and accumulated state

The nested Executor has bootstrap, model, and tools nodes, with conditional routes back to model or to termination. `ExecutorState` holds the statement, messages, pending calls, searched filings, read passage IDs, trace, bootstrap query, initial passages, counters, format reminders, stagnant-search count, and optional result. Nodes copy list containers before making updates.

Initial messages contain system policy and a JSON user payload with the claim, plan, catalogue, latest filing date, and latest annual reporting period. Bootstrap performs automatic retrieval, merges recalled and fresh passages by ID, marks actual loaded IDs as read, and appends an initial-evidence message. Bootstrap failures become visible feedback while the loop may still recover through later tools.

Each model response appends an assistant message containing its content and tool calls. The tools node validates and executes requests, updates coverage/read sets, and appends a tool-role message containing serialized observations or an error. The next model request receives the accumulated conversation. State does not live invisibly inside an abstract agent persona.

Repeated search hits retain their IDs but omit already-loaded full passage text. This avoids paying prompt tokens for the same content repeatedly. Explicit single-passage reads remain possible and can repeat text. The implementation uses explicit list replacement, not an append reducer that automatically merges parallel node outputs. Current execution is sequential, so reducer conflict resolution is unnecessary.

## 17. Concrete execution and call accounting

The recorded full-workflow T15 run illustrates the common short path. The Decomposer makes one request and submits a plan. Memory recall runs separately. Python performs one automatic search-and-read action across all filings. The Executor then makes one model request and accepts a `submit_verdict` call. Accepted evidence is saved afterward.

That path reports two model calls and three tool calls: planning submission, bootstrap retrieval, and final verdict submission. It does not require four model calls because there are four verdicts, or three model calls because there are three PDFs. One tool result can contain several source passages, and one model turn can inspect them together.

Messages can be understood as an ordered record: system policy, claim/context, initial evidence, assistant tool request, tool observation, and later assistant proposal. The final accepted action ends the graph. The report trace separately records events such as model completion, tool requests, errors, and verdict acceptance. Events summarize execution without exposing a private chain of thought.

Model calls count inference attempts. Tool calls count dispatched logical actions, including rejected submissions. Memory reads and writes are separate operation counters. LLM turns, graph transitions, source passages, database queries, and memory hits are different quantities. Confusing them makes an efficient two-call workflow look inexplicably incomplete or makes a large graph-step budget appear to imply unnecessary model requests.

## 18. Budgets, finalization, and stopping guarantees

Default total budgets are eight model calls and sixteen tool calls across planning and verification. With planning enabled, configuration requires at least two of each. The service permits model limits up to twenty and tool limits up to forty. The benchmark CLI uses minimum two even for single-agent comparisons, while lower-level single-agent execution can accept one model call.

Before a model request, exhausted budgets terminate incomplete. When only one model or tool slot remains, the model receives only the final-submission schema. A warning appears when two slots remain. Two successive search actions that add no new passages also switch to finalization. A search finding new passages resets the stagnation count.

Finalization does not automatically force a confident answer. It asks the model to submit the warranted classification using available evidence, with all existing citation requirements intact. Incorrect candidates can still be rejected. If no slots remain afterward, the run ends incomplete. No budget is secretly expanded to obtain a passing label.

Repeated prose without tool calls receives one format reminder, then invalid-output termination. A model transport failure immediately produces an incomplete model-error result with unknown token totals. The LangGraph recursion limit is another orchestration safeguard, computed as twice the Executor model budget plus eight. It is not a count of documents or an instruction to run every possible iteration.

## 19. Submission gate and its actual guarantees

`submit_verdict` is validated as a strict `VerdictCandidate`. Explanations must be between ten and three thousand characters. Evidence is a bounded list of at most eight citation requests, each containing a passage ID and a nonempty quote up to four thousand characters. Submission alongside other tool calls is rejected.

`validate_candidate` checks explicit label/explanation inconsistency, all-filing search coverage, required citations for decisive labels, supported future-annual restrictions, read-before-cite provenance, original quote matching, selected financial consistency, rounding contradictions, employee scope, and the two-filing minimum for OUTDATED. The Executor separately applies supported-metric label checks afterward.

The label/explanation check is deliberately narrow: it catches a final sentence explicitly naming an uppercase verdict that disagrees with the field. It is not a general natural-language contradiction detector. Similarly, the OUTDATED structural check requires at least two filing IDs. Generic confirmation that they support the same fact in proper temporal order still depends on model judgment. Numeric current-balance checks strengthen selected cases but do not prove all temporal semantics.

Accepted evidence metadata comes from canonical passages, not model-generated page numbers or URLs. Duplicate passage/quote pairs are removed. This distinction between proposal, authentication, and semantic interpretation is fundamental. A typed, traceable report can still contain reasoning errors beyond the implemented checks.

## 20. Exact quotations and reversible normalization

PDF extraction introduces whitespace changes, wrapped lines, and quotation-style differences. Literal string equality would reject some correct citations. Conversely, removing punctuation indiscriminately could authenticate changed words. The implementation normalizes whitespace, maps curly quotation styles, preserves internal apostrophes, and records each normalized character's original position.

`find_original_quote` searches for the normalized requested quote as a continuous substring of normalized source text. It then uses the position map to recover the exact original span. Reports therefore restore the source's punctuation and spacing rather than echoing the model's approximation. Normalization does not change case, invent missing words, or permit nonadjacent fragments to become one quotation.

When matching fails, a bounded helper may suggest a substantial literal shared span from the same passage. It requires enough characters, preserves a numeric anchor when the rejected request contained numbers, limits suggestion length, and rechecks continuity. The suggestion is feedback for model reconsideration, not automatic acceptance or proof of relevance.

This resolved the earlier straight-versus-curly apostrophe problem without weakening word integrity. A heading and distant cash row cannot be joined using an ellipsis and called verbatim evidence. Units may be interpreted from page context while the quote remains a short continuous row. That separates semantic context from quotation authentication.

## 21. Monetary amounts, precision, and metric identity

The numeric guard recognizes USD, US-dollar symbols, comma-separated numbers, decimals, and supported thousand/million/billion suffixes, including compact forms. It uses `Decimal` rather than binary floating point. It applies narrowly to simple equality-like claims with one monetary amount and one recognized metric. Negations, inequalities, ranges, and unsupported formats remain semantic judgments.

For a scaled approximate expression such as USD 3.06 billion, the last displayed decimal gives a half-unit tolerance: USD five million. The source value USD 3,055,555,000 lies within that precision interval. An explicitly exact statement disables this allowance. A coarse narrative amount such as USD 3.1 billion cannot refute an overlapping finer approximation merely because printed digits differ.

The guard reconstructs canonical page text to recover complete numeric rows and preceding headings. It resolves source units, selects an unambiguous requested column, and compares normalized amounts. It avoids treating percentage rows as dollar rows. Error feedback can identify the resolved value, source page, and numeric column, helping the model correct rather than repeat its mistake.

Supported-metric checks recognize labels including subscription revenue, total revenue, cash, receivables, assets, and liabilities. They require relevant quoted row labels for SUPPORTED decisions. These regex-based checks are domain safeguards with limited coverage, not a complete financial ontology or arbitrary arithmetic engine.

## 22. Period binding and historical/current distinctions

`periods.py` extracts selected English reporting dates and fiscal-year expressions. Quarterly and year-to-date qualifiers suppress annual-year inference. `table_column` searches backwards through the preceding page text for an appropriate year-header row, then binds the requested fiscal year or explicit balance date to an unambiguous column.

If a requested annual fiscal year appears in a quarterly filing's flow table, the helper declines automatic annual interpretation. Repeated years such as October 2024 and January 2024 require nearby month/day headings to distinguish columns. Ambiguous bindings return no deterministic comparison rather than inventing an interpretation. Some current-period cases use a first-column fallback, so correctness still depends on supported table structure.

Future annual actuals receive a separate safeguard. When a simple monetary claim describes an annual period ending after the latest supplied filing date, earlier actuals or interim numbers cannot establish or refute it. Forecast, guidance, and interim expressions are excluded from this shortcut because they need their own disclosure search.

For selected current balance claims, the guard also examines relevant already-loaded uncited rows. If an earlier row matches the asserted balance and a later filing changes it, a CONTRADICTED candidate is rejected with guidance toward OUTDATED. It does not secretly search the entire corpus during validation or automatically relabel the candidate.

## 23. Population scope and incomplete information

Employee counts expose a general logical problem: a fact about a superset does not automatically determine an exact subset. A company total of 7,925 employees is compatible with a US-based count of 5,000. It therefore cannot, by itself, support or contradict that exact regional count.

`check_employee_scope` recognizes selected regional count phrasings and looks for a direct quantitative relationship between number, employee term, and geography in the quotations. US and UK aliases receive explicit handling. A location mentioned elsewhere, such as a statement about union representation, does not automatically scope a nearby global headcount.

The guard permits a mathematical upper-bound contradiction when the claimed subset exceeds every quoted total. It also leaves company-wide claims outside the regional restriction. These rules catch specific overinterpretations while retaining valid comparisons. They do not implement general set reasoning across every possible employee category, geography, and date.

The same caution applies beyond workforce facts. Revenue concentration is different from receivables concentration, and a qualitative retention discussion does not establish a precise attrition percentage. The system must preserve relation and scope, not just matching entities and numbers. NOT_ENOUGH_INFO is the honest outcome when disclosures cannot resolve those distinctions, subject to retrieval's practical limitations.

## 24. Persistent evidence memory internals

`memory.py` uses a separate SQLite FTS5 virtual table containing namespace, passage ID, filing ID, source key, stored quote, and full source text. Only text is searched. A source key hashes the complete serialized canonical passage, covering source bytes, text, offsets, metadata, and context. It is stricter than remembering a document name.

Recall extracts alphabetic topical terms, removes generic language, company names, months, reporting words, quantities, and financial unit terms, and keeps ordered unique terms. It first retrieves up to eight times the requested limit using BM25 within the namespace. Additional FTS term checks require agreement on up to three distinct topical terms, using consistent stemming.

Candidates must still exist in the current corpus, match the stored source key, avoid table-of-contents passages, and authenticate their saved quotation. Invalid candidates become cache misses. At most three passages return. Recall supplies canonical passages rather than cached verdicts or model-written summaries.

Writes deduplicate passage IDs, check the current PDF hash and quote, delete an older entry for that namespace/passage pair, and insert the current evidence transactionally. One stored quote accompanies each passage entry. Namespaces isolate sessions logically, not cryptographically. SQLite uses a ten-second connection timeout. Memory errors remain optional-performance failures rather than reasons to trust stale content.

## 25. State lifetimes and alternative cache designs

There are several distinct reuse mechanisms. Parsed JSON caches avoid repeated PDF extraction. The corpus index avoids rebuilding unchanged searchable content. Evidence memory supplies previously authenticated passages to related claims. The current graph conversation carries observations within one invocation. Ollama's keep-alive retains loaded model resources. These mechanisms have different invalidation rules and should not all be called agent memory.

The application does not persist LangGraph checkpoints, final-answer caches, complete conversations, or model hidden state as its evidence store. Streamlit session state retains reviewer records for rerendering, but it is not the cross-request knowledge mechanism. Downloaded reports and benchmark predictions are durable artifacts, not an automated answer source.

An exact-response cache could reduce repeat-claim latency further, but would need a key covering normalized claim, corpus fingerprint, model and prompt versions, validation policy, and configuration. It would also complicate comparisons intended to measure model reasoning and evidence reuse. The chosen design avoids replaying a stale classification when new filings arrive.

Memory freshness alone does not guarantee latest-state reasoning. An unchanged old PDF remains valid historical evidence. The system must also search newer filings and compare appropriate periods. That is why recall supplements fresh retrieval rather than replacing it. The cost is retained search work and additional prompt context, which explains why memory can save calls without producing large token reductions.

## 26. Service layer and HTTP request contracts

`VerificationRequest` strips surrounding whitespace and forbids extra fields. It accepts a statement of one to four thousand characters, booleans controlling planning and memory, a namespace of one to eighty characters, and bounded model/tool budgets. A model validator rejects settings that cannot accommodate the selected configuration before graph execution begins.

`verify_once` constructs the graph, awaits its invocation, and validates the final result. FastAPI's `POST /verify` exposes that typed result. Exceptions are logged and returned as HTTP 500 details truncated to a bounded length. Request validation failures occur separately, normally as framework validation responses.

`GET /health` returns service status and configured model name. It does not perform live inference or prove that Ollama currently has enough memory. `GET /docs` serves Swagger, and `GET /openapi.json` exposes the contract. Visiting `/verify` in an address bar sends GET, so Method Not Allowed is expected rather than evidence that POST is broken.

Service and transport are separated so CLI, benchmarks, and HTTP share one core workflow. The HTTP layer does not receive expected labels, reference answers, or benchmark IDs. This avoids separate implementations drifting in verdict behavior. Model availability, source preparation, semantic validation, and transport correctness still require distinct operational checks.

## 27. SSE transport and terminal-event semantics

`POST /verify/stream` returns `text/event-stream`. Each frame includes an event field and JSON data containing type, run ID, and an object payload. The API assigns a UUID, emits queued before acquiring its run lock, and emits started once service execution begins. LangGraph custom events and node updates become step events.

After the workflow finishes, the service validates its last result update and emits result, then done with outcome result. Operationally incomplete verification can still travel as a valid result followed by done. That transport success is separate from the report's complete/incomplete status. Service exceptions instead emit error and done with error outcome.

Cancellation is re-raised, so an interrupted client connection should not be described as guaranteed to receive done. The implementation does not persist event streams for later replay, emit SSE sequence IDs for reconnection, or provide a durable background-job identifier. It also lacks a general heartbeat producer, although its client can ignore heartbeat comments.

SSE fits one-way progress from server to reviewer and avoids the complexity of a bidirectional WebSocket protocol. The UI initiates the POST through HTTPX rather than relying on browser EventSource, which ordinarily opens GET requests. Streaming improves visibility during slow inference. It does not inherently reduce model work or time to the final verdict.

## 28. Client protocol checks and reviewer behavior

`parse_sse_lines` accumulates data lines until an empty separator, supports multiline data and comments, parses JSON, and validates the basic event envelope. It rejects partial trailing frames. `stream_check` rejects HTTP errors, unexpected content types, mixed run IDs, invalid result schemas, missing final reports, and connections ending before done.

The HTTPX client uses a five-second connect timeout and a 180-second read timeout. These are transport settings, distinct from the Ollama request timeout and graph call budgets. They are not a single end-to-end service deadline. A slow queued request can therefore require different operational treatment from a failed model call.

Streamlit keeps single and batch records in session state. Each record includes statement, settings, events, result, and error. It shows live steps, verdict, exact evidence, source links, raw JSON, usage, and downloads. Incomplete reports receive explicit warnings rather than a normal success label.

Batch input accepts lines or JSON statements, including uploaded UTF-8 files. Uploads take precedence over the text box. Parsing extracts only statement text, discarding expected labels or unrelated gold fields. Between one and one hundred statements are allowed. Batch execution is sequential, retains each report, and shows totals from returned results. Request failures can consume unreported resources, so the UI explicitly qualifies those totals.

## 29. Concurrency, sequencing, and resource ownership

FastAPI creates one `asyncio.Lock` during application lifespan. Both verification endpoints acquire it before running the workflow. This serializes inference requests within one API process, which is appropriate for a memory-constrained local model. Queued streaming requests can announce that they are waiting rather than appearing frozen.

The lock is neither distributed nor cross-process. Multiple Uvicorn workers, CLI invocations, or independent evaluators can still overlap. SQLite connections are opened per operation rather than held in a shared application pool. Transactions protect individual writes, but there is no coordinated global ingestion lock for unrelated processes rebuilding an index simultaneously.

Async service orchestration coexists with synchronous Ollama and SQLite functions. LangGraph supports invoking these nodes through its execution machinery, but the project does not implement a fully asynchronous model client or an independently cancelable inference scheduler. Client disconnection does not prove that all underlying synchronous computation stopped immediately.

Parallelizing three small local SQL searches would likely save little compared with model latency. Parallel claim execution could increase throughput on suitable inference infrastructure, but on one local model it may increase contention and tail latency. Sequential benchmark ordering also determines memory availability. Changing that ordering or concurrency would change the experimental condition and require a new reproducible evaluation.

## 30. Development failures and general fixes

The original full benchmark achieved 85% accuracy with eighteen completed cases. T09 and T20 exhausted budgets. T18 misused global headcount to refute a regional subset. T20's fallback happened to match its expected label but correctly received no credit because execution was incomplete.

Earlier extraction milestones exposed environment and representation issues: the wrong Python interpreter could not import installed packages, a schema-shaped response was not a facts instance, and server-side structured JSON mode returned an unsupported-operation error. The final architecture uses explicit virtual-environment setup, native tool submissions, and validation. These are development lessons, not claims that the current pipeline still uses the early single-document extraction script.

The final saved full run still contains recoverable errors. T02 initially submitted a quotation associated with the wrong passage. T14 tried joining table-heading text and a row using synthetic material. T17 proposed a contradiction despite an older matching balance. T18's Decomposer returned an empty required object. The system rejected or bypassed these problems and subsequently completed those cases.

These traces demonstrate recovery, not error-free model behavior. Fixes target general categories such as quote continuity, temporal ordering, scope, relevance, and stagnant search. The code does not route T17 to a predefined answer. Case identifiers remain evaluation metadata outside the agent's request path.

## 31. Labelled cases and evidence anchors

The development dataset contains seven supported, seven contradicted, three outdated, and three missing-information claims. Seventeen shared reference passages support its labels. The following compact map preserves the entire case coverage. Page numbers refer to the included PDFs. Missing-information references provide related context rather than standalone proof of absence.

| ID | Statement focus | Expected verdict | Source anchor |
|---|---|---|---|
| T01 | Fiscal year ends January 31 | SUPPORTED | July 10-Q, page 12 |
| T02 | Fiscal year ends December 31 | CONTRADICTED | July 10-Q, page 12 |
| T03 | 7,925 full-time employees on January 31, 2024 | SUPPORTED | 10-K, page 22 |
| T04 | 9,000 employees on that date | CONTRADICTED | 10-K, page 22 |
| T05 | Fiscal 2024 total revenue approximately USD 3.06 billion | SUPPORTED | 10-K, page 87 |
| T06 | Subscription revenue equals USD 3,055,555,000 | CONTRADICTED | 10-K, page 87 |
| T07 | Subscription accounts for 94% of fiscal 2024 revenue | SUPPORTED | 10-K, page 70 |
| T08 | Professional services account for 94% | CONTRADICTED | 10-K, page 70 |
| T09 | July 19 update caused certain Windows crashes | SUPPORTED | October 10-Q, page 33 |
| T10 | July 19 update did not cause Windows crashes | CONTRADICTED | October 10-Q, page 33 |
| T11 | No customer/channel partner reaches 10% revenue concentration | SUPPORTED | 10-K, page 92 |
| T12 | A customer/channel partner reaches 10% receivables concentration | CONTRADICTED | 10-K, page 92 |
| T13 | October cash equals USD 4,260,324,000 | SUPPORTED | October 10-Q, page 9 |
| T14 | October cash equals unscaled USD 4,260,324 | CONTRADICTED | October 10-Q, page 9 |
| T15 | Latest cash equals July's USD 4,038,536,000 | OUTDATED | July page 6 and October page 9 |
| T16 | Latest assets equal January's USD 6,646,520,000 | OUTDATED | Annual page 86 and October page 9 |
| T17 | Latest current liabilities equal July's USD 2,728,319,000 | OUTDATED | July page 6 and October page 9 |
| T18 | Exactly 5,000 US-based full-time employees | NOT_ENOUGH_INFO | Workforce context, annual page 22 |
| T19 | Fiscal 2024 voluntary attrition rate equals 5% | NOT_ENOUGH_INFO | Retention context, annual page 22 |
| T20 | Fiscal 2030 revenue forecast equals USD 20 billion | NOT_ENOUGH_INFO | Historical context, annual page 15 |

The full original wording, rationales, precise passage IDs, and quotations remain in `data/test_statements.json`. Paired cases isolate individual distinctions, but those similarities also make the set easier than arbitrary independent unseen statements.

## 32. Evaluation protocol and reproducible outputs

The evaluator validates at least twenty cases, unique IDs, all four labels, known references, exact quotations, and PDF-page agreement. Gold OUTDATED cases additionally require distinct earlier/later filings in valid filing-date order. That stronger gold-reference chronology check should not be confused with the runtime candidate's simpler two-filing structural minimum.

Full mode enables planning and memory. No-memory mode retains planning but disables evidence persistence. Single-agent mode disables planning while retaining memory. Each configuration starts with a fresh isolated namespace, processes the same ordered claims, and uses identical total budgets. Evidence can accumulate within a configuration but cannot leak across these namespaces.

Only statement and settings enter `verify_once`. Expected labels, gold evidence, case IDs, and rationales remain in the evaluator. A result counts correct only when complete and label-matching. This is classification accuracy conditioned on operational completion rules, not an independently scored semantic citation-entailment metric.

Each case updates predictions and summary files through a temporary-file replacement, preserving inspectable partial results after interruption. Run metadata records model, Python version, budgets, case order, corpus fingerprint, dataset hash, configuration, namespaces, and application-source hashes. The evaluator checks corpus and dataset stability after each case. It records source hashes at startup but does not continuously rehash every source module during the run.

## 33. Final measurements and original baseline

The final recorded run is `20261105T163921Z_96e9b031`. All sixty executions completed with matching labels. The saved engine hashes correspond to `d6a7e14`, while the original baseline identifies `25edfb1`. Later documentation commits do not invalidate those engine measurements because application sources remained unchanged.

| Configuration | Correct | Completed | Model calls | Tool calls | Tokens | Seconds | Memory reads/writes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 20/20 | 20 | 54 | 74 | 191,196 | 839.504 | 20/18 |
| No memory | 20/20 | 20 | 58 | 78 | 192,919 | 963.127 | 0/0 |
| Single agent | 20/20 | 20 | 35 | 54 | 158,559 | 772.186 | 20/18 |

The full baseline used 61 model calls, 81 tool calls, 266,260 tokens, and about 1,017.1 seconds. Full accuracy improved from 85% to 100%, with completion increasing from eighteen to twenty. That combines reliability and efficiency improvements rather than trading one for the other on this dataset.

Across final configurations, totals are 147 model calls, 206 tool calls, 542,674 tokens, and 2,574.817 recorded workflow seconds. There are twenty unique statements, not sixty unique cases. The corpus and development set were used during iteration. Neither 100% here nor twelve additional successful API checks proves universal correctness or a statistical production guarantee.

## 34. Efficiency changes and why they reduced work

Two optimization stages must be distinguished. The architecture already supplied the catalogue, bootstrap evidence, combined search-and-read, query fusion, and compact context at the saved baseline. Those choices reduced administrative turns compared with earlier prototypes, but they cannot be credited as new changes explaining the measured baseline-to-final delta.

The verified `25edfb1` to `d6a7e14` changes added stricter topical memory recall, passage deduplication within search observations, stagnant-search finalization, explicit reporting coverage, stronger period/precision/scope checks, and bounded page-context navigation. Wrapped-unit extraction also improved and the index version changed. These are the concrete revisions associated with the recorded comparison.

Context compaction removes print noise and unnecessary metadata. Passage deduplication prevents repeated search hits from appending identical text to the growing conversation. Because each model request resubmits accumulated context, preventing duplicates can save prompt processing repeatedly, not just once.

Topical memory filtering reduces unrelated evidence. Stagnation detection prevents repetitive search loops, and finalization reserves an opportunity to return a valid result. More informative numeric and quotation feedback helps rejected candidates recover without rediscovering known source context. These optimizations interact. The baseline-to-final comparison measures their combined effect; the repository does not contain isolated experiments assigning a precise percentage to each individual code change.

## 35. Exact efficiency gains and calculation boundaries

For full mode, saved tokens fell by 75,064, from 266,260 to 191,196, a 28.2% reduction. Model calls fell by seven, from 61 to 54, or 11.5%. Tool calls fell by seven, from 81 to 74, or 8.6%. Recorded elapsed time fell by 177.570 seconds, from 1,017.074 to 839.504, or 17.5%.

The token breakdown explains the improvement more precisely. Full-mode input tokens fell from 253,785 to 178,486, saving 75,299. Output tokens rose from 12,475 to 12,710, an increase of 235. The overall reduction therefore came from less input processing, despite slightly more generated output. It should not be described as shorter answers alone producing all savings.

No-memory mode reduced tokens by 19.9%, model calls by 1.7%, tool calls by 1.3%, and elapsed time by 11.4% against its own baseline. Single-agent mode reduced tokens by 30.5%, model calls by 7.9%, and tool calls by 6.9%, but elapsed time increased by 8.9%.

Across all configurations, total tokens fell from 735,133 to 542,674, approximately 26.2%. Combined workflow time decreased about 8.5%. Percentage reduction uses the earlier configuration's value as denominator. These comparisons concern fixed recorded runs with implementation changes, not a controlled causal estimate for every optimization independently.

## 36. Memory ablation and the meaning of reuse

Comparing final full mode with final no-memory mode isolates the enabled-memory configuration more closely than comparing different source versions. Both retain the Decomposer. Full uses 54 versus 58 model calls, 74 versus 78 tool calls, 191,196 versus 192,919 tokens, and 839.504 versus 963.127 seconds.

That corresponds to 6.9% fewer model calls, 5.1% fewer tool calls, 0.9% fewer tokens, and 12.8% less elapsed time relative to memory-off. Both achieved 100% development accuracy. Memory helps avoid some research turns, but its recalled passages also consume input context. Therefore fewer calls need not produce proportional token savings.

Each condition starts empty and reuses evidence only across its own ordered cases. Related pairs can benefit more than unrelated statements. Changing order, corpus topics, or namespace contents can change the benefit. Memory reads/writes of 20/18 count attempted persistence operations, not twenty successful recalls or eighteen unique passages.

Stale-source checks and fresh all-filing searches deliberately retain work. Removing them might look faster while weakening temporal reliability. The measured implementation favors authenticated reuse over maximum cache hits. A hit ratio alone cannot establish savings, and the current report does not offer a per-operation causal estimate of avoided inference.

## 37. Single-agent ablation and planning overhead

The final single-agent configuration uses 35 model calls compared with full mode's 54, a difference of nineteen. It uses 54 tool calls instead of 74, 158,559 instead of 191,196 tokens, and 772.186 instead of 839.504 seconds. Both classify all twenty development statements correctly with complete execution.

Removing planning avoids its inference and submission overhead, but can also change retrieval queries and later Executor behavior. The result is not obtained simply by subtracting exactly twenty calls from every metric. A simpler pipeline can outperform a more elaborate agent system on a small focused corpus.

The multi-agent configuration remains the default to satisfy and demonstrate the assignment's adaptation. The ablation makes its cost visible rather than assuming that more agents necessarily improve accuracy. Planning may help preserve complex scope or generate useful queries, but this dataset does not establish a universal advantage.

The code exposes planning as a setting so a reviewer can inspect the tradeoff. A production decision could use a validated complexity classifier to enable planning selectively, but such adaptive routing is not implemented. Adding it would require evaluating routing mistakes and counting the classifier's own latency and tokens.

## 38. Latency, tokens, and actual monetary cost

Tokens, inference calls, tool calls, latency, and money are related but distinct measurements. Local Ollama execution does not produce a provider token invoice in this project. No verified rupee or dollar saving is recorded. Local electricity, machine ownership, memory pressure, and opportunity cost still exist, but the benchmark does not measure them.

For a hypothetical hosted provider, an estimate would separately multiply input-token savings by input pricing and output-token savings by output pricing. Here input decreased while output slightly increased in full mode, so multiplying the total-token reduction by one arbitrary rate would be imprecise. Cached-input discounts and provider billing rules would require additional evidence.

Model response metrics record wall time, server duration, loading, prompt evaluation, generation, and output tokens per generation second when available. Ollama durations are converted from nanoseconds. Unknown token counts propagate as null through totals rather than becoming misleading zeros.

The reference environment is Apple M5, 24 GiB RAM, Python 3.12.13, and a warm local model. Full mode averages about 42 workflow seconds per development case, but individual cases vary. The single-agent baseline counterexample shows that lower tokens do not guarantee lower observed time. Thermal state, loading, scheduling, and generation behavior are plausible influences, not measured causal explanations for that specific difference.

## 39. Automated tests, live checks, and CI scope

The project records 92 automated tests. Categories cover agent recovery, budgets, stagnant retrieval, source quotation integrity, numeric scaling, rounding, dates, comparative columns, regional scope, page navigation, memory relevance and isolation, evaluation selection, HTTP contracts, SSE parsing, and Streamlit behavior.

Mocks deliberately supply malformed responses and failures to verify deterministic contracts. Such tests do not establish real-model accuracy. Conversely, sixty correct model runs do not comprehensively test every exception branch. The two forms of evidence complement each other. Twelve additional real HTTP/SSE cases cover paraphrases and financial edge conditions, with complete streams and matching labels.

GitHub Actions runs on Python 3.12, installs the pinned lock file, executes unittest discovery, and validates labelled source references. It does not download or run Qwen for every push. Model-dependent results remain saved artifacts with source and environment metadata. The workflow uses read-only repository permission and pinned action revisions.

The dependency lock records a reference environment, while `pyproject.toml` declares broader compatible ranges. Reproduction should prefer the lock for the recorded Python version. A clean installation was checked. Library versions and model digests can affect behavior, so a newly resolved dependency set should not automatically inherit the old benchmark's measured guarantees.

## 40. Security, trust, and source authenticity

The statement and source passages are untrusted content. Prompts explicitly treat them as data rather than instructions. Tool names are allowlisted, arguments are validated, SQL uses parameters, and the model has no arbitrary shell, filesystem-write, or web-search action. These controls reduce the consequences of prompt injection without proving complete resistance.

Hashes establish identity and detect changes relative to stored files. They are not digital signatures proving that a PDF genuinely originated from the SEC. Official URLs and curated local inputs provide the practical provenance boundary. Someone able to replace both files and trusted metadata can undermine that boundary.

The service targets localhost. It lacks authentication, authorization, per-user quotas, encryption configuration, and a hardened multi-tenant deployment. Namespaces are caller-supplied labels, not access-control boundaries. Error details and traces can expose source context, so external deployment would require deliberate redaction and policy choices.

Exact quotations limit fabricated evidence, but cannot prevent cherry-picking or semantic manipulation. Source evidence could be irrelevant despite authentic text. Human review remains valuable, especially for legal disclosures, ambiguous negation, or unsupported absence claims. These are present trust limitations, not features secretly solved by schema validation.

## 41. Operation, setup, and failure diagnosis

The reproducible setup clones the repository, creates a virtual environment, installs dependencies, pulls `qwen3.5:9b`, and runs `python -m filing_checker.prepare`. Start Uvicorn with `filing_checker.api:app` on localhost port 8000, then run `python -m streamlit run streamlit_app.py` separately. Ollama must be running.

A virtual environment isolates project libraries from externally managed system Python. A prompt displaying a virtual-environment label does not conclusively establish which interpreter executes. Explicitly using `.venv/bin/python` or checking the interpreter path distinguishes package installation from model installation. Downloading the Ollama model does not install the Python client library.

For diagnosis, separate layers: source-file presence and preparation, SQLite retrieval, model availability, workflow validation, HTTP status, stream completion, and UI display. A failed health route is different from a healthy API whose model request fails. A valid HTTP response containing incomplete status is different from transport failure.

Use `python -m unittest discover -s tests -v` for deterministic checks and `python -m filing_checker.evaluate --validate-only` for gold-reference validation. Selected IDs support focused real-model diagnostics. Full evaluation runs all configurations. The evaluator preserves dataset order even when IDs are supplied in another order, maintaining memory-comparison consistency.

## 42. Scaling and future architectural choices

For substantially larger corpora, lexical retrieval may need semantic retrieval and reranking. An evidence-preserving hybrid could retain BM25 for exact numbers and identifiers while using embeddings for paraphrases. That extension adds embedding versions, index costs, recall evaluation, and ranking latency. It should be justified by measured retrieval failures.

More users would require bounded admission, shared inference scheduling, persistent job state, and cross-worker coordination. A process-local lock cannot provide those guarantees. Database selection should follow actual concurrency and corpus needs. SQLite remains appropriate for this local workload, while a shared store and dedicated search service could become reasonable at larger scale.

Durable LangGraph checkpoints would require storage, versioning, replay semantics, and decisions about expensive in-flight model requests. OCR and table extraction would need page-coordinate provenance and quality checks. Compound claims would need separate subresults and an explicit aggregation policy rather than one ambiguous label.

Tool extensibility and module boundaries support these changes without claiming they are already implemented. New sources require manifest records and fingerprint-aware preparation. New metric validators require generalized examples and regression tests. Repeated benchmarks, held-out statements, reordered memory trials, and retrieval-quality measurements should accompany major changes. Architectural sophistication is useful only when it addresses an observed requirement or failure.

## 43. Presentation, architecture, and worked-result alignment

The twenty-slide deck follows the runtime story: task and corpus, architecture, preparation, agents, tools, state, memory, validation, financial interpretation, interfaces, worked verdicts, failures, evaluation, and operation. Excalidraw expands these into nine inspectable frames. Both are explanatory views of the same implementation rather than additional execution layers.

The recorded supported headcount case quotes annual PDF page 22 and reports two model calls, three tools, 4,507 tokens, and 17.811 seconds. Changing headcount to 9,000 yields contradiction from the same passage. The stale-cash example cites July page 6 and October page 9, distinguishing USD 4,038,536,000 from USD 4,260,324,000.

The regional-headcount example finishes missing-information after a planning fallback, demonstrating that failure handling can preserve correct overall behavior. Its quote supplies workforce context without proving an exact US count. The presentation's reviewer screenshot belongs to a separate validated UI run, so its counters need not match benchmark examples.

The presenter guide contains setup commands and four demo statements. Saved predictions provide evidence when live inference is slow. Presenting recorded outcomes as recorded, and live outcomes as newly executed, preserves the distinction between a reproducible demonstration and an unmeasured promise about every future request.

## 44. Consistency, idempotency, and measurement contracts

A repeated HTTP request is a new verification run. There is no idempotency-key store that returns an existing result for duplicate submissions. Repetition can produce new usage, different evidence selection, and additional memory writes. Within a namespace, memory replaces an existing passage entry rather than accumulating unlimited duplicates for that same passage. This storage behavior does not make inference itself idempotent.

Corpus preparation and memory writes use transactions, but they do not form one transaction covering an entire verification. A model request can finish before a later memory operation fails. The final accepted result therefore remains usable even when optional evidence persistence fails. Likewise, a dropped HTTP connection can leave uncertainty about whether the model completed work. Automatic retry would risk duplicate computation unless a durable request/result protocol were added.

The current trace supports diagnosis at the application boundary. It records action names, arguments, timing, errors, and accepted outcomes. It does not provide database-level query telemetry, process-wide resource accounting, or complete internal reasoning. Saved metadata identifies an evaluated source snapshot, while model digest and environment records help explain reproducibility. These records improve auditability without making model execution perfectly deterministic.

The source catalogue and prompts currently target one company. Adding more companies requires more than appending PDFs: retrieval must preserve entity scope, memory must prevent cross-company confusion, and request contracts must select the correct corpus. The present namespaces alone do not implement a company-aware authorization or routing system. Similarly, changing the model requires confirming native tool-call compatibility, schema adherence, context behavior, latency, and accuracy under the same evaluation protocol.

An eight-thousand-token context setting is an inference configuration, not proof that every bounded conversation fits. Character chunks, multiple recalled passages, schemas, retries, and accumulated messages all consume context. Deduplication reduces repeated content, but a sufficiently difficult case can still exceed practical context capacity. A robust extension would measure assembled prompt size and reserve room for generation before deciding which evidence to retain.

Finally, correctness and efficiency should be assessed together. Rejecting every hard claim as incomplete could reduce hallucinations while making the system unhelpful. Skipping validation could reduce latency while accepting unsupported answers. The recorded gains matter because the full configuration improved completion and label accuracy while reducing aggregate calls and input tokens. Future optimization should retain that joint accounting, including unsuccessful attempts, missing usage, source coverage, and report integrity. A smaller number in one metric is insufficient evidence of a better verification system.

## 45. Reference vocabulary and source navigation

A claim is the input assertion. A plan describes its verification target. A passage is canonical extracted source text with identity and provenance. A citation requests a continuous quotation from a read passage. A candidate is a proposed verdict. A report is the validated output, including execution status. A trace records observable actions and errors.

BM25 ranks lexical matches. FTS5 is SQLite's full-text search extension. Reciprocal rank fusion combines ranked lists. A namespace separates logical evidence collections. A fingerprint identifies source/configuration content. A checkpoint would persist graph execution state, which this application does not provide. An ablation disables a component to compare its measured contribution.

The primary source map is `filing_checker/` for implementation, `data/filings.json` for corpus identity, `data/test_statements.json` for labels, `results/benchmark/` for final predictions and usage, `results/baseline/` for the unchanged earlier run, and `results/api_validation/` for additional streamed checks. `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, and `docs/EVALUATION.md` connect those artifacts. `docs/architecture/` contains Excalidraw assets. `docs/demo/` contains presentation files and notes.

The defensible engineering description is a bounded, source-grounded, locally deployed verification workflow with explicit contracts and measured development results. Its strength is inspectable evidence and controlled recovery. Its remaining uncertainty lies chiefly in retrieval completeness, document interpretation, and model judgment beyond narrow deterministic safeguards.
