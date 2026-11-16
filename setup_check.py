#!/usr/bin/env python3
"""
Скрипт для скачивания и установки Python через winget / Microsoft Store,
затем установки зависимостей проекта.
Запустить: python setup_check.py
"""
import sys
import subprocess
import os
import shutil

REQUIRED = (3, 10)

def check_python():
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    if v >= REQUIRED:
        print("  ✅ Версия подходит")
        return True
    print(f"  ❌ Нужен Python {REQUIRED[0]}.{REQUIRED[1]}+")
    return False

def install_deps():
    print("\n  📦 Устанавливаю зависимости...")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"])
    if r.returncode == 0:
        print("  ✅ Зависимости установлены")
        return True
    print("  ❌ Ошибка установки. Попробуйте: pip install -r requirements.txt")
    return False

def check_env():
    if os.path.exists(".env"):
        with open(".env") as f:
            content = f.read()
        if "your_api_key_here" in content:
            print("\n  ⚠️  В .env стоит заглушка вместо реального ключа!")
            print("     Получи ключ на: https://aistudio.google.com/apikey")
            print("     И замени в файле .env строку:")
            print("     GEMINI_API_KEY=your_api_key_here")
            return False
        print("  ✅ .env настроен")
        return True
    else:
        shutil.copy(".env.example", ".env")
        print("\n  ⚠️  Создан файл .env — укажи GEMINI_API_KEY!")
        print("     Получи ключ на: https://aistudio.google.com/apikey")
        return False

if __name__ == "__main__":
    print("\n" + "="*45)
    print("  🐾  FurryArt AI — Проверка установки")
    print("="*45)
    print(f"\n  Проверяю Python...")
    py_ok = check_python()
    deps_ok = install_deps() if py_ok else False
    env_ok = check_env()

    print("\n" + "="*45)
    if py_ok and deps_ok and env_ok:
        print("  🚀 Всё готово! Запуск:")
        print("     python app.py")
        print("  🌐 Браузер: http://localhost:5000")
    else:
        print("  ⚠️  Исправь проблемы выше и попробуй снова")
    print("="*45 + "\n")
