import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

try:
    from config import TELEGRAM_BOT_TOKEN, CHAT_ID, PARSE_INTERVAL, USER_AGENT, COOKIES
except ImportError:
    print("⚠️ Файл config.py не найден! Создайте его на основе config_example.py")
    exit(1)

from parsers.freelancespace_parser_simple import FreelanceSpaceParserSimple

class FreelanceParserBotSimple:
    def __init__(self):
        """Инициализация упрощённого бота"""
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.parser = FreelanceSpaceParserSimple(USER_AGENT, COOKIES)
        self.is_parsing_active = True
        self.last_check_time = None
        
        # Настройка логирования
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        
        # Регистрация обработчиков команд
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд бота"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("parse", self.manual_parse_command))
        self.application.add_handler(CommandHandler("toggle", self.toggle_parsing_command))
        self.application.add_handler(CommandHandler("chatid", self.chatid_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        keyboard = [
            [InlineKeyboardButton("📊 Статус", callback_data='status')],
            [InlineKeyboardButton("🔍 Парсить сейчас", callback_data='parse')],
            [InlineKeyboardButton("⏯️ Вкл/Выкл автопарсинг", callback_data='toggle')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 **Freelance Parser Bot** (Простая версия)

Этот бот автоматически парсит заказы с FreelanceSpace.ru и уведомляет о новых предложениях.

**Особенности:**
• Без базы данных - всё в памяти
• Самый новый заказ отправляется последним
• Автопарсинг каждые 5 минут

**Команды:**
• /start - Главное меню
• /status - Статус парсинга
• /parse - Запустить парсинг вручную
• /toggle - Включить/выключить автопарсинг
• /chatid - Показать ID чата

Используйте кнопки ниже для управления ботом.
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📚 **Помощь по использованию бота (Простая версия)**

**Основные функции:**
• Автоматический парсинг заказов каждые 5 минут
• Уведомления о новых заказах (самый новый последний)
• Хранение отправленных заказов только в памяти

**Команды:**
• `/start` - Главное меню с кнопками управления
• `/status` - Показать текущий статус работы
• `/parse` - Запустить парсинг вручную
• `/toggle` - Включить/выключить автопарсинг
• `/chatid` - Показать ID текущего чата

**Особенности простой версии:**
• Без базы данных - все данные в памяти
• При перезапуске бота может быть дублирование заказов
• Порядок уведомлений: самый новый заказ отправляется последним
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        status_text = f"""
📊 **Статус парсера (Простая версия)**

🔄 Автопарсинг: {'✅ Включён' if self.is_parsing_active else '❌ Выключен'}
⏰ Интервал: {PARSE_INTERVAL} секунд
🕐 Последняя проверка: {self.last_check_time or 'Не выполнялась'}

📈 **Статистика:**
• Отправлено заказов с момента запуска: {len(self.parser.sent_orders)}
• Источники: FreelanceSpace.ru

**Настройки:**
• Хранение: В памяти (без БД)
• Порядок: Самый новый заказ отправляется последним
        """
        
        # Поддержка как обычных команд, так и callback кнопок
        if update.callback_query:
            await update.callback_query.edit_message_text(status_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def manual_parse_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /parse - ручной запуск парсинга"""
        # Отправляем сообщение о начале парсинга
        if update.callback_query:
            await update.callback_query.edit_message_text("🚀 Запускаю быстрый парсинг...")
        else:
            await update.message.reply_text("🚀 Запускаю быстрый парсинг...")
        
        start_time = datetime.now()
        
        try:
            new_orders = await self.parse_and_notify()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if new_orders:
                result_text = f"⚡ Парсинг завершён за {duration:.1f} сек! Найдено {len(new_orders)} новых заказов."
            else:
                result_text = f"⚡ Парсинг завершён за {duration:.1f} сек. Новых заказов не найдено."
                
            # Отправляем результат
            if update.callback_query:
                await update.callback_query.message.reply_text(result_text)
            else:
                await update.message.reply_text(result_text)
                
        except Exception as e:
            error_text = f"❌ Ошибка при парсинге: {str(e)}"
            if update.callback_query:
                await update.callback_query.message.reply_text(error_text)
            else:
                await update.message.reply_text(error_text)
            self.logger.error(f"Ошибка парсинга: {str(e)}")
    
    async def toggle_parsing_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /toggle - включение/выключение автопарсинга"""
        self.is_parsing_active = not self.is_parsing_active
        status = "включён" if self.is_parsing_active else "выключен"
        emoji = "✅" if self.is_parsing_active else "❌"
        
        result_text = f"{emoji} Автопарсинг {status}"
        
        # Поддержка как обычных команд, так и callback кнопок
        if update.callback_query:
            await update.callback_query.edit_message_text(result_text)
        else:
            await update.message.reply_text(result_text)
        
        if self.is_parsing_active:
            self.schedule_parsing()

    async def chatid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /chatid - получение ID чата"""
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        chat_title = getattr(update.effective_chat, 'title', 'Не указано')
        
        info_text = f"""
🆔 **Информация о чате**

**Chat ID:** `{chat_id}`
**Тип чата:** {chat_type}
**Название:** {chat_title}

**Текущий ID в config.py:** `{CHAT_ID}`

**Совпадение:** {'✅ Да' if str(chat_id) == str(CHAT_ID) else '❌ Нет - обновите config.py'}
        """
        
        await update.message.reply_text(info_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'status':
            await self.status_command(update, context)
        elif query.data == 'parse':
            await self.manual_parse_command(update, context)
        elif query.data == 'toggle':
            await self.toggle_parsing_command(update, context)
    
    async def parse_and_notify(self) -> List[Dict]:
        """Парсинг заказов и отправка уведомлений о новых (УСКОРЕННАЯ ВЕРСИЯ)"""
        try:
            parse_start = datetime.now()
            
            # Получаем только новые заказы (в обратном порядке)
            new_orders = self.parser.get_new_orders()
            
            parse_end = datetime.now()
            parse_duration = (parse_end - parse_start).total_seconds()
            
            if not new_orders:
                self.logger.info(f"ℹ️ Новых заказов не найдено (парсинг за {parse_duration:.1f}с)")
                return []
            
            # ПРИНУДИТЕЛЬНАЯ СОРТИРОВКА для правильного порядка отправки
            sorted_orders = self._sort_orders_by_time(new_orders)
            
            send_start = datetime.now()
            self.logger.info(f"🚀 Отправка {len(sorted_orders)} заказов в правильном порядке (парсинг за {parse_duration:.1f}с)...")
            self.logger.info(f"📤 Порядок: от '{sorted_orders[0].get('published', 'Неизвестно')}' до '{sorted_orders[-1].get('published', 'Неизвестно')}'")
            
            # ПОСЛЕДОВАТЕЛЬНАЯ отправка для сохранения порядка (самый новый в конце)
            for i, order in enumerate(sorted_orders, 1):
                try:
                    await self.send_order_notification(order)
                    self.logger.info(f"📨 {i}/{len(sorted_orders)}: {order.get('title', 'Без названия')[:30]}... ({order.get('published', 'Неизвестно')})")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка отправки заказа {i}: {str(e)}")
                    continue
            
            send_end = datetime.now()
            send_duration = (send_end - send_start).total_seconds()
            total_duration = (send_end - parse_start).total_seconds()
            
            self.last_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"⚡ ИТОГО: {len(sorted_orders)} заказов за {total_duration:.1f}с (парсинг: {parse_duration:.1f}с, отправка: {send_duration:.1f}с, скорость: {len(sorted_orders)/total_duration:.1f} заказов/сек)")
            return sorted_orders
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге и уведомлении: {str(e)}")
            return []
    
    async def send_order_notification(self, order: Dict):
        """Отправка уведомления о новом заказе"""
        try:
            text = f"""
🆕 **Новый заказ на {order.get('source', 'FreelanceSpace.ru')}**

📋 **{order.get('title', 'Без названия')}**

💰 **Цена:** {order.get('price', 'Не указана')}
📂 **Категория:** {order.get('category', 'Не указана')}
👤 **Автор:** {order.get('author', 'Не указан')}
🕐 **Опубликовано:** {order.get('published', 'Недавно')}

📝 **Описание:**
{order.get('description', 'Описание отсутствует')}

🔗 **Источник:** {order.get('source', 'freelancespace.ru')}
            """
            
            # Создаём inline кнопку для перехода к заказу
            keyboard = []
            order_url = order.get('url')
            if order_url:
                keyboard.append([InlineKeyboardButton("🔗 Перейти к заказу", url=order_url)])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await self.application.bot.send_message(
                chat_id=CHAT_ID,
                text=text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомления: {str(e)}")
    
    def _sort_orders_by_time(self, orders: List[Dict]) -> List[Dict]:
        """
        Сортировка заказов по времени публикации (самые старые сначала, самые новые в конце)
        """
        def time_to_minutes(time_str: str) -> int:
            """Преобразование времени в минуты для сортировки"""
            if not time_str or time_str == "Недавно":
                return 0  # Самые новые - 0 минут
            
            time_str = time_str.lower()
            
            # Извлекаем число из строки
            import re
            numbers = re.findall(r'\d+', time_str)
            if not numbers:
                return 0
                
            num = int(numbers[0])
            
            # Преобразуем в минуты
            if 'секунд' in time_str:
                return max(1, num // 60)  # Секунды -> минуты (минимум 1)
            elif 'минут' in time_str:
                return num
            elif 'час' in time_str:
                return num * 60
            elif 'день' in time_str or 'дня' in time_str or 'дней' in time_str:
                return num * 24 * 60
            elif 'недел' in time_str:
                return num * 7 * 24 * 60
            elif 'месяц' in time_str:
                return num * 30 * 24 * 60
            else:
                return 0  # Неизвестный формат = самые новые
        
        try:
            # Сортируем по убыванию времени (самые старые сначала, самые новые в конце)
            sorted_orders = sorted(orders, key=lambda x: time_to_minutes(x.get('published', '')), reverse=True)
            return sorted_orders
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сортировки по времени: {str(e)}")
            # Если сортировка не удалась, возвращаем как есть
            return orders
    
    def schedule_parsing(self):
        """Настройка планировщика для автоматического парсинга"""
        async def periodic_parse():
            """Периодический парсинг"""
            while self.is_parsing_active:
                try:
                    self.logger.info("🔄 Запуск автоматического парсинга...")
                    new_orders = await self.parse_and_notify()
                    if new_orders:
                        self.logger.info(f"✅ Найдено {len(new_orders)} новых заказов")
                    else:
                        self.logger.info("ℹ️ Новых заказов не найдено")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка при автопарсинге: {str(e)}")
                
                # Ждём интервал перед следующим парсингом
                await asyncio.sleep(PARSE_INTERVAL)
        
        # Запускаем периодический парсинг как задачу
        asyncio.create_task(periodic_parse())
    
    async def run(self):
        """Запуск бота"""
        self.logger.info("🚀 Запуск Freelance Parser Bot (Простая версия)...")
        
        # Запуск автопарсинга, если он включён
        if self.is_parsing_active:
            self.schedule_parsing()
        
        # Запуск бота
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        self.logger.info("✅ Бот успешно запущен!")
        
        # Ожидание завершения
        try:
            await self.application.updater.idle()
        except AttributeError:
            import signal
            stop_event = asyncio.Event()
            
            def signal_handler():
                stop_event.set()
            
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, lambda s, f: signal_handler())
            
            await stop_event.wait()

def main():
    """Главная функция запуска"""
    bot = FreelanceParserBotSimple()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Остановка бота...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    main() 