import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
import time
import json

# Import functions from other modules
from price_fetch import get_last_available_price, get_start_price_for_symbol, get_start_prices
from notifications import send_discord_message
from utils import calculate_pip_difference
from trade_managment import place_trade, close_trades_by_symbol  # Use close_trades_by_symbol here

# Load details from details.json
with open('./details.json') as f:
    config = json.load(f)

symbols = config['symbols']
ist_timezone = pytz.timezone(config['timezone'])
broker_timezone = pytz.timezone('Etc/GMT-3')  # Replace with correct broker timezone if needed
timeframe = mt5.TIMEFRAME_M5

# Dictionary to track symbols that have hit thresholds
threshold_symbols = {}

def send_threshold_update(symbol, start_price, latest_price, direction):
    """
    Sends an update to Discord when a threshold is hit, including the thresholds list.
    """
    message = (
        f"Symbol: {symbol} hit threshold.\n"
        f"Start Price: {start_price}\n"
        f"Latest Price (Threshold Hit): {latest_price}\n"
        f"Direction: {direction.capitalize()}\n"
        "Current Threshold List:\n"
    )
    # Iterate over the threshold_symbols dictionary and add the threshold details
    for sym, data in threshold_symbols.items():
        message += (
            f"  - Symbol: {sym}, "
            f"Start Price: {data['threshold_price']}, "
            f"Direction: {data['direction']}, "
            f"Threshold Time: {data['threshold_time']}\n"
        )

    # Send the message to Discord
    send_discord_message(message)

def main():
    # Initialize MT5
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return

    try:
        # Fetch start prices
        start_prices = get_start_prices(symbols, broker_timezone, ist_timezone)

        # Track symbols and their pip movements
        threshold_symbols = {}  # To store symbols that hit thresholds

        while True:
            now_ist = datetime.now(ist_timezone)

            for sym in symbols:
                symbol = sym['symbol']
                pip_diff_threshold = sym['pip_difference']
                close_trade_pips = sym['close_trade_at']

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
                pip_difference = calculate_pip_difference(symbol, latest_price, start_price)
                direction = 'up' if pip_difference > 0 else 'down'

                # Handle up/down movements separately
                if direction == 'up' and pip_difference >= pip_diff_threshold:
                    if symbol not in threshold_symbols:
                        threshold_symbols[symbol] = {
                            'threshold_price': latest_price,
                            'threshold_time': now_ist,
                            'direction': direction
                        }
                        # Send the threshold update including the list
                        send_threshold_update(symbol, start_price, latest_price, direction)

                        # Place BUY trade
                        order_type = mt5.ORDER_TYPE_BUY
                        volume = 0.01  # Adjust as per your needs
                        trade_result = place_trade(symbol, order_type, volume, price=0, slippage=20)
                        send_discord_message(f"Placed BUY trade for {symbol}. Comment: {trade_result}")

                    else:
                        last_threshold_price = threshold_symbols[symbol]['threshold_price']
                        additional_pip_difference = calculate_pip_difference(symbol, latest_price, last_threshold_price)

                        if additional_pip_difference >= close_trade_pips:
                            # Close trades after additional upward pip movement
                            send_discord_message(f"{symbol} moved up an additional {additional_pip_difference:.1f} pips. Closing trades.")
                            close_trades_by_symbol(symbol)  # Use close_trades_by_symbol
                            send_discord_message(f"Closed trades for {symbol}. Start price was {start_price}.")
                            # Remove symbol from threshold tracking
                            del threshold_symbols[symbol]

                elif direction == 'down' and pip_difference <= -pip_diff_threshold:
                    if symbol not in threshold_symbols:
                        threshold_symbols[symbol] = {
                            'threshold_price': latest_price,
                            'threshold_time': now_ist,
                            'direction': direction
                        }
                        # Send the threshold update including the list
                        send_threshold_update(symbol, start_price, latest_price, direction)

                        # Place SELL trade
                        order_type = mt5.ORDER_TYPE_SELL
                        volume = 0.01  # Adjust as per your needs
                        trade_result = place_trade(symbol, order_type, volume, price=0, slippage=20)
                        send_discord_message(f"Placed SELL trade for {symbol}. Comment: {trade_result}")

                    else:
                        last_threshold_price = threshold_symbols[symbol]['threshold_price']
                        additional_pip_difference = calculate_pip_difference(symbol, latest_price, last_threshold_price)

                        if additional_pip_difference <= -close_trade_pips:
                            # Close trades after additional downward pip movement
                            send_discord_message(f"{symbol} moved down an additional {abs(additional_pip_difference):.1f} pips. Closing trades.")
                            close_trades_by_symbol(symbol)  # Use close_trades_by_symbol
                            send_discord_message(f"Closed trades for {symbol}. Start price was {start_price}.")
                            # Remove symbol from threshold tracking
                            del threshold_symbols[symbol]

                else:
                    print(f"Symbol {symbol}: Moved {pip_difference:.1f} pips {direction}, below threshold.")

            # Sleep for the next cycle
            time.sleep(60)

    except KeyboardInterrupt:
        print("Terminated by user.")

    finally:
        # Shutdown MT5
        mt5.shutdown()

if __name__ == "__main__":
    main()
