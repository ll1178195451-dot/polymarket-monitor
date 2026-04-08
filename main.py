import requests
import time
from datetime import datetime, timezone, timedelta

THRESHOLD = 700
POLL_INTERVAL = 15

seen = set()

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

def main():
    print("XRP SOL 5分钟和15分钟监控已启动 (阈值 700 shares，只监控 XRP 和 SOL)")

    while True:
        for asset in ["xrp", "sol"]:          # 严格只监控 XRP 和 SOL
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                time_period = get_time_period(mins)
                name = asset.upper() + "_" + str(mins) + "min"

                trades = get_trades(slug)

                for trade in trades:
                    key = trade.get("id") or trade.get("txHash") or str(trade)
                    if key in seen:
                        continue

                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()
                    wallet = trade.get("proxyWallet", "")

                    if side == "BUY" and size >= THRESHOLD and wallet:
                        seen.add(key)
                        outcome = trade.get("outcome", "").upper()
                        direction = "UP" if outcome == "UP" else "DOWN"
                        price = trade.get("price", "?")
                        alert = "单笔买入大单 | 市场: " + name + " | 时间段: " + time_period + " | 方向: " + direction + " | 数量: " + str(int(size)) + " shares | 均价: " + str(price) + " | 钱包: " + wallet
                        print("[" + datetime.now().strftime('%H:%M:%S') + "] " + alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
