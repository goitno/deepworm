"""Example: Using the async API with FastAPI.

Run:
    pip install fastapi uvicorn
    uvicorn examples.fastapi_server:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from deepworm import AsyncResearcher, EventType
from deepworm.config import Config

app = FastAPI(title="deepworm API")


@app.post("/research")
async def research(topic: str, depth: int = 2, persona: str | None = None):
    """Run deep research and return the report."""
    config = Config.auto()
    config.depth = depth

    researcher = AsyncResearcher(config=config)
    report = await researcher.research(topic, persona=persona)

    return {"topic": topic, "report": report}


@app.post("/research/stream")
async def research_stream(topic: str, depth: int = 2):
    """Stream research progress and final report."""
    config = Config.auto()
    config.depth = depth

    researcher = AsyncResearcher(config=config)

    async def generate():
        async for chunk in researcher.research_stream(topic):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")
