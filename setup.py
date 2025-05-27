#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт быстрой настройки Freelance Parser Bot
"""

import os
import subprocess
import sys

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Зависимости установлены успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def create_config():
    """Создание файла конфигурации"""
    print("⚙️ Создание config.py...")
    
    if os.path.exists('config.py'):
        choice = input("📄 config.py уже существует. Перезаписать? (y/n): ")
        if choice.lower() != 'y':
            print("⏭️ Пропускаем создание config.py")
            return True
    
    print("\n🤖 Настройка Telegram бота:")
    print("1. Перейдите к @BotFather в Telegram")
    print("2. Отправьте /newbot")
    print("3. Следуйте инструкциям для создания бота")
    print("4. Скопируйте токен бота\n")
    
    bot_token = input("🔑 Введите токен бота: ").strip()
    
    print("\n👤 Получение Chat ID:")
    print("1. Отправьте любое сообщение боту @userinfobot")
    print("2. Скопируйте ваш ID\n")
    
    chat_id = input("🆔 Введите Chat ID: ").strip()
    
    config_content = f'''# Основные настройки для Telegram бота
TELEGRAM_BOT_TOKEN = "{bot_token}"
CHAT_ID = "{chat_id}"

# Интервал парсинга (в секундах)
PARSE_INTERVAL = 300  # 5 минут

# User-Agent для запросов
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"

# Куки (оставляем пустыми - работает без них)
COOKIES = {{}}

# Настройки логирования
DEBUG_MODE = True  # Включить детальные логи
'''
    
    try:
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("✅ Файл config.py создан успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания config.py: {e}")
        return False

def main():
    """Главная функция настройки"""
    print("🚀 Freelance Parser Bot - Быстрая настройка")
    print("=" * 50)
    
    # Установка зависимостей
    if not install_dependencies():
        return
    
    # Создание конфигурации
    if not create_config():
        return
    
    # Тест парсера
    print("\n🧪 Запуск теста парсера...")
    try:
        subprocess.run([sys.executable, "test_parser.py"], check=True)
    except subprocess.CalledProcessError:
        print("⚠️ Тест парсера завершился с ошибками")
    
    print("\n🎉 Настройка завершена!")
    print("\n📋 Следующие шаги:")
    print("1. python start_bot.py - запуск бота")
    print("2. python test_parser.py - тест парсера")
    print("3. Отправьте /start вашему боту в Telegram")

if __name__ == "__main__":
    main() 