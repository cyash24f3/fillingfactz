import argparse
import json

from filing_checker.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check a statement against CrowdStrike filings."
    )

    parser.add_argument("statement")

    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print progress events to stderr.",
    )

    parser.add_argument(
        "--no-decomposer",
        action="store_true",
        help="Run the Executor without a planning agent.",
    )

    parser.add_argument(
        "--max-model-calls",
        type=int,
        default=8,
        help="Total budget across both agents.",
    )

    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=16,
        help="Total tool budget, including submission calls.",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable evidence-memory reads and writes.",
    )

    parser.add_argument(
        "--memory-namespace",
        default="default",
        help="Name of the independent evidence-memory collection.",
    )
    args = parser.parse_args()

    if not args.memory_namespace.strip():
        parser.error("--memory-namespace cannot be empty.")

    use_decomposer = not args.no_decomposer
    minimum_calls = 2 if use_decomposer else 1

    if args.max_model_calls < minimum_calls:
        parser.error(
            f"--max-model-calls must be at least "
            f"{minimum_calls} for this configuration."
        )

    if args.max_tool_calls < minimum_calls:
        parser.error(
            f"--max-tool-calls must be at least {minimum_calls} for this configuration."
        )

    graph = build_graph(
        trace=args.trace,
        max_model_calls=args.max_model_calls,
        max_tool_calls=args.max_tool_calls,
        use_decomposer=use_decomposer,
        use_memory=not args.no_memory,
        memory_namespace=args.memory_namespace,
    )

    final_state = graph.invoke({"statement": args.statement})

    print(
        json.dumps(
            final_state["result"],
            indent=2,
            ensure_ascii=False,
        )
    )
