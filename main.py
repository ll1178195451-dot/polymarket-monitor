import requests
import time
from datetime import datetime, timezone, timedelta
import telegram
import threading

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POLL_INTERVAL = 15
THRESHOLD = 500   # Top Holders 总持仓 >= 500 shares 就提醒

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

def get_top_holders(market_slug: str, limit=20):
    """获取该市场的 Top Holders 总持仓"""
    try:
        # 使用 /holders 接口获取 Top Holders
        url = f"https://data-api.polymarket.com/holders?market={market_slug}&limit={limit}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def run_monitor():
    print("🚀 XRP & SOL Top Holders 监控已启动 (15秒轮询)")
    while True:
        for asset in ["xrp", "sol"]:
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                name = f"{asset.upper()}_{mins}min"
                time_period = get_time_period(mins)

                holders = get_top_holders(slug)
                for holder in holders:
                    total_shares = float(holder.get("amount", 0))
                    proxy_wallet = holder.get("proxyWallet")
                    outcome = holder.get("outcome", "").upper()

                    if total_shares >= THRESHOLD and proxy_wallet:
                        direction = "📈 **UP**" if outcome == "UP" else "📉 **DOWN**"
                        wallet_short = f"{proxy_wallet[:8]}...{proxy_wallet[-6:]}"

                        alert = f"""🔥 **Top Holder 大持仓警报** 🔥
市场: **{name}**
时间段: {time_period}
方向: {direction}
总持仓: **{total_shares:,.0f}** shares
用户: 匿名用户
钱包: `{wallet_short}`
[Polymarket 用户页](https://polymarket.com/profile/{proxy_wallet})
[市场链接](https://polymarket.com/event/{slug})"""
                        send_alert(alert)

        time.sleep(POLL_INTERVAL)

def main():
    print("🚀 Bot 启动中...")
    send_alert("✅ **XRP & SOL Top Holders 监控已启动！**\n阈值：**总持仓 ≥ 500 shares**\n轮询间隔：**15 秒**\n输入任意消息测试")

    threading.Thread(target=run_monitor, daemon=True).start()

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
