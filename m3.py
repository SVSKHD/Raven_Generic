import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta, time as dt_time

# Initialize MT5
if not mt5.initialize():
    print("Failed to initialize MT5")
    mt5.shutdown()
    quit()
else:
    print("MT5 initialized")

symbols = [
    {"symbol": 'EURUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'GBPUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'USDJPY', "pip_difference": 10, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'EURJPY', "pip_difference": 10, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'XAUUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'XAGUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None}
]

def get_start_price(symbol, timeframe=mt5.TIMEFRAME_M5):
    """
    Fetches the price of the given symbol at 12:00 AM IST of the current day,
    adjusted for the broker's EEST timezone.
    """
    # Timezones
    ist_timezone = pytz.timezone('Asia/Kolkata')  # IST
    eest_timezone = pytz.timezone('Europe/Helsinki')  # EEST/EET with DST handling

    # Get 12:00 AM IST today
    today_ist = datetime.now(ist_timezone).date()
    midnight_ist = datetime.combine(today_ist, dt_time(1, 0, 0, tzinfo=ist_timezone))

    # Convert 12:00 AM IST to EEST/EET (broker's timezone)
    midnight_broker = midnight_ist.astimezone(eest_timezone)

    # Convert to UTC for MT5
    midnight_utc = midnight_broker.astimezone(pytz.utc)

    # Fetch the bar at 12:00 AM IST adjusted to broker's timezone
    rates = mt5.copy_rates_from(symbol, timeframe, midnight_utc, 1)
    if rates is None or len(rates) == 0:
        print(f"Failed to get start price for {symbol} at 12:00 AM IST.")
        return None

    start_price = rates[0]['open']

    # Print detailed information for verification
    print(f"Fetched start price for {symbol} at:")
    print(f" - {midnight_ist.strftime('%Y-%m-%d %H:%M:%S %Z')} (IST)")
    print(f" - {midnight_broker.strftime('%Y-%m-%d %H:%M:%S %Z')} (Broker's Time)")
    print(f" - {midnight_utc.strftime('%Y-%m-%d %H:%M:%S %Z')} (UTC)")
    print(f"Start price: {start_price}")

    return start_price

def get_current_price(symbol):
    """
    Fetches the current price (tick) for the given symbol.
    """
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Failed to get current price for {symbol}.")
        return None
    return tick.last

def update_symbols(symbols_list):
    """
    Updates each symbol in the list with the start price and current price.
    """
    for symbol_dict in symbols_list:
        symbol = symbol_dict['symbol']

        # Ensure the symbol is available in Market Watch
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select symbol {symbol}")
            continue

        # Get start price at 12:00 AM IST
        start_price = get_start_price(symbol)
        if start_price is not None:
            symbol_dict['start_price'] = start_price
            symbol_dict['last_updated'] = datetime.now()
            print(f"{symbol} start price at 12:00 AM IST: {start_price}")
        else:
            print(f"Could not update start price for {symbol}")

        # Get current price
        current_price = get_current_price(symbol)
        if current_price is not None:
            symbol_dict['pip_tracker'] = current_price
            print(f"{symbol} current price: {current_price}")
        else:
            print(f"Could not update current price for {symbol}")

# Update the symbols with start price and current price
update_symbols(symbols)

# Print the updated symbols list
for symbol_dict in symbols:
    print(symbol_dict)

# Shutdown MT5 after operations
mt5.shutdown()
