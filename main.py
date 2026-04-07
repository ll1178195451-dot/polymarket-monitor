import requests
import time
import os
from datetime import datetime, timezone, timedelta
import telegram

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = 8627467932

POLL_INTERVAL = 15
THRESHOLD = 100   # 测试用100

bot = telegram.Bot(token=TELEGRAM_TOKEN)
start_time = datetime.now()
alert_count = 0   # 全局变量

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
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit=80"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def main():
    global alert_count
    print("🚀 Bot 启动中...")
    send_alert("✅ **XRP & SOL 监控 Bot 测试版已启动！**\n阈值：**100 shares**\n轮询间隔：**15 秒**")

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
                    outcome = trade.get("outcome", "").upper()
                    proxy_wallet = trade.get("proxyWallet")

                    if side == "BUY" and size >= THRESHOLD and proxy_wallet:
                        alert_count += 1
                        direction = "📈 **UP**" if outcome == "UP" else "📉 **DOWN**"
                        price = trade.get("price", "?")
                        wallet_short = f"{proxy_wallet[:8]}...{proxy_wallet[-6:]}"

                        alert = "🔥 **大单警报** 🔥\n"
                        alert += f"市场: **{name}**\n"
                        alert += f"时间段: {time_period}\n"
                        alert += f"方向: {direction}\n"
                        alert += f"数量: **{size:,.0f}** shares\n"
                        alert += f"价格: {price}\n"
                        alert += f"钱包: `{wallet_short}`\n"
                        alert += f"[Polymarket 用户页](https://polymarket.com/profile/{proxy_wallet})\n"
                        alert += f"[市场链接](https://polymarket.com/event/{slug})"

                        send_alert(alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
