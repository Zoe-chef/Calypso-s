import base64, pathlib

BASE = pathlib.Path(__file__).resolve().parent
RES = BASE / "resized"
TEMPLATE = BASE / "order_template.html"
OUT = BASE / "dinner-club-order-real.html"
SERVER_OUT = BASE.parent / "server" / "index.html"
ROOT_OUT = BASE.parent / "index.html"  # what Vercel serves as the static homepage

mapping = {
    "__SCENE_DAY__": "scene_day.png",
    "__SCENE_NIGHT__": "scene_night.png",
    "__ROPE_HANGING__": "rope_hanging.png",
    "__NORMAL__": "normal.png",
    "__ICON_TALK__": "icon_talk.png",
    "__ICON_MENU__": "icon_menu.png",
    "__ICON_BAR__": "icon_bar.png",
    "__COUNTER_FRONT__": "bar_counter_front.png",
    "__RECEIPT_BG__": "receipt.png",
    "__NOTE_BG__": "note.png",
}
for i in range(1, 3):
    mapping[f"__CUP_{i}__"] = f"cup_{i}.png"
for i in range(1, 6):
    mapping[f"__PEN_{i}__"] = f"pen_{i}.png"
for i in range(1, 6):
    mapping[f"__ROPE_{i}__"] = f"rope_{i}.png"

html = TEMPLATE.read_text(encoding="utf-8")

for token, filename in mapping.items():
    data = (RES / filename).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    uri = f"data:image/png;base64,{b64}"
    if token not in html:
        raise SystemExit(f"token missing in template: {token}")
    html = html.replace(token, uri)

menu_json = (BASE / "menu_data.min.json").read_text(encoding="utf-8")
if "__MENU_DATA_JSON__" not in html:
    raise SystemExit("token missing in template: __MENU_DATA_JSON__")
html = html.replace("__MENU_DATA_JSON__", menu_json)

OUT.write_text(html, encoding="utf-8")
print("wrote", OUT, OUT.stat().st_size / 1024 / 1024, "MB")

if SERVER_OUT.parent.exists():
    SERVER_OUT.write_text(html, encoding="utf-8")
    print("wrote", SERVER_OUT, "(served by server/app.py, local dev only)")

ROOT_OUT.write_text(html, encoding="utf-8")
print("wrote", ROOT_OUT, "(served by Vercel as the live site)")
