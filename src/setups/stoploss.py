def compra(current_price, stoploss):
    if current_price > stoploss:
        return True
    return False

def venda(current_price, stoploss):
    if current_price < stoploss:
        return True
    return False