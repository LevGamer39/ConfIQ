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

router = Router()

def check_access(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    return admin

@router.message(lambda msg: msg.text and msg.text == "⚙️ Админ-панель")
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
    if not check_access(message, db): 
        return
        
    stats = db.get_stats()
    
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

@router.message(lambda msg: msg.text and msg.text == "👥 Управление админами")
async def admin_manage_menu(message: types.Message, db: FDataBase):
    admin = check_access(message, db)
    if not admin or admin['role'] != 'GreatAdmin':
        await message.answer("⛔ Только GreatAdmin имеет доступ к управлению администраторами.")
        return
    await message.answer("👥 <b>Управление администраторами</b>\nВыберите действие:", 
                        parse_mode="HTML", 
                        reply_markup=get_admin_management_keyboard())

@router.message(lambda msg: msg.text and msg.text == "📋 Список админов")
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

@router.message(lambda msg: msg.text and msg.text == "➕ Добавить админа")
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

@router.message(lambda msg: msg.text and msg.text == "➖ Удалить админа")
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

@router.message(lambda msg: msg.text and msg.text.startswith("/deladmin"))
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

@router.message(lambda msg: msg.text and msg.text == "⬅️ Назад в админ-панель")
async def back_to_panel(message: types.Message, db: FDataBase):
    await admin_panel(message, db)

@router.message(lambda msg: msg.text and msg.text == "🔄 Сканировать источники")
async def scan_sources_start(message: types.Message, state: FSMContext, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await state.set_state(AdminStates.waiting_for_scan_criteria)
    await message.answer(
        "🔍 <b>Сканирование источников</b>\n\n"
        "Выберите критерии для сканирования:\n"
        "• Базовое сканирование - все IT-мероприятия\n"
        "• Расширенное - с выбором тематик\n"
        "• Выборочное - конкретные источники",
        parse_mode="HTML",
        reply_markup=get_scan_type_keyboard()
    )

@router.message(AdminStates.waiting_for_scan_criteria)
async def scan_type_handler(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Сканирование отменено.", reply_markup=get_admin_keyboard())
        return
    
    if message.text == "🔍 Базовое сканирование":
        await state.update_data(scan_type="basic", themes=[], sources=[])
        await start_scan_process(message, state, db)
        return
        
    elif message.text == "🎯 Расширенное сканирование":
        await message.answer(
            "🎯 <b>Выберите тематики для сканирования:</b>",
            parse_mode="HTML",
            reply_markup=get_scan_themes_keyboard()
        )
        return
        
    elif message.text == "📋 Выборочное сканирование":
        await message.answer(
            "📋 <b>Выберите источники для сканирования:</b>",
            parse_mode="HTML",
            reply_markup=get_scan_sources_keyboard()
        )
        return
    
    await message.answer("❌ Выберите тип сканирования из меню:")

@router.callback_query(AdminStates.waiting_for_scan_criteria, F.data.startswith("scan_theme_"))
async def scan_theme_handler(callback: types.CallbackQuery, state: FSMContext):
    theme = callback.data.replace("scan_theme_", "")
    
    data = await state.get_data()
    selected_themes = data.get('themes', [])
    
    if theme == "confirm":
        if not selected_themes:
            await callback.answer("❌ Выберите хотя бы одну тематику")
            return
            
        await state.update_data(scan_type="advanced", sources=[])
        await callback.message.edit_text(
            f"🎯 <b>Выбраны тематики:</b>\n{', '.join([get_theme_display_name(t) for t in selected_themes])}\n\n"
            "Запускаю расширенное сканирование...",
            parse_mode="HTML"
        )
        await start_scan_process(callback.message, state, callback.message.bot.get("db"))
        return
        
    elif theme == "all":
        selected_themes = ["ai", "data_science", "development", "management", "security", "cloud"]
    else:
        if theme in selected_themes:
            selected_themes.remove(theme)
        else:
            selected_themes.append(theme)
    
    await state.update_data(themes=selected_themes)
    
    themes_text = "\n".join([f"✅ {get_theme_display_name(t)}" for t in selected_themes]) if selected_themes else "❌ Не выбрано"
    
    await callback.message.edit_text(
        f"🎯 <b>Выберите тематики для сканирования:</b>\n\n{themes_text}",
        parse_mode="HTML",
        reply_markup=get_scan_themes_keyboard()
    )
    await callback.answer()

@router.callback_query(AdminStates.waiting_for_scan_criteria, F.data.startswith("scan_source_"))
async def scan_source_handler(callback: types.CallbackQuery, state: FSMContext):
    source = callback.data.replace("scan_source_", "")
    
    data = await state.get_data()
    selected_sources = data.get('sources', [])
    
    if source == "confirm":
        if not selected_sources:
            await callback.answer("❌ Выберите хотя бы один источник")
            return
            
        await state.update_data(scan_type="selective", themes=[])
        await callback.message.edit_text(
            f"📋 <b>Выбраны источники:</b>\n{', '.join([get_source_display_name(s) for s in selected_sources])}\n\n"
            "Запускаю выборочное сканирование...",
            parse_mode="HTML"
        )
        await start_scan_process(callback.message, state, callback.message.bot.get("db"))
        return
        
    elif source == "all":
        selected_sources = ["it_event_hub", "it_hr_hub", "spb_prompt", "all_events"]
    else:
        if source in selected_sources:
            selected_sources.remove(source)
        else:
            selected_sources.append(source)
    
    await state.update_data(sources=selected_sources)
    
    sources_text = "\n".join([f"✅ {get_source_display_name(s)}" for s in selected_sources]) if selected_sources else "❌ Не выбрано"
    
    await callback.message.edit_text(
        f"📋 <b>Выберите источники для сканирования:</b>\n\n{sources_text}",
        parse_mode="HTML",
        reply_markup=get_scan_sources_keyboard()
    )
    await callback.answer()

async def start_scan_process(message: types.Message, state: FSMContext, db: FDataBase):
    data = await state.get_data()
    scan_type = data.get('scan_type', 'basic')
    themes = data.get('themes', [])
    sources = data.get('sources', [])
    
    await state.clear()
    
    gigachat = message.bot.get("gigachat")
    parser = message.bot.get("parser")
    
    await message.answer(
        f"🔍 <b>Запуск {get_scan_type_display_name(scan_type)}...</b>\n"
        f"<i>Это может занять некоторое время</i>",
        parse_mode="HTML"
    )
    
    try:
        loop = asyncio.get_running_loop()
        
        if scan_type == "selective" and sources:
            original_sources = parser.sources.copy()
            parser.sources = [s for s in parser.sources if s['name'].replace(' ', '_').lower() in sources]
        
        raw_events = await loop.run_in_executor(None, parser.get_events)
        
        if scan_type == "selective" and sources:
            parser.sources = original_sources
        
        count_added = 0
        count_it_related = 0
        count_filtered = 0
        
        if not raw_events:
            await message.answer("⚠️ Событий не найдено. Возможно, изменилась верстка сайтов.", parse_mode="HTML")
            return

        await message.answer(f"📥 Найдено {len(raw_events)} событий. Начинаю AI анализ...", parse_mode="HTML")

        for event in raw_events:
            analysis = await loop.run_in_executor(None, gigachat.analyze_event, event['text'])
            
            if scan_type == "advanced" and themes:
                event_themes = analysis.get('key_themes', [])
                theme_match = any(
                    any(theme_keyword in theme.lower() for theme_keyword in get_theme_keywords(t)) 
                    for t in themes 
                    for theme in event_themes
                )
                if not theme_match:
                    count_filtered += 1
                    continue
            
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
                status='pending',
                priority=analysis.get('priority', 'medium'),
                participants=analysis.get('expected_participants', 0),
                registration_info=analysis.get('registration_format', ''),
                payment_info=analysis.get('payment_info', ''),
                conditions=analysis.get('participation_conditions', '')
            )
            
            if saved:
                count_added += 1
                if analysis.get('is_it_related'):
                    count_it_related += 1
        
        text = (
            f"✅ <b>Сканирование завершено!</b>\n\n"
            f"📥 Всего найдено: {len(raw_events)}\n"
        )
        
        if scan_type == "advanced" and themes:
            text += f"🎯 Отфильтровано по тематикам: {count_filtered}\n"
        
        text += (
            f"💾 Добавлено новых: {count_added}\n"
            f"🤖 IT-релевантных: {count_it_related}\n\n"
            f"Для модерации новых событий нажмите <b>⚖️ Модерация</b>"
        )
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ <b>Ошибка при сканировании:</b>\n{str(e)}", parse_mode="HTML")

def get_scan_type_display_name(scan_type):
    names = {
        'basic': 'Базовое сканирование',
        'advanced': 'Расширенное сканирование', 
        'selective': 'Выборочное сканирование'
    }
    return names.get(scan_type, scan_type)

def get_theme_display_name(theme):
    names = {
        'ai': '🤖 Искусственный интеллект',
        'data_science': '📊 Data Science',
        'development': '💻 Разработка',
        'management': '🎯 IT-менеджмент',
        'security': '🔐 Кибербезопасность',
        'cloud': '☁️ Облачные технологии'
    }
    return names.get(theme, theme)

def get_theme_keywords(theme):
    keywords = {
        'ai': ['ai', 'искусственный интеллект', 'нейросеть', 'машинное обучение', 'ml'],
        'data_science': ['data science', 'анализ данных', 'машинное обучение', 'ml', 'аналитика'],
        'development': ['разработка', 'программирование', 'код', 'it', 'технологии', 'dev'],
        'management': ['менеджмент', 'управление', 'проекты', 'agile', 'scrum', 'руководство'],
        'security': ['кибербезопасность', 'безопасность', 'security', 'защита'],
        'cloud': ['облачные технологии', 'cloud', 'облако', 'микросервисы']
    }
    return keywords.get(theme, [])

def get_source_display_name(source):
    names = {
        'it_event_hub': '🌐 IT Event Hub',
        'it_hr_hub': '👥 IT HR Hub', 
        'spb_prompt': '🏛️ SPb Prompt',
        'all_events': '📅 All Events'
    }
    return names.get(source, source)

@router.message(lambda msg: msg.text and msg.text == "📩 Добавить от партнера")
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
            status='pending',
            priority='high',
            participants=analysis.get('expected_participants', 0),
            registration_info=analysis.get('registration_format', ''),
            payment_info=analysis.get('payment_info', ''),
            conditions=analysis.get('participation_conditions', '')
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

@router.message(lambda msg: msg.text and msg.text == "📁 Загрузить файл")
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
                status='pending',
                priority=analysis.get('priority', 'medium'),
                participants=analysis.get('expected_participants', 0),
                registration_info=analysis.get('registration_format', ''),
                payment_info=analysis.get('payment_info', ''),
                conditions=analysis.get('participation_conditions', '')
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

@router.message(lambda msg: msg.text and msg.text == "🗑 Управление мероприятиями")
async def events_management(message: types.Message, db: FDataBase):
    if not check_access(message, db): 
        return
        
    await message.answer(
        "🗑 <b>Управление мероприятиями</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_events_management_keyboard()
    )

@router.message(lambda msg: msg.text and msg.text == "🗑 Удалить мероприятие")
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

@router.message(lambda msg: msg.text and msg.text == "📋 Список мероприятий")
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

@router.message(lambda msg: msg.text and msg.text == "⚖️ Модерация")
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
        f"👥 <b>Аудитория:</b> {analysis.get('target_audience', 'не указана')}\n"
        f"📝 <b>Регистрация:</b> {analysis.get('registration_format', 'не указан')}\n"
        f"💰 <b>Оплата:</b> {analysis.get('payment_info', 'не указано')}\n\n"
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

@router.callback_query(F.data == "stop_moderation")
async def stop_moderation_handler(callback: types.CallbackQuery, db: FDataBase):
    await callback.answer("🚪 Модерация завершена")
    await callback.message.delete()
    await admin_panel(callback.message, db)