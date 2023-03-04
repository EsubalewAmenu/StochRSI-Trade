import requests
import random
import settings
import time
from stoch import stoch_main
from common_codes import get_all_coins
from open_close import open_close_main

if __name__ == "__main__":
    print("Started with ", settings.trade_time_frame, " time frame")
    symbols = get_all_coins()

    counter = 1
    for symbol in symbols:
        counter += 1
        # stoch_main(symbol['d'][2], counter, len(symbols))
        open_close_main(symbol['d'][2], counter, len(symbols))
        time.sleep(5)

    # open_close_main("AGIXBUSDPERP", counter, 1)

    print("done")
    time.sleep(3600)
