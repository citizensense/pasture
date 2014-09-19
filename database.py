#!/usr/bin/python3
import os, sqlite3, json, time
# Got some great tips from:
# http://www.pythoncentral.io/introduction-to-sqlite-in-python/

# Class to manage all database operations
class Database:

    # Initialise the db and create the structrure if it doesn't exist
    def __init__(self, dbfile, dbstruct):
        try:
            self.db = sqlite3.connect(dbfile)
            # Get a cursor object
            cursor = self.db.cursor()
            # lets loop through our structure 
            for tablename in dbstruct:
                # Check if our table exists
                cursor.execute('''
                    SELECT * FROM sqlite_master WHERE type='table' 
                    AND name='{}';
                '''.format(tablename))
                table = str(cursor.fetchone())
                # It doesn't seem to exist so lets create it
                if table == 'None':
                    fieldlist = s = ''
                    for i, v in dbstruct[tablename]:
                        if fieldlist != '': s = ',\n'
                        fieldlist += '{}{} {}'.format(s, i, v)
                    cursor.execute('CREATE TABLE {0} ({1})'.format(tablename, fieldlist))
            self.db.commit()
        except:
            return None
            
    # Create a new record when presented with a list of tablenames, fieldnames and values
    def create(self, tablename, data):
        try:
            fieldnames = ','.join(data['fieldnames'])
            q = ','.join(['?']*len(data['fieldnames']))
            qry = 'INSERT INTO {0}({1}) VALUES({2}) '.format(tablename, fieldnames, q)
            cursor = self.db.cursor()  
            cursor.executemany(qry, data['values'])
            fid = cursor.lastrowid  
            self.db.commit()
            return True
        except:
            return False
    
    # Return a json formated list of a select query
    def readasjson(self, table, fields, nodelist=[]):
        try:
            cursor = self.db.cursor() 
            fieldstr = ','.join(fields)
            if len(nodelist) != 0:
                qry = 'WHERE'
            qry = 'SELECT {0} FROM {1}'.format(fieldstr, table)
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
        except:
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
    db = Database("db.sqlite3", dbstruct)
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
    nodes = 20
    while nodes >= 0:
        newVals = []
        for i,v in dbstruct['nodes']:
            if i != 'nid' and i != 'createdhuman':
                if v == 'TEXT unique': val = i+str(random.randint(1,5000000000))   
                if v == 'TEXT': val = i+str(random.randint(1,50000))  
                if v == 'INTEGER': val = random.randint(1,50000)
                if v == 'REAL': val = float("{0:.5f}".format(random.uniform(51.47000, 51.48000)))
                if i == 'created': val = int(time.time())
                newVals.append(val)
        newnodes['values'].append(newVals)
        nodes += -1
    # pprint(newnodes) # lets print a nice human readable version
    # Now create a nice new bunch of nodes
    if db.create('nodes', newnodes): print('Created '+str(nodes)+' Nodes')
    else: print('failed to created nodes')
    # And view them all
    fields = ['nid', 'created', 'createdhuman', 
              'apikey', 'updated', 'title', 'datatype', 'lat', 'lon', 'fuzzylatlon'
    ]
    jsondisplay = db.readasjson('nodes', fields)
    if jsondisplay: print("===Returned JSON===\n"+jsondisplay)
    else: print('Failed to fetch display')


