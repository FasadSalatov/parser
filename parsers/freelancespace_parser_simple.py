import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Импортируем настройки производительности
try:
    from performance_config import get_performance_settings
    PERFORMANCE_MODE = get_performance_settings()
except ImportError:
    # Настройки по умолчанию если файл не найден
    PERFORMANCE_MODE = {
        'max_pages': 3,
        'parallel_sending': True,
        'page_delay': 0.0,
        'description': 'Быстрый режим по умолчанию'
    }

class FreelanceSpaceParserSimple:
    def __init__(self, user_agent: str, cookies: dict = None):
        """
        Упрощённый парсер FreelanceSpace.ru без базы данных
        
        Args:
            user_agent: User-Agent для запросов
            cookies: Куки для авторизации
        """
        self.base_url = "https://freelancespace.ru"
        self.api_url = "https://freelancespace.ru/ajax/filter_orders.php"
        self.session = requests.Session()
        
        # Настройка заголовков
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://freelancespace.ru',
            'Referer': 'https://freelancespace.ru/dashboard',
            'Sec-Ch-Ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        if cookies:
            self.session.cookies.update(cookies)
            
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Список уже отправленных заказов (в памяти)
        self.sent_orders = set()
    
    def parse_orders(self, max_pages: int = 5, search: str = "") -> List[Dict]:
        """
        Парсинг заказов с FreelanceSpace.ru с нескольких страниц
        
        Args:
            max_pages: Максимальное количество страниц для парсинга
            search: Поисковый запрос
            
        Returns:
            Список заказов в обратном порядке (самый новый последний)
        """
        all_orders = []
        start_time = time.time()
        
        self.logger.info(f"🚀 БЫСТРЫЙ парсинг {max_pages} страниц (без задержек)...")
        
        for page in range(1, max_pages + 1):
            try:
                page_start = time.time()
                
                # Данные для POST запроса
                data = {
                    'search': search,
                    'page': page
                }
                
                self.logger.info(f"📤 Страница {page}/{max_pages}: POST запрос на {self.api_url}")
                
                response = self.session.post(self.api_url, data=data, timeout=30)
                
                request_time = time.time() - page_start
                
                parse_start = time.time()
                self.logger.info(f"📥 Страница {page}: статус {response.status_code}, размер {len(response.text)} символов (запрос {request_time:.2f}с)")
                
                if response.status_code == 200:
                    orders = self._parse_html_response(response.text, page)
                    parse_time = time.time() - parse_start
                    
                    if not orders:
                        self.logger.info(f"🚫 Страница {page}: заказы не найдены, прекращаем парсинг")
                        break
                        
                    all_orders.extend(orders)
                    page_total = time.time() - page_start
                    self.logger.info(f"⚡ Страница {page}: добавлено {len(orders)} заказов за {page_total:.2f}с (запрос: {request_time:.2f}с, парсинг: {parse_time:.2f}с)")
                    
                    # НАСТРАИВАЕМАЯ ЗАДЕРЖКА: берём из настроек производительности
                    page_delay = PERFORMANCE_MODE.get('page_delay', 0.0)
                    if page_delay > 0 and page < max_pages:
                        time.sleep(page_delay)
                else:
                    self.logger.error(f"❌ Страница {page}: HTTP ошибка {response.status_code}")
                    break
                    
            except requests.exceptions.Timeout:
                self.logger.error(f"⏰ Страница {page}: таймаут запроса")
                break
            except requests.exceptions.ConnectionError as e:
                self.logger.error(f"🌐 Страница {page}: ошибка соединения: {str(e)}")
                break
            except Exception as e:
                self.logger.error(f"❌ Страница {page}: неожиданная ошибка: {str(e)}")
                continue
        
        # СОРТИРУЕМ ПО ВРЕМЕНИ ПУБЛИКАЦИИ (самые свежие в конце)
        all_orders_sorted = self._sort_orders_by_time(all_orders)
        
        total_time = time.time() - start_time
        self.logger.info(f"🏁 ИТОГО: {len(all_orders_sorted)} заказов за {total_time:.2f} секунд (скорость: {len(all_orders_sorted)/total_time:.1f} заказов/сек)")
        return all_orders_sorted
    
    def _parse_html_response(self, html: str, page_num: int = 1) -> List[Dict]:
        """
        Парсинг HTML ответа для извлечения информации о заказах
        
        Args:
            html: HTML код ответа
            
        Returns:
            Список заказов
        """
        from bs4 import BeautifulSoup
        
        orders = []
        soup = BeautifulSoup(html, 'html.parser')
        
        self.logger.info(f"🔍 Страница {page_num}: начинаем парсинг HTML (размер: {len(html)} символов)")
        
        # Метод 1: Ищем заказы по кнопке "Откликнуться"
        buttons = soup.find_all(text=lambda text: text and 'Откликнуться' in text)
        self.logger.info(f"🔍 Страница {page_num}: найдено {len(buttons)} элементов с текстом 'Откликнуться'")
        
        order_blocks = []
        for button in buttons:
            parent = button.find_parent()
            depth = 0
            while parent and depth < 15:  # Увеличиваем глубину поиска
                if self._is_order_block(parent):
                    order_blocks.append(parent)
                    break
                parent = parent.find_parent()
                depth += 1
        
        # Метод 2: Ищем по CSS селекторам (структура блоков)
        css_selectors = [
            'div.border.border-gray-300',  # Основной селектор блоков
            'div[class*="border"]',        # Любые блоки с border
            'div[class*="shadow"]',        # Блоки с тенью
            'div[class*="rounded"]',       # Округлённые блоки
        ]
        
        for selector in css_selectors:
            blocks = soup.select(selector)
            for block in blocks:
                if self._is_order_block(block) and block not in order_blocks:
                    order_blocks.append(block)
        
        # Метод 3: Поиск по ссылкам на заказы
        order_links = soup.find_all('a', href=lambda x: x and 'order?id=' in x)
        for link in order_links:
            parent = link.find_parent()
            depth = 0
            while parent and depth < 10:
                if self._is_order_block(parent) and parent not in order_blocks:
                    order_blocks.append(parent)
                    break
                parent = parent.find_parent()
                depth += 1
        
        self.logger.info(f"📊 Страница {page_num}: всего найдено {len(order_blocks)} блоков для анализа")
        
        # Анализируем найденные блоки
        for i, block in enumerate(order_blocks):
            try:
                order = self._extract_order_data(block)
                if order:
                    orders.append(order)
                    self.logger.info(f"✅ Страница {page_num}, блок {i+1}: {order.get('title', 'Без названия')}")
            except Exception as e:
                self.logger.error(f"❌ Страница {page_num}, блок {i+1}: ошибка извлечения: {str(e)}")
                continue
        
        self.logger.info(f"🎉 Страница {page_num}: извлечено {len(orders)} заказов")
        return orders
    
    def _is_order_block(self, element) -> bool:
        """Проверка, является ли элемент блоком заказа"""
        if not element or not hasattr(element, 'get_text'):
            return False
        
        text = element.get_text()
        
        # Обязательные элементы для заказа
        has_action_button = any(word in text for word in ['Откликнуться', 'Подать заявку', 'Отправить предложение'])
        
        # Ценовые индикаторы
        has_price = any(word in text for word in ['₽', 'руб', 'По договоренности', 'от ', 'до ', 'руб.'])
        
        # Временные индикаторы
        has_time = any(word in text for word in ['назад', 'час', 'день', 'минут', 'сегодня', 'вчера'])
        
        # Дополнительные индикаторы заказа
        has_order_indicators = any(word in text for word in [
            'категори', 'заказ', 'проект', 'задач', 'работ', 'услуг',
            'исполнител', 'заказчик', 'автор', 'опубликован', 'создан'
        ])
        
        # Проверяем размер блока (заказы обычно содержательные)
        is_substantial = len(text.strip()) > 50
        
        # Ищем ссылки на заказы
        has_order_link = False
        if hasattr(element, 'find_all'):
            links = element.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if 'order' in href or 'task' in href or 'project' in href:
                    has_order_link = True
                    break
        
        # Блок считается заказом если:
        # 1. Есть кнопка действия ИЛИ ссылка на заказ
        # 2. Есть ценовая информация ИЛИ временная ИЛИ индикаторы заказа  
        # 3. Блок достаточно содержательный
        
        is_order = (has_action_button or has_order_link) and \
                   (has_price or has_time or has_order_indicators) and \
                   is_substantial
        
        return is_order
    
    def _extract_order_data(self, block) -> Optional[Dict]:
        """
        Извлечение данных заказа из HTML блока по точной структуре FreelanceSpace
        
        Args:
            block: BeautifulSoup элемент с заказом
            
        Returns:
            Словарь с данными заказа или None
        """
        try:
            # 1. Извлекаем заголовок и URL из h2 > a
            title_element = block.find('h2', class_=['text-xl', 'font-semibold', 'text-gray-800', 'mb-2'])
            if not title_element:
                return None
            
            title_link = title_element.find('a')
            if not title_link:
                return None
            
            title = title_link.get_text(strip=True)
            url = title_link.get('href', '')
            
            if not title:
                return None
            
            # Формируем полный URL
            if url and not url.startswith('http'):
                url = f"https://freelancespace.ru/{url.lstrip('/')}"
            
            # Извлекаем ID заказа из URL
            order_id = None
            if 'order?id=' in url:
                try:
                    order_id = url.split('order?id=')[1].split('&')[0]
                except:
                    pass
            
            if not order_id:
                order_id = str(abs(hash(title + url)))
            
            # 2. Извлекаем автора из span с классом font-semibold в верхней части
            author = "Не указан"
            # Ищем в верхней части блока, где информация об авторе
            author_container = block.find('div', class_=['flex', 'items-start', 'md:items-center', 'gap-4'])
            if author_container:
                # Ищем span с именем автора - берем только видимый текст для desktop версии
                author_spans = author_container.find_all('span', class_='hidden')
                for span in author_spans:
                    if 'sm:inline' in span.get('class', []):
                        author_text = span.get_text(strip=True)
                        # Проверяем, что это имя, а не заголовок
                        if len(author_text) < 50 and author_text != title and '...' not in author_text:
                            author = author_text
                            break
                
                # Если не нашли в hidden span, ищем в обычных
                if author == "Не указан":
                    author_spans = author_container.find_all('span', class_=['text-gray-800', 'font-semibold'])
                    for span in author_spans:
                        if 'font-semibold' in span.get('class', []):
                            author_text = span.get_text(strip=True)
                            # Проверяем, что это имя, а не заголовок, и удаляем дубли
                            if (len(author_text) < 50 and author_text != title and 
                                '...' not in author_text and not author_text.endswith(author_text[:len(author_text)//2])):
                                # Проверяем на дублирование имени (АрсенийАрсений -> Арсений)
                                if len(author_text) > 2:
                                    half_len = len(author_text) // 2
                                    if author_text[:half_len] == author_text[half_len:]:
                                        author = author_text[:half_len]
                                    else:
                                        author = author_text
                                break
            
            # 3. Извлекаем цену из правого верхнего блока
            price = "Не указана"
            price_container = block.find('div', class_=['mt-2', 'md:mt-0', 'md:text-right'])
            if price_container:
                price_element = price_container.find('p', class_=['font-semibold', 'text-lg', 'text-gray-800'])
                if price_element:
                    price = price_element.get_text(strip=True)
            
            # 4. Извлекаем категорию из блока под заголовком  
            category = "Не указана"
            # Ищем все блоки с категориями
            category_containers = block.find_all('div', class_=['flex', 'items-center', 'text-sm', 'text-gray-500'])
            for container in category_containers:
                if 'mb-4' in container.get('class', []) and 'gap-4' in container.get('class', []):
                    # Ищем первый p элемент - это категория
                    first_p = container.find('p')
                    if first_p:
                        cat_text = first_p.get_text(strip=True)
                        # Список валидных категорий
                        valid_categories = [
                            'Разработка', 'Дизайн', 'Копирайтинг', 'SEO продвижение', 
                            'Маркетинг', 'Другое', 'Администрирование', 'DevOps', 
                            'AI - искусственный интеллект', 'Программирование',
                            'Аудио/виде/фото', 'Реклама и маркетинг', 'Копирайтинг и тексты'
                        ]
                        # Проверяем, что это действительно категория
                        if (cat_text in valid_categories and 
                            '₽' not in cat_text and 'руб' not in cat_text and 'договор' not in cat_text.lower()):
                            category = cat_text
                            break
            
            # Если не нашли категорию, ищем в тексте блока
            if category == "Не указана":
                block_text = block.get_text()
                if 'Разработка' in block_text:
                    category = 'Разработка'
                elif 'Дизайн' in block_text:
                    category = 'Дизайн'
                elif 'AI - искусственный интеллект' in block_text:
                    category = 'AI - искусственный интеллект'
                elif 'SEO продвижение' in block_text:
                    category = 'SEO продвижение'
                elif 'Программирование' in block_text:
                    category = 'Программирование'
            
            # 5. Извлекаем время публикации из блока с иконкой schedule
            published = "Недавно"
            # Ищем блок с иконками visibility и schedule
            stats_containers = block.find_all('div', class_=['flex', 'items-center', 'text-sm', 'text-gray-500'])
            for stats_container in stats_containers:
                if 'gap-4' in stats_container.get('class', []) and 'mb-4' in stats_container.get('class', []):
                    # Ищем иконку schedule (может быть как текст, так и material icon)
                    schedule_icons = stats_container.find_all('span', class_='material-symbols-outlined')
                    for icon in schedule_icons:
                        if icon.get_text(strip=True) == 'schedule':
                            # Следующий элемент после иконки - время
                            next_p = icon.find_next_sibling('p')
                            if next_p:
                                time_text = next_p.get_text(strip=True)
                                # Проверяем, что это действительно время
                                if any(word in time_text for word in ['назад', 'час', 'день', 'дня', 'дней', 'минут', 'минуту']):
                                    published = time_text
                                    break
                    
                    # Если нашли время, выходим из внешнего цикла
                    if published != "Недавно":
                        break
            
            # ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ поиска времени если основной не сработал
            if published == "Недавно":
                # Метод 2: Ищем все p элементы с временными индикаторами
                all_p = block.find_all('p')
                for p in all_p:
                    p_text = p.get_text(strip=True)
                    if any(word in p_text for word in ['назад', 'час', 'день', 'дня', 'дней', 'минут', 'минуту', 'секунд']) and len(p_text) < 50:
                        # Проверяем, что это не другие данные
                        if not any(skip in p_text for skip in ['₽', 'руб', 'категори', title, 'просмотр', 'коммент']):
                            published = p_text
                            break
                
                # Метод 3: Ищем среди всех элементов с материальными иконками
                if published == "Недавно":
                    all_material_icons = block.find_all('span', class_='material-symbols-outlined')
                    for icon in all_material_icons:
                        if 'schedule' in icon.get_text():
                            # Ищем следующий элемент с временем
                            parent = icon.parent
                            if parent:
                                next_elements = parent.find_all('p')
                                for elem in next_elements:
                                    elem_text = elem.get_text(strip=True)
                                    if any(word in elem_text for word in ['назад', 'час', 'день', 'дня', 'дней', 'минут', 'минуту']):
                                        published = elem_text
                                        break
                            if published != "Недавно":
                                break
                
                # Если всё ещё не нашли, ищем в span с "был(а)"
                if published == "Недавно":
                    status_spans = block.find_all('span', class_='text-gray-500')
                    for span in status_spans:
                        span_text = span.get_text(strip=True)
                        if 'был(а)' in span_text:
                            # Извлекаем временную часть после "был(а)"
                            parts = span_text.split('был(а)')
                            if len(parts) > 1:
                                time_part = parts[1].strip()
                                if time_part and ('час' in time_part or 'день' in time_part or 'недавно' in time_part):
                                    published = time_part
                                    break
            
            # 6. Извлекаем описание из p с классом text-gray-700
            description = ""
            desc_element = block.find('p', class_=['text-sm', 'text-gray-700', 'mb-4', 'break-words'])
            if desc_element:
                description = desc_element.get_text(strip=True)
            
            # Укорачиваем описание если слишком длинное
            if len(description) > 200:
                description = description[:200] + '...'
            
            return {
                'id': order_id,
                'title': title,
                'description': description,
                'price': price,
                'category': category,
                'author': author,
                'published': published,
                'url': url,
                'source': 'freelancespace.ru'
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении данных заказа: {str(e)}")
            return None
    
    def get_new_orders(self, max_pages: int = None) -> List[Dict]:
        """
        Получение только новых заказов (которые ещё не отправлялись)
        
        Args:
            max_pages: Количество страниц для парсинга (если None - берётся из настроек производительности)
        
        Returns:
            Список новых заказов
        """
        # Используем настройки производительности если не указано явно
        if max_pages is None:
            max_pages = PERFORMANCE_MODE.get('max_pages', 3)
            self.logger.info(f"🚀 Режим производительности: {PERFORMANCE_MODE.get('description', 'Неизвестный')}")
        
        # ОПТИМИЗАЦИЯ: парсим количество страниц согласно настройкам производительности
        all_orders = self.parse_orders(max_pages=max_pages)
        new_orders = []
        
        for order in all_orders:
            order_id = order.get('id')
            if order_id and order_id not in self.sent_orders:
                new_orders.append(order)
                self.sent_orders.add(order_id)
        
        self.logger.info(f"📋 Новых заказов для уведомлений: {len(new_orders)}")
        return new_orders
    
    def _sort_orders_by_time(self, orders: List[Dict]) -> List[Dict]:
        """
        Сортировка заказов по времени публикации (самые старые сначала, самые новые в конце)
        
        Args:
            orders: Список заказов
            
        Returns:
            Отсортированный список заказов
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
            
            # Логируем результат сортировки
            if sorted_orders:
                first_time = sorted_orders[0].get('published', 'Неизвестно')
                last_time = sorted_orders[-1].get('published', 'Неизвестно')
                self.logger.info(f"🕐 Сортировка: от '{first_time}' до '{last_time}' (самый новый в конце)")
            
            return sorted_orders
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сортировки по времени: {str(e)}")
            # Если сортировка не удалась, возвращаем как есть
            return orders 