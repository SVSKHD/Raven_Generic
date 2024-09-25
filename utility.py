import MetaTrader5 as mt5


def get_latest_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise ValueError(
            f"Failed to get the latest price for {symbol}. Ensure the symbol is correct and the market is open.")
    return tick.bid, tick.ask
