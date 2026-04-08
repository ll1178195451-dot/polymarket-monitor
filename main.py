import requests
import time
from datetime import datetime, timezone, timedelta

THRESHOLD = 700
POLL_INTERVAL = 15

# 用于去重，避免同一笔交易重复提醒
seen_trades = set()

def get_current_slug(asset, minutes):
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // (minutes * 60)) * (minutes * 60)
    return f"{asset}-updown-{minutes}m-{period}"

def get_time_period(minutes):
    now = datetime.now(timezone.utc)
    minutes_passed = now.minute % minutes
    seconds_passed = now.second
    start = now - timedelta(minutes=minutes_passed, seconds=seconds_passed)
    end = start + timedelta(minutes=minutes)
    hk_start = start.astimezone(timezone(timedelta(hours=8)))
    hk_end = end.astimezone(timezone(timedelta(hours=8)))
    return f"{hk_start.strftime('%H:%M')}-{hk_end.strftime('%H:%M')}"

def get_trades(market_slug):
    try:
        url = f"https://data-api.polymarket.com/trades?market={market_slug}&limit=80"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def get_top_holders(market_slug):
    try:
        url = f"https://data-api.polymarket.com/holders?market={market_slug}&limit=30"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def main():
    print("XRP SOL 5分钟和15分钟 监控已启动 (单笔买入 或 总持仓 ≥ 700 shares)")

    while True:
        for asset in ["xrp", "sol"]:
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                time_period = get_time_period(mins)
                name = asset.upper() + "_" + str(mins) + "min"

                # 检查单笔买入
                trades = get_trades(slug)
                for trade in trades:
                    trade_key = trade.get("id") or trade.get("txHash") or str(trade)
                    if trade_key in seen_trades:
                        continue

                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()
                    outcome = trade.get("outcome", "").upper()
                    wallet = trade.get("proxyWallet", "未知")
                    price = trade.get("price", "?")

                    if side == "BUY" and size >= THRESHOLD and wallet:
                        seen_trades.add(trade_key)
                        direction = "UP" if outcome == "UP" else "DOWN"
                        alert = "单笔买入大单 | 市场: " + name + " | 时间段: " + time_period + " | 方向: " + direction + " | 数量: " + str(int(size)) + " shares | 均价: " + str(price) + " | 钱包: " + wallet
                        print("[" + datetime.now().strftime('%H:%M:%S') + "] " + alert)

                # 检查 Top Holders 总持仓
                holders = get_top_holders(slug)
                for h in holders:
                    amount = float(h.get("amount", 0))
                    wallet = h.get("proxyWallet", "未知")
                    outcome = h.get("outcome", "").upper()

                    if amount >= THRESHOLD and wallet:
                        direction = "UP" if outcome == "UP" else "DOWN"
                        alert = "Top Holders 大持仓 | 市场: " + name + " | 时间段: " + time_period + " | 方向: " + direction + " | 总持仓: " + str(int(amount)) + " shares | 钱包: " + wallet
                        print("[" + datetime.now().strftime('%H:%M:%S') + "] " + alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
