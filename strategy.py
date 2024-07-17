import pandas as pd

from utils import calculate_percentage, logger, calculate_gain_percentage, calculate_loss_percentage
from datetime import datetime

from setups.stopgain import sell_stopgain, set_sell_stopgain_ratio
from setups.stoploss import sell_stoploss, set_sell_stoploss_min_candles
from setups.emas import buy_double_ema_breakout

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

        if is_buy:
            self.sell_logic(data, trade_history)
        else:
            is_buy, trade_history = self.buy_logic(data, trade_history)

        return is_buy, trade_history

    def sell_logic(self, data, trade_history):
        if not self.position_maintained:
            logger.info("Loop de venda - Checando condições de venda.")
            self.position_maintained = True

        ticker = self.data_interface.get_current_price(self.symbol)
        if ticker is None:
            return

        stoploss = trade_history['stoploss'].iloc[-1]
        stopgain = trade_history['stopgain'].iloc[-1]

        if sell_stoploss(data['low'].iloc[-1], stoploss) or sell_stopgain(data['high'].iloc[-1], stopgain):
            balance_btc = self.data_interface.get_current_balance('BTC')
            lot_size = self.data_interface.get_lot_size(self.symbol)
            if balance_btc > 0 and lot_size:
                quantity_to_sell = (balance_btc // lot_size) * lot_size
                if quantity_to_sell > 0:
                    quantity_to_sell = round(quantity_to_sell, 8)
                    self.data_interface.create_order(self.symbol, 'sell', quantity_to_sell)
                    logger.info(f"Venda realizada na vela das {data['open_time']} em {data['close'].iloc[-1]}.")
                    self.position_maintained = False
                    trade_history = self.update_trade_history(trade_history, ticker)
                    self.update_metrics_on_sell(ticker)

    def buy_logic(self, data, trade_history):
        if not self.position_maintained:
            logger.info("Loop de compra - Checando condições de compra.")
            self.position_maintained = True

        if buy_double_ema_breakout(data, 'ema9', 'ema21'):
            self.data_interface.create_order(self.symbol, 'buy', self.quantity)
            stoploss = set_sell_stoploss_min_candles(data, 14)
            stopgain = set_sell_stopgain_ratio(data['close'].iloc[-1], stoploss, 3.5)
            potential_loss = calculate_loss_percentage(data['close'].iloc[-1], stoploss)
            potential_gain = calculate_gain_percentage(data['close'].iloc[-1], stopgain)
            logger.info(f"Compramos na vela das {data['open_time'].iloc[-1]} em {data['close'].iloc[-1]} - Stop Loss em {stoploss}, Potencial de perda: {potential_loss:.2f}%, Stop Gain em {stopgain} Potencial de ganho: {potential_gain:.2f}%")
            new_row = pd.DataFrame({
                'horario': [datetime.now()],
                'moeda': [self.symbol],
                'valor_compra': [data['close'].iloc[-1]],
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
            trade_history.to_csv('data/trade_history.csv', index=False)
            self.metrics.buy_prices.append(data['close'].iloc[-1])
            self.update_metrics_on_buy(data['close'].iloc[-1], stoploss, stopgain, potential_loss, potential_gain)
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

    def update_metrics_on_buy(self, current_price, stoploss, stopgain, potential_loss, potential_gain):
        self.metrics.current_stoploss_metric.labels(self.symbol).set(stoploss)
        self.metrics.current_stopgain_metric.labels(self.symbol).set(stopgain)
        self.metrics.last_buy_price_metric.labels(self.symbol).set(current_price)
        self.metrics.buy_attempts_metric.labels(self.symbol).inc()
        self.metrics.successful_buys_metric.labels(self.symbol).inc()
        self.metrics.buy_price_spread_metric.labels(self.symbol).set(max(self.metrics.buy_prices) - min(self.metrics.buy_prices) if self.metrics.buy_prices else 0)
        self.metrics.potential_loss_metric.labels(self.symbol).set(potential_loss)
        self.metrics.potential_gain_metric.labels(self.symbol).set(potential_gain)
