def compra(current_price, previous_high):
    if current_price > previous_high:
        return True
    return False

def venda(current_price, previous_low):
    if current_price < previous_low:
        return True
    return False