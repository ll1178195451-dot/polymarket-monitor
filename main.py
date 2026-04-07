import requests
import time
from datetime import datetime, timezone, timedelta

THRESHOLD = 50
POLL_INTERVAL = 15

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
    print("监控启动成功 - 阈值 50 shares")

    while True:
        print("[" + datetime.now().strftime('%H:%M:%S') + "] 新一轮检查开始")

        for asset in ["xrp", "sol"]:
            for mins in [5, 15]:
                slug = get_current_slug(asset, mins)
                time_period = get_time_period(mins)
                name = asset.upper() + "_" + str(mins) + "min"

                trades = get_trades(slug)
                print("[" + datetime.now().strftime('%H:%M:%S') + "] 检查 " + name + " 返回 " + str(len(trades)) + " 条交易")

                for trade in trades:
                    size = float(trade.get("size", 0))
                    side = str(trade.get("side", "")).upper()

                    if side == "BUY" and size >= THRESHOLD:
                        wallet = trade.get("proxyWallet", "未知")
                        alert = "买入大单警报 | 市场: " + name + " | 时间段: " + time_period + " | 买入数量: " + str(int(size)) + " shares | 钱包: " + wallet[:8] + "..." + wallet[-6:]
                        print("[" + datetime.now().strftime('%H:%M:%S') + "] " + alert)

        print("[" + datetime.now().strftime('%H:%M:%S') + "] 本轮检查完成，等待 " + str(POLL_INTERVAL) + " 秒\n")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
