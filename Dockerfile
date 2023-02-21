FROM adrianomartins/binance-stochastic-rsi-bot

WORKDIR /app

# Move files to /app/
COPY ./app/colors.py /app/
COPY ./app/settings.py /app/
COPY ./app/bot.py /app/


# docker build -t my-stoch-trade-image .