import threading
import time
from config import API_KEY, API_SECRET
from data_interface import LiveData
from strategy import TradingStrategy
from metrics import Metrics, start_prometheus_server
from src.utils import read_trade_history, logger
from src.parameters import ativo as SYMBOL, timeframe as INTERVAL, setup as SETUP

def check_last_transaction(data_interface, symbol):
    try:
        trades = data_interface.client.get_my_trades(symbol=symbol, limit=5)
        if not trades:
            return False
        trades_sorted = sorted(trades, key=lambda x: x['time'], reverse=True)
        last_trade = trades_sorted[0]
        is_buy = last_trade['isBuyer']
        return is_buy
    except Exception as e:
        logger.error(f"Erro ao verificar a última transação: {e}")
        return False

def main_loop():
    start_prometheus_server(8000)
    metrics = Metrics(SYMBOL)
    data_interface = LiveData(API_KEY, API_SECRET)
    strategy = TradingStrategy(data_interface, metrics, SYMBOL, INTERVAL, SETUP)

    is_comprado_logged = False
    is_not_comprado_logged = False
    is_buy = False
    trade_history = read_trade_history()

    last_log_time = time.time()  # Inicializa o temporizador de logs

    # Inicia a atualização contínua do preço em uma thread separada
    price_thread = threading.Thread(target=data_interface.update_price_continuously, args=(SYMBOL, 20))
    price_thread.daemon = True
    price_thread.start()

    while True:
        try:
            current_time = time.time()

            is_buy = check_last_transaction(data_interface, SYMBOL)
            metrics.loop_counter_metric.labels(SYMBOL).inc()

            if is_buy and not is_comprado_logged:
                if current_time - last_log_time >= 120:
                    logger.info("Bot v2 iniciado - Loop de venda.")
                    last_log_time = current_time
                is_comprado_logged = True
                is_not_comprado_logged = False

            if not is_buy and not is_not_comprado_logged:
                if current_time - last_log_time >= 120:
                    logger.info("Bot v2 iniciado - Loop de compra.")
                    last_log_time = current_time
                is_not_comprado_logged = True

            if is_buy:
                if current_time - last_log_time >= 120:
                    logger.info("Executando lógica de venda...")
                    last_log_time = current_time
                is_buy, trade_history = strategy.sell_logic(trade_history, current_time)
            else:
                if current_time - last_log_time >= 120:
                    logger.info("Executando lógica de compra...")
                    last_log_time = current_time
                is_buy, trade_history = strategy.buy_logic(
                    trade_history,
                    current_time
                )

        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            time.sleep(25)

if __name__ == "__main__":
    main_loop()
