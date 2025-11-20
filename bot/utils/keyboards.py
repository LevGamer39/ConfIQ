from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(is_admin=False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📅 Мероприятия"), KeyboardButton(text="🔍 Поиск мероприятий")],
        [KeyboardButton(text="🔥 Приоритетные"), KeyboardButton(text="🤝 Партнерские")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📅 Мои мероприятия")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_profile")]
    ])

def get_edit_profile_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 ФИО"), KeyboardButton(text="📧 Email")],
        [KeyboardButton(text="📞 Телефон"), KeyboardButton(text="🏢 Отдел")],
        [KeyboardButton(text="💼 Должность"), KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_admin_keyboard(role="Admin") -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🔄 Сканировать источники"), KeyboardButton(text="📩 Добавить от партнера")],
        [KeyboardButton(text="📁 Загрузить файл"), KeyboardButton(text="🗑 Управление мероприятиями")],
        [KeyboardButton(text="⚖️ Модерация"), KeyboardButton(text="📊 Статистика")]
    ]
    if role == "GreatAdmin":
        buttons.append([KeyboardButton(text="👥 Управление админами")])
        
    buttons.append([KeyboardButton(text="⬅️ Главное меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_management_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Добавить админа"), KeyboardButton(text="➖ Удалить админа")],
        [KeyboardButton(text="📋 Список админов"), KeyboardButton(text="⬅️ Назад в админ-панель")]
    ], resize_keyboard=True)

def get_events_management_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🗑 Удалить мероприятие"), KeyboardButton(text="📋 Список мероприятий")],
        [KeyboardButton(text="⬅️ Назад в админ-панель")]
    ], resize_keyboard=True)

def get_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👑 GreatAdmin"), KeyboardButton(text="👤 Admin")],
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_events_keyboard(events: list, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    buttons = []
    
    selection_row = []
    for i, event in enumerate(events, 1):
        selection_row.append(InlineKeyboardButton(text=str(i), callback_data=f"event_detail_{event['id']}"))
    
    chunk_size = 5
    for i in range(0, len(selection_row), chunk_size):
        buttons.append(selection_row[i:i + chunk_size])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"events_page_{page-1}"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"events_page_{page+1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_selection_keyboard(events: list) -> InlineKeyboardMarkup:
    buttons = []
    selection_row = []
    for i, event in enumerate(events, 1):
        selection_row.append(InlineKeyboardButton(text=str(i), callback_data=f"event_detail_{event['id']}"))
    
    chunk_size = 5
    for i in range(0, len(selection_row), chunk_size):
        buttons.append(selection_row[i:i + chunk_size])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_event_detail_keyboard(event_id: int, url: str, is_registered: bool) -> InlineKeyboardMarkup:
    buttons = []
    
    if url and url.startswith("http"):
        buttons.append([InlineKeyboardButton(text="🔗 Ссылка на мероприятие", url=url)])
    
    if is_registered:
        buttons.append([InlineKeyboardButton(text="✅ В календаре", callback_data="already_added")])
    else:
        buttons.append([InlineKeyboardButton(text="📅 Добавить в календарь", callback_data=f"add_to_calendar_{event_id}")])
    
    buttons.append([InlineKeyboardButton(text="📥 Скачать для календаря", callback_data=f"download_ics_{event_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ К списку", callback_data="back_to_list")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_moderation_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Утвердить", callback_data=f"approve_{event_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{event_id}")],
        [InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_mod"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{event_id}")],
        [InlineKeyboardButton(text="🚪 Завершить модерацию", callback_data="stop_moderation")]
    ])

def get_delete_event_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{event_id}"),
         InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete")]
    ])

def get_search_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔤 Текстовый поиск"), KeyboardButton(text="🎯 Поиск по критериям")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ], resize_keyboard=True)

def get_search_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🤖 Искусственный интеллект"), KeyboardButton(text="📊 Data Science")],
        [KeyboardButton(text="💻 Разработка"), KeyboardButton(text="🎯 IT-менеджмент")],
        [KeyboardButton(text="🏢 Крупные мероприятия"), KeyboardButton(text="🤝 Партнерские")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ], resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отменить")]], resize_keyboard=True)

def get_criteria_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Тематика", callback_data="criteria_theme")],
        [InlineKeyboardButton(text="📍 Местоположение", callback_data="criteria_location")],
        [InlineKeyboardButton(text="📅 Период", callback_data="criteria_date")],
        [InlineKeyboardButton(text="👥 Аудитория", callback_data="criteria_audience")],
        [
            InlineKeyboardButton(text="🔍 Найти", callback_data="criteria_search"),
            InlineKeyboardButton(text="🗑 Очистить", callback_data="criteria_clear")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="criteria_back")]
    ])

def get_themes_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Искусственный интеллект", callback_data="select_theme_ai")],
        [InlineKeyboardButton(text="📊 Data Science", callback_data="select_theme_data_science")],
        [InlineKeyboardButton(text="💻 Разработка", callback_data="select_theme_development")],
        [InlineKeyboardButton(text="🎯 IT-менеджмент", callback_data="select_theme_management")],
        [InlineKeyboardButton(text="🔐 Кибербезопасность", callback_data="select_theme_security")],
        [InlineKeyboardButton(text="☁️ Облачные технологии", callback_data="select_theme_cloud")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="criteria_back")]
    ])

def get_locations_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛️ Санкт-Петербург", callback_data="select_location_spb")],
        [InlineKeyboardButton(text="🏢 Москва", callback_data="select_location_msk")],
        [InlineKeyboardButton(text="🌐 Онлайн", callback_data="select_location_online")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="criteria_back")]
    ])

def get_dates_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 На этой неделе", callback_data="select_date_week")],
        [InlineKeyboardButton(text="📅 В этом месяце", callback_data="select_date_month")],
        [InlineKeyboardButton(text="📅 В этом квартале", callback_data="select_date_quarter")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="criteria_back")]
    ])

def get_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Разработчики", callback_data="select_audience_developers")],
        [InlineKeyboardButton(text="👔 Руководители", callback_data="select_audience_managers")],
        [InlineKeyboardButton(text="📈 Аналитики", callback_data="select_audience_analysts")],
        [InlineKeyboardButton(text="🔬 Исследователи", callback_data="select_audience_researchers")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="criteria_back")]
    ])