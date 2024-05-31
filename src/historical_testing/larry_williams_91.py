from binance import Client
import pandas as pd
from datetime import datetime
import time

script_start = time.time_ns()

api_key = "ok9V7x0ETItBjXJJXp3HZNQbx1rAN26OiGIaPey7DMDm2d2612gU5aVQdT0E82bz"
api_secret = "k15suaXdqzbwfvrYX0qcvNAkXET8EnqjO9JraQhduShjIGQ0YX0kiqXEntTdlRq0"

client = Client(api_key, api_secret)

symbol = "BTCUSDT"
interval = "1h"
# interval = "15m"
# interval = "5m"

time_frame = 1001

klines = client.get_klines(symbol=symbol, interval=interval, limit=time_frame)
data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
data['close'] = data['close'].astype(float)
data['low'] = data['low'].astype(float)
data['high'] = data['high'].astype(float)
data['EMA_9'] = data['close'].ewm(span=9, adjust=False).mean()

print("Início do período:", datetime.fromtimestamp(data['open_time'].iloc[0] / 1000))
print("Final do período: ", datetime.fromtimestamp(data['open_time'].iloc[-1] / 1000))
print("Preço atual:", data['close'].iloc[-1])
print("-------------------")
print("Iniciando avaliação de trades:")

comprado = False

results = {}

for i in range(50, time_frame):
    year = int(datetime.fromtimestamp(data['close_time'].iloc[i - 1] / 1000).year)
    month = int(datetime.fromtimestamp(data['close_time'].iloc[i - 1] / 1000).month)

    if year not in results:
        results[year] = {}
    if month not in results[year]:
        results[year][month] = {
            'open_trades': 0,
            'lucro': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'perda_percentual_total': 0,
        }

    if data['EMA_9'].iloc[i - 2] > data['EMA_9'].iloc[i - 3] and not comprado: # Encontrou a vela referência -> para gatilho e stop do trade::
    # if data['EMA_9'].iloc[i - 2] > data['EMA_9'].iloc[i - 3] and data['EMA_9'].iloc[i - 3] < data['EMA_9'].iloc[i - 4] and not comprado: # Encontrou a vela referência -> para gatilho e stop do trade
        if (data['high'].iloc[i - 1] > data['high'].iloc[i - 2]): # Superou a máxima da vela referência -> ativou o gatilho
            results[year][month]['open_trades'] += 1
            buy_price = data['high'].iloc[i - 2]
            stoploss = data['low'].iloc[i - 2]
            
            stopgain = buy_price * 1.02 # para 1h
            # stopgain = buy_price * 1.015 # para 15m
            # stopgain = buy_price * 1.011 # para 5m
            
            comprado = True
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- COMPRAMOS a", buy_price, "com stoploss em", stoploss, "e stopgain em", stopgain)
            continue
    elif comprado:
        if data['low'].iloc[i - 1] <= stoploss:
            # loss_percentage = (buy_price - data['low'].iloc[i - 2]) / buy_price * 100
            loss_percentage = (buy_price - stoploss) / buy_price * 100
            results[year][month]['failed_trades'] += 1
            results[year][month]['perda_percentual_total'] += loss_percentage
            comprado = False
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stoploss, "com PREJUÍZO percentual de", loss_percentage)
            continue
        elif data['close'].iloc[i - 1] >= stopgain:
            # profit = (data['close'].iloc[i - 1] - buy_price) / buy_price * 100
            profit = (stopgain - buy_price) / buy_price * 100
            results[year][month]['lucro'] += profit
            results[year][month]['successful_trades'] += 1
            comprado = False
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stopgain, "com LUCRO percentual de", profit)
            continue
        # else:
        #     print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "Ainda estamos comprados, esperando a vela fechar para avaliar a próxima ação")
        #     continue

print("Avaliação das operações:")
# print(f"Operações realizadas: {results['open_trades']}")
# print(f"Trades de sucesso: {results['successful_trades']}")
# print(f"Lucro obtido: {results['lucro']}")
# print(f"Trades em prejuízo: {results['failed_trades']}")
# print(f"Percentual de perda total: {results['perda_percentual_total']}")

for year in results:
    print(f"Ano: {year}")
    for month in results[year]:
        print(f"  Mês: {month}")
        print(f"    Operações realizadas: {results[year][month]['open_trades']}")
        print(f"    Trades de sucesso: {results[year][month]['successful_trades']}")
        print(f"    Lucro obtido: {results[year][month]['lucro']}")
        print(f"    Trades em prejuízo: {results[year][month]['failed_trades']}")
        print(f"    Percentual de perda total: {results[year][month]['perda_percentual_total']}")
        print("-------------------")

print("Resultado final:")
print(f"Operações realizadas: {sum([results[year][month]['open_trades'] for year in results for month in results[year]])}")
print(f"Lucro total: {sum([results[year][month]['lucro'] for year in results for month in results[year]])}")
print(f"Trades de sucesso: {sum([results[year][month]['successful_trades'] for year in results for month in results[year]])}")
print(f"Trades em prejuízo: {sum([results[year][month]['failed_trades'] for year in results for month in results[year]])}")
print(f"Percentual de perda total: {sum([results[year][month]['perda_percentual_total'] for year in results for month in results[year]])}")
