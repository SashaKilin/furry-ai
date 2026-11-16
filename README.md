# 🐾 FurryArt AI — Генератор фурри-арта

Загружай фото — ИИ превратит тебя (или кого угодно) в фурри-персонажа!

## Возможности

- 📸 Загрузка фото (drag & drop или выбор файла)
- 🎨 6 стилей: Классика, Волк, Лиса, Кошка, Дракон, Зайчик
- ⬇️ Скачивание готового арта
- 🔄 Перегенерация одним кликом

## Установка

### 1. Получи API ключ Gemini (бесплатно)

Перейди на [aistudio.google.com/apikey](https://aistudio.google.com/apikey) и создай ключ.

### 2. Создай файл `.env`

```
GEMINI_API_KEY=вставь_свой_ключ_сюда
```

### 3. Установи зависимости

```bash
pip install -r requirements.txt
```

### 4. Запусти приложение

```bash
python app.py
```

### 5. Открой браузер

Перейди на [http://localhost:5000](http://localhost:5000)

## Структура проекта

```
1/
├── app.py               # Flask сервер + Gemini AI
├── requirements.txt     # Зависимости Python
├── .env                 # API ключ (создай сам, не коммить!)
├── .env.example         # Пример конфига
├── templates/
│   └── index.html       # Веб-интерфейс
└── README.md
```

## Технологии

- **Backend**: Python + Flask
- **AI**: Google Gemini 2.0 Flash (image generation)
- **Frontend**: HTML + CSS + Vanilla JS
