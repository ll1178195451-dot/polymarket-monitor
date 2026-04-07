import requests
import time
import os
from datetime import datetime
import telegram
from telegram.error import TelegramError

# ================== 配置（必须修改） ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "在这里填你的 Bot Token")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "在这里填你的 Chat ID")  # 数字或 -100xxxxxxxxxx（群）

THRESHOLD_SHARES = 500          # 大单阈值，改成你想要的数字
POLL_INTERVAL = 40              # 轮询间隔（秒），建议 30-60 秒
# ====================================================

bot = telegram.Bot(token=TELEGRAM_TOKEN)
last_seen = {}  # 防止重复提醒

def get_active_5min_markets():
    """自动查找当前活跃的 XRP 和 SOL 5分钟市场"""
    try:
        # 使用 Gamma API 搜索活跃的 5min 市场
        url = "https://gamma-api.polymarket.com/markets?active=true&limit=100"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        markets = {}
        for m in data:
            slug = m.get("slug", "")
            title = m.get("question", "").lower()
            if ("xrp up or down" in title or "sol up or down" in title) and "5 min" in title:
                asset = "XRP" if "xrp" in title else "SOL"
                markets[f"{asset}_5min"] = slug
        return markets
    except Exception as e:
        print(f"获取市场列表失败: {e}")
        # 备用手动 slug 示例（如果自动失败可以临时用）
        return {
            "XRP_5min": "xrp-updown-5m-当前时间戳",  # 程序会自动更新
            "SOL_5min": "sol-updown-5m-当前时间戳"
        }

def get_trades(market_slug, limit=80):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit={limit}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"获取交易失败 {market_slug}: {e}")
        return []

def send_alert(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 提醒已发送")
    except TelegramError as e:
        print(f"Telegram 发送失败: {e}")

def main():
    print("🚀 Polymarket XRP & SOL 5分钟大单监控 已启动")
    print(f"阈值: {THRESHOLD_SHARES} shares | 轮询间隔: {POLL_INTERVAL}秒")
    
    while True:
        monitored = get_active_5min_markets()
        if not monitored:
            print("未找到活跃的 XRP/SOL 5min 市场，等待下次...")
            time.sleep(POLL_INTERVAL)
            continue
            
        print(f"正在监控市场: {list(monitored.keys())}")
        
        for name, slug in monitored.items():
            trades = get_trades(slug)
            for trade in trades:
                ts = trade.get("timestamp")
                size = float(trade.get("size", 0))
                side = str(trade.get("side", "")).upper()
                outcome = trade.get("outcome", "Unknown")
                price = trade.get("price")
                
                if side == "BUY" and size >= THRESHOLD_SHARES:
                    key = f"{name}_{ts}"
                    if key not in last_seen:
                        last_seen[key] = True
                        dt = datetime.fromtimestamp(int(ts)/1000) if isinstance(ts, (int, float)) and ts > 1e10 else datetime.now()
                        
                        alert = f"""🔥 **大单警报** 🔥
**市场**: {name} (5分钟)
**时间**: {dt.strftime('%Y-%m-%d %H:%M:%S')}
**方向**: {outcome} **BUY**
**数量**: **{size:,.0f}** shares
**价格**: {price}
**链接**: https://polymarket.com/{slug}"""
                        
                        send_alert(alert)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
