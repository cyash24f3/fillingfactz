import json
import sqlite3
import sys
from time import monotonic
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from filing_checker.agent import run_verifier
from filing_checker.decomposer import decompose_statement
from filing_checker.ingestion import prepare_corpus
from filing_checker.memory import (
    recall_evidence,
    remember_evidence,
)
from filing_checker.models import (
    ClaimPlan,
    MemoryStats,
    VerificationResult,
)


class VerificationState(TypedDict, total=False):
    statement: str
    started_at: float
    planning: dict

    recalled_passages: list[dict]
    memory_stats: dict
    memory_events: list[dict]

    result: dict


def combine_tokens(
    first: int | None,
    second: int | None,
) -> int | None:
    if first is None or second is None:
        return None

    return first + second


def build_graph(
    trace: bool = False,
    max_model_calls: int = 8,
    max_tool_calls: int = 16,
    use_decomposer: bool = True,
    use_memory: bool = True,
    memory_namespace: str = "default",
):
    minimum_calls = 2 if use_decomposer else 1

    if max_model_calls < minimum_calls:
        raise ValueError(
            f"This configuration needs at least {minimum_calls} model calls."
        )

    if max_tool_calls < minimum_calls:
        raise ValueError(
            f"This configuration needs at least {minimum_calls} tool calls."
        )

    memory_namespace = memory_namespace.strip()

    if not memory_namespace:
        raise ValueError("Memory namespace cannot be empty.")

    def show(event: dict) -> None:
        get_stream_writer()(event)

        if trace:
            print(
                json.dumps(event, ensure_ascii=False),
                file=sys.stderr,
                flush=True,
            )

    def initialize_node(state: VerificationState) -> dict:
        statement = state["statement"].strip()

        if not statement:
            raise ValueError("Statement cannot be empty.")

        started_at = monotonic()
        prepare_corpus()

        return {
            "statement": statement,
            "started_at": started_at,
        }

    def decompose_node(state: VerificationState) -> dict:
        if not use_decomposer:
            return {
                "planning": {
                    "status": "disabled",
                    "plan": None,
                    "model_calls": 0,
                    "tool_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "trace": [],
                }
            }

        return {
            "planning": decompose_statement(
                state["statement"],
                trace=trace,
            )
        }

    def recall_node(state: VerificationState) -> dict:
        stats = MemoryStats(
            enabled=use_memory,
            namespace=(memory_namespace if use_memory else None),
        )

        passages = []
        events = []

        def record(event: dict) -> None:
            events.append(event)
            show(event)

        if use_memory:
            stats.recall_calls = 1

            try:
                passages = recall_evidence(
                    statement=state["statement"],
                    namespace=memory_namespace,
                )

            except (
                sqlite3.Error,
                OSError,
                ValueError,
            ) as error:
                record(
                    {
                        "event": "memory_error",
                        "stage": "memory",
                        "operation": "recall",
                        "error": str(error)[:1000],
                    }
                )

            stats.recalled_passage_ids = [passage["passage_id"] for passage in passages]

            record(
                {
                    "event": "memory_recalled",
                    "stage": "memory",
                    "hits": len(passages),
                    "passage_ids": (stats.recalled_passage_ids),
                }
            )

        return {
            "recalled_passages": passages,
            "memory_stats": stats.model_dump(mode="json"),
            "memory_events": events,
        }

    def verify_node(state: VerificationState) -> dict:
        planning = state["planning"]

        remaining_model_calls = max_model_calls - planning["model_calls"]

        remaining_tool_calls = max_tool_calls - planning["tool_calls"]

        result = run_verifier(
            statement=state["statement"],
            trace=trace,
            max_model_calls=remaining_model_calls,
            max_tool_calls=remaining_tool_calls,
            research_plan=planning["plan"],
            recalled_passages=state["recalled_passages"],
        )

        plan = (
            ClaimPlan.model_validate(planning["plan"])
            if planning["plan"] is not None
            else None
        )

        executor_events = [{**event, "stage": "executor"} for event in result.trace]

        result = result.model_copy(
            update={
                "research_plan": plan,
                "decomposer_status": planning["status"],
                "memory": MemoryStats.model_validate(state["memory_stats"]),
                "model_calls": (planning["model_calls"] + result.model_calls),
                "tool_calls": (planning["tool_calls"] + result.tool_calls),
                "input_tokens": combine_tokens(
                    planning["input_tokens"],
                    result.input_tokens,
                ),
                "output_tokens": combine_tokens(
                    planning["output_tokens"],
                    result.output_tokens,
                ),
                "trace": (planning["trace"] + state["memory_events"] + executor_events),
            }
        )

        return {"result": result.model_dump(mode="json")}

    def remember_node(state: VerificationState) -> dict:
        result = VerificationResult.model_validate(state["result"])

        stats = result.memory

        if use_memory and result.status == "complete" and result.evidence:
            stats.write_calls += 1

            try:
                stats.saved_passages = remember_evidence(
                    evidence=result.evidence,
                    namespace=memory_namespace,
                )

                event = {
                    "event": "memory_saved",
                    "stage": "memory",
                    "passages": stats.saved_passages,
                }

            except (
                sqlite3.Error,
                OSError,
                ValueError,
            ) as error:
                event = {
                    "event": "memory_error",
                    "stage": "memory",
                    "operation": "write",
                    "error": str(error)[:1000],
                }

            result.trace.append(event)
            show(event)

        result.elapsed_seconds = round(
            monotonic() - state["started_at"],
            3,
        )

        return {
            "memory_stats": stats.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
        }

    builder = StateGraph(VerificationState)

    builder.add_node("initialize", initialize_node)
    builder.add_node("decompose", decompose_node)
    builder.add_node("recall", recall_node)
    builder.add_node("verify", verify_node)
    builder.add_node("remember", remember_node)

    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "decompose")
    builder.add_edge("decompose", "recall")
    builder.add_edge("recall", "verify")
    builder.add_edge("verify", "remember")
    builder.add_edge("remember", END)

    return builder.compile()
