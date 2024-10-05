from utils import load_symbols, track_thresholds
from notifications import send_discord_message

# Load symbols from the JSON file (details.json)
symbols_data = load_symbols('./details.json')

# Define sample start prices and current prices for each symbol
sample_data = {
    'EURUSD': {
        'start_price': 1.1000,  # Example start price
        'current_prices': [1.1015, 1.1030, 1.1045, 1.1060, 1.1075]  # Simulated price movements
    },
    'GBPUSD': {
        'start_price': 1.3000,  # Example start price
        'current_prices': [1.3015, 1.3030, 1.3040, 1.3055, 1.3065]  # Simulated price movements
    },
    'USDJPY': {
        'start_price': 110.00,  # Example start price
        'current_prices': [110.05, 110.10, 110.12, 110.15, 110.18]  # Simulated price movements
    },
    'EURJPY': {
        'start_price': 130.00,  # Example start price
        'current_prices': [130.05, 130.10, 130.12, 130.20, 130.25]  # Simulated price movements
    },
    'XAUUSD': {
        'start_price': 1800.00,  # Example start price (Gold)
        'current_prices': [1810.00, 1820.00, 1835.00, 1845.00, 1850.00]  # Simulated price movements
    },
    'XAGUSD': {
        'start_price': 25.00,  # Example start price (Silver)
        'current_prices': [25.15, 25.30, 25.45, 25.55, 25.70]  # Simulated price movements
    }
}

# Track thresholds for each symbol
for symbol_data in symbols_data:
    symbol = symbol_data['symbol']
    start_price = sample_data[symbol]['start_price']
    current_prices = sample_data[symbol]['current_prices']
    pip_difference_target = symbol_data['pip_difference']  # Get the pip difference target from details.json

    thresholds = []  # List to store the thresholds

    print(f"\nTracking thresholds for {symbol}:\n")

    # Simulate tracking thresholds for each current price
    for current_price in current_prices:
        thresholds, current_pip_diff, pip_diff_from_previous, direction = track_thresholds(
            symbol=symbol,
            start_price=start_price,
            current_price=current_price,
            thresholds=thresholds,
            pip_difference_target=pip_difference_target
        )

        # Send a message to Discord with symbol, direction, and thresholds list
        message = (f"Symbol: {symbol}\n"
                   f"Direction: {direction}\n"
                   f"Thresholds so far: {thresholds}\n")
        print(message)
        send_discord_message(message)
