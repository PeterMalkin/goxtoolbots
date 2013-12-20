import datetime
import time
import pickle
import sqlite3
import calendar
import math
from indicator.ma import ExponentialMovingAverage as ema
from exchange_connection import ExchangeConnection, MockExchangeConnection

"""
	Simple mean reversion bot. It relies on three moving averages.
	It believes that if faster moving averages are significantly
	larger slow moving ones, that there will be a reversal movement
	in the market, and price will drop. Same for the opposite scenario.
	If fast moving average is significantly lower the slower moving one,
	it is treated as a signal to buy in anticipation of market mode
	switch to bull.
"""

class StrategyLogicSimpleMeanReversion:
	def __init__(self, xcon, filename = "strategy_logic_simple_mean_reversion.pickle", debug = False):

		self.filename = filename
		self.xcon = xcon

		# Constants
		self.Price_Fast_EMA_Time		= 7  * 60 	# minutes
		self.Price_Slow_EMA_Time		= 14 * 60	# minutes
		self.Price_LongTerm_EMA_Time	= 21 * 60	# minutes

		self.Last_Buy_Price  = 0.0
		self.Last_Sell_Price = 0.0
		self.Current_Price = 0.0

		self.MinimumSpreadBuy = 0.0024
		self.MinimumSpreadSell = 0.0012

		# Price indicators

		# Slow moving price average
		timedelta = datetime.timedelta(minutes = self.Price_Slow_EMA_Time)
		self.price_ema_slow = ema(timedelta)

		# Fast five minutes moving averages
		timedelta = datetime.timedelta(minutes = self.Price_Fast_EMA_Time)
		self.price_ema_fast = ema(timedelta)

		# Long Term moving average
		timedelta = datetime.timedelta(minutes = self.Price_LongTerm_EMA_Time)
		self.price_ema_longterm = ema(timedelta)

		self._debugData = {}

		# Restore state from disk if possible
		if (not debug):
			self.Load()

		# Make sure we use the currently passed ExchangeConnection, not the restored one
		self.xcon = xcon
		self.debug = debug

	def UpdatePrice(self, data):

		self.price_ema_slow.Update(data)
		self.price_ema_fast.Update(data)
		self.price_ema_longterm.Update(data)
		self.Current_Price = data["value"]
		self._updatePriceDebugHook(data)

	def ShouldBuy(self):
		# Returns true if faster moving averages are significantly
		# lower slower moving ones.
		# Treated as a signal to buy.

#		ma_diff_min = self.price_ema_slow.Value * self.MinimumSpreadBuy
		ma_diff_min = self.price_ema_longterm.Value * self.MinimumSpreadBuy
		ma_diff = self.price_ema_slow.Value - self.price_ema_fast.Value
 		if ( ma_diff < ma_diff_min ):
 			return False

#		ma_diff_min = self.price_ema_longterm.Value * self.MinimumSpreadBuy
		ma_diff = self.price_ema_longterm.Value - self.price_ema_slow.Value
 		if ( ma_diff < ma_diff_min ):
 			return False

 		return True

	def ShouldSell(self):
		# Returns true if faster moving averages are significantly
		# larger slower moving ones.
		# Treated as a signal to sell.

		ma_diff_min = self.price_ema_fast.Value * self.MinimumSpreadSell
		ma_diff = self.price_ema_fast.Value - self.price_ema_slow.Value
 		if ( ma_diff < ma_diff_min ):
 			return False

#		ma_diff_min = self.price_ema_slow.Value * self.MinimumSpreadSell
		ma_diff = self.price_ema_slow.Value - self.price_ema_longterm.Value
 		if ( ma_diff < ma_diff_min ):
 			return False

 		return True

	def Act(self):

		# If we do not have enough data, and are just starting, take no action
		if (not self.price_ema_slow.IsAccurate()):
			return

		if (not self.price_ema_longterm.IsAccurate()):
			return

		# Debug breakpoint for particular datapoints in time
		if (self._debugIsNowPassedTimeStamp("2013 Aug 17 05:00", "%Y %b %d %H:%M")):
			set_breakpoint_here = True

		# Currently invested in BTC
		if (self.xcon.AvailableBTC() * self.Current_Price > self.xcon.AvailableUSD()):

			if (not self.ShouldSell()):
				return

			self.ConvertAllToUSD()
			return

		# Currently invested in USD
		if (self.xcon.AvailableBTC() * self.Current_Price < self.xcon.AvailableUSD()):

			if (not self.ShouldBuy()):
				return

			self.ConvertAllToBTC()

	def Load(self):
		try:
			f = open(self.filename,'rb')
			tmp_dict = pickle.load(f)
			self.__dict__.update(tmp_dict)
			print "LoadSuccess!"
			f.close()
		except:
			print "StrategyLogicSimpleMeanReversion: Failed to load previous state, starting from scratch"

	def Save(self):
		try:
			f = open(self.filename,'wb')
			odict = self.__dict__.copy()
			del odict['xcon'] #don't pickle this
			pickle.dump(odict,f,2)
			f.close()
		except:
			print "StrategyLogicSimpleMeanReversion: Failed to save my state, all the data will be lost"

	def ConvertAllToUSD(self):
		self._preSellBTCDebugHook()
		self.Last_Sell_Price = self.Current_Price
		btc_to_sell = self.xcon.AvailableBTC()
		self.xcon.SellBTC(btc_to_sell)
		self._postSellBTCDebugHook()

	def ConvertAllToBTC(self):
		self._preBuyBTCDebugHook()
		self.Last_Buy_Price = self.Current_Price
		affordable_amount_of_btc = self.xcon.AvailableUSD() / self.Current_Price
		self.xcon.BuyBTC(affordable_amount_of_btc)
		self._postBuyBTCDebugHook()

	def _debugIsNowPassedTimeStamp(self, timestring, timeformat):
		if (not self.debug):
			return False

		now = datetime.datetime.fromtimestamp(self._debugData["PriceEmaFast"][-1]["now"])
		time_of_interest = datetime.datetime.strptime(timestring,timeformat)
		if (now > time_of_interest):
			return True

		return False

	def _updatePriceDebugHook(self, data):
		if (not self.debug):
			return

		if ("RawPrice" not in self._debugData):
			self._debugData["RawPrice"] = []

		if ("PriceEmaSlow" not in self._debugData):
			self._debugData["PriceEmaSlow"] = []

		if ("PriceEmaFast" not in self._debugData):
			self._debugData["PriceEmaFast"] = []

		if ("PriceEmaLongTerm" not in self._debugData):
			self._debugData["PriceEmaLongTerm"] = []

		self._debugData["RawPrice"].append(data)

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.price_ema_slow.Value
		self._debugData["PriceEmaSlow"].append(tmp)
		del tmp

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.price_ema_fast.Value
		self._debugData["PriceEmaFast"].append(tmp)
		del tmp

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.price_ema_longterm.Value
		self._debugData["PriceEmaLongTerm"].append(tmp)
		del tmp

		self._debugData["LastPriceUpdateTime"] = data["now"]

	def _preSellBTCDebugHook(self):
		if (not self.debug):
			return
		msg = "Selling " + str(self.xcon.AvailableBTC()) + " BTC"
		msg += " current price: " + str(self.Current_Price)
		print msg

	def _postSellBTCDebugHook(self):
		if (not self.debug):
			return
		msg = " Wallet: " + str(self.xcon.AvailableBTC()) + " BTC " + str(self.xcon.AvailableUSD()) + " USD"
		msg += " totalUSD: " + str(self.xcon.AvailableUSD() + self.xcon.AvailableBTC() * self.Current_Price)
		msg += " date: " + str(datetime.datetime.fromtimestamp(self._debugData["LastPriceUpdateTime"]))
		print msg

		if ("Trades" not in self._debugData):
			self._debugData["Trades"] = []

		tmp = {}
		tmp["now"] = self._debugData["LastPriceUpdateTime"]
		tmp["value"] = self.xcon.AvailableUSD() + self.xcon.AvailableBTC() * self.Current_Price
		self._debugData["Trades"].append(tmp)

		if ("Sell" not in self._debugData):
			self._debugData["Sell"] = []

		tmp = {}
		tmp["now"] = self._debugData["LastPriceUpdateTime"]
		tmp["value"] = self.Last_Sell_Price
		self._debugData["Sell"].append(tmp)

	def _preBuyBTCDebugHook(self):
		if (not self.debug):
			return
		msg = "Buying " + str(self.xcon.AvailableUSD() / self.Current_Price) + " BTC"
		msg += " current price: " + str(self.Current_Price)
		print msg

	def _postBuyBTCDebugHook(self):
		if (not self.debug):
			return
		msg = " Wallet: " + str(self.xcon.AvailableBTC()) + " BTC " + str(self.xcon.AvailableUSD()) + " USD"
		msg += " totalUSD: " + str(self.xcon.AvailableUSD() + self.xcon.AvailableBTC() * self.Current_Price)
		msg += " date: " + str(datetime.datetime.fromtimestamp(self._debugData["LastPriceUpdateTime"]))
		print msg

		if ("Trades" not in self._debugData):
			self._debugData["Trades"] = []

		tmp = {}
		tmp["now"] = self._debugData["LastPriceUpdateTime"]
		tmp["value"] = self.xcon.AvailableUSD() + self.xcon.AvailableBTC() * self.Current_Price
		self._debugData["Trades"].append(tmp)

		if ("Buy" not in self._debugData):
			self._debugData["Buy"] = []

		tmp = {}
		tmp["now"] = self._debugData["LastPriceUpdateTime"]
		tmp["value"] = self.Last_Buy_Price
		self._debugData["Buy"].append(tmp)

def feedRecordedData(score, sqliteDataFile, date_from, date_to):

	db = sqlite3.connect(sqliteDataFile)
	cursor = db.cursor()
	data = cursor.execute("select amount,price,date from trades where ( (date>"+str(date_from)+") and (date<"+str(date_to)+") and (currency='USD') )")
	actual_date_from = 9999999999999
	actual_date_to = 0

	price_volume_data = []

	for row in data:
		volume = float(row[0])
		price = float(row[1])
		date = float(row[2])

		if ( actual_date_from > date ):
			actual_date_from = date
		if ( actual_date_to < date ):
			actual_date_to = date

		update_data = {}
		update_data["now"] = date
		update_data["price"] = price
		update_data["volume"] = volume
		price_volume_data.append(update_data)

	from operator import itemgetter
	price_volume_data = sorted(price_volume_data, key=itemgetter("now"))

	for item in price_volume_data:
		score.xcon.SetBTCPrice(item["price"])
		tmp = {"now":item["now"], "value": item["price"]}
		score.UpdatePrice(tmp)
		score.Act()

	cursor.close()

	return (actual_date_from, actual_date_to)

def plotStrategyCorePerformance(debugData):
	import strategy_plot

	subplots = 1
	splot = strategy_plot.StrategyPlot(debugData, subplots)
	splot.Plot("RawPrice",1, "y-")
	splot.Plot("Sell", 1, "ro")
	splot.Plot("Buy", 1, "g^")
	splot.Plot("PriceEmaSlow", 1, "g-")
	splot.Plot("PriceEmaFast", 1, "b-")
	splot.Plot("PriceEmaLongTerm", 1, "r-")

	splot.Show()

def main():
	# Test this strategy core by mocking ExchangeConnection
	# And by feeding it the prerecorded data
	xcon = MockExchangeConnection()
	score = StrategyLogicSimpleMeanReversion(xcon, debug = True)

	tmp = datetime.datetime.strptime("2013 Dec 1 00:00", "%Y %b %d %H:%M")
	date_from = float(calendar.timegm(tmp.utctimetuple()))
	tmp = datetime.datetime.strptime("2013 Dec 20 12:00", "%Y %b %d %H:%M")
	date_to = float(calendar.timegm(tmp.utctimetuple()))

	(actual_date_from, actual_date_to) = feedRecordedData(score, "mtgoxdata/mtgox.sqlite3", date_from, date_to)
	print "Simulation from: " + str(datetime.datetime.fromtimestamp(date_from)) + " to " + str(datetime.datetime.fromtimestamp(date_to))
	print "Total funds. BTC: " + str(xcon.AvailableBTC()) + " USD: " + str(xcon.AvailableUSD()) + " current price: " + str(xcon.currentPrice) + " Convert to USD:" + str(xcon.AvailableBTC() * score.Current_Price + xcon.AvailableUSD())
	plotStrategyCorePerformance(score._debugData)

if __name__ == "__main__":
    main()