#!/bin/python3
import sys, logging, time, sqlite3, json
from datetime import datetime

# setup logging
debug=False
logger = logging.getLogger('pasture')
hdlr = logging.FileHandler('/var/log/pasture/pasture.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.WARNING)

def run():
    log('ERROR', '---------------STARTED AUTO UPDATE-----------------------------------------')
    # Grab DB name from commandline
    if len(sys.argv) <= 1:
        print('Specify a database: $ genFBnSPtables.py /srv/webapps/frackbox/data/db.sqlite3COPY')
        exit()
    databasefile = sys.argv[1] 
    # Connect to database and create the new frackbox table
    db = sqlite3.connect(databasefile)
    # Grab a list of frackboxes
    qry = 'SELECT nid,title FROM nodes WHERE datatype="frackbox"';
    cursor = db.execute(qry)
    frackboxes = []
    for row in cursor:
        frackboxes.append(str(row[0]))
    # Now generate the data
    genfrackboxdata(db, frackboxes)
    genspeckdata(db, frackboxes)
    db.close()  
    log('ERROR','FINISHED genFBnSPtables.py')

def genspeckdata(db, frackboxes):
    # Create the new frackbox table
    #db.execute("DROP TABLE speckdata;")
    #createtableqry = specktable()
    #db.execute(createtableqry)
    # Now generate the new data
    ands = ' AND nid!='.join(frackboxes)
    cursor = db.execute('SELECT sid,timestamp FROM speckdata ORDER BY sid DESC LIMIT 1;')
    count = cursor.fetchone()
    qry="SELECT DISTINCT cid, nid, created, header, timestamp, csv FROM csvs WHERE cid>{} AND nid!={} ORDER BY cid ASC;".format(count[0], ands)
    cursor = db.execute(qry)
    print('count:{} qry:{}'.format(count[0], qry))
    # Now loop through the rows and create new rows in the frackbox table
    i=n=1
    cursorexi = db.cursor()
    for row in cursor:
        qry = speckqrystring(row)
        #print('i:{} cid:{}'.format(i, row[0]))
        try:
            cursorexi.execute(qry) 
        except Exception as e:
            log('ERROR', 'function:genspeckdata() e:{} row:{} qry:{}'.format(e, row, qry))
            print('count:{}'.format(count[0]))
            exit()
        # Every 5000 records, commit the updates
        if n > 50000: 
            print(qry) 
            n=0 
            #db.commit()
        n=n+1
        i=i+1
    db.commit()
    print('Created {} Speck rows'.format(i))
 
def genfrackboxdata(db, frackboxes):
    # Create the new frackbox table
    #db.execute("DROP TABLE frackboxV1data;")
    #createtableqry = frackboxtable()
    #db.execute(createtableqry)
    # Now generate the new data
    ands = ' OR nid='.join(frackboxes)
    cursor = db.execute('SELECT fid,timestamp FROM frackboxV1data ORDER BY fid DESC LIMIT 1;')
    count = cursor.fetchone()
    qry="SELECT DISTINCT cid, nid, created, header, timestamp, csv FROM csvs WHERE cid>{} AND (nid={})".format(count[0], ands)
    print(qry)
    cursor = db.execute(qry)
    # Now loop through the rows and create new rows in the frackbox table
    i=n=1
    for row in cursor:
        qry = frackboxqrystring(row)
        #print(row[0])
        try:
            db.execute(qry) 
        except Exception as e:
            log('ERROR', 'function:genfrackboxdata() e:{} row:{} qry:{}'.format(e, row, qry))
        # Every 5000 records, commit the updates
        if n > 50000: 
            print(qry) 
            n=0 
            #db.commit()
        n=n+1
        i=i+1
    db.commit()
    print('Created {} Frackbox rows'.format(i))
 

def frackboxtable():
    pass
    #return "CREATE TABLE frackboxV1data(fid INT PRIMARY KEY NOT NULL,nid INT,timestamp INT,localdate TEXT,lat REAL,lon REAL,speed REAL,alt REAL,
    #XTemp REAL,XHumid REAL,winddir TEXT,NOppb REAL,O3ppb REAL,O3no2ppb REAL,NO2ppb REAL,PIDppm REAL,PID REAL,NOwe3 INT,
    #NOae3 INT,O3we2 INT,O3ae2 INT,NO2we1 INT,NO2ae1 INT,PT INT,CPU TEXT,Disk TEXT,Load TEXT,network TEXT,ws INT,wd INT, wid_timestamp INT)"
    
def specktable():
    pass
    # timestamp,raw_particles,particle_concentration,humidity
    #return "CREATE TABLE speckdata(sid INT PRIMARY KEY NOT NULL, nid INT, timestamp INT, localdate TEXT, 
    #raw_particles INT, particle_concentration REAL, humidity INT, ws INT, wd INT, wid_timestamp INT)"

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
        wid_timestamp = None
        values=[sid, nid, timestamp, localdate, raw_particles, particle_concentration, humidity, ws, wd, wid_timestamp]
        valuesstring = json.dumps(values)
        valuesstring = valuesstring.replace('[','(')
        valuesstring = valuesstring.replace(']',');')
        return 'INSERT INTO speckdata VALUES {}'.format(valuesstring)
    except Exception as e:
        header=''
        #print('\nSpeckError nid:{} | {} | \n{}\n{}'.format(nid, e, header,csv)) 
        log('ERROR', 'function:speckqrystring() nid:{} e:{} header:{} csv:{}'.format(nid, e, header,csv))

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
        wid_timestamp = None
        ws = None
        wd = compass(winddir)
        values=[fid,nid,timestamp,gmtdate,lat,lon,speed,alt,XTemp,XHumid,winddir,NOppb,O3ppb,O3no2ppb,NO2ppb,
                PIDppm,PID,NOwe3,NOae3,O3we2,O3ae2,NO2we1,NO2ae1,PT,CPU,Disk,Load,network,ws,wd,wid_timestamp]
        valuesstring = json.dumps(values)
        valuesstring = valuesstring.replace('[','(')
        valuesstring = valuesstring.replace(']',');')
        return 'INSERT INTO frackboxV1data VALUES {}'.format(valuesstring)
    except Exception as e:
        header='fid,nid,timestamp,gmtdate,lat,lon,speed,alt,XTemp,XHumid,winddir,NOppb,O3ppb,O3no2ppb,NO2ppb,PIDppm,PID,NOwe3,NOae3,O3we2,O3ae2,NO2we1,NO2ae1,PT,CPU,Disk,Load,network,ws,wd,wid_timestamp'
        #print('\nError nid:{} | {} | \n{}\n{}'.format(nid, e, header,csv))
        log('ERROR', 'function:frackboxqrystring() nid:{} e:{} header:{} csv:{}'.format(nid, e, header,csv))  

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


def log(level, msg):
    if debug==True: print(msg)
    if level=='ERROR': 
        logger.error(msg)


# Run the script
run()
