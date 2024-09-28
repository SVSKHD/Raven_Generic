import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
import time

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
            last_friday_utc.year, last_friday_utc.month, last_friday_utc.day, 21, 0, 0))

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

def calculate_pip_difference(symbol, price1, price2):
    # Calculate the pip difference between two prices for a given symbol
    # Determine the pip size based on the symbol
    if 'JPY' in symbol:
        pip_size = 0.01
    elif symbol in ['XAUUSD', 'XAGUSD']:  # Gold and Silver
        pip_size = 0.01  # Adjust according to your broker
    else:
        pip_size = 0.0001

    pip_difference = abs(price1 - price2) / pip_size
    return pip_difference

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
            # Convert the fetched time to IST
            fetched_time_ist = result['time'].astimezone(ist_timezone)
            time_str_ist = fetched_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z%z')

            start_prices[symbol] = {
                'start_price': result['start_price'],
                'pip_difference': sym['pip_difference']
            }
            print(f"Symbol: {symbol}, Date: {result['date']}, Time: {time_str_ist}, Start Price: {result['start_price']}")
        else:
            print(f"Could not get start price for {symbol}")

    # Now, fetch the latest prices and compare with start prices
    threshold_symbols = {}  # Symbols that have met the threshold
    while True:
        for sym in symbols:
            symbol = sym['symbol']
            if not select_symbol(symbol):
                continue
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                print(f"Failed to get tick for {symbol}")
                continue
            latest_price = tick.ask  # Or tick.bid, depending on your preference
            start_price_info = start_prices.get(symbol)
            if start_price_info is None:
                continue
            start_price = start_price_info['start_price']
            pip_diff_threshold = start_price_info['pip_difference']
            pip_difference = calculate_pip_difference(symbol, latest_price, start_price)
            if pip_difference >= pip_diff_threshold:
                if symbol not in threshold_symbols:
                    threshold_symbols[symbol] = {
                        'first_threshold_price': latest_price,
                        'first_threshold_time': datetime.now()
                    }
                    print(f"Symbol {symbol} has met the first threshold with a pip difference of {pip_difference:.1f}")
                else:
                    # Check for another threshold
                    first_threshold_price = threshold_symbols[symbol]['first_threshold_price']
                    additional_pip_difference = calculate_pip_difference(symbol, latest_price, first_threshold_price)
                    if additional_pip_difference >= pip_diff_threshold:
                        print(f"Symbol {symbol} has met the second threshold with an additional pip difference of {additional_pip_difference:.1f}")
                        # You can perform further actions here
            else:
                print(f"Symbol {symbol}: Pip difference is {pip_difference:.1f}, below threshold {pip_diff_threshold}")
        # Sleep for a certain interval before checking again
        time.sleep(60)  # Check every 60 seconds

    # Shutdown the MT5 connection (this will not be reached in an infinite loop)
    mt5.shutdown()

if __name__ == "__main__":
    main()
