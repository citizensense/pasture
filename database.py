#!/usr/bin/python3
import os, sqlite3, json, time
# Got some great tips from:
# http://www.pythoncentral.io/introduction-to-sqlite-in-python/

# Class to manage all database operations
class Database:

    # Create a new database connection _
    def __init__(self, dbfile, dbstruct, ignore='locals'):
        self.msg = '\n=======__init--() ==='    
        try:
            self.dbfile = dbfile
            self.dbstruct = dbstruct
            self.db = sqlite3.connect(self.dbfile) 
            self.ignore = ignore
            self.msg += '\nStarted DB'    
            self.keys = {}
            for table in self.dbstruct:
                if table != ignore:
                    self.keys[table] = {}
                    for key, datatype in self.dbstruct[table]:
                        self.keys[table][key] = datatype
        except Exception as e:
            self.msg += '\n'+str(e)   
    
    def printmsg(self):
        rmsg = self.msg
        self.msg= ''
        return rmsg

    # Build the db and create the structure if it doesn't exist
    def build(self):
        self.msg = '\n====--database build()====='  
        try:
            cursor = self.db.cursor()
            # lets loop through our structure 
            for tablename in self.dbstruct:
                # Check we should be building this table
                if self.ignore != tablename:
                    # Check if our table exists
                    qry = "SELECT * FROM sqlite_master WHERE type='table' AND name='{}';".format(tablename)
                    self.msg += '\n'+qry
                    cursor.execute(qry)
                    table = str(cursor.fetchone())
                    # It doesn't seem to exist so lets create it
                    if table == 'None':
                        fieldlist = s = ''
                        for i, v in self.dbstruct[tablename]:
                            if fieldlist != '': s = ','
                            fieldlist += '{}{} {}'.format(s, i, v)
                        qry = 'CREATE TABLE {0} ({1})'.format(tablename, fieldlist)
                        self.msg += '\n'+qry
                        cursor.execute(qry)
                        self.msg += '\n'+qry  
                        self.msg += '\nBuilt a new database\n'
                    else:
                        self.msg += '\nFound a table/database so didn\'t recreate it\n'   
            self.db.commit()
            return True
        except Exception as e:
            self.msg += '\n'+str(e) 
            return False
    
    # Close the dbconnection
    def close(self):
        self.db.close()

    # Create a new set of records when presented with a list of tablenames, fieldnames and values
    def create(self, tablename, data):
        self.msg ="\n====database create() (creates new records)===="
        try:
            # Create a cursor
            cursor = self.db.cursor()
            # And a list of fieldname
            fieldnames = ','.join(data['fieldnames']) 
            q = ','.join(['?']*len(data['fieldnames'])) 
            # Prep the vars for inserting many nodes at a time
            if len(data['values']) > 1:
                qry = 'INSERT INTO {0}({1}) VALUES({2}) '.format(tablename, fieldnames, q)
                self.msg +="\nMultiplenodes:\n"+qry 
                cursor.executemany(qry, data['values'])
                myid = None
            # Prep the vars for inserting a single record
            else:
                qry = 'INSERT INTO {}({}) VALUES({})'.format(tablename, fieldnames,q)
                self.msg +="\nSinglnode:\n"+qry 
                cursor.execute(qry, (data['values'][0]))
                myid = cursor.lastrowid
            self.db.commit()
            return myid
        except Exception as e:
            # TODO: Return the error message, not just false..
            self.msg += '\n'+str(e) 
            return False
    
    # Return a json formated list of a select query
    def readasjson(self, table, fields, nodelist=[], qry=''):
            self.msg = '\n=========database readasjson()======'
        #try:
            cursor = self.db.cursor() 
            fieldstr = ','.join(fields)
            where = ''
            # If we have nodes, then attempt to convert the string to an int
            # This has the effect of failing if the there is a code insertion event
            if len(nodelist) != 0:
                where = 'WHERE nid IN ('+','.join(map(str, map(int, nodelist)))+')'
            qry = 'SELECT {0} FROM {1} {2} {3}'.format(fieldstr, table, where, qry)
            self.msg += '\n'+qry 
            cursor.execute(qry)
            arr = [] 
            for row in cursor:
                arr.append({})
                n = len(arr)-1
                i = 0
                for val in row:
                    key = fields[i]
                    if self.keys[table][key] == 'JSON': 
                        try:
                            val = json.loads(val)
                        except Exception as e:
                            val = json.loads('{}')
                    arr[n][key] = val
                    i += 1
            return json.dumps(arr)
        #except Exception as e:
            self.msg += '\n'+str(e)
            return False
    
    # Update
    def update(self, table, idname, idval, fieldnvalues):
        self.msg ="\n====database update() ===="
        try:
            # Create a cursor
            cursor = self.db.cursor()
            # Prep the vars
            fieldnames = []
            values = []
            for key in fieldnvalues:
                fieldnames.append(key+'=?')  
                values.append(fieldnvalues[key])
            values.append(idval) 
            setqry = ','.join(fieldnames)
            qry = 'UPDATE {0} SET {2} WHERE {1}=?'.format(table, idname, setqry)
            self.msg +="\n"+qry 
            cursor.execute(qry, values)  
            self.db.commit()
            self.msg +="\n"+str(fieldnvalues)   
            self.msg +="\n"+str(values)
            self.msg +="\nSuccess!" 
            return True
        except Exception as e:
            self.msg += '\n'+str(e) 
            return False
 
    # Search for a value and return the spec
    # TODO: Clean up this to return one or many
    def searchfor(self, intable, returnfields, searchfor, sql='', returnrows='one'):
        self.msg = '\n=========database searchfor()======'
        self.msg += '\n'+str(searchfor)
        try:
            cursor = self.db.cursor() 
            fields = ','.join(returnfields)
            search = ''
            sp = ''
            values = []
            for key in searchfor:
                search += sp+key+'=?'
                values.append(searchfor[key])
                sp = ' AND '
            qry = 'SELECT {0} FROM {1} WHERE {2}'.format(fields, intable, search)
            qry += ' '+sql
            # Make thu query human readable for debugging
            self.msg += '\n'+qry
            cursor.execute(qry, (values) )
            if returnrows == 'one':
                row = cursor.fetchone()  
                return row
            else:
                rows = []
                for row in cursor:
                    rows.append(row)
                return rows
        except Exception as e:
            self.msg += '\n'+str(e)
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
            ('description', 'TEXT'),
            ('datatype','TEXT'),
            ('lat','REAL'),
            ('lon','REAL'),
            ('fuzzylatlon', 'TEXT'),
            ('tags','TEXT'),
            ('createdby','INTEGER'),
            ('submissiondata','JSON'),
            ('latest','JSON'),
            ('visible','INTEGER'),
        ]),
        # This isn't created in the database, its just used for internal var storage so order doen't matter
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
    db = Database("data/db.sqlite3", dbstruct, ignore='locals')
    print(db.printmsg())  

    # BUILD A NEW DATABASE
    db.build()
    print(db.printmsg())  

    # CREATE LIST OF NODES TO INSERT
    newnodes = OrderedDict([
        ('fieldnames',[]),
        ('values',[])  
    ]) 
    # Generate the fieldnames
    for fieldname,v in dbstruct['nodes']:
        if fieldname != 'nid' and fieldname != 'createdhuman':
            newnodes['fieldnames'].append(fieldname)
    # And the node values
    nodes = 1
    nodecnt = nodes
    while nodes >= 1:
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
                if i == 'latest': val = json.dumps({"raw":random.randint(1,500), "concentration":random.randint(1,50000), "humidity":random.randint(1,50000) })
                if i == 'lat': val = float("{0:.5f}".format(random.uniform(51.44000, 51.49000))) 
                if i == 'lon': val = float("{0:.5f}".format(random.uniform(-0.03000, -0.09999)))
                newVals.append(val)
        newnodes['values'].append(newVals)
        nodes += -1
    # Now create a nice new bunch of nodes
    nids = db.create('nodes', newnodes)
    print(db.msg)  
    print(nids)

    # VIEW ALL NODES IN THE DATBASE
    fields = ['nid', 'created', 'createdhuman', 'updated', 'title', 'datatype', 'lat', 'lon', 'fuzzylatlon', 'latest']
    jsonstr = db.readasjson('nodes', fields)
    print(db.msg)
    if jsonstr: print('ALL NODES: json response:\n'+jsonstr) 

    # VIEW A SINGLE NODE
    jsonstr = db.readasjson('nodes', fields, [1])  
    print(db.msg)
    if jsonstr: print('SINGLE NODES: json response:\n'+jsonstr)                     
      
    # SEARCH FOR A VALUE AND SEE IF IT EXISTS. Return a row of fields if its exists
    searchfor = {'nid':2, 'datatype':'speck'}
    intable = 'nodes'
    returnfields = ['nid', 'createdby']
    row = db.searchfor(intable, returnfields, searchfor)
    print(db.msg) 
    print(row)
  
    # SEARCH FOR ANOTHER VALUE AND SEE IF IT EXISTS. Return a row of fields if its exists
    searchfor = {'nid':2, 'datatype':'bob'}
    intable = 'nodes'
    returnfields = ['nid', 'createdby']
    row = db.searchfor(intable, returnfields, searchfor)
    print(db.msg) 
    print(row)

    # UPDATE NODE WHERE
    table = 'nodes'
    idname = 'nid'
    idval= 1
    fieldnvalues = {'title':'Changed!!', 'apikey':'changed'}
    db.update(table, idname, idval, fieldnvalues)  
    print(db.msg)




