import os
import time
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Pozwalamy na połączenia z rozszerzenia
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Token między rozszerzeniem a serwerem
EXTENSION_TOKEN = os.getenv("EXTENSION_TOKEN", "kuba-123")

# Klucz OpenAI – tylko na serwerze
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Model (ustawiany w Render → Environment)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat")
async def chat(request: Request):
    start_time = time.time()

    # --- AUTORYZACJA ---
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {EXTENSION_TOKEN}":
        print("CHAT: invalid token", flush=True)
        return {"error": "Zły token (brak dostępu)."}

    # --- WEJŚCIE ---
    body = await request.json()
    text = str(body.get("input", "")).strip()

    if not text:
        return {"error": "Brak tekstu."}

    print(f"CHAT: received text, len={len(text)}", flush=True)

    # --- TEST (diagnostyka) ---
    if text.lower().startswith("ping"):
        return {"output": "pong"}

    if not OPENAI_API_KEY:
        print("CHAT: missing OPENAI_API_KEY", flush=True)
        return {"error": "Brak OPENAI_API_KEY na serwerze."}

    # --- ZAPYTANIE DO OPENAI ---
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Dostaniesz pytanie i możliwe odpowiedzi. Niektóre pytania będą miały jedną poprawną odpowiedź, niektóre wiele poprawnych. W odpowiedzi podaj poprawne odpowiedzi i jednym zdaniem opisz dlaczego je wybrałeś."
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }

    print("CHAT: calling OpenAI...", flush=True)

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
            json=payload,
            timeout=(10, 120)  # 10s połączenie, 120s odpowiedź
        )
    except Exception as e:
        print("CHAT: OpenAI connection error:", str(e), flush=True)
        return {"error": f"OpenAI connection error: {str(e)}"}

    # 🔧 Naprawa polskich znaków
    resp.encoding = "utf-8"

    elapsed = round(time.time() - start_time, 2)
    print(f"CHAT: OpenAI response {resp.status_code} in {elapsed}s", flush=True)

    try:
        data = resp.json()
    except Exception:
        return {"error": "OpenAI zwróciło niepoprawną odpowiedź."}

    if resp.status_code != 200:
        return {"error": data}

    output = data["choices"][0]["message"]["content"]
    return {"output": output}
