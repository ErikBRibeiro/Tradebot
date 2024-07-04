# fechar uma venda com stoploss
def compra(current_price, stoploss):
    if current_price > stoploss:
        return True
    return False

# fechar uma compra com stoploss
def venda(current_price, stoploss):
    if current_price < stoploss:
        return True
    return False

# define o preço de fechamento em stoploss para uma operação de venda
def set_compra_max_candles(data, candles=2):
    return max(data['high'].tail(candles).tolist())

# define o preço de fechamento em stoploss para uma operação de compra
def set_venda_min_candles(data, candles=2):
    return min(data['low'].tail(candles).tolist())