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
TELEGRAM_CHAT_ID = 8627467932   # 已内置你的 Chat ID

POLL_INTERVAL = 15
THRESHOLD = 500

bot = telegram.Bot(token=TELEGRAM_TOKEN)
start_time = datetime.now()
alert_count = 0

def send_alert(text: str):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

def get_current_slug(asset: str, minutes: int) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // (minutes * 60)) * (minutes * 60)
    slug = f"{asset}-updown-{minutes}m-{period}"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 生成市场: {slug}")
    return slug

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
            data = resp.json()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {market_slug} 返回 {len(data)} 条交易")
            return data
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {market_slug} 请求失败: {resp.status_code}")
        return []
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取交易失败: {e}")
        return []

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start 命令 """
    global alert_count
    uptime = str(datetime.now() - start_time).split('.')[0]
    msg = f"""🚀 **XRP & SOL 监控 Bot 已运行**

**当前状态：**
• 运行时间: {uptime}
• 轮询间隔: **{POLL_INTERVAL}** 秒
• 提醒阈值: **{THRESHOLD}** shares
• 累计提醒次数: **{alert_count}**

✅ Bot 正常运行中
输入 `/start` 可随时刷新状态"""

    await update.message.reply_text(msg, parse_mode='Markdown')

def run_monitor():
    global alert_count
    print("🚀 XRP & SOL 监控循环已启动 (15秒轮询)")
    while True:
        for asset in ["xrp", "sol"]:
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                name = f"{asset.upper()}_{mins}min"
                time_period = get_time_period(mins)

                trades = get_trades(slug)
                for trade in trades:
                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()
                    outcome = trade.get("outcome", "").upper()
                    proxy_wallet = trade.get("proxyWallet")

                    if side == "BUY" and size >= THRESHOLD and proxy_wallet:
                        alert_count += 1
                        direction = "📈 **UP**" if outcome == "UP" else "📉 **DOWN**"
                        price = trade.get("price", "?")
                        wallet_short = f"{proxy_wallet[:8]}...{proxy_wallet[-6:]}"

                        alert = f"""🔥 **大单警报** 🔥
市场: **{name}**
时间段: {time_period}
方向: {direction}
数量: **{size:,.0f}** shares
价格: {price}
钱包: `{wallet_short}`
