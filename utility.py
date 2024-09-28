

# Your list of symbols with pip differences
symbols = [
    {"symbol": 'EURUSD', "pip_difference": 15},
    {"symbol": 'GBPUSD', "pip_difference": 15},
    {"symbol": 'USDJPY', "pip_difference": 10},
    {"symbol": 'EURJPY', "pip_difference": 10},
    {"symbol": 'XAUUSD', "pip_difference": 15},
    {"symbol": 'XAGUSD', "pip_difference": 15}
]


# Function to calculate pips
def calculate_pips(symbol, price_difference):
    # Define pip values for each symbol
    pip_values = {
        'EURUSD': 0.0001,
        'GBPUSD': 0.0001,
        'USDJPY': 0.01,
        'EURJPY': 0.01,
        'XAUUSD': 0.01,  # Gold
        'XAGUSD': 0.001  # Silver
    }

    # Check if the symbol is in the pip_values dictionary
    if symbol not in pip_values:
        raise ValueError(f"Symbol '{symbol}' not recognized.")

    # Get the pip value for the symbol
    pip_value = pip_values[symbol]

    # Calculate the number of pips
    pips = price_difference / pip_value

    # Return the number of pips without decimals
    return int(pips)


# Example usage:
# Calculate pips for EURUSD with a price difference of 0.0015
symbol = 'EURUSD'
price_diff = 0.0015
pips = calculate_pips(symbol, price_diff)
print(f"{symbol}: {pips} pips")  # Output: EURUSD: 15 pips

# Calculate pips for USDJPY with a price difference of 0.15
symbol = 'USDJPY'
price_diff = -0.15
pips = calculate_pips(symbol, price_diff)
print(f"{symbol}: {pips} pips")  # Output: USDJPY: 15 pips


get_latest_price("EURUSD")

