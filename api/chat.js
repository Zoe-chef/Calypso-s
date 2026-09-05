// Vercel serverless function — the ONLY place that ever touches the Gemini
// API key. It reads GEMINI_API_KEY from the environment (set in the Vercel
// dashboard, never committed to git, never sent to the browser). The
// frontend just calls fetch("/api/chat") same-origin; it never sees the key.

const { GoogleGenAI, Type } = require("@google/genai");
const { PERSONA_DOC, MENU_CATALOG } = require("./_data");

const MODEL = process.env.GEMINI_MODEL || "gemini-3.6-flash";

let _client = null;
function client() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error(
      "GEMINI_API_KEY is not set. Add it in Vercel → Project → Settings → Environment Variables, then redeploy."
    );
  }
  if (!_client) _client = new GoogleGenAI({ apiKey });
  return _client;
}

const SYSTEM_PROMPT_BASE = `You are role-playing as Sullivan, a bartender, inside a small browser prototype
called "Calypso's". Stay fully in character. Below is her character sheet, written by
her creator for internal reference — use it to inform how she talks and what she knows
about herself, but never quote it verbatim and never break character to discuss it.

--- CHARACTER SHEET ---
${PERSONA_DOC}
--- END CHARACTER SHEET ---

Rules:
- Reply in the SAME language the guest just wrote in (English or Chinese) — mirror them,
  don't default to one language regardless of input.
- Keep it short and conversational, like real bar dialogue: usually 1-3 sentences.
- Never break character. Never mention being an AI, a model, or a prompt.
- The scar's real backstory (tripping on stage) is a rare easter egg — don't volunteer it
  unless the guest has pushed hard / asked about the scar more than once.`;

const ORDER_MODE_SUFFIX = `You are in ORDER mode — the guest is deciding what to eat. Below is tonight's menu
catalog: "id: 中文名/English name [category] taste=... mood=...".
When it fits naturally, recommend 1-3 specific dishes from this catalog by id — don't
force a recommendation into every single line if the guest is just chatting mid-order.
Respond ONLY with JSON of this shape:
{"reply": "<what Sullivan says, in character>", "dish_ids": [<ids you're recommending this turn, or [] if none>]}

--- TONIGHT'S MENU ---
${MENU_CATALOG}
--- END MENU ---`;

const CHAT_MODE_SUFFIX = `You are in CHAT mode — the guest just wants to talk, not order food. Don't recommend
dishes in this mode. Respond ONLY with JSON of this shape:
{"reply": "<what Sullivan says, in character>"}`;

const ORDER_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    reply: { type: Type.STRING },
    dish_ids: { type: Type.ARRAY, items: { type: Type.INTEGER } },
  },
  required: ["reply"],
};
const CHAT_SCHEMA = {
  type: Type.OBJECT,
  properties: { reply: { type: Type.STRING } },
  required: ["reply"],
};

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  try {
    const body = req.body || {};
    const message = String(body.message || "").trim();
    const history = Array.isArray(body.history) ? body.history : [];
    const mode = body.mode === "order" ? "order" : "chat";
    const guestName = String(body.guestName || "Friend").trim().slice(0, 40);

    if (!message) {
      res.status(400).json({ error: "empty message" });
      return;
    }

    const systemPrompt =
      mode === "order"
        ? SYSTEM_PROMPT_BASE + "\n\n" + ORDER_MODE_SUFFIX
        : SYSTEM_PROMPT_BASE + "\n\n" + CHAT_MODE_SUFFIX;
    const schema = mode === "order" ? ORDER_SCHEMA : CHAT_SCHEMA;

    const contents = [];
    for (const turn of history.slice(-20)) {
      const text = String((turn && turn.text) || "").trim();
      if (!text) continue;
      const role = turn.role === "sullivan" ? "model" : "user";
      contents.push({ role, parts: [{ text }] });
    }
    contents.push({ role: "user", parts: [{ text: `[Guest name: ${guestName}] ${message}` }] });

    const response = await client().models.generateContent({
      model: MODEL,
      contents,
      config: {
        systemInstruction: systemPrompt,
        responseMimeType: "application/json",
        responseSchema: schema,
        temperature: 0.9,
      },
    });

    const data = JSON.parse(response.text);
    res.status(200).json({
      reply: data.reply || "...",
      dish_ids: mode === "order" ? data.dish_ids || [] : [],
    });
  } catch (err) {
    console.error("Gemini call failed:", err);
    res.status(502).json({ error: "gemini_call_failed", detail: String((err && err.message) || err) });
  }
};
