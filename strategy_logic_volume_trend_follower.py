import datetime
import time
import pickle
import sqlite3
import calendar
import math
from indicator.ma import ExponentialMovingAverage as ema
from indicator.ma import SimpleMovingAverage as sma
from indicator.candlestick import CandleStick
from indicator.timesum import TimeSum
from indicator.timeminmax import TimeMax, TimeMin
from exchange_connection import ExchangeConnection, MockExchangeConnection

"""
	Volume Trend Following bot
	Similar to moving average based trading bot.
	The difference is that it also pays attention to volume of trades.
	Big price moves are usually associated with big trading volumes.
	So this bot tracks the amount of trades made, and uses it as a
	gating signal for trend following trades.
"""

class StrategyLogicVolumeTrendFollower:
	def __init__(self, xcon, filename = "strategy_logic_volume_trend_follower.pickle", debug = False):

		self.filename = filename
		self.xcon = xcon

		# Constants
		self.Price_Fast_EMA_Time		= 0.5	# 5 minutes
		self.Price_Slow_SMA_Time		= 14	# 30 minutes
		self.Price_LongTerm_EMA_Time	= 60*4	# 4 hours

		self.Volume_TimeSum_Time		= 1		# minutes
		self.Volume_Fast_EMA_Time		= 3		# minutes
		self.Volume_Slow_SMA_Time		= 20	# minutes

		self.Volume_MA_Spike_Diff_Coef	= 3.5	# ema/sma
		self.Volume_MA_Spike_Diff_Value	= 570	# ema - sma

		self.Last_Buy_Price  = 0.0
		self.Last_Sell_Price = 0.0
		self.Current_Price = 0.0

		# Volume indicators

		# Volume TimeSum - a sum of all trades per timeframe
		self.current_volume_timesum = None

		# Volume slow moving average
		timedelta = datetime.timedelta(minutes = self.Volume_Slow_SMA_Time)
		self.volume_sma_slow = sma(timedelta)

		# Volume fast moving average
		timedelta = datetime.timedelta(minutes = self.Volume_Fast_EMA_Time)
		self.volume_ema_fast = ema(timedelta)

		self.volume_spike = False

		# Price indicators

		# Slow moving price average
		timedelta = datetime.timedelta(minutes = self.Price_Slow_SMA_Time)
		self.price_sma_slow = sma(timedelta)

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

	def UpdateVolume(self, data):

		if (self.current_volume_timesum == None):
			timesum_time_from = datetime.datetime.fromtimestamp(int(data["now"]))
			timesum_time_to = timesum_time_from + datetime.timedelta(minutes = self.Volume_TimeSum_Time)
			self.current_volume_timesum = TimeSum(timesum_time_from, timesum_time_to)

		self.current_volume_timesum.Update(data)

		self._volumeUpdateDebugHook(data)

		if ( not self.current_volume_timesum.IsAccurate() ):
			return

		data["value"] = self.current_volume_timesum.Value
		self.volume_sma_slow.Update(data)
		self.volume_ema_fast.Update(data)

		if (self.volume_ema_fast.Value / self.volume_sma_slow.Value > self.Volume_MA_Spike_Diff_Coef):
			if (self.volume_ema_fast.Value - self.volume_sma_slow.Value > self.Volume_MA_Spike_Diff_Value):
				self.volume_spike = True

		if (self.volume_ema_fast.Value < self.volume_sma_slow.Value ):
			self.volume_spike = False

		self.current_volume_timesum = None

	def UpdatePrice(self, data):

		self.price_sma_slow.Update(data)
		self.price_ema_fast.Update(data)
		self.price_ema_longterm.Update(data)
		self.Current_Price = data["value"]

		self._updatePriceDebugHook(data)

	def IsDownTrend(self):

		if ( self.price_ema_fast.Value > self.price_sma_slow.Value ):
			return False

		if ( self.price_ema_fast.Value > self.price_ema_longterm.Value):
			return False

		if (self.price_sma_slow.Value > self.price_ema_longterm.Value):
			return False

		return True

	def IsUpTrend(self):
		ma_diff = self.price_ema_fast.Value - self.price_sma_slow.Value
		ma_diff_min = self.price_ema_fast.Value * 0.0012
		# ma_diff_min = 0

 		if ( ma_diff < ma_diff_min ):
 			return False

		ma_diff = self.price_ema_fast.Value - self.price_ema_longterm.Value
		ma_diff_min = self.price_ema_fast.Value * 0.0012
 		if ( ma_diff < ma_diff_min ):
 			return False

		ma_diff = self.price_sma_slow.Value - self.price_ema_longterm.Value
		ma_diff_min = self.price_ema_fast.Value * 0.0012
 		if ( ma_diff < ma_diff_min ):
 			return False

 		return True

	def Act(self):

		# If we do not have enough data, and are just starting, take no action
		if (not self.price_sma_slow.IsAccurate()):
			return

		if (not self.price_ema_longterm.IsAccurate()):
			return

		if (not self.volume_sma_slow.IsAccurate()):
			return

		# Currently invested in BTC
		if (self.xcon.AvailableBTC() * self.Current_Price > self.xcon.AvailableUSD()):

			if (self.volume_spike == False):
				return

			if (not self.IsDownTrend()):
				return

			self.ConvertAllToUSD()
			return

		# Currently invested in USD
		if (self.xcon.AvailableBTC() * self.Current_Price < self.xcon.AvailableUSD()):

			if (self.volume_spike == False):
				return

			if (not self.IsUpTrend()):
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
			print "SimpleTrendFollowerStrategyCore: Failed to load previous state, starting from scratch"

	def Save(self):
		try:
			f = open(self.filename,'wb')
			odict = self.__dict__.copy()
			del odict['xcon'] #don't pickle this
			pickle.dump(odict,f,2)
			f.close()
		except:
			print "SimpleTrendFollowerStrategyCore: Failed to save my state, all the data will be lost"

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


	def _updatePriceDebugHook(self, data):
		if (not self.debug):
			return

		if ("RawPrice" not in self._debugData):
			self._debugData["RawPrice"] = []

		if ("PriceSmaSlow" not in self._debugData):
			self._debugData["PriceSmaSlow"] = []

		if ("PriceEmaFast" not in self._debugData):
			self._debugData["PriceEmaFast"] = []

		if ("PriceEmaLongTerm" not in self._debugData):
			self._debugData["PriceEmaLongTerm"] = []

		if ("PriceEmaDiff" not in self._debugData):
			self._debugData["PriceEmaDiff"] = []

		self._debugData["RawPrice"].append(data)

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.price_sma_slow.Value
		self._debugData["PriceSmaSlow"].append(tmp)
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

	def _volumeUpdateDebugHook(self, data):

		if (not self.debug):
			return

		if ("RawVolume" not in self._debugData):
			self._debugData["RawVolume"] = []

		if ("VolumeTimeSums" not in self._debugData):
			self._debugData["VolumeTimeSums"] = []

		if ("VolumeSmaSlow" not in self._debugData):
			self._debugData["VolumeSmaSlow"] = []

		if ("VolumeEmaFast" not in self._debugData):
			self._debugData["VolumeEmaFast"] = []

		if ("VolumeSpike" not in self._debugData):
			self._debugData["VolumeSpike"] = []

		self._debugData["RawVolume"].append(data)

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.volume_sma_slow.Value
		self._debugData["VolumeSmaSlow"].append(tmp)
		del tmp

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.volume_ema_fast.Value
		self._debugData["VolumeEmaFast"].append(tmp)

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.current_volume_timesum.Value
		if (self.current_volume_timesum.IsAccurate()):
			self._debugData["VolumeTimeSums"].append(tmp)

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.volume_spike
		self._debugData["VolumeSpike"].append(tmp)

		self._debugData["LastVolumeUpdateTime"] = data["now"]

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
		tmp = {"now":item["now"], "value": item["volume"]}
		score.UpdateVolume(tmp)
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
#	splot.Plot("VolumeTimeSums", 3)
	splot.Plot("PriceSmaSlow", 1, "r-")
	splot.Plot("PriceEmaFast", 1, "b-")
	splot.Plot("PriceEmaLongTerm", 1, "g-")
#	splot.Plot("Trades", 3, "g*")
#	splot.Plot("VolumeSpike", 4, "y-")
#	splot.Plot("VolumeSmaSlow", 2, "r-")
#	splot.Plot("VolumeEmaFast", 2, "b-")
#	splot.Plot("PriceEmaDiff", 3, "y-")

	splot.Show()

def main():
	# Test this strategy core by mocking ExchangeConnection
	# And by feeding it the prerecorded data
	xcon = MockExchangeConnection()
	score = StrategyLogicVolumeTrendFollower(xcon, debug = True)

	tmp = datetime.datetime.strptime("2013 Sep 1 00:00", "%Y %b %d %H:%M")
	date_from = float(calendar.timegm(tmp.utctimetuple()))
	tmp = datetime.datetime.strptime("2013 Sep 30 00:00", "%Y %b %d %H:%M")
	date_to = float(calendar.timegm(tmp.utctimetuple()))

	(actual_date_from, actual_date_to) = feedRecordedData(score, "mtgoxdata/mtgox.sqlite3", date_from, date_to)
	print "Simulation from: " + str(datetime.datetime.fromtimestamp(date_from)) + " to " + str(datetime.datetime.fromtimestamp(date_to))
	print "Total funds. BTC: " + str(xcon.AvailableBTC()) + " USD: " + str(xcon.AvailableUSD()) + " current price: " + str(xcon.currentPrice) + " Convert to USD:" + str(xcon.AvailableBTC() * score.Current_Price + xcon.AvailableUSD())
	plotStrategyCorePerformance(score._debugData)

if __name__ == "__main__":
    main()