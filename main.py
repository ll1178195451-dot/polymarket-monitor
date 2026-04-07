import requests
import time
import os
from datetime import datetime, timezone, timedelta
import telegram

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = 8627467932

POLL_INTERVAL = 15
THRESHOLD = 200

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_alert(text: str):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

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

def get_trades(market_slug: str):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit=50"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def main():
    print("🚀 Bot 启动中...")
    send_alert("✅ **XRP & SOL 监控 Bot 已成功启动！**\n阈值：500 shares\n轮询间隔：15 秒")

    while True:
        for asset in ["xrp", "sol"]:
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                name = f"{asset.upper()}_{mins}min"
                time_period = get_time_period(mins)

                trades = get_trades(slug)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查 {name} → 返回 {len(trades)} 条交易")

                for trade in trades:
                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()
                    if side == "BUY" and size >= THRESHOLD:
                        alert = f"🔥 大单警报！ {name} 买入 {size} shares"
                        send_alert(alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
