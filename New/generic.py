import json


# Function to load symbols from the JSON file
def load_symbols():
    with open("./details.json", 'r') as file:
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



