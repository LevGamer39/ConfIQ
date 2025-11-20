from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import json
import os

from utils.keyboards import *
from utils.states import UserStates
from database import FDataBase
from services.calendar_service import CalendarService

router = Router()

@router.message(CommandStart())
async def start(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    
    await message.answer(
        "👋 <b>Приветствуем в AI-помощнике Сбера по медиа!</b>\n\n"
        "Я помогаю сотрудникам Центра исследований и разработки Сбера в Санкт-Петербурге:\n"
        "• Находить лучшие IT-мероприятия города\n"
        "• Анализировать релевантность с помощью AI\n"
        "• Планировать участие в календаре\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def help_command(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    is_admin = bool(admin)
    
    text = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "📅 <b>Мероприятия</b> - просмотр утвержденных событий\n"
        "🔍 <b>Поиск мероприятий</b> - поиск по темам и датам\n"
    )
    
    if is_admin:
        text += "\n⚙️ <b>Админ-функции:</b>\n"
        text += "🔄 Сканирование - поиск новых мероприятий\n"
        text += "📩 Партнеры - добавление приглашений\n"
        text += "⚖️ Модерация - утверждение событий\n"
        text += "📊 Статистика - детальная аналитика\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "📊 Статистика")
async def show_public_stats(message: types.Message, db: FDataBase):
    admin = db.get_admin(message.from_user.id)
    if not admin:
        await message.answer("⛔ У вас нет доступа к этой функции.")
        return
        
    stats = db.get_stats()
    
    text = (
        "📊 <b>Статистика системы</b>\n\n"
        f"✅ Активных мероприятий: <b>{stats['approved']}</b>\n"
        f"📅 Запланировано на 2025: <b>{stats['upcoming_2025']}</b>\n"
        f"🤝 Партнерских событий: <b>{stats['partners']}</b>\n"
        f"📈 Средняя оценка: <b>{stats['avg_score']}/100</b>\n\n"
        "Используйте поиск для нахождения подходящих мероприятий!"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(lambda msg: msg.text == "📅 Мероприятия")
async def show_events(message: types.Message, db: FDataBase):
    await show_events_page(message, db, 0)

async def show_events_page(message: types.Message, db: FDataBase, page: int = 0):
    events = db.get_events_paginated(page=page, limit=5)
    total_events = db.get_total_approved_events()
    total_pages = (total_events + 4) // 5
    
    if not events:
        await message.answer(
            "📭 <b>Пока нет актуальных мероприятий</b>\n\n"
            "Новые события появятся после модерации администратором.",
            parse_mode="HTML"
        )
        return
        
    if page == 0:
        await message.answer(
            f"📅 <b>Актуальные мероприятия</b> (страница {page + 1}/{total_pages})\n\n"
            f"Всего мероприятий: {total_events}",
            parse_mode="HTML"
        )
    
    for event in events:
        analysis = json.loads(event['ai_analysis'])
        
        source_icon = "🤝" if event['source'] == 'partner' else "🔍" if event['source'] == 'parser' else "📁"
        score_emoji = "🔥" if event['score'] >= 80 else "✅" if event['score'] >= 60 else "📊"
        
        text = (
            f"{source_icon} <b>{event['title']}</b>\n"
            f"📅 {event['date_str']} | 📍 {event['location']}\n"
            f"{score_emoji} <b>Оценка:</b> {event['score']}/100\n\n"
            f"💡 {analysis.get('summary', 'Описание недоступно')}\n"
            f"👥 <b>Аудитория:</b> {analysis.get('target_audience', 'Не указана')}\n"
            f"🎯 <b>Уровень:</b> {analysis.get('level', 'Не указан')}"
        )
        
        await message.answer(
            text, 
            parse_mode="HTML", 
            reply_markup=get_event_keyboard(event['id'], event['url'], page, total_pages)
        )

@router.callback_query(F.data.startswith("prev_"))
async def prev_page_handler(callback: types.CallbackQuery, db: FDataBase):
    page = int(callback.data.split("_")[1])
    await callback.message.delete()
    await show_events_page(callback.message, db, page - 1)

@router.callback_query(F.data.startswith("next_"))
async def next_page_handler(callback: types.CallbackQuery, db: FDataBase):
    page = int(callback.data.split("_")[1])
    await callback.message.delete()
    await show_events_page(callback.message, db, page + 1)

@router.message(lambda msg: msg.text == "🔍 Поиск мероприятий")
async def search_events_start(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.waiting_for_search)
    await message.answer(
        "🔍 <b>Поиск мероприятий</b>\n\n"
        "Введите ключевые слова для поиска:\n"
        "• Тема (AI, Data Science, разработка)\n"
        "• Дата (март 2025, апрель)\n"
        "• Организатор (Сбер, Яндекс, ИТМО)\n\n"
        "Или выберите быстрый поиск:",
        parse_mode="HTML",
        reply_markup=get_search_keyboard()
    )

@router.message(UserStates.waiting_for_search)
async def search_events_process(message: types.Message, state: FSMContext, db: FDataBase):
    if message.text == "⬅️ Главное меню":
        await state.clear()
        admin = db.get_admin(message.from_user.id)
        await message.answer(
            "🔍 Поиск отменен", 
            reply_markup=get_main_keyboard(bool(admin))
        )
        return
    
    query_map = {
        "🤖 Искусственный интеллект": ["искусственный интеллект", "AI", "нейросеть", "машинное обучение", "ML"],
        "📊 Data Science": ["data science", "анализ данных", "машинное обучение", "ML", "аналитика"],
        "💻 Разработка": ["разработка", "программирование", "код", "IT", "технологии", "dev"],
        "🎯 IT-менеджмент": ["менеджмент", "управление", "проекты", "agile", "scrum", "руководство"]
    }
    
    if message.text in query_map:
        keywords = query_map[message.text]
        events = db.search_events_by_keywords(keywords, limit=10)
        query_name = message.text
    else:
        keywords = [message.text.strip()]
        events = db.search_events_by_keywords(keywords, limit=10)
        query_name = message.text
    
    if not events:
        await message.answer(
            f"🔍 <b>По запросу '{query_name}' ничего не найдено</b>\n\n"
            "Попробуйте другие ключевые слова или измените критерии поиска.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    await message.answer(
        f"🔍 <b>Результаты поиска: {query_name}</b>\n"
        f"📅 Найдено мероприятий: {len(events)}",
        parse_mode="HTML"
    )
    
    for event in events[:5]:
        analysis = json.loads(event['ai_analysis'])
        
        text = (
            f"🔥 <b>{event['title']}</b>\n"
            f"📅 {event['date_str']} | 📍 {event['location']}\n"
            f"📊 <b>Оценка:</b> {event['score']}/100\n\n"
            f"💡 {analysis.get('summary', 'Описание недоступно')}\n"
            f"👥 {analysis.get('target_audience', 'Не указана')}"
        )
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_event_keyboard(event['id'], event['url'])
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("cal_"))
async def send_calendar_file(callback: types.CallbackQuery, db: FDataBase):
    eid = int(callback.data.split("_")[1])
    event = db.get_event_by_id(eid)
    
    if not event:
        await callback.answer("❌ Событие не найдено")
        return
        
    await callback.answer("📅 Генерирую файл для календаря...")
    
    try:
        calendar_service = CalendarService()
        filename = calendar_service.generate_ics(event)
        
        file = FSInputFile(filename)
        
        await callback.message.answer_document(
            file,
            caption=(
                f"📅 <b>Файл для календаря</b>\n\n"
                f"📌 {event['title']}\n"
                f"📅 {event['date_str']}\n"
                f"📍 {event['location']}\n\n"
                f"💾 Сохраните файл и импортируйте в ваш календарь"
            ),
            parse_mode="HTML"
        )
        
        calendar_service.cleanup_file(filename)
        
    except Exception as e:
        await callback.message.answer(
            "❌ <b>Ошибка при генерации файла</b>\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML"
        )
        print(f"Calendar generation error: {e}")

@router.message(F.text == "🤖 Искусственный интеллект")
async def search_ai_events(message: types.Message, db: FDataBase):
    keywords = ["искусственный интеллект", "AI", "нейросеть", "машинное обучение", "ML"]
    events = db.search_events_by_keywords(keywords, limit=5)
    await send_search_results(message, events, "Искусственный интеллект")

@router.message(F.text == "📊 Data Science")
async def search_ds_events(message: types.Message, db: FDataBase):
    keywords = ["data science", "анализ данных", "машинное обучение", "ML", "аналитика"]
    events = db.search_events_by_keywords(keywords, limit=5)
    await send_search_results(message, events, "Data Science")

@router.message(F.text == "💻 Разработка")
async def search_dev_events(message: types.Message, db: FDataBase):
    keywords = ["разработка", "программирование", "код", "IT", "технологии", "dev"]
    events = db.search_events_by_keywords(keywords, limit=5)
    await send_search_results(message, events, "Разработка")

@router.message(F.text == "🎯 IT-менеджмент")
async def search_mgmt_events(message: types.Message, db: FDataBase):
    keywords = ["менеджмент", "управление", "проекты", "agile", "scrum", "руководство"]
    events = db.search_events_by_keywords(keywords, limit=5)
    await send_search_results(message, events, "IT-менеджмент")

async def send_search_results(message: types.Message, events: list, query_name: str):
    if not events:
        await message.answer(f"🔍 По запросу \"{query_name}\" ничего не найдено")
        return
    
    await message.answer(f"🔍 <b>Результаты по теме: {query_name}</b>", parse_mode="HTML")
    
    for event in events[:3]:
        analysis = json.loads(event['ai_analysis'])
        
        text = (
            f"📌 <b>{event['title']}</b>\n"
            f"📅 {event['date_str']} | 📍 {event['location']}\n"
            f"📊 Оценка: {event['score']}/100\n\n"
            f"💡 {analysis.get('summary', '')}"
        )
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_event_keyboard(event['id'], event['url'])
        )