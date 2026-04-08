import requests
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

THRESHOLD = 100                    # 大于 100 shares 报警
INTERVAL_SECONDS = 30              # 每 30 秒检查一次

GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

print("=== Polymarket XRP 5分钟市场 大额买入监控（每30秒） ===")
print(f"报警阈值: > {THRESHOLD} shares")
print(f"检查间隔: {INTERVAL_SECONDS} 秒\n")

def get_xrp_markets():
    """获取当前活跃的 XRP 相关市场"""
    try:
        resp = requests.get(f"{GAMMA_API}/markets", params={
            "active": "true",
            "closed": "false",
            "limit": 50,
            "order": "volume"
        }, timeout=10)
        if resp.status_code == 200:
            markets = resp.json()
            # 过滤包含 XRP 的市场
            xrp_markets = [m for m in markets if "XRP" in m.get("question", "").upper()]
            return xrp_markets[:8]   # 限制数量，避免请求过多
        return []
    except Exception as e:
        print(f"[{datetime.now()}] 获取市场列表失败: {e}")
        return []

def get_recent_trades(condition_id):
    """获取某个市场的最近交易"""
    try:
        resp = requests.get(f"{DATA_API}/trades", params={
            "market": condition_id,
            "limit": 15
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def check_large_buys():
    print(f"[{datetime.now()}] 开始检查 XRP 5分钟市场...")
    markets = get_xrp_markets()
    
    alert_count = 0
    for market in markets:
        question = market.get("question", "Unknown Market")
        condition_id = market.get("conditionId")
        if not condition_id:
            continue
            
        trades = get_recent_trades(condition_id)
        
        for trade in trades:
            try:
                size = float(trade.get("size", 0))
                if size > THRESHOLD:
                    buyer = trade.get("proxyWallet") or trade.get("taker") or trade.get("maker_address") or "Unknown"
                    outcome = trade.get("outcome", "Unknown")
                    price = float(trade.get("price", 0))
                    
                    print(f"[{datetime.now()}] 🚨 【大额买入警报】")
                    print(f"   市场: {question}")
                    print(f"   钱包地址: {buyer}")
                    print(f"   买入: {size:.2f} shares   方向: {outcome}   价格: {price:.4f}")
                    print(f"   时间: {trade.get('timestamp') or 'N/A'}")
                    print("-" * 80)
                    alert_count += 1
            except:
                continue   # 跳过解析失败的单条
    
    if alert_count == 0:
        print(f"[{datetime.now()}] 本轮未发现 > {THRESHOLD} shares 的大额买入\n")

if __name__ == "__main__":
    # 立即执行一次
    check_large_buys()
    
    # 启动定时任务
    scheduler = BlockingScheduler()
    scheduler.add_job(check_large_buys, 'interval', seconds=INTERVAL_SECONDS)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n监控已停止")
