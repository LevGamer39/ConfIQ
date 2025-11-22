from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton
import json
import asyncio
from datetime import datetime, timedelta

from utils.keyboards import *
from utils.states import UserStates
from utils.ics_generator import IcsGenerator
from database import FDataBase

router = Router()

@router.message(CommandStart())
async def start(message: types.Message, db: FDataBase, state: FSMContext):
    user = db.get_user(message.from_user.id)
    admin = db.get_admin(message.from_user.id)
    
    if user:
        if user.get('status') != 'approved' and not admin:
            await message.answer(
                "⏳ <b>Ваш аккаунт ожидает подтверждения администратором.</b>\n"
                "Вам придет уведомление, когда доступ будет открыт.",
                parse_mode="HTML"
            )
            return
        
        db.update_user_activity(message.from_user.id)
        is_admin = bool(admin)
        await message.answer(
            "👋 <b>Добро пожаловать в Eventpedia!</b>\n\n"
            "Здесь вы найдете актуальные IT-мероприятия, сможете записаться на них и добавить в свой календарь.",
            reply_markup=get_main_keyboard(is_admin),
            parse_mode="HTML"
        )
        return
    
    await state.set_state(UserStates.waiting_for_full_name)
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Для доступа к мероприятиям необходимо зарегистрироваться.\n"
        "📝 <b>Введите ваше ФИО:</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(UserStates.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена", reply_markup=types.ReplyKeyboardRemove())
        return
    
    if len(message.text) < 2:
        await message.answer("❌ Слишком короткое имя. Пожалуйста, введите ФИО:")
        return
    
    await state.update_data(full_name=message.text)
    await state.set_state(UserStates.waiting_for_email)
    await message.answer("📧 <b>Введите ваш email:</b>", parse_mode="HTML")

@router.message(UserStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена")
        return
    
    if '@' not in message.text:
        await message.answer("❌ Некорректный email. Попробуйте снова:")
        return
    
    await state.update_data(email=message.text)
    await state.set_state(UserStates.waiting_for_phone)
    await message.answer("📞 <b>Введите ваш номер телефона:</b>", parse_mode="HTML")

@router.message(UserStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена")
        return
    
    await state.update_data(phone=message.text)
    await state.set_state(UserStates.waiting_for_position)
    await message.answer(
        "💼 <b>Выберите вашу должность:</b>", 
        parse_mode="HTML",
        reply_markup=get_position_keyboard()
    )

@router.message(UserStates.waiting_for_position)
async def process_position(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена")
        return
    
    await state.update_data(position=message.text)
    data = await state.get_data()
    
    text = (
        "✅ <b>Проверьте данные:</b>\n\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"📧 Email: {data['email']}\n"
        f"📞 Тел: {data['phone']}\n"
        f"💼 Должность: {message.text}\n\n"
        "Всё верно?"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_registration_confirm_keyboard())

@router.callback_query(F.data == "confirm_registration")
async def confirm_registration_handler(callback: types.CallbackQuery, state: FSMContext, db: FDataBase):
    data = await state.get_data()
    
    success = db.add_user(
        callback.from_user.id,
        callback.from_user.username or "unknown",
        data['full_name']
    )
    
    if success:
        db.update_user_profile(
            callback.from_user.id,
            email=data['email'],
            phone=data['phone'],
            position=data['position']
        )
        await state.clear()
        
        admin = db.get_admin(callback.from_user.id)
        if admin:
            db.force_approve_user(callback.from_user.id)
            await callback.message.edit_text("✅ <b>Регистрация завершена!</b>\nВы администратор.", parse_mode="HTML")
            await callback.message.answer("Меню:", reply_markup=get_main_keyboard(True))
        else:
            await callback.message.edit_text(
                "✅ <b>Заявка отправлена!</b>\nОжидайте подтверждения.", 
                parse_mode="HTML"
            )
            admins = db.get_all_admins()
            for adm in admins:
                if adm.get('is_active'):
                    try:
                        await callback.bot.send_message(
                            adm['telegram_id'], 
                            f"👤 <b>НОВАЯ ЗАЯВКА</b>\n{data['full_name']}\n{data['position']}", 
                            parse_mode="HTML"
                        )
                    except: pass
    else:
        await callback.answer("Ошибка регистрации")

@router.callback_query(F.data == "edit_registration")
async def edit_registration_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_full_name)
    await callback.message.edit_text("🔄 Введите ФИО заново:")

@router.message(F.text == "📅 Мероприятия")
async def show_events_menu(message: types.Message):
    await message.answer("📅 <b>Выберите тип мероприятий:</b>", 
                        parse_mode="HTML", 
                        reply_markup=get_events_type_keyboard())

@router.message(F.text == "📋 Основные мероприятия")
async def show_main_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Аккаунт не подтвержден")
        return
    
    await show_events_page(message, db, 0, 'main')

async def show_events_page(message: types.Message, db: FDataBase, page: int, event_type='main'):
    if event_type == 'main':
        events = await asyncio.to_thread(db.get_events_paginated, message.from_user.id, page, 1, None)
        total = await asyncio.to_thread(db.get_total_approved_events, 'main')
        title = "📅 Основные мероприятия"
    elif event_type == 'priority':
        events = await asyncio.to_thread(db.get_high_priority_events_paginated, message.from_user.id, page, 1)
        total = await asyncio.to_thread(db.get_total_priority_events, message.from_user.id)
        title = "🔥 Приоритетные мероприятия"
    elif event_type == 'partner':
        events = await asyncio.to_thread(db.get_partner_events_paginated, message.from_user.id, page, 1)
        total = await asyncio.to_thread(db.get_total_partner_events, message.from_user.id)
        title = "🤝 Партнёрские мероприятия"
    elif event_type == 'my_events':
        events = await asyncio.to_thread(db.get_user_events_paginated, message.from_user.id, page, 1)
        total = await asyncio.to_thread(db.get_total_user_events, message.from_user.id)
        title = "📅 Мои мероприятия"
    
    if not events:
        await message.answer("📭 Мероприятий пока нет.")
        return

    event = events[0]
    
    try:
        analysis = json.loads(event['analysis']) if event.get('analysis') else {}
    except:
        analysis = {}
    
    if event_type == 'my_events':
        status_icon = "✅" if event.get('status') == 'approved' else "⏳"
        text = (
            f"<b>{title}</b> ({page + 1}/{max(1, total)})\n\n"
            f"{status_icon} <b>{event['title']}</b>\n"
            f"📅 {event['date_str']}\n"
            f"📍 {event['location']}\n"
            f"🔗 {event['url'] or 'Нет ссылки'}\n"
            f"📊 Статус: {'Подтверждено' if event.get('status') == 'approved' else 'Ожидает подтверждения'}\n\n"
            f"📝 <b>Описание:</b>\n{event['description'][:300]}..."
        )
    else:
        text = (
            f"<b>{title}</b> ({page + 1}/{max(1, total)})\n\n"
            f"📌 <b>{event['title']}</b>\n"
            f"📅 {event['date_str']}\n"
            f"📍 {event['location']}\n"
            f"🔗 {event['url'] or 'Нет ссылки'}\n"
            f"📊 Score: {event['score']}\n"
            f"💡 AI Summary: {analysis.get('summary', '-')}\n\n"
            f"📝 <b>Описание:</b>\n{event['description'][:300]}..."
        )
    
    kb = get_events_pagination_keyboard(events, page, max(1, total), event_type)
    
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

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

@router.callback_query(F.data.startswith("main_page_"))
async def main_pagination_handler(callback: types.CallbackQuery, db: FDataBase):
    try:
        page = int(callback.data.split("_")[2])
        await callback.message.delete()
        await show_events_page(callback.message, db, page, 'main')
    except Exception as e:
        await callback.answer("❌ Ошибка навигации")

@router.callback_query(F.data.startswith("priority_page_"))
async def priority_pagination_handler(callback: types.CallbackQuery, db: FDataBase):
    try:
        page = int(callback.data.split("_")[2])
        await callback.message.delete()
        await show_events_page(callback.message, db, page, 'priority')
    except Exception as e:
        await callback.answer("❌ Ошибка навигации")

@router.callback_query(F.data.startswith("partner_page_"))
async def partner_pagination_handler(callback: types.CallbackQuery, db: FDataBase):
    try:
        page = int(callback.data.split("_")[2])
        await callback.message.delete()
        await show_events_page(callback.message, db, page, 'partner')
    except Exception as e:
        await callback.answer("❌ Ошибка навигации")

@router.callback_query(F.data.startswith("my_events_page_"))
async def my_events_pagination_handler(callback: types.CallbackQuery, db: FDataBase):
    try:
        page = int(callback.data.split("_")[3])
        await callback.message.delete()
        await show_events_page(callback.message, db, page, 'my_events')
    except Exception as e:
        await callback.answer("❌ Ошибка навигации")

@router.message(F.text == "🔥 Приоритетные")
async def show_priority(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Аккаунт не подтвержден")
        return
    
    await show_events_page(message, db, 0, 'priority')

@router.message(F.text == "🤝 Партнёрские мероприятия")
async def show_partner_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Аккаунт не подтвержден")
        return
    
    await show_events_page(message, db, 0, 'partner')

@router.message(F.text == "🔍 Поиск мероприятий")
async def search_start(message: types.Message, state: FSMContext, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved': return
    
    await state.set_state(UserStates.waiting_for_search_text)
    await message.answer(
        "🔍 <b>Выберите фильтры для поиска:</b>\n"
        "Можно выбрать несколько фильтров по очереди",
        parse_mode="HTML", 
        reply_markup=get_search_filters_keyboard()
    )

@router.message(UserStates.waiting_for_search_text)
async def search_process(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить поиск":
        await state.clear()
        is_admin = bool(db.get_admin(message.from_user.id))
        await message.answer("🔍 Поиск отменен", reply_markup=get_main_keyboard(is_admin))
        return
    
    filter_map = {
        "🎯 IT-тематика": ["IT", "разработка", "программирование", "software"],
        "🤖 AI/ML": ["AI", "искусственный интеллект", "ML", "machine learning", "нейросеть"],
        "📊 Data Science": ["data science", "анализ данных", "big data", "data analysis"],
        "☁️ Cloud/DevOps": ["cloud", "облако", "devops", "aws", "azure", "gcp", "kubernetes"],
        "🔐 Кибербезопасность": ["кибербезопасность", "cybersecurity", "security", "безопасность"],
        "💼 Менеджмент": ["менеджмент", "управление", "project management", "руководство"],
        "🎓 Для начинающих": ["junior", "начальный", "для начинающих", "обучение"],
        "👨‍💻 Для Senior": ["senior", "lead", "архитектор", "экспертный"],
        "📍 Санкт-Петербург": ["санкт-петербург", "спб", "петербург"],
        "🌐 Онлайн": ["онлайн", "online", "webinar"],
        "🔥 Высокий приоритет": ["high"],
        "📅 На этой неделе": ["week"],
        "🔍 Все мероприятия": ["all"]
    }
    
    if message.text not in filter_map:
        await message.answer("❌ Пожалуйста, выберите фильтр из меню.")
        return
    
    selected_filter = filter_map[message.text]
    
    current_data = await state.get_data()
    current_filters = current_data.get('search_filters', [])
    
    if message.text == "🔍 Все мероприятия":
        current_filters = []
        await state.update_data(search_filters=[])
        await message.answer("🔍 <b>Поиск по всем мероприятиям</b>", parse_mode="HTML")
    else:
        if selected_filter[0] in current_filters:
            current_filters = [f for f in current_filters if f != selected_filter[0]]
            await message.answer(f"❌ Фильтр '{message.text}' удален")
        else:
            current_filters.append(selected_filter[0])
            await message.answer(f"✅ Фильтр '{message.text}' добавлен")
        
        await state.update_data(search_filters=current_filters)
    
    if current_filters:
        active_filters = []
        for filter_name, filter_values in filter_map.items():
            if filter_values[0] in current_filters:
                active_filters.append(filter_name)
        
        filters_text = "\n".join([f"• {f}" for f in active_filters])
        await message.answer(
            f"📋 <b>Активные фильтры:</b>\n{filters_text}\n\n"
            f"Выберите еще фильтры или нажмите '🔍 Все мероприятия' для поиска",
            parse_mode="HTML",
            reply_markup=get_search_filters_keyboard()
        )
    else:
        await message.answer(
            "🔍 <b>Поиск по всем мероприятиям</b>\n"
            "Выберите фильтры для уточнения поиска",
            parse_mode="HTML",
            reply_markup=get_search_filters_keyboard()
        )
    
    if current_filters and message.text != "🔍 Все мероприятия":
        await perform_smart_search(message, state, db, current_filters)

async def perform_smart_search(message: types.Message, state: FSMContext, db: FDataBase, filters: list):
    wait_msg = await message.answer("⏳ <b>Ищу мероприятия по выбранным фильтрам...</b>", parse_mode="HTML")
    
    try:
        keywords = []
        date_filter = None
        priority_filter = None
        
        for filter_type in filters:
            if filter_type == "week":
                date_filter = "week"
            elif filter_type == "high":
                priority_filter = "high"
            else:
                keywords.append(filter_type)
        
        events = await asyncio.to_thread(db.search_events_with_filters, 
                                       message.from_user.id, 
                                       keywords, 
                                       date_filter, 
                                       priority_filter)
        
        await wait_msg.delete()
        
        if not events:
            await message.answer(
                "🔍 <b>По вашему запросу ничего не найдено</b>\n"
                "Попробуйте изменить фильтры поиска",
                parse_mode="HTML",
                reply_markup=get_search_filters_keyboard()
            )
            return
        
        if len(events) == 1:
            event = events[0]
            await show_event_details(message, event, db)
        else:
            await show_search_results(message, events, db)
            
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ Ошибка при поиске: {str(e)}")

async def show_search_results(message: types.Message, events: list, db: FDataBase):
    text = f"🔍 <b>Найдено мероприятий: {len(events)}</b>\n\n"
    
    for i, event in enumerate(events[:10], 1):
        icon = "🔥" if event.get('priority') == 'high' else "📅"
        text += f"{i}. {icon} <b>{event['title']}</b>\n📅 {event['date_str']}\n\n"
    
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_selection_keyboard(events[:10])
    )

async def show_event_details(message: types.Message, event: dict, db: FDataBase):
    user = db.get_user(message.from_user.id)
    user_events = db.get_user_events(user['id'])
    
    reg_status = 'none'
    for ue in user_events:
        if ue['id'] == event['id']:
            reg_status = ue['status']
            break
            
    is_admin = bool(db.get_admin(message.from_user.id))
    
    text = (
        f"🎯 <b>{event['title']}</b>\n\n"
        f"📅 <b>Дата:</b> {event['date_str']}\n"
        f"📍 <b>Место:</b> {event['location']}\n"
        f"🔗 <b>Ссылка:</b> {event['url'] or 'Нет'}\n"
        f"📊 <b>Релевантность:</b> {event['score']}/100\n\n"
        f"📝 <b>Описание:</b>\n{event['description'][:500]}..."
    )
    
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_event_detail_keyboard(event['id'], event.get('url', ''), reg_status, is_admin)
    )

@router.message(F.text == "👤 Профиль")
async def show_profile(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user: return
    
    stats = await asyncio.to_thread(db.get_user_stats, user['id'])
    
    text = (
        f"👤 <b>Профиль сотрудника</b>\n\n"
        f"👤 {user['full_name']}\n"
        f"💼 {user['position']}\n"
        f"📧 {user['email']}\n\n"
        f"📅 Мероприятий: <b>{stats.get('total_events', 0)}</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_profile_keyboard())

@router.message(F.text == "📅 Мои мероприятия")
async def show_my_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user: return
    
    await show_events_page(message, db, 0, 'my_events')

@router.message(F.text == "🗂 Экспорт календаря")
async def export_calendar_menu(message: types.Message):
    await message.answer("🗂 <b>Выберите тип экспорта:</b>", 
                        parse_mode="HTML", 
                        reply_markup=get_export_calendar_keyboard())

@router.message(F.text == "📅 Экспорт моих мероприятий")
async def export_my_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user: return
    
    wait_msg = await message.answer("⏳ <b>Генерирую файл с вашими мероприятиями...</b>", parse_mode="HTML")
    
    events = await asyncio.to_thread(db.get_user_events, user['id'])
    
    if not events:
        await wait_msg.delete()
        await message.answer("📭 У вас нет записанных мероприятий для экспорта.")
        return
        
    ics_content = await asyncio.to_thread(IcsGenerator.generate_bulk_ics, events)
    file = BufferedInputFile(ics_content.encode('utf-8'), filename="my_events.ics")
    
    await wait_msg.delete()
    await message.answer_document(
        file, 
        caption=f"✅ <b>Готово!</b>\nФайл содержит {len(events)} ваших мероприятий в формате ICS.",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("export_single_event_"))
async def export_single_event(callback: types.CallbackQuery, db: FDataBase):
    try:
        eid = int(callback.data.split("_")[3])
    except: 
        await callback.answer("❌ Ошибка")
        return
    
    event = db.get_event_by_id(eid)
    if not event:
        await callback.answer("❌ Событие не найдено")
        return
    
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    user_events = db.get_user_events(user['id'])
    is_registered = any(ue['id'] == eid for ue in user_events)
    
    if not is_registered:
        await callback.answer("❌ Вы не записаны на это мероприятие")
        return
    
    wait_msg = await callback.message.answer("⏳ <b>Генерирую файл мероприятия...</b>", parse_mode="HTML")
    
    ics_content = await asyncio.to_thread(IcsGenerator.generate_ics, 
                                         event['title'], 
                                         event['description'],
                                         event['location'],
                                         event['date_str'])
    
    file_name = f"{event['title'][:50]}.ics".replace('/', '-')
    file = BufferedInputFile(ics_content.encode('utf-8'), filename=file_name)
    
    await wait_msg.delete()
    await callback.message.answer_document(
        file, 
        caption=f"✅ <b>Готово!</b>\nФайл мероприятия '{event['title']}' создан.\nИмпортируйте его в календарь.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("event_details_"))
async def event_details(callback: types.CallbackQuery, db: FDataBase):
    try:
        eid = int(callback.data.split("_")[2])
    except: return
    
    event = db.get_event_by_id(eid)
    if not event:
        await callback.answer("Событие не найдено")
        return
    
    user = db.get_user(callback.from_user.id)
    user_events = db.get_user_events(user['id'])
    
    reg_status = 'none'
    for ue in user_events:
        if ue['id'] == eid:
            reg_status = ue['status']
            break
            
    is_admin = bool(db.get_admin(callback.from_user.id))
    
    try:
        analysis = json.loads(event['analysis'])
    except:
        analysis = {}
        
    text = (
        f"🎯 <b>{event['title']}</b>\n\n"
        f"📅 <b>Дата:</b> {event['date_str']}\n"
        f"📍 <b>Место:</b> {event['location']}\n"
        f"🔗 <b>Ссылка:</b> {event['url'] or 'Нет'}\n"
        f"📊 <b>Релевантность:</b> {event['score']}/100\n\n"
        f"📝 <b>Описание:</b>\n{event['description'][:500]}...\n\n"
        f"👥 <b>Аудитория:</b> {analysis.get('target_audience', 'Все желающие')}"
    )
    
    await callback.message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_event_detail_keyboard(eid, event.get('url', ''), reg_status, is_admin)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("request_registration_"))
async def request_reg(callback: types.CallbackQuery, db: FDataBase):
    user = db.get_user(callback.from_user.id)
    eid = int(callback.data.split("_")[2])
    
    user_rank = db._get_position_rank(user['position'])
    
    if db.add_user_event(user['id'], eid):
        if user_rank >= 3:
            await callback.answer("✅ Вы успешно записаны (Автоподтверждение)!")
            db.approve_registration(user['id'], eid)
            
            event = db.get_event_by_id(eid)
            if event:
                ics_content = await asyncio.to_thread(IcsGenerator.generate_ics, 
                                                     event['title'], 
                                                     event['description'],
                                                     event['location'],
                                                     event['date_str'])
                file_name = f"{event['title'][:50]}.ics".replace('/', '-')
                file = BufferedInputFile(ics_content.encode('utf-8'), filename=file_name)
                
                try:
                    await callback.bot.send_document(
                        user['telegram_id'],
                        document=file,
                        caption=f"✅ <b>Вы успешно записаны на мероприятие!</b>\n\n🎯 <b>{event['title']}</b>\n📅 {event['date_str']}",
                        parse_mode="HTML"
                    )
                except: pass
        else:
            await callback.answer("⏳ Заявка отправлена на подтверждение руководителю")
            manager = db.get_user_manager(user['telegram_id'])

            if not manager:
                 admins = db.get_all_admins()
                 if admins: manager = admins[0]

            if manager:
                try:
                    event = db.get_event_by_id(eid)
                    await callback.bot.send_message(
                        manager['telegram_id'],
                        f"📝 <b>ЗАПРОС НА РЕГИСТРАЦИЮ</b>\n\n"
                        f"👤 <b>Сотрудник:</b> {user['full_name']}\n"
                        f"💼 <b>Должность:</b> {user['position']}\n"
                        f"📧 <b>Email:</b> {user['email']}\n"
                        f"📞 <b>Телефон:</b> {user['phone']}\n\n"
                        f"🎯 <b>Мероприятие:</b> {event['title']}\n"
                        f"📅 <b>Дата:</b> {event['date_str']}\n\n"
                        f"Для подтверждения перейдите в раздел '📝 Модерация регистраций'",
                        parse_mode="HTML",
                        reply_markup=get_admin_main_kb(manager['role'])
                    )
                except: pass
        
        event = db.get_event_by_id(eid)
        is_admin = bool(db.get_admin(callback.from_user.id))
        try:
            status_display = 'approved' if user_rank >= 3 else 'pending'
            await callback.message.edit_reply_markup(
                reply_markup=get_event_detail_keyboard(eid, event['url'], status_display, is_admin)
            )
        except: pass
    else:
        await callback.answer("⚠️ Вы уже записаны или заявка на рассмотрении")

@router.callback_query(F.data.startswith("remove_from_calendar_"))
async def remove_reg(callback: types.CallbackQuery, db: FDataBase):
    user = db.get_user(callback.from_user.id)
    eid = int(callback.data.split("_")[3])
    
    if db.remove_user_event(user['id'], eid):
        await callback.answer("🗑 Запись отменена")
        
        event = db.get_event_by_id(eid)
        is_admin = bool(db.get_admin(callback.from_user.id))
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_event_detail_keyboard(eid, event['url'], 'none', is_admin)
            )
        except: pass
    else:
        await callback.answer("Ошибка удаления")

@router.callback_query(F.data == "pending_status_info")
async def pending_info(callback: types.CallbackQuery):
    await callback.answer("Ваша заявка находится на рассмотрении у руководителя.", show_alert=True)

@router.callback_query(F.data == "close_message")
async def close_msg(callback: types.CallbackQuery, db: FDataBase):
    try: 
        await callback.message.delete()
    except: 
        pass
    
    admin = db.get_admin(callback.from_user.id)
    is_admin = bool(admin)
    await callback.message.answer(
        "🔙 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "close_profile")
async def close_prof(callback: types.CallbackQuery, db: FDataBase):
    try: 
        await callback.message.delete()
    except: 
        pass
    
    admin = db.get_admin(callback.from_user.id)
    is_admin = bool(admin)
    await callback.message.answer(
        "🔙 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_callback(callback: types.CallbackQuery, db: FDataBase):
    try: 
        await callback.message.delete()
    except: 
        pass
    
    admin = db.get_admin(callback.from_user.id)
    is_admin = bool(admin)
    await callback.message.answer(
        "🔙 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(F.text == "⬅️ Главное меню")
async def back_to_main_menu(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    await message.answer(
        "🔙 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )