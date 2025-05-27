#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск упрощённого Telegram бота для парсинга заказов фриланса
Версия без базы данных - всё хранится в памяти
"""

import sys
import os

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Главная функция запуска"""
    print("🚀 Запуск Freelance Parser Bot (Простая версия)")
    print("=" * 60)
    print("📋 Особенности:")
    print("• Без базы данных - всё в памяти")
    print("• Самый новый заказ отправляется последним")
    print("• При перезапуске возможно дублирование")
    print("=" * 60)
    
    try:
        # Проверяем наличие config.py
        try:
            from config import TELEGRAM_BOT_TOKEN, CHAT_ID
            print("✅ Конфигурация загружена")
        except ImportError:
            print("❌ Файл config.py не найден!")
            print("📋 Создайте файл config.py со следующими параметрами:")
            print("""
TELEGRAM_BOT_TOKEN = "ваш_токен_бота"
CHAT_ID = "ваш_chat_id"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
COOKIES = {}
PARSE_INTERVAL = 300  # 5 минут
            """)
            return
        
        # Запускаем бот
        from telegram_bot_simple import main as bot_main
        bot_main()
        
    except KeyboardInterrupt:
        print("\n🛑 Остановка бота пользователем")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {str(e)}")
        print("📋 Установите зависимости: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 