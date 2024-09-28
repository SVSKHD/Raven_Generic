import MetaTrader5 as mt5
from notifications import send_discord_message
import os
import time  # We'll use this for sleep

bot = True

def initialize_mt5():
    # Initialize MT5 platform
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return False

    # Define login credentials
    login = 213171528  # Your login ID
    password = "AHe@Yps3"  # Your password
    server = "OctaFX-Demo"  # Your server name

    if not login or not password or not server:
        print("Login credentials are not set.")
        mt5.shutdown()
        return False

    # Perform the login
    authorized = mt5.login(login=int(login), password=password, server=server)

    if authorized:
        print("Logged in successfully")
        send_discord_message("Logged in successfully")
    else:
        print(f"Login failed, error code: {mt5.last_error()}")
        mt5.shutdown()
        return False

    return True

def get_latest_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Failed to get tick for {symbol}")
        return None
    else:
        print(f"Tick for {symbol}: {tick.ask}")
        return tick

symbols = [
    {"symbol": 'EURUSD', "pip_difference": 15},
    {"symbol": 'GBPUSD', "pip_difference": 15},
    {"symbol": 'USDJPY', "pip_difference": 10},
    {"symbol": 'EURJPY', "pip_difference": 10},
    {"symbol": 'XAUUSD', "pip_difference": 15},
    {"symbol": 'XAGUSD', "pip_difference": 15}
]

def main():
    global bot  # Declare bot as global to modify it inside the function

    # Initialize MT5
    initialized = initialize_mt5()
    if not initialized:
        print("Failed to initialize MT5")
        return

    try:
        while bot:
            for symbol in symbols:
                get_latest_price(symbol['symbol'])
            # Sleep for a while before fetching prices again
            time.sleep(5)  # Fetch prices every 5 seconds (adjust as needed)

    except KeyboardInterrupt:
        # This block is executed when you press Ctrl+C
        print("\nBot stopped by user.")
        bot = False
        print("bot", bot)

    finally:
        # Perform cleanup actions here
        mt5.shutdown()
        print("MetaTrader 5 connection closed.")

if __name__ == "__main__":
    main()
