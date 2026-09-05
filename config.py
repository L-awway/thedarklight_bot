import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
OWNER = os.getenv("OWNER")
DEPUTY = os.getenv("DEPUTY")
HEAD_ADMIN = os.getenv("HEAD_ADMIN")
TIMEZONE = os.getenv("TIMEZONE")

ADMINS = [OWNER, DEPUTY, HEAD_ADMIN]

# Очки за день
MAX_SCORE = 16
LOW_SCORE_THRESHOLD = 10  # если меньше - предупреждение
MAX_WARNINGS = 3  # до вылета
MAX_SKIPS = 3  # прогулов до красной зоны
