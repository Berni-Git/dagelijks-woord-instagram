#!/usr/bin/env python3
"""
Génère une image carrée (1080x1080, format Instagram) avec le verset du jour,
sur fond de photo de nature (montagne, forêt, plage, étoiles, terre depuis
l'espace, désert, cascade, lac...) récupérée via l'API Unsplash.

Le verset lui-même vient de BijbelAPI (bijbelapi.com), une API néerlandaise
gratuite qui expose un endpoint "verset du jour" basé sur la date et qui
pioche dans toute la Bible (Statenvertaling) — donc des milliers de versets
possibles, pas de répétition avant très longtemps. Si cette API est
indisponible un jour (panne, quota, pas de réseau...), le script bascule sur
la petite liste locale `verses.json` en secours, pour que la publication ne
soit jamais bloquée.

Nécessite la variable d'environnement UNSPLASH_ACCESS_KEY (sinon fond de
couleur unie utilisé automatiquement).
"""
import io
import json
import os
from datetime import date

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1080
TEXT_COLOR = (250, 250, 245)
ACCENT_COLOR = (232, 196, 120)  # doré, lisible sur fond sombre
FALLBACK_BG = (25, 32, 44)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "images")
OUT_PATH = os.path.join(OUT_DIR, "verse_of_the_day.png")

FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Thèmes nature uniquement — surtout pas de bâtiments / architecture.
# "topics=6sMVjTLSkeQ" restreint la recherche au topic officiel Unsplash "Nature".
NATURE_TOPIC_ID = "6sMVjTLSkeQ"
NATURE_QUERIES = [
    "mountain landscape",
    "forest trees sunlight",
    "ocean beach waves",
    "starry night sky",
    "earth from space",
    "desert dunes",
    "waterfall nature",
    "lake reflection mountains",
    "sunrise landscape nature",
    "snowy mountains nature",
    "northern lights aurora",
    "green valley nature",
]


def find_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fetch_online_verse():
    """
    Récupère le verset du jour depuis BijbelAPI (bijbelapi.com), en
    néerlandais (Statenvertaling). Retourne None si l'appel échoue ou si la
    réponse est inattendue, pour déclencher le secours local.
    """
    try:
        resp = requests.get(
            "https://bijbelapi.com/api/daytext",
            params={"version": "hs1917", "date": date.today().isoformat()},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        text = data.get("text")
        if not text or len(text.strip()) < 5:
            print("BijbelAPI : réponse sans texte exploitable, secours local utilisé.")
            return None

        book = data.get("book")
        chapter = data.get("chapter")
        verse = data.get("verse")
        if book and chapter and verse:
            reference = f"{book} {chapter}:{verse}"
        else:
            reference = data.get("reference") or ""

        print(f"Verset récupéré via BijbelAPI : {reference}")
        return {"reference": reference, "text": text.strip()}
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Échec BijbelAPI ({e}) : secours sur la liste locale de versets.")
        return None


def pick_local_verse():
    """Secours local : liste restreinte de versets, en cas de panne de l'API."""
    with open(os.path.join(HERE, "verses.json"), encoding="utf-8") as f:
        verses = json.load(f)
    idx = date.today().timetuple().tm_yday % len(verses)
    return verses[idx]


def pick_verse():
    return fetch_online_verse() or pick_local_verse()


def pick_query():
    idx = date.today().timetuple().tm_yday % len(NATURE_QUERIES)
    return NATURE_QUERIES[idx]


def fetch_nature_background():
    """Récupère une photo de nature carrée depuis Unsplash. Retourne None en cas d'échec."""
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not access_key:
        print("UNSPLASH_ACCESS_KEY absent : fond de couleur unie utilisé.")
        return None
    query = pick_query()
    try:
        resp = requests.get(
            "https://api.unsplash.com/photos/random",
            params={
                "query": query,
                "topics": NATURE_TOPIC_ID,
                "orientation": "squarish",
                "content_filter": "high",
            },
            headers={"Authorization": f"Client-ID {access_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        image_url = data["urls"]["regular"]
        # Bonne pratique Unsplash : signaler le téléchargement (non bloquant si ça échoue)
        try:
            requests.get(
                data["links"]["download_location"],
                headers={"Authorization": f"Client-ID {access_key}"},
                timeout=10,
            )
        except requests.RequestException:
            pass

        img_resp = requests.get(image_url, timeout=20)
        img_resp.raise_for_status()
        img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
        return crop_to_square(img)
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"Échec de récupération Unsplash ({e}) : fond de couleur unie utilisé.")
        return None


def crop_to_square(img):
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_image(verse):
    bg = fetch_nature_background()
    if bg is None:
        base = Image.new("RGB", (SIZE, SIZE), FALLBACK_BG)
    else:
        # Léger flou + assombrissement de l'ensemble pour la lisibilité générale
        base = bg.filter(ImageFilter.GaussianBlur(1.5))
        dark_overlay = Image.new("RGBA", (SIZE, SIZE), (10, 12, 18, 90))
        base = Image.alpha_composite(base.convert("RGBA"), dark_overlay).convert("RGB")

    draw = ImageDraw.Draw(base, "RGBA")

    margin = 110
    max_width = SIZE - 2 * margin

    text_len = len(verse["text"])
    if text_len < 90:
        font_size = 58
    elif text_len < 180:
        font_size = 48
    elif text_len < 280:
        font_size = 38
    else:
        font_size = 32

    verse_font = find_font(FONT_CANDIDATES_REGULAR, font_size)
    ref_font = find_font(FONT_CANDIDATES_BOLD, 32)

    lines = wrap_text(draw, verse["text"], verse_font, max_width)
    line_height = int(font_size * 1.4)
    block_height = len(lines) * line_height

    ref_text = verse["reference"].upper()
    extra_for_ref = 90

    total_height = block_height + extra_for_ref
    start_y = (SIZE - total_height) // 2

    # Panneau semi-transparent derrière le texte pour garantir la lisibilité
    # quel que soit le fond (ciel clair, sable, neige...).
    pad_x, pad_y = 60, 50
    panel_top = start_y - pad_y
    panel_bottom = start_y + total_height + pad_y
    draw.rounded_rectangle(
        [(margin - pad_x, panel_top), (SIZE - margin + pad_x, panel_bottom)],
        radius=28,
        fill=(8, 10, 16, 120),
    )

    y = start_y
    for line in lines:
        w = draw.textlength(line, font=verse_font)
        x = (SIZE - w) / 2
        draw.text((x, y), line, font=verse_font, fill=TEXT_COLOR)
        y += line_height

    ref_w = draw.textlength(ref_text, font=ref_font)
    draw.text(((SIZE - ref_w) / 2, y + 30), ref_text, font=ref_font, fill=ACCENT_COLOR)

    line_w = 70
    draw.rectangle(
        [(SIZE - line_w) / 2, y + 20, (SIZE + line_w) / 2, y + 23],
        fill=ACCENT_COLOR,
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    base.save(OUT_PATH, "PNG")
    return OUT_PATH


if __name__ == "__main__":
    verse = pick_verse()
    path = make_image(verse)
    print(f"Image générée : {path}")
    print(f"Verset : {verse['reference']} — {verse['text']}")
    caption = f"{verse['text']}\n\n— {verse['reference']}\n\n#bijbeltekstvandedag #bijbel #geloof #gebed #jezus #god #bijbelvers #natuur"
    with open(os.path.join(HERE, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
