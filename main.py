import requests
import time
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 配置部分 ---
SYMBOLS = ["XRP", "SOL"]
INTERVALS = ["5 Minutes", "15 Minutes"]
THRESHOLD = 500  # 提醒阈值：500 shares
POLL_INTERVAL = 10  # 轮询间隔（秒）- 建议不低于 5 秒以防 API 限制

# Telegram 配置 (请在下方填入您的 Bot Token 和 Chat ID)
TG_BOT_TOKEN = ""  # 例如: "123456789:ABCDEF..."
TG_CHAT_ID = ""    # 例如: "987654321"

# API 接口
GAMMA_API = "https://gamma-api.polymarket.com/markets"
HOLDERS_API = "https://data-api.polymarket.com/holders"

# 日志配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class PolymarketMonitor:
    def __init__(self):
        self.active_markets = {}  # {condition_id: {"title": str, "symbol": str, "interval": str}}
        self.last_holders = {}    # {condition_id: {wallet_address: amount}}
        self.start_time = datetime.now()
        self.total_alerts = 0

    def get_active_markets(self):
        """获取当前活跃的 XRP/SOL 5m/15m 市场"""
        new_markets = {}
        for symbol in SYMBOLS:
            for interval in INTERVALS:
                query = f"{symbol} Up or Down - {interval}"
                params = {"active": "true", "limit": 5, "query": query}
                try:
                    response = requests.get(GAMMA_API, params=params, timeout=10)
                    if response.status_code == 200:
                        markets = response.json()
                        for m in markets:
                            if query in m['question'] and m['active']:
                                cid = m['conditionId']
                                new_markets[cid] = {
                                    "title": m['question'],
                                    "symbol": symbol,
                                    "interval": interval
                                }
                except Exception as e:
                    logging.error(f"Error fetching markets for {query}: {e}")
        self.active_markets = new_markets
        return list(new_markets.keys())

    async def check_holders(self, condition_id, context: ContextTypes.DEFAULT_TYPE = None):
        """检查特定市场的持仓情况"""
        params = {"market": condition_id, "limit": 20, "minBalance": 1}
        try:
            response = requests.get(HOLDERS_API, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if not data: return
                
                for item in data:
                    holders = item.get('holders', [])
                    current_market_holders = {}
                    
                    for h in holders:
                        wallet = h['proxyWallet']
                        amount = h['amount']
                        current_market_holders[wallet] = amount
                        
                        prev_amount = self.last_holders.get(condition_id, {}).get(wallet, 0)
                        
                        # 提醒逻辑：当前持仓 >= 500 且 相比上次有增加
                        if amount >= THRESHOLD and amount > prev_amount:
                            await self.notify(condition_id, wallet, amount, prev_amount, context)
                    
                    self.last_holders[condition_id] = current_market_holders
        except Exception as e:
            logging.error(f"Error checking holders for {condition_id}: {e}")

    async def notify(self, cid, wallet, amount, prev_amount, context: ContextTypes.DEFAULT_TYPE):
        self.total_alerts += 1
        market_info = self.active_markets.get(cid, {})
        title = market_info.get('title', 'Unknown Market')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        msg = f"🚨 <b>[Polymarket 提醒]</b>\n"
        msg += f"⏰ 时间: {timestamp}\n"
        msg += f"📊 市场: {title}\n"
        msg += f"👛 钱包: <code>{wallet}</code>\n"
        msg += f"💰 当前持仓: <b>{amount}</b> shares\n"
        
        if prev_amount > 0:
            msg += f"📈 变动: +{amount - prev_amount} shares\n"
        else:
            msg += f"✨ 动作: 新买入并持有超过 {THRESHOLD} shares\n"
        
        logging.info(f"Alert: {title} - {wallet} - {amount}")
        
        if TG_BOT_TOKEN and TG_CHAT_ID and context:
            try:
                await context.bot.send_message(chat_id=TG_CHAT_ID, text=msg, parse_mode='HTML')
            except Exception as e:
                logging.error(f"Failed to send TG message: {e}")

    def get_status_text(self):
        uptime = str(datetime.now() - self.start_time).split('.')[0]
        status = f"🤖 <b>Polymarket 监控运行中</b>\n"
        status += f"⏱ 运行时间: {uptime}\n"
        status += f"📡 监控市场数: {len(self.active_markets)}\n"
        status += f"🔔 累计提醒次数: {self.total_alerts}\n\n"
        status += "<b>当前监控列表:</b>\n"
        for cid, info in self.active_markets.items():
            status += f"• {info['symbol']} ({info['interval']})\n"
        return status

# --- Telegram Bot 处理函数 ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    monitor = context.bot_data.get('monitor')
    if monitor:
        await update.message.reply_text(monitor.get_status_text(), parse_mode='HTML')
    else:
        await update.message.reply_text("❌ 监控程序尚未初始化。")

async def monitor_loop(context: ContextTypes.DEFAULT_TYPE):
    monitor = context.bot_data.get('monitor')
    cids = monitor.get_active_markets()
    for cid in cids:
        await monitor.check_holders(cid, context)
        await asyncio.sleep(1)

# --- 主程序 ---
def main():
    if not TG_BOT_TOKEN:
        print("⚠️ 请先在代码中填入 TG_BOT_TOKEN")
        return

    monitor = PolymarketMonitor()
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()
    app.bot_data['monitor'] = monitor

    # 注册命令
    app.add_handler(CommandHandler("start", start_command))

    # 注册定时任务 (轮询)
    job_queue = app.job_queue
    job_queue.run_repeating(monitor_loop, interval=POLL_INTERVAL, first=1)

    print("🚀 Polymarket 监控 Bot 已启动...")
    app.run_polling()

if __name__ == "__main__":
    main()
