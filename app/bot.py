import requests
import random
import settings
import time
from stoch import stoch_main
from common_codes import get_all_spot_coins

if __name__ == "__main__":
    print("Started with ", settings.trade_time_frame, " time frame")
    symbols = get_all_spot_coins()

    counter = 1
    for symbol in symbols:
        counter += 1
        stoch_main(symbol['d'][2], counter, len(symbols))
    print("done")
    time.sleep(3600)
