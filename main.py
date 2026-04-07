import requests
import time
import os
from datetime import datetime, timezone, timedelta
import telegram
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# 已内置你的 Chat ID
TELEGRAM_CHAT_ID = 8627467932  

POLL_INTERVAL = 15
THRESHOLD = 500

bot = telegram.Bot(token=TELEGRAM_TOKEN)
start_time = datetime.now()
alert_count = 0

def send_alert(text: str):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功")
        return True
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

def get_current_slug(asset: str, minutes: int) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // (minutes * 60)) * (minutes * 60)
    return f"{asset}-updown-{minutes}m-{period}"

def get_time_period(minutes: int) -> str:
    now = datetime.now(timezone.utc)
    minutes_passed = now.minute % minutes
    seconds_passed = now.second
    start = now - timedelta(minutes=minutes_passed, seconds=seconds_passed)
    end = start + timedelta(minutes=minutes)
    hk_start = start.astimezone(timezone(timedelta(hours=8)))
    hk_end = end.astimezone(timezone(timedelta(hours=8)))
    return f"[{minutes}min {hk_start.strftime('%H:%M')}-{hk_end.strftime('%H:%M')}]"

def get_trades(market_slug: str, limit=80):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit={limit}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    global alert_count
    uptime = str(datetime.now() - start_time).split('.')[0]
    msg = f"""🚀 **XRP & SOL 监控 Bot 已运行**

**当前状态：**
• 运行时间: {uptime}
• 轮询间隔: **{POLL_INTERVAL}** 秒
• 提醒
