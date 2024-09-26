# main_script.py

import datetime
import pandas as pd
import MetaTrader5 as mt5
import schedule
import time
import pytz
import asyncio
from datetime import timedelta
from db import save_or_update_threshold_in_mongo, check_data_exists_in_mongo  # Import DB functions

# Universal JSON structure for symbols
symbols = [
    {"symbol": 'EURUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'GBPUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'USDJPY', "pip_difference": 10, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'EURJPY', "pip_difference": 10, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'XAUUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None},
    {"symbol": 'XAGUSD', "pip_difference": 15, "start_price": None, "last_updated": None, "pip_tracker": None}
]


class PipTracker:
    def __init__(self, symbol, start_price, pip_difference_threshold):
        self.symbol = symbol
        self.start_price = start_price
        self.pip_difference_threshold = pip_difference_threshold
        self.thresholds = []  # List to store all thresholds reached
        self.current_price = start_price
        self.trade_placed = {"status": None, "trade_error": None}

    def calculate_pip_difference(self, current_price):
        pip_movement = current_price - self.start_price

        # Calculate the actual pip difference based on the instrument type
        if self.symbol in ['USDJPY', 'EURJPY']:
            pip_difference = round(pip_movement * 100, 1)  # JPY pairs
        elif self.symbol == 'XAUUSD':  # Gold
            pip_difference = round(pip_movement * 100, 2)
        elif self.symbol == 'XAGUSD':  # Silver
            pip_difference = round(pip_movement * 1000, 3)
        else:
            pip_difference = round(pip_movement * 10000, 1)  # Standard forex pairs

        direction = "up" if pip_movement > 0 else "down" if pip_movement < 0 else "neutral"

        threshold_reached = False
        if abs(pip_difference) >= self.pip_difference_threshold:
            threshold_reached = True
            self.thresholds.append({
                "current_price": current_price,
                "pip_difference": pip_difference,
                "direction": direction,
                "time_reached": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            self.start_price = current_price

            # Ensure the timestamp is timezone-aware
            timestamp = pd.Timestamp.now(tz=pytz.utc)
            start_price_time = pd.Timestamp(self.start_price).tz_localize(pytz.utc)

            asyncio.run(save_or_update_threshold_in_mongo(
                self.symbol, self.start_price, current_price, self.start_price, pip_difference, direction,
                self.thresholds, timestamp, start_price_time
            ))

        self.current_price = current_price

        return {
            "symbol": self.symbol,
            "start_price": self.start_price,
            "current_price": current_price,
            "pip_difference": pip_difference,
            "direction": direction,
            "threshold_reached": threshold_reached,
            "all_thresholds": self.thresholds,
            "trade_placed": self.trade_placed
        }


def get_price_at_12am(symbol):
    # Define IST timezone
    ist = pytz.timezone('Asia/Kolkata')

    # Get current date and set the target 12:00 AM IST time
    current_date = datetime.datetime.now(ist)
    target_time_12am_ist = ist.localize(
        datetime.datetime(current_date.year, current_date.month, current_date.day, 0, 0, 0))

    # Convert 12:00 AM IST to UTC
    target_time_12am_utc = target_time_12am_ist.astimezone(pytz.utc)

    # Fetch tick data from MT5 for 12:00 AM IST converted to UTC
    ticks_12am = mt5.copy_ticks_range(symbol, target_time_12am_utc, target_time_12am_utc + timedelta(minutes=5),
                                      mt5.COPY_TICKS_ALL)

    if ticks_12am is not None and len(ticks_12am) > 0:
        print(f"Tick data at 12:00 AM IST for {symbol}: {ticks_12am[0]['bid']}")
        return ticks_12am[0]['bid']

    # If no data found for 12:00 AM, fallback to fetch data at 12:30 AM IST
    target_time_1230am_ist = ist.localize(
        datetime.datetime(current_date.year, current_date.month, current_date.day, 0, 30, 0))
    target_time_1230am_utc = target_time_1230am_ist.astimezone(pytz.utc)

    ticks_1230am = mt5.copy_ticks_range(symbol, target_time_1230am_utc, target_time_1230am_utc + timedelta(minutes=5),
                                        mt5.COPY_TICKS_ALL)

    if ticks_1230am is not None and len(ticks_1230am) > 0:
        print(f"Tick data at 12:30 AM IST for {symbol}: {ticks_1230am[0]['bid']}")
        return ticks_1230am[0]['bid']

    raise ValueError(f"Could not fetch tick data for {symbol} at 12:00 AM or 12:30 AM IST.")


def refresh_start_prices():
    if not mt5.initialize():
        print("MetaTrader 5 initialization failed")
        return

    for symbol_info in symbols:
        symbol = symbol_info["symbol"]
        try:
            start_price = get_price_at_12am(symbol)  # Fetch the price using the tick data at 12 AM
            symbol_info["start_price"] = start_price
            symbol_info["last_updated"] = "12:00 AM"
            symbol_info["pip_tracker"] = PipTracker(symbol, start_price, symbol_info["pip_difference"])
            print(f"Updated {symbol}: Start Price = {start_price} at 12:00 AM IST")
        except ValueError as e:
            print(e)

    mt5.shutdown()


def monitor_pip_movements():
    if not mt5.initialize():
        print("MetaTrader 5 initialization failed")
        return

    for symbol_info in symbols:
        symbol = symbol_info["symbol"]
        tick = mt5.symbol_info_tick(symbol)

        if tick and symbol_info["pip_tracker"]:
            current_price = tick.bid
            result = symbol_info["pip_tracker"].calculate_pip_difference(current_price)
            print(result)

    mt5.shutdown()


def print_updated_prices():
    print("\nUpdated Start Prices at 12 AM:")
    for symbol_info in symbols:
        print(
            f"{symbol_info['symbol']} - Start Price: {symbol_info['start_price']} Last Updated: {symbol_info['last_updated']}")


def display_thresholds():
    print("\nThresholds Reached for Each Symbol:")
    for symbol_info in symbols:
        tracker = symbol_info["pip_tracker"]
        if tracker:
            print(f"\nSymbol: {symbol_info['symbol']}")
            for threshold in tracker.thresholds:
                print(threshold)
        else:
            print(f"{symbol_info['symbol']} - No thresholds reached or tracker not initialized yet.")


schedule.every().day.at("00:00").do(refresh_start_prices)
refresh_start_prices()

while True:
    try:
        monitor_pip_movements()
        time.sleep(300)  # Sleep for 5 minutes to monitor pip movements
        schedule.run_pending()
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        time.sleep(60)  # Wait for 1 minute before retrying in case of an error
