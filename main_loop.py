import threading
import time
from config import API_KEY, API_SECRET
from data_interface import LiveData
from strategy import TradingStrategy
from metrics import Metrics, start_prometheus_server
from src.utils import read_trade_history, logger
from src.parameters import ativo, timeframe, setup  # Importa variáveis de parameters.py

from binance.exceptions import BinanceAPIException
from requests.exceptions import ConnectionError, Timeout

def check_last_transaction(data_interface, symbol):
    try:
        logger.info(f"Verificando última transação para {symbol} (Futuros)")
        
        # Verifique se há histórico de transações
        trades = data_interface.client.futures_account_trades(symbol=symbol, limit=5)
        
        if not trades or len(trades) == 0:
            logger.info("Nenhuma transação encontrada. Pode ser que não haja histórico de transações para este símbolo.")
            return False

        trades_sorted = sorted(trades, key=lambda x: x['time'], reverse=True)
        last_trade = trades_sorted[0]
        is_buy = last_trade['side'] == 'BUY'  # Verifica se foi uma compra
        return is_buy
    except BinanceAPIException as e:
        logger.error(f"Erro na API Binance ao verificar a última transação: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar a última transação: {e}")
        return False


def main_loop():
    start_prometheus_server(8000)
    metrics = Metrics(ativo)  # Usa o ativo definido em parameters.py
    
    # Inicializa a interface de dados com futuros
    data_interface = LiveData(API_KEY, API_SECRET, futures=True)
    
    strategy = TradingStrategy(data_interface, metrics, ativo, timeframe, setup)

    is_comprado_logged = False
    is_not_comprado_logged = False
    is_buy = False
    trade_history = read_trade_history()

    last_log_time = time.time()  # Inicializa o temporizador de logs

    # Inicia a atualização contínua do preço em uma thread separada com uma frequência reduzida
    price_thread = threading.Thread(target=data_interface.update_price_continuously, args=(ativo, 0.5))  # Reduz a frequência para 0.5 requisições por segundo
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
