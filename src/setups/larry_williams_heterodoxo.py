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
# vende quando fecha abaixo da ema, na abertura da próxima
def venda_ema_fechamento(previous_ema, previous_close):
    if previous_close < previous_ema:
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

# compra quando fecha acima da ema, na abertura da próxima
def compra_ema_fechamento():
    return False

def compra_double_ema_rompimento():
    return False

def venda_double_ema_rompimento():
    return False

def compra_double_ema_violacao():
    return False

def venda_double_ema_violacao():
    return False

# falta validação do funcionamento da função
def compra_triple_ema_rompimento(previous_ema1, previous_ema2, previous_ema3, previous_close, previous_high, current_price):
    if previous_close > previous_ema1 and previous_close > previous_ema2 and previous_close > previous_ema3 and current_price > previous_high:
        return True
    return False

def venda_triple_ema_rompimento():
    return False

def compra_triple_ema_violação():
    return False

def venda_triple_ema_violação():
    return False