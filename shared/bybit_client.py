import requests
import logging

def get_bybit_ticker(symbol="BTCUSDT"):
    """Fetches real-time ticker data from Bybit Linear (Futures) API."""
    sym = symbol.upper().strip()
    if not sym.endswith("USDT") and not sym.endswith("USDC"):
        sym += "USDT"

    url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={sym}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("retCode") == 0 and data["result"]["list"]:
            item = data["result"]["list"][0]
            last_price = float(item["lastPrice"])
            change_pct = float(item["price24hPcnt"]) * 100
            high_24h = float(item["highPrice24h"])
            low_24h = float(item["lowPrice24h"])
            turnover_24h = float(item["turnover24h"]) / 1_000_000 # in Millions $
            funding_rate = float(item.get("fundingRate", 0)) * 100 # in %
            oi_val = float(item.get("openInterestValue", 0)) / 1_000_000 # in Millions $

            return {
                "symbol": sym,
                "price": last_price,
                "change_pct": change_pct,
                "high_24h": high_24h,
                "low_24h": low_24h,
                "turnover_24h_m": turnover_24h,
                "funding_rate_pct": funding_rate,
                "open_interest_m": oi_val
            }
    except Exception as e:
        logging.error(f"Error fetching Bybit ticker {symbol}: {e}")
    return None

def get_market_overview():
    """Fetches overview for key market leaders."""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    results = []
    for s in symbols:
        t = get_bybit_ticker(s)
        if t:
            results.append(t)
    return results
