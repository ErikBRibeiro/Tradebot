from prometheus_client import start_http_server, Gauge, Counter, Histogram, Summary

class Metrics:
    def __init__(self, symbol):
        self.symbol = symbol
        # Métricas Prometheus
        # Atualizado constantemente
        self.current_price_metric = Gauge('trade_bot_current_price', 'Current price of the asset', ['currency'])
        self.current_trade_volume_metric = Gauge('trade_bot_current_trade_volume', 'Current volume of the asset traded', ['currency'])
        self.total_trades_count_metric = Gauge('trade_bot_total_trades_count', 'Total count of trades', ['currency'])
        self.current_accumulated_profit_metric = Gauge('trade_bot_current_accumulated_profit', 'Current accumulated profit', ['currency'])
        self.current_accumulated_loss_metric = Gauge('trade_bot_current_accumulated_loss', 'Current accumulated loss', ['currency'])
        self.average_buy_price_metric = Gauge('trade_bot_average_buy_price', 'Average buy price', ['currency'])
        self.average_sell_price_metric = Gauge('trade_bot_average_sell_price', 'Average sell price', ['currency'])
        self.current_success_rate_metric = Gauge('trade_bot_current_success_rate', 'Current success rate of trades', ['currency'])
        self.average_trade_time_metric = Gauge('trade_bot_average_trade_time', 'Average time per trade', ['currency'])
        self.price_standard_deviation_metric = Gauge('trade_bot_price_standard_deviation', 'Standard deviation of closing prices', ['currency'])
        self.current_high_price_metric = Gauge('trade_bot_current_high_price', 'Current high price of the asset', ['currency'])
        self.current_low_price_metric = Gauge('trade_bot_current_low_price', 'Current low price of the asset', ['currency'])
        self.current_volume_metric = Gauge('trade_bot_current_volume', 'Current trading volume', ['currency'])

        # Atualizado ao comprar
        self.buy_attempts_metric = Counter('trade_bot_buy_attempts', 'Number of buy attempts', ['currency'])
        self.successful_buys_metric = Counter('trade_bot_successful_buys', 'Number of successful buys', ['currency'])
        self.current_stoploss_metric = Gauge('trade_bot_current_stoploss', 'Current stoploss value', ['currency'])
        self.current_stopgain_metric = Gauge('trade_bot_current_stopgain', 'Current stopgain value', ['currency'])
        self.last_buy_price_metric = Gauge('trade_bot_last_buy_price', 'Last buy price', ['currency'])
        self.buy_duration_metric = Histogram('trade_bot_buy_duration_seconds', 'Duration of buy transactions in seconds', ['currency'])
        self.buy_price_spread_metric = Gauge('trade_bot_buy_price_spread', 'Spread between buy prices', ['currency'])
        self.potential_loss_metric = Gauge('trade_bot_potential_loss', 'Potential loss of current buy', ['currency'])
        self.potential_gain_metric = Gauge('trade_bot_potential_gain', 'Potential gain of current buy', ['currency'])
        self.mid_stoploss_metric = Gauge('trade_bot_mid_stoploss', 'Mid stoploss value', ['currency'])

        # Atualizado ao vender
        self.successful_sells_metric = Counter('trade_bot_successful_sells', 'Number of successful sells', ['currency'])
        self.last_sell_price_metric = Gauge('trade_bot_last_sell_price', 'Last sell price', ['currency'])
        self.sell_duration_metric = Histogram('trade_bot_sell_duration_seconds', 'Duration of sell transactions in seconds', ['currency'])
        self.transaction_outcome_metric = Summary('trade_bot_transaction_outcome', 'Transaction outcomes (gain/loss)', ['currency'])
        self.sell_price_spread_metric = Gauge('trade_bot_sell_price_spread', 'Spread between sell prices', ['currency'])

        # Atualizado após cada trade
        self.total_trades_metric = Counter('trade_bot_total_trades', 'Total number of trades', ['currency'])
        self.total_loss_metric = Gauge('trade_bot_total_loss', 'Total loss accumulated', ['currency'])
        self.trade_volume_metric = Gauge('trade_bot_trade_volume', 'Total volume of trades', ['currency'])
        self.success_rate_metric = Gauge('trade_bot_success_rate', 'Success rate of trades', ['currency'])
        self.total_profit_metric = Gauge('trade_bot_total_profit', 'Total profit accumulated', ['currency'])
        self.average_trade_duration_metric = Gauge('trade_bot_average_trade_duration', 'Average duration of trades', ['currency'])
        self.profit_factor_metric = Gauge('trade_bot_profit_factor', 'Profit factor (total profit / total loss)', ['currency'])

        # Contador para o número de vezes que o loop principal é executado
        self.loop_counter_metric = Counter('trade_bot_loop_executions', 'Number of loop executions', ['currency'])

        # Variáveis para monitorar o lucro, perda e duração total das trades
        self.total_profit = 0
        self.total_loss = 0
        self.total_trade_duration = 0
        self.successful_trades = 0
        self.total_trades = 0
        self.total_trade_volume = 0
        self.buy_prices = []
        self.sell_prices = []


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
        

    def update_metrics_on_sell(self, ticker):
        self.metrics.last_sell_price_metric.labels(self.symbol).set(ticker)
        self.metrics.successful_sells_metric.labels(self.symbol).inc()
        self.metrics.sell_price_spread_metric.labels(self.symbol).set(max(self.metrics.sell_prices) - min(self.metrics.sell_prices) if self.metrics.sell_prices else 0)

def start_prometheus_server(port=8000):
    start_http_server(port)
