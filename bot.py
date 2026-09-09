import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime, timedelta

# ===================================================
# 1. НАСТРОЙКИ (ПОМЕНЯЙ ТОКЕН)
# ===================================================
BOT_TOKEN = "8983642305:AAHjcQafXP0QPEgl0TQebRXWOud347-HcyI"
CHAT_ID = -1002734456748
ADMINS = ["polllllllllllllllivi", "DanielDerecha", "Dasyero", "Ahahanta", "Zhongli_3112", "Kyoruk"]

MAX_SCORE = 16
LOW_SCORE_THRESHOLD = 10
MAX_WARNINGS = 3
MAX_SKIPS = 3
TIMEZONE_OFFSET = 3
DATA_FILE = "data.json"

# ===================================================
# 2. РАБОТА С ДАННЫМИ (JSON)
# ===================================================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Загружаем данные
db = load_data()
users = db["users"]

def get_next_user_id():
    """Генерирует следующий свободный ID (user_1, user_2, ...)"""
    used_ids = set()
    for uid in users.keys():
        if uid.startswith("user_"):
            try:
                num = int(uid.split("_")[1])
                used_ids.add(num)
            except:
                pass
    
    next_num = 1
    while next_num in used_ids:
        next_num += 1
    
    return f"user_{next_num}"
# Для отслеживания уведомлений (чтобы не спамить)
last_notify_hour = None
# ===================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОИСКА ПО USERNAME
# ===================================================

def get_user_by_username(username):
    """Находит пользователя по username (регистронезависимо)"""
    username_lower = username.lower()
    for uid, data in users.items():
        if data["username"].lower() == username_lower:
            return uid, data
    return None, None

def ensure_user_exists(username):
    """Создаёт пользователя, если его нет (с уникальным ID)"""
    uid, data = get_user_by_username(username)
    if uid is None:
        uid = get_next_user_id()  # ← НОВАЯ ЛОГИКА!
        users[uid] = {
            "username": username,
            "today_score": 0,
            "warnings": 0,
            "skips": 0,
            "history": {str(d): None for d in range(1, 32)}
        }
        save_data(db)
    return uid, users[uid]

# ===================================================
# 3. ДАТА И СЕЗОНЫ (БЕЗ PYTZ)
# ===================================================
def get_moscow_time():
    """Возвращает текущее время по Москве (UTC+3)"""
    return datetime.utcnow() + timedelta(hours=3)

def get_season_day():
    """Возвращает номер дня в сезоне (1-31)"""
    now = get_moscow_time()
    # Сезон начинается 5-го числа в 00:00
    if now.day >= 5:
        season_start = datetime(now.year, now.month, 5, 0, 0)
        day_num = (now - season_start).days + 1
    else:
        # Если 1-4 число, сезон начался в прошлом месяце
        if now.month == 1:
            season_start = datetime(now.year - 1, 12, 5, 0, 0)
        else:
            season_start = datetime(now.year, now.month - 1, 5, 0, 0)
        day_num = (now - season_start).days + 1
    return min(day_num, 31)

def is_deadline_passed():
    """Проверяет, можно ли сдавать отчёт за сегодня"""
    now = get_moscow_time()
    # Если сейчас 00:00 или позже — сегодняшний день уже начался
    # Если сейчас 23:59 — ещё можно сдать
    return False  # Всегда можно сдавать! (проверка дедлайна — в уведомлениях)

# ===================================================
# 4. БОТ
# ===================================================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===================================================
# 5. КОМАНДЫ ДЛЯ ВСЕХ
# ===================================================

@dp.message(Command("старт"))
async def start_cmd(message: types.Message):
    await message.reply(
        "👋 Бот клана The Dark Wars\n\n"
        "📌 Команды:\n"
        "/и 14 — сдать отчёт\n"
        "/я — моя статистика\n"
        "/топовость — топ-5 клана\n"
        "/стата @Nick — статистика игрока\n"
        "/прогулы — список прогульщиков\n"
        "/сливы — кто часто <10 очков\n"
        "/дедлайн — тегает всех неотыгравших\n\n"
        "👑 Админы:\n"
        "/добавить @Nick\n"
        "/удалить @Nick\n"
        "/зарегистрировать @Nick1 @Nick2 ...\n"
        "/исправить @Nick 14\n"
        "/состав"
    )

@dp.message(Command("и"))
async def report_score(message: types.Message):
    args = message.text.split()

    target_username = None
    if len(args) >= 3 and args[1].startswith("@"):
        if message.from_user.username not in ADMINS:
            await message.reply("⛔ Только админы могут писать за других.")
            return
        target_username = args[1]
        try:
            score = int(args[2])
        except:
            await message.reply("❗ Используйте: /и @Nick 14")
            return
    else:
        if len(args) < 2:
            await message.reply("❗ Используйте: /и 14")
            return
        try:
            score = int(args[1])
        except:
            await message.reply("❗ Используйте: /и 14")
            return
        
        # Определяем username игрока
        username = "@" + message.from_user.username if message.from_user.username else None
        
        if not username:
            await message.reply("❌ У вас не установлен юзернейм! Установите его в настройках Telegram.")
            return
        
        # Проверяем, есть ли игрок в базе
        uid, data = get_user_by_username(username)
        if uid is None:
            await message.reply("❌ Вы не зарегистрированы в клане! Обратитесь к администратору для регистрации.")
            return
        
        target_username = username

    if score < 0 or score > MAX_SCORE:
        await message.reply(f"❗ Очки должны быть от 0 до {MAX_SCORE}")
        return

    # Находим или создаём пользователя
    uid, user_data = ensure_user_exists(target_username)
    day_num = str(get_season_day())

    # Проверка: если сегодня уже сдал
    if user_data["history"].get(day_num) is not None:
        await message.reply("❗ Ты уже сдал отчёт сегодня!")
        return

    # Сохраняем результат
    user_data["history"][day_num] = score
    user_data["today_score"] = score
    save_data(db)

    # Логика предупреждений
    if score == 0:
        user_data["warnings"] += 1
        await message.reply(f"😅 {user_data['username']} — 0 очков! Неудачный день. Слив #{user_data['warnings']}")
        if user_data["warnings"] >= MAX_WARNINGS:
            await bot.send_message(
                CHAT_ID,
                f"⚠️ {user_data['username']} — {user_data['warnings']} дней с результатом <10! Работаем над колодой."
            )
    elif score < LOW_SCORE_THRESHOLD:
        user_data["warnings"] += 1
        await message.reply(f"⚠️ {score}/{MAX_SCORE} — ниже 10! Слив #{user_data['warnings']}")
        if user_data["warnings"] >= MAX_WARNINGS:
            await bot.send_message(
                CHAT_ID,
                f"⚠️ {user_data['username']} — {user_data['warnings']} дней с результатом <10! Работаем над колодой."
            )
    else:
        await message.reply(f"✅ {user_data['username']} — {score}/{MAX_SCORE}!")

    save_data(db)

@dp.message(Command("я"))
async def my_stats(message: types.Message):
    username = "@" + message.from_user.username if message.from_user.username else None
    
    if not username:
        await message.reply("❌ У вас не установлен юзернейм! Установите его в настройках Telegram.")
        return
    
    uid, data = get_user_by_username(username)
    if uid is None:
        await message.reply("❌ Нет данных. Сдайте отчёт: /и 14")
        return
    
    scores = [s for s in data["history"].values() if s is not None]
    total = sum(scores) if scores else 0
    avg = round(total / len(scores), 1) if scores else 0
    
    await message.reply(
        f"📊 Статистика {data['username']}:\n"
        f"Сегодня: {data['today_score']}/{MAX_SCORE}\n"
        f"Прогулов: {data['skips']}/{MAX_SKIPS}\n"
        f"Предупреждений: {data['warnings']} (из {MAX_WARNINGS})\n"
        f"Средний балл: {avg}\n"
        f"Дней в сезоне: {len(scores)}"
    )

@dp.message(Command("топовость"))
async def top_cmd(message: types.Message):
    if not users:
        await message.reply("❌ Нет данных.")
        return
    
    # Сортируем по сумме очков
    sorted_users = sorted(
        users.items(),
        key=lambda x: sum(s for s in x[1]["history"].values() if s is not None),
        reverse=True
    )
    top = sorted_users[:5]
    
    text = "🏆 ТОП-5 КЛАНА:\n"
    for i, (uid, data) in enumerate(top, 1):
        scores = [s for s in data["history"].values() if s is not None]
        total = sum(scores) if scores else 0
        avg = round(total / len(scores), 1) if scores else 0
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        clean_username = data['username'].replace('@', '')
        text += f"{medal} {clean_username} — {total} очков (ср. {avg})\n"
    await message.reply(text)

@dp.message(Command("стата"))
async def player_stats(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: /стата @Nickname")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    for uid, data in users.items():
        if data["username"] == username:
            scores = [s for s in data["history"].values() if s is not None]
            total = sum(scores) if scores else 0
            avg = round(total / len(scores), 1) if scores else 0
            await message.reply(
                f"📊 Статистика {username}:\n"
                f"Прогулов: {data['skips']}/{MAX_SKIPS}\n"
                f"Предупреждений: {data['warnings']} (из {MAX_WARNINGS})\n"
                f"Средний балл: {avg}\n"
                f"Дней в сезоне: {len(scores)}"
            )
            return
    
    await message.reply(f"❌ Игрок {username} не найден.")

@dp.message(Command("прогулы"))
async def skip_list(message: types.Message):
    # Собираем всех игроков с прогулами
    skip_list = []
    for uid, data in users.items():
        if data["skips"] > 0:
            clean_username = data['username'].replace('@', '')
            skip_list.append((clean_username, data["skips"]))
    
    if not skip_list:
        await message.reply("✅ Нет игроков с прогулами! Все молодцы!")
        return
    
    # Сортируем по убыванию (кто больше прогулял — тот выше)
    skip_list.sort(key=lambda x: x[1], reverse=True)
    
    text = "🚫 РЕЙТИНГ ПРОГУЛЬЩИКОВ\n\n"
    text += "Чем выше в списке — тем больше прогулов.\n"
    text += "3+ прогула — повод задуматься об удалении!\n\n"
    
    for i, (username, count) in enumerate(skip_list, 1):
        medal = ""
        if count >= 3:
            medal = "🔴 "  # критично
        elif count >= 2:
            medal = "🟡 "  # предупреждение
        else:
            medal = "🟢 "  # первый раз
        
        text += f"{i}. {medal}{username} — {count}\n"
    
    await message.reply(text)

@dp.message(Command("сливы"))
async def warning_list(message: types.Message):
    # Собираем всех игроков со сливами
    warning_list = []
    for uid, data in users.items():
        if data["warnings"] > 0:
            clean_username = data['username'].replace('@', '')
            warning_list.append((clean_username, data["warnings"]))
    
    if not warning_list:
        await message.reply("✅ Все игроки показывают хорошие результаты! Так держать!")
        return
    
    # Сортируем по убыванию (кто больше слил — тот выше)
    warning_list.sort(key=lambda x: x[1], reverse=True)
    
    text = "📊 РЕЙТИНГ СЛИВОВ (дней с результатом <10 очков)\n\n"
    text += "Чем выше в списке — тем больше дней с низким результатом.\n"
    text += "3+ дня — нужна помощь с колодой!\n\n"
    
    for i, (username, count) in enumerate(warning_list, 1):
        medal = ""
        if count >= 3:
            medal = "🔴 "  # критично
        elif count >= 2:
            medal = "🟡 "  # предупреждение
        else:
            medal = "🟢 "  # первый раз
        
        text += f"{i}. {medal}{username} — {count} дней\n"
    
    await message.reply(text)

@dp.message(Command("время"))
async def show_time(message: types.Message):
    now = get_moscow_time()
    deadline = now.replace(hour=23, minute=59, second=0, microsecond=0)
    time_left = (deadline - now).total_seconds()
    
    # Форматируем оставшееся время
    if time_left > 0:
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        time_str = f"{hours} ч {minutes} мин {seconds} сек"
    else:
        time_str = "⏰ Дедлайн уже прошёл! Ожидайте следующий день."
    
    day_num = get_season_day()
    
    await message.reply(
        f"🕐 Текущее время (МСК): {now.strftime('%H:%M:%S')}\n"
        f"📅 Дата: {now.strftime('%d.%m.%Y')}\n"
        f"📆 День сезона: {day_num}/31\n"
        f"⏳ До дедлайна (23:59): {time_str}\n\n"
        f"📌 Команда `/и 14` — сдать отчёт"
    )

@dp.message(Command("дедлайн"))
async def show_deadline(message: types.Message):
    """Показывает, сколько осталось до дедлайна, и список неотыгравших с @"""
    now = get_moscow_time()
    deadline = now.replace(hour=23, minute=59, second=0, microsecond=0)
    time_left = (deadline - now).total_seconds()
    
    # Форматируем оставшееся время
    if time_left > 0:
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        time_str = f"{hours} ч {minutes} мин {seconds} сек"
    else:
        time_str = "⏰ Дедлайн уже прошёл! Ожидайте следующий день."
    
    # Находим неотыгравших (с @)
    day_num = str(get_season_day())
    missing = []
    for uid, data in users.items():
        if data["history"].get(day_num) is None:
            missing.append(data["username"])  # ← ОСТАВЛЯЕМ С @
    
    # Формируем сообщение
    msg = f"⏳ До дедлайна (23:59 МСК): {time_str}\n\n"
    
    if missing:
        msg += f"🚫 Не отыграли ({len(missing)} чел.):\n" + "\n".join(missing)
    else:
        msg += "✅ Все отыграли! Молодцы!"
    
    await message.reply(msg)
# ===================================================
# 6. АДМИН-КОМАНДЫ
# ===================================================

def is_admin(username):
    return username in ADMINS

@dp.message(Command("добавить"))
async def add_user(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: /добавить @Nickname")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    # Проверяем, есть ли уже
    for uid, data in users.items():
        if data["username"] == username:
            await message.reply(f"❌ {username} уже в клане.")
            return
    
    # Добавляем с уникальным ID
    new_id = get_next_user_id()  # ← НОВАЯ ЛОГИКА!
    users[new_id] = {
        "username": username,
        "today_score": 0,
        "warnings": 0,
        "skips": 0,
        "history": {str(d): None for d in range(1, 32)}
    }
    save_data(db)
    await message.reply(f"✅ {username} добавлен в клан!")

@dp.message(Command("зарегистрировать"))
async def register_many(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()[1:]
    if not args:
        await message.reply("❗ Используйте: /зарегистрировать @Nick1 @Nick2 ...")
        return
    
    count = 0
    for username in args:
        if not username.startswith("@"):
            username = "@" + username
        
        # Проверяем, есть ли уже
        exists = False
        for uid, data in users.items():
            if data["username"] == username:
                exists = True
                break
        if exists:
            continue
        
        # Добавляем с уникальным ID
        new_id = get_next_user_id()  # ← НОВАЯ ЛОГИКА!
        users[new_id] = {
            "username": username,
            "today_score": 0,
            "warnings": 0,
            "skips": 0,
            "history": {str(d): None for d in range(1, 32)}
        }
        count += 1
    
    save_data(db)
    await message.reply(f"✅ Добавлено {count} игроков.")

@dp.message(Command("удалить"))
async def remove_user(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: /удалить @Nickname")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    for uid, data in list(users.items()):
        if data["username"] == username:
            del users[uid]
            save_data(db)
            await message.reply(f"✅ {username} удалён из клана.")
            return
    
    await message.reply(f"❌ {username} не найден.")

@dp.message(Command("исправить"))
async def fix_score(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❗ Используйте: /исправить @Nickname 14")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    try:
        new_score = int(args[2])
        if new_score < 0 or new_score > MAX_SCORE:
            await message.reply(f"❗ Очки должны быть от 0 до {MAX_SCORE}")
            return
    except:
        await message.reply("❗ Введите число, например: /исправить @Nick 14")
        return
    
    for uid, data in users.items():
        if data["username"] == username:
            day_num = str(get_season_day())
            old_score = data["history"].get(day_num)
            data["history"][day_num] = new_score
            data["today_score"] = new_score
            
            # Пересчитываем предупреждения и прогулы (для простоты оставляем старые)
            save_data(db)
            await message.reply(f"✅ {username}: {old_score} → {new_score} исправлено.")
            return
    
    await message.reply(f"❌ {username} не найден.")

@dp.message(Command("состав"))
async def show_roster(message: types.Message):
    if not users:
        await message.reply("❌ В клане пока нет игроков.")
        return
    
    text = "👥 СОСТАВ КЛАНА:\n\n"
    for uid, data in users.items():
        clean_username = data['username'].replace('@', '')
        text += f"{clean_username} — сегодня: {data['today_score']}/{MAX_SCORE}\n"
    
    await message.reply(text)

@dp.message(Command("сброс"))
async def reset_season(message: types.Message):
    if message.from_user.username != "polllllllllllllllivi":
        await message.reply("⛔ Только владелец может сбросить сезон.")
        return
    
    # Сброс всех данных
    for uid in users:
        users[uid]["today_score"] = 0
        users[uid]["warnings"] = 0
        users[uid]["skips"] = 0
        users[uid]["history"] = {str(d): None for d in range(1, 32)}
    
    save_data(db)
    await message.reply("✅ Сезон сброшен! Все данные обнулены.")
    
@dp.message(Command("уведомление"))
async def test_notify(message: types.Message):
    if message.from_user.username not in ADMINS:
        await message.reply("⛔ Только для админов.")
        return
    
    await check_and_notify()
    await message.reply("✅ Уведомление проверено!")

# ===================================================
# 7. УВЕДОМЛЕНИЯ (ЗА 6/3/2/1 ЧАС)
# ===================================================

async def check_and_notify():
    """Отправляет уведомления в указанные часы (в любую минуту)"""
    
    now = get_moscow_time()
    current_hour = now.hour
    current_minute = now.minute
    
    print(f"🔍 check_and_notify вызван в {now.strftime('%H:%M')}")  # ← ЛОГ
    
    if current_hour not in [18, 21, 23]:
        print(f"⏳ Час {current_hour} не разрешён")  # ← ЛОГ
        return
    
    print(f"📨 Час {current_hour} разрешён, ищем неотыгравших")  # ← ЛОГ
    
    day_num = str(get_season_day())
    missing = []
    for uid, data in users.items():
        if data["history"].get(day_num) is None:
            missing.append(data["username"])
    
    print(f"📊 Найдено неотыгравших: {len(missing)}")  # ← ЛОГ
    
    if missing:
        msg = "🚨 **СПИСОК НЕОТЫГРАВШИХ**\n\n"
        msg += "Эти игроки ещё не сдали отчёт за сегодня:\n\n"
        msg += "\n".join(missing)
    else:
        msg = "✅ **Все отыграли! Молодцы!**"
    
    await bot.send_message(CHAT_ID, msg)
    print(f"✅ Уведомление отправлено в {now.strftime('%H:%M')}")  # ← ЛОГ
# ===================================================
# 7. ФОНОВАЯ ЗАДАЧА (ОБНУЛЕНИЕ В 00:00)
# ===================================================

async def reset_today_scores():
    """Обнуляет today_score у всех игроков в 00:00 и считает прогулы (с 3-го дня)"""
    for uid, data in users.items():
        # Проверяем, сдал ли игрок отчёт за вчерашний день
        day_num = get_season_day() - 1  # Вчерашний день
        
        # Прогулы считаем только с 3-го дня
        if day_num >= 3:
            if str(day_num) in data["history"] and data["history"][str(day_num)] is None:
                data["skips"] += 1
        
        # Обнуляем today_score для нового дня
        data["today_score"] = 0
    
    save_data(db)
    await bot.send_message(CHAT_ID, "🔄 Новый день! Все результаты обнулены до 0/16. Вносите новые результаты!")
    print(f"🔄 {get_moscow_time().strftime('%H:%M')} — today_score обнулён, прогулы подсчитаны")

# ===================================================
# 8. ФОНОВАЯ ЗАДАЧА (БЕЗ ЛИШНИХ ПРОВЕРОК)
# ===================================================

async def background_tasks():
    """Фоновая задача: вызывает /дедлайн в 18:00, 21:00, 23:00"""
    
    while True:
        now = get_moscow_time()
        
        # Список задач: (час, минута, функция)
        tasks = [
            (19, 37, show_deadline),   # ← ТЕСТ В 19:20
            (18, 0, show_deadline),
            (21, 0, show_deadline),
            (23, 0, show_deadline),
            (0, 0, reset_today_scores)
]
        
        # Находим ближайшую задачу
        next_task_time = None
        next_task_func = None
        
        for hour, minute, func in tasks:
            task_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if task_time < now:
                task_time += timedelta(days=1)
            
            if next_task_time is None or task_time < next_task_time:
                next_task_time = task_time
                next_task_func = func
        
        wait_seconds = (next_task_time - now).total_seconds()
        
        # Ждём ровно до нужного времени
        await asyncio.sleep(wait_seconds)
        
        # Выполняем задачу (show_deadline или reset_today_scores)
        await next_task_func()
# ===================================================
# 8. ЗАПУСК
# ===================================================

async def main():
    print("🚀 Бот запущен!")
    print(f"📅 Текущий день сезона: {get_season_day()}")
    
    # Запускаем фоновую задачу для уведомлений (каждую минуту)
    asyncio.create_task(background_tasks())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
