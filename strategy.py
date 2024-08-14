import pandas as pd
from datetime import datetime
from src.utils import logger, update_trade_history, safe_float_conversion, calculate_gain_percentage, calculate_loss_percentage
import time

from src.setups.stopgain import sell_stopgain, set_sell_stopgain_ratio
from src.setups.stoploss import sell_stoploss, set_sell_stoploss_min_candles
from src.setups.emas import buy_double_ema_breakout
from src.parameters import short_period, long_period, ratio, stop_candles, ativo, timeframe, setup  # Importa variáveis de parameters.py

class TradingStrategy:
    def __init__(self, data_interface, metrics, symbol=ativo, interval=timeframe, setup=setup):
        self.data_interface = data_interface
        self.metrics = metrics
        self.symbol = symbol
        self.interval = interval
        self.setup = setup
        self.position_maintained = False
        self.last_log_time = time.time()  # Inicializa o temporizador de logs

    def sell_logic(self, trade_history, current_time):
        if not self.position_maintained:
            logger.info("Loop de venda - Checando condições de venda.")
            self.position_maintained = True

        klines = self.data_interface.client.futures_klines(symbol=self.symbol, interval=self.interval, limit=150)
        data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        
        data['low'] = data['low'].apply(safe_float_conversion)
        data['high'] = data['high'].apply(safe_float_conversion)

        if current_time - self.last_log_time >= 120:
            logger.info("Obtendo preço atual...")
        ticker = self.data_interface.get_current_price(self.symbol)
        if ticker is None:
            if current_time - self.last_log_time >= 120:
                logger.warning("Preço atual não obtido. Tentando novamente...")
            return True, trade_history

        if current_time - self.last_log_time >= 120:
            logger.info(f"Preço atual obtido: {ticker}")

        stoploss = trade_history['stoploss'].iloc[-1]
        stopgain = trade_history['stopgain'].iloc[-1]

        if current_time - self.last_log_time >= 120:
            logger.info(f"Condições de venda - Stoploss: {stoploss}, Stopgain: {stopgain}")

        if sell_stoploss(data['low'].iloc[-1], stoploss) or sell_stopgain(data['high'].iloc[-1], stopgain):
            if current_time - self.last_log_time >= 120:
                logger.info("Condições de venda atendidas, tentando executar venda...")
            start_time = time.time()
            balance_asset = self.data_interface.get_current_balance(self.symbol.replace('USDT', ''))
            lot_size = self.data_interface.get_lot_size(self.symbol)
            if balance_asset > 0 and lot_size:
                quantity_to_sell = (balance_asset // lot_size) * lot_size
                if quantity_to_sell > 0:
                    quantity_to_sell = round(quantity_to_sell, 8)
                    order = self.data_interface.create_order(self.symbol, 'SELL', quantity_to_sell, 'MARKET')
                    if order is not None:
                        trade_duration = time.time() - start_time
                        self.metrics.sell_duration_metric.labels(self.symbol).observe(trade_duration)
                        self.metrics.total_trade_duration += trade_duration
                        if current_time - self.last_log_time >= 120:
                            logger.info(f"Venda realizada em {trade_duration:.2f} segundos. Preço: {ticker}, Stoploss: {stoploss}, Stopgain: {stopgain}")
                        trade_history = update_trade_history(trade_history, ticker)  # Usa a função do utils.py
                        self.metrics.update_metrics_on_sell(ticker, self.symbol)
                        self.position_maintained = False
                        self.last_log_time = current_time
                        return False, trade_history  # Atualiza para indicar que não está mais comprado
                    else:
                        logger.error("Erro ao tentar criar a ordem de venda.")
                else:
                    if current_time - self.last_log_time >= 120:
                        logger.info("Quantidade ajustada para venda é menor que o tamanho do lote.")
                    self.position_maintained = False
                    return False, trade_history
            else:
                if current_time - self.last_log_time >= 120:
                    logger.info("Saldo de ativo insuficiente para venda.")
                self.position_maintained = False
                return False, trade_history

        if current_time - self.last_log_time >= 120:
            logger.info("Condições de venda não atendidas, mantendo posição.")
            self.last_log_time = current_time
        return True, trade_history  # Continua indicando que está comprado

    def buy_logic(self, trade_history, current_time):
        if not self.position_maintained:
            logger.info("Loop de compra - Checando condições de compra.")
            self.position_maintained = True

        klines = self.data_interface.client.futures_klines(symbol=self.symbol, interval=self.interval, limit=150)
        data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

        data['close'] = data['close'].apply(safe_float_conversion)
        data['low'] = data['low'].apply(safe_float_conversion)
        data['high'] = data['high'].apply(safe_float_conversion)
        data['volume'] = data['volume'].apply(safe_float_conversion)
        data[f'EMA_{short_period}'] = data['close'].ewm(span=short_period, adjust=False).mean()
        data[f'EMA_{long_period}'] = data['close'].ewm(span=long_period, adjust=False).mean()

        if data[['close', 'low', 'high', 'volume']].isnull().any().any():
            logger.error("Dados corrompidos recebidos da API Binance.")
            return False, trade_history

        current_price = data['close'].iloc[-1]

        if buy_double_ema_breakout(data, f'EMA_{short_period}', f'EMA_{long_period}'):
            logger.info("Condições de compra atendidas, tentando executar compra...")
            start_time = time.time()

            # Obtém o saldo disponível em USDT
            balance_usdt = self.data_interface.get_current_balance('USDT')
            if balance_usdt > 0:
                # Calcula a quantidade de ativo a ser comprado com todo o saldo USDT disponível
                quantity_to_buy = balance_usdt / current_price

                # Ajusta a quantidade para o tamanho do lote
                lot_size = self.data_interface.get_lot_size(self.symbol)
                if lot_size:
                    quantity_to_buy = (quantity_to_buy // lot_size) * lot_size
                    quantity_to_buy = round(quantity_to_buy, 8)  # Arredonda para 8 casas decimais

                    if quantity_to_buy > 0:
                        order = self.data_interface.create_order(self.symbol, 'BUY', quantity_to_buy, 'MARKET')
                        if order is not None:
                            stoploss = set_sell_stoploss_min_candles(data, stop_candles)
                            stopgain = set_sell_stopgain_ratio(data['close'].iloc[-1], stoploss, ratio)
                            potential_loss = calculate_loss_percentage(current_price, stoploss)
                            potential_gain = calculate_gain_percentage(current_price, stopgain)
                            logger.info(f"Compramos - Preço: {current_price}, Stoploss: {stoploss}, Stopgain: {stopgain}")
                            new_row = pd.DataFrame({
                                'horario': [datetime.now()],
                                'moeda': [self.symbol],
                                'valor_compra': [current_price],
                                'valor_venda': [None],
                                'quantidade_moeda': [quantity_to_buy],
                                'max_referencia': [data['high'].iloc[-2]],
                                'min_referencia': [set_sell_stoploss_min_candles(data, stop_candles)],
                                'stoploss': [stoploss],
                                'stopgain': [stopgain],
                                'potential_loss': [potential_loss],
                                'potential_gain': [potential_gain],
                                'timeframe': [self.interval],
                                'setup': [self.setup],
                                'outcome': [None]
                            })
                            trade_history = pd.concat([trade_history, new_row], ignore_index=True)
                            logger.info(f"Histórico de negociações atualizado com nova compra. Linhas: {len(trade_history)}")
                            trade_history.to_csv('data/trade_history.csv', index=False)
                            self.metrics.buy_prices.append(current_price)
                            self.metrics.update_metrics_on_buy(self.symbol, current_price, stoploss, stopgain, potential_loss, potential_gain)
                            self.position_maintained = False
                            return True, trade_history
                        else:
                            logger.error("Erro ao tentar criar a ordem de compra.")
                            self.position_maintained = False
                            return False, trade_history
                    else:
                        logger.error("Quantidade calculada para compra é menor que o tamanho do lote.")
                else:
                    logger.error("Tamanho do lote não encontrado para o símbolo.")
            else:
                logger.error("Saldo insuficiente em USDT para realizar a compra.")

        if current_time - self.last_log_time >= 120:
            logger.info("Condições de compra não atendidas.")
            self.last_log_time = current_time
        return False, trade_history
