# fechar uma venda com stopgain
def buy_stopgain(current_price, stopgain):
    if current_price <= stopgain:
        return True
    return False

# fechar uma compra com stopgain
def sell_stopgain(current_price, stopgain):
    if current_price >= stopgain:
        return True
    return False

# define preço de fechamento em stopgain para uma operação de venda
def set_buy_stopgain_ratio(buy_price, stoploss, gain_ratio):
    return buy_price - (stoploss - buy_price) * gain_ratio

# define preço de fechamento em stopgain para uma operação de compra
def set_sell_stopgain_ratio(buy_price, stoploss, gain_ratio):
    return buy_price + (buy_price - stoploss) * gain_ratio

# define preço de fechamento em stopgain para uma operação de venda
def set_buy_stopgain_percentage(buy_price, gain_percentage):
    return buy_price - buy_price * gain_percentage / 100

# define preço de fechamento em stopgain para uma compra aberta
def set_sell_stopgain_percentage(buy_price, gain_percentage):
    return buy_price + buy_price * gain_percentage / 100