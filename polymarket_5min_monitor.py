import requests
import time
import os
from datetime import datetime, timezone
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POLL_INTERVAL = 25  # 秒

# 不同资产的阈值设置
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

def get_trades(market_slug: str, limit=80):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit={limit}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"获取交易失败 {market_slug}: {e}")
        return []

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
        for asset in ["xrp", "sol", "btc", "eth"]:
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                key = f"{asset.upper()}_{mins}min"
                markets[key] = (slug, THRESHOLDS.get(asset.upper(), 500))

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在监控 {len(markets)} 个市场...")

        for name, (slug, threshold) in markets.items():
            try:
                trades = get_trades(slug)
                for trade in trades:
                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()
                    outcome = trade.get("outcome", "").upper()

                    if side == "BUY" and size >= threshold:
                        direction = "📈 **UP**" if outcome == "UP" else "📉 **DOWN**"
                        price = trade.get("price", "?")
                        
                        alert = f"""🔥 **大单警报** 🔥
市场: **{name}**
方向: {direction}
时间: {datetime.now().strftime('%H:%M:%S')}
数量: **{size:,.0f}** shares
价格: {price}
链接: https://polymarket.com/event/{slug}"""
                        send_alert(alert)
            except:
                pass

        time.sleep(POLL_INTERVAL)

def main():
    print("🚀 多周期大单监控 Bot 启动中...")

    send_alert("✅ **监控 Bot 已成功启动！**\n已支持 BTC/ETH/XRP/SOL 的 5min & 15min 市场\n大单提醒会显示 **UP / DOWN** 方向\n输入 `/start` 查看状态")

    threading.Thread(target=run_monitor, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    
    print("Telegram Bot 已启动...")
    application.run_polling()

if __name__ == "__main__":
    main()
