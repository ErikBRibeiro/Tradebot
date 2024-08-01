import pandas as pd
from binance.client import Client
from binance import exceptions
from requests.exceptions import ConnectionError, Timeout

from src.utils import logger, safe_float_conversion

class LiveData:
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret, requests_params={'timeout': 20})

    def get_historical_data(self, symbol, interval, limit=150):
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

            data['close'] = data['close'].apply(safe_float_conversion)
            data['low'] = data['low'].apply(safe_float_conversion)
            data['high'] = data['high'].apply(safe_float_conversion)
            data['volume'] = data['volume'].apply(safe_float_conversion)
            data['EMA_9'] = data['close'].ewm(span=9, adjust=False).mean()
            data['EMA_21'] = data['close'].ewm(span=21, adjust=False).mean()

            if data[['close', 'low', 'high', 'volume']].isnull().any().any():
                logger.error("Dados corrompidos recebidos da API Binance.")
                return None

            return data

        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro na API Binance ao obter dados históricos: {e}")
            return None
        except (ConnectionError, Timeout) as e:
            logger.error(f"Erro de conexão ao obter dados históricos: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter dados históricos: {e}")
            return None

    def get_current_price(self, symbol):
        try:
            ticker = float(self.client.get_symbol_ticker(symbol=symbol)['price'])
            return ticker
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro na API Binance ao obter preço atual: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter preço atual: {e}")
            return None

    def get_current_balance(self, asset):
        try:
            balance_info = self.client.get_asset_balance(asset=asset)
            return float(balance_info['free'])
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro na API Binance ao obter saldo: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Erro inesperado ao obter saldo: {e}")
            return 0.0

    def get_lot_size(self, symbol):
        try:
            info = self.client.get_symbol_info(symbol)
            for f in info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    return float(f['stepSize'])
            return None
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro na API Binance ao obter LOT_SIZE: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter LOT_SIZE: {e}")
            return None

    def create_order(self, symbol, side, quantity):
        try:
            if side.lower() == 'buy':
                order = self.client.order_market_buy(symbol=symbol, quantity=quantity)
            elif side.lower() == 'sell':
                order = self.client.order_market_sell(symbol=symbol, quantity=quantity)
            else:
                logger.error(f"Tipo de ordem não reconhecido: {side}")
                return None
            return order
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro ao criar ordem na Binance: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao criar ordem: {e}")
            return None
