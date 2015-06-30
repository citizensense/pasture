#!/bin/python3
import time, datetime, sqlite3

class UploadMe:

    def __init__(self):
        self.dbconnect()
        #self.loopmarcellus() # Insert wellstart, inspections and violations data
        self.looptownshipsgps() # Insert township gps data

    def dbconnect(self):
        # Connect to database
        self.db = sqlite3.connect('../data/db.sqlite3')
        print("Opened database successfully")
    
    def convertdate(self, datestring):
        timecode = time.mktime(datetime.datetime.strptime(datestring, "%m/%d/%Y").timetuple())
        return timecode

    def looptownshipsgps(self):
        # Read the csv file
        fo = open("townshipgps.csv", "r")
        # Create a DB cursor
        cursor = self.db.cursor()
        # Now loop through the data and generate data and json
        i = n = 0;
        line = True
        while line:
            line = fo.readline()
            data = line.strip().split(',') 
            if(len(data)>1):
                title = data[0].strip()
                lat = data[1].strip()
                lon = data[2].strip()
                print('title:"{}" lat:"{}" lon:"{}"'.format(title, lat, lon))
                qry = "UPDATE marcellus_data SET gps_lat=?, gps_lon=? WHERE township=?"
                self.db.execute(qry, (lat, lon, title)) 
            n=n+1
        self.db.commit()
        print('Updated Rows{}'.format(n))

    def loopmarcellus(self):
        # Read the csv file
        fo = open("marcellus.csv", "r")
        # Create a DB cursor
        cursor = self.db.cursor()
        # Now loop through the data and generate data and json
        i = n = 0;
        line = True
        while line:
            line = fo.readline()
            data = line.strip().split(',') 
            datalen = len(data)
            if n > 0 and datalen>2:
                timecode = int(self.convertdate(data[3]))
                values = (data[1], data[2], data[3], timecode, data[5], data[6], data[7])
                print('[{}] values:{}'.format(n,values))
                qry = "INSERT INTO marcellus_data(filename,type,datestring,timestamp,township,insp_vio_id,permit_number) VALUES(?,?,?,?,?,?,?)"
                self.db.execute(qry, values) 
            if i >= 400:
                i=0
                self.db.commit()
            i=i+1
            n=n+1
        self.db.commit()
        print('Updated Rows{}'.format(n))

UploadMe();
