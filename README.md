🎭 Проект: helikon-opera_bot
📌 Краткое описание
Бот-помощник для музыкантов театра «Геликон-опера». Управляет личным расписанием репетиций и спектаклей, синхронизирует события с Google Calendar, парсит афишу с сайта театра и предоставляет информацию о дирижёрах.
🎯 Основные функции
✅ Управление расписанием:
   • Просмотр событий на текущую/следующую неделю
   • Добавление событий через текстовые команды
   • Удаление событий по названию и дате

✅ Синхронизация с Google Calendar:
   • Автоматическое создание событий в календаре
   • Удаление событий из календаря
   • Напоминания за 3 часа до события

✅ Парсинг сайта Геликон-оперы:
   • Автоматическое получение афиши на неделю
   • Извлечение дат, времени, залов, названий спектаклей

✅ Информация о дирижёрах:
   • База данных дирижёров по спектаклям
   • Ответ на запросы вида "Кто дирижёр «Кармен»?"

✅ Мультиплатформенность:
   • Telegram-бот (python-telegram-bot)
   • VK-бот (vkbottle)
   • Общая бизнес-логика и база данных
💬 Примеры команд пользователя
📅 Расписание:
• "Когда я работаю на этой неделе?"
• "Что у меня на следующей неделе?"
• Кнопки: [📅 Эта неделя] [🗓️ След. неделя]

➕ Добавление:
• "добавь спектакль «Кармен» 15.10 с 19:00 до 21:30 в Шаховском"
• "добавь репетицию «Алеко» 20.10 с 14:00 до 16:00 в Стравинском"

🗑️ Удаление:
• "удалить спектакль «Кармен» 15.10"

📰 Информация:
• "Новости" / "Есть ли новости?"
• "Кто дирижёр «Кармен»?"

🤖 Меню:
• "меню" или кнопка [🤖 Меню] — показать все возможности
🚀 Запуск через systemd
Telegram-бот
# /etc/systemd/system/helikon-bot.service
[Unit]
Description=Helikon Opera Telegram Bot
After=network.target

[Service]
User=cubinez85
WorkingDirectory=/home/cubinez85/helikon-opera_bot
Environment="PATH=/home/cubinez85/helikon-opera_bot/venv/bin"
ExecStart=/home/cubinez85/helikon-opera_bot/venv/bin/python /home/cubinez85/helikon-opera_bot/bot_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

VK-бот
# /etc/systemd/system/helikon-bot-vk.service
[Unit]
Description=Helikon Opera VK Bot
After=network.target

[Service]
User=cubinez85
WorkingDirectory=/home/cubinez85/helikon-opera_bot
Environment="PATH=/home/cubinez85/helikon-opera_bot/venv/bin"
ExecStart=/home/cubinez85/helikon-opera_bot/venv/bin/python /home/cubinez85/helikon-opera_bot/bot_vk.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

🛠️ Техническое обслуживание
# Проверка статуса ботов
sudo systemctl status helikon-bot helikon-bot-vk

# Просмотр логов
journalctl -u helikon-bot -f
journalctl -u helikon-bot-vk -f

# Перезапуск
sudo systemctl restart helikon-bot
sudo systemctl restart helikon-bot-vk

# Очистка старых событий из БД
cd /home/cubinez85/helikon-opera_bot
source venv/bin/activate
python -c "from db import cleanup_old_events; cleanup_old_events(365)"

# Бэкап базы данных
cp gelikon.db gelikon.db.backup.$(date +%Y%m%d)
