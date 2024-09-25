# main.py
from datetime import datetime, timedelta
import time
import pytz
import MetaTrader5 as mt5
from utility import get_latest_price

# Initialize MetaTrader 5
if not mt5.initialize():
    print("MetaTrader 5 initialization failed.")
    quit()

# Define the symbols with pip thresholds
symbols = [
    {"symbol": 'EURUSD', "pip_difference": 15},
    {"symbol": 'GBPUSD', "pip_difference": 15},
    {"symbol": 'USDJPY', "pip_difference": 10},
    {"symbol": 'EURJPY', "pip_difference": 10},
    {"symbol": 'XAUUSD', "pip_difference": 15},
    {"symbol": 'XAGUSD', "pip_difference": 15}
]


def check_day_saturday_or_sunday():
    current_day = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%A')
    return current_day in ['Saturday', 'Sunday']


def calculate_pip_difference_int(symbol, start_price, current_price):
    price_difference = current_price - start_price
    direction = "up" if price_difference > 0 else "down"
    price_difference = abs(price_difference)

    if symbol in ['USDJPY', 'EURJPY']:
        pip_difference = int(price_difference * 100)
    elif symbol in ['XAUUSD', 'XAGUSD']:
        pip_difference = int(price_difference * 100)
    else:
        pip_difference = int(price_difference * 10000)

    return pip_difference, direction, symbol


def fetch_friday_end_price(symbol):
    """Fetch the last available price from Friday using a 5-minute timeframe."""
    end_time = datetime.now(pytz.timezone('EET'))  # MetaTrader 5 works in EET (Eastern European Time)
    friday = end_time - timedelta(days=(end_time.weekday() - 4) % 7)
    friday = friday.replace(hour=23, minute=55, second=0, microsecond=0)  # Closest 5-minute interval before 11:59 PM

    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, friday, 1)
    if rates is None or len(rates) == 0:
        raise ValueError(f"Could not fetch Friday's end price for {symbol}.")

    return rates[0]['close']  # Get the closing price from the last 5-minute interval on Friday


def set_start_prices():
    """Set the start prices for all symbols at 12 AM IST using MetaTrader 5."""
    print("Setting start prices from MetaTrader 5...")
    start_prices = {}
    current_day = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%A')

    for symbol_info in symbols:
        symbol = symbol_info['symbol']
        if current_day == 'Monday':
            start_prices[symbol] = fetch_friday_end_price(symbol)
            print(f"Start price for {symbol} set to last Friday's end price: {start_prices[symbol]}")
        else:
            bid, _ = get_latest_price(symbol)
            start_prices[symbol] = bid
            print(f"Start price for {symbol} set to current bid price: {start_prices[symbol]}")

    return start_prices


def main_execute():
    ist_timezone = pytz.timezone('Asia/Kolkata')

    while True:
        current_time = datetime.now(ist_timezone)
        if current_time.hour == 0 and current_time.minute == 0:
            break
        time.sleep(1)  # Sleep until 12 AM IST

    if check_day_saturday_or_sunday():
        print("Market is closed")
    else:
        start_prices = set_start_prices()

        # Example logic to use start prices
        for symbol_info in symbols:
            symbol = symbol_info['symbol']
            current_bid, _ = get_latest_price(symbol)

            pip_difference, direction, _ = calculate_pip_difference_int(symbol, start_prices[symbol], current_bid)
            print(f"Symbol: {symbol}, Pip Difference: {pip_difference}, Direction: {direction}")


# Execute the main function
try:
    main_execute()
finally:
    # Shutdown MetaTrader 5 connection
    mt5.shutdown()
