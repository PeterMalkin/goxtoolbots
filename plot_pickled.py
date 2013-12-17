import strategy_plot
from strategy_core_trailing_stoploss import StrategyCoreTrailingStoploss
from exchange_connection import MockExchangeConnection

def plotStrategyCorePerformance(debugData):

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
	score = StrategyCoreTrailingStoploss(xcon, debug = True)
	score.Load()
	plotStrategyCorePerformance(score._debugData)

if __name__ == "__main__":
    main()