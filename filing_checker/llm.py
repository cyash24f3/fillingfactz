from ollama import Client

from filing_checker.config import MODEL_NAME


client = Client(
    host="http://127.0.0.1:11434",
    timeout=120.0,
)


def ask_model(messages, tools):
    return client.chat(
        model=MODEL_NAME,
        messages=messages,
        tools=tools,
        think=False,
        keep_alive="10m",
        options={
            "temperature": 0,
            "num_ctx": 8192,
            "num_predict": 1800,
        },
    )


def response_metrics(response, wall_seconds):
    reported = response.model_dump()

    def seconds(key):
        value = reported.get(key)

        return (
            round(
                value / 1_000_000_000,
                4,
            )
            if value is not None
            else None
        )

    generation_seconds = seconds("eval_duration")

    output_tokens = reported.get("eval_count")

    return {
        "wall_seconds": round(
            wall_seconds,
            3,
        ),
        "server_seconds": seconds("total_duration"),
        "load_seconds": seconds("load_duration"),
        "prompt_seconds": seconds("prompt_eval_duration"),
        "generation_seconds": generation_seconds,
        "input_tokens": reported.get("prompt_eval_count"),
        "output_tokens": output_tokens,
        "output_tokens_per_second": (
            round(
                output_tokens / generation_seconds,
                2,
            )
            if (
                output_tokens is not None
                and generation_seconds is not None
                and generation_seconds > 0
            )
            else None
        ),
    }
