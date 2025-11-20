from secret import BOT_TOKEN, GIGACHAT_API_KEY

EVENT_CRITERIA = {
    'target_audience': ['IT-специалисты', 'разработчики', 'data scientist', 'руководители IT', 'исследователи', 'аналитики'],
    'themes': [
        'искусственный интеллект', 'машинное обучение', 'data science', 
        'разработка', 'IT-менеджмент', 'цифровая трансформация', 'нейросети',
        'big data', 'компьютерное зрение', 'обработка естественного языка'
    ],
    'locations': ['Санкт-Петербург', 'СПб', 'Петербург', 'spb', 'Ленинградская область'],
    'min_participants': 50,
    'premium_organizers': [
        'Сбер', 'Яндекс', 'VK', 'ИТМО', 'СПбГУ', 'СПбПУ', 
        'Правительство Санкт-Петербурга', 'АСИ', 'Газпром', 'РАН'
    ],
    'priority_keywords': [
        'AI', 'искусственный интеллект', 'Data Science', 'ML', 
        'цифровая трансформация', 'IT-форум', 'хакатон', 'митап'
    ]
}

PARSER_CONFIG = {
    'timeout': 10,
    'max_events_per_source': 10,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

BOT_CONFIG = {
    'admin_ids': [5159491775],
    'max_events_per_user': 20,
    'cleanup_interval_hours': 24
}