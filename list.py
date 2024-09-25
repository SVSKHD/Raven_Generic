# main.py
from datetime import datetime, timedelta
import time
import pytz
import MetaTrader5 as mt5
from utility import get_latest_price
from notifications import send_discord_message

TIMEFRAME = mt5.TIMEFRAME_M5

# IST Timezone
ist = pytz.timezone('Asia/Kolkata')

symbols = [
    {"symbol": 'EURUSD', "pip_difference": 15},
    {"symbol": 'GBPUSD', "pip_difference": 15},
    {"symbol": 'USDJPY', "pip_difference": 10},
    {"symbol": 'EURJPY', "pip_difference": 10},
    {"symbol": 'XAUUSD', "pip_difference": 15},
    {"symbol": 'XAGUSD', "pip_difference": 15}
]

# Initialize MetaTrader 5
def initialize_mt5():
    # Initialize MT5 platform
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return False

    # Define login credentials
    login = 213171528  # Login from the image
    password = "AHe@Yps3"  # Password from the image
    server = "OctaFX-Demo"  # Server from the image

    # Perform the login
    authorized = mt5.login(login=login, password=password, server=server)

    if authorized:
        print("Logged in successfully")
        send_discord_message("Logged in successfully")
    else:
        print(f"Login failed, error code: {mt5.last_error()}")
        mt5.shutdown()

    return authorized

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

def get_historical_price(symbol, date):
    # Convert the date to 12:00 AM IST or 12:30 AM IST
    ist = pytz.timezone('Asia/Kolkata')
    target_time_12am = ist.localize(datetime(date.year, date.month, date.day, 0, 0, 0)).astimezone(pytz.utc)
    target_time_1230am = ist.localize(datetime(date.year, date.month, date.day, 0, 30, 0)).astimezone(pytz.utc)

    # Attempt to fetch historical price at 12:00 AM IST
    rates_12am = mt5.copy_rates_range(symbol, TIMEFRAME, target_time_12am, target_time_12am + timedelta(minutes=1))
    if rates_12am is not None and len(rates_12am) > 0:
        return rates_12am[0]['close']  # Return the close price at 12:00 AM

    # If no data at 12:00 AM, try to fetch at 12:30 AM IST
    rates_1230am = mt5.copy_rates_range(symbol, TIMEFRAME, target_time_1230am, target_time_1230am + timedelta(minutes=1))
    if rates_1230am is not None and len(rates_1230am) > 0:
        return rates_1230am[0]['close']  # Return the close price at 12:30 AM

    # If both attempts fail, raise an error
    raise ValueError(f"Could not fetch historical price for {symbol} at 12:00 AM or 12:30 AM IST.")

def set_start_prices():
    """Set the start prices for all symbols at 12 AM IST using MetaTrader 5."""
    print("Waiting until 12 AM IST to set start prices...")
    send_discord_message("Waiting until 12 AM IST to set start prices...")

    # Wait until 12 AM IST
    ist_timezone = pytz.timezone('Asia/Kolkata')
    while True:
        current_time = datetime.now(ist_timezone)
        if current_time.hour == 0 and current_time.minute == 0:
            print("It's 12 AM IST. Fetching start prices from MetaTrader 5...")
            send_discord_message("It's 12 AM IST. Fetching start prices from MetaTrader 5...")
            break
        time.sleep(1)  # Check every second until it's 12 AM IST

    start_prices = {}
    current_day = current_time.strftime('%A')

    for symbol_info in symbols:
        symbol = symbol_info['symbol']
        if current_day == 'Monday':
            try:
                start_prices[symbol] = fetch_friday_end_price(symbol)
                print(f"Start price for {symbol} set to last Friday's end price: {start_prices[symbol]}")
                send_discord_message(f"Start price for {symbol} set to last Friday's end price: {start_prices[symbol]}")
            except ValueError as e:
                print(e)
                send_discord_message(str(e))
        else:
            try:
                start_prices[symbol] = get_historical_price(symbol, current_time)
                print(f"Start price for {symbol} set to historical price: {start_prices[symbol]}")
                send_discord_message(f"Start price for {symbol} set to historical price: {start_prices[symbol]}")
            except ValueError as e:
                print(f"Failed to fetch historical price for {symbol}: {e}")
                send_discord_message(f"Failed to fetch historical price for {symbol}: {e}")

    return start_prices

def main_execute():
    start_prices = set_start_prices()
    print(start_prices)

# Execute the main function
if __name__ == "__main__":
    try:
        if initialize_mt5():
            main_execute()
    finally:
        # Ensure MetaTrader 5 connection is shutdown properly
        mt5.shutdown()
