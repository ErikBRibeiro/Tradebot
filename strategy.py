import pandas as pd
from datetime import datetime
from src.utils import logger, update_trade_history, safe_float_conversion, calculate_gain_percentage, calculate_loss_percentage
import time

from src.setups.stopgain import sell_stopgain, set_sell_stopgain_ratio
from src.setups.stoploss import sell_stoploss, set_sell_stoploss_min_candles
from src.setups.emas import buy_double_ema_breakout
from src.parameters import short_period, long_period, ratio, stop_candles, ativo, timeframe, setup  

class TradingStrategy:
    def __init__(self, data_interface, metrics, symbol=ativo, interval=timeframe, setup=setup):
        self.data_interface = data_interface
        self.metrics = metrics
        self.symbol = symbol
        self.interval = interval
        self.setup = setup
        self.position_maintained = False
        self.last_log_time = time.time()

    def sell_logic(self, trade_history, current_time):
        try:
            if not self.position_maintained:
                self.position_maintained = True

            # Verifica se ainda há uma posição aberta antes de tentar vender
            open_position = self.data_interface.client.get_positions(symbol=self.symbol, category='linear')
            if open_position is None or 'result' not in open_position or not open_position['result']['list'] or open_position['result']['list'][0]['size'] == '0':
                self.position_maintained = False
                return False, trade_history  # Inicia o ciclo de compra

            klines = self.data_interface.client.get_kline(symbol=self.symbol, interval=self.interval, limit=150, category='linear')
            if klines is None or 'result' not in klines or 'list' not in klines['result'] or not klines['result']['list']:
                return False, trade_history

            candles = klines['result']['list']
            data = pd.DataFrame(candles, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            data['low'] = data['low'].apply(safe_float_conversion)
            data['high'] = data['high'].apply(safe_float_conversion)

            ticker = self.data_interface.get_current_price(self.symbol)
            if ticker == 0:
                return True, trade_history

            if not trade_history.empty:
                stoploss = trade_history.get('stoploss').iloc[-1] if 'stoploss' in trade_history else None
                stopgain = trade_history.get('stopgain').iloc[-1] if 'stopgain' in trade_history else None
            else:
                stoploss = None
                stopgain = None

            if stoploss is None or stopgain is None:
                return True, trade_history

            # Log do horário da vela de referência para o stoploss e da vela atual
            referencia_time = pd.to_datetime(data['open_time'].iloc[1], unit='ms')
            current_time = pd.to_datetime(data['open_time'].iloc[0], unit='ms')
            logger.info(f"Horário da vela referência para stoploss: {referencia_time}, Horário da vela atual: {current_time}")

            # Emitir um log a cada 10 minutos
            if (pd.Timestamp.now() - self.last_log_time).total_seconds() >= 600:  # 600 segundos = 10 minutos
                logger.info(f"Verificando condições de venda - Stoploss: {stoploss}, Stopgain: {stopgain}, Minima da vela atual: {data['low'].iloc[0]}")
                self.last_log_time = pd.Timestamp.now()

            if sell_stoploss(data['low'].iloc[0], stoploss) or sell_stopgain(data['high'].iloc[0], stopgain):
                start_time = time.time()
                balance_asset = self.data_interface.get_current_balance('USDT')
                if balance_asset <= 0:
                    return False, trade_history

                lot_size = self.data_interface.get_lot_size(self.symbol, self.data_interface)
                if lot_size is None or float(lot_size) <= 0:
                    return False, trade_history

                order = self.data_interface.close_order(self.symbol)
                if order is not None:
                    trade_duration = time.time() - start_time
                    self.metrics.sell_duration_metric.labels(self.symbol).observe(trade_duration)
                    self.metrics.total_trade_duration += trade_duration

                    outcome = "Stoploss" if sell_stoploss(data['low'].iloc[0], stoploss) else "Stopgain"
                    logger.info(f"Venda realizada em {trade_duration:.2f} segundos. Preço: {ticker}, Resultado: {outcome}, Stoploss: {stoploss}, Stopgain: {stopgain}")

                    self.metrics.transaction_outcome_metric.labels(self.symbol).observe(trade_duration)

                    trade_history = update_trade_history(trade_history, ticker)
                    self.metrics.update_metrics_on_sell(ticker, self.symbol)
                    self.position_maintained = False
                    return False, trade_history
                else:
                    return False, trade_history

            return True, trade_history  
        except Exception as e:
            logger.error(f"Erro em sell_logic: {e}")
            return False, trade_history


    def buy_logic(self, trade_history, current_time):
        try:
            if not self.position_maintained:
                self.position_maintained = True

            klines = self.data_interface.client.get_kline(symbol=self.symbol, interval=self.interval, limit=150, category='linear')
            if klines is None or 'result' not in klines or 'list' not in klines['result'] or not klines['result']['list']:
                return False, trade_history

            candles = klines['result']['list']
            data = pd.DataFrame(candles, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])

            data['close'] = data['close'].apply(safe_float_conversion)
            data['low'] = data['low'].apply(safe_float_conversion)
            data['high'] = data['high'].apply(safe_float_conversion)
            data['volume'] = data['volume'].apply(safe_float_conversion)
            data[f'EMA_{short_period}'] = data['close'].ewm(span=short_period, adjust=False).mean()
            data[f'EMA_{long_period}'] = data['close'].ewm(span=long_period, adjust=False).mean()

            if data[['close', 'low', 'high', 'volume']].isnull().any().any():
                return False, trade_history

            current_price = data['close'].iloc[0]

            if buy_double_ema_breakout(data, f'EMA_{short_period}', f'EMA_{long_period}'):
                start_time = time.time()

                balance_usdt = self.data_interface.get_current_balance('USDT')
                if balance_usdt <= 0:
                    return False, trade_history

                quantity_to_buy = (balance_usdt / current_price)
                truncated_quantity = int(quantity_to_buy * 1000) / 1000  # Truncado para 3 casas decimais

                lot_size = self.data_interface.get_lot_size(self.symbol, self.data_interface)
                if lot_size is None or truncated_quantity <= 0:
                    return False, trade_history

                order = self.data_interface.create_order(self.symbol, 'Buy', truncated_quantity)
                if order is not None:
                    trade_duration = time.time() - start_time
                    self.metrics.buy_duration_metric.labels(self.symbol).observe(trade_duration)

                    stoploss = set_sell_stoploss_min_candles(data, stop_candles)
                    stopgain = set_sell_stopgain_ratio(data['close'].iloc[0], stoploss, ratio)
                    potential_loss = calculate_loss_percentage(current_price, stoploss)
                    potential_gain = calculate_gain_percentage(current_price, stopgain)

                    # Log do horário da vela de referência para o stoploss e da vela atual
                    referencia_time = pd.to_datetime(data['open_time'].iloc[1], unit='ms')
                    current_time = pd.to_datetime(data['open_time'].iloc[0], unit='ms')
                    logger.info(f"Horário da vela referência para stoploss: {referencia_time}, Horário da vela atual: {current_time}")

                    logger.info(f"Compra realizada! Preço: {current_price}, Stoploss: {stoploss}, Stopgain: {stopgain}, Potential Gain: {potential_gain}%, Potential Loss: {potential_loss}%")

                    new_row = pd.DataFrame({
                        'horario': [datetime.now()],
                        'moeda': [self.symbol],
                        'valor_compra': [current_price],
                        'valor_venda': [None],
                        'quantidade_moeda': [truncated_quantity],
                        'max_referencia': [data['high'].iloc[1]],
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
                    trade_history.to_csv('data/trade_history.csv', index=False)
                    self.metrics.buy_prices.append(current_price)
                    self.metrics.update_metrics_on_buy(self.symbol, current_price, stoploss, stopgain, potential_loss, potential_gain)
                    self.position_maintained = False
                    return True, trade_history
                else:
                    return False, trade_history

            # Emitir um log a cada 10 minutos
            if current_time - self.last_log_time >= 600:  # 600 segundos = 10 minutos
                logger.info("Condições de compra não atendidas, mantendo posição.")
                self.last_log_time = current_time

            return True, trade_history
        except Exception as e:
            logger.error(f"Erro em buy_logic: {e}")
            return False, trade_history
