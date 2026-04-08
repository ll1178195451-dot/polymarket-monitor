import requests
import time
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler

THRESHOLD = 100                    # 大于 100 shares 才报警（只监控 BUY）
INTERVAL_SECONDS = 30

GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

print("=== Polymarket XRP 5分钟市场 大额买入监控（每30秒） ===")
print(f"报警阈值: BUY > {THRESHOLD} shares")
print(f"只有检测到大额买入时才会显示日志\n")

def is_market_active(market):
    """判断市场是否正在进行中"""
    try:
        now = datetime.now(timezone.utc).timestamp()
        # 支持不同字段格式
        start = market.get("startDate") or market.get("events", [{}])[0].get("startDate")
        end = market.get("endDate") or market.get("events", [{}])[0].get("endDate")
        
        if isinstance(start, str):
            start = datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp()
        if isinstance(end, str):
            end = datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp()
            
        return start <= now <= end
    except:
        return False

def get_active_xrp_markets():
    """获取当前正在进行的 XRP 5分钟市场"""
    try:
        resp = requests.get(f"{GAMMA_API}/markets", params={
            "active": "true",
            "closed": "false",
            "limit": 100,
            "order": "volume"
        }, timeout=12)
        
        if resp.status_code != 200:
            return []
        
        markets = resp.json()
        xrp_markets = []
        for m in markets:
            question = m.get("question", "").upper()
            if "XRP" in question and ("5 MIN" in question or "5M" in question or "5分钟" in question):
                if is_market_active(m):
                    xrp_markets.append(m)
        
        return xrp_markets[:8]   # 限制数量，防止请求过多
    except:
        return []

def get_recent_trades(condition_id):
    try:
        resp = requests.get(f"{DATA_API}/trades", params={
            "conditionId": condition_id,
            "limit": 25
        }, timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except:
        return []

def check_large_buys():
    markets = get_active_xrp_markets()
    
    for market in markets:
        question = market.get("question", "XRP 5min Market")
        condition_id = market.get("conditionId")
        if not condition_id:
            continue
        
        trades = get_recent_trades(condition_id)
        
        for trade in trades:
            try:
                size = float(trade.get("size", 0))
                side = trade.get("side", "").upper()
                
                if size > THRESHOLD and side == "BUY":
                    buyer = trade.get("proxyWallet") or trade.get("taker") or "Unknown"
                    outcome = trade.get("outcome", "Unknown")
                    price = float(trade.get("price", 0))
                    ts = trade.get("timestamp")
                    trade_time = datetime.fromtimestamp(ts/1000 if ts and ts > 1e10 else ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A"
                    
                    # 只在检测到时打印
                    print(f"[{datetime.now()}] 🚨 【大额买入警报】")
                    print(f"   市场: {question}")
                    print(f"   市场时间: {market.get('startDate', 'N/A')} → {market.get('endDate', 'N/A')}")
                    print(f"   钱包地址: {buyer}")
                    print(f"   买入: {size:.2f} shares   方向: {outcome}   价格: {price:.4f}")
                    print(f"   交易时间: {trade_time}")
                    print("-" * 90)
            except:
                continue

if __name__ == "__main__":
    # 启动时先运行一次（避免错过）
    check_large_buys()
    
    scheduler = BlockingScheduler()
    scheduler.add_job(check_large_buys, 'interval', seconds=INTERVAL_SECONDS)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("监控已停止")
