import json


# Function to load symbols from the JSON file
def load_symbols(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data['symbols']


# Function to calculate pip difference between two prices for a given symbol
def calculate_pip_difference(symbol, price1, price2):
    # Determine the pip size based on the symbol
    if 'JPY' in symbol:
        pip_size = 0.01
    elif symbol in ['XAUUSD', 'XAGUSD']:  # Gold and Silver
        pip_size = 0.1  # Adjust according to your broker
    elif symbol == 'BTCUSD':
        pip_size = 1  # Bitcoin usually has a pip size of 1
    else:
        pip_size = 0.0001

    # Calculate pip difference, retaining the sign for direction
    pip_difference = (price1 - price2) / pip_size
    return pip_difference


# Function to measure pips from start-price, record thresholds, and determine direction
def track_thresholds(symbol, start_price, current_price, thresholds, pip_difference_target):
    current_pip_diff = calculate_pip_difference(symbol, current_price, start_price)
    direction = "up" if current_pip_diff > 0 else "down"

    if (current_pip_diff >= pip_difference_target and direction == "up") or \
            (current_pip_diff <= -pip_difference_target and direction == "down"):
        thresholds.append(current_price)  # Record the threshold price

        # Calculate the pip difference from the previous threshold
        previous_threshold_price = thresholds[-2] if len(thresholds) > 1 else start_price
        pip_diff_from_previous_threshold = calculate_pip_difference(symbol, current_price, previous_threshold_price)

        previous_direction = "up" if pip_diff_from_previous_threshold > 0 else "down"

        print(
            f"Threshold reached for {symbol}: {current_price}, Pip difference from start: {current_pip_diff:.2f} pips ({direction})")
        print(
            f"Pip difference from previous threshold: {pip_diff_from_previous_threshold:.2f} pips ({previous_direction})")

        return thresholds, current_pip_diff, pip_diff_from_previous_threshold, direction

    return thresholds, current_pip_diff, None, direction
