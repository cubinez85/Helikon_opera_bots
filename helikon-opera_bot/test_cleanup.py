#!/usr/bin/env python3
# test_cleanup.py — Тест функций очистки БД

from db import cleanup_old_events, get_db_stats

print("📊 Статистика базы данных:")
print("=" * 50)

stats = get_db_stats()
print(f"   Размер файла: {stats['db_size_mb']} МБ")
print(f"   Всего событий: {stats['total_events']}")
print(f"   Всего пользователей: {stats['total_users']}")
print(f"   Старейшее событие: {stats['oldest_event'] or 'нет данных'}")
print(f"   Новейшее событие: {stats['newest_event'] or 'нет данных'}")
print("=" * 50)

print("\n🗑️ Запуск очистки (события старше 365 дней)...")
deleted = cleanup_old_events(days_old=365)
print(f"✅ Удалено событий: {deleted}")

print("\n📊 Статистика после очистки:")
print("=" * 50)
stats = get_db_stats()
print(f"   Размер файла: {stats['db_size_mb']} МБ")
print(f"   Всего событий: {stats['total_events']}")
print("=" * 50)
