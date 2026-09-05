# Sullivan's Bar (Calypso's)

A browser prototype for a friends' dinner club, with a real Gemini-backed
bartender (Sullivan) you can chat with.

## Layout

- `index.html` — the built frontend (single self-contained HTML page). This
  is what Vercel serves as the live site. Don't hand-edit it — it's
  generated, see below.
- `api/chat.js` — the Vercel serverless function that holds the Gemini API
  key and calls the Gemini API on the frontend's behalf. The browser never
  sees the key.
- `api/_data.js` — Sullivan's persona + the menu catalog, baked into a plain
  JS module so the function never has to read files at request time.
  Generated, don't hand-edit — see below.
- `build/` — the source template (`order_template.html`) and the scripts
  that generate everything above. Not deployed (see `.vercelignore`).
- `server/` — a Flask app for local development only (not deployed to
  Vercel). Handy for quickly testing UI changes against a real Gemini call
  without pushing anything.
- `Sullivan_人设文档.md`, `menu_final.xlsx` — source of truth for the persona
  and the menu.

## Making changes

1. Edit `build/order_template.html` (frontend) and/or `Sullivan_人设文档.md` /
   `menu_final.xlsx` (persona / menu — menu changes also need re-exporting to
   `build/menu_data.min.json`, see the menu-import notes for that step).
2. Regenerate everything:
   ```bash
   cd build
   python3 build.py            # rebuilds index.html (root + server/)
   python3 gen_api_data.py     # rebuilds api/_data.js from the persona + menu
   ```
3. Test locally with the Flask server (real Gemini calls, your key from
   `server/.env`):
   ```bash
   cd server
   ./venv/bin/python app.py    # http://127.0.0.1:5050
   ```
4. Commit and push — Vercel redeploys automatically from `main`.

## Environment variables (set in Vercel, never committed)

- `GEMINI_API_KEY` — required.
- `GEMINI_MODEL` — optional, defaults to `gemini-3.6-flash`.

For local dev, the equivalent lives in `server/.env` (copy
`server/.env.example`); that file is gitignored.
