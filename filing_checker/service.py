import asyncio
import logging
from collections.abc import AsyncIterator

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from filing_checker.graph import build_graph
from filing_checker.models import VerificationResult


logger = logging.getLogger(__name__)


class VerificationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    statement: str = Field(
        min_length=1,
        max_length=4000,
    )

    use_decomposer: bool = True
    use_memory: bool = True

    memory_namespace: str = Field(
        default="default",
        min_length=1,
        max_length=80,
    )

    max_model_calls: int = Field(
        default=8,
        ge=1,
        le=20,
    )

    max_tool_calls: int = Field(
        default=16,
        ge=1,
        le=40,
    )

    @model_validator(mode="after")
    def validate_budgets(self):
        minimum = 2 if self.use_decomposer else 1

        if self.max_model_calls < minimum:
            raise ValueError(
                f"This configuration requires at least {minimum} model calls."
            )

        if self.max_tool_calls < minimum:
            raise ValueError(
                f"This configuration requires at least {minimum} tool calls."
            )

        return self


def graph_for(payload: VerificationRequest):
    return build_graph(
        trace=False,
        max_model_calls=payload.max_model_calls,
        max_tool_calls=payload.max_tool_calls,
        use_decomposer=payload.use_decomposer,
        use_memory=payload.use_memory,
        memory_namespace=payload.memory_namespace,
    )


async def verify_once(
    payload: VerificationRequest,
) -> VerificationResult:
    graph = graph_for(payload)

    final_state = await graph.ainvoke({"statement": payload.statement})

    return VerificationResult.model_validate(final_state["result"])


async def stream_verification(
    payload: VerificationRequest,
    run_id: str,
) -> AsyncIterator[dict]:
    outcome = "error"

    try:
        yield {
            "type": "started",
            "run_id": run_id,
            "data": {
                "statement": payload.statement,
                "use_memory": payload.use_memory,
                "use_decomposer": payload.use_decomposer,
            },
        }

        graph = graph_for(payload)
        final_result = None

        async for chunk in graph.astream(
            {"statement": payload.statement},
            stream_mode=["custom", "updates"],
            version="v2",
        ):
            if chunk["type"] == "custom":
                yield {
                    "type": "step",
                    "run_id": run_id,
                    "data": chunk["data"],
                }

            elif chunk["type"] == "updates":
                for node_name, update in chunk["data"].items():
                    yield {
                        "type": "step",
                        "run_id": run_id,
                        "data": {
                            "event": "node_completed",
                            "node": node_name,
                        },
                    }

                    if isinstance(update, dict) and "result" in update:
                        final_result = update["result"]

        if final_result is None:
            raise RuntimeError("The workflow ended without returning a result.")

        checked = VerificationResult.model_validate(final_result)

        yield {
            "type": "result",
            "run_id": run_id,
            "data": checked.model_dump(mode="json"),
        }

        outcome = "result"

    except asyncio.CancelledError:
        raise

    except Exception as error:
        logger.exception("Streaming verification failed.")

        yield {
            "type": "error",
            "run_id": run_id,
            "data": {
                "code": "verification_failed",
                "message": str(error)[:1000],
            },
        }

    yield {
        "type": "done",
        "run_id": run_id,
        "data": {
            "outcome": outcome,
        },
    }
