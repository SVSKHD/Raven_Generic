import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz

# Initialize the MT5 platform
if not mt5.initialize():
    print("initialize() failed")
    mt5.shutdown()
    quit()

# Select the symbol
symbol = "GBPUSD"
if not mt5.symbol_select(symbol, True):
    print(f"Failed to select {symbol}")
    mt5.shutdown()
    quit()

# Define time zones
ist_timezone = pytz.timezone("Asia/Kolkata")    # IST timezone
broker_timezone = pytz.timezone("Europe/Athens")  # EEST/EET timezone

# Number of days to fetch
num_days = 10

# List to store start prices
start_prices = []

# Get current time in IST
now_ist = datetime.now(ist_timezone)

# Loop over the last 'num_days' days
for day_offset in range(num_days):
    # Calculate the date for each day
    day_ist = now_ist - timedelta(days=day_offset)

    # Set time to 1 AM IST
    one_am_ist = ist_timezone.localize(datetime(day_ist.year, day_ist.month, day_ist.day, 1, 0, 0))

    # Convert 1 AM IST to broker's server time
    one_am_broker = one_am_ist.astimezone(broker_timezone)

    # Fetch the price at 1 AM IST (converted to broker time)
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, one_am_broker, 1)

    if rates is None or len(rates) == 0:
        print(f"No data for {one_am_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
    else:
        # Get the open price at 1 AM IST
        start_price = rates[0]['open']
        date_str = one_am_ist.strftime('%Y-%m-%d')
        print(f"Date: {date_str}, Start Price at 1 AM IST: {start_price}")
        start_prices.append({'date': date_str, 'start_price': start_price})

# Shutdown the MT5 connection
mt5.shutdown()

# Optionally, print all collected start prices
print("\nCollected Start Prices at 1 AM IST:")
for item in start_prices:
    print(f"Date: {item['date']}, Start Price: {item['start_price']}")
