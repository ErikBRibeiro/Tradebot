import time
import pandas as pd
from pybit.unified_trading import HTTP
from requests.exceptions import ConnectionError, Timeout
from src.parameters import short_period, long_period
from src.utils import logger, safe_float_conversion
import os

class LiveData:
    def __init__(self, api_key, api_secret, futures=False):
        self.api_key = api_key 
        self.api_secret = api_secret
        self.futures = futures
        if self.futures:
            self.client = HTTP(api_key=api_key, api_secret=api_secret)
        else:
            self.client = HTTP(api_key=api_key, api_secret=api_secret)
        self.current_price = None

    def check_rate_limit(self, headers):
        limit_status = int(headers.get("X-Bapi-Limit-Status", -1))
        limit_reset_timestamp = int(headers.get("X-Bapi-Limit-Reset-Timestamp", time.time()))

        if limit_status <= 2:
            sleep_time = max(0, limit_reset_timestamp - time.time())
            logger.warning(f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time + 1)  # Sleep for an extra second to ensure reset.

    def get_historical_data(self, symbol, interval, limit=150):
        try:
            response = self.client.get_kline(symbol=symbol, interval=interval, limit=limit, category='linear')
            
            if response is None or 'result' not in response:
                logger.error("Resposta inválida ao obter dados históricos.")
                return None

            data = pd.DataFrame(response['result'], columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time'])

            data['close'] = data['close'].apply(safe_float_conversion)
            data['low'] = data['low'].apply(safe_float_conversion)
            data['high'] = data['high'].apply(safe_float_conversion)
            data['volume'] = data['volume'].apply(safe_float_conversion)

            data[f'EMA_{short_period}'] = data['close'].ewm(span=short_period, adjust=False).mean()
            data[f'EMA_{long_period}'] = data['close'].ewm(span=long_period, adjust=False).mean()

            if data[['close', 'low', 'high', 'volume']].isnull().any().any():
                logger.error("Dados corrompidos recebidos da API Bybit.")
                return None

            return data

        except Exception as e:
            logger.error(f"Erro inesperado ao obter dados históricos: {e}")
            return None

    def get_current_price(self, symbol):
        try:
            response = self.client.get_tickers(symbol=symbol, category='linear')

            if response is None or 'result' not in response or len(response['result']['list']) == 0:
                logger.error(f"Erro ao obter preço: resposta inválida ou vazia.")
                return 0  # Retorna 0 em caso de erro

            if 'lastPrice' not in response['result']['list'][0]:
                logger.error(f"Erro ao obter preço: campo 'lastPrice' não encontrado.")
                return 0  # Retorna 0 se o campo não for encontrado

            ticker = float(response['result']['list'][0]['lastPrice'])
            return ticker
        except Exception as e:
            logger.error(f"Erro inesperado ao obter preço atual: {e}")
            return 0

    def get_current_balance(self, asset):
        try:
            response = self.client.get_wallet_balance(accountType="UNIFIED", coin=asset)

            if response is None or 'result' not in response:
                logger.error(f"Erro ao obter saldo: resposta inválida ou vazia.")
                return 0.0

            return float(response['result']['list'][0]['totalEquity'])
        except Exception as e:
            logger.error(f"Erro inesperado ao obter saldo: {e}")
            return 0.0

    def get_lot_size(self, symbol, data_interface):
        try:
            response = data_interface.client.get_positions(symbol=symbol, category="linear", limit=1)
            
            if response is None or 'result' not in response or len(response['result']['list']) == 0:
                logger.error(f"Erro ao obter LOT_SIZE: resposta inválida ou vazia.")
                return None
            
            lot_size = response['result']['list'][0]['size']
            return lot_size

        except Exception as e:
            logger.error(f"Erro inesperado ao obter LOT_SIZE: {e}")
            return None

    def create_order(self, symbol, side, quantity):
        try:
            if self.futures:
                if side.lower() == 'buy':
                    response = self.client.place_order(category='linear', symbol=symbol, isLeverage=1, side='Buy', orderType="Market", qty=quantity)
                else:
                    response = self.client.place_order(category='linear', symbol=symbol, isLeverage=1, side='Buy', orderType="Market", qty=quantity)
            else:
                if side.lower() == 'buy':
                    response = self.client.place_order(category='linear', symbol=symbol, isLeverage=1, side='Buy', orderType="Market", qty=quantity)
                elif side.lower() == 'sell':
                    response = self.client.place_order(category='linear', symbol=symbol, isLeverage=1, side='Sell', orderType="Market", qty=quantity)
                else:
                    logger.error(f"Tipo de ordem não reconhecido: {side}")
                    return None

            if response is None or 'result' not in response:
                logger.error(f"Erro ao criar ordem: resposta inválida ou vazia.")
                return None

            return response
        except Exception as e:
            logger.error(f"Erro inesperado ao criar ordem: {e}")
            return None

    def close_order(self, symbol):
        try:
            response = self.client.place_order(category='linear', symbol=symbol, isLeverage=1, side='Sell', orderType="Market", qty=0, reduceOnly=True, closeOnTrigger=True)

            if response is None or 'result' not in response:
                logger.error(f"Erro ao fechar ordem: resposta inválida ou vazia.")
                return None

            return response
        except Exception as e:
            logger.error(f"Erro inesperado ao fechar ordem: {e}")
            return None

    def update_price_continuously(self, symbol, frequency_per_second=1):
        interval = 1 / frequency_per_second
        while True:
            try:
                self.current_price = self.get_current_price(symbol)
            except Exception as e:
                logger.error(f"Erro ao atualizar o preço continuamente: {e}")
            time.sleep(interval)

    def read_trade_history():
        try:
            file_path = os.path.join('data', 'trade_history.csv')
            df = pd.read_csv(file_path)
            if df.empty:
                logger.info("Histórico de transações vazio.")
                return []
            return df
        except FileNotFoundError:
            logger.warning("Arquivo de histórico de transações não encontrado, iniciando com histórico vazio.")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao ler histórico de transações: {e}")
            return []
