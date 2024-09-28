from pymongo import MongoClient
import pytz
import pandas as pd
from notifications import send_discord_message  # Make sure this function is correctly set up

# MongoDB setup
MONGO_URI = 'mongodb+srv://hithesh:hithesh@utbiz.npdehas.mongodb.net/'
client = MongoClient(MONGO_URI)
db = client['pip_tracking_db']
ist = pytz.timezone('Asia/Kolkata')


# Function to save or update threshold data in MongoDB
def save_or_update_threshold_in_mongo(symbol, start_price, current_price, previous_threshold, pips_from_start,
                                      direction, thresholds_list, timestamp, start_price_time):
    collection_name = "pip_check2"
    pip_check_collection = db[collection_name]

    # Ensure the timestamp and start_price_time are timezone-aware
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=pytz.utc)  # Localize to UTC if not already localized
    if start_price_time.tzinfo is None:
        start_price_time = start_price_time.replace(tzinfo=pytz.utc)  # Localize to UTC if not already localized

    # Convert to IST for display and storage purposes
    current_date_ist = timestamp.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')
    start_price_time_ist = start_price_time.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')

    # Create the query and data structure for upserting
    query = {"symbol": symbol, "date": current_date_ist.split()[0]}

    threshold_data = {
        "symbol": symbol,
        "start_price": start_price,
        "start_price_time": start_price_time_ist,
        "initial_threshold_price": current_price,
        "previous_threshold": previous_threshold,
        "pips_from_start": pips_from_start,
        "direction": direction,
        "timestamp": current_date_ist,
        "trade_placed": {"status": "Pending", "trade_error": None}  # Initial status and error for trade
    }

    update_data = {
        "$set": threshold_data,
        "$addToSet": {"thresholds_list": {"$each": thresholds_list}}
    }

    try:
        # Attempt to update or insert the document
        result = pip_check_collection.update_one(query, update_data, upsert=True)

        if result.matched_count > 0:
            message = f"Updated existing document for {symbol} on {current_date_ist}. Data saved successfully."
        else:
            message = f"Inserted new document for {symbol} on {current_date_ist}. Data saved successfully."

        print(message)
        send_discord_message(message)

    except Exception as e:
        error_message = f"Failed to save/update document for {symbol} on {current_date_ist}: {str(e)}"
        print(error_message)
        send_discord_message(error_message)



# Function to check if data already exists in MongoDB
def check_data_exists_in_mongo(symbol, date):
    collection_name = "pip_check"
    pip_check_collection = db[collection_name]

    # Ensure the date is in string format 'YYYY-MM-DD'
    date_str = date.strftime('%Y-%m-%d')

    # Query MongoDB for the existing document
    query = {"symbol": symbol, "date": date_str}

    try:
        return pip_check_collection.find_one(query)
    except Exception as e:
        print(f"Error while checking data existence for {symbol} on {date_str}: {str(e)}")
        return None
