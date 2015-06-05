#!/bin/python3
import time, sqlite3, json, string, os.path, calendar
import urllib.request as ur
from datetime import datetime

# Create the DB connection
db = sqlite3.connect('db.sqlite3')
myfile = "out.csv"

with open(myfile) as f:
    content = f.readlines()
    cursor = db.cursor() 
    r=0
    for row in content:
        data = row.strip().split(',')
        myid = data[0]
        alttitle = data[1].replace('"', '')
        if alttitle != '' and r>0:
            qry = 'UPDATE nodes SET code="{1}" WHERE nid={0};'.format(myid, alttitle)
            print(qry)
            cursor.execute(qry)
        r = r+1
db.commit()

