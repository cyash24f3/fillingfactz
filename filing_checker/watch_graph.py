import json

from filing_checker.graph import build_graph


if __name__ == "__main__":
    graph = build_graph(trace=False)

    for chunk in graph.stream(
        {"statement": ("CrowdStrike's fiscal year ends on January 31.")},
        stream_mode=["custom", "updates"],
        version="v2",
    ):
        if chunk["type"] == "custom":
            print(
                json.dumps(
                    chunk["data"],
                    ensure_ascii=False,
                ),
                flush=True,
            )

        elif chunk["type"] == "updates":
            for node_name in chunk["data"]:
                print(
                    f"Completed node: {node_name}",
                    flush=True,
                )
