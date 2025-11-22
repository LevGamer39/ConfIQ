from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(is_admin=False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📅 Мероприятия"), KeyboardButton(text="🔍 Поиск мероприятий")],
        [KeyboardButton(text="📅 Мои мероприятия"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📅 Экспорт моих мероприятий")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_events_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Основные мероприятия"), KeyboardButton(text="🔥 Приоритетные")],
        [KeyboardButton(text="🤝 Партнёрские мероприятия")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ], resize_keyboard=True)

def get_export_calendar_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Экспорт моих мероприятий")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ], resize_keyboard=True)

def get_admin_export_period_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 На неделю"), KeyboardButton(text="📅 На месяц")],
        [KeyboardButton(text="📅 На 3 месяца"), KeyboardButton(text="📅 На год")],
        [KeyboardButton(text="⬅️ Назад в админку")]
    ], resize_keyboard=True)

def get_admin_main_kb(role):
    if role == 'Manager':
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📝 Управление мероприятиями")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🔔 Настройка уведомлений")],
            [KeyboardButton(text="🗓 Экспорт по периоду")],
            [KeyboardButton(text="⬅️ Главное меню")]
        ], resize_keyboard=True)
    
    btns = [
        [KeyboardButton(text="📝 Управление мероприятиями"), KeyboardButton(text="👥 Управление пользователями")],
        [KeyboardButton(text="🔄 Сканировать источники"), KeyboardButton(text="🌐 Источники парсинга")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🗓 Экспорт по периоду")]
    ]
    if role in ('TechSupport', 'Owner', 'GreatAdmin'): 
        btns.append([KeyboardButton(text="👤 Управление админами")])
    
    btns.append([KeyboardButton(text="⬅️ Главное меню")])
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

def get_events_mgmt_kb(role='TechSupport'):
    if role == 'Manager':
        btns = [
            [KeyboardButton(text="✅ Утвердить записи"), KeyboardButton(text="📋 Список всех мероприятий")],
            [KeyboardButton(text="⬅️ Назад в админку")]
        ]
    else:
        btns = [
            [KeyboardButton(text="📜 Модерация"), KeyboardButton(text="🔍 Поиск (Админ)")],
            [KeyboardButton(text="➕ Создать событие"), KeyboardButton(text="🤝 Добавить партнёрское")],
            [KeyboardButton(text="📂 Загрузить из файла"), KeyboardButton(text="📂 Экспорт всех (CSV)")],
            [KeyboardButton(text="📋 Список всех мероприятий"), KeyboardButton(text="⬅️ Назад в админку")]
        ]
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

def get_sources_mgmt_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Добавить источник"), KeyboardButton(text="➖ Удалить источник")],
        [KeyboardButton(text="📋 Список источников"), KeyboardButton(text="⬅️ Назад в админку")]
    ], resize_keyboard=True)

def get_users_mgmt_kb():
    btns = [
        [KeyboardButton(text="✅ Подтверждение (Модерация)"), KeyboardButton(text="📋 Список сотрудников")],
        [KeyboardButton(text="📝 Модерация регистраций"), KeyboardButton(text="⬅️ Назад в админку")]
    ]
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

def get_admin_management_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Список админов"), KeyboardButton(text="➕ Добавить админа")],
        [KeyboardButton(text="➖ Удалить админа"), KeyboardButton(text="📝 Изменить роль админа")],
        [KeyboardButton(text="⬅️ Назад в админку")]
    ], resize_keyboard=True)

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
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
    ])

def get_admin_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👑 ТехПоддержка (Full)"), KeyboardButton(text="👔 Руководитель")],
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_notification_day_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔄 Каждый день"), KeyboardButton(text="📅 Каждый месяц")],
        [KeyboardButton(text="Понедельник"), KeyboardButton(text="Вторник")],
        [KeyboardButton(text="Среда"), KeyboardButton(text="Четверг")],
        [KeyboardButton(text="Пятница"), KeyboardButton(text="Суббота"), KeyboardButton(text="Воскресенье")],
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_notification_time_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="09:00"), KeyboardButton(text="10:00"), KeyboardButton(text="11:00")],
        [KeyboardButton(text="12:00"), KeyboardButton(text="13:00"), KeyboardButton(text="14:00")],
        [KeyboardButton(text="15:00"), KeyboardButton(text="16:00"), KeyboardButton(text="17:00")],
        [KeyboardButton(text="18:00"), KeyboardButton(text="19:00"), KeyboardButton(text="20:00")],
        [KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)

def get_registration_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё верно", callback_data="confirm_registration"),
            InlineKeyboardButton(text="✏️ Исправить", callback_data="edit_registration")
        ]
    ])

def get_events_keyboard(events: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i in range(len(events)):
        row.append(InlineKeyboardButton(text=str(i + 1), callback_data=f"event_details_{events[i]['id']}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row: buttons.append(row)

    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{current_page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{current_page + 1}"))
    
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_selection_keyboard(events: list) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i in range(len(events)):
        row.append(InlineKeyboardButton(text=str(i + 1), callback_data=f"event_details_{events[i]['id']}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_event_detail_keyboard(event_id: int, url: str, registration_status: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if url:
        buttons.append([InlineKeyboardButton(text="🔗 Ссылка на событие", url=url)])
    
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="✏️ Редактировать (Админ)", callback_data=f"admin_event_details_{event_id}")
        ])
    
    if registration_status == 'approved':
        buttons.append([
            InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"remove_from_calendar_{event_id}"),
            InlineKeyboardButton(text="📤 Экспорт", callback_data=f"export_single_event_{event_id}")
        ])
    elif registration_status == 'pending':
        buttons.append([InlineKeyboardButton(text="⏳ Заявка на рассмотрении", callback_data="pending_status_info")])
    else:
        buttons.append([InlineKeyboardButton(text="📝 Записаться", callback_data=f"request_registration_{event_id}")])
        
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_moderation_keyboard(event_id: int, current_index: int, total_count: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_event_{event_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_event_{event_id}"),
        ],
        [InlineKeyboardButton(text="✏️ Ред.", callback_data=f"admin_event_details_{event_id}")],
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"mod_prev_{current_index - 1}" if current_index > 0 else "ignore"),
            InlineKeyboardButton(text=f"{current_index + 1}/{total_count}", callback_data="ignore"),
            InlineKeyboardButton(text="➡️", callback_data=f"mod_next_{current_index + 1}" if current_index < total_count - 1 else "ignore")
        ],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_user_approval_pagination_keyboard(users: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    if not users: return InlineKeyboardMarkup(inline_keyboard=[])
    user = users[0]
    
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_user_{user['id']}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_user_{user['id']}")
        ]
    ]
    
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"user_approval_prev_{current_page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"user_approval_next_{current_page + 1}"))
    
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_events_list_keyboard(events: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_events_prev_{current_page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_events_next_{current_page + 1}"))
    if nav: buttons.append(nav)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_event_confirm_{event_id}"),
            InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")
        ]
    ])

def get_participants_keyboard(event_id: int, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"part_prev_{event_id}_{current_page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"part_next_{event_id}_{current_page + 1}"))
    if nav: buttons.append(nav)
    
    buttons.append([
        InlineKeyboardButton(text="📊 Экспорт в файл", callback_data=f"export_participants_{event_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_event_{event_id}")
    ])
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_employees_list_keyboard(users):
    buttons = []
    for user in users[:10]:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {user['full_name']}",
                callback_data=f"view_user_events_{user['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_role_management_keyboard(users):
    buttons = []
    for user in users[:10]:
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {user['full_name'][:15]}...",
                callback_data=f"change_user_role_{user['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_reg_moderation_keyboard(user_id: int, event_id: int, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"reg_approve_{user_id}_{event_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reg_reject_{user_id}_{event_id}"),
        ]
    ]
    
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"reg_prev_{current_page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"reg_next_{current_page + 1}"))
    
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_bulk_moderation_keyboard(event_id: int, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Утвердить всех", callback_data=f"bulk_approve_{event_id}"),
            InlineKeyboardButton(text="❌ Отклонить всех", callback_data=f"bulk_reject_{event_id}")
        ]
    ]
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"bulk_prev_{current_page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"bulk_next_{current_page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="👥 Просмотреть участников", callback_data=f"view_event_registrations_{event_id}_0")])
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_events_pagination_keyboard(events: list, current_page: int, total_pages: int, event_type: str = 'main') -> InlineKeyboardMarkup:
    buttons = []
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"{event_type}_page_{current_page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"{event_type}_page_{current_page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    if events:
        buttons.append([InlineKeyboardButton(text="🔍 Подробнее", callback_data=f"event_details_{events[0]['id']}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_events_pagination_keyboard(events: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_events_prev_{current_page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_events_next_{current_page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    if events:
        buttons.append([
            InlineKeyboardButton(text="🔍 Детали", callback_data=f"admin_event_details_{events[0]['id']}"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_event_details_{events[0]['id']}")
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_manager_events_pagination_keyboard(events: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"manager_events_prev_{current_page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"manager_events_next_{current_page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    if events:
        buttons.append([
            InlineKeyboardButton(text="🔍 Детали", callback_data=f"manager_event_details_{events[0]['id']}"),
            InlineKeyboardButton(text="👥 Участники", callback_data=f"event_participants_{events[0]['id']}")
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_manager_event_detail_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Участники", callback_data=f"event_participants_{event_id}"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_manager_events")
        ],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
    ])
    
def get_search_filters_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎯 IT-тематика"), KeyboardButton(text="🤖 AI/ML")],
        [KeyboardButton(text="📊 Data Science"), KeyboardButton(text="☁️ Cloud/DevOps")],
        [KeyboardButton(text="🔐 Кибербезопасность"), KeyboardButton(text="💼 Менеджмент")],
        [KeyboardButton(text="🎓 Для начинающих"), KeyboardButton(text="👨‍💻 Для Senior")],
        [KeyboardButton(text="📍 Санкт-Петербург"), KeyboardButton(text="🌐 Онлайн")],
        [KeyboardButton(text="🔥 Высокий приоритет"), KeyboardButton(text="📅 На этой неделе")],
        [KeyboardButton(text="🔍 Все мероприятия"), KeyboardButton(text="❌ Отменить поиск")]
    ], resize_keyboard=True)

def get_admin_search_filters_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎯 IT-тематика"), KeyboardButton(text="🤖 AI/ML")],
        [KeyboardButton(text="📊 Data Science"), KeyboardButton(text="☁️ Cloud/DevOps")],
        [KeyboardButton(text="🔐 Кибербезопасность"), KeyboardButton(text="💼 Менеджмент")],
        [KeyboardButton(text="📍 Санкт-Петербург"), KeyboardButton(text="🌐 Онлайн")],
        [KeyboardButton(text="✅ Одобренные"), KeyboardButton(text="⏳ На модерации")],
        [KeyboardButton(text="🤝 Партнёрские"), KeyboardButton(text="📂 Из файла")],
        [KeyboardButton(text="🔍 Все мероприятия"), KeyboardButton(text="❌ Отменить поиск")]
    ], resize_keyboard=True)

def get_parsing_filters_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎯 IT-тематика"), KeyboardButton(text="🤖 AI/ML")],
        [KeyboardButton(text="📊 Data Science"), KeyboardButton(text="☁️ Cloud/DevOps")],
        [KeyboardButton(text="🔐 Кибербезопасность"), KeyboardButton(text="💼 Менеджмент")],
        [KeyboardButton(text="📍 Санкт-Петербург"), KeyboardButton(text="🌐 Онлайн")],
        [KeyboardButton(text="🎓 Образовательные"), KeyboardButton(text="👨‍💻 Технические")],
        [KeyboardButton(text="🔍 Все темы"), KeyboardButton(text="❌ Отменить")]
    ], resize_keyboard=True)
    
def get_user_edit_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изм. ФИО", callback_data=f"edit_usr_name_{user_id}"),
            InlineKeyboardButton(text="✏️ Изм. Email", callback_data=f"edit_usr_email_{user_id}")
        ],
        [
            InlineKeyboardButton(text="💼 Изм. Должность", callback_data=f"edit_usr_pos_{user_id}"),
            InlineKeyboardButton(text="🗑 Удалить сотрудника", callback_data=f"delete_usr_{user_id}")
        ],
        [InlineKeyboardButton(text="⬅️ К списку", callback_data="back_to_users_list_0")]
    ])

def get_employees_list_keyboard(users, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    for user in users:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {user['full_name']} | {user['position']}",
                callback_data=f"manage_user_{user['id']}"
            )
        ])
    
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_list_prev_{current_page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"users_list_next_{current_page + 1}"))
    
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)