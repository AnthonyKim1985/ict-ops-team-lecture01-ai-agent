from fastapi import FastAPI

from src.config import settings  # noqa: F401

app = FastAPI(title="날씨 AI Agent")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
