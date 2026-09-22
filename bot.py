import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime, timedelta
from aiogram.types import FSInputFile

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
current_raid = None
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
            "history": {str(d): None for d in range(1, 32)},
            "bank": 0,
            "bank_blocked_until": None,
            "last_bank_accrual_day": None
        }
        save_data(db)
    return uid, users[uid]

def accrue_bank(user_data, score):
    """Начисляет/списывает банк в зависимости от очков за день"""
    day_num = str(get_season_day())
    
    # Проверяем блокировку
    blocked_until = user_data.get("bank_blocked_until")
    if blocked_until:
        today_str = get_moscow_time().strftime("%Y-%m-%d")
        if today_str <= blocked_until:
            return 0  # Заблокирован
    
    # Проверяем, не начисляли ли уже сегодня
    if user_data.get("last_bank_accrual_day") == day_num:
        return 0
    
    # Определяем изменение банка
    delta = 0
    if score == 16:
        delta = 1.0
    elif 13 <= score <= 14:
        delta = 0.5
    elif 11 <= score <= 12:
        delta = 0.25
    elif 8 <= score <= 9:
        delta = -0.25
    elif 6 <= score <= 7:
        delta = -0.5
    elif score <= 5:
        delta = -1.0
    
    if delta != 0:
        current_bank = user_data.get("bank", 0)
        new_bank = round(current_bank + delta, 2)
        
        # Минимальный баланс = 0
        if new_bank < 0:
            new_bank = 0
        
        user_data["bank"] = new_bank
        user_data["last_bank_accrual_day"] = day_num
    
    return delta
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
    # ===== 1. ОТПРАВЛЯЕМ ВИДЕО =====
    try:
        video = FSInputFile("video.mp4")
        await message.reply_video(
            video=video,
            caption="👋 Добро пожаловать в бота клана The Dark Wars of Light!"
        )
    except Exception as e:
        print(f"⚠️ Видео не загрузилось: {e}")
    
    await message.reply(
        "📌 КОМАНДЫ ДЛЯ ВСЕХ:\n"
        "/и 14 — сдать отчёт\n"
        "/я — моя статистика\n"
        "/банк — мой банк\n"
        "/топовость — топ-5 клана\n"
        "/стата @Nick — статистика игрока\n"
        "/прогулы — список прогульщиков\n"
        "/сливы — кто часто <10 очков\n"
        "/дедлайн — кто не отыграл\n"
        "/+рейд — записаться на рейд\n"
        "/-рейд — отписаться от рейда\n"
        "/рейдинфо — информация о рейде\n\n"
        
        "👑 КОМАНДЫ ДЛЯ АДМИНОВ:\n"
        "/добавить @Nick\n"
        "/удалить @Nick\n"
        "/зарегистрировать @Nick1 @Nick2 ...\n"
        "/исправить @Nick 14\n"
        "/куплено @Nick 5 — списать\n"
        "/штраф @Nick 5 — блокировка банка\n"
        "/отменаштрафа @Nick — снять блокировку\n"
        "/рейд 21:00 — создать рейд\n"
        "/отменарейда — отменить рейд\n"
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
    
    # Начисляем банк
        # Начисляем банк
    accrued = accrue_bank(user_data, score)
    if accrued > 0:
        await message.reply(f"🏦 В банк начислено: +{accrued} пт. Баланс: {user_data['bank']} пт")
    elif accrued < 0:
        await message.reply(f"🏦 Из банка списано: {accrued} пт. Баланс: {user_data['bank']} пт")

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
        f"🏦 Банк: {data.get('bank', 0)} пт\n"
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
                f"📊 Статистика {data['username']}:\n"
                f"Сегодня: {data['today_score']}/{MAX_SCORE}\n"
                f"🏦 Банк: {data.get('bank', 0)} пт\n"
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
    
@dp.message(Command("банк"))
async def my_bank(message: types.Message):
    """Показывает баланс банка игрока"""
    username = "@" + message.from_user.username if message.from_user.username else None
    
    if not username:
        await message.reply("❌ У вас не установлен юзернейм! Установите его в настройках Telegram.")
        return
    
    uid, data = get_user_by_username(username)
    if uid is None:
        await message.reply("❌ Вы не зарегистрированы в клане!")
        return
    
    bank = data.get("bank", 0)
    
    # Проверяем блокировку
    blocked_until = data.get("bank_blocked_until")
    blocked_text = ""
    if blocked_until and get_moscow_time().strftime("%Y-%m-%d") <= blocked_until:
        blocked_text = f"\n⛔ Начисление в банк заблокировано до {blocked_until}"
    
    await message.reply(
        f"🏦 Банк {data['username']}\n\n"
        f"Баланс: {bank} пт{blocked_text}"
    )
    
@dp.message(Command("+рейд"))
async def join_raid(message: types.Message):
    global current_raid
    
    # Проверяем, есть ли активный рейд
    if current_raid is None:
        await message.reply("❌ Сейчас нет активного рейда.")
        return
    
    # Определяем username
    username = "@" + message.from_user.username if message.from_user.username else None
    if not username:
        await message.reply("❌ У вас не установлен юзернейм!")
        return
    
    # Проверяем, есть ли уже в списке
    if username in current_raid["members"]:
        await message.reply("❌ Ты уже зарегался на рейд!")
        return
    
    # Добавляем в список
    current_raid["members"].append(username)
    
    await message.reply(
        f"✅ {username} записан на рейд в {current_raid['time']} МСК!\n"
        f"👥 Всего записано: {len(current_raid['members'])}"
    )
    
@dp.message(Command("-рейд"))
async def leave_raid(message: types.Message):
    global current_raid
    
    # Проверяем, есть ли активный рейд
    if current_raid is None:
        await message.reply("❌ Сейчас нет активного рейда.")
        return
    
    # Определяем username
    username = "@" + message.from_user.username if message.from_user.username else None
    if not username:
        await message.reply("❌ У вас не установлен юзернейм!")
        return
    
    # Проверяем, записан ли игрок
    if username not in current_raid["members"]:
        await message.reply("❌ Ты не записан на рейд.")
        return
    
    # Удаляем из списка
    current_raid["members"].remove(username)
    
    await message.reply(
        f"✅ {username} отписан от рейда на {current_raid['time']} МСК.\n"
        f"👥 Осталось участников: {len(current_raid['members'])}"
    )
    
@dp.message(Command("рейдинфо"))
async def raid_info(message: types.Message):
    """Показывает информацию о текущем рейде"""
    if current_raid is None:
        await message.reply("ℹ️ Сейчас нет активного рейда.")
        return
    
    now = get_moscow_time()
    raid_dt = current_raid["raid_datetime"]
    time_to_raid = (raid_dt - now).total_seconds() / 60  # в минутах
    
    # Форматируем время
    if time_to_raid < 0:
        time_str = "⏰ Рейд уже начался!"
    elif time_to_raid < 60:
        time_str = f"⏳ До рейда: {int(time_to_raid)} мин"
    else:
        hours = int(time_to_raid // 60)
        minutes = int(time_to_raid % 60)
        time_str = f"⏳ До рейда: {hours} ч {minutes} мин"
    
    members = current_raid["members"]
    # Убираем @ для отображения
    members_clean = [m.replace("@", "") for m in members]
    members_str = "\n".join(members_clean) if members_clean else "❌ Никто не записался"
    
    msg = (
        f"📋 **ИНФОРМАЦИЯ О РЕЙДЕ**\n\n"
        f"🕐 Время: {current_raid['time']} МСК\n"
        f"{time_str}\n"
        f"👥 Участники ({len(members)} чел.):\n{members_str}"
    )
    
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
        "history": {str(d): None for d in range(1, 32)},
        "bank": 0,
        "bank_blocked_until": None,
        "last_bank_accrual_day": None
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
            "history": {str(d): None for d in range(1, 32)},
            "bank": 0,
            "bank_blocked_until": None,
            "last_bank_accrual_day": None
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
            
            # ===== ОТМЕНЯЕМ СТАРОЕ НАЧИСЛЕНИЕ БАНКА =====
            if old_score is not None and data.get("last_bank_accrual_day") == day_num:
                # Определяем, сколько было начислено/списано в прошлый раз
                old_delta = 0
                if old_score == 16:
                    old_delta = 1.0
                elif 13 <= old_score <= 14:
                    old_delta = 0.5
                elif 11 <= old_score <= 12:
                    old_delta = 0.25
                elif 8 <= old_score <= 9:
                    old_delta = -0.25
                elif 6 <= old_score <= 7:
                    old_delta = -0.5
                elif old_score <= 5:
                    old_delta = -1.0
                
                # Откатываем банк
                data["bank"] = round(data.get("bank", 0) - old_delta, 2)
                
                # Не уходим в минус
                if data["bank"] < 0:
                    data["bank"] = 0
                
                # Сбрасываем флаг, чтобы можно было начислить заново
                data["last_bank_accrual_day"] = None
            
            # ===== ЗАПИСЫВАЕМ НОВОЕ ЗНАЧЕНИЕ =====
            data["history"][day_num] = new_score
            data["today_score"] = new_score
            
            # ===== НАЧИСЛЯЕМ БАНК ЗА НОВОЕ ЗНАЧЕНИЕ =====
            new_delta = accrue_bank(data, new_score)
            
            save_data(db)
            
            # Формируем ответ
            bank_info = ""
            if new_delta > 0:
                bank_info = f"\n🏦 В банк начислено: +{new_delta} пт. Баланс: {data['bank']} пт"
            elif new_delta < 0:
                bank_info = f"\n🏦 Из банка списано: {new_delta} пт. Баланс: {data['bank']} пт"
            elif data.get("bank_blocked_until"):
                bank_info = f"\n⛔ Начисление в банк заблокировано"
            else:
                bank_info = f"\n🏦 Банк без изменений. Баланс: {data['bank']} пт"
            
            await message.reply(
                f"✅ {username}: {old_score} → {new_score} исправлено.{bank_info}"
            )
            return
    
    await message.reply(f"❌ {username} не найден.")

@dp.message(Command("куплено"))
async def bank_purchase(message: types.Message):
    """Админ: списать/начислить банк игроку"""
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❗ Используйте: /куплено @Nickname 5 или /куплено @Nickname -5")
        return
    
    # Определяем пользователя
    target_username = args[1]
    if not target_username.startswith("@"):
        target_username = "@" + target_username
    
    # Определяем сумму
    try:
        amount = float(args[2].replace(",", "."))
    except:
        await message.reply("❗ Введите число, например: /куплено @Nick 5")
        return
    
    # Ищем игрока
    uid, data = get_user_by_username(target_username)
    if uid is None:
        await message.reply(f"❌ {target_username} не найден.")
        return
    
    current_bank = data.get("bank", 0)
    
    # Если списание (положительное число) — проверяем, хватает ли
    if amount > 0:
        if current_bank < amount:
            await message.reply(
                f"❌ У {target_username} недостаточно средств.\n"
                f"Баланс: {current_bank} пт, нужно: {amount} пт"
            )
            return
        new_bank = round(current_bank - amount, 2)
        data["bank"] = new_bank
        save_data(db)
        await message.reply(
            f"✅ Списано {amount} пт у {target_username}.\n"
            f"Новый баланс: {new_bank} пт"
        )
    else:
        # Начисление (отрицательное число)
        add_amount = abs(amount)
        new_bank = round(current_bank + add_amount, 2)
        data["bank"] = new_bank
        save_data(db)
        await message.reply(
            f"✅ Начислено {add_amount} пт игроку {target_username}.\n"
            f"Новый баланс: {new_bank} пт"
        )
    
@dp.message(Command("штраф"))
async def bank_penalty(message: types.Message):
    """Админ: блокирует начисление банка на N дней"""
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❗ Используйте: /штраф @Nickname 5")
        return
    
    # Определяем пользователя
    target_username = args[1]
    if not target_username.startswith("@"):
        target_username = "@" + target_username
    
    # Определяем количество дней
    try:
        days = int(args[2])
        if days <= 0:
            await message.reply("❗ Количество дней должно быть больше 0.")
            return
    except:
        await message.reply("❗ Введите число, например: /штраф @Nick 5")
        return
    
    # Ищем игрока
    uid, data = get_user_by_username(target_username)
    if uid is None:
        await message.reply(f"❌ {target_username} не найден.")
        return
    
    # Считаем дату окончания блокировки
    blocked_until = (get_moscow_time() + timedelta(days=days)).strftime("%Y-%m-%d")
    data["bank_blocked_until"] = blocked_until
    save_data(db)
    
    await message.reply(
        f"🚫 {target_username} — начисление в банк заблокировано на {days} дней.\n"
        f"⛔ Разблокировка: {blocked_until}"
    )
    
@dp.message(Command("отменаштрафа"))
async def bank_unblock(message: types.Message):
    """Админ: снимает блокировку начисления банка"""
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: /отменаштрафа @Nickname")
        return
    
    # Определяем пользователя
    target_username = args[1]
    if not target_username.startswith("@"):
        target_username = "@" + target_username
    
    # Ищем игрока
    uid, data = get_user_by_username(target_username)
    if uid is None:
        await message.reply(f"❌ {target_username} не найден.")
        return
    
    # Проверяем, есть ли вообще блокировка
    blocked_until = data.get("bank_blocked_until")
    if not blocked_until:
        await message.reply(f"ℹ️ У {target_username} нет активной блокировки.")
        return
    
    # Снимаем блокировку
    data["bank_blocked_until"] = None
    save_data(db)
    
    await message.reply(
        f"✅ {target_username} — блокировка начисления банка снята.\n"
        f"🏦 Начисления снова активны."
    )
    
@dp.message(Command("рейд"))
async def create_raid(message: types.Message):
    global current_raid  # ← ВАЖНО! Чтобы менять глобальную переменную
    
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    # Проверяем, нет ли уже активного рейда
    if current_raid is not None:
        await message.reply("❌ Уже есть активный рейд! Сначала отмените его: /отменарейда")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: /рейд 21:00")
        return
    
    # Парсим время
    try:
        raid_time = args[1]  # "21:00"
        hour, minute = map(int, raid_time.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.reply("❗ Неверный формат времени. Используйте: /рейд 21:00")
        return
    
    # Проверяем, не прошло ли время
    now = get_moscow_time()
    raid_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    if raid_datetime <= now:
        # Время прошло — переносим на завтра
        raid_datetime += timedelta(days=1)
    
    # Создаём рейд
    current_raid = {
        "time": f"{hour:02d}:{minute:02d}",
        "raid_datetime": raid_datetime,
        "members": [],
        "notified_today": None
    }
    
    await message.reply(
        f"🚀 Рейд создан на {hour:02d}:{minute:02d} МСК!\n"
        f"📝 Записывайтесь командой: `/+рейд`"
    )
    
@dp.message(Command("отменарейда"))
async def cancel_raid(message: types.Message):
    global current_raid
    
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    if current_raid is None:
        await message.reply("ℹ️ Нет активного рейда.")
        return
    
    # Сбрасываем рейд
    time_was = current_raid["time"]
    current_raid = None
    
    await message.reply(f"🗑️ Рейд на {time_was} МСК отменён.")
    
@dp.message(Command("состав"))
async def show_roster(message: types.Message):
    if not users:
        await message.reply("❌ В клане пока нет игроков.")
        return
    
    day_num = str(get_season_day())
    
    # Собираем игроков
    players = []
    for uid, data in users.items():
        clean_username = data['username'].replace('@', '')
        today_history = data["history"].get(day_num)
        today_score = data['today_score']
        players.append((clean_username, today_score, today_history))
    
    # Сортируем: сначала отыгравшие (по убыванию очков), потом неотыгравшие
    players.sort(key=lambda x: (x[2] is None, -x[1] if x[1] is not None else 0))
    
    text = "👥 СОСТАВ КЛАНА:\n\n"
    for username, score, today_history in players:
        if today_history is None:
            # Не отыграл — без иконки
            text += f"{username}\n"
        else:
            # Отыграл — ставим иконку
            if score == 16:
                icon = "❤️‍🔥"
            elif 11 <= score <= 15:
                icon = "❤️"
            elif score == 10:
                icon = "✅"
            elif 5 <= score <= 9:
                icon = "⚠️"
            elif 1 <= score <= 4:
                icon = "❌"
            else:  # 0
                icon = "💀"
            
            text += f"{username} — {score}/{MAX_SCORE} {icon}\n"
    
    await message.reply(text)
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

    
    
async def send_deadline_notification():
    """Отправляет уведомление о дедлайне (для автоматического вызова)"""
    now = get_moscow_time()
    
    day_num = str(get_season_day())
    missing = []
    for uid, data in users.items():
        if data["history"].get(day_num) is None:
            missing.append(data["username"])
    
    deadline = now.replace(hour=23, minute=59, second=0, microsecond=0)
    time_left = (deadline - now).total_seconds()
    
    if time_left > 0:
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        time_str = f"{hours} ч {minutes} мин"
    else:
        time_str = "⏰ Дедлайн прошёл!"
    
    msg = f"⏳ До дедлайна (23:59 МСК): {time_str}\n\n"
    
    if missing:
        msg += f"🚫 Не отыграли ({len(missing)} чел.):\n" + "\n".join(missing)
    else:
        msg += "✅ Все отыграли! Молодцы!"
    
    await bot.send_message(CHAT_ID, msg)
    print(f"📨 Уведомление отправлено в {now.strftime('%H:%M')}")
# ===================================================
# 8. ФОНОВАЯ ЗАДАЧА (БЕЗ ЛИШНИХ ПРОВЕРОК)
# ===================================================

async def background_tasks():
    """Фоновая задача: события по расписанию + проверка рейда"""
    
    print("🔄 Фоновая задача запущена")
    
    while True:
        now = get_moscow_time()
        
        # ===== ЕСЛИ ЕСТЬ РЕЙД — СПИМ 60 СЕК И ПРОВЕРЯЕМ =====
        if current_raid is not None:
            raid_dt = current_raid["raid_datetime"]
            time_to_raid = (raid_dt - now).total_seconds() / 60  # в минутах
            
            # Уведомление за 5 минут
            if 0 < time_to_raid <= 5 and current_raid.get("notified_today") is None:
                await send_raid_notification()
                current_raid["notified_today"] = get_moscow_time().strftime("%Y-%m-%d")
            
            # Рейд прошёл — удаляем
            if time_to_raid <= 0:
                await finish_raid()
            
            # Спим 60 секунд и проверяем снова
            await asyncio.sleep(60)
            continue
        
        # ===== РЕЙДА НЕТ — ОБЫЧНЫЕ СОБЫТИЯ =====
        events = [
            (18, 0, send_deadline_notification),
            (21, 0, send_deadline_notification),
            (23, 0, send_deadline_notification),
            (0, 0, reset_today_scores)
        ]
        
        # Находим ближайшее событие
        next_event_time = None
        next_event_func = None
        
        for hour, minute, func in events:
            event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if event_time <= now:
                event_time += timedelta(days=1)
            if next_event_time is None or event_time < next_event_time:
                next_event_time = event_time
                next_event_func = func
        
        # Спим до события, НО максимум 60 секунд (чтобы узнать про новый рейд)
        wait_seconds = (next_event_time - now).total_seconds()
        sleep_time = min(60, wait_seconds)
        
        print(f"⏳ Ближайшее событие в {next_event_time.strftime('%H:%M')}, спим {int(sleep_time)} сек")
        await asyncio.sleep(sleep_time)
        
        # Проверяем, не настало ли время события
        now = get_moscow_time()
        for hour, minute, func in events:
            if now.hour == hour and now.minute == minute:
                await func()
                break
        
async def send_raid_notification():
    """Отправляет уведомление о рейде (за 5 минут)"""
    global current_raid
    
    if current_raid is None:
        return
    
    members = current_raid["members"]
    
    if members:
        msg = (
            f"🚀 РЕЙД ЧЕРЕЗ 5 МИНУТ! (в {current_raid['time']} МСК)\n\n"
            f"👥 Участники ({len(members)} чел.):\n"
            + "\n".join(members)
        )
    else:
        msg = (
            f"⚠️ РЕЙД ЧЕРЕЗ 5 МИНУТ! (в {current_raid['time']} МСК)\n\n"
            f"❌ Никто не записался! Записывайтесь: /+рейд "
        )
    
    await bot.send_message(CHAT_ID, msg)
    print(f"📨 Уведомление о рейде отправлено в {get_moscow_time().strftime('%H:%M')}")


async def finish_raid():
    """Завершает рейд (удаляет после старта)"""
    global current_raid
    
    if current_raid is None:
        return
    
    time_was = current_raid["time"]
    current_raid = None
    print(f"🗑️ Рейд на {time_was} завершён")
# ===================================================
# 8. ЗАПУСК
# ===================================================

async def main():
    print("🚀 Бот запущен!")
    print(f"📅 Текущий день сезона: {get_season_day()}")
    
    # Запускаем фоновую задачу для уведомлений (каждую минуту)
    asyncio.create_task(background_tasks())
    
    await dp.start_polling(bot)
