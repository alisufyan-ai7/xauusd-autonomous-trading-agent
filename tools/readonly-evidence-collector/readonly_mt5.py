"""Capability-limited MetaTrader 5 adapter for Phase 0 evidence collection.

Only explicitly enumerated observation and calculation methods are exposed.
The terminal's external-Python trading protection is separately required by
collector.py before account or market evidence is read.
"""

from datetime import datetime

import MetaTrader5 as _mt5


class ReadOnlyMT5:
    """Narrow adapter with no order submission or state-changing operation."""

    @staticmethod
    def package_metadata():
        return {
            "author": _mt5.__author__,
            "version": _mt5.__version__,
        }

    @staticmethod
    def initialize():
        # No path, account, server, password, timeout, or portable-mode input.
        # This can only attach to the terminal session already opened by the operator.
        return _mt5.initialize()

    @staticmethod
    def shutdown():
        return _mt5.shutdown()

    @staticmethod
    def last_error():
        return _mt5.last_error()

    @staticmethod
    def version():
        return _mt5.version()

    @staticmethod
    def terminal_info():
        return _mt5.terminal_info()

    @staticmethod
    def account_info():
        return _mt5.account_info()

    @staticmethod
    def symbols_get():
        return _mt5.symbols_get()

    @staticmethod
    def symbol_info(symbol):
        return _mt5.symbol_info(symbol)

    @staticmethod
    def symbol_info_tick(symbol):
        return _mt5.symbol_info_tick(symbol)

    @staticmethod
    def copy_rates_from_pos(symbol, timeframe_name, start_pos, count):
        timeframes = {
            "M1": _mt5.TIMEFRAME_M1,
            "M5": _mt5.TIMEFRAME_M5,
            "M15": _mt5.TIMEFRAME_M15,
            "H1": _mt5.TIMEFRAME_H1,
            "H4": _mt5.TIMEFRAME_H4,
            "D1": _mt5.TIMEFRAME_D1,
        }
        return _mt5.copy_rates_from_pos(
            symbol, timeframes[timeframe_name], start_pos, count
        )

    @staticmethod
    def copy_ticks_from(symbol, from_utc, count):
        if not isinstance(from_utc, datetime) or from_utc.tzinfo is None:
            raise ValueError("from_utc must be a timezone-aware datetime")
        return _mt5.copy_ticks_from(symbol, from_utc, count, _mt5.COPY_TICKS_ALL)

    @staticmethod
    def orders_get():
        return _mt5.orders_get()

    @staticmethod
    def positions_get():
        return _mt5.positions_get()

    @staticmethod
    def history_orders_get(from_utc, to_utc):
        return _mt5.history_orders_get(from_utc, to_utc)

    @staticmethod
    def history_deals_get(from_utc, to_utc):
        return _mt5.history_deals_get(from_utc, to_utc)

    @staticmethod
    def order_calc_profit(direction, symbol, volume, price_open, price_close):
        order_type = {
            "BUY": _mt5.ORDER_TYPE_BUY,
            "SELL": _mt5.ORDER_TYPE_SELL,
        }[direction]
        return _mt5.order_calc_profit(
            order_type, symbol, volume, price_open, price_close
        )

    @staticmethod
    def order_calc_margin(direction, symbol, volume, price_open):
        order_type = {
            "BUY": _mt5.ORDER_TYPE_BUY,
            "SELL": _mt5.ORDER_TYPE_SELL,
        }[direction]
        return _mt5.order_calc_margin(order_type, symbol, volume, price_open)

