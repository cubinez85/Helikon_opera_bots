# bot_vk.py — Геликон-опера VK-бот с меню
import logging
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle.tools import Keyboard, KeyboardButtonColor, Text

# === Загрузка переменных из .env ===
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

VK_TOKEN = os.getenv("VK_TOKEN")

if not VK_TOKEN:
    raise ValueError("⚠️ VK_TOKEN не найден в .env!")

# === Настройка логирования ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(VK_TOKEN)

# === Импорт ваших модулей ===
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

# Инициализация БД
init_db()

# === Клавиатуры ===

def main_keyboard():
    """Основная клавиатура с меню"""
    return (
        Keyboard(one_time=False, inline=False)
        .add(Text("📅 Эта неделя"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("🗓️ След. неделя"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("📰 Новости"), color=KeyboardButtonColor.SECONDARY)
        .add(Text("🤖 Меню"), color=KeyboardButtonColor.POSITIVE)
        .get_json()
    )

def menu_keyboard():
    """Клавиатура внутри меню (с кнопкой 'Назад')"""
    return (
        Keyboard(one_time=False, inline=False)
        .add(Text("🔙 Назад"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )

# === Обработчик /start или "привет" ===
@bot.on.message(text=["привет", "Привет", "/старт", "/start", "старт"])
async def hello_handler(message: Message):
    user_id = message.from_id
    create_or_update_user(user_id)
    logger.info(f"👋 Start от {user_id}")
    
    await message.answer(
        "Здравствуйте! Я ваш личный менеджер по расписанию Геликон-оперы. Чем могу помочь?",
        keyboard=main_keyboard()
    )

# === Обработчик кнопки "Меню" ===
@bot.on.message(text=["🤖 Меню", "Меню", "меню", "/menu"])
async def menu_handler(message: Message):
    user_id = message.from_id
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
• привет — начать работу с ботом
• меню — показать это сообщение

💡 **Примеры запросов:**
• Когда я работаю на этой неделе?
• Какие спектакли в театре на следующей неделе?
• Есть ли новости?
"""
    
    await message.answer(menu_text, keyboard=menu_keyboard())

# === Обработчик кнопки "Назад" ===
@bot.on.message(text=["🔙 Назад", "Назад", "назад"])
async def back_handler(message: Message):
    user_id = message.from_id
    logger.info(f"🔙 Назад от {user_id}")
    
    await message.answer(
        "Главное меню:",
        keyboard=main_keyboard()
    )

# === Обработчик "Эта неделя" ===
@bot.on.message(text=["📅 Эта неделя", "Эта неделя", "эта неделя"])
async def this_week_handler(message: Message):
    user_id = message.from_id
    logger.info(f"📅 Эта неделя от {user_id}")
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    local_events = get_events_for_current_week(user_id)
    if local_events:
        reply = "Ваше расписание на этой неделе:\n"
        for ev in local_events:
            reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event']}» в зале {ev['hall']}.\n"
        await message.answer(reply, keyboard=main_keyboard())
    else:
        site_events = get_events_for_week(start_of_week, end_of_week)
        if site_events:
            reply = "На этой неделе у вас пока нет записей.\n"
            reply += "Но на сайте «Геликон-опера» найдены следующие мероприятия:\n"
            for ev in site_events:
                reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
            reply += "\nХотите добавить их все в расписание? Напишите «да»."
            await message.answer(reply, keyboard=main_keyboard())
        else:
            await message.answer("На этой неделе мероприятий не найдено.", keyboard=main_keyboard())

# === Обработчик "След. неделя" ===
@bot.on.message(text=["🗓️ След. неделя", "Следующая неделя", "след неделя", "на следующей неделе"])
async def next_week_handler(message: Message):
    user_id = message.from_id
    logger.info(f"🗓️ След. неделя от {user_id}")
    
    today = datetime.now().date()
    start_of_next_week = today + timedelta(days=(7 - today.weekday()))
    end_of_next_week = start_of_next_week + timedelta(days=6)
    
    local_events = get_events_for_next_week(user_id)
    if local_events:
        reply = "Ваше расписание на следующей неделе:\n"
        for ev in local_events:
            reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event']}» в зале {ev['hall']}.\n"
        await message.answer(reply, keyboard=main_keyboard())
    else:
        site_events = get_events_for_week(start_of_next_week, end_of_next_week)
        if site_events:
            reply = "На сайте «Геликон-опера» найдены следующие мероприятия:\n"
            for ev in site_events:
                reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
            reply += "\nХотите добавить их все в расписание? Напишите «да»."
            await message.answer(reply, keyboard=main_keyboard())
        else:
            await message.answer("На следующей неделе мероприятий не найдено.", keyboard=main_keyboard())

# === Обработчик "Новости" ===
@bot.on.message(text=["📰 Новости", "Новости", "новости", "есть ли новости"])
async def news_handler(message: Message):
    user_id = message.from_id
    logger.info(f"📰 Новости от {user_id}")
    
    news = parse_news()
    if news and "Ошибка" not in news[0]:
        news_text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(news[:5]))
        await message.answer(f"Новости «Геликон-оперы»:\n{news_text}", keyboard=main_keyboard())
    else:
        await message.answer("Не удалось загрузить новости. Попробуйте позже.", keyboard=main_keyboard())

# === Основной обработчик сообщений ===
@bot.on.message()
async def handle_message(message: Message):
    text = message.text.strip() if message.text else ""
    text_lower = text.lower()
    user_id = message.from_id
    create_or_update_user(user_id)
    
    logger.info(f"📩 Получено от {user_id}: '{text}'")
    
    # === Удаление события ===
    if ("удалить" in text_lower) and ("репетиц" in text_lower or "спектакл" in text_lower):
        title_match = re.search(r'[«"\'"](.+?)[»"\'"]', text)
        if not title_match:
            await message.answer("Укажите название в кавычках, например: удалить спектакль «Кармен» 15.10", keyboard=main_keyboard())
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
                    await message.answer("Не распознал месяц. Укажите как 15.10 или 15 октября", keyboard=main_keyboard())
                    return
                year = datetime.now().year
            else:
                await message.answer("Укажите дату: 15.10 или 15 октября", keyboard=main_keyboard())
                return
        
        try:
            event_date = datetime(year, month, day).date()
            date_iso = event_date.strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Некорректная дата.", keyboard=main_keyboard())
            return
        
        cal_event_id = delete_event(user_id, title, date_iso)
        if not cal_event_id:
            await message.answer(f"Событие «{title}» на {date_iso} не найдено.", keyboard=main_keyboard())
            return
        
        try:
            service = get_calendar_service()
            delete_calendar_event(service, cal_event_id)
        except Exception as e:
            logger.error(f"Ошибка Google Calendar: {e}")
            await message.answer(f"✅ Удалено локально, но ошибка в Google Calendar: {e}", keyboard=main_keyboard())
            return
        
        await message.answer(f"🗑️ «{title}» на {date_iso} удалено из расписания и Google Calendar.", keyboard=main_keyboard())
        return
    
    # === Добавление события ===
    if "добавь" in text_lower and ("репетиц" in text_lower or "спектакл" in text_lower):
        title_match = re.search(r'[«"\'"](.+?)[»"\'"]', text)
        if not title_match:
            await message.answer("Укажите название в кавычках: «В гостях у оперной сказки»", keyboard=main_keyboard())
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
                    await message.answer("Не распознал месяц.", keyboard=main_keyboard())
                    return
                year = datetime.now().year
            else:
                await message.answer("Укажите дату.", keyboard=main_keyboard())
                return
        
        try:
            event_date = datetime(year, month, day).date()
            date_iso = event_date.strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Некорректная дата.", keyboard=main_keyboard())
            return
        
        time_match = re.search(r"(\d{1,2}:\d{2})\s*(?:[-–]|\bдо\b)\s*(\d{1,2}:\d{2})", text, re.IGNORECASE)
        if time_match:
            start_time, end_time = time_match.group(1), time_match.group(2)
        else:
            time_match = re.search(r"(\d{1,2}:\d{2})", text)
            if not time_match:
                await message.answer("Укажите время: 14:00–15:30", keyboard=main_keyboard())
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
            await message.answer(f"Ошибка подключения к календарю: {e}", keyboard=main_keyboard())
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
        
        await message.answer(
            f"✅ Записано: {date_iso}, {start_time}–{end_time} — {event_type} «{title}» в зале {hall}.\n"
            "Добавлено в Google Календарь с напоминанием за 3 часа.",
            keyboard=main_keyboard()
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
            await message.answer(reply, keyboard=main_keyboard())
        else:
            site_events = get_events_for_week(start_of_week, end_of_week)
            if site_events:
                reply = "На этой неделе у вас пока нет записей.\n"
                reply += "Но на сайте «Геликон-опера» найдены следующие мероприятия:\n"
                for ev in site_events:
                    reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
                reply += "\nХотите добавить их все в расписание? Напишите «да»."
                await message.answer(reply, keyboard=main_keyboard())
            else:
                await message.answer("На этой неделе мероприятий не найдено.", keyboard=main_keyboard())
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
            await message.answer(reply, keyboard=main_keyboard())
        else:
            site_events = get_events_for_week(start_of_next_week, end_of_next_week)
            if site_events:
                reply = "На сайте «Геликон-опера» найдены следующие мероприятия:\n"
                for ev in site_events:
                    reply += f"- {ev['date']}, {ev['start']}–{ev['end']} — {ev['type']} «{ev['event_name']}» в зале {ev['hall']}.\n"
                reply += "\nХотите добавить их все в расписание? Напишите «да»."
                await message.answer(reply, keyboard=main_keyboard())
            else:
                await message.answer("На следующей неделе мероприятий не найдено.", keyboard=main_keyboard())
        return
    
    # === Новости (текстовый запрос) ===
    if any(kw in text_lower for kw in ["новост", "ново", "актуальн", "свеж"]):
        news = parse_news()
        if news and "Ошибка" not in news[0]:
            news_text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(news[:5]))
            await message.answer(f"Новости «Геликон-оперы»:\n{news_text}", keyboard=main_keyboard())
        else:
            await message.answer("Не удалось загрузить новости. Попробуйте позже.", keyboard=main_keyboard())
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
            await message.answer(f"Дирижёром спектакля «{title.title()}» является {conductor}.", keyboard=main_keyboard())
        else:
            await message.answer(
                "Уточните, пожалуйста, название спектакля. Например:\n"
                "— Кто дирижёр «В гостях у оперной сказки»?\n"
                "— Кто дирижёр «Маддалены»?",
                keyboard=main_keyboard()
            )
        return
    
    # === Подтверждение добавления списка ===
    if text_lower in ["да", "добавь"]:
        # Логика добавления всех событий из pending_events
        # (если вы используете context.user_data в Telegram, в VK нужно хранить иначе)
        await message.answer(
            "Для добавления всех событий напишите конкретную команду.\n"
            "Например: добавь спектакль «Кармен» 15.10 с 19:00 до 21:30",
            keyboard=main_keyboard()
        )
        return
    
    # === По умолчанию ===
    await message.answer(
        "Я помогаю с расписанием, новостями и информацией о дирижёрах.\n\n"
        "Нажмите 🤖 Меню, чтобы увидеть все возможности!",
        keyboard=main_keyboard()
    )

# === Запуск ===
if __name__ == "__main__":
    logger.info("🚀 Helikon Opera VK Bot starting...")
    bot.run_forever()
