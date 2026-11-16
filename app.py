import os
import base64
import io
import time
import random
import urllib.parse
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from PIL import Image
import requests

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

FURRY_STYLES = {
    "classic": {
        "label": "Классика",
        "emoji": "🦊",
        "animal": "fox",
        "prompt_extra": "fox furry, orange fur, fox ears, fox tail with white tip, anthropomorphic fox character",
    },
    "wolf": {
        "label": "Волк",
        "emoji": "🐺",
        "animal": "wolf",
        "prompt_extra": "wolf furry, grey wolf fur, pointed wolf ears, wolf snout, bushy wolf tail, anthropomorphic wolf character",
    },
    "fox": {
        "label": "Лиса",
        "emoji": "🦊",
        "animal": "fox",
        "prompt_extra": "fox furry, orange and white fox fur, large fox ears, fox muzzle, fluffy fox tail, anthropomorphic fox character",
    },
    "cat": {
        "label": "Кошка",
        "emoji": "🐱",
        "animal": "cat",
        "prompt_extra": "neko cat furry, cat ears, cat eyes with slit pupils, whiskers, cat tail, anime style, anthropomorphic cat character",
    },
    "dragon": {
        "label": "Дракон",
        "emoji": "🐉",
        "animal": "dragon",
        "prompt_extra": "dragon fursona, dragon horns, scales, reptilian eyes, dragon wings, dragon tail, fantasy style, anthropomorphic dragon character",
    },
    "bunny": {
        "label": "Зайчик",
        "emoji": "🐰",
        "animal": "bunny",
        "prompt_extra": "bunny furry, long rabbit ears, soft white fur, bunny nose, cottontail, cute style, anthropomorphic bunny character",
    },
}


def analyze_photo_with_gemini(image_bytes: bytes) -> str:
    """Use Gemini free vision to describe the person in the photo."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
        return ""

    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_b64
                        }
                    },
                    {
                        "text": (
                            "Describe this person's appearance for use in a furry art prompt. "
                            "Include: hair color, approximate age range (young/adult/etc), "
                            "clothing style, pose, expression, and any notable features. "
                            "Keep it short, 1-2 sentences, focus on visual details. "
                            "Reply in English only."
                        )
                    }
                ]
            }],
            "generationConfig": {"maxOutputTokens": 150}
        }

        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            description = data["candidates"][0]["content"]["parts"][0]["text"]
            return description.strip()
    except Exception:
        pass

    return ""


def build_prompt(style: dict, person_description: str) -> str:
    """Build a detailed furry art prompt."""
    base = (
        f"anthropomorphic {style['animal']} character, {style['prompt_extra']}, "
        "high quality digital furry art, detailed fur texture, vibrant colors, "
        "clean lineart, professional furry fandom artwork, 4k"
    )

    if person_description:
        base = f"{base}, inspired by person: {person_description}"

    negative = (
        "ugly, deformed, bad anatomy, blurry, low quality, "
        "watermark, text, human face, realistic human, photo"
    )

    return base, negative


def generate_with_pollinations(prompt: str) -> bytes:
    """Call Pollinations.AI and return image bytes."""
    encoded = urllib.parse.quote(prompt)
    seed = random.randint(1, 999999)

    # No width/height/model — use defaults (free tier)
    url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}"

    resp = requests.get(url, timeout=120)

    if resp.status_code == 402:
        raise Exception("Лимит: 1 картинка каждые 45 секунд. Подождите немного и попробуйте снова.")

    resp.raise_for_status()
    return resp.content


def generate_furry_art(image_bytes: bytes, style_key: str) -> dict:
    style = FURRY_STYLES.get(style_key, FURRY_STYLES["classic"])

    try:
        # Step 1: Resize the uploaded photo
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((800, 800), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_bytes_small = buf.getvalue()

        # Step 2: Analyze photo with Gemini (free) to get person description
        person_desc = analyze_photo_with_gemini(img_bytes_small)

        # Step 3: Build prompt
        prompt, negative = build_prompt(style, person_desc)

        # Step 4: Generate with Pollinations.AI
        result_bytes = generate_with_pollinations(prompt)

        result_b64 = base64.b64encode(result_bytes).decode("utf-8")

        return {
            "success": True,
            "image": result_b64,
            "mime_type": "image/jpeg",
            "style_label": style["label"],
            "style_emoji": style["emoji"],
            "description": f"Описание фото: {person_desc}" if person_desc else "",
        }

    except requests.exceptions.ConnectionError:
        return {"error": "Нет соединения с сервером генерации. Проверьте интернет."}
    except requests.exceptions.Timeout:
        return {"error": "Таймаут — сервер не ответил. Попробуйте снова."}
    except Exception as e:
        return {"error": f"Ошибка генерации: {str(e)}"}


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", styles=FURRY_STYLES)


@app.route("/generate", methods=["POST"])
def generate():
    if "photo" not in request.files:
        return jsonify({"error": "Фото не загружено"}), 400

    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"error": "Выберите файл"}), 400

    style_key = request.form.get("style", "classic")
    if style_key not in FURRY_STYLES:
        style_key = "classic"

    image_bytes = file.read()
    result = generate_furry_art(image_bytes, style_key)

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route("/styles")
def get_styles():
    return jsonify({k: {"label": v["label"], "emoji": v["emoji"]} for k, v in FURRY_STYLES.items()})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "api_configured": True,  # Pollinations.AI doesn't need a key
        "gemini_key": bool(GEMINI_API_KEY and GEMINI_API_KEY != "your_api_key_here"),
        "generator": "pollinations.ai"
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  FurryArt AI — Pollinations.AI Edition")
    print("=" * 55)
    has_gemini = bool(GEMINI_API_KEY and GEMINI_API_KEY != "your_api_key_here")
    if has_gemini:
        print("  Gemini API: есть (анализ фото включён)")
    else:
        print("  Gemini API: нет (базовый режим)")
    print("  Генерация: Pollinations.AI (бесплатно)")
    print("=" * 55)
    print("  Открыть: http://localhost:5000")
    print("=" * 55)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
