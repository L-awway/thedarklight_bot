import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime

# ===== ТВОИ ДАННЫЕ (поменяй токен на новый) =====
BOT_TOKEN = "import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime

# ===== ТВОИ ДАННЫЕ (поменяй токен на новый) =====
BOT_TOKEN = "8983642305:AAHjcQafXP0QPEgl0TQebRXWOud347-HcyI"
ADMINS = ["polllllllllllllllivi", "DanielDerecha", "Dasyero"]
MAX_SCORE = 16
LOW_SCORE_THRESHOLD = 10
MAX_WARNINGS = 3

# ===== ХРАНИЛИЩЕ В ПАМЯТИ =====
users = {}

# ===== НАСТРОЙКА =====
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== КОМАНДЫ =====
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply("👋 Бот для клана The Dark Wars работает!\n\n"
                        "📌 Команды:\n"
                        "!и 14 — сдать отчёт\n"
                        "!я — моя статистика\n"
                        "!топ — топ игроков\n"
                        "!добавить @Nick (админ)\n"
                        "!удалить @Nick (админ)")

@dp.message(Command("и"))
async def report_score(message: types.Message):
    user_id = message.from_user.id
    username = "@" + message.from_user.username if message.from_user.username else f"User{user_id}"

    try:
        score = int(message.text.split()[1])
        if score < 0 or score > MAX_SCORE:
            await message.reply(f"❗ Очки должны быть от 0 до {MAX_SCORE}")
            return
    except:
        await message.reply("❗ Используй: !и 14")
        return

    if user_id not in users:
        users[user_id] = {"username": username, "today": 0, "warnings": 0, "history": []}

    users[user_id]["today"] = score
    users[user_id]["history"].append(score)

    if 0 < score < LOW_SCORE_THRESHOLD:
        users[user_id]["warnings"] += 1
        await message.reply(f"⚠️ {score}/{MAX_SCORE} — это меньше 10! Предупреждение #{users[user_id]['warnings']}")
        if users[user_id]["warnings"] >= MAX_WARNINGS:
            await bot.send_message(-1002734456748, f"🚨 {username} — 3 предупреждения! Нужна помощь с колодой!")
    elif score == 0:
        await message.reply(f"❌ 0 очков — день потерян!")
    else:
        await message.reply(f"✅ Записано {score}/{MAX_SCORE}!")

@dp.message(Command("я"))
async def my_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users or not users[user_id]["history"]:
        await message.reply("❌ Нет данных.")
        return
    data = users[user_id]
    total = sum(data["history"])
    avg = round(total / len(data["history"]), 1)
    await message.reply(f"📊 Статистика:\n"
                        f"Сегодня: {data['today']}/{MAX_SCORE}\n"
                        f"Средний балл: {avg}\n"
                        f"Предупреждений: {data['warnings']}")

@dp.message(Command("топ"))
async def top_cmd(message: types.Message):
    if not users:
        await message.reply("❌ Нет данных.")
        return
    sorted_users = sorted(users.items(), key=lambda x: sum(x[1]["history"]), reverse=True)[:5]
    text = "🏆 ТОП-5 КЛАНА:\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        text += f"{i}. {data['username']} — {sum(data['history'])} очков\n"
    await message.reply(text)

# ===== ЗАПУСК =====
async def main():
    print("✅ Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())"
ADMINS = ["polllllllllllllllivi", "DanielDerecha", "Dasyero"]
MAX_SCORE = 16
LOW_SCORE_THRESHOLD = 10
MAX_WARNINGS = 3

# ===== ХРАНИЛИЩЕ В ПАМЯТИ =====
users = {}

# ===== НАСТРОЙКА =====
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== КОМАНДЫ =====
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply("👋 Бот для клана The Dark Wars работает!\n\n"
                        "📌 Команды:\n"
                        "!и 14 — сдать отчёт\n"
                        "!я — моя статистика\n"
                        "!топ — топ игроков\n"
                        "!добавить @Nick (админ)\n"
                        "!удалить @Nick (админ)")

@dp.message(Command("и"))
async def report_score(message: types.Message):
    user_id = message.from_user.id
    username = "@" + message.from_user.username if message.from_user.username else f"User{user_id}"

    try:
        score = int(message.text.split()[1])
        if score < 0 or score > MAX_SCORE:
            await message.reply(f"❗ Очки должны быть от 0 до {MAX_SCORE}")
            return
    except:
        await message.reply("❗ Используй: !и 14")
        return

    if user_id not in users:
        users[user_id] = {"username": username, "today": 0, "warnings": 0, "history": []}

    users[user_id]["today"] = score
    users[user_id]["history"].append(score)

    if 0 < score < LOW_SCORE_THRESHOLD:
        users[user_id]["warnings"] += 1
        await message.reply(f"⚠️ {score}/{MAX_SCORE} — это меньше 10! Предупреждение #{users[user_id]['warnings']}")
        if users[user_id]["warnings"] >= MAX_WARNINGS:
            await bot.send_message(-1002734456748, f"🚨 {username} — 3 предупреждения! Нужна помощь с колодой!")
    elif score == 0:
        await message.reply(f"❌ 0 очков — день потерян!")
    else:
        await message.reply(f"✅ Записано {score}/{MAX_SCORE}!")

@dp.message(Command("я"))
async def my_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users or not users[user_id]["history"]:
        await message.reply("❌ Нет данных.")
        return
    data = users[user_id]
    total = sum(data["history"])
    avg = round(total / len(data["history"]), 1)
    await message.reply(f"📊 Статистика:\n"
                        f"Сегодня: {data['today']}/{MAX_SCORE}\n"
                        f"Средний балл: {avg}\n"
                        f"Предупреждений: {data['warnings']}")

@dp.message(Command("топ"))
async def top_cmd(message: types.Message):
    if not users:
        await message.reply("❌ Нет данных.")
        return
    sorted_users = sorted(users.items(), key=lambda x: sum(x[1]["history"]), reverse=True)[:5]
    text = "🏆 ТОП-5 КЛАНА:\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        text += f"{i}. {data['username']} — {sum(data['history'])} очков\n"
    await message.reply(text)

# ===== ЗАПУСК =====
async def main():
    print("✅ Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
