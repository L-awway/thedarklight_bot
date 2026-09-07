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
    """Создаёт пользователя, если его нет"""
    uid, data = get_user_by_username(username)
    if uid is None:
        uid = f"user_{len(users) + 1}"
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

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply(
        "👋 Бот клана The Dark Wars\n\n"
        "📌 Команды:\n"
        "/и 14 — сдать отчёт\n"
        "/я — моя статистика\n"
        "/топ — топ-5 клана\n"
        "/стата @Nick — статистика игрока\n"
        "/прогулы — список прогульщиков\n"
        "/сливы — кто часто <10 очков\n\n"
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

@dp.message(Command("топ"))
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
        text += f"{medal} {data['username']} — {total} очков (ср. {avg})\n"
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
    text = "🚫 ИГРОКИ С ПРОГУЛАМИ (>3):\n\n"
    found = False
    
    for uid, data in users.items():
        if data["skips"] > MAX_SKIPS:
            text += f"{data['username']} — {data['skips']} прогулов\n"
            found = True
    
    if not found:
        text = "✅ Нет игроков с превышением прогулов."
    
    await message.reply(text)

@dp.message(Command("сливы"))
async def warning_list(message: types.Message):
    text = "📊 ИГРОКИ, КОТОРЫМ НУЖНА ПОМОЩЬ С КОЛОДОЙ:\n\n"
    text += "Здесь собраны игроки, у которых было 3+ дня с результатом меньше 10 очков.\n"
    text += "Свяжитесь с ними, чтобы помочь улучшить колоду!\n\n"
    
    found = False  # ← ДОБАВИЛИ
    
    for uid, data in users.items():
        if data["warnings"] >= MAX_WARNINGS:
            clean_username = data['username'].replace('@', '')
            text += f"• {clean_username} — {data['warnings']} дней с низким результатом\n"
            found = True
    
    if not found:
        text = "✅ Все игроки показывают хорошие результаты! Так держать!"
    
    await message.reply(text)  # ← ПЕРЕНЕСЛИ ВНУТРЬ ФУНКЦИИ

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
        f"🕐 **Текущее время (МСК):** {now.strftime('%H:%M:%S')}\n"
        f"📅 **Дата:** {now.strftime('%d.%m.%Y')}\n"
        f"📆 **День сезона:** {day_num}/31\n"
        f"⏳ **До дедлайна (23:59):** {time_str}\n\n"
        f"📌 Команда `/и 14` — сдать отчёт"
    )

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
    
    # Добавляем (создаём пустую запись)
    new_id = f"user_{len(users) + 1}"
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
        
        new_id = f"user_{len(users) + 1}"
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

# ===================================================
# 7. УВЕДОМЛЕНИЯ (ЗА 6/3/2/1 ЧАС)
# ===================================================

async def check_and_notify():
    """Проверяет каждую минуту, нужно ли уведомлять"""
    now = get_moscow_time()
    deadline = now.replace(hour=23, minute=59, second=0, microsecond=0)
    time_left = (deadline - now).total_seconds() / 3600  # часов до дедлайна

    # Если дедлайн уже прошёл — не уведомляем
    if time_left < 0:
        return

    # Определяем, какое уведомление отправлять
    notify_hours = None
    if 5.5 < time_left <= 6.5:
        notify_hours = "6"
    elif 2.5 < time_left <= 3.5:
        notify_hours = "3"
    elif 1.5 < time_left <= 2.5:
        notify_hours = "2"
    elif 0.5 < time_left <= 1.5:
        notify_hours = "1"
    else:
        return

    # Находим неотыгравших
    day_num = str(get_season_day())
    missing = []
    for uid, data in users.items():
        if data["history"].get(day_num) is None:
            missing.append(data["username"])

    if not missing:
        return

    # Формируем сообщение
    if notify_hours in ["6", "3"]:
        msg = f"⏰ Через {notify_hours} часа дедлайн (23:59 МСК)!\nНе отчитались:\n" + "\n".join(missing)
        await bot.send_message(CHAT_ID, msg)
    else:
        msg = f"⏰ Через {notify_hours} часа! @{' @'.join([m.replace('@', '') for m in missing])} — сдайте отчёт!"
        await bot.send_message(CHAT_ID, msg)

        for username in missing:
            try:
                await bot.send_message(
                    username,
                    f"⏰ Дедлайн через {notify_hours} часа! Сдай отчёт: /и 14"
                )
            except:
                pass

# ===================================================
# 7. ФОНОВАЯ ЗАДАЧА (ОБНУЛЕНИЕ В 00:00)
# ===================================================

async def reset_today_scores():
    """Обнуляет today_score у всех игроков в 00:00"""
    for uid, data in users.items():
        data["today_score"] = 0
    save_data(db)
    await bot.send_message(CHAT_ID, "🔄 Новый день! Все результаты обнулены до 0/16. Вносите новые результаты!")
    print(f"🔄 {get_moscow_time().strftime('%H:%M')} — today_score обнулён")

async def background_tasks():
    """Фоновая задача: проверяет время и обнуляет очки"""
    last_reset_day = None  # Чтобы не обнулять несколько раз
    
    while True:
        now = get_moscow_time()
        
        # Обнуление в 00:00 (только если ещё не обнуляли сегодня)
        if now.hour == 0 and now.minute == 0 and last_reset_day != now.day:
            await reset_today_scores()
            last_reset_day = now.day
        
        await asyncio.sleep(60)  # Проверяем раз в минуту

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
