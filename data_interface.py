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

    def check_rate_limit(self, headers):
        limit_status = int(headers.get("X-Bapi-Limit-Status", -1))
        limit_reset_timestamp = int(headers.get("X-Bapi-Limit-Reset-Timestamp", time.time()))

        if limit_status <= 2:
            sleep_time = max(0, limit_reset_timestamp - time.time())
            logger.warning(f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time + 1)  # Sleep for an extra second to ensure reset.

    def get_historical_data(self, symbol, interval, limit=150):
        try:
            if self.futures:
                response = self.client.query_kline(symbol=symbol, interval=interval, limit=limit)
            else:
                response = self.client.query_kline(symbol=symbol, interval=interval, limit=limit)

            # Check rate limit from headers
            self.check_rate_limit(response.headers)

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
            if self.futures:
                response = self.client.latest_information_for_symbol(symbol=symbol)
            else:
                response = self.client.latest_information_for_symbol(symbol=symbol)

            # Check rate limit from headers
            self.check_rate_limit(response.headers)

            ticker = float(response['result'][0]['last_price'])
            return ticker
        except Exception as e:
            logger.error(f"Erro inesperado ao obter preço atual: {e}")
            return None

    def get_current_balance(self, asset):
        try:
            if self.futures:
                response = self.client.get_wallet_balance()
            else:
                response = self.client.get_wallet_balance()

            # Check rate limit from headers
            self.check_rate_limit(response.headers)

            return float(response['result'][asset]['equity'])
        except Exception as e:
            logger.error(f"Erro inesperado ao obter saldo: {e}")
            return 0.0

    def get_lot_size(self, symbol):
        try:
            response = self.client.query_symbol()

            # Check rate limit from headers
            self.check_rate_limit(response.headers)

            for s in response['result']:
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
                    response = self.client.place_active_order(symbol=symbol, side="Buy", order_type="Market", qty=quantity)
                elif side.lower() == 'sell':
                    response = self.client.place_active_order(symbol=symbol, side="Sell", order_type="Market", qty=quantity)
                else:
                    logger.error(f"Tipo de ordem não reconhecido: {side}")
                    return None
            else:
                if side.lower() == 'buy':
                    response = self.client.place_active_order(symbol=symbol, side="Buy", order_type="Market", qty=quantity)
                elif side.lower() == 'sell':
                    response = self.client.place_active_order(symbol=symbol, side="Sell", order_type="Market", qty=quantity)
                else:
                    logger.error(f"Tipo de ordem não reconhecido: {side}")
                    return None

            # Check rate limit from headers
            self.check_rate_limit(response.headers)

            return response
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
