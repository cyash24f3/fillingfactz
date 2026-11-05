import json

import httpx
import streamlit as st

from filing_checker.ui_client import (
    StreamProtocolError,
    parse_batch,
    stream_check,
)


st.set_page_config(
    page_title="Filing Fact-Checker",
    layout="wide",
)


def event_text(event):
    kind = event["type"]
    data = event["data"]

    if kind == "queued":
        return "Waiting for the API worker"

    if kind == "started":
        return "Verification started"

    if kind == "result":
        return "Report received"

    if kind == "done":
        return "Request finished"

    if kind == "error":
        return "Request error: " + str(data.get("message", ""))

    name = data.get("event", "step")
    arguments = data.get("arguments") or {}

    if not isinstance(arguments, dict):
        arguments = {}

    if name == "model_call":
        return f"Executor model call {data.get('number')}"

    if name == "tool_requested":
        detail = arguments.get("query") or arguments.get("passage_id") or ""

        return (f"Tool: {data.get('name')} {detail}").strip()

    if name == "tool_error":
        return "Tool error: " + str(data.get("error", ""))[:240]

    if name == "memory_recalled":
        return f"Memory recalled {data.get('hits', 0)} passage(s)"

    if name == "memory_saved":
        return f"Memory saved {data.get('passages', 0)} passage(s)"

    if name == "node_completed":
        return f"Completed: {data.get('node')}"

    if name == "finalization_started":
        return "Finalizing from gathered evidence"

    return name.replace("_", " ").capitalize()


def new_record(statement, settings):
    return {
        "statement": statement,
        "settings": dict(settings),
        "events": [],
        "result": None,
        "error": None,
    }


def execute_record(
    record,
    api_base,
    status_slot,
    log_slot,
):
    payload = {
        "statement": record["statement"],
        **record["settings"],
    }

    try:
        for event in stream_check(api_base, payload):
            record["events"].append(event)

            if event["type"] == "result":
                record["result"] = event["data"]

            elif event["type"] == "error":
                record["error"] = event["data"].get(
                    "message",
                    "Verification failed.",
                )

            status_slot.info(event_text(event))

            log_slot.code(
                "\n".join(event_text(item) for item in record["events"][-14:]),
                language=None,
            )

    except (
        httpx.HTTPError,
        httpx.InvalidURL,
        StreamProtocolError,
        ValueError,
    ) as error:
        record["error"] = str(error)

    if record["result"] is None and record["error"] is None:
        record["error"] = "The API returned no report."

    if record["error"]:
        status_slot.error(record["error"])

    elif record["result"]["status"] == "incomplete":
        status_slot.warning("Research stopped before an accepted verdict.")

    else:
        status_slot.success("Report ready")


def token_total(result):
    first = result.get("input_tokens")
    second = result.get("output_tokens")

    if first is None or second is None:
        return None

    return first + second


def render_record(record):
    st.write(record["statement"])

    if record["error"]:
        st.error(record["error"])

    result = record["result"]

    if result is not None:
        if result["status"] != "complete":
            st.warning(
                "INCOMPLETE — "
                + result["stop_reason"]
                + ". The returned verdict is a fallback."
            )

        elif result["verdict"] == "SUPPORTED":
            st.success("SUPPORTED")

        elif result["verdict"] == "CONTRADICTED":
            st.error("CONTRADICTED")

        elif result["verdict"] == "OUTDATED":
            st.warning("OUTDATED")

        else:
            st.info("NOT_ENOUGH_INFO")

        st.write(result["explanation"])

        columns = st.columns(4)

        columns[0].metric(
            "Model calls",
            result["model_calls"],
        )

        columns[1].metric(
            "Tool calls",
            result["tool_calls"],
        )

        tokens = token_total(result)

        columns[2].metric(
            "Total tokens",
            (f"{tokens:,}" if tokens is not None else "Unknown"),
        )

        columns[3].metric(
            "Seconds",
            f"{result['elapsed_seconds']:.1f}",
        )

        memory = result.get("memory", {})

        st.caption(
            f"Memory: "
            f"{'on' if memory.get('enabled') else 'off'} | "
            f"Recalled passages: "
            f"{len(memory.get('recalled_passage_ids', []))} | "
            f"Decomposer: "
            f"{result.get('decomposer_status', 'unknown')}"
        )

        st.write("Evidence")

        if not result["evidence"]:
            st.caption("No accepted citations were returned.")

        for index, item in enumerate(
            result["evidence"],
            start=1,
        ):
            with st.expander(
                f"{index}. {item['filing_id']} — PDF page {item['pdf_page']}"
            ):
                st.code(
                    item["quote"],
                    language=None,
                )

                st.caption(
                    f"Period ended: {item['period_end']} | Filed: {item['filed_at']}"
                )

                st.caption(f"Passage: {item['passage_id']}")

                st.markdown(f"[Open official source]({item['source_url']})")

        with st.expander("Full JSON report"):
            st.json(result)

    if record["events"]:
        with st.expander("Run steps"):
            st.code(
                "\n".join(event_text(item) for item in record["events"]),
                language=None,
            )

        with st.expander("Raw events"):
            st.json(record["events"])


def summary_rows(records):
    rows = []

    for index, record in enumerate(
        records,
        start=1,
    ):
        result = record["result"] or {}

        status = (
            "request_error" if record["error"] else result.get("status", "no_result")
        )

        rows.append(
            {
                "#": index,
                "Statement": record["statement"],
                "Status": status,
                "Verdict": (
                    result.get("verdict") if status == "complete" else "INCOMPLETE"
                ),
                "Model calls": result.get("model_calls"),
                "Tool calls": result.get("tool_calls"),
                "Tokens": token_total(result),
                "Memory hits": (
                    len(
                        result.get("memory", {}).get(
                            "recalled_passage_ids",
                            [],
                        )
                    )
                    if result
                    else None
                ),
            }
        )

    return rows


if "single_run" not in st.session_state:
    st.session_state.single_run = None

if "batch_runs" not in st.session_state:
    st.session_state.batch_runs = []


st.title("Filing Fact-Checker")

st.caption("Review statements against the supplied CrowdStrike filings.")


with st.sidebar:
    st.subheader("Run settings")

    api_base = (
        st.text_input(
            "API address",
            value="http://127.0.0.1:8000",
        )
        .strip()
        .rstrip("/")
    )

    use_memory = st.checkbox(
        "Use evidence memory",
        value=True,
    )

    use_decomposer = st.checkbox(
        "Use Decomposer",
        value=True,
    )

    namespace = st.text_input(
        "Memory collection",
        value="reviewer",
        help=("Use a new name to start with an empty evidence memory."),
    ).strip()

    model_budget = int(
        st.number_input(
            "Maximum model calls",
            min_value=1,
            max_value=20,
            value=8,
            step=1,
        )
    )

    tool_budget = int(
        st.number_input(
            "Maximum tool calls",
            min_value=1,
            max_value=40,
            value=16,
            step=1,
        )
    )

    settings_valid = bool(api_base and namespace) and (
        not use_decomposer or (model_budget >= 2 and tool_budget >= 2)
    )

    if not settings_valid:
        st.warning(
            "Enter an API address and memory collection. "
            "With the Decomposer enabled, both budgets "
            "must be at least 2."
        )

    if st.button("Check API"):
        try:
            response = httpx.get(
                api_base + "/health",
                timeout=5.0,
            )

            response.raise_for_status()
            st.success("API is responding")

        except (
            httpx.HTTPError,
            httpx.InvalidURL,
            ValueError,
        ) as error:
            st.error(str(error))


settings = {
    "use_memory": use_memory,
    "use_decomposer": use_decomposer,
    "memory_namespace": namespace,
    "max_model_calls": model_budget,
    "max_tool_calls": tool_budget,
}


single_tab, batch_tab = st.tabs(["Single statement", "Batch review"])


with single_tab:
    with st.form("single_form"):
        statement = st.text_area(
            "Statement",
            value=("CrowdStrike's fiscal year ends on January 31."),
            height=100,
        )

        single_submitted = st.form_submit_button(
            "Check statement",
            disabled=not settings_valid,
        )

    if single_submitted:
        if not 1 <= len(statement.strip()) <= 4000:
            st.error("Enter a statement containing 1–4000 characters.")

        else:
            record = new_record(
                statement.strip(),
                settings,
            )

            st.session_state.single_run = record

            status_slot = st.empty()
            log_slot = st.empty()

            execute_record(
                record,
                api_base,
                status_slot,
                log_slot,
            )

            log_slot.empty()

    if st.session_state.single_run is not None:
        record = st.session_state.single_run

        render_record(record)

        st.download_button(
            "Download review",
            data=json.dumps(
                record,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="single_review.json",
            mime="application/json",
            key="single_download",
        )


with batch_tab:
    with st.form("batch_form"):
        batch_text = st.text_area(
            "One statement per line",
            value=(
                "CrowdStrike's fiscal year "
                "ends on January 31.\n"
                "CrowdStrike's fiscal year "
                "ends on December 31."
            ),
            height=160,
        )

        uploaded = st.file_uploader(
            "Or upload a TXT or JSON file",
            type=["txt", "json"],
        )

        st.caption("An uploaded file takes precedence over the text box.")

        batch_submitted = st.form_submit_button(
            "Check batch",
            disabled=not settings_valid,
        )

    if batch_submitted:
        try:
            if uploaded is not None:
                statements = parse_batch(
                    uploaded.getvalue().decode("utf-8-sig"),
                    json_input=uploaded.name.lower().endswith(".json"),
                )

            else:
                statements = parse_batch(batch_text)

        except (ValueError, UnicodeError) as error:
            st.error(str(error))

        else:
            st.session_state.batch_runs = []
            st.session_state.pop(
                "batch_inspect",
                None,
            )

            progress = st.progress(0.0)
            heading = st.empty()
            status_slot = st.empty()
            log_slot = st.empty()
            table_slot = st.empty()

            for index, statement in enumerate(statements):
                heading.info(f"Checking {index + 1} of {len(statements)}: " + statement)

                record = new_record(
                    statement,
                    settings,
                )

                st.session_state.batch_runs.append(record)

                execute_record(
                    record,
                    api_base,
                    status_slot,
                    log_slot,
                )

                table_slot.dataframe(summary_rows(st.session_state.batch_runs))

                progress.progress((index + 1) / len(statements))

            heading.success("Batch processing finished")

            log_slot.empty()
            table_slot.empty()

    records = st.session_state.batch_runs

    if records:
        st.dataframe(summary_rows(records))

        reports = [
            record["result"] for record in records if record["result"] is not None
        ]

        columns = st.columns(3)

        columns[0].metric(
            "Statements processed",
            len(records),
        )

        columns[1].metric(
            "Reported model calls",
            sum(result["model_calls"] for result in reports),
        )

        columns[2].metric(
            "Reported tool calls",
            sum(result["tool_calls"] for result in reports),
        )

        st.caption(
            "Usage totals include returned reports. "
            "Request failures may have unreported usage."
        )

        selected = st.selectbox(
            "Inspect a statement",
            options=list(range(len(records))),
            format_func=lambda index: (
                f"{index + 1}. {records[index]['statement'][:100]}"
            ),
            key="batch_inspect",
        )

        render_record(records[selected])

        st.download_button(
            "Download batch reviews",
            data=json.dumps(
                records,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="batch_reviews.json",
            mime="application/json",
            key="batch_download",
        )
