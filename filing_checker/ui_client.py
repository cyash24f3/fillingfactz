import json

import httpx

from filing_checker.models import VerificationResult


class StreamProtocolError(RuntimeError):
    pass


def parse_sse_lines(lines):
    data_lines = []

    for line in lines:
        if line == "":
            if data_lines:
                event = json.loads("\n".join(data_lines))

                if (
                    not isinstance(event, dict)
                    or not isinstance(event.get("data"), dict)
                    or not isinstance(event.get("run_id"), str)
                    or event.get("type")
                    not in {
                        "queued",
                        "started",
                        "step",
                        "result",
                        "error",
                        "done",
                    }
                ):
                    raise StreamProtocolError("The API returned an invalid event.")

                yield event
                data_lines = []

            continue

        if line.startswith(":"):
            continue

        field, _, value = line.partition(":")

        if value.startswith(" "):
            value = value[1:]

        if field == "data":
            data_lines.append(value)

    if data_lines:
        raise StreamProtocolError("The connection ended in the middle of an event.")


def stream_check(api_base, payload, transport=None):
    timeout = httpx.Timeout(
        30.0,
        connect=5.0,
        read=180.0,
    )

    with httpx.Client(
        timeout=timeout,
        transport=transport,
    ) as client:
        with client.stream(
            "POST",
            api_base.rstrip("/") + "/verify/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            if response.is_error:
                response.read()

                raise StreamProtocolError(
                    f"API returned HTTP {response.status_code}: " + response.text[:1500]
                )

            content_type = response.headers.get(
                "content-type",
                "",
            )

            if "text/event-stream" not in content_type:
                raise StreamProtocolError("The API did not return an event stream.")

            run_id = None
            result_seen = False

            for event in parse_sse_lines(response.iter_lines()):
                if run_id is None:
                    run_id = event["run_id"]

                elif event["run_id"] != run_id:
                    raise StreamProtocolError("The stream contains mixed run IDs.")

                if event["type"] == "result":
                    checked = VerificationResult.model_validate(event["data"])

                    event["data"] = checked.model_dump(mode="json")
                    result_seen = True

                if event["type"] == "done":
                    if event["data"].get("outcome") == "result" and not result_seen:
                        raise StreamProtocolError(
                            "The stream ended without its result."
                        )

                    yield event
                    return

                yield event

    raise StreamProtocolError("The connection closed before the done event.")


def parse_batch(text, json_input=False):
    if json_input:
        items = json.loads(text)

        if isinstance(items, dict):
            items = items.get("statements")

    else:
        items = [line.strip() for line in text.splitlines() if line.strip()]

    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("Supply between 1 and 100 statements.")

    statements = []

    for item in items:
        value = item.get("statement") if isinstance(item, dict) else item

        if not isinstance(value, str):
            raise ValueError("Each item must contain a statement string.")

        value = value.strip()

        if not 1 <= len(value) <= 4000:
            raise ValueError("Each statement must contain 1–4000 characters.")

        statements.append(value)

    return statements
