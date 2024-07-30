import pandas as pd
from datetime import datetime
from src.utils import logger, update_trade_history, safe_float_conversion, calculate_gain_percentage, calculate_loss_percentage
import time

from src.setups.stopgain import sell_stopgain, set_sell_stopgain_ratio
from src.setups.stoploss import sell_stoploss, set_sell_stoploss_min_candles
from src.setups.emas import buy_double_ema_breakout

class TradingStrategy:
    def __init__(self, data_interface, metrics, symbol, quantity, interval, setup):
        self.data_interface = data_interface
        self.metrics = metrics
        self.symbol = symbol
        self.quantity = quantity
        self.interval = interval
        self.setup = setup
        self.position_maintained = False
        self.last_log_time = time.time()  # Inicializa o temporizador de logs

    def sell_logic(self, trade_history, current_time):
        if not self.position_maintained:
            logger.info("Loop de venda - Checando condições de venda.")
            self.position_maintained = True

        klines = self.data_interface.client.get_klines(symbol=self.symbol, interval=self.interval, limit=150)
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
            balance_btc = self.data_interface.get_current_balance('BTC')
            lot_size = self.data_interface.get_lot_size(self.symbol)
            if balance_btc > 0 and lot_size:
                quantity_to_sell = (balance_btc // lot_size) * lot_size
                if quantity_to_sell > 0:
                    quantity_to_sell = round(quantity_to_sell, 8)
                    order = self.data_interface.create_order(self.symbol, 'sell', quantity_to_sell)
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
                    logger.info("Saldo de BTC insuficiente para venda.")
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

        # FIX: VERIFICAR NECESSIDADE DESSA PARTE
        # if len(trade_history) < 10:  # Certifique-se de que há dados suficientes para calcular a EMA
        #     logger.info("Histórico de negociações insuficiente para calcular a EMA.")
        #     return False, trade_history

        klines = self.data_interface.client.get_klines(symbol=self.symbol, interval=self.interval, limit=150)
        data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

        data['close'] = data['close'].apply(safe_float_conversion)
        data['low'] = data['low'].apply(safe_float_conversion)
        data['high'] = data['high'].apply(safe_float_conversion)
        data['volume'] = data['volume'].apply(safe_float_conversion)
        data['EMA_9'] = data['close'].ewm(span=9, adjust=False).mean()
        data['EMA_21'] = data['close'].ewm(span=21, adjust=False).mean()

        if data[['close', 'low', 'high', 'volume']].isnull().any().any():
            logger.error("Dados corrompidos recebidos da API Binance.")
            return False, trade_history

        current_price = data['close'].iloc[-1]

        # FIX: VERIFICAR NECESSIDADE DESSA PARTE -> lógica de compra foi alterada para usar a função buy_double_ema_breakout e considera 2 médias móveis além de outra forma de avaliar o preço em relação às EMAs
        # if current_time - self.last_log_time >= 120:
        #     logger.info(f"Valores de compra - previous_ema: {previous_ema}, previous_close: {pre_previous_ema}, current_price: {current_price}, previous_high: {previous_high}")

        if buy_double_ema_breakout(data, 'EMA_9', 'EMA_21'):
            logger.info("Condições de compra atendidas, tentando executar compra...")
            start_time = time.time()
            order = self.data_interface.create_order(self.symbol, 'buy', self.quantity)
            if order is not None:
                stoploss = set_sell_stoploss_min_candles(data, 14)
                stopgain = set_sell_stopgain_ratio(data['close'].iloc[-1], stoploss, 3.5)
                potential_loss = calculate_loss_percentage(current_price, stoploss)
                potential_gain = calculate_gain_percentage(current_price, stopgain)
                logger.info(f"Compramos - Preço: {current_price}, Stoploss: {stoploss}, Stopgain: {stopgain}")
                new_row = pd.DataFrame({
                    'horario': [datetime.now()],
                    'moeda': [self.symbol],
                    'valor_compra': [current_price],
                    'valor_venda': [None],
                    'quantidade_moeda': [self.quantity],
                    'max_referencia': [data['high'].iloc[-2]],
                    'min_referencia': [set_sell_stoploss_min_candles(data, 14)],
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
                trade_history.to_csv('data/trade_history.csv', index=False)  # Salva no CSV apenas após uma compra
                self.metrics.buy_prices.append(current_price)
                self.metrics.update_metrics_on_buy(self.symbol, current_price, stoploss, stopgain, potential_loss, potential_gain)
                self.position_maintained = False
                return True, trade_history
            else:
                logger.error("Erro ao tentar criar a ordem de compra.")
                self.position_maintained = False
                return False, trade_history

        if current_time - self.last_log_time >= 120:
            logger.info("Condições de compra não atendidas.")
            self.last_log_time = current_time
        return False, trade_history
