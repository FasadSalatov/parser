#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер заказов с FL.ru
Простая версия без базы данных с переходом по индивидуальным ссылкам
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from typing import List, Dict, Set
import logging

class FLParser:
    def __init__(self, user_agent: str, cookies: dict = None):
        """Инициализация парсера FL.ru"""
        self.user_agent = user_agent
        self.cookies = cookies or {}
        self.sent_orders: Set[str] = set()  # Хранение отправленных заказов в памяти
        self.base_url = "https://www.fl.ru"
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Создание сессии
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        if self.cookies:
            self.session.cookies.update(self.cookies)
    
    def get_new_orders(self, pages: int = 3) -> List[Dict]:
        """
        Получение новых заказов с FL.ru (только первые 5 заказов)
        """
        self.logger.info(f"🔍 Начинаю парсинг FL.ru (первые 5 заказов)...")
        all_orders = []
        
        # Парсим только первую страницу, но ограничиваем 5 заказами
        try:
            page_orders = self._parse_page(1, max_orders=5)
            all_orders.extend(page_orders)
            self.logger.info(f"📄 Первая страница FL.ru: найдено {len(page_orders)} заказов (лимит: 5)")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга FL.ru: {str(e)}")
        
        # Фильтруем только новые заказы
        new_orders = []
        for order in all_orders:
            order_id = order.get('id')
            if order_id and order_id not in self.sent_orders:
                new_orders.append(order)
                self.sent_orders.add(order_id)
        
        self.logger.info(f"✅ FL.ru: обработано {len(all_orders)} заказов, новых: {len(new_orders)}")
        return new_orders
    
    def _parse_page(self, page: int, max_orders: int = None) -> List[Dict]:
        """Парсинг одной страницы заказов"""
        url = f"{self.base_url}/projects/category/programmirovanie/"
        if page > 1:
            url += f"?page={page}"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            orders = []
            
            # Ищем блоки с заказами - h2 элементы с ссылками на проекты
            h2_elements = soup.find_all('h2')
            
            for block in h2_elements:
                try:
                    # Проверяем лимит заказов
                    if max_orders and len(orders) >= max_orders:
                        break
                    
                    # Ищем ссылку в h2
                    link = block.find('a')
                    if not link:
                        continue
                    
                    href = link.get('href', '')
                    if not href or '/projects/' not in href or 'category' in href:
                        continue  # Пропускаем ссылки на категории
                    
                    # Извлекаем данные заказа из индивидуальной страницы
                    order = self._extract_order_from_individual_page(href)
                    if order:
                        orders.append(order)
                        
                except Exception as e:
                    self.logger.debug(f"Ошибка обработки блока: {str(e)}")
                    continue
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки страницы {page}: {str(e)}")
            return []
    
    def _extract_order_from_individual_page(self, href: str) -> Dict:
        """Извлечение данных заказа с индивидуальной страницы"""
        try:
            # Формируем полную ссылку
            if href.startswith('/'):
                full_url = f"{self.base_url}{href}"
            else:
                full_url = href
            
            # ID заказа из URL
            order_id_match = re.search(r'/projects/(\d+)/', href)
            if not order_id_match:
                # Используем хэш от URL как ID
                order_id = f"fl_{abs(hash(href)) % 1000000}"
            else:
                order_id = f"fl_{order_id_match.group(1)}"
            
            # Загружаем индивидуальную страницу заказа
            response = self.session.get(full_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлекаем данные с индивидуальной страницы
            order_data = self._parse_individual_page(soup, full_url, order_id)
            
            return order_data
            
        except Exception as e:
            self.logger.debug(f"Ошибка загрузки индивидуальной страницы {href}: {str(e)}")
            return None
    
    def _parse_individual_page(self, soup: BeautifulSoup, url: str, order_id: str) -> Dict:
        """Парсинг данных с индивидуальной страницы заказа"""
        try:
            # 1. Заголовок - ищем h1 или заголовок в title
            title = "Заказ без названия"
            
            # Сначала ищем h1
            h1_element = soup.find('h1')
            if h1_element:
                title = self._clean_text(h1_element.get_text())
            
            # Если h1 не найден, ищем в title страницы
            if not title or title == "Заказ без названия":
                title_element = soup.find('title')
                if title_element:
                    title_text = title_element.get_text()
                    # Убираем "FL.ru" и другие лишние части
                    title = title_text.split(' | ')[0].split(' - ')[0].strip()
                    title = self._clean_text(title)
            
            # 2. Бюджет - ищем по ключевым словам
            price = "По договорённости"
            page_text = soup.get_text()
            
            budget_patterns = [
                r'Бюджет:\s*([^\n\r]+)',
                r'бюджет:\s*([^\n\r]+)',
                r'по договор[её]нности',
                r'(\d+[\s\d,]*)\s*руб',
                r'(\d+[\s\d,]*)\s*рублей'
            ]
            
            for pattern in budget_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    if 'договор' in pattern:
                        price = "По договорённости"
                    else:
                        price = match.group(1).strip()
                    break
            
            # 3. Описание заказа - берём заголовок как описание или ищем большой блок текста
            description = title
            
            # Ищем div с текстом, который может быть описанием
            desc_candidates = soup.find_all(['div', 'p'], string=lambda text: text and len(text.strip()) > 30)
            for candidate in desc_candidates:
                text = candidate.get_text().strip()
                if len(text) > 50 and text != title:
                    # Проверяем что это не футер или системный текст
                    if not any(word in text.lower() for word in ['сведения об ооо', 'fl.ru', 'copyright', '©']):
                        description = text[:300]
                        break
            
            # 4. Автор - ищем информацию о заказчике
            author = "Не указан"
            
            # Ищем заказчика
            customer_patterns = [
                r'Заказчик\s*([^\n\r]+)',
                r'заказчик\s*([^\n\r]+)',
                r'Автор:\s*([^\n\r]+)',
                r'автор:\s*([^\n\r]+)'
            ]
            
            for pattern in customer_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    author = match.group(1).strip()[:50]
                    break
            
            # 5. Дата публикации - ищем по ключевым словам
            published = "Недавно"
            
            date_patterns = [
                r'Опубликован:\s*([^\n\r]+)',
                r'опубликован:\s*([^\n\r]+)',
                r'Размещен:\s*([^\n\r]+)',
                r'размещен:\s*([^\n\r]+)',
                r'(\d{1,2}[./]\d{1,2}[./]\d{4})',
                r'(\d+)\s*минут[уы]?\s*назад',
                r'(\d+)\s*час[ова]?\s*назад',
                r'(\d+)\s*дн[яей]+\s*назад'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    published = match.group(1).strip() if 'опубликован' in pattern.lower() else match.group(0)
                    break
            
            order = {
                'id': order_id,
                'title': title,
                'url': url,
                'source': 'FL.ru',
                'price': price,
                'category': 'Программирование',
                'author': author,
                'published': published,
                'description': description,
                'parsed_at': datetime.now().isoformat()
            }
            
            return order
            
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга индивидуальной страницы: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Очистка текста от лишних символов"""
        if not text:
            return ""
        
        # Убираем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Убираем специальные символы
        text = text.replace('\n', ' ').replace('\t', ' ')
        
        return text[:200]  # Ограничиваем длину 