import os
import base64
import io
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from PIL import Image
import requests

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

SEGMIND_API_KEY = os.getenv("SEGMIND_API_KEY", "")
SEGMIND_URL = "https://api.segmind.com/v1/sdxl-img2img"

FURRY_STYLES = {
    "classic": {
        "label": "Классика",
        "emoji": "🦊",
        "prompt": (
            "anthropomorphic furry fox character, fluffy fur, animal fox ears on top of head, "
            "fox muzzle, black nose, detailed fur texture, digital furry artwork, "
            "highly detailed, beautiful lighting, artstation trending, vibrant colors, expressive eyes"
        ),
    },
    "wolf": {
        "label": "Волк",
        "emoji": "🐺",
        "prompt": (
            "anthropomorphic furry wolf character, thick grey and black wolf fur, pointed wolf ears, "
            "detailed wolf muzzle, fierce yet friendly expression, digital furry art, "
            "cinematic lighting, sharp details, fantasy aesthetic"
        ),
    },
    "fox": {
        "label": "Лиса",
        "emoji": "🦊",
        "prompt": (
            "anthropomorphic cute red fox character, orange and white fluffy fur, large pointy fox ears, "
            "fluffy tail, fox snout, beautiful expressive eyes, high quality digital furry fanart, "
            "warm soft lighting, smooth lineart"
        ),
    },
    "cat": {
        "label": "Кошка",
        "emoji": "🐱",
        "prompt": (
            "anthropomorphic feline cat furry character, fluffy cat ears, whiskers, small cat nose, "
            "feline eyes with slit pupils, soft detailed fur, anime-inspired furry art, "
            "cute aesthetic, vibrant pastel palette, masterpiece"
        ),
    },
    "dragon": {
        "label": "Дракон",
        "emoji": "🐉",
        "prompt": (
            "anthropomorphic dragon scalie character, sleek dragon horns, iridescent scales, "
            "reptilian slit eyes, subtle frills, epic fantasy digital art, "
            "dramatic lighting, highly detailed scales texture, masterpiece"
        ),
    },
    "bunny": {
        "label": "Зайчик",
        "emoji": "🐰",
        "prompt": (
            "anthropomorphic bunny rabbit character, long upright rabbit ears, soft fluffy fur, "
            "cute bunny nose, big expressive innocent eyes, sweet pastel colors, "
            "whimsical fantasy furry artwork, high detail"
        ),
    },
}

NEGATIVE_PROMPT = (
    "human ears, human skin, human nose, photographic human, duplicate, watermark, signature, "
    "text, low quality, distorted anatomy, extra limbs, bad eyes, blur, mutated, ugly, poorly drawn"
)


def prepare_image_b64(image_bytes: bytes) -> str:
    """Оптимизация размера изображения под модель (макс 1024x1024, JPEG)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # SDXL лучше всего работает с размерами кратно 64 (например 1024x1024 или 768x768)
    img.thumbnail((1024, 1024), Image.LANCZOS)
    
    # Подгоняем под кратность 64
    w = (img.width // 64) * 64
    h = (img.height // 64) * 64
    w = max(512, w)
    h = max(512, h)
    img = img.resize((w, h), Image.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_furry_art(image_bytes: bytes, style_key: str) -> dict:
    """Настоящий img2img через Segmind SDXL."""
    if not SEGMIND_API_KEY or SEGMIND_API_KEY == "your_segmind_key_here":
        return {"error": "API ключ Segmind не настроен. Добавьте SEGMIND_API_KEY в файл .env"}

    style = FURRY_STYLES.get(style_key, FURRY_STYLES["classic"])

    try:
        # Подготовка фото
        img_b64 = prepare_image_b64(image_bytes)

        # Параметры img2img
        payload = {
            "image": img_b64,
            "prompt": style["prompt"],
            "negative_prompt": NEGATIVE_PROMPT,
            "samples": 1,
            "scheduler": "dpmpp_2m",
            "num_inference_steps": 25,
            "guidance_scale": 7.5,
            # strength определяет, насколько сильно меняется фото:
            # 0.68 идеально: лицо и форма человека перерисовываются в персонажа, но сохраняется поза и композиция
            "strength": 0.68,
            "base64": True
        }

        headers = {
            "x-api-key": SEGMIND_API_KEY,
            "Content-Type": "application/json"
        }

        resp = requests.post(SEGMIND_URL, json=payload, headers=headers, timeout=120)

        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            
            # Если вернулся JSON с base64
            if "application/json" in content_type:
                data = resp.json()
                img_result_b64 = data.get("image", "")
            else:
                # Если вернулась чистая картинка байтами
                img_result_b64 = base64.b64encode(resp.content).decode("utf-8")

            return {
                "success": True,
                "image": img_result_b64,
                "mime_type": "image/jpeg",
                "style_label": style["label"],
                "style_emoji": style["emoji"],
                "description": "Сгенерировано на базе вашего фото (SDXL Image-to-Image)",
            }

        elif resp.status_code == 401 or resp.status_code == 403:
            return {"error": "Неверный API ключ Segmind. Проверьте SEGMIND_API_KEY в файле .env"}
        elif resp.status_code == 429:
            return {"error": "Превышен лимит запросов Segmind или закончились бесплатные кредиты на сегодня."}
        else:
            try:
                err_text = resp.json().get("message", resp.text)
            except Exception:
                err_text = resp.text
            return {"error": f"Ошибка Segmind API ({resp.status_code}): {err_text}"}

    except requests.exceptions.Timeout:
        return {"error": "Таймаут — сервер Segmind не ответил вовремя. Попробуйте снова."}
    except requests.exceptions.ConnectionError:
        return {"error": "Ошибка подключения к сети. Проверьте интернет."}
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

    image_bytes = file.read()
    style_key = request.form.get("style", "classic")
    if style_key not in FURRY_STYLES:
        style_key = "classic"

    result = generate_furry_art(image_bytes, style_key)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route("/styles")
def get_styles():
    return jsonify({k: {"label": v["label"], "emoji": v["emoji"]} for k, v in FURRY_STYLES.items()})


@app.route("/health")
def health():
    has_key = bool(SEGMIND_API_KEY and SEGMIND_API_KEY != "your_segmind_key_here")
    return jsonify({
        "status": "ok",
        "api_configured": has_key,
        "engine": "Segmind SDXL Img2Img"
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  🐾 FurryArt AI — Segmind SDXL Img2Img Edition")
    print("=" * 55)
    if not SEGMIND_API_KEY or SEGMIND_API_KEY == "your_segmind_key_here":
        print("  ⚠️  Внимание: SEGMIND_API_KEY не установлен!")
        print("  Получить бесплатно: https://www.segmind.com/api-keys")
    else:
        print("  ✅  Segmind API ключ подключен!")
    print("=" * 55)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
