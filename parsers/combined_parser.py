#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Объединённый парсер заказов с FreelanceSpace.ru и FL.ru
Простая версия без базы данных
"""

import asyncio
from typing import List, Dict
import logging
from datetime import datetime

from .freelancespace_parser_simple import FreelanceSpaceParserSimple
from .fl_parser import FLParser

class CombinedParser:
    def __init__(self, user_agent: str, cookies: dict = None):
        """Инициализация объединённого парсера"""
        self.user_agent = user_agent
        self.cookies = cookies or {}
        
        # Инициализация парсеров
        self.freelancespace_parser = FreelanceSpaceParserSimple(user_agent, cookies)
        self.fl_parser = FLParser(user_agent, cookies)
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Общее хранилище отправленных заказов
        self.sent_orders = set()
    
    def get_new_orders(self, pages: int = 3) -> List[Dict]:
        """
        Получение новых заказов со всех источников
        """
        self.logger.info(f"🚀 Начинаю объединённый парсинг ({pages} страниц)...")
        start_time = datetime.now()
        
        all_orders = []
        
        try:
            # Парсинг FreelanceSpace.ru
            self.logger.info("📍 Парсинг FreelanceSpace.ru...")
            freelancespace_orders = self.freelancespace_parser.get_new_orders(pages)
            all_orders.extend(freelancespace_orders)
            self.logger.info(f"✅ FreelanceSpace.ru: {len(freelancespace_orders)} новых заказов")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга FreelanceSpace.ru: {str(e)}")
        
        try:
            # Парсинг FL.ru
            self.logger.info("📍 Парсинг FL.ru...")
            fl_orders = self.fl_parser.get_new_orders(pages)
            all_orders.extend(fl_orders)
            self.logger.info(f"✅ FL.ru: {len(fl_orders)} новых заказов")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга FL.ru: {str(e)}")
        
        # Фильтрация дубликатов и уже отправленных
        unique_orders = self._filter_unique_orders(all_orders)
        
        # Сортировка по времени (самые новые в конце)
        sorted_orders = self._sort_orders_by_time(unique_orders)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.info(f"⚡ Объединённый парсинг завершён за {duration:.1f}с")
        self.logger.info(f"📊 Всего найдено: {len(all_orders)}, уникальных новых: {len(sorted_orders)}")
        
        return sorted_orders
    
    def _filter_unique_orders(self, orders: List[Dict]) -> List[Dict]:
        """Фильтрация уникальных заказов"""
        unique_orders = []
        seen_ids = set()
        
        for order in orders:
            order_id = order.get('id')
            if order_id and order_id not in seen_ids and order_id not in self.sent_orders:
                unique_orders.append(order)
                seen_ids.add(order_id)
                self.sent_orders.add(order_id)
        
        return unique_orders
    
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
    
    @property
    def total_sent_orders(self) -> int:
        """Общее количество отправленных заказов"""
        return len(self.sent_orders)
    
    def get_sources_info(self) -> Dict:
        """Информация об источниках"""
        return {
            'freelancespace': {
                'name': 'FreelanceSpace.ru',
                'sent_orders': len(self.freelancespace_parser.sent_orders)
            },
            'fl': {
                'name': 'FL.ru',
                'sent_orders': len(self.fl_parser.sent_orders)
            },
            'total_sent': self.total_sent_orders
        } 