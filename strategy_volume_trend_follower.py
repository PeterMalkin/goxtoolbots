import sys
import goxapi
import time
import datetime
from strategy_logic_volume_trend_follower import StrategyLogicVolumeTrendFollower
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
        self.strategy_logic = StrategyLogicVolumeTrendFollower(self.exchangeConnection)
        self.strategy_logic.Load()

        self.debug("%s loaded" % self.name)

    def __del__(self):
        self.debug("%s unloaded" % self.name)

    def slot_before_unload(self, _sender, _data):
        self.debug("%s before_unload" % self.name)
        self.strategy_logic.Save()

    def slot_keypress(self, gox, (key)):

        # sell all BTC as market order
        if ( key == ord('s') ):
            self.strategy_logic.ConvertAllToUSD()

        # spend all USD to buy BTC as market order
        if ( key == ord('b') ):
            self.strategy_logic.ConvertAllToBTC()

        #dump the state of strategy_logic
        if ( key == ord('d') ):
            self.strategy_logic.Save()

        # immediately cancel all orders
        if ( key == ord('c') ):
            for order in gox.orderbook.owns:
                gox.cancel(order.oid)

    def slot_trade(self, gox, (date, price, volume, typ, own)):
        # a trade message has been received

        # update the volume indicators
        data = {"now": float(time.time()), "value": gox.base2float(volume) }
        self.strategy_logic.UpdateVolume(data)

        # update price indicators
        data = {"now": float(time.time()), "value": gox.quote2float(price) }
        self.strategy_logic.UpdatePrice(data)

        # Trigger the trading logic
        self.strategy_logic.Act()
