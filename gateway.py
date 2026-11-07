import os
import re
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Xcelsior AI Gateway")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# The model name is the one caller-supplied part of an upstream URL. Only allow
# the characters real model IDs use, so it can only ever name a model on
# Google's own host.
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")

@app.post("/v1/chat/openai")
async def proxy_openai(request: Request):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            timeout=60.0
        )
    return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("content-type"))

@app.post("/v1/chat/anthropic")
async def proxy_anthropic(request: Request):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=body,
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            timeout=60.0
        )
    return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("content-type"))

@app.post("/v1/chat/gemini")
async def proxy_gemini(request: Request):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    body = await request.json()
    # "-latest" alias rather than a pinned ID, which 404s once Google retires it.
    model = body.pop("model", "gemini-flash-latest")
    if not isinstance(model, str) or not MODEL_ID.fullmatch(model):
        raise HTTPException(status_code=400, detail="invalid model name")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GEMINI_MODELS_URL}/{model}:generateContent",
            json=body,
            # A header, not ?key=: a key in the URL ends up in access and proxy logs.
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            timeout=60.0
        )
    return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("content-type"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
