from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(is_admin=False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📅 Мероприятия"), KeyboardButton(text="🔍 Поиск мероприятий")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель"), KeyboardButton(text="📊 Статистика")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

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

def get_event_keyboard(event_id: int, url: str, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    buttons = []
    if url and url.startswith("http"):
        buttons.append([InlineKeyboardButton(text="🔗 Ссылка на мероприятие", url=url)])
    buttons.append([InlineKeyboardButton(text="🗓 Добавить в календарь", callback_data=f"cal_{event_id}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_{page}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"next_{page}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_moderation_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Утвердить", callback_data=f"approve_{event_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{event_id}")],
        [InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_mod"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{event_id}")]
    ])

def get_delete_event_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{event_id}"),
         InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete")]
    ])

def get_search_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🤖 Искусственный интеллект"), KeyboardButton(text="📊 Data Science")],
        [KeyboardButton(text="💻 Разработка"), KeyboardButton(text="🎯 IT-менеджмент")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ], resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отменить")]], resize_keyboard=True)