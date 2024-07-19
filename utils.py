import os
import pandas as pd
import logging
from prometheus_client import Summary

# Configure o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def calculate_percentage(current_price, target_price):
    return (target_price - current_price) / current_price * 100

def calculate_standard_deviation(prices):
    return pd.Series(prices).std()

def calculate_profit_factor(total_profit, total_loss):
    return total_profit / abs(total_loss) if total_loss != 0 else float('inf')

def safe_float_conversion(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def read_trade_history():
    if os.path.exists('data/trade_history.csv'):
        df = pd.read_csv('data/trade_history.csv')
        if not df.empty:
            return df
    return pd.DataFrame()

# Métricas Prometheus
transaction_outcome_metric = Summary('trade_bot_transaction_outcome', 'Transaction outcomes (gain/loss)', ['currency'])
total_profit_metric = Summary('trade_bot_total_profit', 'Total profit accumulated', ['currency'])
total_loss_metric = Summary('trade_bot_total_loss', 'Total loss accumulated', ['currency'])
success_rate_metric = Summary('trade_bot_success_rate', 'Success rate of trades', ['currency'])
total_trades_metric = Summary('trade_bot_total_trades', 'Total number of trades', ['currency'])
average_trade_duration_metric = Summary('trade_bot_average_trade_duration', 'Average duration of trades', ['currency'])
trade_volume_metric = Summary('trade_bot_trade_volume', 'Total volume of trades', ['currency'])
average_sell_price_metric = Summary('trade_bot_average_sell_price', 'Average sell price', ['currency'])
profit_factor_metric = Summary('trade_bot_profit_factor', 'Profit factor (total profit / total loss)', ['currency'])

def update_trade_history(df, sell_price):
    global total_profit, total_loss, total_trade_duration, successful_trades, total_trades, total_trade_volume, buy_prices, sell_prices
    df.at[df.index[-1], 'valor_venda'] = sell_price
    outcome = calculate_percentage(df.loc[df.index[-1], 'valor_compra'], sell_price)
    df.at[df.index[-1], 'outcome'] = outcome
    df.to_csv('data/trade_history.csv', index=False)
    transaction_outcome_metric.labels(df.loc[df.index[-1], 'moeda']).observe(outcome)

    if outcome > 0:
        total_profit += outcome
        successful_trades += 1
    else:
        total_loss += outcome

    total_trades += 1
    total_trade_volume += df['quantidade_moeda'].iloc[-1]
    sell_prices.append(sell_price)
    total_profit_metric.labels(df.loc[df.index[-1], 'moeda']).set(total_profit)
    total_loss_metric.labels(df.loc[df.index[-1], 'moeda']).set(total_loss)
    success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
    success_rate_metric.labels(df.loc[df.index[-1], 'moeda']).set(success_rate)
    total_trades_metric.labels(df.loc[df.index[-1], 'moeda']).inc()
    average_trade_duration = total_trade_duration / total_trades if total_trades > 0 else 0
    average_trade_duration_metric.labels(df.loc[df.index[-1], 'moeda']).set(average_trade_duration)
    trade_volume_metric.labels(df.loc[df.index[-1], 'moeda']).set(total_trade_volume)
    average_sell_price_metric.labels(df.loc[df.index[-1], 'moeda']).set(sum(sell_prices) / len(sell_prices))
    profit_factor_metric.labels(df.loc[df.index[-1], 'moeda']).set(calculate_profit_factor(total_profit, total_loss))
