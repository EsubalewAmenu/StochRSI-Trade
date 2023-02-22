import requests
import random
import settings

def get_all_spot_coins():

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