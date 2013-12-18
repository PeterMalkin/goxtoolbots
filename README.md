#GoxToolBots

A collection of trading bots implementing simple strategies for goxtool

Goxtool is a trading client for the MtGox Bitcon currency exchange.
The user manual is here:
[http://prof7bit.github.com/goxtool/](http://prof7bit.github.com/goxtool/)


Simple trend following bot:
---------------------------
    strategy_simple_trend_follower.py

This bot records MtGox trades and estimates the market trend.
When upward trend detected, the bot buys. When downward trend detected,
bot sells.

Market trend estimation is done by using three moving price averages.

Features:  
* Uses three moving average to estimate the trend of the market  
* Trades following the market trend  
* Download historic data for MtGox trades  
* Backtest your strategy on historic date  
* Plot the behavior of your bot  
* Save/Restore bot state  

Usage:  
    ./goxtool.py --strategy strategy_simple_trend_follower.py


Volume gated trend following bot:
---------------------------------
    strategy_volume_trend_follower.py

Very similar to trend follower, but the trades are gated by the shift in
volume. The idea is that significant price shift is always a result of
a significant change in trade volumes. So unless an increased trade volume
is detected, the trend follower is disabled.

Market trend estimation is done by using three moving price averages.

Usage:  
    <code>./goxtool.py --strategy strategy\_volume\_trend\_follower.py</code>


Trailing stop loss bot:
-------------------------------
    strategy_trailing_stoploss.py

This is an implementation of a trailing stop loss trading bot
for MtGox bitcoin exchange.

This bot tracks MtGox trades and records the maximum price of BTC in the last three hours.
If the current price drops below 15% of the maximum, the bot sells all BTC assets
as Market Order and stops. It also send a notification email to the owner.

Features:  
* Sell all BTC for USD in case the BTC price dips 15% below maximum value of 3 hours  
* Send an email notification when sell BTC  
* Download historic data for MtGox trades  
* Backtest your strategy on historic date  
* Plot the behavior of your bot  
* Save/Restore bot state  

Usage:  
    </code>./goxtool.py --strategy strategy\_trailing\_stoploss.py</code>


Key commands:
------------
Each bot supports these key commands:  
* "S" - Sell all BTC  
* "B" - Buy BTC for all the USD you have  
* "C" - Cancell all outstanding orders  
* "D" - Dump bot state (for offline plotting)  

Backtesting:
------------
    python download-mtgox-data.py  
in the mtgoxdata folder downloads all the data from mtgox trades
into a sqlite database. Please be careful and do not overwhelm
the exchange with requests. I will try to put up a website to
share this data for direct download. Meanwhile you can ping me,
I can send it to you.

If you run any of the <code>strategy\_logic\_*.py</code>
python scripts as a standalone porgram, it will default
to backtesting its behavior on downloaded historic data.
It will use matplotlib to show the prices and points of
sells/buys. This is useful for developing your own bots.

Examples:  
    <code>python strategy\_logic\_simple\_trend\_follower.py</code>  
    <code>python strategy\_logic\_trailing\_stoploss.py</code>  

Please not that in the main() function of each strategy logic scripts you can tweak the
simluation start and end dates.

Bots states:
----------
Bot automatically dumps its state into a file when the strategy is unloaded.
You can also manually produce a dump by pressing "D". You can plot the state
of the dump with <code>plot\_pickled.py.</code>
The filename of the dump is <code>strategy\_logic\_*.pickle</code>

Email:
------
Trailing stop loss bot can send you an email notification when it sells.
Adjust your email credentials in goxtool.ini to enable email notifications.
You will need the following:

    [email]
    email_to = mtgoxtrader@example.com  
    email_from = tradingbot@example.com  
    email_server = smtp.example.com  
    email_server_port = 25  
    email_server_password = TradingBotEmailPassword  

Support:
--------
Please consider donating to: 16csNHCBstmdcLnPg45fxF2PdKoPyPJDhX

