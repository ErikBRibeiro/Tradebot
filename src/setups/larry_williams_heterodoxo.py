# preferencial para tempos gráficos abaixo de 4h
def compra_ema9_rompimento(previous_ema, pre_previous_ema, previous_high, current_price):
    if previous_ema > pre_previous_ema and previous_high < current_price:
        return True
    return False

# falta validação do funcionamento da função
# preferencial para tempos gráficos iguais ou acima de 4h
def compra_ema9_violacao(previous_ema, previous_high, current_price):
    if previous_high > previous_ema and previous_high < current_price:
        return True
    return True

def compra_ema9_ema21_rompimento():
    return True

def compra_ema9_ema21_violacao():
    return True

def compra_ema9_ema80_rompimento():
    return True

def compra_ema9_ema80_violacao():
    return True

# falta validação do funcionamento da função
def venda_ema9_rompimento(previous_ema, pre_previous_ema, previous_low, current_price):
    if previous_ema < pre_previous_ema and previous_low > current_price:
        return True
    return False

# falta validação do funcionamento da função
def venda_ema9_violacao(previous_ema, previous_low, current_price):
    if previous_low < previous_ema and previous_low > current_price:
        return True
    return False

def venda_ema9_ema21_rompimento():
    return True

def venda_ema9_ema21_violacao():
    return True

def venda_ema9_ema80_rompimento():
    return True

def venda_ema9_ema80_violacao():
    return True