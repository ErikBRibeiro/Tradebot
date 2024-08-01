import pandas as pd
from datetime import datetime
import requests
import plotly.graph_objects as go

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# from utils import calculate_gain_percentage, calculate_loss_percentage
import utils as utils
import setups.emas as emas
import setups.stopgain as StopGain
import setups.stoploss as StopLoss

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

def plot_trades(data, trades):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=data['open_time'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='Candlesticks'
    ))

    fig.add_trace(go.Scatter(
        x=data['open_time'],
        y=data['EMA_9'],
        mode='lines',
        name='EMA 9',
        line=dict(color='green', width=1)
    ))
    fig.add_trace(go.Scatter(
        x=data['open_time'],
        y=data['EMA_21'],
        mode='lines',
        name='EMA 21',
        line=dict(color='yellow', width=1)
    ))

    for trade in trades:
        fig.add_trace(go.Scatter(
            x=[trade['open_time']],
            y=[trade['buy_price']],
            mode='markers',
            marker=dict(color='yellow', size=7, symbol='triangle-down'),
            name='Buy'
        ))
        
        # fig.add_trace(go.Scatter(
        #     x=[trade['open_time']],
        #     y=[trade['buy_price']+500],
        #     mode='markers',
        #     marker=dict(color='yellow', size=50, symbol='triangle-up'),
        #     name=trade['result'].capitalize()
        # ))
        # if trade['outcome'] > 0:
        #     color = 'green'
        # else:
        #     color = 'red'
        

    fig.update_layout(
        title='Trades',
        xaxis_title='Time',
        yaxis_title='Price',
        template='plotly_dark'
    )

    fig.show()

start_date = '2022-12-20'
# end_date = '2024-06-27'
end_date = datetime.now().strftime('%Y-%m-%d')

ativo = 'BTCUSDT'
timeframe = '15m'

data = fetch_candles(ativo, timeframe, start_date, end_date)
data['close'] = data['close'].astype(float)
data['low'] = data['low'].astype(float)
data['high'] = data['high'].astype(float)
data['EMA_9'] = data['close'].ewm(span=9, adjust=False).mean()
data['EMA_21'] = data['close'].ewm(span=21, adjust=False).mean()
data['EMA_80'] = data['close'].ewm(span=90, adjust=False).mean()

saldo = 1000

taxa_por_operacao = 0.0153 # futuros usdc
# taxa_por_operacao = 0.04125 # spot usdc
# taxa_por_operacao = 0.045 # spot e futuros usdt
# taxa_por_operacao = 0 # sem taxa de entrada e de saída

# print(data)

print("Início do período:", datetime.fromtimestamp(data['open_time'].iloc[0] / 1000))
print("Final do período: ", datetime.fromtimestamp(data['open_time'].iloc[-1] / 1000))
print("Preço atual:", data['close'].iloc[-1])
print("-------------------")
print("Iniciando avaliação de trades...")

comprado = False

results = {}
trades = []
trade = {
    'open_time': 0,
    'buy_price': 0,
    'stoploss': 0,
    'stopgain': 0,
    'close_price': 0,
    'close_time': 0,
    'outcome': 0,
    'result': ''
}

for i in range(999, len(data)):
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
            'saldo_inicial': saldo,
            'saldo_final': saldo
        }

    if comprado:
        if StopLoss.sell_stoploss(data['low'].iloc[i - 1], stoploss):
            loss_percentage = utils.calculate_loss_percentage(buy_price, stoploss)
            results[year][month]['failed_trades'] += 1
            results[year][month]['perda_percentual_total'] += loss_percentage + taxa_por_operacao
            saldo -= saldo * ((loss_percentage + taxa_por_operacao) / 100)
            results[year][month]['saldo_final'] = saldo
            comprado = False
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stoploss, "com PREJUÍZO percentual de", loss_percentage)
            
            trade['close_price'] = stoploss
            trade['close_time'] = data['open_time'].iloc[i - 1]
            trade['outcome'] = loss_percentage
            trade['result'] = 'StopLoss'
            trades.append(trade)

            continue
            
        elif StopGain.sell_stopgain(data['high'].iloc[i - 1], stopgain):
            # profit = (data['close'].iloc[i - 1] - buy_price) / buy_price * 100
            profit = utils.calculate_gain_percentage(buy_price, stopgain)
            results[year][month]['lucro'] += profit - taxa_por_operacao
            results[year][month]['successful_trades'] += 1
            saldo += saldo * ((profit - taxa_por_operacao) / 100)
            results[year][month]['saldo_final'] = saldo
            comprado = False
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stopgain, "com LUCRO percentual de", profit)

            trade['close_price'] = stopgain
            trade['close_time'] = data['open_time'].iloc[i - 1]
            trade['outcome'] = profit
            trade['result'] = 'StopGain'
            trades.append(trade)

            continue

        # elif LarryWilliamsHeterodoxo.venda_ema_fechamento(data['EMA_9'].iloc[i - 2], data['close'].iloc[i - 2]):
        #     # verifica se foi loss ou gain
        #     if StopLoss.venda(data['close'].iloc[i - 2], buy_price):
        #         loss_percentage = Utilities.calculate_loss_percentage(buy_price, data['low'].iloc[i - 2])
        #         results[year][month]['failed_trades'] += 1
        #         results[year][month]['perda_percentual_total'] += loss_percentage + taxa_por_operacao
        #         saldo -= saldo * ((loss_percentage + taxa_por_operacao) / 100)
        #         results[year][month]['saldo_final'] = saldo
        #         comprado = False
        #         # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stoploss, "com PREJUÍZO percentual de", loss_percentage)
        #         continue
        #     elif StopGain.venda(data['close'].iloc[i - 2], buy_price):
        #         profit = Utilities.calculate_gain_percentage(buy_price, data['low'].iloc[i - 2])
        #         results[year][month]['lucro'] += profit - taxa_por_operacao
        #         results[year][month]['successful_trades'] += 1
        #         saldo += saldo * ((profit - taxa_por_operacao) / 100)
        #         results[year][month]['saldo_final'] = saldo
        #         comprado = False
        #         # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- Vendemos a", stopgain, "com LUCRO percentual de", profit)
        #         continue

    if not comprado:
        if emas.buy_double_ema_breakout(data.iloc[i - 5:i], 'EMA_9', 'EMA_21'):
        # if data['close'].iloc[i - 2] > data['EMA_21'].iloc[i - 2] and data['close'].iloc[i - 2] > data['EMA_9'].iloc[i - 2] and data['high'].iloc[i - 1] > data['high'].iloc[i - 2]: 
            results[year][month]['open_trades'] += 1
            buy_price = data['high'].iloc[i - 2]
            stoploss = StopLoss.set_sell_stoploss_min_candles(data.iloc[i - 15:i], 14) # stoploss = StopLoss.set_venda_min_candles(data, 14) -> para o código live
            # stoploss = min(data['low'].iloc[i - 14:i])
            if taxa_por_operacao != 0:
                saldo -= saldo * taxa_por_operacao / 100
            results[year][month]['saldo_final'] = saldo
            ratio = 3.5
            stopgain = StopGain.set_sell_stopgain_ratio(buy_price, stoploss, ratio)
            comprado = True
            # print(datetime.fromtimestamp(data['open_time'].iloc[i - 1] / 1000), "- COMPRAMOS a", buy_price, "com stoploss em", stoploss, "e stopgain em", stopgain)
            trade = {
                'open_time': data['open_time'].iloc[i - 1],
                'buy_price': buy_price,
                'stoploss': stoploss,
                'stopgain': stopgain,
                'close_price': 0,
                'close_time': 0,
                'outcome': 0,
                'result': ''
            }
            continue

descricao_setup = "EMA 9/21 rompimento, stopgain ratio " + str(ratio) + " e stoploss 14 candles"

for year in results:
    print(f"Ano: {year}")
    print(f"  Operações realizadas: {sum([results[year][month]['open_trades'] for month in results[year]])}")
    print(f"  Trades de sucesso: {sum([results[year][month]['successful_trades'] for month in results[year]])}")
    print(f"  Soma dos ganhos: {sum([results[year][month]['lucro'] for month in results[year]]):.2f}%")
    try:
        print(f"  Ganho médio por trade: {sum([results[year][month]['lucro'] for month in results[year]]) / sum([results[year][month]['successful_trades'] for month in results[year]]):.2f}%")
    except ZeroDivisionError:
        print(f"  Ganho médio por trade: 0")
    print(f"  Trades em prejuízo: {sum([results[year][month]['failed_trades'] for month in results[year]])}")
    print(f"  Soma das perdas: {sum([results[year][month]['perda_percentual_total'] for month in results[year]]):.2f}%")
    
    total_loss = sum([results[year][month]['perda_percentual_total'] for month in results[year]])
    total_failed_trades = sum([results[year][month]['failed_trades'] for month in results[year]])

    if total_failed_trades != 0:
        avg_loss_per_trade = total_loss / total_failed_trades
    else:
        avg_loss_per_trade = 0

    print(f"  Perda média por trade: {avg_loss_per_trade:.2f}%")
    
    if results[year][list(results[year].keys())[0]]['saldo_inicial'] <= results[year][list(results[year].keys())[-1]]['saldo_final']:
        print(f"  Resultado final: {((results[year][list(results[year].keys())[-1]]['saldo_final'] / results[year][list(results[year].keys())[0]]['saldo_inicial']) - 1) * 100:.2f}%")
    else:
        print(f"  Resultado final: {((1 - (results[year][list(results[year].keys())[-1]]['saldo_final'] / results[year][list(results[year].keys())[0]]['saldo_inicial'])) * -1) * 100:.2f}%")
    
    print(f"  Saldo inicial: {results[year][list(results[year].keys())[0]]['saldo_inicial']:.2f}")
    print(f"  Saldo final: {results[year][list(results[year].keys())[-1]]['saldo_final']:.2f}")
    print("Detalhes:")
    for month in results[year]:
        print(f"  Mês: {month}")
        print(f"    Operações realizadas: {results[year][month]['open_trades']}")
        print(f"    Trades de sucesso: {results[year][month]['successful_trades']}")
        print(f"    Soma dos ganhos: {results[year][month]['lucro']:.2f}%")
        try:
            print(f"    Ganho médio por trade: {results[year][month]['lucro'] / results[year][month]['successful_trades']:.2f}%")
        except ZeroDivisionError:
            print(f"    Ganho médio por trade: 0")
        print(f"    Trades em prejuízo: {results[year][month]['failed_trades']}")
        print(f"    Soma das perdas: {results[year][month]['perda_percentual_total']:.2f}%")
        
        failed_trades = results[year][month]['failed_trades']

        if failed_trades != 0:
            avg_loss_per_trade = results[year][month]['perda_percentual_total'] / failed_trades
        else:
            avg_loss_per_trade = 0

        print(f"    Perda média por trade: {avg_loss_per_trade:.2f}%")

        if results[year][month]['saldo_inicial'] <= results[year][month]['saldo_final']:
            print(f"    Resultado final: {(results[year][month]['saldo_final'] / results[year][month]['saldo_inicial'] - 1) * 100:.2f}%")
        else:
            print(f"    Resultado final: {((1 - (results[year][month]['saldo_final'] / results[year][month]['saldo_inicial'])) * -1) * 100:.2f}%")

        print(f"    Saldo inicial: {results[year][month]['saldo_inicial']:.2f}")
        print(f"    Saldo final: {results[year][month]['saldo_final']:.2f}")
        print("-------------------")

print("Total:")
print(f"Operações realizadas: {sum([results[year][month]['open_trades'] for year in results for month in results[year]])}")

try:
    print(f"Taxa de acerto: {sum([results[year][month]['successful_trades'] for year in results for month in results[year]]) / sum([results[year][month]['open_trades'] for year in results for month in results[year]]) * 100:.2f}%")
except ZeroDivisionError:
    print(f"Taxa de acerto: 0")
print(f"Trades de sucesso: {sum([results[year][month]['successful_trades'] for year in results for month in results[year]])}")
print(f"Soma dos ganhos: {sum([results[year][month]['lucro'] for year in results for month in results[year]]):.2f}%")

try:
    print(f"Ganho médio por trade: {sum([results[year][month]['lucro'] for year in results for month in results[year]]) / sum([results[year][month]['successful_trades'] for year in results for month in results[year]]):.2f}%")
except ZeroDivisionError:
    print(f"Ganho médio por trade: 0")

print(f"Trades em prejuízo: {sum([results[year][month]['failed_trades'] for year in results for month in results[year]])}")
print(f"Soma das perdas: {sum([results[year][month]['perda_percentual_total'] for year in results for month in results[year]]):.2f}%")
try:
    print(f"Perda média por trade: {sum([results[year][month]['perda_percentual_total'] for year in results for month in results[year]]) / sum([results[year][month]['failed_trades'] for year in results for month in results[year]]):.2f}%")
except ZeroDivisionError:
    print(f"Perda média por trade: 0")

saldo_inicial = results[list(results.keys())[0]][list(results[list(results.keys())[0]].keys())[0]]['saldo_inicial']
saldo_final = results[list(results.keys())[-1]][list(results[list(results.keys())[-1]].keys())[-1]]['saldo_final']

if saldo_inicial <= saldo_final:
    print(f"Resultado final: {(saldo_final / saldo_inicial - 1) * 100:.2f}%")
else:
    print(f"Resultado final: {((1 - (saldo_final / saldo_inicial)) * -1) * 100:.2f}%")

print(f"Saldo inicial: {results[list(results.keys())[0]][list(results[list(results.keys())[0]].keys())[0]]['saldo_inicial']:.2f}")
print(f"Saldo final: {results[list(results.keys())[-1]][list(results[list(results.keys())[-1]].keys())[-1]]['saldo_final']:.2f}")
print("-------------------")
print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Teste finalizado: {ativo} - {timeframe}.")
print(f"Setup: {descricao_setup}")

# print(f"Trades: {trades}")

plot_trades(data, trades)