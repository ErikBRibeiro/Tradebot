def calculate_gain_percentage(buy_price, target_price):
    return (target_price - buy_price) / buy_price * 100

def calculate_loss_percentage(buy_price, stop_loss):
    return (buy_price - stop_loss) / buy_price * 100