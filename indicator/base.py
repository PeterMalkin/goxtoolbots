class Updatable:
    def Update(self, data):
        pass

class Runnable:
    def Run(self):
        pass
    def Stop(self):
        pass

class Indicator(Updatable):

    def _checkData(self, data):
        if (data==None):
            return False

        if (len(data)==0):
            return False

        if ("now" not in data):
            return False

        if ("value" not in data):
            return False
        
        if ( (not isinstance(data["value"], float)) and (not isinstance(data["value"], int)) ):
            return False
        
        if ( (not isinstance(data["now"], float)) and (not isinstance(data["now"], int)) ):
            return False

        return True
