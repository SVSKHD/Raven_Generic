# import random
#
# # Initialize symbols and their respective start prices
# symbols = [{symbol:'xauusd', pip_difference:0.0015}, {'xagusd', 'gbpusd', 'eurusd']
# start_prices = [1800.0, 25.00, 1.3000, 1.1000]  # Different start prices for each symbol
#
#
# # Function to calculate pips for different start prices and current prices
# def calculate_pips(symbols, start_prices, current_prices):
#     pip_values = []
#
#     for symbol, start_price, current_price in zip(symbols, start_prices, current_prices):
#         symbol = symbol.lower()
#
#         # Calculate the price change from the start price to the current price
#         price_change = abs(current_price - start_price)
#
#         # Determine pip value based on the symbol
#         if symbol.endswith("jpy"):
#             pip = price_change / 0.01
#         elif symbol == "xauusd":  # Gold
#             pip = price_change / 0.10
#         elif symbol == "xagusd":  # Silver
#             pip = price_change / 0.01
#         else:
#             pip = price_change / 0.0001
#
#         pip_values.append({"symbol": symbol.upper(), "pip_difference": pip, "start_price": start_price,
#                            "current_price": current_price})
#
#     return pip_values
#
#
# # Function to generate random prices and check for 15 pip movements
# def simulate_price_changes(symbols, start_prices, threshold_pip=15):
#     reached_threshold = []
#     iterations = 0  # To prevent infinite loops in testing
#
#     while len(reached_threshold) < len(
#             symbols) and iterations < 1000:  # Run until all reach the threshold or hit 1000 iterations
#         iterations += 1
#
#         # Generate random current prices
#         current_prices = [round(start + random.uniform(-0.05, 0.05), 4) if symbol != 'xauusd' and symbol != 'xagusd'
#                           else round(start + random.uniform(-1, 1), 2) for start, symbol in zip(start_prices, symbols)]
#
#         # Calculate pip differences
#         pip_values = calculate_pips(symbols, start_prices, current_prices)
#
#         # Check for those that reached or exceeded 15 pips and haven't been reported
#         for pip_info in pip_values:
#             if pip_info["pip_difference"] >= threshold_pip and pip_info["symbol"] not in [r["symbol"] for r in
#                                                                                           reached_threshold]:
#                 reached_threshold.append(pip_info)
#                 print(
#                     f"Threshold reached for {pip_info['symbol']}: Start Price = {pip_info['start_price']}, Current Price = {pip_info['current_price']}, Pip Difference = {pip_info['pip_difference']}")
#
#
# simulate_price_changes(symbols, start_prices, threshold_pip=15)
#
