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
        events = await asyncio.to_thread(db.get_events_paginated, message.from_user.id, page, 5, None)
        total = await asyncio.to_thread(db.get_total_approved_events, 'main')
        title = "📅 Основные мероприятия"
    elif event_type == 'priority':
        events = await asyncio.to_thread(db.get_high_priority_events, message.from_user.id)
        total = len(events) if events else 0
        page = 0
        title = "🔥 Приоритетные мероприятия"
    elif event_type == 'partner':
        events = await asyncio.to_thread(db.get_partner_events, message.from_user.id)
        total = len(events) if events else 0
        page = 0
        title = "🤝 Партнёрские мероприятия"
    
    if not events:
        await message.answer("📭 Мероприятий пока нет.")
        return

    text = f"<b>{title}</b>\n\n"
    for i, event in enumerate(events, 1):
        icon = "🔥" if event['priority'] == 'high' else "🤝" if event['source'] == 'partner' else "🔵"
        text += f"{i}. {icon} <b>{event['title']}</b>\n📅 {event['date_str']}\n\n"
    
    if event_type in ['priority', 'partner']:
        kb = get_selection_keyboard(events)
    else:
        kb = get_events_keyboard(events, page, max(1, (total + 4) // 5))
    
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("page_"))
async def pagination_handler(callback: types.CallbackQuery, db: FDataBase):
    try:
        page = int(callback.data.split("_")[1])
        await callback.message.delete()
        await show_events_page(callback.message, db, page, 'main')
    except: pass

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
    await message.answer("🔍 <b>Введите запрос:</b>\n(тема, спикер или технология)", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(UserStates.waiting_for_search_text)
async def search_process(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        is_admin = bool(db.get_admin(message.from_user.id))
        await message.answer("Поиск отменен", reply_markup=get_main_keyboard(is_admin))
        return
    
    wait_msg = await message.answer("⏳ <b>Ищу мероприятия...</b>", parse_mode="HTML")
    
    keywords = [k.strip() for k in message.text.split(',') if k.strip()]
    events = await asyncio.to_thread(db.search_events_by_keywords, message.from_user.id, keywords)
    
    await state.clear()
    await wait_msg.delete()
    
    if not events:
        is_admin = bool(db.get_admin(message.from_user.id))
        await message.answer("🔍 Ничего не найдено.", reply_markup=get_main_keyboard(is_admin))
        return
        
    text = f"🔍 <b>Результаты ({len(events)}):</b>\n\n"
    for i, event in enumerate(events[:10], 1):
        text += f"{i}. <b>{event['title']}</b>\n📅 {event['date_str']}\n\n"
        
    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(events[:10]))

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
    
    events = await asyncio.to_thread(db.get_user_events, user['id'])
    
    if not events:
        await message.answer("📭 Вы пока никуда не записаны.")
        return
        
    text = "📅 <b>Ваши планы:</b>\n\n"
    for i, event in enumerate(events, 1):
        status = "✅" if event['status'] == 'approved' else "⏳"
        text += f"{i}. {status} <b>{event['title']}</b>\n📅 {event['date_str']}\n\n"
        
    await message.answer(text, parse_mode="HTML", reply_markup=get_selection_keyboard(events))

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
        
    file_content = "📅 Ваши мероприятия:\n\n"
    for i, event in enumerate(events, 1):
        status = "✅ Подтверждено" if event['status'] == 'approved' else "⏳ Ожидает подтверждения"
        file_content += f"{i}. {event['title']}\n"
        file_content += f"   📅 Дата: {event['date_str']}\n"
        file_content += f"   📍 Место: {event['location']}\n"
        file_content += f"   📊 Статус: {status}\n"
        file_content += f"   🔗 Ссылка: {event['url'] or 'Нет'}\n\n"
    
    file_name = f"my_events_{user['id']}.txt"
    file = BufferedInputFile(file_content.encode('utf-8'), filename=file_name)
    
    await wait_msg.delete()
    await message.answer_document(
        file, 
        caption=f"✅ <b>Готово!</b>\nФайл содержит {len(events)} ваших мероприятий.",
        parse_mode="HTML"
    )

@router.message(F.text == "🗓 Экспорт по периоду")
async def export_period_menu(message: types.Message):
    await message.answer("🗓 <b>Выберите период для экспорта:</b>", 
                        parse_mode="HTML", 
                        reply_markup=get_export_period_keyboard())

@router.message(F.text.in_(["📅 На неделю", "📅 На месяц", "📅 На 3 месяца", "📅 На год"]))
async def export_by_period(message: types.Message, db: FDataBase):
    user = db.get_user(message.from_user.id)
    if not user: return
    
    if message.text == "📅 На неделю":
        days = 7
        period_name = "неделю"
    elif message.text == "📅 На месяц":
        days = 30
        period_name = "месяц"
    elif message.text == "📅 На 3 месяца":
        days = 90
        period_name = "3 месяца"
    else:
        days = 365
        period_name = "год"
    
    wait_msg = await message.answer(f"⏳ <b>Генерирую календарь на {period_name}...</b>", parse_mode="HTML")
    
    events = await asyncio.to_thread(db.get_upcoming_events, user['telegram_id'], days)
    
    if not events:
        await wait_msg.delete()
        await message.answer(f"📅 Нет мероприятий на ближайшие {period_name}.")
        return
        
    ics_content = await asyncio.to_thread(IcsGenerator.generate_bulk_ics, events)
    file = BufferedInputFile(ics_content.encode('utf-8'), filename=f"events_{days}d.ics")
    
    await wait_msg.delete()
    await message.answer_document(
        file, 
        caption=f"✅ <b>Готово!</b>\nКалендарь на {period_name} содержит {len(events)} событий.\nИмпортируйте его в Outlook или Google Calendar.",
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
        if user_rank <= 2:
            await callback.answer("✅ Вы успешно записаны!")
            db.approve_registration(user['id'], eid)
        else:
            await callback.answer("⏳ Заявка отправлена на подтверждение руководителю")
            manager = db.get_user_manager(user['telegram_id'])
            if manager:
                try:
                    await callback.bot.send_message(
                        manager['telegram_id'],
                        f"📝 <b>ЗАПРОС НА РЕГИСТРАЦИЮ</b>\n\n"
                        f"👤 Сотрудник: {user['full_name']}\n"
                        f"💼 Должность: {user['position']}\n"
                        f"📅 Мероприятие: {db.get_event_by_id(eid)['title']}\n\n"
                        f"✅ /approve_reg_{user['id']}_{eid}\n"
                        f"❌ /reject_reg_{user['id']}_{eid}",
                        parse_mode="HTML"
                    )
                except: pass
        
        event = db.get_event_by_id(eid)
        is_admin = bool(db.get_admin(callback.from_user.id))
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_event_detail_keyboard(eid, event['url'], 'pending', is_admin)
            )
        except: pass
    else:
        await callback.answer("⚠️ Вы уже записаны или заявка на рассмотрении")

@router.message(lambda msg: msg.text and msg.text.startswith("/approve_reg_"))
async def approve_registration_cmd(message: types.Message, db: FDataBase):
    try:
        parts = message.text.split("_")
        user_id = int(parts[2])
        event_id = int(parts[3])
        
        if db.approve_registration(user_id, event_id):
            user = db.get_user_by_id(user_id)
            event = db.get_event_by_id(event_id)
            
            await message.answer("✅ Регистрация подтверждена")
            
            if user:
                try:
                    await message.bot.send_message(
                        user['telegram_id'],
                        f"✅ <b>Ваша регистрация подтверждена!</b>\n\n"
                        f"📅 Мероприятие: {event['title']}\n"
                        f"📅 Дата: {event['date_str']}",
                        parse_mode="HTML"
                    )
                except: pass
        else:
            await message.answer("❌ Ошибка подтверждения")
    except:
        await message.answer("❌ Неверный формат команды")

@router.message(lambda msg: msg.text and msg.text.startswith("/reject_reg_"))
async def reject_registration_cmd(message: types.Message, db: FDataBase):
    try:
        parts = message.text.split("_")
        user_id = int(parts[2])
        event_id = int(parts[3])
        
        if db.reject_registration(user_id, event_id):
            user = db.get_user_by_id(user_id)
            event = db.get_event_by_id(event_id)
            
            await message.answer("❌ Регистрация отклонена")
            
            if user:
                try:
                    await message.bot.send_message(
                        user['telegram_id'],
                        f"❌ <b>Ваша регистрация отклонена руководителем</b>\n\n"
                        f"📅 Мероприятие: {event['title']}\n"
                        f"📅 Дата: {event['date_str']}",
                        parse_mode="HTML"
                    )
                except: pass
        else:
            await message.answer("❌ Ошибка отклонения")
    except:
        await message.answer("❌ Неверный формат команды")

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
async def close_msg(callback: types.CallbackQuery):
    try: await callback.message.delete()
    except: pass
    await callback.answer()

@router.callback_query(F.data == "close_profile")
async def close_prof(callback: types.CallbackQuery):
    try: await callback.message.delete()
    except: pass
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

@router.message(F.text == "⬅️ Назад к экспорту")
async def back_to_export(message: types.Message):
    await export_calendar_menu(message)