# google_calendar.py
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

# Путь к файлу ключа сервисного аккаунта
SERVICE_ACCOUNT_FILE = 'service-account.json'

# ID вашего календаря (обычно совпадает с email для основного календаря)
CALENDAR_ID = 'cubinez85@gmail.com'

# Убраны лишние пробелы в scope!
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    """Создаёт клиент Google Calendar API с использованием сервисного аккаунта."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Файл сервисного аккаунта не найден: {SERVICE_ACCOUNT_FILE}")
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    # ❌ УДАЛЕНО: .with_subject() — не работает для обычных аккаунтов!
    service = build('calendar', 'v3', credentials=credentials)
    return service

def create_calendar_event(service, summary, start_time, end_time, location, description):
    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Europe/Moscow',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Europe/Moscow',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 180},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    # ✅ Используем явный CALENDAR_ID вместо 'primary'
    event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    return event['id']

def delete_calendar_event(service, event_id: str):
    """Удаляет событие из Google Calendar по его ID."""
    try:
        # ✅ Также используем CALENDAR_ID
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except Exception as e:
        logging.error(f"Ошибка при удалении события из Google Calendar: {e}")
        raise
