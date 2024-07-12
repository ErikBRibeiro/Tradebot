import pandas as pd
import time

from utils import calculate_percentage, logger
from datetime import datetime

class TradingStrategy:


    def __init__(self, data_interface, metrics, symbol, quantity, interval, setup):
        self.data_interface = data_interface
        self.metrics = metrics
        self.symbol = symbol
        self.quantity = quantity
        self.interval = interval
        self.setup = setup
        self.position_maintained = False


    def evaluate(self, is_buy, trade_history):
        data = self.data_interface.get_historical_data(self.symbol, self.interval)
        if data is None:
            return is_buy, trade_history

        previous_ema = data['close'].ewm(span=9, adjust=False).mean().iloc[-2]
        pre_previous_ema = data['close'].ewm(span=9, adjust=False).mean().iloc[-3]
        current_price = data['close'].iloc[-1]
        previous_high = data['high'].iloc[-2]
        previous_low = data['low'].iloc[-2]

        if is_buy:
            self.sell_logic(current_price, trade_history, previous_low, previous_high)
        else:
            is_buy, trade_history = self.buy_logic(previous_ema, pre_previous_ema, current_price, previous_high, previous_low, trade_history)

        return is_buy, trade_history


    def sell_logic(self, current_price, trade_history, previous_low, previous_high):
        if not self.position_maintained:
            logger.info("Loop de venda - Checando condições de venda.")
            self.position_maintained = True

        while True:
            ticker = self.data_interface.get_current_price(self.symbol)
            if ticker is None:
                return

            stoploss = trade_history['stoploss'].iloc[-1]
            stopgain = trade_history['stopgain'].iloc[-1]
            mid_stoploss = previous_low

            if ticker <= stoploss or ticker >= stopgain or ticker <= mid_stoploss:
                start_time = time.time()
                balance_btc = self.data_interface.get_current_balance('BTC')
                lot_size = self.data_interface.get_lot_size(self.symbol)
                if balance_btc > 0 and lot_size:
                    quantity_to_sell = (balance_btc // lot_size) * lot_size
                    if quantity_to_sell > 0:
                        quantity_to_sell = round(quantity_to_sell, 8)
                        self.data_interface.create_order(self.symbol, 'sell', quantity_to_sell)
                        trade_duration = time.time() - start_time
                        self.metrics.sell_duration_metric.labels(self.symbol).observe(trade_duration)
                        self.metrics.total_trade_duration += trade_duration
                        logger.info("Venda realizada.")
                        self.position_maintained = False
                        trade_history = self.update_trade_history(trade_history, ticker)
                        self.update_metrics_on_sell(ticker)
                        break
                    else:
                        logger.info("Quantidade ajustada para venda é menor que o tamanho do lote.")
                        self.position_maintained = False
                        break
                else:
                    logger.info("Saldo de BTC insuficiente para venda.")
                    self.position_maintained = False
                    break
            time.sleep(1)


    def buy_logic(self, previous_ema, pre_previous_ema, current_price, previous_high, previous_low, trade_history):
        if not self.position_maintained:
            logger.info("Loop de compra - Checando condições de compra.")
            self.position_maintained = True

        if previous_ema > pre_previous_ema and current_price >= previous_high:
            self.data_interface.create_order(self.symbol, 'buy', self.quantity)
            stoploss = previous_low
            stopgain = previous_high * 1.05
            mid_stoploss = previous_low
            potential_loss = calculate_percentage(current_price, stoploss)
            potential_gain = calculate_percentage(current_price, stopgain)
            logger.info(f"Compramos - Potencial de perda: {potential_loss:.2f}%, Potencial de ganho: {potential_gain:.2f}%")
            new_row = pd.DataFrame({
                'horario': [datetime.now()],
                'moeda': [self.symbol],
                'valor_compra': [current_price],
                'valor_venda': [None],
                'quantidade_moeda': [self.quantity],
                'max_referencia': [previous_high],
                'min_referencia': [previous_low],
                'stoploss': [stoploss],
                'stopgain': [stopgain],
                'mid_stoploss': [mid_stoploss],
                'potential_loss': [potential_loss],
                'potential_gain': [potential_gain],
                'timeframe': [self.interval],
                'setup': [self.setup],
                'outcome': [None]
            })
            trade_history = pd.concat([trade_history, new_row], ignore_index=True)
            trade_history.to_csv('data/trade_history.csv', index=False)
            self.metrics.buy_prices.append(current_price)
            self.update_metrics_on_buy(current_price, stoploss, stopgain, mid_stoploss, potential_loss, potential_gain)
            self.position_maintained = False
            return True, trade_history

        return False, trade_history


    def update_trade_history(self, df, sell_price):
        df.at[df.index[-1], 'valor_venda'] = sell_price
        outcome = calculate_percentage(df.loc[df.index[-1], 'valor_compra'], sell_price)
        df.at[df.index[-1], 'outcome'] = outcome
        df.to_csv('data/trade_history.csv', index=False)
        self.metrics.transaction_outcome_metric.labels(self.symbol).observe(outcome)
        return df


    def update_metrics_on_sell(self, ticker):
        self.metrics.last_sell_price_metric.labels(self.symbol).set(ticker)
        self.metrics.successful_sells_metric.labels(self.symbol).inc()
        self.metrics.sell_price_spread_metric.labels(self.symbol).set(max(self.metrics.sell_prices) - min(self.metrics.sell_prices) if self.metrics.sell_prices else 0)


    def update_metrics_on_buy(self, current_price, stoploss, stopgain, mid_stoploss, potential_loss, potential_gain):
        self.metrics.current_stoploss_metric.labels(self.symbol).set(stoploss)
        self.metrics.current_stopgain_metric.labels(self.symbol).set(stopgain)
        self.metrics.last_buy_price_metric.labels(self.symbol).set(current_price)
        self.metrics.buy_attempts_metric.labels(self.symbol).inc()
        self.metrics.successful_buys_metric.labels(self.symbol).inc()
        self.metrics.buy_price_spread_metric.labels(self.symbol).set(max(self.metrics.buy_prices) - min(self.metrics.buy_prices) if self.metrics.buy_prices else 0)
        self.metrics.potential_loss_metric.labels(self.symbol).set(potential_loss)
        self.metrics.potential_gain_metric.labels(self.symbol).set(potential_gain)
        self.metrics.mid_stoploss_metric.labels(self.symbol).set(mid_stoploss)
