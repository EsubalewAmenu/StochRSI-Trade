#!python3
import configparser
import datetime
import json
import math
import os
import queue
import random
import time
import traceback
import sys

import pandas as pd
import talib
import numpy as np  # computing multidimensionla arrays
import urllib3

import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException

import settings
from colors import bcolors


def telegram_bot_sendtext(bot_message):
    if settings.telegram_token:
        bot_token = settings.telegram_token
        bot_chatID = settings.telegram_chatid
        send_text = 'https://api.telegram.org/bot' + bot_token + \
            '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        return response.json()


def Stoch(close, high, low, smoothk, smoothd, n):
    lowestlow = pd.Series.rolling(low, window=n, center=False).min()
    highesthigh = pd.Series.rolling(high, window=n, center=False).max()
    K = pd.Series.rolling(
        100*((close-lowestlow)/(highesthigh-lowestlow)), window=smoothk).mean()
    D = pd.Series.rolling(K, window=smoothd).mean()
    return K, D


def retry(howmany):
    def tryIt(func):
        def f(*args, **kwargs):
            time.sleep(1)
            attempts = 0
            while attempts < howmany:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print("Failed to Buy/Sell. Trying Again.")
                    if attempts == 0:
                        print(e)
                        attempts += 1

        return f

    return tryIt


def get_market_ticker_price(client, ticker_symbol):
    '''
    Get ticker price of a specific coin
    '''
    for ticker in client.get_symbol_ticker():
        if ticker[u'symbol'] == ticker_symbol:
            return float(ticker[u'price'])
    return None


def get_currency_balance(client: Client, currency_symbol: str):
    '''
    Get balance of a specific coin
    '''
    for currency_balance in client.get_account()[u'balances']:
        if currency_balance[u'asset'] == currency_symbol:
            return float(currency_balance[u'free'])
    return None


def get_enhanced_error_message(error_code):
    '''
    Get an enhanced error message based on the API error code
    '''
    enhanced_error_messages = dict([(
        -2013, 'Order has not been filled yet.'
    )])
    try:
        return enhanced_error_messages[error_code]
    except:
        return ''


@retry(20)
def buy_alt(client: Client, alt, crypto, price, order_quantity):
    '''
    Buy
    '''

    # Try to buy until successful
    order = None
    while order is None:
        try:
            if int(settings.trade_market) == 1:
                order = client.order_market_buy(
                    symbol=crypto + alt,
                    quantity=order_quantity
                )
            else:
                order = client.order_limit_buy(
                    symbol=crypto + alt,
                    quantity=order_quantity,
                    price=price
                )
        except BinanceAPIException as e:
            print(e)
            time.sleep(1)
        except Exception as e:
            print("Unexpected Error: {0}".format(e))

    print("Waiting for Binance")
    order_recorded = False
    while not order_recorded:
        try:
            time.sleep(3)
            stat = client.get_order(
                symbol=crypto + alt, orderId=order[u'orderId'])
            order_recorded = True
        except BinanceAPIException as e:
            print(e)
            time.sleep(10)
        except Exception as e:
            print("Unexpected Error: {0}".format(e))
    while stat[u'status'] != 'FILLED':
        try:
            stat = client.get_order(
                symbol=crypto + alt, orderId=order[u'orderId'])
            time.sleep(1)
        except BinanceAPIException as e:
            print(e)
            enhanced_error_message = get_enhanced_error_message(e.code)
            if enhanced_error_message:
                print(enhanced_error_message)
            time.sleep(2)
        except Exception as e:
            print("Unexpected Error: {0}".format(e))

    msg = 'Bought {0} of {1}'.format(order_quantity, crypto)
    telegram_bot_sendtext(msg)
    print(msg)

    return order


@retry(20)
def sell_alt(client: Client, alt, crypto, price, order_quantity):
    '''
    Sell
    '''

    bal = get_currency_balance(client, crypto)
    print('Balance is {0}'.format(bal))
    order = None
    while order is None:
        if int(settings.trade_market) == 1:
            order = client.order_market_sell(
                symbol=crypto + alt,
                quantity=(order_quantity)
            )
        else:
            order = client.order_limit_sell(
                symbol=crypto + alt,
                quantity=(order_quantity),
                price=price
            )

    # Binance server can take some time to save the order
    print("Waiting for Binance")
    time.sleep(3)
    order_recorded = False
    stat = None
    while not order_recorded:
        try:
            time.sleep(3)
            stat = client.get_order(
                symbol=crypto + alt, orderId=order[u'orderId'])
            order_recorded = True
        except BinanceAPIException as e:
            print(e)
            time.sleep(10)
        except Exception as e:
            print("Unexpected Error: {0}".format(e))

    while stat[u'status'] != 'FILLED':
        try:
            stat = client.get_order(
                symbol=crypto + alt, orderId=order[u'orderId'])
            time.sleep(1)
        except BinanceAPIException as e:
            print(e)
            enhanced_error_message = get_enhanced_error_message(e.code)
            if enhanced_error_message:
                print(enhanced_error_message)
            time.sleep(2)
        except Exception as e:
            print("Unexpected Error: {0}".format(e))

    newbal = get_currency_balance(client, crypto)
    while (newbal >= bal):
        newbal = get_currency_balance(client, crypto)

    msg = 'Sold {0} of {1}'.format(order_quantity, crypto)
    telegram_bot_sendtext(msg)
    print(msg)

    return order


def main(symbol, counter, total):
    # print('Started')

    if not settings.api_key:
        sys.exit("Configurations Error!")
    api_key = settings.api_key
    api_secret_key = settings.api_secret
    tld = settings.tld

    client = Client(api_key, api_secret_key, tld=tld)

    lastStatus = 0
    lastCloseTrade = None
    lastCloseTradeUp = None
    lastCloseTradeDown = None
    lastCloseUpSUM = 0
    lastCloseDownSUM = 0
    validateBuy = False
    validateSell = False

    try:
        alt = settings.trade_coin
        crypto = settings.trade_crypto

        #symbol = f"{crypto}{alt}"

        print(f"{counter} out of {total}: {symbol}")

        # Get Binance Data into dataframe
        KLINE_INTERVAL = settings.trade_time_frame
        candles = client.get_klines(
            symbol=symbol, interval=KLINE_INTERVAL)
        df = pd.DataFrame(candles)
        df.columns = ['timestart', 'open', 'high', 'low',
                        'close', '?', 'timeend', '?', '?', '?', '?', '?']
        df.timestart = [datetime.datetime.fromtimestamp(
            i/1000) for i in df.timestart.values]
        df.timeend = [datetime.datetime.fromtimestamp(
            i/1000) for i in df.timeend.values]

        # Compute RSI after fixing data
        float_data = [float(x) for x in df.close.values]
        np_float_data = np.array(float_data)
        rsi = talib.RSI(np_float_data, settings.trade_rsi_ifr)
        df['rsi'] = rsi

        # Compute StochRSI using RSI values in Stochastic function
        mystochrsi = Stoch(df.rsi, df.rsi, df.rsi, settings.trade_rsi_k,
                            settings.trade_rsi_d, settings.trade_rsi_stochastic)
        df['MyStochrsiK'], df['MyStochrsiD'] = mystochrsi

        newestcandlestart = df.timestart.astype(
            str).iloc[-1]  # gets last time
        newestcandleend = df.timeend.astype(
            str).iloc[-1]  # gets current time?
        newestcandleclose = round(
            float(df.close.iloc[-1]), 8)  # gets last close
        newestcandleRSI = round(
            float(df.rsi.astype(str).iloc[-1]), 8)  # gets last rsi
        newestcandleK = round(float(df.MyStochrsiK.astype(
            str).iloc[-1]), 8)  # gets last rsi
        newestcandleD = round(float(df.MyStochrsiD.astype(
            str).iloc[-1]), 8)  # gets last rsi

        if  newestcandleK < 20:
            print (f"{bcolors.OKGREEN} {symbol} Oversold {bcolors.ENDC}")
        elif newestcandleK > 90:
            print (f"{bcolors.ALERT} {symbol} Overb {bcolors.ENDC}")
        
        if settings.trade_upper_stoch_validador:
            # Get Binance Data into dataframe
            KLINE_INTERVAL_UPPER = settings.trade_upper_stoch_validador_value
            candlesUpper = client.get_klines(
                symbol=symbol, interval=KLINE_INTERVAL_UPPER)
            dfUpper = pd.DataFrame(candlesUpper)
            dfUpper.columns = ['timestart', 'open', 'high', 'low',
                        'close', '?', 'timeend', '?', '?', '?', '?', '?']
            dfUpper.timestart = [datetime.datetime.fromtimestamp(
                i/1000) for i in dfUpper.timestart.values]
            dfUpper.timeend = [datetime.datetime.fromtimestamp(
                i/1000) for i in dfUpper.timeend.values]

            # Compute RSI after fixing data
            float_data_upper = [float(x) for x in dfUpper.close.values]
            np_float_data_upper = np.array(float_data_upper)
            rsiUpper = talib.RSI(np_float_data_upper, settings.trade_rsi_ifr)
            dfUpper['rsi'] = rsiUpper

            # Compute StochRSI using RSI values in Stochastic function
            mystochrsiUpper = Stoch(dfUpper.rsi, dfUpper.rsi, dfUpper.rsi, settings.trade_rsi_k,
                            settings.trade_rsi_d, settings.trade_rsi_stochastic)
            dfUpper['MyStochrsiK'], dfUpper['MyStochrsiD'] = mystochrsiUpper

            newestcandleKUpper = round(float(dfUpper.MyStochrsiK.astype(
                str).iloc[-1]), 8)  # gets last rsi
            newestcandleDUpper = round(float(dfUpper.MyStochrsiD.astype(
                str).iloc[-1]), 8)  # gets last rsi

        if settings.trade_wma_cross:
            # Compute WMAs
            wmaLow = round(
                float((talib.WMA(df['close'], timeperiod=settings.trade_wma_low)).iloc[-1]), 8)
            wmaMiddle = round(
                float((talib.WMA(df['close'], timeperiod=settings.trade_wma_middle)).iloc[-1]), 8)
            wmaHigh = round(
                float((talib.WMA(df['close'], timeperiod=settings.trade_wma_high)).iloc[-1]), 8)
            # Trade Validator
            if float(wmaLow) > float(wmaMiddle):
                lastClose = df.timeend.iloc[-1]
                if lastClose != lastCloseTradeUp:
                    lastCloseTradeUp = lastClose
                    lastCloseUpSUM += 1
                if lastCloseUpSUM == settings.trade_wma_cross_candle_qtd:
                    if settings.trade_upper_stoch_validador:
                        validateBuy = (float(newestcandleK) > float(newestcandleD)) and (float(newestcandleKUpper) > float(newestcandleDUpper))
                    else:
                        validateBuy = float(newestcandleK) > float(newestcandleD)
                    validateSell = False
                    lastCloseUpSUM = 0
                    lastCloseTradeUp = None
            else:
                validateBuy = False
                lastCloseUpSUM = 0
                lastCloseTradeUp = None
            if float(wmaLow) < float(wmaHigh):
                lastClose = df.timeend.iloc[-1]
                if lastClose != lastCloseTradeDown:
                    lastCloseTrade = lastClose
                    lastCloseDownSUM += 1
                if lastCloseDownSUM == settings.trade_wma_cross_candle_qtd:
                    if settings.trade_upper_stoch_validador:
                        validateSell = (float(newestcandleK) < float(newestcandleD)) 
                    else:
                        validateSell = float(newestcandleK) < float(newestcandleD)
                    validateBuy = False
                    lastCloseDownSUM = 0
                    lastCloseTradeDown = None
            else:
                lastCloseDownSUM = 0
                validateSell = False
                lastCloseTradeDown = None
            statusMsg = f"Price: {newestcandleclose} - RSI: {newestcandleRSI} - K%: {newestcandleK} - D%: {newestcandleD} - WMA {settings.trade_wma_low}: {wmaLow} - WMA {settings.trade_wma_middle}: {wmaMiddle} - WMA {settings.trade_wma_high}: {wmaHigh}"

        if settings.trade_ema_cross:
            # Compute EMAs
            emaLow = round(
                float((talib.EMA(df['close'], timeperiod=settings.trade_ema_low)).iloc[-1]), 8)
            emaHigh = round(
                float((talib.EMA(df['close'], timeperiod=settings.trade_ema_high)).iloc[-1]), 8)
            # Trade Validator
            if settings.trade_upper_stoch_validador:
                validateBuy = (float(newestcandleK) > float(newestcandleD)) and (
                    emaLow > emaHigh) and (float(newestcandleKUpper) > float(newestcandleDUpper)) 
                validateSell = (float(newestcandleK) < float(newestcandleD)) and (
                    emaLow < emaHigh) 
            else:
                validateBuy = (float(newestcandleK) > float(newestcandleD)) and (
                    emaLow > emaHigh)
                validateSell = (newestcandleK < newestcandleD) and (
                    emaLow < emaHigh)
            statusMsg = f"Price: {newestcandleclose} - RSI: {newestcandleRSI} - K%: {newestcandleK} - D%: {newestcandleD} - EMA {settings.trade_ema_low}: {emaLow} - EMA {settings.trade_ema_high}: {emaHigh}"

        if settings.trade_ema_base_candle:
            # Compute EMA
            emaBaseClosed = round(
                float((talib.EMA(df['close'], timeperiod=settings.trade_ema_base_candle_value)).iloc[-1]), 8)
            # Trade Validator
            lastClose = df.timeend.iloc[-1]
            if lastClose != lastCloseTrade:
                lastCloseTrade = lastClose
                if newestcandleclose > emaBaseClosed:
                    lastCloseUpSUM = lastCloseUpSUM + 1
                else:
                    lastCloseUpSUM = 0
                if newestcandleclose < emaBaseClosed:
                    lastCloseDownSUM = lastCloseDownSUM + 1
                else:
                    lastCloseDownSUM = 0
            if lastCloseUpSUM == settings.trade_ema_base_candle_qtd:
                if settings.trade_upper_stoch_validador:
                    validateBuy = (float(newestcandleK) > float(newestcandleD)) and (float(newestcandleKUpper) > float(newestcandleDUpper))
                else:
                    validateBuy = (float(newestcandleK) > float(newestcandleD))
                validateSell = False
                lastCloseUpSUM = 0
                lastCloseTrade = None
            if lastCloseDownSUM == settings.trade_ema_base_candle_qtd:
                if settings.trade_upper_stoch_validador:
                    validateSell = float(newestcandleK) < float(newestcandleD)
                else:
                    validateSell = float(newestcandleK) < float(newestcandleD)
                validateBuy = False
                lastCloseDownSUM = 0
                lastCloseTrade = None
            statusMsg = f"Price: {newestcandleclose} - RSI: {newestcandleRSI} - K%: {newestcandleK} - D%: {newestcandleD} - EMA {settings.trade_ema_low}: {emaLow} - EMA {settings.trade_ema_high}: {emaHigh} - EMA {settings.trade_ema_base_candle_value}: {emaBaseClosed}"

        if not settings.trade_ema_base_candle and not settings.trade_ema_cross and not settings.trade_wma_cross:
            if settings.trade_upper_stoch_validador:
                if (float(newestcandleK) > float(newestcandleD)) and (float(newestcandleKUpper) > float(newestcandleDUpper)):
                    lastClose = df.timeend.iloc[-1]
                    if lastClose != lastCloseTradeUp:
                        lastCloseTradeUp = lastClose
                        lastCloseUpSUM += 1
                    if lastCloseUpSUM == settings.trade_stochrsi_base_candle_qtd:
                        validateBuy = True
                        validateSell = False
                        lastCloseUpSUM = 0
                        lastCloseTradeUp = None
                else:
                    validateBuy = False
                    lastCloseUpSUM = 0
                    lastCloseTradeUp = None
                if (float(newestcandleK) < float(newestcandleD)):
                    lastClose = df.timeend.iloc[-1]
                    if lastClose != lastCloseTradeDown:
                        lastCloseTradeDown = lastClose
                        lastCloseDownSUM += 1
                    if lastCloseDownSUM == settings.trade_stochrsi_base_candle_qtd:
                        validateSell = True
                        validateBuy = False
                        lastCloseDownSUM = 0
                        lastCloseTradeDown = None
                else:
                    validateSell = False
                    lastCloseDownSUM = 0
                    lastCloseTradeDown = None
                statusMsg = f"Price: {newestcandleclose} - RSI: {newestcandleRSI} - K%: {newestcandleK} - D%: {newestcandleD} - Upper K%: {newestcandleKUpper} - Upper D%: {newestcandleDUpper}"
            else:
                if (float(newestcandleK) > float(newestcandleD)):
                    lastClose = df.timeend.iloc[-1]
                    if lastClose != lastCloseTradeUp:
                        lastCloseTradeUp = lastClose
                        lastCloseUpSUM += 1
                    if lastCloseUpSUM == settings.trade_stochrsi_base_candle_qtd:
                        validateBuy = True
                        validateSell = False
                        lastCloseUpSUM = 0
                        lastCloseTradeUp = None
                else:
                    validateBuy = False
                    lastCloseUpSUM = 0
                    lastCloseTradeUp = None
                if (float(newestcandleK) < float(newestcandleD)):
                    lastClose = df.timeend.iloc[-1]
                    if lastClose != lastCloseTradeDown:
                        lastCloseTradeDown = lastClose
                        lastCloseDownSUM += 1
                    if lastCloseDownSUM == settings.trade_stochrsi_base_candle_qtd:
                        validateSell = True
                        validateBuy = False
                        lastCloseDownSUM = 0
                        lastCloseTradeDown = None
                else:
                    validateSell = False
                    lastCloseDownSUM = 0
                    lastCloseTradeDown = None
                statusMsg = f"Price: {newestcandleclose} - RSI: {newestcandleRSI} - K%: {newestcandleK} - D%: {newestcandleD}"

        print(statusMsg)

        result = None
        if validateBuy:
            if lastStatus != 1:
                lastStatus = 1
                asks_lowest = round(
                    float(client.get_orderbook_ticker(symbol=symbol)['askPrice']), 8)
                msg = f"{bcolors.OKGREEN}BUY {symbol} - Price Book: {asks_lowest}{bcolors.ENDC}"
                print(msg)
                ticks = {}
                for filt in client.get_symbol_info(crypto + alt)['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        if filt['stepSize'].find('1') == 0:
                            ticks[alt] = 1 - filt['stepSize'].find('.')
                        else:
                            ticks[alt] = filt['stepSize'].find('1') - 1
                        break
                if settings.trade_limit_coin_balance:
                    balance = float(settings.trade_limit_coin_balance)
                else:
                    balance = get_currency_balance(client, alt)
                order_quantity = ((math.floor(
                    balance * 10 ** ticks[alt] / float(asks_lowest)) / float(10 ** ticks[alt])))
                if order_quantity > 0 or int(settings.notification_only) == 1:
                    if int(settings.notification_only) == 1:
                        msg = f"Notification: Buy {order_quantity} of {crypto} at {asks_lowest} {alt}"
                        telegram_bot_sendtext(msg)
                        print(msg)
                    else:
                        msg = f"Purchasing {order_quantity} of {crypto} at {asks_lowest} {alt}"
                        telegram_bot_sendtext(msg)
                        print(msg)
                        while result is None:
                            result = buy_alt(
                                client, alt, crypto, asks_lowest, order_quantity)
        elif validateSell:
            if lastStatus != 2:
                lastStatus = 2
                bids_highest = round(
                    float(client.get_orderbook_ticker(symbol=symbol)['bidPrice']), 8)
                msg = f"{bcolors.ALERT}SELL  {symbol} - Price Book: {bids_highest}{bcolors.ENDC}"
                print(msg)
                ticks = {}
                for filt in client.get_symbol_info(crypto + alt)['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        if filt['stepSize'].find('1') == 0:
                            ticks[alt] = 1 - \
                                filt['stepSize'].find('.')
                        else:
                            ticks[alt] = filt['stepSize'].find(
                                '1') - 1
                        break
                order_quantity = get_currency_balance(client, crypto)
                if order_quantity > 0 or int(settings.notification_only) == 1:
                    if int(settings.notification_only) == 1:
                        msg = f"Notification: Sell {order_quantity} of {crypto} at {bids_highest} {alt}"
                        telegram_bot_sendtext(msg)
                        print(msg)
                    else:
                        msg = f"Selling {order_quantity} of {crypto} at {bids_highest} {alt}"
                        telegram_bot_sendtext(msg)
                        print(msg)
                        while result is None:
                            result = sell_alt(
                                client, alt, crypto, bids_highest, order_quantity)

        time.sleep(5)

    except Exception as e:
        print('Error while trading...\n{}\n'.format(traceback.format_exc()))


def get_all_coins():

    alt = settings.trade_coin
    

    url = 'https://scanner.tradingview.com/crypto/scan'
    data = '{"filter":[{"left":"exchange","operation":"equal","right":"BINANCE"},{"left":"name,description","operation":"match","right":"'+alt+'$"}],"options":{"lang":"en"},"markets":["crypto"],"symbols":{"query":{"types":[]},"tickers":[]},"columns":["base_currency_logoid","currency_logoid","name","exchange","change_abs|1","description","type","subtype","update_mode"],"sort":{"sortBy":"name","sortOrder":"desc"},"price_conversion":{"to_symbol":false},"range":[0,600]}'

    response = requests.post(url, data=data)

    if response.status_code == 200:
        print('All Coins Request succeeded: Length ', len(response.json()['data']))
        # print(response.content.decode())

        counter = 1

        symbols = [symbol for symbol in response.json()['data']]
        random.shuffle(symbols)
        for symbol in symbols:
            counter += 1
            # if symbol['d'][2].endswith(alt):
            main(symbol['d'][2], counter, len(symbols))
        return "done"
    else:
        print('All Coins Request failed with status code:', response.status_code)
        return None

if __name__ == "__main__":
    print("Started with ", settings.trade_time_frame, " time frame")
    get_all_coins()
    print("done")
    time.sleep(3600)
