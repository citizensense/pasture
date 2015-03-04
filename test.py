#!/bin/python3
from database import *

db = Database('data/db.sqlite3', {}, 'locals')
print(db.msg)

# Now bring back some actual data!
rows = db.dbselectquery("SELECT timestamp, csv, cid FROM csvs WHERE timestamp is null")
print(db.msg)

# Now loop through the data and generate data and json
i=n=1
for row in rows:
    vals = row[1].split(',')
    emptytimestamp = row[0]
    realtimestamp = vals[0]
    cid = row[2]
    csv = row[1]
    # Now lets update the database with the new timestamp
    toupdate = {'timestamp':realtimestamp}
    dbresp = db.update('csvs', 'cid', cid, toupdate)
    if dbresp:
        if n > 100:
            print('{} | {} | {} | {}'.format(cid, emptytimestamp, realtimestamp, csv)) 
            n=0
    else:
        print('Unable to update:{}'.format(cid))
    #print(i)
    n=n+1
    i=i+1
print('Rows updated:{}'.format(i))

