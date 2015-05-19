#!/bin/python3
import time, sqlite3, json
from datetime import datetime

def run():
    # Connect to database and create the new frackbox table
    db = sqlite3.connect('db.sqlite3')
    frackboxes = ['1','2','3','4','6','8','14','15','234','309','335','336']
    genfrackboxdata(db, frackboxes)
    genspeckdata(db, frackboxes)

def genspeckdata(db, frackboxes):
    # Create the new frackbox table
    #db.execute("DROP TABLE speckdata;")
    createtableqry = specktable()
    db.execute(createtableqry)
    # Now generate the new data
    ands = ' AND nid!='.join(frackboxes)
    qry="SELECT DISTINCT cid, nid, created, header, timestamp, csv FROM csvs WHERE nid!={}".format(ands)
    cursor = db.execute(qry)
    # Now loop through the rows and create new rows in the frackbox table
    i=n=1
    for row in cursor:
        qry = speckqrystring(row)
        if row[0] == 58923: 
            print('FOUND: 58923-----------------------------------------------------------------------------------')
            print(qry)
        try:
            db.execute(qry) 
        except Exception as e:
            #print('\n')
            #print(e)
            #print(row)
            #print(qry)
            pass
        # Every 5000 records, commit the updates
        if n > 50000: 
            print(qry) 
            n=0 
            db.commit()
        n=n+1
        i=i+1
    db.commit()
    print('Created {} Speck rows'.format(i))
 
def genfrackboxdata(db, frackboxes):
    # Create the new frackbox table
    #db.execute("DROP TABLE frackboxV1data;")
    createtableqry = frackboxtable()
    db.execute(createtableqry)
    # Now generate the new data
    ands = ' OR nid='.join(frackboxes)
    qry="SELECT DISTINCT cid, nid, created, header, timestamp, csv FROM csvs WHERE nid={}".format(ands)
    cursor = db.execute(qry)
    # Now loop through the rows and create new rows in the frackbox table
    i=n=1
    for row in cursor:
        qry = frackboxqrystring(row)
        try:
            db.execute(qry) 
        except:
            pass
        # Every 5000 records, commit the updates
        if n > 50000: 
            print(qry) 
            n=0 
            db.commit()
        n=n+1
        i=i+1
    db.commit()
    print('Created {} Frackbox rows'.format(i))
 

def frackboxtable():
    return "CREATE TABLE frackboxV1data(fid INT PRIMARY KEY NOT NULL,nid INT,timestamp INT,localdate TEXT,lat REAL,lon REAL,speed REAL,alt REAL,
    XTemp REAL,XHumid REAL,winddir TEXT,NOppb REAL,O3ppb REAL,O3no2ppb REAL,NO2ppb REAL,PIDppm REAL,PID REAL,NOwe3 INT,
    NOae3 INT,O3we2 INT,O3ae2 INT,NO2we1 INT,NO2ae1 INT,PT INT,CPU TEXT,Disk TEXT,Load TEXT,network TEXT,ws INT,wd INT)"

def specktable():
    # timestamp,raw_particles,particle_concentration,humidity
    return "CREATE TABLE speckdata(sid INT PRIMARY KEY NOT NULL, nid INT, timestamp INT, localdate TEXT, 
    raw_particles INT, particle_concentration REAL, humidity INT, ws INT, wd INT)"

def speckqrystring(row):
    csv=row[5]
    nid=row[1]
    # Header= sid, nid, timestamp, localdate, raw_particles, particle_concentration, humidity, ws, wd
    vals = csv.split(',')
    #print('{} | {}'.format(nid, csv))
    try:
        sid=row[0]
        nid=row[1]
        timestamp=strtoint(row[4])
        localdate=gmt(timestamp)
        raw_particles=strtoint(vals[1])
        particle_concentration=strtofloat(vals[2])
        humidity=strtoint(vals[3])
        ws = None
        wd = None
        values=[sid, nid, timestamp, localdate, raw_particles, particle_concentration, humidity, ws, wd]
        valuesstring = json.dumps(values)
        valuesstring = valuesstring.replace('[','(')
        valuesstring = valuesstring.replace(']',');')
        return 'INSERT INTO speckdata VALUES {}'.format(valuesstring)
    except Exception as e:
        header=''
        print('\nError nid:{} | {} | \n{}\n{}'.format(nid, e, header,csv))


def frackboxqrystring(row):
    csv=row[5]
    nid=row[1]
    # Header= 0:timestamp,1:humandate,2:lat,3:lon,4:speed,5:alt,6:XTemp,7:XHumid,8:winddir,9:NOppb,10:O3ppb,
    # 11:O3no2ppb,12:NO2ppb,13:PIDppm,14:PID,15:NOwe3,16:NOae3,17:O3we2,18:O3ae2,19:NO2we1,20:NO2ae1,
    # 21:PT+,22:CPU,23:Disk,24:Load,25:network
    vals = csv.split(',')
    #print('{} | {}'.format(nid, csv))
    try:
        fid=row[0]
        nid=row[1]
        timestamp=strtoint(row[4])
        gmtdate=gmt(timestamp)
        lat=strtofloat(vals[2])
        lon=strtofloat(vals[3])
        speed=strtofloat(vals[4])
        alt=strtofloat(vals[5])
        XTemp=strtofloat(vals[6])
        XHumid=strtofloat(vals[7])
        winddir=vals[8]
        NOppb=strtofloat(vals[9])
        O3ppb=strtofloat(vals[10])
        O3no2ppb=strtofloat(vals[11])
        NO2ppb=strtofloat(vals[12])
        PIDppm=strtofloat(vals[13])
        PID=strtofloat(vals[14])
        NOwe3=strtoint(vals[15])
        NOae3=strtoint(vals[16])
        O3we2=strtoint(vals[17])
        O3ae2=strtoint(vals[18])
        NO2we1=strtoint(vals[19])
        NO2ae1=strtoint(vals[20])
        PT=strtoint(vals[21])
        CPU=vals[22]
        Disk=vals[23]
        Load=vals[24]
        network=vals[25]
        ws = None
        wd = compass(winddir)
        values=[fid,nid,timestamp,gmtdate,lat,lon,speed,alt,XTemp,XHumid,winddir,NOppb,O3ppb,O3no2ppb,NO2ppb,
                PIDppm,PID,NOwe3,NOae3,O3we2,O3ae2,NO2we1,NO2ae1,PT,CPU,Disk,Load,network,ws,wd]
        valuesstring = json.dumps(values)
        valuesstring = valuesstring.replace('[','(')
        valuesstring = valuesstring.replace(']',');')
        return 'INSERT INTO frackboxV1data VALUES {}'.format(valuesstring)
    except Exception as e:
        header='fid,nid,timestamp,gmtdate,lat,lon,speed,alt,XTemp,XHumid,winddir,NOppb,O3ppb,O3no2ppb,NO2ppb,PIDppm,PID,NOwe3,NOae3,O3we2,O3ae2,NO2we1,NO2ae1,PT,CPU,Disk,Load,network,ws,wd'
        print('\nError nid:{} | {} | \n{}\n{}'.format(nid, e, header,csv))

def gmt(timestamp):
    # Minus 5 hours in seconds
    fivehours = (60*60)*5
    timestamp = timestamp-fivehours
    # GMT without BST or DST conversion
    date = datetime.utcfromtimestamp(timestamp)
    # With BST/DST conversion
    date =  datetime.fromtimestamp(timestamp)
    # Return in this format: # YYYY-MM-DD HH:MM:SS
    return date.strftime("%Y-%m-%d %H:%M:%S")

def strtoint(string):
    if string != '':
        i=int(string)
    else:
        i=None
    return i

def strtofloat(string):
    if string != '':
        f=float(string)
    else:
        f=None
    return f

def compass(baring):
    d=None
    if baring=='N':d=0
    if baring=='NE':d=45
    if baring=='E':d=90
    if baring=='SE':d=135
    if baring=='S':d=180
    if baring=='SW':d=225
    if baring=='W':d=270
    if baring=='NW':d=315
    return d

# Run the script
run()
