from datetime import datetime

def calculate_gain_percentage(buy_price, target_price):
    return (target_price - buy_price) / buy_price * 100

def calculate_loss_percentage(buy_price, stop_loss):
    return (buy_price - stop_loss) / buy_price * 100

# verifica se o candle em questão está em um dia útil
def is_weekday(data):
    return datetime.fromtimestamp(data['open_time'] / 1000).weekday() < 5

# verifica se o candle em questão está em um dia útil menos sexta
def is_weekday_but_friday(data):
    return datetime.fromtimestamp(data['open_time'] / 1000).weekday() < 4