import gigachat
from gigachat.models import Chat, Messages, MessagesRole
import json
import re
from config import GIGACHAT_API_KEY, EVENT_CRITERIA

class GigaChatService:
    def __init__(self):
        self.api_key = GIGACHAT_API_KEY
        
    def analyze_event(self, text: str) -> dict:
        try:
            client = gigachat.GigaChat(credentials=self.api_key, verify_ssl_certs=False)
            
            prompt = f"""Ты AI-аналитик Центра исследований и разработки Сбера в Санкт-Петербурге.
Проанализируй описание мероприятия по критериям релевантности для IT-специалистов Сбера.

КРИТЕРИИ ЦЕНТРА СБЕРА:
- Целевая аудитория: {', '.join(EVENT_CRITERIA['target_audience'])}
- Приоритетные темы: {', '.join(EVENT_CRITERIA['themes'])}
- География: Санкт-Петербург и ЛО
- Масштаб: от 50+ участников
- Уровень: экспертные сессии, конференции, стратегические встречи

ИНСТРУКЦИЯ:
1. Извлеки: название, дату, место, целевую аудиторию
2. Оцени релевантность (0-100) для IT-специалистов Сбера
3. Определи IT-тематику (true/false)
4. Проанализируй уровень мероприятия
5. Предложи рекомендацию

ВЕРНИ ТОЛЬКО JSON БЕЗ ФОРМАТИРОВАНИЯ:
{{
    "title": "Короткое ясное название",
    "date": "Дата или 'Не указана'",
    "location": "Место проведения",
    "score": 85,
    "is_it_related": true,
    "summary": "Краткая суть (1-2 предложения)",
    "target_audience": "Конкретная аудитория",
    "level": "экспертный/отраслевой/региональный/международный",
    "expected_scale": "количество участников",
    "recommendation": "рекомендовать/рассмотреть/пропустить",
    "key_themes": ["AI", "Data Science", "Разработка"]
}}

Текст для анализа: {text[:1500]}"""

            messages = [Messages(role=MessagesRole.USER, content=prompt)]
            response = client.chat(Chat(messages=messages, temperature=0.3))
            content = response.choices[0].message.content
            
            content = re.sub(r"```json|```", "", content).strip()
            
            result = json.loads(content)
            
            if any(theme.lower() in text.lower() for theme in ['AI', 'искусственный интеллект', 'нейросети']):
                result['score'] = min(result['score'] + 10, 100)
                
            if any(org in text for org in EVENT_CRITERIA['premium_organizers']):
                result['score'] = min(result['score'] + 15, 100)
                
            return result
            
        except Exception as e:
            print(f"GigaChat analysis error: {e}")
            return {
                "title": "Не удалось распознать",
                "date": "Не указана",
                "location": "СПб",
                "score": 0,
                "is_it_related": False,
                "summary": "Ошибка анализа",
                "target_audience": "Не определена",
                "level": "неизвестно",
                "expected_scale": "неизвестно",
                "recommendation": "пропустить",
                "key_themes": []
            }

    def analyze_file_content(self, text: str) -> list:
        try:
            client = gigachat.GigaChat(credentials=self.api_key, verify_ssl_certs=False)
            
            prompt = f"""Ты AI-аналитик Центра исследований и разработки Сбера. 
Из текста документа извлеки все упоминания о мероприятиях, событиях, конференциях, встречах.

Для каждого мероприятия верни JSON массив с объектами:
[
    {{
        "title": "Название мероприятия",
        "date": "Дата проведения",
        "location": "Место проведения", 
        "description": "Полное описание",
        "organizer": "Организатор",
        "participants": "Количество участников",
        "themes": ["тема1", "тема2"]
    }}
]

Текст документа: {text[:3000]}"""

            messages = [Messages(role=MessagesRole.USER, content=prompt)]
            response = client.chat(Chat(messages=messages, temperature=0.3))
            content = response.choices[0].message.content
            
            content = re.sub(r"```json|```", "", content).strip()
            
            events = json.loads(content)
            return events if isinstance(events, list) else []
            
        except Exception as e:
            print(f"GigaChat file analysis error: {e}")
            return []