# db_operations.py

from pymongo import MongoClient
import pytz
import pandas as pd
from notifications import send_discord_message  # Import your Discord messaging function

# MongoDB setup
MONGO_URI = 'mongodb+srv://hithesh:hithesh@utbiz.npdehas.mongodb.net/'
client = MongoClient(MONGO_URI)
db = client['pip_tracking_db']
ist = pytz.timezone('Asia/Kolkata')

# Function to save or update threshold data in MongoDB
async def save_or_update_threshold_in_mongo(symbol, start_price, current_price, previous_threshold, pips_from_start,
                                            direction, thresholds_list, timestamp, start_price_time):
    collection_name = "pip_check"
    pip_check_collection = db[collection_name]

    current_date_ist = timestamp.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')
    query = {"symbol": symbol, "date": current_date_ist.split()[0]}

    threshold_data = {
        "symbol": symbol,
        "start_price": start_price,
        "start_price_time": start_price_time.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S'),
        "initial_threshold_price": current_price,
        "previous_threshold": previous_threshold,
        "pips_from_start": pips_from_start,
        "direction": direction,
        "timestamp": timestamp.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S'),
        "trade_placed": {"status": "Pending", "trade_error": None}  # Initial status and error for trade
    }

    update_data = {
        "$set": threshold_data,
        "$addToSet": {"thresholds_list": {"$each": thresholds_list}}
    }

    result = pip_check_collection.update_one(query, update_data, upsert=True)

    if result.matched_count > 0:
        message = f"Updated existing document for {symbol} on {current_date_ist}. Data saved successfully."
    else:
        message = f"Inserted new document for {symbol} on {current_date_ist}. Data saved successfully."

    print(message)
    await send_discord_message(message)

# Function to check if data already exists in MongoDB
def check_data_exists_in_mongo(symbol, date):
    collection_name = "pip_check"
    pip_check_collection = db[collection_name]

    # Convert the date to a string
    date_str = date.strftime('%Y-%m-%d')

    # Query MongoDB for the existing document
    query = {"symbol": symbol, "date": date_str}
    return pip_check_collection.find_one(query)
