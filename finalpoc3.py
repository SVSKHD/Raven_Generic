import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
import time
from trade_management import place_trade, close_trades_by_symbol  # Import your trade management functions
from db import save_or_update_threshold_in_mongo, check_data_exists_in_mongo  # Import DB functions


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


def get_start_prices(symbols, broker_timezone, ist_timezone):
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
                'pip_difference': sym['pip_difference'],
                'close_trade_at': sym['close_trade_at'],
                'date': result['date'],
                'time': result['time']
            }
            print(
                f"Symbol: {symbol}, Date: {result['date']}, Time: {time_str_ist}, Start Price: {result['start_price']}")
        else:
            print(f"Could not get start price for {symbol}")
    return start_prices


def get_start_price_for_symbol(symbol, broker_timezone, ist_timezone):
    # Ensure the symbol is selected
    if not select_symbol(symbol):
        return None

    # Get current time in IST
    now_ist = datetime.now(ist_timezone)
    today_weekday = now_ist.weekday()  # Monday=0, ..., Sunday=6

    if today_weekday in [5, 6]:  # Saturday, Sunday
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
        # Today is Monday to Friday
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
        pip_size = 0.1  # Adjust according to your broker
    elif symbol == 'BTCUSD':
        pip_size = 1  # Bitcoin usually has a pip size of 1
    else:
        pip_size = 0.0001

    pip_difference = (price1 - price2) / pip_size  # Retain sign for direction
    return pip_difference


def main():
    # Initialize MT5
    if not initialize_mt5():
        return

    # Define time zones
    ist_timezone = pytz.timezone("Asia/Kolkata")  # IST timezone
    broker_timezone = pytz.timezone('Etc/GMT-3')  # Broker's server time zone (UTC+3)

    # Define symbols list with 'close_trade_at' key
    symbols = [
        {"symbol": 'EURUSD', "pip_difference": 15, "close_trade_at": 5},
        {"symbol": 'GBPUSD', "pip_difference": 15, "close_trade_at": 5},
        {"symbol": 'USDJPY', "pip_difference": 10, "close_trade_at": 5},
        {"symbol": 'EURJPY', "pip_difference": 10, "close_trade_at": 5},
        {"symbol": 'XAUUSD', "pip_difference": 150, "close_trade_at": 50},  # Adjusted for pip size
        {"symbol": 'XAGUSD', "pip_difference": 15, "close_trade_at": 5},
    ]

    # Initialize start prices
    start_prices = get_start_prices(symbols, broker_timezone, ist_timezone)

    threshold_symbols = {}  # Symbols that have met the first threshold
    last_update_date = None  # To track when start prices were last updated

    # Log initial start prices to MongoDB
    for symbol in start_prices:
        start_price_info = start_prices[symbol]
        start_price = start_price_info['start_price']
        start_price_time = start_price_info['time']
        timestamp = datetime.now()
        # Since we're at the beginning of the day, there are no thresholds crossed yet
        previous_threshold = None
        pips_from_start = 0
        direction = None
        thresholds_list = []
        # Call the function
        save_or_update_threshold_in_mongo(symbol, start_price, start_price, previous_threshold,
                                          pips_from_start, direction, thresholds_list, timestamp, start_price_time)

    while True:
        try:
            # Get current time in IST
            now_ist = datetime.now(ist_timezone)

            # Update start prices at 1 AM IST each day
            if now_ist.hour == 1 and (last_update_date != now_ist.date()):
                print("\nUpdating start prices at 1 AM IST...")
                start_prices = get_start_prices(symbols, broker_timezone, ist_timezone)
                threshold_symbols = {}  # Reset thresholds for new day
                last_update_date = now_ist.date()

                # Log updated start prices to MongoDB
                for symbol in start_prices:
                    start_price_info = start_prices[symbol]
                    start_price = start_price_info['start_price']
                    start_price_time = start_price_info['time']
                    timestamp = datetime.now()
                    previous_threshold = None
                    pips_from_start = 0
                    direction = None
                    thresholds_list = []
                    # Call the function
                    save_or_update_threshold_in_mongo(symbol, start_price, start_price, previous_threshold,
                                                      pips_from_start, direction, thresholds_list, timestamp,
                                                      start_price_time)

            for sym in symbols:
                symbol = sym['symbol']
                pip_diff_threshold = sym['pip_difference']
                close_trade_at = sym['close_trade_at']

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
                pip_difference = calculate_pip_difference(symbol, latest_price, start_price)
                direction = 'up' if pip_difference > 0 else 'down'

                # Absolute pip difference for threshold comparison
                abs_pip_difference = abs(pip_difference)

                if abs_pip_difference >= pip_diff_threshold:
                    if symbol not in threshold_symbols:
                        threshold_symbols[symbol] = {
                            'threshold_price': latest_price,
                            'threshold_time': datetime.now(),
                            'direction': direction,
                            'thresholds_list': [latest_price]
                        }
                        print(
                            f"Symbol {symbol} has moved {direction} by {abs_pip_difference:.1f} pips from the start price. Threshold price: {latest_price}")
                        # Place trade on first threshold
                        order_type = mt5.ORDER_TYPE_BUY if direction == 'up' else mt5.ORDER_TYPE_SELL
                        volume = 0.01  # Adjust volume as needed
                        if symbol == 'BTCUSD':
                            volume = 0.001  # Example smaller volume for BTCUSD
                        comment = f"Trade opened by script on {direction} movement"

                        trade_result = place_trade(symbol, order_type, volume, slippage=20)
                        print(trade_result)

                        # Log the threshold crossing
                        previous_threshold = start_price
                        pips_from_start = abs_pip_difference
                        thresholds_list = threshold_symbols[symbol]['thresholds_list']
                        timestamp = datetime.now()
                        start_price_time = start_price_info['time']
                        # Save to MongoDB
                        save_or_update_threshold_in_mongo(symbol, start_price, latest_price, previous_threshold,
                                                          pips_from_start, direction, thresholds_list, timestamp,
                                                          start_price_time)
                    else:
                        # Check for additional movement after first threshold
                        last_threshold_price = threshold_symbols[symbol]['threshold_price']
                        additional_pip_difference = calculate_pip_difference(symbol, latest_price, last_threshold_price)
                        abs_additional_pip_difference = abs(additional_pip_difference)
                        if abs_additional_pip_difference >= close_trade_at:
                            print(
                                f"Symbol {symbol} has moved an additional {abs_additional_pip_difference:.1f} pips {direction} from the threshold price. New threshold price: {latest_price}")
                            # Update the threshold price
                            threshold_symbols[symbol]['threshold_price'] = latest_price
                            threshold_symbols[symbol]['threshold_time'] = datetime.now()
                            threshold_symbols[symbol]['thresholds_list'].append(latest_price)
                            # Close all trades for this symbol after additional movement
                            close_trades_by_symbol(symbol)

                            # Log the threshold crossing
                            previous_threshold = last_threshold_price
                            pips_from_start = abs_pip_difference  # total pips from start price
                            thresholds_list = threshold_symbols[symbol]['thresholds_list']
                            timestamp = datetime.now()
                            start_price_time = start_price_info['time']
                            # Save to MongoDB
                            save_or_update_threshold_in_mongo(symbol, start_price, latest_price, previous_threshold,
                                                              pips_from_start, direction, thresholds_list, timestamp,
                                                              start_price_time)
                else:
                    print(
                        f"Symbol {symbol}: Price has moved {abs_pip_difference:.1f} pips {direction} from start price, below threshold {pip_diff_threshold}")
            # Sleep for a certain interval before checking again
            time.sleep(60)  # Check every 60 seconds
        except KeyboardInterrupt:
            print("Script terminated by user.")
            break

    # Shutdown the MT5 connection
    mt5.shutdown()


if __name__ == "__main__":
    main()
