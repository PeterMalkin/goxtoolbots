import httplib
import json
import time
import datetime
import sqlite3
import sys
import calendar

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot
import matplotlib.dates


# Plot prices
def plotPrices(timestamps, price, volume, filename = "prices.png"):
	fig = matplotlib.pyplot.figure( figsize=(10, 4), dpi=80 )
	ax = fig.add_subplot(111)
	line1, = ax.plot(timestamps, price, color="red")
#	line2, = ax.plot(timestamps, volume, color="blue")
	ax.set_ylabel("USD")
	ax.set_xlabel("time")
	matplotlib.pyplot.xticks(rotation="25")
#	fig.legend([line1, line2], ["price, USD", "volume, BTC"])
	fig.savefig(filename)

def loadDataFromSqllite(filename, date_from, date_to):
	db = sqlite3.connect(filename)
	cursor = db.cursor()
	data = cursor.execute("select amount,price,date,tid from trades where ( (date>"+str(date_from)+") and (date<"+str(date_to)+") and (currency='USD') )")

	actual_date_from = 9999999999999
	actual_date_to = 0
	volumes = []
	prices = []
	dates = []
	for row in data:
		volume = float(row[0])
		price = float(row[1])
		date = int(row[2])
		if ( actual_date_from > date ):
			actual_date_from = date
		if ( actual_date_to < date ):
			actual_date_to = date
		if ( price > 1000 ):
			print int(row[3])
			print price
			continue
		volumes.append( volume )
		prices.append( price )
		dates.append( date )

	cursor.close()
	result = {}
	result["prices"]=prices
	result["volumes"]=volumes
	result["dates"]=dates
	result["date_from"]=actual_date_from
	result["date_to"]=actual_date_to
	return result

def printData(trade_dates, mtgox_prices, mtgox_volumes):
	totalVolume = 0
	for vol in mtgox_volumes:
		totalVolume+=vol
	print "Total volume for period: " + str(totalVolume)
	print "Closing price: " + str(mtgox_prices[-1])

def Main():

	if (len(sys.argv)<2):
		print "Please give me a sqlite database as a parameter"
		print "example: python mtgoxprint.py mtgox.sqlite3"
		exit()

	tmp = datetime.datetime.strptime("2013 Oct 19 15:00", "%Y %b %d %H:%M")
	# tmp = datetime.datetime.now() - datetime.timedelta(days = 1)
	date_from = float(calendar.timegm(tmp.utctimetuple()))
	tmp = datetime.datetime.strptime("2013 Oct 19 16:00", "%Y %b %d %H:%M")
	date_to = float(calendar.timegm(tmp.utctimetuple()))
	# date_to = int(time.time())
	data = loadDataFromSqllite(sys.argv[1],date_from, date_to)

	trade_dates = data["dates"]
	mtgox_prices = data["prices"]
	mtgox_volumes = data["volumes"]
	timestamp_from = data["date_from"]
	timestamp_to = data["date_to"]

	printData(trade_dates, mtgox_prices, mtgox_volumes)
	plotPrices(trade_dates, mtgox_prices, mtgox_volumes)

	result = "Total records: " + str(len(mtgox_prices)) + " "
	result += " from: " + str(datetime.datetime.fromtimestamp(timestamp_from)) + " "
	result += " to: " + str(datetime.datetime.fromtimestamp(timestamp_to)) + " "
	print result

Main()


