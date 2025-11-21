from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import json
import asyncio
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
        print(f"Access check error: {e}")
        return None

def check_callback_access(callback: types.CallbackQuery, db: FDataBase):
    admin = check_access(callback, db)
    if not admin:
        try:
            asyncio.create_task(callback.answer("⛔ У вас нет доступа к системе управления.", show_alert=True))
        except:
            pass
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
        except:
            pass
            
    return datetime.now()

def get_admin_main_kb(role):
    btns = [
        [KeyboardButton(text="📝 Управление мероприятиями"), KeyboardButton(text="👥 Управление пользователями")],
        [KeyboardButton(text="🔄 Сканировать источники"), KeyboardButton(text="📊 Статистика")],
    ]
    if role in ('GreatAdmin', 'Owner'):
        btns.append([KeyboardButton(text="👤 Управление админами")])
    
    btns.append([KeyboardButton(text="⬅️ Главное меню")])
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

def get_events_mgmt_kb():
    btns = [
        [KeyboardButton(text="📜 Модерация"), KeyboardButton(text="🔍 Поиск (Админ)")],
        [KeyboardButton(text="➕ Создать событие"), KeyboardButton(text="🤝 Добавить партнёрское")],
        [KeyboardButton(text="📂 Загрузить из файла"), KeyboardButton(text="📋 Список всех")],
        [KeyboardButton(text="📋 Список сотрудников")],
        [KeyboardButton(text="⬅️ Назад в админку")]
    ]
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

def get_users_mgmt_kb():
    btns = [
        [KeyboardButton(text="✅ Подтверждение (Модерация)"), KeyboardButton(text="📋 Список пользователей")],
        [KeyboardButton(text="📋 Список сотрудников"), KeyboardButton(text="📝 Управление ролями")],
        [KeyboardButton(text="📝 Модерация регистраций"), KeyboardButton(text="⬅️ Назад в админку")]
    ]
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

def get_admin_management_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Список админов"), KeyboardButton(text="➕ Добавить админа")],
        [KeyboardButton(text="➖ Удалить админа"), KeyboardButton(text="📝 Изменить роль админа")],
        [KeyboardButton(text="⬅️ Назад в админку")]
    ], resize_keyboard=True)

@router.message(lambda msg: msg.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    
    await message.answer(
        f"🕵️‍♂️ <b>Панель управления</b>\n"
        f"👤 Роль: <b>{admin.get('role')}</b>\n"
        f"🆔 ID: <code>{admin.get('telegram_id')}</code>",
        reply_markup=get_admin_main_kb(admin.get('role')),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text == "⬅️ Назад в админку")
async def back_to_admin_handler_msg(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await admin_panel(message, db)

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_handler_cb(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin:
        return
    await callback.message.delete()
    await admin_panel(callback.message, db)

@router.message(lambda msg: msg.text == "⬅️ Главное меню")
async def back_to_main_menu(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    await message.answer(
        "🔙 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text == "📊 Статистика")
async def show_stats(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    
    stats = await asyncio.to_thread(db.get_stats)
    text = (
        "📊 <b>Статистика системы</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: <b>{stats.get('total_users', 0)}</b>\n"
        f"• Активных: <b>{stats.get('active_users', 0)}</b>\n"
        f"• Ожидают: <b>{stats.get('pending_users', 0)}</b>\n\n"
        f"📅 <b>Мероприятия:</b>\n"
        f"• Всего: <b>{stats.get('total_events', 0)}</b>\n"
        f"• Опубл.: <b>{stats.get('approved_events', 0)}</b>\n"
        f"• На модерации: <b>{stats.get('pending_events', 0)}</b>\n\n"
        f"📝 <b>Регистрации:</b>\n"
        f"• Всего: <b>{stats.get('total_registrations', 0)}</b>\n"
        f"• Ожидают: <b>{stats.get('pending_registrations', 0)}</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "🔄 Сканировать источники")
async def scan_sources(message: types.Message, db: FDataBase, parser, gigachat):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    
    status_msg = await message.answer("⏳ <b>Запускаю сканирование...</b>\nПожалуйста, подождите.", parse_mode="HTML")
    
    try:
        raw_events = await asyncio.to_thread(parser.get_events)
        
        if not raw_events:
            await status_msg.edit_text("❌ Событий на источниках не найдено.")
            return
            
        await status_msg.edit_text(f"🔍 Найдено <b>{len(raw_events)}</b> событий. Анализирую через AI...", parse_mode="HTML")
        
        c = 0
        for raw_event in raw_events:
            try:
                if db.check_event_exists_by_url(raw_event.get('url')):
                    continue

                analysis = await asyncio.to_thread(gigachat.analyze_event, raw_event.get('text', ''))
                
                dt_obj = parse_date_safe(analysis.get('date', ''))
                dt_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                
                score = analysis.get('score', 0)
                priority = 'high' if score >= 80 else 'medium'

                db.add_new_event(
                    title=analysis.get('title', 'Неизвестно'),
                    description=raw_event.get('text', ''),
                    location=analysis.get('location', 'СПб'),
                    date_str=analysis.get('date', 'Не указана'),
                    url=raw_event.get('url', ''),
                    analysis=json.dumps(analysis, ensure_ascii=False),
                    score=score,
                    priority=priority,
                    required_rank=1,
                    event_datetime=dt_str,
                    status='new',
                    source='parser'
                )
                c += 1
            except:
                continue
                
        await status_msg.edit_text(f"✅ <b>Готово!</b>\nДобавлено новых событий: <b>{c}</b>\nПроверьте раздел 'Модерация'.", parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")

@router.message(lambda msg: msg.text == "👥 Управление пользователями")
async def manage_users_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await message.answer("👥 <b>Меню пользователей</b>", reply_markup=get_users_mgmt_kb(), parse_mode="HTML")

@router.message(lambda msg: msg.text == "✅ Подтверждение (Модерация)")
async def show_user_approvals(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
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
        f"👤 <b>ЗАЯВКА #{user['id']}</b>\n\n"
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
    if not admin:
        return
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
    if not admin:
        return
    db.reject_user(int(c.data.split("_")[2]))
    await c.answer("❌ Заявка отклонена")
    await c.message.delete()
    await show_user_approval_page(c.message, db, 0)

@router.callback_query(F.data == "skip_user")
async def skip_user_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    await c.message.delete()
    await show_user_approval_page(c.message, db, 0)

@router.callback_query(F.data.startswith("user_approval_next_"))
async def user_approval_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_user_approval_page(c.message, db, page)

@router.message(lambda msg: msg.text == "📋 Список пользователей")
async def list_users(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    s = await asyncio.to_thread(db.get_stats)
    await message.answer(
        f"📋 <b>Пользователи</b>\n"
        f"Всего: {s.get('total_users', 0)}\n"
        f"Активных: {s.get('active_users', 0)}\n"
        f"На модерации: {s.get('pending_users', 0)}",
        reply_markup=get_users_mgmt_kb(),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text == "📝 Модерация регистраций")
async def show_registration_moderation(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await show_reg_moderation_page(message, db, 0)

async def show_reg_moderation_page(message: types.Message, db: FDataBase, page: int):
    registrations = await asyncio.to_thread(db.get_pending_registrations)
    
    if not registrations:
        await message.answer("✅ Нет заявок на регистрацию для модерации.", reply_markup=get_users_mgmt_kb())
        return
    
    total = len(registrations)
    if page >= total:
        page = 0
    
    reg = registrations[page]
    
    text = (
        f"📝 <b>МОДЕРАЦИЯ РЕГИСТРАЦИЙ</b> ({page+1}/{total})\n\n"
        f"👤 <b>Сотрудник:</b> {reg['user_name']}\n"
        f"💼 <b>Должность:</b> {reg['user_position']}\n"
        f"📅 <b>Мероприятие:</b> {reg['event_title']}\n"
        f"🗓 <b>Дата:</b> {reg['date_str']}\n"
        f"🔗 <b>Ссылка:</b> {reg['url'] or 'Нет'}\n"
    )
    
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_reg_moderation_keyboard(reg['user_id'], reg['event_id'], page, total)
    )

@router.callback_query(F.data.startswith("reg_approve_"))
async def reg_approve_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin:
        await callback.answer("⛔ Нет доступа.")
        return
        
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("❌ Неверные данные.")
        return
        
    user_id = int(parts[2])
    event_id = int(parts[3])
    
    if db.approve_registration(user_id, event_id):
        user = db.get_user_by_id(user_id)
        event = db.get_event_by_id(event_id)
        
        if user and event:
            bot = callback.bot
            ics_content = IcsGenerator.generate_ics(
                event.get('title', ''), 
                event.get('description', ''), 
                event.get('location', ''), 
                event.get('date_str', '')
            )
            ics_file = BufferedInputFile(ics_content.encode('utf-8'), filename=f"{event_id}_event.ics")
            try:
                await bot.send_document(
                    user.get('telegram_id'), 
                    ics_file,
                    caption=f"✅ <b>Регистрация на мероприятие подтверждена!</b>\n\n"
                            f"🎯 <b>{event.get('title')}</b>\n"
                            f"📅 {event.get('date_str')}\n"
                            f"📍 {event.get('location')}\n\n"
                            f"Прикрепите ICS файл к вашему календарю.",
                    parse_mode="HTML"
                )
            except:
                pass
                
        await callback.answer("✅ Регистрация подтверждена")
    else:
        await callback.answer("❌ Ошибка: Запрос уже обработан")
        
    try:
        await callback.message.delete()
    except:
        pass
    await show_reg_moderation_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("reg_reject_"))
async def reg_reject_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin:
        await callback.answer("⛔ Нет доступа.")
        return
        
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("❌ Неверные данные.")
        return
        
    user_id = int(parts[2])
    event_id = int(parts[3])
    
    if db.reject_registration(user_id, event_id):
        user = db.get_user_by_id(user_id)
        event = db.get_event_by_id(event_id)
        
        if user and event:
            try:
                await callback.bot.send_message(
                    user.get('telegram_id'),
                    f"❌ <b>Регистрация на мероприятие отклонена</b>\n\n"
                    f"🎯 <b>{event.get('title')}</b>\n"
                    f"📅 {event.get('date_str')}\n"
                    f"📍 {event.get('location')}\n\n"
                    f"По вопросам обращайтесь к администратору.",
                    parse_mode="HTML"
                )
            except:
                pass
                
        await callback.answer("❌ Регистрация отклонена")
    else:
        await callback.answer("❌ Ошибка: Запрос уже обработан")
        
    try:
        await callback.message.delete()
    except:
        pass
    await show_reg_moderation_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("reg_next_"))
async def reg_next_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin:
        return
        
    page = int(callback.data.split("_")[2])
    await callback.message.delete()
    await show_reg_moderation_page(callback.message, db, page)

@router.callback_query(F.data.startswith("reg_prev_"))
async def reg_prev_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin:
        return
        
    page = int(callback.data.split("_")[2])
    await callback.message.delete()
    await show_reg_moderation_page(callback.message, db, page)

@router.message(lambda msg: msg.text == "📝 Управление мероприятиями")
async def manage_events_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await message.answer("📝 <b>Меню мероприятий</b>", reply_markup=get_events_mgmt_kb(), parse_mode="HTML")

@router.message(lambda msg: msg.text == "📜 Модерация")
async def start_moderation(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
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
    
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_moderation_keyboard(e['id'], page, max(1, total))
    )

@router.callback_query(F.data.startswith("approve_event_"))
async def approve_event_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    db.update_status(int(c.data.split("_")[2]), 'approved')
    await c.answer("✅ Одобрено")
    await c.message.delete()
    await show_moderation_page(c.message, db, 0)

@router.callback_query(F.data.startswith("reject_event_"))
async def reject_event_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    db.update_status(int(c.data.split("_")[2]), 'rejected')
    await c.answer("❌ Отклонено")
    await c.message.delete()
    await show_moderation_page(c.message, db, 0)

@router.callback_query(F.data == "skip_event_mod")
async def skip_event_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    await c.message.delete()
    await show_moderation_page(c.message, db, 0)

@router.callback_query(F.data.startswith("mod_next_"))
async def mod_next_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    page = int(c.data.split("_")[2])
    await c.message.delete()
    await show_moderation_page(c.message, db, page)

@router.callback_query(F.data.startswith("mod_prev_"))
async def mod_prev_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    page = int(c.data.split("_")[2])
    await c.message.delete()
    await show_moderation_page(c.message, db, page)

@router.message(lambda msg: msg.text == "🔍 Поиск (Админ)")
async def admin_search_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_search_text)
    await message.answer("🔍 Введите запрос для поиска по всей базе:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_search_text)
async def admin_search_process(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return

    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    
    wait_msg = await message.answer("⏳ Ищу...")
    results = await asyncio.to_thread(db.search_all_events_by_keywords, message.text.split(','), 10)
    await state.clear()
    await wait_msg.delete()
    
    if not results:
        await message.answer("🔍 Ничего не найдено.", reply_markup=get_events_mgmt_kb())
        return
        
    text = "🔍 <b>Результаты:</b>\n\n"
    for res in results:
        status_icon = "✅" if res['status'] == 'approved' else "⏳"
        text += f"{status_icon} <b>{res['title']}</b>\nID: /admin_event_details_{res['id']}\n\n"
        
    await message.answer(text, parse_mode="HTML", reply_markup=get_events_mgmt_kb())

@router.message(lambda msg: msg.text == "🤝 Добавить партнёрское")
async def add_partner_event_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_event_title)
    await state.update_data(event_source='partner')
    await message.answer("🤝 <b>Новое партнёрское событие</b>\nВведите название:", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(lambda msg: msg.text == "➕ Создать событие")
async def create_event_manual_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_event_title)
    await state.update_data(event_source='manual')
    await message.answer("📝 <b>Новое событие</b>\nВведите название:", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_event_title)
async def process_event_title(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return

    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_title=message.text)
    await state.set_state(AdminStates.waiting_for_event_description)
    await message.answer("📝 Описание:")

@router.message(AdminStates.waiting_for_event_description)
async def process_event_desc(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return

    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_description=message.text)
    await state.set_state(AdminStates.waiting_for_event_location)
    await message.answer("📍 Место проведения:")

@router.message(AdminStates.waiting_for_event_location)
async def process_event_loc(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return

    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_location=message.text)
    await state.set_state(AdminStates.waiting_for_event_date)
    await message.answer("📅 Дата (текстом, напр. '25 декабря'):")

@router.message(AdminStates.waiting_for_event_date)
async def process_event_date(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return

    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return
    await state.update_data(event_date=message.text)
    await state.set_state(AdminStates.waiting_for_event_url)
    await message.answer("🔗 Ссылка (или '-'):")

@router.message(AdminStates.waiting_for_event_url)
async def process_event_url(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return

    data = await state.get_data()
    source = data.get('event_source', 'manual')
    
    dt_obj = parse_date_safe(data['event_date'])
    dt_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    
    db.add_new_event(
        title=data['event_title'],
        description=data['event_description'],
        location=data['event_location'],
        date_str=data['event_date'],
        url=message.text,
        analysis="{}",
        score=0,
        priority='medium',
        required_rank=1,
        event_datetime=dt_str,
        status='pending',
        source=source
    )
    
    await state.clear()
    await message.answer(f"✅ Событие ({source}) создано и отправлено на модерацию!", reply_markup=get_events_mgmt_kb())

@router.message(lambda msg: msg.text == "📂 Загрузить из файла")
async def upload_file_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_file)
    await message.answer(
        "📂 <b>Отправьте файл</b> (.txt, .json)\n"
        "AI проанализирует содержимое и создаст черновики событий.",
        parse_mode="HTML", 
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_file)
async def process_file_upload(message: types.Message, state: FSMContext, db: FDataBase, gigachat: any, bot: Bot):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return

    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_events_mgmt_kb())
        return

    if not message.document:
        await message.answer("❌ Это не файл. Пожалуйста, прикрепите документ.")
        return

    if message.document.file_size > 5 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой (макс 5 МБ).")
        return

    wait_msg = await message.answer("⏳ Скачиваю и анализирую файл...")
    
    try:
        file_info = await bot.get_file(message.document.file_id)
        downloaded = await bot.download_file(file_info.file_path)
        content = downloaded.read().decode('utf-8', errors='ignore')

        events_data = await asyncio.to_thread(gigachat.analyze_file_content, content)
        
        if not events_data:
            await wait_msg.delete()
            await message.answer("❌ Не удалось найти события в файле.", reply_markup=get_events_mgmt_kb())
            return
            
        count = 0
        for ev in events_data:
            dt_obj = parse_date_safe(ev.get('date', ''))
            dt_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            
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
                event_datetime=dt_str,
                status='pending',
                source='file'
            )
            count += 1
            
        await state.clear()
        await wait_msg.delete()
        await message.answer(f"✅ Файл обработан.\nСоздано черновиков: <b>{count}</b>", parse_mode="HTML", reply_markup=get_events_mgmt_kb())
        
    except Exception as e:
        await state.clear()
        try:
            await wait_msg.delete()
        except:
            pass
        await message.answer(f"❌ Ошибка: {str(e)}", parse_mode="HTML", reply_markup=get_events_mgmt_kb())

@router.message(lambda msg: msg.text == "📋 Список всех")
async def list_all_events(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await show_events_list_page(message, db, 0)

async def show_events_list_page(message: types.Message, db: FDataBase, page: int):
    events = await asyncio.to_thread(db.get_all_events_paginated, page, 10)
    total = await asyncio.to_thread(db.get_total_events_count)
    total_pages = max(1, (total + 9) // 10)
    
    text = "📋 <b>Все мероприятия</b>\n"
    for e in events:
        icon = "🤝" if e['source'] == 'partner' else "📂" if e['source'] == 'file' else "🤖"
        status = "✅" if e['status'] == 'approved' else "⏳"
        text += f"{icon} {status} <b>{e['title']}</b>\nID: /admin_event_details_{e['id']}\n\n"
        
    await message.answer(text, parse_mode="HTML", reply_markup=get_events_list_keyboard(events, page, total_pages))

@router.callback_query(F.data.startswith("admin_events_prev_"))
async def admin_events_prev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_events_list_page(c.message, db, page)

@router.callback_query(F.data.startswith("admin_events_next_"))
async def admin_events_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    page = int(c.data.split("_")[3])
    await c.message.delete()
    await show_events_list_page(c.message, db, page)

@router.message(lambda msg: msg.text and msg.text.startswith("/admin_event_details_"))
async def admin_det_cmd(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    try: eid = int(message.text.split("_")[3])
    except: return
    await show_admin_detail(message, db, eid)

@router.callback_query(F.data.startswith("admin_event_details_"))
async def admin_det_cb(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
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
    if not admin:
        return
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
    await m.answer("✅ Название обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_desc_"))
async def edit_d(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
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
    await m.answer("✅ Описание обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_location_"))
async def edit_l(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
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
    await m.answer("✅ Место обновлено")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_date_"))
async def edit_dt(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
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
    await m.answer("✅ Дата обновлена")
    await state.clear()

@router.callback_query(F.data.startswith("edit_event_url_"))
async def edit_u(c: types.CallbackQuery, state: FSMContext, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
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
    await m.answer("✅ Ссылка обновлена")
    await state.clear()

@router.callback_query(F.data.startswith("delete_event_confirm_"))
async def del_ev(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    db.delete_event(int(c.data.split("_")[3]))
    await c.answer("🗑 Удалено")
    await c.message.delete()

@router.callback_query(F.data.startswith("back_to_event_"))
async def back_to_event(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    await admin_det_cb(c, db)

@router.callback_query(F.data.startswith("event_participants_"))
async def show_participants(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
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
    if not admin:
        return
    p = c.data.split("_")
    await show_participants_page(c.message, db, int(p[2]), int(p[3]))

@router.callback_query(F.data.startswith("part_next_"))
async def part_next(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
    p = c.data.split("_")
    await show_participants_page(c.message, db, int(p[2]), int(p[3]))

@router.callback_query(F.data.startswith("export_participants_"))
async def export_participants_handler(callback: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(callback, db)
    if not admin:
        return
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

@router.message(lambda msg: msg.text == "👤 Управление админами")
async def admin_admins_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin.get('role') not in ('GreatAdmin', 'Owner'):
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("👤 <b>Управление админами</b>", reply_markup=get_admin_management_keyboard(), parse_mode="HTML")

@router.message(lambda msg: msg.text == "📋 Список админов")
async def list_admins(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    admins = db.get_all_admins()
    text = "📋 <b>Администраторы:</b>\n\n"
    for a in admins:
        text += f"• <b>{a['telegram_id']}</b> ({a['role']})\n"
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "➕ Добавить админа")
async def add_adm(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_new_admin_id)
    await message.answer("➕ ID нового админа:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_new_admin_id)
async def add_adm_id(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    if m.text == "❌ Отменить":
        await handle_cancel(m, state, db, get_admin_management_keyboard())
        return
    if not m.text.isdigit():
        await m.answer("❌ ID должен быть числом.")
        return
    await state.update_data(nid=int(m.text))
    await state.set_state(AdminStates.waiting_for_new_admin_role)
    await m.answer("👤 Выберите роль:", reply_markup=get_admin_role_keyboard())

@router.message(AdminStates.waiting_for_new_admin_role)
async def add_adm_role(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    if m.text == "❌ Отменить":
        await handle_cancel(m, state, db, get_admin_management_keyboard())
        return
    d = await state.get_data()
    role = "Admin"
    if "GreatAdmin" in m.text: role = "GreatAdmin"
    elif "Moderator" in m.text: role = "Moderator"
    
    db.add_admin(d['nid'], "Unknown", role)
    await m.answer(f"✅ Админ {d['nid']} добавлен ({role}).", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text == "➖ Удалить админа")
async def rm_adm(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_remove_admin)
    await m.answer("➖ ID для удаления:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_remove_admin)
async def rm_adm_fin(m: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(m, db)
    if not admin:
        await m.answer("⛔ У вас нет доступа к системе управления.")
        return
    if m.text == "❌ Отменить":
        await handle_cancel(m, state, db, get_admin_management_keyboard())
        return
    if not m.text.isdigit():
        await m.answer("❌ Число!")
        return
    db.remove_admin(int(m.text))
    await m.answer("🗑 Админ удален.", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text == "📝 Изменить роль админа")
async def change_role_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await state.set_state(AdminStates.waiting_for_change_role_id)
    await message.answer("📝 Введите ID админа:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_change_role_id)
async def change_role_id(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_admin_management_keyboard())
        return
    if not message.text.isdigit():
        await message.answer("❌ Число!")
        return
    await state.update_data(change_role_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_change_role_new)
    await message.answer("👤 Новая роль:", reply_markup=get_admin_role_keyboard())

@router.message(AdminStates.waiting_for_change_role_new)
async def change_role_fin(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    if message.text == "❌ Отменить":
        await handle_cancel(message, state, db, get_admin_management_keyboard())
        return
    role = "Admin"
    if "GreatAdmin" in message.text: role = "GreatAdmin"
    elif "Moderator" in message.text: role = "Moderator"
    
    d = await state.get_data()
    db.update_admin_role(d['change_role_id'], role)
    await message.answer("✅ Роль обновлена.", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text == "📋 Список сотрудников")
async def list_employees(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    
    users = await asyncio.to_thread(db.get_all_approved_users)
    if not users:
        await message.answer("📭 Нет подтвержденных сотрудников.")
        return
        
    text = "📋 <b>Список сотрудников:</b>\n\n"
    for user in users[:20]:
        rank = db._get_position_rank(user['position'])
        text += f"👤 <b>{user['full_name']}</b>\n💼 {user['position']} (ранг: {rank})\n📞 {user['phone']}\n\n"
        
    await message.answer(text, parse_mode="HTML", reply_markup=get_employees_list_keyboard(users))

@router.message(lambda msg: msg.text == "📝 Управление ролями")
async def manage_roles_start(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
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
    if not admin:
        return
        
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

@router.callback_query(F.data.startswith("view_user_events_"))
async def view_user_events_handler(c: types.CallbackQuery, db: FDataBase):
    admin = check_callback_access(c, db)
    if not admin:
        return
        
    user_id = int(c.data.split("_")[3])
    user = db.get_user_by_id(user_id)
    
    if not user:
        await c.answer("❌ Пользователь не найден")
        return
        
    events = db.get_user_events(user_id)
    
    text = f"📅 <b>Мероприятия сотрудника {user['full_name']}:</b>\n\n"
    if not events:
        text += "📭 Сотрудник не записан на мероприятия"
    else:
        for i, event in enumerate(events, 1):
            status_icon = "✅" if event['status'] == 'approved' else "⏳"
            text += f"{i}. {status_icon} <b>{event['title']}</b>\n📅 {event['date_str']}\n\n"
            
    await c.message.answer(text, parse_mode="HTML")
    await c.answer()