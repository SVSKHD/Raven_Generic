# main.py
import MetaTrader5 as mt5
from datetime import datetime
import pytz
import time
import json

# Import functions from other modules
from price_fetch import get_start_prices
from utils import calculate_pip_difference
from trade_managment import place_trade, close_trades_by_symbol
from notifications import send_discord_message
from db import save_or_update_threshold_in_mongo, save_threshold_symbols_to_db, load_threshold_symbols_from_db  # DB functions

# Load details from details.json
with open('./details.json') as f:
    config = json.load(f)

symbols = config['symbols']
ist_timezone = pytz.timezone(config['timezone'])
broker_timezone = pytz.timezone('Etc/GMT-3')  # Replace with correct broker timezone if needed
timeframe = mt5.TIMEFRAME_M5

# Load the previous threshold symbols state from MongoDB to avoid placing trades again on script restart
threshold_symbols = load_threshold_symbols_from_db()

def main():
    # Initialize MT5
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return

    try:
        # Fetch start prices
        start_prices = get_start_prices(symbols, broker_timezone, ist_timezone)

        # Format and log start prices with time for debugging
        message = ""
        for symbol, data in start_prices.items():
            start_price = data['start_price']
            time_fetched = data['time']  # Assuming 'time' is part of the returned data
            # Convert the start time to IST and log it
            time_fetched_ist = time_fetched.astimezone(ist_timezone)
            message += f"Symbol: {symbol}, Start Price: {start_price}, Time (IST): {time_fetched_ist}\n"

        # Send the start prices message to Discord
        send_discord_message(message)

        while True:
            now_ist = datetime.now(ist_timezone)

            for sym in symbols:
                symbol = sym['symbol']
                pip_diff_threshold = sym['pip_difference']
                close_trade_pips = sym['close_trade_at']
                close_opposite_pips = sym['close_trade_at_opposite_direction']  # New key for opposite direction

                if not mt5.symbol_select(symbol, True):
                    print(f"Failed to select {symbol}")
                    continue

                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    print(f"Failed to get tick for {symbol}")
                    continue

                latest_price = tick.ask
                start_price_info = start_prices.get(symbol)

                if start_price_info is None:
                    continue

                start_price = start_price_info['start_price']
                start_time = start_price_info['time']  # When the start price was recorded
                start_time_ist = start_time.astimezone(ist_timezone)  # Convert to IST

                pip_difference = calculate_pip_difference(symbol, latest_price, start_price)
                direction = 'up' if pip_difference > 0 else 'down'

                # Check if the symbol is already in the threshold_symbols, to prevent duplicate trades
                if symbol in threshold_symbols:
                    print(f"Trade already placed for {symbol}, skipping...")
                    continue  # Skip trade placement if it's already tracked in threshold_symbols

                if direction == 'up' and pip_difference >= pip_diff_threshold:
                    threshold_symbols[symbol] = {
                        'threshold_price': latest_price,
                        'threshold_time': now_ist,
                        'direction': direction,
                        'trade_type': 'buy'
                    }

                    # Save threshold data to MongoDB with start price and time
                    save_or_update_threshold_in_mongo(symbol, start_price, latest_price, start_price,
                                                      pip_difference, direction, [], now_ist, start_time)

                    # Place BUY trade
                    order_type = mt5.ORDER_TYPE_BUY
                    volume = 0.01  # Adjust as per your needs
                    trade_result = place_trade(symbol, order_type, volume, price=0, slippage=20)

                    # Record the trade placement price and time (IST)
                    trade_time_ist = datetime.now(ist_timezone)
                    send_discord_message(
                        f"Placed BUY trade for {symbol} at {latest_price} (IST: {trade_time_ist}). "
                        f"Start Price: {start_price} (IST: {start_time_ist}), Comment: {trade_result}"
                    )

                    # Save the updated threshold_symbols to MongoDB to persist the trade state
                    save_threshold_symbols_to_db(threshold_symbols)

                elif direction == 'down' and pip_difference <= -pip_diff_threshold:
                    threshold_symbols[symbol] = {
                        'threshold_price': latest_price,
                        'threshold_time': now_ist,
                        'direction': direction,
                        'trade_type': 'sell'
                    }

                    # Save threshold data to MongoDB with start price and time
                    save_or_update_threshold_in_mongo(symbol, start_price, latest_price, start_price,
                                                      pip_difference, direction, [], now_ist, start_time)

                    # Place SELL trade
                    order_type = mt5.ORDER_TYPE_SELL
                    volume = 0.01  # Adjust as per your needs
                    trade_result = place_trade(symbol, order_type, volume, price=0, slippage=20)

                    # Record the trade placement price and time (IST)
                    trade_time_ist = datetime.now(ist_timezone)
                    send_discord_message(
                        f"Placed SELL trade for {symbol} at {latest_price} (IST: {trade_time_ist}). "
                        f"Start Price: {start_price} (IST: {start_time_ist}), Comment: {trade_result}"
                    )

                    # Save the updated threshold_symbols to MongoDB to persist the trade state
                    save_threshold_symbols_to_db(threshold_symbols)

                # Close trades if the price moves in the opposite direction
                elif symbol in threshold_symbols:
                    last_threshold_price = threshold_symbols[symbol]['threshold_price']
                    additional_pip_difference = calculate_pip_difference(symbol, latest_price, last_threshold_price)

                    # Close BUY trade if the price continues to move up
                    if threshold_symbols[symbol]['trade_type'] == 'buy' and additional_pip_difference >= close_trade_pips:
                        send_discord_message(f"{symbol} moved up an additional {additional_pip_difference:.1f} pips. Closing BUY trades.")
                        close_trades_by_symbol(symbol)
                        send_discord_message(f"Closed BUY trades for {symbol}. Start price was {start_price}.")
                        del threshold_symbols[symbol]

                    # Close SELL trade only if the price continues to move down
                    elif threshold_symbols[symbol]['trade_type'] == 'sell' and additional_pip_difference <= -close_trade_pips:
                        send_discord_message(f"{symbol} moved down an additional {additional_pip_difference:.1f} pips. Closing SELL trades.")
                        close_trades_by_symbol(symbol)
                        send_discord_message(f"Closed SELL trades for {symbol}. Start price was {start_price}.")
                        del threshold_symbols[symbol]

                    # **New Logic: Close trades if the price moves in the opposite direction**
                    # For a BUY trade, close if price moves down by 'close_trade_at_opposite_direction' pips
                    elif threshold_symbols[symbol]['trade_type'] == 'buy' and additional_pip_difference <= -close_opposite_pips:
                        send_discord_message(f"{symbol} moved down {additional_pip_difference:.1f} pips in the opposite direction. Closing BUY trades.")
                        close_trades_by_symbol(symbol)
                        send_discord_message(f"Closed BUY trades for {symbol} due to opposite direction movement.")

                    # For a SELL trade, close if price moves up by 'close_trade_at_opposite_direction' pips
                    elif threshold_symbols[symbol]['trade_type'] == 'sell' and additional_pip_difference >= close_opposite_pips:
                        send_discord_message(f"{symbol} moved up {additional_pip_difference:.1f} pips in the opposite direction. Closing SELL trades.")
                        close_trades_by_symbol(symbol)
                        send_discord_message(f"Closed SELL trades for {symbol} due to opposite direction movement.")

                else:
                    print(f"Symbol {symbol}: Moved {pip_difference:.1f} pips {direction}, below threshold.")

            # Sleep for the next cycle
            time.sleep(1)

    except KeyboardInterrupt:
        print("Terminated by user.")

    finally:
        # Shutdown MT5
        mt5.shutdown()

if __name__ == "__main__":
    main()
