import time
import pandas as pd
from binance.client import Client
from binance import exceptions
from requests.exceptions import ConnectionError, Timeout
from src.parameters import short_period, long_period
from src.utils import logger, safe_float_conversion

class LiveData:
    def __init__(self, api_key, api_secret, futures=False):
        self.futures = futures
        if self.futures:
            self.client = Client(api_key, api_secret, requests_params={'timeout': 20})
            self.client.FUTURES_URL = 'https://fapi.binance.com'  # URL da API de Futuros
        else:
            self.client = Client(api_key, api_secret, requests_params={'timeout': 20})
        self.current_price = None

    def get_historical_data(self, symbol, interval, limit=150):
        try:
            if self.futures:
                logger.info(f"Requisitando dados históricos para {symbol} (Futuros) com intervalo {interval}")
                klines = self.client.futures_klines(symbol=symbol, interval=interval, limit=limit)
            else:
                logger.info(f"Requisitando dados históricos para {symbol} com intervalo {interval}")
                klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)

            data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

            data['close'] = data['close'].apply(safe_float_conversion)
            data['low'] = data['low'].apply(safe_float_conversion)
            data['high'] = data['high'].apply(safe_float_conversion)
            data['volume'] = data['volume'].apply(safe_float_conversion)
            
            # Substituindo os valores fixos de EMA pelos valores definidos em parameters.py
            data[f'EMA_{short_period}'] = data['close'].ewm(span=short_period, adjust=False).mean()
            data[f'EMA_{long_period}'] = data['close'].ewm(span=long_period, adjust=False).mean()

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
            if self.futures:
                logger.info(f"Requisitando preço atual para {symbol} (Futuros)")
                ticker = float(self.client.futures_symbol_ticker(symbol=symbol)['price'])
            else:
                logger.info(f"Requisitando preço atual para {symbol}")
                ticker = float(self.client.get_symbol_ticker(symbol=symbol)['price'])
            logger.info(f"Preço atual para {symbol}: {ticker}")
            return ticker
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro na API Binance ao obter preço atual: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter preço atual: {e}")
            return None

    def get_current_balance(self, asset):
        try:
            if self.futures:
                logger.info(f"Requisitando saldo para {asset} (Futuros)")
                balance_info = self.client.futures_account_balance()
                for balance in balance_info:
                    if balance['asset'] == asset:
                        balance_value = float(balance['balance'])
                        logger.info(f"Saldo disponível para {asset}: {balance_value}")
                        return balance_value
            else:
                logger.info(f"Requisitando saldo para {asset}")
                balance_info = self.client.get_asset_balance(asset=asset)
                balance_value = float(balance_info['free'])
                logger.info(f"Saldo disponível para {asset}: {balance_value}")
                return balance_value
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro na API Binance ao obter saldo: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Erro inesperado ao obter saldo: {e}")
            return 0.0

    def get_lot_size(self, symbol):
        try:
            logger.info(f"Requisitando LOT_SIZE para {symbol}")
            info = self.client.get_symbol_info(symbol)
            for f in info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    lot_size = float(f['stepSize'])
                    logger.info(f"LOT_SIZE para {symbol}: {lot_size}")
                    return lot_size
            logger.warning(f"LOT_SIZE não encontrado para {symbol}")
            return None
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro na API Binance ao obter LOT_SIZE: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter LOT_SIZE: {e}")
            return None

    def create_order(self, symbol, side, quantity):
        try:
            logger.info(f"Criando ordem: {side} {quantity} de {symbol}")
            if self.futures:
                if side.lower() == 'buy':
                    order = self.client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=quantity)
                elif side.lower() == 'sell':
                    order = self.client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=quantity)
                else:
                    logger.error(f"Tipo de ordem não reconhecido: {side}")
                    return None
            else:
                if side.lower() == 'buy':
                    order = self.client.order_market_buy(symbol=symbol, quantity=quantity)
                elif side.lower() == 'sell':
                    order = self.client.order_market_sell(symbol=symbol, quantity=quantity)
                else:
                    logger.error(f"Tipo de ordem não reconhecido: {side}")
                    return None
            logger.info(f"Ordem criada com sucesso: {order}")
            return order
        except exceptions.BinanceAPIException as e:
            logger.error(f"Erro ao criar ordem na Binance: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao criar ordem: {e}")
            return None

    def update_price_continuously(self, symbol, frequency_per_second=1):
        interval = 1 / frequency_per_second
        while True:
            try:
                logger.info(f"Atualizando preço continuamente para {symbol}")
                self.current_price = self.get_current_price(symbol)
            except Exception as e:
                logger.error(f"Erro ao atualizar o preço continuamente: {e}")
            time.sleep(interval)
