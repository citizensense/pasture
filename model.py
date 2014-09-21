#!/usr/bin/python3
import cherrypy, json, csv, re, time, datetime, uuid, os, sys,string, subprocess
from collections import OrderedDict
from database import *

# TODO: Security check fid variable
# TODO: Add list of 'registered devices' to config
# TODO: Swap apikeys if new marked is created with the same one..
class Model:
    
    # Create a database object for us to use
    def __init__(self):
        dbstruct = self.database_structure()
        self.db = Database(cherrypy.config['dbfile'], dbstruct, ignore='locals')
        self.dbfields = self.db.keys

    # Return a nicely formated dict of the db fields
    def grab_dbfields(self):
        return self.dbfields

    # Construct 'raw' posted data structure where fid=UniqueDirectoryName
    def database_structure(self):
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
            # This isn't created in the database, its just used for internal var storage
            ('locals',{
                'info':{},
                'path':[],
                'body':'',
                'filestosave':[],
                'submitted':{},
                'errors':{},
                'success':{},
                'altresponse':''
            })
        ])
        return dbstruct 
    
    def grab_opensessions(self):
        return len(cherrypy.config['session'])

    # Parse the submission and determine what we need to do with it
    def parse_submission(self, data):
        # Grab the submitted data and convert it to JSON with all commas escaped to &#44;
        jsondump = json.dumps(data['submitted'])
        data['info']['submissiondata'] = jsondump.replace(',', '&#44')
        # Check what/who submitted this data, parse it, then fill in our data structure
        plugins=(UploadformSubmission, SpecGatewaySubmission, CitizenSenseKitSubmission)
        for plugin in plugins:
            obj = plugin()
            parsedoutput = obj.checksubmission(self, data)
            if parsedoutput is not False: break
        # Save the number of open sessions
        data['nsessions'] = self.grab_opensessions()
        # Prepare for json response
        if parsedoutput:
            data.pop('filestosave', None)
            data.pop('submitted', None) 
            if len(parsedoutput['errors']) < 1:
                # All looks OK
                data['success']['code'] = 'OK'
                data['success']['msg'] = 'A new node has been created' 
                # If the module has its own response then send that instead
                if data['altresponse'] is not '':
                    return data['altresponse']
        else:
            # The submission hasn't been recognised
            data.pop('filestosave', None)
            data.pop('info', None)
            data.pop("success", None)
            data['errors']['form'] = 'Post structure not recognised' 
        return json.dumps(data)
    
    # CREATE A NEW NODE
    def create_node(self, data):
        # As we are creating a single node lets create seperate field and value lists
        fieldlist = []
        valuelist = []
        for key in data['info']:
            fieldlist.append(key)
            valuelist.append(data['info'][key])
        # And construct the ordered dict ready for the database
        newnode = OrderedDict([
            ('fieldnames',fieldlist),
            ('values',[valuelist])  
        ]) 
        nid = self.db.create('nodes', newnode)
        print(self.db.msg)
        if nid == None or False: data['errors']['dbcreatenode'] = 'Database could not create node'
        else: data['info']['nid'] = nid
        return data
      
    # RETURN A LIST OF ALL NODES WITH TITLE AND GPS
    def view_all(self):
        fields = ['nid', 'lat', 'lon', 'title', 'datatype', 'latest', 'created', 'updated']
        jsondisplay = self.db.readasjson('nodes', fields)
        print(self.db.msg)
        if jsondisplay:
            return jsondisplay
        else:
            return '{}'
    
    # VIEW AN INDIVIDUAL NODE
    def view_node(self, nid):
        fields = ['nid', 'lat', 'lon', 'title', 'datatype', 'latest', 'created', 'updated'] 
        jsondisplay = self.db.readasjson('nodes', fields, [int(nid)])
        print(self.db.msg)     
        if jsondisplay: return jsondisplay
        else: return '{}'

    # UPDATE SPECIFIED FIELDS OF A NODE
    def update_node(self, nid, fieldsnvalues):
        update = self.db.update('nodes', 'nid', int(nid), fieldsnvalues)
        print(self.db.update)
        if update:
            return True
        else:
            return False

    # DELETE A NODE
    def delete_node(self, response, fid):
        if cherrypy.config['filemanager'].move_dir('data/'+fid, 'dustbin/'+fid):
            response['success']['completed'] = 'Moved to the rubbish bin'
        else:
            response['errors']['failed'] = "Failed to move to rubbish bin"
        #for item in keyvaluepairs:
        return response
    
    # MANAGE USER SESSIONS
    # TODO: Tidy up! Convolyuted at the moment
    # TODO: Cleanup old session ids
    def validuser(self, uname='', pwd='', sid=''):
        msg = "\n==== validuser() ======="
        loggedin = False
        try:
            # First check if there are old session id's that need to be deleted
            timeout = 60*60 # How many seconds to keep people logged in
            currentime = int(time.time())  
            todelete = []
            for sessiondel in cherrypy.config['session']:
                loggedinuser = cherrypy.config['session'][sessiondel]['username']
                lastused = cherrypy.config['session'][sessiondel]['lastused']
                sesslen = currentime - lastused
                msg += "\n{} last logged in {} secs ago".format(loggedinuser, sesslen)
                if sesslen >= timeout:
                    msg += "\nWhich is more than {} secs ago so it has been deleted".format(timeout)
                    todelete.append(sessiondel)
            # Delete any old sessions
            with cherrypy.config['sessionlock']:
                for i in todelete:
                    del cherrypy.config['session'][i]
            # Check if a session id has been set and no password or username
            if sid.strip() != '' and uname.strip() == '' and pwd.strip != '':
                msg += "\nA session id has been sent to us with no pass or username: \n"+sid
                # We have a sesion id so check if its available
                if sid in cherrypy.config['session']:
                    msg += "\nAnd it exists in one of the saved sessions so lets keep logged in"
                    sessionid = sid
                    uid = cherrypy.config['session'][sid]['uid']  
                    username = cherrypy.config['session'][sid]['username']  
                    permissions = cherrypy.config['session'][sid]['permissions']
                    lastused = int(time.time())
                    loggedin = True
                else:
                    msg += "\nThis session ID has not been recognised!: \n "
            # Ok, no sessionid, so lets check if a username/password has been set
            elif len(uname.strip()) > 0 and len(pwd.strip()) > 0:
                msg += "\nNo session id But recieves password + username"
                if uname not in cherrypy.config['users']:
                    msg += "\nUsername not recognised: "+uname
                else:
                    msg += "\nUsername has been recognised:"+uname
                    uid = cherrypy.config['users'][uname]['uid']
                    username = uname
                    password = cherrypy.config['users'][uname]['password']
                    permissions = cherrypy.config['users'][uname]['permissions']  
                    if pwd != password:
                        msg += "\nPassword not recognised: "+pwd
                    else:
                        msg += "\nPassword has been recognised:"+pwd
                        # All looks good so set the sessionid
                        sessionid = str(uuid.uuid1())+str(len(cherrypy.config['session']))
                        timestamp = int(time.time()) 
                        with cherrypy.config['sessionlock']:
                            cherrypy.config['session'][sessionid] = {}
                            cherrypy.config['session'][sessionid]['uid'] = uid
                            cherrypy.config['session'][sessionid]['username'] = username
                            cherrypy.config['session'][sessionid]['lastused'] = timestamp
                            cherrypy.config['session'][sessionid]['permissions'] = permissions
                        msg += "\nCreated a new session:\n uid:{} \n username:{} \n pass: {} \n id: {}".format(uid, uname, password, sessionid)
                        loggedin = True
            else:
                msg += '\n No session id, No username, No password'
            msg += '\n'+str(len(cherrypy.config['session']))+' sessions in list'
            print(msg)
            print( cherrypy.config['session'] )
            if loggedin == True:
                return {'uid':uid, 'username':username, 'sessionid':sessionid, 'permissions':permissions, 'msg':msg}
            else:
                print(msg)
                print( cherrypy.config['session'] )
                return False
        except Exception as e:
            msg += '\nError with user validation: '+str(e)
            print(msg)
            print( cherrypy.config['session'] )
            return False
        
    # MODEL UTILITIES
    #  Compare two lists and see if their contents match
    def match_keys(self, expected, provided):
        # List of field names we are expecting and specify 
        for key in provided:
            if key not in expected: 
                state = False
            else: 
                state = True
        if len(expected) is not len(provided):
            state = False
        return state
    
#==================================================================#
#==============PLUGINS TO HANDLE MULTIPLE TYPES OF DATA SUBMISSION==================#
#===================================================================================#

#========= THE MAIN UPLOAD FORM ============================================#
class UploadformSubmission:

    # [REQUIRED METHOD] Check if submission is recognised, if it is, return structured data
    def checksubmission(self, model, data):
        self.data = data
        self.model = model
        # List of field names we are expecting
        expected = ['gpstype','title', 'description', 'gps', 'apikey', 'file', 'datatype', 'username', 'password', 'sessionid']
        self.tosubmit = {
            'title':'',
            'description':'', 
            'apikey':str(uuid.uuid1()), 
            'fuzzylatlon':'',
            'created':int(time.time()),
            'updated':int(time.time()),
            'createdby':None,
            'datatype':'',
            'submissiondata':'{}'
        }
        submitted = data['submitted'].keys()
        if self.model.match_keys(expected, submitted) == False:
            return False
        # Now check if this submission has been made by a valid user
        username = data['submitted']['username']
        password = data['submitted']['password']
        sessionid = data['submitted']['sessionid']
        # Check if we are logged in and save the session id if we are
        self.user = self.model.validuser(username, password, sessionid)
        if self.user is False:
            data['errors']['user'] = 'This username/password combination has not been recognised. Or you may have been automatically logged out.'
            data['sessionid'] = '' 
            return data
        self.tosubmit['createdby'] = self.user['uid']
        self.tosubmit['username'] = self.user['username']  
        data['sessionid'] = self.user['sessionid']
        # Now format each of the variables and save in 'data'
        for key in expected:
            var = getattr(self, "format_"+key)()
        self.tosubmit['submissiondata'] = json.dumps(data['submitted'])
        self.data['info'] = self.tosubmit
        # if there are no errors, create a new node
        if len(self.data['errors']) <=0:
            newdata = self.model.create_node(self.data)
        # Return the data
        return self.data
        
    def format_gps(self):
        latlon = self.data['submitted']['gps'].split(',')
        try:
            self.tosubmit['lat'] = float(latlon[0])
            self.tosubmit['lon'] = float(latlon[1])
        except:
            return
    
    def format_gpstype(self):
        return
 
    def format_sessionid(self):
        return

    def format_username(self):
        # Set the created by field
        # self.data['info']['createdby'] = session.userid  
        # if cherrypy.config['users']['f'][0])
        return

    def format_password(self):
        return

    def format_file(self):
        # Check we have a file in the correct format
        #filename = self.data['submitted']['file']
        #  Check we can save files of this type
        #if cherrypy.config['filemanager'].fileisoneof(filename, 'csv' ) is False:
        #    return False
        # Now save the filename
        #self.data['info']['csvfile'] = filename
        # And save the file
        # TODO: Add save chunks here....
        return

    def format_title(self):
        title = self.data['submitted']['title'].strip()
        if title != '':
            self.tosubmit['title'] = self.data['submitted']['title']       
        else:
            self.data['errors']['title'] = 'Title needs to be filled in'

    def format_description(self):
        datatype = self.data['submitted']['datatype']
        description = self.data['submitted']['description']
        if datatype == 'observation' and len(description) < 1:
            self.data['errors']['description'] = 'Please fill in a description for this Observation'
        self.tosubmit['description'] = description

    def format_datatype(self):
        self.tosubmit['datatype'] = self.data['submitted']['datatype'] 

    def format_apikey(self):
        # Set some basic vars
        apikey = self.data['submitted']['apikey']  
        if apikey.strip() != '':self.tosubmit['apikey'] = apikey    
        # Does this API key already exist?
        datatype = self.data['submitted']['datatype']
        searchfor = {'apikey':apikey}
        intable = 'nodes'
        returnfields = ['nid', 'createdby', 'datatype']
        row = self.model.db.searchfor(intable, returnfields, searchfor)
        print(self.model.db.msg)
        # This key doesn't exist so go ahead and use it
        if row is None:
            if apikey.strip() != '':self.tosubmit['apikey'] = apikey
        else:
            # Check if the current user can edit the node
            if self.user['uid'] == row[1] or self.user['permissions'] == 'admin':
                print("SWAPPING KEYS")
                # The key does exist, so lets replace the old value with a new one
                newkey = str(uuid.uuid1())
                # UPDATE NODE WHERE
                table = 'nodes'
                idname = 'nid'
                idval = row[0]
                fieldnvalues = {'apikey':newkey}
                self.model.db.update(table, idname, idval, fieldnvalues)  
                print(self.model.db.msg)
            else:
                device = self.data['submitted']['datatype']
                self.data['errors']['DeviceNameClash'] = 'Someone has already created a marker with this Device name'
                self.data['errors']['action'] = 'Please contact citizensense if you would like to create a new marker using this Device Name.'   
        return
    
#================== SPEC GATEWAY APPLICATION ================================#
class SpecGatewaySubmission:
    
    # Check if submission is recognised, if it is, return structured data
    # TODO: This is looking a bit messy so tidy up & move try/except to individual calls
    def checksubmission(self, data):
        # List of field names we are expecting. Reject if they don't match
        expected = ['dev_nickname']
        submitted = data['submitted'].keys()
        if cherrypy.config['model'].match_keys(expected, submitted) == False:
            return False
        # Lets see if we have a node to upload this data to
        # TODO: Check if we e allowed to upload to this marker via Username/Password
        fid = cherrypy.config['model'].dbsearchfor_colval('apikey', data['submitted']['dev_nickname'])
        if fid is False:
            data['altresponse'] = '{"result":"KO", "message":"No marker to upload to"}'
            return data
        else:
            # We have a marker so lets read the data                                                 
            # TODO: Create a log so we can track uploads
            try:
                # Looks ok so lets load it
                if data['postedbody'] != '{}': 
                    js = json.loads(data['postedbody'])
                    array = []
                    # Create the csv headera
                    headerlist = ['last_updated', 'timestamp']+js['channel_names']
                    header = ','.join(headerlist)
                    # create the csv strings
                    for x in js['data']:
                        array.append( ','.join(map(str, x)) )
                    csv = '\n'.join(array)
                else:
                    # We've been sent empty JSON, but all is ok, lets halt the process
                    data['altresponse'] = '{"result":"OK"}'
                    return data
            except:
                # Could be invalid JSON, so return an error to the gateway
                data['altresponse'] = '{"result":"KO", "message":"Invalid JSON"}'
                return data
            # Now try and save the data to file
            try:
                cherrypy.config['datalogger'].log('data/'+fid+'/data.csv', header, csv)
                latest = OrderedDict()
                timestamp = js['data'][-1][0]
                humantime = datetime.datetime.fromtimestamp(timestamp).strftime('%d %b %Y %I:%M%p')
                values = [humantime]+js['data'][-1]
                # Convert the last value to key value pairs
                i = 0
                for key in headerlist: 
                    if key == 'raw_particles' : key = 'raw'
                    if key == 'particle_concentration' : key = 'concentration'
                    latest[key] = values[i]
                    i += 1
                lateststr = json.dumps(latest)
                print(lateststr)
                cherrypy.config['model'].update_node(fid, {'latest':lateststr})
                data['altresponse'] = '{"result":"OK","message":"Upload successful!","payload":{"successful_records":"1","failed_records":"0"}}'
            except:
                data['altresponse'] = '{"result":"KO","message":"Unable to save data to file"}'
        return data


#================== Citizen Sense Kit submission ============================#
class CitizenSenseKitSubmission:

    # Check if submission is recognised, if it is, return structured data
    def checksubmission(self, data):
        msg = ''
        self.data = data
        # List of field names we are expecting and specify:
        # TODO: Also count the number of fields
        expectedkeys = ['uid', 'deviceserial', 'data']
        for key in data['submitted'].keys():
            if key not in expectedkeys: 
                return False
        # Now check we have a node to post to
        msg = 'A Citizen Sense Kit submission'
        #if exists(uid):
        # And save the new data to file
        self.data['success']['msg'] = msg
        return self.data

