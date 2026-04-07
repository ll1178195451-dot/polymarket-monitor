import requests
import time
import os
from datetime import datetime, timezone
import telegram
from telegram.error import TelegramError
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================== 配置 ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

THRESHOLD_SHARES = 500          # 大单阈值，可自行修改
POLL_INTERVAL = 35              # 秒

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_alert(text: str):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

def get_current_5min_slug(asset: str) -> str:
    """自动计算当前 5 分钟市场的 slug"""
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // 300) * 300
    return f"{asset}-updown-5m-{period}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    monitored_xrp = get_current_5min_slug("xrp")
    monitored_sol = get_current_5min_slug("sol")
    
    msg = f"""🚀 **Polymarket 监控 Bot 已运行**

**当前状态：**
• 阈值：**{THRESHOLD_SHARES}** shares（BUY）
• 轮询间隔：{POLL_INTERVAL} 秒
• XRP 市场：`{monitored_xrp}`
• SOL 市场：`{monitored_sol}`

输入 `/start` 可随时查看状态
大单出现时会自动提醒你！"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')

def main():
    print("🚀 Polymarket 大单监控 Bot 启动中...")

    # 发送启动测试消息
    test_msg = f"""✅ **监控 Bot 已成功启动！**
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
阈值: {THRESHOLD_SHARES} shares
模式: 自动计算 5分钟市场

使用 `/start` 查看当前状态
大单（≥{THRESHOLD_SHARES} shares BUY）将立即提醒！"""
    send_alert(test_msg)

    # 设置 Telegram Bot 命令
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))

    # 启动监控循环（在后台运行）
    import threading
    def run_monitor():
        while True:
            monitored = {
                "XRP_5min": get_current_5min_slug("xrp"),
                "SOL_5min": get_current_5min_slug("sol"),
            }

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 监控市场: {list(monitored.values())}")

            for name, slug in monitored.items():
                try:
                    url = f"https://data-api.polymarket.com/trades?market={slug}&limit=60"
                    resp = requests.get(url, timeout=15)
                    if resp.status_code == 200:
                        trades = resp.json()
                        for trade in trades:
                            size = float(trade.get("size", 0))
                            side = str(trade.get("side", "")).upper()
                            if side == "BUY" and size >= THRESHOLD_SHARES:
                                outcome = trade.get("outcome", "Unknown")
                                price = trade.get("price")
                                alert = f"""🔥 **大单警报** 🔥
市场: {name}
时间: {datetime.now().strftime('%H:%M:%S')}
方向: {outcome} **BUY**
数量: **{size:,.0f}** shares
价格: {price}
链接: https://polymarket.com/event/{slug}"""
                                send_alert(alert)
                except Exception as e:
                    print(f"检查 {name} 出错: {e}")

            time.sleep(POLL_INTERVAL)

    # 启动监控线程
    threading.Thread(target=run_monitor, daemon=True).start()

    # 启动 Telegram Bot（处理 /start 命令）
    print("Telegram Bot 已启动，等待 /start 命令...")
    application.run_polling()

if __name__ == "__main__":
    main()
