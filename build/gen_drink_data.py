"""
Converts drink_menu_final.xlsx (34 drinks: Beer, Shot, Cocktail, Non-Alcoholic,
Juice) into build/drink_data.min.json, the same way menu_final.xlsx feeds the
food menu. Run whenever the spreadsheet changes:

    python3 build/gen_drink_data.py
"""
import json
import re
import pathlib

import openpyxl

BASE = pathlib.Path(__file__).resolve().parent
XLSX = BASE.parent / "drink_menu_final.xlsx"
OUT = BASE / "drink_data.min.json"


def split_list(s):
    if not s:
        return []
    return [x.strip() for x in re.split(r"[,，、]", s) if x.strip()]


wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb["drinks"]
rows = list(ws.iter_rows(values_only=True))
header = rows[0]
raw = [dict(zip(header, r)) for r in rows[1:]]

drinks = []
for i, d in enumerate(raw, start=1001):
    en_ing = split_list(d["ingredients"])
    cn_ing = split_list(d["ingredients_cn"])
    ingredients = [{"en": e, "cn": (cn_ing[j] if j < len(cn_ing) else "")} for j, e in enumerate(en_ing)]
    drinks.append({
        "id": i,
        "cn": d["drink_name_cn"],
        "en": d["drink_name"],
        "category": d["category"],  # Beer | Shot | Cocktail | Non-Alcoholic | Juice
        "base_spirit": d["base_spirit"],  # Vodka/Whisky/Rum/Gin/Tequila/Brandy, or null
        "ingredients": ingredients,
        "vibe": split_list(d["vibe_tags"]),
        "note": d["sullivan_recommendation"],
    })

OUT.write_text(json.dumps({"drinks": drinks}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("wrote", OUT, "-", len(drinks), "drinks")
