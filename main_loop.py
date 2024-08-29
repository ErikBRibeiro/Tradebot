import threading
import time
from config import API_KEY, API_SECRET
from data_interface import LiveData
from strategy import TradingStrategy
from metrics import Metrics, start_prometheus_server, server_status_metric, server_down_metric_duration
from src.utils import read_trade_history, logger
<<<<<<< HEAD
from src.parameters import ativo, timeframe, setup  # Importa variáveis de parameters.py

from binance.exceptions import BinanceAPIException
from requests.exceptions import ConnectionError, Timeout

def check_last_transaction(data_interface, symbol):
    try:
        logger.info(f"Verificando última transação para {symbol} (Spot)")
        
        # Verifique se há histórico de transações
        trades = data_interface.client.get_my_trades(symbol=symbol, limit=5)
        
        if not trades or len(trades) == 0:
            logger.info("Nenhuma transação encontrada. Pode ser que não haja histórico de transações para este símbolo.")
            return False

        trades_sorted = sorted(trades, key=lambda x: x['time'], reverse=True)
        last_trade = trades_sorted[0]
        is_buy = last_trade['isBuyer']  # Verifica se foi uma compra
        return is_buy
    except BinanceAPIException as e:
        logger.error(f"Erro na API Binance ao verificar a última transação: {e}")
        return False
=======
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
>>>>>>> 5514ccf621f1038e972f413b12c79c83c3ddc0b7
    except Exception as e:
        logger.error(f"Erro ao verificar a última transação: {e}")
        return False

<<<<<<< HEAD

def main_loop():
    start_prometheus_server(8000)
    metrics = Metrics(ativo)  
    
    # Remova o argumento 'futures' ao instanciar LiveData
    data_interface = LiveData(API_KEY, API_SECRET)  
    logger.info(API_KEY)
    logger.info(API_SECRET)
    strategy = TradingStrategy(data_interface, metrics, ativo, timeframe, setup)
=======
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
>>>>>>> 5514ccf621f1038e972f413b12c79c83c3ddc0b7

    is_comprado_logged = False
    is_not_comprado_logged = False

    trade_history = read_trade_history()

<<<<<<< HEAD
    last_log_time = time.time() 

    # Reduza a frequência para uma requisição a cada 5 segundos
    price_thread = threading.Thread(target=data_interface.update_price_continuously, args=(ativo, 0.2))  
=======
    price_thread = threading.Thread(target=data_interface.update_price_continuously, args=(ativo, 1))
>>>>>>> 5514ccf621f1038e972f413b12c79c83c3ddc0b7
    price_thread.daemon = True
    price_thread.start()

    while True:
        try:
            current_time = time.time()

<<<<<<< HEAD
            # Ativar novamente a verificação de transações para Spot
            is_buy = check_last_transaction(data_interface, ativo)
            metrics.loop_counter_metric.labels(ativo).inc()
=======
            is_buy = check_last_transaction(data_interface, ativo)
            metrics.loop_counter_metric.labels(ativo).inc()

            server_status_metric.set(1)
>>>>>>> 5514ccf621f1038e972f413b12c79c83c3ddc0b7

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
            server_status_metric.set(0)
            offline_start = time.time()
            logger.error(f"Erro inesperado: {e}")
            time.sleep(25)
            offline_duration = time.time() - offline_start
            server_down_metric_duration.observe(offline_duration)

if __name__ == "__main__":
    main_loop()
