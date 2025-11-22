from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import json
import asyncio
import csv
import io
from datetime import datetime, timedelta

try:
    import dateparser
except ImportError:
    dateparser = None

from utils.keyboards import *
from utils.states import AdminStates
from utils.ics_generator import IcsGenerator
from database import FDataBase

router = Router()

def check_access(source, db: FDataBase):
    try:
        user_id = source.from_user.id
        admin = db.get_admin(user_id)
        if admin and admin.get('is_active', True):
            return admin
        return None
    except Exception as e:
        return None

def check_callback_access(callback: types.CallbackQuery, db: FDataBase):
    admin = check_access(callback, db)
    if not admin:
        try:
            asyncio.create_task(callback.answer("⛔ У вас нет прав администратора.", show_alert=True))
        except:
            pass
        return None
    return admin

async def handle_cancel(message: types.Message, state: FSMContext, db: FDataBase, target_keyboard=None):
    await state.clear()
    admin = db.get_admin(message.from_user.id)
    if target_keyboard:
        await message.answer("❌ Действие отменено", reply_markup=target_keyboard)
    elif admin:
        await message.answer("❌ Действие отменено", reply_markup=get_admin_main_kb(admin.get('role')))
    else:
        await message.answer("❌ Действие отменено", reply_markup=get_main_keyboard(False))

def parse_date_safe(date_str):
    if not date_str:
        return datetime.now()
    if dateparser:
        try:
            dt = dateparser.parse(date_str, languages=['ru', 'en'], settings={'PREFER_DATES_FROM': 'future'})
            if dt:
                if dt < datetime.now() - timedelta(days=1):
                     try: dt = dt.replace(year=datetime.now().year + 1)
                     except: pass
                return dt
        except: pass
    return datetime.now()

@router.message(lambda msg: msg.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    
    role_display = "👔 Руководитель" if admin.get('role') == 'Manager' else "👑 ТехПоддержка" if admin.get('role') == 'TechSupport' else admin.get('role')
    
    await message.answer(
        f"🕵️‍♂️ <b>Панель управления</b>\n"
        f"👤 Роль: <b>{role_display}</b>\n"
        f"🆔 ID: <code>{admin.get('telegram_id')}</code>",
        reply_markup=get_admin_main_kb(admin.get('role')),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text == "⬅️ Назад в админку")
async def back_to_admin_handler_msg(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    await admin_panel(message, db)

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_handler_cb(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin:
        return
    await callback.message.delete()
    await callback.message.answer("⚙️ Админ-панель", reply_markup=get_admin_main_kb(admin.get('role')))

@router.message(lambda msg: msg.text == "⬅️ Главное меню")
async def back_to_main_menu(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    await message.answer(
        "🔙 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text == "🔔 Настройка уведомлений")
async def configure_notifications_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') != 'Manager':
        await message.answer("⛔ Доступ только для Руководителей.")
        return
        
    await state.set_state(AdminStates.waiting_for_notify_day)
    await message.answer(
        "🔔 <b>Настройка уведомлений</b>\n\n"
        "Как часто вы хотите получать напоминания о проверке заявок?",
        parse_mode="HTML",
        reply_markup=get_notification_day_keyboard()
    )

@router.message(AdminStates.waiting_for_notify_day)
async def process_notify_day(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db)
        return
        
    days_map = {
        "🔄 Каждый день": "every_day",
        "📅 Каждый месяц": "every_month",
        "Понедельник": "0", "Вторник": "1", "Среда": "2", "Четверг": "3",
        "Пятница": "4", "Суббота": "5", "Воскресенье": "6"
    }
    
    if message.text not in days_map:
        await message.answer("❌ Пожалуйста, выберите вариант из меню.")
        return
        
    await state.update_data(notify_day=days_map[message.text])
    await state.set_state(AdminStates.waiting_for_notify_time)
    await message.answer("🕒 Выберите время получения:", reply_markup=get_notification_time_keyboard())

@router.message(AdminStates.waiting_for_notify_time)
async def process_notify_time(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db)
        return
        
    if ":" not in message.text:
        await message.answer("❌ Выберите время из меню.")
        return
        
    data = await state.get_data()
    day_val = data['notify_day']
    
    db.update_admin_notification(message.from_user.id, day_val, message.text)
    
    label = message.text
    if day_val == 'every_day': label = f"Каждый день в {message.text}"
    elif day_val == 'every_month': label = f"1-го числа каждого месяца в {message.text}"
    else:
        d_names = ["Понедельникам", "Вторникам", "Средам", "Четвергам", "Пятницам", "Субботам", "Воскресеньям"]
        label = f"По {d_names[int(day_val)]} в {message.text}"
    
    await state.clear()
    await message.answer(
        f"✅ <b>Уведомления настроены!</b>\nЯ буду писать вам: <b>{label}</b>",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb('Manager')
    )

@router.message(lambda msg: msg.text == "📊 Статистика")
async def show_stats(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    
    stats = await asyncio.to_thread(db.get_stats)
    text = (
        "📊 <b>Статистика системы</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: <b>{stats.get('total_users', 0)}</b>\n"
        f"• Активных: <b>{stats.get('active_users', 0)}</b>\n\n"
        f"📅 <b>Мероприятия:</b>\n"
        f"• Опубл.: <b>{stats.get('approved_events', 0)}</b>\n"
        f"• На модерации: <b>{stats.get('pending_events', 0)}</b>\n\n"
        f"📝 <b>Регистрации:</b>\n"
        f"• Всего: <b>{stats.get('total_registrations', 0)}</b>\n"
        f"• Ожидают: <b>{stats.get('pending_registrations', 0)}</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "📋 Список мероприятий")
async def list_events_manager(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') != 'Manager':
        await message.answer("⛔ Доступ только для Руководителей.")
        return
    
    await show_manager_events_list_page(message, db, 0)

async def show_manager_events_list_page(message: types.Message, db: FDataBase, page: int):
    events = await asyncio.to_thread(db.get_all_events_paginated, page, 1)
    total = await asyncio.to_thread(db.get_total_events_count)
    
    if not events:
        await message.answer("📭 Мероприятий пока нет.")
        return

    event = events[0]
    
    try:
        analysis = json.loads(event['analysis']) if event.get('analysis') else {}
    except:
        analysis = {}
    
    status_icon = "✅" if event['status'] == 'approved' else "⏳" if event['status'] in ['new', 'pending'] else "❌"
    source_icon = "🤝" if event['source'] == 'partner' else "📂" if event['source'] == 'file' else "🤖"
    
    text = (
        f"📋 <b>Список мероприятий</b> ({page + 1}/{max(1, total)})\n\n"
        f"{status_icon} {source_icon} <b>{event['title']}</b>\n"
        f"📅 {event['date_str']}\n"
        f"📍 {event['location']}\n"
        f"🔗 {event['url'] or 'Нет ссылки'}\n"
        f"📊 Score: {event['score']} | Status: {event['status']}\n"
        f"💡 AI Summary: {analysis.get('summary', '-')}\n\n"
        f"📝 <b>Описание:</b>\n{event['description'][:300]}..."
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_manager_events_pagination_keyboard(events, page, max(1, total)))

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

@router.callback_query(F.data.startswith("manager_events_prev_"))
async def manager_events_prev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_manager_events_list_page(c.message, db, page)

@router.callback_query(F.data.startswith("manager_events_next_"))
async def manager_events_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_manager_events_list_page(c.message, db, page)

@router.callback_query(F.data.startswith("manager_event_details_"))
async def manager_event_details(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await show_manager_event_detail(c.message, db, int(c.data.split("_")[3]))

async def show_manager_event_detail(message, db, eid):
    e = db.get_event_by_id(eid)
    if not e: return
    text = f"📝 <b>{e['title']}</b>\nID: {eid}\n📅 {e['date_str']}\n📍 {e['location']}\n🔗 {e['url']}"
    kb = get_manager_event_detail_keyboard(eid)
    if isinstance(message, types.Message):
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.edit_text(text, parse_mode="HTML", reply_markup=kb)

def get_manager_event_detail_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Участники", callback_data=f"event_participants_{event_id}"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_manager_events")
        ],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
    ])

@router.callback_query(F.data == "back_to_manager_events")
async def back_to_manager_events(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await c.message.delete()
    await show_manager_events_list_page(c.message, db, 0)

@router.message(lambda msg: msg.text == "✅ Утвердить записи")
async def start_bulk_moderation(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    await show_pending_registrations_list(message, db, 0)

async def show_pending_registrations_list(message: types.Message, db: FDataBase, page: int):
    events_data = await asyncio.to_thread(db.get_events_with_pending_registrations, page, 5)
    total = await asyncio.to_thread(db.get_total_events_with_pending_regs)
    
    if not events_data:
        role = db.get_admin(message.from_user.id).get('role')
        await message.answer("✅ Нет мероприятий с ожидающими записями.", reply_markup=get_admin_main_kb(role))
        return
    
    text = "🛡 <b>УТВЕРЖДЕНИЕ ЗАПИСЕЙ</b>\n\n"
    
    for i, event in enumerate(events_data, page * 5 + 1):
        text += f"{i}. <b>{event['title']}</b>\n"
        text += f"   📅 {event['date_str']}\n"
        text += f"   👥 Ожидают: <b>{event['pending_count']} чел.</b>\n"
        text += f"   [ID: {event['id']}]\n\n"
    
    text += f"<i>Выберите мероприятие для просмотра деталей</i>"
    
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_pending_registrations_list_keyboard(events_data, page, max(1, (total + 4) // 5))
    )

def get_pending_registrations_list_keyboard(events: list, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    
    for event in events:
        buttons.append([
            InlineKeyboardButton(
                text=f"📋 {event['title'][:30]}... ({event['pending_count']})",
                callback_data=f"view_event_registrations_{event['id']}_0"
            )
        ])
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pending_list_prev_{current_page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперед", callback_data=f"pending_list_next_{current_page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="refresh_pending_list")])
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(F.data.startswith("view_event_registrations_"))
async def view_event_registrations(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    parts = c.data.split("_")
    event_id = int(parts[3])
    user_page = int(parts[4])
    
    await show_event_registrations_page(c.message, db, event_id, user_page)

async def show_event_registrations_page(message: types.Message, db: FDataBase, event_id: int, user_page: int):
    event = db.get_event_by_id(event_id)
    if not event:
        await message.answer("❌ Мероприятие не найдено.")
        return
    
    pending_regs = await asyncio.to_thread(db.get_pending_registrations_for_event, event_id)
    
    if not pending_regs:
        await message.answer("✅ На этом мероприятии нет ожидающих регистраций.")
        return
    
    users_per_page = 5
    total_pages = max(1, (len(pending_regs) + users_per_page - 1) // users_per_page)
    current_page = min(user_page, total_pages - 1)
    
    start_idx = current_page * users_per_page
    end_idx = start_idx + users_per_page
    current_users = pending_regs[start_idx:end_idx]
    
    text = f"🛡 <b>РЕГИСТРАЦИИ НА МЕРОПРИЯТИЕ</b>\n\n"
    text += f"📌 <b>{event['title']}</b>\n"
    text += f"📅 {event['date_str']}\n"
    text += f"📍 {event['location']}\n\n"
    text += f"<b>Ожидают подтверждения ({current_page + 1}/{total_pages}):</b>\n\n"
    
    for i, user in enumerate(current_users, start_idx + 1):
        text += f"{i}. <b>{user['user_name']}</b>\n"
        text += f"   💼 {user['user_position']}\n"
        text += f"   📧 {user.get('email', 'Не указан')}\n"
        text += f"   📞 {user.get('phone', 'Не указан')}\n\n"
    
    await message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_event_registrations_detail_keyboard(event_id, current_page, total_pages, len(pending_regs))
    )

def get_event_registrations_detail_keyboard(event_id: int, current_page: int, total_pages: int, total_users: int) -> InlineKeyboardMarkup:
    buttons = []
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"event_users_prev_{event_id}_{current_page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"event_users_next_{event_id}_{current_page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([
        InlineKeyboardButton(text="✅ ВСЕХ", callback_data=f"bulk_approve_{event_id}"),
        InlineKeyboardButton(text="❌ ВСЕХ", callback_data=f"bulk_reject_{event_id}")
    ])
    
    buttons.append([InlineKeyboardButton(text="📋 Список всех", callback_data=f"view_all_users_{event_id}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ К списку мероприятий", callback_data="back_to_pending_list_0")])
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(F.data.startswith("view_all_users_"))
async def view_all_users_list(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    event_id = int(c.data.split("_")[3])
    event = db.get_event_by_id(event_id)
    pending_regs = await asyncio.to_thread(db.get_pending_registrations_for_event, event_id)
    
    if not pending_regs:
        await c.answer("❌ Нет ожидающих регистраций")
        return
    
    text = f"📋 <b>ПОЛНЫЙ СПИСОК ОЖИДАЮЩИХ</b>\n\n"
    text += f"📌 <b>{event['title']}</b>\n"
    text += f"👥 Всего: {len(pending_regs)} чел.\n\n"
    
    for i, user in enumerate(pending_regs, 1):
        status_icon = "⏳"
        text += f"{i}. {status_icon} <b>{user['user_name']}</b>\n"
        text += f"   💼 {user['user_position']}\n"
        text += f"   📧 {user.get('email', 'Не указан')}\n"
        text += f"   📞 {user.get('phone', 'Не указан')}\n\n"
    
    buttons = []
    for i, user in enumerate(pending_regs[:10]):
        buttons.append([
            InlineKeyboardButton(
                text=f"✅ {user['user_name'][:15]}...",
                callback_data=f"approve_single_{user['user_id']}_{event_id}"
            ),
            InlineKeyboardButton(
                text=f"❌ {user['user_name'][:15]}...", 
                callback_data=f"reject_single_{user['user_id']}_{event_id}"
            )
        ])
    
    if len(pending_regs) > 10:
        buttons.append([InlineKeyboardButton(text="📄 Еще пользователи...", callback_data=f"view_event_registrations_{event_id}_0")])
    
    buttons.append([
        InlineKeyboardButton(text="✅ ВСЕХ", callback_data=f"bulk_approve_{event_id}"),
        InlineKeyboardButton(text="❌ ВСЕХ", callback_data=f"bulk_reject_{event_id}")
    ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"view_event_registrations_{event_id}_0")])
    
    await c.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("approve_single_"))
async def approve_single_user(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    parts = c.data.split("_")
    user_id = int(parts[2])
    event_id = int(parts[3])
    
    if db.approve_registration(user_id, event_id):
        user = db.get_user_by_id(user_id)
        event = db.get_event_by_id(event_id)
        
        if user and event:
            try:
                ics_content = await asyncio.to_thread(
                    IcsGenerator.generate_ics, 
                    event['title'], 
                    event['description'] or "Описание отсутствует",
                    event['location'] or "Онлайн/Не указано",
                    event['date_str']
                )
                file_name = f"invite_{event['id']}.ics"
                file = BufferedInputFile(ics_content.encode('utf-8'), filename=file_name)
                
                await c.bot.send_document(
                    user['telegram_id'],
                    document=file,
                    caption=(
                        f"✅ <b>Ваша регистрация подтверждена администратором!</b>\n\n"
                        f"🎯 <b>{event['title']}</b>\n"
                        f"📅 {event['date_str']}\n\n"
                        f"Файл для календаря прикреплен 📎"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Ошибка отправки ICS пользователю {user['telegram_id']}: {e}")

        await c.answer(f"✅ {user['full_name']} подтвержден и уведомлен")
        await update_registrations_view(c, db, event_id)
    else:
        await c.answer("❌ Ошибка подтверждения")

@router.callback_query(F.data.startswith("reject_single_"))
async def reject_single_user(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    parts = c.data.split("_")
    user_id = int(parts[2])
    event_id = int(parts[3])
    
    if db.reject_registration(user_id, event_id):
        user = db.get_user_by_id(user_id)
        event = db.get_event_by_id(event_id)
        
        if user and event:
            try:
                await c.bot.send_message(
                    user['telegram_id'],
                    f"❌ <b>Ваша регистрация отклонена</b>\n\n🎯 <b>{event['title']}</b>",
                    parse_mode="HTML"
                )
            except: pass
        
        await c.answer(f"❌ {user['full_name']} отклонен")
        
        await update_registrations_view(c, db, event_id)
    else:
        await c.answer("❌ Ошибка отклонения")

async def update_registrations_view(c: types.CallbackQuery, db: FDataBase, event_id: int):
    pending_regs = await asyncio.to_thread(db.get_pending_registrations_for_event, event_id)
    
    if not pending_regs:
        await c.message.edit_text(
            "✅ <b>Все регистрации на этом мероприятии обработаны!</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 К списку мероприятий", callback_data="back_to_pending_list_0")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
            ])
        )
        return
    
    event = db.get_event_by_id(event_id)
    await show_event_registrations_page(c.message, db, event_id, 0)

@router.callback_query(F.data.startswith("event_users_prev_"))
async def event_users_prev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    parts = c.data.split("_")
    event_id = int(parts[3])
    page = int(parts[4])
    
    await show_event_registrations_page(c.message, db, event_id, page)

@router.callback_query(F.data.startswith("event_users_next_"))
async def event_users_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    parts = c.data.split("_")
    event_id = int(parts[3])
    page = int(parts[4])
    
    await show_event_registrations_page(c.message, db, event_id, page)

@router.callback_query(F.data.startswith("pending_list_prev_"))
async def pending_list_prev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_pending_registrations_list(c.message, db, page)

@router.callback_query(F.data.startswith("pending_list_next_"))
async def pending_list_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_pending_registrations_list(c.message, db, page)

@router.callback_query(F.data == "refresh_pending_list")
async def refresh_pending_list(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    await c.message.delete()
    await show_pending_registrations_list(c.message, db, 0)

@router.callback_query(F.data.startswith("back_to_pending_list_"))
async def back_to_pending_list(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_pending_registrations_list(c.message, db, page)

@router.callback_query(F.data.startswith("bulk_approve_"))
async def bulk_approve_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    event_id = int(c.data.split("_")[2])

    approved_users = await asyncio.to_thread(db.approve_all_event_registrations, event_id)
    
    await c.answer(f"✅ Утверждено записей: {len(approved_users)}")
    
    if approved_users:
        event = db.get_event_by_id(event_id)
        if event:
            try:
                ics_content = await asyncio.to_thread(
                    IcsGenerator.generate_ics, 
                    event['title'], 
                    event['description'] or "",
                    event['location'] or "",
                    event['date_str']
                )
                file_name = f"invite_{event['id']}.ics"
                
                for u in approved_users:
                    try:
                        file = BufferedInputFile(ics_content.encode('utf-8'), filename=file_name)
                        
                        await c.bot.send_document(
                            u['telegram_id'],
                            document=file,
                            caption=f"✅ <b>Ваша заявка подтверждена!</b>\n\n🎯 <b>{event['title']}</b>",
                            parse_mode="HTML"
                        )
                        await asyncio.sleep(0.1) 
                    except Exception as e:
                        print(f"Не удалось отправить файл юзеру {u.get('telegram_id')}: {e}")
            except Exception as e:
                print(f"Ошибка генерации ICS для рассылки: {e}")
        
    await c.message.delete()
    await show_pending_registrations_list(c.message, db, 0)

@router.callback_query(F.data.startswith("bulk_reject_"))
async def bulk_reject_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    
    event_id = int(c.data.split("_")[2])
    rejected_users = await asyncio.to_thread(db.reject_all_event_registrations, event_id)
    await c.answer(f"❌ Отклонено записей: {len(rejected_users)}")
    
    for u in rejected_users:
        try:
            event = db.get_event_by_id(event_id)
            if event:
                await c.bot.send_message(
                    u['telegram_id'], 
                    f"❌ <b>Ваша запись отклонена руководителем</b>\n\n🎯 <b>{event['title']}</b>", 
                    parse_mode="HTML"
                )
        except: pass

    await c.message.delete()
    await show_pending_registrations_list(c.message, db, 0)

@router.message(lambda msg: msg.text == "🌐 Источники парсинга")
async def manage_sources_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("🌐 <b>Управление источниками</b>", reply_markup=get_sources_mgmt_kb(), parse_mode="HTML")

@router.message(lambda msg: msg.text == "➕ Добавить источник")
async def add_source_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await state.set_state(AdminStates.waiting_for_source_name)
    await message.answer("Введите название источника:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_source_name)
async def add_source_name(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_sources_mgmt_kb())
        return
    await state.update_data(source_name=message.text)
    await state.set_state(AdminStates.waiting_for_source_url)
    await message.answer("Введите URL (страницу с событиями):")

@router.message(AdminStates.waiting_for_source_url)
async def add_source_url(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_sources_mgmt_kb())
        return
    
    data = await state.get_data()
    from urllib.parse import urlparse
    parsed = urlparse(message.text)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    if db.add_source(data['source_name'], message.text, base_url):
        await message.answer("✅ Источник добавлен!", reply_markup=get_sources_mgmt_kb())
    else:
        await message.answer("❌ Ошибка (возможно, URL уже есть)", reply_markup=get_sources_mgmt_kb())
    await state.clear()

@router.message(lambda msg: msg.text == "📋 Список источников")
async def list_sources(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    sources = db.get_active_sources()
    text = "🌐 <b>Активные источники:</b>\n\n"
    for s in sources:
        text += f"ID: {s['id']} | <b>{s['name']}</b>\n🔗 {s['url']}\n\n"
    await message.answer(text, parse_mode="HTML", reply_markup=get_sources_mgmt_kb())

@router.message(lambda msg: msg.text == "➖ Удалить источник")
async def delete_source_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await state.set_state(AdminStates.waiting_for_delete_source_id)
    await message.answer("Введите ID источника для удаления:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_delete_source_id)
async def delete_source_process(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_sources_mgmt_kb())
        return
    if not message.text.isdigit():
        await message.answer("❌ ID должен быть числом")
        return
        
    if db.delete_source(int(message.text)):
        await message.answer("✅ Удалено", reply_markup=get_sources_mgmt_kb())
    else:
        await message.answer("❌ Не найдено", reply_markup=get_sources_mgmt_kb())
    await state.clear()

@router.message(lambda msg: msg.text == "🔄 Сканировать источники")
async def scan_sources_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ У вас нет прав на сканирование.")
        return
    await state.set_state(AdminStates.waiting_for_parsing_criteria)
    await message.answer(
        "🔍 <b>Настройка парсинга</b>\nВыберите темы для поиска:",
        parse_mode="HTML", 
        reply_markup=get_parsing_filters_keyboard()
    )

@router.message(AdminStates.waiting_for_parsing_criteria)
async def scan_sources_process(message: types.Message, state: FSMContext, db: FDataBase, parser, gigachat):
    admin = check_access(message, db)
    if not admin: return
    
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_admin_main_kb(admin['role']))
        return

    parsing_filters = {
        "🎯 IT-тематика": ["IT", "разработка", "программирование", "software"],
        "🤖 AI/ML": ["AI", "искусственный интеллект", "ML", "machine learning", "нейросеть"],
        "📊 Data Science": ["data science", "анализ данных", "big data", "data analysis"],
        "☁️ Cloud/DevOps": ["cloud", "облако", "devops", "aws", "azure", "gcp"],
        "🔐 Кибербезопасность": ["кибербезопасность", "cybersecurity", "security", "безопасность"],
        "💼 Менеджмент": ["менеджмент", "управление", "project management", "руководство"],
        "📍 Санкт-Петербург": ["санкт-петербург", "спб", "петербург"],
        "🌐 Онлайн": ["онлайн", "online", "webinar"],
        "🎓 Образовательные": ["образование", "обучение", "курс", "семинар"],
        "👨‍💻 Технические": ["технический", "technical", "engineering"],
        "🔍 Все темы": []
    }
    
    if message.text not in parsing_filters:
        await message.answer("❌ Пожалуйста, выберите тему из меню.")
        return
    
    criteria = parsing_filters[message.text]
    
    await state.clear()
    criteria_text = message.text if message.text == "🔍 Все темы" else ", ".join(criteria)
    status_msg = await message.answer(f"⏳ <b>Сканирование...</b>\nТема: {criteria_text}", parse_mode="HTML")
    
    try:
        db_sources = await asyncio.to_thread(db.get_active_sources)
        raw_events = await asyncio.to_thread(parser.get_events, db_sources, criteria)
        
        if not raw_events:
            await status_msg.edit_text("❌ Событий не найдено.")
            return
            
        await status_msg.edit_text(f"🔍 Найдено {len(raw_events)}. Анализ AI...", parse_mode="HTML")
        
        added_count = 0
        for raw_event in raw_events:
            if db.check_event_exists_by_url(raw_event.get('url')): continue
            
            analysis = await asyncio.to_thread(gigachat.analyze_event, raw_event.get('text', ''), criteria)
            dt_obj = parse_date_safe(analysis.get('date', ''))
            dt_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            priority = analysis.get('priority', 'medium')

            db.add_new_event(
                title=analysis.get('title', 'Без названия'),
                description=raw_event.get('text', ''),
                location=analysis.get('location', 'СПб'),
                date_str=analysis.get('date', 'Не указана'),
                url=raw_event.get('url', ''),
                analysis=json.dumps(analysis, ensure_ascii=False),
                score=analysis.get('score', 0),
                priority=priority,
                required_rank=1,
                event_datetime=dt_str,
                status='new',
                source='parser'
            )
            added_count += 1
                
        await status_msg.edit_text(f"✅ <b>Готово!</b> Добавлено: {added_count}", parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")

@router.message(lambda msg: msg.text == "📝 Управление мероприятиями")
async def manage_events_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    
    await message.answer("📝 <b>Меню мероприятий</b>", reply_markup=get_events_mgmt_kb(admin.get('role')), parse_mode="HTML")

@router.message(lambda msg: msg.text == "📂 Экспорт всех (CSV)")
async def export_all_events_handler(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    
    events = await asyncio.to_thread(db.get_all_events_for_export)
    if not events:
        await message.answer("Нет событий для экспорта.")
        return
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Date', 'Location', 'URL', 'Status', 'Source'])
    
    for e in events:
        writer.writerow([e['id'], e['title'], e['date_str'], e['location'], e['url'], e['status'], e['source']])
        
    file = BufferedInputFile(output.getvalue().encode('utf-8'), filename="all_events.csv")
    await message.answer_document(file, caption=f"✅ Экспорт {len(events)} событий")

@router.message(lambda msg: msg.text == "👥 Управление пользователями")
async def manage_users_menu_tech(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("👥 <b>Меню пользователей</b>", reply_markup=get_users_mgmt_kb(), parse_mode="HTML")

@router.message(lambda msg: msg.text == "👤 Управление админами")
async def admin_admins_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("👤 <b>Управление админами</b>", reply_markup=get_admin_management_keyboard(), parse_mode="HTML")

@router.message(lambda msg: msg.text == "🤝 Добавить партнёрское")
async def add_partner_event_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await state.set_state(AdminStates.waiting_for_event_title)
    await state.update_data(event_source='partner')
    await message.answer("🤝 <b>Новое партнёрское событие</b>\nВведите название:", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(lambda msg: msg.text == "➕ Создать событие")
async def create_event_manual_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await state.set_state(AdminStates.waiting_for_event_title)
    await state.update_data(event_source='manual')
    await message.answer("📝 <b>Новое событие</b>\nВведите название:", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_event_title)
async def process_event_title(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_title=message.text)
    await state.set_state(AdminStates.waiting_for_event_description)
    await message.answer("📝 Описание:")

@router.message(AdminStates.waiting_for_event_description)
async def process_event_desc(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_description=message.text)
    await state.set_state(AdminStates.waiting_for_event_location)
    await message.answer("📍 Место проведения:")

@router.message(AdminStates.waiting_for_event_location)
async def process_event_loc(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_location=message.text)
    await state.set_state(AdminStates.waiting_for_event_date)
    await message.answer("📅 Дата (текстом, напр. '25 декабря'):")

@router.message(AdminStates.waiting_for_event_date)
async def process_event_date(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_date=message.text)
    await state.set_state(AdminStates.waiting_for_event_url)
    await message.answer("🔗 Ссылка (или '-'):")

@router.message(AdminStates.waiting_for_event_url)
async def process_event_url_finish(message: types.Message, state: FSMContext, db: FDataBase, gigachat):
    admin = check_access(message, db)
    if not admin: return

    data = await state.get_data()
    source = data.get('event_source', 'manual')
    url_val = message.text if message.text != '-' else ''
    
    wait_msg = await message.answer(f"⏳ <b>Сохранение ({source})...</b>\nАнализ через AI...", parse_mode="HTML")
    
    text_for_analysis = f"{data['event_title']}. {data['event_description']}"
    analysis = await asyncio.to_thread(gigachat.analyze_event, text_for_analysis)
    
    dt_obj = parse_date_safe(data['event_date'])
    dt_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    
    db.add_new_event(
        title=data['event_title'],
        description=data['event_description'],
        location=data['event_location'],
        date_str=data['event_date'],
        url=url_val,
        analysis=json.dumps(analysis, ensure_ascii=False),
        score=analysis.get('score', 50),
        priority='high' if source == 'partner' else analysis.get('priority', 'medium'),
        required_rank=1,
        event_datetime=dt_str,
        status='approved', 
        source=source 
    )
    
    await state.clear()
    await wait_msg.delete()
    await message.answer(f"✅ Событие ({source}) успешно добавлено и одобрено!", reply_markup=get_events_mgmt_kb())

@router.message(lambda msg: msg.text == "📂 Загрузить из файла")
async def upload_file_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await state.set_state(AdminStates.waiting_for_file)
    await message.answer("📂 <b>Отправьте файл</b> (.txt, .json)", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_file)
async def process_file_upload(message: types.Message, state: FSMContext, db: FDataBase, gigachat: any, bot: Bot):
    admin = check_access(message, db)
    if not admin: return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    if not message.document:
        await message.answer("❌ Прикрепите файл.")
        return

    wait_msg = await message.answer("⏳ Анализирую файл...")
    try:
        file_info = await bot.get_file(message.document.file_id)
        downloaded = await bot.download_file(file_info.file_path)
        content = downloaded.read().decode('utf-8', errors='ignore')
        events_data = await asyncio.to_thread(gigachat.analyze_file_content, content)
        
        count = 0
        for ev in events_data:
            dt_obj = parse_date_safe(ev.get('date', ''))
            db.add_new_event(
                title=ev.get('title', 'Без названия'),
                description=ev.get('description', ''),
                location=ev.get('location', 'Не указано'),
                date_str=ev.get('date', 'Не указана'),
                url='',
                analysis=json.dumps(ev, ensure_ascii=False),
                score=50,
                priority='medium',
                required_rank=1,
                event_datetime=dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
                status='pending',
                source='file'
            )
            count += 1
        await state.clear()
        await wait_msg.delete()
        await message.answer(f"✅ Загружено черновиков: <b>{count}</b>", parse_mode="HTML", reply_markup=get_events_mgmt_kb())
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=get_events_mgmt_kb())

@router.message(lambda msg: msg.text == "📋 Список всех")
async def list_all_events(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await show_admin_events_list_page(message, db, 0)

async def show_admin_events_list_page(message: types.Message, db: FDataBase, page: int):
    events = await asyncio.to_thread(db.get_all_events_paginated, page, 1)
    total = await asyncio.to_thread(db.get_total_events_count)
    
    if not events:
        await message.answer("📭 Мероприятий пока нет.")
        return

    event = events[0]
    
    try:
        analysis = json.loads(event['analysis']) if event.get('analysis') else {}
    except:
        analysis = {}
    
    status_icon = "✅" if event['status'] == 'approved' else "⏳" if event['status'] in ['new', 'pending'] else "❌"
    source_icon = "🤝" if event['source'] == 'partner' else "📂" if event['source'] == 'file' else "🤖"
    
    text = (
        f"📋 <b>Все мероприятия</b> ({page + 1}/{max(1, total)})\n\n"
        f"{status_icon} {source_icon} <b>{event['title']}</b>\n"
        f"📅 {event['date_str']}\n"
        f"📍 {event['location']}\n"
        f"🔗 {event['url'] or 'Нет ссылки'}\n"
        f"📊 Score: {event['score']} | Status: {event['status']}\n"
        f"💡 AI Summary: {analysis.get('summary', '-')}\n\n"
        f"📝 <b>Описание:</b>\n{event['description'][:300]}..."
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_events_pagination_keyboard(events, page, max(1, total)))

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

@router.callback_query(F.data.startswith("admin_events_prev_"))
async def admin_events_prev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_admin_events_list_page(c.message, db, page)

@router.callback_query(F.data.startswith("admin_events_next_"))
async def admin_events_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_admin_events_list_page(c.message, db, page)

@router.message(lambda msg: msg.text == "🔍 Поиск (Админ)")
async def admin_search_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_search_text)
    await message.answer(
        "🔍 <b>Выберите фильтры для поиска по базе:</b>\n"
        "Можно выбрать несколько фильтров по очереди",
        parse_mode="HTML",
        reply_markup=get_admin_search_filters_keyboard()
    )

@router.message(AdminStates.waiting_for_search_text)
async def admin_search_process(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить поиск":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    
    filter_map = {
        "🎯 IT-тематика": ["IT", "разработка", "программирование"],
        "🤖 AI/ML": ["AI", "искусственный интеллект", "ML", "machine learning"],
        "📊 Data Science": ["data science", "анализ данных", "big data"],
        "☁️ Cloud/DevOps": ["cloud", "облако", "devops", "aws", "azure"],
        "🔐 Кибербезопасность": ["кибербезопасность", "cybersecurity", "security"],
        "💼 Менеджмент": ["менеджмент", "управление", "project management"],
        "📍 Санкт-Петербург": ["санкт-петербург", "спб", "петербург"],
        "🌐 Онлайн": ["онлайн", "online", "webinar"],
        "✅ Одобренные": ["approved"],
        "⏳ На модерации": ["pending", "new"],
        "🤝 Партнёрские": ["partner"],
        "📂 Из файла": ["file"],
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
            reply_markup=get_admin_search_filters_keyboard()
        )
    else:
        await message.answer(
            "🔍 <b>Поиск по всем мероприятиям</b>\n"
            "Выберите фильтры для уточнения поиска",
            parse_mode="HTML",
            reply_markup=get_admin_search_filters_keyboard()
        )
    
    if current_filters and message.text != "🔍 Все мероприятия":
        await perform_admin_smart_search(message, state, db, current_filters)

async def perform_admin_smart_search(message: types.Message, state: FSMContext, db: FDataBase, filters: list):
    wait_msg = await message.answer("⏳ <b>Ищу мероприятия...</b>", parse_mode="HTML")
    
    try:
        keywords = []
        status_filter = None
        source_filter = None
        
        for filter_type in filters:
            if filter_type in ["approved", "pending", "new"]:
                status_filter = filter_type
            elif filter_type in ["partner", "file", "parser"]:
                source_filter = filter_type
            else:
                keywords.append(filter_type)
        
        results = await asyncio.to_thread(db.search_admin_events_with_filters, 
                                        keywords, 
                                        status_filter, 
                                        source_filter,
                                        20)
        
        await state.clear()
        await wait_msg.delete()
        
        if not results:
            await message.answer(
                "🔍 <b>Ничего не найдено</b>", 
                parse_mode="HTML", 
                reply_markup=get_events_mgmt_kb()
            )
            return
            
        text = "🔍 <b>Результаты поиска:</b>\n\n"
        for res in results:
            status_icon = "✅" if res['status'] == 'approved' else "⏳"
            source_icon = "🤝" if res['source'] == 'partner' else "📂" if res['source'] == 'file' else "🤖"
            text += f"{status_icon}{source_icon} <b>{res['title']}</b>\nID: /admin_event_details_{res['id']}\n\n"
        
        await message.answer(text, parse_mode="HTML", reply_markup=get_events_mgmt_kb())
        
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ Ошибка при поиске: {str(e)}")

@router.message(lambda msg: msg.text and msg.text.startswith("/admin_event_details_"))
async def admin_det_cmd(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    try: eid = int(message.text.split("_")[3])
    except: return
    await show_admin_detail(message, db, eid)

@router.callback_query(F.data.startswith("admin_event_details_"))
async def admin_det_cb(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await show_admin_detail(c.message, db, int(c.data.split("_")[3]))

async def show_admin_detail(message, db, eid):
    e = db.get_event_by_id(eid)
    if not e: return
    text = f"📝 <b>{e['title']}</b>\nID: {eid}\n📅 {e['date_str']}\n📍 {e['location']}\n🔗 {e['url']}"
    kb = get_event_edit_keyboard(eid)
    if isinstance(message, types.Message):
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("edit_event_title_"))
async def edit_t(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await state.update_data(editing_eid=int(c.data.split("_")[3]))
    await state.set_state(AdminStates.waiting_for_edit_event_title)
    await c.message.answer("Новое название:", reply_markup=get_cancel_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_event_title)
async def edit_t_fin(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    d = await state.get_data()
    db.update_event(d['editing_eid'], title=m.text)
    await m.answer("✅ Обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_desc_"))
async def edit_d(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await state.update_data(editing_eid=int(c.data.split("_")[3]))
    await state.set_state(AdminStates.waiting_for_edit_event_desc)
    await c.message.answer("Новое описание:", reply_markup=get_cancel_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_event_desc)
async def edit_d_fin(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    d = await state.get_data()
    db.update_event(d['editing_eid'], description=m.text)
    await m.answer("✅ Обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_location_"))
async def edit_l(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await state.update_data(editing_eid=int(c.data.split("_")[3]))
    await state.set_state(AdminStates.waiting_for_edit_event_location)
    await c.message.answer("Новое место:", reply_markup=get_cancel_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_event_location)
async def edit_l_fin(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    d = await state.get_data()
    db.update_event(d['editing_eid'], location=m.text)
    await m.answer("✅ Обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_date_"))
async def edit_dt(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await state.update_data(editing_eid=int(c.data.split("_")[3]))
    await state.set_state(AdminStates.waiting_for_edit_event_date)
    await c.message.answer("Новая дата:", reply_markup=get_cancel_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_event_date)
async def edit_dt_fin(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    d = await state.get_data()
    dt_obj = parse_date_safe(m.text)
    db.update_event(d['editing_eid'], date_str=m.text, event_datetime=dt_obj.strftime('%Y-%m-%d %H:%M:%S'))
    await m.answer("✅ Обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_url_"))
async def edit_u(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await state.update_data(editing_eid=int(c.data.split("_")[3]))
    await state.set_state(AdminStates.waiting_for_edit_event_url)
    await c.message.answer("Новая ссылка:", reply_markup=get_cancel_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_event_url)
async def edit_u_fin(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    d = await state.get_data()
    db.update_event(d['editing_eid'], url=m.text)
    await m.answer("✅ Обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("delete_event_confirm_"))
async def del_ev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    db.delete_event(int(c.data.split("_")[3]))
    await c.answer("🗑 Удалено")
    await c.message.delete()

@router.callback_query(F.data.startswith("back_to_event_"))
async def back_to_event(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    await admin_det_cb(c, db)

@router.callback_query(F.data.startswith("event_participants_"))
async def show_participants(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    eid = int(c.data.split("_")[2])
    await show_participants_page(c.message, db, eid, 0)
    await c.answer()

async def show_participants_page(message: types.Message, db: FDataBase, eid: int, page: int):
    regs = db.get_event_registrations(eid)
    event = db.get_event_by_id(eid)
    chunk = regs[page*5:(page+1)*5]
    total_pages = max(1, (len(regs) + 4) // 5)
    text = f"👥 <b>Участники: {event['title']}</b>\nВсего: {len(regs)}\n\n"
    for i, r in enumerate(chunk, page*5+1):
        status_icon = "✅" if r['status'] == 'approved' else "⏳"
        text += f"{i}. {status_icon} {r['full_name']} ({r['position']})\n"
    await message.edit_text(text, parse_mode="HTML", reply_markup=get_participants_keyboard(eid, page, total_pages))

@router.callback_query(F.data.startswith("part_prev_"))
async def part_prev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    p = c.data.split("_")
    await show_participants_page(c.message, db, int(p[2]), int(p[3]))

@router.callback_query(F.data.startswith("part_next_"))
async def part_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    p = c.data.split("_")
    await show_participants_page(c.message, db, int(p[2]), int(p[3]))

@router.callback_query(F.data.startswith("export_participants_"))
async def export_participants_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin: return
    eid = int(callback.data.split("_")[2])
    regs = db.get_event_registrations(eid)
    event = db.get_event_by_id(eid)
    if not regs:
        await callback.answer("Нет участников для экспорта")
        return
    file_content = f"Участники: {event['title']}\nДата: {event['date_str']}\n\n"
    for i, r in enumerate(regs, 1):
        file_content += f"{i}. {r['full_name']} | {r['position']} | {r['status']}\n"
    file_name = f"participants_{eid}.txt"
    file = BufferedInputFile(file_content.encode('utf-8'), filename=file_name)
    await callback.message.answer_document(file, caption="📊 Список участников")
    await callback.answer()

@router.message(lambda msg: msg.text == "📝 Управление ролями")
async def manage_roles_start(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ Доступ запрещен.")
        return
    users = await asyncio.to_thread(db.get_all_approved_users)
    if not users:
        await message.answer("📭 Нет подтвержденных сотрудников.")
        return
    text = "📝 <b>Управление ролями сотрудников:</b>\n\n"
    for user in users[:10]:
        rank = db._get_position_rank(user['position'])
        text += f"👤 <b>{user['full_name']}</b>\n💼 {user['position']} (ранг: {rank})\n🆔 ID: {user['telegram_id']}\n\n"
    await message.answer(text, parse_mode="HTML", reply_markup=get_role_management_keyboard(users))

@router.callback_query(F.data.startswith("change_user_role_"))
async def change_user_role_handler(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    user_id = int(c.data.split("_")[3])
    user = db.get_user_by_id(user_id)
    if not user:
        await c.answer("❌ Пользователь не найден")
        return
    await state.update_data(editing_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_new_user_role)
    await c.message.answer(
        f"📝 <b>Изменение роли для {user['full_name']}</b>\n"
        f"Текущая должность: {user['position']}\n"
        "Выберите новую должность:",
        parse_mode="HTML",
        reply_markup=get_position_keyboard()
    )
    await c.answer()

@router.message(AdminStates.waiting_for_new_user_role)
async def process_new_user_role(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_users_mgmt_kb())
        return
    data = await state.get_data()
    user_id = data['editing_user_id']
    if db.update_user_profile(user_id, position=message.text):
        await message.answer(f"✅ Должность обновлена на: {message.text}", reply_markup=get_users_mgmt_kb())
    else:
        await message.answer("❌ Ошибка обновления должности", reply_markup=get_users_mgmt_kb())
    await state.clear()

@router.message(lambda msg: msg.text == "✅ Подтверждение (Модерация)")
async def show_user_approvals(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ Доступ запрещен.")
        return
    await show_user_approval_page(message, db, 0)

async def show_user_approval_page(message: types.Message, db: FDataBase, page: int):
    users = await asyncio.to_thread(db.get_pending_users_paginated, page, 1)
    total = await asyncio.to_thread(db.get_total_pending_users_count)
    if not users:
        await message.answer("✅ Нет активных заявок на регистрацию.", reply_markup=get_users_mgmt_kb())
        return
    user = users[0]
    text = (
        f"👤 <b>ЗАЯВКА #{user['id']}</b> ({page+1}/{max(1, total)})\n\n"
        f"👤 ФИО: <b>{user.get('full_name')}</b>\n"
        f"💼 Должность: {user.get('position')}\n"
        f"📧 Email: {user.get('email')}\n"
        f"📞 Тел: {user.get('phone')}\n"
        f"📅 Дата: {user.get('registered_at')}\n"
    )
    kb = get_user_approval_pagination_keyboard(users, page, max(1, total))
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("approve_user_"))
async def approve_user_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    uid = int(c.data.split("_")[2])
    user = db.get_user_by_id(uid)
    if db.approve_user(uid):
        await c.answer("✅ Пользователь подтвержден")
        if user:
            try:
                await c.bot.send_message(
                    user['telegram_id'],
                    "✅ <b>Ваш аккаунт подтвержден!</b>\nДоступ к функциям бота открыт.",
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard(False)
                )
            except: pass
    else:
        await c.answer("❌ Ошибка")
    await c.message.delete()
    await show_user_approval_page(c.message, db, 0)

@router.callback_query(F.data.startswith("reject_user_"))
async def reject_user_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    db.reject_user(int(c.data.split("_")[2]))
    await c.answer("❌ Заявка отклонена")
    await c.message.delete()
    await show_user_approval_page(c.message, db, 0)

@router.callback_query(F.data.startswith("user_approval_next_"))
async def user_approval_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_user_approval_page(c.message, db, page)

@router.callback_query(F.data.startswith("user_approval_prev_"))
async def user_approval_prev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_user_approval_page(c.message, db, page)

@router.message(lambda msg: msg.text == "📝 Модерация регистраций")
async def show_registration_moderation(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ Доступ запрещен.")
        return
    await show_reg_moderation_page(message, db, 0)

async def show_reg_moderation_page(message: types.Message, db: FDataBase, page: int):
    registrations = await asyncio.to_thread(db.get_pending_registrations)
    if not registrations:
        await message.answer("✅ Нет заявок на регистрацию для модерации.", reply_markup=get_users_mgmt_kb())
        return
    total = len(registrations)
    if page >= total: page = 0
    reg = registrations[page]
    text = (
        f"📝 <b>МОДЕРАЦИЯ РЕГИСТРАЦИЙ</b> ({page+1}/{total})\n\n"
        f"👤 <b>Сотрудник:</b> {reg['user_name']}\n"
        f"💼 <b>Должность:</b> {reg['user_position']}\n"
        f"📅 <b>Мероприятие:</b> {reg['event_title']}\n"
        f"🗓 <b>Дата:</b> {reg['date_str']}\n"
        f"🔗 <b>Ссылка:</b> {reg['url'] or 'Нет'}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_reg_moderation_keyboard(reg['user_id'], reg['event_id'], page, total))

@router.callback_query(F.data.startswith("reg_approve_"))
async def reg_approve_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin: return
    
    parts = callback.data.split("_")
    user_id = int(parts[2])
    event_id = int(parts[3])
    
    if db.approve_registration(user_id, event_id):
        user = db.get_user_by_id(user_id)
        event = db.get_event_by_id(event_id)
        
        if user and event:
            try:
                ics_content = await asyncio.to_thread(
                    IcsGenerator.generate_ics, 
                    event['title'], 
                    event['description'] or "Описание отсутствует",
                    event['location'] or "Онлайн/Не указано",
                    event['date_str']
                )
                file_name = f"invite_{event['id']}.ics"
                file = BufferedInputFile(ics_content.encode('utf-8'), filename=file_name)
                
                await callback.bot.send_document(
                    user.get('telegram_id'),
                    document=file,
                    caption=(
                        f"✅ <b>Руководитель подтвердил вашу заявку!</b>\n\n"
                        f"🎯 <b>{event.get('title')}</b>\n"
                        f"📅 {event.get('date_str')}\n\n"
                        f"Добавьте событие в календарь 👇"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Ошибка отправки ICS: {e}")

        await callback.answer("✅ Регистрация подтверждена")
    else:
        await callback.answer("❌ Ошибка базы данных")
        
    await callback.message.delete()
    await show_reg_moderation_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("reg_reject_"))
async def reg_reject_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin: return
    parts = callback.data.split("_")
    user_id = int(parts[2])
    event_id = int(parts[3])
    if db.reject_registration(user_id, event_id):
        user = db.get_user_by_id(user_id)
        event = db.get_event_by_id(event_id)
        if user and event:
            try:
                await callback.bot.send_message(
                    user.get('telegram_id'),
                    f"❌ <b>Регистрация отклонена</b>\n\n🎯 <b>{event.get('title')}</b>",
                    parse_mode="HTML"
                )
            except: pass
        await callback.answer("❌ Регистрация отклонена")
    else:
        await callback.answer("❌ Ошибка")
    await callback.message.delete()
    await show_reg_moderation_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("reg_next_"))
async def reg_next_handler(callback: types.CallbackQuery, db: FDataBase):
    if check_callback_access(callback, db):
        await callback.message.delete()
        await show_reg_moderation_page(callback.message, db, int(callback.data.split("_")[2]))

@router.callback_query(F.data.startswith("reg_prev_"))
async def reg_prev_handler(callback: types.CallbackQuery, db: FDataBase):
    if check_callback_access(callback, db):
        await callback.message.delete()
        await show_reg_moderation_page(callback.message, db, int(callback.data.split("_")[2]))

@router.message(lambda msg: msg.text == "📜 Модерация")
async def start_moderation(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') == 'Manager':
        await message.answer("⛔ Доступ запрещен.")
        return
    await show_moderation_page(message, db, 0)

async def show_moderation_page(message: types.Message, db: FDataBase, page: int):
    events = await asyncio.to_thread(db.get_pending_events_paginated, page, 1)
    total = await asyncio.to_thread(db.get_total_pending_events_count)
    if not events:
        await message.answer("🎉 <b>Все события проверены!</b>", parse_mode="HTML", reply_markup=get_events_mgmt_kb())
        return
    e = events[0]
    an = json.loads(e['analysis'] or '{}')
    text = (
        f"🛡 <b>МОДЕРАЦИЯ</b> ({page+1}/{max(1, total)})\n\n"
        f"📌 <b>{e.get('title')}</b>\n"
        f"📅 {e.get('date_str')}\n"
        f"📍 {e.get('location')}\n"
        f"🔗 {e.get('url')}\n"
        f"📊 Score: {e.get('score')}\n"
        f"💡 AI Summary: {an.get('summary', '-')}\n\n"
        f"Источник: {e.get('source')}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_moderation_keyboard(e['id'], page, max(1, total)))

@router.callback_query(F.data.startswith("approve_event_"))
async def approve_event_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    db.update_status(int(c.data.split("_")[2]), 'approved')
    await c.answer("✅ Одобрено")
    await c.message.delete()
    await show_moderation_page(c.message, db, 0)

@router.callback_query(F.data.startswith("reject_event_"))
async def reject_event_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    db.update_status(int(c.data.split("_")[2]), 'rejected')
    await c.answer("❌ Отклонено")
    await c.message.delete()
    await show_moderation_page(c.message, db, 0)

@router.callback_query(F.data.startswith("mod_next_"))
async def mod_next_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[2])
    await c.message.delete()
    await show_moderation_page(c.message, db, page)

@router.callback_query(F.data.startswith("mod_prev_"))
async def mod_prev_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin: return
    page = int(c.data.split("_")[2])
    await c.message.delete()
    await show_moderation_page(c.message, db, page)

@router.message(lambda msg: msg.text == "📋 Список админов")
async def list_admins(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    admins = db.get_all_admins()
    text = "📋 <b>Администраторы:</b>\n\n"
    for a in admins:
        r = "👔 Руководитель" if a['role'] == 'Manager' else "👑 ТехПоддержка" if a['role'] == 'TechSupport' else a['role']
        text += f"• <b>{a['telegram_id']}</b> ({r})\n"
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "➕ Добавить админа")
async def add_adm(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await state.set_state(AdminStates.waiting_for_new_admin_id)
    await message.answer("➕ ID нового админа:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_new_admin_id)
async def add_adm_id(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": await handle_cancel(m, state, db, get_admin_management_keyboard()); return
    if not m.text.isdigit(): await m.answer("❌ Число!"); return
    await state.update_data(nid=int(m.text))
    await state.set_state(AdminStates.waiting_for_new_admin_role)
    await m.answer("👤 Роль:", reply_markup=get_admin_role_keyboard())

@router.message(AdminStates.waiting_for_new_admin_role)
async def add_adm_role(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": await handle_cancel(m, state, db, get_admin_management_keyboard()); return
    d = await state.get_data()
    role = "Manager"
    if "ТехПоддержка" in m.text: role = "TechSupport"
    elif "Руководитель" in m.text: role = "Manager"
    db.add_admin(d['nid'], "Unknown", role)
    await m.answer(f"✅ Админ {d['nid']} ({role}) добавлен.", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text == "➖ Удалить админа")
async def rm_adm(m: types.Message, state: FSMContext, db: FDataBase):
    if check_access(m, db):
        await state.set_state(AdminStates.waiting_for_remove_admin)
        await m.answer("➖ ID:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_remove_admin)
async def rm_adm_fin(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": await handle_cancel(m, state, db, get_admin_management_keyboard()); return
    if not m.text.isdigit(): await m.answer("❌ Число!"); return
    db.remove_admin(int(m.text))
    await m.answer("🗑 Удален.", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text == "📝 Изменить роль админа")
async def change_role(m: types.Message, state: FSMContext, db: FDataBase):
    if check_access(m, db):
        await state.set_state(AdminStates.waiting_for_change_role_id)
        await m.answer("📝 ID админа:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_change_role_id)
async def change_role_id(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": await handle_cancel(m, state, db, get_admin_management_keyboard()); return
    if not m.text.isdigit(): await m.answer("❌ Число!"); return
    await state.update_data(change_role_id=int(m.text))
    await state.set_state(AdminStates.waiting_for_change_role_new)
    await m.answer("👤 Новая роль:", reply_markup=get_admin_role_keyboard())

@router.message(AdminStates.waiting_for_change_role_new)
async def change_role_fin(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": await handle_cancel(m, state, db, get_admin_management_keyboard()); return
    role = "Manager"
    if "ТехПоддержка" in m.text: role = "TechSupport"
    elif "Руководитель" in m.text: role = "Manager"
    d = await state.get_data()
    db.update_admin_role(d['change_role_id'], role)
    await m.answer("✅ Обновлено.", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text == "🗓 Экспорт по периоду")
async def admin_export_period(message: types.Message):
    await message.answer("🗓 <b>Выберите период для экспорта:</b>", 
                        parse_mode="HTML", 
                        reply_markup=get_admin_export_period_keyboard())

@router.message(F.text.in_(["📅 На неделю", "📅 На месяц", "📅 На 3 месяца", "📅 На год"]))
async def admin_export_by_period(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    
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
    
    events = await asyncio.to_thread(db.get_upcoming_events, message.from_user.id, days)
    
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

# --- УПРАВЛЕНИЕ СПИСКОМ СОТРУДНИКОВ ---

@router.message(lambda msg: msg.text == "📋 Список сотрудников")
async def list_employees_handler(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin: return
    await show_employees_list(message, db, 0)

async def show_employees_list(message: types.Message, db: FDataBase, page: int):
    # Получаем всех подтвержденных пользователей пагинацией
    # Примечание: нужно реализовать/использовать метод пагинации пользователей в БД.
    # Сейчас используем get_all_approved_users и режем список вручную (можно оптимизировать SQL позже)
    all_users = await asyncio.to_thread(db.get_all_approved_users)
    
    limit = 7
    total_pages = max(1, (len(all_users) + limit - 1) // limit)
    page = min(page, total_pages - 1)
    start = page * limit
    end = start + limit
    current_users = all_users[start:end]
    
    text = f"📋 <b>Список сотрудников</b> ({page + 1}/{total_pages})\nВсего: {len(all_users)}\n\nВыберите сотрудника для редактирования:"
    
    kb = get_employees_list_keyboard(current_users, page, total_pages)
    
    if isinstance(message, types.Message):
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("users_list_prev_"))
async def users_list_prev(c: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(c, db): return
    page = int(c.data.split("_")[3])
    await show_employees_list(c.message, db, page)

@router.callback_query(F.data.startswith("users_list_next_"))
async def users_list_next(c: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(c, db): return
    page = int(c.data.split("_")[3])
    await show_employees_list(c.message, db, page)

@router.callback_query(F.data == "back_to_users_list_0")
async def back_users_list(c: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(c, db): return
    await show_employees_list(c.message, db, 0)

# --- КАРТОЧКА СОТРУДНИКА ---

@router.callback_query(F.data.startswith("manage_user_"))
async def manage_user_detail(c: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(c, db): return
    user_id = int(c.data.split("_")[2])
    user = db.get_user_by_id(user_id)
    
    if not user:
        await c.answer("Пользователь не найден", show_alert=True)
        return

    stats = await asyncio.to_thread(db.get_user_stats, user_id)
    
    text = (
        f"👤 <b>Профиль сотрудника</b>\n\n"
        f"🆔 ID: {user['id']}\n"
        f"📝 <b>ФИО:</b> {user['full_name']}\n"
        f"💼 <b>Должность:</b> {user['position']} (Rank: {db._get_position_rank(user['position'])})\n"
        f"📧 <b>Email:</b> {user.get('email', '-')}\n"
        f"📞 <b>Телефон:</b> {user.get('phone', '-')}\n"
        f"📊 <b>Записей на мероприятия:</b> {stats.get('total_events', 0)}"
    )
    
    await c.message.edit_text(text, parse_mode="HTML", reply_markup=get_user_edit_keyboard(user_id))

# --- РЕДАКТИРОВАНИЕ ---

# 1. ФИО
@router.callback_query(F.data.startswith("edit_usr_name_"))
async def edit_usr_name_start(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    if not check_callback_access(c, db): return
    user_id = int(c.data.split("_")[3])
    await state.update_data(edit_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_edit_user_name)
    await c.message.answer("Введите новое ФИО сотрудника:", reply_markup=get_cancel_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_user_name)
async def edit_usr_name_process(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": 
        await handle_cancel(m, state, db, get_users_mgmt_kb())
        return
    data = await state.get_data()
    db.update_user_profile(data['edit_user_id'], full_name=m.text)
    await m.answer("✅ ФИО обновлено!", reply_markup=get_users_mgmt_kb())
    await state.clear()

# 2. Email
@router.callback_query(F.data.startswith("edit_usr_email_"))
async def edit_usr_email_start(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    if not check_callback_access(c, db): return
    user_id = int(c.data.split("_")[3])
    await state.update_data(edit_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_edit_user_email)
    await c.message.answer("Введите новый Email:", reply_markup=get_cancel_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_user_email)
async def edit_usr_email_process(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": 
        await handle_cancel(m, state, db, get_users_mgmt_kb())
        return
    data = await state.get_data()
    db.update_user_profile(data['edit_user_id'], email=m.text)
    await m.answer("✅ Email обновлен!", reply_markup=get_users_mgmt_kb())
    await state.clear()

# 3. Должность
@router.callback_query(F.data.startswith("edit_usr_pos_"))
async def edit_usr_pos_start(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    if not check_callback_access(c, db): return
    user_id = int(c.data.split("_")[3])
    await state.update_data(edit_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_edit_user_pos)
    await c.message.answer("Выберите или введите новую должность:", reply_markup=get_position_keyboard())
    await c.answer()

@router.message(AdminStates.waiting_for_edit_user_pos)
async def edit_usr_pos_process(m: types.Message, state: FSMContext, db: FDataBase):
    if m.text == "❌ Отменить": 
        await handle_cancel(m, state, db, get_users_mgmt_kb())
        return
    data = await state.get_data()
    db.update_user_profile(data['edit_user_id'], position=m.text)
    await m.answer("✅ Должность обновлена!", reply_markup=get_users_mgmt_kb())
    await state.clear()

# 4. Удаление
@router.callback_query(F.data.startswith("delete_usr_"))
async def delete_usr_handler(c: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(c, db): return
    user_id = int(c.data.split("_")[2])
    # Используем reject_user как удаление
    db.reject_user(user_id) 
    await c.answer("🗑 Сотрудник удален из базы", show_alert=True)
    await show_employees_list(c.message, db, 0)