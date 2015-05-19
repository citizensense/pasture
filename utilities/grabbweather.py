#!/bin/python3
import time, sqlite3, json, string, os.path, calendar
import urllib.request as ur
from datetime import datetime

# Create the DB connection
db = sqlite3.connect('db.sqlite3')
newweatherdata = []
debug = False

def run():
    log('--------------------------------------------')
    # Create the new frackbox table in the DB
    createweathertable()
    # Now loop through the speck data and add weather info
    table = 'speckdata'
    primaryid = 'sid'
    qry =  'SELECT DISTINCT {0}.sid, nodes.title, {0}.timestamp, {0}.localdate, nodes.lat, nodes.lon, {0}.wid_timestamp '.format(table)
    qry += 'FROM {} '.format(table)
    qry += 'JOIN nodes ON {}.nid=nodes.nid '.format(table)
    qry += 'WHERE wid_timestamp is null '
    # Now loop through the speck data and add weather info
    loopthroughdata(table, primaryid, qry)
    # Now loop through the frackbox data and add weather info
    table = 'frackboxV1data'
    primaryid = 'fid'
    qry =  'SELECT DISTINCT {0}.fid, nodes.title, {0}.timestamp, {0}.localdate, nodes.lat, nodes.lon, {0}.wid_timestamp '.format(table)
    qry += 'FROM {} '.format(table)
    qry += 'JOIN nodes ON {}.nid=nodes.nid '.format(table)
    qry += 'WHERE wid_timestamp is null '
    loopthroughdata(table, primaryid, qry)

def loopthroughdata(table, primaryid, qry):
    cursor = db.execute(qry)
    cursor2 = db.cursor()
    i = 0
    n = 0
    for row in cursor:
        theid = row[0]
        title = row[1]
        timestamp = row[2]
        localdate = row[3]
        wid_timestampA = row[6]
        lat = row[4]    
        lon = row[5]    
        op = 'i:{} {}:{} title:{} wid_timestamp=:{} timestamp:{} localdate:{} lat:{} lon:{}'
        out = op.format(i, primaryid, theid, title, wid_timestampA, timestamp, localdate, lat, lon)
        # Save weather data for this row
        if timestamp < 1402152570: # if its a date before june 2014 then set a default
            wid_timestamp = 1
        else:
            wid_timestamp = grabweather(timestamp, lat, lon, out)
        qry = 'UPDATE {2} SET wid_timestamp={0} WHERE {3}={1}'
        if wid_timestamp != False:
            cursor2.execute(qry.format(wid_timestamp, theid, table, primaryid))
        else:
            # try once more
            wid_timestamp = grabweather(timestamp, lat, lon, out)
            if wid_timestamp != False:
                cursor2.execute(qry.format(wid_timestamp, theid, table, primaryid))
        # Provide a bit of progress output so we know whats happening
        i=i+1
        n=n+1
        if n>1000:
            print(out)
            db.commit()
            n=0
            time.sleep(0.25)
    log('DONE:{} rows'.format(i))

def grabweather(timestamp, lat, lon, row):
    utc = timestamptostring(timestamp, "%Y %m %d %H %M %S").split(' ') ##YYYY MM DD
    year = utc[0]   
    month = utc[1]   
    day = utc[2]    
    hour = utc[3]   
    minute = utc[4] 
    url = 'http://api.wunderground.com/api/cdf731cff4f0922a/history_{}{}{}/geolookup/q/{},{}.json'
    geturl = url.format(year, month, day, lat, lon)
    filename = '{}-{}-{}|{},{}.json'.format(year, month, day, lat, lon)
    filepath = 'weather/'+filename
    log(geturl)
    # Check if we have decent data in the database: search for timestamp within an hour of the data
    weather = searchweatherdb(timestamp)
    log('---')
    if str(weather) != 'None':
        wid_timestamp = weather[0]
        # Work out the time difference and if its greater than 30mins then a new search needs to be performed
        timedif = (wid_timestamp-timestamp)/60
        if timedif < 0: timedif = timedif*-1
        log('wid_timestamp:{} row_timestamp:{} difInMins:{}'.format(wid_timestamp, timestamp, timedif))
        if timedif > 201 : 
            print('This aint good enough: {} | {}'.format(timedif, row))
            #pass
        else:
            return wid_timestamp
    # Ok, so not weather in the DB so check if we need to download .json file
    if os.path.isfile(filepath) ==  False:
        jsonfile = ur.URLopener()
        jsonfile.retrieve(geturl, filepath)
        print('Download:{}'.format(geturl))
        time.sleep(3.1)
    # Now extract the data from the JSON file
    jsontxt = open(filepath).read()
    jsonobj = json.loads(jsontxt)
    extractweather(jsonobj)
    # And save it in the database
    saveweathertodb()
    log('--------------------------------------------')
    return False

def saveweathertodb():
    cursor = db.cursor()
    qry = 'INSERT INTO weatherunderground(wid_timestamp, utcdate, tempi, hum, wspdi, wdird, visi, precipi) VALUES(?,?,?,?,?,?,?,?)'
    #print(newweatherdata)
    for ob in newweatherdata:
        #print('{} {}'.format(ob[0], ob[1]))
        try:
            cursor.execute(qry, ob)
        except Exception as e:
            pass
            #print('{}={}'.format(e, ob))
    #cursor.executemany(qry, newweatherdata)
    db.commit()

def searchweatherdb(findtimestamp):
    # Check if we have the data in the database: search for timestamp within an hour of the data
    qry =  "SELECT * FROM weatherunderground "
    qry += "ORDER BY ABS({} - wid_timestamp) LIMIT 1".format(findtimestamp)
    cursor = db.execute(qry)
    weather = cursor.fetchone()
    log("WeatherSearch:{}".format(weather))
    return weather

def extractweather(jsonobj):
    for ob in jsonobj['history']['observations']:
        utcdate = ob['utcdate']['pretty']
        ampm = utcdate.split(' ')[1]
        year = ob['utcdate']['year']
        month = ob['utcdate']['mon']
        day = ob['utcdate']['mday']
        hour = ob['utcdate']['hour']
        minute = ob['utcdate']['min']
        tempi = ob['tempi']     # Temp in F
        hum = ob['hum']         # Humidity %
        wspdi = ob['wspdi']     # Windspeed in mph
        wdird = ob['wdird']     # Wind direction in degrees
        visi = ob['visi']       # Visability in Miles
        precipi = ob['precipi'] # Precipitation in inches
        utcdatestr = "{}/{}/{} {}:{}".format(year, month, day, hour, minute)
        wid_timestamp = calendar.timegm(time.strptime(utcdatestr, '%Y/%m/%d %H:%M')) 
        op = 'Date:{} Datestr:{} timestamp:{} Tempi:{} Hum:{} Wspdi:{} Wdird:{} Visi:{} Precipi:{}'
        #print(op.format(utcdate, utcdatestr+'GMT', wid_timestamp, tempi, hum, wspdi, wdird, visi, precipi))
        newweatherdata.append((wid_timestamp, utcdatestr+' (-0 GMT)', tempi, hum, wspdi, wdird, visi, precipi))

def createweathertable():
    # First check if it already exists
    tablename = 'weatherunderground'
    qry = "SELECT * FROM sqlite_master WHERE type='table' AND name='{}';".format(tablename)
    cursor = db.execute(qry)
    table = str(cursor.fetchone())
    # Table doesn't exist so lets create it
    if table == 'None':
        qry = "CREATE TABLE {}(wid_timestamp INT PRIMARY KEY NOT NULL, utcdate TEXT, tempi REAL, hum INT, wspdi REAL, wdird INT, visi REAL, precipi REAL); ".format(tablename)
        db.execute(qry)
        log("CREATED NEW DB TABLE:{}".format(tablename))
        # and insert a default value used when we dont have weather data
        qry = 'INSERT INTO weatherunderground (wid_timestamp, utcdate, tempi, hum, wspdi, wdird, visi, precipi) VALUES (1,'', -999.9, -1, -999.9, 0, -999.9, -999.9);'
        db.execute(qry)

# timestamptostring(1234567, "%Y-%m-%d %H:%M:%S") 
def timestamptostring(timestamp, myformat):
    # GMT without BST or DST conversion
    date = datetime.utcfromtimestamp(timestamp)
    # Return with the specified format
    return date.strftime(myformat)

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

def log(msg):
    if debug==True: print(msg)

# Run the script
run()
