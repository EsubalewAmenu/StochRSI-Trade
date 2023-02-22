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
from common_codes import get_all_spot_coins, get_kline


def open_close_main(symbol, counter, total):
    # print('open_close_mainStarted')

    if not settings.api_key:
        sys.exit("Configurations Error!")
    api_key = settings.api_key
    api_secret_key = settings.api_secret
    tld = settings.tld

    client = Client(api_key, api_secret_key, tld=tld)

    try:
        alt = settings.trade_coin
        crypto = settings.trade_crypto

        #symbol = f"{crypto}{alt}"

        print(f"{counter} out of {total}: {symbol}")

        df = get_kline(symbol, 5)

        twoDayAgoOpen = df.open[1]
        dayBeforeYesterdayOpen = df.open[2]
        yesterdayopen = df.open[3]


        twoDayAgoClose = df.close[1]
        dayBeforeYesterdayClose = df.close[2]
        yesterdayClose = df.close[3]

        # print (" twoDayAgoopen open ", twoDayAgoOpen, " dayBeforeYesterdayopen ", dayBeforeYesterdayOpen, " yesterdayopen " ,yesterdayopen)

        if (twoDayAgoClose < twoDayAgoOpen or dayBeforeYesterdayClose < dayBeforeYesterdayOpen ) and yesterdayClose > yesterdayopen:
            print (f"{bcolors.OKGREEN} Check {symbol} {bcolors.ENDC}")
            
        return None

    except Exception as e:
        print('Error while trading...\n{}\n'.format(traceback.format_exc()))