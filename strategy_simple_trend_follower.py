import sys
import goxapi
import time
import datetime
from strategy_core_simple_trend_follower import SimpleTrendFollowerStrategyCore
from exchange_connection import ExchangeConnection

class Strategy(goxapi.BaseObject):
    # pylint: disable=C0111,W0613,R0201

    def __init__(self, gox):
        goxapi.BaseObject.__init__(self)
        self.signal_debug.connect(gox.signal_debug)
        gox.signal_keypress.connect(self.slot_keypress)
        gox.signal_strategy_unload.connect(self.slot_before_unload)
        gox.signal_trade.connect(self.slot_trade)
        self.gox = gox
        self.name = "%s.%s" % \
            (self.__class__.__module__, self.__class__.__name__)

        self.exchangeConnection = ExchangeConnection(self.gox)
        self.score = SimpleTrendFollowerStrategyCore(self.exchangeConnection)
        self.score.Load()

        self.debug("%s loaded" % self.name)

    def __del__(self):
        self.debug("%s unloaded" % self.name)

    def slot_before_unload(self, _sender, _data):
        self.debug("%s before_unload" % self.name)
        self.score.Save()

    def slot_keypress(self, gox, (key)):

        # sell all BTC as market order
        if ( key == ord('s') ):
            self.score.ConvertAllToUSD()

        # spend all USD to buy BTC as market order
        if ( key == ord('b') ):
            self.score.ConvertAllToBTC()

        #dump the state of score
        if ( key == ord('d') ):
            self.score.Save()

        # immediately cancel all orders
        if ( key == ord('c') ):
            for order in gox.orderbook.owns:
                gox.cancel(order.oid)

    def slot_trade(self, gox, (date, price, volume, typ, own)):
        # a trade message has been received

        # update price indicators
        data = {"now": float(time.time()), "value": gox.quote2float(price) }
        self.score.UpdatePrice(data)

        # Trigger the trading logic
        self.score.Act()
