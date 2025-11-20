import requests
import json
import re
from datetime import datetime

class ParserService:
    def __init__(self):
        self.sources = [
            {
                "name": "Timepad IT SPb",
                "url": "https://spb.timepad.ru/events/category/it/",
            },
            {
                "name": "Piter IT Meetups", 
                "url": "https://www.meetup.com/cities/ru/spb/technology/",
            }
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_events(self):
        all_events = []
        
        demo_events = [
            {
                "text": "AI Conference St. Petersburg 2025. Искусственный интеллект и машинное обучение. 15-16 марта 2025. Экспофорум. Спикеры из Сбера, Яндекса, ИТМО. Ожидается 500+ участников.",
                "url": "https://ai-conference-spb.ru"
            },
            {
                "text": "Data Science Meetup SPb. Разбор кейсов из e-commerce. 20 марта 2025. Офис Сбера, ул. Кузнечный переулок. Для data scientists и ML engineers.",
                "url": "https://ds-meetup-spb.ru"
            },
            {
                "text": "Стратегическая сессия 'Цифровая трансформация Санкт-Петербурга'. 25 марта 2025. Правительство СПб. Участвуют вице-губернаторы и IT-директора.",
                "url": "https://gov-spb.ru/events/digital"
            },
            {
                "text": "Хакатон SPb Tech Challenge. Разработка AI-решений для бизнеса. 30-31 марта 2025. Коворкинг ЛЕНПОЛИГРАФМАШ. Призы от Сбера и партнеров.",
                "url": "https://spb-tech-hackathon.ru"
            },
            {
                "text": "Митап по DevOps и Kubernetes. 5 апреля 2025. Офис Яндекс. Для системных администраторов и DevOps инженеров.",
                "url": "https://devops-spb.ru"
            },
            {
                "text": "Конференция Frontend SPB 2025. Современный JavaScript и фреймворки. 12 апреля 2025. Коворкинг Таврический. Спикеры из VK и Сбера.",
                "url": "https://frontend-spb.ru"
            },
            {
                "text": "Women in Data Science 2025. 7 марта 2025. Сообщество OpenData Science. Выступление Дарьи Козловой из ИТМО. Тема: Data Science и искусственный интеллект.",
                "url": "https://wids-spb.ru"
            },
            {
                "text": "Круглый стол в Деловом Петербурге. 11 февраля 2025. Участие зам.председателя комитета по образованию Розова Павла Сергеевича. Обсуждение IT-образования.",
                "url": "https://delovoy-spb.ru"
            },
            {
                "text": "Международный Невский форум 'Россия в многополярном мире'. 27 июня 2025. Участие представителей Сбера. Цифровая трансформация и IT-технологии.",
                "url": "https://neva-forum.ru"
            },
            {
                "text": "ИТМО TOP AI выступление. 21 июля 2025. Лекции по искусственному интеллекту от ведущих экспертов. Машинное обучение и нейросети.",
                "url": "https://itmo-ai.ru"
            },
            {
                "text": "Стратегическая сессия Правительства Санкт-Петербурга по человеческому капиталу. 13 февраля 2025. 100 участников. Топ спикеры - вице-губернаторы СПб.",
                "url": "https://gov-spb.ru/strategy"
            },
            {
                "text": "Петербургский международный образовательный форум. 27 марта 2025. 80 участников. Цифровые технологии в образовании.",
                "url": "https://education-forum.spb.ru"
            },
            {
                "text": "Конференция 'Подготовка кадров для ИИ: вызовы, тренды и роль партнерства'. 23 апреля 2025. Сбер совместно с СПбГУ и СПбПУ.",
                "url": "https://ai-education.ru"
            }
        ]
        
        all_events.extend(demo_events)
        
        try:
            for source in self.sources:
                try:
                    response = requests.get(source['url'], headers=self.headers, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {source['name']} доступен")
                except Exception as e:
                    print(f"⚠️ Ошибка при проверке {source['name']}: {e}")
        except Exception as e:
            print(f"Парсинг источников временно отключен: {e}")
        
        return all_events