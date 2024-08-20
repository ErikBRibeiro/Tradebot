import time
import pandas as pd
from pybit import HTTP
from requests.exceptions import ConnectionError, Timeout
from src.parameters import short_period, long_period
from src.utils import logger, safe_float_conversion

class LiveData:
    def __init__(self, api_key, api_secret, futures=False):
        self.futures = futures
        if self.futures:
            self.client = HTTP("https://api.bybit.com", api_key=api_key, api_secret=api_secret)
        else:
            self.client = HTTP("https://api.bybit.com", api_key=api_key, api_secret=api_secret)
        self.current_price = None

    def get_historical_data(self, symbol, interval, limit=150):
        try:
            if self.futures:
                klines = self.client.query_kline(symbol=symbol, interval=interval, limit=limit)
            else:
                klines = self.client.query_kline(symbol=symbol, interval=interval, limit=limit)

            data = pd.DataFrame(klines['result'], columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time'])

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
            if self.futures:
                ticker = float(self.client.latest_information_for_symbol(symbol=symbol)['result'][0]['last_price'])
            else:
                ticker = float(self.client.latest_information_for_symbol(symbol=symbol)['result'][0]['last_price'])
            return ticker
        except Exception as e:
            logger.error(f"Erro inesperado ao obter preço atual: {e}")
            return None

    def get_current_balance(self, asset):
        try:
            if self.futures:
                balance_info = self.client.get_wallet_balance()
                return float(balance_info['result'][asset]['equity'])
            else:
                balance_info = self.client.get_wallet_balance()
                return float(balance_info['result'][asset]['equity'])
        except Exception as e:
            logger.error(f"Erro inesperado ao obter saldo: {e}")
            return 0.0

    def get_lot_size(self, symbol):
        try:
            info = self.client.query_symbol()
            for s in info['result']:
                if s['name'] == symbol:
                    return float(s['lot_size_filter']['min_trading_qty'])
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter LOT_SIZE: {e}")
            return None

    def create_order(self, symbol, side, quantity):
        try:
            if self.futures:
                if side.lower() == 'buy':
                    order = self.client.place_active_order(symbol=symbol, side="Buy", order_type="Market", qty=quantity)
                elif side.lower() == 'sell':
                    order = self.client.place_active_order(symbol=symbol, side="Sell", order_type="Market", qty=quantity)
                else:
                    logger.error(f"Tipo de ordem não reconhecido: {side}")
                    return None
            else:
                if side.lower() == 'buy':
                    order = self.client.place_active_order(symbol=symbol, side="Buy", order_type="Market", qty=quantity)
                elif side.lower() == 'sell':
                    order = self.client.place_active_order(symbol=symbol, side="Sell", order_type="Market", qty=quantity)
                else:
                    logger.error(f"Tipo de ordem não reconhecido: {side}")
                    return None
            return order
        except Exception as e:
            logger.error(f"Erro inesperado ao criar ordem: {e}")
            return None

    def update_price_continuously(self, symbol, frequency_per_second=1):
        interval = 1 / frequency_per_second
        while True:
            try:
                self.current_price = self.get_current_price(symbol)
            except Exception as e:
                logger.error(f"Erro ao atualizar o preço continuamente: {e}")
            time.sleep(interval)
