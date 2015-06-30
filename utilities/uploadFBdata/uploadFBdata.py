#!/usr/bin/python3
#############################################################################
# Application used to Asynchronously:                               #
#   1. Grab sensor data 
#   2. Save to local csv file                                               #
#   3. Send to server                                                       #
#############################################################################
# Include the 'libraries folder' in the system path
import sys, os, time, logging, threading, subprocess, urllib
from collections import OrderedDict
path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(path, 'libraries') ) 
import config
from datetime import datetime
from PostData import *
from database import *

# The application class
class GrabSensors:
    
    # Initialise the object
    def __init__(self):
        # vars to keep track of the health of the system
        self.counter = 0
        self.timepassed = 0
        self.healthcheck = {}
        self.failedposts = 0
        self.postlimit = 2
        # Load the config for this device
        self.log('INFO', 'Attempt to load the config')
        self.CONFIG = config.init()
        # Load some vars from the commandline
        self.grabargs()
        # Setup logging
        logging.basicConfig(filename='/home/csk/csk/csk.log', level=logging.DEBUG)
        self.log('INFO', 'Started script')
        # Setup means to save and post data to the server
        dbstruct = self.dbstructure()
        db = Database(self.CONFIG['dbfile'], dbstruct)
        self.log('INFO', db.printmsg() )  
        self.dblock = threading.Lock()
        # Build a new database if need be
        db.build()
        self.log('INFO', db.printmsg())  
        # A class to help us post data
        self.poster = PostData()
        # Setup some base variables
        self.lock = threading.Lock()
        self.datapath = os.path.join(os.path.dirname(__file__), 'data/data.csv')
        self.datamodel = OrderedDict([
            ('lat',             ['USB-ND1000S',     []  ]),
            ('lon',             ['ND1000S-LON',     []  ]),
            ('speed',           ['ND1000S-SPEED',   []  ]),
            ('alt',             ['ND1000S-ALT',     []  ]),
            ("XTemp",         ['',    []  ]),
            ("XHumid",        ['',    []  ]),
            ('winddir',         ['SPI-8ADC--MCP3008-WindDirection',         []  ]),
            ('NOppb',          ['',    []  ]),
            ('O3ppb',           ['',    []  ]),
            ('O3no2ppb',           ['',    []  ]),
            ('NO2ppb',          ['',    []  ]),
            ('PIDppm',           ['',    []  ]),
            ('PID',             ['A1->16ADC->I2C',  []  ]),
            ('NOwe3',          ['A2->16ADC->I2C',  []  ]),
            ('NOae3',          ['A3->16ADC->I2C',  []  ]),
            ('O3we2',           ['A4->16ADC->I2C',  []  ]),
            ('O3ae2',           ['A5->16ADC->I2C',  []  ]),
            ('NO2we1',          ['A6->16ADC->I2C',  []  ]),
            ('NO2ae1',          ['A7->16ADC->I2C',  []  ]),
            ('PT+',             ['A8->16ADC->I2C',  []  ]),
            ('CPU',             ['RPi-TempC',       []  ]),
            ('Disk',            ['RPi-diskAvail',   []  ]),
            ('Load',            ['Rpi-CPU Load Ave',[]  ]),
            ('network',         ['HuaweiAvailable', []  ])
        ])
        # Place to store asychronosly generated values
        self.csvbuffer = OrderedDict([])
        # Initialise a list of threads so data can be aquired asynchronosly
        threads = []
        threads.append(threading.Thread(target=self.postdata) )         # Post data to server
        for item in threads:
            item.start()
    
    # Grab variables from the commandline
    def grabargs(self):
        # Check this script is running as root
        euid = os.geteuid()
        msg = '$ sudo uploadFBdata.py 000000003068b18fss data/db.sqlite'
        if euid != 0:
            print('Please run this command as root: \n'+msg)
            exit()
        # Grab the DB name and nid from the commandline
        if len(sys.argv) <= 2:
            print('Specify a Frackbox serial number and database to upload from: \n'+msg)
            exit()
        serial = sys.argv[1]
        database = sys.argv[2]
        print('Upload data from:{} With serial:{}'.format(database, serial))
        exit()

    # The database model to save data in
    def dbstructure(self):
        # The database model
        dbstruct = OrderedDict([
            # A place to store csvs
            ('csvs', [
                ('cid', 'INTEGER PRIMARY KEY'),
                ('timestamp', 'INTEGER'),
                ('csv', 'TEXT'),
                ('uploaded', 'INTEGER') # 0=notuploaded 1=uploaded
            ])
        ])
        return dbstruct
    
    # Counter to keep track of how much time has passed
    def timepassing(self):
        while True:
            self.counter = self.counter+1
            time.sleep(1)
   
    # Periodically attempt to post saved data to the server
    def postdata(self):
        # Prep a 'failed posts' counter
        self.failedposts = 0
        self.timeout = 60*60  # 1 hour
        self.postlimit = 2
        # Initialise a database connection
        dbstruct = self.dbstructure()
        print('DB File:{}'.format(self.CONFIG['dbfile']))
        db = Database(self.CONFIG['dbfile'], dbstruct)
        self.log('WARN', 'POST DB INIT MSG: {}'.format(db.msg))
        # Now send some data to a locally installed version of frackbox
        url = self.CONFIG['posturl']
        # Generate an array of key names
        keys = ["timestamp","humandate"]
        for key in self.datamodel: keys.append(key)
        keys = json.dumps(keys)
        # Now periodically upload the data
        while True:
            # All is ok
            failed = False
            # Grab data to upload 
            qry = 'SELECT cid, csv FROM csvs WHERE uploaded = 0 LIMIT {}'.format(self.postlimit)
            rows = db.query(qry)
            self.log('WARN', 'DB for POST: {}'.format(qry))
            values = []
            cids = []
            # Prep for upload
            if rows is not False:
                for row in rows:
                    cids.append(row[0])
                    values.append(row[1])
            else:
                self.log('WARN', 'DB Error. rows = {}'.format(str(rows) ))
                #db = Database(self.CONFIG['dbfile'], dbstruct) 
                failed = True
            # If we have data to post, then attempt to post it!
            if len(cids) > 0 and failed is not True:
                jsonvalues = json.dumps(values)
                data = {
                    'serial':self.CONFIG['serial'],
                    'name':self.CONFIG['name'], 
                    'MAC':self.CONFIG['MAC'],
                    'jsonkeys': keys, 
                    'jsonvalues': jsonvalues
                }
                try:
                    poster = PostData()
                    resp = poster.send(url, data)
                    self.log('WARN', 'POSTer.msg: '+poster.msg )
                    self.log('WARN', 'POSTer resp: '+str(resp) )  
                except Exception as e:
                    resp = False
                    self.log('WARN', 'POST Error ')
                # Do we have a respose to read
                if resp is not False:
                    self.failedposts = 0
                    self.timepassed = 0
                    # We have posted data, but have errors from the server
                    if len(resp['errors']) > 0: 
                        self.log('WARN', 'POST ERRORS:'+str(resp['errors']) )
                    # All is fine
                    else:
                        # Update database as we have successfully uploaded all data
                        self.log('DEBUG', 'Sucessfully uploaded')
                        where = 'cid='+' OR cid='.join(map(str, cids))
                        qry = "UPDATE csvs SET uploaded=1 WHERE {}".format(where)
                        rows = db.query(qry)
                        #print(db.msg)
                        self.log('WARN', 'POST sucess DB: '+str(db.msg) ) 
                else:
                    failed = True
            # Start a counter if we have failed to upload
            if failed is True:
                # start a time to see how long we havent posted for
                if self.failedposts == 0: timerstart = self.counter 
                # Looks like we have a failed post
                self.failedposts = self.failedposts+1
                # If 1 hour has passed then restart
                if self.timepassed >= self.timeout:
                    self.log('WARN', 'NO NETWORK CONNECTION REBOOT: '+str(self.timeout))
                    subprocess.check_output("reboot", shell=True).decode("utf-8")
                self.log('WARN', 'UNABLE TO POST DATA [FailedPosts: {} timepassed: {} counter: {} postlimit: {}]'.format(self.failedposts, self.timepassed, self.counter, self.postlimit))
                self.postlimit = 2 
            else:
                 self.postlimit = self.postlimit*2
            # And round again!
            if self.postlimit >= 500: self.postlimit = 500
            if self.postlimit <= 2: self.postlimit = 2
            time.sleep(0.2)

   
    # Used for application debugging
    def log(self, level, msg):
        datetime = time.strftime('%d/%m/%Y %H:%M:%S')
        msg = datetime+' '+msg
        if level == 'DEBUG':
            # Print to log  
            logging.debug(msg)
        elif level == 'INFO':
            # Print to log 
            logging.info(msg)
        elif level == 'WARN':
            # Print to log and console  
            logging.warning(msg)
   
# Start grabbing sensors
GrabSensors()

