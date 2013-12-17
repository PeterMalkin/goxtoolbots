# Candle sticks
import datetime
import time
from base import Indicator

# Base class for real indicators (SimpleMovingAverage, ExponentialMovingAverage)
class CandleStick(Indicator):
    
    # Opening price
    Open = 0.0
    
    # Closing price
    Close = 0.0
    
    # Highest price
    High = 0.0
    
    # Lowest price
    Low = 0.0
    
    # Open timestamp
    OpenTime = datetime.datetime.fromtimestamp(time.time());

    # Close timestamp
    CloseTime = OpenTime;

    def __init__(self, openTime, closeTime):
        if (isinstance(openTime, datetime.datetime)):
            self.OpenTime = openTime
        if (isinstance(closeTime, datetime.datetime)):
            self.CloseTime = closeTime
        
        self._is_closed = False

    # Returns true if candle stick accumulated enough data to represent the 
    # time span between Opening and Closing timestamps
    def IsAccurate(self):
        return self._is_closed
            
    def Update(self, data):

        if ( self.CloseTime < self.OpenTime ):
            self._resetPrice(0.0)
            self._is_closed = False
            return

        if (not self._checkData(data)):
            return

        _current_timestamp = datetime.datetime.fromtimestamp(data["now"])
        _price = data["value"]

        if (_current_timestamp >= self.CloseTime):
            self._is_closed = True
        
        if (_current_timestamp <= self.CloseTime and _current_timestamp >= self.OpenTime):
            self._updateData(_price)

    def _resetPrice(self, price):
        self.High = price
        self.Low = price
        self.Open = price
        self.Close = price
       
    # Update the running timestamps of the data    
    def _updateData(self, price):
        # If this is the first datapoint, initialize the values
        if ( self.High == 0.0 and self.Low == 0.0 and self.Open == 0.0 and self.Close == 0.0):
            self._resetPrice(price)
            self._is_closed = False
            return
        
        # Update the values in case the current datapoint is a current High/Low
        self.Close = price
        self.High = max(price,self.High)
        self.Low = min(price,self.Low)
