import datetime
import time
import pickle
import sqlite3
import calendar
import math
import smtplib
from email.mime.text import MIMEText
from indicator.ma import ExponentialMovingAverage as ema
from indicator.timeminmax import TimeMax, TimeMin
from exchange_connection import ExchangeConnection, MockExchangeConnection

"""
	Trailing stop loss bot.
	When bot detects that the price has droped over 15%
	from the maximum price recorded in the last three hours,
	it sells all funds and sends an email notification.
"""

class StrategyLogicTrailingStoploss:
	def __init__(self, xcon, filename = "strategy_logic_trailing_stoploss.pickle", debug = False):

		self.filename = filename
		self.xcon = xcon

		# Constants
		self.Price_Fast_EMA_Time	= 1	# 60 seconds, just to smooth out the price
		self.Price_Max_Time			= 90	# 3 hours
		self.Price_Drop_Percent		= 15.0	# percent
		self.Current_Price = 0.0
		self.Enabled = True

		# Fast price moving average
		timedelta = datetime.timedelta(minutes = self.Price_Fast_EMA_Time)
		self.price_ema_fast = ema(timedelta)

		# Price maximum values over an hour for sell signal
		timedelta = datetime.timedelta(minutes = self.Price_Max_Time)
		self.price_trailing_max = TimeMax(timedelta)

		self._debugData = {}

		# If we are in debug mode, do not restore previously saved state from file
		if (not debug):
			self.Load()

		# Make sure we use the currently passed ExchangeConnection, not the restored one
		self.xcon = xcon
		self.debug = debug

	def __del__(self):
		self.Save()

	def UpdatePrice(self, data):
		self.price_ema_fast.Update(data)
		self.Current_Price = data["value"]

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.price_ema_fast.Value
		self.price_trailing_max.Update(tmp)

		self._updatePriceDebugHook(data)

	def IsBigPriceDrop(self):

		if (not self.price_trailing_max.IsAccurate()):
			return False

		if ( self.price_trailing_max.Max - self.price_ema_fast.Value > self.price_trailing_max.Max * (self.Price_Drop_Percent/100) ):
			timedelta = datetime.timedelta(minutes = self.Price_Max_Time)
			self.price_trailing_max = TimeMax(timedelta)
			return True

		return False

	def Act(self):

		if ( self.Enabled == False ):
			return

		# If we do not have enough data, and are just starting, take no action
		if (not self.price_ema_fast.IsAccurate()):
			return

		# Currently invested in BTC
		if (self.xcon.AvailableBTC() * self.Current_Price > self.xcon.AvailableUSD()):

			if ( self.IsBigPriceDrop() ):
				self.ConvertAllToUSD()
				if (not self.debug):
					self.Enabled = False
					self.SendEmail()

		# For testing purposes, convert everything back immediately to give chance to
		# Stop loss to sell again. Uncomment the following for backtesting.
		# It will result it continuous buys and sells, but you can catch see
		# All of the curves where the bot would sell
#		if (self.xcon.AvailableUSD() > self.xcon.AvailableBTC() * self.Current_Price):
#
#			if (self.debug):
#				self.ConvertAllToBTC()

	def Load(self):
		try:
			f = open(self.filename,'rb')
			tmp_dict = pickle.load(f)
			self.__dict__.update(tmp_dict)
			f.close()
		except:
			print "StrategyCore: Failed to load previous state, starting from scratch"

	def Save(self):
		try:
			f = open(self.filename,'wb')
			odict = self.__dict__.copy()
			del odict['xcon'] #don't pickle this
			pickle.dump(odict,f,2)
			f.close()
		except:
			print "StrategyCore: Failed to save my state, all the data will be lost"

	def SendEmail(self):

		try:
			email_to = self.xcon.gox.config.get_string("email", "email_to")
			email_from = self.xcon.gox.config.get_string("email", "email_from")
			email_server = self.xcon.gox.config.get_string("email", "email_server")
			email_server_port = self.xcon.gox.config.get_string("email", "email_server_port")
			email_server_password = self.xcon.gox.config.get_string("email", "email_server_password")
		except:
			print "Trailing Stop loss bot failed to send a notification email. Check email settings in goxtool.ini"
			print "These need to be filled out:"
			print "[email]"
			print "email_to=mtgoxtrader@example.com"
			print "email_from=tradingbot@example.com"
			print "email_server=smtp.example.com"
			print "email_server_port=25"
			print "email_server_password=TradingBotEmailPassword"

		msg = "Hello!\n\n"
		msg += "This is a notification from your mtgox trailing stop loss bot.\n"
		msg += "I have just sold "+ str(self.xcon.AvailableBTC()) + " BTC " + "at a price of " + str(self.Current_Price) + " USD\n"
		msg += "Date: " + str(datetime.datetime.fromtimestamp(self._debugData["LastPriceUpdateTime"]))
		msg += "\n\n"
		msg += "If this bot was helpful to you, please consider donating to 16csNHCBstmdcLnPg45fxF2PdKoPyPJDhX\n\n"
		msg += "Thank you!"

		email = MIMEText(msg)
		email['Subject']	= "MtGox trailing stop loss bot sold BTC"
		email['From']		= email_from
		email['To']		= email_to
		s = smtplib.SMTP(email_server,email_server_port)
		s.login(email_from, email_server_password)
		s.sendmail(email_from, email_to, email.as_string())
		s.quit()

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

		if ("RawPrice" not in self._debugData):
			self._debugData["RawPrice"] = []

		if ("PriceEmaFast" not in self._debugData):
			self._debugData["PriceEmaFast"] = []

		self._debugData["RawPrice"].append(data)

		tmp = {}
		tmp["now"] = data["now"]
		tmp["value"] = self.price_ema_fast.Value
		self._debugData["PriceEmaFast"].append(tmp)
		del tmp

		self._debugData["LastPriceUpdateTime"] = data["now"]

	def _preSellBTCDebugHook(self):

		msg = "Selling " + str(self.xcon.AvailableBTC()) + " BTC"
		msg += " current price: " + str(self.Current_Price)
		print msg

	def _postSellBTCDebugHook(self):

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

		msg = "Buying " + str(self.xcon.AvailableUSD() / self.Current_Price) + " BTC"
		msg += " current price: " + str(self.Current_Price)
		print msg

	def _postBuyBTCDebugHook(self):

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
	splot.Plot("Sell", 1, "go")
	splot.Plot("Buy", 1, "y^")
	splot.Plot("PriceEmaFast", 1, "b-")

	splot.Show()

def main():
	# Test this strategy core by mocking ExchangeConnection
	# And by feeding it the prerecorded data
	xcon = MockExchangeConnection()
	score = StrategyLogicTrailingStoploss(xcon, debug = True)

	tmp = datetime.datetime.strptime("2013 Oct 1 22:00", "%Y %b %d %H:%M")
	date_from = float(calendar.timegm(tmp.utctimetuple()))
	tmp = datetime.datetime.strptime("2013 Oct 3 12:00", "%Y %b %d %H:%M")
	date_to = float(calendar.timegm(tmp.utctimetuple()))

	(actual_date_from, actual_date_to) = feedRecordedData(score, "mtgoxdata/mtgox.sqlite3", date_from, date_to)
	print "Simulation from: " + str(datetime.datetime.fromtimestamp(date_from)) + " to " + str(datetime.datetime.fromtimestamp(date_to))
	print "Total funds. BTC: " + str(xcon.AvailableBTC()) + " USD: " + str(xcon.AvailableUSD()) + " current price: " + str(xcon.currentPrice) + " Convert to USD:" + str(xcon.AvailableBTC() * score.Current_Price + xcon.AvailableUSD())
	plotStrategyCorePerformance(score._debugData)

if __name__ == "__main__":
    main()