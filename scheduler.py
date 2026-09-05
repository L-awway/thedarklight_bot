from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from config import CHAT_ID, TIMEZONE, MAX_SCORE, LOW_SCORE_THRESHOLD

TZ = pytz.timezone(TIMEZONE)

class Scheduler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.scheduler = AsyncIOScheduler(timezone=TZ)
        
        self.scheduler.add_job(
            self.daily_report,
            CronTrigger(hour=3, minute=0, timezone=TZ)
        )
        self.scheduler.start()
    
    async def daily_report(self):
        all_players = self.db.players.get_all_values()
        today_idx = self.db.get_today_index()
        
        ok, low, skip = [], [], []
        
        for row in all_players[1:]:
            username = row[0]
            stats = self.db.get_player_stats(username)
            if stats and len(stats) > today_idx + 1:
                score = stats[today_idx + 1]
                if not score:
                    skip.append(username)
                elif int(score) < LOW_SCORE_THRESHOLD:
                    low.append((username, score))
                else:
                    ok.append((username, score))
        
        report = f"📊 ОТЧЁТ ЗА {datetime.now(TZ).strftime('%d.%m.%Y')}\n\n"
        
        if ok:
            report += "✅ ОТЫГРАЛИ:\n" + "\n".join([f"{u} ({s}/{MAX_SCORE})" for u, s in ok]) + "\n\n"
        
        if low:
            report += "⚠️ НИЗКАЯ ЭФФЕКТИВНОСТЬ (<10):\n"
            report += "\n".join([f"{u} ({s}/{MAX_SCORE})" for u, s in low]) + "\n\n"
        
        if skip:
            report += "🚫 ПРОГУЛЫ (0):\n" + "\n".join(skip)
        
        await self.bot.send_message(CHAT_ID, report)
