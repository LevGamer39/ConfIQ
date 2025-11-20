from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
import json
import asyncio
from datetime import datetime

from utils.keyboards import *
from utils.states import AdminStates
from utils.ics_generator import IcsGenerator
from database import FDataBase

router = Router()

def _get_user_id(source):
    try:
        return source.from_user.id
    except Exception:
        try:
            return source.user.id
        except Exception:
            return None

def check_access_by_id(user_id: int, db: FDataBase):
    if user_id is None:
        return None
    admin = db.get_admin(user_id)
    if not admin:
        return None
    role = admin.get('role', '')
    if role in ('GreatAdmin', 'Owner', 'Admin', 'Moderator'):
        return admin
    return None

def check_access(message: types.Message, db: FDataBase):
    user_id = _get_user_id(message)
    return check_access_by_id(user_id, db)

def check_callback_access(callback: types.CallbackQuery, db: FDataBase):
    user_id = _get_user_id(callback)
    return check_access_by_id(user_id, db)

@router.message(lambda msg: msg.text and msg.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await message.answer(
        f"🕵️‍♂️ <b>Панель управления Media Agent</b>\n"
        f"👤 Ваша роль: <b>{admin.get('role')}</b>\n"
        f"🆔 Ваш ID: <code>{admin.get('telegram_id') or admin.get('id') or message.from_user.id}</code>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_admin_keyboard(admin.get('role')),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text and msg.text == "⬅️ Главное меню")
async def back_to_main_menu(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    await message.answer(
        "🔙 <b>Возврат в главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text and msg.text == "📊 Статистика")
async def show_stats(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    stats = db.get_stats()
    text = (
        "📊 <b>Статистика системы</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: <b>{stats.get('total_users', 0)}</b>\n"
        f"• Активных: <b>{stats.get('active_users', 0)}</b>\n"
        f"• Ожидают подтверждения: <b>{stats.get('pending_users', 0)}</b>\n\n"
        f"📅 <b>Мероприятия:</b>\n"
        f"• Всего: <b>{stats.get('total_events', 0)}</b>\n"
        f"• Опубликовано: <b>{stats.get('approved_events', 0)}</b>\n"
        f"• На модерации: <b>{stats.get('pending_events', 0)}</b>\n"
        f"• Высокий приоритет: <b>{stats.get('high_priority', 0)}</b>\n\n"
        f"📋 <b>Регистрации:</b>\n"
        f"• Всего запросов: <b>{stats.get('total_registrations', 0)}</b>\n"
        f"• Ожидают подтверждения: <b>{stats.get('pending_registrations', 0)}</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text and msg.text == "📋 Модерация регистраций")
async def show_registration_moderation(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к модерации регистраций.")
        return
    await message.answer("🔄 Запуск модерации регистраций...")
    await show_next_reg_moderation(message, db)

async def show_next_reg_moderation(message: types.Message, db: FDataBase):
    pending_regs = db.get_pending_registrations()
    if not pending_regs:
        await message.answer("✅ Новых запросов на регистрацию нет.", reply_markup=get_admin_keyboard('Admin'))
        return
    reg = pending_regs[0]
    text = (
        f"📝 <b>ЗАПРОС НА РЕГИСТРАЦИЮ</b>\n\n"
        f"👤 Сотрудник: <b>{reg.get('user_name')}</b>\n"
        f"💼 Должность: {reg.get('user_position', 'Не указано')}\n"
        f"🆔 ID пользователя: <code>{reg.get('user_id')}</code>\n\n"
        f"🔥 <b>Мероприятие: {reg.get('event_title')}</b>\n"
        f"🆔 ID мероприятия: <code>{reg.get('event_id')}</code>\n"
        f"📅 Дата: {reg.get('date_str')}\n"
        f"📍 Место: {reg.get('location', 'Не указано')}\n"
        f"🔗 <a href='{reg.get('url', '')}'>Ссылка на мероприятие</a>"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_registration_moderation_keyboard(reg.get('user_id'), reg.get('event_id')),
        disable_web_page_preview=True
    )

@router.callback_query(F.data.startswith("reg_approve_"))
async def reg_approve_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
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
    await show_next_reg_moderation(callback.message, db)

@router.callback_query(F.data.startswith("reg_reject_"))
async def reg_reject_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
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
            bot = callback.bot
            try:
                await bot.send_message(
                    user.get('telegram_id'), 
                    f"❌ <b>Регистрация на мероприятие отклонена</b>\n\n"
                    f"🎯 <b>{event.get('title')}</b>\n"
                    f"📅 {event.get('date_str')}\n\n"
                    f"Пожалуйста, свяжитесь с руководителем для уточнения причин.",
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
    await show_next_reg_moderation(callback.message, db)

@router.callback_query(F.data == "skip_reg_mod")
async def skip_reg_mod_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    await callback.answer("⏭ Запрос пропущен")
    try:
        await callback.message.delete()
    except:
        pass
    await show_next_reg_moderation(callback.message, db)

@router.message(lambda msg: msg.text and msg.text == "🔄 Сканировать источники")
async def scan_sources(message: types.Message, parser, db: FDataBase, gigachat):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("🔄 Запускаю сканирование веб-источников...")
    try:
        raw_events = parser.get_events()
        if not raw_events:
            await message.answer("❌ Не удалось найти события на источниках.")
            return
        await message.answer(f"🔍 Найдено {len(raw_events)} потенциальных событий. Отправляю на AI-анализ...")
        processed_count = 0
        for raw_event in raw_events:
            try:
                analysis = gigachat.analyze_event(raw_event.get('text', ''))
                score = analysis.get('score', 0)
                priority = 'high' if score >= 80 else 'medium'
                required_rank = 1
                try:
                    event_datetime = datetime.strptime(analysis.get('date', ''), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                except:
                    event_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                db.add_new_event(
                    analysis.get('title', 'Неизвестно'),
                    raw_event.get('text', ''),
                    analysis.get('location', 'СПб'),
                    analysis.get('date', 'Не указана'),
                    raw_event.get('url', ''),
                    json.dumps(analysis, ensure_ascii=False),
                    score,
                    priority,
                    required_rank,
                    event_datetime,
                    'new'
                )
                processed_count += 1
            except Exception:
                continue
        await message.answer(f"✅ Обработка завершена. {processed_count} событий отправлено на модерацию.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при сканировании: {str(e)}")

@router.message(lambda msg: msg.text and msg.text == "👥 Подтверждение пользователей")
async def show_user_approvals(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.answer("🔄 Загрузка пользователей для подтверждения...")
    await show_user_approval_page(message, db, 0)

async def show_user_approval_page(message: types.Message, db: FDataBase, page: int):
    users = db.get_pending_users_paginated(page=page, limit=1)
    total_users = db.get_total_pending_users_count()
    total_pages = max(1, total_users)
    if not users:
        await message.answer("✅ Нет пользователей для подтверждения.", reply_markup=get_admin_keyboard('Admin'))
        return
    user = users[0]
    text = (
        f"👤 <b>НОВЫЙ ПОЛЬЗОВАТЕЛЬ</b>\n\n"
        f"🆔 ID: <code>{user.get('telegram_id')}</code>\n"
        f"👤 ФИО: <b>{user.get('full_name')}</b>\n"
        f"📧 Email: {user.get('email') or 'Не указан'}\n"
        f"📞 Телефон: {user.get('phone') or 'Не указан'}\n"
        f"💼 Должность: {user.get('position') or 'Не указана'}\n"
        f"📅 Зарегистрирован: {user.get('registered_at')[:10]}\n\n"
        f"<i>Статус: Ожидает подтверждения</i>"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_user_approval_pagination_keyboard(users, page, total_pages)
    )

@router.callback_query(F.data.startswith("user_approval_prev_"))
async def user_approval_prev_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer()
        return
    page = int(parts[3])
    try:
        await callback.message.delete()
    except:
        pass
    await show_user_approval_page(callback.message, db, page)
    await callback.answer()

@router.callback_query(F.data.startswith("user_approval_next_"))
async def user_approval_next_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer()
        return
    page = int(parts[3])
    try:
        await callback.message.delete()
    except:
        pass
    await show_user_approval_page(callback.message, db, page)
    await callback.answer()

@router.callback_query(F.data.startswith("approve_user_"))
async def approve_user_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    user_id = int(parts[2])
    if db.approve_user(user_id):
        user = db.get_user_by_id(user_id)
        if user:
            bot = callback.bot
            try:
                await bot.send_message(
                    user.get('telegram_id'),
                    "✅ <b>Ваш аккаунт подтвержден!</b>\n\n"
                    "Теперь вы можете пользоваться всеми функциями бота:\n"
                    "• 📅 Просмотр мероприятий\n"
                    "• 🔍 Поиск событий\n"
                    "• 📝 Регистрация на мероприятия\n"
                    "• 🗂 Экспорт календаря\n\n"
                    "Используйте меню для навигации.",
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard(False)
                )
            except:
                pass
        await callback.answer("✅ Пользователь подтвержден")
    else:
        await callback.answer("❌ Ошибка подтверждения")
    try:
        await callback.message.delete()
    except:
        pass
    await show_user_approval_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("reject_user_"))
async def reject_user_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    user_id = int(parts[2])
    if db.reject_user(user_id):
        user = db.get_user_by_id(user_id)
        if user:
            bot = callback.bot
            try:
                await bot.send_message(
                    user.get('telegram_id'),
                    "❌ <b>Ваш аккаунт не был подтвержден.</b>\n\n"
                    "Пожалуйста, свяжитесь с администратором для уточнения причин.",
                    parse_mode="HTML"
                )
            except:
                pass
        await callback.answer("❌ Пользователь отклонен")
    else:
        await callback.answer("❌ Ошибка отклонения")
    try:
        await callback.message.delete()
    except:
        pass
    await show_user_approval_page(callback.message, db, 0)

@router.callback_query(F.data == "skip_user")
async def skip_user_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    await callback.answer("⏭ Пользователь пропущен")
    try:
        await callback.message.delete()
    except:
        pass
    await show_user_approval_page(callback.message, db, 0)

@router.message(lambda msg: msg.text and msg.text == "👤 Управление админами")
async def admin_management(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    if admin.get('role') not in ('GreatAdmin', 'Owner'):
        await message.answer("⛔ Только GreatAdmin или Owner может управлять администраторами.")
        return
    await message.answer(
        "👤 <b>Управление администраторами</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_admin_management_keyboard()
    )

@router.message(lambda msg: msg.text and msg.text == "📋 Список админов")
async def list_admins(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    admins = db.get_all_admins()
    if not admins:
        await message.answer("📭 Администраторы не найдены.")
        return
    text = "📋 <b>Список администраторов:</b>\n\n"
    for a in admins:
        role_icon = "👑" if a.get('role') in ('GreatAdmin', 'Owner') else "👤"
        status = "🟢 Активен" if a.get('is_active', True) else "🔴 Неактивен"
        text += f"{role_icon} <code>{a.get('telegram_id')}</code> | {a.get('role')} | @{a.get('username')} | {status}\n"
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text and msg.text == "➕ Добавить админа")
async def add_admin_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    if admin.get('role') not in ('GreatAdmin', 'Owner'):
        await message.answer("⛔ Только GreatAdmin или Owner может добавлять администраторов.")
        return
    await state.set_state(AdminStates.waiting_for_new_admin_id)
    await message.answer(
        "👤 <b>Добавление администратора</b>\n\n"
        "Введите Telegram ID нового администратора:\n(Можно узнать через @userinfobot)",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_new_admin_id)
async def add_admin_process_id(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Добавление администратора отменено.", reply_markup=get_admin_management_keyboard())
        return
    if not message.text.isdigit():
        await message.answer("❌ ID должен быть числом. Попробуйте еще раз:")
        return
    telegram_id = int(message.text)
    existing_admin = db.get_admin(telegram_id)
    if existing_admin:
        await message.answer("❌ Пользователь уже является администратором.")
        await state.clear()
        return
    await state.update_data(new_admin_id=telegram_id)
    await state.set_state(AdminStates.waiting_for_new_admin_role)
    await message.answer(
        f"🆔 ID получен: <code>{telegram_id}</code>\n\n"
        "Выберите роль для нового администратора:",
        parse_mode="HTML",
        reply_markup=get_admin_role_keyboard()
    )

@router.message(AdminStates.waiting_for_new_admin_role)
async def add_admin_process_role(message: types.Message, state: FSMContext, db: FDataBase):
    mapping = {"👑 GreatAdmin": "GreatAdmin", "👤 Admin": "Admin", "👥 Moderator": "Moderator"}
    if message.text not in mapping:
        await message.answer("❌ Пожалуйста, выберите роль из предложенных кнопок:")
        return
    role = mapping[message.text]
    data = await state.get_data()
    telegram_id = data.get('new_admin_id')
    success = db.add_admin(telegram_id, "Неизвестно", role)
    if success:
        await message.answer(
            f"✅ <b>Администратор добавлен!</b>\n\n"
            f"🆔 ID: <code>{telegram_id}</code>\n"
            f"👤 Роль: <b>{role}</b>\n\n"
            f"Пользователь получит права администратора.",
            parse_mode="HTML",
            reply_markup=get_admin_management_keyboard()
        )
        try:
            await message.bot.send_message(
                telegram_id,
                f"🎉 <b>Вам назначены права администратора!</b>\n\n"
                f"👤 Роль: <b>{role}</b>\n"
                f"📋 Доступ: Панель управления ботом\n\n"
                f"Используйте кнопку '⚙️ Админ-панель' для доступа к функциям.",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        await message.answer(
            "❌ <b>Ошибка при добавлении администратора</b>\nПопробуйте еще раз.",
            parse_mode="HTML",
            reply_markup=get_admin_management_keyboard()
        )
    await state.clear()

@router.message(lambda msg: msg.text and msg.text == "➖ Удалить админа")
async def remove_admin_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    if admin.get('role') not in ('GreatAdmin', 'Owner'):
        await message.answer("⛔ Только GreatAdmin или Owner может удалять администраторов.")
        return
    await state.set_state(AdminStates.waiting_for_remove_admin)
    await message.answer(
        "🗑 <b>Удаление администратора</b>\n\nВведите Telegram ID администратора для удаления:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_remove_admin)
async def remove_admin_process(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Удаление администратора отменено.", reply_markup=get_admin_management_keyboard())
        return
    if not message.text.isdigit():
        await message.answer("❌ ID должен быть числом. Попробуйте еще раз:")
        return
    telegram_id = int(message.text)
    if telegram_id == message.from_user.id:
        await message.answer("❌ Нельзя удалить самого себя.")
        await state.clear()
        return
    target_admin = db.get_admin(telegram_id)
    if not target_admin:
        await message.answer("❌ Администратор с таким ID не найден.")
        await state.clear()
        return
    success = db.remove_admin(telegram_id)
    if success:
        await message.answer(
            f"✅ <b>Администратор удален!</b>\n\n"
            f"🆔 ID: <code>{telegram_id}</code>\n"
            f"👤 Роль: <b>{target_admin.get('role')}</b>",
            parse_mode="HTML",
            reply_markup=get_admin_management_keyboard()
        )
        try:
            await message.bot.send_message(
                telegram_id,
                "❌ <b>Ваши права администратора были отозваны.</b>\n\nВы больше не имеете доступа к панели управления.",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        await message.answer("❌ <b>Ошибка при удалении администратора</b>", parse_mode="HTML", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text and msg.text == "📝 Изменить роль админа")
async def change_role_start(message: types.Message, state: FSMContext, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    if admin.get('role') not in ('GreatAdmin', 'Owner'):
        await message.answer("⛔ Только GreatAdmin или Owner может изменять роли.")
        return
    await state.set_state(AdminStates.waiting_for_change_role_id)
    await message.answer("📝 <b>Изменение роли администратора</b>\n\nВведите Telegram ID администратора:", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_change_role_id)
async def change_role_process_id(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Изменение роли отменено.", reply_markup=get_admin_management_keyboard())
        return
    if not message.text.isdigit():
        await message.answer("❌ ID должен быть числом. Попробуйте еще раз:")
        return
    telegram_id = int(message.text)
    target_admin = db.get_admin(telegram_id)
    if not target_admin:
        await message.answer("❌ Администратор с таким ID не найден.")
        await state.clear()
        return
    if telegram_id == message.from_user.id:
        await message.answer("❌ Нельзя изменить свою собственную роль.")
        await state.clear()
        return
    await state.update_data(change_role_id=telegram_id, current_role=target_admin.get('role'))
    await state.set_state(AdminStates.waiting_for_change_role_new)
    await message.answer(f"👤 Текущая роль: <b>{target_admin.get('role')}</b>\n🆔 Администратор: <code>{telegram_id}</code>\n\nВыберите новую роль:", parse_mode="HTML", reply_markup=get_admin_role_keyboard())

@router.message(AdminStates.waiting_for_change_role_new)
async def change_role_process_new(message: types.Message, state: FSMContext, db: FDataBase):
    mapping = {"👑 GreatAdmin": "GreatAdmin", "👤 Admin": "Admin", "👥 Moderator": "Moderator"}
    if message.text not in mapping:
        await message.answer("❌ Пожалуйста, выберите роль из предложенных кнопок:")
        return
    new_role = mapping[message.text]
    data = await state.get_data()
    telegram_id = data.get('change_role_id')
    current_role = data.get('current_role')
    success = db.update_admin_role(telegram_id, new_role)
    if success:
        await message.answer(
            f"✅ <b>Роль изменена!</b>\n\n"
            f"🆔 ID: <code>{telegram_id}</code>\n"
            f"👤 Было: <b>{current_role}</b>\n"
            f"👤 Стало: <b>{new_role}</b>",
            parse_mode="HTML",
            reply_markup=get_admin_management_keyboard()
        )
        try:
            await message.bot.send_message(
                telegram_id,
                f"🔄 <b>Ваша роль администратора изменена</b>\n\n👤 Новая роль: <b>{new_role}</b>",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        await message.answer("❌ <b>Ошибка при изменении роли</b>", parse_mode="HTML", reply_markup=get_admin_management_keyboard())
    await state.clear()

@router.message(lambda msg: msg.text and msg.text == "⬅️ Назад в админку")
async def back_to_admin_panel(message: types.Message, db: FDataBase):
    await admin_panel(message, db)

@router.message(lambda msg: msg.text and msg.text == "📜 Модерация событий")
async def start_moderation(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа.")
        return
    await show_moderation_page(message, db, 0)

async def show_moderation_page(message: types.Message, db: FDataBase, page: int):
    events = db.get_pending_events_paginated(page=page, limit=1)
    total_events = db.get_total_pending_events_count()
    total_pages = max(1, total_events)
    if not events:
        await message.answer("🎉 <b>Все события проверены!</b>\n\nНет событий, ожидающих модерации.", parse_mode="HTML", reply_markup=get_admin_keyboard('Admin'))
        return
    event = events[0]
    analysis = json.loads(event.get('analysis') or '{}')
    source_icon = "🤝" if event.get('source') == 'partner' else "🔍" if event.get('source') == 'parser' else "📁"
    text = (
        f"🛡 <b>МОДЕРАЦИЯ СОБЫТИЯ</b>\n\n"
        f"{source_icon} <b>Источник:</b> {event.get('source', 'unknown')}\n"
        f"📌 <b>Название:</b> {event.get('title')}\n"
        f"📅 <b>Дата:</b> {event.get('date_str')}\n"
        f"📍 <b>Место:</b> {event.get('location')}\n"
        f"📊 <b>Оценка AI:</b> {event.get('score')}/100\n"
        f"🎯 <b>Уровень:</b> {analysis.get('level', 'не указан')}\n"
        f"👥 <b>Аудитория:</b> {analysis.get('target_audience', 'не указана')}\n"
        f"📝 <b>Регистрация:</b> {analysis.get('registration_format', 'не указан')}\n"
        f"💰 <b>Оплата:</b> {analysis.get('payment_info', 'не указано')}\n\n"
        f"💡 <b>Анализ AI:</b>\n{analysis.get('summary', 'Нет анализа')}\n\n"
        f"🏷 <b>Темы:</b> {', '.join(analysis.get('key_themes', []) if isinstance(analysis.get('key_themes', []), list) else [])}\n"
        f"💭 <b>Рекомендация:</b> {analysis.get('recommendation', 'рассмотреть')}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_moderation_keyboard(event.get('id'), page, total_pages))

@router.callback_query(F.data.startswith("mod_prev_"))
async def mod_prev_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    page = int(parts[2])
    try:
        await callback.message.delete()
    except:
        pass
    await show_moderation_page(callback.message, db, page)
    await callback.answer()

@router.callback_query(F.data.startswith("mod_next_"))
async def mod_next_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    page = int(parts[2])
    try:
        await callback.message.delete()
    except:
        pass
    await show_moderation_page(callback.message, db, page)
    await callback.answer()

@router.callback_query(F.data.startswith("approve_event_"))
async def approve_event_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    eid = int(parts[2])
    db.update_status(eid, 'approved')
    await callback.answer("✅ Событие утверждено")
    try:
        await callback.message.delete()
    except:
        pass
    await show_moderation_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("reject_event_"))
async def reject_event_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    eid = int(parts[2])
    db.update_status(eid, 'rejected')
    await callback.answer("❌ Событие отклонено")
    try:
        await callback.message.delete()
    except:
        pass
    await show_moderation_page(callback.message, db, 0)

@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    eid = int(parts[2])
    event = db.get_event_by_id(eid)
    if event:
        db.delete_event(eid)
        await callback.answer("🗑 Событие удалено")
        try:
            await callback.message.delete()
        except:
            pass
        await show_moderation_page(callback.message, db, 0)
    else:
        await callback.answer("❌ Событие не найдено")

@router.callback_query(F.data == "skip_event_mod")
async def skip_event_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    await callback.answer("⏭ Событие пропущено")
    try:
        await callback.message.delete()
    except:
        pass
    await show_moderation_page(callback.message, db, 0)

@router.message(lambda msg: msg.text and msg.text == "📝 Управление мероприятиями")
async def manage_events(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await message.answer(
        "📝 <b>Управление мероприятиями</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=get_events_management_keyboard()
    )

@router.message(lambda msg: msg.text and msg.text == "👥 Регистрации на события")
async def show_event_registrations(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    await message.answer("🔄 Загрузка списка мероприятий...")
    await show_events_list_page(message, db, 0)

async def show_events_list_page(message: types.Message, db: FDataBase, page: int):
    events = db.get_all_events_paginated(page=page, limit=10)
    total_events = db.get_total_events_count()
    total_pages = max(1, (total_events + 10 - 1) // 10)
    if not events:
        await message.answer("📭 Мероприятия не найдены.")
        return
    text = "📋 <b>Все мероприятия</b>\n\n"
    for event in events:
        status_icon = "✅" if event.get('status') == 'approved' else "⏳" if event.get('status') == 'pending' else "❌"
        text += f"{status_icon} <b>{event.get('title')}</b>\n"
        text += f"   📅 {event.get('date_str')} | 📍 {event.get('location')}\n"
        text += f"   📊 Оценка: {event.get('score')}/100 | 👥 ID: {event.get('id')}\n\n"
    text += f"📄 Страница {page + 1}/{total_pages}"
    await message.answer(text, parse_mode="HTML", reply_markup=get_events_list_keyboard(events, page, total_pages))

@router.callback_query(F.data == "manage_all_events")
async def manage_all_events_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    try:
        await callback.message.delete()
    except:
        pass
    await show_events_list_page(callback.message, db, 0)
    await callback.answer()

@router.callback_query(F.data == "create_event")
async def create_event_handler(callback: types.CallbackQuery, state: FSMContext, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    await state.set_state(AdminStates.waiting_for_event_title)
    await callback.message.answer(
        "📝 <b>Создание нового мероприятия</b>\n\nВведите название мероприятия:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "search_events_admin")
async def search_events_admin_handler(callback: types.CallbackQuery, state: FSMContext, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    await state.set_state(AdminStates.waiting_for_search_text)
    await callback.message.answer(
        "🔍 <b>Поиск мероприятий (админ)</b>\n\nВведите ключевые слова для поиска:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "registration_stats")
async def registration_stats_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    stats = db.get_stats()
    text = (
        "📊 <b>Статистика регистраций</b>\n\n"
        f"📋 Всего запросов: <b>{stats.get('total_registrations', 0)}</b>\n"
        f"⏳ Ожидают подтверждения: <b>{stats.get('pending_registrations', 0)}</b>\n"
        f"✅ Подтверждено: <b>{stats.get('total_registrations', 0) - stats.get('pending_registrations', 0)}</b>"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    try:
        await callback.message.delete()
    except:
        pass
    await admin_panel(callback.message, db)
    await callback.answer()

@router.message(AdminStates.waiting_for_event_title)
async def process_event_title(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание мероприятия отменено.", reply_markup=get_events_management_keyboard())
        return
    await state.update_data(event_title=message.text)
    await state.set_state(AdminStates.waiting_for_event_description)
    await message.answer("📝 <b>Введите описание мероприятия:</b>", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_event_description)
async def process_event_description(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание мероприятия отменено.", reply_markup=get_events_management_keyboard())
        return
    await state.update_data(event_description=message.text)
    await state.set_state(AdminStates.waiting_for_event_location)
    await message.answer("📍 <b>Введите место проведения:</b>", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_event_location)
async def process_event_location(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание мероприятия отменено.", reply_markup=get_events_management_keyboard())
        return
    await state.update_data(event_location=message.text)
    await state.set_state(AdminStates.waiting_for_event_date)
    await message.answer("📅 <b>Введите дату мероприятия:</b>\n\nПример: 25.12.2024 или 25 декабря 2024", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_event_date)
async def process_event_date(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание мероприятия отменено.", reply_markup=get_events_management_keyboard())
        return
    await state.update_data(event_date=message.text)
    await state.set_state(AdminStates.waiting_for_event_url)
    await message.answer("🔗 <b>Введите ссылку на мероприятие (если есть):</b>", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_for_event_url)
async def process_event_url(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание мероприятия отменено.", reply_markup=get_events_management_keyboard())
        return
    data = await state.get_data()
    title = data.get('event_title') or 'Без названия'
    description = data.get('event_description') or ''
    location = data.get('event_location') or ''
    date_str = data.get('event_date') or ''
    url = message.text if message.text and message.text != "❌ Отменить" else ''
    db.add_new_event(title, description, location, date_str, url, json.dumps({}, ensure_ascii=False), 0, 'medium', 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'pending')
    await state.clear()
    await message.answer("✅ Мероприятие создано и отправлено на модерацию.", reply_markup=get_events_management_keyboard())

@router.callback_query(F.data.startswith("admin_events_prev_"))
async def admin_events_prev_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer()
        return
    page = int(parts[3])
    try:
        await callback.message.delete()
    except:
        pass
    await show_events_list_page(callback.message, db, page)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_events_next_"))
async def admin_events_next_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer()
        return
    page = int(parts[3])
    try:
        await callback.message.delete()
    except:
        pass
    await show_events_list_page(callback.message, db, page)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_event_details_"))
async def admin_event_details_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("❌ Неверные данные.")
        return
    event_id = int(parts[-1])
    event = db.get_event_by_id(event_id)
    if not event:
        await callback.answer("❌ Событие не найдено")
        return
    registrations = db.get_event_registrations(event_id)
    analysis = json.loads(event.get('analysis') or '{}')
    text = (
        f"🎯 <b>{event.get('title')}</b>\n\n"
        f"📅 <b>Дата:</b> {event.get('date_str')}\n"
        f"📍 <b>Место:</b> {event.get('location')}\n"
        f"🔗 <b>Ссылка:</b> {event.get('url')}\n"
        f"📊 <b>Оценка AI:</b> {event.get('score')}/100\n"
        f"🎯 <b>Приоритет:</b> {event.get('priority')}\n"
        f"👥 <b>Аудитория:</b> {analysis.get('target_audience', 'не указана')}\n\n"
        f"📝 <b>Описание:</b>\n{event.get('description')[:500] if event.get('description') else 'Нет описания'}.\n\n"
        f"👥 <b>Зарегистрированные пользователи ({len(registrations)}):</b>\n"
    )
    for i, reg in enumerate(registrations[:10], 1):
        status_icon = "✅" if reg.get('status') == 'approved' else "⏳"
        text += f"{i}. {status_icon} {reg.get('full_name')} - {reg.get('position')}\n"
    if len(registrations) > 10:
        text += f"\n📎 ... и еще {len(registrations) - 10} пользователей"
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_keyboard(event_id))
    await callback.answer()

@router.callback_query(F.data.startswith("event_participants_"))
async def event_participants_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return
    event_id = int(parts[-1])
    await show_participants_page(callback.message, db, event_id, 0)
    await callback.answer()

async def show_participants_page(message: types.Message, db: FDataBase, event_id: int, page: int):
    registrations = db.get_event_registrations(event_id)
    event = db.get_event_by_id(event_id)
    if not event:
        await message.answer("❌ Событие не найдено")
        return
    total_pages = max(1, (len(registrations) + 5 - 1) // 5)
    start_idx = page * 5
    end_idx = start_idx + 5
    page_registrations = registrations[start_idx:end_idx]
    text = (
        f"👥 <b>Участники мероприятия</b>\n\n"
        f"🎯 <b>{event.get('title')}</b>\n"
        f"📅 {event.get('date_str')}\n\n"
        f"<b>Список участников:</b>\n"
    )
    for i, reg in enumerate(page_registrations, start_idx + 1):
        status_icon = "✅" if reg.get('status') == 'approved' else "⏳"
        text += f"{i}. {status_icon} <b>{reg.get('full_name')}</b>\n"
        text += f"   💼 {reg.get('position')}\n"
        text += f"   📅 Зарегистрирован: {reg.get('registration_date')[:10]}\n\n"
    if not registrations:
        text += "📭 Пока нет зарегистрированных участников"
    text += f"\n📄 Страница {page + 1}/{total_pages}"
    await message.answer(text, parse_mode="HTML", reply_markup=get_participants_keyboard(event_id, page, total_pages))

@router.callback_query(F.data.startswith("part_prev_"))
async def part_prev_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer()
        return
    event_id = int(parts[2])
    page = int(parts[3])
    try:
        await callback.message.delete()
    except:
        pass
    await show_participants_page(callback.message, db, event_id, page)
    await callback.answer()

@router.callback_query(F.data.startswith("part_next_"))
async def part_next_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer()
        return
    event_id = int(parts[2])
    page = int(parts[3])
    try:
        await callback.message.delete()
    except:
        pass
    await show_participants_page(callback.message, db, event_id, page)
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_event_"))
async def back_to_event_handler(callback: types.CallbackQuery, db: FDataBase):
    if not check_callback_access(callback, db):
        await callback.answer("⛔ Нет доступа.")
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer()
        return
    event_id = int(parts[3])
    event = db.get_event_by_id(event_id)
    if not event:
        await callback.answer("❌ Событие не найдено")
        return
    registrations = db.get_event_registrations(event_id)
    analysis = json.loads(event.get('analysis') or '{}')
    text = (
        f"🎯 <b>{event.get('title')}</b>\n\n"
        f"📅 <b>Дата:</b> {event.get('date_str')}\n"
        f"📍 <b>Место:</b> {event.get('location')}\n"
        f"🔗 <b>Ссылка:</b> {event.get('url')}\n"
        f"📊 <b>Оценка AI:</b> {event.get('score')}/100\n"
        f"🎯 <b>Приоритет:</b> {event.get('priority')}\n"
        f"👥 <b>Аудитория:</b> {analysis.get('target_audience', 'не указана')}\n\n"
        f"📝 <b>Описание:</b>\n{event.get('description')[:500] if event.get('description') else 'Нет описания'}.\n\n"
        f"👥 <b>Зарегистрированные пользователи ({len(registrations)}):</b>\n"
    )
    for i, reg in enumerate(registrations[:10], 1):
        status_icon = "✅" if reg.get('status') == 'approved' else "⏳"
        text += f"{i}. {status_icon} {reg.get('full_name')} - {reg.get('position')}\n"
    if len(registrations) > 10:
        text += f"\n📎 ... и еще {len(registrations) - 10} пользователей"
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_keyboard(event_id))
    await callback.answer()
