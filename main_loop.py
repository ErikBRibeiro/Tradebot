import threading
import time
from config import API_KEY, API_SECRET
from data_interface import LiveData
from strategy import TradingStrategy
from metrics import Metrics, start_prometheus_server
from src.utils import read_trade_history, logger
from src.parameters import ativo, timeframe, setup  

def check_last_transaction(data_interface, symbol):
    try:
        # Obtém a posição atual
        response = data_interface.client.get_positions(symbol=symbol, category="linear", limit=1)
        
        # Verifique se a resposta contém resultados
        if 'result' not in response or 'list' not in response['result'] or len(response['result']['list']) == 0:
            logger.info("Nenhuma posição encontrada. Considerando executar uma compra...")
            return False  # Nenhuma transação anterior, pode comprar
        
        # Obtém a posição e verifica o tamanho
        position = response['result']['list'][0]
        size = float(position['size'])

        if size > 0:
            logger.info(f"Posição aberta encontrada: {position['side']} com tamanho {size}")
            return True  # Já há uma posição long, não compra novamente
        else:
            logger.info("Posição aberta tem tamanho 0, pode considerar comprar.")
            return False  # Não há posição ativa, pode comprar
    except Exception as e:
        logger.error(f"Erro ao verificar a última transação: {e}")
        return False


def check_open_position(data_interface, symbol):
    try:
        response = data_interface.client.get_positions(symbol=symbol)
        
        if not response or 'result' not in response or len(response['result']) == 0:
            logger.info("Nenhuma posição aberta encontrada.")
            return None  # Nenhuma posição aberta
        
        # Verifica a posição aberta
        position = response['result'][0]
        side = position['side']  # "Buy" para long
        size = float(position['size'])

        if size > 0:
            logger.info(f"Posição aberta encontrada: {side} com tamanho {size}")
            return side  # Retorna "Buy"
        else:
            return None  # Nenhuma posição relevante encontrada
    except Exception as e:
        logger.error(f"Erro ao verificar posição aberta: {e}")
        return None


def main_loop():
    metrics = Metrics(ativo)  
    data_interface = LiveData(API_KEY, API_SECRET)
    strategy = TradingStrategy(data_interface, metrics, ativo, timeframe, setup)

    is_comprado_logged = False
    is_not_comprado_logged = False
    last_log_time = time.time()

    # Inicializa trade_history corretamente usando a função ajustada
    trade_history = read_trade_history()

    price_thread = threading.Thread(target=data_interface.update_price_continuously, args=(ativo, 1))
    price_thread.daemon = True
    price_thread.start()

    while True:
        try:
            current_time = time.time()

            is_buy = check_last_transaction(data_interface, ativo)
            metrics.loop_counter_metric.labels(ativo).inc()

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
                # Passe trade_history para a lógica de venda
                is_buy, trade_history = strategy.sell_logic(trade_history, current_time)
            else:
                if current_time - last_log_time >= 120:
                    logger.info("Executando lógica de compra...")
                    last_log_time = current_time
                # Passe trade_history para a lógica de compra
                is_buy, trade_history = strategy.buy_logic(trade_history, current_time)

        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            time.sleep(25)

if __name__ == "__main__":
    main_loop()

