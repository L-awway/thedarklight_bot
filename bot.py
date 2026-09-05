import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime

# ===== ТВОЙ НОВЫЙ ТОКЕН =====
BOT_TOKEN = "8983642305:AAHjcQafXP0QPEgl0TQebRXWOud347-HcyI"

# ===== НАСТРОЙКИ =====
MAX_SCORE = 16
LOW_SCORE_THRESHOLD = 10
MAX_WARNINGS = 3

users = {}
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply("👋 Бот клана работает! Просто пиши: !и 14")

@dp.message(Command("и"))
async def report_score(message: types.Message):
    user_id = message.from_user.id
    username = "@" + message.from_user.username if message.from_user.username else f"User{user_id}"

    try:
        score = int(message.text.split()[1])
        if score < 0 or score > MAX_SCORE:
            await message.reply(f"❗ От 0 до {MAX_SCORE}")
            return
    except:
        await message.reply("❗ Пример: !и 14")
        return

    if user_id not in users:
        users[user_id] = {"username": username, "today": 0, "warnings": 0, "history": []}

    users[user_id]["today"] = score
    users[user_id]["history"].append(score)

    if 0 < score < LOW_SCORE_THRESHOLD:
        users[user_id]["warnings"] += 1
        await message.reply(f"⚠️ Предупреждение #{users[user_id]['warnings']}")
    elif score == 0:
        await message.reply(f"❌ 0 очков")
    else:
        await message.reply(f"✅ Записано {score}/{MAX_SCORE}")

@dp.message(Command("я"))
async def my_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users or not users[user_id]["history"]:
        await message.reply("❌ Нет данных.")
        return
    data = users[user_id]
    total = sum(data["history"])
    avg = round(total / len(data["history"]), 1)
    await message.reply(f"📊 Сегодня: {data['today']}/{MAX_SCORE}\nСр.балл: {avg}")

async def main():
    print("✅ Бот готов!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
