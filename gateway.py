import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response

app = FastAPI(title="Xcelsior AI Gateway")

# Note: Set these via environment variables or a .env file later
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.post("/v1/chat/openai")
async def proxy_openai(request: Request):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    
    body = await request.json()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json=body,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
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
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
    return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("content-type"))

if __name__ == "__main__":
    import uvicorn
    # Bind to all interfaces so Tailscale (100.64.0.x) can reach it
    uvicorn.run(app, host="0.0.0.0", port=8080)
