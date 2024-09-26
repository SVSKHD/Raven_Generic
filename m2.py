# main_script.py

import datetime
import pandas as pd
import MetaTrader5 as mt5
import schedule
import time
import asyncio
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
            pip_difference = round(pip_movement * 100, 1)
        elif self.symbol == 'XAUUSD':
            pip_difference = round(pip_movement * 100, 2)
        elif self.symbol == 'XAGUSD':
            pip_difference = round(pip_movement * 1000, 3)
        else:
            pip_difference = round(pip_movement * 10000, 1)

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

            timestamp = pd.Timestamp.now()
            asyncio.run(save_or_update_threshold_in_mongo(
                self.symbol, self.start_price, current_price, self.start_price, pip_difference, direction,
                self.thresholds, timestamp, timestamp
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


def refresh_start_prices():
    if not mt5.initialize():
        print("MetaTrader 5 initialization failed")
        return

    ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    current_time = datetime.datetime.now(ist_timezone)
    date_str = current_time.strftime('%Y-%m-%d 12:00 AM')

    for symbol_info in symbols:
        symbol = symbol_info["symbol"]
        tick = mt5.symbol_info_tick(symbol)

        if tick:
            start_price = tick.bid
            symbol_info["start_price"] = start_price
            symbol_info["last_updated"] = date_str
            symbol_info["pip_tracker"] = PipTracker(symbol, start_price, symbol_info["pip_difference"])
            print(f"Updated {symbol}: Start Price = {start_price} at {date_str}")
        else:
            print(f"Failed to get price for {symbol}")

    print_updated_prices()
    mt5.shutdown()


def monitor_pip_movements():
    if not mt5.initialize():
        print("MetaTrader 5 initialization failed")
        return

    for symbol_info in symbols:
        symbol = symbol_info["symbol"]
        tick = mt5.symbol_info_tick(symbol) #this is not tick we need to fetch the

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
    monitor_pip_movements()
    time.sleep(300)
    schedule.run_pending()
