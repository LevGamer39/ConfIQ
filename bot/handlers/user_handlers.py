from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
import json
from typing import List, Dict

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
                "⏳ <b>Ваш аккаунт ожидает подтверждения</b>\n\n"
                "Администратор проверит ваши данные и активирует аккаунт.",
                parse_mode="HTML"
            )
            return
        
        db.update_user_activity(message.from_user.id)
        
        is_admin = bool(admin)
        await message.answer(
            "👋 <b>Добро пожаловать в Eventpedia!</b>\n\n"
            "Ваш персональный помощник по мероприятиям.",
            reply_markup=get_main_keyboard(is_admin),
            parse_mode="HTML"
        )
        return
    
    await state.set_state(UserStates.waiting_for_full_name)
    await message.answer(
        "👋 <b>Добро пожаловать в Eventpedia!</b>\n\n"
        "Давайте зарегистрируем ваш аккаунт.\n"
        "📝 <b>Введите ваше полное ФИО:</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(UserStates.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена")
        return
    
    full_name = message.text.strip()
    if len(full_name) < 2:
        await message.answer("❌ Введите корректное ФИО (минимум 2 символа):")
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(UserStates.waiting_for_email)
    await message.answer(
        "📧 <b>Введите ваш email:</b>\n\n"
        "На этот email будут приходить уведомления о мероприятиях.",
        parse_mode="HTML"
    )

@router.message(UserStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена")
        return
    
    email = message.text.strip()
    if not '@' in email or not '.' in email:
        await message.answer("❌ Введите корректный email адрес:")
        return
    
    await state.update_data(email=email)
    await state.set_state(UserStates.waiting_for_phone)
    await message.answer(
        "📞 <b>Введите ваш номер телефона:</b>\n\n"
        "Номер будет использоваться для связи по мероприятиям.",
        parse_mode="HTML"
    )

@router.message(UserStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Регистрация отменена")
        return
    
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(UserStates.waiting_for_position)
    await message.answer(
        "💼 <b>Выберите вашу должность:</b>\n\n"
        "Это поможет нам подбирать мероприятия, соответствующие вашему уровню.",
        parse_mode="HTML",
        reply_markup=get_position_keyboard()
    )

@router.message(UserStates.waiting_for_position)
async def process_position(message: types.Message, state: FSMContext, db: FDataBase):
    position_map = {
        "👨‍💻 Стажер": "Стажер",
        "👨‍💻 Junior разработчик": "Junior разработчик", 
        "👨‍💻 Middle разработчик": "Middle разработчик",
        "👨‍💻 Senior разработчик": "Senior разработчик",
        "👨‍💻 Team Lead": "Team Lead",
        "👨‍💼 Менеджер проектов": "Менеджер проектов",
        "👨‍💼 Руководитель отдела": "Руководитель отдела",
        "👨‍💼 Директор": "Директор"
    }
    
    if message.text not in position_map:
        await message.answer("❌ Пожалуйста, выберите должность из предложенных кнопок:")
        return
    
    position = position_map[message.text]
    await state.update_data(position=position)
    
    data = await state.get_data()
    
    text = (
        "✅ <b>Проверьте ваши данные:</b>\n\n"
        f"👤 <b>ФИО:</b> {data['full_name']}\n"
        f"📧 <b>Email:</b> {data['email']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"💼 <b>Должность:</b> {position}\n\n"
        "Всё верно?"
    )
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_registration_confirm_keyboard()
    )

@router.callback_query(F.data == "confirm_registration")
async def confirm_registration_handler(callback: types.CallbackQuery, state: FSMContext, db: FDataBase):
    data = await state.get_data()
    
    success = db.add_user(
        callback.from_user.id,
        callback.from_user.username,
        data['full_name']
    )
    
    if success:
        db.update_user_profile(
            callback.from_user.id,
            email=data['email'],
            phone=data['phone'],
            position=data['position']
        )
        
        user = db.get_user(callback.from_user.id)
        admin = db.get_admin(callback.from_user.id)
        
        await state.clear()
        
        if admin:
            await callback.message.edit_text(
                "✅ <b>Регистрация завершена!</b>\n\n"
                "Вы зарегистрированы как администратор.\n"
                "Теперь вы можете пользоваться всеми функциями бота.",
                parse_mode="HTML"
            )
            await callback.message.answer(
                "Выберите действие:",
                reply_markup=get_main_keyboard(True)
            )
        else:
            await callback.message.edit_text(
                "✅ <b>Регистрация завершена!</b>\n\n"
                "Ваша заявка отправлена на рассмотрение администратору.\n"
                "Вы получите уведомление, когда аккаунт будет подтвержден.",
                parse_mode="HTML"
            )
            
            admins = db.get_all_admins()
            for admin in admins:
                try:
                    await callback.bot.send_message(
                        admin['telegram_id'],
                        f"👤 <b>НОВАЯ ЗАЯВКА НА РЕГИСТРАЦИЮ</b>\n\n"
                        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
                        f"👤 ФИО: <b>{user['full_name']}</b>\n"
                        f"📧 Email: {user['email']}\n"
                        f"📞 Телефон: {user['phone']}\n"
                        f"💼 Должность: {user['position']}\n\n"
                        f"Для подтверждения перейдите в '👥 Подтверждение пользователей'",
                        parse_mode="HTML",
                        reply_markup=get_user_approval_keyboard(user['id'])
                    )
                except:
                    continue
    else:
        await callback.answer("❌ Ошибка при регистрации")
    
    await callback.answer()

@router.callback_query(F.data == "edit_registration")
async def edit_registration_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_full_name)
    await callback.message.edit_text(
        "🔄 <b>Начнем регистрацию заново</b>\n\n"
        "📝 <b>Введите ваше полное ФИО:</b>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(F.text == "👤 Профиль")
async def profile_button(message: types.Message, db: FDataBase):
    await show_profile(message, db)

@router.message(Command("profile"))
async def show_profile(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    if user.get('status') != 'approved':
        await message.answer(
            "⏳ <b>Ваш аккаунт ожидает подтверждения</b>\n\n"
            "Администратор проверит ваши данные и активирует аккаунт.\n"
            "Вы получите уведомление, когда все будет готово.",
            parse_mode="HTML"
        )
        return
    
    stats = db.get_user_stats(user['id'])
    db.update_user_activity(message.from_user.id)
    
    status_icon = "✅" if user.get('status') == 'approved' else "⏳"
    status_text = "Подтвержден" if user.get('status') == 'approved' else "Ожидает подтверждения"
    
    text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"{status_icon} <b>Статус:</b> {status_text}\n"
        f"👤 <b>ФИО:</b> {user['full_name'] or 'Не указано'}\n"
        f"📧 <b>Email:</b> {user['email'] or 'Не указан'}\n"
        f"📞 <b>Телефон:</b> {user['phone'] or 'Не указан'}\n"
        f"💼 <b>Должность:</b> {user['position'] or 'Не указана'}\n"
        f"📅 <b>Регистрация:</b> {user['registered_at'][:10]}\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Мероприятий в календаре: {stats.get('total_events', 0)}\n"
        f"• Высокоприоритетных: {stats.get('high_priority', 0)}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_profile_keyboard())

@router.message(F.text == "📅 Мероприятия")
async def show_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Ваш аккаунт ожидает подтверждения администратором.")
        return
        
    db.update_user_activity(message.from_user.id)
    await show_events_page(message, db, 0)

async def show_events_page(message: types.Message, db: FDataBase, page: int):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Ваш аккаунт ожидает подтверждения администратором.")
        return
        
    events = db.get_events_paginated(user['telegram_id'], page=page)
    total_events = db.get_total_approved_events()
    total_pages = max(1, (total_events + 5 - 1) // 5)

    if not events:
        await message.answer(
            "📭 На данный момент нет мероприятий, подходящих для вашей должности.\n\n"
            "Попробуйте позже или используйте поиск.",
            parse_mode="HTML"
        )
        return

    text = f"📅 <b>Доступные мероприятия (Страница {page + 1}/{total_pages}):</b>\n\n"
    for i, event in enumerate(events, 1):
        analysis = json.loads(event['analysis'])
        priority_icon = "🔥" if event['priority'] == 'high' else "📊"
        audience = analysis.get('target_audience', 'не указана')
        text += f"{i}. {priority_icon} <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100 | 👥 {audience[:30]}...\n\n"

    text += "👉 <i>Нажмите на номер кнопки ниже, чтобы открыть подробности и записаться</i>"
    
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_events_keyboard(events, page, total_pages)
    )

@router.callback_query(F.data.startswith("page_"))
async def pagination_handler(callback: types.CallbackQuery, db: FDataBase):
    user = db.get_user(callback.from_user.id)
    if not user or user.get('status') != 'approved':
        await callback.answer("⏳ Аккаунт не подтвержден")
        return
        
    page = int(callback.data.split("_")[1])
    try:
        await callback.message.delete()
    except Exception:
        pass 
    await show_events_page(callback.message, db, page)
    await callback.answer()

@router.message(F.text == "🔥 Приоритетные")
async def show_priority_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Ваш аккаунт ожидает подтверждения администратором.")
        return
        
    db.update_user_activity(message.from_user.id)
        
    events = db.get_high_priority_events(user['telegram_id'], limit=10) 
        
    if not events:
        await message.answer(
            "📭 Пока нет высокоприоритетных событий, подходящих для вашей должности.\n\n"
            "Обычно такие события появляются перед крупными конференциями.",
            parse_mode="HTML"
        )
        return

    text = "🔥 <b>Высокоприоритетные мероприятия</b>\n\n"
    for i, event in enumerate(events, 1):
        analysis = json.loads(event['analysis'])
        audience = analysis.get('target_audience', 'не указана')
        text += f"{i}. <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100 | 👥 {audience[:30]}...\n\n"

    text += "👉 <i>Нажмите на номер кнопки ниже, чтобы открыть подробности и запросить регистрацию</i>"
        
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_selection_keyboard(events)
    )

@router.message(F.text == "🔍 Поиск мероприятий")
async def search_events_start(message: types.Message, state: FSMContext, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Ваш аккаунт ожидает подтверждения администратором.")
        return
        
    db.update_user_activity(message.from_user.id)
        
    await state.set_state(UserStates.waiting_for_search_text)
    await message.answer(
        "🔍 <b>Поиск мероприятий</b>\n\n"
        "Введите ключевые слова для поиска:\n"
        "• Тема (AI, Python, Data Science)\n"
        "• Тип (конференция, митап, воркшоп)\n"
        "• Место (СПб, Москва, онлайн)\n\n"
        "<i>Можно вводить несколько слов через запятую</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(UserStates.waiting_for_search_text)
async def process_search_text(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("🔍 Поиск отменен")
        return
        
    keywords = message.text.strip().split(',')
    keywords = [k.strip() for k in keywords if k.strip()]
    
    if not keywords:
        await message.answer("❌ Введите хотя бы одно ключевое слово:")
        return
    
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await state.clear()
        await message.answer("⏳ Аккаунт не подтвержден")
        return
        
    events = db.search_events_by_keywords(user['telegram_id'], keywords, limit=20)
    
    await state.clear() 
    await show_search_results(message, db, events)

async def show_search_results(message: types.Message, db: FDataBase, events: List[Dict]):
    if not events:
        await message.answer(
            "🔍 <b>По вашему запросу ничего не найдено</b>\n\n"
            "Попробуйте:\n"
            "• Изменить ключевые слова\n"
            "• Использовать более общие запросы\n"
            "• Проверить позже - мероприятия добавляются регулярно",
            parse_mode="HTML"
        )
        return
        
    text = "🔍 <b>Результаты поиска:</b>\n\n"
    for i, event in enumerate(events[:10], 1): 
        priority_icon = "🔥" if event['priority'] == 'high' else "📊"
        text += f"{i}. {priority_icon} <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"   📊 Оценка: {event['score']}/100\n\n"

    if len(events) > 10:
        text += f"\n📎 Показано 10 из {len(events)} мероприятий"

    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(events[:10]))

@router.message(F.text == "📅 Мои мероприятия")
async def show_my_events(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Ваш аккаунт ожидает подтверждения администратором.")
        return

    events = db.get_user_events(user['id'])
    db.update_user_activity(message.from_user.id)
    
    if not events:
        await message.answer(
            "📭 <b>У вас пока нет мероприятий в календаре</b>\n\n"
            "Чтобы добавить мероприятия:\n"
            "1. Перейдите в '📅 Мероприятия'\n"
            "2. Выберите интересующее событие\n"
            "3. Нажмите '📝 Запросить регистрацию'\n"
            "4. Дождитесь подтверждения руководителя",
            parse_mode="HTML"
        )
        return

    approved_events = [e for e in events if e['status'] == 'approved']
    pending_events = [e for e in events if e['status'] == 'pending']
    
    text = "📅 <b>Ваш календарь мероприятий</b>\n\n"
    
    if approved_events:
        text += "✅ <b>Подтвержденные:</b>\n"
        for i, event in enumerate(approved_events[:5], 1):
            text += f"{i}. <b>{event['title']}</b>\n"
            text += f"   📅 {event['date_str']} | 📍 {event['location']}\n"
            text += f"   🔗 Подтверждено: {event['registration_date'][:10]}\n\n"
    
    if pending_events:
        text += "🕒 <b>Ожидают подтверждения:</b>\n"
        for i, event in enumerate(pending_events[:5], 1):
            text += f"{i}. <b>{event['title']}</b>\n"
            text += f"   📅 {event['date_str']} | 📍 {event['location']}\n\n"

    if len(events) > 10:
        text += f"\n📎 Всего мероприятий: {len(events)}"
        
    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(events[:10]))

@router.message(F.text == "🗂 Экспорт календаря")
async def export_monthly_events_button(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user or user.get('status') != 'approved':
        await message.answer("⏳ Ваш аккаунт ожидает подтверждения администратором.")
        return
        
    db.update_user_activity(message.from_user.id)
        
    events = db.get_upcoming_events(user['telegram_id'], days=31) 
    
    if not events:
        await message.answer(
            "📭 <b>Нет предстоящих мероприятий на следующий месяц</b>\n\n"
            "Новые мероприятия появляются регулярно.\n"
            "Попробуйте проверить позже или использовать поиск.",
            parse_mode="HTML"
        )
        return

    ics_content = IcsGenerator.generate_bulk_ics(events)
    
    file_count = len(events)
    file_name = f"events_{file_count}_events.ics"
    
    ics_file = BufferedInputFile(ics_content.encode('utf-8'), filename=file_name)
    
    await message.answer_document(
        ics_file,
        caption=f"✅ <b>Календарь мероприятий выгружен</b>\n\n"
                f"📅 Период: ближайшие 31 день\n"
                f"📋 Событий: <b>{file_count}</b>\n"
                f"💾 Файл: <code>{file_name}</code>\n\n"
                f"Импортируйте файл в ваш календарь.",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("event_details_"))
async def event_details_handler(callback: types.CallbackQuery, db: FDataBase):
    user = db.get_user(callback.from_user.id)
    if not user or user.get('status') != 'approved':
        await callback.answer("⏳ Аккаунт не подтвержден")
        return
        
    event_id = int(callback.data.split("_")[2])
    event = db.get_event_by_id(event_id)
    
    if not event:
        await callback.answer("❌ Событие не найдено")
        return
        
    user_events = db.get_user_events(user['id'])
    
    registration_status = "none"
    for e in user_events:
        if e['id'] == event_id:
            registration_status = e['status']
            break
            
    user_rank = db._get_user_rank(user['telegram_id'])
    if event.get('required_rank', 99) > user_rank:
        await callback.answer("❌ Доступ запрещен по должности")
        return
        
    analysis = json.loads(event['analysis'])
    
    themes = analysis.get('key_themes', [])
    organizers = analysis.get('organizers', [])
    level = analysis.get('level', 'не указан')
    
    text = (
        f"🎯 <b>{event['title']}</b>\n\n"
        f"📅 <b>Дата:</b> {event['date_str']}\n"
        f"📍 <b>Место:</b> {event['location']}\n"
        f"🏷 <b>Уровень:</b> {level}\n"
        f"📊 <b>Оценка AI:</b> {event['score']}/100\n\n"
        f"📝 <b>Описание:</b>\n{event['description'][:400]}...\n\n"
        f"🔍 <b>Детали:</b>\n"
        f"• 👥 Аудитория: {analysis.get('target_audience', 'не указана')}\n"
        f"• 🏷 Темы: {', '.join(themes) if themes else 'не указаны'}\n"
        f"• 🏢 Организаторы: {', '.join(organizers) if organizers else 'не указаны'}\n"
        f"• 👥 Участники: {analysis.get('expected_participants', 'не указано')}\n"
        f"• 📝 Регистрация: {analysis.get('registration_format', 'не указан')}\n"
        f"• 💰 Оплата: {analysis.get('payment_info', 'не указано')}"
    )

    admin = db.get_admin(callback.from_user.id)
    is_admin = bool(admin)
    
    keyboard = get_event_detail_keyboard(event_id, event['url'], registration_status, is_admin)
    
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("request_registration_"))
async def request_registration_handler(callback: types.CallbackQuery, db: FDataBase):
    user = db.get_user(callback.from_user.id)
    if not user or user.get('status') != 'approved':
        await callback.answer("⏳ Аккаунт не подтвержден")
        return
    
    event_id = int(callback.data.split("_")[2])
    event = db.get_event_by_id(event_id)
    
    if not event:
        await callback.answer("❌ Событие не найдено")
        return

    user_rank = db._get_user_rank(user['telegram_id'])
    if event.get('required_rank', 99) > user_rank:
        await callback.answer("❌ Доступ запрещен по должности")
        return

    existing_reg = db.get_user_events(user['id'])
    for reg in existing_reg:
        if reg['id'] == event_id:
            if reg['status'] == 'pending':
                await callback.answer("⏳ Запрос уже отправлен")
            elif reg['status'] == 'approved':
                await callback.answer("✅ Вы уже зарегистрированы")
            return

    if db.add_user_event(user['id'], event_id):
        await callback.answer("✅ Запрос отправлен руководителю!")
        
        manager = db.get_user_manager(user['telegram_id'])
        if manager and manager['telegram_id'] != user['telegram_id']:
            try:
                await callback.bot.send_message(
                    manager['telegram_id'],
                    f"🚨 <b>НОВЫЙ ЗАПРОС НА РЕГИСТРАЦИЮ</b>\n\n"
                    f"👤 <b>Сотрудник:</b> {user['full_name']}\n"
                    f"💼 <b>Должность:</b> {user.get('position', 'Не указано')}\n"
                    f"🎯 <b>Мероприятие:</b> {event['title']}\n"
                    f"📅 <b>Дата:</b> {event['date_str']}\n"
                    f"📍 <b>Место:</b> {event['location']}\n\n"
                    f"Для подтверждения используйте кнопки ниже:",
                    parse_mode="HTML",
                    reply_markup=get_registration_moderation_keyboard(user['id'], event_id)
                )
            except:
                db.approve_registration(user['id'], event_id)
                await callback.answer("✅ Регистрация автоматически подтверждена!")
        else:
            db.approve_registration(user['id'], event_id)
            await callback.answer("✅ Регистрация автоматически подтверждена!")

        admin = db.get_admin(callback.from_user.id)
        is_admin = bool(admin)
        keyboard = get_event_detail_keyboard(event_id, event['url'], 'pending', is_admin)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except:
            pass 
        
    else:
        await callback.answer("❌ Ошибка при отправке запроса")

@router.callback_query(F.data == "pending_status_info")
async def pending_status_info_handler(callback: types.CallbackQuery):
    await callback.answer("Ваш запрос находится на рассмотрении у руководителя")

@router.callback_query(F.data.startswith("remove_from_calendar_"))
async def remove_from_calendar_handler(callback: types.CallbackQuery, db: FDataBase):
    user = db.get_user(callback.from_user.id)
    if not user or user.get('status') != 'approved':
        await callback.answer("⏳ Аккаунт не подтвержден")
        return
        
    event_id = int(callback.data.split("_")[3])
    db.remove_user_event(user['id'], event_id)
    
    event = db.get_event_by_id(event_id)
    admin = db.get_admin(callback.from_user.id)
    is_admin = bool(admin)
    keyboard = get_event_detail_keyboard(event_id, event['url'], 'none', is_admin)
    
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except:
        pass 
        
    await callback.answer("🗑 Удалено из календаря")

@router.callback_query(F.data == "close_message")
async def close_message_handler(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()

@router.callback_query(F.data == "close_profile")
async def close_profile_handler(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()