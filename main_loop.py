import time

from config import API_KEY, API_SECRET, SYMBOL, QUANTITY, INTERVAL, SETUP
from data_interface import LiveData
from strategy import TradingStrategy
from metrics import Metrics, start_prometheus_server
from utils import read_trade_history, logger

def check_last_transaction(data_interface, symbol):
    try:
        trades = data_interface.client.get_my_trades(symbol=symbol, limit=5)
        if not trades:
            return False, read_trade_history()
        trades_sorted = sorted(trades, key=lambda x: x['time'], reverse=True)
        last_trade = trades_sorted[0]
        is_buy = last_trade['isBuyer']
        trade_history = read_trade_history()
        return is_buy, trade_history
    except Exception as e:
        logger.error(f"Erro ao verificar a última transação: {e}")
        return False, read_trade_history()

def main_loop():
    metrics = Metrics(SYMBOL)
    start_prometheus_server()
    data_interface = LiveData(API_KEY, API_SECRET)
    strategy = TradingStrategy(data_interface, metrics, SYMBOL, QUANTITY, INTERVAL, SETUP)

    is_comprado_logged = False
    is_not_comprado_logged = False

    while True:
        try:
            is_buy, trade_history = check_last_transaction(data_interface, SYMBOL)
            metrics.loop_counter_metric.labels(SYMBOL).inc()

            if is_buy and not is_comprado_logged:
                logger.info("Bot v2 iniciado - Loop de venda.")
                is_comprado_logged = True
                is_not_comprado_logged = False

            if not is_buy and not is_not_comprado_logged:
                logger.info("Bot v2 iniciado - Loop de compra.")
                is_not_comprado_logged = True

            if is_buy:
                strategy.sell_logic(trade_history['valor_compra'].iloc[-1], trade_history, trade_history['min_referencia'].iloc[-1], trade_history['max_referencia'].iloc[-1])
            else:
                is_buy, trade_history = strategy.buy_logic(
                    trade_history['valor_compra'].ewm(span=9, adjust=False).mean().iloc[-2],
                    trade_history['valor_compra'].ewm(span=9, adjust=False).mean().iloc[-3],
                    trade_history['valor_compra'].iloc[-1],
                    trade_history['max_referencia'].iloc[-1],
                    trade_history['min_referencia'].iloc[-1],
                    trade_history
                )

        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            time.sleep(25)
            
if __name__ == "__main__":
    main_loop()
