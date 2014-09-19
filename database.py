#!/usr/bin/python3
import os, sqlite3, json, time
# Got some great tips from:
# http://www.pythoncentral.io/introduction-to-sqlite-in-python/

# Class to manage all database operations
class Database:

    def __init__(self, dbfile):
        self.dbfile = dbfile

    # Build the db and create the structure if it doesn't exist
    def build(self, dbstruct, ignore='locals'):
        try:
            self.msg = '\n====--database init--()====='
            self.connect()
            cursor = self.db.cursor()
            # lets loop through our structure 
            for tablename in dbstruct:
                # Check we should be building this table
                if ignore != tablename:
                    # Check if our table exists
                    qry = "SELECT * FROM sqlite_master WHERE type='table' AND name='{}';".format(tablename)
                    self.msg += '\n'+qry
                    cursor.execute(qry)
                    table = str(cursor.fetchone())
                    # It doesn't seem to exist so lets create it
                    if table == 'None':
                        fieldlist = s = ''
                        for i, v in dbstruct[tablename]:
                            if fieldlist != '': s = ',\n'
                            fieldlist += '{}{} {}'.format(s, i, v)
                        qry = 'CREATE TABLE {0} ({1})'.format(tablename, fieldlist)
                        self.msg += '\n'+qry
                        cursor.execute(qry)
            self.db.commit()
        except Exception as e:
            self.msg += str(e) 
        return None
    
    # Connect and create a new database connection
    def connect(self):
        self.db = sqlite3.connect(self.dbfile)
    
    # Close the dbconnection
    def close(self):
        self.db.close()

    # Create a new record when presented with a list of tablenames, fieldnames and values
    def create(self, tablename, data):
        try:
            self.msg ="\n====database create()===="
            # Create a cursor
            cursor = self.db.cursor()
            # Prep the vars
            fieldnames = ','.join(data['fieldnames'])
            q = ','.join(['?']*len(data['fieldnames']))
            qry = 'INSERT INTO {0}({1}) VALUES({2}) '.format(tablename, fieldnames, q)
            cursor.executemany(qry, data['values'])
            fid = cursor.lastrowid  
            self.db.commit()
            return True
        except Exception as e:
            self.msg = str(e) 
            return False
    
    # Return a json formated list of a select query
    def readasjson(self, table, fields, nodelist=[]):
        self.msg = '=========database readasjson()======'
        try:
            cursor = self.db.cursor() 
            fieldstr = ','.join(fields)
            if len(nodelist) != 0:
                qry = 'WHERE'
            qry = 'SELECT {0} FROM {1}'.format(fieldstr, table)
            self.msg += '\n'+qry 
            cursor.execute(qry)
            arr = [] 
            for row in cursor:
                arr.append({})
                n = len(arr)-1
                i = 0
                for val in row:
                    key = fields[i]
                    arr[n][key] = val
                    i += 1
            return json.dumps(arr)
        except Exception as e:
            self.msg += str(e)
            return False

    # Return a json formated list of a select query
    def readasjson2(self, table, fields, nodelist=[]):
        self.msg = '=========database readasjson()======'
        try:
            cursor = self.db.cursor() 
            fieldstr = ','.join(fields)
            if len(nodelist) != 0:
                qry = 'WHERE'
            qry = 'SELECT {0} FROM {1}'.format(fieldstr, table)
            self.msg += '\n'+qry 
            cursor.execute(qry)
            arr = [] 
            for row in cursor:
                arr.append({})
                n = len(arr)-1
                i = 0
                for val in row:
                    key = fields[i]
                    arr[n][key] = val
                    i += 1
            return json.dumps(arr)
        except Exception as e:
            self.msg += str(e)
            return False

# Example showing how to to use this class
# Used for unit tests
if __name__ == "__main__":
    # Setup elements for  example
    import random, time
    from pprint import pprint
    from collections import OrderedDict   
    # Our database structure as an ordered list
    dbstruct = OrderedDict([
        ('nodes', [
            ('nid', 'INTEGER PRIMARY KEY'),
            ('apikey', 'TEXT unique'),                
            ('created', 'INTEGER'),
            ('createdhuman', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ('updated', 'INTEGER'),
            ('title', 'TEXT'),
            ('csvfile','TEXT'),
            ('deviceid', 'TEXT'),
            ('datatype','TEXT'),
            ('lat','REAL'),
            ('lon','REAL'),
            ('fuzzylatlon', 'TEXT'),
            ('tags','TEXT'),
            ('createdby','INTEGER'),
            ('submissiondata','TEXT'),
            ('latest','TEXT'),
            ('visible','INTEGER'),
        ]),
        # This isn't created in the database, its just used for internal var storage
        ('locals',{
            'path':[],
            'postedbody':'',
            'filestosave':[],
            'submitted':{},
            'errors':{},
            'success':{},
            'altresponse':''
        })
    ])
    # Initialise the database
    db = Database("data/db.sqlite3")
    db.build(dbstruct, ignore='locals')
    if db == None: print(db.msg) 
    # Create a list of random nodes to insert
    newnodes = OrderedDict([
        ('fieldnames',[]),
        ('values',[])  
    ]) 
    # Generate the fieldnames
    for fieldname,v in dbstruct['nodes']:
        if fieldname != 'nid' and fieldname != 'createdhuman':
            newnodes['fieldnames'].append(fieldname)
    # Gen a list of values so we can create multiple nodes with the above fieldnames
    nodes = 200
    while nodes >= 0:
        newVals = []
        for i,v in dbstruct['nodes']:
            if i != 'nid' and i != 'createdhuman':
                if v == 'TEXT unique': val = i+str(random.randint(1,5000000000))   
                if v == 'TEXT': val = i+str(random.randint(1,50000))  
                if v == 'INTEGER': val = random.randint(1,50000)
                # 51.47501,-0.03608
                if v == 'REAL': val = float("{0:.5f}".format(random.uniform(51.47000, 51.48000)))
                if i == 'created': val = int(time.time())
                if i == 'datatype': val = "speck"
                if i == 'latest': val = "{'raw':"+str(random.randint(1,500))+", 'concentration':"+str(random.randint(1,50000))+", 'humidity':"+str(random.randint(1,50000))+"}"
                if i == 'lat': val = float("{0:.5f}".format(random.uniform(51.44000, 51.49000))) 
                if i == 'lon': val = float("{0:.5f}".format(random.uniform(-0.03000, -0.09999)))
                newVals.append(val)
        newnodes['values'].append(newVals)
        nodes += -1
    # pprint(newnodes) # lets print a nice human readable version
    # Now create a nice new bunch of nodes
    if db.create('nodes', newnodes): print('Created '+str(nodes)+' Nodes')
    else: print(db.msg)
    # And view them all
    fields = ['nid', 'created', 'createdhuman', 
              'apikey', 'updated', 'title', 'datatype', 'lat', 'lon', 'fuzzylatlon', 'latest'
    ]
    jsondisplay = db.readasjson('nodes', fields)
    if jsondisplay: print("===Returned JSON===\n"+jsondisplay)
    else: print('Failed to fetch display')


