import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

class Database:
    def __init__(self, sheet_url):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
        client = gspread.authorize(creds)
        self.sh = client.open_by_url(sheet_url)
        
        # Инициализация листов
        try:
            self.players = self.sh.worksheet("Игроки")
        except:
            self.players = self.sh.add_worksheet("Игроки", 100, 3)
            self.players.append_row(["@username", "Дата добавления", "Роль"])
        
        try:
            self.stats = self.sh.worksheet("Статистика")
        except:
            self.stats = self.sh.add_worksheet("Статистика", 100, 35)
            headers = ["@username"]
            for i in range(1, 32):
                headers.append(f"День{i}")
            headers.extend(["Прогулы", "Дней_<10", "Всего_очков", "Средний_балл"])
            self.stats.append_row(headers)
    
    def get_player_stats(self, username):
        cells = self.stats.find(username)
        if not cells:
            return None
        row = cells[0].row
        data = self.stats.row_values(row)
        return data
    
    def update_score(self, username, score, day_index):
        cells = self.stats.find(username)
        if not cells:
            row = [username] + [""] * 33
            self.stats.append_row(row)
            row_num = len(self.stats.get_all_values())
        else:
            row_num = cells[0].row
        
        self.stats.update_cell(row_num, day_index + 2, str(score))
        self._recalc_stats(row_num, username)
    
    def _recalc_stats(self, row_num, username):
        row = self.stats.row_values(row_num)
        scores = [int(x) if x.isdigit() else -1 for x in row[1:33]]
        
        skips = sum(1 for s in scores if s == 0)
        low_days = sum(1 for s in scores if 0 < s < 10)
        total = sum(s for s in scores if s > 0)
        played_days = sum(1 for s in scores if s > 0)
        avg = round(total / played_days, 1) if played_days > 0 else 0
        
        self.stats.update_cell(row_num, 33, skips)
        self.stats.update_cell(row_num, 34, low_days)
        self.stats.update_cell(row_num, 35, total)
        self.stats.update_cell(row_num, 36, avg)
    
    def get_today_index(self):
        today = datetime.datetime.now()
        day = today.day
        if today.hour < 3 and today.day == 5:
            return 31
        if today.hour >= 3 and today.day == 5:
            return 1
        return min(day, 31)
