import requests
import time
import os
from datetime import datetime, timezone, timedelta
import telegram
import threading

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POLL_INTERVAL = 15
THRESHOLD = 500

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_alert(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

def get_current_slug(asset, minutes):
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // (minutes * 60)) * (minutes * 60)
    return f"{asset}-updown-{minutes}m-{period}"

def get_time_period(minutes):
    now = datetime.now(timezone.utc)
    minutes_passed = now.minute % minutes
    seconds_passed = now.second
    start = now - timedelta(minutes=minutes_passed, seconds=seconds_passed)
    end = start + timedelta(minutes=minutes)
    hk_start = start.astimezone(timezone(timedelta(hours=8)))
    hk_end = end.astimezone(timezone(timedelta(hours=8)))
    return f"[{minutes}min {hk_start.strftime('%H:%M')}-{hk_end.strftime('%H:%M')}]"

def get_trades(market_slug):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit=60"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def run_monitor():
    print("🚀 XRP & SOL 监控启动 (15秒轮询)")
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
                        direction = "📈 UP" if outcome == "UP" else "📉 DOWN"
                        price = trade.get("price", "?")
                        wallet_short = f"{proxy_wallet[:8]}...{proxy_wallet[-6:]}"

                        alert = f"""🔥 大单警报 🔥
市场: {name}
时间段: {time_period}
方向: {direction}
数量: {size:,.0f} shares
价格: {price}
钱包: {wallet_short}
[用户页](https://polymarket.com/profile/{proxy_wallet})
[市场](https://polymarket.com/event/{slug})"""
                        send_alert(alert)

        time.sleep(POLL_INTERVAL)

def main():
    print("🚀 Bot 启动...")
    send_alert("✅ XRP & SOL 监控已启动\n阈值 500 shares\n15秒轮询")

    threading.Thread(target=run_monitor, daemon=True).start()

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
