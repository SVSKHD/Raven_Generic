def check_pip_difference(symbol, start_price, current_price):
    direction = None
    difference = current_price - start_price

    if difference > 0:
        direction = "up"
    elif difference < 0:
        direction = "down"
    else:
        direction = "neutral"  # In case the prices are the same
    print(symbol, direction, abs(difference))
    return symbol, direction, abs(difference)

check_pip_difference('EURUSD', 1.1114, 1.12332)