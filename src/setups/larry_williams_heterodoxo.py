# preferencial para tempos gráficos abaixo de 4h
def compra_ema_rompimento(previous_ema, pre_previous_ema, previous_high, current_price):
    if previous_ema > pre_previous_ema and previous_high < current_price:
        return True
    return False

# falta validação do funcionamento da função
def venda_ema_rompimento(previous_ema, pre_previous_ema, previous_low, current_price):
    if previous_ema < pre_previous_ema and previous_low > current_price:
        return True
    return False

# falta validação do funcionamento da função
# preferencial para tempos gráficos iguais ou acima de 4h
def compra_ema_violacao(previous_ema, previous_high, current_price):
    if previous_high > previous_ema and previous_high < current_price:
        return True
    return True

# falta validação do funcionamento da função
def venda_ema_violacao(previous_ema, previous_low, current_price):
    if previous_low < previous_ema and previous_low > current_price:
        return True
    return False

def compra_double_ema_rompimento():
    return False

def venda_double_ema_rompimento():
    return False

def compra_double_ema_violacao():
    return False

def venda_double_ema_violacao():
    return False

def compra_triple_ema_rompimento():
    return False

def venda_triple_ema_rompimento():
    return False

def compra_triple_ema_violação():
    return False

def venda_triple_ema_violação():
    return False