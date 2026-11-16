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

GETIMG_API_KEY = os.getenv("GETIMG_API_KEY", "")
GETIMG_URL = "https://api.getimg.ai/v1/essential-v2/image-to-image"

FURRY_STYLES = {
    "classic": {
        "label": "Классика",
        "emoji": "🦊",
        "prompt": (
            "anthropomorphic furry fox character, fluffy fur, animal fox ears, cute fox snout, "
            "detailed fur texture, beautiful digital furry art, vibrant colors, expressive eyes, masterpiece"
        ),
    },
    "wolf": {
        "label": "Волк",
        "emoji": "🐺",
        "prompt": (
            "anthropomorphic furry wolf character, thick wolf fur, pointed wolf ears on head, "
            "detailed wolf muzzle, sharp friendly eyes, high quality digital furry artwork, cinematic lighting"
        ),
    },
    "fox": {
        "label": "Лиса",
        "emoji": "🦊",
        "prompt": (
            "anthropomorphic red fox character, orange and white fluffy fur, large fluffy fox ears, "
            "fox nose, detailed fur shading, high quality furry fanart, warm soft lighting"
        ),
    },
    "cat": {
        "label": "Кошка",
        "emoji": "🐱",
        "prompt": (
            "anthropomorphic feline cat character, soft fluffy cat ears, whiskers, small cat nose, "
            "cat eyes with vertical pupils, cute anime furry aesthetic, soft pastel colors, masterpiece"
        ),
    },
    "dragon": {
        "label": "Дракон",
        "emoji": "🐉",
        "prompt": (
            "anthropomorphic dragon scalie character, sleek dragon horns, iridescent scales, "
            "reptilian slit eyes, epic fantasy furry art, detailed scales texture, dramatic lighting"
        ),
    },
    "bunny": {
        "label": "Зайчик",
        "emoji": "🐰",
        "prompt": (
            "anthropomorphic cute bunny rabbit character, long rabbit ears, soft fluffy fur, "
            "cute bunny nose, big expressive eyes, sweet pastel colors, detailed digital furry artwork"
        ),
    },
}

NEGATIVE_PROMPT = (
    "human ears, human nose, photographic human skin, ugly, deformed, blurry, bad anatomy, "
    "low quality, distorted face, extra limbs, watermark, text"
)


def prepare_image_b64(image_bytes: bytes) -> str:
    """Подготавливает изображение под требования GetImg.ai (макс 1024x1024, JPEG)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((1024, 1024), Image.LANCZOS)
    
    # Кратность 64 для нейросети
    w = max(512, (img.width // 64) * 64)
    h = max(512, (img.height // 64) * 64)
    img = img.resize((w, h), Image.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_furry_art(image_bytes: bytes, style_key: str) -> dict:
    """Настоящий Image-to-Image через GetImg.ai."""
    if not GETIMG_API_KEY or GETIMG_API_KEY == "your_getimg_key_here":
        return {"error": "API ключ GetImg.ai не настроен. Добавьте GETIMG_API_KEY в файл .env"}

    style = FURRY_STYLES.get(style_key, FURRY_STYLES["classic"])

    try:
        img_b64 = prepare_image_b64(image_bytes)

        payload = {
            "image": img_b64,
            "prompt": style["prompt"],
            "negative_prompt": NEGATIVE_PROMPT,
            # strength 0.65: сохраняет позу, освещение и черты фото, но трансформирует в фурри
            "strength": 0.65,
            "steps": 25,
            "guidance": 7.5,
            "output_format": "jpeg"
        }

        headers = {
            "Authorization": f"Bearer {GETIMG_API_KEY}",
            "Content-Type": "application/json"
        }

        resp = requests.post(GETIMG_URL, json=payload, headers=headers, timeout=120)

        if resp.status_code == 200:
            data = resp.json()
            img_result_b64 = data.get("image", "")

            return {
                "success": True,
                "image": img_result_b64,
                "mime_type": "image/jpeg",
                "style_label": style["label"],
                "style_emoji": style["emoji"],
                "description": "Сгенерировано строго по вашему фото (GetImg.ai Image-to-Image)",
            }

        elif resp.status_code == 401:
            return {"error": "Неверный API ключ GetImg.ai. Проверьте GETIMG_API_KEY в файле .env"}
        elif resp.status_code == 429:
            return {"error": "Лимит запросов исчерпан. Попробуйте чуть позже."}
        else:
            try:
                err_text = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err_text = resp.text
            return {"error": f"Ошибка GetImg.ai ({resp.status_code}): {err_text}"}

    except requests.exceptions.Timeout:
        return {"error": "Таймаут — сервис генерации не ответил за 2 минуты. Попробуйте снова."}
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
    has_key = bool(GETIMG_API_KEY and GETIMG_API_KEY != "your_getimg_key_here")
    return jsonify({
        "status": "ok",
        "api_configured": has_key,
        "engine": "GetImg.ai Image-to-Image"
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  🐾 FurryArt AI — GetImg.ai Image-to-Image Edition")
    print("=" * 55)
    if not GETIMG_API_KEY or GETIMG_API_KEY == "your_getimg_key_here":
        print("  ⚠️  Внимание: GETIMG_API_KEY не установлен!")
        print("  Получить бесплатно: https://getimg.ai/dashboard/api-keys")
    else:
        print("  ✅  GetImg.ai API ключ подключен!")
    print("=" * 55)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
