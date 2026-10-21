import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Moonlight Reflection Anime Image API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=3000)
    resolution: str | None = None
    seed: int | None = None
    guidance_scale: float | None = None
    remove_background: bool | None = None
    timeout: int | None = 180

@app.get("/")
def root():
    return {"service": "Moonlight Reflection Anime API", "status": "ok", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/generate")
async def generate(body: GenerateRequest):
    # AnimeAPI demo is free to try but limited to 3 images/day per IP; not unlimited.
    url = "https://animeapi.ai/api/demo/generate"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=20.0), follow_redirects=True) as client:
            response = await client.post(url, json={"prompt": body.prompt})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="انتهت مهلة مصدر التوليد. حاول مرة أخرى لاحقًا.")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"تعذر الاتصال بمصدر AnimeAPI: {type(exc).__name__}")

    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="انتهى الحد المجاني اليومي لمصدر التوليد. جرّب بعد تجدد الحد.")
    if response.status_code >= 400:
        detail = "رفض مصدر AnimeAPI الطلب. قد تكون خدمة التجربة متوقفة أو بلغ الحد المجاني."
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("error") or detail
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail)
    try:
        data = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="أعاد مصدر التوليد ردًا غير صالح.")

    image_url = data.get("image_url") or data.get("image")
    if not image_url and isinstance(data.get("data"), list) and data["data"]:
        image_url = data["data"][0].get("url")
    if not image_url:
        raise HTTPException(status_code=502, detail="لم يُرجع مصدر التوليد رابط صورة.")
    return {
        "image": image_url,
        "image_url": image_url,
        "enhanced_prompt": data.get("enhanced_prompt"),
        "generation_time_ms": data.get("generation_time_ms"),
        "demo_remaining": data.get("demo_remaining"),
        "provider": "AnimeAPI Demo",
    }
