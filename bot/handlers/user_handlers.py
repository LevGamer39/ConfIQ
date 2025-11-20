from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
import json
import os

from utils.keyboards import *
from utils.states import UserStates
from utils.ics_generator import IcsGenerator
from database import FDataBase

router = Router()

@router.message(CommandStart())
async def start(message: types.Message, db: FDataBase, state: FSMContext):
    user = db.get_user(message.from_user.id)
    db.update_user_activity(message.from_user.id)
    
    if not user:
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        db.add_user(message.from_user.id, message.from_user.username, full_name)
        db.log_user_activity(message.from_user.id, "start", "First start")
        
        await message.answer(
            "👋 <b>Добро пожаловать в AI-помощник Сбера!</b>\n\n"
            "Для завершения регистрации заполните ваш профиль.\n"
            "Введите ваше ФИО:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(UserStates.waiting_for_full_name)
        return
    
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    db.log_user_activity(user['id'], "start", "Returning user")
    
    await message.answer(
        "👋 <b>С возвращением в AI-помощник Сбера!</b>\n\n"
        "Я помогаю сотрудникам Центра исследований и разработки Сбера в Санкт-Петербурге:\n"
        "• Находить лучшие IT-мероприятия города\n"
        "• Анализировать релевантность с помощью AI\n"
        "• Планировать участие в календаре\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )

@router.message(UserStates.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена", reply_markup=types.ReplyKeyboardRemove())
        return
    
    full_name = message.text.strip()
    if len(full_name) < 2:
        await message.answer("❌ Введите корректное ФИО:")
        return
    
    db.update_user_profile(message.from_user.id, full_name=full_name)
    await state.set_state(UserStates.waiting_for_email)
    await message.answer("📧 Теперь введите ваш email:")

@router.message(UserStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена", reply_markup=types.ReplyKeyboardRemove())
        return
    
    email = message.text.strip()
    if not '@' in email or not '.' in email:
        await message.answer("❌ Введите корректный email:")
        return
    
    db.update_user_profile(message.from_user.id, email=email)
    await state.set_state(UserStates.waiting_for_phone)
    await message.answer("📞 Теперь введите ваш номер телефона:")

@router.message(UserStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена", reply_markup=types.ReplyKeyboardRemove())
        return
    
    phone = message.text.strip()
    db.update_user_profile(message.from_user.id, phone=phone)
    
    user = db.get_user(message.from_user.id)
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    
    db.log_user_activity(user['id'], "registration_complete")
    
    await state.clear()
    await message.answer(
        "✅ <b>Регистрация завершена!</b>\n\n"
        "Теперь вы можете пользоваться всеми функциями бота.\n"
        "Посмотреть ваш профиль: /profile",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Профиль")
async def profile_button(message: types.Message, db: FDataBase):
    await show_profile(message, db)

@router.message(F.text == "📅 Мои мероприятия")
async def my_events_button(message: types.Message, db: FDataBase):
    await show_my_events(message, db)

@router.message(Command("profile"))
async def show_profile(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    db.update_user_activity(message.from_user.id)
    
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    stats = db.get_user_stats(user['id'])
    db.log_user_activity(user['id'], "view_profile")
    
    text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
        f"👤 ФИО: {user['full_name'] or 'Не указано'}\n"
        f"📧 Email: {user['email'] or 'Не указан'}\n"
        f"📞 Телефон: {user['phone'] or 'Не указан'}\n"
        f"🏢 Отдел: {user['department'] or 'Не указан'}\n"
        f"💼 Должность: {user['position'] or 'Не указана'}\n"
        f"📅 Зарегистрирован: {user['registered_at'][:10]}\n\n"
        f"📊 <b>Статистика активности:</b>\n"
        f"• Мероприятий в календаре: {stats['total_events']}\n"
        f"• Высокоприоритетных: {stats['high_priority']}\n"
        f"• Активных дней (30 дней): {stats['active_days_30']}\n"
        f"• Активность (7 дней): {stats['weekly_activity']} действий"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_profile_keyboard())

@router.callback_query(F.data == "close_profile")
async def close_profile(callback: types.CallbackQuery):
    await callback.message.delete()

@router.message(Command("edit_profile"))
async def edit_profile_start(message: types.Message, state: FSMContext, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    await state.set_state(UserStates.waiting_for_edit_field)
    await message.answer(
        "✏️ <b>Редактирование профиля</b>\n\n"
        "Выберите поле для редактирования:",
        parse_mode="HTML",
        reply_markup=get_edit_profile_keyboard()
    )

@router.message(UserStates.waiting_for_edit_field)
async def process_edit_field(message: types.Message, state: FSMContext, db: FDataBase):
    field_map = {
        "👤 ФИО": "full_name",
        "📧 Email": "email", 
        "📞 Телефон": "phone",
        "🏢 Отдел": "department",
        "💼 Должность": "position"
    }
    
    if message.text not in field_map:
        await message.answer("❌ Выберите поле из списка:")
        return
    
    field = field_map[message.text]
    await state.update_data(editing_field=field)
    await state.set_state(UserStates.waiting_for_edit_value)
    
    field_names = {
        "full_name": "ФИО",
        "email": "email",
        "phone": "номер телефона", 
        "department": "отдел",
        "position": "должность"
    }
    
    await message.answer(
        f"✏️ Введите новое значение для {field_names[field]}:",
        reply_markup=get_cancel_keyboard()
    )

@router.message(UserStates.waiting_for_edit_value)
async def process_edit_value(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Редактирование отменено")
        return
    
    data = await state.get_data()
    field = data['editing_field']
    value = message.text.strip()
    
    updates = {field: value}
    db.update_user_profile(message.from_user.id, **updates)
    db.log_user_activity(message.from_user.id, "edit_profile", f"Updated {field}")
    
    await state.clear()
    await message.answer(f"✅ {field.replace('_', ' ').title()} успешно обновлено!")

@router.message(Command("my_events"))
async def show_my_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    db.update_user_activity(message.from_user.id)
    
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    events = db.get_user_events(user['id'])
    db.log_user_activity(user['id'], "view_my_events")
    
    if not events:
        await message.answer(
            "📭 <b>У вас пока нет мероприятий в календаре</b>\n\n"
            "Добавьте мероприятия через меню мероприятий.",
            parse_mode="HTML"
        )
        return
    
    text = "📅 <b>Ваши мероприятия:</b>\n\n"
    for i, event in enumerate(events[:15], 1):
        analysis = json.loads(event['ai_analysis'])
        priority_icon = "🔥" if event['priority'] == 'high' else "✅" if event['priority'] == 'medium' else "📊"
        status_icon = "✅" if event['status'] == 'registered' else "⏳"
        
        text += f"{i}. {priority_icon} <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100 | {status_icon} {event.get('registration_status', 'зарегистрирован')}\n"
        text += f"   📝 Добавлено: {event['registration_date'][:10]}\n\n"
    
    text += "👉 <i>Нажмите на номер кнопки ниже для скачивания или просмотра</i>"
    
    if len(events) > 15:
        text += f"\n📎 ... и еще {len(events) - 15} мероприятий"
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(events[:15]))

@router.message(Command("help"))
async def help_command(message: types.Message, db: FDataBase):
    db.update_user_activity(message.from_user.id)
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    
    text = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "📅 <b>Мероприятия</b> - все утвержденные события\n"
        "🔍 <b>Поиск мероприятий</b> - поиск по темам\n"
        "🔥 <b>Приоритетные</b> - высокоприоритетные события\n"
        "🤝 <b>Партнерские</b> - мероприятия от партнеров\n"
        "👤 <b>Профиль</b> - ваша статистика\n"
        "📅 <b>Мои мероприятия</b> - ваш календарь\n"
        "✏️ <b>Редактировать профиль</b> - изменить данные\n"
    )
    
    if is_admin:
        text += "\n⚙️ <b>Админ-функции:</b>\n"
        text += "🔄 Сканирование - поиск новых мероприятий\n"
        text += "📩 Партнеры - добавление приглашений\n"
        text += "⚖️ Модерация - утверждение событий\n"
        text += "📊 Статистика - аналитика системы\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text and msg.text == "📊 Статистика")
async def show_stats(message: types.Message, db: FDataBase):
    db.update_user_activity(message.from_user.id)
    admin = db.get_admin(message.from_user.id)
    
    if not admin:
        user = db.get_user(message.from_user.id)
        if user:
            stats = db.get_user_stats(user['id'])
            db.log_user_activity(user['id'], "view_stats")
            
            text = (
                "📊 <b>Ваша статистика</b>\n\n"
                f"📅 Мероприятий в календаре: <b>{stats['total_events']}</b>\n"
                f"🔥 Высокоприоритетных: <b>{stats['high_priority']}</b>\n"
                f"📈 Активных дней (30 дней): <b>{stats['active_days_30']}</b>\n"
                f"🎯 Активность (7 дней): <b>{stats['weekly_activity']}</b> действий"
            )
            await message.answer(text, parse_mode="HTML")
        return
        
    stats = db.get_stats()
    db.log_user_activity(message.from_user.id, "view_admin_stats")
    
    departments_text = ""
    for dept, count in stats.get('departments', {}).items():
        departments_text += f"• {dept}: {count}\n"
    
    text = (
        "📊 <b>Статистика системы</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"• Активных пользователей: <b>{stats['active_users']}</b>\n"
        f"• Активных за неделю: <b>{stats['weekly_active_users']}</b>\n\n"
        
        f"📅 <b>Регистрации:</b>\n"
        f"• Всего регистраций: <b>{stats['total_registrations']}</b>\n"
        f"• За неделю: <b>{stats['weekly_registrations']}</b>\n\n"
        
        f"🏢 <b>Отделы:</b>\n{departments_text}\n"
        
        f"🎯 <b>Мероприятия:</b>\n"
        f"• Всего событий: <b>{stats['total_events']}</b>\n"
        f"• Опубликовано: <b>{stats['approved']}</b>\n"
        f"• На модерации: <b>{stats['pending']}</b>\n"
        f"• Высокий приоритет: <b>{stats['high_priority']}</b>\n"
        f"• Партнерских: <b>{stats['partners']}</b>\n"
        f"• На 2025 год: <b>{stats['upcoming_2025']}</b>\n"
        f"• Средняя оценка: <b>{stats['avg_score']}/100</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text and msg.text == "📅 Мероприятия")
async def show_events(message: types.Message, db: FDataBase):
    db.update_user_activity(message.from_user.id)
    user = db.get_user(message.from_user.id)
    if user:
        db.log_user_activity(user['id'], "view_events")
    await show_events_page(message, db, 0)

async def show_events_page(message: types.Message, db: FDataBase, page: int = 0):
    events = db.get_events_paginated(page=page, limit=10)
    total_events = db.get_total_approved_events()
    total_pages = (total_events + 9) // 10
    
    if not events:
        await message.answer(
            "📭 <b>Пока нет актуальных мероприятий</b>\n\n"
            "Новые события появятся после модерации администратором.",
            parse_mode="HTML"
        )
        return
    
    text = f"📅 <b>Мероприятия</b> (страница {page + 1}/{total_pages})\n\n"
    
    for i, event in enumerate(events, 1):
        analysis = json.loads(event['ai_analysis'])
        priority_icon = "🔥" if event['priority'] == 'high' else "✅" if event['priority'] == 'medium' else "📊"
        text += f"{i}. {priority_icon} <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100\n"
        text += f"   👥 Участники: {analysis.get('expected_participants', 'не указано')}\n\n"
    
    text += "👉 <i>Нажмите на номер кнопки ниже, чтобы открыть подробности и записаться</i>"
    
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_events_keyboard(events, page, total_pages)
    )

@router.message(lambda msg: msg.text and msg.text == "🔥 Приоритетные")
async def show_priority_events(message: types.Message, db: FDataBase):
    db.update_user_activity(message.from_user.id)
    user = db.get_user(message.from_user.id)
    if user:
        db.log_user_activity(user['id'], "view_priority_events")
        
    events = db.get_high_priority_events(limit=10)
    
    if not events:
        await message.answer(
            "📭 <b>Нет высокоприоритетных мероприятий</b>\n\n"
            "Высокоприоритетные события появляются для стратегических встреч и крупных конференций.",
            parse_mode="HTML"
        )
        return
    
    text = "🔥 <b>Высокоприоритетные мероприятия</b>\n\n"
    
    for i, event in enumerate(events, 1):
        analysis = json.loads(event['ai_analysis'])
        text += f"{i}. 🔥 <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100\n"
        text += f"   👥 Участники: {analysis.get('expected_participants', 'не указано')}\n\n"
        
    text += "👉 <i>Нажмите на номер кнопки ниже для записи</i>"
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(events))

@router.message(lambda msg: msg.text and msg.text == "🤝 Партнерские")
async def show_partner_events(message: types.Message, db: FDataBase):
    db.update_user_activity(message.from_user.id)
    user = db.get_user(message.from_user.id)
    if user:
        db.log_user_activity(user['id'], "view_partner_events")
        
    events = db.search_events_by_keywords(['партнер', 'приглаш', 'встреча'], limit=10)
    partner_events = [event for event in events if event['source'] == 'partner']
    
    if not partner_events:
        await message.answer(
            "📭 <b>Нет партнерских мероприятий</b>\n\n"
            "Партнерские приглашения добавляются администраторами вручную.",
            parse_mode="HTML"
        )
        return
    
    text = "🤝 <b>Партнерские мероприятия</b>\n\n"
    
    for i, event in enumerate(partner_events, 1):
        analysis = json.loads(event['ai_analysis'])
        text += f"{i}. 🤝 <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100\n"
        text += f"   📋 Условия: {analysis.get('participation_conditions', 'не указаны')}\n\n"
        
    text += "👉 <i>Нажмите на номер кнопки ниже для записи</i>"
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(partner_events))

@router.callback_query(F.data.startswith("events_page_"))
async def events_page_handler(callback: types.CallbackQuery, db: FDataBase):
    page = int(callback.data.split("_")[2])
    await callback.message.delete()
    await show_events_page(callback.message, db, page)

@router.callback_query(F.data.startswith("event_detail_"))
async def event_detail_handler(callback: types.CallbackQuery, db: FDataBase):
    event_id = int(callback.data.split("_")[2])
    event = db.get_event_by_id(event_id)
    
    if not event:
        await callback.answer("❌ Мероприятие не найдено")
        return
    
    user = db.get_user(callback.from_user.id)
    if user:
        db.log_user_activity(user['id'], "view_event_detail", f"Event {event_id}")
    
    analysis = json.loads(event['ai_analysis'])
    
    text = (
        f"📌 <b>{event['title']}</b>\n\n"
        f"📅 <b>Дата:</b> {event['date_str']}\n"
        f"📍 <b>Место:</b> {event['location']}\n"
        f"📊 <b>Оценка:</b> {event['score']}/100\n"
        f"👥 <b>Участники:</b> {analysis.get('expected_participants', 'не указано')}\n"
        f"🎯 <b>Уровень:</b> {analysis.get('level', 'не указан')}\n"
        f"📝 <b>Регистрация:</b> {analysis.get('registration_format', 'не указан')}\n"
        f"💰 <b>Оплата:</b> {analysis.get('payment_info', 'не указано')}\n\n"
        f"💡 <b>Описание:</b>\n{analysis.get('summary', 'Нет описания')}\n\n"
        f"🏷 <b>Темы:</b> {', '.join(analysis.get('key_themes', []))}"
    )
    
    is_registered = False
    if user:
         user_events = db.get_user_events(user['id'])
         is_registered = any(e['id'] == event_id for e in user_events)
    
    keyboard = get_event_detail_keyboard(event_id, event['url'], is_registered)
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        
    await callback.answer()

@router.callback_query(F.data == "back_to_list")
async def back_to_list_handler(callback: types.CallbackQuery, db: FDataBase):
    await callback.message.delete()
    await show_events_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("add_to_calendar_"))
async def add_to_calendar_handler(callback: types.CallbackQuery, db: FDataBase):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала завершите регистрацию через /start")
        return
    
    event_id = int(callback.data.split("_")[3])
    event = db.get_event_by_id(event_id)
    
    if not event:
        await callback.answer("❌ Мероприятие не найдено")
        return
    
    success = db.add_user_event(user['id'], event_id)
    if success:
        await callback.answer("✅ Добавлено в ваш календарь")
        
        analysis = json.loads(event['ai_analysis'])
        text = (
            f"✅ <b>Мероприятие добавлено в календарь</b>\n\n"
            f"📌 {event['title']}\n"
            f"📅 {event['date_str']}\n"
            f"📍 {event['location']}\n\n"
            f"Просмотреть ваши мероприятия: /my_events"
        )
        await callback.message.answer(text, parse_mode="HTML")
        
        new_keyboard = get_event_detail_keyboard(event_id, event['url'], True)
        try:
            await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        except:
            pass
            
    else:
        await callback.answer("❌ Уже в вашем календаре")

@router.callback_query(F.data == "already_added")
async def already_added_handler(callback: types.CallbackQuery):
    await callback.answer("✅ Вы уже зарегистрированы на это событие", show_alert=True)

@router.callback_query(F.data.startswith("download_ics_"))
async def download_ics_handler(callback: types.CallbackQuery, db: FDataBase):
    try:
        event_id = int(callback.data.split("_")[2])
        event = db.get_event_by_id(event_id)
        
        if not event:
            await callback.answer("❌ Мероприятие не найдено")
            return

        await callback.answer("🔄 Генерирую файл календаря...")
        
        analysis = json.loads(event['ai_analysis'])
        description = f"{analysis.get('summary', 'Без описания')}\n\nСсылка: {event['url']}"
        
        ics_data = IcsGenerator.generate_ics(
            title=event['title'],
            description=description,
            location=event['location'],
            date_str=event['date_str']
        )
        
        file = BufferedInputFile(ics_data, filename=f"event_{event_id}.ics")
        
        await callback.message.answer_document(
            document=file,
            caption="📅 Файл для календаря (Outlook, Google, Apple)"
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка при создании файла: {str(e)}", show_alert=True)

@router.message(lambda msg: msg.text and msg.text == "🔍 Поиск мероприятий")
async def search_events_start(message: types.Message, state: FSMContext, db: FDataBase):
    db.update_user_activity(message.from_user.id)
    user = db.get_user(message.from_user.id)
    if user:
        db.log_user_activity(user['id'], "start_search")
        
    await state.set_state(UserStates.waiting_for_search)
    await message.answer(
        "🔍 <b>Поиск мероприятий</b>\n\n"
        "Выберите тип поиска:",
        parse_mode="HTML",
        reply_markup=get_search_type_keyboard()
    )

@router.message(UserStates.waiting_for_search)
async def search_type_handler(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "⬅️ Главное меню":
        await state.clear()
        admin = db.get_admin(message.from_user.id)
        await message.answer(
            "🔍 Поиск отменен", 
            reply_markup=get_main_keyboard(bool(admin))
        )
        return
    
    if message.text == "🔤 Текстовый поиск":
        await message.answer(
            "🔤 <b>Текстовый поиск</b>\n\n"
            "Введите ключевые слова для поиска:\n"
            "• Тема (AI, Data Science, разработка)\n"
            "• Дата (март 2025, апрель)\n"
            "• Организатор (Сбер, Яндекс, ИТМО)",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(UserStates.waiting_for_search_text)
        return
        
    elif message.text == "🎯 Поиск по критериям":
        await message.answer(
            "🎯 <b>Поиск по критериям</b>\n\n"
            "Выберите критерии для поиска:",
            parse_mode="HTML",
            reply_markup=get_criteria_selection_keyboard()
        )
        await state.set_state(UserStates.waiting_for_criteria)
        return
    
    await message.answer("❌ Выберите тип поиска из меню:")

@router.message(UserStates.waiting_for_search_text)
async def search_text_handler(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        admin = db.get_admin(message.from_user.id)
        await message.answer(
            "🔍 Поиск отменен", 
            reply_markup=get_main_keyboard(bool(admin))
        )
        return
    
    keywords = [message.text.strip()]
    events = db.search_events_by_keywords(keywords, limit=20)
    
    user = db.get_user(message.from_user.id)
    if user:
        db.log_user_activity(user['id'], "search_text", f"Query: {message.text}, Results: {len(events)}")
    
    await show_search_results(message, events, f"по запросу '{message.text}'")
    await state.clear()

@router.callback_query(UserStates.waiting_for_criteria, F.data.startswith("criteria_"))
async def criteria_selection_handler(callback: types.CallbackQuery, state: FSMContext, db: FDataBase):
    action = callback.data.split("_")[1]
    
    if action == "theme":
        await callback.message.edit_text(
            "🎯 <b>Выберите тематику мероприятий:</b>",
            parse_mode="HTML",
            reply_markup=get_themes_keyboard()
        )
        
    elif action == "location":
        await callback.message.edit_text(
            "📍 <b>Выберите местоположение:</b>",
            parse_mode="HTML",
            reply_markup=get_locations_keyboard()
        )
        
    elif action == "date":
        await callback.message.edit_text(
            "📅 <b>Выберите период:</b>",
            parse_mode="HTML",
            reply_markup=get_dates_keyboard()
        )
        
    elif action == "audience":
        await callback.message.edit_text(
            "👥 <b>Выберите целевую аудиторию:</b>",
            parse_mode="HTML",
            reply_markup=get_audience_keyboard()
        )
        
    elif action == "search":
        data = await state.get_data()
        selected_criteria = data.get('criteria', {})
        
        if not selected_criteria:
            await callback.answer("❌ Выберите хотя бы один критерий")
            return
            
        events = db.search_events_by_criteria(selected_criteria, limit=20)
        
        user = db.get_user(callback.from_user.id)
        if user:
            db.log_user_activity(user['id'], "search_criteria", f"Criteria: {selected_criteria}, Results: {len(events)}")
        
        await callback.message.delete()
        criteria_text = format_criteria_text(selected_criteria)
        await show_search_results(callback.message, events, f"по критериям:\n{criteria_text}")
        await state.clear()
    
    elif action == "clear":
        await state.update_data(criteria={})
        await callback.message.edit_text(
            "🎯 <b>Критерии очищены</b>\n\n"
            "Выберите критерии для поиска:",
            parse_mode="HTML",
            reply_markup=get_criteria_selection_keyboard()
        )
        await callback.answer("✅ Критерии очищены")
    
    elif action == "back":
        await callback.message.edit_text(
            "🎯 <b>Поиск по критериям</b>\n\n"
            "Выберите критерии для поиска:",
            parse_mode="HTML",
            reply_markup=get_criteria_selection_keyboard()
        )

@router.callback_query(UserStates.waiting_for_criteria, F.data.startswith("select_"))
async def criteria_value_handler(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    criteria_type = parts[1]
    value = "_".join(parts[2:])
    
    data = await state.get_data()
    selected_criteria = data.get('criteria', {})
    
    if criteria_type not in selected_criteria:
        selected_criteria[criteria_type] = []
    
    if value in selected_criteria[criteria_type]:
        selected_criteria[criteria_type].remove(value)
    else:
        selected_criteria[criteria_type].append(value)
    
    await state.update_data(criteria=selected_criteria)
    
    criteria_text = format_criteria_text(selected_criteria)
    await callback.message.edit_text(
        f"🎯 <b>Выбранные критерии:</b>\n{criteria_text}\n\n"
        "Продолжайте выбирать критерии или нажмите '🔍 Найти':",
        parse_mode="HTML",
        reply_markup=get_criteria_selection_keyboard()
    )
    
    await callback.answer(f"✅ {get_criteria_display_name(criteria_type, value)}")

async def show_search_results(message: types.Message, events: list, search_description: str):
    if not events:
        await message.answer(
            f"🔍 <b>По {search_description} ничего не найдено</b>\n\n"
            "Попробуйте изменить критерии поиска или использовать другие ключевые слова.",
            parse_mode="HTML"
        )
        return
    
    text = f"🔍 <b>Результаты поиска {search_description}</b>\nНайдено мероприятий: {len(events)}\n\n"
    
    for i, event in enumerate(events[:10], 1):
        analysis = json.loads(event['ai_analysis'])
        priority_icon = "🔥" if event['priority'] == 'high' else "✅"
        text += f"{i}. {priority_icon} <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100\n\n"
    
    text += "👉 <i>Нажмите на номер кнопки ниже для просмотра деталей</i>"

    if len(events) > 10:
        text += f"\n📎 Показано 10 из {len(events)} мероприятий"

    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(events[:10]))

def format_criteria_text(criteria: dict) -> str:
    if not criteria:
        return "❌ Критерии не выбраны"
    
    text = ""
    criteria_names = {
        'theme': '🎯 Темы',
        'location': '📍 Местоположение', 
        'date': '📅 Период',
        'audience': '👥 Аудитория'
    }
    
    for key, values in criteria.items():
        if values:
            display_values = [get_criteria_display_name(key, v) for v in values]
            text += f"{criteria_names.get(key, key)}: {', '.join(display_values)}\n"
    
    return text

def get_criteria_display_name(criteria_type: str, value: str) -> str:
    display_names = {
        'ai': '🤖 Искусственный интеллект',
        'data_science': '📊 Data Science',
        'development': '💻 Разработка',
        'management': '🎯 IT-менеджмент',
        'security': '🔐 Кибербезопасность',
        'cloud': '☁️ Облачные технологии',
        'spb': '🏛️ Санкт-Петербург',
        'msk': '🏢 Москва',
        'online': '🌐 Онлайн',
        'week': '📅 На этой неделе',
        'month': '📅 В этом месяце',
        'quarter': '📅 В этом квартале',
        'developers': '👨‍💻 Разработчики',
        'managers': '👔 Руководители',
        'analysts': '📈 Аналитики',
        'researchers': '🔬 Исследователи'
    }
    return display_names.get(value, value)