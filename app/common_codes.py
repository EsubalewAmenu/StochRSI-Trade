import requests
import random
import settings
import datetime
import traceback

from binance.client import Client
from binance.exceptions import BinanceAPIException

import pandas as pd
import talib
import numpy as np  # computing multidimensionla arrays
import urllib3

def get_all_coins():

    alt = settings.trade_coin
    

    url = 'https://scanner.tradingview.com/crypto/scan'
    data = '{"filter":[{"left":"exchange","operation":"equal","right":"BINANCE"},{"left":"name,description","operation":"match","right":"'+alt+'$"}],"options":{"lang":"en"},"markets":["crypto"],"symbols":{"query":{"types":[]},"tickers":[]},"columns":["base_currency_logoid","currency_logoid","name","exchange","change_abs|1","description","type","subtype","update_mode"],"sort":{"sortBy":"name","sortOrder":"desc"},"price_conversion":{"to_symbol":false},"range":[0,600]}'

    response = requests.post(url, data=data)

    if response.status_code == 200:
        print('All Coins Request succeeded: Length ', len(response.json()['data']))
        # print(response.content.decode())

        # counter = 1

        symbols = [symbol for symbol in response.json()['data']]
        random.shuffle(symbols)
        return symbols
        # for symbol in symbols:
        #     counter += 1
        #     main(symbol['d'][2], counter, len(symbols))
        return "done"
    else:
        print('All Coins Request failed with status code:', response.status_code)
        return None

def get_kline(symbol, LIMIT):

    if not settings.api_key:
        sys.exit("Configurations Error!")
    api_key = settings.api_key
    api_secret_key = settings.api_secret
    tld = settings.tld

    client = Client(api_key, api_secret_key, tld=tld)

    try:
        # Get Binance Data into dataframe
        KLINE_INTERVAL = settings.trade_time_frame

        if symbol.endswith("PERP"):
            symbol = symbol[:-4]
            
            if LIMIT > 0:
                candles = client.futures_klines(
                    symbol=symbol, interval=KLINE_INTERVAL, limit=LIMIT, timeout=120)
            else:
                candles = client.futures_klines(
                    symbol=symbol, interval=KLINE_INTERVAL, timeout=120)
        else:
            if LIMIT > 0:
                candles = client.get_klines(
                    symbol=symbol, interval=KLINE_INTERVAL, limit=LIMIT, timeout=120)
            else:
                candles = client.get_klines(
                    symbol=symbol, interval=KLINE_INTERVAL, timeout=120)



        df = pd.DataFrame(candles)
        df.columns = ['timestart', 'open', 'high', 'low',
                        'close', 'volume', 'timeend', '?', '?', '?', '?', '?']
        df.timestart = [datetime.datetime.fromtimestamp(
            i/1000) for i in df.timestart.values]
        df.timeend = [datetime.datetime.fromtimestamp(
            i/1000) for i in df.timeend.values]


        # Compute RSI after fixing data
        float_data = [float(x) for x in df.close.values]
        np_float_data = np.array(float_data)
        rsi = talib.RSI(np_float_data, settings.trade_rsi_ifr)
        df['rsi'] = rsi

        return df
    except Exception as e:
        print('Error while trading...\n{}\n'.format(traceback.format_exc()))
        return None