import pandas as pd
from datetime import datetime
from prometheus_client import Gauge, Counter, Histogram, Summary
import os
import logging
from binance import exceptions
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def initialize_metrics():
    # Prometheus metrics
    metrics = {
        'current_price_metric': Gauge('trade_bot_current_price', 'Current price of the asset', ['currency']),
        'current_high_price_metric': Gauge('trade_bot_current_high_price', 'Current high price of the asset', ['currency']),
        'current_low_price_metric': Gauge('trade_bot_current_low_price', 'Current low price of the asset', ['currency']),
        'current_volume_metric': Gauge('trade_bot_current_volume', 'Current trading volume', ['currency']),
        'price_standard_deviation_metric': Gauge('trade_bot_price_standard_deviation', 'Standard deviation of closing prices', ['currency']),
        'buy_duration_metric': Histogram('trade_bot_buy_duration_seconds', 'Duration of buy transactions in seconds', ['currency']),
        'current_stoploss_metric': Gauge('trade_bot_current_stoploss', 'Current stoploss value', ['currency']),
        'current_stopgain_metric': Gauge('trade_bot_current_stopgain', 'Current stopgain value', ['currency']),
        'last_buy_price_metric': Gauge('trade_bot_last_buy_price', 'Last buy price', ['currency']),
        'buy_attempts_metric': Counter('trade_bot_buy_attempts', 'Number of buy attempts', ['currency']),
        'successful_buys_metric': Counter('trade_bot_successful_buys', 'Number of successful buys', ['currency']),
        'buy_price_spread_metric': Gauge('trade_bot_buy_price_spread', 'Spread between buy prices', ['currency']),
        'potential_loss_metric': Gauge('trade_bot_potential_loss', 'Potential loss of current buy', ['currency']),
        'potential_gain_metric': Gauge('trade_bot_potential_gain', 'Potential gain of current buy', ['currency']),
        'last_sell_price_metric': Gauge('trade_bot_last_sell_price', 'Last sell price', ['currency']),
        'successful_sells_metric': Counter('trade_bot_successful_sells', 'Number of successful sells', ['currency']),
        'sell_duration_metric': Histogram('trade_bot_sell_duration_seconds', 'Duration of sell transactions in seconds', ['currency']),
        'transaction_outcome_metric': Summary('trade_bot_transaction_outcome', 'Transaction outcomes (gain/loss)', ['currency']),
        'sell_price_spread_metric': Gauge('trade_bot_sell_price_spread', 'Spread between sell prices', ['currency']),
        'total_trades_metric': Counter('trade_bot_total_trades', 'Total number of trades', ['currency']),
        'total_loss_metric': Gauge('trade_bot_total_loss', 'Total loss accumulated', ['currency']),
        'trade_volume_metric': Gauge('trade_bot_trade_volume', 'Total volume of trades', ['currency']),
        'success_rate_metric': Gauge('trade_bot_success_rate', 'Success rate of trades', ['currency']),
        'total_profit_metric': Gauge('trade_bot_total_profit', 'Total profit accumulated', ['currency']),
        'average_trade_duration_metric': Gauge('trade_bot_average_trade_duration', 'Average duration of trades', ['currency']),
        'profit_factor_metric': Gauge('trade_bot_profit_factor', 'Profit factor (total profit / total loss)', ['currency'])
    }
    return metrics

def update_metrics_on_buy(metrics, current_price, stoploss, stopgain, potential_loss, potential_gain, symbol):
    metrics['current_stoploss_metric'].labels(symbol).set(stoploss)
    metrics['current_stopgain_metric'].labels(symbol).set(stopgain)
    metrics['last_buy_price_metric'].labels(symbol).set(current_price)
    metrics['buy_attempts_metric'].labels(symbol).inc()
    metrics['successful_buys_metric'].labels(symbol).inc()
    metrics['buy_price_spread_metric'].labels(symbol).set(potential_gain - potential_loss)
    metrics['potential_loss_metric'].labels(symbol).set(potential_loss)
    metrics['potential_gain_metric'].labels(symbol).set(potential_gain)

def update_metrics_on_sell(metrics, ticker, symbol):
    metrics['last_sell_price_metric'].labels(symbol).set(ticker)
    metrics['successful_sells_metric'].labels(symbol).inc()
    metrics['sell_price_spread_metric'].labels(symbol).set(ticker)

def buy_condition(data, ema_span):
    previous_ema = data['close'].ewm(span=ema_span, adjust=False).mean().iloc[-2]
    pre_previous_ema = data['close'].ewm(span=ema_span, adjust=False).mean().iloc[-3]
    current_price = data['close'].iloc[-1]
    previous_high = data['high'].iloc[-2]
    return previous_ema > pre_previous_ema and current_price >= previous_high, current_price, previous_high

def sell_condition(ticker, stoploss, stopgain):
    return ticker <= stoploss or ticker >= stopgain

def process_buy(client, symbol, quantity, data, interval, setup, trade_history, stopgain_percentage, metrics):
    buy_prices = []
    start_time = datetime.now()
    order = client.order_market_buy(symbol=symbol, quantity=quantity)
    buy_duration = (datetime.now() - start_time).total_seconds()
    current_price = data['close'].iloc[-1]
    stoploss = data['low'].iloc[-2]
    stopgain = current_price * (1 + stopgain_percentage / 100)
    potential_loss = (stoploss - current_price) / current_price * 100
    potential_gain = (stopgain - current_price) / current_price * 100
    
    logger.info(f"Bought - Potential loss: {potential_loss:.2f}%, Potential gain: {potential_gain:.2f}%")
    logger.info(f"Previous EMA: {data['close'].ewm(span=9, adjust=False).mean().iloc[-2]}, Pre-Previous EMA: {data['close'].ewm(span=9, adjust=False).mean().iloc[-3]}, Current Price: {current_price}, Previous High: {data['high'].iloc[-2]}")

    new_row = pd.DataFrame({
        'horario': [datetime.now()],
        'moeda': [symbol],
        'valor_compra': [current_price],
        'valor_venda': [None],
        'quantidade_moeda': [quantity],
        'max_referencia': [data['high'].iloc[-2]],
        'min_referencia': [data['low'].iloc[-2]],
        'stoploss': [stoploss],
        'stopgain': [stopgain],
        'potential_loss': [potential_loss],
        'potential_gain': [potential_gain],
        'timeframe': [interval],
        'setup': [setup],
        'outcome': [None]
    })

    trade_history = pd.concat([trade_history, new_row], ignore_index=True)
    trade_history.to_csv('data/trade_history.csv', index=False)
    buy_prices.append(current_price)
    
    update_metrics_on_buy(metrics, current_price, stoploss, stopgain, potential_loss, potential_gain, symbol)
    
    return trade_history, buy_prices, stoploss, stopgain, potential_loss, potential_gain, buy_duration

def process_sell(client, symbol, balance_btc, lot_size, ticker, trade_history, metrics):
    sell_prices = []
    start_time = datetime.now()
    if balance_btc > 0 and lot_size:
        quantity_to_sell = (balance_btc // lot_size) * lot_size
        if quantity_to_sell > 0:
            quantity_to_sell = round(quantity_to_sell, 8)
            order = client.order_market_sell(symbol=symbol, quantity=quantity_to_sell)
            sell_duration = (datetime.now() - start_time).total_seconds()
            logger.info("Venda realizada.")
            logger.info(f"Ticker: {ticker}, Stoploss: {trade_history['stoploss'].iloc[-1]}, Stopgain: {trade_history['stopgain'].iloc[-1]}")
            trade_history.loc[trade_history['valor_venda'].isnull(), 'valor_venda'] = ticker
            trade_history.loc[trade_history['outcome'].isnull(), 'outcome'] = "Success"
            trade_history.to_csv('data/trade_history.csv', index=False)
            sell_prices.append(ticker)
            update_metrics_on_sell(metrics, ticker, symbol)
            return True, trade_history, sell_prices, sell_duration
    return False, trade_history, sell_prices, 0

def safe_float_conversion(value):
    try:
        return float(value)
    except ValueError:
        return None

def calculate_standard_deviation(prices):
    return pd.Series(prices).std()

def calculate_percentage(current_price, target_price):
    return ((target_price - current_price) / current_price) * 100

def get_current_balance(client, asset):
    try:
        balance_info = client.get_asset_balance(asset=asset)
        return float(balance_info['free'])
    except exceptions.BinanceAPIException as e:
        logger.error(f"Error in Binance API while getting balance: {e}")
        return 0.0
    except Exception as e:
        logger.error(f"Unexpected error while getting balance: {e}")
        return 0.0

def get_lot_size(client, symbol):
    try:
        info = client.get_symbol_info(symbol)
        for f in info['filters']:
            if (f['filterType'] == 'LOT_SIZE'):
                return float(f['stepSize'])
        return None
    except exceptions.BinanceAPIException as e:
        logger.error(f"Error in Binance API while getting LOT_SIZE: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while getting LOT_SIZE: {e}")
        return None

def read_trade_history():
    if os.path.exists('data/trade_history.csv'):
        df = pd.read_csv('data/trade_history.csv')
        if not df.empty:
            return df
    return pd.DataFrame()

def calculate_profit_factor(total_profit, total_loss):
    return total_profit / abs(total_loss) if total_loss != 0 else float('inf')


def update_trade_history(df, sell_price, symbol, metrics):
    global total_profit, total_loss, total_trade_duration, successful_trades, total_trades, total_trade_volume, buy_prices, sell_prices

    df.at[df.index[-1], 'valor_venda'] = sell_price
    outcome = calculate_percentage(df.loc[df.index[-1], 'valor_compra'], sell_price)
    df.at[df.index[-1], 'outcome'] = outcome
    df.to_csv('data/trade_history.csv', index=False)
    metrics['transaction_outcome_metric'].labels(symbol).observe(outcome)

    if outcome > 0:
        total_profit += outcome
        successful_trades += 1
    else:
        total_loss += outcome

    total_trades += 1
    total_trade_volume += df['quantidade_moeda'].iloc[-1]
    sell_prices.append(sell_price)
    metrics['total_profit_metric'].labels(symbol).set(total_profit)
    metrics['total_loss_metric'].labels(symbol).set(total_loss)
    success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
    metrics['success_rate_metric'].labels(symbol).set(success_rate)
    metrics['total_trades_metric'].labels(symbol).inc()
    average_trade_duration = total_trade_duration / total_trades if total_trades > 0 else 0
    metrics['average_trade_duration_metric'].labels(symbol).set(average_trade_duration)
    metrics['trade_volume_metric'].labels(symbol).set(total_trade_volume)
    metrics['average_sell_price_metric'].labels(symbol).set(sum(sell_prices) / len(sell_prices))
    metrics['profit_factor_metric'].labels(symbol).set(calculate_profit_factor(total_profit, total_loss))

def check_last_transaction(client, symbol):
    try:
        trades = client.get_my_trades(symbol=symbol, limit=5)
        if not trades:
            return False, pd.DataFrame()
        trades_sorted = sorted(trades, key=lambda x: x['time'], reverse=True)
        last_trade = trades_sorted[0]
        is_buy = last_trade['isBuyer']
        trade_history = read_trade_history()
        return is_buy, trade_history
    except exceptions.BinanceAPIException as e:
        logger.error(f"Erro na API Binance: {e}")
        time.sleep(25)
        return check_last_transaction(client, symbol)
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar a última transação: {e}")
        time.sleep(25)
        return check_last_transaction(client, symbol)
