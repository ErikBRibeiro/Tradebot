import pandas as pd
from datetime import datetime
from utils import calculate_percentage, logger, update_trade_history
import time

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

    def sell_logic(self, current_price, trade_history, previous_low, previous_high, current_time):
        if not self.position_maintained:
            logger.info("Loop de venda - Checando condições de venda.")
            self.position_maintained = True

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
        mid_stoploss = previous_low

        if current_time - self.last_log_time >= 120:
            logger.info(f"Condições de venda - Stoploss: {stoploss}, Stopgain: {stopgain}, Mid Stoploss: {mid_stoploss}")

        if ticker <= stoploss or ticker >= stopgain or (ticker <= mid_stoploss and mid_stoploss > trade_history['valor_compra'].iloc[-1]):
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
                            logger.info(f"Venda realizada em {trade_duration:.2f} segundos. Preço: {ticker}, Stoploss: {stoploss}, Stopgain: {stopgain}, Mid Stoploss: {mid_stoploss}")
                        trade_history = update_trade_history(trade_history, ticker)  # Usa a função do utils.py
                        self.update_metrics_on_sell(ticker)
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

    def buy_logic(self, previous_ema, pre_previous_ema, current_price, previous_high, previous_low, trade_history, current_time):
        if not self.position_maintained:
            logger.info("Loop de compra - Checando condições de compra.")
            self.position_maintained = True

        if previous_ema > pre_previous_ema and current_price >= previous_high:
            logger.info("Condições de compra atendidas, tentando executar compra...")
            start_time = time.time()
            order = self.data_interface.create_order(self.symbol, 'buy', self.quantity)
            if order is not None:
                stoploss = previous_low
                stopgain = previous_high * 1.05
                mid_stoploss = previous_low
                potential_loss = calculate_percentage(current_price, stoploss)
                potential_gain = calculate_percentage(current_price, stopgain)
                logger.info(f"Compramos - Preço: {current_price}, Stoploss: {stoploss}, Stopgain: {stopgain}, Mid Stoploss: {mid_stoploss}")
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
                logger.info(f"Histórico de negociações atualizado com nova compra. Linhas: {len(trade_history)}")
                trade_history.to_csv('data/trade_history.csv', index=False)  # Salva no CSV apenas após uma compra
                self.metrics.buy_prices.append(current_price)
                self.update_metrics_on_buy(current_price, stoploss, stopgain, mid_stoploss, potential_loss, potential_gain)
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
