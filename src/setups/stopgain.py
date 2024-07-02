def compra(current_price, stopgain):
    if current_price <= stopgain:
        return True
    return False

def venda(current_price, stopgain):
    if current_price >= stopgain:
        return True
    return False