from binance import Client
import pandas as pd
from datetime import datetime
import requests
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utilities import calculate_gain_percentage, calculate_loss_percentage

def fetch_candles(symbol, interval, start_str, end_str=None):
    url = 'https://api.binance.com/api/v3/klines'
    data = []
    limit = 1000
    start_time = int(pd.to_datetime(start_str).timestamp() * 1000)
    end_time = int(pd.to_datetime(end_str).timestamp() * 1000) if end_str else None

    while True:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_time,
            'limit': limit
        }
        if end_time:
            params['endTime'] = end_time

        response = requests.get(url, params=params)
        new_data = response.json()
        if not new_data:
            break
        data.extend(new_data)
        start_time = new_data[-1][0] + 1

    columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
               'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
               'taker_buy_quote_asset_volume', 'ignore']
    df = pd.DataFrame(data, columns=columns)
    df = df[['open', 'high', 'low', 'close', 'open_time', 'close_time']]
    return df

start_date = (datetime.now() - pd.DateOffset(years=1, months=6)).strftime('%Y-%m-%d')
# end_date = (datetime.now() - pd.DateOffset(months=6)).strftime('%Y-%m-%d')
end_date = datetime.now().strftime('%Y-%m-%d')

data = fetch_candles('BTCUSDT', '5m', start_date, end_date)
data['close'] = data['close'].astype(float)
data['low'] = data['low'].astype(float)
data['high'] = data['high'].astype(float)
data['EMA_9'] = data['close'].ewm(span=9, adjust=False).mean()

saldo = 1000

taxa_por_operacao = 0.0153 * 2 # taxa de entrada e de saída -> futuros usdc
# taxa_por_operacao = 0.04125 * 2 # taxa de entrada e de saída -> spot usdc
# taxa_por_operacao = 0.045 * 2 # taxa de entrada e de saída -> spot e futuros usdt
# taxa_por_operacao = 0 # sem taxa de entrada e de saída

# print(data)

print("Início do período:", datetime.fromtimestamp(data['open_time'].iloc[0] / 1000))
print("Final do período: ", datetime.fromtimestamp(data['open_time'].iloc[-1] / 1000))
print("Preço atual:", data['close'].iloc[-1])
print("-------------------")
print("Iniciando avaliação de trades...")

comprado = False

results = {}

for i in range(50, len(data)):
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
            
            # stopgain = buy_price * 1.35 # para 1d
            # stopgain = buy_price * 1.1 # para 4h
            # stopgain = buy_price * 1.05 # para 1h
            # stopgain = buy_price * 1.05 # para 1h no ETH
            # stopgain = buy_price * 1.015 # para 15m
            # stopgain = buy_price * 1.085 # para 5m (valor atual no bot em operação real para ETH)
            stopgain = buy_price * 1.05 # para 5m (valor atual no bot em operação real para BTC)
            
            comprado = True
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- COMPRAMOS a", buy_price, "com stoploss em", stoploss, "e stopgain em", stopgain)
            continue
    elif comprado:
        if data['low'].iloc[i - 1] <= data['low'].iloc[i - 2]:
            # loss_percentage = (buy_price - data['low'].iloc[i - 2]) / buy_price * 100
            if data['low'].iloc[i - 2] < buy_price:
                loss_percentage = calculate_loss_percentage(buy_price, data['low'].iloc[i - 2])
                results[year][month]['failed_trades'] += 1
                results[year][month]['perda_percentual_total'] += loss_percentage + taxa_por_operacao
                saldo -= saldo * ((loss_percentage + taxa_por_operacao) / 100)
                comprado = False
                # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stoploss, "com PREJUÍZO percentual de", loss_percentage)
                continue
            elif data['low'].iloc[i - 2] >= buy_price:
                profit = calculate_gain_percentage(buy_price, data['low'].iloc[i - 2])
                results[year][month]['lucro'] += profit - taxa_por_operacao
                results[year][month]['successful_trades'] += 1
                saldo += saldo * ((profit - taxa_por_operacao) / 100)
                comprado = False
                # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stopgain, "com LUCRO percentual de", profit)
                continue
        elif data['high'].iloc[i - 1] >= stopgain:
            # profit = (data['close'].iloc[i - 1] - buy_price) / buy_price * 100
            profit = calculate_gain_percentage(buy_price, stopgain)
            results[year][month]['lucro'] += profit - taxa_por_operacao
            results[year][month]['successful_trades'] += 1
            saldo += saldo * ((profit - taxa_por_operacao) / 100)
            comprado = False
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stopgain, "com LUCRO percentual de", profit)
            continue
        # else:
        #     print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "Ainda estamos comprados, esperando a vela fechar para avaliar a próxima ação")
        #     continue
        # elif data['EMA_9'].iloc[i - 2] < data['EMA_9'].iloc[i - 3] and data['EMA_9'].iloc[i - 3] > data['EMA_9'].iloc[i - 4]:
        #     if (data['low'].iloc[i - 1] > data['low'].iloc[i - 2]):
        #         profit = calculate_gain_percentage(buy_price, data['low'].iloc[i - 2])
        #         results[year][month]['lucro'] += profit
        #         results[year][month]['successful_trades'] += 1
        #         comprado = False
        #         # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stopgain, "com LUCRO percentual de", profit)
        #         continue

for year in results:
    print(f"Ano: {year}")
    print(f"  Operações realizadas: {sum([results[year][month]['open_trades'] for month in results[year]])}")
    print(f"  Trades de sucesso: {sum([results[year][month]['successful_trades'] for month in results[year]])}")
    print(f"  Lucro obtido: {sum([results[year][month]['lucro'] for month in results[year]])}")
    print(f"  Ganho médio por trade: {sum([results[year][month]['lucro'] for month in results[year]]) / sum([results[year][month]['successful_trades'] for month in results[year]])}")
    print(f"  Trades em prejuízo: {sum([results[year][month]['failed_trades'] for month in results[year]])}")
    print(f"  Perda total: {sum([results[year][month]['perda_percentual_total'] for month in results[year]])}")
    
    total_loss = sum([results[year][month]['perda_percentual_total'] for month in results[year]])
    total_failed_trades = sum([results[year][month]['failed_trades'] for month in results[year]])

    if total_failed_trades != 0:
        avg_loss_per_trade = total_loss / total_failed_trades
    else:
        avg_loss_per_trade = 0  # or any other value you want to return when there are no failed trades

    print(f"  Perda média por trade: {avg_loss_per_trade}")
    print(f"  Resultado final: {sum([results[year][month]['lucro'] - results[year][month]['perda_percentual_total'] for month in results[year]])}")
    print("Detalhes:")
    for month in results[year]:
        print(f"  Mês: {month}")
        print(f"    Operações realizadas: {results[year][month]['open_trades']}")
        print(f"    Trades de sucesso: {results[year][month]['successful_trades']}")
        print(f"    Lucro obtido: {results[year][month]['lucro']}")
        print(f"    Ganho médio por trade: {results[year][month]['lucro'] / results[year][month]['successful_trades']}")
        print(f"    Trades em prejuízo: {results[year][month]['failed_trades']}")
        print(f"    Perda total: {results[year][month]['perda_percentual_total']}")
        
        failed_trades = results[year][month]['failed_trades']
        if failed_trades != 0:
            avg_loss_per_trade = results[year][month]['perda_percentual_total'] / failed_trades
        else:
            avg_loss_per_trade = 0  # or any other value you want to return when there are no failed trades

        print(f"    Perda média por trade: {avg_loss_per_trade}")
        print(f"    Resultado final: {results[year][month]['lucro'] - results[year][month]['perda_percentual_total']}")
        print("-------------------")

print("Total:")
print(f"Operações realizadas: {sum([results[year][month]['open_trades'] for year in results for month in results[year]])}")
print(f"Taxa de acerto: {sum([results[year][month]['successful_trades'] for year in results for month in results[year]]) / sum([results[year][month]['open_trades'] for year in results for month in results[year]]) * 100}%")
print(f"Trades de sucesso: {sum([results[year][month]['successful_trades'] for year in results for month in results[year]])}")
print(f"Lucro obtido: {sum([results[year][month]['lucro'] for year in results for month in results[year]])}")
print(f"Ganho médio por trade: {sum([results[year][month]['lucro'] for year in results for month in results[year]]) / sum([results[year][month]['successful_trades'] for year in results for month in results[year]])}")
print(f"Trades em prejuízo: {sum([results[year][month]['failed_trades'] for year in results for month in results[year]])}")
print(f"Perda total: {sum([results[year][month]['perda_percentual_total'] for year in results for month in results[year]])}")
print(f"Perda média por trade: {sum([results[year][month]['perda_percentual_total'] for year in results for month in results[year]]) / sum([results[year][month]['failed_trades'] for year in results for month in results[year]])}")
print(f"Resultado final: {sum([results[year][month]['lucro'] - results[year][month]['perda_percentual_total'] for year in results for month in results[year]])}")
print(f"Saldo final: {saldo}")
