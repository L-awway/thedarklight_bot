import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
import pytz

from config import *
from database import Database
from scheduler import Scheduler

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ВСТАВЬТЕ ССЫЛКУ НА ВАШУ ТАБЛИЦУ GOOGLE SHEETS
db = Database("https://docs.google.com/spreadsheets/d/ВАШ_ID_ТАБЛИЦЫ/edit")
scheduler = Scheduler(bot, db)

def is_admin(username):
    return username in ADMINS

@dp.message(Command("и"))
async def report_score(message: types.Message):
    if not message.reply_to_message:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❗ Используйте: !и 14")
            return
        
        username = "@" + message.from_user.username
        try:
            score = int(args[1])
            if score < 0 or score > MAX_SCORE:
                await message.reply(f"❗ Очки должны быть от 0 до {MAX_SCORE}")
                return
        except:
            await message.reply("❗ Введите число, например: !и 14")
            return
        
        day_idx = db.get_today_index()
        db.update_score(username, score, day_idx)
        await message.reply(f"✅ {username}, записано {score}/{MAX_SCORE} за сегодня!")

@dp.message(Command("я"))
async def my_stats(message: types.Message):
    username = "@" + message.from_user.username
    stats = db.get_player_stats(username)
    if not stats:
        await message.reply("❌ Вы не в клане! Обратитесь к администратору.")
        return
    
    skips = stats[33] if len(stats) > 33 else "0"
    low_days = stats[34] if len(stats) > 34 else "0"
    avg = stats[36] if len(stats) > 36 else "0"
    
    text = f"📊 Статистика {username}:\n"
    text += f"Прогулов: {skips}/{MAX_SKIPS}\n"
    text += f"Дней <10: {low_days} (из {MAX_WARNINGS})\n"
    text += f"Средний балл: {avg}\n"
    await message.reply(text)

@dp.message(Command("топ"))
async def top_players(message: types.Message):
    all_data = db.stats.get_all_values()
    players = []
    for row in all_data[1:]:
        if len(row) > 36 and row[36] and row[36] != "0":
            players.append((row[0], float(row[36])))
    
    players.sort(key=lambda x: x[1], reverse=True)
    top = players[:5]
    
    text = "🏆 ТОП-5 КЛАНА:\n"
    for i, (name, avg) in enumerate(top, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        text += f"{medal} {name} — {avg}\n"
    await message.reply(text)

@dp.message(Command("добавить"))
async def add_player(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: !добавить @Nickname")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    if db.players.find(username):
        await message.reply(f"❌ {username} уже в клане.")
        return
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    db.players.append_row([username, now, "игрок"])
    db.stats.append_row([username] + [""] * 35)
    
    await message.reply(f"✅ {username} добавлен в клан!")

@dp.message(Command("удалить"))
async def remove_player(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: !удалить @Nickname")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    cells = db.players.find(username)
    if cells:
        db.players.delete_rows(cells[0].row)
    
    cells = db.stats.find(username)
    if cells:
        db.stats.delete_rows(cells[0].row)
    
    await message.reply(f"✅ {username} удалён из клана.")

@dp.message(Command("состав"))
async def show_roster(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.reply("⛔ Доступно только администраторам.")
        return
    
    all_players = db.players.get_all_values()
    text = "👥 СОСТАВ КЛАНА:\n\n"
    for row in all_players[1:]:
        text += f"{row[0]}\n"
    await message.reply(text)

@dp.message(Command("стата"))
async def player_stats(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: !стата @Nickname")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    stats = db.get_player_stats(username)
    if not stats:
        await message.reply(f"❌ Игрок {username} не найден.")
        return
    
    skips = stats[33] if len(stats) > 33 else "0"
    low_days = stats[34] if len(stats) > 34 else "0"
    avg = stats[36] if len(stats) > 36 else "0"
    
    text = f"📊 Статистика {username}:\n"
    text += f"Прогулов: {skips}/{MAX_SKIPS}\n"
    text += f"Дней <10: {low_days} (из {MAX_WARNINGS})\n"
    text += f"Средний балл: {avg}\n"
    await message.reply(text)

@dp.message(Command("прогулы"))
async def skip_list(message: types.Message):
    all_data = db.stats.get_all_values()
    text = "🚫 ИГРОКИ С >3 ПРОГУЛОВ:\n\n"
    found = False
    
    for row in all_data[1:]:
        if len(row) > 33 and row[33] and int(row[33]) > MAX_SKIPS:
            text += f"{row[0]} — {row[33]} прогулов\n"
            found = True
    
    if not found:
        text = "✅ Нет игроков с превышением прогулов."
    
    await message.reply(text)

@dp.message(Command("зам"))
async def set_deputy(message: types.Message):
    if message.from_user.username != OWNER:
        await message.reply("⛔ Только владелец может назначать заместителя.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Используйте: !зам @Nickname")
        return
    
    username = args[1]
    if not username.startswith("@"):
        username = "@" + username
    
    # Обновляем в .env (нужно перезапустить бота)
    await message.reply(f"✅ {username} назначен заместителем.\n⚠️ Нужно обновить переменную DEPUTY в .env и перезапустить бота!")

async def main():
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
