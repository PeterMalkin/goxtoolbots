# Candle sticks
import datetime
import time
from base import Indicator

# Indicator to represent a sum of values over a time window
# For example, the volume of all trades during a time period
class TimeSum(Indicator):
    
    Value = 0.0
    
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
            self._resetValue(0.0)
            self._is_closed = False
            return

        if (not self._checkData(data)):
            return

        _current_timestamp = datetime.datetime.fromtimestamp(data["now"])
        _value = data["value"]

        if (_current_timestamp >= self.CloseTime):
            self._is_closed = True
        
        if (_current_timestamp <= self.CloseTime and _current_timestamp >= self.OpenTime):
            self._updateData(_value)

    def _resetValue(self, value):
        self.Value = value
       
    # Update the running timestamps of the data    
    def _updateData(self, value):
        # Update the values in case the current datapoint is a current High/Low
        self.Value += value
