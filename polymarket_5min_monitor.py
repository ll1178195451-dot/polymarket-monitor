import requests
import time
import os
from datetime import datetime, timezone, timedelta
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POLL_INTERVAL = 25  # 秒

THRESHOLDS = {
    "XRP": 500,
    "SOL": 500,
    "BTC": 10000,
    "ETH": 10000
}

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_alert(text: str):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

def get_current_slug(asset: str, minutes: int) -> str:
    """自动计算当前 N 分钟市场的 slug"""
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // (minutes * 60)) * (minutes * 60)
    return f"{asset.lower()}-updown-{minutes}m-{period}"

def get_time_period(minutes: int, ts=None) -> str:
    """生成时间段显示 [5min 21:15-21:20]（香港时间）"""
    if ts is None:
        ts = datetime.now(timezone.utc).timestamp()
    else:
        ts = ts / 1000 if ts > 1e10 else ts
    
    start = datetime.fromtimestamp(ts, tz=timezone.utc)
    end = start + timedelta(minutes=minutes)
    
    hk_start = start.astimezone(timezone(timedelta(hours=8)))
    hk_end = end.astimezone(timezone(timedelta(hours=8)))
    
    return f"[{minutes}min {hk_start.strftime('%H:%M')}-{hk_end.strftime('%H:%M')}]"

def get_trades(market_slug: str, limit=80):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit={limit}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"获取交易失败 {market_slug}: {e}")
        return []

def get_user_position(proxy_wallet: str, market_slug: str):
    """查询用户在该市场的总持仓量"""
    try:
        url = f"https://data-api.polymarket.com/positions?user={proxy_wallet}&limit=20"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            for pos in resp.json():
                if market_slug in str(pos.get("conditionId", "")) or market_slug.split("-")[-1] in str(pos):
                    return float(pos.get("size", 0))
        return 0
    except:
        return 0

def get_user_profile(proxy_wallet: str):
    """尝试获取用户名"""
    try:
        url = f"https://gamma-api.polymarket.com/public-profile?wallet={proxy_wallet}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("name") or data.get("username") or "匿名用户"
    except:
        pass
    return "匿名用户"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start 命令 """
    msg = f"""🚀 **Polymarket 多周期大单监控 Bot 已运行**

**监控配置：**
• XRP / SOL → ≥ **{THRESHOLDS['XRP']}** shares (5min & 15min)
• BTC / ETH → ≥ **{THRESHOLDS['BTC']}** shares (5min & 15min)
• 轮询间隔：**{POLL_INTERVAL}** 秒

✅ Bot 正常运行中
输入 `/start` 可随时刷新状态"""

    await update.message.reply_text(msg, parse_mode='Markdown')

def run_monitor():
    """后台实时监控"""
    while True:
        markets = {}
