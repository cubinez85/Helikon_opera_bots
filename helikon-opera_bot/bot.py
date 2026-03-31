# bot.py
import logging
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from db import (
    init_db,
    create_or_update_user,
    add_event,
    get_events_for_next_week,
    get_events_for_current_week,
    delete_event
)
from parser import parse_news, get_events_for_week
from google_calendar import get_calendar_service, create_calendar_event, delete_calendar_event

# === Загрузка переменных из .env ===
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("⚠️ TELEGRAM_TOKEN не найден в .env или окружении!")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация БД при старте
init_db()

# === Клавиатуры ===

def main_keyboard():
    """Основная клавиатура с меню"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📅 Эта неделя"), KeyboardButton("🗓️ След. неделя")],
            [KeyboardButton("📰 Новости"), KeyboardButton("🤖 Меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def menu_keyboard():
    """Клавиатура внутри меню (с кнопкой 'Назад')"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# === Обработчик команды /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    create_or_update_user(user_id)
    logger.info(f"👋 Start от {user_id}")
    
    await update.message.reply_text(
        "Здравствуйте! Я ваш личный менеджер по расписанию Геликон-оперы. Чем могу помочь?",
        reply_markup=main_keyboard()
    )

# === Обработчик кнопки "Меню" ===
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"🤖 Меню запрошено от {user_id}")
    
    menu_text = """
🎭 **Геликон-опера Бот — Возможности**

📅 **Расписание:**
• Эта неделя — ваше расписание на текущую неделю
• След. неделя — расписание на следующую неделю

➕ **Добавить событие:**
• добавь спектакль «Кармен» 15.10 с 19:00 до 21:30 в Шаховском
• добавь репетицию «Алеко» 20.10 с 14:00 до 16:00 в Стравинском

🗑️ **Удалить событие:**
• удалить спектакль «Кармен» 15.10

📰 **Информация:**
• Новости — последние новости театра
• Кто дирижёр «Кармен»? — информация о дирижёре

⚙️ **Команды:**
• /start — начать работу с ботом
• /menu — показать это сообщение

💡 **Примеры запросов:**
• Когда я работаю на этой неделе?
• Какие спектакли в театре на следующей неделе?
• Есть ли новости?
"""
    
    await update.message.reply_text(menu_text, reply_markup=menu_keyboard())

# === Обработчик кнопки "Назад" ===
async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"🔙 Назад от {user_id}")
    
    await update.message.reply_text(
        "Главное меню:",
        reply_markup=main_keyboard()
    )

# === Обработчик "Эта неделя" ===
async def this_week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"📅 Эта неделя от {user_id}")
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    local_events = get_events_for_current_week(user_id)
    if local_events:
        reply = "Ваше расписание на этой неделе:\n"
        for ev in local_events:
            reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event']}» в зале {ev['hall']}.\n"
        await update.message.reply_text(reply, reply_markup=main_keyboard())
    else:
        site_events = get_events_for_week(start_of_week, end_of_week)
        if site_events:
            reply = "На этой неделе у вас пока нет записей.\n"
            reply += "Но на сайте «Геликон-опера» найдены следующие мероприятия:\n"
            for ev in site_events:
                reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
            reply += "\nХотите добавить их все в расписание? Напишите «да»."
            await update.message.reply_text(reply, reply_markup=main_keyboard())
        else:
            await update.message.reply_text("На этой неделе мероприятий не найдено.", reply_markup=main_keyboard())

# === Обработчик "След. неделя" ===
async def next_week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"🗓️ След. неделя от {user_id}")
    
    today = datetime.now().date()
    start_of_next_week = today + timedelta(days=(7 - today.weekday()))
    end_of_next_week = start_of_next_week + timedelta(days=6)
    
    local_events = get_events_for_next_week(user_id)
    if local_events:
        reply = "Ваше расписание на следующей неделе:\n"
        for ev in local_events:
            reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event']}» в зале {ev['hall']}.\n"
        await update.message.reply_text(reply, reply_markup=main_keyboard())
    else:
        site_events = get_events_for_week(start_of_next_week, end_of_next_week)
        if site_events:
            reply = "На сайте «Геликон-опера» найдены следующие мероприятия:\n"
            for ev in site_events:
                reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
            reply += "\nХотите добавить их все в расписание? Напишите «да»."
            await update.message.reply_text(reply, reply_markup=main_keyboard())
        else:
            await update.message.reply_text("На следующей неделе мероприятий не найдено.", reply_markup=main_keyboard())

# === Обработчик "Новости" ===
async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"📰 Новости от {user_id}")
    
    news = parse_news()
    if news and "Ошибка" not in news[0]:
        news_text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(news[:5]))
        await update.message.reply_text(f"Новости «Геликон-оперы»:\n{news_text}", reply_markup=main_keyboard())
    else:
        await update.message.reply_text("Не удалось загрузить новости. Попробуйте позже.", reply_markup=main_keyboard())

# === Основной обработчик сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    text_lower = text.lower()
    user_id = update.effective_user.id
    create_or_update_user(user_id)
    
    logger.info(f"📩 Получено от {user_id}: '{text}'")
    
    # === Обработка кнопок меню ===
    if text == "📅 Эта неделя":
        await this_week_handler(update, context)
        return
    
    if text == "🗓️ След. неделя":
        await next_week_handler(update, context)
        return
    
    if text == "📰 Новости":
        await news_handler(update, context)
        return
    
    if text == "🤖 Меню":
        await menu_handler(update, context)
        return
    
    if text == "🔙 Назад":
        await back_handler(update, context)
        return
    
    # === Удаление события ===
    if ("удалить" in text_lower) and ("репетиц" in text_lower or "спектакл" in text_lower):
        title_match = re.search(r'[«"\'"](.+?)[»"\'"]', text)
        if not title_match:
            await update.message.reply_text("Укажите название в кавычках, например: удалить спектакль «Кармен» 15.10", reply_markup=main_keyboard())
            return
        
        title = title_match.group(1).strip()
        
        date_match = re.search(r"(\d{1,2})[ .\-](\d{1,2})(?:[ .\-](\d{4}))?", text)
        if date_match:
            day, month = int(date_match.group(1)), int(date_match.group(2))
            year = int(date_match.group(3)) if date_match.group(3) else datetime.now().year
        else:
            month_map = {
                'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4, 'май': 5, 'июн': 6,
                'июл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12
            }
            date_match_text = re.search(r"(\d{1,2})\s+([а-яё]+)", text, re.IGNORECASE)
            if date_match_text:
                day = int(date_match_text.group(1))
                month_word = date_match_text.group(2).lower()
                month = next((v for k, v in month_map.items() if month_word.startswith(k)), None)
                if not month:
                    await update.message.reply_text("Не распознал месяц. Укажите как 15.10 или 15 октября", reply_markup=main_keyboard())
                    return
                year = datetime.now().year
            else:
                await update.message.reply_text("Укажите дату: 15.10 или 15 октября", reply_markup=main_keyboard())
                return
        
        try:
            event_date = datetime(year, month, day).date()
            date_iso = event_date.strftime("%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Некорректная дата.", reply_markup=main_keyboard())
            return
        
        cal_event_id = delete_event(user_id, title, date_iso)
        if not cal_event_id:
            await update.message.reply_text(f"Событие «{title}» на {date_iso} не найдено.", reply_markup=main_keyboard())
            return
        
        try:
            service = get_calendar_service()
            delete_calendar_event(service, cal_event_id)
        except Exception as e:
            logger.error(f"Ошибка Google Calendar: {e}")
            await update.message.reply_text(f"✅ Удалено локально, но ошибка в Google Calendar: {e}", reply_markup=main_keyboard())
            return
        
        await update.message.reply_text(f"🗑️ «{title}» на {date_iso} удалено из расписания и Google Calendar.", reply_markup=main_keyboard())
        return
    
    # === Добавление события ===
    if "добавь" in text_lower and ("репетиц" in text_lower or "спектакл" in text_lower):
        title_match = re.search(r'[«"\'"](.+?)[»"\'"]', text)
        if not title_match:
            await update.message.reply_text("Укажите название в кавычках: «В гостях у оперной сказки»", reply_markup=main_keyboard())
            return
        title = title_match.group(1).strip()
        
        date_match = re.search(r"(\d{1,2})[ .\-](\d{1,2})(?:[ .\-](\d{4}))?", text)
        if date_match:
            day, month = int(date_match.group(1)), int(date_match.group(2))
            year = int(date_match.group(3)) if date_match.group(3) else datetime.now().year
        else:
            month_map = {
                'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4, 'май': 5, 'июн': 6,
                'июл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12
            }
            date_match_text = re.search(r"(\d{1,2})\s+([а-яё]+)", text, re.IGNORECASE)
            if date_match_text:
                day = int(date_match_text.group(1))
                month_word = date_match_text.group(2).lower()
                month = next((v for k, v in month_map.items() if month_word.startswith(k)), None)
                if not month:
                    await update.message.reply_text("Не распознал месяц.", reply_markup=main_keyboard())
                    return
                year = datetime.now().year
            else:
                await update.message.reply_text("Укажите дату.", reply_markup=main_keyboard())
                return
        
        try:
            event_date = datetime(year, month, day).date()
            date_iso = event_date.strftime("%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Некорректная дата.", reply_markup=main_keyboard())
            return
        
        time_match = re.search(r"(\d{1,2}:\d{2})\s*(?:[-–]|\bдо\b)\s*(\d{1,2}:\d{2})", text, re.IGNORECASE)
        if time_match:
            start_time, end_time = time_match.group(1), time_match.group(2)
        else:
            time_match = re.search(r"(\d{1,2}:\d{2})", text)
            if not time_match:
                await update.message.reply_text("Укажите время: 14:00–15:30", reply_markup=main_keyboard())
                return
            start_time = time_match.group(1)
            duration = 1.5 if "репетиц" in text_lower else 2.5
            try:
                start_obj = datetime.strptime(start_time, "%H:%M")
                end_obj = start_obj + timedelta(hours=duration)
                end_time = end_obj.strftime("%H:%M")
            except:
                end_time = "13:30" if "репетиц" in text_lower else "21:30"
        
        hall = "Стравинский"
        if "шаховск" in text_lower:
            hall = "Шаховской"
        elif "покровск" in text_lower:
            hall = "Покровский"
        
        event_type = "репетиция" if "репетиц" in text_lower else "спектакль"
        
        try:
            service = get_calendar_service()
        except Exception as e:
            await update.message.reply_text(f"Ошибка подключения к календарю: {e}", reply_markup=main_keyboard())
            return
        
        start_dt_iso = f"{date_iso}T{start_time}:00"
        end_dt_iso = f"{date_iso}T{end_time}:00"
        summary = f"{event_type.capitalize()} «{title}»"
        location = f"Зал {hall}"
        description = "участие в оркестре — фагот"
        
        try:
            cal_id = create_calendar_event(service, summary, start_dt_iso, end_dt_iso, location, description)
        except Exception as e:
            logger.error(f"Ошибка Google Calendar: {e}")
            cal_id = ""
        
        add_event(user_id, {
            "event_name": title,
            "date": date_iso,
            "start_time": start_time,
            "end_time": end_time,
            "hall": hall,
            "event_type": event_type,
            "role": "участие в оркестре — фагот",
            "calendar_event_id": cal_id
        })
        
        await update.message.reply_text(
            f"✅ Записано: {date_iso}, {start_time}–{end_time} — {event_type} «{title}» в зале {hall}.\n"
            "Добавлено в Google Календарь с напоминанием за 3 часа.",
            reply_markup=main_keyboard()
        )
        return
    
    # === Расписание на этой неделе (текстовый запрос) ===
    if "этой неделе" in text_lower and ("работаю" in text_lower or "распис" in text_lower or "что у меня" in text_lower):
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        local_events = get_events_for_current_week(user_id)
        if local_events:
            reply = "Ваше расписание на этой неделе:\n"
            for ev in local_events:
                reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event']}» в зале {ev['hall']}.\n"
            await update.message.reply_text(reply, reply_markup=main_keyboard())
        else:
            site_events = get_events_for_week(start_of_week, end_of_week)
            if site_events:
                reply = "На этой неделе у вас пока нет записей.\n"
                reply += "Но на сайте «Геликон-опера» найдены следующие мероприятия:\n"
                for ev in site_events:
                    reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
                reply += "\nХотите добавить их все в расписание? Напишите «да»."
                await update.message.reply_text(reply, reply_markup=main_keyboard())
            else:
                await update.message.reply_text("На этой неделе мероприятий не найдено.", reply_markup=main_keyboard())
        return
    
    # === Расписание на следующей неделе (текстовый запрос) ===
    if "следующей неделе" in text_lower or ("расписание" in text_lower and "недел" in text_lower):
        today = datetime.now().date()
        start_of_next_week = today + timedelta(days=(7 - today.weekday()))
        end_of_next_week = start_of_next_week + timedelta(days=6)
        
        local_events = get_events_for_next_week(user_id)
        if local_events:
            reply = "Ваше расписание на следующей неделе:\n"
            for ev in local_events:
                reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event']}» в зале {ev['hall']}.\n"
            await update.message.reply_text(reply, reply_markup=main_keyboard())
        else:
            site_events = get_events_for_week(start_of_next_week, end_of_next_week)
            if site_events:
                reply = "На сайте «Геликон-опера» найдены следующие мероприятия:\n"
                for ev in site_events:
                    reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
                reply += "\nХотите добавить их все в расписание? Напишите «да»."
                await update.message.reply_text(reply, reply_markup=main_keyboard())
            else:
                await update.message.reply_text("На следующей неделе мероприятий не найдено.", reply_markup=main_keyboard())
        return
    
    # === Новости (текстовый запрос) ===
    if any(kw in text_lower for kw in ["новост", "ново", "актуальн", "свеж"]):
        news = parse_news()
        if news and "Ошибка" not in news[0]:
            news_text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(news[:5]))
            await update.message.reply_text(f"Новости «Геликон-оперы»:\n{news_text}", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("Не удалось загрузить новости. Попробуйте позже.", reply_markup=main_keyboard())
        return
    
    # === Дирижёр ===
    if "дириж" in text_lower:
        conductors = {
            "в гостях у оперной сказки": "Михаил Егиазарьян",
            "маддалена": "Валерий Кирьянов",
            "кармен щедрин": "Феликс Коробов",
            "кармен": "Феликс Коробов",
            "алеко": "Артем Давыдов",
            "паяцы": "Филипп Селиванов",
            "борис годунов": "Валерий Кирьянов",
            "сказки гофмана": "Феликс Коробов",
            "травиата": "Феликс Коробов",
            "тоска": "Феликс Коробов",
            "аида": "Феликс Коробов",
            "ключ на мостовой": "Артем Давыдов",
            "золушка": "Артем Давыдов",
            "диалоги кармелиток": "Феликс Коробов",
            "медиум": "Дмитрий Бертман",
            "кофейная кантата": "Дмитрий Бертман",
            "летучая мышь": "Феликс Коробов",
            "свет вифлеемской звезды": "Дмитрий Бертман",
            "новый год в сказочном городе": "Дмитрий Бертман"
        }
        
        query = text_lower
        for word in ["спектакль", "репетиц", "дириж", "кто", "«", "»", '"', "‘", "’"]:
            query = query.replace(word, "")
        query = query.strip()
        
        found = None
        for title, conductor in conductors.items():
            if title in query:
                found = (title, conductor)
                break
        
        if found:
            title, conductor = found
            await update.message.reply_text(f"Дирижёром спектакля «{title.title()}» является {conductor}.", reply_markup=main_keyboard())
        else:
            await update.message.reply_text(
                "Уточните, пожалуйста, название спектакля. Например:\n"
                "— Кто дирижёр «В гостях у оперной сказки»?\n"
                "— Кто дирижёр «Маддалены»?",
                reply_markup=main_keyboard()
            )
        return
    
    # === Подтверждение добавления списка ===
    if text_lower in ["да", "добавь"]:
        await update.message.reply_text(
            "Для добавления всех событий напишите конкретную команду.\n"
            "Например: добавь спектакль «Кармен» 15.10 с 19:00 до 21:30",
            reply_markup=main_keyboard()
        )
        return
    
    # === По умолчанию ===
    await update.message.reply_text(
        "Я помогаю с расписанием, новостями и информацией о дирижёрах.\n\n"
        "Нажмите 🤖 Меню, чтобы увидеть все возможности!",
        reply_markup=main_keyboard()
    )

def main():
    # Токен уже загружен из .env в начале файла
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    
    # Кнопки меню
    app.add_handler(MessageHandler(filters.Regex("^📅 Эта неделя$"), this_week_handler))
    app.add_handler(MessageHandler(filters.Regex("^🗓️ След. неделя$"), next_week_handler))
    app.add_handler(MessageHandler(filters.Regex("^📰 Новости$"), news_handler))
    app.add_handler(MessageHandler(filters.Regex("^🤖 Меню$"), menu_handler))
    app.add_handler(MessageHandler(filters.Regex("^🔙 Назад$"), back_handler))
    
    # Все остальные сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
