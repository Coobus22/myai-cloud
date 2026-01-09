import os
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Na start pozwól wszystkim (żeby nie walczyć z blokadami).
# Potem można zawęzić.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# To jest "hasło" między rozszerzeniem a Twoim serwerem
EXTENSION_TOKEN = os.getenv("EXTENSION_TOKEN", "kuba-123")

# Klucz OpenAI trzymamy TYLKO na serwerze (nigdy w rozszerzeniu)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Możesz zostawić gpt-5 / gpt-4o – zależy co masz dostępne na koncie
MODEL = os.getenv("OPENAI_MODEL", "gpt-5")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
async def chat(request: Request):
    # 1) Sprawdź token od rozszerzenia
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {EXTENSION_TOKEN}":
        return {"error": "Zły token (brak dostępu)."}

    # 2) Weź tekst
    body = await request.json()
    text = str(body.get("input", "")).strip()
    if not text:
        return {"error": "Brak tekstu."}

    if not OPENAI_API_KEY:
        return {"error": "Brak ustawionego OPENAI_API_KEY na serwerze."}

    # 3) Zapytaj model w chmurze (Chat Completions)
    # Endpoint i format są opisane w dokumentacji Chat Completions. :contentReference[oaicite:6]{index=6}
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": text}]
        },
        timeout=120,
    )

    data = resp.json()

    # Jeśli coś poszło źle, pokaż błąd wprost
    if resp.status_code != 200:
        return {"error": data}

    output = data["choices"][0]["message"]["content"]
    return {"output": output}
