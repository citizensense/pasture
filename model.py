#!/usr/bin/python3
import cherrypy, json, csv, re, time, datetime, uuid, os, sys,string, subprocess, arrow
from collections import OrderedDict
from database import *
# TODO: Remove this from model & keep in view..
from jinja2 import Environment, PackageLoader

# TODO: Security check fid variable
# TODO: Add list of 'registered devices' to config
# TODO: Swap apikeys if new marked is created with the same one..
class Model:
    
    # Create a database object for us to use
    def __init__(self):
        dbstruct = self.database_structure()
        self.db = Database(cherrypy.config['dbfile'], dbstruct, ignore='locals')
        self.dbfields = self.db.keys
        self.kwargs = {}

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
            # A place to store csvs
            ('csvs', [
                ('cid', 'INTEGER PRIMARY KEY'),
                ('nid', 'INTEGER'),                
                ('created', 'INTEGER'),
                ('header', 'TEXT'),
                ('timestamp', 'INTEGER'),
                ('csv', 'TEXT')
            ]),
            # A place to store annotations
            ('annotations', [
                ('aid', 'INTEGER PRIMARY KEY'),
                ('nid', 'INTEGER'), 
                ('uid', 'INTEGER'),
                ('timestamp', 'INTEGER'),
                ('text', 'TEXT'),
                ('created', 'INTEGER')
            ]),
            # This isn't created in the database, its just used for internal var storage
            # TODO: Pos get rid of this as its setup in the controller
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

    # Parse POSTED data and determine what we need to do with it
    def parse_submission(self, data):
        # Grab the submitted data and convert it to JSON with all commas escaped to &#44;
        jsondump = json.dumps(data['submitted'])
        data['info']['submissiondata'] = jsondump.replace(',', '&#44')
        # Check what/who submitted this data, parse it, then fill in our data structure
        plugins=(AnnotationSubmission, UploadformSubmission, SpecGatewaySubmission, CitizenSenseKitSubmission)
        for plugin in plugins:
            obj = plugin()
            parsedoutput = obj.checksubmission(self, data)
            if parsedoutput is not False: break
        # Save the number of open sessions
        data['nsessions'] = self.grab_opensessions()
        # Prepare for json response
        if parsedoutput:
            # TODO: Should get rid of this and just return the response from the
            # modules... they should decide to pop or not!
            data.pop('filestosave', None)
            data.pop('submitted', None) 
            # Check if we return a custom repsponse
            if data['altresponse'] is not '':
                return data['altresponse']
            # If not, the check for errors
            elif len(parsedoutput['errors']) <= 0:
                # All looks OK
                # TODO: SHould move this to the modules...
                data['success']['code'] = 'OK'
                data['success']['msg'] = 'A new node has been created' 
        else:
            # The submission hasn't been recognised
            data.pop('filestosave', None)
            data.pop('info', None)
            data.pop("success", None)
            data['errors']['form'] = 'Post structure not recognised' 
        return json.dumps(data)
    
    # CREATE A NEW ANNOTATION
    def create_annotation(self, nid, uid, timestamp, text):
        # And construct the ordered dict ready for the database
        created = int(time.time()) # ALTER TABLE annotations ADD COLUMN created INT;
        newannotation = OrderedDict([
            ('fieldnames',['nid', 'uid', 'timestamp', 'text', 'created']),
            ('values',[[nid, uid, timestamp, text, created]])  
        ]) 
        aid = self.db.create('annotations', newannotation)
        response = {}
        if aid == None or aid == False:
            response['code'] = 'KO'
            response['msg'] = 'Could not create annotation. DB Error: {0}'.format(self.db.msg)
        else:
            response['code'] = 'OK'
            response['msg'] = 'Annotation #{0} has been saved'.format(aid)
        response['timestamp'] = timestamp;
        response['aid'] = aid; 
        return response
    
    # UPDATE AN EXISTING ANNOTATION
    def update_annotation(self, aid, data):
        resp = {'code':'KO', 'msg':'', 'aid':aid}
        # Lets check we have valid variables
        try:
            text = data['annotation']
            user = data['username']
            passwd = data['password']
            sessionid = data['sessionid'] 
        except:
            resp['msg'] = 'Error: Can\'t find one of:\n annotation OR username OR password OR sessionid'
            return resp
        # Then check if we have permission to update
        user = self.validuser(user, passwd, sessionid)
        if user:
            uid = user['uid'] 
            resp['sessionid'] = user['sessionid']
        else:
            resp['msg'] = 'This username/password combination has not been recognised. Or you may have been automatically logged out. Please try again.'
            resp['sessionid'] = ''
            return resp
        # And check if this specific user can update this specific annotation
        anno = self.view_annotation(aid)
        if anno['uid'] is not user['uid'] and user['permissions'] is not 'admin':
            resp['msg'] = 'Sorry. this user cannot update this annotation.'
            return resp
        # Then finaly make the database call 
        toupdate = {'text':text}
        dbresp = self.db.update('annotations', 'aid', aid, toupdate)
        if dbresp:
            resp['code'] = 'OK'
            resp['msg'] = 'Success! The annotation has been updated.'
        else:
            resp['code'] = 'KO'
            resp['msg'] = 'Database Error: '.format(self.db.msg)
        return resp

    # DELETE AN ANNOTATION
    def delete_annotation(self, aid, data):
        #print(data)
        resp = {'code':'KO','msg':''}
        user = self.validuser(data['username'], data['password'], data['sessionid'] )  
        #print('====USER=====')
        #print(user)  
        # Check if this user can delete this node
        if user == False:
            resp['msg'] = 'User not recognised. Try refreshing the page.'
            candelete = False
        elif user['permissions'] is 'admin':
            candelete = True
        # Check if the user owns the marker
        else:
            searchfor = {'uid':user['uid'], 'aid':aid}
            intable = 'annotations'
            returnfields = ['aid']
            anno = self.db.searchfor(intable, returnfields, searchfor)
            print(self.db.msg)
            if anno is not None:
                candelete = True
            else:
                response['msg'] = 'This annotation was created by another user. You do not have permission to delete it.'
                return response
        # Ok can we now delete please?
        if candelete:
            db = self.db.dbquery('DELETE FROM annotations WHERE aid={}'.format(int(aid)) )
            if db is not False:
                resp['code'] = 'OK'
                resp['msg'] = 'Deleted annotation'
            else:
                resp['msg'] = 'Database Error:\n {}'.format(self.db.msg) 
            # Update the database
        #return response
        return resp
    
    # View a single annotation
    def view_annotation(self, aid):
        fields = ['aid', 'uid']
        searchfor = {'aid':aid}
        intable = 'annotations'
        returnfields = ['aid', 'uid'] 
        row = self.db.searchfor(intable, returnfields, searchfor)
        resp = {}
        if row:
            # TODO: This shoudl be moved into database.py
            resp['aid'] = row[0]
            resp['uid'] = row[1]
        else:
            resp = row
        return resp

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
    def view_all(self, qry=''):
        fields = ['nid', 'lat', 'lon', 'title', 'visible', 'datatype', 'latest', 'created', 'updated']
        qry = ' WHERE visible=1 {}'.format(qry)  
        jsondisplay = self.db.readasjson('nodes', fields, [], qry)
        print(self.db.msg)
        if jsondisplay:
            return jsondisplay
        else:
            return '{}'
    
    # VIEW AN INDIVIDUAL NODE
    # TODO: This is inefficiant - no need to convert in/out of json...
    def view_node(self, nid):
        fields = ['datatype', 'apikey', 'title', 'description', 'lat', 'lon', 
                  'createdhuman', 'updated', 
                  'latest', 'nid', 'createdby']
        jsonstr = self.db.readasjson('nodes', fields, [int(nid)])  
        if jsonstr:     
            data = json.loads(jsonstr)
            node = data[0]
            # Now bring back some actual data!
            searchfor = {'nid':nid}
            intable = 'csvs'
            returnfields = ['created', 'csv','header']
            sql = 'ORDER BY created DESC LIMIT 5' 
            rows = self.db.searchfor(intable, returnfields, searchfor, sql, 'many')
            node['data'] = json.dumps(rows)
            return json.dumps(node)
        else: 
            return '{}'
    
    # VIEW AN INDIVIDUAL as an HTML table
    def view_node_html(self, nid):
        # TODO: Move view code out of model
        ENV = Environment(loader=PackageLoader('controllers', 'templates')) 
        template = ENV.get_template('data.html') 
        # Setup some base variables
        ENV = Environment(loader=PackageLoader('controllers', 'templates')) 
        fields = ['datatype', 'apikey', 'title', 'description', 'lat', 'lon', 
                  'createdhuman', 'updated', 'latest', 'nid', 'createdby']
        timeadj = int(self.kwargs['timeadj']) if 'timeadj' in self.kwargs else 0 
        timeadjcalc = (timeadj*60)*60 # Timestamp adjustment for local time
        count = int(self.kwargs['count']) if 'count' in self.kwargs else 3000
        if count > 12000: count = 12000
        countfrom = int(self.kwargs['from']) if 'from' in self.kwargs else 0
        if countfrom < 0: countfrom = 0
        # Now make the query
        #try:
        jsonstr = self.db.readasjson('nodes', fields, [int(nid)])  
        if jsonstr: 
            data = json.loads(jsonstr)
            node = data[0]
            graph = []
            # TODO This code is a temp fix and should be removed as the submission should be consistant across all datatypes
            if node['datatype'] == 'speck':
                keyarr = ['timestamp', 'raw', 'concentration', 'humidity']
                graph = {   'humidity':'humidity', 
                            'concentration':'particles'
                }          
            else:
                graph = {   ' NOppb':'NOppb', 
                            ' O3ppb':'O3ppb',
                            ' NO2ppb':'NO2ppb',
                            ' PIDppm':'PIDppm'
                }
                node['latest']['csvheader']
                keyarr = node['latest']['csvheader'].split(',')
            if 'name' in node['latest']:
                node['title'] = '{} [{}]'.format(node['title'], node['latest']['name'])
            header = '<h2>{}: Created {}</h2><p>{}</p><hr />'.format(node['title'], node['createdhuman'], node['description'])
            # Now bring back some actual data!
            searchfor = {'nid':nid}
            intable = 'csvs'
            returnfields = ['created', 'csv']
            sql = 'ORDER BY timestamp ASC LIMIT {}, {}'.format(countfrom, count) 
            rows = self.db.searchfor(intable, returnfields, searchfor, sql, 'many')
            # And grab a list of annotations: TODO: Think about limits i.e. sql = 'ORDER BY timestamp DESC LIMIT {}, {}'.format(countfrom, count) 
            sql = 'ORDER BY timestamp DESC '
            annotations = self.db.searchfor('annotations', ['aid','timestamp','text', 'nid'], {'nid':nid}, sql, 'many')
            i=0
            for ano in annotations:
                timestamp = int(ano[1]+timeadjcalc)
                print(timestamp)
                mydate = datetime.datetime.fromtimestamp(timestamp).strftime('%d %b %Y %H:%M:%S ({}GMT)'.format(timeadj))
                annotations[i] = (ano[0], ano[1], ano[2], mydate, ano[3])
                i+=1
            annotationsjson = json.dumps(annotations)
            # And prep vars used to format the output
            table = '<table class="whitetable"><tr><th>'
            table += '</th><th>'.join(keyarr)+'</th></tr>\n\n\n'
            starttime = ''
            rowdatetime = ''
            # Make a record of the position of the keys
            graphpos = {}
            for item in graph:
                key = item
                mapname = graph[item].replace(' ', '')
                for position, findkey in enumerate(keyarr):
                    if findkey == key:
                        graphpos[key] = {'position':position,'color':"'#000'", 'data':[], 'name':"'{}'".format(mapname)}
            i = 0
            # Now loop through the data and generate data and json
            for row in rows:
                vals = row[1].split(',')
                # Create a timestamp
                timestamp = int(vals[0]) #+timeadjcalc
                time = arrow.get(timestamp)
                local = time.to('US/Central')
                rowdatetime = local.format('YYYY-MM-DD HH:mm:ss')
                vals[0] = rowdatetime
                if i == 0: starttime = rowdatetime
                # Prep the js
                for key in graph:
                    n = graphpos[key]['position']
                    val = vals[n]
                    if val.replace(' ', '') is not '':
                        graphpos[key]['data'].append( {'x':timestamp, 'y':val} )
                # Prep the HTML
                line = '<tr><td>'
                line += '</td><td>'.join(vals)
                line += '</td></tr>'
                table += line
                i += 1
                # TODO: Prep the array for the jinja template
            # Now prep the final output
            data = []
            for item in graphpos: data.append(graphpos[item])
            jsondata = json.dumps(data)
            jsdata = jsondata.replace('"', '') # Javscript formated data
            jsdata = jsdata.replace(' ', '')
            table += '</table>'
            prevcount = countfrom-count
            nextlink = '<a class="prevnext" href="/api/viewhtml/{}/?count={}&from={}&timeadj={}">Next&raquo;</a>'.format(nid, count, countfrom+count, timeadj)
            if prevcount <= 0: 
                prevcount=0
                prevlink = ''
            if countfrom > 0:
                prevlink = '<a class="prevnext" href="/api/viewhtml/{}/?count={}&from={}&timeadj={}">&#171;Previous</a>'.format(nid, count, prevcount, timeadj)
            header += '<strong>{}</strong> | <strong>View</strong> {} Points <strong> From:</strong> {} <strong>To:</strong> {} | <strong>{}</strong>'.format(prevlink, count, rowdatetime, starttime,  nextlink)
            templatevars = {'nid':nid,'table':table, 'header':header, 'jsdata':jsdata, 'timeadj':timeadj, 'annotationsjson':annotationsjson, 'annotations':annotations}
            return template.render(var=templatevars)  
        else: 
            return 'No data'
        #except Exception as e:
        #    return 'error: '+str(e)

    # UPDATE SPECIFIED FIELDS OF A NODE
    def update_node(self, nid, fieldsnvalues):
        update = self.db.update('nodes', 'nid', int(nid), fieldsnvalues)
        print(self.db.update)
        if update:return True
        else: return False

    # DELETE A NODE
    def delete_node(self, response, nid, user, password):
        candelete = False
        # This username/password combination is valid
        user = self.validuser(user, password)
        if user == False:
            response['errors']['failed'] = 'This username/password combination has not been recognised'
            return response
        # Check if this user can delete this node
        if user['permissions'] is 'admin':
            candelete = True
        # Check if the user owns the marker
        else:
            searchfor = {'createdby':user['uid'], 'nid':nid}
            intable = 'nodes'
            returnfields = ['nid', 'createdby']
            node = self.db.searchfor(intable, returnfields, searchfor)
            print(self.db.msg)
            if node is not None:
                candelete = True
            else:
                response['errors']['failed'] = 'This marker was created by another user. You do not have permission to delete it.'
                return response
        # Ok can we now delete please?
        if candelete:
            # Update the database
            table = 'nodes'
            idname = 'nid'
            idval= nid
            fieldnvalues = {'visible':0}
            if self.db.update(table, idname, idval, fieldnvalues):
                response['success']['completed'] = 'Marker has been deleted' 
            else:
                response['errors']['failed'] = 'Error: Failed to delete marker' 
            print(self.db.msg)
        return response
    
    # MANAGE USER SESSIONS
    # TODO: Tidy up!! Very messy at the moment
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
                if uname not in cherrypy.config['CONFIG']['users']:
                    msg += "\nUsername not recognised: "+uname
                else:
                    msg += "\nUsername has been recognised:"+uname
                    uid = cherrypy.config['CONFIG']['users'][uname]['uid']
                    username = uname
                    password = cherrypy.config['CONFIG']['users'][uname]['password']
                    permissions = cherrypy.config['CONFIG']['users'][uname]['permissions']  
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
                return False
            else: 
                state = True
        if len(expected) is not len(provided):
            state = False
        return state
    
#==================================================================#
#==============PLUGINS TO HANDLE MULTIPLE TYPES OF DATA SUBMISSION==================#
#===================================================================================#

#========= THE ANNOTATION FORM ============================================#
class AnnotationSubmission:

    # [REQUIRED METHOD] Check if submission is recognised, if it is, return structured data
    def checksubmission(self, model, data):
        self.data = data
        self.model = model
        response = {}    
        response['msg'] = ''
        response['code'] = 'OK'   
        # List of field names we are expecting
        expected = ['timecode','annotation', 'chartid', 'username', 'password', 'sessionid', 'update'] # username, password, sessionid
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
            response['code'] = 'KO'
            response['msg'] = 'This username/password combination has not been recognised. Or you may have been automatically logged out. Please try again.'
            data['sessionid'] = ''           
        else:
            uid = self.user['uid'] 
            response['sessionid'] = self.user['sessionid']
        # OK lets validate the data
        try:
            nid = int(data['submitted']['chartid'].replace('chart',''))
            timecode = int(data['submitted']['timecode'])
        except Exception as e:
            response['code'] = 'KO'  
            response['msg'] += 'Invalid ChartID or timecode'  
        annotation = data['submitted']['annotation'].strip()
        if annotation == '':
            response['code'] = 'KO'  
            response['msg'] += 'Please fill in the annotation field'     
        # Now attempt to save to the database
        if response['code'] != 'KO':
            dbresp = self.model.create_annotation(nid, uid, timecode, annotation)
            if dbresp['code'] == 'KO':
                response['code'] = 'KO'
                response['msg'] = 'DB Error: '+dbresp['msg']
            else:
                response['msg'] = dbresp['msg']  
                response['aid'] = dbresp['aid']
                response['timestamp'] =  dbresp['timestamp']  
        data['altresponse'] = json.dumps(response)
        cherrypy.response.headers['Content-Type']= 'text/html' 
        return data
 
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
            'submissiondata':'{}',
            'visible':1  
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
        data['username'] = self.user['username']  
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
# Test a fack Speck Gateway post with the following curl command in the terminal:
#    curl -H "Content-Type:application/json" http://localhost:8787/api/bodytrack/jupload?dev_nickname=Speck -d @etc/speck_data.json
#    curl -i -u f:f http://localhost:8787/api/bodytrack/upload -d dev_nickname=test -d channel_names='["a","b"]' -d data='[[1332754616,1,10], [1332754617,-1,20]]'
#============================================================================#
class SpecGatewaySubmission:
    
    # Check if submission is recognised, if it is, return structured data
    # TODO: This is looking a bit messy so tidy up & move try/except to individual calls
    def checksubmission(self, model, data):
        # List of field names we are expecting. Reject if they don't match
        expected = ['dev_nickname']
        expected2 = ["dev_nickname", "data", "channel_names"]
        submitted = data['submitted'].keys()
        # Check if we recognise this post
        msg =''
        if model.match_keys(expected, submitted) == True:    # We got a Speck Gatweway
            try: 
                if data['body'] == '{}': 
                    data['altresponse'] = '{"result":"OK"}'
                    return data
                allspeckdata = json.loads(data['body'])
                speckdata = allspeckdata['data']
                speckchannels = allspeckdata['channel_names']
            except Exception as e: 
                speckdata = []
                msg = ' But data could be invalid from Speck Gateway: '+str(e)
        elif model.match_keys(expected2, submitted) == True: # General body track post
            try:
                speckdata =  json.loads(data['submitted']['data'])
                speckchannels = json.loads(data['submitted']['channel_names'])
            except Exception as e:
                print('BAD speckdata JSON: '+str(e))
                print( json.dumps(data) )
                msg = 'But data could be invalid'
                speckdata = []
        else: # Not recognised so reject
            return False

        # If we have empy JSON all is ok but there is nothing to do
        if len(speckdata) == 0:
            data['altresponse'] = '{"result":"OK", "msg":"We have connected.'+msg+'"}'
            return data
        
        # Now lets see if we have a node to upload this data to
        apikey = data['submitted']['dev_nickname'] # The device name/id
        searchfor = {'apikey':apikey, 'visible':1}
        intable = 'nodes'
        returnfields = ['nid', 'createdby', 'datatype']
        node = model.db.searchfor(intable, returnfields, searchfor)
        print(model.db.msg)
        print('Searched for: '+apikey)
        print(node)
        if node is None:
            data['altresponse'] = '{"result":"KO", "message":"No marker to upload to"}'
            return data
        else:
            nid = node[0]

        # We have a marker so lets read the data                                                 
        # TODO: Create a log so we can track uploads
        # Create a csv header
        headerlist = ['timestamp']+speckchannels
        csvheader = ','.join(headerlist)
        csvheader = '#MARKER_ID:{}\n{}'.format(nid,csvheader)
        # Create the csv value strings
        csvstrlist = []
        csvvaluelist = []
        created  = int(time.time()) 
        for x in speckdata:
            csvline =  ','.join(map(str, x))
            csvstrlist.append(csvline)
            timestamp = x[0]
            print('{}: {}'.format(timestamp, csvline))
            csvvaluelist.append([nid, timestamp, created, csvheader, csvline])
        csvstring = '\n'.join(csvstrlist)
        
        # Now try and save the data to file
        print('\n=======String to save')
        print(csvheader+'\n'+csvstring)
        try:
            directory = 'data/csvs/'+str(nid)
            # Check we have a folder
            cherrypy.config['datalogger'].createDir(directory)
            # Now save the file
            myfile = '{0}/{1}.csv'.format(directory, nid)
            cherrypy.config['datalogger'].log(myfile, csvheader, csvstring)
        except Exception as e: 
            data['altresponse'] = '{"result":"KO","message":"Unable to save speck data to file"}'
            return data
        
        # And create a 'latest' summary for the display in a nice key:value json string
        latest = OrderedDict()
        values = speckdata[-1]
        i = 0
        for key in headerlist: 
            if key == 'raw_particles' : key = 'raw'
            if key == 'particle_concentration' : key = 'concentration'
            latest[key] = values[i]
            i += 1
        lateststr = json.dumps(latest)

        # Now save the latest data
        print('NID:'+str(nid))
        model.db.update('nodes', 'nid', nid, {'latest':lateststr, 'updated':int(time.time())})
        print(model.db.msg)
        
        # And save a copy of the csv in the database (should seperate into seperate fields...)
        newcsvs = OrderedDict([
            ('fieldnames',['nid', 'timestamp', 'created', 'header', 'csv']),
            ('values', csvvaluelist)  
        ]) 
        resp = model.db.create('csvs', newcsvs)
        print(model.db.msg)
        print(newcsvs)
        data['altresponse'] = '{"result":"OK","message":"Upload successful!","payload":{"successful_records":"1","failed_records":"0"}}'
        return data

#================== Citizen Sense Kit submission ============================#
class CitizenSenseKitSubmission:

    # Check if submission is recognised, if it is, return structured data
    def checksubmission(self, model, data):
        
        # Check if we recognise this post
        expected = ["serial", "name", "jsonkeys", "jsonvalues", "MAC"]
        submitted = data['submitted'].keys()
        msg =''
        if model.match_keys(expected, submitted) is not True:    # We got a csk submission
            return False
        
        # Check if this is a known MAC address
        if data['submitted']['MAC'] not in cherrypy.config['CONFIG']['MACS']:
            data['altresponse'] = '{"success":"KO", "errors":[{"MAC":"MAC not recognised"}]}'
            return data

        # Save the name to use later
        name = data['submitted']['name'] # The kit name

        # Check if there is a node to save this data to
        apikey = data['submitted']['serial'] # The raspberry pi serial number
        searchfor = {'apikey':apikey, 'visible':1}
        intable = 'nodes'
        returnfields = ['nid', 'createdby', 'datatype']
        node = model.db.searchfor(intable, returnfields, searchfor)
        #print(model.db.msg)
        #print('Searched for: '+apikey)
        #print(node)
        if node is None:
            data['altresponse'] = '{"success":"KO", "errors":[{"serial":"No marker to submit to. Either no serial or not visible"}]}'
            return data
        else:
            nid = node[0]
        
        # OK lets parse the response
        try:
            # Create container for 'latest' data for display in a nice 'key:value' display
            latest = OrderedDict()
            latest['csvheader'] = data['submitted']['jsonkeys'].replace('[', '')
            latest['csvheader'] = latest['csvheader'].replace(']', '')
            latest['csvheader'] = latest['csvheader'].replace('"', '')
            latest['name'] = data['submitted']['name']
            keys = json.loads(data['submitted']['jsonkeys'])
            for key in keys:
                latest[key] = ''
            newvalues = []
            # Fomat the data ready to save
            rows = json.loads(data['submitted']['jsonvalues'] )
            created  = int(time.time()) 
            newvalues = []
            for row in rows:
                i = 0
                values = row.split(',')
                csvtimecode = values[0]
                newvalues.append([nid, created, row, csvtimecode])
                for key in keys:
                    if values[i] != '': latest[key] = values[i]
                    i += 1
                lateststr = json.dumps(latest)
        except Exception as e:
            print('Failed to read POSTED json: '+str(e))
            data['altresponse'] = '{"success":"KO", "errors":[{"json":"Posted values are not in a recognised json format: {0}"}]}'.format(str(e))
            return data
        
        # 
        print('===========Attempt to save=======')
        print('Latest')
        print(json.dumps(latest))

        # Now update the node and save the 'latest' data
        success = model.db.update('nodes', 'nid', nid, {'latest':lateststr, 'updated':int(time.time())})
        if success is not True:
            print('Failed: To save \'latest\' data in node')
            data['altresponse'] = '{"success":"KO", "errors":[{"database":"Unable to update node "}]}'
            return data
        else:
            print('Sucess: Saved latest in node:')
            
        # And now create a new csv record
        newcsvs = OrderedDict([
            ('fieldnames',['nid', 'created', 'csv', 'timestamp']),
            ('values', newvalues)  
        ]) 
        resp = model.db.create('csvs', newcsvs)
        if resp is not None:
            print('Failed: To create new csvDBrecord')
            data['altresponse'] = '{"success":"KO", "errors":[{"database":"Unable to create new csv records in database"}]}'
            return data
        else:
            print('Sucess: Created new csvDBrecord')

        # Now try and save the data to file
        csvheader = ','.join(keys)
        csvvalues = '\n'.join(rows)
        csvheader = '#MARKER_ID:{}\n{}'.format(nid,csvheader)
        try:
            directory = 'data/csvs/'+str(nid)
            # Check we have a folder
            cherrypy.config['datalogger'].createDir(directory)
            # Now save the file
            myfile = '{}/{}.csv'.format(directory, nid)
            cherrypy.config['datalogger'].log(myfile, csvheader, csvvalues)
            print('Save to file: Sucess')
        except Exception as e: 
            print('Couldn\'t save data to file')
            data['altresponse'] =  '{"success":[{"OK":"Data saved to database but not file"}], "errors":[]}'
            return data
        
        # All done we have complete sucess
        print("Sucess, we have save new data to DB and file for marker: "+str(nid))
        data['altresponse'] = '{"success":"Saved submitted data", "errors":[]}'
        return data

