"""Minimal read-only MT5 adapter for the Gate 0 VPS/session diagnostic."""

import MetaTrader5 as _mt5


class ReadOnlyMT5:
    @staticmethod
    def initialize():
        # Attach only; credentials, terminal path and account switching are impossible here.
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
    def symbol_info(symbol):
        return _mt5.symbol_info(symbol)

    @staticmethod
    def symbol_info_tick(symbol):
        return _mt5.symbol_info_tick(symbol)

