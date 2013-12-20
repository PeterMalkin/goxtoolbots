import goxapi

class ExchangeConnection:
	def __init__(self, gox):
		self.gox = gox
	def AvailableBTC(self):
		btc = self.gox.wallet[self.gox.curr_base]
		return self.gox.base2float(btc)
	def AvailableUSD(self):
		usd = self.gox.wallet[self.gox.curr_quote]
		return self.gox.quote2float(usd)
	def SellBTC(self,amount):
		print "Selling " + str(amount) + " BTC"
		self.gox.sell(0, self.gox.base2int(amount))
	def BuyBTC(self,amount):
		print "Buying " + str(amount) + " BTC"
		self.gox.buy(0, self.gox.base2int(amount))

class MockExchangeConnection(ExchangeConnection):
	def __init__(self, availableBTC = 0.0, availableUSD = 10.0, currentPrice = 200.0):
		self.availableBTC = availableBTC
		self.availableUSD = availableUSD
		self.currentPrice = currentPrice
	def SetBTCPrice(self, price):
		self.currentPrice = price
	def AvailableBTC(self):
		return self.availableBTC
	def AvailableUSD(self):
		return self.availableUSD
	def SellBTC(self, amount):
		if (amount <= 0.0):
			return
		if (self.availableBTC < amount):
			print "SellBTC: not enough BTC to sell: I was asked to sell " + str(amount) + ", but I only have " + str(self.availableBTC)
			return
		self.availableUSD += amount * self.currentPrice
		self.availableBTC -= amount
		self.availableUSD = self.availableUSD - self.availableUSD * 0.006
	def BuyBTC(self, amount):
		if (amount <= 0.0):
			return
		if (self.availableUSD / self.currentPrice < amount):
			print "BuyBTC: not enough USD to buy BTC: I was asked to buy " + str(amount) + "BTC, but I only have " + str(self.availableUSD) + "USD, and the current price is " + str(self.currentPrice)
			return
		self.availableUSD -= self.currentPrice * amount
		self.availableBTC += amount
		self.availableBTC -= self.availableBTC * 0.006