"""Minimum read-only adapter for exposure counts; no mutation APIs."""

import MetaTrader5 as _mt5


class ReadOnlyExposureMT5:
    initialize = staticmethod(_mt5.initialize)
    shutdown = staticmethod(_mt5.shutdown)
    last_error = staticmethod(_mt5.last_error)
    terminal_info = staticmethod(_mt5.terminal_info)
    positions_get = staticmethod(_mt5.positions_get)
    orders_get = staticmethod(_mt5.orders_get)
