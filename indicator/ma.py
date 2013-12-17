# Moving averages indicators
import datetime
import time
from base import Indicator

# Base class for real indicators (SimpleMovingAverage, ExponentialMovingAverage)
class MovingAverage(Indicator):
    
    # The current value of moving average
    Value = 0.0

    # The window used to calculate the moving average
    TimeWindow = datetime.timedelta(hours=1)
    
    def __init__(self, time_window):
        if (isinstance(time_window, datetime.timedelta)):
            self.TimeWindow = abs(time_window)
        self._data = []
        self._current_timestamp = datetime.datetime.fromtimestamp(time.time())
        self._window_start_timestamp = datetime.datetime.fromtimestamp(time.time())
        self._oldest_datapoint_timestamp = datetime.datetime.fromtimestamp(time.time())
        self._isAccurate = False

    # TimeWindow of the actual data that indicator has received so far
    def ActualDataTimeWindow(self):
        if (len(self._data)<=1):
            return datetime.timedelta(0)
        oldest = datetime.datetime.fromtimestamp(self._data[0]["now"])
        newest = datetime.datetime.fromtimestamp(self._data[len(self._data)-1]["now"])
        result = newest - oldest
        return result

    # Returns true if the indicator has enough data to satisfy requested time window
    def IsAccurate(self):
        return self._isAccurate
        # return self.TimeWindow > self.ActualDataTimeWindow()

    # Update the running timestamps of the data    
    def _updateTimestamps(self, data):
        self._current_timestamp = datetime.datetime.fromtimestamp(data["now"])
        self._window_start_timestamp = self._current_timestamp - self.TimeWindow
        if (len(self._data)==0):
            self._oldest_datapoint_timestamp = self._current_timestamp
        else:
            self._oldest_datapoint_timestamp = datetime.datetime.fromtimestamp(self._data[0]["now"])
        if ( self.TimeWindow < self.ActualDataTimeWindow() ):
            self._isAccurate = True

# Moving average of a price over a period of time
class SimpleMovingAverage(MovingAverage):

    def Update(self, d):

        if (not self._checkData(d)):
            return

        # force copy values to prevent storing a reference to the object outside self
        data = {"now":d["now"], "value":d["value"]}

        self._updateTimestamps(data)

        if ( self._oldest_datapoint_timestamp < self._window_start_timestamp ):
            # Update current moving average, avoiding the loop over all datapoints
            self.Value = self.Value + ( data["value"] - self._data[0]["value"] ) / len(self._data) 
            # Remove outdated datapoint from the storage
            self._data.pop(0)
        else:
            # Not enough data accumulated. Compute cumulative moving average
            self.Value = self.Value + (data["value"] - self.Value) / ( len(self._data) + 1.0 )

        # Add the data point to the storage
        self._data.append(data)

# Moving average with exponential smoothing of a price over a period of time
class ExponentialMovingAverage(MovingAverage):

    def Update(self, d):

        if (not self._checkData(d)):
            return
        
        # force copy values to prevent storing a reference to the object outside self
        data = {"now":d["now"], "value":d["value"]}
       
        self._updateTimestamps(data)
        
        smoothing = 2.0 / (len(self._data) + 1.0)

        if ( self._oldest_datapoint_timestamp < self._window_start_timestamp ):
            # Update current exponential moving average, avoiding the loop over all datapoints
            self.Value = self.Value + smoothing * ( data["value"] - self.Value ) 
            # Remove outdated datapoint from the storage
            self._data.pop(0)
        else:
            # Not enough data accumulated. Compute cumulative moving average
            self.Value = self.Value + (data["value"] - self.Value) / ( len(self._data) + 1.0 )

        # Add the data point to the storage
        self._data.append(data)
    
# Moving average with exponential smoothing of a volume over a period of time
# If two values arrive on the same timestamp, they are added together
# Imagine to execute an order there was several trades, then the total volume 
# of the order would be split up into several volumes. 
class SimpleCummulativeMovingAverage(MovingAverage):

    def Update(self, d):

        if (not self._checkData(d)):
            return

        # force copy values to prevent storing a reference to the object outside self
        data = {"now":d["now"], "value":d["value"]}
        
        # if there is more values for the same point in time, add them up
        if (datetime.datetime.fromtimestamp(data["now"]) == self._current_timestamp):
            data["value"] += self._data.pop()["value"]
            self.Value = self._lastValue

        self._lastValue = self.Value

        self._updateTimestamps(data)

        if ( self._oldest_datapoint_timestamp < self._window_start_timestamp ):
            # Update current moving average, avoiding the loop over all datapoints
            self.Value = self.Value + ( data["value"] - self._data[0]["value"] ) / len(self._data) 
            # Remove outdated datapoint from the storage
            self._data.pop(0)
        else:
            # Not enough data accumulated. Compute cumulative moving average
            self.Value = self.Value + (data["value"] - self.Value) / ( len(self._data) + 1.0 )

        # Add the data point to the storage
        self._data.append(data)

# Moving average with exponential smoothing of a volume over a period of time
# If two values arrive on the same timestamp, they are added together
# Imagine to execute an order there was several trades, then the total volume 
# of the order would be split up into several volumes. 
class ExponentialCummulativeMovingAverage(MovingAverage):

    def Update(self, d):

        if (not self._checkData(d)):
            return
        
        # force copy values to prevent storing a reference to the object outside self
        data = {"now":d["now"], "value":d["value"]}
        
        # if there is more values for the same point in time, add them up
        if (datetime.datetime.fromtimestamp(data["now"]) == self._current_timestamp):
            data["value"] += self._data.pop()["value"]
            self.Value = self._lastValue

        self._lastValue = self.Value
       
        self._updateTimestamps(data)
        
        smoothing = 2.0 / (len(self._data) + 1.0)

        if ( self._oldest_datapoint_timestamp < self._window_start_timestamp ):
            # Update current exponential moving average, avoiding the loop over all datapoints
            self.Value = self.Value + smoothing * ( data["value"] - self.Value ) 
            # Remove outdated datapoint from the storage
            self._data.pop(0)
        else:
            # Not enough data accumulated. Compute cumulative moving average
            self.Value = self.Value + (data["value"] - self.Value) / ( len(self._data) + 1.0 )

        # Add the data point to the storage
        self._data.append(data)
