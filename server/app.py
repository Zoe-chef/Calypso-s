"""
Sullivan's Bar — backend for real Gemini-powered conversation.

Why this exists at all: an API key can never live safely inside a page the
browser downloads (view-source or the Network tab hands it straight to
anyone). It has to sit on a server, read from an environment variable, and
the server does the actual call to Gemini on the frontend's behalf. That's
all this file does — it also serves the built page itself, so the frontend
can just call a same-origin "/api/chat" with no extra setup.

Run it:
    cd server
    python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
    cp .env.example .env      # then edit .env and paste your real key in
    ./venv/bin/python app.py
    open http://127.0.0.1:5050
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
BUILD_DIR = PROJECT_DIR / "build"

load_dotenv(BASE_DIR / ".env")

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not API_KEY or API_KEY == "paste-your-real-key-here":
    raise SystemExit(
        "GEMINI_API_KEY is not set.\n"
        "  1. cp server/.env.example server/.env\n"
        "  2. open server/.env and paste your real key after GEMINI_API_KEY=\n"
        "  3. run this again"
    )
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()

client = genai.Client(api_key=API_KEY)
app = Flask(__name__)

# ---------------- Persona + menu, loaded once at startup ----------------

PERSONA_DOC = (PROJECT_DIR / "Sullivan_人设文档.md").read_text(encoding="utf-8")

_menu_catalog_cache = None


def menu_catalog():
    """A condensed, LLM-friendly listing of every dish, built once and cached."""
    global _menu_catalog_cache
    if _menu_catalog_cache is not None:
        return _menu_catalog_cache
    data = json.loads((BUILD_DIR / "menu_data.min.json").read_text(encoding="utf-8"))
    lines = []
    for d in data["dishes"]:
        taste = ",".join(d.get("taste", []))
        mood = ",".join(d.get("mood", []))
        lines.append(f'{d["id"]}: {d["cn"]}/{d["en"]} [{d.get("category","")}] taste={taste} mood={mood}')
    _menu_catalog_cache = "\n".join(lines)
    return _menu_catalog_cache


SYSTEM_PROMPT_BASE = f"""You are role-playing as Sullivan, a bartender, inside a small browser prototype
called "Calypso's". Stay fully in character. Below is her character sheet, written by
her creator for internal reference — use it to inform how she talks and what she knows
about herself, but never quote it verbatim and never break character to discuss it.

--- CHARACTER SHEET ---
{PERSONA_DOC}
--- END CHARACTER SHEET ---

Rules:
- Reply in the SAME language the guest just wrote in (English or Chinese) — mirror them,
  don't default to one language regardless of input.
- Keep it short and conversational, like real bar dialogue: usually 1-3 sentences.
- Never break character. Never mention being an AI, a model, or a prompt.
- The scar's real backstory (tripping on stage) is a rare easter egg — don't volunteer it
  unless the guest has pushed hard / asked about the scar more than once.
""".strip()

ORDER_MODE_SUFFIX = """
You are in ORDER mode — the guest is deciding what to eat. Below is tonight's menu
catalog: "id: 中文名/English name [category] taste=... mood=...".
When it fits naturally, recommend 1-3 specific dishes from this catalog by id — don't
force a recommendation into every single line if the guest is just chatting mid-order.
Respond ONLY with JSON of this shape:
{{"reply": "<what Sullivan says, in character>", "dish_ids": [<ids you're recommending this turn, or [] if none>]}}

--- TONIGHT'S MENU ---
{catalog}
--- END MENU ---
""".strip()

CHAT_MODE_SUFFIX = """
You are in CHAT mode — the guest just wants to talk, not order food. Don't recommend
dishes in this mode. Respond ONLY with JSON of this shape:
{"reply": "<what Sullivan says, in character>"}
""".strip()

ORDER_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "reply": types.Schema(type=types.Type.STRING),
        "dish_ids": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.INTEGER)),
    },
    required=["reply"],
)
CHAT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={"reply": types.Schema(type=types.Type.STRING)},
    required=["reply"],
)


@app.route("/")
def index():
    return send_file(BASE_DIR / "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True, silent=True) or {}
    message = (body.get("message") or "").strip()
    history = body.get("history") or []  # [{role: "user"|"sullivan", text: "..."}]
    mode = body.get("mode") if body.get("mode") in ("chat", "order") else "chat"
    guest_name = (body.get("guestName") or "Friend").strip()[:40]

    if not message:
        return jsonify({"error": "empty message"}), 400

    if mode == "order":
        system_prompt = SYSTEM_PROMPT_BASE + "\n\n" + ORDER_MODE_SUFFIX.format(catalog=menu_catalog())
        schema = ORDER_SCHEMA
    else:
        system_prompt = SYSTEM_PROMPT_BASE + "\n\n" + CHAT_MODE_SUFFIX
        schema = CHAT_SCHEMA

    contents = []
    for turn in history[-20:]:
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        role = "model" if turn.get("role") == "sullivan" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=f"[Guest name: {guest_name}] {message}")]))

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.9,
            ),
        )
        data = json.loads(response.text)
    except Exception as exc:  # noqa: BLE001 — surface any Gemini/network failure as a 502
        app.logger.exception("Gemini call failed")
        return jsonify({"error": "gemini_call_failed", "detail": str(exc)}), 502

    return jsonify({
        "reply": data.get("reply") or "...",
        "dish_ids": data.get("dish_ids") or [] if mode == "order" else [],
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
