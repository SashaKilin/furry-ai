import os
import base64
import io
import time
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from PIL import Image
import requests

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

# AI Horde — бесплатная сеть Stable Diffusion (img2img)
HORDE_API_URL = "https://aihorde.net/api/v2/generate/async"
HORDE_CHECK_URL = "https://aihorde.net/api/v2/generate/check/"
HORDE_STATUS_URL = "https://aihorde.net/api/v2/generate/status/"
HORDE_API_KEY = os.getenv("HORDE_API_KEY", "0000000000")  # Бесплатный анонимный доступ

FURRY_STYLES = {
    "classic": {
        "label": "Классика",
        "emoji": "🦊",
        "prompt": (
            "anthropomorphic furry fox character, detailed fluffy fur texture, animal fox ears, "
            "cute fox muzzle, expressive eyes, beautiful digital furry fanart, masterpiece, vibrant colors"
        ),
    },
    "wolf": {
        "label": "Волк",
        "emoji": "🐺",
        "prompt": (
            "anthropomorphic furry wolf character, thick grey and black wolf fur, pointed wolf ears, "
            "detailed wolf muzzle, piercing friendly eyes, digital furry art, cinematic lighting, masterpiece"
        ),
    },
    "fox": {
        "label": "Лиса",
        "emoji": "🦊",
        "prompt": (
            "anthropomorphic cute red fox character, orange and white fluffy fur, large pointy fox ears, "
            "fluffy tail, fox snout, warm soft lighting, detailed furry artwork"
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
            "cute bunny nose, big expressive innocent eyes, sweet pastel colors, detailed furry art"
        ),
    },
}

NEGATIVE_PROMPT = (
    "human ears, human nose, realistic human face, duplicate, watermark, signature, text, "
    "low quality, distorted anatomy, extra limbs, bad eyes, blur, mutated, ugly, poorly drawn"
)


def prepare_image_b64(image_bytes: bytes) -> str:
    """Подготовка и сжатие изображения под Stable Diffusion (512x512 или 768x768 WebP)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # Ресайз до 512-768 для быстрого рендеринга на воркерах
    img.thumbnail((768, 768), Image.LANCZOS)
    
    # Кратность 64
    w = max(512, (img.width // 64) * 64)
    h = max(512, (img.height // 64) * 64)
    img = img.resize((w, h), Image.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_furry_art(image_bytes: bytes, style_key: str) -> dict:
    """Полноценный Image-to-Image через децентрализованную сеть AI Horde."""
    style = FURRY_STYLES.get(style_key, FURRY_STYLES["classic"])

    try:
        img_b64 = prepare_image_b64(image_bytes)
        
        # Формируем промпт: позитивный + разделитель '###' + негативный
        full_prompt = f"{style['prompt']} ### {NEGATIVE_PROMPT}"

        payload = {
            "prompt": full_prompt,
            "params": {
                "steps": 25,
                "cfg_scale": 7.5,
                "sampler_name": "k_euler_a",
                # denoising_strength: 0.65 (сохраняет форму лица, позу и одежду, меняя детали на фурри)
                "denoising_strength": 0.65,
                "clip_skip": 1
            },
            "source_image": img_b64,
            "source_processing": "img2img",
            "models": ["stable_diffusion"],
            "r2": True
        }

        headers = {
            "apikey": HORDE_API_KEY,
            "Client-Agent": "FurryArtAI:1.0"
        }

        # Отправляем задачу на воркер
        resp = requests.post(HORDE_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code != 202:
            return {"error": f"Ошибка отправки задачи ({resp.status_code}): {resp.text}"}

        task_id = resp.json().get("id")
        if not task_id:
            return {"error": "Не удалось получить ID задачи от нейросети."}

        # Ожидаем выполнение (до 90 секунд)
        for _ in range(45):
            time.sleep(2)
            check_resp = requests.get(f"{HORDE_CHECK_URL}{task_id}", headers=headers, timeout=15)
            
            if check_resp.status_code == 200:
                status_data = check_resp.json()
                if status_data.get("done"):
                    # Получаем результат
                    result_resp = requests.get(f"{HORDE_STATUS_URL}{task_id}", headers=headers, timeout=15)
                    if result_resp.status_code == 200:
                        gen_data = result_resp.json()
                        generations = gen_data.get("generations", [])
                        if generations:
                            img_data = generations[0].get("img")
                            
                            # Если это URL на Cloudflare R2
                            if img_data.startswith("http"):
                                img_bytes = requests.get(img_data, timeout=30).content
                                img_b64_res = base64.b64encode(img_bytes).decode("utf-8")
                            else:
                                img_b64_res = img_data

                            return {
                                "success": True,
                                "image": img_b64_res,
                                "mime_type": "image/webp",
                                "style_label": style["label"],
                                "style_emoji": style["emoji"],
                                "description": "Сгенерировано нейросетью Stable Diffusion Image-to-Image",
                            }

        return {"error": "Время ожидания генерации истекло. Попробуйте снова через минуту."}

    except requests.exceptions.Timeout:
        return {"error": "Таймаут соединения с нейросетью. Попробуйте снова."}
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
    return jsonify({
        "status": "ok",
        "api_configured": True,
        "engine": "AI Horde Stable Diffusion (img2img)"
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  🐾 FurryArt AI — Stable Diffusion (Image-to-Image)")
    print("=" * 55)
    print("  ✅  Движок: AI Horde (Бесплатный Stable Diffusion img2img)")
    print("  🌐  Локальный запуск: http://localhost:5000")
    print("=" * 55)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
