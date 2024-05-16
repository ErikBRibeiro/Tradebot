#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import logging
from binance import Client, exceptions
import pandas as pd
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configure o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Obtenha as chaves da API de variáveis de ambiente
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

if not api_key or not api_secret:
    logger.error("API Key ou API Secret não encontrada. Verifique o arquivo .env")
    exit(1)

client = Client(api_key, api_secret)

symbol = "BTCUSDT"
quantity = 0.0011  # A quantidade de BTC transacionada
interval = '1h'  # O intervalo de tempo das velas
setup = "9.1"  # Identificador do setup de trading

def calculate_percentage(current_price, target_price):
    return (target_price - current_price) / current_price * 100

def read_state():
    if os.path.exists('bot_state.txt'):
        with open('bot_state.txt', 'r') as file:
            state = file.read().strip()
        if state == 'comprado':
            return True, read_trade_history()
    return False, pd.DataFrame()

def save_state(comprado, transaction_history=None):
    with open('bot_state.txt', 'w') as file:
        file.write('comprado' if comprado else 'não comprado')
    if transaction_history is not None:
        transaction_history.to_csv('trade_history.csv', index=False)

def read_trade_history():
    if os.path.exists('trade_history.csv'):
        df = pd.read_csv('trade_history.csv')
        if not df.empty:
            return df
    return pd.DataFrame()

def update_trade_history(df, sell_price):
    df.at[df.index[-1], 'valor_venda'] = sell_price
    df.at[df.index[-1], 'outcome'] = calculate_percentage(df.loc[df.index[-1], 'valor_compra'], sell_price)
    df.to_csv('trade_history.csv', index=False)

def is_ema_declining(data):
    """
    Verifica se a EMA está em uma tendência de queda
    """
    ema9 = data['close'].ewm(span=9, adjust=False).mean()
    return ema9.iloc[-2] < ema9.iloc[-3]

while True:
    try:
        # Verifica o estado do bot
        comprado, trade_history = read_state()
        
        logger.info("Bot iniciado.")
        
        waiting_for_ema_decline = True
        
        while not comprado:
            klines = client.get_klines(symbol=symbol, interval=interval, limit=50)
            data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            data['close'] = data['close'].astype(float)
            data['low'] = data['low'].astype(float)
            data['high'] = data['high'].astype(float)
            
            previous_ema = data['close'].ewm(span=9, adjust=False).mean().iloc[-2]
            pre_previous_ema = data['close'].ewm(span=9, adjust=False).mean().iloc[-3]
            current_price = data['close'].iloc[-1]
            previous_high = data['high'].iloc[-2]
            
            logger.info("Loop de compra - Checando condições de compra.")

            if waiting_for_ema_decline:
                if is_ema_declining(data):
                    logger.info("EMA está em declínio, aguardando reversão.")
                    waiting_for_ema_decline = False
                else:
                    logger.info("Ainda aguardando declínio da EMA.")
            else:
                if previous_ema > pre_previous_ema and current_price >= previous_high:
                    order = client.order_market_buy(symbol=symbol, quantity=quantity)
                    stoploss = data['low'].iloc[-2]
                    stopgain = previous_high * 1.02
                    potential_loss = calculate_percentage(current_price, stoploss)
                    potential_gain = calculate_percentage(current_price, stopgain)
                    logger.info(f"Compramos - Potencial de perda: {potential_loss:.2f}%, Potencial de ganho: {potential_gain:.2f}%")
                    comprado = True
                    new_row = pd.DataFrame({
                        'horario': [datetime.now()],
                        'moeda': [symbol],
                        'valor_compra': [current_price],
                        'valor_venda': [None],
                        'quantidade_moeda': [quantity],
                        'max_referencia': [previous_high],
                        'min_referencia': [data['low'].iloc[-2]],
                        'stoploss': [stoploss],
                        'stopgain': [stopgain],
                        'potential_loss': [potential_loss],
                        'potential_gain': [potential_gain],
                        'timeframe': [interval],
                        'setup': [setup],
                        'outcome': [None]
                    })
                    trade_history = pd.concat([trade_history, new_row], ignore_index=True)
                    save_state(comprado, trade_history)
                else:
                    logger.info("Aguardando condições de compra ideais.")
            time.sleep(5)
        
        while comprado:
            logger.info("Loop de venda - Checando condições de venda.")
            ticker = float(client.get_symbol_ticker(symbol=symbol)['price'])
            
            if not trade_history.empty:
                stoploss = trade_history['stoploss'].iloc[-1]
                stopgain = trade_history['stopgain'].iloc[-1]
                
                if ticker <= stoploss:
                    order = client.order_market_sell(symbol=symbol, quantity=quantity)
                    comprado = False
                    logger.info("Fomos stopados :(")
                    update_trade_history(trade_history, ticker)
                    save_state(comprado, trade_history)
                    waiting_for_ema_decline = True  # Espera por um declínio da EMA antes da próxima compra
                elif ticker >= stopgain:
                    order = client.order_market_sell(symbol=symbol, quantity=quantity)
                    comprado = False
                    logger.info("Alcançamos o stopgain! Vendendo...")
                    update_trade_history(trade_history, ticker)
                    save_state(comprado, trade_history)
                    waiting_for_ema_decline = True  # Espera por um declínio da EMA antes da próxima compra
                else:
                    logger.info("Posição mantida")
                time.sleep(1)
            else:
                logger.info("Detalhes de transação não disponíveis. Aguarde a próxima oportunidade de compra.")
                time.sleep(5)

    except exceptions.BinanceAPIException as e:
        logger.error(f"Erro na API Binance: {e}")
        time.sleep(20)  # Espera antes de tentar novamente
    except exceptions.BinanceOrderException as e:
        logger.error(f"Erro ao criar ordem na Binance: {e}")
        time.sleep(20)  # Espera antes de tentar novamente
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        time.sleep(20)  # Espera antes de tentar novamente


# In[ ]:


trade_history


# In[ ]:




