"""Read-only MT5 adapter for XAUUSD boundary observations."""

import MetaTrader5 as _mt5


class ReadOnlyMT5:
    initialize=staticmethod(_mt5.initialize)
    shutdown=staticmethod(_mt5.shutdown)
    last_error=staticmethod(_mt5.last_error)
    terminal_info=staticmethod(_mt5.terminal_info)
    account_info=staticmethod(_mt5.account_info)
    symbol_info=staticmethod(_mt5.symbol_info)
    symbol_info_tick=staticmethod(_mt5.symbol_info_tick)

