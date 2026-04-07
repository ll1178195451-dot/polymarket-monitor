import requests
import time
import os
from datetime import datetime, timezone
import telegram
from telegram.error import TelegramError

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

THRESHOLD_SHARES = 500          # 大单阈值，可改
POLL_INTERVAL = 35              # 秒，建议 30-45 秒

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_alert(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 提醒已发送")
    except Exception as e:
        print(f"❌ Telegram 发送失败: {e}")

def get_current_5min_slug(asset: str) -> str:
    """自动计算当前/下一个 5 分钟市场的 slug"""
    now = int(datetime.now(timezone.utc).timestamp())
    # 5分钟 = 300 秒，向下取整到最近的 5 分钟周期
    period = (now // 300) * 300
    return f"{asset}-updown-5m-{period}"

def get_trades(market_slug: str, limit=80):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit={limit}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"获取交易失败 {market_slug}: {e}")
        return []

def main():
    print("🚀 Polymarket XRP & SOL 5分钟大单监控 已启动（自动计算市场）")
    print(f"阈值: {THRESHOLD_SHARES} shares | 轮询间隔: {POLL_INTERVAL}秒")

    # 启动测试消息
    test_msg = f"""✅ **监控 Bot 已成功启动！**
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
阈值: {THRESHOLD_SHARES} shares
模式: 自动计算 5 分钟市场

大单（≥{THRESHOLD_SHARES} shares BUY）出现时会立即提醒！"""
    send_alert(test_msg)

    while True:
        # 每次循环都重新计算当前最新的市场（防止市场结束）
        monitored = {
            "XRP_5min": get_current_5min_slug("xrp"),
            "SOL_5min": get_current_5min_slug("sol"),
        }

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在监控: {list(monitored.values())}")

        for name, slug in monitored.items():
            trades = get_trades(slug)
            for trade in trades:
                ts = trade.get("timestamp")
                size = float(trade.get("size", 0))
                side = str(trade.get("side", "")).upper()
                outcome = trade.get("outcome", "Unknown")
                price = trade.get("price")

                if side == "BUY" and size >= THRESHOLD_SHARES:
                    dt = datetime.fromtimestamp(int(ts)/1000 if isinstance(ts, (int,float)) and ts > 1e10 else ts, tz=timezone.utc)
                    alert = f"""🔥 **大单警报** 🔥
市场: {name}
时间: {dt.strftime('%H:%M:%S')}
方向: {outcome} **BUY**
数量: **{size:,.0f}** shares
价格: {price}
链接: https://polymarket.com/event/{slug}"""
                    send_alert(alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
