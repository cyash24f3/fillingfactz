import asyncio
import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse

from filing_checker.config import MODEL_NAME
from filing_checker.models import VerificationResult
from filing_checker.service import (
    VerificationRequest,
    stream_verification,
    verify_once,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Serialize normal verification runs in this API process.
    app.state.run_lock = asyncio.Lock()
    yield


app = FastAPI(
    title="Filing Fact-Checker",
    version="0.1.0",
    lifespan=lifespan,
)


def encode_sse(event: dict) -> str:
    data = json.dumps(
        event,
        ensure_ascii=False,
    )

    return f"event: {event['type']}\ndata: {data}\n\n"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_NAME,
    }


@app.post(
    "/verify",
    response_model=VerificationResult,
)
async def verify(
    payload: VerificationRequest,
    request: Request,
):
    async with request.app.state.run_lock:
        try:
            return await verify_once(payload)

        except Exception as error:
            logger.exception("Verification request failed.")

            raise HTTPException(
                status_code=500,
                detail=str(error)[:1000],
            ) from error


@app.post("/verify/stream")
async def verify_stream(
    payload: VerificationRequest,
    request: Request,
):
    run_id = str(uuid4())

    async def body():
        yield encode_sse(
            {
                "type": "queued",
                "run_id": run_id,
                "data": {},
            }
        )

        async with request.app.state.run_lock:
            async for event in stream_verification(
                payload,
                run_id,
            ):
                yield encode_sse(event)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
