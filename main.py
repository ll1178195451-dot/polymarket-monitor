import requests
import time
from datetime import datetime, timezone, timedelta

THRESHOLD = 50
POLL_INTERVAL = 15

def get_current_slug(asset):
    now = int(datetime.now(timezone.utc).timestamp())
    period = (now // 300) * 300   # 5分钟 = 300秒
    return f"{asset}-updown-5m-{period}"

def get_time_period():
    now = datetime.now(timezone.utc)
    minutes_passed = now.minute % 5
    seconds_passed = now.second
    start = now - timedelta(minutes=minutes_passed, seconds=seconds_passed)
    end = start + timedelta(minutes=5)
    hk_start = start.astimezone(timezone(timedelta(hours=8)))
    hk_end = end.astimezone(timezone(timedelta(hours=8)))
    return f"{hk_start.strftime('%H:%M')}-{hk_end.strftime('%H:%M')}"

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
    print("XRP SOL 5分钟 Top Holders 监控 已启动 (阈值 500 shares)")

    while True:
        for asset in ["xrp", "sol"]:
            slug = get_current_slug(asset)
            time_period = get_time_period()
            name = asset.upper() + "_5min"

            holders = get_top_holders(slug)

            for h in holders:
                amount = float(h.get("amount", 0))
                wallet = h.get("proxyWallet")
                outcome = h.get("outcome", "").upper()

                if amount >= THRESHOLD and wallet:
                    direction = "UP" if outcome == "UP" else "DOWN"

                    alert = "大单警报\n"
                    alert += "市场: " + name + "\n"
                    alert += "时间段: " + time_period + "\n"
                    alert += "方向: " + direction + "\n"
                    alert += "总持仓: " + str(int(amount)) + " shares\n"
                    alert += "钱包: " + wallet[:8] + "..." + wallet[-6:] + "\n"
                    alert += "用户页: https://polymarket.com/profile/" + wallet

                    print("[" + datetime.now().strftime('%H:%M:%S') + "] " + alert)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
