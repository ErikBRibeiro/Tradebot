import pandas as pd
import logging
from datetime import datetime
import os

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
    except ValueError:
        return None

def read_trade_history():
    if os.path.exists('data/trade_history.csv'):
        df = pd.read_csv('data/trade_history.csv')
        if not df.empty:
            return df
    return pd.DataFrame()

def update_trade_history(df, sell_price, metrics):
    df.at[df.index[-1], 'valor_venda'] = sell_price
    outcome = calculate_percentage(df.loc[df.index[-1], 'valor_compra'], sell_price)
    df.at[df.index[-1], 'outcome'] = outcome
    df.to_csv('data/trade_history.csv', index=False)
    metrics.transaction_outcome_metric.labels(metrics.symbol).observe(outcome)

def log_trade(trade):
    with open('trades.log', 'a') as f:
        f.write(f"{trade}\n")
