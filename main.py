import requests
import time
from datetime import datetime, timezone, timedelta
import telegram

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = 8627467932   # 你的 Chat ID

THRESHOLD = 500
POLL_INTERVAL = 15   # 秒

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_alert(text: str):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

def get_current_slug(asset: str) -> str:
    """自动计算当前 5分钟市场 slug"""
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // 300) * 300          # 5分钟 = 300秒
    return f"{asset}-updown-5m-{period}"

def get_time_period() -> str:
    """显示香港时间段"""
    now = datetime.now(timezone.utc)
    minutes_passed = now.minute % 5
    seconds_passed = now.second
    start = now - timedelta(minutes=minutes_passed, seconds=seconds_passed)
    end = start + timedelta(minutes=5)
    hk_start = start.astimezone(timezone(timedelta(hours=8)))
    hk_end = end.astimezone(timezone(timedelta(hours=8)))
    return f"[{hk_start.strftime('%H:%M')}-{hk_end.strftime('%H:%M')}]"

def get_top_holders(market_slug: str):
    try:
        url = f"https://data-api.polymarket.com/holders?market={market_slug}&limit=30"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def main():
    print("🚀 超级简单 XRP & SOL 5min Top Holders 监控 已启动")
    send_alert("✅ **简单监控已启动**\n只监控 XRP/SOL 5分钟市场\nTop Holders ≥ 500 shares 就提醒")

    while True:
        for asset in ["xrp", "sol"]:
            slug = get_current_slug(asset)
            time_period = get_time_period()
            name = f"{asset.upper()}_5min"

            holders = get_top_holders(slug)

            for h in holders:
                amount = float(h.get("amount", 0))
                proxy_wallet = h.get("proxyWallet")
                outcome = h.get("outcome", "").upper()

                if amount >= THRESHOLD and proxy_wallet:
                    direction = "📈 **UP**" if outcome == "UP" else "📉 **DOWN**"
                    wallet_short = f"{proxy_wallet[:8]}...{proxy_wallet[-6:]}"

                    alert = f"""🔥 **Top Holder 大持仓警报** 🔥
市场: **{name}**
时间段: {time_period}
方向: {direction}
总持仓: **{amount:,.0f}** shares
钱包: `{wallet_short}`
[用户页](https://polymarket.com/profile/{proxy_wallet})
[市场](https://polymarket.com/event/{slug})"""

                    send_alert(alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
