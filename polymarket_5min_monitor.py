import requests
import time
import os
from datetime import datetime, timezone, timedelta
import telegram
import threading

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POLL_INTERVAL = 15   # 15秒轮询

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
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功: {text[:100]}...")
        return True
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

def get_current_slug(asset: str, minutes: int) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // (minutes * 60)) * (minutes * 60)
    return f"{asset.lower()}-updown-{minutes}m-{period}"

def get_time_period(minutes: int, ts=None) -> str:
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
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def run_monitor():
    print("🚀 监控循环已启动 (15秒轮询)")
    while True:
        try:
            markets = {}
            for asset in ["xrp", "sol", "btc", "eth"]:
                for mins in [5, 15]:
                    slug = get_current_slug(asset, mins)
                    key = f"{asset.upper()}_{mins}min"
                    markets[key] = (slug, THRESHOLDS.get(asset.upper(), 500), mins)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在监控 {len(markets)} 个市场...")

            for name, (slug, threshold, mins) in markets.items():
                trades = get_trades(slug)
                for trade in trades:
                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()
                    outcome = trade.get("outcome", "").upper()
                    proxy_wallet = trade.get("proxyWallet")
                    ts = trade.get("timestamp")

                    if side == "BUY" and size >= threshold and proxy_wallet:
                        direction = "📈 **UP**" if outcome == "UP" else "📉 **DOWN**"
                        time_period = get_time_period(mins, ts)
                        price = trade.get("price", "?")
                        wallet_short = f"{proxy_wallet[:8]}...{proxy_wallet[-6:]}"

                        alert = f"""🔥 **大单警报** 🔥
市场: **{name}**
时间段: {time_period}
方向: {direction}
数量: **{size:,.0f}** shares
价格: {price}
钱包: `{wallet_short}`
[Polymarket 用户页](https://polymarket.com/profile/{proxy_wallet})
[市场链接](https://polymarket.com/event/{slug})"""
                        send_alert(alert)
        except Exception as e:
            print(f"循环出错: {e}")

        time.sleep(POLL_INTERVAL)

def main():
    print("🚀 Bot 主程序启动中...")

    # 立即发送启动消息（关键测试）
    success = send_alert("✅ **监控 Bot 已成功启动！**\n轮询间隔：**15 秒**\n大单提醒已优化\n输入任意消息测试是否正常")

    if success:
        print("✅ 启动消息发送成功")
    else:
        print("⚠️ 启动消息发送失败，请检查 TELEGRAM_CHAT_ID")

    # 启动监控循环
    threading.Thread(target=run_monitor, daemon=True).start()

    # 保持进程运行（Railway 必须）
    print("✅ Bot 已进入保持运行模式")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
