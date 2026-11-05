import argparse
import asyncio
import hashlib
import json
import platform
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from filing_checker.config import (
    DATABASE_PATH,
    MODEL_NAME,
    PROJECT_ROOT,
)
from filing_checker.evidence import find_original_quote
from filing_checker.ingestion import prepare_corpus
from filing_checker.models import Verdict
from filing_checker.retrieval import read_passage
from filing_checker.service import (
    VerificationRequest,
    verify_once,
)


LABELS = (
    "SUPPORTED",
    "CONTRADICTED",
    "OUTDATED",
    "NOT_ENOUGH_INFO",
)

MODES = {
    "full": {
        "use_decomposer": True,
        "use_memory": True,
    },
    "no_memory": {
        "use_decomposer": True,
        "use_memory": False,
    },
    "single_agent": {
        "use_decomposer": False,
        "use_memory": True,
    },
}


class Reference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str
    pdf_page: int = Field(ge=1)
    quote: str = Field(min_length=1)


class GoldCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str = Field(
        min_length=1,
        max_length=4000,
    )
    expected_verdict: Verdict
    reference_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=10)

    earlier_reference: str | None = None
    later_reference: str | None = None


class Benchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    references: dict[str, Reference]
    statements: list[GoldCase] = Field(min_length=20)


def corpus_fingerprint():
    with closing(
        sqlite3.connect(
            DATABASE_PATH.as_uri() + "?mode=ro",
            uri=True,
        )
    ) as database:
        row = database.execute(
            "SELECT value FROM index_meta WHERE key = 'fingerprint'"
        ).fetchone()

    if row is None:
        raise RuntimeError("The corpus has no fingerprint.")

    return row[0]


def validate_benchmark(benchmark):
    identifiers = [case.id for case in benchmark.statements]

    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Test IDs must be unique.")

    if {case.expected_verdict for case in benchmark.statements} != set(LABELS):
        raise ValueError("The benchmark must cover all four verdicts.")

    references = {}

    for key, reference in benchmark.references.items():
        passage = read_passage(reference.passage_id)

        if passage.pdf_page != reference.pdf_page:
            raise ValueError(f"Wrong PDF page in reference {key}.")

        quote = find_original_quote(
            passage.text,
            reference.quote,
        )

        references[key] = {
            "passage_id": passage.passage_id,
            "filing_id": passage.filing_id,
            "pdf_page": passage.pdf_page,
            "quote": quote,
            "filed_at": passage.filed_at.isoformat(),
            "source_url": passage.source_url,
            "pdf_sha256": passage.pdf_sha256,
        }

    for case in benchmark.statements:
        if any(key not in references for key in case.reference_ids):
            raise ValueError(f"Unknown reference in {case.id}.")

        if case.expected_verdict == "OUTDATED":
            earlier = case.earlier_reference
            later = case.later_reference

            if earlier not in case.reference_ids or later not in case.reference_ids:
                raise ValueError(f"{case.id} needs earlier and later references.")

            if (
                references[earlier]["filing_id"] == references[later]["filing_id"]
                or references[earlier]["filed_at"] >= references[later]["filed_at"]
            ):
                raise ValueError(f"Invalid filing chronology in {case.id}.")

    return references


def make_prediction(
    case,
    mode,
    references,
    result=None,
    error=None,
):
    expected_sources = []

    for key in case.reference_ids:
        role = "reference"

        if case.expected_verdict == "NOT_ENOUGH_INFO":
            role = "context"

        elif key == case.earlier_reference:
            role = "earlier"

        elif key == case.later_reference:
            role = "later"

        expected_sources.append(
            {
                **references[key],
                "role": role,
            }
        )

    usage = None

    if result is not None:
        usage = {
            "model_calls": result.model_calls,
            "tool_calls": result.tool_calls,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "memory_reads": result.memory.recall_calls,
            "memory_writes": result.memory.write_calls,
            "elapsed_seconds": result.elapsed_seconds,
        }

    return {
        "id": case.id,
        "configuration": mode,
        "statement": case.statement,
        "expected_verdict": case.expected_verdict,
        "system_verdict": (result.verdict if result else None),
        "status": (result.status if result else "error"),
        "correct": bool(
            result is not None
            and result.status == "complete"
            and result.verdict == case.expected_verdict
        ),
        "evidence": (
            [item.model_dump(mode="json") for item in result.evidence] if result else []
        ),
        "explanation": (result.explanation if result else str(error)),
        "stop_reason": (result.stop_reason if result else "exception"),
        "usage": usage,
        "memory": (result.memory.model_dump(mode="json") if result else None),
        "expected_evidence": expected_sources,
        "label_rationale": case.rationale,
        "trace": result.trace if result else [],
    }


def total_usage(rows, key):
    values = [(row["usage"] or {}).get(key) for row in rows]

    if not values or any(value is None for value in values):
        return None

    return sum(values)


def summarize(rows, dataset_size):
    input_tokens = total_usage(
        rows,
        "input_tokens",
    )
    output_tokens = total_usage(
        rows,
        "output_tokens",
    )

    return {
        "cases": len(rows),
        "dataset_size": dataset_size,
        "full_dataset": len(rows) == dataset_size,
        "accuracy": (sum(row["correct"] for row in rows) / len(rows)),
        "completed": sum(row["status"] == "complete" for row in rows),
        "incomplete": sum(row["status"] == "incomplete" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "model_calls": total_usage(
            rows,
            "model_calls",
        ),
        "tool_calls": total_usage(
            rows,
            "tool_calls",
        ),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": (
            input_tokens + output_tokens
            if (input_tokens is not None and output_tokens is not None)
            else None
        ),
        "elapsed_seconds": total_usage(
            rows,
            "elapsed_seconds",
        ),
        "memory_reads": total_usage(
            rows,
            "memory_reads",
        ),
        "memory_writes": total_usage(
            rows,
            "memory_writes",
        ),
    }


def write_json(path, value):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def summary_table(summaries):
    lines = [
        "| Configuration | Cases | Accuracy | Completed | "
        "Model calls | Tool calls | Tokens | Seconds | Memory reads/writes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def shown(value):
        return "unknown" if value is None else str(value)

    for mode, item in summaries.items():
        elapsed = item.get("elapsed_seconds")
        seconds = f"{elapsed:.1f}" if elapsed is not None else "unknown"

        lines.append(
            f"| {mode} "
            f"| {item['cases']}/{item['dataset_size']} "
            f"| {item['accuracy']:.1%} "
            f"| {item['completed']} "
            f"| {shown(item['model_calls'])} "
            f"| {shown(item['tool_calls'])} "
            f"| {shown(item['total_tokens'])} "
            f"| {seconds} "
            f"| {shown(item['memory_reads'])}/"
            f"{shown(item['memory_writes'])} |"
        )

    return "\n".join(lines) + "\n"


def select_cases(benchmark, ids=None, limit=None):
    cases = benchmark.statements

    if ids is not None:
        if limit is not None:
            raise ValueError("Use either --ids or --limit.")

        if not ids:
            raise ValueError("Supply at least one test ID.")

        if len(ids) != len(set(ids)):
            raise ValueError("Test IDs cannot be repeated.")

        requested = set(ids)
        known = {case.id for case in cases}
        unknown = requested - known

        if unknown:
            raise ValueError("Unknown test IDs: " + ", ".join(sorted(unknown)))

        # Preserve dataset order for reproducible memory reuse.
        return [case for case in cases if case.id in requested]

    if limit is not None:
        if not 1 <= limit <= len(cases):
            raise ValueError("--limit is outside the dataset size.")

        return cases[:limit]

    return list(cases)


async def run_evaluation(
    args,
    benchmark,
    references,
):
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    )

    output = PROJECT_ROOT / "results" / run_id

    modes = list(MODES) if args.mode == "all" else [args.mode]

    cases = select_cases(
        benchmark,
        ids=args.ids,
        limit=args.limit,
    )

    fingerprint = corpus_fingerprint()

    dataset_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()

    metadata = {
        "run_id": run_id,
        "status": "running",
        "model": MODEL_NAME,
        "python": platform.python_version(),
        "corpus_fingerprint": fingerprint,
        "dataset_sha256": dataset_hash,
        "case_order": [case.id for case in cases],
        "max_model_calls": args.max_model_calls,
        "max_tool_calls": args.max_tool_calls,
        "configurations": {
            mode: {
                **MODES[mode],
                "memory_namespace": (f"eval_{run_id}_{mode}"),
            }
            for mode in modes
        },
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (PROJECT_ROOT / "filing_checker").glob("*.py")
        },
    }

    write_json(
        output / "run.json",
        metadata,
    )

    summaries = {}

    for mode in modes:
        rows = []

        options = metadata["configurations"][mode]

        for index, case in enumerate(
            cases,
            start=1,
        ):
            result = None
            error = None

            try:
                payload = VerificationRequest(
                    statement=case.statement,
                    max_model_calls=args.max_model_calls,
                    max_tool_calls=args.max_tool_calls,
                    **options,
                )

                result = await verify_once(payload)

            except Exception as caught:
                error = caught

            row = make_prediction(
                case,
                mode,
                references,
                result,
                error,
            )

            rows.append(row)

            write_json(
                output / mode / "predictions.json",
                rows,
            )

            if (
                corpus_fingerprint() != fingerprint
                or hashlib.sha256(args.dataset.read_bytes()).hexdigest() != dataset_hash
            ):
                raise RuntimeError(
                    "The corpus or benchmark changed "
                    "during evaluation. Start a new run "
                    "with fixed inputs."
                )

            print(
                f"{mode} {index}/{len(cases)} {case.id}: "
                f"expected={case.expected_verdict} "
                f"got={row['system_verdict']} "
                f"status={row['status']}",
                flush=True,
            )

            summaries[mode] = summarize(
                rows,
                len(benchmark.statements),
            )

            write_json(
                output / "summary.json",
                summaries,
            )

            (output / "summary.md").write_text(
                summary_table(summaries),
                encoding="utf-8",
            )

    metadata["status"] = "finished"

    write_json(
        output / "run.json",
        metadata,
    )

    print(summary_table(summaries))
    print(f"Results: {output}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset",
        type=Path,
        default=(PROJECT_ROOT / "data" / "test_statements.json"),
    )

    parser.add_argument(
        "--mode",
        choices=["all", *MODES],
        default="all",
    )

    selection = parser.add_mutually_exclusive_group()

    selection.add_argument(
        "--limit",
        type=int,
    )

    selection.add_argument(
        "--ids",
        nargs="+",
        help="Specific test IDs, separated by spaces.",
    )

    parser.add_argument(
        "--max-model-calls",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=16,
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
    )

    args = parser.parse_args()

    if not 2 <= args.max_model_calls <= 20:
        parser.error("--max-model-calls must be between 2 and 20.")

    if not 2 <= args.max_tool_calls <= 40:
        parser.error("--max-tool-calls must be between 2 and 40.")

    benchmark = Benchmark.model_validate_json(args.dataset.read_text(encoding="utf-8"))

    try:
        selected_cases = select_cases(
            benchmark,
            ids=args.ids,
            limit=args.limit,
        )

    except ValueError as error:
        parser.error(str(error))

    prepare_corpus()
    references = validate_benchmark(benchmark)

    if args.validate_only:
        print(
            json.dumps(
                {
                    "cases": len(benchmark.statements),
                    "references": len(references),
                    "selected_ids": [case.id for case in selected_cases],
                    "labels": {
                        label: sum(
                            case.expected_verdict == label
                            for case in benchmark.statements
                        )
                        for label in LABELS
                    },
                    "model_calls": 0,
                },
                indent=2,
            )
        )

        return

    asyncio.run(
        run_evaluation(
            args,
            benchmark,
            references,
        )
    )


if __name__ == "__main__":
    main()
