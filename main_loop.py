import threading
import time
from config import API_KEY, API_SECRET
from data_interface import LiveData
from strategy import TradingStrategy
from metrics import Metrics, start_prometheus_server
from src.utils import read_trade_history, logger
from src.parameters import ativo, timeframe, setup

start_prometheus_server()

def check_last_transaction(data_interface, symbol):
    try:
        response = data_interface.client.get_positions(symbol=symbol, category="linear", limit=1)
        
        if 'result' not in response or 'list' not in response['result'] or len(response['result']['list']) == 0:
            logger.info("Nenhuma posição encontrada. Considerando executar uma compra...")
            return False
        
        position = response['result']['list'][0]
        size = float(position['size'])

        if size > 0:
            return True
        else:
            logger.info("Posição aberta tem tamanho 0, pode considerar comprar.")
            return False
    except Exception as e:
        logger.error(f"Erro ao verificar a última transação: {e}")
        return False

def check_open_position(data_interface, symbol):
    try:
        response = data_interface.client.get_positions(symbol=symbol)
        
        if not response or 'result' not in response or len(response['result']) == 0:
            logger.info("Nenhuma posição aberta encontrada.")
            return None
        
        position = response['result'][0]
        side = position['side']
        size = float(position['size'])

        if size > 0:
            return side
        else:
            return None
    except Exception as e:
        logger.error(f"Erro ao verificar posição aberta: {e}")
        return None

def main_loop():
    metrics = Metrics(ativo)  
    data_interface = LiveData(API_KEY, API_SECRET)
    strategy = TradingStrategy(data_interface, metrics, ativo, timeframe, setup)

    logger.info("SandsBot Bybit iniciado")

    is_comprado_logged = False
    is_not_comprado_logged = False

    trade_history = read_trade_history()

    price_thread = threading.Thread(target=data_interface.update_price_continuously, args=(ativo, 1))
    price_thread.daemon = True
    price_thread.start()

    while True:
        try:
            current_time = time.time()

            is_buy = check_last_transaction(data_interface, ativo)
            metrics.loop_counter_metric.labels(ativo).inc()

            metrics.server_status_metric.set(1)

            if is_buy and not is_comprado_logged:
                logger.info("Bot v2 iniciado - Loop de venda.")
                is_comprado_logged = True
                is_not_comprado_logged = False

            if not is_buy and not is_not_comprado_logged:
                logger.info("Bot v2 iniciado - Loop de compra.")
                is_not_comprado_logged = True
                is_comprado_logged = False

            if is_buy:
                is_buy, trade_history = strategy.sell_logic(trade_history, current_time)
            else:
                is_buy, trade_history = strategy.buy_logic(trade_history, current_time)

        except Exception as e:
            metrics.server_status_metric.set(0)
            offline_start = time.time()
            logger.error(f"Erro inesperado: {e}")
            time.sleep(25)
            offline_duration = time.time() - offline_start
            metrics.server_down_metric_duration.observe(offline_duration)

if __name__ == "__main__":
    main_loop()
