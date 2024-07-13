import time
from config import API_KEY, API_SECRET, SYMBOL, QUANTITY, INTERVAL, SETUP
from data_interface import LiveData
from strategy import TradingStrategy
from metrics import Metrics, start_prometheus_server
from utils import read_trade_history, logger

def check_last_transaction(data_interface, symbol, trade_history):
    try:
        trades = data_interface.client.get_my_trades(symbol=symbol, limit=5)
        if not trades:
            return False, trade_history
        trades_sorted = sorted(trades, key=lambda x: x['time'], reverse=True)
        last_trade = trades_sorted[0]
        is_buy = last_trade['isBuyer']
        return is_buy, trade_history
    except Exception as e:
        logger.error(f"Erro ao verificar a última transação: {e}")
        return False, trade_history

def main_loop():
    metrics = Metrics(SYMBOL)
    start_prometheus_server()
    data_interface = LiveData(API_KEY, API_SECRET)
    strategy = TradingStrategy(data_interface, metrics, SYMBOL, QUANTITY, INTERVAL, SETUP)

    is_comprado_logged = False
    is_not_comprado_logged = False
    is_buy = False
    trade_history = read_trade_history()

    last_log_time = time.time()  # Inicializa o temporizador de logs
    last_csv_read_time = time.time()  # Inicializa o temporizador de leitura do CSV

    while True:
        try:
            current_time = time.time()
            
            # Lê o CSV a cada 30 segundos
            if current_time - last_csv_read_time >= 30:
                trade_history = read_trade_history()
                last_csv_read_time = current_time

            is_buy, trade_history = check_last_transaction(data_interface, SYMBOL, trade_history)
            metrics.loop_counter_metric.labels(SYMBOL).inc()

            if is_buy and not is_comprado_logged:
                if current_time - last_log_time >= 30:
                    logger.info("Bot v2 iniciado - Loop de venda.")
                    last_log_time = current_time
                is_comprado_logged = True
                is_not_comprado_logged = False

            if not is_buy and not is_not_comprado_logged:
                if current_time - last_log_time >= 30:
                    logger.info("Bot v2 iniciado - Loop de compra.")
                    last_log_time = current_time
                is_not_comprado_logged = True

            if is_buy:
                if current_time - last_log_time >= 30:
                    logger.info("Executando lógica de venda...")
                    last_log_time = current_time
                is_buy, trade_history = strategy.sell_logic(
                    trade_history['valor_compra'].iloc[-1],
                    trade_history,
                    trade_history['min_referencia'].iloc[-1],
                    trade_history['max_referencia'].iloc[-1]
                )
            else:
                if current_time - last_log_time >= 30:
                    logger.info("Executando lógica de compra...")
                    last_log_time = current_time
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
