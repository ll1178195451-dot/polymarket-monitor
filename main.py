import requests
import time
from datetime import datetime, timezone, timedelta

THRESHOLD = 700
POLL_INTERVAL = 15

seen = set()  # 去重

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
    print("XRP SOL 监控已启动 (阈值 700 shares，显示总持仓成本)")

    while True:
        for asset in ["xrp", "sol"]:
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                time_period = get_time_period(mins)
                name = asset.upper() + "_" + str(mins) + "min"

                # 单笔买入提醒
                trades = get_trades(slug)
                for trade in trades:
                    key = trade.get("id") or trade.get("txHash") or str(trade)
                    if key in seen:
                        continue

                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()
                    wallet = trade.get("proxyWallet")

                    if side == "BUY" and size >= THRESHOLD and wallet:
                        seen.add(key)
                        alert = "单笔买入大单 | 市场: " + name + " | 时间段: " + time_period + " | 数量: " + str(int(size)) + " shares | 钱包: " + wallet
                        print("[" + datetime.now().strftime('%H:%M:%S') + "] " + alert)

                # Top Holders 总持仓提醒 + 持仓成本
                holders = get_top_holders(slug)
                for h in holders:
                    amount = float(h.get("amount", 0))
                    wallet = h.get("proxyWallet")
                    if amount >= THRESHOLD and wallet:
                        # 这里显示总持仓金额 / 数量 = 平均成本（持仓成本）
                        total_cost = float(h.get("totalCost", 0))   # Polymarket 返回的总成本
                        avg_price = total_cost / amount if amount > 0 else 0

                        alert = "Top Holders 大持仓 | 市场: " + name + " | 时间段: " + time_period + " | 总持仓: " + str(int(amount)) + " shares | 持仓成本: " + str(round(avg_price, 6)) + " | 钱包: " + wallet
                        print("[" + datetime.now().strftime('%H:%M:%S') + "] " + alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
