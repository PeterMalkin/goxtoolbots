import httplib
import json
import time
import threading
import sqlite3
import socket

print_lock = threading.RLock()

#currencies = ['USD','EUR','JPY','CAD','GBP','CHF','RUB','AUD','SEK','DKK','HKD','PLN','CNY','SGD','THB','NZD']
currencies = ['USD']

headers = {'User-Agent':'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.20) Gecko/20110921 Gentoo Firefox/3.6.20','Connection':'keep-alive'}

class MtGoxWorker(threading.Thread):
    def run(self):
        db = sqlite3.connect('mtgox.sqlite3')
        db.execute('PRAGMA checkpoint_fullfsync=false')
        db.execute('PRAGMA fullfsync=false')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=off')
        db.execute('PRAGMA temp_store=MEMORY')
        
        connection = httplib.HTTPSConnection('data.mtgox.com')
        
        cursor = db.cursor()
        cursor.execute("select max(tid) from trades where currency=?",(self.currency,))
        try:
            max_tid = int(cursor.fetchone()[0])
        except TypeError:
            max_tid = 0

        with print_lock:
            print "connected",self.currency
        
        while True:
            try:
                print max_tid
                connection.request('GET','/api/1/BTC'+self.currency+'/public/trades?since='+str(max_tid),'',headers)
                
                response = connection.getresponse()
                result = json.load(response)
                
                if result['result'] == 'success':
                    if len(result['return']) == 0:
                        time.sleep(120)
                    else:
                        cursor = db.cursor()
                        
                        for trade in result['return']:
                            cursor.execute("""
                            INSERT OR IGNORE INTO trades(tid,currency,amount,price,date,real)
                            VALUES (?,?,?,?,?,?)
                            """,(trade['tid'],trade['price_currency'],trade['amount'],trade['price'],trade['date'],trade['primary']=='Y'))
                        
                        cursor.execute("select max(tid) from trades where currency=?",(self.currency,))
                        
                        max_tid = int(cursor.fetchone()[0])
                        
                        db.commit()
                        cursor.close()
            except httplib.HTTPException:
                connection = httplib.HTTPSConnection('data.mtgox.com')
            except socket.error:
                connection = httplib.HTTPSConnection('data.mtgox.com')
            except ValueError:
                connection = httplib.HTTPSConnection('data.mtgox.com')

db = sqlite3.connect('mtgox.sqlite3')
db.execute('PRAGMA checkpoint_fullfsync=false')
db.execute('PRAGMA fullfsync=false')
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA synchronous=off')
db.execute('PRAGMA temp_store=MEMORY')

db.execute('CREATE TABLE IF NOT EXISTS trades(tid integer,currency text,amount real,price real,date integer,real boolean);')
db.execute('CREATE UNIQUE INDEX IF NOT EXISTS trades_currency_tid_index on trades(currency,tid);')

db.close()

workers = []

for currency in currencies:
    w = MtGoxWorker()
    w.currency = currency
    w.daemon = True
    w.start()
    
    workers.append(w)
    
    time.sleep(5000)

while True:
    time.sleep(2)
