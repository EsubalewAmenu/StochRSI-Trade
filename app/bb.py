import pandas as pd
from binance.client import Client
from ta.volatility import BollingerBands

API_KEY = 'YOUR_BINANCE_API_KEY'
API_SECRET = 'YOUR_BINANCE_API_SECRET'
client = Client(API_KEY, API_SECRET)

def get_all_usdt_pairs():
    # Fetch futures exchange info
    exchange_info = client.futures_exchange_info()
    # exchange_info = client.get_exchange_info()
    symbols = exchange_info['symbols']
    usdt_pairs = [sym['symbol'] for sym in symbols if sym['quoteAsset'] == 'USDT' and sym['status'] == 'TRADING']
    return usdt_pairs
    
def get_trend(df):
    latest_close = df['close'].iloc[-1]
    one_hour_ago_close = df['close'].iloc[-2]
    
    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    if latest_close > one_hour_ago_close:
        return f"{GREEN}Upward{RESET}"
    elif latest_close < one_hour_ago_close:
        return f"{RED}Downward{RESET}"
    else:
        return "Sideways"


def get_binance_klines(symbol, interval, limit=100):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'trades_count', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def check_bollinger_break(df):
    bollinger = BollingerBands(close=df['close'])
    df['bb_high_indicator'] = bollinger.bollinger_hband_indicator()
    df['bb_low_indicator'] = bollinger.bollinger_lband_indicator()
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    if last_row['bb_high_indicator'] == 1.0 or prev_row['bb_high_indicator'] == 1.0:
        return f"{GREEN}Upper Band Breach{RESET}"
    elif last_row['bb_low_indicator'] == 1.0 or prev_row['bb_low_indicator'] == 1.0:
        return f"{RED}Lower Band Breach{RESET}"
    return None


def scan_symbols(symbol_list, interval):
    breaches = {}
    for symbol in symbol_list:
        main_df = get_binance_klines(symbol, interval)
        breach = check_bollinger_break(main_df)
        if breach:
            df = get_binance_klines(symbol, Client.KLINE_INTERVAL_4HOUR, limit=3)  # At least 3 data points: 2 for the trend and 1 extra for safe measure.
            trend = get_trend(df)
            breaches[symbol] = {"Breach": breach, "Trend": trend}
            print(f"{symbol}: {breach}, {Client.KLINE_INTERVAL_4HOUR} Trend: {trend}     https://www.binance.com/en/futures/{symbol}")
    return breaches
    
usdt_pairs = get_all_usdt_pairs()
interval = Client.KLINE_INTERVAL_3MINUTE
results = scan_symbols(usdt_pairs, interval)
print("Done")
