def calculate_pip_difference(symbol, start_price, current_price):
    # Calculate the raw price difference
    price_difference = abs(current_price - start_price)

    # Determine the pip value based on the symbol
    if symbol in ['USDJPY', 'EURJPY']:  # JPY pairs typically have 2 decimal places
        pip_value = price_difference * 100
    elif symbol in ['XAUUSD', 'XAGUSD']:  # Precious metals typically have 2 decimal places
        pip_value = price_difference * 100
    else:  # Major currency pairs like EURUSD typically have 4 decimal places
        pip_value = price_difference * 10000

    return round(pip_value, 2)


# Example usage
eurusd_pip_difference = calculate_pip_difference('EURUSD', 1.1200, 1.12452)
usdjpy_pip_difference = calculate_pip_difference('USDJPY', 110.00, 110.45)
xauusd_pip_difference = calculate_pip_difference('XAUUSD', 1920.50, 1920.95)

print(f"EURUSD pip difference: {eurusd_pip_difference} pips")
print(f"USDJPY pip difference: {usdjpy_pip_difference} pips")
print(f"XAUUSD pip difference: {xauusd_pip_difference} pips")
