#!/bin/python3
from database import *
import time, sqlite3

# Connect to database
db = sqlite3.connect('data/db.sqlite3')
print("Opened database successfully")
cursor = db.execute("SELECT timestamp, csv, cid FROM csvs WHERE timestamp is null")

# Now loop through the data and generate data and json
i=n=1
dbupdate=True
for row in cursor:
    vals = row[1].split(',')
    emptytimestamp = row[0]
    realtimestamp = vals[0]
    cid = row[2]
    csv = row[1]
    # Now lets update the database with the new timestamp
    if dbupdate:
        db.execute("UPDATE csvs SET timestamp=? WHERE cid=?", (realtimestamp, cid)) 
        if n > 50000: 
            print('# {} | {} | {} | {} | {}'.format(i, cid, emptytimestamp, realtimestamp, csv)) 
            n=0 
            db.commit()
    n=n+1
    i=i+1
db.commit()
print('Rows to update{}'.format(i))

