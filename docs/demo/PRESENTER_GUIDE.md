# Presenter guide

The full deck has twenty slides. For a short demo, present slides 1, 4, 13–16,
18–20 and keep the technical slides available for questions.

## Setup

From a fresh checkout:

```sh
git clone https://github.com/cyash24f3/fillingfactz.git
cd fillingfactz
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ollama pull qwen3.5:9b
python -m filing_checker.prepare
```

Keep Ollama running. Start the API and UI in separate activated terminals:

```sh
python -m uvicorn filing_checker.api:app --host 127.0.0.1 --port 8000
```

```sh
python -m streamlit run streamlit_app.py
```

Open http://localhost:8501 and check the API. Swagger is at
http://127.0.0.1:8000/docs. Its verification route requires POST.

## Live demonstration

1. Use the four claims in `demo-statements.txt`. Keep memory and Decomposer on,
   with the default eight-model/sixteen-tool-call limits. Use a fresh namespace
   such as `presentation_20261106`.
2. Submit the 7,925-employee claim. Explain the live steps, SUPPORTED verdict,
   exact quotation and PDF page 22.
3. Change the count to 9,000. Explain why the same passage now contradicts it.
4. Submit the latest-cash claim. Inspect the July and October citations and
   explain why both sources establish OUTDATED.
5. Submit the US-specific headcount. Explain why a global total cannot establish
   the exact regional number, giving NOT_ENOUGH_INFO.
6. Expand the JSON, event trail and usage. Use batch mode if time permits and
   download its report.
7. Show the saved benchmark comparison. The full sixty-run benchmark is already
   recorded and does not need to run during the presentation.

Live model calls can take tens of seconds or longer. The worked slides and
recorded-examples.json provide a source-backed demonstration if live inference
is slow. New runs may use different searches, quotes, calls or latency.

## Discussion points

- Python controls parsing, retrieval, provenance, validation and call budgets.
  The model interprets scope, chooses tools and evaluates meaning.
- Memory persists evidence rather than previous answers. Every run still searches
  all filings and validates recalled sources.
- Complete missing-information judgments differ from incomplete execution.
- Twenty claims across three configurations means sixty runs, not sixty unique
  statements. This development benchmark does not prove unseen-case accuracy.
- The single-agent mode performs well with fewer calls in this dataset. Planning
  has a measurable cost, and memory gains depend on related claims and order.

## Slide-by-slide notes

### Slide 1

This project verifies statements generated about a company before a human analyst relies on them. The evidence boundary is the three supplied CrowdStrike filings. Each report exposes the source passage and PDF page, the decision, a concise explanation, and actual usage. The system adapts the MERMAID components to a small local corpus. The recorded result covers twenty development statements under three configurations. It does not establish universal accuracy on unseen claims. This deck includes a complete recorded walkthrough and instructions for an optional live demonstration. All financial facts refer to the supplied historical filings, not the present company position.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/README.md
https://github.com/cyash24f3/fillingfactz/blob/main/docs/EVALUATION.md

### Slide 2

The four labels describe the evidence relationship. A separate complete or incomplete status describes execution. A failed or exhausted run must not masquerade as a successful missing-information judgment. Every accepted citation connects a quote to a canonical passage with source metadata. OUTDATED has a specific temporal meaning: the earlier amount must actually have been correct and a later filing must update the same fact. A dated historical statement is evaluated at its specified date, even when a newer balance exists. The task allows local models, so Qwen runs without a paid provider key. The application never treats model pretraining or web search as evidence.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/models.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md
https://github.com/cyash24f3/fillingfactz/blob/main/data/test_statements.json

### Slide 3

The application bundles the exact PDF copies used in evaluation. Their pagination is therefore reproducible. A source manifest records the original official URLs, file names, form type, reporting dates and filing dates. The latest supplied report ends October 31, 2024 and was filed November 27. That boundary prevents the system from treating a later completed annual result as already disclosed. A current quarter also contains comparative January balances, so selecting the newest document alone is insufficient. The relevant column and metric must match the claim. The task requires only these filings. No outside information updates the historical corpus during a run.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/data/filings.json
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md

### Slide 4

Read the diagram from the reviewer across the top row. FastAPI validates request settings and coordinates one workflow. LangGraph combines the Decomposer, evidence recall, a nested verification graph, and evidence persistence. Ollama supplies interpretation and tool selection. The lower row shows the data path from official files to searchable passages, tool observations and final validation. Python checks provenance, schema and selected financial consistency rules before accepting a candidate. The memory store persists source evidence rather than final answers. Accepted reports flow back through the original request or SSE connection. CLI and benchmark runs bypass HTTP but use the same core workflow. The Excalidraw board provides a more detailed module-level diagram.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/docs/ARCHITECTURE.md
https://github.com/cyash24f3/fillingfactz/blob/main/docs/architecture/README.md

### Slide 5

Parsing and indexing happen outside the model. Source fingerprints identify changes so unchanged files can reuse preparation work. Overlap reduces boundary loss, while page context carries headings and unit disclosures into later chunks. FTS5 provides BM25 lexical ranking. Query fusion retains specific words from the original claim when a generated planning query is broad. The initial search covers all three filings before the model can conclude. Coverage is a search safeguard, not a claim that every line of every PDF has been read. The system filters table-of-contents entries because they resemble substantive sections but contain little evidence. It does not implement OCR or a general cross-page table reconstruction engine.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/prepare.py
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/retrieval.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md

### Slide 6

The assignment asks for an adaptation rather than a literal reproduction of the research paper. The retained components are Decomposer, Executor, toolset and memory. The implementation uses a compact validated claim plan instead of a complete graph of subclaims. It uses local tools instead of web research and a Python registry instead of an MCP service. The Decomposer extracts scope and potential search terms. The Executor inspects source passages and reasons about a final decision. Python handles indexing, search, persistence, counters, schemas and quote authentication. The single-agent mode disables the planning stage while retaining the same evidence gate and call budgets. Independent compound-claim verification remains a future extension.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/graph.py
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/models.py

### Slide 7

Tool choice is informed by descriptions and schemas, rather than blind trial and error. The local model can request a search when the observed evidence leaves a gap, or read an identified passage or page. Python dispatches calls through a registry and returns either a validated observation or an error message. submit_verdict is a special structured action that attempts to finish the run. The evidence gate may reject it and append feedback. The budget counts planning, finalization, bootstrap retrieval and rejected attempts. Memory operations have separate counters. Adding a tool means supplying a registry definition, argument model and handler. Tool selection is probabilistic, but its execution and accounting are controlled by code.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/tools.py
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/agent.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md

### Slide 8

This table illustrates the message protocol. It does not claim every run follows an identical number of turns. A model request submits the current conversation, including observations received since earlier requests. LangGraph state also tracks structured fields that Python uses independently of natural-language messages: counters, searched filings, known passage IDs and the current plan. Source text is deduplicated to reduce repeated context. A tool failure is feedback in the same run, so the model can correct arguments. When the invocation ends, in-memory state ends. Evidence memory and the corpus database persist separately. The implementation does not provide durable graph checkpointing or automatic resumption of a partially completed model conversation.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/agent.py
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/graph.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/ARCHITECTURE.md

### Slide 9

Memory avoids treating a previous answer as authority. It stores source material that a new claim can reuse. FTS recall filters weak overlaps such as a shared year or amount because unrelated financial rows often contain the same numbers. The application revalidates recalled passages against the current corpus. A memory hit does not remove fresh all-filing retrieval, which protects against older cached evidence suppressing a later update. Separate namespaces avoid mixing benchmark conditions with manual experiments. The reported memory reads and writes count operations, not passages. The recorded comparison found four fewer model and tool calls with memory. Its token savings were only about 0.9%, so memory should not be presented as a large universal efficiency improvement.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/memory.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md
https://github.com/cyash24f3/fillingfactz/blob/main/docs/EVALUATION.md

### Slide 10

Pydantic forbids extra fields in the main candidate schema. Evidence arrives as passage identifiers and exact quoted text. Python enriches accepted references with canonical metadata rather than asking the model to invent page numbers or URLs. Quote matching tolerates whitespace and external quotation marks but preserves internal apostrophes and requires a continuous source span. Financial checks cover selected numeric formats and labels, rather than a general financial reasoning engine. OUTDATED needs evidence from earlier and later filings about the same fact. All filings must have been searched. A verified quote alone does not prove that it entails every interpretation of a statement. The model and reviewer remain responsible for broader meaning.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/models.py
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/evidence.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md

### Slide 11

The annual statement reports 3,055,555 thousand dollars for fiscal 2024 revenue. Multiplying by one thousand yields 3,055,555,000 dollars. Dividing by a billion gives 3.055555, which rounds to 3.06. A simple equality check on a coarsely rounded narrative figure would be too strict, so precision intervals matter. Metric checks stop the total-revenue number being used as subscription revenue. Temporal checks distinguish an explicit historical claim from a claim about the latest supplied position. Population checks prevent a global headcount from automatically proving or refuting an exact regional subset. These are source-backed consistency checks. They are not claim-specific answer rules or a replacement for semantic interpretation.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/data/test_statements.json
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/evidence.py

### Slide 12

Open Swagger at port 8000/docs. Expand POST /verify, choose Try it out, enter a valid body and execute it. An address-bar navigation to /verify sends GET and correctly returns Method Not Allowed. SSE is a separate POST endpoint with text/event-stream. It emits an initial queued event, a started event after acquiring the process lock, incremental steps, a validated result and a terminal done event. The client checks event run IDs. The service serializes its own runs to avoid overlapping local inference. Multiple server processes or independent CLI runs do not share that lock. Input failures receive ordinary validation responses. Stream failures use explicit error events.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/api.py
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/service.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/VALIDATION.md

### Slide 13

This screenshot comes from the actual validated reviewer. It shows the January 31 and December 31 fiscal-year statements, their supported and contradicted verdicts, and per-statement usage. Those screenshot counters differ from the later benchmark because they describe a separate run. In a live demonstration, first check the API address and keep the configured default budgets. Submit one statement, then show the evidence, usage and event trail. The batch view runs cases sequentially and preserves each report so reviewers can inspect and download them. The UI uses the HTTP service, while command-line evaluation runs the same workflow directly. Reported batch totals cover returned reports, and failed requests may have unreported usage.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/docs/images/reviewer-validation.jpg
https://github.com/cyash24f3/fillingfactz/blob/main/streamlit_app.py
https://github.com/cyash24f3/fillingfactz/blob/main/docs/VALIDATION.md

### Slide 14

Both examples come from the saved final full-workflow predictions, not a hypothetical output. T03 asks for the exact headcount disclosed in Human Capital Resources. The model submits a supported verdict and a quotation from PDF page 22. T04 changes the headcount to 9,000 but keeps the company, date and employee scope fixed. The same quotation then supports a contradiction. The evidence object carries the passage ID, filing, period end, filing date, PDF page, original URL and PDF fingerprint. The recorded token total adds input and output tokens. Local latency varies across runs, so these numbers identify this benchmark snapshot rather than promise live response time.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/results/benchmark/full/predictions.json
https://github.com/cyash24f3/fillingfactz/blob/main/data/test_statements.json

### Slide 15

This example demonstrates why finding one supporting passage is insufficient for a current-state claim. The July balance sheet supports 4,038,536 thousand dollars. The later October balance sheet reports 4,260,324 thousand dollars. The claim uses the phrase most recently reported, so the older amount is stale within this corpus. A proper OUTDATED report includes both earlier support and later change. The visible values normalize table scale for explanation. The actual report preserves the original quoted row text and source provenance. If the user instead asks whether cash was that amount on July 31, the newer balance does not falsify the historical statement. Both the date and metric define the comparison.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/results/benchmark/full/predictions.json
https://github.com/cyash24f3/fillingfactz/blob/main/data/test_statements.json

### Slide 16

The initial baseline mishandled this case by using the global total to contradict a regional subset. The final system preserves population scope and returns NOT_ENOUGH_INFO. It still searches all supplied filings. A related employee passage is useful context, but the absence of a country breakdown in one quotation does not establish absence everywhere. Missing-information decisions therefore retain a practical retrieval and model limitation. Execution status is separately important: a budget-exhausted run can return a fallback label, but the evaluator refuses to credit it. The recorded T18 result completed with source evidence and explicit reasoning. T19 tests a 5% voluntary attrition rate, while T20 tests a USD 20 billion fiscal 2030 forecast.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/results/benchmark/full/predictions.json
https://github.com/cyash24f3/fillingfactz/blob/main/docs/EVALUATION.md

### Slide 17

The graph has clear stopping conditions. It can accept a validated candidate or terminate with an explicit incomplete status when execution cannot finish. Rejected candidates and failed tool calls still consume the same total budget, so recovery cannot silently create an unbounded loop. A malformed plan falls back to the original claim rather than blocking all verification. The system gives one format reminder for unstructured responses. Page context helps when chunks lose a unit heading, and source provenance enables a reviewer to inspect the underlying PDF. These measures improve reliability without claiming a complete solution to OCR or arbitrary table reconstruction. The automated tests exercise these failure contracts separately from real-model evaluation.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/docs/DESIGN.md
https://github.com/cyash24f3/fillingfactz/blob/main/docs/VALIDATION.md
https://github.com/cyash24f3/fillingfactz/blob/main/filing_checker/agent.py

### Slide 18

Read this table as sixty runs over twenty unique claims. Full mode uses both agents and evidence memory. No-memory mode keeps planning but disables persistent evidence reuse. Single-agent mode disables Decomposer while retaining memory. All conditions start with an empty isolated namespace and use the same case order and budget limits. Labels and reference evidence are used only by the evaluator, never supplied as answers to the agent. Full accuracy is twenty out of twenty complete results in each configuration. Predictions save one record per statement with evidence and explanation. The run metadata records model settings, hashes, budgets and case order. This benchmark was used during development, so it should not be described as an unseen generalization result.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/results/benchmark/summary.json
https://github.com/cyash24f3/fillingfactz/blob/main/results/benchmark/run.json
https://github.com/cyash24f3/fillingfactz/blob/main/docs/EVALUATION.md

### Slide 19

The baseline comparison includes implementation changes, not just toggling memory. It therefore measures the revised system as a whole. The main improvements were filtering weak memory matches, avoiding duplicate source text, reducing searches that make no progress, and giving precise validation feedback. The full mode reduced tokens by 28.2% while fixing completion and accuracy. The ablation also shows that the simpler single-agent mode performs well on this small development corpus and consumes fewer model calls. That is an explicit planning tradeoff. Memory savings are modest and depend on case sequence. The single-agent time rose relative to its own older run, illustrating why fewer tokens do not guarantee lower measured latency. These are local single-run observations, not universal speedups.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/results/baseline/summary.json
https://github.com/cyash24f3/fillingfactz/blob/main/results/benchmark/summary.json
https://github.com/cyash24f3/fillingfactz/blob/main/docs/EVALUATION.md

### Slide 20

The README gives the full clone, virtual-environment and dependency-install steps. The three source PDFs are already included, so preparation does not require downloading new evidence. Start the local Ollama service before opening the API and UI. For a concise live demo, show a supported headcount, change it to a contradicted headcount, then run the outdated-cash claim and regional missing-information claim. Expand one exact citation and the usage metrics. The saved deck and predictions provide a recorded walkthrough if live inference is slow. Automated tests, source-reference validation and live API checks test different aspects. None establishes unrestricted correctness on unseen claims. The professional handoff includes the code, documentation, measured benchmark and editable architecture.

Sources
https://github.com/cyash24f3/fillingfactz/blob/main/README.md
https://github.com/cyash24f3/fillingfactz/blob/main/SUBMISSION.md
https://github.com/cyash24f3/fillingfactz/blob/main/docs/VALIDATION.md
https://github.com/cyash24f3/fillingfactz/blob/main/results/api_validation/README.md

