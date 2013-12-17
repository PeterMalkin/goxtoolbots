from ma import MovingAverage

# Indicator to represent a minimum value over a time window
# For example, the minimum price of all trades during a time period
class TimeMin(MovingAverage):

    def __init__(self, time_window):
        MovingAverage.__init__(self, time_window)
        self.Min = None

    def Update(self, d):

        if (not self._checkData(d)):
            return

        # force copy values to prevent storing a reference to the object outside self
        data = {"now":d["now"], "value":d["value"]}

        self._updateTimestamps(data)

        # Add the data point to the storage
        self._data.append(data)

        # Recalculate min
        if (self.Min == None):
            self.Min = d["value"]

        if (d["value"] < self.Min):
            self.Min = d["value"]

        if ( self._oldest_datapoint_timestamp < self._window_start_timestamp ):
            # Remove outdated datapoint from the storage
            oldest_value = self._data.pop(0)
            # if the oldest was the minimum, do a full linear search for min
            if (self.Min == oldest_value["value"]):
                minvalue = min(self._data, key=lambda x:x["value"])
                self.Min = minvalue["value"]

# Indicator to represent a maximum value over a time window
# For example, the maximum price of all trades during a time period
class TimeMax(MovingAverage):

    def __init__(self, time_window):
        MovingAverage.__init__(self, time_window)
        self.Max = None

    def Update(self, d):

        if (not self._checkData(d)):
            return

        # force copy values to prevent storing a reference to the object outside self
        data = {"now":d["now"], "value":d["value"]}

        self._updateTimestamps(data)

        # Add the data point to the storage
        self._data.append(data)

        # Recalculate max
        if (self.Max == None):
            self.Max = d["value"]

        if (d["value"] > self.Max):
            self.Max = d["value"]

        if ( self._oldest_datapoint_timestamp < self._window_start_timestamp ):
            # Remove outdated datapoint from the storage
            oldest_value = self._data.pop(0)
            # if the oldest was the maximum, do a full linear search for min
            if (self.Max == oldest_value["value"]):
                maxvalue = max(self._data, key=lambda x:x["value"])
                self.Max = maxvalue["value"]
