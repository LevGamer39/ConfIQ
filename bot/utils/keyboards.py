from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List

def get_main_keyboard(is_admin=False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📅 Мероприятия"), KeyboardButton(text="🔍 Поиск мероприятий")],
        [KeyboardButton(text="🔥 Приоритетные"), KeyboardButton(text="📅 Мои мероприятия")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🗂 Экспорт календаря")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_position_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👨‍💻 Стажер"), KeyboardButton(text="👨‍💻 Junior разработчик")],
        [KeyboardButton(text="👨‍💻 Middle разработчик"), KeyboardButton(text="👨‍💻 Senior разработчик")],
        [KeyboardButton(text="👨‍💻 Team Lead"), KeyboardButton(text="👨‍💼 Менеджер проектов")],
        [KeyboardButton(text="👨‍💼 Руководитель отдела"), KeyboardButton(text="👨‍💼 Директор")],
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="profile_stats")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_profile")]
    ])

def get_admin_keyboard(role="Admin") -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📜 Модерация событий"), KeyboardButton(text="📋 Модерация регистраций")],
        [KeyboardButton(text="👥 Подтверждение пользователей"), KeyboardButton(text="🔄 Сканировать источники")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👤 Управление админами")],
        [KeyboardButton(text="📝 Управление мероприятиями"), KeyboardButton(text="👥 Регистрации на события")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_management_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Список админов"), KeyboardButton(text="➕ Добавить админа")],
        [KeyboardButton(text="➖ Удалить админа"), KeyboardButton(text="📝 Изменить роль админа")],
        [KeyboardButton(text="⬅️ Назад в админку")]
    ], resize_keyboard=True)

def get_admin_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👑 GreatAdmin"), KeyboardButton(text="👤 Admin")],
        [KeyboardButton(text="👥 Moderator")],
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_events_keyboard(events: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    row1 = []
    for i in range(len(events)):
        row1.append(InlineKeyboardButton(text=str(i + 1), callback_data=f"event_details_{events[i]['id']}"))
    buttons.append(row1)

    page_buttons = []
    if current_page > 0:
        page_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{current_page - 1}"))
    
    page_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="current_page"))
    
    if current_page < total_pages - 1:
        page_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{current_page + 1}"))
    
    if page_buttons:
        buttons.append(page_buttons)

    buttons.append([
        InlineKeyboardButton(text="📅 Мои мероприятия", callback_data="show_my_events"),
        InlineKeyboardButton(text="🔍 Поиск", callback_data="start_search")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_selection_keyboard(events: list, current_page: int = 0, total_pages: int = 1, prefix: str = "event") -> InlineKeyboardMarkup:
    buttons = []
    
    row1 = []
    for i in range(len(events)):
        row1.append(InlineKeyboardButton(text=str(i + 1), callback_data=f"{prefix}_details_{events[i]['id']}"))
        if (i + 1) % 5 == 0 and i < len(events) - 1:
            buttons.append(row1)
            row1 = []
    if row1:
        buttons.append(row1)

    if total_pages > 1:
        page_buttons = []
        if current_page > 0:
            page_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{prefix}_page_{current_page - 1}"))
        
        page_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="current_page"))
        
        if current_page < total_pages - 1:
            page_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"{prefix}_page_{current_page + 1}"))
        
        buttons.append(page_buttons)
        
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_message")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_event_detail_keyboard(event_id: int, url: str, registration_status: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="🔗 Подробности и регистрация", url=url)]]
    
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event_{event_id}"),
            InlineKeyboardButton(text="👥 Участники", callback_data=f"event_participants_{event_id}")
        ])
    
    if registration_status == 'approved':
        buttons.append([
            InlineKeyboardButton(text="❌ Отменить регистрацию", callback_data=f"remove_from_calendar_{event_id}")
        ])
    elif registration_status == 'pending':
        buttons.append([
            InlineKeyboardButton(text="🕒 Ожидает подтверждения", callback_data="pending_status_info")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="📝 Запросить регистрацию", callback_data=f"request_registration_{event_id}")
        ])
        
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_message")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
    
def get_registration_moderation_keyboard(user_id: int, event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"reg_approve_{user_id}_{event_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reg_reject_{user_id}_{event_id}"),
        ],
        [
            InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_reg_mod")
        ]
    ])

def get_user_approval_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_user_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_user_{user_id}"),
        ],
        [
            InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_user")
        ]
    ])

def get_moderation_keyboard(event_id: int, current_index: int, total_count: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Утвердить", callback_data=f"approve_event_{event_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_event_{event_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_event_{event_id}"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event_{event_id}")
        ]
    ]
    
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущее", callback_data=f"mod_prev_{current_index - 1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current_index + 1}/{total_count}", callback_data="current_mod"))
    
    if current_index < total_count - 1:
        nav_buttons.append(InlineKeyboardButton(text="Следующее ➡️", callback_data=f"mod_next_{current_index + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_event_mod")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_registration_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё верно", callback_data="confirm_registration"),
            InlineKeyboardButton(text="✏️ Исправить", callback_data="edit_registration")
        ]
    ])

def get_events_management_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Все мероприятия", callback_data="manage_all_events"),
            InlineKeyboardButton(text="➕ Создать мероприятие", callback_data="create_event")
        ],
        [
            InlineKeyboardButton(text="🔍 Поиск мероприятий", callback_data="search_events_admin"),
            InlineKeyboardButton(text="📊 Статистика регистраций", callback_data="registration_stats")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")
        ]
    ])

def get_event_edit_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_event_title_{event_id}"),
            InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_event_desc_{event_id}")
        ],
        [
            InlineKeyboardButton(text="📍 Место", callback_data=f"edit_event_location_{event_id}"),
            InlineKeyboardButton(text="📅 Дата", callback_data=f"edit_event_date_{event_id}")
        ],
        [
            InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"edit_event_url_{event_id}"),
            InlineKeyboardButton(text="👥 Участники", callback_data=f"event_participants_{event_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_event_{event_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_event_confirm_{event_id}")
        ]
    ])

def get_participants_keyboard(event_id: int, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    page_buttons = []
    if current_page > 0:
        page_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"part_prev_{event_id}_{current_page - 1}"))
    
    page_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="current_part_page"))
    
    if current_page < total_pages - 1:
        page_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"part_next_{event_id}_{current_page + 1}"))
    
    if page_buttons:
        buttons.append(page_buttons)
    
    buttons.append([
        InlineKeyboardButton(text="📊 Экспорт списка", callback_data=f"export_participants_{event_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_event_{event_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_events_list_keyboard(events: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    for event in events:
        status_icon = "✅" if event['status'] == 'approved' else "⏳" if event['status'] == 'pending' else "❌"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} {event['title'][:30]}...", 
                callback_data=f"admin_event_details_{event['id']}"
            )
        ])
    
    page_buttons = []
    if current_page > 0:
        page_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_events_prev_{current_page - 1}"))
    
    page_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="current_admin_page"))
    
    if current_page < total_pages - 1:
        page_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"admin_events_next_{current_page + 1}"))
    
    if page_buttons:
        buttons.append(page_buttons)
    
    buttons.append([
        InlineKeyboardButton(text="➕ Создать мероприятие", callback_data="create_event"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_user_approval_pagination_keyboard(users: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    if users:
        user = users[0]
        buttons.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_user_{user['id']}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_user_{user['id']}")
        ])
    
    page_buttons = []
    if current_page > 0:
        page_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"user_approval_prev_{current_page - 1}"))
    
    page_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="current_user_page"))
    
    if current_page < total_pages - 1:
        page_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"user_approval_next_{current_page + 1}"))
    
    if page_buttons:
        buttons.append(page_buttons)
    
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_user")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)