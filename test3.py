import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz

def initialize_mt5():
    # Initialize the MT5 platform
    if not mt5.initialize():
        print("initialize() failed")
        return False
    return True

def select_symbol(symbol):
    # Select the symbol
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select {symbol}")
        return False
    return True

def get_last_available_price(symbol, desired_time_broker, broker_timezone, price_type='close'):
    """
    Fetches the last available price at or before the desired time.
    """
    max_attempts = 120  # Increased attempts to cover possible delays
    attempts = 0
    while attempts < max_attempts:
        rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, desired_time_broker, 1)
        if rates is not None and len(rates) > 0:
            price = rates[0][price_type]
            rate_time = datetime.fromtimestamp(rates[0]['time'], pytz.utc)
            return price, rate_time
        else:
            # Decrement time by 1 minute
            desired_time_broker -= timedelta(minutes=1)
            attempts += 1
    return None, None

def get_start_price_for_symbol(symbol, broker_timezone, ist_timezone):
    # Ensure the symbol is selected
    if not select_symbol(symbol):
        return None

    # Get current time in IST
    now_ist = datetime.now(ist_timezone)
    today_weekday = now_ist.weekday()  # Monday=0, ..., Sunday=6

    if today_weekday in [5, 6, 0]:  # Saturday, Sunday, Monday
        # Need to get Friday's closing price
        days_since_friday = (today_weekday - 4) % 7
        last_friday_ist = now_ist - timedelta(days=days_since_friday)

        # Convert last Friday's date from IST to UTC
        last_friday_utc = last_friday_ist.astimezone(pytz.utc)

        # Market closes at 21:00 UTC on Friday
        friday_close_utc = pytz.utc.localize(datetime(
            last_friday_utc.year, last_friday_utc.month, last_friday_utc.day, 23, 0, 0))

        # Convert to broker's server time
        friday_close_broker = friday_close_utc.astimezone(broker_timezone)

        # Fetch last available price before market close
        closing_price, actual_time = get_last_available_price(
            symbol, friday_close_broker, broker_timezone, price_type='close')

        if closing_price is not None:
            friday_date = last_friday_ist.strftime('%Y-%m-%d')
            return {
                'symbol': symbol,
                'date': friday_date,
                'start_price': closing_price,
                'time': actual_time
            }
        else:
            print(f"Could not get Friday's closing price for {symbol}")
            return None

    else:
        # Today is Tuesday to Friday
        # Need to get today's 1 AM IST price

        # Set time to 1 AM IST today
        one_am_ist = ist_timezone.localize(datetime(
            now_ist.year, now_ist.month, now_ist.day, 1, 0, 0))

        # Convert to broker's server time
        one_am_broker = one_am_ist.astimezone(broker_timezone)

        # Fetch the price at 1 AM IST (converted to broker time)
        start_price, actual_time = get_last_available_price(
            symbol, one_am_broker, broker_timezone, price_type='open')

        if start_price is not None:
            date_str = one_am_ist.strftime('%Y-%m-%d')
            return {
                'symbol': symbol,
                'date': date_str,
                'start_price': start_price,
                'time': actual_time
            }
        else:
            print(f"No data available for {one_am_ist.strftime('%Y-%m-%d %H:%M:%S')} IST for {symbol}")
            return None

def main():
    # Initialize MT5
    if not initialize_mt5():
        return

    # Define time zones
    ist_timezone = pytz.timezone("Asia/Kolkata")     # IST timezone
    broker_timezone = pytz.timezone('Etc/GMT-3')     # Broker's server time zone (UTC+3)

    # Define symbols list
    symbols = [
        {"symbol": 'EURUSD', "pip_difference": 15},
        {"symbol": 'GBPUSD', "pip_difference": 15},
        {"symbol": 'USDJPY', "pip_difference": 10},
        {"symbol": 'EURJPY', "pip_difference": 10},
        {"symbol": 'XAUUSD', "pip_difference": 15},
        {"symbol": 'XAGUSD', "pip_difference": 15}
    ]

    start_prices = {}

    for sym in symbols:
        symbol = sym['symbol']
        result = get_start_price_for_symbol(symbol, broker_timezone, ist_timezone)
        if result:
            start_prices[symbol] = result['start_price']
            print(f"Symbol: {symbol}, Date: {result['date']}, Start Price: {result['start_price']}")
        else:
            print(f"Could not get start price for {symbol}")

    # Shutdown the MT5 connection
    mt5.shutdown()

    # Optionally, print all collected start prices
    print("\nCollected Start Prices:")
    for symbol, start_price in start_prices.items():
        print(f"Symbol: {symbol}, Start Price: {start_price}")

if __name__ == "__main__":
    main()
