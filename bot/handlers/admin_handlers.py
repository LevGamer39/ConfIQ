from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, BufferedInputFile
import json
import os
import io
import asyncio

from utils.keyboards import *
from utils.states import AdminStates
from database import FDataBase
from services.calendar_service import CalendarService

router = Router()

def check_access(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    return admin

@router.message(lambda msg: msg.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin:
        await message.answer("⛔ У вас нет доступа к системе управления.")
        return
    
    await message.answer(
        f"🕵️‍♂️ <b>Панель управления Media Agent</b>\n"
        f"👤 Ваша роль: <b>{admin['role']}</b>\n"
        f"🆔 Ваш ID: <code>{admin['telegram_id']}</code>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_admin_keyboard(admin['role']),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text == "⬅️ Главное меню")
async def back_to_main_menu(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    await message.answer(
        "🔙 <b>Возврат в главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text == "📊 Статистика")
async def show_stats(message: types.Message, db: FDataBase):
    if not check_access(message, db): 
        return
        
    stats = db.get_stats()
    text = (
        "📊 <b>Детальная статистика системы</b>\n\n"
        f"📂 Всего событий в базе: <b>{stats['total_events']}</b>\n"
        f"⏳ Ожидают модерации: <b>{stats['pending']}</b>\n"
        f"✅ Опубликовано: <b>{stats['approved']}</b>\n"
        f"❌ Отклонено: <b>{stats['rejected']}</b>\n"
        f"🤝 От партнеров: <b>{stats['partners']}</b>\n"
        f"📅 Запланировано на 2025: <b>{stats['upcoming_2025']}</b>\n"
        f"📈 Средняя оценка: <b>{stats['avg_score']}/100</b>\n"
        f"📆 Добавлено в этом месяце: <b>{stats['this_month']}</b>\n"
        f"👮 Администраторов: <b>{stats['total_admins']}</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "👥 Управление админами")
async def admin_manage_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin['role'] != 'GreatAdmin':
        await message.answer("⛔ Только GreatAdmin имеет доступ к управлению администраторами.")
        return
    await message.answer("👥 <b>Управление администраторами</b>\nВыберите действие:", 
                        parse_mode="HTML", 
                        reply_markup=get_admin_management_keyboard())

@router.message(lambda msg: msg.text == "📋 Список админов")
async def list_admins(message: types.Message, db: FDataBase):
    if not check_access(message, db): 
        return
        
    admins = db.get_all_admins()
    if not admins:
        await message.answer("📭 Администраторы не найдены.")
        return
        
    text = "📋 <b>Список администраторов:</b>\n\n"
    for admin in admins:
        role_icon = "👑" if admin['role'] == 'GreatAdmin' else "👤"
        text += f"{role_icon} <code>{admin['telegram_id']}</code> | {admin['role']} | @{admin['username']}\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "➕ Добавить админа")
async def add_admin_start(message: types.Message, state: FSMContext, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await state.set_state(AdminStates.waiting_for_new_admin_id)
    await message.answer(
        "👤 <b>Добавление администратора</b>\n\n"
        "Введите Telegram ID нового администратора:\n"
        "(Можно узнать через @userinfobot)",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_new_admin_id)
async def add_admin_role_select(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Добавление администратора отменено.", 
                           reply_markup=get_admin_management_keyboard())
        return
        
    if not message.text.isdigit():
        await message.answer("❌ ID должен быть числом. Попробуйте еще раз:")
        return
    
    await state.update_data(new_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_new_admin_role)
    await message.answer("Выберите роль для нового администратора:", 
                        reply_markup=get_role_keyboard())

@router.message(AdminStates.waiting_for_new_admin_role)
async def add_admin_finish(message: types.Message, state: FSMContext, db: FDataBase):
    role_map = {"👑 GreatAdmin": "GreatAdmin", "👤 Admin": "Admin"}
    
    if message.text not in role_map:
        await message.answer("❌ Пожалуйста, выберите роль из предложенных кнопок.")
        return
    
    data = await state.get_data()
    new_id = data['new_id']
    role = role_map[message.text]
    
    success = db.add_admin(new_id, "Unknown", role)
    
    if success:
        await message.answer(
            f"✅ <b>Администратор добавлен!</b>\n\n"
            f"🆔 ID: <code>{new_id}</code>\n"
            f"👤 Роль: <b>{role}</b>",
            parse_mode="HTML",
            reply_markup=get_admin_management_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при добавлении администратора</b>\n"
            "Возможно, пользователь уже является администратором.",
            parse_mode="HTML",
            reply_markup=get_admin_management_keyboard()
        )
    await state.clear()

@router.message(lambda msg: msg.text == "➖ Удалить админа")
async def remove_admin_start(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin['role'] != 'GreatAdmin':
        await message.answer("⛔ Только GreatAdmin может удалять администраторов.")
        return
        
    await message.answer(
        "🗑 <b>Удаление администратора</b>\n\n"
        "Для удаления используйте команду:\n"
        "<code>/deladmin ID_администратора</code>\n\n"
        "Пример: <code>/deladmin 123456789</code>",
        parse_mode="HTML"
    )

@router.message(lambda msg: msg.text.startswith("/deladmin"))
async def remove_admin_exec(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin['role'] != 'GreatAdmin': 
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Неверный формат команды. Используйте: /deladmin ID")
            return
            
        target_id = int(parts[1])
        
        if target_id == message.from_user.id:
            await message.answer("❌ Нельзя удалить самого себя.")
            return
            
        target_admin = db.get_admin(target_id)
        if not target_admin:
            await message.answer("❌ Администратор с таким ID не найден.")
            return
            
        db.remove_admin(target_id)
        await message.answer(f"✅ Администратор <code>{target_id}</code> удален.", parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении: {e}")

@router.message(lambda msg: msg.text == "⬅️ Назад в админ-панель")
async def back_to_panel(message: types.Message, db: FDataBase):
    await admin_panel(message, db)

@router.message(lambda msg: msg.text == "🔄 Сканировать источники")
async def start_scan(message: types.Message, db: FDataBase, gigachat, parser):
    if not check_access(message, db): 
        return
        
    await message.answer("🔍 <b>Запуск сканирования источников...</b>", parse_mode="HTML")
    
    try:
        raw_events = parser.get_events()
        count_added = 0
        count_it_related = 0
        
        for event in raw_events:
            analysis = gigachat.analyze_event(event['text'])
            
            saved = db.add_event(
                title=analysis.get('title', 'Без названия'),
                description=event['text'],
                date_str=analysis.get('date', 'Не указана'),
                location=analysis.get('location', 'СПб'),
                url=event['url'],
                ai_analysis=json.dumps(analysis, ensure_ascii=False),
                score=analysis.get('score', 0),
                is_it_related=analysis.get('is_it_related', False),
                source='parser',
                status='pending'
            )
            
            if saved:
                count_added += 1
                if analysis.get('is_it_related'):
                    count_it_related += 1
        
        text = (
            f"✅ <b>Сканирование завершено!</b>\n\n"
            f"📥 Обработано событий: {len(raw_events)}\n"
            f"💾 Добавлено в БД: {count_added}\n"
            f"🤖 IT-релевантных: {count_it_related}\n\n"
            f"Для модерации новых событий нажмите <b>⚖️ Модерация</b>"
        )
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка при сканировании:</b>\n{str(e)}", parse_mode="HTML")

@router.message(lambda msg: msg.text == "📩 Добавить от партнера")
async def partner_invite_start(message: types.Message, state: FSMContext, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await state.set_state(AdminStates.waiting_for_partner_invite)
    await message.answer(
        "🤝 <b>Добавление партнерского приглашения</b>\n\n"
        "Перешлите текст приглашения или введите описание мероприятия:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_partner_invite)
async def partner_invite_process(message: types.Message, state: FSMContext, db: FDataBase, gigachat):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Добавление приглашения отменено.", 
                           reply_markup=get_admin_keyboard())
        return

    await message.answer("🤖 <b>AI анализирует приглашение...</b>", parse_mode="HTML")
    
    try:
        analysis = gigachat.analyze_event(message.text)
        
        partner_score = min(analysis.get('score', 0) + 20, 100)
        
        db.add_event(
            title=f"🤝 {analysis.get('title', 'Партнерское событие')}",
            description=message.text,
            date_str=analysis.get('date', 'Уточнить у партнера'),
            location=analysis.get('location', 'СПб'),
            url="invite",
            ai_analysis=json.dumps(analysis, ensure_ascii=False),
            score=partner_score,
            is_it_related=True,
            source='partner',
            status='pending'
        )
        
        await state.clear()
        await message.answer(
            "✅ <b>Партнерское приглашение добавлено!</b>\n\n"
            f"📌 Название: {analysis.get('title', 'Партнерское событие')}\n"
            f"📊 Оценка AI: {partner_score}/100\n\n"
            "Событие добавлено в очередь модерации.",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка при обработке:</b>\n{str(e)}", parse_mode="HTML")
        await state.clear()

@router.message(lambda msg: msg.text == "📁 Загрузить файл")
async def file_upload_start(message: types.Message, state: FSMContext, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await state.set_state(AdminStates.waiting_for_file)
    await message.answer(
        "📁 <b>Загрузка файла с мероприятиями</b>\n\n"
        "Отправьте текстовый файл (.txt) с описанием мероприятий.\n"
        "Бот извлечет все мероприятия из текста автоматически.",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_file, F.document)
async def file_upload_process(message: types.Message, state: FSMContext, db: FDataBase, gigachat):
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте файл.")
        return

    file_name = message.document.file_name
    if not file_name.endswith('.txt'):
        await message.answer("❌ Поддерживаются только текстовые файлы .txt")
        return

    await message.answer("📥 <b>Загружаю файл...</b>", parse_mode="HTML")
    
    try:
        file = await message.bot.get_file(message.document.file_id)
        file_path = file.file_path
        
        downloaded_file = await message.bot.download_file(file_path)
        file_content = downloaded_file.read()
        
        text_content = file_content.decode('utf-8')
        
        await message.answer("🤖 <b>AI анализирует содержимое файла...</b>", parse_mode="HTML")
        
        events_from_file = gigachat.analyze_file_content(text_content)
        
        count_added = 0
        for event_data in events_from_file:
            analysis = gigachat.analyze_event(str(event_data))
            
            saved = db.add_event(
                title=analysis.get('title', event_data.get('title', 'Событие из файла')),
                description=event_data.get('description', str(event_data)),
                date_str=analysis.get('date', event_data.get('date', 'Не указана')),
                location=analysis.get('location', event_data.get('location', 'СПб')),
                url="file_upload",
                ai_analysis=json.dumps(analysis, ensure_ascii=False),
                score=analysis.get('score', 0),
                is_it_related=analysis.get('is_it_related', False),
                source='file',
                status='pending'
            )
            
            if saved:
                count_added += 1
        
        await state.clear()
        await message.answer(
            f"✅ <b>Файл обработан!</b>\n\n"
            f"📁 Файл: {file_name}\n"
            f"📝 Найдено мероприятий: {len(events_from_file)}\n"
            f"💾 Добавлено в систему: {count_added}\n\n"
            "События добавлены в очередь модерации.",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка при обработке файла:</b>\n{str(e)}", parse_mode="HTML")
        await state.clear()

@router.message(AdminStates.waiting_for_file, F.text)
async def file_upload_text_fallback(message: types.Message, state: FSMContext, db: FDataBase, gigachat):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Загрузка файла отменена.", reply_markup=get_admin_keyboard())
        return
    
    await message.answer("❌ Пожалуйста, отправьте текстовый файл (.txt)")

@router.message(lambda msg: msg.text == "🗑 Управление мероприятиями")
async def events_management(message: types.Message, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await message.answer(
        "🗑 <b>Управление мероприятиями</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_events_management_keyboard()
    )

@router.message(lambda msg: msg.text == "🗑 Удалить мероприятие")
async def delete_event_start(message: types.Message, state: FSMContext, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await state.set_state(AdminStates.waiting_for_delete_event)
    await message.answer(
        "🗑 <b>Удаление мероприятия</b>\n\n"
        "Введите ID мероприятия для удаления:\n"
        "(ID можно узнать из списка мероприятий)",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_delete_event)
async def delete_event_process(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Удаление отменено.", reply_markup=get_events_management_keyboard())
        return

    if not message.text.isdigit():
        await message.answer("❌ ID должен быть числом. Попробуйте еще раз:")
        return

    event_id = int(message.text)
    event = db.get_event_by_id(event_id)
    
    if not event:
        await message.answer("❌ Мероприятие с таким ID не найдено.")
        return

    await state.clear()
    
    text = (
        f"🗑 <b>Подтверждение удаления</b>\n\n"
        f"📌 <b>Название:</b> {event['title']}\n"
        f"📅 <b>Дата:</b> {event['date_str']}\n"
        f"📍 <b>Место:</b> {event['location']}\n"
        f"📊 <b>Оценка:</b> {event['score']}/100\n\n"
        f"Вы уверены, что хотите удалить это мероприятие?"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_delete_event_keyboard(event_id))

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_handler(callback: types.CallbackQuery, db: FDataBase):
    event_id = int(callback.data.split("_")[2])
    
    event = db.get_event_by_id(event_id)
    if event:
        db.delete_event(event_id)
        await callback.answer("✅ Мероприятие удалено")
        await callback.message.edit_text(
            f"✅ <b>Мероприятие удалено</b>\n\n"
            f"📌 {event['title']}\n"
            f"🗑 ID: {event_id}",
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Мероприятие не найдено")

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_handler(callback: types.CallbackQuery):
    await callback.answer("❌ Удаление отменено")
    await callback.message.delete()

@router.message(lambda msg: msg.text == "📋 Список мероприятий")
async def list_events_admin(message: types.Message, db: FDataBase):
    if not check_access(message, db): 
        return
        
    events = db.get_approved_events(limit=50)
    
    if not events:
        await message.answer("📭 Нет мероприятий для отображения.")
        return

    text = "📋 <b>Все мероприятия в системе:</b>\n\n"
    for event in events[:10]:
        text += f"🆔 <code>{event['id']}</code> | {event['title']}\n"
        text += f"📅 {event['date_str']} | 📍 {event['location']}\n"
        text += f"📊 {event['score']}/100 | 🔧 {event['source']}\n\n"

    if len(events) > 10:
        text += f"📎 ... и еще {len(events) - 10} мероприятий"

    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "⚖️ Модерация")
async def start_moderation(message: types.Message, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await show_next_moderation(message, db)

async def show_next_moderation(message: types.Message, db: FDataBase):
    events = db.get_pending_events()
    
    if not events:
        await message.answer(
            "🎉 <b>Все события проверены!</b>\n\n"
            "Нет событий, ожидающих модерации.",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
        return

    event = events[0]
    analysis = json.loads(event['ai_analysis'])
    
    source_icon = "🤝" if event['source'] == 'partner' else "🔍" if event['source'] == 'parser' else "📁"
    
    text = (
        f"🛡 <b>МОДЕРАЦИЯ СОБЫТИЯ</b>\n\n"
        f"{source_icon} <b>Источник:</b> {event['source']}\n"
        f"📌 <b>Название:</b> {event['title']}\n"
        f"📅 <b>Дата:</b> {event['date_str']}\n"
        f"📍 <b>Место:</b> {event['location']}\n"
        f"📊 <b>Оценка AI:</b> {event['score']}/100\n"
        f"🎯 <b>Уровень:</b> {analysis.get('level', 'не указан')}\n"
        f"👥 <b>Аудитория:</b> {analysis.get('target_audience', 'не указана')}\n\n"
        f"💡 <b>Анализ AI:</b>\n{analysis.get('summary', 'Нет анализа')}\n\n"
        f"🏷 <b>Темы:</b> {', '.join(analysis.get('key_themes', []))}\n"
        f"💭 <b>Рекомендация:</b> {analysis.get('recommendation', 'рассмотреть')}"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_moderation_keyboard(event['id']))

@router.callback_query(F.data.startswith("approve_"))
async def approve_handler(callback: types.CallbackQuery, db: FDataBase):
    eid = int(callback.data.split("_")[1])
    db.update_status(eid, 'approved')
    await callback.answer("✅ Событие утверждено")
    await callback.message.delete()
    await show_next_moderation(callback.message, db)

@router.callback_query(F.data.startswith("reject_"))
async def reject_handler(callback: types.CallbackQuery, db: FDataBase):
    eid = int(callback.data.split("_")[1])
    db.update_status(eid, 'rejected')
    await callback.answer("❌ Событие отклонено")
    await callback.message.delete()
    await show_next_moderation(callback.message, db)

@router.callback_query(F.data.startswith("delete_"))
async def delete_mod_handler(callback: types.CallbackQuery, db: FDataBase):
    eid = int(callback.data.split("_")[1])
    event = db.get_event_by_id(eid)
    
    if event:
        db.delete_event(eid)
        await callback.answer("🗑 Событие удалено")
        await callback.message.delete()
        await show_next_moderation(callback.message, db)
    else:
        await callback.answer("❌ Событие не найдено")

@router.callback_query(F.data == "skip_mod")
async def skip_handler(callback: types.CallbackQuery, db: FDataBase):
    await callback.answer("⏭ Событие пропущено")
    await callback.message.delete()
    await show_next_moderation(callback.message, db)