from collections import defaultdict

import utils
import setups.emas as emas
import setups.stopgain as StopGain
import setups.stoploss as StopLoss

class EvaluatedStrategy:
    def __init__(self, identifier, starting_balance, trading_tax,
                 historical_data, short_period, long_period, stop_candles,
                 ratio):
        self.identifier = identifier
        self.balance = starting_balance
        self.trading_tax = trading_tax
        self.stop_candles = stop_candles
        self.ratio = ratio

        self.is_holding = False
        self.monthly_results = defaultdict(lambda: defaultdict(
            lambda: {
                'open_trades': 0,
                'lucro': 0,
                'succesful_trades': 0,
                'failed_trades': 0,
                'perda_percentual_total': 0,
                'saldo_inicial': starting_balance,
                'saldo_final': starting_balance,
                'max_drawdown': 0
            }
        ))

        self.computed_short_period = historical_data['close'].ewm(
            span=short_period, adjust=False
            ).mean()

        self.computed_long_period = historical_data['close'].ewm(
            span=long_period, adjust=False
            ).mean()

        self.max_balance = starting_balance
        self.min_balance_since_max = starting_balance
        self.max_drawdown = 0

        self.trades = []
        self.losses = []
        self.gains = []

        self.current_trade = None
        self.stop_gain = None
        self.stop_loss = None
        self.buy_price

    def trade(self, idx, candle, historical_data):
        open_time = candle.open_time
        year = open_time.year
        month = open_time.month

        if self.is_holding:
            if StopLoss.sell_stoploss(candle.low, self.stop_loss):
                loss_percentage = utils.calculate_loss_percentage(self.buy_price, self.stop_loss)
                self.monthly_results[year][month]['failed_trades'] += 1
                self.monthly_results[year][month]['perda_percentual_total'] += loss_percentage + self.trading_tax
                self.balance -= self.balance * (loss_percentage + self.trading_tax) / 100
                self.monthly_results[year][month]['saldo_final'] = self.balance
                comprado = False

                self.current_trade['close_price'] = self.stoploss
                self.current_trade['close_time'] = open_time
                self.current_trade['outcome'] = loss_percentage
                self.current_trade['result'] = 'StopLoss'
                self.trades.append(self.current_trade)
                self.losses.append(-(loss_percentage + self.trading_tax))

                if self.balance < self.min_balance_since_max:
                    self.min_balance_since_max = self.balance
                drawdown = (self.max_balance - self.min_balance_since_max) / self.max_balance * 100

                if drawdown > self.max_drawdown:
                    self.max_drawdown = drawdown

                self.monthly_results[year][month]['max_drawdown'] = self.max_drawdown
                return

            elif StopGain.sell_stopgain(candle.high, self.stopgain):
                profit = utils.calculate_gain_percentage(self.buy_price, self.stopgain)
                self.monthly_results[year][month]['lucro'] += profit - self.trading_tax
                self.monthly_results[year][month]['successful_trades'] += 1
                self.balance += self.balance * ((profit - self.trading_tax) / 100)
                self.monthly_results[year][month]['saldo_final'] = self.balance
                comprado = False

                self.current_trade['close_price'] = self.stopgain
                self.current_trade['close_time'] = open_time
                self.current_trade['outcome'] = profit
                self.current_trade['result'] = 'StopGain'
                self.trades.append(self.current_trade)

                self.gains.append(profit - self.trading_tax)

                if self.balance > self.max_balance:
                    self.max_balance = self.balance
                    self.min_balance_since_max = self.balance
                return

        if not comprado:
            historical_data['ema_short'] = self.computed_short_period
            historical_data['ema_long'] = self.computed_long_period
            if emas.buy_double_ema_breakout(historical_data.iloc[idx - 5:idx], 'ema_short', 'ema_long'):
                self.monthly_results[year][month]['open_trades'] += 1
                buy_price = historical_data['high'].iat[idx - 2]
                stoploss = StopLoss.set_sell_stoploss_min_candles(
                    historical_data.iloc[idx - (self.stop_candles + 1):idx],
                    self.stop_candles)
                if self.trading_tax != 0:
                    self.balance -= self.balance * self.trading_tax / 100
                self.monthly_results[year][month]['saldo_final'] = self.balance
                stopgain = StopGain.set_sell_stopgain_ratio(buy_price, stoploss, self.ratio)
                comprado = True

                self.current_trade = {
                    'open_time': open_time,
                    'buy_price': buy_price,
                    'stoploss': stoploss,
                    'stopgain': stopgain,
                    'close_price': 0,
                    'close_time': 0,
                    'outcome': 0,
                    'result': ''
                }
                return
        pass

    def current_balance(self):
        return self.balance

    def metrics(self):
        return {
            "balance": self.balance,
            "trades": self.trades,
            "monthly_results": self.monthly_results,
            "max_drawdown": self.max_drawdown,
            "gains": self.gains,
            "losses": self.losses
        }
