"""
UI/Shot.jpeg came out of the asset pipeline with a checkerboard "transparency
preview" baked into its actual pixels (JPEG can't hold real alpha), so it's
unusable as a plain icon. Props/Shot.jpeg has the same glass art on a clean
flat grey backdrop, so we chroma-key that one instead and crop it down to a
transparent icon, matching Beer/Cocktail/Juice's style.
"""
from PIL import Image, ImageDraw
import numpy as np
import pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent / "Assets"
SRC = BASE / "Props" / "Shot.jpeg"
OUT = BASE / "UI" / "Shot.png"

im = Image.open(SRC).convert("RGBA")
w, h = im.size

for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 2), (2, h // 2), (w - 2, h // 2)]:
    ImageDraw.floodfill(im, corner, (0, 0, 0, 0), thresh=35)

# The source also has a floor reflection below the glass, disconnected from it
# by a gap — cut it off there so only the glass itself becomes the icon.
alpha_arr = np.array(im.split()[3])
row_has_content = (alpha_arr > 200).sum(axis=1)
content_rows = np.where(row_has_content > 3)[0]
first_row = int(content_rows.min())
last_row = first_row
prev = first_row
for r in content_rows[1:]:
    if r - prev > 15:
        break
    last_row = r
    prev = r
im = im.crop((0, first_row, w, last_row + 1))
w, h = im.size

bbox = im.split()[3].getbbox()
pad_x = int((bbox[2] - bbox[0]) * 0.12)
pad_y = int((bbox[3] - bbox[1]) * 0.08)
crop_box = (
    max(0, bbox[0] - pad_x),
    max(0, bbox[1] - pad_y),
    min(w, bbox[2] + pad_x),
    min(h, bbox[3] + pad_y),
)
cropped = im.crop(crop_box)
# Downscale — the source is a huge 2048x2048 render, way bigger than needed.
target_h = 480
scale = target_h / cropped.size[1]
resized = cropped.resize((max(1, int(cropped.size[0] * scale)), target_h), Image.LANCZOS)
resized.save(OUT)
print("wrote", OUT, resized.size)
